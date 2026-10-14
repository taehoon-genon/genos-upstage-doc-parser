import base64
import os
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

UPSTAGE_API_URL = os.environ["UPSTAGE_API_URL"]
UPSTAGE_API_KEY = os.environ.get("UPSTAGE_API_KEY")
UPSTAGE_MODEL = os.environ.get("UPSTAGE_MODEL")

# Upstage 서버 타임아웃(300초)과 같게 둔다.
UPSTAGE_TIMEOUT = 300

app = FastAPI()
client = httpx.AsyncClient(timeout=UPSTAGE_TIMEOUT, verify=False)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/v1/document-parse")
async def document_parse(request: Request):
    form = await request.form()
    # 문서 없이 필드만 와도 multipart로 보내야 Upstage가 원래 요청과 같은 오류를 준다.
    # 그래서 문자열 필드도 files 목록에 넣는다.
    parts = []
    for name, value in form.multi_items():
        if isinstance(value, str):
            parts.append((name, (None, value)))
        else:
            parts.append((name, (value.filename, value.file, value.content_type)))

    try:
        upstream = await _send(parts)
    except httpx.TimeoutException:
        return _error(504, "upstream_timeout", "Upstage 응답 시간이 초과되었습니다.")
    except httpx.TransportError:
        return _error(502, "upstream_unreachable", "Upstage에 연결하지 못했습니다.")

    return Response(
        upstream.content,
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type"),
    )


async def _send(parts):
    if UPSTAGE_MODEL:
        parts = [part for part in parts if part[0] != "model"]
        parts.append(("model", (None, UPSTAGE_MODEL)))
    headers = {"Authorization": f"Bearer {UPSTAGE_API_KEY}"} if UPSTAGE_API_KEY else {}
    return await client.post(UPSTAGE_API_URL, files=parts, headers=headers)


@app.post("/preprocess")
async def preprocess(request: Request):
    body = await request.json()
    params = body.get("params") or {}
    size = int(params.get("chunk_size", 1000))
    overlap = int(params.get("chunk_overlap", 100))
    name = body.get("file_name") or "document"
    if not body.get("file_content_base64"):
        return _fail("file_content_base64가 없습니다.")

    parts = [
        ("document", (name, base64.b64decode(body["file_content_base64"]))),
        ("output_formats", (None, "['markdown']")),
    ]
    try:
        upstream = await _send(parts)
    except httpx.TimeoutException:
        return _fail("Upstage 응답 시간이 초과되었습니다.")
    except httpx.TransportError:
        return _fail("Upstage에 연결하지 못했습니다.")
    if upstream.status_code != 200:
        return _fail(f"Upstage 오류 {upstream.status_code}: {upstream.text[:200]}")

    result = upstream.json()
    # 요소를 chunk_size 이하 조각으로 자른 뒤, chunk_size까지 이어 붙여 청크를 만든다.
    pieces = []
    for e in result["elements"]:
        text = e["content"]["markdown"].strip()
        pieces += [(e["page"], text[i:i + size]) for i in range(0, len(text), size)]

    chunks, buf, page = [], "", 1
    for p, t in pieces:
        if buf and len(buf) + len(t) + 2 > size:
            chunks.append((page, buf))
            buf = buf[-overlap:] if overlap else ""
            page = p
        elif not buf:
            page = p
        buf = f"{buf}\n\n{t}" if buf else t
    if buf:
        chunks.append((page, buf))

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    data = [
        {
            "text": t,
            "n_chars": len(t),
            "n_words": len(t.split()),
            "n_lines": len(t.splitlines()),
            "i_page": p,
            "n_page": result["usage"]["pages"],
            "i_chunk_on_doc": i,
            "n_chunk_of_doc": len(chunks),
            "reg_date": now,
            "file_name": name,
        }
        for i, (p, t) in enumerate(chunks)
    ]
    return {"code": 0, "errMsg": "success", "data": data}


def _fail(message: str) -> JSONResponse:
    return JSONResponse({"code": 1, "errMsg": message, "data": None})


def _error(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status_code)

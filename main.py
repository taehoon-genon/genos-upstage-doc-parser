import os

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

    if UPSTAGE_MODEL:
        parts = [part for part in parts if part[0] != "model"]
        parts.append(("model", (None, UPSTAGE_MODEL)))
    headers = {"Authorization": f"Bearer {UPSTAGE_API_KEY}"} if UPSTAGE_API_KEY else {}

    try:
        upstream = await client.post(UPSTAGE_API_URL, files=parts, headers=headers)
    except httpx.TimeoutException:
        return _error(504, "upstream_timeout", "Upstage 응답 시간이 초과되었습니다.")
    except httpx.TransportError:
        return _error(502, "upstream_unreachable", "Upstage에 연결하지 못했습니다.")

    return Response(
        upstream.content,
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type"),
    )


def _error(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status_code)

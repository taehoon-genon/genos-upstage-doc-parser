import os

os.environ.setdefault("UPSTAGE_API_URL", "https://upstream.test/v1/document-digitization")
os.environ.setdefault("UPSTAGE_API_KEY", "test-key")
os.environ.setdefault("UPSTAGE_MODEL", "document-parse")

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

import main

URL = os.environ["UPSTAGE_API_URL"]
http = TestClient(main.app)


def post_pdf(**fields):
    return http.post(
        "/v1/document-parse",
        files={"document": ("a.pdf", b"%PDF-1.4 sample", "application/pdf")},
        data=fields,
    )


@respx.mock
def test_인자와_파일을_그대로_넘기고_응답을_돌려준다():
    route = respx.post(URL).respond(200, json={"api": "2.0", "usage": {"pages": 1}})

    res = post_pdf(ocr="force", output_formats="['markdown']")

    assert res.status_code == 200
    assert res.json() == {"api": "2.0", "usage": {"pages": 1}}
    sent = route.calls.last.request
    assert sent.headers["authorization"] == "Bearer test-key"
    assert b'name="model"' in sent.content and b"document-parse" in sent.content
    assert b'name="ocr"' in sent.content and b"force" in sent.content
    assert b"['markdown']" in sent.content
    assert b'filename="a.pdf"' in sent.content and b"%PDF-1.4 sample" in sent.content


@respx.mock
def test_문서가_없어도_multipart로_넘긴다():
    route = respx.post(URL).respond(400, json={})

    http.post("/v1/document-parse", data={"ocr": "auto"})

    sent = route.calls.last.request
    assert sent.headers["content-type"].startswith("multipart/form-data")


@respx.mock
def test_호출자가_보낸_model은_설정값으로_바뀐다():
    route = respx.post(URL).respond(200, json={})

    post_pdf(model="other")

    body = route.calls.last.request.content
    assert body.count(b'name="model"') == 1 and b"other" not in body


@respx.mock
def test_키와_모델이_없으면_붙이지_않는다(monkeypatch):
    monkeypatch.setattr(main, "UPSTAGE_API_KEY", None)
    monkeypatch.setattr(main, "UPSTAGE_MODEL", None)
    route = respx.post(URL).respond(200, json={})

    post_pdf()

    sent = route.calls.last.request
    assert "authorization" not in sent.headers
    assert b'name="model"' not in sent.content


@respx.mock
@pytest.mark.parametrize("status", [400, 401, 413, 429])
def test_업스트림_오류는_상태_코드와_본문을_그대로_돌려준다(status):
    body = {"error": {"code": "from_upstream"}}
    respx.post(URL).respond(status, json=body)

    res = post_pdf()

    assert res.status_code == status
    assert res.json() == body


@respx.mock
def test_업스트림_타임아웃은_504():
    respx.post(URL).mock(side_effect=httpx.ReadTimeout("slow"))

    res = post_pdf()

    assert res.status_code == 504
    assert res.json()["error"]["code"] == "upstream_timeout"


@respx.mock
def test_업스트림_연결_실패는_502():
    respx.post(URL).mock(side_effect=httpx.ConnectError("down"))

    res = post_pdf()

    assert res.status_code == 502
    assert res.json()["error"]["code"] == "upstream_unreachable"


def test_health():
    assert http.get("/health").json() == {"status": "ok"}

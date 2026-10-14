import base64
import os

os.environ.setdefault("UPSTAGE_API_URL", "https://upstream.test/v1/document-digitization")
os.environ.setdefault("UPSTAGE_API_KEY", "test-key")
os.environ.setdefault("UPSTAGE_MODEL", "document-parse")

import httpx
import respx
from fastapi.testclient import TestClient

import main

URL = os.environ["UPSTAGE_API_URL"]
http = TestClient(main.app)


def element(page, markdown):
    return {"page": page, "content": {"markdown": markdown}}


def request_body(size=100, overlap=10):
    return {
        "file_path": "/x/a.pdf",
        "file_name": "a.pdf",
        "params": {"chunk_size": size, "chunk_overlap": overlap},
        "file_content_base64": base64.b64encode(b"%PDF").decode(),
    }


@respx.mock
def test_요소를_chunk_size까지_합쳐_청크로_만든다():
    elements = [element(1, "A" * 60), element(1, "B" * 60), element(2, "C" * 250), element(3, "")]
    route = respx.post(URL).respond(200, json={"elements": elements, "usage": {"pages": 3}})

    res = http.post("/preprocess", json=request_body()).json()

    assert res["code"] == 0
    data = res["data"]
    assert [c["i_page"] for c in data] == [1, 1, 2, 2, 2]
    assert [c["i_chunk_on_doc"] for c in data] == [0, 1, 2, 3, 4]
    assert all(c["n_chunk_of_doc"] == 5 and c["n_page"] == 3 for c in data)
    assert all(len(c["text"]) <= 100 + 10 + 2 for c in data)
    assert data[1]["text"].startswith("A" * 10 + "\n\n" + "B")
    assert data[0]["reg_date"].endswith("Z") and data[0]["file_name"] == "a.pdf"
    sent = route.calls.last.request.content
    assert b"%PDF" in sent and b"['markdown']" in sent and b"document-parse" in sent


@respx.mock
def test_오류는_HTTP_200에_code_1로_돌려준다():
    respx.post(URL).respond(413, json={"error": {"code": "too_large"}})
    res = http.post("/preprocess", json=request_body())
    assert res.status_code == 200
    assert res.json()["code"] == 1 and "413" in res.json()["errMsg"]

    respx.post(URL).mock(side_effect=httpx.ConnectError("x"))
    assert http.post("/preprocess", json=request_body()).json()["code"] == 1

    assert http.post("/preprocess", json={"params": {}}).json()["code"] == 1

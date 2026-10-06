# Upstage Document Parser 프록시

`POST /v1/document-parse` 요청을 Upstage Document Parser로 그대로 넘기고 응답을 그대로 돌려준다.

## 환경변수

`.env.example`을 `.env`로 복사해서 쓴다.

| 이름 | 설명 |
|---|---|
| `UPSTAGE_API_URL` | (필수) Upstage 엔드포인트 전체 주소 |
| `UPSTAGE_API_KEY` | 있으면 `Authorization: Bearer` 헤더를 붙인다 |
| `UPSTAGE_MODEL` | 있으면 `model` 필드를 붙인다 (상용 API는 필수) |

## 실행과 테스트

Python 3.12.

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --env-file .env
python -m pytest
```

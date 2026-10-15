# GenOS Upstage Document Parser

GenOS 코드서빙에 올려 Upstage Document Parser를 부르는 앱이다.

| 엔드포인트 | 설명 |
|---|---|
| `POST /v1/document-parse` | 받은 요청을 Upstage로 그대로 넘기고, 응답도 그대로 돌려준다 |
| `POST /preprocess` | GenOS 전처리기. 파일을 Upstage로 파싱하고 청크로 나눠 돌려준다 |
| `GET /health` | 상태 확인 |

## 환경변수

`.env.example`을 `.env`로 복사해서 쓴다.

| 이름 | 설명 |
|---|---|
| `UPSTAGE_API_URL` | (필수) Upstage 엔드포인트 전체 주소 |
| `UPSTAGE_API_KEY` | 있으면 `Authorization: Bearer` 헤더를 붙인다 |
| `UPSTAGE_MODEL` | 있으면 `model` 필드를 붙인다 (상용 API는 필수) |

## 전처리기로 등록

코드서빙 리비전의 컨테이너 서비스 페이지에서 "전처리기로 사용"을 켜고 아래 값을 넣는다.

| 항목 | 값 |
|---|---|
| 전처리기 호출 경로 | `/preprocess` |
| 지원 확장자 | `pdf,docx,ppt,pptx,xlsx,csv,hwp,hwpx,jpg,jpeg,png` |
| 기본 파라미터 | `{"chunk_size":1000,"chunk_overlap":100}` |

`/preprocess`는 GenOS가 보내는 `{file_path, file_content_base64, params}` 본문을 받는다. 성공하면 `{"code":0,"data":[청크...]}`를 돌려주고, 실패하면 HTTP 200에 `{"code":1,"errMsg":"..."}`를 돌려준다.

청크는 `chunk_size`자(문자 수)까지 문서 요소를 이어 붙여 만들고, 앞 청크의 끝 `chunk_overlap`자를 다음 청크 앞에 겹쳐 붙인다.

## 실행과 테스트

Python 3.12.

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn main:app --env-file .env
python -m pytest
```

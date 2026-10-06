#!/bin/sh
# 실행 중인 프록시에 input/test1.pdf를 보내고 결과를 출력한다.
curl -sS -X POST "${PROXY_URL:-localhost:8000}/v1/document-parse" \
  -F "document=@input/test1.pdf" \
  -F "output_formats=['markdown']" |
  python3 -c "import json, sys; d = json.load(sys.stdin); print(d['content']['markdown']); print(d['usage'])"

# 실행 경계

`execute_or_stop.py`는 새 review branch에서 한 번만 실행한다.

1. 준비 파일 checksum과 회귀 테스트를 확인한다.
2. Network download 없이 local-only compatible tokenizer를 찾는다.
3. Historical v0.2A 두 request의 provider prompt count 4,903/14,387을 local tokenizer가 정확히 재현하는지 확인한다.
4. 실패하면 model invocation 없이 preflight result만 commit/push한다.
5. 성공하면 S-long-control을 정확히 14,387 local prompt tokens로 만들고 preflight input을 먼저 commit/push한다.
6. 이후 두 fixed arm을 각 1회 실행하고 raw review evidence를 별도 commit/push한다.

어느 경로에서도 main merge, deploy, promotion 또는 dependency 설치를 수행하지 않는다.

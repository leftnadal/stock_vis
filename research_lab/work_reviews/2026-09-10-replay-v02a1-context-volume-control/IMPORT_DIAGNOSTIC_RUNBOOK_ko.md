# Replay v0.2A.1 ImportError No-Network Diagnostic

이 작업은 CEO가 별도로 승인한 read-only diagnostic이다. 기존 `official-pinned-001`
격리 환경과 tokenizer snapshot을 변경하지 않고, historical request/count gate 대신
최소 chat-template 호출로 기존 `ImportError`의 traceback과 누락 module identity만
확인한다.

고정 경계:

- network 0
- package installation 0
- historical count gate rerun 0
- provider/model invocation 0
- 기존 evidence 및 tokenizer asset 수정 0
- 진단 결과는 `diagnostics/import-error-001/`에 append-only 기록

실행:

```bash
python3 execute_diagnostic_and_publish.py
```

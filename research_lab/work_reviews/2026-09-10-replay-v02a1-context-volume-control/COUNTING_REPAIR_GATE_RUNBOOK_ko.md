# Replay v0.2A.1 counting-only exact gate

이 continuation은 기존 `len(BatchEncoding) == 2` 증거를 보존하고 실제
`input_ids` sequence length를 사용해 historical short/original reference gate를 정확히
한 번만 재평가한다.

동일한 historical request, corrected environment, tokenizer snapshot/revision 및 chat-template
호출 조건을 사용한다. 입력 정규화, tokenizer/template 변경, arm 생성과 provider/model 호출은
수행하지 않는다.

결과는 로컬 commit까지만 만들며 자동 push하지 않는다.

```bash
python3 execute_counting_repair_gate.py
```

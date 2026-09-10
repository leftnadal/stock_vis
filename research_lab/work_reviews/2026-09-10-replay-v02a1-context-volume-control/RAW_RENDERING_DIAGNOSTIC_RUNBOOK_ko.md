# Replay v0.2A.1 raw rendering/token-accounting 진단

이 runner는 기존 corrected environment와 tokenizer snapshot만 사용해 한 번의
no-network/no-model 진단을 수행한다. 두 historical request의 원문과 구조를 변경하지 않는다.

관측 항목은 `tokenize=False` 렌더링의 형식·길이·해시·본문 포함 여부와,
`tokenize=True` 반환 구조의 최상위 길이 및 실제 `input_ids` 길이다.

결과는 기존 Jinja correction 아래 별도 diagnostic lineage에 추가되며 기존 gate evidence를
수정하지 않는다. 실행은 결과를 로컬 commit까지만 만들고 GitHub push는 하지 않는다.

```bash
python3 execute_rendering_diagnostic.py
```

어떤 outcome에서도 model-visible arm 생성, provider/model 호출, 입력 정규화,
tokenizer/template 교체 또는 count fitting을 수행하지 않는다.

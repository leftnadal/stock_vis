# LLM Messages Persistence Policy

> **신설**: Slice 11 Step 0 §2 (#52). Slice 10 Fallback A 트리거(#52 부채) 해결.
> **목적**: 모든 LLM 호출의 `messages + system + model + token + cost`를 슬라이스별로
> 영속화하여 estimator/router/cost 모델 fitting 데이터를 자동 누적.

## 1. 저장 위치

```
docs/portfolio/coach/slice<N>/llm_messages.jsonl
```

- 슬라이스별 격리 (cross-slice 오염 방지).
- JSONL (한 줄 = 한 호출 record).
- gitignore 미적용 — **read-only 자산**으로 영구 보관.

## 2. Record schema

```jsonc
{
  "hash": "sha256(messages+system+model)",  // 64-hex, 멱등성 key
  "slice": 11,
  "messages": [{"role": "user", "content": "<redacted text>"}, ...],
  "system": "<redacted system prompt>",      // null 가능
  "model": "claude-haiku-4-5",
  "input_tokens": 1234,
  "output_tokens": 567,
  "cost_usd": 0.00123,
  "timestamp": "2026-05-18T10:30:00+00:00",
  "extra": {                                 // 호출 컨텍스트 (선택)
    "scenario_id": "S01",
    "preset_id": "V1_garp",
    "entry_point": "e3_portfolio"
  }
}
```

## 3. 멱등성

- **dedupe key**: `SHA256({messages, system, model})` (정렬된 JSON).
- 동일 hash가 이미 파일에 존재 → no-op (False 반환).
- 재실행, retry, idempotent batch 모두 안전.
- 충돌 발생 시(같은 messages인데 의도가 다른 경우) `extra.run_id` 등을 추가하여
  hash 변형(향후 fallback §2 룰).

## 4. Toggle

환경 변수 `STOCKVIS_LLM_MESSAGE_DUMP=0` → hook no-op.

- 테스트 환경 기본값: `0` (테스트가 messages 영속을 trigger하지 않도록).
- production / live LLM 호출 환경: `1` (또는 unset, 기본 ON).
- CI에서 secret 누출 위험 시 OFF.

## 5. Redact (민감정보 마스킹)

`portfolio.measure.message_dumper.redact()`가 자동 적용:

| 패턴                     | 마스킹                                     |
| ------------------------ | ------------------------------------------ |
| `API_KEY=...`            | `API_KEY=<REDACTED>`                       |
| `password=...`           | `password=<REDACTED>`                      |
| `secret=...`             | `secret=<REDACTED>`                        |
| `token=...`              | `token=<REDACTED>`                         |
| `sk-ant-[a-zA-Z0-9_-]{20,}` | `<REDACTED>` (Anthropic API key prefix) |

- ⚠️ **위 룰은 휴리스틱**. 사용자 prompt 자체에 PII가 포함되면 별도 정책 필요.
- 향후 슬라이스에서 `extra.redacted_fields` 필드를 도입하여 사후 검증 가능.

## 6. all_llm_calls.jsonl과의 관계

| 자산                                   | 역할                                                          |
| -------------------------------------- | ------------------------------------------------------------- |
| `all_llm_calls.jsonl` (Slice 10 §1)    | Slice 1~9 raw entry 통합 dump (metadata only — messages 부재) |
| `slice<N>/llm_messages.jsonl` (Slice 11+) | 신규 호출별 messages 영속 (#52 close)                       |

Slice 12+ Step 0에서 두 자산을 함께 로드하여 multivariate estimator fitting 데이터로
사용 예정.

## 7. 통합 dump 시 사용법

향후 슬라이스(예: Slice 12+ Step 9 `output estimator v4`)에서 사용:

```python
from pathlib import Path
import json

slice_files = sorted(Path("docs/portfolio/coach").glob("slice*/llm_messages.jsonl"))
records = []
for f in slice_files:
    for line in f.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))

# records → estimator/router fitting input
```

## 8. 호출 통합 (Slice 11 Part 1+ 작업)

`portfolio/llm/client.py`의 `_call_anthropic_*` 메서드 내부에서 응답 직후
`dump_llm_call(...)` 호출 통합. 통합 작업은 Step 0 scope 외 — Part 1/3 진입 시 적용.

```python
from portfolio.measure.message_dumper import dump_llm_call

# _call_anthropic 직후
dump_llm_call(
    messages=messages,
    system=system,
    model=resolved_model,
    input_tokens=response.usage.input_tokens,
    output_tokens=response.usage.output_tokens,
    cost_usd=compute_cost(response, resolved_model),
    slice_n=CURRENT_SLICE,
    extra={"entry_point": entry_point, "scenario_id": scenario_id},
)
```

## 9. 신규 호출 시 책임

- LLM 호출자: `slice_n` 정확히 지정 (현재 슬라이스 번호).
- `entry_point` 등 컨텍스트는 `extra`로 전달 → fitting 시 활용.
- 환경 toggle은 test fixture 외 변경 금지.

## 10. 부채 정리

- **#52 close 조건**: 본 정책 + `message_dumper.py` + 테스트 6건 + Part 1+에서
  `client.py` 통합 완료.
- 본 Step 0은 정책 + 인프라 + 단위 테스트만 완료 → **Part 1+에서 본격 발동**.

## 참조

- `portfolio/measure/message_dumper.py` — hook 구현.
- `tests/coach/test_messages_persistence.py` — 단위 테스트 6건.
- `docs/portfolio/coach/COST_POLICY.md` — 비용 관리 (related).

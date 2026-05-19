# Slice 12 Step 0a 종결 — #58 parse_json_response trailing characters tolerance

**작업명**: parsers.py Tier 3 raw_decode tolerance 도입
**브랜치**: `slice12`
**작업일**: 2026-05-20
**비용**: $0 (LLM 호출 없음)

---

## §1. 구현 요약

### Tier 구조 (Slice 1 호환 + Slice 12 신규)

| Tier | 동작                                                      | 도입 시점         |
| ---- | --------------------------------------------------------- | ----------------- |
| 1    | `strip_markdown_fences` 후 `model_validate_json`          | Slice 1 기존      |
| 2    | (Tier 1 안에 흡수 — fences 제거)                          | Slice 1 기존      |
| **3** | `raw_decode`로 첫 valid JSON 추출 후 `model_validate`     | **Slice 12 #58** |

### 핵심 로직
```python
try:
    return model_cls.model_validate_json(cleaned)   # Tier 1
except ValidationError as exc:
    if not _is_trailing_characters_error(exc):
        raise
    obj, _end = json.JSONDecoder().raw_decode(cleaned)   # Tier 3
    return model_cls.model_validate(obj)
```

### Trailing characters 식별 (`_is_trailing_characters_error`)
Pydantic ValidationError의 `errors()[i]['type']` == `json_invalid` + msg/ctx에 "trailing" 또는 "extra data" 키워드 매칭. 그 외 schema mismatch는 그대로 raise.

---

## §2. 검증

### Slice 11 E3/haiku/#1 재현 PASS
- 원본 schema_fitting_pass=False (response 1829 chars, valid JSON + `---` + 마크다운)
- Slice 12 #58 보강 후: **PASS** — 5 필드 모두 추출 (summary/key_observations/confidence/action_items/risk_flags)
- action_items 3건 정상 파싱

### 단위 테스트 6/6 PASS
| #   | 테스트                              | 검증 내용                          |
| --- | ----------------------------------- | ---------------------------------- |
| 1   | trailing_markdown_separator         | `{}\n---\n## 추가 코멘트` 패턴     |
| 2   | trailing_korean_text                | `{}\n\n한국어 텍스트` 패턴         |
| 3   | trailing_second_json_object         | `{...}\n{...}` 첫 객체만 추출      |
| 4   | clean_json_unchanged                | 깨끗한 JSON Tier 1 (backward-compat) |
| 5   | code_fence_unchanged                | ```json...``` 펜스 (backward-compat) |
| 6   | invalid_json_raises                 | JSON 전혀 없으면 raise (silent X)  |

---

## §3. Backward-compat

- 기존 13건 호출자 (`e1_garp.py`, `e2_diagnostic_card.py`, `e3_metric_comment.py`, `e3_portfolio_service.py`, `e5_adjustment_parser.py`, `e6_comparison.py`, `coach/e{1~6}_service.py`) 모두 시그니처 무변경
- Tier 1/2에서 통과하던 케이스는 Tier 3 진입 안 함 → 회귀 영향 0
- 신규 PASS 케이스: 기존 ValidationError (json_invalid: trailing) 던지던 경우만

---

## §4. 부채 처리

### #58 → close
- 구현 + 단위 테스트 + 재현 PASS 모두 완료
- Slice 11 Part 4 매트릭스 4.17% FAIL 패턴 완전 해소

### #41 → close (dependency 해소)
- Slice 11 Part 4/5에서 keep_open 1 part (V16 e3/haiku/#1 trailing)
- #58 close로 schema fitting 100% 회복 → **자연 close**

---

## §5. KPI

| #   | KPI                              | 측정값 | 기대값 | PASS/FAIL |
| --- | -------------------------------- | ------ | ------ | --------- |
| 0a-1 | parsers.py Tier 3 보강           | O      | O      | PASS      |
| 0a-2 | 단위 테스트 +6                   | 6      | 6      | PASS      |
| 0a-3 | Slice 11 케이스 재현 PASS        | PASS   | PASS   | PASS      |
| 0a-4 | backward-compat (13건 호출자 무변경) | 회귀 영향 0 | 영향 0 | PASS  |
| 0a-5 | #58 close                        | close  | close  | PASS      |
| 0a-6 | #41 자연 close                   | close  | close  | PASS      |

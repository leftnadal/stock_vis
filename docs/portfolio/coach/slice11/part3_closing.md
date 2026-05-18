# Slice 11 Part 3 종결 보고 — Prompt Builder + E1 service + Smoke (#48 v3 정착)

> A2 통합 진입점 첫 LLM 실측. #48 v3 (count_tokens API) **delta 0.0%** 확인 → **정착 확정**.

## 요약

| 항목                | 값                                            |
| ------------------- | --------------------------------------------- |
| 회귀                | 550 → **559** (+9, ±30% 범위 PASS)            |
| IDENTICAL hash      | 7/7                                           |
| 단독 비용           | **$0.0290** (haiku $0.00684 + sonnet $0.02213) |
| 누적 비용           | **$2.4065** (Slice 1~10 $2.3775 + Part 3 $0.0290) |
| Slice 11 비용 (현재) | $0.0290 / cap $1.00 (마진 **97.1%**)          |
| 신 임계 $4.00 마진  | **39.8%**                                     |
| LLM 호출            | 2 / 50                                        |
| KPI 12/12           | 12 PASS, 0 FAIL                               |
| #48 v3              | **정착 확정** (max_delta 0.0%, N=2)           |
| #41                 | close 유지 (E1Output validate PASS)           |
| Fallback 발동       | 없음                                          |

## §1 baseline 확인

- 브랜치: `slice11`
- Part 2 commit: `975958f`
- baseline 회귀: 550
- Part 1/2 schema 검증: 6 / 6
- ANTHROPIC_API_KEY: 설정됨 (108 chars)

## §2 인벤토리 (Step 1)

- E1 service 파일: `portfolio/services/e1_garp.py` (74 라인, OneLineDiagnosis 사용)
- 기존 prompt builder: `portfolio/prompts/e1/e1_builder.py` (48 라인)
- token estimator: `portfolio/measure/estimator_v3.py:estimate_input_tokens` (Slice 10 #48)
- 마이그레이션 결정: **신규 coach service 추가** (`portfolio/services/coach/`)
  - 기존 `run_e1_garp` production endpoint 무변경 (frontend 보호)
  - 신규 `run_e1_coach`가 Part 1 `E1Input` + Part 2 `E1Output` 사용

자세히: `docs/portfolio/coach/slice11/part3_inventory.md`.

## §3 prompt_builder 모듈 (Step 2)

`portfolio/services/coach/prompt_builder.py` 신규:

- `PromptBuilderBase` (stateless classmethod, `build_system_prompt` + `build_messages` 공통)
- `E1PromptBuilder` **풀 구현** (Part 1 E1Input → user prompt, E1Output JSON schema injection)
- `E2~E6PromptBuilder` **스켈레톤** (`build_user_prompt` 호출 시 `NotImplementedError("Part 4...")`)
- `PROMPT_BUILDER_CLASSES` dict 6 entry — Part 1/2 registry 미러 (sanity check assert 포함)

## §4 E1 service 마이그레이션 (Step 3)

**경로**: `portfolio/services/coach/e1_service.py` (신규)

- `run_e1_coach(input_data, provider="haiku", client=None, max_tokens=2000) -> dict`
- 내부: `E1PromptBuilder.build_messages(input_data)` → `LLMClient.complete(prompt=user, system=system, ...)`
- 응답: `parse_json_response(E1Output, response)` (ValidationError = #41 재오픈 트리거)
- 반환: `{"output": E1Output dict, "llm_metadata": ...}`
- **기존 e1_garp.py 무변경** → 호출자 영향 0건

## §5 builder 단위 테스트 (Step 4)

`tests/coach/test_prompt_builder.py` **8/8 PASS**:

1. `test_base_build_user_prompt_raises_not_implemented`
2. `test_e1_system_prompt_includes_output_schema_json`
3. `test_e1_user_prompt_includes_portfolio_data`
4. `test_e1_build_messages_returns_two_messages`
5. `test_prompt_builder_classes_registry_matches_part1_and_part2`
6. `test_e2_to_e6_skeletons_raise_not_implemented`
7. `test_e1_user_prompt_deterministic`
8. `test_e1_classvar_schema_alignment`

## §6 Smoke + #48 v3 (Step 5)

`scripts/slice11_part3_smoke.py` 실행 결과:

| # | 모델              | predicted | counted | actual | output | delta_pred | delta_count | latency_ms | cost      | fitting |
| - | ----------------- | --------- | ------- | ------ | ------ | ---------- | ----------- | ---------- | --------- | ------- |
| 1 | claude-haiku-4-5  | 1807      | 1807    | 1807   | 1349   | **0.0%**   | **0.0%**    | 14374      | $0.00684  | PASS    |
| 2 | claude-sonnet-4-5 | 1807      | 1807    | 1807   | 1114   | **0.0%**   | **0.0%**    | 23066      | $0.02213  | PASS    |

- **schema fitting**: 양 모델 `E1Output.model_validate_json()` **PASS**
- **#48 v3 max_delta**: **0.0%** (count_tokens API 명세 ≤2% 보장이 실측에서 정확 일치 확인)
- **smoke 비용**: $0.0290 (cap $1.00 마진 97.1%, 신 임계 $4.00 마진 39.8%)

전체 dump (LLM 응답 raw 텍스트 포함): `docs/portfolio/coach/slice11/part3_smoke_dump.md`.

## §7 회귀 (Step 6)

- 550 → **559** (+9, ±30% [4.2, 13] 안)
- KPI 7 PASS
- IDENTICAL 7/7 PASS
- 기존 e1_garp 회귀 — `run_e1_garp` 무변경으로 모든 테스트 PASS

분배:
- `tests/coach/test_prompt_builder.py`: 8건
- `portfolio/tests/slice11/test_regression_classifier.py`: +1건

## §8 classifier (Step 7)

`portfolio/tests/slice11/test_regression_classifier.py`에 신규 룰 +1:
- `test_prompt_builder_and_coach_service_are_mixed` — `portfolio/services/coach/` + `tests/coach/` → mixed

`portfolio/services/`는 기존 cost 카테고리에 이미 포함 → coach 하위 자동 cost 분류. classifier 코드 변경 없음.

## §9 비용

- 단독 (Part 3): **$0.0290**
- 누적 (Slice 1~10 + Part 3): **$2.4065**
- slice cap: $0.0290 / $1.00 (마진 **97.1%**)
- 신 임계 $4.00 마진: **39.8%** (Slice 11 D-3 상향 효과)

## §10 KPI matrix (12건)

`docs/portfolio/coach/slice11/kpi_part3.md` 별도 문서. **12/12 PASS**.

## §11 부채 처리

### #48 v3 — **정착 확정**

| KPI 항목 | 결과 |
| -------- | ---- |
| max_delta_counted (count_tokens API 정확성) | **0.0%** (haiku + sonnet) |
| N | 2 (강 신호) |
| 판정 | **v3 정책 정착 확정** — Slice 12+ 자연 활용 |

count_tokens API의 ±2% 명세 보장이 실측 N=2에서 **0% delta**로 더 보수적 정확도 확인.
Slice 10 Fallback A 사유(raw messages 부재)는 본 슬라이스 Part 3에서 자연 해소.

### #41 — close 유지

E1Output validate **양 모델 PASS** → Part 2의 close 결정 그대로 유지.

### 신규 부채 후보 (모니터링)

- **#54**: builder 모듈 helper 분리 (PS 1.0) — 모듈 700+ lines 도달 시 (현재 209 라인, 안전).
- **#55**: E2~E6 builder 마이그레이션 — **부채 아님**, Part 4 정규 작업 항목.

## §12 산출물 dump

| 영역    | 파일                                                    | 신규/수정       |
| ------- | ------------------------------------------------------- | --------------- |
| builder | `portfolio/services/coach/prompt_builder.py`            | **신규** (Base + E1 풀 + E2~E6 스켈레톤 + dict) |
| service | `portfolio/services/coach/e1_service.py`                | **신규** (`run_e1_coach`) |
| service | `portfolio/services/coach/__init__.py`                  | **신규** (빈)   |
| 테스트  | `tests/coach/test_prompt_builder.py`                    | **신규** (8건)  |
| 스크립트 | `scripts/slice11_part3_smoke.py`                       | **신규** (smoke + #48 v3 측정) |
| 분류    | `portfolio/tests/slice11/test_regression_classifier.py` | 수정 (+1건)     |
| 문서    | `docs/portfolio/coach/slice11/part3_inventory.md`       | **신규**        |
| 문서    | `docs/portfolio/coach/slice11/part3_smoke_dump.md`      | **신규** (LLM raw + delta) |
| 문서    | `docs/portfolio/coach/slice11/kpi_part3.md`             | **신규**        |
| 문서    | `docs/portfolio/coach/slice11/part3_closing.md` (본 문서) | **신규**     |

## §13 커밋 예정

`[slice11] Part 3 종결: prompt builder + coach E1 service + smoke (#48 v3 정착, delta 0.0%)`

## §14 Part 4 진입 준비

| 자산                                              | 상태               |
| ------------------------------------------------- | ------------------ |
| Part 1 input schema (6 sub class)                 | READY              |
| Part 2 output schema (6 sub class)                | READY              |
| Part 3 PromptBuilderBase + E1PromptBuilder        | **PRODUCTION READY** |
| E2~E6 builder 스켈레톤                            | Part 4 마이그레이션 대상 |
| `run_e1_coach` service                            | **PRODUCTION READY** |
| portfolio_a2 fixture (6 진입점)                   | READY              |
| #48 v3                                            | **정착 확정**      |
| #41                                               | close              |
| Slice cap 잔여                                    | $0.9710 (97.1%)    |
| 회귀 baseline                                     | **559**            |

**Part 4 scope (예정)**:
- E2~E6 service 마이그레이션 (5 신규 coach service)
- 풀 matrix: haiku/sonnet × 6 진입점 = **12 케이스** smoke
- manual eval 준비 + 5/5 가설 (글쓰기 정착) 재확인

## 회신 매트릭스

```
Slice 11 Part 3 종결 (prompt builder + E1 coach + smoke, #48 v3 정착).
- 회귀: 550 → 559 (+9)
- IDENTICAL: 7/7
- 비용 단독: $0.0290 / 누적: $2.4065 (마진 39.8%, cap 97.1%)
- LLM 호출: 2/50
- KPI 12/12: 12 PASS, 0 FAIL
- prompt_builder: PromptBuilderBase + E1 풀 + E2~E6 스켈레톤
- coach E1 service: run_e1_coach 신규 (기존 e1_garp 무변경)
- smoke N=2: haiku + sonnet 양 모델 schema fitting PASS
- #48 v3: max_delta 0.0% (정착 확정, N=2 강 신호)
- #41: close 유지
- Fallback 발동: 없음

Slice 11 Part 4 진입 준비 상태: 완료
다음 작업: E2~E6 service 마이그레이션 + 12 케이스 풀 matrix
```

## Manual 검증 필요 항목

- 없음. 12/12 PASS, IDENTICAL 7/7, #48 v3 정착 확정.
- LLM 응답 raw 텍스트는 `part3_smoke_dump.md`에 보존 (Slice 11 #52 정책).

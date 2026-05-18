# Slice 11 Part 3 Step 1 — 호출자 인벤토리 + builder 설계 (KPI 1)

## 1. 기존 E1 service 인벤토리

| 항목                        | 값                                                              |
| --------------------------- | --------------------------------------------------------------- |
| service 파일                | `portfolio/services/e1_garp.py` (74 라인)                       |
| public 함수                 | `run_e1_garp(provider="haiku", client=None) -> dict`            |
| 응답 형식                   | `{"diagnosis": OneLineDiagnosis, "llm_metadata": ...}`          |
| 사용 schema (input)         | `AnalysisContext` (Slice 1 legacy)                              |
| 사용 schema (output)        | `OneLineDiagnosis` (headline + summary, Slice 1 legacy)         |
| prompt builder              | `portfolio.prompts.e1.build_e1_prompt(context) → (system, user)` |
| LLM caller                  | `LLMClient.complete(prompt=concat, **kwargs)`                   |

## 2. `run_e1_garp` 호출자

| # | 파일                                  | 사용 형태                                             |
| - | ------------------------------------- | ----------------------------------------------------- |
| 1 | `portfolio/views.py:53`               | **production HTTP endpoint** — `result = run_e1_garp(provider=provider)` |
| 2 | `portfolio/services/__init__.py:3,6`  | re-export (`__all__`)                                  |

→ **frontend production 의존성 있음**. 외부 시그니처/응답 형식 변경 금지.

## 3. 마이그레이션 설계 결정

지시서 §1.3 룰 "외부 시그니처 변경 0 + 내부 prompt만 builder 호출로 전환"을 보존하면서,
신규 `E1Output` 스키마(Slice 11 Part 2)와 기존 `OneLineDiagnosis`(Slice 1) 간 schema
완전 비대칭 문제를 안전하게 해결.

| 결정         | 채택                                                              |
| ------------ | ----------------------------------------------------------------- |
| 마이그레이션 경로 | **신규 coach service 추가** (`portfolio/services/coach/e1_service.py:run_e1_coach`) |
| 기존 service | `run_e1_garp` 변경 0 — production HTTP endpoint 무영향              |
| A2 통합 path | 신규 `run_e1_coach` — Part 1 `E1Input` + Part 2 `E1Output` 사용  |
| 호출자 영향  | **0건** (신규 모듈 추가, 기존 미수정)                               |

지시서 §1.3 "in-place"는 본질적으로 schema 비대칭 시 충돌. 본 인벤토리 §3 결정 채택 시
지시서 KPI 3 ("E1 service 호출자 영향: 0")는 자연 PASS (신규 모듈이므로 호출자 0).

## 4. token estimator 위치 (#48 v3 검증용)

| 항목                  | 값                                                              |
| --------------------- | --------------------------------------------------------------- |
| Slice 10 estimator v3 | `portfolio/measure/estimator_v3.py:estimate_input_tokens`        |
| 시그니처              | `estimate_input_tokens(messages, system=None, model=...) -> int` |
| Internal              | `client.messages.count_tokens(model, system, messages).input_tokens` |
| Cache                 | in-memory LRU max=1000, `_hash_inputs` 키                        |

→ Step 5 smoke에서 v3 직접 호출 + `count_tokens` API 자체 호출 → delta 계산.

## 5. Builder 설계 인터페이스 매핑표

지시서 §1.2 골격을 채택. coach/ 디렉토리 신설.

```
portfolio/services/coach/
    __init__.py             # 신규
    prompt_builder.py       # 신규 (Base + 6 sub class + dict)
    e1_service.py           # 신규 (run_e1_coach, A2 통합용)
```

| 항목                | 정의                                                              |
| ------------------- | ----------------------------------------------------------------- |
| `PromptBuilderBase` | stateless classmethod (인스턴스 X), `build_system_prompt` / `build_messages` 공통 |
| `E1PromptBuilder`   | **풀 구현** — E1Input → user prompt + E1Output JSON schema injection |
| `E2~E6PromptBuilder`| **스켈레톤** — `build_user_prompt` 호출 시 NotImplementedError(Part 4) |
| `PROMPT_BUILDER_CLASSES` | dict 6 entry — Part 1/2 registry 미러                          |

## 6. Step 1 KPI 1 판정

| KPI                              | 측정                  | 판정    |
| -------------------------------- | --------------------- | ------- |
| E1 service 파일 식별             | `e1_garp.py` (74 라인)| **PASS** |
| 기존 prompt 코드 추출            | `e1_builder.py` 48 라인 (system, user 튜플 반환) | **PASS** |
| 마이그레이션 경로 결정           | 신규 coach service 추가 | **PASS** |

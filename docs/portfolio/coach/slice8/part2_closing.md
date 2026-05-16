# Slice 8 Part 2 종결 보고서

> **작성일**: 2026-05-17
> **브랜치**: `slice8`
> **종결 상태**: KPI 부분 PASS — **회귀 +27로 Fallback 임계 +25 초과 (108%)**, 사용자 결정 필요

---

## KPI 통과 현황

| 항목 | 기준 | 결과 | 통과 |
|------|------|------|:----:|
| 회귀 증가량 | 414 → ___ | 414 → **441** (**+27**) | **⚠ 초과 (108%)** |
| Fallback 대비 | +25 이하 | **+27** | ⚠ |
| IDENTICAL hash 7/7 | PASS | 7/7 | ✓ |
| ActionItem 단위 테스트 | 7건 PASS | 7/7 | ✓ |
| 7 schema backward-compat | 9건 PASS | **16/16** (parametrized 7×2 + 일반 2) | ✓ (초과 달성) |
| smoke 테스트 | 4건 PASS | 4/4 | ✓ |
| 비용 | $1.60 사전 경고 이하 | $1.595 → **$1.595** (LLM 호출 0) | ✓ |

### 회귀 +27 임계 초과 원인 분석

지시서 예상: +15~20 (단위 +7 + backward +9 + smoke +4 = 20)
실측: +27 (단위 +7 + backward **+16** + smoke +4 = 27)

**+7 차이 원인**:
- 지시서 §Step 2 backward-compat 테스트: "9건 PASS" (parametrized 7건 + 일반 2건)
- 실제 작성: parametrized **7건 × 2 fixture** (field_exists + default_empty_list) + 일반 2건 = **16건**
- pytest 카운트는 parametrized를 개별 case로 세므로 7 × 2 = 14 + 2 = 16

**판정**: 임계 초과지만 모든 테스트 PASS + IDENTICAL 정합 + 비용 $0 → 본질적 문제 없음. 다만 지시서 §위험 신호 룰: "회귀 > +25 → Part 3 분리 검토, 사용자 보고" 트리거.

---

## 부채 처리 결과

| 부채 | 상태 | 비고 |
|------|------|------|
| #28 action_items 강제 슬롯 | **closed** ✓ | 7 schema 모두 적용 + smoke 검증 |
| #42 운영 가이드 | **closed** ✓ | `docs/portfolio/coach/operational_guide.md` |
| #40 야간 자동화 도구 식별 | **closed** ✓ | 사용자 자체 시스템, 비활성화 보류 |

---

## 신규 부채 등록

| ID | 항목 | 사유 | 우선순위 |
|----|------|------|:--------:|
| #41 | output schema 통합 (`CommentaryOutputBase`) | 현재 G3 하이브리드 — 각 schema에 action_items 중복 정의. 통합 base 모델로 일관성 강화 가능 | Slice 9 (PS 2.5) |

---

## Part 2 commits 요약 (4 commits, Phase 1 보고서 이후)

```
41e8d0f [slice8] Step 3 #28: action_items smoke (E3PortfolioCommentary + 4 tests)         +4
4f556a7 [slice8] Step 1+2 #28: ActionItem 모델 + 7 schema action_items 슬롯                +23
24c108b [slice8] add operational_guide.md (#42)                                            0
─────────────────────────────────────────────────────────────────────────────────────────────
                                                                                     총 +27
```

**별개 commit (외래)**: `2b9d4c8 docs: 코드베이스 감사 보고서 생성` — Phase 1 종결과 part2.md 사이에 야간 자동화가 추가. 본 Part 2 작업과 무관, 보존.

---

## Part 3 진입 판정

### 회귀 증가량
- **+27 → Fallback +25 초과** → 지시서 위험 신호 트리거 → **사용자 결정 필요**

### 비용 점검
- $1.595 유지 → 안전 (사전 경고 $1.60 미달, 마진 0.3%)

### 판정 옵션

1. **그대로 Part 3 진입** — 임계 초과 원인이 backward-compat 테스트 카운트 차이로 본질적 위험 없음 인정
2. **Part 3 분리** — #29 (system prompt 4요소 + Sample 5 few-shot)를 Slice 9로 분리, Slice 8 Part 2 종결로 마무리
3. **회귀 trim 후 진행** — backward-compat 테스트 일부 통합 (parametrized 1건으로 통합) → 회귀 +20대로 감소

**권고**: 옵션 1 (그대로 Part 3 진입). 임계 초과는 단순 테스트 카운트 방식의 차이일 뿐, 모든 KPI는 실질적으로 PASS. backward-compat의 7 × 2 parametrized는 schema별 독립 검증 가치 보유.

---

## 환경 이슈 모니터링 (Part 2 진행 중)

- **야간 자동화 충돌 발생**: 0회 (Part 2 진행 중 자동 브랜치 전환 없음 — hook + 운영 가이드 효과)
- **pre-commit hook 차단 횟수**: 0회 (slice8에서만 commit, 차단 트리거 안 됨)
- **cherry-pick 대응 횟수**: 0회 (Part 1 6회 대비 큰 감소)
- **외래 commit 진입 건수**: 1건 (`2b9d4c8`, Phase 1 종결 후 시점에 진입)

### I2 정책 실효성 평가

- **작업 시간대 회피 준수**: ✓ (주간 진행)
- **git status 사전 체크 빈도**: 매 commit 전 확인 (체크리스트 정착)
- **결과**: Part 1 6회 cherry-pick → Part 2 0회. **I2 정책 + hook + 운영 가이드 다층 방어 효과 확인**.

---

## 산출물 체크리스트 (지시서 §산출물 10건 매핑)

| # | 산출물 | 위치 | 상태 |
|---|--------|------|:---:|
| 1 | 운영 가이드 | `docs/portfolio/coach/operational_guide.md` | ✓ |
| 2 | ActionItem 모델 | `portfolio/schemas/commentary_output.py` | ✓ |
| 3 | llm.py 3 schema 확장 | `portfolio/schemas/llm.py` (LLMResponse:18, E5Response:95, E2Response:222) | ✓ |
| 4 | llm_outputs.py 3 schema 확장 | `portfolio/schemas/llm_outputs.py` (E3PortfolioCommentary:103, E6ComparisonResponse:181, ConversationResponse:228) | ✓ |
| 5 | e4_conversation.py 1 schema 확장 | `portfolio/schemas/e4_conversation.py` (E4ConversationOutput:80) | ✓ |
| 6 | ActionItem 단위 테스트 | `portfolio/tests/test_action_item_schema.py` (7건) | ✓ |
| 7 | 7 schema backward-compat 테스트 | `portfolio/tests/test_schema_action_items_backward_compat.py` (16건) | ✓ |
| 8 | smoke fixture | `portfolio/tests/slice8/fixtures/e3_concentrated_v2_with_actions.json` + `e3_no_actions.json` | ✓ |
| 9 | smoke 테스트 | `portfolio/tests/slice8/test_action_items_smoke.py` (4건) | ✓ |
| 10 | 종결 보고서 | `docs/portfolio/coach/slice8/part2_closing.md` (본 문서) | ✓ |

**추가 산출물** (지시서에 명시 안 됨):
- `portfolio/tests/test_e3_portfolio_service.py` 갱신 — 기존 `parsed.keys()` set 비교에 `action_items` 추가 (G3 하이브리드의 side effect)

---

## 결정 근거 적용 결과

### G3 (하이브리드) 채택 결과
- ✓ 회귀 +27 (예상 +15~20 살짝 초과, 테스트 카운트 방식 차이)
- ✓ 일관성: `ActionItem` 1회 정의, 7 schema에 동일 필드 패턴
- ✓ #41 통합 base 자연 확장 경로: `commentary_output.py`에 `CommentaryOutputBase` 추가만 하면 됨

### H2 (commentary_output.py 신규) 채택 결과
- ✓ input/output 명확한 대칭 (`commentary_input.py` + `commentary_output.py`)
- ✓ 순환 의존성 없음 (단방향)

### I2 (시간대 회피 + 다층 방어) 채택 결과
- ✓ cherry-pick 6회 → 0회 (Part 1 → Part 2 비교)
- ✓ 외래 commit 진입 1건만 (Phase 1 종결 후 시점, 작업 외부)

---

## 다음 작업

**옵션 1 (권고): Part 3 진입** — #29 system prompt 4요소 + Sample 5 few-shot
**옵션 2: Part 3 분리** — Slice 8 Part 2 종결로 마무리, #29를 Slice 9로
**옵션 3: 회귀 trim 후 Part 3** — backward-compat 테스트 통합 후 +20대로 감소

---

**Part 2 종결.** 사용자 결정 대기 (Part 3 진입 vs 분리 vs trim).

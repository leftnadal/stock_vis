# Slice 13 / Part 5 종결 보고 (★ Slice 13 종합 포함)

**작업 범위**: E4 DRF endpoint 추출 (마지막 진입점, 순수 복제)
**완료 일자**: 2026-05-21
**브랜치**: `slice13` (Part 4 commit `54cc47f` 위)
**비용**: $0 (real LLM 호출 0건, mock 기반)
**슬라이스 유형**: 표준 슬라이스, 단건 (+9~13 기대 → 실제 +10 PASS)

---

## 1. 사전 점검 결과 요약 (정합화 0 확정)

E4는 표준 진입점과 동등한 자산을 이미 보유 — 보강 작업 없음:

| 항목 | 상태 | 비고 |
|------|------|------|
| `run_e4_coach` | ✅ 표준 시그니처 존재 (`portfolio/services/coach/e4_service.py:19`) | preset_id/metrics kwarg는 부재 — E4 특이점 |
| `CommentaryInputE4` | ✅ Slice 11 InputBase 편입 (`commentary_input.py:145`) | user_question + conversation_history |
| `E4Output` | ✅ Slice 11 OutputBase 편입 (`commentary_output.py:114`) | base만 사용 (특화 필드 없음) |
| 기존 legacy view | ❌ **부재** | E4는 마이그레이션 대상 아님 (#65 special case) |
| fixture | ✅ `portfolio_a2.json` inputs.e4 | user_question + conversation_history |
| 기존 회귀 carrier | ✅ 85건 (IDENTICAL 20/31 = E4 conversation schema) | Part 5에서 PASS 보호 확인 |

**인계 메모 정정**: "URL 미등록" → 정확. legacy view 자체가 부재 (E4 유일).

---

## 2. 핵심 설계 원칙 준수 검증

| 원칙 | 결과 |
|------|------|
| ADDITIVE — `run_e4_coach` / `E4PromptBuilder` / E4 스키마 무수정 | ✅ git diff 0 |
| Pydantic 단일 진실 소스 — DRF serializer는 얇은 어댑터 | ✅ |
| ★★ IDENTICAL 31/31 PASS — E4 경로 무수정 (20/31 carrier 보호) | ✅ |
| contract test가 LLM mock 기반 — real 호출 0 | ✅ |
| E1~E3·E5·E6 패턴 순수 복제 — 새 설계 미도입 | ✅ |
| E4 mock 검증이 실제 시그니처 반영 (preset_id/metrics kwarg 미존재) | ✅ (`assert "preset_id" not in call_kwargs`) |

---

## 3. 변경 사항

| 파일 | 변경 |
|------|------|
| `portfolio/api/serializers.py` | E4 Request + Response serializer 2개 추가 (E5/E6 패턴 복제) |
| `portfolio/api/views.py` | `coach_e4` view 추가 (E5 동형, preset_id/metrics 미전달) |
| `portfolio/api/urls.py` | `coach/e4/` 1줄 추가 → **E1~E6 6개 endpoint 완료** |
| **신규** `portfolio/tests/api/test_e4_endpoint.py` | 10건 contract test (★ kwarg 미존재 검증 포함) |
| `docs/portfolio/coach/debts.md` | **#65 단서 보강** — E4 special case (legacy 부재) + 선행조건 충족 명시 |
| `docs/portfolio/coach/kpi_matrix.md` | §5 베이스라인 767로 갱신, Slice 13 누적 +99 종합 |

### 무수정 보증
- `portfolio/views.py` (legacy): git diff **0 lines** ✅ (★ E4 legacy view 신규 추가 없음 확인)
- `portfolio/urls.py` (legacy): git diff **0 lines** ✅
- `run_e4_coach` / `E4PromptBuilder` / `CommentaryInputE4` / `E4Output`: 무수정 ✅
- E1/E2/E3/E5/E6 view + serializer: 무수정 ✅

---

## 4. 종결 체크리스트

- [x] 회귀 전체 PASS — **767 passed, 1 skipped** (757 +10, 표준 슬라이스 +9~13 중앙값 PASS)
- [x] ★ IDENTICAL 31/31 PASS (E4 경로 무수정 — 20/31 carrier 보호)
- [x] `portfolio/views.py` / `urls.py` 무변경 (E4 legacy view 신규 추가 없음)
- [x] POST `/api/v1/coach/e4/` — 정상 200 / 검증 실패 400 / 예외 500 / budget 429 / LLM 502
- [x] contract test가 E4Output 계약 위반 시 FAIL (drift 안전망 1건)
- [x] E4 mock 검증이 실제 시그니처 반영 (preset_id/metrics kwarg 미존재)
- [x] part5_closing.md 신규 (★ E1~E6 완료 현황 + #65 안내 포함)
- [x] kpi_matrix.md §5 갱신, debts.md §1 #65 단서 보강
- [x] 비용: real LLM 호출 0 → $0

---

## 5. 회귀 카운트 추이

| 단계 | 카운트 | Δ |
|------|--------|---|
| Part 4 종결 | 757 passed | — (baseline) |
| 작업 3 신규 테스트 (E4 contract) | 767 | **+10** |
| **Part 5 종결** | **767 passed + 1 skipped** | **+10** |

> 표준 슬라이스 임계 +9~13, ±30% 임계 [+6, +17]. **임계 중앙값 PASS** — E1·E2·E3와 동일 +10 답습.

---

## 6. contract test 커버리지 (10건)

| 카테고리 | 건수 | 항목 |
|---------|------|------|
| 정상 경로 (200) | 2 | 응답 구조 + E4Output 역검증 + **kwarg 미존재 검증** (★ E4 특이) |
| 검증 실패 (400) | 4 | 필수 필드 누락 (user_question) / 잘못된 타입 / non-dict body / invalid provider |
| Service 예외 | 3 | 500 (스택트레이스 미노출) / 429 (budget) / 502 (LLMRateLimitError) |
| Schema drift 안전망 | 1 | service confidence 위반 시 serializer 차단 |
| **합계** | **10** | (E5/E6 동일 + kwarg 미존재 검증 변형) |

---

# 🏁 Slice 13 종합 — E1~E6 6개 endpoint 완료 현황

## A. 진행 현황

| Part | Commit | 작업 | 회귀 Δ | 비용 |
|------|--------|------|--------|------|
| Step 0a | `f7fd62b` | 3단 게이트 ADDITIVE + estimator multivariate fit | +27 (component buildup) | $0 |
| Step 0b | `22d1e99` | estimator → CostGuard non-blocking integration | +12 (mini) | $0 |
| Part 1 | `44d5e90` | E1 endpoint (DRF serializer + contract test) | +10 (표준) | $0 |
| Part 1.5 | `28d19c4` | API 경로에 v1 버전 세그먼트 도입 | 0 (불변) | $0 |
| Part 2 | `50c6313` | E2 endpoint (E1 패턴 복제) | +10 (표준) | $0 |
| Part 3 | `ae0a9e1` | E3 endpoint (코멘트만, preset 점수는 #66) | +10 (표준) | $0 |
| Part 4 | `54cc47f` | E5 + E6 endpoint 묶음 | +20 (표준×2) | $0 |
| **Part 5** | (이번) | **E4 endpoint (마지막 진입점)** | **+10 (표준)** | $0 |
| **합계** | 8 commits | **E1~E6 완료** | **+99** (668 → 767) | **$0** |

## B. 신규 endpoint 매트릭스 (E1~E6)

| 진입점 | URL | Legacy view | 마이그레이션 처리 |
|--------|-----|-------------|------------------|
| E1 | `/api/v1/coach/e1/` | `coach_e1_garp` | ✅ Part 1 (legacy 유지) |
| E2 | `/api/v1/coach/e2/` | `coach_e2_diagnostic_card` | ✅ Part 2 (legacy 유지) |
| E3 | `/api/v1/coach/e3/` | `coach_e3_metric_comment` | ✅ Part 3 (legacy 유지 / preset 점수는 #66) |
| **E4** | `/api/v1/coach/e4/` | **부재** | ✅ Part 5 (★ legacy 마이그 대상 아님) |
| E5 | `/api/v1/coach/e5/` | `coach_e5_adjustment` | ✅ Part 4 (legacy 유지) |
| E6 | `/api/v1/coach/e6/` | `coach_e6_comparison` | ✅ Part 4 (legacy 유지) |

## C. 신규 부채 변동 (Slice 13)

- **#61** (PS 2.5, Slice 14): 3단 게이트 경계값 calibration
- **#62** (Step 0b → close): estimator → CostGuard non-blocking integration
- **#63** (PS 1.5, Slice 14+): 누적 비용 ledger 영속화
- **#64** (PS 1.0, Slice 14+): 사전 추정 blocking 차단 모드
- **#65** (PS 1.5, Slice 13 종결 후): **기존 순수 view 5건 최종 처리** ← 선행조건 충족, 진입 가능
- **#66** (PS 2.0, 분석엔진 #12 Phase 2): E3 preset 점수 API 노출

## D. ADDITIVE 원칙 누적 검증

- `portfolio/views.py` / `portfolio/urls.py` (legacy): Slice 13 전체 git diff **0 lines** 유지 ✅
- 6개 service 함수 (`run_e1~e6_coach`): 무수정 (E3는 Step 0a에서 gate-tier kwarg 추가 ADDITIVE만) ✅
- 6개 Pydantic 스키마 (`CommentaryInputE*` / `E*Output`): 무수정 (Step 0a에서 gate_tiers 필드 ADDITIVE만) ✅
- IDENTICAL 31/31: Slice 13 전체에서 모든 Part 종결 시 PASS 유지 ✅

---

## 7. #65 진입 안내

**선행조건 충족**:
- E1~E6 6개 endpoint 전체 DRF 마이그레이션 완료 ✅
- contract test 커버리지: 6 × 10 = **60건** (Slice 13 신규 추가)
- legacy view git diff 0 — 안전망 확보

**#65 작업 범위 (Slice 13 종결 후 또는 Slice 14+)**:
1. 기존 순수 view **5건** (E4 제외) 처리 결정: 유지 / 제거 / wrapper화
2. 클라이언트 호출 경로 분석 (frontend, 자동화 스크립트)
3. wrapper화 선택 시: 순수 view → DRF endpoint 호출로 위임 (이중 라우팅 제거)

**E4는 special case**: legacy view 자체가 없으므로 마이그레이션 대상에서 제외.

---

**Slice 13 Part 5 종결 = Slice 13 종결**. Slice 13 closing 사이클 준비 또는 #65 진입 결정 대기.

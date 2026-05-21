# Slice 13 / Part 3 종결 보고

**작업 범위**: E3 DRF endpoint 추출 (코멘트 노출, preset 점수 기능은 #66로 분리)
**완료 일자**: 2026-05-21
**브랜치**: `slice13` (Part 2 commit `50c6313` 위)
**비용**: $0 (real LLM 호출 0건, mock 기반)
**슬라이스 유형**: 표준 슬라이스 (+9~13 기대 → 실제 +10 PASS)
**지시서 버전**: part3_v2.md (v1 분기 B 결정 후 옵션 A 답습으로 재설계)

---

## 1. 작업 0 결과 요약 (분기 B → 옵션 A 선정 근거)

### 1-1. v1 지시서 분기 B 결정 사실

| 항목 | 확인 결과 |
|------|----------|
| E3 입력 스키마 | `CommentaryInputE3` (`portfolio/schemas/commentary_input.py:136`) — 핵심 필드 `concentration_metrics: dict[str, Any]` |
| E3 출력 스키마 | `E3Output` (`portfolio/schemas/commentary_output.py:107`) |
| `run_e3_coach` 시그니처 | `(input, provider="haiku", client=None, max_tokens=2000, *, preset_id=None, metrics=None)` |
| 기존 E3 view | `coach_e3_metric_comment` (`portfolio/views.py:248`), `/api/coach/e3/metric-comment/` |
| preset 진실 소스 | `PRESET_ID_TO_CATEGORY` (`portfolio/services/scoring/__init__.py`) — 12개 |
| **holdings → 7종 metrics 계산 함수** | ❌ **부재** (분기 B 결정 근거) |

### 1-2. metrics 두 종류 명확화 (혼동 방지)

| 명칭 | 용도 | 출처 | Part 3 처리 |
|------|------|------|------------|
| `concentration_metrics` (입력 스키마 필드) | 코멘트 생성용 입력 | 클라이언트 전송 | endpoint에 노출 (필수 필드) |
| `metrics` (run_e3_coach kwarg) | ScoringEngine 점수용 정규화 지표 | 분석엔진 #12 필요 (3종 외부 데이터 의존) | **endpoint 미노출 → #66 분리** |

### 1-3. 옵션 A 선정 근거

- v1 §0-3 분기 B → 옵션 후보 B-1/B-2/B-3 보고 → **옵션 A (E1·E2 패턴 순수 복제)** 결정
- 근거: ScoringEngine은 7종 metrics 완비 전제. 분석엔진 #12 부재 상태에서 부분적(4종) 노출은 placeholder만 양산
- preset 점수 기능은 **breaking change 없이** 분석엔진 완성 후 ADDITIVE 추가 가능 (#66)

---

## 2. 핵심 설계 원칙 준수 검증

| 원칙 | 결과 |
|------|------|
| ADDITIVE — `portfolio/views.py` / `portfolio/urls.py` / `run_e3_coach` 무수정 | ✅ git diff 0 |
| Pydantic 단일 진실 소스 — DRF serializer는 얇은 어댑터 | ✅ (E2 패턴 답습) |
| IDENTICAL 31/31 PASS — service/LLM 경로 무수정 | ✅ |
| contract test가 LLM mock 기반 — real 호출 0 | ✅ |
| E1·E2 패턴 순수 복제 — 새 설계 미도입 | ✅ |
| preset_id / metrics endpoint 미노출 — run_e3_coach 호출 시 미전달 (#66로 분리) | ✅ (`test_post_e3_returns_200_with_valid_request`에서 mock 호출 인자 검증) |

---

## 3. 변경 사항

| 파일 | 변경 |
|------|------|
| `portfolio/api/serializers.py` | `E3RequestSerializer` + `E3ResponseSerializer` 추가 (E2 동형) |
| `portfolio/api/views.py` | `coach_e3` view 추가 (E2 view와 동형, kwarg 미전달) |
| `portfolio/api/urls.py` | `path("coach/e3/", views.coach_e3)` 1줄 추가 |
| **신규** `portfolio/tests/api/test_e3_endpoint.py` | 10건 contract test (E2 패턴 복제 + kwarg 미전달 검증 추가) |
| `docs/portfolio/coach/debts.md` | **#66 신규 등록** (preset 점수 API 노출, 분석엔진 #12 의존), §5 사전 등록 갱신 |
| `docs/portfolio/coach/kpi_matrix.md` | §5 베이스라인 737로 갱신, Part 3 종결 추적 추가 |

### 무수정 보증
- `portfolio/views.py` (legacy): git diff **0 lines** ✅
- `portfolio/urls.py` (legacy 라우팅): git diff **0 lines** ✅
- `run_e3_coach` service: 무수정 ✅
- `coach_e1` / `coach_e2` view + E1/E2 serializer: 무수정 ✅

---

## 4. 종결 체크리스트

- [x] 회귀 전체 PASS — **737 passed, 1 skipped** (727 +10, 표준 슬라이스 +9~13 임계 중앙값 PASS)
- [x] IDENTICAL 31/31 PASS (service/LLM 경로 무수정)
- [x] 기존 `coach_e3_metric_comment` view 동작 불변 (git diff 0)
- [x] POST `/api/v1/coach/e3/` — 정상 200 / 검증 실패 400 / 예외 500 / budget 429 / LLM 502
- [x] endpoint 요청 표면에 `preset_id` / `metrics` 필드 없음 (#66로 분리)
- [x] contract test가 E3Output 계약 위반 시 FAIL (drift 안전망 1건)
- [x] **#66 debts.md §1 등록** (분석엔진 #12 Phase 2 선행조건 명시)
- [x] part3_closing.md 신규, kpi_matrix.md §5 갱신
- [x] 비용: real LLM 호출 0 → $0

---

## 5. 회귀 카운트 추이

| 단계 | 카운트 | Δ |
|------|--------|---|
| Part 2 종결 | 727 passed | — (baseline) |
| 작업 3 신규 테스트 (E3 contract) | 737 | **+10** |
| **Part 3 종결** | **737 passed + 1 skipped** | **+10** |

> 표준 슬라이스 임계 +9~13, ±30% 임계 [+6, +17]. **임계 중앙값 PASS** — E1·E2와 동일 +10 답습.

---

## 6. contract test 커버리지 (10건)

| 카테고리 | 건수 | 항목 |
|---------|------|------|
| 정상 경로 (200) | 2 | 응답 구조 + E3Output 역검증 + **kwarg 미전달 검증** (★ Part 3 신규) |
| 검증 실패 (400) | 4 | 필수 필드 누락 (concentration_metrics) / 잘못된 타입 / non-dict body / invalid provider |
| Service 예외 | 3 | 500 (스택트레이스 미노출) / 429 (budget) / 502 (LLMRateLimitError) |
| Schema drift 안전망 | 1 | service confidence 위반 시 serializer 차단 |
| **합계** | **10** | (E2 동일 + kwarg 비노출 보증 추가) |

---

## 7. ADDITIVE 원칙 위반 신호 점검

- 기존 31 IDENTICAL 테스트 PASS ✅
- 기존 `portfolio/views.py` / `portfolio/urls.py` git diff 0 ✅
- `run_e3_coach` service signature 무수정 ✅
- E1·E2 endpoint 동작 영향 없음 (회귀 carrier 20건 PASS 유지) ✅

---

## 8. E3 endpoint 동작 요약

```
POST /api/v1/coach/e3/?provider=haiku

Request body (JSON):
  {
    "portfolio_id": "...",
    "fetched_at": "2026-05-21T00:00:00Z",
    "preset": "garp",
    "holdings": [{ "ticker": "AAPL", "weight": 0.5 }, ...],
    "concentration_metrics": {
      "hhi": 0.21, "top3_weight": 0.65,
      "sector_top_weight": 0.35, "single_name_max": 0.25
    }
  }

Response (200):
  {
    "output": E3Output(summary, key_observations, confidence,
                        action_items, risk_flags),
    "llm_metadata": { provider, model, latency_ms, ... }
  }

Errors: 400 / 429 / 500 / 502 (E1·E2 동일 표면)

★ preset_id / metrics 필드는 본 endpoint에서 받지 않는다 (#66 분리).
```

---

## 9. 신규 부채 #66 등록 사실

- **제목**: E3 endpoint preset 점수 기능 API 노출 (preset_id + metrics optional 필드)
- **선행조건**: 분석엔진 #12 (Phase 2) — `sector_hhi`, `portfolio_beta`, `avg_correlation` 3종 외부 데이터 의존
- **breaking change**: 없음 (ADDITIVE optional 필드)
- **PS**: 2.0 (Phase 2 블록)
- **현재 위치**: debts.md §1 OPEN 부채 + §5 Slice 14+ 사전 등록

---

## 10. Part 4 진입 준비

- **다음 작업**: E4 endpoint 확장 → `/api/v1/coach/e4/` (대화 Q&A)
- **E4 특이점**: `CommentaryInputE4`는 `user_question` + `conversation_history` 필드 보유 (대화 컨텍스트)
- **예상 회귀 +Δ**: +9~13 (표준 슬라이스 동일)
- **예상 비용**: $0
- **남은 endpoint**: E4 → E5 → E6 (3건). 완료 시 #65 (기존 view 최종 처리) 진입.

---

**Slice 13 Part 3 종결**. Part 4 (E4) 진입 대기.

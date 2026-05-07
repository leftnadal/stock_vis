# Slice 4 Refactor Backlog

> 작성일: 2026-05-07
> 슬라이스: 4 (E6 조정 후 비교 해설) Part 2 종결 시점
> 누적 처리율: Slice 1·2·3 9건 + Slice 4 신규 6건 = 15건 추적

---

## §1 Slice 4 처리 결과 (Slice 3 8건 + Slice 4 신규 6건)

### 완료 (2건)

| # | 항목 | PS | 처리 슬라이스 | 처리 내역 |
|---|------|-----|-------------|----------|
| 2 | score 산식 통합 (e1+e2+e6) | 3.0 | **Slice 4 Step 9** | `_main_unified()` + `_normalize_results` + `_build_lex_filter` + `_build_output_dict`. e5는 delegation 유지. Slice 1·3 IDENTICAL 보존. 단위 테스트 +10. |
| 9 | latency 임계 16,000ms 상향 | 2.0 | **Slice 4 Step 6** | **e6 한정 적용** — `run_step6_e6_smoke.py` 신규에만 적용. 기존 5 파일은 변경 없음 (회귀 위험 0). 9,180ms 실측 → 임계 57% 사용. |

### Slice 5 이연 (6건)

| # | 항목 | PS | 트리거 | 이연 사유 |
|---|------|-----|-------|----------|
| 5 | TOKEN_BUDGET LLMClient 통합 (잔여) | 2.0 | Slice 3 부분 처리 | LLMClient에 `entrypoint` 인자 추가 필요 (백로그 #8과 결합) |
| 6 | Step 8 raw output CSV 옵션 | 1.0 | Slice 1 deferred | CSV 파싱 도구가 있어야 가치 발생 — Slice 5+ 분석 도구 함께 |
| 7 | Mock LLMClient mode dict 매핑 | 1.0 | Slice 1 deferred | mocks.py가 5개 mode를 if-elif로 처리 — dict로 정리 |
| 8 | LLMClient entrypoint 인자 + 가드레일 | 2.5 | Slice 3 Step 9 미완 | LLMClient.complete에 `entrypoint` 추가 + token_budgets 자동 적용 |
| 10 | E2 keyword_match 룰 보완 | 1.5 | Slice 3 Step 8 발견 | E2 자동 평가 룰 정교화 — 본 슬라이스 #15와 결합 검토 |
| 11 | metrics_table 일반화 | 1.5 | Slice 3 deferred | E3 진입점 진입 시 적용 |

---

## §2 Slice 4 신규 백로그 (6건)

| # | 항목 | PS | 트리거 | 처리 시점 |
|---|------|-----|-------|----------|
| 12 | **E6 분석 엔진 재계산 (Phase 2)** | 5.0 | D-7 스켈레톤 `original + adjusted + overrides` 패턴이 비-스코프로 보류. 분석 엔진이 조정 후 AnalysisContext를 산출할 수 있어야 정량 비교 가능 | **Phase 2** (별도 슬라이스, 분석 엔진 확장 슬라이스와 결합) |
| 13 | `run_step6_*.py` 5종 latency 일괄 16,000ms 상향 | 1.0 | Slice 4 #9 e6 한정 적용 후 일관성 — 다른 진입점도 한도 도달 가능 (E2 7,471ms 발생 사례) | Slice 5+ (마지막 진입점 검증 후 일괄 정리) |
| 14 | `score_step8.py` CLI 인자 확장 (`--input`/`--output`) | 1.5 | Slice 4 사전 데이터에서 발견 — 지시서 가정과 실제 차이. 기존 round-trip 검증은 default 경로 + git diff로 우회 | Slice 5+ (진입점 추가 시 round-trip 검증 편의) |
| 15 | E6 자동 평가 룰 정교화 | 1.5 | Step 8 자동 평가 룰이 simple — sonnet 통찰 차별화 미반영 가능성. Slice 3 sonnet insight +0.57 패턴 재현 안 됨 | Slice 5+ (#10과 결합 — 자동 평가 룰 일반화) |
| 16 | E6 latency 24s 초과 sonnet 패턴 분석 | 1.0 | Step 8 sonnet 4건이 22~24s — 24,561ms 최대 도달. 임계 16,000ms 추가 상향 검토 | Slice 5+ (latency 임계 일괄 정리 시) |
| 17 | `auto_eval_e6.py` 패턴 일반화 | 2.0 | Slice 4 신규 자동 평가 스크립트 — E2 keyword_match와 통합 가능 (#10 + #15) | Slice 5+ |

---

## §3 Slice 5 진입점 후보 (사전 등록)

| 후보 | 근거 | 의존성 | 구현 복잡도 | 권장도 |
|------|------|--------|-------------|--------|
| **E3 (지표 코멘트 — preset 외삽 검증)** | Slice 3 insight 그룹차 0.67~0.83 위험 — Buffett/Defensive preset fixture 추가 검증. 글쓰기 가설 5번째 외삽 | 단독 (낮음) | 낮음 | ⭐⭐⭐ |
| **E4 (대화 Q&A Tier 1~3)** | Coach 핵심 가치 / Phase 2 product 시연. Tier별 다른 패턴 가능 | Tier 다층 (높음) | 높음 | ⭐⭐⭐⭐ |

### 3.1 E3 채택 시 Slice 5 시나리오

- 진입점: E3 (지표 코멘트, D-4)
- Default provider: **haiku** (글쓰기 가설 4/4 → 5번째 외삽)
- Fixture 전략: 신규 hybrid (preset 다양성 — GARP 3 + Buffett 2 + Defensive 2)
- 평가 차원: naturalness + insight + 새 차원 `metric_alignment` (지표 코멘트 정합성)
- Step 9 슬롯: 백로그 #10 (E2 keyword_match 룰) + #15 (E6 자동 평가 룰) 통합 일반화

### 3.2 E4 채택 시 Slice 5 시나리오

- 진입점: E4 (대화 Q&A, D-5)
- Default provider: **mixed** (Tier 1 추출 sonnet, Tier 2~3 글쓰기 haiku)
- Fixture 전략: Tier별 분리 (3 Tier × 3 fixture = 9 fixture)
- 평가 차원: naturalness + insight + intent_routing (Tier 1→Tier 2 전이 정확도)
- Step 9 슬롯: 백로그 #5 + #8 (LLMClient entrypoint + budget 통합)

---

## §4 Slice 5 결정 사항 (Slice 4 종결 시 사전 등록)

(Slice 4 Part 2 종결 후 사용자 결정 대기)

권장 결정 매트릭스:

| Q | 결정 옵션 | 권장 |
|---|----------|------|
| Q1 진입점 | E3 (단독, 외삽 강화) vs E4 (Phase 2 product 시연) | **E3** (의존성 낮음, 빠른 완수) |
| Q2 default provider | haiku (글쓰기 가설 5번째 검증) | haiku |
| Q3 fixture 전략 | preset 다양성 (GARP+Buffett+Defensive) | hybrid 7 (Slice 3·4 패턴) |
| Q4 평가 차원 | naturalness + insight + metric_alignment | 신규 차원 추가 |
| Q5 reset | CostGuard.reset_slice("slice5") | 자동 |
| Q6 score 산식 | DIMENSION_LOOKUP[e3] 추가 (Slice 4 _main_unified 1줄 추가) | 1 라인 |
| Q7 Step 9 슬롯 | 백로그 #10 + #15 + #17 (자동 평가 룰 일반화) | 묶음 처리 |

---

## §5 누적 처리율 (Slice 1·2·3·4 합산)

| 카테고리 | 항목 수 | 비고 |
|---------|--------|------|
| 누적 신규 등록 | 17건 | Slice 1: 2건 / Slice 2: 4건 / Slice 3: 6건 / Slice 4: 6건 + 1 deprecated |
| 완료 | 5건 | #1 (Slice 1 Step 9), #3·#4 (Slice 3 흡수), #2·#9 (Slice 4 처리) |
| 부분 완료 | 1건 | #5 (Slice 3 token_budgets 도입, LLMClient 통합 잔여) |
| Slice 5 이연 | 6건 | #5 잔여, #6, #7, #8, #10, #11 |
| Slice 5+ 신규 이연 | 5건 | #13, #14, #15, #16, #17 |
| Phase 2 위임 | 1건 | #12 (E6 분석 엔진 재계산) |

**처리율**: 5 + 1×0.5 = **5.5 / 17 = 32%** (Slice 4 Step 9 단일 슬롯에서 +PS 3.0 처리, Slice 3 50% 슬롯 활용보다 효율 ↑).

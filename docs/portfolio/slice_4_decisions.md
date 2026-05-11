# Slice 4 결정 사항 보존

> 작성일: 2026-05-07
> 상태: 본문 미작성 (다음 세션에서 작성)
> 용도: 다음 세션 진입 시 결정 복원

## 다음 세션 진입 가정

| 항목           | 가정                                |
| -------------- | ----------------------------------- |
| Slice 3 실행   | **완료 가정** (Q1.A)                |
| Slice 4 진입점 | **TBD** (Q2.C — 다음 세션에서 결정) |

## 다음 세션 시작 트리거

다음 세션 시작 시 다음 입력을 첨부:

1. **Slice 3 실행 결과 매개변수** (Slice 2 Part 2 패턴 mirror)
   - winner / use_fallback
   - tradeoff frequency
   - 누적 호출 / 비용
   - score_step8 일반화 진척 (DIMENSION_LOOKUP[e2] 추가 결과)
   - CostGuard reset 동작 확인
   - **fixture 그룹 비교 결과** (Q4 hybrid 정당성 검증 — Slice 3 신규 항목)
   - 회귀 카운트 최종값

2. **클로드코드 Slice 4 작성용 참고자료** (코드 인터페이스, Slice 1/2/3 패턴 차이 표)

3. **본 보존 문서**

## Slice 4 진입점 후보 (다음 세션에서 결정)

메모리 명시 슬라이스 순서 기준:

- **E3** (지표 코멘트) — 메모리 순서. 글쓰기 작업. Slice 1/3 mirror
- **E4+E6** (Q&A + 비교 해설) — 가장 복잡. E4는 Tier 1~3 전체 통합

진입점 결정 자료:

- Slice 3 실행 결과 (글쓰기 winner, 그룹 비교 패턴)
- 53개 지표 × 12 프리셋 매트릭스 범위 결정 (E3 채택 시)
- 분석 엔진 의존성 (E6 채택 시 — 조정 후 AnalysisContext 계산 로직)

## 누적 결정 사항 (Slice 1~3 보존)

다음 세션에서 Slice 4 작성 시 참고할 누적 결정:

| 영역             | 결정                                                     |
| ---------------- | -------------------------------------------------------- |
| docs 경로        | `docs/portfolio/coach/sliceN/` 분리                      |
| Default provider | 작업 종류별 (글쓰기=haiku, 추출=sonnet)                  |
| 비용 가드        | CostGuard 모듈, Slice 단위 reset (Slice 3에서 코드 구현) |
| 평가 차원        | manual 2개 + completeness 자동 (글쓰기 진입점)           |
| score 일반화     | DIMENSION_LOOKUP 직접 추가 (delegation 가능)             |
| LLM-as-judge     | Phase 2 (Slice 5+)                                       |
| Mock             | text_strategy 패턴 (e1/e5/e2 등록)                       |
| D4 가이드        | 모든 run 스크립트에 \_json_default + round-trip 의무     |

## Slice 3 미실행 시 분기

다음 세션 시작 시 Slice 3 실행이 미완료라면:

- Slice 4 작성 보류
- Slice 3 실행 우선 → 결과 받은 후 Slice 4 진입

# 부록 A — Slice 4 종결 결정 표 (Part 2 종결 갱신, 2026-05-07)

| 항목                       | 값 (Part 1 시점)                                     | 값 (Part 2 종결)                                                               |
| -------------------------- | ---------------------------------------------------- | ------------------------------------------------------------------------------ |
| 진입점                     | E6 (조정 후 비교 해설)                               | (동일 — 변경 없음)                                                             |
| Default provider           | haiku                                                | **haiku 검증 ✓** (Slice 4 winner=haiku, label_means 21.76 vs 7.73, 64.5% 우세) |
| Fixture 전략               | hybrid 7 (e5_baseline 3 + e6_focused 4)              | (동일)                                                                         |
| 평가 차원                  | naturalness / insight (manual) + completeness (자동) | (동일)                                                                         |
| Step 8 매트릭스            | 7 × 2 = 14 (haiku 7 + sonnet 7)                      | **14 calls 정상 종결, 재시도 0**                                               |
| Step 9 슬롯 작업           | #2 score 산식 통합 (e1/e2/e6 \_main_unified)         | **완료** — Slice 1/Slice 3 IDENTICAL hash 일치, e5 delegation 유지             |
| Step 8 winner              | (Part 2 종결 시 기재)                                | **haiku** (efficiency 21.7590 vs 7.7294, 차이 64.5%)                           |
| Lex pass rate              | (Part 2 종결 시 기재)                                | **haiku 7/7 (100%) / sonnet 7/7 (100%)** — 둘 다 ≥50%                          |
| 글쓰기 가설 외삽 검증      | (Part 2 종결 시 기재)                                | **4/4 정착 ✓** — S1·S3·S4 글쓰기 모두 haiku, S2 추출 반례 일관                 |
| Token budget e6 등록값     | 1차 추정 1,000                                       | **e6=1500** (P90 845 × 1.5 → round-up 500) — 사전 추정 +50% 편차               |
| 누적 호출 (Slice 4)        | (Part 2 종결 시 기재)                                | **15 / 50** (마진 35)                                                          |
| 누적 비용 (Slice 4)        | (Part 2 종결 시 기재)                                | **$0.1576** ($0.20 임계 78.8%)                                                 |
| 누적 비용 (Slice 1~4 광의) | —                                                    | **$0.585~$0.648** (정합 미회복, Slice 5 Step 0 부채 #γ1)                       |
| 케이스 A~F 발동            | —                                                    | **모두 미발동** (6종 0건)                                                      |
| Slice 1 IDENTICAL hash     | —                                                    | **True** ✓ (`917fa3ef…0f7b9`)                                                  |
| Slice 3 IDENTICAL hash     | —                                                    | **True** ✓ (`5594c6ab…f3ba`)                                                   |
| Slice 5 진입 결정          | Slice 4 종결 회고 시                                 | **E3 (preset 외삽 검증)** — 가중합 4.70/5.00, 부록 F.1                         |

# 부록 B — Slice 4 백로그 처리 통합 표 (갱신)

## B.1 Slice 3 9건의 Slice 4 처리 결과

| #   | 항목                               | PS  | Slice 3 등록 | Slice 4 처리 결과                                                             |
| --- | ---------------------------------- | --- | ------------ | ----------------------------------------------------------------------------- |
| 2   | score 산식 통합 (e1/e2/e6)         | 3.0 | 신규         | **Slice 4 Step 9 완료** ✓                                                     |
| 5   | TOKEN_BUDGET LLMClient 통합 (잔여) | 2.0 | 부분         | Slice 5 이연                                                                  |
| 6   | Step 8 CSV 옵션                    | 1.0 | 이연         | Slice 5 이연                                                                  |
| 7   | Mock mode dict 매핑                | 1.0 | 이연         | Slice 5 이연                                                                  |
| 8   | LLMClient entrypoint 인자          | 2.5 | 이연         | Slice 5 이연 (Slice 6 슬롯 후보)                                              |
| 9   | latency 임계 16,000ms 상향         | 2.0 | 이연         | **Slice 4 Step 6 완료 (e6 한정)** ✓ + Slice 5 이연 (#13으로 기존 5 파일 일괄) |
| 10  | E2 keyword_match 룰 보완           | 1.5 | 이연         | Slice 5 이연 (E2 한정)                                                        |
| 11  | metrics_table 일반화               | 1.5 | 이연         | Slice 5 이연 — **E3 진입 시 Step 9 슬롯 자연 흡수 후보**                      |

**처리율**: Slice 4 완료 2건 (#2, #9 e6 한정) / Slice 5 이연 6건 (Slice 3 본문에 #10이 누락된 점 검증 필요).

## B.2 Slice 4 신규 백로그 (보고서 기준 6건 — 부록 갱신)

| #   | 항목                                            | PS  | 트리거                                         |
| --- | ----------------------------------------------- | --- | ---------------------------------------------- |
| 12  | E6 분석 엔진 재계산 (Phase 2)                   | 5.0 | D-7 스켈레톤 패턴 회귀, 정량 재계산 추가 시    |
| 13  | run*step6*\*.py 5종 latency 일괄 16,000ms 상향  | 1.0 | Slice 4 e6 한정 적용 후 일관성                 |
| 14  | score_step8.py CLI 인자 확장 (--input/--output) | 1.5 | Slice 5+ round-trip 편의                       |
| 15  | E6 자동 평가 룰 정교화                          | 1.5 | sonnet 통찰 차별화 미반영, Slice 5+ #10과 결합 |
| 16  | E6 latency 24s 초과 sonnet 패턴 분석            | 1.0 | 임계 추가 상향 검토                            |
| 17  | auto_eval_e6.py 패턴 일반화                     | 2.0 | E2 keyword_match (#10)와 통합                  |

## B.3 신규 백로그 (검증 단계에서 추가)

| #   | 항목                                              | PS  | 출처                                               |
| --- | ------------------------------------------------- | --- | -------------------------------------------------- |
| 18  | score_step8_e5.py argparse --entrypoint 인자 추가 | 1.0 | 이슈 δ — Slice 4 Step 9 검증 시 발견 (회귀 영향 0) |

# 부록 C — 회귀 카운트 진행 표 (Part 2 종결 갱신)

| 단계                    | 추가 테스트 (단독) | 누적 (단독) | 누적 (origin rebase 포함) | 비고                                     |
| ----------------------- | ------------------ | ----------- | ------------------------- | ---------------------------------------- |
| Slice 3 종결            | —                  | 123         | —                         | baseline                                 |
| Slice 4 Part 1 종결     | +37                | 160         | —                         | E6 schema 5 + Mock 17 + hybrid 15        |
| Part 2 Step 6           | 0                  | 160         | —                         | 산출물만                                 |
| Part 2 Step 7           | +3                 | 163         | —                         | token_budgets 단위                       |
| Part 2 Step 8           | 0                  | 163         | —                         | 산출물만                                 |
| Part 2 Step 9           | +10                | **173**     | —                         | \_main_unified + dispatch                |
| **Slice 4 종결 (단독)** | —                  | **173**     | **296**                   | origin rebase로 marketpulse v2 +123 합산 |

목표 +8~13 단독 카운트 기준 충족 (+13).

# 부록 G (신규) — Slice 4 종결 잔존 부채 (Slice 5 Step 0 후보)

매 슬라이스 Step 0 = 이전 슬라이스 미해결 부채 정리 패턴 적용.

| #   | 부채                                                                                           | 등급 | Severity × Probability / Fix Cost | PS       |
| --- | ---------------------------------------------------------------------------------------------- | ---- | --------------------------------- | -------- |
| β1  | token budget 한국어 휴리스틱 보정 (chars/3 → chars/2.5 또는 count_tokens API 사전 호출 의무화) | 중요 | 3 × 0.7 / 1.0                     | **2.10** |
| γ1  | 누적 비용 광의/협의 정합 회복 (Slice 1·2 헤더 vs 본문 차이 추적 + 단일 산출 정책 확정)         | 중요 | 2 × 1.0 / 0.5                     | **4.00** |
| δ1  | (백로그 #18로 이관 — score_step8_e5 argparse 인자)                                             | 경미 | 1 × 1.0 / 0.5                     | 2.00     |

**Slice 5 Step 0 처리 우선순위**: #γ1 (4.00) → #β1 (2.10) → #δ1 (백로그로 이관)

- #γ1: 30분 한도 내 — validation_report 1·2·3 §5 비용 섹션 재집계 + 단일 산출 정책 1줄 명시
- #β1: 30분 한도 내 — token_budgets.py 휴리스틱 코드 1곳 수정 + Slice 5 Step 7에서 검증

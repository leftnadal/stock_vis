# Slice 6 Part 3 v2 — 작업 지시서

> **버전**: v2 (Part 2 완료 보고 검증 후 모델 구성 3A 채택)
> **시점**: Slice 6 Part 2 종결 / Part 3 미실행
> **브랜치**: `portfolio`
> **누적 회귀**: 395 / 누적 광의 비용: $0.764
> **대상 진입점**: concentrated_portfolio E3 portfolio-level
> **모델 구성**: haiku + sonnet (10 cases, gemini 제외 정책 유지)

---

## 0. 컨텍스트

Part 2에서 prompt builder 보강 (input 3,862 평균/4,030 max) + mock 흐름 정적 검증 완료. Part 3는 **real LLM 매트릭스 10 cases** 실행 단계. Slice 4·5 패턴 mirror (Step 6 smoke → Step 7 매트릭스 → Step 8 사전 준비).

**모델 구성 (3A 채택)**:

- haiku × 5 (V1~V5) — primary, 글쓰기 가설 5/5 정착 검증
- sonnet × 5 (V1~V5) — fallback 후보, 5번째 진입점 글쓰기 가설 비교
- gemini 제외 (Slice 1 9/9 폴백 + 5슬라이스 일관 제외 정책 유지)

**Part 2 → Part 3 의존 자산**:

- `portfolio/services/e3_portfolio_service.py` — `run_e3_portfolio` (real) 진입 함수 (Part 2 산출)
- `portfolio/prompts/e3_portfolio/builder.py` — reinforced 모드 (input 3,783~4,030)
- `portfolio/tests/fixtures/sample_e3_portfolio_context.py` — V1~V5 fixture
- `BUDGETS["e3_portfolio"] = 7,000` (Part 2 등록)

**진행 순서**: Step 6 → Step 7 → Step 7.5 → Step 8 사전 준비 (Manual eval은 Part 4)

---

## 1. Step 6 — Smoke Test (V1 × haiku × 1 call)

### 1.1 목적

real LLM 1회 호출로 흐름 전체 검증. 매트릭스 실행 전 prompt/parser/CostGuard/fallback 통합 검증.

### 1.2 산출물

1. `scripts/slice6/run_step6_smoke.py` 신규 (또는 기존 step6 패턴 mirror)
2. `docs/portfolio/coach/slice6/step6_smoke_result.json` raw 응답
3. `docs/portfolio/coach/slice6/step6_smoke_result.md` 4판정 표

### 1.3 Smoke 호출 명세

| 항목      | 값                               |
| --------- | -------------------------------- |
| fixture   | V1 (concentrated_balanced, GARP) |
| 모델      | haiku (primary)                  |
| 호출 수   | 1                                |
| budget    | 7,000 (registered)               |
| 예상 비용 | ~$0.005                          |

### 1.4 4판정 (Slice 5 Step 6 mirror)

| 판정                  | 기준                                                              |
| --------------------- | ----------------------------------------------------------------- |
| **schema PASS**       | E3PortfolioCommentary 6 필드 + Literal + min/max length 모두 PASS |
| **completeness PASS** | 6 필드 모두 비공란, 의미 있는 내용 (단순 placeholder 아님)        |
| **cost PASS**         | 단건 비용 ≤ $0.020 임계                                           |
| **token PASS**        | output tokens ≤ 1,000 (buffer 1.5x 적용된 추정 한계 내)           |

### 1.5 Acceptance Criteria

| 항목      | 기준                                       |
| --------- | ------------------------------------------ |
| 4판정     | 4/4 PASS                                   |
| 응답 파싱 | parse_e3_portfolio_response 성공           |
| CostGuard | 호출 1건 카운팅 정확 (50콜 상한 중 1 소진) |
| fallback  | 0건                                        |
| 비용      | ≤ $0.010 (단건)                            |
| 시간      | 5~10분                                     |

**FAIL 시**: 분기 G1 발동 → Step 7 진입 보류, 원인 분석 + 보정 사이클

---

## 2. Step 7 — 본 매트릭스 실행 (10 cases)

### 2.1 목적

V1~V5 × haiku/sonnet 10 cases real LLM 호출 → raw 응답 수집 → KPI 자동 측정.

### 2.2 산출물

1. `scripts/slice6/run_step7_matrix.py` 신규
2. `docs/portfolio/coach/slice6/step7_matrix_raw.json` 10건 raw 응답
3. `docs/portfolio/coach/slice6/step7_matrix_metrics.json` KPI 측정값
4. `docs/portfolio/coach/slice6/step7_matrix_report.md` 매트릭스 결과 요약

### 2.3 매트릭스 구성 (10 cases)

| Case | fixture                  | 모델   | 카테고리          |
| ---- | ------------------------ | ------ | ----------------- |
| 1    | V1 concentrated_balanced | haiku  | growth aligned    |
| 2    | V1 concentrated_balanced | sonnet | growth aligned    |
| 3    | V2 concentrated_misfit   | haiku  | growth misaligned |
| 4    | V2 concentrated_misfit   | sonnet | growth misaligned |
| 5    | V3 concentrated_large    | haiku  | factor            |
| 6    | V3 concentrated_large    | sonnet | factor            |
| 7    | V4 concentrated_value    | haiku  | value             |
| 8    | V4 concentrated_value    | sonnet | value             |
| 9    | V5 concentrated_dividend | haiku  | income            |
| 10   | V5 concentrated_dividend | sonnet | income            |

### 2.4 KPI 자동 측정 (Slice 5 패턴 mirror)

**모델별 label_means** (글쓰기 가설 검증 핵심):

- haiku 5건 평균 (naturalness, insight, completeness, lex_coverage)
- sonnet 5건 평균
- haiku/sonnet 격차 → 글쓰기 가설 5/5 vs 4/5 판정 입력 자료

**preset 외삽 robustness** (Slice 5에서 검증된 패턴):

- haiku V1~V5 그룹차: insight 차이 ≤ 0.50 안전, > 0.50 시 preset 일반화 우선순위 상승 신호
- sonnet 동일 측정

**완전성 (completeness)**:

- 10건 모두 6 필드 cover (no missing field)
- preset_alignment Literal 5종 정합 (V1=aligned, V2=misaligned, V3=partial, V4=aligned, V5=aligned)
  - **주의**: Part 2 mock에서 V1=partial로 평가됨 → real LLM 응답이 mock과 일치할 필요는 없음. fixture 의도(aligned)와 LLM 평가의 차이를 분석에 반영
- confidence 1~5 분포 (편향 검증)

**비용 breakdown**:

- haiku 5건 × 추정 $0.005 = ~$0.025
- sonnet 5건 × 추정 $0.020 = ~$0.100
- 총 ~$0.125 (안전 마진 포함 임계 $0.150)

### 2.5 Acceptance Criteria

| 항목              | 기준                                                |
| ----------------- | --------------------------------------------------- |
| 매트릭스 실행     | 10/10 호출 성공 (fallback 포함)                     |
| schema PASS       | 10/10 E3PortfolioCommentary parse                   |
| completeness PASS | 10/10 6 필드 cover                                  |
| fallback          | 0건 (목표), 발동 시 fallback_from 메타 검증         |
| CostGuard         | 10건 카운팅 정확 (50콜 상한 중 11 누적 소진)        |
| 단건 비용         | haiku ≤ $0.010, sonnet ≤ $0.030                     |
| 총 비용           | ≤ $0.150 (임계, Slice 6 누적 광의 $0.764 → ~$0.914) |
| token usage       | 10건 모두 budget 7,000 이내                         |
| 시간              | 30~60분 (병렬 호출 시 단축 가능)                    |

**FAIL 시**: 케이스별 분기 (G2~G5) 처리 후 재시도 또는 Step 7.5 진입

---

## 3. Step 7.5 — KPI 자동 검증 (Slice 5 Step 6 mirror)

### 3.1 목적

Step 7 raw 응답 → 자동 KPI 측정값 → Part 4 manual eval 진입 가능 여부 판정.

### 3.2 산출물

1. `scripts/slice6/score_step7_5.py` 신규 (Slice 5 score_step8 패턴 mirror)
2. `docs/portfolio/coach/slice6/step7_5_kpi_report.md` KPI 8항목 PASS/FAIL

### 3.3 KPI 8항목 (Slice 5 Step 6 mirror)

| #   | KPI                      | 기준                                 |
| --- | ------------------------ | ------------------------------------ |
| 1   | **Slice 1 e1 IDENTICAL** | hash diff 0                          |
| 2   | **Slice 3 e2 IDENTICAL** | hash diff 0                          |
| 3   | **호출 카운트**          | 11/50 (smoke 1 + matrix 10), 마진 39 |
| 4   | **schema 10/10**         | E3PortfolioCommentary parse          |
| 5   | **completeness 10/10**   | 6 필드 cover + non-empty             |
| 6   | **fallback 0건**         | haiku/sonnet 직접 응답               |
| 7   | **단건 비용 PASS**       | haiku ≤ $0.010, sonnet ≤ $0.030      |
| 8   | **총 비용 PASS**         | ≤ $0.150                             |

### 3.4 KPI 12항목 추가 (보조 측정)

| #   | KPI                            | 기준                                                             |
| --- | ------------------------------ | ---------------------------------------------------------------- |
| 9   | **label_means 격차**           | haiku/sonnet efficiency 격차 측정 (정량적 결과만, 판정은 Part 4) |
| 10  | **preset 외삽 insight 그룹차** | haiku V1~V5 / sonnet V1~V5 각각, > 0.50 시 preset 일반화 신호    |
| 11  | **lex coverage**               | haiku/sonnet 각 5건 어휘 다양성 (Slice 5 패턴)                   |
| 12  | **token usage P90/max**        | budget 7,000 대비 실측 P90 (#β2 재오픈 외삽 후속 데이터)         |

### 3.5 케이스 A~G 사전 검증

Slice 5 정착 패턴 mirror. 발동 시 즉시 분석 + 보정 사이클.

| 케이스 | 발동 조건                                    | 처리                                                     |
| ------ | -------------------------------------------- | -------------------------------------------------------- |
| A      | schema FAIL 1건 이상                         | 해당 case 재시도 (max 2회)                               |
| B      | completeness FAIL 1건 이상                   | 응답 분석 + prompt 보강 검토                             |
| C      | fallback 1건 이상                            | fallback_from 메타 검증 + 원인 분석                      |
| D      | 단건 비용 임계 초과                          | 즉시 정지 + 원인 분석                                    |
| E      | 총 비용 임계 초과                            | 즉시 정지 + CostGuard 동작 검증                          |
| F      | label_means 격차 비정상 (예: sonnet > haiku) | manual eval에서 정밀 분석 (Part 4)                       |
| G      | preset 외삽 insight 그룹차 > 0.50            | preset 일반화 우선순위 상승 → Slice 7 진입점 후보 재평가 |

### 3.6 Acceptance Criteria

| 항목          | 기준                                                 |
| ------------- | ---------------------------------------------------- |
| KPI 1~8       | 8/8 PASS                                             |
| 케이스 A~E    | 0건 발동                                             |
| 케이스 F·G    | 발동 시 Part 4 manual eval에서 분석 (즉시 차단 아님) |
| 보조 KPI 9~12 | 측정값 docs 기록 (판정은 Part 4)                     |
| 시간          | 15~30분                                              |

---

## 4. Step 8 사전 준비 (Manual Eval 대기)

### 4.1 목적

Part 4 manual eval 진입 자료 준비. 자동 단계 종결.

### 4.2 산출물

1. `docs/portfolio/coach/slice6/step8_2way_e3_portfolio_raw.json` (DIMENSION_LOOKUP 등록 경로)
2. `docs/portfolio/coach/slice6/step8_2way_e3_portfolio_scored.json` (자동 점수 dump)
3. `docs/portfolio/coach/slice6/step7_5_summary.md` Part 4 manual eval 입력 자료

### 4.3 manual eval 입력 자료 구성

- haiku 5건 + sonnet 5건 응답 raw
- preset_alignment / confidence 모델별 분포
- label_means 자동 측정값 (naturalness/insight/completeness/lex)
- preset 외삽 그룹차 (haiku V1~V5, sonnet V1~V5)
- Slice 5 e3 결과와 비교 baseline (글쓰기 가설 5/5 vs 4/5 판정 입력)

### 4.4 Manual eval 항목 사전 정의 (Part 4 입력 가이드)

- **winner 판정**: haiku vs sonnet
- **글쓰기 가설 5/5 vs 4/5**: 5번째 진입점 (E3 portfolio-level)에서 haiku 우위 유지 여부
- **5 preset 외삽 robustness**: insight 그룹차 ≤ 0.50 안전 vs > 0.50 신호
- **preset_alignment LLM 평가 분포**: fixture 의도 vs LLM 평가 차이 분석

---

## 5. 분기 시나리오 처리 절차

### G1 — Step 6 smoke FAIL

- 원인: prompt 빌더 또는 parser 또는 service layer 결함
- 처리: 응답 raw 분석 → 결함 위치 식별 → 즉시 수정 → 재시도
- Step 7 진입 보류

### G2 — Step 7 총 비용 임계 ($0.150) 초과

- 원인: token usage 예상보다 많음 (#β2 재오픈 후속 검증 미흡)
- 처리: 즉시 정지 → CostGuard 50콜 상한 동작 검증 → prompt 압축 검토 → token_budgets 재조정
- 신규 부채 등재 검토

### G3 — Fallback 1건 이상 발동

- 원인: 모델 응답 invalid 또는 timeout
- 처리: fallback_from 메타 검증 → 원인별 처리
  - timeout: 재시도
  - invalid response: prompt 보강
  - rate limit: 호출 간격 조정
- fallback ≥ 3건 시 분기 차단 (Slice 1 gemini 패턴 회피)

### G4 — Completeness FAIL (10건 중 1건 이상 6 필드 누락)

- 원인: LLM이 schema 일부 필드 생략
- 처리: 해당 case 재시도 (max 2회) → 재시도도 FAIL 시 prompt schema 명세 보강 검토
- 신규 부채 등재 검토 (PS 1.5~2.0)

### G5 — Token Budget 초과 (7,000 초과 응답)

- 원인: 응답 길이가 추정 초과
- 처리: 잘림 검증 → output 토큰 임계 조정 → budget 재조정 검토
- #β2 재오픈에 추가 데이터 입력

### G6 — Preset 외삽 insight 그룹차 > 0.50

- 원인: 특정 preset에서 LLM이 다른 평가
- 처리: 즉시 차단 아님, Part 4 manual eval에서 정밀 분석
- 후속: Slice 7 진입점 후보 재평가 (preset 일반화 우선순위 상승)

---

## 6. Part 3 종합 KPI

| 항목                 | 목표                                                                             |
| -------------------- | -------------------------------------------------------------------------------- |
| 회귀 누적            | 395 → 400~415 (+5~20, matrix runner 테스트 자연 추가)                            |
| 비용 단독            | ≤ $0.150 (추정 $0.125 + 안전 마진)                                               |
| 누적 광의            | $0.764 → ~$0.89 (임계 $1.00 90% 소진, 회고 안건)                                 |
| 신규 부채            | 0건 예상 (G2·G4·G5 발동 시 부채 등재 검토)                                       |
| 호출 카운트          | 11/50 (smoke 1 + matrix 10), 마진 39                                             |
| 시간                 | 60~120분 (Step 6 10분 + Step 7 30~60분 + Step 7.5 15~30분 + Step 8 사전 15~20분) |
| KPI 8항목            | 8/8 PASS                                                                         |
| 케이스 A~E           | 0건 발동                                                                         |
| Slice 1 e1 IDENTICAL | diff 0                                                                           |
| Slice 3 e2 IDENTICAL | diff 0                                                                           |

---

## 7. 회수 양식 (Step 6/7/7.5/8 실행 후)

```
[Slice 6 Part 3 완료 보고]

== Step 6 (Smoke) ==
A1. 4판정:
  schema:        PASS / FAIL
  completeness:  PASS / FAIL
  cost:          PASS / FAIL ($___)
  token:         PASS / FAIL (output ___tokens)
A2. CostGuard 호출 카운트: 1/50
A3. Fallback: 0 / ___건
A4. 시간: ___분
→ G1 분기 발동 여부: Y / N

== Step 7 (매트릭스) ==
B1. 10 cases 실행 결과:
  V1 × haiku: schema __ completeness __ cost $__ tokens __
  V1 × sonnet: ...
  V2 × haiku: ...
  V2 × sonnet: ...
  V3 × haiku: ...
  V3 × sonnet: ...
  V4 × haiku: ...
  V4 × sonnet: ...
  V5 × haiku: ...
  V5 × sonnet: ...

B2. 총합:
  schema PASS: __/10
  completeness PASS: __/10
  fallback: __건
  단건 비용 max: haiku $__ / sonnet $__
  총 비용: $___
  token usage P90: __, max: __
  호출 카운트: 11/50

B3. preset_alignment LLM 평가 (vs fixture 의도):
  V1 (의도 aligned): haiku=__, sonnet=__
  V2 (의도 misaligned): haiku=__, sonnet=__
  V3 (의도 partial): haiku=__, sonnet=__
  V4 (의도 aligned): haiku=__, sonnet=__
  V5 (의도 aligned): haiku=__, sonnet=__

B4. 케이스 발동: A__ / B__ / C__ / D__ / E__ / F__ / G__ / 없음

== Step 7.5 (KPI 자동) ==
C1. KPI 8항목:
  1. Slice 1 e1 IDENTICAL: PASS / FAIL
  2. Slice 3 e2 IDENTICAL: PASS / FAIL
  3. 호출 카운트 11/50: PASS / FAIL
  4. schema 10/10: PASS / FAIL
  5. completeness 10/10: PASS / FAIL
  6. fallback 0건: PASS / FAIL
  7. 단건 비용 PASS: PASS / FAIL
  8. 총 비용 PASS: PASS / FAIL

C2. 보조 KPI 9~12:
  9. label_means: haiku __, sonnet __, 격차 __%
  10. preset 외삽 insight 그룹차: haiku __, sonnet __ (>0.50 시 G6 신호)
  11. lex coverage: haiku __%, sonnet __%
  12. token usage P90: __, max: __ (vs budget 7000)

== Step 8 사전 준비 ==
D1. raw dump: docs/.../step8_2way_e3_portfolio_raw.json ___건
D2. scored dump: docs/.../step8_2way_e3_portfolio_scored.json
D3. summary docs 작성: PASS / FAIL

== 종합 ==
- 누적 회귀: 395 → ___
- Part 3 단독 비용: $___
- 누적 광의: $0.764 → $___
- 기존 395 영향: ___건
- Part 3 소요 시간: Step 6 __ / Step 7 __ / Step 7.5 __ / Step 8 사전 __ (총 __분)
- 분기 시나리오 발동: G1 / G2 / G3 / G4 / G5 / G6 / 없음
- IDENTICAL hash: Slice 1 e1 ✓/✗ / Slice 3 e2 ✓/✗
- 신규 부채: ___
- Part 4 manual eval 진입 준비: 완료 / 미완료
```

---

## 8. 작업 흐름 (Claude Code용)

1. **Step 6 실행 (smoke)**
   - V1 × haiku × 1 call
   - 4판정 + CostGuard + fallback 검증
   - PASS → Step 7 / FAIL → G1 분기 처리

2. **Step 7 실행 (매트릭스 10 cases)**
   - V1~V5 × haiku/sonnet 순차 또는 병렬
   - CostGuard 호출 카운트 + 비용 누적
   - 각 case raw 응답 dump
   - G2~G5 분기 모니터링

3. **Step 7.5 실행 (KPI 자동)**
   - KPI 8 + 보조 12 측정
   - 케이스 A~G 발동 검증
   - IDENTICAL hash 검증 (Slice 1·3)

4. **Step 8 사전 준비**
   - raw + scored dump (DIMENSION_LOOKUP 등록 경로)
   - summary docs 작성

5. **결과 회수**
   - 위 7번 양식 그대로 채워서 보고
   - 분기 발동 여부 명시
   - Part 4 manual eval 진입 준비 상태 명시

6. **commit 메시지 권장**
   - `feat(slice6/part3/step6): smoke test V1 × haiku (4판정 PASS)`
   - `feat(slice6/part3/step7): matrix 10 cases (V1~V5 × haiku/sonnet)`
   - `feat(slice6/part3/step7_5): KPI 8/8 + 보조 9~12 + case A~G 검증`
   - `feat(slice6/part3/step8): manual eval 입력 자료 준비`

---

## 9. Part 4 진입 전 체크포인트

- [ ] Step 6 smoke 4/4 PASS
- [ ] Step 7 매트릭스 10/10 schema + completeness PASS
- [ ] Step 7.5 KPI 8/8 PASS
- [ ] 케이스 A~E 0건 발동
- [ ] 총 비용 ≤ $0.150
- [ ] IDENTICAL hash KPI 유지 (Slice 1 e1 + Slice 3 e2)
- [ ] raw + scored dump 파일 생성
- [ ] Part 4 manual eval 입력 자료 준비 완료
- [ ] 신규 부채 0건 또는 처리 계획 명시
- [ ] 누적 광의 비용 $0.89 근처 (임계 $1.00 90% 소진)

Part 4 = Step 8 manual eval (winner + 글쓰기 가설 5/5 vs 4/5 + preset 외삽 robustness 판정). Slice 5 Step 8 manual eval과 통합 처리 권장.

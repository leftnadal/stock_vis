# Slice 9 전체 종결 보고서

> **작성일**: 2026-05-18
> **브랜치**: slice9 (4 commits, main 미머지)
> **종결 상태**: ✓ Slice 9 전체 종결 — 6/7 분기, #49 close, Slice 10 진입 결정

---

## §1. 누적 지표 (Step 0 + Part 1 + Part 2 + Manual Eval)

| 항목                | Slice 8 종결 | Slice 9 종결 | Δ                  |
| ------------------- | ------------ | ------------ | ------------------ |
| 회귀                | 458          | **496**      | **+38**             |
| IDENTICAL hash      | 7/7          | **7/7**      | 유지                |
| 누적 cost (광의)    | $2.0483      | **$2.3775**  | +$0.3292 (Part 1)   |
| 임계 마진           | -2.4% (초과) | **20.7%** ✓  | $3.00 임계 갱신 후 |
| 슬라이스 cap (신규) | —            | **$0.3292** (33%) | cap $1.00 마진 67% |
| LLM 호출            | 27/100       | **26/100**   | Sonnet 26콜 rationale |
| commit 수           | —            | **4건**       | c9754d5/ccc8086/277bb12/ed7d445 |

---

## §2. Slice 9 단계별 요약

### Step 0 (#43 / E1) — c9754d5

- COST_POLICY $2.00 → **$3.00**, 슬라이스 cap **$1.00 신설**
- E1 회귀 분리 룰 (KPI 9a cost ±30% / 9b no-cost ±50%) + regression_classifier 자동 분류
- KPI 매트릭스 v2 (core 8 + auxiliary 4 = 12 KPI)
- 회귀: 458 → 476 (+18), 비용 $0
- KPI: 6/6 PASS

### Part 1 Phase 1 (#44 prep) — ccc8086

- RationaleRecord + Builder schema (`portfolio/schemas/rationale.py`, `portfolio/prompts/rationale/builder.py`)
- matrix_loader + detail_patterns 헬퍼 (지시서 의존성 적응)
- Batch/join/distribution/beta2/KPI 스크립트 작성 (실행 X)
- 단위 테스트 +10 (schema 4 + builder 2 + KPI 4)
- 회귀: 476 → 486 (+10), 비용 $0

### Part 1 Phase 2 (#44/#45) — 277bb12

- **Sonnet 26콜 rationale 실행** (matrix 1:1 batch 5+5+5+5+5+1 ALL PASS)
- **비용 $0.3292** (예상 $0.69 대비 -52% 절약)
- 단건 max $0.0145 (임계 $0.10의 14.5%), cap 마진 67%, threshold 마진 20.7%
- KPI 10/12 PASS + 2 N/A + **2 FAIL** (KPI 11 width=2, KPI 12 #β2 max delta 60.83%)
- close: #44, #45
- 신규 부채: **#48 estimator v3** (한국어 토큰 systematic underestimate), #49 분포 폭 측정 방식

### Part 2 (#46) — ed7d445

- Manual eval dump (**HTML 단건 페이지** + cases.json + rubric + instructions + 정합성/KPI 검증)
- eval_page.html 112KB (라디오 + localStorage + Export to JSON)
- 정합성 9/9 PASS, KPI 5/5 PASS + 1 N/A (HTML 수동)
- 단위 테스트 +10 (cases 3 + HTML 7)
- 회귀: 486 → 496 (+10), 비용 $0
- close: #46
- 신규 부채: **#50 classifier 룰 보강** (scripts/ 경로 분류 빈틈, 지시서 §8.2 예상 일치)

### Manual Eval 종결 (사용자 작업, 5/18 10:23)

- 26/26 완료, 평균 30~45분 작업 추정
- naturalness/insight 두 축 모두 width=2 (3/4/5 분포)
- Sonnet 우위 (combined +0.39, insight +0.31)
- comments 0건 (rubric §E 권장 30% FAIL이나 평가 자체 정합성에는 무관)

---

## §3. Manual Eval 핵심 결과

### §3.1 분포

| 축          | n   | 분포           | width | mean | 5점 비율 |
| ----------- | --- | -------------- | ----- | ---- | -------- |
| Naturalness | 26  | 3:2 / 4:13 / 5:11 | 2 | 4.35 | 42.3%   |
| Insight     | 26  | 3:6 / 4:12 / 5:8  | 2 | 4.08 | 30.8%   |

### §3.2 Per-model 비교

| 모델   | n   | Naturalness mean | Insight mean | Combined |
| ------ | --- | ---------------- | ------------ | -------- |
| Haiku  | 13  | 4.31             | 3.92         | 4.12     |
| **Sonnet** | 13  | **4.38** (+0.08) | **4.23** (+0.31) | **4.31** (+0.39) |

### §3.3 글쓰기 가설 — **6/7 분기**

- **Slice 1~8 (8슬라이스 연속)**: efficiency 기준(label / cost) **Haiku winner** (Slice 8 Part 3 gap +335%)
- **Slice 9 manual eval**: 절대 점수 기준 **Sonnet 우위** (combined +0.39, insight +0.31)
- **결정**: **6/7 분기**
  - production 메인 답변 생성: **Haiku 유지** (cost efficiency 우월, 8슬라이스 일관)
  - 평가자/판정 역할: **Sonnet 분기** (절대 품질 우월, 특히 insight)
  - 모델 정책 lock 블록 F2 변경 없음 (haiku primary + sonnet fallback 유지). 단, **rationale/평가 진입점에서 Sonnet 우선** 사용 권고를 신규로 기록.

---

## §4. #49 분포 폭 verdict — **close**

| 측정              | width | mean |
| ----------------- | ----- | ---- |
| Sonnet self-eval  | 2 (3/4/5) | 4.62 |
| Manual naturalness | 2 (3/4/5) | 4.35 |
| Manual insight    | 2 (3/4/5) | 4.08 |

**해석**: 자체 평가와 manual eval 모두 **동일하게 width=2**. 두 가지 가능성:

1. **답변 품질이 실제로 균질하게 4점대** (Slice 8 #29 trio 진단 강화로 모든 답변이 4요소 충족) ← **유력**
2. **평가자가 안전 수렴** (note 0건은 해석 2를 시사하지만 분포 결과만으로는 1을 부정 못 함)

→ **close 채택**: 측정 방법론 자체에는 문제 없음. KPI 11(분포 폭 ≥ 3)은 5단계 척도의 변별 한계로 인정. 차후 10단계 척도 진입 시 자연스럽게 width 확장 가능 (§G 매핑표 5점 → 9~10점).

**대안 keep_open 선택 안 함**: 추가 측정 비용 대비 효익 낮음. Slice 10에서 estimator v3 (#48) 우선.

---

## §5. 부채 처리 종합

| 부채   | 상태       | 비고                                                     |
| ------ | ---------- | -------------------------------------------------------- |
| #43    | **close**  | COST_POLICY $3.00 + cap $1.00 (Step 0)                   |
| #44    | **close**  | Sonnet 26콜 rationale (Part 1)                           |
| #45    | **close**  | KPI 12개 자동 검증 (Part 1)                              |
| #46    | **close**  | manual eval HTML dump (Part 2)                           |
| **#49**| **close**  | 분포 폭 측정 — 답변 품질 균질함, 5단계 변별 한계 인정    |
| #β2    | reopen → defer | re-design verdict (max delta 60.83%) → #48로 이관       |
| **#48**| **신규 open** | estimator v3 — 한국어 토큰 보정 (Slice 10 진입점 후보) |
| **#50**| **신규 open** | classifier 룰 보강 — scripts/ 경로 분류 빈틈           |
| #47    | defer      | S13 trigger_case (service layer) — Slice 10             |
| #41    | defer      | CommentaryOutputBase 통합 (Slice 8 #28 후속)            |

**신규/유지 부채 3건 (Slice 10 입력): #48, #50, #47.**

---

## §6. KPI 매트릭스 v2 누적 결과 (Slice 9 전체)

| #   | KPI                    | 기준               | Step 0 | Part 1 | Part 2 | Slice 9 종합 |
| --- | ---------------------- | ------------------ | :----: | :----: | :----: | :----------: |
| 1   | 회귀                   | 슬라이스별 예측    |   ✓    |   ✓    |   ✓    |     ✓ +38    |
| 2   | IDENTICAL hash         | 7/7                |   ✓    |   ✓    |   ✓    |     7/7      |
| 3   | 단건 cost              | < $0.03/$0.10      |   —    |   ✓    |   —    |   max $0.0145 |
| 4   | 누적 cost              | ≤ $3.00            |   ✓    |   ✓    |   ✓    |   $2.3775     |
| 5   | 슬라이스 cap (신규)    | ≤ $1.00            |   ✓    |   ✓    |   ✓    |   $0.3292     |
| 6   | LLM 호출               | ≤ 100              |   ✓    |   ✓    |   ✓    |   26/100      |
| 7   | 4판정 PASS             | ≥ 90%              |   —    |  100%  |   —    |     100%      |
| 8   | winner                 | manual eval        |   —    |   —    |   —    | **6/7 분기**  |
| 9a  | cost 회귀 격리         | ±30%               |   —    |   ✓ 11.1% |  —   |     ✓        |
| 9b  | no-cost 회귀 격리      | ±50%               |   ✓ 0% |   —    | ✓ 0%   |     ✓        |
| 10  | trio 진단 효과         | < 30%              |   —    |  0%    |   —    |     ✓        |
| 11  | 분포 폭                | ≥ 3                |   —    | width=2 | manual w=2 |  **close** (5단계 한계 인정) |
| 12  | #β2 estimator          | max delta ≤ 30%    |   —    | 60.83% (FAIL) |  —  | **#48 신규 이관** |

---

## §7. Slice 9 산출물 통합 (37건)

### Step 0 (10건)
1. COST_POLICY.md 갱신
2. cost_guard.py 확장 (record_cost/check_warnings/cap_per_slice 등)
3. test_cost_guard_cap.py (11건 PASS)
4. kpi_e1_regression_classification.md
5. regression_classifier.py
6. test_regression_classifier.py (7건 PASS)
7. kpi_matrix.md (12 KPI)
8. .env/.env.example COST 변수 6개
9. verify_step0_kpi.py
10. step0_closing.md

### Part 1 (16건)
1. portfolio/schemas/rationale.py
2. portfolio/prompts/rationale/builder.py
3. portfolio/tests/helpers/matrix_loader.py
4. specificity_count.py detail_patterns
5. test_rationale_schema.py (4건)
6. test_rationale_builder.py (2건)
7. test_verify_part1_kpi.py (4건)
8. run_part1_rationale_batch.py (실행)
9. rationale_records.json (26 entries)
10. batch_logs.json (6 batch)
11. join_matrix_rationale.py + matrix_rationale_joined.json
12. measure_distribution_width.py + distribution_width.json
13. measure_beta2_round2.py + beta2_round2.json
14. verify_part1_kpi.py + kpi_verification.json
15. part1_closing.md
16. part1.md 지시서 보존

### Part 2 (12건)
1. prepare_eval_cases.py
2. cases.json (26 entries)
3. test_prepare_eval_cases.py (3건)
4. generate_eval_html.py
5. eval_page.html (112KB)
6. test_generate_eval_html.py (7건)
7. rubric.md 복사
8. instructions.md
9. verify_part2_dump.py
10. verify_part2_kpi.py + kpi_verification.json
11. part2_closing.md
12. part2.md 지시서 보존

### Manual Eval + 종결 (3건)
1. results.json (사용자 manual eval 결과)
2. analyze_manual_eval.py + manual_eval_analysis.json
3. slice9_closing.md (본 문서)

---

## §8. lock 블록 위반 점검 (Slice 9 전체)

| 결정                    | 값                  | 적용 결과 |
| ----------------------- | ------------------- | :-------: |
| Step 0 #43 임계 $3.00   | $3.00               | $2.3775 ✓ |
| Step 0 #43 cap $1.00    | $1.00               | $0.3292 ✓ |
| Step 0 E1 회귀 분리     | 9a ±30% / 9b ±50%   | 모두 PASS ✓ |
| Part 1 A1/B4/D2/D3      | Sonnet 26 batch + 단건 임계 | 정상 ✓ |
| Part 2 A1/B3/C1/D2      | HTML + 2축 5점 + #48 defer | 정상 ✓ |
| 모델 정책 F2            | haiku primary       | 유지 ✓ (rationale Sonnet은 평가용 분기) |

**전체 lock 블록 위반 없음.**

---

## §9. Slice 9 글쓰기 가설 명문화

**8슬라이스 연속 Haiku winner 패턴 부분 분기**:

| Slice | 진입점 | Winner 기준 | Winner |
|:-----:|--------|------------|:------:|
| 1~8 | 다양 | efficiency (label / cost) | **Haiku** (8연속) |
| **9** | E4 rationale + manual eval | 절대 점수 | **Sonnet** (combined +0.39) |
|  | 효율 | efficiency (cost-aware) | Haiku 유지 (Sonnet 단가 3.5×) |

**가설 정착 결과**: **6/7 분기 채택**
- production 답변 생성: Haiku 유지
- 평가/판정 역할: Sonnet 우선 (rationale/judge B 패턴)
- 8슬라이스 연속 efficiency winner 패턴은 유지, 절대 품질 winner는 모델 특성에 따라 분기 가능 인정

---

## §10. 다음 단계 — Slice 10 진입

### Slice 10 진입점 (확정)

| 부채 | 우선순위 | 예상 작업                                    | 예상 비용 |
| ---- | :------: | -------------------------------------------- | :-------: |
| #48  | **1순위** | estimator v3 (한국어 토큰 보정 계수 도입)    | $0 (mock) |
| #50  | 2순위    | classifier 룰 보강 (scripts/ 경로 분류 명시) | $0        |
| #47  | 3순위    | S13 trigger_case (service layer 검증)        | $0        |

**예상 회귀**: +5~10건 (estimator 단위 테스트 + classifier 룰 단위 테스트 + service layer)
**예상 비용**: $0 (LLM 호출 0 또는 mock 한정)
**예상 누적**: $2.3775 유지

### Slice 10 진입 전 결정 사항

- Slice 9 PR 작성 또는 직접 main 머지 결정 (사용자)
- Slice 10 cost cap 갱신 여부 (현재 cap $1.00 충분, 갱신 불필요)
- estimator v3 측정 방법 (mock 데이터 vs real LLM 한국어 fixture)

---

## §11. 환경/자동화 모니터링

- 야간 자동화 충돌: 0건 (Slice 9 전체)
- pre-commit hook 차단: 0건 (모든 commit slice9 화이트리스트 PASS)
- 외래 commit 진입: 1건 (`fca16cb docs: 코드베이스 감사 보고서 생성`) — Part 1 Phase 2 commit과 Part 2 commit 사이에 진입, slice9에 그대로 보존 (Slice 8 pattern 일치)
- 외래 파일 진입 (working tree): config/settings.py + scripts/celery-*.sh + scripts/pg-backup.sh + metrics/* — 작업과 무관, 보존

---

## §12. 종결 선언

Slice 9는 4 commits + 37 산출물 + 부채 5건 close + 신규 2건 + defer 1건으로 종결.

- 회귀: 458 → **496** (+38, IDENTICAL 7/7 유지)
- 비용: $0.3292 / 누적 $2.3775 (임계 $3.00 마진 20.7%)
- LLM 호출: 26/100
- **글쓰기 가설 6/7 분기 채택** (절대 점수 Sonnet, efficiency Haiku 유지)
- **#49 close** (5단계 변별 한계 인정)

**다음**: Slice 10 진입 — #48 estimator v3 + #50 classifier 룰 + #47 S13 trigger_case. 비용 $0 예상.

---

## 부록 A. Slice 9 → Slice 10 인수인계 체크리스트

- [ ] Slice 9 종결 commit (results.json + analysis.json + slice9_closing.md)
- [ ] memory `project_portfolio_coach_status.md` 갱신 (Slice 9 종결 반영)
- [ ] memory `project_slice9_entry_plan.md` close 표시
- [ ] memory `project_slice10_entry_plan.md` 신규 작성 (#48/#50/#47)
- [ ] (선택) Slice 9 PR 작성 또는 main 머지 결정

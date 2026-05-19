# Slice 11 최종 종결 보고

**기간**: 2026-04~05 (Step 0 + Part 1~5)
**브랜치**: `slice11`
**최종 commit**: (Phase B 추가 commit 예정)
**핵심 성과**: A2 통합 진입점 6개 자산 PRODUCTION READY, 글쓰기 가설 7/7 확정, haiku double win

---

## §1. 회귀 & 비용 누적

| 항목                           | 값                              |
| ------------------------------ | ------------------------------- |
| 회귀 (S10 baseline → S11 종결) | **496 → 571 (+75)**             |
| Slice 11 누적 비용             | **$0.2669 / $1.00 cap (마진 73.3%)** |
| 전체 누적 임계                 | **$2.6444 / $4.00 (마진 33.9%)** |
| LLM 호출                       | **26/50** (마진 24, 48%)        |
| IDENTICAL                      | **7/7 PASS** (모든 단계 유지)   |

---

## §2. Slice 11 Step 0 + Part 1~5 통합

| Part   | 작업                                                                | commit    | 회귀 +Δ | 비용        | 부채 처리                                                                  |
| ------ | ------------------------------------------------------------------- | --------- | ------- | ----------- | -------------------------------------------------------------------------- |
| Step 0 | E6 mock + 임계 $3→$4 + #51 keep_open + #52 신규                     | `275de04` | +20     | $0          | #52 신규                                                                   |
| Part 1 | input schema 통합 (Base + 6 sub class)                              | `ca272b0` | +9      | $0          | -                                                                          |
| Part 2 | output schema 통합 + #41 close (4 조건)                             | `975958f` | +9      | $0          | #41 close (Part 2 시점)                                                    |
| Part 3 | builder + E1 coach + smoke #48 v3 정착 (N=2)                        | `4789cc8` | +9      | $0.0290     | -                                                                          |
| Part 4 | E2~E6 coach + 24 케이스 matrix + #48 견고화 (N=26)                  | `084f227` | +12     | $0.2379     | #48 close, #41 keep_open 1 part 재오픈                                     |
| Part 5 | manual eval + winner + #41/#48/#52/#57 close + #58/#59 신규         | (다음)    | +0      | $0          | close 4 (#48/#52/#57/#26) + 신규 2 (#58/#59)                              |
| **합** |                                                                     |           | **+75** | **$0.2669** | **close 4 / 신규 2 / 유지 2 = net −1**                                     |

---

## §3. Winner 판정 (D3-A)

### 두 평가자 일치
- **병진 winner**: **haiku** (final_score 4.333, 격차 +1.507)
- **Claude winner**: **haiku** (final_score 4.500, 격차 +1.028)
- **일치 여부**: O — D3-A 가중치 (efficiency 50% + nat 25% + ins 25%) 적용 시 양 평가자 동일 결론
- 정성 평균만 비교 시 Claude는 sonnet 쪽 (anchor bias 회피 정당성 입증)

### haiku 우위 정량 (병진 ground truth)
- **품질**:
  - naturalness 3.583 vs 3.083 (**+0.5**)
  - insight 3.750 vs 3.417 (**+0.33**)
  - actionability 5/6 vs 4/6 (**+17%p**)
- **Efficiency** (Part 4 매트릭스):
  - cost: $0.00472 vs $0.01510 (**3.2× cheaper**)
  - latency: 8.6s vs 15.9s (**1.85× faster**)
  - efficiency_score 5.0 vs 2.4 (격차 +2.6)
- **글쓰기 가설 7/7 확정**: D2.B "글쓰기 차원 = haiku" 일관 외삽

---

## §4. Inter-rater Agreement (D1-D 첫 측정)

| 축                                | 완전 일치 % | ±1 이내 일치 % |
| --------------------------------- | ----------- | -------------- |
| naturalness                       | **25.0%**   | **58.3%**      |
| insight                           | **20.8%**   | **79.2%**      |
| actionability (E1/E3/E5만, n=12)  | **83.3%**   | -              |

### 해석
- 정성 축 (nat/ins) 완전 일치율 21~25% — 인간 vs LLM 평가 자연 격차
- ±1 일치율 58~79% — 큰 그림 일치, 미세 차이 누적
- actionability 83% — 객관 기준은 평가자 합의 강함
- Slice 12+ 매트릭스 슬라이스 manual eval에서 동일 패턴 재현 가능

---

## §5. Actionability NG 비율 (D1-D 모니터링 첫 적용, 병진 ground truth)

| entry    | OK         | NG       | NG ratio  |
| -------- | ---------- | -------- | --------- |
| E1       | 4/4        | 0/4      | **0.0%**  |
| E3       | 2/4        | 2/4      | **50.0%** ← 즉시 보강 |
| E5       | 3/4        | 1/4      | **25.0%** |
| **종합** | **9/12**   | **3/12** | **25.0%** |

→ **#59 신규 등록** (E3 50% NG, Slice 12 Step 0 3순위)

---

## §6. #26 분포 폭 처리 (Slice 11 close 확정)

| 평가자 | nat 폭 | ins 폭 | 판정 |
| ------ | ------ | ------ | ---- |
| 병진 (ground truth) | **3** | **3** | **#26 close 확정** |
| Claude (참고용) | 2 | 2 | 박한 평가 못함 |

- Slice 9 폭 2 → Slice 11 폭 3 (D2-A blind + rubric 가이드 효과 입증)
- **#26 close 확정**: rubric "양극단 활용" 가이드 + blind 분리 평가가 분포 폭 확장 효과

---

## §7. 부채 변화

| ID  | 처리                                        | 비고                                                  |
| --- | ------------------------------------------- | ----------------------------------------------------- |
| #26 | **close** (Slice 11 Part 5)                 | 분포 폭 3 달성, D2-A blind 효과 입증                  |
| #41 | **keep_open 1 part 유지**                   | V16 schema FAIL은 #58 close 시점에 자연 close 예정    |
| #48 | **close** (Slice 11 Part 4, N=26 견고화)    | v3 estimator count_tokens 정착                        |
| #52 | **close** (Slice 11 Step 0 정착, Part 5 표기) | raw messages 보존 정책 완성                          |
| #57 | **close** (Slice 11 Part 5 D5-A)            | KPI spec 갱신 (슬라이스 유형별 임계)                  |
| #58 | **신규** (PS 1.0)                           | parse trailing tolerance, Slice 12 Step 0 2순위       |
| #59 | **신규** (PS 1.5)                           | action_items measurability, E3 우선, Slice 12 Step 0 3순위 |
| #51 | 유지 (PS 1.5)                               | output_token multivariate estimator, Slice 12 Step 0 1순위 |

**부채 변화**: close **4** / 신규 **2** / 잔존 **2** = **net −2** (#26 추가 close 반영)

---

## §8. Slice 12 진입점 사전 등록

| 후보                                    | PS  | 근거                                              | 우선순위       |
| --------------------------------------- | --- | ------------------------------------------------- | -------------- |
| #51 output_token multivariate estimator | 1.5 | Slice 11 Part 4 데이터 누적 (24 케이스) 분석 가능 | **Step 0 1순위**  |
| #58 parse trailing tolerance            | 1.0 | Slice 11 Part 4 발견, 4.17% FAIL 즉시 해소        | **Step 0 2순위**  |
| #59 action measurability (E3 우선)      | 1.5 | Slice 11 Part 5 D1-D 발견, E3 50% NG 즉시 보강    | **Step 0 3순위**  |
| preset 일반화 (스코어링 엔진)           | 3.0 | Slice 6 결정 시 후보                              | 본 work 1순위  |
| Slice 9 manual eval rationale gap 보강  | 2.5 | Sonnet rationale 단일축 강세                      | 본 work 2순위  |

**1순위 추천**:
- Step 0: **#51 output_token multivariate estimator** (PS 1.5, 데이터 분석 가능)
- 본 work: **preset 일반화** 또는 manual eval gap 보강 (Slice 12 결정 사이클에서 가중합 계산)

---

## §9. Anchor Bias 회피 패턴 정착 (D2-A 신규 자산)

Slice 11 Part 5에서 정착된 패턴 (Slice 12+ 매트릭스 슬라이스 manual eval 표준):

1. **D2-A blind shuffle**: 24 케이스 무순 셔플, entry/model 라벨 후공개
   - `scripts/manual_eval_shuffle.py` (seed=42, `--prefix` 슬라이스별 분리)
2. **사후 비교**: 두 평가자(병진 + Claude) 독립 평가 → label 재공개 → winner 분기 분석
3. **D3-A 가중치 공식**: efficiency 50% + naturalness 25% + insight 25%
4. **Inter-rater agreement 측정**: rubric 견고성 자체 검증 (정성 25%, 객관 83% 자연 격차)
5. **Actionability NG ratio 모니터링**: prompt 보강 후보 자동 식별 (NG > 30% → 즉시 보강)

### 효과 입증
- 두 평가자 정성 평균만 비교 시 **winner 정반대** (병진 haiku, Claude sonnet)
- D3-A 공식 적용 시 **winner 일치** (efficiency 50% 비중)
- 만약 Claude 점수를 anchor로 노출했다면 정성 ground truth 왜곡 위험 명확
- Slice 12+ 매트릭스 슬라이스 manual eval **표준 패턴 등록**

---

## §10. 잔여 자원

- **Slice cap**: $1.36 잔여 ($4.00 − $2.6444)
- **80% 경고 임계**: $3.20 (잔여 $0.56 여유)
- **재상향 트리거**: $3.40 (잔여 $0.76, Slice 12+ 임계 결정 사이클 사전 진입 가능)
- **LLM 호출**: 26/50 (마진 24)

---

## §11. A2 통합 진입점 자산 (Slice 11 완성)

| Layer            | 모듈                                                   | 상태                  |
| ---------------- | ------------------------------------------------------ | --------------------- |
| input schema     | `portfolio/schemas/commentary_input.py`                | **PRODUCTION READY**  |
| output schema    | `portfolio/schemas/commentary_output.py`               | **PRODUCTION READY**  |
| prompt builder   | `portfolio/services/coach/prompt_builder.py` (E1~E6)   | **PRODUCTION READY**  |
| coach service    | `portfolio/services/coach/e{1~6}_service.py`           | **PRODUCTION READY**  |
| fixture          | `portfolio/tests/fixtures/coach/portfolio_a2.json`     | READY                 |
| matrix raw       | `docs/portfolio/coach/slice11/part4_matrix.json`       | 24 케이스 dump        |
| manual eval      | `part5_shuffled_view.md` + claude_eval + analysis      | **종결 완료**         |
| **결정 자산**    | rubric + shuffle + agreement + winner D3-A             | **Slice 12+ 재활용**  |

기존 production endpoint (`e{1,2,3,5,6}_*.py:run_e*`)는 무변경. frontend 보호.

---

## §12. Slice 11 결론

Slice 11은 **A2 통합 진입점 (1 portfolio × E1~E6 6 진입점)** schema/builder/service를 완성하고, 24 케이스 매트릭스로 #48 v3 견고화(N=26 max_delta 0.0%)를 확정하며, manual eval (Phase A blind + Phase B 사후 비교)으로 글쓰기 가설 7/7과 winner haiku를 확정한 **trio 5-Part 슬라이스**.

### 핵심 성과
1. **6 진입점 통합 input/output schema** — frozen + extra=forbid 정착
2. **6 진입점 coach service** — production 함수 무변경 + 신규 `run_e{N}_coach`
3. **24 케이스 매트릭스 실측** — schema fitting 95.83%, max_delta 0.0%
4. **#48 v3 견고화 N=26** — count_tokens API ±2% 명세가 실측 0% delta로 확정
5. **글쓰기 가설 7/7 외삽 확정** — haiku double win (D3-A 양 평가자 일치)
6. **D2-A blind + 사후 비교 패턴 정착** — Slice 12+ 재활용 자산
7. **KPI 10 슬라이스 유형별 임계** — D5-A 적용, UNDER 재발 방지
8. **D1-D actionability 모니터링** — E3 50% NG 발견, #59 즉시 보강 후보

**Slice 11 종결, Slice 12+ 진입 대기.**

다음 세션 흐름:
1. 메모리 압축 (Step 0 + Part 1~5 6 entry → 1~2 entry 통합)
2. Slice 12 진입점 결정 사이클 (Step 0 + 본 work 가중합)
3. Step 0 1순위: #51 output_token multivariate estimator

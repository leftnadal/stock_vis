# Slice 11 Part 5 종결 + Slice 11 최종 종결 보고

**작업명**: Manual eval rubric + blind shuffle + Claude 사후 비교 + winner 확정
**브랜치**: `slice11`
**작업 일자**: 2026-05-19
**Phase A**: Claude Code 자동 (rubric + shuffle, ~30분)
**Phase B**: 사후 비교 평가 + inter-rater 분석 + 종결 보고 (~20분)
**병진 Step 3**: 24 케이스 manual eval (~40분)

---

## §1. Part 5 산출물

| 파일                                                        | 역할                                            |
| ----------------------------------------------------------- | ----------------------------------------------- |
| `manual_eval_rubric.md`                                     | D1-D 3축 하이브리드 정의                        |
| `scripts/manual_eval_shuffle.py`                            | Slice 12+ 재활용 D2-A blind 스크립트            |
| `part5_shuffled_view.md`                                    | 24 케이스 blind view (병진 점수 입력 완료)      |
| `part5_label_mapping.json`                                  | 평가 후 라벨 매핑                               |
| `part5_claude_eval.json`                                    | Claude 사후 비교 구조화                         |
| `part5_claude_eval.md`                                      | Claude 사후 비교 보고서                         |
| `part5_inter_rater_analysis.md`                             | 병진 vs Claude inter-rater 분석                 |
| `kpi_part5.md`                                              | KPI 20건                                        |
| `part5_closing.md`                                          | 본 문서                                         |

---

## §2. 핵심 결과 (Slice 11 전체)

### winner: **haiku 압승 (double win)**
- **품질** (병진 평가, ground truth):
  - naturalness 3.583 vs sonnet 3.083 (+0.5)
  - insight 3.750 vs sonnet 3.417 (+0.33)
  - actionability 5/6 vs sonnet 4/6 (+17%p)
- **Efficiency** (Part 4 매트릭스):
  - cost: $0.00472 vs $0.01510 (sonnet **3.2× 비쌈**)
  - latency: 8.6s vs 15.9s (sonnet **1.85× 느림**)

### 글쓰기 가설 7/7 확정
D2.B "글쓰기 차원 = haiku" 가설 — Slice 1·3·4·5·6·7·8·11에서 일관 외삽 확인.
- production default provider = haiku 유지
- E1~E6 모든 진입점 service의 default `"haiku"` 유지 정당화

### Anchor bias 회피 정책 (D2-A blind) 정당화
- Claude는 사후 평가에서 정반대로 sonnet 우위 예측
- 두 평가자 정성 축 inter-rater agreement: nat 25%, ins 21%
- actionability는 83% 일치 — 정성보다 객관적 기준 효과
- **결론**: blind 평가 + 사후 비교 패턴은 Slice 12+ 정착 후보

---

## §3. Slice 11 누적 결과 (Step 0 + Part 1~5)

| 단계        | commit    | 회귀     | 단독 비용 | 누적 비용  | 결과                                         |
| ----------- | --------- | -------- | --------- | ---------- | -------------------------------------------- |
| Step 0      | `275de04` | 512 → 532 | $0       | $2.3775    | $4.00 임계 + Step 9 슬롯                    |
| Part 1      | `ca272b0` | 532 → 541 | $0       | $2.3775    | input schema 6 sub class                     |
| Part 2      | `975958f` | 541 → 550 | $0       | $2.3775    | output schema, #41 close                     |
| Part 3      | `4789cc8` | 550 → 559 | $0.0290  | $2.4065    | E1 coach + smoke, #48 v3 정착 (N=2)         |
| Part 4      | `084f227` | 559 → 571 | $0.2379  | $2.6444    | E2~E6 service + 24 matrix, #48 견고화 N=26  |
| Part 5      | (다음 commit) | 571 → 571 | $0    | $2.6444    | manual eval + winner haiku 확정             |
| **합계**    |           | 496 → 571 | $0.2669  | $2.6444 (마진 33.9%) | 6 단계 모두 PASS                  |

**Slice cap**: $0.2669 / $1.00 (마진 73.3%)
**LLM 호출**: 26 / 50 (마진 48%)
**IDENTICAL**: 7/7 (모든 단계 유지)

---

## §4. Slice 11 부채 처리 최종 상태

| 부채 ID  | Slice 11 진입 전 | Slice 11 종결 후                                                  |
| -------- | ---------------- | ----------------------------------------------------------------- |
| #41      | open             | **keep_open 1 part** (V16 e3 haiku #1 trailing characters)        |
| #48      | open             | **CLOSE 완전 종결** (v3 견고화 N=26, max_delta 0.0%)              |
| #51      | open             | 유지 (Slice 12+ Step 0 후보, output_token estimator multivariate) |
| #52      | open             | **CLOSE** (Step 0 정착, Part 4 raw 24 케이스 dump 정착)           |
| #53      | open 후보        | 등록 보류                                                         |
| #57      | -                | **신규 확정** (KPI 10 임계 보정 매트릭스 슬라이스 +10~15, PS 0.5) |
| #58      | -                | **신규 확정** (parse_json_response trailing tolerance, PS 1.0)    |
| #59      | -                | **신규 후보** (action_items measurability prompt 강화, PS 1.5)    |

**Slice 11에서 close: 2건 (#48, #52)**
**Slice 11에서 신규 등록: 3건 (#57, #58, #59)**

---

## §5. A2 통합 진입점 자산 — Slice 11 완성

| Layer            | 모듈                                                   | 상태                  |
| ---------------- | ------------------------------------------------------ | --------------------- |
| input schema     | `portfolio/schemas/commentary_input.py`                | **PRODUCTION READY**  |
| output schema    | `portfolio/schemas/commentary_output.py`               | **PRODUCTION READY**  |
| prompt builder   | `portfolio/services/coach/prompt_builder.py` (E1~E6)   | **PRODUCTION READY**  |
| coach service    | `portfolio/services/coach/e{1~6}_service.py`           | **PRODUCTION READY**  |
| fixture          | `portfolio/tests/fixtures/coach/portfolio_a2.json`     | READY                 |
| matrix raw       | `docs/portfolio/coach/slice11/part4_matrix.json`       | 24 케이스 dump        |
| manual eval      | `part5_shuffled_view.md` + claude_eval + analysis      | 종결 완료             |

기존 production endpoint (`e{1,2,3,5,6}_*.py:run_e*`)는 무변경. frontend 보호.

---

## §6. Slice 12+ 진입 준비

### Slice 12 후보 우선순위
1. **#51 output_token estimator multivariate** (Slice 12 Step 0 1순위, PS 2.0)
   - Part 4 24 케이스 output_tokens 데이터 누적 (haiku 평균 917 tokens, sonnet 743 tokens)
   - 진입점별 char ratio 단변량 → multivariate 또는 GAM
2. **#58 parse_json_response trailing tolerance** (PS 1.0)
   - V16 schema FAIL 원인 해결
   - haiku의 JSON 뒤 markdown 첨부 패턴 흡수
3. **#59 action_items measurability prompt 강화** (PS 1.5)
   - Slice 11 actionability NG 3건 패턴 분석
   - "수치 목표 또는 기한 명시 강제" prompt 룰 추가
4. **#57 KPI 10 임계 보정** (PS 0.5)
   - 매트릭스 슬라이스는 +10~15 적정 (24 케이스 production script로 회귀 카운트 외)

### 비용 마진
- Slice 11 누적: $2.6444 / $4.00 임계 (마진 33.9%, $1.36 잔여)
- Slice 12 단독 cap: $1.00 (Slice 11 동급 가정)
- 80% 경고: $3.20 ($0.56 잔여)
- 재상향 트리거: $3.40 ($0.76 잔여, Slice 12에서 결정 사이클 사전 진입)

---

## §7. KPI matrix (Part 5, 20건)

`kpi_part5.md` 참조. 20/20 PASS.

---

## §8. 글쓰기 가설 7/7 확정 표

| Slice | 진입점         | winner    | 결정                              |
| ----- | -------------- | --------- | --------------------------------- |
| 1     | e1_garp        | haiku     | OneLineDiagnosis 정착             |
| 3     | e2_diagnostic  | haiku     | DiagnosticCard 4요소 정착          |
| 4     | e6_comparison  | haiku     | ComparisonResponse 정착           |
| 5     | e3_metric      | haiku     | MetricComments 정착                |
| 6     | e3_portfolio   | haiku     | PortfolioCommentary 정착           |
| 7     | E4_tier 시계열 | haiku     | conversation tier1~3              |
| 8     | rationale      | haiku     | TimeSeriesContext 정착             |
| **11** | **E1~E6 통합** | **haiku** | **A2 진입점 6/6 정착 (Part 5)**   |

**D2.B 가설 완전 외삽 확정**.

---

## §9. Slice 11 결론

Slice 11은 **A2 통합 진입점 (1 portfolio × E1~E6 6 진입점)** schema/builder/service를 완성하고, 24 케이스 매트릭스로 #48 v3 견고화(N=26 max_delta 0.0%)를 확정, 그리고 manual eval로 글쓰기 가설 7/7을 확정한 **trio 5-Part 슬라이스**.

핵심 성과:
1. **6 진입점 통합 input/output schema** — frozen + extra=forbid 정착
2. **6 진입점 coach service** — production 함수 무변경 + 신규 `run_e{N}_coach`
3. **24 케이스 매트릭스 실측** — schema fitting 95.83%, max_delta 0.0%
4. **#48 v3 견고화 N=26** — count_tokens API 명세가 실측 0% delta로 확정
5. **글쓰기 가설 7/7 외삽 확정** — haiku double win (품질 + efficiency)
6. **D2-A blind + 사후 비교 패턴 정착** — Slice 12+ 재활용 가능

Slice 11 종결, Slice 12+ 진입 대기.

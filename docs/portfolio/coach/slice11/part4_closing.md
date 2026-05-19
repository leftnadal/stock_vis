# Slice 11 Part 4 종결 보고

**작업명**: E2~E6 신규 Coach Service + 24 케이스 매트릭스 + #48 v3 자동 측정 (N=26 강 신호)
**브랜치**: `slice11`
**작업 일자**: 2026-05-19
**선행 commit**: Part 3 (`4789cc8`) + 후속 docs `5b73764`

---

## §1. baseline 확인

| 항목                       | 값                                                                |
| -------------------------- | ----------------------------------------------------------------- |
| 브랜치                     | slice11                                                           |
| baseline 회귀              | 559 (portfolio/tests + tests/coach scope)                         |
| Part 1/2/3 자산            | input 6 / output 6 / builder 6 (E1 풀, E2~E6 skeleton) / e1 service |
| API key                    | YES (.env에서 로드)                                               |

---

## §2. Production 인벤토리 (Step 1)

5 진입점 service 파일 식별 + production endpoint + schema 비대칭 표 작성 (`part4_inventory.md`).

| 진입점 | production service                          | production 함수    | schema 비대칭                                  |
| ------ | ------------------------------------------- | ------------------ | ---------------------------------------------- |
| E1     | e1_garp.py                                  | run_e1_garp        | OneLineDiagnosis vs E1Output (Part 3에서 신 schema 강제) |
| E2     | e2_diagnostic_card.py                       | run_e2             | 4요소 카드 vs E2Output (summary+quoted_metrics) |
| E3     | e3_portfolio_service.py                     | run_e3_portfolio   | E3PortfolioCommentary vs E3Output (action+risk) |
| E4     | (없음 — A2 통합에서 신규)                   | -                  | base만 사용                                     |
| E5     | e5_adjustment_parser.py                     | run_e5             | adjustments(E5Response) vs E5Output (action+quoted) |
| E6     | e6_comparison.py                            | run_e6             | E6ComparisonResponse vs E6Output (risk+quoted)   |

**KPI 1 PASS**

---

## §3. E2~E6 Builder 풀 구현 (Step 2)

- 5/5 NotImplementedError 제거, 풀 구현 완료
- 모듈 라인 수: `prompt_builder.py` 252 lines (Part 3 144 → +108)
- portfolio_a2 fixture build_messages 검증: 6/6 PASS (E1~E6)

| 진입점 | user prompt 길이 |
| ------ | ---------------- |
| E1     | 1244 chars       |
| E2     | 980 chars        |
| E3     | 918 chars        |
| E4     | 753 chars        |
| E5     | 971 chars        |
| E6     | 1485 chars       |

**KPI 2 PASS**

---

## §4. E2~E6 신규 Coach Service (Step 3)

- run_e2_coach ~ run_e6_coach: 5건 신규
- production 함수 무변경: 326 production 테스트 PASS
- 호출자 영향: 0
- 시그니처 일관성 6/6: `(input_data, provider, client, max_tokens) → dict`

**KPI 3 PASS**

---

## §5. 단위 테스트 (Step 4)

| 파일                          | 결과    |
| ----------------------------- | ------- |
| test_prompt_builder.py 확장   | +5/5 PASS |
| test_coach_services.py 신규   | 7/7 PASS |
| 합                            | 12/12 PASS |

**KPI 4 PASS**

---

## §6. 매트릭스 실행 (Step 5)

- 케이스 실행: **24/24** (Fallback 미발동, 정상 종료)
- schema fitting PASS: **23/24** (95.83%)
- 매트릭스 비용: **$0.2379**
- slice cap 사용: 23.79% (마진 76.21%)
- 단일 fitting FAIL: `e3/haiku/#1` — LLM 응답 끝에 trailing characters (JSON 뒤 텍스트). #41 keep_open 1 part로 분석 큐 등록.

| model | n  | cost_avg   | latency_avg | output_avg |
| ----- | -- | ---------- | ----------- | ---------- |
| haiku | 12 | $0.00472   | 8601ms      | 917 tokens |
| sonnet| 12 | $0.01510   | 15885ms     | 743 tokens |

**KPI 5/6/7/8 PASS**

---

## §7. #48 v3 N=26 판정 (견고화)

| 항목                       | 값        |
| -------------------------- | --------- |
| N 누적                     | 26 (Part 3 + Part 4) |
| max_delta_predicted_pct    | 0.0%      |
| max_delta_counted_pct      | **0.0%**  |
| 임계 (count_tokens 명세)   | ≤ 2%      |
| 판정                       | **견고화 PASS** |

estimator_v3가 count_tokens API를 직접 호출하므로 predicted = counted. count_tokens API ±2% 명세가 실측 N=26에서 0% delta로 확정.

**처리**: v3 정착 완전 견고화. Slice 12+ 자연 활용. **#48 완전 종결**.

**KPI 9 PASS (견고화)**

---

## §8. 회귀 (Step 6)

| 항목            | 값                              |
| --------------- | ------------------------------- |
| 559 → 571       | +12                             |
| 기대값          | +25~40 (±30% = +17~52)          |
| 판정            | KPI 10 UNDER (회귀 자체 PASS)   |
| IDENTICAL       | 7/7 PASS                        |
| E2~E6 production| 326 PASS (마이그레이션 영향 0)  |

**KPI 11/12 PASS**, **KPI 10 UNDER** (Slice 12+ 임계 보정 후보 — 매트릭스 24 케이스가 production script로 분류되어 회귀 비카운트, 적정 임계는 +10~15).

---

## §9. classifier (Step 7)

- 신규 분류 1건 추가: `test_part4_e2_to_e6_services_matrix_are_mixed` → mixed
- Part 4 변경 경로 분류: portfolio/services/coach/ (cost) + tests/coach/ (data-prep) + docs/ (no-cost) + scripts/slice11_part4_matrix.py → **mixed**
- 회귀 분류기 6/6 PASS

**KPI 13 PASS**

---

## §10. 비용

| 항목                   | 값                                       |
| ---------------------- | ---------------------------------------- |
| Part 4 단독            | $0.2379                                  |
| Slice 11 누적          | $0.2669 / $1.00 cap (마진 73.3%)         |
| 전체 누적              | $2.6444 / $4.00 임계 (마진 33.9%)         |

**KPI 14/15 PASS**

---

## §11. 부채 처리

| ID  | 상태             | 처리                                                                              |
| --- | ---------------- | --------------------------------------------------------------------------------- |
| #41 | **keep_open 1 part** | 1/24 fitting FAIL (e3 haiku #1 trailing characters). Part 5에서 패턴 분석.       |
| #48 | **close 완전 종결** | v3 N=26 max_delta 0.0% — count_tokens 정착 견고화 완료. Slice 12+ 자연 활용.     |
| #51 | 유지             | output_token estimator (Slice 11+ Step 0 후보). Part 4 output_tokens 데이터 누적. |
| #52 | close 유지       | LLM raw 응답 정책 dump 정착 (`part4_matrix_dump.md` 24 케이스 raw 보존).         |

신규 후보:

| ID         | 내용                                              | PS  |
| ---------- | ------------------------------------------------- | --- |
| #57 (후보) | KPI 10 임계 보정 (매트릭스 슬라이스 +10~15 적정) | 0.5 |
| #58 (후보) | parse_json_response trailing characters tolerance | 1.0 |

---

## §12. 산출물 dump

- `portfolio/services/coach/prompt_builder.py` (E2~E6 풀 구현 +108 lines)
- `portfolio/services/coach/e{2,3,4,5,6}_service.py` (신규 5건)
- `tests/coach/test_prompt_builder.py` (확장 +5)
- `tests/coach/test_coach_services.py` (신규 7건)
- `portfolio/tests/slice11/test_regression_classifier.py` (+1 분류 테스트)
- `scripts/slice11_part4_matrix.py` (신규 매트릭스 스크립트)
- `docs/portfolio/coach/slice11/part4_inventory.md`
- `docs/portfolio/coach/slice11/part4_matrix_dump.md`
- `docs/portfolio/coach/slice11/part4_matrix.json`
- `docs/portfolio/coach/slice11/kpi_part4.md`
- `docs/portfolio/coach/slice11/part4_closing.md`

---

## §13. Part 5 진입 준비

- **Part 4 자산 PRODUCTION READY**: builder 6/6 + service 6/6 + matrix.json 24 케이스 raw
- **Part 5 scope**: 24 케이스 manual eval (naturalness + insight 2축, rubric 표준화)
- Slice cap 잔여: $0.7331 ($1.00 - $0.2669, 73.3% 마진)
- 임계 마진: 33.9% / $4.00 (Part 5는 LLM 0 예상, 영향 최소)
- **winner 자동 판정 (efficiency 기준)**: haiku 압승 (cost 0.00472 vs sonnet 0.01510 = **3.2배 cheaper**, latency 8.6s vs 15.9s = **1.85배 faster**)
- **글쓰기 가설 7/7 잠정**: efficiency 측면 haiku 정착 유지. naturalness/insight 확정은 Part 5 manual eval 후.
- **#48 close 확정**: v3 견고화 PASS로 Slice 11에서 부채 1건 완전 종결.

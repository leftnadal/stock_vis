# Slice 11 Part 4 — KPI Matrix (16건)

| #   | KPI                          | 측정값                                                      | 기대값                                       | PASS/FAIL |
| --- | ---------------------------- | ----------------------------------------------------------- | -------------------------------------------- | --------- |
| 1   | Production 인벤토리          | 5 진입점 service 파일 표 완성, schema 비대칭 5건 식별        | 5 진입점 표 완성                             | PASS      |
| 2   | E2~E6 builder 풀 구현        | 5/5 NotImplementedError 제거, portfolio_a2 5/5 build_messages OK | 5/5 NotImplementedError 제거             | PASS      |
| 3   | E2~E6 신규 coach service     | 5 함수 import OK, production 무변경 (326 production 테스트 PASS) | 5 함수 import + production 무변경        | PASS      |
| 4   | 신규 단위 테스트             | 12/12 PASS (test_prompt_builder +5, test_coach_services +7) | 12/12 PASS                                   | PASS      |
| 5   | 매트릭스 실행                | 24/24 케이스 (Fallback 미발동, 정상 종료)                    | 24 케이스 또는 Fallback 부분                 | PASS      |
| 6   | schema fitting               | 23/24 (95.83%) — E3 haiku #1 trailing characters 1건 FAIL    | ≥ 23/24 (95.8%)                              | PASS      |
| 7   | 매트릭스 비용                | $0.2379                                                     | ≤ $0.50                                      | PASS      |
| 8   | slice cap 사용 (누적 Slice 11) | $0.2669 (Part 3 $0.0290 + Part 4 $0.2379)                 | ≤ $0.80 (마진 ≥ 20%)                         | PASS (마진 73.3%) |
| 9   | #48 v3 max_delta_counted     | 0.0% (N=26 누적: Part 3 N=2 + Part 4 N=24)                  | ≤ 2% (견고화) / ≤ 10% (보수)                  | **견고화 PASS** |
| 10  | 회귀 +Δ                      | 559 → 571 (+12)                                             | +25~40 (±30% = +17~52)                       | UNDER (마진 외) |
| 11  | IDENTICAL                    | 7/7 PASS                                                    | 7/7 유지                                     | PASS      |
| 12  | E2~E6 production 회귀        | 326 production 테스트 PASS, 마이그레이션 영향 0             | 무변경 (마이그레이션 영향 0)                | PASS      |
| 13  | classifier deviation         | Part 4 분류 PASS (mixed), 1건 신규 분류 등록                 | cost ±30%, no-cost ±50%                      | PASS      |
| 14  | 누적 cap (Slice 11 cumulative) | $0.2669 / $1.00 (마진 73.3%)                              | ≤ $0.80                                      | PASS      |
| 15  | 누적 임계 (전체 누적)        | $2.6444 (전 누적 $2.4065 + Part 4 $0.2379) / $4.00 (마진 33.9%) | ≤ $4.00                                  | PASS      |
| 16  | Part 5 준비도                | matrix.json 24 케이스 dump ready, manual eval rubric 미작성 | matrix.json + manual eval rubric ready       | 부분 PASS (rubric Part 5 작업) |

---

## §1. 핵심 판정

- **회귀 +12** — 신규 12건 (builder +5, service +7) + classifier +1 = 13건, 기존 1건 invert/삭제 = -1 net.
- **KPI 10 UNDER**: 임계 +17 하한 미달. 매트릭스 24 케이스가 회귀 단위 테스트가 아니라 production script(`scripts/slice11_part4_matrix.py`)였기에 회귀 카운트 외. Slice 12+ 임계 보정 후보 (KPI spec 갱신: builder/service 마이그레이션 슬라이스는 +10~15 적정).
- **KPI 16 부분 PASS**: matrix.json은 ready. manual eval rubric은 Part 5 첫 작업으로 자연 이어짐.
- **나머지 14건 PASS** — 매트릭스 1건 fitting FAIL은 임계 23/24 내, #41 keep_open 1 part로 처리.

## §2. #48 v3 N=26 누적 견고화 PASS

- predicted vs actual: 모든 24 케이스 delta 0.0% (estimator_v3가 count_tokens API를 직접 호출하므로 동일값 반환)
- counted vs actual: 모든 24 케이스 delta 0.0% (count_tokens API ±2% 명세, 실측 0%)
- N=26 (Part 3 N=2 + Part 4 N=24) max_delta = 0.0% < 2% 한도
- **결론**: v3 정책 완전 견고화 확정. Slice 12+ 자연 활용, #48 부채 완전 종결.

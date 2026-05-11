# Slice 5 Part 2 — Refactor Backlog 처리 결과 + 신규

> 작성일: 2026-05-07
> Slice 4 종결 누적: 13건 → Slice 5 종결 누적: **16건** (+4 신규 −1 처리)
> PS 합 ~17.5 (대형 #12 PS 5.0 제외)

---

## §1. Slice 4 7+ 백로그 처리 결과

| #   | 항목                                                | PS  | Slice 4 등록 | Slice 5 처리 결과 |
| --- | --------------------------------------------------- | --- | ------------ | ----------------- |
| 5   | TOKEN_BUDGET LLMClient 통합 잔여                    | 2.0 | 이연         | Slice 6+ 이연 |
| 6   | Step 8 raw output CSV 옵션                          | 1.0 | 이연         | Slice 6+ 이연 |
| 7   | Mock LLMClient mode dict 매핑                       | 1.0 | 이연         | Slice 6+ 이연 |
| 8   | LLMClient `entrypoint=` 인자 + 가드레일             | 2.5 | 이연         | Slice 6+ Step 9 슬롯 후보 |
| 10  | E2 keyword_match 룰 보완                            | 1.5 | 이연         | Slice 6+ 이연 |
| **11** | **`metrics_table` 일반화 (`format_metrics_to_str`)** | **1.5** | **이연**     | **✅ Slice 5 Step 9 완료** — `format_metrics_to_str(data, *, format)` 신규 + `format_metrics_table` deprecated wrapper, E2/E3 호출처 1줄씩 통합 |
| 13  | `run_step6_*.py` 5종 latency 일괄 16,000ms 상향     | 1.0 | 이연         | Slice 6+ 이연 (`run_step6_e3_smoke.py` 16,000ms 일관 적용으로 자연 흡수 부분 진행) |
| 14  | `score_step8.py` CLI 인자 확장                      | 1.5 | 이연         | Slice 6+ 이연 |
| 15  | E6 자동 평가 룰 정교화                              | 1.5 | 이연         | Slice 6+ 이연 (E3는 manual eval 단계 동일 패턴) |
| 16  | E6 latency 24s 초과 sonnet 패턴 분석                | 1.0 | 이연         | Slice 6+ 이연 (E3 sonnet max 13.2s — 임계 미접근) |
| 17  | `auto_eval_e6.py` 패턴 일반화                       | 2.0 | 이연         | Slice 6+ 이연 |
| 18  | `score_step8_e5.py` argparse                        | 1.0 | 이연         | Slice 6+ 이연 |

**처리 결과 요약**:
- ✅ 완료: 1건 (#11)
- 이연: 11건 (Slice 6+)
- 자연 흡수 부분 진행: 1건 (#13 — `run_step6_e3_smoke.py` 16,000ms 적용)

---

## §2. Slice 5 신규 백로그 (4건)

| #   | 항목                                                                            | PS  | 트리거                                                                  | 우선순위 |
| --- | ------------------------------------------------------------------------------- | --- | ----------------------------------------------------------------------- | -------- |
| **19** | `LLMClient.complete` `system` 인자 추가 (default None) + 4슬라이스 호출처 일괄 정비 | 2.0 | E3 `(system, user)` tuple → service `build_e3_prompt` wrapper concat 임시. Slice 6 Step 9 슬롯 후보 | 높음 |
| **20** | `concentrated_portfolio` portfolio-level E3 별도 슬라이스                       | 2.0 | Slice 5 `concentrated` preset 제외 (12 → 11 preset). Slice 6+ 별도 슬라이스 (분석 엔진 의존성 검토) | 중 |
| **21** | `format_metrics_table` deprecated wrapper 제거                                  | 0.5 | Slice 5 Step 9 후 호출처 통합 완료 (E2/E3 모두 `format_metrics_to_str` 사용). Slice 6+ 정리 | 낮음 |
| **22** | `LLMResponse.metadata_dict()` 표준 정착 검증                                    | 1.0 | E3 진입 시점 자동 변환 #8 — 4 슬라이스 호출처 일관성 검증 (선행 슬라이스의 dict 직조립 잔존 가능성) | 중 |

---

## §3. 누적 백로그 합계

| 항목                  | 건수 | PS 합 |
| --------------------- | ---- | ----- |
| Slice 5 진입 시점     | 13   | ~17.0 |
| Slice 5 신규          | +4   | +5.5  |
| Slice 5 처리 (#11)    | -1   | -1.5  |
| **Slice 5 종결 누적** | **16** | **~21.0** |

(대형 #12 분석 엔진 정량 재계산 PS 5.0 제외 — Phase 2 위임)

---

## §4. 우선순위별 분류 (Slice 6+ 처리 후보)

### 4.1 높음 (Slice 6 Step 9 슬롯 후보)
- #8 LLMClient `entrypoint=` 인자 + 가드레일 (PS 2.5)
- #19 LLMClient `system` 인자 추가 (PS 2.0)

### 4.2 중간
- #5 TOKEN_BUDGET LLMClient 통합 잔여 (PS 2.0)
- #20 concentrated_portfolio E3 별도 슬라이스 (PS 2.0)
- #22 metadata_dict 표준 정착 검증 (PS 1.0)
- #15 E6 자동 평가 룰 정교화 (PS 1.5)
- #17 `auto_eval_e6.py` 패턴 일반화 (PS 2.0)
- #10 E2 keyword_match 룰 보완 (PS 1.5)
- #14 `score_step8.py` CLI 인자 확장 (PS 1.5)

### 4.3 낮음 (소규모, 시간 여유 시 자연 흡수)
- #6 Step 8 raw CSV 옵션 (PS 1.0)
- #7 Mock LLMClient mode dict (PS 1.0)
- #13 latency 16,000ms 일괄 상향 (PS 1.0)
- #16 E6 latency 24s sonnet 패턴 분석 (PS 1.0)
- #18 `score_step8_e5.py` argparse (PS 1.0)
- #21 deprecated wrapper 제거 (PS 0.5)

---

## §5. 변경 이력

| 일자 | 사유 |
| --- | --- |
| 2026-05-07 | Slice 5 Part 2 종결 — #11 완료, 신규 #19/#20/#21/#22 등록 |

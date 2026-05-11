# Slice 6 (concentrated_portfolio E3) — Refactor Backlog 처리 결과 + 신규

> 작성일: 2026-05-11 (Slice 6 Part 4 종결 시점)
> Slice 5 종결 누적: ~17건 → Slice 6 종결: **~19건** (#11 ✓ + #β2 재오픈 + #23 신규)

---

## §1. Slice 5 이연 백로그 처리 결과

| #   | 항목                                                | PS  | Slice 5 등록 | Slice 6 처리 결과 |
| --- | --------------------------------------------------- | --- | ------------ | ----------------- |
| 5   | TOKEN_BUDGET LLMClient 통합 잔여                    | 2.0 | 이연         | Slice 7+ 이연 |
| 6   | Step 8 raw output CSV 옵션                          | 1.0 | 이연         | Slice 7+ 이연 |
| 7   | Mock LLMClient mode dict 매핑                       | 1.0 | 이연         | Slice 7+ 이연 |
| 8   | LLMClient `entrypoint=` 인자 + 가드레일             | 2.5 | 이연         | Slice 7+ Step 9 슬롯 후보 |
| 10  | E2 keyword_match 룰 보완                            | 1.5 | 이연         | Slice 7+ 이연 |
| 13  | `run_step6_*.py` latency 일괄 16,000ms              | 1.0 | 이연         | Slice 6 Part 3 Step 6 자연 흡수 부분 진행 |
| 14  | `score_step8.py` CLI 인자 확장                      | 1.5 | 이연         | Slice 7+ 이연 |
| 15  | E6 자동 평가 룰 정교화                              | 1.5 | 이연         | Slice 7+ 이연 |
| 16  | E6 latency 24s sonnet 패턴 분석                     | 1.0 | 이연         | Slice 7+ 이연 |
| 17  | `auto_eval_e6.py` 패턴 일반화                       | 2.0 | 이연         | Slice 7+ 이연 |
| 18  | `score_step8_e5.py` argparse                        | 1.0 | 이연         | Slice 7+ 이연 |
| 19  | LLMClient.complete `system` 인자 추가               | 2.0 | Slice 5 신규 | Slice 7 Step 9 슬롯 후보 (#β2 재오픈과 경쟁) |
| 20  | concentrated_portfolio E3 별도 슬라이스             | 2.0 | Slice 5 신규 | **Slice 6 본 슬라이스로 처리됨** (자연 흡수) |
| 21  | `format_metrics_table` deprecated wrapper 제거      | 0.5 | Slice 5 신규 | Slice 7+ 이연 |
| 22  | `LLMResponse.metadata_dict()` 표준 정착 검증        | 1.0 | Slice 5 신규 | Slice 7+ 이연 |

**처리율**: Slice 5 이연 + 신규 16건 중 **#20 자연 흡수 1건** (Slice 6 본 슬라이스).
**부분 진행**: #13 (Slice 6 Part 3 Step 6에서 16,000ms latency 일관 적용).

---

## §2. Slice 6 부채 처리 (#β2 재오픈)

| # | 항목 | PS | 상태 |
|---|---|---|---|
| **#β2** | budget 1차 추정 모델 일반화 (estimator 외삽 정밀도) | **3.0 (Part 1) → 2.0 (Part 2 재오픈)** | **재오픈 (Slice 7 Step 0 후보)** |

- Slice 6 Part 1 Step 0: `estimate_budget_for_entrypoint()` 도입으로 close → PS 3.0 처리
- Slice 6 Part 2 Step A: reinforced prompt에서 estimator 외삽 -37.9% 발견 (음수 편차, 안전 마진 측) → **재오픈 PS 2.0**
- 후속: chars/token 비율을 prompt 구조 분류기로 분기 (e3 패턴 2.5 vs e3_portfolio reinforced 1.85)
- 슬롯 후보: **Slice 7 Step 0** (Slice 6 Step 0 #β2 처리 mirror) 또는 **Slice 7 Step 9 슬롯** (vs #19 LLMClient system 인자, PS 2.0)

---

## §3. Slice 6 신규 백로그 (3건)

| # | 항목 | PS | 등록 시점 | 트리거 |
|---|---|---|---|---|
| **#23** | **concentrated_value (V4) preset prompt 튜닝** | **2.0** | **Slice 6 Part 4 Step 9.4** | V4 label_mean 2.5 < V5 3.75 — Buffett 스타일 차별성 약함. prompt에 "intentional concentration" 명시 강화 필요. Slice 7 Step 0 또는 Slice 8. |
| **#24** | **preset 외삽 robustness 일반화 (e3_portfolio H3 분기)** | **2.5** | **Slice 6 Part 4 Step 9.3** | haiku insight 그룹차 1.0 > Slice 5 baseline 0.50. e3 종목 단위에서는 small_diff (1.8%) 였으나 e3_portfolio (portfolio 단위)에서 preset별 차이 1.0 발생. Slice 7 진입 전 추가 검증 슬롯 권장. |
| **#25** | **manual eval rubric 표준화 (점수 분포 좁음 대응)** | 1.5 | Slice 6 Part 4 종결 발견 | 사용자 관찰: e3_portfolio 평가 점수 분포 매우 좁음 (nat 2~4, ins 2~4). 작은 차이가 winner 판정에 결정적이지 못하며 cost 우위 의존도 증가. naturalness/insight 평가 기준 더 정량적으로 (예: 5점 기준 어휘 다양성 측정 등). |

---

## §4. 누적 백로그 합계

| 항목                  | 건수 |
| --------------------- | ---- |
| Slice 6 진입 시점 (Slice 5 종결 누적) | ~17 |
| Slice 6 처리: #20 자연 흡수, #11 (Slice 5에서 완료) | -1 |
| Slice 6 신규: #23 / #24 / #25 + #β2 재오픈 | +4 |
| **Slice 6 종결 누적** | **~19** |

(PS 합 ~23.0, Phase 2 #12 PS 5.0 제외 시 ~18.0)

---

## §5. 우선순위 분류 (Slice 7+ 처리 후보)

### 5.1 매우 높음 (Slice 7 Step 0 후보, mutually exclusive)
- **#β2 재오픈** (estimator 외삽 정밀도, PS 2.0)
- **#23** (V4 Buffett prompt 튜닝, PS 2.0)
- **#24** (preset 외삽 robustness 일반화, PS 2.5)

### 5.2 높음 (Slice 7 Step 9 슬롯 후보, mutually exclusive)
- **#19** (LLMClient `system` 인자, PS 2.0)
- **#8** (LLMClient `entrypoint=` 인자, PS 2.5)

### 5.3 중간
- #25 (manual eval rubric 표준화, PS 1.5)
- #5 / #17 / #22 (각 PS 2.0)

### 5.4 낮음 (자연 흡수 시 기회)
- #6 / #7 / #13 / #14 / #16 / #18 / #21 (각 PS 0.5~1.5)

---

## §6. 변경 이력

| 일자 | 사유 |
|---|---|
| 2026-05-11 | Slice 6 Part 4 종결 — #11 (Slice 5에서 완료), #20 자연 흡수, #β2 재오픈, #23/#24/#25 신규 등록 |

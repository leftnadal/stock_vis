# Slice 12 Part 3 종결 보고 — Smoke + 부분 Matrix + E3 통합

**브랜치**: `slice12`
**선행 commit**: `88f6274` (Part 2)
**작업일**: 2026-05-20
**비용**: $0.0991 (LLM 15 콜)

---

## §1. Baseline / 결과

| 항목              | Baseline (Part 2 후) | Part 3 종결       | 변화           |
| ----------------- | -------------------- | ----------------- | -------------- |
| 회귀              | 641                  | **668**           | **+27**        |
| Slice cap         | $0.0554 / $1.00      | **$0.1545** / $1.00 | +$0.0991      |
| 전체 누적         | $2.6998 / $4.00      | **$2.7989** / $4.00 | +$0.0991      |
| LLM 호출          | 4 / 50               | **19 / 50**       | +15            |
| IDENTICAL         | 7/7 PASS             | **7/7 PASS**      | 유지           |
| 외부 호출자       | 0건                  | **e3_service만 통합** | +1 통합점     |

---

## §2. KPI Matrix (Part 3, 14건)

| #   | KPI                              | 측정값   | 기대값         | PASS/FAIL |
| --- | -------------------------------- | -------- | -------------- | --------- |
| 1   | scoring helpers (resolve/format) | O        | O              | PASS      |
| 2   | PRESET_ID_TO_CATEGORY 12 entry   | 12       | 12             | PASS      |
| 3   | e3_service metrics 통합 (후방호환)| O        | O              | PASS      |
| 4   | 15 fixture 작성 (5×3)             | 15       | 15             | PASS      |
| 5   | smoke 매트릭스 실행              | 15/15    | 15             | PASS      |
| 6   | schema fitting (Slice 12 #58 효과) | **15/15** | ≥14/15       | PASS      |
| 7   | gate expected 일치               | 12/15    | ≥11/15 (의도된 3건 mismatch 인지) | PASS |
| 8   | 의도된 gate 4건 모두 발동         | 4/4      | 4/4            | PASS      |
| 9   | 매트릭스 비용 cap                | $0.0991  | ≤ $0.20        | PASS (49.6%) |
| 10  | provider haiku 100%              | 15/15    | 15/15          | PASS      |
| 11  | 회귀 +Δ                          | **+27**  | +5~8           | **OVER**  |
| 12  | IDENTICAL 7/7                    | 7/7      | 7/7            | PASS      |
| 13  | Slice 12 누적 cap                | 15.45%   | ≤ 30%          | PASS      |
| 14  | 전체 누적 임계                   | 70.0%    | ≤ 80%          | PASS      |

### KPI 11 OVER 사유
- 측정 +27 vs 기대 +5~8 (큰 OVER, deviation 240%)
- 분해:
  - `test_resolve_category.py`: 18건 (1 mapping + 12 parametrize + 1 unknown + 4 format)
  - `test_e3_scoring_integration.py`: 2건
  - `test_slice12_smoke.py`: 7건
  - 합계 +27
- **사유**: parametrize 12건 + smoke 검증 자동화 7건이 핵심. component buildup 패턴 강화.
- **D4-A 적용 강 신호**: Slice 12 종결 시 `kpi_matrix.md` §6에 신규 슬라이스 유형 **"component buildup smoke +25~35"** 추가 검토.

---

## §3. 신규 자산

### 신규/수정 모듈
| 파일                                                | 변경                                                    |
| --------------------------------------------------- | ------------------------------------------------------- |
| `portfolio/services/scoring/__init__.py`            | `resolve_category` + `format_scores_for_prompt` + `PRESET_ID_TO_CATEGORY` 추가 |
| `portfolio/services/coach/e3_service.py`            | keyword-only `preset_id`, `metrics` 추가 (후방 호환, IDENTICAL 보장) |

### 신규 산출물
| 파일                                                       | 역할                                |
| ---------------------------------------------------------- | ----------------------------------- |
| `tests/scoring/fixtures/*.json` (15건)                      | 5 카테고리 × 3 case (normal/edge/gate) |
| `tests/scoring/conftest.py`                                 | `load_fixture` fixture loader        |
| `tests/scoring/test_resolve_category.py` (18 tests)          | helper 검증                          |
| `tests/scoring/test_e3_scoring_integration.py` (2 tests)     | e3_service 시그니처 + KeyError 검증 |
| `tests/scoring/test_slice12_smoke.py` (7 tests)              | smoke 결과 자동 검증                |
| `scripts/slice12_part3_smoke.py`                            | 15 LLM 매트릭스 실행 스크립트        |
| `docs/portfolio/coach/slice12/part3_smoke_results.json`     | 15 case 결과 dump                   |
| `docs/portfolio/coach/slice12/part3_smoke_dump.md`          | 15 case 가독성 dump                 |
| `docs/portfolio/coach/slice12/part3_smoke_analysis.md`      | gate 분석 + commentary 인상         |

### 갱신 테스트
- `tests/coach/test_coach_services.py::test_six_coach_services_signature_consistency` — e3 keyword-only 추가 파라미터 허용 (Part 3 통합 반영)

---

## §4. 동작 검증 핵심

### Schema fitting 15/15 (Slice 12 Step 0a #58 production 검증)
- Slice 11 Part 4 매트릭스 1/24 FAIL → Slice 12 Step 0a `parse_json_response` Tier 3 도입
- Part 3 매트릭스에서 **100% PASS** 재확인 — #58 close production-grade 효과 입증

### Gate 발동 정확성
- 의도된 gate 4건 (income×2 + factor low_vol×2) 모두 발동 정상
- 빈 dict 3건 (value/growth/special_edge)도 자연스러운 score=0 (gate 없지만 가중합 0)
- LLM commentary는 score=0 케이스에서도 자연어 응답 정상 생성

### 후방 호환성 (IDENTICAL 보장)
- e3_service.run_e3_coach signature: `(input_data, provider, client, max_tokens, *, preset_id=None, metrics=None)`
- 기존 호출자(테스트·view)는 preset_id/metrics 미전달 → 기존 prompt 그대로 → hash 동일
- IDENTICAL 7/7 PASS 재확인

---

## §5. Scope 격리 (D1-B 확인)

| 항목                       | 변화                                              |
| -------------------------- | ------------------------------------------------- |
| E1/E2/E5/E6 호출자 통합    | 변경 없음 (Slice 13+ 분산)                       |
| action_items prompt (#59 E5) | 변경 없음 (Slice 13 Step 0 multi-debt mini 예정) |
| analysis_engine            | 변경 없음                                         |
| 12 preset / PresetSpec.gate | 변경 없음 (Part 2 동결)                          |

---

## §6. 부채 변화

| ID  | 상태            | 비고                                              |
| --- | --------------- | ------------------------------------------------- |
| #51 | 유지            | Slice 13 Step 0 1순위 (output_token multivariate) |
| #59 E5 | 유지 (D3-B 격리) | Slice 13 Step 0 multi-debt mini 두 번째 사례 #51과 묶음 |
| #57 | (강 후보)       | parametrize-heavy 패턴 누적 (Part 1 +25 / Part 2 +36 / Part 3 +27) — D4-A 적용 강 신호 |
| **#60 (후보)** | **신규**   | gate-aware prompt (gate 발동 시 LLM이 더 명시적으로 임계 미충족 설명) PS 1.0 |

close 0 / 신규 1 후보 (#60) / 유지 2. net +1 (후보 등록만, Slice 13 결정).

---

## §7. Slice 12 누적

| Part   | commit         | 회귀          | 비용     | 결과                                          |
| ------ | -------------- | ------------- | -------- | --------------------------------------------- |
| Step 0 | `f013c48`      | 571 → 580 (+9) | $0.0554  | multi-debt mini (#58/#41/#59 E3 close)        |
| Part 1 | `74fd49b`      | 580 → 605 (+25) | $0     | scoring base + 5 adapter 스켈레톤             |
| Part 2 | `88f6274`      | 605 → 641 (+36) | $0     | 5 ScoringEngine 풀 + PresetSpec + gate        |
| Part 3 | (다음 commit)  | 641 → 668 (+27) | $0.0991 | E3 통합 + 15 smoke + #58 production 검증    |

전체 누적: 571 → 668 (+97), $0.1545 (slice cap 15.45%, 마진 84.55%).
전체 임계 누적: $2.7989 / $4.00 (마진 30.0%).
LLM 호출: 19 / 50 (마진 31).

---

## §8. Part 4 진입 준비

| 항목             | 값                                                       |
| ---------------- | -------------------------------------------------------- |
| Part 4 작업      | manual eval D1-D + D2-A blind (15 commentary 평가)       |
| 예상 시간        | ~2h                                                      |
| 예상 LLM         | 0 콜                                                     |
| 예상 비용        | $0                                                       |
| Part 3 자산      | 15 case commentary (5 카테고리 × 3 type)                 |
| 진입 자산        | `scripts/manual_eval_shuffle.py` (seed=42 재활용)        |
| 글쓰기 가설      | 7/7 검증 또는 8/8 정착 (Part 4 결정)                     |

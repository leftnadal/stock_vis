# Slice 7 Part 3 Step 8 Summary (Part 4 입력 가이드)

- 총 entries: 28
- 매트릭스 raw: `docs/portfolio/coach/slice7/step8_2way_e4_conversation_raw.json`
- scored stub: `docs/portfolio/coach/slice7/step8_2way_e4_conversation_scored.json`

## Part 4 manual eval 작업 순서

1. `prepare_manual_eval_v7.py` 실행 → eval_form_v7.md + eval_key_v7.json (seed=42)
2. 병진 rubric 기반 평가 (rubric §C.6 분포 폭 KPI 자동 보고)
3. `score_step9_v7.py` 실행 → winner + 글쓰기 가설 6/6 + 외삽 검증 + #26 자연 close 판정

## DIMENSION_LOOKUP entry 추가 (Part 4 진입 시)

`scripts/validation/score_step8.py` DIMENSION_LOOKUP에 `e4_conversation` 등록 필요.
상세: `docs/portfolio/coach/slice7/step3_dimension_lookup_decision.md` §2.2

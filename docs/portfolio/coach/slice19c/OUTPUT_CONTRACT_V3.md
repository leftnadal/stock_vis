# 산출 계약 v3 (SLICE19C) — 배치 엔진 v2

> v2(OUTPUT_CONTRACT_V2, SLICE19B) + 다이얼·손잡이 스냅·집중도 사실·레인 구분·확장 근거.
> **소비처 0**(Slice 20 미착수) → 의미 변경 안전(additive). 1차 소스 = `advisory_engine.recommend`.

## 진입점
- `recommend(user) -> dict` : **순수 계산**(부작용 없음). 아래 계약 반환.
- `run_advisory(user) -> dict` : 스냅샷 upsert(이중 기록) + `recommend` + `AdvisoryRun` 기록 후 산출 반환.

## 반환 구조

```jsonc
{
  "mode": "BUY" | "DEFEND",
  "summary": {
    // --- v2 승계 ---
    "progress_gap":   { "return_pct", "gap_pct", "cost_krw", "value_krw", "by_currency", "cost_labels" },
    "allocation_gap": { "cash_krw", "holdings_value_krw", "idle_ratio", "by_currency" },
    "goal_target_return_pct": Decimal | null,
    "numeraire": "KRW",
    "cost_basis_note": "…(취득원가 근사 여부 사실)",
    "fx_context": { "available", "spot", "percentile", "sample_n", "span", "note" },  // 예측 아님

    // --- v3 신설 ---
    "dial": {
      "dd":  Decimal,            // flow 조정 드로다운(0~1). 가격·환율 효과만
      "a":   Decimal,            // dd + A%p + G%p·𝟙(신고점)
      "buffer": Decimal,         // max(10% − a, 3%). 바닥 3% 불가침
      "is_new_high": bool,       // 신고점 국면(G 점등 조건)
      "headroom_frac": Decimal,  // 유휴현금비중 − 버퍼 (0 클램프)
      "deployable_krw_total": Decimal,
      "frozen": bool,            // 가격 신선도 밖 → dd 동결 여부
      "window_days": int,        // 고점 관측 창(콜드 스타트 정직 표기)
      "by_currency": { "<CUR>": { "cash_krw", "buffer_share_krw", "deployable_krw", "headroom_ratio" } }
    },
    "knobs": { "A", "G", "w", "L", "E" },       // 손잡이 5종 스냅(사후분석)
    "max_concentration": { "symbol", "currency", "weight" } | null,  // 사실 항상(L 무관)
    "notes": [ "…자동 장치·손잡이 적용 사실…" ]   // flow 제외/dd 동결/바닥 클램프/손잡이
  },
  "recommendations": [
    {
      "action": "BUY" | "HOLD" | "TRIM",
      "symbol": str,
      "currency": str,
      "score": Decimal | null,      // BUY=배치 우선순위 점수(기대수익 아님), HOLD/TRIM=null
      "lane": "core" | "exploration",
      "rationale": str              // 레인·손잡이 근거 문구
    }
  ],
  "disclaimer": "…예측 아님…"
}
```

## 계약 불변식
- **신뢰도 지배**: 코어 BUY 점수는 `(1−w)(0.60·신뢰도+0.25·진입가+0.15·통화여력)+w·분산`, w≤0.20 → 신뢰도 가중 0.48 최대.
- **탐험 레인**: `lane="exploration"`는 젊은 후보(관측<30일)·신뢰도 성분 없음(무보정)·E>0에서만.
- **사실 보고**: `max_concentration`은 L·mode 무관 항상. `notes`에 자동 장치·손잡이 적용.
- **버퍼 바닥 3%**: `dial.buffer >= 0.03` 항상.

## AdvisoryRun 기록 (사후분석 토대)
`run_advisory`가 실행마다 1행: `snapshot`(FK)·`output`(위 계약 JSON)·`knobs_snapshot`(손잡이 5종 + dd/buffer/deployable 파생). 19d 재보정이 이 라벨을 축적 소비.

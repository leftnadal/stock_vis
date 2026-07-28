# 산출 계약 v2 — 목표-대비 권유 엔진 (KRW 기준, SLICE19B)

> `advisory_engine.recommend(user)` 반환 형태. Slice 20이 소비. 19a v1 대비 **KRW 기준 + FX 맥락 factor + 취득원가 출처 라벨** 추가. "예측 아님" 정직성 문구 유지.

## 반환 구조

```python
{
  "mode": "BUY" | "DEFEND",
  "summary": {
    "progress_gap": {
      "return_pct": Decimal,        # KRW 기준 포트폴리오 미실현 수익률
      "gap_pct": Decimal,           # return_pct − 목표수익률 (음수=목표 미달)
      "cost_krw": Decimal,          # KRW 환산 총 취득원가
      "value_krw": Decimal,         # KRW 환산 총 평가액
      "by_currency": {              # 통화별 소계(참고)
        "USD": {"cost_krw", "value_krw"}, "KRW": {...}
      },
      "cost_labels": {              # 취득원가 출처 분포(정직성)
        "exact": n, "approx_first_buy": m, "approx_low_confidence": k, "native_krw": j
      }
    },
    "allocation_gap": {
      "cash_krw": Decimal,          # KRW 환산 총 현금
      "holdings_value_krw": Decimal,
      "idle_ratio": Decimal,        # 유휴현금 비중(KRW 통합 정본)
      "by_currency": {"USD": {"cash_krw","holdings_value_krw"}, "KRW": {...}}
    },
    "goal_target_return_pct": Decimal | None,
    "numeraire": "KRW",
    "cost_basis_note": str,         # "KRW 원가 N건은 매수일/근사 환율 기준(정본 아님)..." 
    "fx_context": {                 # 역사적 백분위 (사실·맥락, 예측 아님)
      "available": bool,
      "pair": "USDKRW", "spot": Decimal,
      "percentile": float,          # 현재 spot의 시계열 백분위
      "sample_n": int, "span": {"from": date, "to": date},
      "note": "현재 USDKRW ...는 ...~... 대비 P백분위 (사실·맥락, 예측 아님)"
    }
  },
  "recommendations": [
    {
      "action": "BUY" | "HOLD" | "TRIM",
      "symbol": str, "currency": "USD" | "KRW",
      "score": float | None,        # BUY=RelationConfidence, else None
      "rationale": str              # "...신뢰도/여력 기반(예측 아님)" / 집중도 / 보유 유지
    }
  ],
  "disclaimer": "19a는 수익 예측기가 아닙니다 — ...forward 예측이 아닙니다."
}
```

## v1 → v2 변경 (의도된 의미 변경)
- 진행/배치 갭: **통화별 사일로 dict → KRW 통합 정본** (통화별은 `by_currency`로 참고 유지).
- 신규: `numeraire`, `cost_basis_note`, `fx_context`, `cost_labels`.
- 랭킹/모드: KRW 통합 수치 기반. **FX factor는 표시용 맥락 — 가중치로 넣지 않음(19c 소관).**

## 정직성 장치 (모두 "예측 아님")
- `cost_labels`/`cost_basis_note`: KRW 취득원가 근사 여부를 사실로 표시.
- `fx_context`: 환율 역사적 위치를 사실로 표시(방향 베팅 아님).
- `disclaimer`: 예측기 아님 명시.

## 소비처 (STEP 0 실측)
- 현재 소비처 **0**(Slice 20 미착수) → 의미 변경 전파 안전. Slice 20이 첫 소비처.

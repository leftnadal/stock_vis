# Market Pulse v2 — Celery Tasks 카탈로그 (10 tasks)

## Domain tasks

### `marketpulse.tasks.news.mp_fetch_news_hourly` — 매시 :05
FMP General + FMP Stock (MAG7) + Marketaux → 6 카테고리 분류 + URL hash dedup. CB: `fmp_news`, `marketaux`.

### `marketpulse.tasks.breadth.mp_calc_breadth_5min` — 평일 09:30~16:30 매 5분
SP500Constituent 503 + DailyPrice → advance/decline + 52w high/low + AD-line cumulative.

### `marketpulse.tasks.sector_flow.mp_calc_sector_5min` — 평일 09:30~16:30 매 5분
11 SECTOR ETF + SPY benchmark → S02~S06, long-format 11 row/cycle.

### `marketpulse.tasks.concentration.mp_calc_concentration_daily` — 평일 17:15
FMP `/stable/etf/holdings?symbol=SPY` → top5/top10/HHI. CB: `fmp_etf`.

### `marketpulse.tasks.regime.mp_calc_regime_15min` — 매 15분
14 지표 → 5단계 + 2일 히스테리시스. coverage<0.6 → INSUFFICIENT_DATA.

### `marketpulse.tasks.anomaly.mp_detect_anomaly_5min` — 평일 09:30~16:30 매 5분
4 Core 룰 (R02/R04/R09/R12). ANOMALY ≥2 / HYBRID =1 / CALM =0.

### `marketpulse.tasks.briefing.mp_generate_brief_daily` — 평일 NY 17:15 (KST 06:15)
Gemini 2.5 Flash 동기 호출 (Bug #8). CB: `gemini`.

## Ops tasks

### `marketpulse.tasks.finalize.mp_finalize_daily` — 평일 NY 16:30 (KST 05:30)
4 스냅샷 is_finalized=True + cache invalidate.

### `marketpulse.tasks.finalize.mp_purge_news_daily` — 매일 NY 14:00 (KST 03:00)
90일 초과 + is_exposed=False 삭제.

### `marketpulse.tasks.finalize.mp_purge_news_view_log_daily` — 매일 NY 14:05 (KST 03:05)
48h+ NewsViewLog 정리.

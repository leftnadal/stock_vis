# EOD Dashboard - 시그널 기반 종목 발굴

## 개요

매일 장 마감 후 S&P 500 전 종목(~503개)을 분석하여 14개 시그널을 감지하고, JSON Baking으로 프론트엔드에 직접 서빙하는 대시보드. 메인 페이지(`/app/page.tsx`)로 동작.

## 아키텍처

```
DailyPrice(250일) → Calculator(벡터연산) → Tagger → NewsEnricher → JSONBaker → Next.js
                                                                       ↓
                                                              public/static/signals/
```

**서빙**: Next.js가 `public/static/signals/dashboard.json`을 직접 fetch. Django API는 admin/debug 전용.

## 핵심 파일

| 파일 | 역할 |
|------|------|
| `stocks/services/eod_signal_calculator.py` | 14개 시그널 벡터 연산 |
| `stocks/services/eod_regime_calculator.py` | Z-score 기반 VIX 레짐 판별 (3단계: normal/elevated/high_vol) |
| `stocks/services/eod_signal_tagger.py` | 태깅 + primary/sub_tags |
| `stocks/services/eod_news_enricher.py` | 5단계 뉴스 매칭 + sentiment 시간적 인과성 보정 |
| `stocks/services/eod_json_baker.py` | Atomic Write → static/ |
| `stocks/services/eod_pipeline.py` | 파이프라인 오케스트레이터 |
| `stocks/views_eod.py` | admin API (3개) |
| `stocks/tasks.py` | run_eod_pipeline, backfill_signal_accuracy |
| `stocks/management/commands/pipeline_status.py` | CLI |

## 14개 시그널

**Momentum**: P1(연속상승/하락), P2(수익률상위), P3(갭감지), P4(장대봉)
**Breakout**: P5(52주 신고가 근접)
**Reversal**: P7(저가반등)
**Volume**: V1(거래량폭발), PV1(가격-거래량효율), PV2(매집의심)
**Technical**: MA1(골든/데드크로스), T1(RSI 과매도/과매수)
**Relation**: S1(섹터상대강도), S2(섹터소외주), S4(폭락장생존자)

VIX > 25 시 P2/P3/P4/P7/V1 임계값 상향.

## DB 모델

- `EODSignal`: 일별 종목 시그널 (unique: stock+date)
- `SignalAccuracy`: 시그널 수익률 추적 (unique: stock+signal_date+signal_tag)
- `EODDashboardSnapshot`: Baked JSON 백업 (unique: date)
- `PipelineLog`: 파이프라인 로그 (unique: run_id)
- `StockNews`: 뉴스 기사 (News Enricher용)

## JSON 출력 구조

```
frontend/public/static/signals/
├── dashboard.json          # 메인 대시보드
├── meta.json               # 파이프라인 메타
├── cards/{category}.json   # 카테고리별 전체 종목
└── stocks/{SYMBOL}.json    # 종목별 60일 히스토리
```

## API (admin/debug 전용)

- `GET /api/v1/stocks/eod/dashboard/?date=` → DB snapshot
- `GET /api/v1/stocks/eod/signal/<id>/?date=` → 시그널 상세
- `GET /api/v1/stocks/eod/pipeline/status/` → 파이프라인 로그

## Celery Beat

- `run_eod_pipeline`: 18:30 ET Mon-Fri (EOD 동기화 이후)
- `backfill_signal_accuracy`: 19:00 ET Mon-Fri

## CLI

```bash
python manage.py pipeline_status           # 최근 7일 로그
python manage.py pipeline_status --run     # 즉시 실행
python manage.py pipeline_status --quality # 품질 메트릭
```

## 코딩 규칙

1. **벡터 연산만**: for-loop/iterrows/apply(custom) 금지
2. **멱등성**: bulk_create(update_conflicts=True), unique_together
3. **Atomic Write**: 3단계 디렉토리 swap (실패 시 이전 데이터 유지)
4. **품질 체크**: 종목수 전일 ±10%, sector null > 5%, vol zero > 3% → degrade mode

## 프론트엔드 컴포넌트

`frontend/components/eod/`:
DataFreshnessBadge, MarketSummaryBar, VixChip, SignalFilterTabs, SignalCardGrid,
SignalCard, SignalDetailSheet, StockRow, MiniSparkline, ConfidenceBadge,
NewsContextBadge, EODSkeleton

## 테스트

```
tests/unit/stocks/test_eod_signal_calculator.py  # 시그널 단위 + VIX 레짐
tests/unit/stocks/test_eod_regime_calculator.py  # DynamicRegimeCalculator Z-score + 캐싱 + 절대값 하한선
tests/unit/stocks/test_eod_news_enricher_sentiment.py  # sentiment 시간적 인과성 보정
tests/unit/stocks/test_eod_pipeline.py           # 통합 + 멱등성
tests/unit/stocks/test_eod_ingest_quality.py     # 품질 체크
tests/unit/stocks/test_eod_api.py               # API 엔드포인트
```

> 상세: `docs/features/eod-dashboard/README.md`

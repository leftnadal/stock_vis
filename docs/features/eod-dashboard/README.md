# EOD Dashboard - 시그널 기반 종목 발굴 대시보드

## 개요

매일 장 마감 후 S&P 500 전 종목을 분석하여 14개 시그널을 감지하고, JSON 파일로 bake하여 프론트엔드에서 직접 서빙하는 대시보드.

**핵심 철학**: 시그널이 주(主), 뉴스가 종(從) / 숫자가 아니라 스토리 / JSON Baking → API 비용 0원

## 아키텍처

```
DailyPrice (250일) → EODSignalCalculator (벡터 연산)
                         ↓
                    EODSignalTagger (태깅 + 카드 빌더)
                         ↓
                    EODNewsEnricher (5단계 계층 매칭)
                         ↓
                    EODJSONBaker (Atomic Write → public/static/signals/)
                         ↓
                    Next.js (fetch('/static/signals/dashboard.json'))
```

### 파이프라인 단계 (8+1 Stage)

| Stage | 역할 | 핵심 |
|-------|------|------|
| 1. Ingest | DailyPrice에서 S&P 500 데이터 로드 | 품질 체크 (degrade mode) |
| 2. Filter | volume/dollar_volume 필터링 | vol >= 100K, dollar >= $500K |
| 3. Calculate | 14개 시그널 벡터 연산 | VIX 레짐 분기 |
| 4. Tag | primary/sub_tags 결정 | priority: relation > volume > momentum > ... |
| 5. News Enrich | 5단계 계층적 뉴스 매칭 | confidence 차등화 |
| 6. DB Upsert | bulk_create ON CONFLICT DO UPDATE | 멱등성 보장 |
| 7. JSON Bake | Atomic directory swap | 실패 시 이전 데이터 유지 |
| 8. Accuracy Backfill | 1d/5d/20d 수익률 소급 | SPY excess 포함 |
| 9. Health Check | 최소 시그널 수 확인 | - |

## 14개 시그널

| ID | 시그널명 | 카테고리 | 핵심 로직 |
|----|---------|---------|----------|
| P1 | 연속 상승/하락 | momentum | N일 연속 close > prev_close (3일+) |
| P2 | 수익률 상위 | momentum | \|change_pct\| > 5% (VIX>25: 7%) |
| P3 | 갭 감지 | momentum | open vs prev_close 갭 3%+ (VIX>25: 5%) |
| P4 | 장대양봉/음봉 | momentum | body_pct > 3% AND body > 60% range |
| P5 | 52주 신고가 근접 | breakout | close >= 52w_high × 0.95 |
| P7 | 저가 반등 | reversal | bounce 3%+ AND close > open |
| V1 | 거래량 폭발 | volume | vol/avg_20d >= 2.0 (VIX>25: 3.0) |
| PV1 | 가격-거래량 효율성 | volume | change > 2% AND vol_ratio < 1.0 |
| PV2 | 매집 의심 | volume | vol_ratio > 2.0 AND \|change\| < 1% |
| MA1 | 골든/데드크로스 | technical | SMA50 × SMA200 교차 |
| T1 | RSI 과매도/과매수 | technical | RSI < 30 or RSI > 70 |
| S1 | 섹터 상대 강도 | relation | 섹터 평균 대비 +3%p |
| S2 | 섹터 소외주 | relation | 섹터 상승일 대비 -3%p |
| S4 | 폭락장 생존자 | relation | SPY -2%+ 하락일에 보합/상승 |

## DB 모델

| 모델 | 테이블 | 역할 |
|------|--------|------|
| `EODSignal` | `stocks_eod_signal` | 일별 종목 시그널 (핵심) |
| `SignalAccuracy` | `stocks_signal_accuracy` | 시그널 정확도 추적 |
| `EODDashboardSnapshot` | `stocks_eod_dashboard_snapshot` | Baked JSON 백업 |
| `PipelineLog` | `stocks_pipeline_log` | 파이프라인 실행 로그 |
| `StockNews` | `stocks_stock_news` | 뉴스 기사 저장 |

### 멱등성

- `EODSignal`: unique_together('stock', 'date') → bulk_create(update_conflicts=True)
- `SignalAccuracy`: unique_together('stock', 'signal_date', 'signal_tag')
- `EODDashboardSnapshot`: unique date
- `PipelineLog`: unique run_id

## 파일 구조

### Backend
```
stocks/
├── models.py                          # EODSignal, SignalAccuracy, etc.
├── views_eod.py                       # admin/debug API endpoints
├── tasks.py                           # run_eod_pipeline, backfill_signal_accuracy
├── management/commands/
│   └── pipeline_status.py             # CLI: status, run, quality
└── services/
    ├── eod_signal_calculator.py        # 14개 시그널 벡터 연산
    ├── eod_signal_tagger.py            # 태깅 + 카드 빌더
    ├── eod_news_enricher.py            # 뉴스 계층 매칭
    ├── eod_json_baker.py               # JSON Bake + Atomic swap
    └── eod_pipeline.py                 # 파이프라인 오케스트레이터
```

### Frontend
```
frontend/
├── app/page.tsx                        # EOD Dashboard (메인 페이지)
├── types/eod.ts                        # TypeScript 타입
├── services/eodService.ts              # Static file fetch
├── hooks/useEODDashboard.ts            # TanStack Query hooks
├── components/eod/
│   ├── DataFreshnessBadge.tsx
│   ├── MarketSummaryBar.tsx
│   ├── SignalFilterTabs.tsx
│   ├── SignalCardGrid.tsx
│   ├── SignalCard.tsx
│   ├── SignalDetailSheet.tsx
│   ├── StockRow.tsx
│   ├── MiniSparkline.tsx
│   ├── ConfidenceBadge.tsx
│   ├── NewsContextBadge.tsx
│   └── EODSkeleton.tsx
└── public/static/signals/              # Baked JSON (파이프라인 출력)
    ├── dashboard.json
    ├── meta.json
    ├── cards/{category}.json
    └── stocks/{SYMBOL}.json
```

## API Endpoints (admin/debug 전용)

프론트엔드는 static 파일을 직접 읽음. 아래는 admin/debug fallback:

| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/v1/stocks/eod/dashboard/` | DB snapshot 조회 |
| GET | `/api/v1/stocks/eod/signal/<id>/` | 특정 시그널 상세 |
| GET | `/api/v1/stocks/eod/pipeline/status/` | 파이프라인 로그 |

## JSON 서빙 구조

```
Next.js fetch('/static/signals/dashboard.json')
  → public/static/signals/dashboard.json (Baked JSON)
  → 매일 18:30 ET Celery Beat → EODPipeline → Atomic swap
```

### Atomic Write (3단계 디렉토리 Swap)
```
1. signals_tmp/ 에 새 파일 생성
2. signals/ → signals_old/ (기존 백업)
3. signals_tmp/ → signals/ (새 데이터 승격)
4. signals_old/ 삭제
```
실패 시 signals_old/ → signals/ 복구.

## Celery Beat 스케줄

| 태스크 | 스케줄 | 설명 |
|--------|--------|------|
| `run_eod_pipeline` | 매일 18:30 ET, Mon-Fri | 전체 파이프라인 |
| `backfill_signal_accuracy` | 매일 19:00 ET, Mon-Fri | 수익률 소급 계산 |

## CLI 사용법

```bash
# 최근 7일 로그
python manage.py pipeline_status

# 특정 날짜 즉시 실행
python manage.py pipeline_status --run --date 2026-02-25

# 품질 메트릭 상세
python manage.py pipeline_status --quality
```

## 카테고리 색상

| 카테고리 | 색상 | HEX |
|---------|------|-----|
| momentum | orange | #F0883E |
| volume | blue | #58A6FF |
| breakout | green | #3FB950 |
| reversal | purple | #A371F7 |
| relation | purple | #A371F7 |
| technical | gray | #8B949E |

## 뉴스 Confidence 레벨

| 우선순위 | match_type | confidence | UI 표현 |
|---------|-----------|------------|---------|
| 1 | symbol_today | high | 강조 표시 |
| 2 | symbol_7d | medium | 보통 + "N일 전" |
| 3 | symbol_30d | low | 흐리게 + "N일 전" |
| 4 | industry_7d | context | "배경:" + 이탤릭 |
| 5 | profile | info | "기업 정보" 톤 |

## Phase 로드맵

| Phase | 대상 | 상태 |
|-------|------|------|
| Phase 1 | S&P 500 (503종목) | **구현 완료** |
| Phase 1.5 | 전체 US 시장 (~6,000종목) | 계획 |
| Phase 2 | 시그널 정확도 기반 자동 조정 | 계획 |

# Market Movers 5개 지표 시스템

## 지표 설명

| 지표 | 계산 방식 | 해석 | Phase |
|------|----------|------|-------|
| **RVOL** | 당일 거래량 / 20일 평균 | 2.0+: 비정상적 관심도, 1.5~2.0: 높은 관심, <1.0: 평균 이하 | Phase 1 |
| **Trend Strength** | (종가-시가) / (고가-저가) | +0.7+: 강한 상승, -0.7-: 강한 하락, 0 전후: 횡보 | Phase 1 |
| **Sector Alpha** | 종목 수익률 - 섹터 ETF 수익률 | 양수: 섹터 평균 초과, 음수: 섹터 평균 미달 | Phase 2 |
| **ETF Sync Rate** | 피어슨 상관계수(종목, 섹터 ETF) | 0.8+: 강한 동조, 0.5~0.8: 중간, <0.5: 독립적 | Phase 2 |
| **Volatility %ile** | 당일 변동성의 백분위 (0-100) | 90+: 매우 높음, 50 전후: 평균, <10: 낮음 | Phase 2 |

## 아키텍처

```
FMP API (/stable/*)
    │
    ├─ biggest-gainers ────┐
    ├─ biggest-losers ─────┤
    └─ most-actives ───────┤
                           │
                           ▼
              MarketMoversSync (data_sync.py)
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
    FMP Quote      FMP Historical      FMP Profile
    (volume)         (20일 OHLC)        (섹터 정보)
        │                  │                  │
        └──────────────────┴──────────────────┘
                           │
                           ▼
              IndicatorCalculator (순수 Python)
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
    Phase 1 지표      Phase 2 지표      Display 포맷
    (RVOL, Trend)   (Alpha, Sync, Vol)  (2.5x, ▲0.83 등)
                           │
                           ▼
                    PostgreSQL (MarketMover 모델)
                           │
                           ▼
                  REST API (/api/v1/serverless/movers)
                           │
                           ▼
                Frontend (MoverCard 컴포넌트)
```

## Celery Beat 스케줄 (Market Movers 관련)

```python
# config/settings.py
'sync-market-movers': {
    'task': 'serverless.tasks.sync_daily_market_movers',
    'schedule': crontab(hour=7, minute=30),  # 매일 07:30 EST
}

# config/celery.py
'keyword-generation-pipeline': {
    'task': 'serverless.tasks.keyword_generation_pipeline',
    'schedule': crontab(hour=8, minute=0),  # 매일 08:00 EST (동기화 30분 후)
    'kwargs': {'mover_type': 'gainers'},
}
```

> 전체 Celery Beat 스케줄은 `config/settings.py`와 `config/celery.py` 두 곳에 분산 정의됨

## Corporate Action 감지 시스템

가격 변동 ±50% 이상 시 주식분할/역분할/배당을 자동 감지 (yfinance 기반)

| 컴포넌트 | 역할 |
|---------|------|
| **CorporateActionService** | yfinance로 Corporate Action 감지 |
| **CorporateAction 모델** | 이벤트 이력 저장 |
| **MarketMover 필드** | has_corporate_action, corporate_action_type, corporate_action_display |

**감지 조건**:
- **주식분할**: ratio < 1 (예: 0.5 → 2:1 분할)
- **역분할**: ratio > 1 (예: 28.0 → 1:28 역분할)
- **특별배당**: 배당 수익률 5% 이상
- **LOOKBACK_DAYS**: 최근 7일 이내 이벤트만 체크

**테스트**: `tests/serverless/test_corporate_action_service.py` (12개), `tests/serverless/test_indicators.py` (21개)

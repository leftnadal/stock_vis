# Graph Analysis (그래프 온톨로지) - Phase 1

## 개요

주식 간 가격 변동 상관관계를 그래프 네트워크로 분석하는 시스템. 사용자 Watchlist의 종목들을 노드로, 상관계수를 엣지로 표현하여 실시간 모니터링.

## 핵심 개념

| 개념 | 설명 | 기술 |
|------|------|------|
| **Node** | Watchlist 내 각 종목 | Stock 모델 |
| **Edge** | 두 종목 간 상관계수 | CorrelationEdge 모델 |
| **Correlation** | 3개월 가격 변동 상관성 | Pearson correlation (pandas) |
| **Anomaly** | ±0.2 이상 상관계수 변화 | AnomalyDetector |
| **Graph** | NetworkX 네트워크 그래프 | NetworkX library |

## 계산 파라미터

```python
DEFAULT_PERIOD_DAYS = 90  # 3개월 rolling window
MIN_DATA_POINTS = 20      # 최소 20일 데이터 필요
ANOMALY_THRESHOLD = 0.2   # ±0.2 변화 감지
MAX_ALERTS_PER_DAY = 5    # 일일 최대 알림 5개
COOLDOWN_HOURS = 24       # 동일 페어 24시간 쿨다운
```

## 데이터베이스 모델

**CorrelationMatrix** - 전체 상관계수 행렬
```python
{ watchlist: FK, date: DateField, matrix_data: JSONField, stock_count: Int, calculation_period: Int(90) }
```

**CorrelationEdge** - 개별 상관관계
```python
{ watchlist: FK, stock_a: FK, stock_b: FK, date: Date, correlation: Decimal(-1~1),
  previous_correlation: Decimal, correlation_change: Decimal, is_anomaly: Bool }
```

**CorrelationAnomaly** - 이상 패턴
```python
{ watchlist: FK, edge: FK, date: Date, anomaly_type: Choice('divergence','convergence','reversal'),
  previous_correlation: Decimal, current_correlation: Decimal, change_magnitude: Decimal,
  alerted: Bool, dismissed: Bool }
```

**PriceCache** - 가격 데이터 캐싱
```python
{ stock: FK, date: Date, prices: JSONField, period_days: Int(90) }
```

**GraphMetadata** - 계산 메타데이터
```python
{ watchlist: FK, date: Date, stock_count: Int, edge_count: Int, anomaly_count: Int,
  calculation_time_ms: Int, status: Choice('pending','processing','completed','failed') }
```

## Services

**CorrelationCalculator** (`graph_analysis/services/correlation_calculator.py`)
- 3개월 rolling correlation 계산
- NetworkX 그래프 생성
- 평균 계산 시간: < 100ms (50개 종목)

**AnomalyDetector** (`graph_analysis/services/anomaly_detector.py`)
- Divergence: 상관계수 약화
- Convergence: 상관계수 강화
- Reversal: 부호 변경

## 상관계수 해석

| 값 | 강도 | 의미 |
|----|------|------|
| 0.8 ~ 1.0 | Very Strong | 거의 동일한 움직임 |
| 0.6 ~ 0.8 | Strong | 강한 동조 |
| 0.4 ~ 0.6 | Moderate | 중간 수준 |
| 0.2 ~ 0.4 | Weak | 약한 관련성 |
| -0.2 ~ 0.2 | Very Weak | 관련성 없음 |
| -1.0 ~ -0.2 | Negative | 역관계 |

## 외부 API: EODHD Historical Data

- `api_request/eodhd_client.py`
- Bulk EOD API: 5,000+ US 종목 일괄 다운로드
- Cost: $19.99/월 (Basic Plan), No rate limits

## Phase 1 진행 상태

- ✅ Week 1-2: PostgreSQL 스키마 (5개 모델), Django 모델, NetworkX 엔진
- ✅ Week 1-2: Services (CorrelationCalculator, AnomalyDetector)
- ⏳ **urls.py 미구현**: graph_analysis에 URL 패턴 없음
- ⏳ **tasks.py 미생성**: Celery 태스크 파일 없음
- ⏳ Week 3-4: REST API 엔드포인트, Frontend 그래프 시각화 (D3.js)
- ⏳ Week 5-6: 이상 감지 알림, 테스트

## 참고 문서

- `docs/architecture/GRAPH_ONTOLOGY_INFRA_REDESIGN.md`
- `docs/architecture/DATA_INFRASTRUCTURE_ROADMAP_EVALUATION.md`

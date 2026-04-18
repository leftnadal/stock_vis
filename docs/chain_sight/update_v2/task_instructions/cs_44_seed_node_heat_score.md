# CS-4-4: Seed Node heat_score 배치

> **작업 번호**: CS-4-4
> **로드맵 버전**: v1.4 (신규)
> **목표**: 일간 heat_score 배치로 섹터별 시드 노드(탐색 시작점) 추천 가능
> **예상 소요**: 2~3일
> **선행 조건**: CS-3-3 (GDS 알고리즘 배치), CS-2-2 (CoMentionEdge), CS-2-4 (RelationConfidence)
> **산출물**:
> - `chainsight/tasks/seed_tasks.py` (calculate_heat_scores)
> - Neo4j :Stock 노드에 heat_score 속성 + 4개 signal 상세 속성
> - Celery Beat 등록 (`chainsight-heat-score-daily`)

---

## 배경

**Chain Sight 마켓뷰의 진입 문제**: 사용자가 섹터를 선택하면 단순 market cap 상위 노드만 보여주게 되는데, 이러면 매번 같은 대형주(AAPL, MSFT, NVDA 등)만 반복 노출된다. "지금 탐색할 가치가 있는 노드"는 market cap과 다르다.

**해결 방향**: 시장 시그널 + 관계 변화를 종합한 heat_score로 섹터별 시드 노드를 동적으로 추천한다. 시드 노드는 MarketView(CS-5-5)에서 bounce 애니메이션으로 강조 표시된다.

**Phase 매핑** (PM_DESIGN.md 섹션 6-1):
- Phase A: 시장 시그널 (price, volume) — 본 작업에 포함
- Phase B: 관계 변화 (relation change, news activation) — 본 작업에 포함
- Phase C: Heat Score 종합 — 본 작업의 핵심
- Phase D: 이벤트 전파 모델 (propagation_weight) — **Post-MVP, 본 작업 제외**

---

## 설계 결정

### heat_score 저장 위치: Neo4j :Stock 노드 속성

세 가지 옵션 비교 후 Neo4j 선택:

| 옵션 | 장점 | 단점 | 결정 |
|-----|------|------|------|
| Neo4j :Stock 속성 | 섹터별 top heat 쿼리 바로 가능. GDS centrality와 같은 패턴. | 배치 후 Neo4j 쓰기 작업 | ✅ 채택 |
| chainsight_chain_profile 컬럼 | SQL ORDER BY 간단 | Neo4j 동기화 필요 | ❌ |
| 신규 chainsight_heat_score 테이블 | 명확한 책임 | 테이블 증가, 원칙 4 위배 | ❌ |

### 저장 스키마 (Neo4j :Stock 노드 추가 속성)

```
heat_score: float (0~1, 종합 점수)
price_signal: float (0~1)
volume_signal: float (0~1)
relation_change_signal: float (0~1)
news_activation: float (0~1)
heat_score_updated_at: datetime (배치 실행 시각)
```

heat_score_version 같은 복잡한 필드는 두지 않음 (원칙 4). 가중치 변경 시 전체 재계산.

---

## 계산 로직

### 공식

```
heat_score = w1 × price_signal
           + w2 × volume_signal
           + w3 × relation_change_signal
           + w4 × news_activation

MVP 가중치: w1 = w2 = w3 = w4 = 0.25
```

### 각 Signal 정규화 (0~1 범위)

**1. price_signal — 5일 수익률의 절댓값 percentile rank**

```python
# stocks/DailyPrice에서 전체 종목 5일 수익률 계산
# abs(5d_return)을 전체 종목 중 percentile로 변환 → 0~1

def compute_price_signal(symbol: str, all_prices: pd.DataFrame) -> float:
    """
    all_prices: columns=['symbol', 'date', 'close']
    5일 전 대비 변동률의 절댓값 → percentile rank
    """
    latest = all_prices.groupby('symbol').tail(1)
    five_days_ago = all_prices.groupby('symbol').apply(
        lambda g: g.iloc[-6] if len(g) >= 6 else None
    ).dropna()

    returns = {}
    for sym in latest['symbol'].unique():
        if sym in five_days_ago.index:
            latest_close = latest[latest['symbol'] == sym]['close'].iloc[0]
            past_close = five_days_ago.loc[sym, 'close']
            returns[sym] = abs((latest_close - past_close) / past_close)

    # percentile rank
    series = pd.Series(returns)
    ranks = series.rank(pct=True)  # 0~1
    return float(ranks.get(symbol, 0.0))
```

**2. volume_signal — 당일 거래량 / 20일 평균 거래량 비율**

```python
def compute_volume_signal(symbol: str, all_prices: pd.DataFrame) -> float:
    """
    당일 거래량 / 20일 평균 거래량
    min(ratio / 3, 1)로 클리핑 (3배 이상은 모두 1)
    """
    df = all_prices[all_prices['symbol'] == symbol].tail(20)
    if len(df) < 20:
        return 0.0
    today_volume = df['volume'].iloc[-1]
    avg_volume = df['volume'].mean()
    if avg_volume == 0:
        return 0.0
    ratio = today_volume / avg_volume
    return min(ratio / 3.0, 1.0)
```

**3. relation_change_signal — 최근 7일 내 신규/변경된 RelationConfidence 수**

```python
def compute_relation_change_signal(symbol: str) -> float:
    """
    최근 7일 내에 해당 symbol과 관련된 RelationConfidence가
    새로 생겼거나 relation_status가 변경된 건수.
    min(count / 5, 1)로 클리핑 (5건 이상은 모두 1)
    """
    from chainsight.models import RelationConfidence
    from django.utils import timezone
    from datetime import timedelta
    from django.db.models import Q

    cutoff = timezone.now() - timedelta(days=7)
    count = RelationConfidence.objects.filter(
        Q(symbol_a=symbol) | Q(symbol_b=symbol),
        last_verified_at__gte=cutoff,  # 또는 first_observed_at
    ).count()
    return min(count / 5.0, 1.0)
```

**4. news_activation — 최근 3일 내 CoMention 발생 수**

```python
def compute_news_activation(symbol: str) -> float:
    """
    최근 3일 내에 해당 symbol이 co-mention된 건수.
    min(count / 3, 1)로 클리핑
    """
    from chainsight.models import CoMentionEdge
    from django.utils import timezone
    from datetime import timedelta
    from django.db.models import Q

    cutoff = timezone.now() - timedelta(days=3)
    count = CoMentionEdge.objects.filter(
        Q(symbol_a=symbol) | Q(symbol_b=symbol),
        last_co_mention_date__gte=cutoff,
    ).count()
    return min(count / 3.0, 1.0)
```

---

## 구현

### 파일 구조

```
chainsight/
└── tasks/
    └── seed_tasks.py   ← 신규 생성
```

### 전체 task

```python
# chainsight/tasks/seed_tasks.py

import logging
from datetime import timedelta
from typing import Dict

import pandas as pd
from celery import shared_task
from django.db.models import Q
from django.utils import timezone

from stocks.models import Stock, DailyPrice
from chainsight.models import RelationConfidence, CoMentionEdge
from chainsight.graph.repository import Neo4jGraphRepository
from django.conf import settings

logger = logging.getLogger(__name__)


WEIGHTS = {
    'price': 0.25,
    'volume': 0.25,
    'relation_change': 0.25,
    'news_activation': 0.25,
}


@shared_task(name='chainsight.tasks.seed_tasks.calculate_heat_scores')
def calculate_heat_scores() -> Dict:
    """
    Celery Beat: 매일 07:00.
    모든 :Stock 노드의 heat_score를 계산하여 Neo4j에 저장.

    Returns:
        {'processed': int, 'errors': int, 'updated_at': str}
    """
    start_time = timezone.now()

    # 1) 전체 가격 데이터 로드 (pd.DataFrame)
    price_df = _load_recent_prices(days=25)  # 20일 평균 + 5일 수익률용

    # 2) 전체 symbol 목록
    symbols = list(Stock.objects.values_list('ticker', flat=True))

    # 3) price_signal은 전체 symbol에 대해 percentile 계산 필요
    price_signals = _compute_price_signals_batch(price_df, symbols)

    repo = Neo4jGraphRepository(
        uri=settings.NEO4J_URI,
        user=settings.NEO4J_USER,
        password=settings.NEO4J_PASSWORD,
    )

    processed = 0
    errors = 0

    for symbol in symbols:
        try:
            price_sig = price_signals.get(symbol, 0.0)
            volume_sig = _compute_volume_signal(symbol, price_df)
            relation_sig = _compute_relation_change_signal(symbol)
            news_sig = _compute_news_activation(symbol)

            heat_score = (
                WEIGHTS['price'] * price_sig
                + WEIGHTS['volume'] * volume_sig
                + WEIGHTS['relation_change'] * relation_sig
                + WEIGHTS['news_activation'] * news_sig
            )

            # Neo4j :Stock 노드 속성 업데이트
            repo.run_query(
                """
                MATCH (s:Stock {ticker: $ticker})
                SET s.heat_score = $heat_score,
                    s.price_signal = $price_sig,
                    s.volume_signal = $volume_sig,
                    s.relation_change_signal = $relation_sig,
                    s.news_activation = $news_sig,
                    s.heat_score_updated_at = datetime()
                """,
                {
                    'ticker': symbol,
                    'heat_score': heat_score,
                    'price_sig': price_sig,
                    'volume_sig': volume_sig,
                    'relation_sig': relation_sig,
                    'news_sig': news_sig,
                }
            )
            processed += 1

        except Exception as e:
            logger.error(f"heat_score 계산 실패 {symbol}: {e}")
            errors += 1

    elapsed = (timezone.now() - start_time).total_seconds()
    logger.info(
        f"heat_score 배치 완료: {processed} processed, "
        f"{errors} errors, {elapsed:.1f}s"
    )

    return {
        'processed': processed,
        'errors': errors,
        'updated_at': start_time.isoformat(),
        'elapsed_seconds': elapsed,
    }


# === Helper functions ===

def _load_recent_prices(days: int = 25) -> pd.DataFrame:
    """최근 N일 DailyPrice를 DataFrame으로 로드."""
    cutoff = timezone.now().date() - timedelta(days=days)
    qs = DailyPrice.objects.filter(
        date__gte=cutoff
    ).values('symbol', 'date', 'close', 'volume')
    df = pd.DataFrame.from_records(qs)
    if not df.empty:
        df = df.sort_values(['symbol', 'date'])
    return df


def _compute_price_signals_batch(price_df: pd.DataFrame, symbols: list) -> Dict[str, float]:
    """
    전체 종목의 5일 수익률 절댓값 → percentile rank로 반환.
    percentile이므로 전체 모수에서 한 번에 계산해야 함.
    """
    if price_df.empty:
        return {s: 0.0 for s in symbols}

    returns = {}
    for sym, group in price_df.groupby('symbol'):
        if len(group) < 6:
            continue
        latest_close = group['close'].iloc[-1]
        past_close = group['close'].iloc[-6]
        if past_close > 0:
            returns[sym] = abs((latest_close - past_close) / past_close)

    if not returns:
        return {s: 0.0 for s in symbols}

    series = pd.Series(returns)
    ranks = series.rank(pct=True)
    return {s: float(ranks.get(s, 0.0)) for s in symbols}


def _compute_volume_signal(symbol: str, price_df: pd.DataFrame) -> float:
    """당일 거래량 / 20일 평균 → min(ratio/3, 1)"""
    df = price_df[price_df['symbol'] == symbol].tail(20)
    if len(df) < 20:
        return 0.0
    today_volume = df['volume'].iloc[-1]
    avg_volume = df['volume'].mean()
    if avg_volume == 0:
        return 0.0
    ratio = float(today_volume) / float(avg_volume)
    return min(ratio / 3.0, 1.0)


def _compute_relation_change_signal(symbol: str) -> float:
    """최근 7일 내 관련 RelationConfidence 갱신 수 → min(count/5, 1)"""
    cutoff = timezone.now() - timedelta(days=7)
    count = RelationConfidence.objects.filter(
        Q(symbol_a=symbol) | Q(symbol_b=symbol),
        last_verified_at__gte=cutoff,
    ).count()
    return min(count / 5.0, 1.0)


def _compute_news_activation(symbol: str) -> float:
    """최근 3일 내 CoMention 수 → min(count/3, 1)"""
    cutoff = timezone.now() - timedelta(days=3)
    count = CoMentionEdge.objects.filter(
        Q(symbol_a=symbol) | Q(symbol_b=symbol),
        last_co_mention_date__gte=cutoff.date(),
    ).count()
    return min(count / 3.0, 1.0)
```

### Celery Beat 등록

CS-2-5에서 등록한 9개 스케줄 중 `chainsight-heat-score-daily`를 활성화한다 (CS-2-5 시점에는 주석 처리 또는 no-op 상태였음).

```python
# config/settings.py (또는 config/celery.py)

CELERY_BEAT_SCHEDULE = {
    # ... (기존 8개 스케줄)
    'chainsight-heat-score-daily': {
        'task': 'chainsight.tasks.seed_tasks.calculate_heat_scores',
        'schedule': crontab(hour=7, minute=0),
    },
}
```

### Neo4j 인덱스 추가 여부

로드맵 v1.4 섹션 2.4에 heat_score 인덱스는 정의되지 않음. 원칙 1(문서에 정의되지 않은 기능 구현 금지)에 따라 **본 작업에서 인덱스 추가하지 않음**. 섹터별 top 쿼리는 `stock_sector` 인덱스 + 50개 이하 필터로 충분히 빠름. 필요 시 추후 로드맵 업데이트 후 추가.

---

## API 연계 (CS-4-1, CS-5-5)

### CS-4-1 그래프 탐색 API 활용

```cypher
// 섹터별 top heat_score 노드 3개 (MarketView 시드 노드용)
MATCH (s:Stock {sector: $sector})
WHERE s.heat_score IS NOT NULL
RETURN s
ORDER BY s.heat_score DESC
LIMIT 3
```

### CS-5-5 MarketView 활용

MarketView가 섹터를 선택하면:
1. 해당 섹터 market cap 상위 20개 노드 조회 (기본 뷰)
2. 그중 heat_score 상위 3개 노드를 시드 노드로 지정
3. 프론트엔드에서 bounce 애니메이션 처리

---

## 완료 기준

```
□ chainsight/tasks/seed_tasks.py 생성
□ calculate_heat_scores task 수동 실행 성공 (celery worker 없이 .delay() 또는 직접 호출)
□ Neo4j에서 :Stock 노드 전체 heat_score 속성 확인
     Cypher: MATCH (s:Stock) WHERE s.heat_score IS NOT NULL RETURN count(s)
     → 전체 Stock 노드 수와 유사해야 함
□ heat_score 분포 합리성 확인 (0~1 범위, 평균 0.3~0.5 부근)
□ 상위 10개 heat_score 노드 합리성 확인 (실제 최근 가격 급변 / 뉴스 많은 종목인가?)
□ Celery Beat 스케줄 등록 확인 (celery -A config inspect scheduled)
□ 단위 테스트: 각 signal 함수 (price, volume, relation, news)
```

---

## 주의사항

### 가격 데이터 부족 처리

신규 상장 종목이나 거래 중단 종목은 DailyPrice 20일치가 없을 수 있다. 이 경우 volume_signal = 0, price_signal = 0으로 처리하여 전체 배치가 실패하지 않도록 한다.

### 섹터 전체가 침체된 경우

특정 섹터 전체가 heat_score가 낮을 수 있다 (예: Utilities는 대체로 시그널이 약함). MarketView에서 해당 섹터를 선택했을 때 시드 노드가 없어도 문제없도록, CS-5-5에서 fallback 로직(heat_score 없으면 market cap 상위) 필요.

### 가중치 튜닝

MVP는 동일 가중치(0.25씩)로 시작. 사용자 클릭 로그가 쌓이면 (Phase 7 완료 후) A/B 테스트로 조정. 현재는 WEIGHTS 상수를 코드에 박아두되, 미래에 `chainsight_heat_score_config` 테이블이나 환경변수로 이동할 수 있도록 WEIGHTS dict로 분리해둠.

### 개인화는 v1.3 이후

본 작업은 user-agnostic 배치. 사용자별 heat_score 보너스(PathAction 50건 이상 시 자주 보는 섹터 가중치 증가 등)는 v1.3 이후. PM_DESIGN.md 섹션 14 참조.

---

→ **다음**: cs_51 (Phase 5 프론트엔드 시작) — Watchlist API는 Phase 6에서 별도 진행

**END OF DOCUMENT**

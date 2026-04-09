# Chain Sight 시드 노드 선정 로직 설계서

> **버전**: v2.0  
> **작성일**: 2026-04-09  
> **상태**: 확정  
> **변경 이력**: v1.0 → v2.0 — 시드의 역할을 그래프 시작점 + 대표 카드/탐색 시작점으로 확장

---

## 1. 개요

Chain Sight 마켓 뷰(`/chainsight`)는 **시장 탐색 허브**다. 시드 노드란 이 허브의 **출발점** — 그래프 초기 렌더링의 시작점이자, 관계 카드/대표 카드의 탐색 시작점을 의미한다.

시드는 "어젯밤 미국장에서 유의미한 변화가 감지된 종목"을 자동으로 선정한다.

### 시드의 두 가지 역할

1. **그래프 시작점**: 섹터 선택 후 그래프에서 bounce 애니메이션으로 표시되는 노드
2. **카드 탐색 시작점**: 섹터 진입 시 관계 카드 대신 표시되는 "대표 시드 카드"의 후보

### Phase 발전 경로

```
Phase 1 (B+A)  →  Phase 2 (C)  →  Phase 3 (D)
시장 시그널      복합 랭킹         이벤트 전파
+ 관계 변화      Heat Score        뉴스·주가·거래량·SEC
```

---

## 2. Phase 1: 시장 시그널 + 관계 변화 (B+A)

### 2.1 시드 소스

| 소스                         | 타입         | 현재 상태 | 주기       |
| ---------------------------- | ------------ | --------- | ---------- |
| EOD 수익률 이상치            | Signal (B)   | ✅ 운영중 | 매일       |
| EOD 거래량 급증              | Signal (B)   | ✅ 운영중 | 매일       |
| RelationConfidence 상태 전이 | Relation (A) | ✅ 운영중 | 매일 11:00 |
| co-mention 급증              | Relation (A) | ✅ 운영중 | 매일 10:00 |

### 2.2 시드 선정 기준

#### B: 시장 시그널

```python
price_seeds = Stock.objects.filter(
    daily_return__gte=threshold_upper  # 상위 2σ
) | Stock.objects.filter(
    daily_return__lte=threshold_lower  # 하위 2σ
)

volume_seeds = Stock.objects.filter(
    volume__gte=F('volume_sma20') * 2.0
)

sector_outlier_seeds = Stock.objects.annotate(
    sector_avg=Subquery(sector_avg_return)
).filter(
    daily_return__gt=F('sector_avg') + 2 * F('sector_std')
)
```

#### A: 관계 변화

```python
relation_seeds = RelationConfidence.objects.filter(
    updated_at__gte=yesterday,
    status__in=['confirmed', 'probable']
).exclude(
    previous_status=F('status')
).values_list('stock_a', 'stock_b')

comention_seeds = CoMention.objects.filter(
    date=today,
    count__gte=F('count_7d_avg') * 2.0
)
```

> 필요 스키마: RelationConfidence에 `previous_status` 필드 추가

#### 합산

```python
all_seeds = set(price_seeds) | set(volume_seeds) | set(sector_outlier_seeds)
           | set(relation_seeds_stocks) | set(comention_seeds_stocks)

seed_ranking = Counter(all_occurrences).most_common(MAX_SEED_NODES)
```

### 2.3 출력

| 필드             | 설명                               |
| ---------------- | ---------------------------------- |
| `symbol`         | 종목 심볼                          |
| `seed_reasons[]` | 시드 사유 리스트                   |
| `signal_count`   | 시드 소스 출현 횟수                |
| `neighbors[]`    | 1-depth Neo4j 이웃 (그래프 렌더용) |

### 2.4 제약

- MAX_SEED_NODES = 20
- 이웃 포함 총 노드 수 상한: 80
- 시드 부족 시: 전일 시드 유지 + "변화 없음" 표시

---

## 3. Phase 2: Heat Score (C)

### 3.1 정의

```
heat_score(S) =
    w1 × norm_price_anomaly(S)
  + w2 × norm_volume_surge(S)
  + w3 × norm_relation_change_count(S)
  + w4 × norm_comention_surge(S)
  + w5 × norm_news_event_count(S)
  + w6 × norm_gds_centrality_delta(S)
```

### 3.2 정규화

| 항목                  | 정규화                        | 범위 |
| --------------------- | ----------------------------- | ---- |
| price_anomaly         | \|return\| / σ_20d, min-max   | 0~1  |
| volume_surge          | (vol/sma20 - 1), cap=3.0      | 0~1  |
| relation_change_count | count, cap=5                  | 0~1  |
| comention_surge       | (today/avg7d - 1), cap=3.0    | 0~1  |
| news_event_count      | count, cap=10                 | 0~1  |
| gds_centrality_delta  | \|PR_new - PR_prev\|, min-max | 0~1  |

### 3.3 초기 가중치

```python
W = {
    'price_anomaly': 0.25, 'volume_surge': 0.20,
    'relation_change': 0.20, 'comention_surge': 0.15,
    'news_event': 0.10, 'gds_centrality_delta': 0.10,
}
```

### 3.4 저장

```python
class SeedHeatScore(models.Model):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    date = models.DateField()
    heat_score = models.FloatField()
    components = models.JSONField()
    seed_rank = models.IntegerField(null=True)

    class Meta:
        unique_together = ('stock', 'date')
        indexes = [models.Index(fields=['-date', '-heat_score'])]
```

### 3.5 섹터 정렬 기준 변경

Phase 1: `seed_count DESC` → Phase 2+: `heat_total DESC`

---

## 4. Phase 3: 이벤트 전파 모델 (D)

### 4.1 개요

핵심 원칙: **모든 정성 데이터(뉴스)는 정량 변환 후에만 모델에 투입.**

### 4.2 이벤트 시드 4종

| 시드       | 주기        | 기준                         | 역할                                                   |
| ---------- | ----------- | ---------------------------- | ------------------------------------------------------ |
| 뉴스       | 실시간~일간 | 종목 관련 뉴스 + 키워드 추출 | 정성→정량 변환 출발점                                  |
| 주가       | 일간        | \|return\| > 2σ              | 시장 반응 직접 관측                                    |
| 거래량     | 일간        | vol / sma20 > 2.0            | 시장 관심 직접 관측                                    |
| SEC filing | 분기별      | 10-K/10-Q 감지               | **전파 경로(관계) 업데이트** — 시드가 아닌 "도로 갱신" |

### 4.3 뉴스 정량 변환

```
뉴스 → Gemini Flash 키워드 추출 → Embedding → 종목별 키워드 벡터 집합
→ 종목 페어 간 text_conditional_prob 계산
```

**text_conditional_prob(A, B):**

```
= frequency_component × semantic_component

frequency = |days_both(A,B)| / |days_with_news(A)|
semantic  = mean_cosine_sim(keyword_vectors, days_both)
```

90일 rolling / 기존 관계 페어만 (~1만 페어) / 비대칭

### 4.4 전파 가중치

```
propagation_weight(A→B) = f(
    text_conditional_prob(A,B),
    price_correlation(A,B),      # lagged: max(lag0, lag1, lag2)
    volume_response(B|event_A)   # event 후 거래량 반응
)
```

**합산:**

```
norm_text   = text_conditional_prob              (0~1)
norm_price  = (price_correlation + 1) / 2        (-1~1 → 0~1)
norm_volume = min(volume_response / 2.0, 1)      (cap=2.0)

if norm_text < TEXT_THRESHOLD (0.05):
    propagation_weight = 0    # 텍스트 게이트: 뉴스 연결 없으면 전파 아님
else:
    propagation_weight = 0.40×norm_text + 0.35×norm_price + 0.25×norm_volume
```

비대칭: `propagation_weight(A→B) ≠ propagation_weight(B→A)` → Neo4j 방향성 엣지

### 4.5 관계 타입별 전파 의미론

| 관계        | 전파 방향 | 의미             |
| ----------- | --------- | ---------------- |
| SUPPLIES_TO | 상류→하류 | 공급 리스크/수혜 |
| PEER_OF     | 양방향    | 동조/경쟁 관심   |
| HAS_THEME   | 전파 아님 | 필터링 전용      |

### 4.6 D Phase 단계

| 단계 | 내용                                                      | 의존                       |
| ---- | --------------------------------------------------------- | -------------------------- |
| D-1  | 키워드 벡터 유사도 + text_conditional_prob                | ChromaDB, Gemini Embedding |
| D-2  | lagged correlation + volume_response + propagation_weight | D-1 + 60 거래일            |
| D-3  | 전파 사후 검증 → 가중치 학습                              | D-2 + 검증 데이터          |

---

## 5. 프론트엔드 통합

### 5.1 화면 구조

시드 데이터는 마켓 뷰의 세 영역에서 활용된다:

| 영역                    | 시드 활용                                       |
| ----------------------- | ----------------------------------------------- |
| ① 섹터 버튼 바          | seed_count/heat_total로 정렬, pct_change로 색상 |
| ② 그래프 캔버스         | is_seed=true 노드에 bounce 애니메이션           |
| ④ 관계 카드 (섹터 진입) | 중심 노드 미선택 시 대표 시드 카드로 표시       |
| ⑤ 체인 스토리 피드      | 시드 기반 자동 구성 체인                        |

### 5.2 노드 클릭 정책

마켓 뷰에서 노드 클릭(그래프든 카드든)은 **항상 in-place 중심 이동**:

1. `GET /api/v1/chainsight/{symbol}/neighbors/`
2. 그래프 중심 이동
3. 관계 카드 패널 갱신
4. 탐색 트레일 확장

`/chainsight/[symbol]`(에고 그래프 워크스페이스)로의 이동은 **"Deep dive" CTA에서만** 허용. 에고 그래프는 validation, trace, advanced analysis 용도.

### 5.3 코드 처리: 점진적 전환 (C)

| 구분   | 처리                                                                                                                                |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------- |
| 신규   | `app/chainsight/page.tsx`, `MarketGraphCanvas`, `RelationCardPanel`, `ExplorationTrail`, `ChainStoryFeed`, `useExplorationState` 등 |
| 재사용 | `types/chainsight.ts`, `chainsightService.ts`, `graphStyles.ts`                                                                     |
| 유지   | `app/chainsight/[symbol]/page.tsx` (deep dive workspace)                                                                            |
| 변경   | `app/stocks/[symbol]` Chain Sight 탭 제거 → `/chainsight?focus=SYMBOL` 딥링크                                                       |

### 5.4 신규 API 엔드포인트

```
GET /api/v1/chainsight/seeds/          ← 섹터 바 + 대표 카드
GET /api/v1/chainsight/sector/{s}/graph/  ← 초기 구조 시각화
GET /api/v1/chainsight/{symbol}/neighbors/ ← 중심 이동 + 관계 카드
GET /api/v1/chainsight/signals/        ← chain flow + discovery
```

---

## 6. Celery Beat 추가 태스크

| 이름                          | Task                                            | 스케줄     | Phase         |
| ----------------------------- | ----------------------------------------------- | ---------- | ------------- |
| chainsight-seed-selection     | signal_tasks.select_daily_seeds                 | 매일 12:00 | Phase 1       |
| chainsight-heat-score         | signal_tasks.calculate_heat_scores              | 매일 11:30 | Phase 2       |
| chainsight-text-conditional   | propagation_tasks.calculate_text_probs          | 매일 13:00 | Phase 3 (D-1) |
| chainsight-lagged-correlation | propagation_tasks.calculate_lagged_correlations | 토 03:30   | Phase 3 (D-2) |
| chainsight-propagation-weight | propagation_tasks.calculate_propagation_weights | 토 05:30   | Phase 3 (D-2) |

---

## 7. 의존성

| Phase       | 전제                                        |
| ----------- | ------------------------------------------- |
| Phase 1     | RelationConfidence `previous_status` 추가   |
| Phase 2     | SeedHeatScore 모델 + Phase 1 안정화         |
| Phase 3 D-1 | Gemini Embedding API + ChromaDB 키워드 벡터 |
| Phase 3 D-2 | 60 거래일 데이터 (D-1 시작 후 ~3개월)       |
| Phase 3 D-3 | 전파 검증 레이블 충분 축적                  |

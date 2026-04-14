# Chain Sight 시드 노드 선정 로직 설계서

> **버전**: v2.1 FINAL  
> **작성일**: 2026-04-10  
> **상태**: 확정 — 구현 진행 가능  
> **변경 이력**: v2.0 → v2.1 — 시드 출력 정리, 용어 통일, 프론트 통합 재서술  
> **선행 문서**: CHAIN_SIGHT_ROADMAP

---

## 1. 개요

Chain Sight 마켓 뷰(`/chainsight`)는 **시장 탐색 허브**다. 시드 노드는 이 허브의 **출발점**이다.

### 시드의 역할

1. **그래프 시작점**: 섹터 overview graph에서 bounce 애니메이션으로 표시되는 노드
2. **대표 시드 카드의 source**: 섹터 진입 후 centerSymbol == null 상태에서, 관계 카드 패널의 pre-focus state로 표시되는 카드의 데이터

> 용어: "대표 시드 카드"는 관계 카드 패널의 pre-focus state. centerSymbol이 설정되면 `neighbors/` 기반 **관계 카드**로 전환된다.

### Phase 발전 경로

```
Phase 1 (B+A)  →  Phase 2 (C)  →  Phase 3 (D)
시장 시그널      복합 랭킹         이벤트 전파
+ 관계 변화      Heat Score        뉴스·주가·거래량·SEC
```

---

## 2. Phase 1: 시장 시그널 + 관계 변화 (B+A)

### 2.1 시드 소스

| 소스                         | 타입         | 상태 | 주기       |
| ---------------------------- | ------------ | ---- | ---------- |
| EOD 수익률 이상치            | Signal (B)   | ✅   | 매일       |
| EOD 거래량 급증              | Signal (B)   | ✅   | 매일       |
| RelationConfidence 상태 전이 | Relation (A) | ✅   | 매일 11:00 |
| co-mention 급증              | Relation (A) | ✅   | 매일 10:00 |

### 2.2 선정 기준

**B: 시장 시그널**

```python
price_seeds = Stock.objects.filter(daily_return__gte=threshold_upper)  # 상위 2σ
            | Stock.objects.filter(daily_return__lte=threshold_lower)  # 하위 2σ

volume_seeds = Stock.objects.filter(volume__gte=F('volume_sma20') * 2.0)

sector_outlier_seeds = ...  # 섹터 평균 대비 ±2σ
```

**A: 관계 변화**

```python
relation_seeds = RelationConfidence.objects.filter(
    updated_at__gte=yesterday
).exclude(previous_status=F('status'))

comention_seeds = CoMention.objects.filter(
    date=today, count__gte=F('count_7d_avg') * 2.0
)
```

> 필요 스키마: RelationConfidence에 `previous_status` 필드 추가

**합산**

```python
all_seeds = union of all seed sets
seed_ranking = Counter(all_occurrences).most_common(MAX_SEED_NODES)
```

### 2.3 시드 출력

| 필드         | 타입     | 설명                                                  |
| ------------ | -------- | ----------------------------------------------------- |
| symbol       | string   | 종목 ticker                                           |
| seed_reasons | string[] | 시드 사유 코드                                        |
| signal_count | int      | 시드 소스 출현 횟수                                   |
| seed_type    | string   | 대표 시드 타입: price / volume / relation / comention |
| sector       | string   | 섹터                                                  |
| daily_return | float    | 전일 수익률 (%)                                       |
| volume_ratio | float    | 거래량 / SMA20                                        |

### 2.4 제약

- MAX_SEED_NODES = 20
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

### 4.1 원칙

**모든 정성 데이터(뉴스)는 정량 변환 후에만 모델에 투입.**

### 4.2 이벤트 시드 4종

| 시드       | 주기        | 역할                                                   |
| ---------- | ----------- | ------------------------------------------------------ |
| 뉴스       | 실시간~일간 | 정성→정량 변환 출발점                                  |
| 주가       | 일간        | 시장 반응 직접 관측                                    |
| 거래량     | 일간        | 시장 관심 직접 관측                                    |
| SEC filing | 분기별      | **전파 경로(관계) 업데이트** — 시드가 아닌 "도로 갱신" |

### 4.3 뉴스 정량 변환

```
뉴스 → Gemini Flash 키워드 추출 → Embedding → 종목별 벡터 집합
→ text_conditional_prob(A, B) = frequency × semantic_similarity
```

90일 rolling / 기존 관계 페어만 / 비대칭

### 4.4 전파 가중치

```
propagation_weight(A→B) = f(
    text_conditional_prob(A,B),
    price_correlation(A,B),       # lagged: max(lag0, lag1, lag2)
    volume_response(B|event_A)
)
```

```
if norm_text < 0.05:  # 텍스트 게이트
    propagation_weight = 0
else:
    = 0.40×norm_text + 0.35×norm_price + 0.25×norm_volume
```

비대칭 → Neo4j 방향성 엣지

### 4.5 D Phase 단계

| 단계 | 내용                                                      | 의존                       |
| ---- | --------------------------------------------------------- | -------------------------- |
| D-1  | text_conditional_prob                                     | ChromaDB, Gemini Embedding |
| D-2  | lagged correlation + volume_response + propagation_weight | D-1 + 60 거래일            |
| D-3  | 사후 검증 → 가중치 학습                                   | D-2 + 검증 데이터          |

---

## 5. 프론트엔드 통합

### 5.1 시드 데이터의 UI 활용

| UI 영역                 | 시드 활용                                       | 데이터 흐름                         |
| ----------------------- | ----------------------------------------------- | ----------------------------------- |
| ① 섹터 바               | seed_count/heat_total로 정렬, pct_change로 색상 | `seeds/` → `sector_summary`         |
| ② 그래프                | is_seed=true 노드에 bounce                      | `sector graph/` → `nodes[].is_seed` |
| ③ 트레일                | 경로 보존 + undo                                | 탐색 시 자동 확장                   |
| ④ 관계 카드 (pre-focus) | 대표 시드 카드                                  | `seeds/` → 프론트 섹터 필터         |
| ⑤ 체인 스토리           | 시드 기반 자동 구성 체인                        | `signals/`                          |

### 5.2 상태별 카드 패널

| 상태        | centerSymbol | ④ 카드 패널                             |
| ----------- | ------------ | --------------------------------------- |
| 섹터만 선택 | null         | **대표 시드 카드** (pre-focus)          |
| 종목 선택됨 | 종목         | **관계 카드** (focused, neighbors 기반) |

### 5.3 노드 클릭 정책

마켓 뷰 노드 클릭(그래프든 카드든) = **항상 in-place 중심 이동**:

1. `GET /{symbol}/neighbors/`
2. ② 중심 이동 + ③ 트레일 확장 + ④ 관계 카드 갱신

Deep dive workspace(`/chainsight/[symbol]`) 이동은 관계 카드 "Deep dive" CTA에서만.

---

## 6. Celery Beat 태스크

| 이름                          | 스케줄     | Phase         |
| ----------------------------- | ---------- | ------------- |
| chainsight-seed-selection     | 매일 12:00 | Phase 1       |
| chainsight-heat-score         | 매일 11:30 | Phase 2       |
| chainsight-text-conditional   | 매일 13:00 | Phase 3 (D-1) |
| chainsight-lagged-correlation | 토 03:30   | Phase 3 (D-2) |
| chainsight-propagation-weight | 토 05:30   | Phase 3 (D-2) |

---

## 7. 의존성

| Phase       | 전제                                |
| ----------- | ----------------------------------- |
| Phase 1     | `previous_status` 추가              |
| Phase 2     | SeedHeatScore 모델 + Phase 1 안정화 |
| Phase 3 D-1 | Gemini Embedding + ChromaDB         |
| Phase 3 D-2 | 60 거래일 (D-1 후 ~3개월)           |
| Phase 3 D-3 | 검증 레이블 축적                    |

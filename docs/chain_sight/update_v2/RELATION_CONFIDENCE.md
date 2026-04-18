# 관계 신뢰도 엔진 설계서

> **버전**: v2.1  
> **최종 수정**: 2026-04-17  
> **구현 작업**: CS-2-4 (관계 판정), CS-3-2 (Neo4j 동기화), CS-4-1 (API 노출)  
> **상태**: 확정 — Phase 2 진입 시 구현

---

## 1. 판정 철학

Chain Sight의 관계는 두 가지로 분류된다.

**Truth 관계** — 사업 구조에 기반한 관계. 독립적 증거로 검증 가능하며, confirmed까지 상향 가능.

- PEER_OF: 동종업계 경쟁사
- SUPPLIES_TO: 공급망 관계 (canonical 방향만 저장, 역방향은 API에서 CUSTOMER_OF로 파생)
- COMPETES_WITH: 직접 경쟁
- BELONGS_TO_SECTOR / BELONGS_TO_INDUSTRY: 산업 분류
- HAS_THEME: 테마 연결 (ETF 기반)

**Market 관계** — 시장 현상에 기반한 관계. 사업 구조를 증명하지 않으며, confirmed 불가. 보조 라벨 용도.

- CO_MENTIONED: 뉴스 동시출현
- PRICE_CORRELATED: 주가 동조

Truth 관계만 truth_score를 계산하고 5단계 상태 판정을 받는다. Market 관계는 truth_score 비대상이며, Neo4j에서 보조 속성으로만 첨부된다.

---

## 2. 5단계 상태 체계

| 상태 | truth_score 대표값 | 의미 | Neo4j 엣지 | API 노출 |
|------|------------------|------|-----------|---------|
| confirmed | 85 | 독립 증거 2개 이상으로 검증됨 | ✅ 생성 | ✅ |
| probable | 60 | 강한 단일 증거 또는 복수 약한 증거 | ✅ 생성 | ✅ |
| weak | 35 | 약한 증거만 존재 | ❌ 미생성 | 요청 시만 |
| hidden | 15 | 증거 부족 또는 폐기 | ❌ 미생성 | ❌ |
| stale | — | 마지막 검증 후 임계일 초과 | ❌ 삭제 | ❌ |

**상태 전이 규칙**:
- 상향: hidden → weak → probable → confirmed (증거 추가 시)
- 하향 (stale decay): confirmed → stale, probable → weak, weak → hidden (임계일 초과 시)
- stale 전용: confirmed만 stale로 전이 가능 (probable/weak는 직접 하향)

---

## 3. 증거 등급 (Evidence Tier)

| Tier | 설명 | 예시 | 신뢰도 |
|------|------|------|--------|
| Tier 1 | API 직접 데이터 | FMP Peers, Finnhub Supply Chain, SEC 공시 | 높음 |
| Tier 2 | 파생 계산 | ETF Holdings 동시 보유, 가격 상관관계 | 중간 |
| Tier 3 | LLM/뉴스 추론 | Gemini Flash 추출, 뉴스 co-mention | 낮음 |

`evidence_tier_best`는 해당 관계에 존재하는 가장 높은 등급의 증거를 기록한다.

---

## 4. 정책표 — 상태 판정 기준

### confirmed 조건 (truth_score = 85)
- Tier 1 증거 2개 이상 독립 소스, 또는
- Tier 1 증거 1개 + Tier 2 증거 2개 이상

### probable 조건 (truth_score = 60)
- Tier 1 증거 1개, 또는
- Tier 2 증거 2개 이상, 또는
- Tier 2 증거 1개 + Tier 3 증거 2개 이상

### weak 조건 (truth_score = 35)
- Tier 2 증거 1개, 또는
- Tier 3 증거 2개 이상

### hidden 조건 (truth_score = 15)
- Tier 3 증거 1개 이하, 또는
- 모든 증거가 stale

---

## 5. Stale 판정

`stale_threshold_days` 필드로 관계 유형별 임계일을 설정한다.

| 관계 유형 | 임계일 | 근거 |
|----------|--------|------|
| PEER_OF | 180일 | 경쟁 구도는 느리게 변함 |
| SUPPLIES_TO | 120일 | 공급 계약은 분기~반기 단위 |
| COMPETES_WITH | 180일 | 경쟁 관계는 느리게 변함 |
| HAS_THEME | 90일 | 테마는 시장 흐름에 따라 빠르게 변함 |

판정 기준: `last_verified_at`로부터 `stale_threshold_days`가 지나면 하향 전이 실행.

Celery Beat 스케줄: `chainsight-stale-decay-weekly` (매주 일요일 04:30)

---

## 6. relation_basis_summary 템플릿

사용자에게 "왜 이 관계인가"를 설명하는 1줄 요약. 템플릿 기반 자동 생성.

| 조건 | 템플릿 | 예시 |
|------|--------|------|
| has_peer_source + has_industry_source | "{A}와 {B}는 {industry} 내 peers (Finnhub/FMP 확인)" | "NVDA와 AMD는 반도체 설계 내 peers" |
| has_supply_chain_source | "{A}는 {B}의 공급망 파트너 (Tier 1 증거)" | "TSM은 NVDA의 공급망 파트너" |
| has_etf_source | "{A}와 {B}는 동일 ETF ({etf_name})에 포함" | "NVDA와 ASML은 SOXX ETF에 포함" |
| has_news_source only | "{A}와 {B}는 뉴스에서 함께 언급 ({count}건)" | "AAPL과 QCOM은 뉴스에서 함께 언급 (12건)" |
| has_llm_source only | "{A}와 {B}는 AI 분석에서 관계 추정" | "TSLA와 LG에너지는 AI 분석에서 관계 추정" |

---

## 7. RelationConfidence 스키마 v2.1

```python
class RelationConfidence(models.Model):
    # 식별
    symbol_a = models.CharField(max_length=10, db_index=True)
    symbol_b = models.CharField(max_length=10, db_index=True)
    # ⚠️ undirected 관계는 symbol_a < symbol_b 사전순 강제 (normalize_pair)

    relation_type = models.CharField(max_length=30)
    # PEER_OF, SUPPLIES_TO, COMPETES_WITH, HAS_THEME, CO_MENTIONED, PRICE_CORRELATED

    relation_category = models.CharField(max_length=10, choices=[('truth','Truth'),('market','Market')])
    canonical_direction = models.CharField(max_length=10, blank=True, null=True)
    # SUPPLIES_TO: 'a_to_b' 또는 'b_to_a'. undirected는 null.

    # 상태
    relation_status = models.CharField(max_length=15)
    # hidden / weak / probable / confirmed / stale

    # 점수
    truth_score = models.FloatField(null=True)         # Truth 관계만. 대표값: 85/60/35/15
    market_score = models.FloatField(null=True)         # MVP: null (v1.3 이후)
    investment_relevance = models.FloatField(null=True)  # MVP: null (v1.3 이후)

    # 증거
    evidence_tier_best = models.PositiveSmallIntegerField(null=True)  # 1, 2, 3
    evidence_count_total = models.PositiveSmallIntegerField(default=0)
    evidence_count_independent = models.PositiveSmallIntegerField(default=0)
    evidence_sources = models.JSONField(default=dict)
    # {"finnhub_peers": {"date": "...", "data": ...}, "fmp_peers": {...}, ...}

    # 빠른 필터 (7개 bool)
    has_peer_source = models.BooleanField(default=False)
    has_industry_source = models.BooleanField(default=False)
    has_supply_chain_source = models.BooleanField(default=False)
    has_news_source = models.BooleanField(default=False)
    has_price_source = models.BooleanField(default=False)
    has_etf_source = models.BooleanField(default=False)
    has_llm_source = models.BooleanField(default=False)

    # 설명
    relation_basis_summary = models.TextField(blank=True)

    # 시간
    first_observed_at = models.DateTimeField(auto_now_add=True)
    last_observed_at = models.DateTimeField(auto_now=True)
    last_verified_at = models.DateTimeField(null=True)
    stale_threshold_days = models.PositiveSmallIntegerField(default=180)

    # 동기화
    synced_to_neo4j = models.BooleanField(default=False)
    score_version = models.CharField(max_length=10, default='v2.1')

    class Meta:
        db_table = 'chainsight_relation_confidence'
        unique_together = [['symbol_a', 'symbol_b', 'relation_type']]
        indexes = [
            models.Index(fields=['relation_status']),
            models.Index(fields=['relation_type']),
            models.Index(fields=['synced_to_neo4j']),
        ]
```

---

## 8. normalize_pair 유틸

```python
def normalize_pair(symbol_a: str, symbol_b: str) -> tuple[str, str]:
    """undirected 관계의 사전순 정규화. symbol_a < symbol_b 보장."""
    if symbol_a <= symbol_b:
        return symbol_a, symbol_b
    return symbol_b, symbol_a
```

모든 undirected 관계(PEER_OF, COMPETES_WITH, CO_MENTIONED, PRICE_CORRELATED) 저장 시 반드시 이 함수를 거친다.

SUPPLIES_TO는 directed이므로 정규화하지 않고 canonical_direction으로 방향을 기록한다.

---

## 9. CUSTOMER_OF 처리 정책

**별도 저장하지 않는다.** SUPPLIES_TO만 canonical 저장.

API(CS-4-1)에서 SUPPLIES_TO 엣지를 발견하면 방향에 따라:
- 정방향: "공급" 라벨
- 역방향: "고객 관계" 라벨 (CUSTOMER_OF로 표시)

```python
# cs_41 그래프 API에서의 역방향 파생
if edge['type'] == 'SUPPLIES_TO':
    if viewing_from_supplier_side:
        edge['display_label'] = '공급'
    else:
        edge['reverse_label'] = 'CUSTOMER_OF'
        edge['display_label'] = '고객 관계'
```

---

## 10. Neo4j 동기화 규칙 (CS-3-2)

| 관계 | 조건 | Neo4j 처리 |
|------|------|-----------|
| Truth + confirmed | synced_to_neo4j=False | 엣지 생성/갱신 |
| Truth + probable | synced_to_neo4j=False | 엣지 생성/갱신 |
| Truth + weak/hidden/stale | — | 엣지 미생성. 기존 엣지 삭제 |
| Market (모든 상태) | — | 별도 엣지 아님. Truth 엣지의 보조 속성으로 첨부 |

동기화 속성:
```python
repo.upsert_edge(rel.symbol_a, rel.symbol_b, rel.relation_type, {
    "truth_score": rel.truth_score,
    "status": rel.relation_status,
    "basis_summary": rel.relation_basis_summary,
})
```

---

## 부록: 관계 유형 전체 목록

| 관계 | 분류 | 방향 | 저장 방식 | DC Phase |
|------|------|------|----------|---------|
| BELONGS_TO_SECTOR | Truth | Stock → Sector | 항상 저장 | DC-1 |
| BELONGS_TO_INDUSTRY | Truth | Stock → Industry | 항상 저장 | DC-1 |
| PEER_OF | Truth | undirected | symbol_a < symbol_b | DC-1 |
| SUPPLIES_TO | Truth | directed | canonical_direction | DC-3, DC-4 |
| COMPETES_WITH | Truth | undirected | symbol_a < symbol_b | CS-2 |
| HAS_THEME | Truth | Stock → Theme | 항상 저장 | DC-2 |
| CO_MENTIONED | Market | undirected | symbol_a < symbol_b | DC-5 |
| PRICE_CORRELATED | Market | undirected | symbol_a < symbol_b | CS-2 |

**END OF DOCUMENT**

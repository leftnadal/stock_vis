# Chain Sight 관계 신뢰도 엔진 설계서 v1.1

> **작성일**: 2026-04-02
> **위치**: `docs/chain_sight/RELATION_CONFIDENCE.md`
> **연관 문서**: ROADMAP.md (v1.2), ONTOLOGY.md
> **상태**: 초안 — CS-0 착수 전 리뷰 필요

### v1 → v1.1 변경 사항

- undirected relation 사전순 정규화 규칙 추가 (섹션 2 원칙 6 + 섹션 8)
- manual_seed 작성 프로토콜 추가 (섹션 3 Tier 1 + 섹션 9)
- same_industry의 역할 범위 제한 명시 (섹션 3 Tier 2 + 섹션 5)
- has_same_industry ≠ has_peer_source 분리 (섹션 7 스키마)
- truth_score를 상태 대표값으로 단순화 (섹션 10, 추천 A 채택)
- PRICE_CORRELATED / CO_MENTIONED를 truth_score 대상에서 제외 → market 전용 (섹션 4, 10)
- evidence_sources JSONB → RelationEvidence 분리 확장 경로 명시 (섹션 14)
- PEER_OF confirmed 조건 보수화: Tier 1 × 2 필수, Tier 1 + same_industry = probable (섹션 6)
- SUPPLIES_TO Tier 2 × 2 = confirmed 제거 → probable로 변경 (섹션 6, 10)
- PRICE_CORRELATED 판정 기준을 count에서 raw metric(상관계수)으로 명확화 (섹션 6, 10)
- probable → weak → hidden 시간 경과 하향 전이 규칙 추가 (섹션 5, 13)
- price_corr_90d를 Tier 2에서 Tier 3으로 이동 (섹션 3)

---

## 1. 이 문서의 목적

로드맵 v1.2에는 관계를 수집하고 저장하는 파이프라인이 정의되어 있다.
이 문서는 그 파이프라인 위에 올라가는 **판정 철학** — 즉 "어떤 관계를 믿을 것인가, 어떻게 보여줄 것인가"를 정의한다.

로드맵이 "엔진의 부품 목록과 조립 순서"라면,
이 문서는 "엔진이 출력을 어떤 원리로 조절하는가"에 해당한다.

---

## 2. 핵심 원칙

### 원칙 1 — 관계 수보다 관계 품질

관계를 많이 만드는 것이 목표가 아니다.
잘못된 관계가 늘면 "그럴듯하게 틀린 연결"이 보여서 사용자 신뢰가 깨진다.
그래프는 한번 오염되면 회복이 어렵다.

### 원칙 2 — 증거의 개수보다 증거의 급(Tier)

source_count = 2라고 해도 "FMP peer + Finnhub peer"와 "어제 뉴스 + 오늘 뉴스"는 완전히 다르다.
숫자 가중치 대신, 증거의 급(Tier)을 나누는 정책으로 운영한다.

### 원칙 3 — 저장과 노출을 분리

DB에는 후보 관계를 넉넉하게 저장하되, UI에는 threshold를 넘은 것만 보여준다.
"hidden"은 삭제가 아니다. 언제든 증거가 추가되면 승격될 수 있다.

### 원칙 4 — 설명 가능해야 한다

최종 confidence는 숫자 하나가 아니라, "왜 이 상태인가"가 따라와야 한다.
처음부터 LLM 설명 생성이 아닌, 템플릿 기반 설명으로 시작한다.

### 원칙 5 — Truth와 Market Relevance는 다른 질문

"이 관계가 사업적으로 존재하는가" (truth)와
"이 관계가 최근 시장에서 작동하는가" (market relevance)는 별개의 질문이다.
스키마에 두 필드를 분리하되, MVP에서는 truth만 계산한다.

**Truth 대상 관계**: PEER*OF, SUPPLIES_TO, COMPETES_WITH, HAS_THEME, BELONGS_TO*\*
**Market 대상 관계**: PRICE_CORRELATED, CO_MENTIONED

Market 대상 관계는 truth_score를 부여하지 않는다.
MVP에서는 relation_status만 관리하고, market_score 구현 시 입력으로 활용한다.

### 원칙 6 — Undirected 관계는 사전순 정규화

방향성이 없는 관계(PEER_OF, COMPETES_WITH, PRICE_CORRELATED, CO_MENTIONED)는
저장 시 반드시 `symbol_a < symbol_b` (사전순)으로 정렬한다.

이유: unique_together 중복 방지 + 조인/집계 일관성.

```python
# chainsight/utils.py
def normalize_pair(symbol_a: str, symbol_b: str, direction: str) -> tuple[str, str]:
    """undirected 관계의 심볼 쌍을 사전순으로 정규화."""
    if direction == 'undirected':
        return (min(symbol_a, symbol_b), max(symbol_a, symbol_b))
    return (symbol_a, symbol_b)  # directed는 원래 순서 유지
```

모든 management command, Celery task, API 입력에서 저장 전 이 함수를 호출한다.

---

## 3. 증거 등급 체계 (Tier System)

숫자 가중치 대신, 모든 증거를 3개 Tier로 분류한다.

### Tier 1 — 구조적/검증된 증거

사업 구조, 공식 데이터, 수동 검증에 기반한 강한 증거.
단독으로도 관계의 존재를 주장할 수 있다.

| 증거 유형                        | source_type    | 설명                                                                |
| -------------------------------- | -------------- | ------------------------------------------------------------------- |
| 수동 검증 공급망 (프로토콜 준수) | `manual_seed`  | data/seed/ JSON. **반드시 provenance 필드 포함 필수** (섹션 9 참조) |
| FMP Peers API                    | `fmp_peer`     | FMP 공식 peer 데이터                                                |
| Finnhub Peers API                | `finnhub_peer` | Finnhub 공식 peer 데이터                                            |
| FMP Profile (sector/industry)    | `fmp_industry` | 공식 산업 분류                                                      |
| ETF Holdings (확인됨)            | `etf_holding`  | 공식 ETF holdings 데이터                                            |

⚠️ `manual_seed`가 Tier 1인 이유는 seed 자체가 아니라 **작성 프로토콜(섹션 9)**을 신뢰하기 때문이다.
provenance 없는 seed는 Tier 2로 강등한다.

### Tier 2 — 파생/보조 증거

통계적 분석이나 테마 추론에 기반한 중간 강도 증거.
단독으로는 confirmed를 줄 수 없지만, Tier 1을 보강하거나 probable까지는 가능.

| 증거 유형                        | source_type              | 설명                                 | 역할 제한                                                                 |
| -------------------------------- | ------------------------ | ------------------------------------ | ------------------------------------------------------------------------- |
| Gemini Flash SC 추출 (검증 통과) | `gemini_extracted`       | LLM 추출 + FMP ticker 실존 확인 통과 | -                                                                         |
| 동일 industry (쿼리 기반)        | `same_industry`          | 같은 industry에 속하는 관계          | ⚠️ **보조 보강만 가능. 상태 전이의 핵심 트리거로 사용 금지.** (아래 참조) |
| ETF 테마 추정 (holdings 없이)    | `theme_inferred`         | industry 키워드 기반 테마 매칭       | -                                                                         |
| provenance 없는 manual seed      | `manual_seed_unverified` | 근거 문서 없이 작성된 seed           | Tier 1 강등                                                               |

#### same_industry 역할 제한 규칙

`same_industry`는 좋은 보조 신호이지만, 과대평가되면 false positive가 많아진다.
같은 industry라고 해서 반드시 peer도, 경쟁사도 아니다.

적용 규칙:

- `PEER_OF` confirmed 판정 시: same_industry는 보강 증거로 인정하되, **Tier 1 소스 1개가 반드시 선행**해야 함. same_industry 단독으로 probable 이상 불가.
- `COMPETES_WITH` confirmed 판정 시: same_industry는 **필수 전제 조건이 아니라 선택적 보강**. peer 소스 2개가 핵심이고, same_industry는 있으면 좋지만 없어도 confirmed 가능.
- 어떤 관계에서도 same_industry가 confirmed 승격의 결정적 트리거 역할을 하면 안 됨.

### Tier 3 — 약한/현상 증거

뉴스, 단기 가격 동조 등 현상에 기반한 약한 증거.
단독으로는 weak가 최대. 다른 Tier 증거의 보조 역할.

| 증거 유형                    | source_type       | 설명                                     |
| ---------------------------- | ----------------- | ---------------------------------------- |
| 뉴스 동시출현 (CO_MENTIONED) | `news_comention`  | Marketaux 뉴스에서 동시 태깅             |
| 가격 상관 30일 (단기)        | `price_corr_30d`  | 30일 correlation (시장 환경 오염 높음)   |
| Gemini Flash 추출 (미검증)   | `gemini_raw`      | 검증 레이어 미통과                       |
| 뉴스 내 공급망 키워드        | `news_sc_keyword` | "supplier", "supply" 등 키워드 동시 존재 |
| 가격 상관 90일 (r ≥ 0.7)     | `price_corr_90d`  | 90일 rolling correlation                 |

⚠️ **v1.1 변경**: `price_corr_90d`를 Tier 2에서 Tier 3으로 이동.
가격 상관은 truth(사업 관계 존재)보다 market relevance(시장 반영)에 가까운 신호이므로,
truth 판정의 증거로 사용하기에는 Tier가 높았음.

---

## 4. 관계 분류: Truth 관계 vs Market 관계

### Truth 관계 (truth_score 계산 대상)

사업 구조 관점에서 "이 관계가 존재하는가"를 판정하는 관계.

- `BELONGS_TO_SECTOR`
- `BELONGS_TO_INDUSTRY`
- `PEER_OF`
- `SUPPLIES_TO`
- `COMPETES_WITH`
- `HAS_THEME`

### Market 관계 (truth_score 비대상, relation_status만 관리)

시장 현상 관점에서 "최근 가격/뉴스에서 관찰되는가"를 기록하는 관계.

- `PRICE_CORRELATED`
- `CO_MENTIONED`

MVP에서 이 두 타입은:

- RelationConfidence에 row를 만들되 truth_score = null
- relation_status는 관리 (hidden / weak / probable, confirmed 불가)
- 추후 market_score 구현 시 입력으로 활용
- UI에서는 Truth 관계의 보강 라벨로 표시 (예: "PEER_OF ✅ + 가격 동조 📈")

이유: 원칙 5에서 "truth와 market은 다른 질문"이라고 정의했으므로,
market성 관계에 truth_score를 부여하면 철학이 흔들린다.

---

## 5. 관계 상태 (Relation Status)

### 5단계 상태

| 상태        | 의미                             | UI 노출                         |
| ----------- | -------------------------------- | ------------------------------- |
| `hidden`    | DB에 저장되어 있으나 증거 부족   | 안 보임                         |
| `weak`      | 약한 증거만 존재, 참고용         | 상세 패널에서만 표시 가능       |
| `probable`  | 꽤 그럴듯하나 확정은 아님        | 토글 시 표시 ("추정 관계" 라벨) |
| `confirmed` | 충분한 증거로 확인됨             | 기본 그래프에 표시              |
| `stale`     | 과거에는 강했으나 최근 검증 부족 | 기본 숨김, 흐린 표시 가능       |

### 상태 전이 규칙

```
hidden → weak      : Tier 3 증거 1개 이상 추가
weak → probable    : Tier 2 증거 1개 이상 추가, 또는 Tier 3 증거 3개 이상 + 반복성
probable → confirmed : 관계 타입별 confirmed 규칙 충족 (아래 섹션 6 참조)
confirmed → stale  : last_verified_at으로부터 stale_threshold_days 초과 + 새 증거 없음
stale → confirmed  : 새로운 Tier 1 또는 Tier 2 증거 추가
any → hidden       : 모든 증거가 만료되거나 반대 증거로 무효화

시간 경과에 따른 하향 전이:
confirmed → stale  : stale_threshold_days 초과 (위와 동일)
probable → weak    : stale_threshold_days × 1.5 초과 + 새 증거 없음
weak → hidden      : stale_threshold_days × 2 초과 + 새 증거 없음

예시 (PEER_OF, stale=180일):
  confirmed → stale : 180일 초과
  probable → weak  : 270일 초과
  weak → hidden    : 360일 초과
```

---

## 6. 관계 타입별 Confirmed 규칙표

### `BELONGS_TO_SECTOR` / `BELONGS_TO_INDUSTRY`

```
항상 confirmed.
FMP Profile에서 온 공식 분류이므로 별도 검증 불필요.
```

### `PEER_OF`

```
confirmed 조건:
  - Tier 1 독립 소스 2개 (예: FMP peer + Finnhub peer)
  - Tier 1 + same_industry로는 confirmed 불가 (probable까지만)

probable 조건:
  - Tier 1 소스 1개 + same_industry 보강
  - 또는 Tier 1 소스 1개만 (보강 없이)

weak 조건:
  - Tier 2(same_industry 등) 또는 Tier 3만

⚠️ same_industry 단독으로는 probable 이상 불가.
⚠️ confirmed는 반드시 독립 Tier 1 소스 2개. 초기 false positive 방지 우선.
stale 임계: 180일
```

### `SUPPLIES_TO`

```
confirmed 조건:
  - Tier 1 (manual_seed, provenance 있음) 단독 가능
  - 또는 Tier 1 + Tier 2 조합 (예: manual_seed_unverified + gemini_extracted)

probable 조건:
  - Tier 2 (gemini_extracted) 1개만
  - 또는 Tier 2 × 2개 (예: gemini_extracted + 보조 Tier 2)
  - 또는 manual_seed_unverified (provenance 없음) 단독

weak 조건:
  - Tier 3 (news_sc_keyword, news_comention) 만

⚠️ Tier 3 단독으로는 절대 confirmed 불가.
⚠️ gemini_raw (미검증 LLM 추출)로는 probable 이상 불가.
⚠️ Tier 2 × 2로는 confirmed 불가. 공급망 오탐 시 타격이 크므로 보수적 운영.

stale 임계: 180일
canonical 저장: SUPPLIES_TO만 저장. CUSTOMER_OF는 API에서 역방향 view로 파생.
```

### `COMPETES_WITH`

```
confirmed 조건:
  - Tier 1 (peer) 독립 소스 2개 이상
  - same_industry는 선택적 보강. 없어도 confirmed 가능.
  - same_industry만으로는 confirmed 불가.

probable 조건:
  - Tier 1 (peer) 1개 + same_industry 보강
  - 또는 Tier 1 (peer) 2개이나 industry가 다름 (의외의 경쟁)

weak 조건:
  - same_industry만
  - Tier 3만

stale 임계: 90일
```

### `PRICE_CORRELATED` (Market 관계)

```
⚠️ truth_score 비대상. confirmed 불가.
⚠️ 판정 기준은 evidence count가 아니라 raw metric(상관계수 값, 기간, 최근성).

probable 조건:
  - 90일 correlation ≥ 0.7 + 다른 Truth 관계가 이미 confirmed 상태로 존재

weak 조건:
  - 90일 correlation ≥ 0.7 단독
  - 30일 correlation만 (기간 무관)

hidden 조건:
  - correlation < 0.5

참고: evidence_sources JSONB에 corr 값과 기간을 raw_value로 저장.
      count가 아닌 corr 값으로 상태를 판정한다.

stale 임계: 30일
```

### `CO_MENTIONED` (Market 관계)

```
⚠️ truth_score 비대상. confirmed 불가.

weak 조건:
  - co_mention_count ≥ 3 (최근 90일)

probable 승격 조건:
  - co_mention_count ≥ 5 + 다른 Truth 관계가 이미 존재

hidden 조건:
  - co_mention_count < 3 또는 90일 이상 새 co-mention 없음

stale 임계: 14일
```

### `HAS_THEME`

```
confirmed 조건:
  - ETF holdings에서 실제 포함 확인 (Tier 1: etf_holding)

probable 조건:
  - industry 키워드 매칭 기반 추정 (Tier 2: theme_inferred)

UI 구분: confirmed → ✅ 확정 테마 / probable → ⚠️ 추정 테마
stale 임계: 90일
```

---

## 6.1 Confirmed 규칙 요약표 (빠른 참조)

| 관계 타입        | 최소 confirmed 조건                                  | same_industry 역할      | Tier 3 단독 최대 | stale 임계 |
| ---------------- | ---------------------------------------------------- | ----------------------- | ---------------- | ---------- |
| BELONGS*TO*\*    | 항상 confirmed                                       | N/A                     | N/A              | N/A        |
| PEER_OF          | Tier 1 × 2 (독립 소스 필수)                          | probable 보강만         | weak             | 180일      |
| SUPPLIES_TO      | Tier 1(manual+provenance) 단독, 또는 Tier 1 + Tier 2 | 비해당                  | weak             | 180일      |
| COMPETES_WITH    | Tier 1(peer) × 2                                     | 선택적 보강 (필수 아님) | weak             | 90일       |
| PRICE_CORRELATED | confirmed 불가 (Market, raw metric 기준)             | 비해당                  | hidden           | 30일       |
| CO_MENTIONED     | confirmed 불가 (Market, count 기준)                  | 비해당                  | hidden           | 14일       |
| HAS_THEME        | ETF holding 확인                                     | 비해당                  | probable(추정)   | 90일       |

---

## 7. RelationConfidence Django 모델 스키마 (v2.1)

v2에서 보강된 점: bool 필드 분리, truth_score 단순화, Market 관계 처리.

```python
class RelationConfidence(models.Model):
    """
    종목 간 관계의 신뢰도 종합 판정.
    Chain Sight 관계 엔진의 핵심 테이블.

    판정 철학: docs/chain_sight/RELATION_CONFIDENCE.md 참조.
    """

    # ── 관계 식별 ──
    symbol_a = models.CharField(max_length=20, db_index=True)
    symbol_b = models.CharField(max_length=20, db_index=True)
    relation_type = models.CharField(max_length=50, db_index=True)

    canonical_direction = models.CharField(
        max_length=20, default='undirected'
    )
    # "undirected": PEER_OF, COMPETES_WITH, PRICE_CORRELATED, CO_MENTIONED
    #   → 저장 시 symbol_a < symbol_b 사전순 강제 (원칙 6)
    # "a_to_b": SUPPLIES_TO (a가 b에 공급)
    # CUSTOMER_OF는 별도 저장하지 않음 → API에서 역방향 view로 파생

    relation_category = models.CharField(
        max_length=10, default='truth'
    )
    # "truth": PEER_OF, SUPPLIES_TO, COMPETES_WITH, HAS_THEME, BELONGS_TO_*
    # "market": PRICE_CORRELATED, CO_MENTIONED
    # truth_score는 relation_category == "truth"인 경우만 계산

    # ── 상태 ──
    relation_status = models.CharField(
        max_length=20, default='hidden',
        db_index=True
    )
    # "hidden" / "weak" / "probable" / "confirmed" / "stale"

    # ── 점수 ──
    truth_score = models.IntegerField(null=True, blank=True)
    # Truth 관계만 사용. 상태의 숫자 표현 (정밀 점수가 아님).
    # confirmed=85, probable=60, weak=35, hidden=15
    # Market 관계는 null.

    market_score = models.IntegerField(null=True, blank=True)
    # MVP에서는 null. Phase B/C에서 계산.

    investment_relevance = models.IntegerField(null=True, blank=True)
    # MVP에서는 null. truth + market 둘 다 있을 때 계산.

    # ── 증거 요약 ──
    evidence_tier_best = models.IntegerField(default=3)
    # 이 관계에 기여한 증거 중 최고 Tier (1, 2, 3)

    evidence_count_total = models.IntegerField(default=0)
    evidence_count_independent = models.IntegerField(default=0)

    evidence_sources = models.JSONField(default=list)
    # MVP에서는 JSONB로 저장.
    # evidence 개수가 종목쌍당 10개 이상 쌓이거나
    # 감사 추적이 중요해지면 RelationEvidence 별도 테이블로 분리한다.

    # ── 소스별 존재 여부 (빠른 필터용) ──
    has_peer_source = models.BooleanField(default=False)        # fmp_peer 또는 finnhub_peer
    has_industry_source = models.BooleanField(default=False)    # same_industry, fmp_industry
    has_supply_chain_source = models.BooleanField(default=False)  # manual_seed, gemini_extracted
    has_news_source = models.BooleanField(default=False)        # news_comention, news_sc_keyword
    has_price_source = models.BooleanField(default=False)       # price_corr_*
    has_etf_source = models.BooleanField(default=False)         # etf_holding
    has_llm_source = models.BooleanField(default=False)         # gemini_extracted, gemini_raw

    # ── 설명 ──
    relation_basis_summary = models.TextField(blank=True, default='')

    # ── 시간 ──
    first_observed_at = models.DateTimeField(auto_now_add=True)
    last_observed_at = models.DateTimeField(auto_now=True)
    last_verified_at = models.DateTimeField(null=True, blank=True)
    stale_threshold_days = models.IntegerField(default=180)

    # ── Neo4j 동기화 ──
    synced_to_neo4j = models.BooleanField(default=False)
    neo4j_synced_at = models.DateTimeField(null=True, blank=True)

    # ── 점수 버전 ──
    score_version = models.IntegerField(default=1)

    class Meta:
        db_table = 'chainsight_relation_confidence'
        unique_together = ('symbol_a', 'symbol_b', 'relation_type')
        indexes = [
            models.Index(fields=['relation_status']),
            models.Index(fields=['relation_type', 'relation_status']),
            models.Index(fields=['relation_category']),
            models.Index(fields=['evidence_tier_best']),
        ]

    def save(self, *args, **kwargs):
        # undirected 관계는 사전순 정규화 강제
        if self.canonical_direction == 'undirected':
            if self.symbol_a > self.symbol_b:
                self.symbol_a, self.symbol_b = self.symbol_b, self.symbol_a
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.symbol_a} → {self.symbol_b} "
            f"[{self.relation_type}] "
            f"{self.relation_status} "
            f"(tier={self.evidence_tier_best})"
        )
```

### v2 → v2.1 변경 사항

| 항목                | v2                       | v2.1                               | 이유                                         |
| ------------------- | ------------------------ | ---------------------------------- | -------------------------------------------- |
| industry 필드       | `has_peer_source`로 대신 | `has_industry_source` 별도 분리    | peer와 industry는 완전히 다른 신호           |
| `relation_category` | 없음                     | `truth` / `market` 구분 필드 추가  | truth_score 계산 대상을 스키마 레벨에서 구분 |
| truth_score 의미    | 0~100 세밀 점수          | 상태 대표값 (85/60/35/15)          | 점수 차이에 의미를 부여하지 않음             |
| `save()` override   | 없음                     | undirected 사전순 정규화 자동 적용 | 중복 방지                                    |

---

## 8. CUSTOMER_OF 처리 규칙

> v1과 동일. 변경 없음.

`CUSTOMER_OF`는 별도 row로 저장하지 않는다.

```
저장 (DB):
  symbol_a = "TSM", symbol_b = "AAPL"
  relation_type = "SUPPLIES_TO", canonical_direction = "a_to_b"

API 응답 (TSM 기준): { "type": "SUPPLIES_TO" }
API 응답 (AAPL 기준): { "type": "CUSTOMER_OF" }  ← 파생
```

---

## 9. Manual Seed 작성 프로토콜

manual_seed가 Tier 1인 이유는 seed 자체가 아니라 이 프로토콜을 신뢰하기 때문이다.
프로토콜을 따르지 않은 seed는 `manual_seed_unverified`로 Tier 2 강등.

### 필수 규칙

1. 모든 seed 관계에는 `provenance` 필드가 반드시 포함되어야 한다.
2. provenance에는 **구체적인 근거 출처**를 명시한다.
3. "알려진 사실이라서", "유명한 관계라서" 같은 주관적 근거는 불인정.

### 허용 근거 유형

| 근거 유형                | 예시                                                    | Tier       |
| ------------------------ | ------------------------------------------------------- | ---------- |
| 공식 IR/연차보고서       | "TSMC 2024 Annual Report, Apple listed as top customer" | 1          |
| SEC 10-K 명시            | "AAPL 10-K 2024, TSMC mentioned in supply risk section" | 1          |
| 복수 주요 언론 반복 보도 | "Reuters, Bloomberg 2024년 3건 이상 보도"               | 1          |
| 단일 기사/블로그         | "TechCrunch 2024-03-15 기사"                            | 2 (불충분) |
| 개인 판단/상식           | "누구나 아는 관계"                                      | 2 (불충분) |

### Seed JSON 구조 (provenance 필수)

```json
{
	"from": "TSM",
	"to": "AAPL",
	"type": "SUPPLIES_TO",
	"category": "semiconductor_foundry",
	"confidence": 0.95,
	"source": "manual_seed",
	"provenance": "TSMC 2024 Annual Report: Apple is largest customer (~25% revenue). SEC 10-K cross-reference.",
	"verified_date": "2026-04-01"
}
```

provenance가 없거나 허용 근거 기준 미달인 경우:

```json
{
	"source": "manual_seed_unverified",
	"provenance": "일반적으로 알려진 관계",
	"note": "Tier 2 강등. 보강 증거 필요."
}
```

---

## 10. truth_score 계산 규칙 (MVP)

### 설계 철학 (v1.1 변경)

truth_score는 **정밀한 연속 점수가 아니라 상태의 숫자 표현**이다.
같은 confirmed 안에서 90과 85의 차이는 의미 없다.
목적은 relation_status 결정 + 정렬/필터 편의용이다.

### 상태 대표값

| relation_status | truth_score 대표값                     |
| --------------- | -------------------------------------- |
| hidden          | 15                                     |
| weak            | 35                                     |
| probable        | 60                                     |
| confirmed       | 85                                     |
| stale           | 이전 점수 유지, relation_status만 변경 |

### 계산 함수

```python
def calculate_truth_and_status(relation: RelationConfidence) -> tuple[int | None, str]:
    """
    증거 등급 정책표 기반 truth_score + relation_status 계산.
    Market 관계는 truth_score = None.

    Returns: (truth_score, relation_status)
    """
    rtype = relation.relation_type

    # ── Market 관계: truth_score 비대상 ──
    if relation.relation_category == 'market':
        status = _calculate_market_status(relation)
        return (None, status)

    # ── BELONGS_TO_* ──
    if rtype in ('BELONGS_TO_SECTOR', 'BELONGS_TO_INDUSTRY'):
        return (85, 'confirmed')

    tier_best = relation.evidence_tier_best
    count_indep = relation.evidence_count_independent
    evidences = relation.evidence_sources or []
    source_types = [e.get('source_type', '') for e in evidences]

    # ── PEER_OF ──
    if rtype == 'PEER_OF':
        tier1_indep = sum(
            1 for st in source_types if st in ('fmp_peer', 'finnhub_peer')
        )
        if tier1_indep >= 2:
            return (85, 'confirmed')  # 독립 Tier 1 × 2 필수
        if tier1_indep == 1 and relation.has_industry_source:
            return (60, 'probable')   # Tier 1 + industry = probable (confirmed 아님)
        if tier1_indep == 1:
            return (60, 'probable')   # Tier 1 단독도 probable
        if tier_best == 2:
            return (35, 'weak')
        return (15, 'hidden')

    # ── SUPPLIES_TO ──
    if rtype == 'SUPPLIES_TO':
        has_manual_verified = 'manual_seed' in source_types
        has_manual_unverified = 'manual_seed_unverified' in source_types
        has_tier1 = has_manual_verified or has_manual_unverified
        has_tier2_non_manual = any(
            e.get('tier', 3) <= 2
            for e in evidences
            if e.get('source_type') not in ('manual_seed', 'manual_seed_unverified')
        )

        if has_manual_verified:
            return (85, 'confirmed')  # provenance 있는 manual = confirmed
        if has_manual_unverified and has_tier2_non_manual:
            return (85, 'confirmed')  # Tier 1(unverified) + Tier 2 = confirmed
        if has_manual_unverified:
            return (60, 'probable')   # unverified 단독 = probable
        if tier_best == 2:
            return (60, 'probable')   # Tier 2 × N = 최대 probable (confirmed 불가)
        return (35, 'weak')

    # ── COMPETES_WITH ──
    if rtype == 'COMPETES_WITH':
        peer_count = sum(1 for st in source_types if st in ('fmp_peer', 'finnhub_peer'))
        if peer_count >= 2:
            return (85, 'confirmed')
        if peer_count == 1 and relation.has_industry_source:
            return (60, 'probable')
        if peer_count == 1:
            return (35, 'weak')
        return (15, 'hidden')

    # ── HAS_THEME ──
    if rtype == 'HAS_THEME':
        if relation.has_etf_source:
            return (85, 'confirmed')
        return (60, 'probable')

    return (15, 'hidden')


def _calculate_market_status(relation: RelationConfidence) -> str:
    """
    Market 관계(PRICE_CORRELATED, CO_MENTIONED)의 상태만 판정.
    truth_score는 부여하지 않음.
    """
    rtype = relation.relation_type
    evidences = relation.evidence_sources or []

    if rtype == 'PRICE_CORRELATED':
        # PRICE_CORRELATED는 count가 아닌 raw metric(상관계수)으로 판정.
        # evidence_sources에서 corr 값을 읽는다.
        best_corr = 0.0
        for ev in evidences:
            raw = ev.get('raw_value', {})
            corr = raw.get('correlation', 0.0) if isinstance(raw, dict) else 0.0
            best_corr = max(best_corr, abs(corr))

        if best_corr >= 0.7:
            return 'weak'   # MVP에서 단독 최대 weak
        if best_corr >= 0.5:
            return 'hidden' # 약한 동조는 기록만
        return 'hidden'

    if rtype == 'CO_MENTIONED':
        # CO_MENTIONED는 count 기반 판정.
        count = relation.evidence_count_total
        if count >= 3:
            return 'weak'
        return 'hidden'

    return 'hidden'
```

---

## 11. relation_basis_summary 생성 (템플릿 기반)

> v1과 동일한 구조. 일부 템플릿 추가.

```python
TEMPLATES = {
    'peer_confirmed_dual': (
        "두 개의 독립 소스({sources})에서 peer 관계가 반복 확인됨."
    ),
    'peer_probable_single': (
        "{source}에서 peer 관계 확인. 추가 소스 보강 시 confirmed 예정."
    ),
    'supply_manual_confirmed': (
        "수동 검증된 공급망 관계. 근거: {provenance}"
    ),
    'supply_manual_unverified': (
        "수동 등록 공급망 관계이나 근거 문서 미비. 보강 증거 확보 시 confirmed 승격 가능."
    ),
    'supply_extracted_probable': (
        "AI 추출(Gemini Flash)로 발견된 공급 관계. 검증 통과. "
        "추가 증거 확보 시 confirmed 승격 가능."
    ),
    'compete_confirmed': (
        "복수 독립 소스에서 경쟁 관계 확인. peer 소스: {peer_sources}."
    ),
    'market_price_weak': (
        "최근 {period}일 가격 상관계수 {corr}. "
        "시장 현상 기반 관계. 구조적 관계 증거는 별도."
    ),
    'market_comention_weak': (
        "최근 90일 뉴스 동시출현 {count}회. "
        "뉴스 흐름 기반 관찰. 구조적 관계 증거는 별도."
    ),
    'theme_confirmed': (
        "{etf} ETF에 포함 확인. 테마: {theme}."
    ),
    'theme_inferred': (
        "산업 분류 기반 테마 추정. ETF holdings 확인 시 승격 가능."
    ),
    'stale_warning': (
        "마지막 검증: {last_verified}. {days}일 경과. 새 증거 없이 stale 전환됨."
    ),
}
```

---

## 12. API 설명 응답 (CS-4 보강)

> v1과 동일. 변경 없음.

그래프 탐색 API 응답에 explanation 포함. Market 관계는 보강 라벨로 표시.

```json
{
	"edges": [
		{
			"from": "NVDA",
			"to": "AMD",
			"type": "PEER_OF",
			"category": "truth",
			"status": "confirmed",
			"truth_score": 85,
			"explanation": {
				"summary": "두 개의 독립 소스(FMP, Finnhub)에서 peer 관계가 반복 확인됨.",
				"evidence_tier": 1,
				"evidence_count": 2,
				"last_verified": "2026-03-31"
			},
			"market_signals": [
				{
					"type": "PRICE_CORRELATED",
					"status": "weak",
					"detail": "90일 상관 0.78"
				}
			]
		}
	]
}
```

---

## 13. Stale 판정 및 관리

### stale_threshold_days 기본값

| 관계 타입        | stale 임계 (일) | probable→weak (×1.5) | weak→hidden (×2) |
| ---------------- | --------------- | -------------------- | ---------------- |
| PEER_OF          | 180             | 270                  | 360              |
| SUPPLIES_TO      | 180             | 270                  | 360              |
| COMPETES_WITH    | 90              | 135                  | 180              |
| PRICE_CORRELATED | 30              | 45                   | 60               |
| CO_MENTIONED     | 14              | 21                   | 28               |
| HAS_THEME        | 90              | 135                  | 180              |

### 시간 경과에 따른 하향 규칙

```
confirmed → stale   : stale_threshold_days 초과
probable  → weak    : stale_threshold_days × 1.5 초과
weak      → hidden  : stale_threshold_days × 2 초과
```

새로운 증거가 추가되면 last_verified_at이 갱신되어 하향이 리셋된다.

### MVP stale 관리 구현

```python
def check_stale_and_decay():
    """주 1회 실행. 오래된 관계를 하향 전이."""
    from django.utils import timezone
    now = timezone.now()

    relations = RelationConfidence.objects.filter(
        last_verified_at__isnull=False
    ).exclude(
        relation_status='hidden'
    ).exclude(
        relation_type__in=('BELONGS_TO_SECTOR', 'BELONGS_TO_INDUSTRY')
    )

    for rel in relations:
        days = (now - rel.last_verified_at).days
        threshold = rel.stale_threshold_days
        old_status = rel.relation_status

        new_status = old_status
        if old_status == 'confirmed' and days > threshold:
            new_status = 'stale'
        elif old_status == 'probable' and days > threshold * 1.5:
            new_status = 'weak'
        elif old_status == 'weak' and days > threshold * 2:
            new_status = 'hidden'

        if new_status != old_status:
            rel.relation_status = new_status
            rel.relation_basis_summary += (
                f"\n[{now.date()}] {days}일 경과, "
                f"{old_status}→{new_status} 하향 전이."
            )
            rel.save(update_fields=[
                'relation_status', 'relation_basis_summary'
            ])
```

decay 함수(half-life)는 MVP에서 구현하지 않는다.
`last_verified_at`을 기록해두면 나중에 decay를 붙일 때 데이터가 준비됨.

---

## 14. evidence_sources JSONB 구조

> v1과 동일. source_family 분류 유지.

### 확장 경로 명시

MVP에서는 `evidence_sources`를 JSONB 필드로 저장한다.
**evidence 개수가 종목쌍당 10개 이상 쌓이거나, 감사 추적(audit trail)이 중요해지면
`RelationEvidence` 별도 테이블로 분리한다.**

분리 시 구조:

```
RelationConfidence (1) ←→ (N) RelationEvidence
  FK: relation_confidence_id
  각 evidence row: source_type, tier, observed_at, detail, provenance_ref
```

이 문장을 넣어두면 미래 확장 경로가 선명해지고,
지금은 JSONB의 단순함을 유지할 수 있다.

### source_family 분류

| family       | 포함 source_type                                                                                      |
| ------------ | ----------------------------------------------------------------------------------------------------- |
| `structural` | fmp_peer, finnhub_peer, fmp_industry, same_industry, manual_seed, manual_seed_unverified, etf_holding |
| `market`     | price_corr_90d, price_corr_30d                                                                        |
| `news`       | news_comention, news_sc_keyword                                                                       |
| `extracted`  | gemini_extracted, gemini_raw                                                                          |

### evidence_count_independent 계산

```python
def count_independent(evidence_sources: list[dict]) -> int:
    """
    같은 source_family 내에서는 최대 2개까지만 독립 증거로 인정.
    """
    family_counts: dict[str, int] = {}
    for ev in evidence_sources:
        family = ev.get('source_family', 'unknown')
        family_counts[family] = family_counts.get(family, 0) + 1

    return sum(min(count, 2) for count in family_counts.values())
```

---

## 15. MVP 구현 우선순위

### Phase A — CS-2 착수 시 (최소 필수)

```
□ RelationConfidence v2.1 모델 마이그레이션
□ normalize_pair 유틸 함수 (undirected 사전순)
□ evidence_sources JSONB 구조 확정
□ Tier 1/2/3 분류 적용 (DC-1 데이터부터)
□ calculate_truth_and_status 함수 (규칙 기반, 상태 대표값)
□ relation_basis_summary 템플릿 10개
□ CUSTOMER_OF 별도 저장 제거 → API 역방향 파생
□ manual_seed provenance 규칙 적용 (DC-3 시점)
```

### Phase B — CS-3~4 시 (API 보강)

```
□ stale + 하향 전이 Celery task (confirmed→stale, probable→weak, weak→hidden)
□ API 응답에 explanation + market_signals 포함
□ Market 관계(PRICE_CORRELATED, CO_MENTIONED)를 Truth 관계의 보강 라벨로 연결
□ score_version 관리
```

### Phase C — CS-5 이후 (풍부화)

```
□ market_score 계산 (price_correlation + event_reaction + co_mention 입력)
□ investment_relevance 계산 (truth + market 종합)
□ UI에서 confirmed/probable/weak 시각 구분
□ stale → decay 함수 전환 검토
□ evidence_sources → RelationEvidence 분리 검토
```

---

## 16. 로드맵 v1.2와의 연결

| 로드맵 항목                    | 이 문서의 영향                                                      |
| ------------------------------ | ------------------------------------------------------------------- |
| CS-0-1 migrations              | RelationConfidence v2.1 스키마로 마이그레이션                       |
| CS-2-4 RelationConfidence 종합 | 섹션 10 규칙 + 섹션 6 정책표로 구현                                 |
| CS-3-2 Neo4j 엣지 동기화       | relation_status == 'confirmed' 또는 'probable'만 동기화             |
| CS-4-1~3 API                   | 섹션 12의 explanation + market_signals 응답                         |
| CS-5 프론트엔드                | 상태별 UI 노출 규칙 (섹션 5)                                        |
| DC-3 수동 시드                 | source_type = "manual_seed", tier = 1, **provenance 필수** (섹션 9) |
| DC-4 Gemini Flash              | source_type = "gemini_extracted", tier = 2                          |
| DC-5 뉴스 축적                 | source_type = "news_comention", tier = 3, **Market 관계로 분류**    |

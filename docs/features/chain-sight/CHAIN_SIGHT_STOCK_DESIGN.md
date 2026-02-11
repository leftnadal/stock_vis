# Chain Sight Stock - 개별 종목 연관 탐색

## 개요

Chain Sight Stock은 개별 주식 페이지에서 AI가 관계 카테고리를 제안하고, 사용자가 선택하면 관련 종목 + 인사이트를 보여주는 "파도타기" 탐험 기능입니다.

### 핵심 플로우
```
NVDA 페이지 진입 → AI 카테고리 제안 ["경쟁사(5)", "AI 반도체 생태계(8)"]
→ 사용자 "AI 반도체 생태계" 선택 → SMCI, ARM, TSM 카드 표시
→ SMCI 클릭 → SMCI 페이지로 "파도타기" → 반복
```

---

## 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│ Frontend: /stocks/[symbol] → ChainSightExplorer 탭      │
│   ├── CategorySelector (카테고리 칩)                    │
│   ├── RelatedStockGrid (종목 카드)                      │
│   └── AIInsightPanel (인사이트 + 후속질문)              │
└─────────────────────────────────────────────────────────┘
                         │ REST API
                         ▼
┌─────────────────────────────────────────────────────────┐
│ Backend: serverless/                                     │
│   ├── ChainSightStockService (메인 서비스)              │
│   ├── CategoryGenerator (AI 카테고리 생성)             │
│   └── RelationshipService (관계 쿼리/동기화)            │
└─────────────────────────────────────────────────────────┘
         │              │              │
         ▼              ▼              ▼
    [FMP API]     [NewsEntity]   [Redis Cache]
```

---

## 관계 타입 (Relationship Types)

| 타입 | 설명 | 데이터 소스 |
|------|------|-------------|
| **PEER_OF** | 경쟁사 | FMP `/stable/stock-peers` |
| **SAME_INDUSTRY** | 동일 산업 | FMP `/stable/company-screener` |
| **CO_MENTIONED** | 뉴스 동시언급 | NewsEntity 모델 |

### PEER_OF vs SAME_INDUSTRY 차이
- **PEER_OF**: FMP가 분석한 실제 경쟁사 (예: AAPL → GOOGL, META, MSFT)
- **SAME_INDUSTRY**: 같은 산업 분류 내 모든 기업 (예: AAPL → SONY, LPL 등)

---

## 카테고리 Tier 시스템

| Tier | 설명 | 생성 방식 | 예시 |
|------|------|----------|------|
| **0** | DB 쿼리 기반 | StockRelationship 조회 | 경쟁사 (5개), 동일 산업 (12개), 뉴스 연관 (3개) |
| **1** | AI 산업 맥락 | 프로필 분석 + 테마 매칭 | EUV 기술 생태계, CUDA 플랫폼 |
| **2** | AI 동적 생성 | 뉴스/설명 키워드 분석 | 반독점 규제 관련, AI 투자 수혜 |

### Tier 1 테마 목록
- `ai_ecosystem`: AI 생태계
- `ev_ecosystem`: EV 생태계
- `cloud_ecosystem`: 클라우드 생태계
- `fintech_ecosystem`: 핀테크 생태계
- `biotech_ecosystem`: 바이오테크 생태계
- `gaming_ecosystem`: 게이밍 생태계
- `5g_ecosystem`: 5G/통신 생태계
- `renewable_ecosystem`: 재생에너지 생태계
- `sector_leaders`: 섹터 리더 (시가총액 $100B+)

---

## 백엔드 구현

### 모델

**StockRelationship** - 종목 간 관계 저장
```python
class StockRelationship(models.Model):
    source_symbol = models.CharField(max_length=10, db_index=True)
    target_symbol = models.CharField(max_length=10, db_index=True)
    relationship_type = models.CharField(max_length=20)  # PEER_OF, SAME_INDUSTRY, CO_MENTIONED
    strength = models.DecimalField(max_digits=4, decimal_places=3, default=1.0)
    source_provider = models.CharField(max_length=20)  # fmp, news
    context = models.JSONField(default=dict)
    discovered_at = models.DateTimeField(auto_now_add=True)
    last_verified_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [['source_symbol', 'target_symbol', 'relationship_type']]
```

**CategoryCache** - AI 생성 카테고리 캐시
```python
class CategoryCache(models.Model):
    symbol = models.CharField(max_length=10, db_index=True)
    date = models.DateField(db_index=True)
    categories = models.JSONField(default=list)
    expires_at = models.DateTimeField()  # 24시간 후 자동 만료

    class Meta:
        unique_together = [['symbol', 'date']]
```

### 서비스

| 서비스 | 파일 | 역할 |
|--------|------|------|
| **RelationshipService** | `relationship_service.py` | FMP/NewsEntity에서 관계 동기화 |
| **CategoryGenerator** | `category_generator.py` | Tier 0/1/2 카테고리 생성 |
| **ChainSightStockService** | `chain_sight_stock_service.py` | 메인 서비스, API 응답 조합 |

### API 엔드포인트

```bash
# 카테고리 목록 조회
GET /api/v1/serverless/chain-sight/stock/{symbol}

# 카테고리별 종목 조회
GET /api/v1/serverless/chain-sight/stock/{symbol}/category/{category_id}

# 관계 동기화 (수동)
POST /api/v1/serverless/chain-sight/stock/{symbol}/sync
```

### 응답 예시

**카테고리 목록**
```json
{
    "success": true,
    "data": {
        "symbol": "NVDA",
        "company_name": "NVIDIA Corporation",
        "categories": [
            {
                "id": "peer",
                "name": "경쟁사",
                "tier": 0,
                "count": 5,
                "icon": "users",
                "description": "FMP가 분석한 NVDA의 주요 경쟁사"
            },
            {
                "id": "ai_ecosystem",
                "name": "AI 생태계",
                "tier": 1,
                "count": 8,
                "icon": "brain",
                "is_dynamic": true,
                "description": "NVDA와 함께 AI 생태계를 구성하는 기업들"
            }
        ],
        "is_cold_start": false
    }
}
```

**카테고리 종목**
```json
{
    "success": true,
    "data": {
        "category": {
            "id": "peer",
            "name": "경쟁사"
        },
        "stocks": [
            {
                "symbol": "AMD",
                "company_name": "Advanced Micro Devices",
                "relationship_strength": 0.85,
                "current_price": 125.50,
                "change_percent": 2.3,
                "market_cap": 200000000000,
                "sector": "Technology"
            }
        ],
        "ai_insights": "AMD는 NVDA의 주요 GPU 경쟁사로, 데이터센터와 게이밍 시장에서 경쟁합니다.",
        "follow_up_questions": [
            "경쟁사들의 밸류에이션을 비교해볼까요?",
            "GPU 시장 점유율 추이가 궁금하신가요?"
        ]
    }
}
```

---

## Celery 태스크

### 스케줄

| 태스크 | 스케줄 | 설명 |
|--------|--------|------|
| `batch_sync_stock_relationships` | 매일 05:00 EST | 주요 종목 관계 배치 동기화 |
| `cleanup_expired_category_cache` | 매일 06:00 EST | 만료된 CategoryCache 정리 |

### 사용법

```python
from serverless.tasks import sync_stock_relationships, batch_sync_stock_relationships

# 개별 종목 동기화
sync_stock_relationships.delay('NVDA')

# 배치 동기화
batch_sync_stock_relationships.delay(['AAPL', 'MSFT', 'GOOGL'])
```

---

## 프론트엔드 구현

### 파일 구조

```
frontend/
├── components/chain-sight/
│   ├── ChainSightExplorer.tsx    # 메인 컨테이너
│   ├── CategorySelector.tsx      # 카테고리 칩/카드
│   ├── RelatedStockGrid.tsx      # 종목 그리드
│   ├── RelatedStockCard.tsx      # 개별 종목 카드
│   ├── AIInsightPanel.tsx        # 인사이트 패널
│   └── index.ts
├── hooks/
│   ├── useChainSightCategories.ts
│   └── useChainSightStocks.ts
├── services/
│   └── chainSightService.ts
└── types/
    └── chainSight.ts
```

### 타입 정의

```typescript
interface ChainSightCategory {
  id: string;
  name: string;
  tier: 0 | 1 | 2;
  count: number;
  description: string;
  icon: string;
  is_dynamic?: boolean;
  sector?: string;
}

interface ChainSightStock {
  symbol: string;
  company_name: string;
  relationship_strength: number;
  current_price: number;
  change_percent: number;
  market_cap?: number;
  sector?: string;
  industry?: string;
}

interface ChainSightCategoryStocks {
  category: Pick<ChainSightCategory, 'id' | 'name'>;
  stocks: ChainSightStock[];
  ai_insights: string;
  follow_up_questions: string[];
}
```

### 주식 상세 페이지 통합

`frontend/app/stocks/[symbol]/page.tsx`에 Chain Sight 탭 추가:

```tsx
import { Compass } from 'lucide-react';
import { ChainSightExplorer } from '@/components/chain-sight';

// 탭 정의에 추가
const tabs = [
  // ... 기존 탭들 ...
  { id: 'chain-sight' as TabType, label: 'Chain Sight', icon: Compass },
];

// 탭 콘텐츠
{activeTab === 'chain-sight' && (
  <ChainSightExplorer symbol={symbol.toUpperCase()} />
)}
```

---

## Cold Start 처리

관계 데이터가 없는 종목 첫 방문 시:

1. **즉시 응답**: "동일 산업" 카테고리만 반환 (FMP screener ~2초)
2. **백그라운드**: `sync_stock_relationships.delay(symbol)` 트리거
3. **후속 요청**: 전체 카테고리 표시

```python
# 최소 카테고리 보장
if is_cold_start:
    return {
        "categories": [{
            "id": "same_industry",
            "name": "동일 산업",
            "count": "?",
            "description": "관계 데이터 로딩 중...",
            "is_loading": True
        }],
        "is_cold_start": True
    }
```

---

## 강도 계산 (Strength)

### 시가총액 유사도 (PEER_OF, SAME_INDUSTRY)
```python
def _calculate_market_cap_similarity(source_mc, target_mc):
    # 로그 스케일 비교 (최대 2 orders of magnitude 허용)
    log_diff = abs(log10(source_mc) - log10(target_mc))
    return max(0, 1 - log_diff / 2)  # 0.0 ~ 1.0
```

| 시가총액 차이 | 유사도 |
|--------------|--------|
| 동일 | 1.0 |
| 10배 | 0.5 |
| 100배+ | 0.0 |

### 동시언급 강도 (CO_MENTIONED)
```python
# 정규화된 언급 횟수
strength = mention_count / max_mentions_in_period
```

---

## 테스트

### 단위 테스트
```bash
pytest tests/serverless/test_chain_sight_stock_service.py -v
```

**테스트 커버리지**: 24개 테스트
- RelationshipService: 시가총액 유사도 계산 (4개)
- CategoryGenerator: Tier 0/1 카테고리 생성 (8개)
- ChainSightStockService: 인사이트/후속질문 생성 (7개)
- Django 모델: StockRelationship, CategoryCache (5개)

### API 테스트
```bash
# 카테고리 조회
curl http://localhost:8000/api/v1/serverless/chain-sight/stock/NVDA

# 경쟁사 종목 조회
curl http://localhost:8000/api/v1/serverless/chain-sight/stock/NVDA/category/peer

# 관계 동기화
curl -X POST http://localhost:8000/api/v1/serverless/chain-sight/stock/NVDA/sync
```

---

## FMP API 사용

| 엔드포인트 | 용도 | 캐시 TTL |
|----------|------|----------|
| `/stable/stock-peers` | 경쟁사 목록 | 24시간 |
| `/stable/company-screener` | 산업별 종목 | 5분 |
| `/stable/profile` | 종목 프로필 | 24시간 |
| `/stable/quote` | 실시간 시세 | 1분 |

---

## Neo4j 온톨로지 통합

Chain Sight는 PostgreSQL + Neo4j 하이브리드 아키텍처를 사용합니다.
Neo4j 우선 사용, PostgreSQL fallback으로 안정성 보장.

### 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│ ChainSightStockService                                       │
│   └── _get_relationship_stocks()                            │
│         ├── Neo4j 우선 조회 ───▶ Neo4jChainSightService     │
│         │                              │                     │
│         │                              ▼                     │
│         │                       [Neo4j Graph DB]             │
│         │                       - Stock 노드 (75+)           │
│         │                       - PEER_OF, SAME_INDUSTRY     │
│         │                       - N-depth 그래프 탐색        │
│         │                              │                     │
│         └── PostgreSQL fallback ──────┘ (Neo4j 불가 시)     │
│                   │                                          │
│                   ▼                                          │
│            [PostgreSQL]                                      │
│            - StockRelationship 테이블                        │
└─────────────────────────────────────────────────────────────┘
```

### Neo4j 노드 타입

| 노드 | 속성 | 설명 |
|------|------|------|
| **Stock** | symbol, name, sector, industry, market_cap | 개별 종목 |
| **Sector** | name, display_name | 섹터 (Technology, Healthcare 등) |
| **Industry** | name, sector | 산업 (Semiconductors 등) |

### Neo4j 관계 타입

| 관계 | 방향 | 속성 | 설명 |
|------|------|------|------|
| **PEER_OF** | Stock → Stock | weight, source, context_json | 경쟁사 |
| **SAME_INDUSTRY** | Stock → Stock | weight, industry | 동일 산업 |
| **CO_MENTIONED** | Stock → Stock | weight, mention_count | 뉴스 동시언급 |
| **BELONGS_TO_SECTOR** | Stock → Sector | - | 섹터 소속 |
| **BELONGS_TO_INDUSTRY** | Stock → Industry | - | 산업 소속 |

### 그래프 API 엔드포인트

```bash
# N-depth 그래프 조회 (시각화용)
GET /api/v1/serverless/chain-sight/graph/{symbol}?depth=2

# Neo4j 동기화 트리거
POST /api/v1/serverless/chain-sight/graph/{symbol}/sync

# 그래프 통계
GET /api/v1/serverless/chain-sight/graph/stats
```

### 그래프 응답 예시 (react-force-graph 호환)

```json
{
    "nodes": [
        {"id": "NVDA", "name": "NVIDIA", "sector": "Technology", "group": "center"},
        {"id": "AMD", "name": "AMD", "sector": "Technology", "group": "related"}
    ],
    "edges": [
        {"source": "NVDA", "target": "AMD", "type": "PEER_OF", "weight": 0.85}
    ],
    "metadata": {
        "depth": 2,
        "total_nodes": 29,
        "total_edges": 34
    }
}
```

### 마이그레이션 커맨드

```bash
# 전체 PostgreSQL → Neo4j 마이그레이션
python manage.py migrate_chain_sight_to_neo4j --all

# 특정 종목만 마이그레이션
python manage.py migrate_chain_sight_to_neo4j --symbol NVDA

# 통계 확인
python manage.py migrate_chain_sight_to_neo4j --stats

# 드라이런 (변경 없이 확인만)
python manage.py migrate_chain_sight_to_neo4j --all --dry-run
```

### Neo4j 서비스 사용법

```python
from serverless.services.neo4j_chain_sight_service import Neo4jChainSightService

service = Neo4jChainSightService()

# 연결 확인
if service.is_available():
    # 관련 종목 조회
    related = service.get_related_stocks('NVDA', rel_type='PEER_OF', limit=10)

    # N-depth 그래프 조회
    graph = service.get_n_depth_graph('NVDA', depth=2)

    # PostgreSQL에서 동기화
    result = service.sync_from_postgres('NVDA')
    print(f"Synced: {result['synced']}, Failed: {result['failed']}")
```

### 환경 변수

```bash
# Neo4j 연결 (선택적 - 없으면 PostgreSQL만 사용)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
```

---

## Phase 로드맵

| Phase | 기능 | 상태 | 비용 |
|-------|------|------|------|
| 1 (MVP) | PEER_OF, SAME_INDUSTRY, CO_MENTIONED | ✅ 완료 | $0 |
| 1.5 | Neo4j 온톨로지 통합 | ✅ 완료 | $0 |
| 2 | 프론트엔드 그래프 시각화 (react-force-graph) | 예정 | $0 |
| 3 | ETF Holdings (HAS_THEME) | ✅ 완료 | $0 |
| 4 | Supply Chain (SUPPLIED_BY, CUSTOMER_OF) | 예정 | $0 |
| 5 | Gemini LLM 관계 추출 | 예정 | ~$5/월 |
| 6 | 뉴스 자연 축적 + 사용자 행동 Edge Weight | 예정 | $0 |
| 7 | Insider/Institution (HELD_BY_SAME_FUND) | 예정 | $0~30/월 |
| 8 | Regulatory + Patent Network | 예정 | $0 |

> 상세 로드맵: [CHAIN_SIGHT_ROADMAP.md](./CHAIN_SIGHT_ROADMAP.md)

# News-based Stock Insights (뉴스 기반 종목 인사이트)

## 개요

뉴스에서 언급된 종목을 팩트(사실) 중심으로 정리하여 보여주는 시스템.
"추천", "점수" 같은 주관적 표현 대신 뉴스 언급 횟수, 감성 분포, 시장 데이터를 표시.

## 핵심 원칙

| 제거 | 보여줄 것 |
|------|----------|
| 추천 점수, Score | 뉴스 언급 횟수 |
| 강한 추천, 약한 추천 | 감성 분포 (긍정/부정/중립) |
| 주관적 판단 | 키워드별 뉴스 헤드라인 |
| - | 시장 데이터 (52주 범위, MA, 밸류에이션) |

## 아키텍처

```
NewsEntity (PostgreSQL)
        │
        ▼
NewsBasedStockInsights (Service)
        │
        ├─ 뉴스 언급 수집 (symbol별)
        ├─ 감성 분포 계산 (positive/negative/neutral)
        ├─ 키워드 매칭 (DailyKeyword 연결)
        └─ 시장 데이터 조회 (Stock 모델)
        │
        ▼
REST API (/api/v1/news/insights/)
        │
        ▼
Frontend Components
        ├─ NewsHighlightedStocks (컨테이너)
        ├─ StockInsightCard (개별 종목)
        ├─ SentimentBar (감성 분포 차트)
        ├─ KeywordMentionList (키워드 + 뉴스)
        └─ MarketDataBadge (시장 데이터)
```

## 주요 파일

| 파일 | 역할 |
|------|------|
| `news/services/stock_insights.py` | 팩트 기반 인사이트 서비스 |
| `news/api/views.py` | `/insights/` 엔드포인트 |
| `frontend/types/news.ts` | StockInsight, SentimentDistribution 타입 |
| `frontend/components/news/NewsHighlightedStocks.tsx` | 인사이트 컨테이너 |
| `frontend/components/news/StockInsightCard.tsx` | 개별 종목 카드 |
| `frontend/components/news/SentimentBar.tsx` | 감성 분포 바 |
| `frontend/components/news/MarketDataBadge.tsx` | 시장 데이터 배지 |

## 용어 변경

| 기존 | 변경 |
|------|------|
| AI 추천 종목 | 뉴스 언급 종목 |
| StockRecommendations | NewsHighlightedStocks |
| RecommendationCard | StockInsightCard |
| 추천 점수 | (제거) |

---

## 뉴스 수집 카테고리 시스템

### 개요

관리자가 Admin Dashboard에서 뉴스 수집 카테고리를 정의하면, Celery Beat가 카테고리별 심볼을 자동 해석하여 Finnhub company-news를 수집.
기존 MarketMover 기반 수집(`collect_daily_news`)과 독립 병행.

### 카테고리 타입

| 타입 | 심볼 해석 | 예시 |
|------|----------|------|
| `sector` | `SP500Constituent.sector` 쿼리 | "Information Technology" → 68종목 |
| `sub_sector` | `SP500Constituent.sub_sector` 쿼리 | "Semiconductor Materials & Equipment" → 8종목 |
| `custom` | 관리자 직접 심볼 입력 | "TSLA,ALB,PANW" (S&P 500 외 종목 가능) |

### 우선순위 & 수집 주기

| Priority | 수집 주기 | Celery Beat |
|----------|----------|-------------|
| `high` | 2회/일 (06:30 + 17:00 EST, 평일) | `collect-category-news-high-morning/evening` |
| `medium` | 1회/일 (07:00 EST, 평일) | `collect-category-news-medium` |
| `low` | 주 1회 (월요일 07:30 EST) | `collect-category-news-low` |

### 모델

- **NewsCollectionCategory** (`news/models.py`): name, category_type, value, priority, max_symbols, 수집 통계
- `resolve_symbols()`: 타입별 심볼 리스트 해석

### 태스크

- **collect_category_news** (`news/tasks.py`): category_id 또는 priority_filter 기준 수집
- 카테고리간 심볼 dedup → 심볼별 1회만 fetch → 카테고리별 통계 업데이트
- `time.sleep(2)`: Finnhub 60/min 준수

### Admin API

| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| GET/POST | `/serverless/admin/dashboard/news/categories/` | 카테고리 목록 / 생성 |
| PUT/DELETE | `/serverless/admin/dashboard/news/categories/<id>/` | 수정 / 삭제 |
| GET | `/serverless/admin/dashboard/news/sector-options/` | 섹터/서브섹터 드롭다운 옵션 |

### Admin Action

- `collect_category_news`: 개별 카테고리 즉시 수집 (params: `category_id`)

### Frontend

| 파일 | 역할 |
|------|------|
| `frontend/types/admin.ts` | NewsCollectionCategory, SectorOptionsResponse 등 타입 |
| `frontend/services/adminService.ts` | CRUD + sector-options API 메서드 |
| `frontend/hooks/useAdminDashboard.ts` | useNewsCategories, useSectorOptions, useNewsCategoryMutations |
| `frontend/components/admin/NewsCategoryManager.tsx` | 카테고리 관리 컴포넌트 (인라인 폼 + 테이블) |
| `frontend/components/admin/NewsTab.tsx` | SummaryCard 4열 + NewsCategoryManager 통합 |

### 테스트: 46개

- `tests/news/test_news_collection_category.py`: 모델 10개
- `tests/news/test_collect_category_news.py`: 태스크 10개
- `tests/serverless/test_news_categories_api.py`: API 26개

# 주요 API 엔드포인트

## 주식 데이터

- `GET /api/v1/stocks/api/chart/<symbol>/` - 차트 데이터
- `GET /api/v1/stocks/api/overview/<symbol>/` - 기업 개요
- `GET /api/v1/stocks/api/balance-sheet/<symbol>/` - 재무상태표
- `GET /api/v1/stocks/api/income-statement/<symbol>/` - 손익계산서
- `GET /api/v1/stocks/api/cashflow/<symbol>/` - 현금흐름표
- `GET /api/v1/stocks/api/indicators/<symbol>/` - 기술적 지표

## Watchlist (관심종목)

- `GET /api/v1/users/watchlist/` - 관심종목 리스트 목록
- `POST /api/v1/users/watchlist/` - 관심종목 리스트 생성
- `GET /api/v1/users/watchlist/<id>/` - 관심종목 리스트 상세
- `PATCH /api/v1/users/watchlist/<id>/` - 관심종목 리스트 수정
- `DELETE /api/v1/users/watchlist/<id>/` - 관심종목 리스트 삭제
- `POST /api/v1/users/watchlist/<id>/add-stock/` - 종목 추가
- `GET /api/v1/users/watchlist/<id>/stocks/` - 종목 목록 + 실시간 가격
- `PATCH /api/v1/users/watchlist/<id>/stocks/<symbol>/` - 종목 설정 수정
- `DELETE /api/v1/users/watchlist/<id>/stocks/<symbol>/remove/` - 종목 제거

## Market Pulse (거시경제)

- `GET /api/v1/macro/pulse/` - 전체 대시보드
- `GET /api/v1/macro/fear-greed/` - 공포/탐욕 지수
- `GET /api/v1/macro/interest-rates/` - 금리/수익률 곡선
- `GET /api/v1/macro/global-markets/` - 글로벌 시장
- `POST /api/v1/macro/sync/` - 데이터 동기화 시작
- `GET /api/v1/macro/sync/status/` - 동기화 상태 확인

## Stock 동기화

- `POST /api/v1/stocks/api/sync/<symbol>/` - 수동 데이터 동기화
  - Body: `{"data_types": ["overview", "price"], "force": false}`
  - Response: `{"symbol": "AAPL", "status": "success", "synced": {...}}`
- `GET /api/v1/stocks/api/sync/<symbol>/` - 동기화 상태 조회
- API 응답에 `_meta` 필드 포함:
  ```json
  {"source": "db", "synced_at": "...", "freshness": "fresh", "can_sync": true}
  ```

## ETF Holdings (Chain Sight Phase 3)

- `GET /api/v1/serverless/etf/status` - ETF 수집 상태 조회
  - Query Params: `tier` (선택, 'sector' 또는 'theme')
- `POST /api/v1/serverless/etf/sync` - ETF Holdings 동기화
  - Body: `{"etf_symbol": "XLK"}` (선택, 없으면 전체)
- `POST /api/v1/serverless/etf/resolve-url` - 실패한 ETF URL 자동 복구
  - Body: `{"etf_symbol": "XLK"}` (선택, 없으면 전체 실패 ETF)
- `GET /api/v1/serverless/etf/<symbol>/holdings` - 특정 ETF Holdings
- `GET /api/v1/serverless/etf/stock/<symbol>/themes` - 종목의 테마 조회
- `GET /api/v1/serverless/etf/stock/<symbol>/peers` - ETF 동반 종목 조회
- `GET /api/v1/serverless/themes` - 전체 테마 목록
- `GET /api/v1/serverless/themes/<theme_id>/stocks` - 테마별 종목 조회
- `POST /api/v1/serverless/themes/refresh` - 테마 매치 갱신

## Supply Chain (Chain Sight Phase 4)

- `GET /api/v1/serverless/chain-sight/stock/<symbol>/supply-chain` - 공급망 조회
  - Response: `{"suppliers": [...], "customers": [...], "cached": true}`
- `POST /api/v1/serverless/chain-sight/stock/<symbol>/sync-supply-chain` - 공급망 동기화 트리거
  - Response: `{"status": "success", "customer_count": 2, "supplier_count": 1}`
- `GET /api/v1/serverless/chain-sight/stock/<symbol>/category/suppliers` - 공급사 카테고리
- `GET /api/v1/serverless/chain-sight/stock/<symbol>/category/customers` - 고객사 카테고리

## LLM Relation Extraction (Chain Sight Phase 5)

- `POST /api/v1/serverless/llm-relations/extract` - 뉴스에서 LLM 관계 추출
  - Body: `{"news_id": "uuid"}` 또는 `{"batch": true, "hours": 24, "limit": 100}`
- `GET /api/v1/serverless/llm-relations/<symbol>` - 종목의 LLM 추출 관계 조회
  - Query Params: `relation_type`, `confidence`, `days`, `include_expired`
- `POST /api/v1/serverless/llm-relations/sync` - LLM 관계를 StockRelationship/Neo4j에 동기화
  - Body: `{"days": 7}`
- `GET /api/v1/serverless/llm-relations/stats` - LLM 관계 추출 통계

## Market Movers (서버리스)

- `GET /api/v1/serverless/movers?type=gainers&date=2026-01-07` - Market Movers 조회 (키워드 포함)
  - Query Params:
    - `type`: 'gainers', 'losers', 'actives' (필수)
    - `date`: YYYY-MM-DD 형식 (선택, 기본값: 오늘)
  - Response: TOP 20 종목 + 5개 지표 + AI 키워드

## AI 키워드

```bash
POST /api/v1/serverless/keywords/generate-all        # Market Movers용
POST /api/v1/serverless/keywords/generate-screener    # Screener용
GET  /api/v1/serverless/keywords/<symbol>?date=...    # 키워드 조회
POST /api/v1/serverless/keywords/batch                # 배치 조회
```

## Market Breadth & Sector Heatmap

```bash
GET  /api/v1/serverless/breadth                                # Market Breadth
GET  /api/v1/serverless/breadth/history                        # Breadth 히스토리
POST /api/v1/serverless/breadth/sync                           # Breadth 동기화
GET  /api/v1/serverless/heatmap/sectors                        # 섹터 히트맵
GET  /api/v1/serverless/heatmap/sectors/<sector>/stocks        # 섹터별 종목
POST /api/v1/serverless/heatmap/sync                           # 히트맵 동기화
```

## Screener

```bash
GET  /api/v1/serverless/screener/                     # Enhanced 스크리너
POST /api/v1/serverless/screener/chain-sight          # Chain Sight DNA
POST /api/v1/serverless/thesis/generate               # 투자 테제 생성
GET  /api/v1/serverless/thesis/{id}                   # 테제 조회
GET  /api/v1/serverless/thesis/shared/{share_code}    # 공유 테제
```

## RAG Analysis

```bash
GET /api/v1/rag/monitoring/usage/?hours=24   # 사용량 통계
GET /api/v1/rag/monitoring/cost/             # 비용 요약
GET /api/v1/rag/monitoring/cache/            # 캐시 통계
```

## News Insights

```bash
GET /api/v1/news/insights/?date=2026-02-06&limit=10&include_market_data=true
```

## News Collection Categories (Admin)

```bash
GET  /api/v1/serverless/admin/dashboard/news/categories/          # 카테고리 목록
POST /api/v1/serverless/admin/dashboard/news/categories/          # 카테고리 생성
PUT  /api/v1/serverless/admin/dashboard/news/categories/<id>/     # 카테고리 수정
DELETE /api/v1/serverless/admin/dashboard/news/categories/<id>/   # 카테고리 삭제
GET  /api/v1/serverless/admin/dashboard/news/sector-options/      # 섹터/서브섹터 드롭다운 옵션
```

- POST 필수 필드: `name`, `category_type` (sector/sub_sector/custom), `value`
- POST 선택 필드: `is_active`, `priority` (high/medium/low), `max_symbols`
- Admin Action: `collect_category_news` (params: `category_id`)

## EOD Dashboard (admin/debug 전용)

```bash
GET /api/v1/stocks/eod/dashboard/?date=YYYY-MM-DD    # DB 스냅샷 조회
GET /api/v1/stocks/eod/signal/<signal_id>/?date=      # 시그널 상세
GET /api/v1/stocks/eod/pipeline/status/               # 파이프라인 로그
```

- 프론트엔드는 이 API를 사용하지 않음 (static 파일 직접 읽기)
- Static: `fetch('/static/signals/dashboard.json')`, `cards/{category}.json`, `stocks/{SYMBOL}.json`

## News Intelligence Pipeline v3

```bash
GET /api/v1/news/all/                              # 뉴스 목록 (필터, 페이지네이션)
GET /api/v1/news/sources/                           # 소스별 건수
GET /api/v1/news/stock/<symbol>/                    # 종목별 뉴스
GET /api/v1/news/stock/<symbol>/sentiment/          # 종목 감성 분석
GET /api/v1/news/trending/                          # 트렌딩 종목
GET /api/v1/news/market/                            # 시장 뉴스
GET /api/v1/news/daily-keywords/                    # LLM 키워드
GET /api/v1/news/insights/                          # 종목 인사이트
GET /api/v1/news/market-feed/                       # AI 브리핑 (콜드 스타트)
GET /api/v1/news/interest-options/                  # 관심사 옵션
GET /api/v1/news/personalized-feed/                 # 맞춤 피드
GET /api/v1/news/news-events/?symbol=X&days=7       # Neo4j 뉴스 이벤트
GET /api/v1/news/news-events/impact-map/            # 영향도 맵
GET /api/v1/news/ml-status/                         # ML 모델 상태
GET /api/v1/news/ml-shadow-report/                  # Shadow 비교 리포트
GET /api/v1/news/ml-weekly-report/                  # 주간 ML 리포트
GET /api/v1/news/ml-lightgbm-readiness/             # LightGBM 전환 준비
```

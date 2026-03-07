# Stock-Vis MSA 전환 검토 보고서

> 작성일: 2026-03-07
> 목적: Docker 컨테이너화 및 MSA 전환 타당성 평가

---

## 1. 현재 아키텍처 현황

### 1.1 규모

| 항목 | 수치 |
|------|------|
| Backend Python 파일 | 361개 |
| Backend 코드 라인 | ~119,000줄 |
| Frontend TS/TSX 파일 | 216개 |
| Django 앱 | 10개 (stocks, users, analysis, news, macro, graph_analysis, rag_analysis, serverless, thesis, api_request) |
| 외부 의존성 | PostgreSQL, Redis, Neo4j, Gemini API, FMP/Alpha Vantage/FRED |
| 비동기 처리 | Celery Worker + Beat (7개 앱에 tasks.py) |

### 1.2 앱별 코드 규모

| 앱 | 라인 수 | 역할 |
|----|---------|------|
| serverless | 30,803 | Chain Sight, Market Movers, Screener, 키워드 |
| rag_analysis | 14,529 | RAG 파이프라인, Neo4j, LLM |
| stocks | 13,261 | 주가, 재무제표, EOD Dashboard |
| news | 11,004 | 뉴스 수집/분석, Intelligence Pipeline |
| api_request | 7,053 | 외부 API 클라이언트 (FMP, Alpha Vantage) |
| macro | 3,390 | FRED, Market Pulse |
| users | 2,869 | 인증, Watchlist |
| graph_analysis | 1,270 | 상관관계 온톨로지 |
| thesis | 722 | 가설 통제실 (방금 생성, 아직 모델만) |
| analysis | 301 | 기술적 지표 |

### 1.3 앱 간 결합도 분석

```
높은 결합 (직접 import 다수):
  news → stocks, serverless, users, rag_analysis
  serverless → stocks, news, analysis, rag_analysis
  rag_analysis → stocks
  graph_analysis → stocks, users

낮은 결합 (독립적):
  macro (FRED만 호출, 다른 앱 import 없음)
  thesis (news.NewsArticle FK만, 아직 서비스 없음)
  users (다른 앱을 import하지 않음)
  analysis (독립적)
```

### 1.4 기존 Docker 구성

이미 `docker/docker-compose.yml`에 7개 서비스가 정의되어 있음:
- db (PostgreSQL), redis, neo4j, backend, celery-worker, celery-beat, flower, frontend

**현재 구조: 모놀리스를 Docker로 감싼 형태** (MSA가 아님)

---

## 2. 제안된 MSA 도메인 분리

사용자 제안 기준 5개 도메인:

| # | 도메인 | 현재 Django 앱 매핑 | 비고 |
|---|--------|-------------------|------|
| 1 | Dashboard | stocks (EOD), macro, news (일부) | 읽기 위주, 데이터 소비자 |
| 2 | Thesis Control | thesis, stocks (일부) | 신규, 독립적 설계 가능 |
| 3 | Chain Sight | serverless, graph_analysis, rag_analysis | Neo4j 의존, 가장 큰 코드베이스 |
| 4 | Stock Screener | serverless (screener), analysis, api_request | 외부 API 의존 |
| 5 | Portfolio | users (확장), thesis (연계) | 미구현, 향후 기능 |

---

## 3. MSA 전환 평가

### 3.1 MSA의 이론적 이점과 현실적 비용

| 이점 | 현실적 평가 |
|------|------------|
| 독립 배포 | 현재 1인 개발 → 독립 배포의 이점이 크지 않음 |
| 독립 스케일링 | 트래픽이 서비스별로 극단적 차이가 나야 의미. 현재 단계에서는 불필요 |
| 기술 스택 다양화 | 전부 Django + Gemini. 다른 스택 도입 계획 없음 |
| 장애 격리 | Celery 태스크가 이미 장애를 격리하고 있음 |
| 팀 간 독립성 | 1인 개발 → 해당 없음 |

| 비용 | 구체적 영향 |
|------|------------|
| 서비스 간 통신 | REST/gRPC 호출 → 레이턴시 증가, 에러 핸들링 복잡도 |
| 데이터 일관성 | 분산 트랜잭션 필요 (Saga 패턴 등) |
| 공유 모델 | Stock, User 모델을 모든 서비스가 참조 → 데이터 동기화 문제 |
| 인프라 복잡도 | API Gateway, Service Discovery, 분산 로깅, 분산 트레이싱 |
| 운영 부담 | 5개 서비스 x (API + Worker + Beat) = 15+ 컨테이너 관리 |
| 개발 속도 저하 | 기능 하나에 여러 서비스 수정 필요 |

### 3.2 핵심 문제: 높은 결합도

현재 앱 간 결합이 MSA 분리를 어렵게 만드는 구체적 사례:

```
1. news.tasks.py → stocks.models.Stock, serverless.models, users.models
   뉴스 수집 시 종목 정보 + 키워드 + 사용자 설정을 모두 참조

2. serverless (Chain Sight) → stocks, news, analysis, rag_analysis
   관계 추출 시 주가 + 뉴스 + 기술지표 + Neo4j를 동시에 사용

3. EOD Dashboard → stocks + news + macro
   하나의 JSON에 주가 시그널 + 뉴스 감성 + VIX를 합산

4. api_request → 거의 모든 앱에서 사용
   FMP/Alpha Vantage 클라이언트가 공유 라이브러리 역할
```

이걸 MSA로 분리하면 **서비스 간 HTTP 호출이 폭발**합니다:
- EOD Dashboard 하나 렌더링에 3개 서비스 호출
- Chain Sight 관계 탐색에 4개 서비스 호출
- 각 호출마다 네트워크 레이턴시 + 에러 핸들링

### 3.3 결론: **현 단계에서 MSA 전환은 비추천**

이유:
1. **1인 개발**: MSA의 최대 이점인 "팀 간 독립성"이 적용되지 않음
2. **규모 부족**: 119K 라인은 모놀리스로 충분히 관리 가능한 규모
3. **결합도가 높음**: Stock, User 모델을 거의 모든 앱이 참조 → 분리 시 데이터 동기화 지옥
4. **트래픽 차별화 없음**: 아직 사용자 수가 서비스별 독립 스케일링을 필요로 하지 않음
5. **운영 복잡도 폭증**: 1인이 15+ 컨테이너, API Gateway, 분산 트랜잭션을 관리하는 것은 비현실적

---

## 4. 추천: Modular Monolith + Docker

### 4.1 전략: "분리할 수 있게 만들되, 분리하지 않는다"

```
현재 (모놀리스)          →  추천 (모듈러 모놀리스)        →  미래 (선택적 MSA)

┌──────────────┐        ┌──────────────────────┐        ┌─────────┐ ┌─────────┐
│  Django 1개  │        │  Django 1개           │        │ Main API│ │ LLM     │
│  모든 앱     │   →    │  도메인별 경계 명확   │   →    │ (대부분)│ │ Worker  │
│  뒤섞인 의존 │        │  도메인 간 인터페이스  │        └─────────┘ └─────────┘
└──────────────┘        │  공유 모델은 그대로   │         필요할 때만 분리
                        └──────────────────────┘
```

### 4.2 구체적 실행 방안

#### Phase 1: Docker 컨테이너화 강화 (즉시)

현재 docker-compose.yml은 이미 잘 구성되어 있음. 보강 사항:

```yaml
# docker-compose.yml 개선
services:
  backend:         # Django API (기존)
  celery-worker:   # 범용 Worker (기존)
  celery-llm:      # LLM 전용 Worker (신규 - 분리 추천)
    command: celery -A config worker -l info -Q llm --concurrency=2
  celery-data:     # 데이터 수집 Worker (신규 - 분리 추천)
    command: celery -A config worker -l info -Q data --concurrency=4
  celery-beat:     # 스케줄러 (기존)
  frontend:        # Next.js (기존)
```

**Celery 큐 분리가 MSA보다 효과적인 이유:**
- LLM 호출(느림, 비쌈)과 데이터 수집(빠름, 빈번)을 분리
- 코드 변경 없이 큐 이름만 지정하면 됨
- LLM Worker만 스케일업/다운 가능
- 장애 격리 효과도 동일

#### Phase 2: 도메인 경계 정리 (1-2주)

```
# 현재: 앱 간 직접 import (강결합)
from stocks.models import Stock
from news.models import NewsArticle

# 개선: 도메인 서비스 인터페이스 (약결합)
# 각 앱에 public_api.py 또는 interfaces.py 생성
# 다른 앱은 이 인터페이스만 사용

stocks/interfaces.py:
  def get_stock_by_symbol(symbol: str) -> StockDTO
  def get_daily_prices(symbol: str, days: int) -> list[PriceDTO]

news/interfaces.py:
  def get_recent_news(symbol: str, limit: int) -> list[NewsDTO]
```

이렇게 하면:
- 앱 간 결합점이 명시적으로 관리됨
- 나중에 MSA로 분리할 때 인터페이스를 HTTP 호출로 교체하면 끝
- 지금은 같은 프로세스 내 함수 호출이므로 성능 저하 없음

#### Phase 3: 도메인 그룹핑 (코드 정리)

```
# Django 앱 재그룹핑 (폴더 구조만, 앱 분리 아님)

domain/
├── dashboard/          # EOD, 메인 화면
│   ├── stocks/         # 기존 stocks 앱
│   ├── macro/          # 기존 macro 앱
│   └── news/           # 기존 news 앱
├── thesis/             # 가설 통제실
│   └── thesis/         # 기존 thesis 앱
├── chainsight/         # 관계 탐색
│   ├── serverless/     # 기존 serverless 앱
│   └── graph_analysis/ # 기존 graph_analysis 앱
├── intelligence/       # AI/LLM
│   └── rag_analysis/   # 기존 rag_analysis 앱
└── core/               # 공유
    ├── users/
    ├── analysis/
    └── api_request/
```

> 주의: 이건 물리적 폴더 재배치일 뿐, Django INSTALLED_APPS는 변경하지 않음.
> 목적은 개발자(자신)가 도메인 경계를 인식하게 하는 것.
> **지금 당장 할 필요는 없음** — 앱이 더 커지면 고려.

### 4.3 미래에 MSA가 필요해지는 시점

다음 조건 중 2개 이상 해당되면 그때 분리 검토:

| # | 조건 | 현재 |
|---|------|------|
| 1 | 팀원이 3명 이상이고, 도메인별 담당자가 구분됨 | 1인 개발 |
| 2 | 특정 서비스의 트래픽이 다른 서비스의 10배 이상 | 균일 |
| 3 | LLM 비용이 월 $500+ 이고 별도 스케일링이 필요 | 무료 티어 |
| 4 | 배포 빈도가 일 2회 이상이고 서비스별로 다름 | 낮음 |
| 5 | 장애가 전파되어 전체 서비스가 다운되는 일이 반복됨 | 발생 안 함 |

### 4.4 MSA가 아닌 "유일하게 분리할 만한 것"

**LLM Worker 분리**는 지금도 가치가 있음:

```yaml
# Celery 큐 기반 분리 (코드 변경 최소)
celery-llm-worker:
  command: celery -A config worker -l info -Q llm -c 2
  deploy:
    resources:
      limits:
        memory: 2G  # LLM 응답 처리에 더 많은 메모리
```

이유:
- Gemini API 호출은 응답이 2-10초로 느림
- 다른 빠른 태스크(데이터 수집, EOD 계산)를 블로킹하면 안 됨
- LLM Worker만 별도로 스케일링 가능
- **이건 MSA가 아니라 Worker 큐 분리** — 훨씬 단순

---

## 5. 즉시 실행 가능한 액션 아이템

| 우선순위 | 작업 | 난이도 | 효과 |
|---------|------|-------|------|
| 1 | Celery 큐 분리 (llm / data / default) | 낮음 | LLM 장애 격리, 스케일링 |
| 2 | docker-compose에 llm-worker 추가 | 낮음 | 독립 스케일링 |
| 3 | 각 앱에 interfaces.py 추가 (점진적) | 중간 | 결합도 관리, 미래 MSA 대비 |
| 4 | serverless 앱 리네이밍/분할 (30K줄) | 중간 | 가독성, 유지보수성 |
| 5 | 환경별 docker-compose 분리 (dev/prod) | 낮음 | 운영 안정성 |

---

## 6. 요약

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   MSA 전환?  →  시기상조 (No)                               │
│   Docker?    →  이미 있음, 보강하면 됨 (Yes)                │
│   대신?      →  Modular Monolith + Celery 큐 분리           │
│                                                             │
│   핵심 원칙:                                                │
│   "분리할 수 있게 설계하되, 분리하지 않는다"                │
│   "MSA의 비용을 지불하기 전에, MSA의 이점이 필요한지 확인"  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

현재 Stock-Vis는 **잘 구조화된 Django 모놀리스 + Docker + Celery**가 최적입니다.
MSA로 전환하면 개발 속도가 절반으로 줄고, 인프라 관리에 시간의 40%를 쓰게 됩니다.
1인 개발에서 MSA는 "미래를 위한 투자"가 아니라 "현재의 발목"이 됩니다.

# Environment Variables Documentation

Stock-Vis 프로젝트의 환경 변수 설정 가이드입니다.

---

## 빠른 시작

```bash
# .env.example을 복사하여 .env 파일 생성
cp .env.example .env

# 필수 값 설정
# 1. ALPHA_VANTAGE_API_KEY
# 2. DB_USER, DB_PASSWORD
```

---

## API Keys

### Alpha Vantage (필수)

```bash
ALPHA_VANTAGE_API_KEY="your_api_key"
```

| 항목 | 값 |
|------|-----|
| 발급 URL | https://www.alphavantage.co/support/#api-key |
| 무료 티어 제한 | 5 calls/min, 500 calls/day |
| Rate Limit 대기 | 12초 |

### Financial Modeling Prep (선택)

```bash
FMP_API_KEY="your_api_key"
```

| 항목 | 값 |
|------|-----|
| 발급 URL | https://financialmodelingprep.com/developer |
| 무료 티어 제한 | 250 calls/day |

### Finnhub (뉴스 기능용)

```bash
FINNHUB_API_KEY="your_api_key"
```

| 항목 | 값 |
|------|-----|
| 발급 URL | https://finnhub.io/register |
| 무료 티어 제한 | 60 calls/min |
| 용도 | 실시간 뉴스, 감성 분석 |
| Rate Limit 대기 | 1초 |

### Marketaux (뉴스 기능용)

```bash
MARKETAUX_API_KEY="your_api_key"
```

| 항목 | 값 |
|------|-----|
| 발급 URL | https://www.marketaux.com/account/dashboard |
| 무료 티어 제한 | 100 calls/day |
| 용도 | 종합 뉴스, 엔티티 추출 |
| Rate Limit 대기 | 1초 |

---

## Stock Data Provider Configuration

Provider 추상화 레이어를 통해 엔드포인트별로 다른 데이터 제공자를 사용할 수 있습니다.

### 기본 설정 (Alpha Vantage)

```bash
# 모든 엔드포인트에서 Alpha Vantage 사용 (기본값)
STOCK_PROVIDER_QUOTE=alpha_vantage
STOCK_PROVIDER_PROFILE=alpha_vantage
STOCK_PROVIDER_DAILY_PRICES=alpha_vantage
STOCK_PROVIDER_WEEKLY_PRICES=alpha_vantage
STOCK_PROVIDER_BALANCE_SHEET=alpha_vantage
STOCK_PROVIDER_INCOME_STATEMENT=alpha_vantage
STOCK_PROVIDER_CASH_FLOW=alpha_vantage
STOCK_PROVIDER_SEARCH=alpha_vantage
STOCK_PROVIDER_SECTOR=alpha_vantage
```

### FMP 전환 예시

```bash
# 재무제표만 FMP 사용
STOCK_PROVIDER_BALANCE_SHEET=fmp
STOCK_PROVIDER_INCOME_STATEMENT=fmp
STOCK_PROVIDER_CASH_FLOW=fmp

# 나머지는 Alpha Vantage 유지
STOCK_PROVIDER_QUOTE=alpha_vantage
STOCK_PROVIDER_PROFILE=alpha_vantage
```

### Fallback 설정

```bash
# 주 Provider 실패 시 대체 Provider 자동 사용
PROVIDER_FALLBACK_ENABLED=True
```

| 주 Provider | Fallback |
|-------------|----------|
| Alpha Vantage | FMP |
| FMP | Alpha Vantage |

---

## Database (PostgreSQL)

```bash
DB_USER=stockvis
DB_PASSWORD=your_secure_password
DB_HOST=localhost
DB_PORT=5432
```

### Docker 환경

```bash
# docker-compose에서는 DB_HOST를 서비스명으로 설정
DB_HOST=db
```

---

## Redis (Cache + Celery)

```bash
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### Docker 환경

```bash
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
```

---

## Django Settings

```bash
# 개발 환경
DEBUG=True

# 프로덕션 환경
DEBUG=False
SECRET_KEY=your_production_secret_key_here
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
```

### SECRET_KEY 생성

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## Neo4j (Knowledge Graph Database)

뉴스 기능을 위한 그래프 데이터베이스입니다. Stock-News-Entity 관계를 관리합니다.

### 로컬 개발 환경 (기본값)

Docker Compose를 통해 자동으로 실행됩니다:

```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
NEO4J_DATABASE=neo4j
```

| 항목 | 값 |
|------|-----|
| HTTP 브라우저 | http://localhost:7474 |
| Bolt 연결 | bolt://localhost:7687 |
| APOC 플러그인 | 활성화 |

### Docker 환경

```bash
# docker-compose 내부에서는 서비스명 사용
NEO4J_URI=bolt://neo4j:7687
```

### Neo4j Aura (클라우드 환경 - 선택)

클라우드 환경을 사용할 경우:

```bash
NEO4J_USE_AURA=True
NEO4J_URI=neo4j+s://your_instance.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_neo4j_aura_password
NEO4J_DATABASE=neo4j
AURA_INSTANCEID=your_instance_id
AURA_INSTANCENAME=your_instance_name
```

### Neo4j 초기화

```bash
# 1. Neo4j 서비스 시작
docker-compose up -d neo4j

# 2. 브라우저에서 접속
open http://localhost:7474

# 3. 초기화 스크립트 실행
cat scripts/init-neo4j.cypher | docker exec -i stockvis-neo4j cypher-shell -u neo4j -p password
```

---

## News API Configuration

```bash
# News API 우선순위 설정
NEWS_PRIMARY_PROVIDER=finnhub        # 1차 API
NEWS_FALLBACK_PROVIDER=marketaux     # 2차 API (1차 실패 시)
```

### News API 선택 가이드

| 시나리오 | 권장 설정 |
|---------|----------|
| 실시간성 중요 | PRIMARY=finnhub (60 calls/min) |
| 종합 분석 중요 | PRIMARY=marketaux (더 상세한 내용) |
| 높은 트래픽 | FALLBACK 활성화 권장 |

### Rate Limit 설정 (config/settings.py)

```python
NEWS_RATE_LIMITS = {
    'finnhub': {
        'per_minute': 60,
        'wait_seconds': 1,
    },
    'marketaux': {
        'per_day': 100,
        'articles_per_request': 3,
        'wait_seconds': 1,
    },
}
```

### Cache TTL 설정 (config/settings.py)

```python
NEWS_CACHE_TTL = {
    'stock_news': 3600,      # 1시간 - 종목별 뉴스
    'trending': 300,         # 5분 - 트렌딩 뉴스
    'sentiment': 900,        # 15분 - 감성 분석
    'entity': 1800,          # 30분 - 엔티티 추출
}
```

---

## Frontend Environment

`frontend/.env.local` 파일:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 프로덕션

```bash
NEXT_PUBLIC_API_URL=https://api.your-domain.com
```

---

## 환경별 설정 파일

| 파일 | 용도 |
|------|------|
| `.env` | 로컬 개발 환경 |
| `.env.production` | 프로덕션 환경 |
| `.env.example` | 템플릿 (버전 관리 포함) |
| `frontend/.env.local` | Frontend 로컬 환경 |

---

## 환경 변수 우선순위

1. 시스템 환경 변수
2. `.env` 파일 (python-dotenv)
3. 기본값 (settings.py)

---

## 보안 주의사항

- `.env`, `.env.production` 파일은 **절대** Git에 커밋하지 마세요
- API 키는 정기적으로 교체하세요
- 프로덕션에서는 강력한 SECRET_KEY를 사용하세요
- 데이터베이스 비밀번호는 복잡하게 설정하세요

---

## 환경 변수 검증

```bash
# Django 설정 확인
python manage.py check

# Provider 설정 확인
python -c "from api_request.providers.factory import print_current_config; print_current_config()"
```

출력 예시:
```
=== Stock Provider Configuration ===
  quote                -> alpha_vantage   [STOCK_PROVIDER_QUOTE=(not set)]
  profile              -> alpha_vantage   [STOCK_PROVIDER_PROFILE=(not set)]
  daily_prices         -> alpha_vantage   [STOCK_PROVIDER_DAILY_PRICES=(not set)]
  ...
=====================================
```

# Stock-Vis 사용자 가이드

> 퀀트 개발자를 위한 Stock-Vis 서비스 완전 가이드

## 목차

### 📊 주요 페이지

1. [Portfolio (포트폴리오)](./portfolio/) - 개인 투자 포트폴리오 관리
2. [Stock Detail (종목 상세)](./stock-detail/) - 개별 종목 심층 분석
3. [Market Pulse (시장 맥박)](./market-pulse/) - 거시경제 및 시장 동향 대시보드
4. [Strategy Analysis (전략 분석실)](./strategy-analysis/) - AI 기반 투자 전략 분석 (개발 예정)

---

## 문서 구성

각 페이지 가이드는 다음과 같이 구성됩니다:

### 1. 서비스 이해
- **기능 정의**: 해당 기능이 무엇을 하는가
- **목적**: 왜 이 기능이 필요한가
- **투자 지식**: 관련된 투자/금융 개념 설명

### 2. 기술 아키텍처
- **데이터베이스 스키마**: 사용하는 모델과 관계
- **API 엔드포인트**: REST API 명세
- **데이터 소스**: 외부 API 통합
- **캐싱 전략**: Redis 캐싱 정책

### 3. 코드 구성
- **Backend**: Django 앱, 서비스, 모델 위치
- **Frontend**: Next.js 컴포넌트, 훅, 서비스 위치
- **비동기 작업**: Celery 태스크 및 스케줄

---

## 시작하기

### 퀀트 개발자를 위한 빠른 시작

```bash
# 1. 프로젝트 클론
git clone <repository-url>
cd stock_vis

# 2. Backend 설정
poetry install
createdb stock_vis
python manage.py migrate

# 3. Frontend 설정
cd frontend
npm install

# 4. Redis & Celery 시작
brew services start redis
celery -A config worker -l info
celery -A config beat -l info

# 5. 서버 실행
python manage.py runserver  # Backend: localhost:8000
npm run dev                  # Frontend: localhost:3000
```

---

## 주요 기술 스택

### Backend
- **Framework**: Django REST Framework
- **Database**: PostgreSQL
- **Cache**: Redis
- **Task Queue**: Celery + Celery Beat
- **API**: Alpha Vantage, FMP, yfinance

### Frontend
- **Framework**: Next.js 14+ (App Router)
- **Language**: TypeScript
- **State Management**: TanStack Query (서버), Zustand (클라이언트)
- **Charts**: Recharts

### Infrastructure
- **Containerization**: Docker (예정)
- **Serverless**: AWS Lambda (Market Movers 전환 예정)

---

## 개발 원칙

1. **3계층 아키텍처**: API Client → Processor → Service
2. **순수 함수**: Django 의존성 없는 계산 로직 (AWS Lambda 전환 대비)
3. **캐싱 우선**: Rate limit 회피 및 응답 속도 향상
4. **타입 안전성**: TypeScript strict mode
5. **테스트 커버리지**: 핵심 로직 80% 이상

---

## 기여 가이드

- **Backend**: `@backend` 에이전트 영역 참고
- **Frontend**: `@frontend` 에이전트 영역 참고
- **인프라**: `@infra` 에이전트 영역 참고
- **테스트**: `@qa` 에이전트 영역 참고

자세한 내용은 [CLAUDE.md](../../CLAUDE.md) 참조

# Stock-Vis 서버리스 전환 계획

## 개요

Stock-Vis 플랫폼의 백그라운드 작업을 AWS Lambda 기반 서버리스 아키텍처로 전환하는 계획입니다.

---

## 현재 아키텍처 vs 목표 아키텍처

### 현재 (Celery + Redis)

```
Django Server
     │
     ├── Celery Worker (24/7 실행)
     │      ├── Market Movers 동기화
     │      ├── AI 키워드 생성
     │      └── (뉴스 수집 - 미구현)
     │
     └── Celery Beat (스케줄러)
            └── crontab 기반 태스크 트리거
```

**문제점:**
- 24/7 서버 비용 발생
- 트래픽 없을 때도 리소스 사용
- 스케일링 수동 관리 필요

### 목표 (AWS Lambda + EventBridge)

```
                    ┌─────────────────────────────────────┐
                    │         AWS EventBridge             │
                    │    (스케줄 기반 트리거)              │
                    └─────────────────────────────────────┘
                                     │
          ┌──────────────────────────┼──────────────────────────┐
          ▼                          ▼                          ▼
   ┌─────────────┐           ┌─────────────┐           ┌─────────────┐
   │   Lambda    │           │   Lambda    │           │   Lambda    │
   │ News Sync   │           │  Movers     │           │  Keywords   │
   └─────────────┘           └─────────────┘           └─────────────┘
          │                          │                          │
          └──────────────────────────┼──────────────────────────┘
                                     ▼
                    ┌─────────────────────────────────────┐
                    │        PostgreSQL (RDS)             │
                    │        Redis (ElastiCache)          │
                    └─────────────────────────────────────┘
```

**장점:**
- 사용한 만큼만 비용 지불
- 자동 스케일링
- 관리 오버헤드 감소

---

## 서버리스 전환 대상

### Phase 1: 뉴스 자동 수집 (우선순위 높음)
- 사용자 모니터링 종목 뉴스 수집
- 섹터/인더스트리 Top 20 뉴스 수집
- **문서**: `01_NEWS_AUTO_COLLECTION.md`

### Phase 2: Market Movers 동기화
- 기존 Celery 태스크를 Lambda로 전환
- 매일 07:30 EST 실행
- **문서**: `02_MARKET_MOVERS_LAMBDA.md`

### Phase 3: AI 키워드 생성
- LLM 호출 Lambda 분리
- 비용 최적화 (Gemini API 호출 집중)
- **문서**: `03_AI_KEYWORDS_LAMBDA.md`

### Phase 4: 가격 데이터 동기화
- 실시간 가격 업데이트
- 히스토리컬 데이터 백필
- **문서**: `04_PRICE_SYNC_LAMBDA.md`

---

## AWS 서비스 구성

| 서비스 | 용도 | 예상 비용 |
|--------|------|----------|
| **Lambda** | 함수 실행 | $0.20/1M requests |
| **EventBridge** | 스케줄링 | $1.00/1M events |
| **SQS** | 작업 큐 | $0.40/1M requests |
| **S3** | Lambda 코드 저장 | $0.023/GB |
| **CloudWatch** | 로그/모니터링 | $0.50/GB ingested |
| **Secrets Manager** | API 키 관리 | $0.40/secret/month |

### 예상 월 비용 (초기)
- Lambda: ~$5-10
- EventBridge: ~$1
- SQS: ~$1
- CloudWatch: ~$5
- **총합: ~$15-20/월**

---

## 배포 전략

### Infrastructure as Code (Terraform)

```
infra/
├── terraform/
│   ├── main.tf
│   ├── variables.tf
│   ├── lambda.tf
│   ├── eventbridge.tf
│   ├── sqs.tf
│   └── iam.tf
└── lambda/
    ├── news_sync/
    │   ├── handler.py
    │   └── requirements.txt
    ├── market_movers/
    │   ├── handler.py
    │   └── requirements.txt
    └── ai_keywords/
        ├── handler.py
        └── requirements.txt
```

### CI/CD (GitHub Actions)

```yaml
# .github/workflows/deploy-lambda.yml
on:
  push:
    paths:
      - 'infra/lambda/**'
    branches:
      - main

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3
      - name: Deploy Lambda
        run: |
          cd infra/terraform
          terraform init
          terraform apply -auto-approve
```

---

## 마이그레이션 계획

### Step 1: 병행 운영 (2주)
- Lambda 함수 배포
- Celery와 Lambda 동시 실행
- 결과 비교 및 검증

### Step 2: 트래픽 전환 (1주)
- Lambda로 점진적 전환
- Celery 태스크 비활성화
- 모니터링 강화

### Step 3: Celery 제거 (1주)
- Celery Worker/Beat 중단
- 관련 코드 정리
- 문서 업데이트

---

## 모니터링 및 알림

### CloudWatch 대시보드
- Lambda 실행 횟수/시간
- 에러율
- 동시 실행 수

### 알림 설정
- Lambda 실패 시 Slack 알림
- 비용 임계치 초과 시 알림
- Rate Limit 도달 시 알림

---

## 관련 문서

1. [뉴스 자동 수집 계획](./01_NEWS_AUTO_COLLECTION.md)
2. [Market Movers Lambda 전환](./02_MARKET_MOVERS_LAMBDA.md) (예정)
3. [AI 키워드 Lambda 전환](./03_AI_KEYWORDS_LAMBDA.md) (예정)
4. [가격 동기화 Lambda 전환](./04_PRICE_SYNC_LAMBDA.md) (예정)

---

## 버전 히스토리

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 0.1 | 2026-01-26 | 초안 작성 |

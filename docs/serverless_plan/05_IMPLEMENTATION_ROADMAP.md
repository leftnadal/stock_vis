# 서버리스 전환 구현 로드맵

## 전체 타임라인

```
     Phase 1          Phase 2          Phase 3          Phase 4
   (뉴스 수집)      (Market Movers)   (AI 키워드)      (가격 동기화)
       │                 │                │                │
  Week 1-4          Week 5-6          Week 7-8          Week 9-10
       │                 │                │                │
       ▼                 ▼                ▼                ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│ Lambda 구축 │   │ Celery 전환 │   │ LLM Lambda  │   │ Batch Sync  │
│ SQS 설정   │   │ 병행 운영   │   │ Rate Limit  │   │ On-demand   │
│ DB 스키마   │   │ 검증/전환   │   │ 폴백 처리   │   │ API GW 연동 │
└─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘
```

---

## Phase별 상세 일정

### Phase 1: 뉴스 자동 수집 (Week 1-4)

| 주차 | 작업 | 담당 | 산출물 |
|------|------|------|--------|
| **Week 1** | 인프라 구축 | Infra | Terraform 코드, SQS 큐 |
| **Week 2** | Lambda 개발 | Backend | Scheduler, Worker Lambda |
| **Week 3** | DB 스키마 및 API | Backend | Migration, REST API |
| **Week 4** | 프론트엔드 통합 | Frontend | Watchlist 설정 UI |

**마일스톤**: 사용자가 Watchlist에서 뉴스 자동 수집 활성화 가능

### Phase 2: Market Movers Lambda 전환 (Week 5-6)

| 주차 | 작업 | 담당 | 산출물 |
|------|------|------|--------|
| **Week 5** | Lambda 개발, 병행 운영 | Backend/Infra | Orchestrator, Worker |
| **Week 6** | 검증, Celery 제거 | Backend | 마이그레이션 완료 |

**마일스톤**: Celery 의존성 제거, Lambda 단독 운영

### Phase 3: AI 키워드 Lambda (Week 7-8)

| 주차 | 작업 | 담당 | 산출물 |
|------|------|------|--------|
| **Week 7** | Lambda 개발, Rate Limit | Backend/Infra | Keyword Generator Lambda |
| **Week 8** | 에러 처리, DLQ | Backend | 폴백 로직, 모니터링 |

**마일스톤**: 키워드 생성 완전 서버리스화

### Phase 4: 가격 동기화 Lambda (Week 9-10)

| 주차 | 작업 | 담당 | 산출물 |
|------|------|------|--------|
| **Week 9** | Batch Sync Lambda | Backend/Infra | Orchestrator, Worker |
| **Week 10** | On-demand API | Backend/Frontend | API Gateway, 실시간 동기화 |

**마일스톤**: 가격 데이터 완전 자동화

---

## 우선순위 매트릭스

| 기능 | 비즈니스 가치 | 기술 복잡도 | 우선순위 |
|------|-------------|------------|----------|
| 뉴스 자동 수집 | 높음 (사용자 요청) | 중간 | **P1** |
| Market Movers Lambda | 중간 (비용 절감) | 낮음 (기존 로직) | **P2** |
| AI 키워드 Lambda | 중간 | 중간 | **P3** |
| 가격 동기화 Lambda | 높음 | 높음 (대량 데이터) | **P4** |

---

## 비용 요약

### 현재 비용 (Celery 기반)

| 항목 | 월 비용 |
|------|--------|
| EC2 (Celery Worker) | $15 |
| ElastiCache (Redis) | $15 |
| **총합** | **$30/월** |

### 전환 후 비용 (Lambda 기반)

| Phase | Lambda | SQS | 기타 | 소계 |
|-------|--------|-----|------|------|
| 뉴스 수집 | $0.70 | $0.01 | $0.50 | $1.21 |
| Market Movers | $0.06 | $0.01 | $0.03 | $0.10 |
| AI 키워드 | $0.16 | $0.01 | $0.18 | $0.35 |
| 가격 동기화 | $0.15 | $0.01 | $0.04 | $0.20 |
| **총합** | **$1.07** | **$0.04** | **$0.75** | **$1.86/월** |

### 절감 효과

```
현재: $30/월
전환 후: ~$2/월
절감액: $28/월 (93% 절감)
연간 절감: $336
```

---

## 기술 스택

### AWS 서비스

| 서비스 | 용도 | 설정 |
|--------|------|------|
| **Lambda** | 함수 실행 | Python 3.11, 256-512MB |
| **EventBridge** | 스케줄링 | cron 표현식 |
| **SQS** | 메시지 큐 | Standard Queue, DLQ |
| **Secrets Manager** | API 키 관리 | 자동 로테이션 |
| **CloudWatch** | 로그/메트릭 | 커스텀 대시보드 |
| **API Gateway** | HTTP API | On-demand 엔드포인트 |

### IaC

| 도구 | 용도 |
|------|------|
| **Terraform** | AWS 리소스 프로비저닝 |
| **GitHub Actions** | CI/CD 파이프라인 |

### 모니터링

| 도구 | 용도 |
|------|------|
| **CloudWatch Logs** | Lambda 로그 |
| **CloudWatch Metrics** | 성능 메트릭 |
| **SNS** | 알림 전송 |
| **Slack** | 알림 수신 |

---

## 리스크 관리

### 기술적 리스크

| 리스크 | 영향 | 완화 전략 |
|--------|------|----------|
| Lambda Cold Start | 지연 증가 | Provisioned Concurrency |
| VPC 연결 지연 | DB 접근 느림 | RDS Proxy 사용 |
| Rate Limit 초과 | 데이터 수집 실패 | SQS 지연, 재시도 |
| LLM 응답 불안정 | 키워드 품질 저하 | 폴백 키워드 |

### 운영 리스크

| 리스크 | 영향 | 완화 전략 |
|--------|------|----------|
| 비용 초과 | 예산 초과 | 비용 알림 설정 |
| 서비스 중단 | 사용자 영향 | 롤백 계획 |
| 모니터링 누락 | 장애 감지 지연 | 알림 설정 검증 |

---

## 롤백 계획

### 긴급 롤백 절차

```bash
# 1. EventBridge 스케줄 비활성화
aws events disable-rule --name news-scheduler-hourly
aws events disable-rule --name market-movers-daily

# 2. Celery Beat 재활성화
celery -A config beat -l info &
celery -A config worker -l info &

# 3. 상태 확인
curl http://localhost:8000/api/v1/health/
```

### 롤백 기준

- Lambda 에러율 > 10%
- 응답 시간 > 30초
- 데이터 정합성 문제 발견

---

## 체크리스트

### Phase 1 시작 전

- [ ] AWS 계정 설정 확인
- [ ] IAM 역할 및 정책 생성
- [ ] VPC 서브넷 확인 (Private)
- [ ] Secrets Manager에 API 키 등록
- [ ] Terraform 상태 백엔드 설정

### 각 Phase 완료 시

- [ ] 단위 테스트 통과
- [ ] 통합 테스트 통과
- [ ] 스테이징 환경 검증
- [ ] 프로덕션 배포
- [ ] 모니터링 대시보드 확인
- [ ] 문서 업데이트

---

## 문서 목록

| 문서 | 설명 | 상태 |
|------|------|------|
| [00_SERVERLESS_OVERVIEW.md](./00_SERVERLESS_OVERVIEW.md) | 전체 개요 | ✅ 완료 |
| [01_NEWS_AUTO_COLLECTION.md](./01_NEWS_AUTO_COLLECTION.md) | 뉴스 자동 수집 | ✅ 완료 |
| [02_MARKET_MOVERS_LAMBDA.md](./02_MARKET_MOVERS_LAMBDA.md) | Market Movers 전환 | ✅ 완료 |
| [03_AI_KEYWORDS_LAMBDA.md](./03_AI_KEYWORDS_LAMBDA.md) | AI 키워드 전환 | ✅ 완료 |
| [04_PRICE_SYNC_LAMBDA.md](./04_PRICE_SYNC_LAMBDA.md) | 가격 동기화 | ✅ 완료 |
| [05_IMPLEMENTATION_ROADMAP.md](./05_IMPLEMENTATION_ROADMAP.md) | 구현 로드맵 | ✅ 완료 |

---

## 버전 히스토리

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 0.1 | 2026-01-26 | 초안 작성 |

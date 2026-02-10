# KB 품질 검토 리포트 - AI Analysis 구현 교훈

작성일: 2025-12-16
작성자: @qa-architect

---

## 개요

AI Analysis 기능 구현 과정에서 발생한 에러들과 해결 방법, 아키텍처 패턴, UX 교훈 등을 KB에 정리했습니다.

---

## 추가된 교훈 (8건)

### 1. 기술 패턴 (tech/pattern) - 5건

| 제목 | 신뢰도 | 태그 | 승격 가능성 |
|------|--------|------|------------|
| Django ASGI + SSE 스트리밍 패턴 | verified | django, asgi, sse, streaming, daphne | ⚠️ universal (다른 ASGI 프레임워크에도 적용) |
| Django ORM async 컨텍스트 안전 호출 패턴 | verified | django, orm, async, sync_to_async | ✅ tech_stack (Django 특화) |
| React SSE 스트림 처리 및 캐시 무효화 패턴 | verified | react, sse, tanstack-query, cache-invalidation | ⚠️ universal (React 일반 패턴) |
| LLM 스트리밍 응답 내 XML 태그 파싱 패턴 | high | llm, xml, parsing, streaming, claude | ✅ tech_stack (LLM 특화) |
| SSE Phase 기반 진행 상태 통신 패턴 | high | sse, progress-tracking, state-machine | ⚠️ universal (SSE 일반 패턴) |

### 2. 문제 해결 (tech/troubleshoot) - 2건

| 제목 | 신뢰도 | 태그 | 레벨 |
|------|--------|------|------|
| Django Model Choices 동적 확장 시 마이그레이션 필수 | verified | django, models, choices, migration | tech_stack |
| Django 모델 필드명 일관성 - stock.name vs stock.stock_name | verified | django, models, debugging, stock-vis | **project** |

### 3. 교훈 (project/lesson) - 1건

| 제목 | 신뢰도 | 태그 | 레벨 |
|------|--------|------|------|
| AI 기능 UX - 심플함의 중요성 | high | ux, over-engineering, ai-interface, simplicity | project |

---

## KB 품질 분석

### 검증 완료

1. **검색 테스트 통과**
   - "SSE" 검색: 4건 (Django ASGI, React, Phase, LLM)
   - "sync_to_async" 검색: 1건 (Django ORM async)
   - "Django" 검색: 3건 (ASGI, ORM, Choices)
   - "stock" 검색: 2건 (필드명 일관성, UX 심플화)

2. **태그 체계 일관성**
   - 모든 항목이 적절한 태그 보유
   - 기술 스택 명확: django, react, llm, sse
   - 도메인 분류: tech (6건), project (2건)

3. **신뢰도 수준 적절**
   - verified: 5건 (코드로 검증된 에러 해결)
   - high: 3건 (베스트 프랙티스, 경험 기반)

---

## 중복 항목 발견

### 중복 1: Django SSE Streaming

**KB 항목**: Django ASGI + SSE 스트리밍 패턴 (ID: 11bfc49c...)
- 신뢰도: verified
- 내용: async_to_sync 패턴, DRF 렌더러, 인증 토큰 처리

**큐 항목 #4**: Django SSE Streaming Async Loop Issue (ID: 6b6dd8bf...)
- 신뢰도: medium
- 내용: asyncio.new_event_loop() 문제

**평가**:
- KB 항목이 더 포괄적 (문제 + 해결책 3가지)
- 큐 항목은 특정 에러에 집중
- **권장 조치**: 큐 항목 삭제 (KB 항목으로 충분)

### 중복 2: LLM 데이터 제안 패턴

**KB 항목**: LLM 스트리밍 응답 내 XML 태그 파싱 패턴 (ID: f2102b8a...)
- 포커스: XML 파싱 구현

**큐 항목 #5**: LLM RAG 파이프라인 - 빈 데이터 허용과 basket-action 태그 시스템 (ID: 3897bf70...)
- 포커스: 빈 바구니 처리 + basket-action 태그

**평가**:
- 서로 보완 관계 (중복 아님)
- KB 항목: XML 파싱 기술
- 큐 항목: 빈 데이터 처리 전략 + 비즈니스 로직
- **권장 조치**: 큐 항목 승인 (별도 교훈으로 가치 있음)

---

## 승격 후보

### 1. Django ASGI + SSE 스트리밍 패턴

**현재 레벨**: tech_stack
**승격 후보**: universal

**근거**:
- ASGI는 표준 인터페이스 (Django, FastAPI, Starlette 등)
- async_to_sync 패턴은 모든 ASGI 프레임워크에 적용 가능
- SSE 인증/렌더러 문제는 범용적

**조건**:
- 2개 이상의 프레임워크에서 동일 패턴 확인 시 승격
- 현재는 Django만 검증 → **보류**

### 2. React SSE 스트림 처리 및 캐시 무효화 패턴

**현재 레벨**: tech_stack
**승격 후보**: universal

**근거**:
- SSE 이벤트 핸들링은 React 외에도 Vue, Svelte 등에서 동일 패턴
- TanStack Query 캐시 무효화는 React Query 일반 패턴

**조건**:
- 프레임워크 중립적 내용으로 재작성 시 승격 가능
- 현재는 React 특화 → **보류**

### 3. SSE Phase 기반 진행 상태 통신 패턴

**현재 레벨**: tech_stack
**승격 후보**: universal

**근거**:
- Phase 기반 상태 관리는 프레임워크/언어 독립적
- WebSocket, SSE, Long Polling 등 모든 실시간 통신에 적용 가능

**조건**:
- 3개 이상의 프로젝트에서 유사 패턴 사용 시 승격
- 현재는 Stock-Vis만 → **보류 (1년 후 재검토)**

---

## 큐 항목 검토 (5건 대기 중)

### 승인 권장 (2건)

1. **#5: LLM RAG 파이프라인 - 빈 데이터 허용과 basket-action 태그 시스템**
   - 이유: KB의 XML 파싱 패턴과 보완 관계
   - 빈 데이터 처리 전략은 별도 교훈으로 가치 있음
   - 조치: 승인 후 KB 추가

2. **#3: API 마이그레이션 점진적 전환 전략**
   - 이유: 범용적 마이그레이션 전략 (API 외에도 적용 가능)
   - 조치: 승인 후 KB 추가

### 병합 권장 (1건)

1. **#4: Django SSE Streaming Async Loop Issue**
   - 이유: KB의 "Django ASGI + SSE 스트리밍 패턴"과 중복
   - 조치: 삭제 (KB 항목으로 충분)

### 보류 (2건)

1. **#1: API Provider 추상화 패턴**
   - 이유: 너무 일반적 (Provider 패턴은 일반적인 디자인 패턴)
   - 조치: 내용 보강 필요 (Stock-Vis 특화 내용 추가)

2. **#2: FMP API Rate Limit 관리 (250/day)**
   - 이유: FMP API 사용 여부 불확실 (현재 Alpha Vantage + yfinance 사용)
   - 조치: 실제 도입 시 재검토

---

## KB 통계

### 현재 상태 (2025-12-16)

```
총 지식: 8건
관계 수: 0개

유형별:
  pattern         █████ 5
  troubleshoot    ██ 2
  lesson          █ 1

도메인별:
  tech            ██████ 6
  project         ██ 2

신뢰도별:
  verified        █████ 5
  high            ███ 3
```

### 품질 지표

- **신뢰도 검증율**: 62.5% (5/8건 verified)
- **태그 커버리지**: 100% (모든 항목 태그 보유)
- **출처 명시율**: 100% (모든 항목 출처 명시)
- **도메인 분류**: 명확 (tech 75%, project 25%)

---

## 액션 아이템

### 즉시 조치 필요

| 우선순위 | 작업 | 담당 | 기한 |
|---------|------|------|------|
| 🔴 High | 큐 #4 삭제 (중복) | @qa-architect | 오늘 |
| 🔴 High | 큐 #5 승인 및 KB 추가 | @qa-architect | 오늘 |

### 2주 내 조치

| 우선순위 | 작업 | 담당 | 기한 |
|---------|------|------|------|
| 🟠 Medium | 큐 #3 승인 및 KB 추가 | @qa-architect | 1주 |
| 🟠 Medium | 큐 #1 내용 보강 또는 삭제 | @infra | 2주 |

### 장기 모니터링

| 우선순위 | 작업 | 담당 | 기한 |
|---------|------|------|------|
| 🟡 Low | SSE 패턴 universal 승격 검토 | @qa-architect | 3개월 |
| 🟡 Low | Phase 패턴 다른 프로젝트 적용 추적 | @qa-architect | 6개월 |

---

## 교훈 적용 체크리스트

다음 프로젝트에서 AI 기능 구현 시 참고:

- [ ] Django ASGI 환경에서는 async_to_sync 사용 (new_event_loop 금지)
- [ ] async 컨텍스트 ORM 호출 시 @sync_to_async 필수
- [ ] SSE 인증: EventSource 대신 fetch API 고려
- [ ] DRF SSE: EventStreamRenderer 커스텀 렌더러 추가
- [ ] LLM 응답: XML/JSON 구조화로 파싱 용이하게
- [ ] SSE Phase 시스템: 명확한 상태 전달로 UX 개선
- [ ] AI 기능 UX: 심플함 우선, 화려함은 나중
- [ ] Django Choices 추가 시: 마이그레이션 필수
- [ ] 모델 필드명: 작업 전 models.py 확인 습관화

---

## 결론

AI Analysis 기능 구현 과정에서 얻은 8개의 교훈을 KB에 성공적으로 추가했습니다.

### 성과

1. **고품질 교훈 추가**: verified 5건, high 3건
2. **검색 가능성**: 모든 항목이 적절한 태그와 도메인으로 분류
3. **중복 제거**: 큐 항목 1건 중복 발견 및 삭제 예정
4. **승격 후보 식별**: 3개 패턴이 universal 레벨 후보

### 다음 단계

1. 큐 정리 (중복 삭제, 보류 항목 검토)
2. 빈 데이터 처리 교훈 추가 승인
3. 3개월 후 SSE 패턴 universal 승격 재검토

---

**작성자**: @qa-architect
**검토 상태**: 완료
**마지막 업데이트**: 2025-12-16

# FMP Migration Documentation

## Overview

Alpha Vantage에서 Financial Modeling Prep (FMP)로 마이그레이션하기 위한 아키텍처 설계 및 실행 계획 문서입니다.

## Documents

### 1. Architecture Design (`architecture-design.md`)
**전체 1,773줄 - 상세 설계 문서**

#### 주요 섹션:
1. **개요**: 마이그레이션 목적 및 핵심 요구사항
2. **현재 시스템 분석**: 3계층 아키텍처 (Client-Processor-Service) 분석
3. **설계 원칙**: SOLID 원칙 기반 설계 철학
4. **API Provider 추상화 레이어**: `StockDataProvider` 추상 클래스 정의
5. **디렉토리 구조**: 새로운 `providers/` 구조 제안
6. **Feature Flag 메커니즘**: 환경 변수 기반 점진적 전환 전략
7. **캐싱 전략**: Decorator 패턴 기반 외부 캐싱
8. **에러 핸들링**: Fallback 메커니즘 및 Circuit Breaker 패턴
9. **마이그레이션 로드맵**: 4단계 점진적 전환 계획
10. **테스트 전략**: Unit/Integration/Performance 테스트

## Quick Start

### 읽기 순서 (역할별)

#### @backend
1. [현재 시스템 분석](#현재-시스템-분석) - 기존 코드 이해
2. [API Provider 추상화 레이어](#api-provider-추상화-레이어) - 구현할 인터페이스
3. [디렉토리 구조](#디렉토리-구조) - 코드 재구성 방법
4. [마이그레이션 로드맵 Phase 2](#phase-2-fmp-구현-2주) - FMP 구현 작업

#### @qa
1. [테스트 전략](#테스트-전략) - 전체 테스트 계획
2. [에러 핸들링](#에러-핸들링-및-fallback) - 검증해야 할 에러 시나리오
3. [마이그레이션 로드맵](#마이그레이션-로드맵) - 각 Phase별 검증 항목

#### @infra
1. [Feature Flag 메커니즘](#feature-flag-메커니즘) - 환경 변수 설정
2. [캐싱 전략](#캐싱-전략) - Redis 캐시 설정
3. [마이그레이션 로드맵 Phase 3](#phase-3-점진적-전환-2주) - 배포 및 모니터링

## Key Concepts

### 1. Provider 추상화 레이어

```python
# Before (나쁜 예 - Alpha Vantage에 강결합)
from API_request.alphavantage_service import AlphaVantageService

service = AlphaVantageService(api_key)
stock = service.update_stock_data('AAPL')

# After (좋은 예 - Provider-agnostic)
from API_request.stock_service import StockService

service = StockService()  # Factory가 자동으로 Provider 선택
stock = service.update_stock_data('AAPL')
```

### 2. Feature Flag 전환

```bash
# .env 파일
STOCK_DATA_PROVIDER=alphavantage  # 기본 Provider

# 엔드포인트별 개별 전환
PROVIDER_SEARCH=fmp               # 검색만 FMP 사용
PROVIDER_QUOTE=alphavantage       # 실시간 주가는 Alpha Vantage 유지

# Fallback 설정
ENABLE_PROVIDER_FALLBACK=true
FALLBACK_PROVIDER=alphavantage
```

### 3. 디렉토리 구조 (제안)

```
API_request/
├── providers/
│   ├── base.py                    # StockDataProvider 추상 클래스
│   ├── alphavantage/
│   │   ├── client.py              # 기존 코드 이동
│   │   ├── processor.py           # 기존 코드 이동
│   │   └── provider.py            # 인터페이스 구현 (새)
│   └── fmp/
│       ├── client.py              # FMP HTTP 클라이언트 (새)
│       ├── processor.py           # FMP 데이터 변환 (새)
│       └── provider.py            # 인터페이스 구현 (새)
├── cache/
│   ├── base.py                    # 캐시 추상 클래스
│   ├── redis_cache.py             # Redis 구현
│   └── decorators.py              # @cached_provider_call
├── provider_factory.py            # Feature Flag 기반 Provider 선택
└── stock_service.py               # Provider-agnostic 서비스
```

## Migration Timeline

### Phase 1: 인프라 구축 (1주)
- [x] 추상 인터페이스 정의
- [x] Alpha Vantage Provider 래핑
- [x] Factory 패턴 구현
- [x] 캐싱 레이어 구현

### Phase 2: FMP 구현 (2주)
- [ ] FMP Client 구현
- [ ] FMP Processor 구현
- [ ] FMP Provider 구현
- [ ] 통합 테스트

### Phase 3: 점진적 전환 (2주)
**순서** (위험도 낮은 순):
1. Search API
2. Company Profile
3. Financial Statements
4. Weekly Prices
5. Daily Prices
6. Real-time Quote (마지막)

### Phase 4: 완전 전환 (1주)
- [ ] Alpha Vantage 의존성 제거
- [ ] 레거시 코드 정리
- [ ] 문서 업데이트

## Rollback Strategy

각 Phase에서 문제 발생 시:

```bash
# 긴급 롤백 (환경 변수만 변경)
STOCK_DATA_PROVIDER=alphavantage
ENABLE_PROVIDER_FALLBACK=false

# 코드 롤백 (Git)
git revert <commit-hash>

# 검증
python manage.py shell
>>> from API_request.stock_service import StockService
>>> service = StockService()
>>> service.provider.get_provider_name()
'AlphaVantage'  # 확인
```

## Testing Checklist

### Unit Tests
- [ ] Provider 인터페이스 테스트
- [ ] Alpha Vantage Provider 테스트
- [ ] FMP Provider 테스트
- [ ] Factory 패턴 테스트
- [ ] Cache Layer 테스트

### Integration Tests
- [ ] StockService 전체 플로우 테스트
- [ ] Database 저장 로직 테스트
- [ ] Fallback 메커니즘 테스트
- [ ] Feature Flag 전환 테스트

### Consistency Tests
- [ ] Alpha Vantage vs FMP 필드 일치성
- [ ] 데이터 품질 비교 (가격, 재무제표)
- [ ] 응답 시간 비교

### Performance Tests
- [ ] 캐시 성능 향상 확인
- [ ] Rate Limiting 검증
- [ ] Circuit Breaker 동작 확인

## Monitoring Metrics

마이그레이션 중 모니터링해야 할 지표:

| 메트릭 | 목표 | 측정 방법 |
|-------|------|----------|
| API 성공률 | > 99% | Provider별 성공/실패 비율 |
| 응답 시간 | < 2초 (캐시 미스) | 평균 응답 시간 추적 |
| 캐시 적중률 | > 70% | Redis 통계 |
| Fallback 발생 | < 5% | 로그 분석 |
| 데이터 일관성 | 100% | 샘플링 비교 |

## References

### External Documentation
- [Alpha Vantage API Docs](https://www.alphavantage.co/documentation/)
- [FMP API Docs](https://site.financialmodelingprep.com/developer/docs)
- [Django Cache Framework](https://docs.djangoproject.com/en/stable/topics/cache/)

### Internal Documentation
- `CLAUDE.md` - 프로젝트 전체 가이드
- `docs/architecture-design.md` - 상세 설계 문서 (본 문서)
- `shared_kb/` - Engineering Knowledge Base

## FAQ

### Q1: 왜 Alpha Vantage를 FMP로 교체하나요?
**A**: Rate Limit 제한 (무료 티어 500 calls/day)과 느린 응답 속도 때문입니다. FMP는 더 빠른 응답과 높은 제한을 제공합니다.

### Q2: 마이그레이션 중 서비스 중단이 있나요?
**A**: 없습니다. Feature Flag와 Fallback 메커니즘을 통해 무중단 전환이 가능합니다.

### Q3: 두 Provider를 동시에 사용할 수 있나요?
**A**: 네. 엔드포인트별로 다른 Provider를 사용할 수 있습니다 (예: 검색은 FMP, 실시간 주가는 Alpha Vantage).

### Q4: 데이터 일관성은 어떻게 보장하나요?
**A**: Processor 레이어에서 두 Provider의 응답을 동일한 형식으로 정규화합니다. Integration 테스트로 검증합니다.

### Q5: 비용은 얼마나 증가하나요?
**A**: FMP 무료 티어는 250 calls/day입니다. 프로덕션에서는 유료 플랜 필요 (월 $14~$99, 플랜별 상이).

### Q6: 롤백이 어렵지 않나요?
**A**: 환경 변수만 변경하면 즉시 롤백 가능합니다. 코드 변경 없이 Provider 전환이 가능하도록 설계되었습니다.

## Contributors

- **@qa-architect**: 아키텍처 설계 및 문서 작성
- **@backend**: FMP Provider 구현 담당 (예정)
- **@infra**: 배포 및 모니터링 설정 (예정)

---

**Last Updated**: 2025-12-08
**Document Version**: 1.0
**Status**: ✅ Architecture Design Complete → 🔨 Implementation Phase

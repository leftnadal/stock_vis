# CS-0-0: 레거시 정리 + API 접근 테스트

> **완료일**: 2026-04-02

## 결과

### 1단계: 레거시 코드 정리
- serverless/ Chain Sight 뷰 6개 제거
- serverless/ Chain Sight 서비스 3개 파일 제거
- serverless/urls.py chain-sight/* 라우트 제거
- frontend/ Chain Sight 컴포넌트 일괄 제거 + 탭 비활성화
- StockRelationship, CategoryCache: 6개 서비스 참조 → LEGACY_KEEP 태그 처리 (모델 유지)
- ETFProfile, ETFHolding, ThemeMatch: DC-2까지 보관 (`LEGACY_KEEP_UNTIL_DC2`)

### 2단계: API 접근 테스트
- 의사결정 기록: `docs/chain_sight/decisions/003_api_access_test.md`

| API | 결과 | 영향 |
|-----|------|------|
| FMP Stock Peers | ✅ 200 | DC-1 Peer 품질 향상 |
| Finnhub Supply Chain | ❌ 403 | DC-3 수동시드 + DC-4 Gemini 유지 |
| Finnhub ETF Holdings | ❌ 403 | DC-2 CSV 다운로드 방식 |
| Finnhub Insider | ✅ 200 | CS-2-1c InsiderSignal 구현 가능 |
| FMP Revenue Segmentation | ✅ 200 | CS-2-1b SensitivityProfile 구현 가능 |

### 3단계: RelationConfidence v2.1 마이그레이션
- 3-tier 점수 (truth/market/investment_relevance)
- 5단계 상태 (hidden/weak/probable/confirmed/stale)
- 7개 evidence source boolean 필드

## 다음 작업

→ CS-0-1: 마이그레이션 검증

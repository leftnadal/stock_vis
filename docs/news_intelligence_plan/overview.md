# News Intelligence Pipeline v3 — 전체 설계 개요

## 아키텍처

```
뉴스 수집 (Finnhub/Marketaux)
    ↓
Phase 1: 규칙 엔진 분류 (Engine A/B/C)
    ↓ importance_score, rule_tickers, rule_sectors
Phase 2a: LLM 심층 분석 (Gemini 2.5 Flash, 3-Tier)
    ↓ llm_analysis (direct/indirect/opportunity/sector_ripple)
Phase 2b: ML Label 수집 (DailyPrice +24h 변동폭)
    ↓ ml_label_24h, ml_label_confidence
Phase 3: Neo4j 통합 (NewsEvent 노드 + 영향 관계)
    ↓ Graph DB 저장
Phase 4: ML 학습 + Shadow Mode
    ↓ Engine C 가중치 자동 업데이트
Phase 5: Production Mode
    ↓ Safety Gate 정식 가동
Phase 6: LightGBM 전환
    ↓ 고도화
```

## 핵심 설계 결정

### 1. LLM 통일: Gemini 2.5 Flash
- 비용: 월 ~$0 (무료 한도 내, 1500 RPD 중 ~220 RPD 사용)
- 프롬프트 깊이로 Tier 차등화 (A/B/C)

### 2. ML Label: Company News 우선
- Finnhub Company News = ticker 명시 → Engine A+B 불필요
- 순환 의존 방지: ML 학습 → label → 종목 매칭 → Engine 품질

### 3. Safety Gate + Shadow Mode
- 초기 4주 Shadow Mode (배포 안 함, 기록만)
- F1 > 0.55 연속 4주 → Production 진입
- 3단계 Safety Gate: F1, 하락폭, 가중치 변동

### 4. 당일 누적 퍼센타일
- 배치 단위가 아닌 당일 전체 뉴스 기준 상위 15%
- 일관된 품질 기준 + 소급 선별 가능

### 5. label_confidence
- 같은 종목 뉴스 수에 따른 노이즈 가중치
- 금요일/휴일 감쇠 (주말 이벤트 개입 방지)

## 타임라인

| 마일스톤 | 시기 |
|----------|------|
| Label 수집 시작 | Week 3 |
| 3,000건 축적 완료 | Week 6-7 |
| ML 첫 학습 | Week 7 |
| Shadow Mode 종료 | Week 10-11 |
| ML 실전 투입 | Week 11-12 |

## 수집량 현실

| 소스 | 일간 추정 |
|------|----------|
| Finnhub General | ~50-100건 |
| Finnhub Company | ~100-200건 |
| MarketAux | ~50-100건 |
| **합계** | **~200-400건** |

## Gemini RPD 사용량

| 항목 | RPD |
|------|-----|
| 현재 스케줄 | ~103 |
| 현재 온디맨드 | ~5-17 |
| 뉴스 심층 분석 | ~100 |
| **합계** | **~208-220** |
| **무료 한도** | **1,500** |
| **사용률** | **~15%** |

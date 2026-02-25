# Phase 2: LLM 심층 분석 + ML Label 수집 (✅ 완료)

## 기간
Week 3-4

## 구현 내용

### LLM 심층 분석 — `news/services/news_deep_analyzer.py`

**Gemini 2.5 Flash 3-Tier 분석**

| Tier | importance_score | 분석 범위 | Max Tokens |
|------|-----------------|-----------|------------|
| A | ≥ 0.70 | direct_impact만 | 2,000 |
| B | ≥ 0.85 | direct + indirect (최대 3개) + chain_logic | 4,000 |
| C | ≥ 0.93 | 전체 + opportunity + sector_ripple | 6,000 |

**출력 스키마 (llm_analysis JSON)**:
```json
{
  "direct_impacts": [{"symbol": "NVDA", "direction": "bullish", "confidence": 0.95, "reason": "..."}],
  "indirect_impacts": [{"symbol": "TSLA", "direction": "bullish", "confidence": 0.7, "chain_logic": "..."}],
  "opportunities": [{"symbol": "ARM", "thesis": "...", "timeframe": "...", "confidence": 0.6}],
  "sector_ripple": [{"sector": "Technology", "direction": "positive", "reason": "..."}],
  "tier": "C",
  "analyzed_at": "2026-02-06T10:30:00Z"
}
```

**주요 기능**:
- `genai.Client` 동기 호출 (Celery 호환)
- Ticker 유효성 검증 (Stock DB와 대조)
- 4초 간격 RPM 준수 (15 RPM Gemini Free)
- JSON 파싱 + 기본값 주입

### ML Label 수집 — `news/services/ml_label_collector.py`

**DailyPrice 기반 +24h 변동폭 계산**:
- `label = (close[t+1 거래일] - close[t]) / close[t] × 100`
- Company News 우선 처리 (source_tickers 사용, Engine A+B 불필요)

**섹터별 threshold**:
- Technology: 2.5%, Healthcare: 2.0%, Financials: 1.5%
- Utilities: 1.0%, Energy: 2.0%, Consumer Discretionary: 2.0% 등

**label_confidence 계산**:
| 조건 | confidence |
|------|-----------|
| 당일 같은 종목 뉴스 1건 | 1.0 |
| 당일 같은 종목 뉴스 2건 | 0.6 |
| 당일 같은 종목 뉴스 3건+ | 0.3 |
| 금요일 뉴스 | ×0.5 감쇠 |
| 장 휴일 전날 뉴스 | ×0.5 감쇠 |

**NYSE 거래 캘린더**:
- 2025-2026년 휴일 하드코딩
- `is_trading_day()`, `next_trading_day()`, `is_pre_holiday()` 유틸리티

### Celery 태스크
- `analyze_news_deep`: 매 2시간 (08:30~18:30, 평일), max 50건/배치
- `collect_ml_labels`: 매일 19:00 EST (장 마감 + 1시간)

### 테스트
- `tests/news/test_news_deep_analyzer.py`: 102개 테스트
- `tests/news/test_ml_label_collector.py`: 92개 테스트
- **전체 286개 신규 테스트 통과, 363개 뉴스 테스트 통과**

## 검증 결과
- Django API 정상 응답
- Frontend 뉴스 페이지 정상 렌더링
- Django Admin에서 모든 신규 필드 확인 완료

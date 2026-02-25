# Phase 1: 규칙 엔진 + 모델 변경 (✅ 완료)

## 기간
Week 1-2

## 구현 내용

### 모델 변경 — `news/models.py`
NewsArticle에 9개 필드 추가:
- `importance_score` (Float): Engine C 규칙 기반 중요도 점수
- `rule_sectors` (JSON): 규칙 엔진 추출 섹터 리스트
- `rule_tickers` (JSON): 규칙 엔진 추출 티커 리스트
- `llm_analyzed` (Boolean): LLM 심층 분석 완료 여부
- `llm_analysis` (JSON): LLM 심층 분석 결과
- `ml_label_24h` (Float): 발행 후 다음 거래일 변동폭 (%)
- `ml_label_important` (Boolean): 섹터별 threshold 적용 중요 뉴스 여부
- `ml_label_confidence` (Float): Label 신뢰도 (0~1)
- `ml_label_updated_at` (DateTime): ML Label 업데이트 시간

MLModelHistory 모델 추가:
- `model_version`, `algorithm`, `training_samples`, `feature_count`
- `f1_score`, `precision`, `recall`, `accuracy`
- `weights`, `smoothed_weights`, `feature_importance`, `training_config`
- `safety_gate_passed`, `safety_gate_details`
- `deployment_status`, `deployed_at`, `shadow_comparison`

마이그레이션: `news/migrations/0004_news_intelligence_pipeline_v3.py`

### 3-Engine 분류 서비스 — `news/services/news_classifier.py`

**Engine A: 종목 매칭 (`extract_tickers`)**
- NewsEntity 심볼 → Cashtag regex (`$AAPL`) → Exchange bracket regex (`(NASDAQ: AAPL)`) → SymbolMatcher
- 동음이의어 필터 (META, NOW 등 → 주식 컨텍스트 단어 필요)

**Engine B: 섹터 분류 (`extract_sectors`)**
- 16카테고리 170개 키워드→섹터 매핑 (`keyword_sector_map.py`)
- Technology, Communication Services, Healthcare, Financials 등

**Engine C: 5-Factor 중요도 스코어링 (`calculate_importance`)**
- β₁: source_credibility (0.15) — Reuters 1.0, Bloomberg 0.95 등
- β₂: entity_count (0.20) — (tickers + sectors) / 5
- β₃: sentiment_magnitude (0.20) — abs(sentiment_score)
- β₄: recency (0.25) — 2시간: 1.0, 6시간: 0.85, 24시간: 0.5
- β₅: keyword_relevance (0.20) — sectors / 3

**당일 누적 퍼센타일 선별 (`select_for_analysis`)**
- 상위 15% threshold, llm_analyzed=False 필터
- 최소 1건 보장 (빈 배치 방지)

### 키워드-섹터 매핑 — `news/services/keyword_sector_map.py`
- 16개 카테고리, ~170개 키워드
- `match_sectors(text)` → 정렬된 섹터 리스트

### Celery 태스크 — `news/tasks.py`
- `classify_news_batch`: 매 2시간 (08:15~18:15, 평일)

### Admin — `news/admin.py`
- NewsArticleAdmin: importance_score, llm_analyzed 컬럼 추가
- "Intelligence Pipeline v3", "ML Labels" 필드셋 추가
- MLModelHistoryAdmin 등록

### 테스트 — `tests/news/test_news_classifier.py`
- 92개 테스트: Engine A/B/C, classify_batch, select_for_analysis

## 검증 결과
- 92개 테스트 전체 통과
- 실 DB 테스트: 103/284 기사 분류 완료 (점수 범위 0.26~0.78)
- Django Admin 정상 표시

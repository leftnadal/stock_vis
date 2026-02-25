# News Intelligence Pipeline v3 — 최종 종합 문서

## 프로젝트 개요

뉴스 기반 투자 인사이트 파이프라인. 6단계 Phase를 통해 규칙 엔진부터 ML 자동 배포까지 구축.

**핵심 목표**: 뉴스 수집 → 규칙 기반 분류 → LLM 심층 분석 → ML 가중치 최적화 → 자동 배포

---

## 아키텍처 총괄

```
[뉴스 수집]          [규칙 엔진]          [LLM 분석]        [ML 학습]         [Production]
Finnhub/Marketaux → Engine A(종목) → Gemini 2.5 Flash → Logistic Reg → Auto Deploy
                    Engine B(섹터)   (Tier A/B/C)       LightGBM       Safety Gate
                    Engine C(스코어)                     Shadow Mode    Weekly Report
                                                                       ↓
                                    [Neo4j]              [Label 수집]   Engine C 자동 업데이트
                                    NewsEvent 노드       DailyPrice 기반
                                    Impact 관계          +24h 변동폭
```

---

## Phase별 요약

### Phase 1: 규칙 엔진 + 모델 변경 (Week 1-2)

| 구성 요소 | 파일 | 설명 |
|-----------|------|------|
| Engine A | `news/services/news_classifier.py` | SymbolMatcher + cashtag/괄호 regex |
| Engine B | `news/services/keyword_sector_map.py` | 16개 섹터 키워드 매핑 |
| Engine C | `news/services/news_classifier.py` | 5-factor 가중 합산 (β₁~β₅) |
| 퍼센타일 선별 | `select_for_analysis()` | 당일 누적 상위 15%, 미분석 필터 |
| 모델 변경 | `news/models.py` | importance_score, rule_sectors/tickers, ML label 필드 |

### Phase 2: LLM 심층 분석 + ML Label 수집 (Week 3-4)

| 구성 요소 | 파일 | 설명 |
|-----------|------|------|
| LLM 분석 | `news/services/news_deep_analyzer.py` | Gemini 2.5 Flash, Tier A/B/C 프롬프트 |
| ML Label | `news/services/ml_label_collector.py` | DailyPrice +24h 변동폭, 섹터별 threshold |
| Confidence | `ml_label_confidence` | 같은 종목 뉴스 수 + 주말/휴일 감쇠 |

### Phase 3: Neo4j 통합 + API (Week 5-6)

| 구성 요소 | 파일 | 설명 |
|-----------|------|------|
| Neo4j Sync | `news/services/news_neo4j_sync.py` | NewsEvent 노드, Impact 관계 |
| Sector Ripple | `propagate_sector_ripple()` | 대형주 → 같은 섹터 중소형주 2-hop 확산 (20개 캡, 0.4배 감쇠) |
| TTL | 관계별 차등 | DIRECTLY 30일, INDIRECTLY 21일, POTENTIALLY 14일, AFFECTS_SECTOR 21일 |
| API | `news/api/views.py` | news-events, impact-map 엔드포인트 |

### Phase 4: ML 학습 + Shadow Mode + 프론트엔드 (Week 7-10)

| 구성 요소 | 파일 | 설명 |
|-----------|------|------|
| ML Optimizer | `news/services/ml_weight_optimizer.py` | Logistic Regression, Time-Series CV |
| Safety Gate | 3단계 | F1>=0.55, Precision>=0.50, 하락<=10%p |
| Smoothing | 0.7×new + 0.3×prev | 급격한 가중치 변동 방지 |
| Shadow Mode | 병렬 비교 | ML vs 수동 선별 agreement_rate |
| 프론트엔드 | `MLModelStatusCard.tsx` | 모델 상태, 데이터 현황, 성능 추이 |

### Phase 5: ML Production Mode (Week 11-12)

| 구성 요소 | 파일 | 설명 |
|-----------|------|------|
| Production Manager | `news/services/ml_production_manager.py` | 자동 배포, 롤백, 리포트 |
| 자동 배포 | `check_auto_deploy` | 4주 연속 Gate 통과 + agreement>=0.70 |
| 연속 하락 감지 | `detect_consecutive_decline` | 3주 연속 F1 하락 → Rolling Window 축소 (8→6→4주) |
| LLM 정확도 | `measure_llm_accuracy` | 예측 방향 vs 실제 주가 비교 |
| 주간 리포트 | `generate_weekly_report` | 성능 추이, 추천 사항 |
| Engine C 통합 | `_load_deployed_weights()` | 배포 가중치 자동 적용, 폴백 내장 |
| 프론트엔드 | `NewsEventTimeline.tsx` | 뉴스 이벤트 타임라인 + chain_logic tooltip |

### Phase 6: ML Phase 2 — LightGBM (Month 3+)

| 구성 요소 | 파일 | 설명 |
|-----------|------|------|
| 확장 Feature | `extract_extended_features()` | 10개 feature (기존 5 + 확장 5) |
| General News | `prepare_extended_training_data()` | confidence >= 0.8 General News 포함 |
| LightGBM | `train_lightgbm()` | Gradient Boosting, Feature Importance |
| A/B 테스트 | `ab_test()` | LR vs LightGBM 비교 |
| 전환 조건 | `check_lightgbm_readiness()` | 10K 데이터, 정체, feature 안정화 |

---

## 서비스 클래스 전체 목록

| 서비스 | 파일 | Phase |
|--------|------|-------|
| `NewsClassifier` | `news/services/news_classifier.py` | 1, 5 |
| `NewsDeepAnalyzer` | `news/services/news_deep_analyzer.py` | 2 |
| `MLLabelCollector` | `news/services/ml_label_collector.py` | 2 |
| `NewsNeo4jSyncService` | `news/services/news_neo4j_sync.py` | 3 |
| `MLWeightOptimizer` | `news/services/ml_weight_optimizer.py` | 4, 6 |
| `MLProductionManager` | `news/services/ml_production_manager.py` | 5 |

---

## Celery Beat 스케줄 (일요일)

```
03:00  train_importance_model       LR 학습 (Phase 4)
03:30  generate_shadow_report       Shadow 비교 (Phase 4)
04:00  check_auto_deploy            자동 배포 체크 (Phase 5)
04:15  generate_weekly_ml_report    주간 리포트 (Phase 5)
04:20  monitor_ml_performance       연속 하락 감지 (Phase 5)
04:30  train_lightgbm_model         LightGBM 학습 (Phase 6, 조건부)
```

## Celery Beat 스케줄 (평일)

```
04:00  cleanup_expired_news_rels    만료 관계 정리
06:00  collect_daily_news           종목 뉴스 수집 (Company News)
06:30  collect_category_news(high)  카테고리 뉴스 (High, 2회/일)
07:00  collect_category_news(med)   카테고리 뉴스 (Medium, 1회/일)
08:15  classify_news_batch          분류 (2시간 단위: 08/10/12/14/16/18시)
08:30  analyze_news_deep            LLM 분석 (2시간 단위: 08/10/12/14/16/18시)
08:45  sync_news_to_neo4j           Neo4j 동기화 (2시간 단위: 08/10/12/14/16/18시)
12:00  collect_market_news          시장 뉴스 수집 (General News, 1차)
17:00  collect_category_news(high)  카테고리 뉴스 (High, 2차)
18:00  collect_market_news          시장 뉴스 수집 (General News, 2차)
19:00  collect_ml_labels            ML Label 수집
```

---

## API 엔드포인트 전체 목록

| 엔드포인트 | Phase | 설명 |
|-----------|-------|------|
| `GET /api/v1/news/all/` | - | 뉴스 목록 (필터, 페이지네이션) |
| `GET /api/v1/news/sources/` | - | 소스별 건수 |
| `GET /api/v1/news/stock/{symbol}/` | - | 종목별 뉴스 |
| `GET /api/v1/news/stock/{symbol}/sentiment/` | - | 종목 감성 분석 |
| `GET /api/v1/news/trending/` | - | 트렌딩 종목 |
| `GET /api/v1/news/market/` | - | 시장 뉴스 |
| `GET /api/v1/news/daily-keywords/` | 2 | LLM 키워드 |
| `GET /api/v1/news/insights/` | 3 | 종목 인사이트 |
| `GET /api/v1/news/market-feed/` | A | AI 브리핑 (콜드 스타트) |
| `GET /api/v1/news/interest-options/` | B | 관심사 옵션 |
| `GET /api/v1/news/personalized-feed/` | B | 맞춤 피드 |
| `GET /api/v1/news/news-events/` | 3 | Neo4j 뉴스 이벤트 |
| `GET /api/v1/news/news-events/impact-map/` | 3 | 영향도 맵 |
| `GET /api/v1/news/ml-status/` | 4 | ML 모델 상태 |
| `GET /api/v1/news/ml-shadow-report/` | 4 | Shadow 비교 리포트 |
| `GET /api/v1/news/ml-weekly-report/` | 5 | 주간 ML 리포트 |
| `GET /api/v1/news/ml-lightgbm-readiness/` | 6 | LightGBM 전환 준비 |

---

## 테스트 현황

| 테스트 파일 | 테스트 수 | Phase |
|------------|----------|-------|
| `test_news_classifier.py` | 100+ | 1 |
| `test_news_deep_analyzer.py` | 80+ | 2 |
| `test_ml_label_collector.py` | 60+ | 2 |
| `test_news_neo4j_sync.py` | 80+ | 3 |
| `test_ml_weight_optimizer.py` | 61 | 4 |
| `test_ml_production_manager.py` | 56 | 5 |
| `test_lightgbm.py` | 41 | 6 |
| `test_market_feed.py` | 기타 | A |
| **전체** | **587** | - |

---

## 주요 모델 필드 (NewsArticle)

```
# 규칙 엔진 (Phase 1)
importance_score    Float       Engine C 스코어 (0~1)
rule_sectors        JSONField   추출 섹터 리스트
rule_tickers        JSONField   추출 티커 리스트

# LLM 분석 (Phase 2)
llm_analyzed        Boolean     분석 완료 여부
llm_analysis        JSONField   분석 결과 (impacts, chain_logic 등)

# ML Label (Phase 2)
ml_label_24h        Float       +24h 변동폭 (%)
ml_label_important  Boolean     중요 뉴스 여부
ml_label_confidence Float       Label 신뢰도 (0~1)
ml_label_updated_at DateTime    Label 업데이트 시각
```

## 주요 모델 (MLModelHistory)

```
model_version       CharField   버전 (lr_v1_..., lgbm_v2_...)
algorithm           CharField   logistic_regression / lightgbm
feature_count       Integer     5 (LR) 또는 10 (LightGBM)
f1_score            Float       F1 Score
weights             JSONField   원본 가중치
smoothed_weights    JSONField   Smoothing 적용 가중치
feature_importance  JSONField   Feature Importance 리포트
safety_gate_passed  Boolean     Gate 통과 여부
deployment_status   CharField   shadow / deployed / rolled_back / failed
shadow_comparison   JSONField   ML vs 수동 비교
```

---

## 의존성

```
scikit-learn    Logistic Regression (Phase 4)
lightgbm        LightGBM Gradient Boosting (Phase 6)
```

---

## 운영 규칙

### Shadow Mode → Production 전환
1. 4주 연속 Safety Gate 통과 (F1 >= 0.55)
2. Shadow 비교 agreement_rate >= 0.70
3. `check_auto_deploy` 태스크가 자동 배포 실행
4. Engine C가 다음 분류 배치부터 ML 가중치 사용

### 롤백
1. `MLProductionManager.rollback_model()` 호출
2. deployed 모델 → rolled_back 전환
3. Engine C 자동으로 DEFAULT_WEIGHTS 복귀

### LightGBM 전환
1. 매주 자동으로 3가지 조건 체크
2. 모두 충족 시 LightGBM 자동 학습
3. A/B 테스트로 LR 대비 성능 확인
4. Safety Gate 통과 시 Shadow Mode 진입
5. 이후 기존 배포 프로세스와 동일

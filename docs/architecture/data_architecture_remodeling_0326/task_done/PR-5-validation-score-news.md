# PR-5: CategoryScore + ValidationNewsSummary — 완료 보고서

> 완료일: 2026-03-27

---

## 작업 요약

validation 앱에 CategoryScore(7개 카테고리별 종합 점수)와 ValidationNewsSummary(뉴스 감성/이벤트 집계 캐시) 모델을 추가했습니다.

## 완료 항목

| # | 항목 | 상태 |
|---|------|------|
| 1 | CategoryScore 모델 생성 (score/grade nullable) | ✅ |
| 2 | ValidationNewsSummary 모델 생성 | ✅ |
| 3 | admin 등록 | ✅ |
| 4 | validation models/__init__.py에 4개 모델 전부 export | ✅ |
| 5 | 기존 코드 영향 없음 | ✅ |

## 생성/수정된 파일

### 신규 생성
- `validation/migrations/0002_validationnewssummary_categoryscore.py`

### 수정
- `validation/models/category_score.py` — placeholder → 모델 구현
- `validation/models/news_summary.py` — placeholder → 모델 구현
- `validation/models/__init__.py` — CategoryScore, ValidationNewsSummary export 추가
- `validation/admin.py` — CategoryScore, ValidationNewsSummary admin 등록

## 검증 결과

```
CategoryScore unique_together: (symbol, category)
score nullable: null=True, blank=True
grade blank: True

ValidationNewsSummary PK: symbol (OneToOne→Stock)
validation models export 4개: 모두 True
```

## 모델 구조

### CategoryScore
- symbol (FK→Stock), category (7개 choices)
- MVP: signal (green/yellow/red), signal_reason
- Phase 2: score, grade, rank_in_industry, total_in_industry
- contributing_metrics (JSONField), score_1y_ago, score_change
- unique_together: (symbol, category)
- DB: `validation_category_score`

### ValidationNewsSummary
- symbol (PK, OneToOne→Stock)
- event_count_30d, event_count_90d, avg_sentiment_30d, sentiment_trend
- dominant_event_type, high_importance_count
- has_regulatory_risk, has_exec_change, has_guidance_cut
- recent_highlights (JSONField)
- DB: `validation_news_summary`

## 기존 코드 영향

없음. validation 앱 내부 파일만 수정.

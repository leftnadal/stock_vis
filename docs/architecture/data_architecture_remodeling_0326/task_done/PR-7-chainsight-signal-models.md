# PR-7: CompanyInsiderSignal + CompanyNarrativeTag + CompanyEventReaction — 완료 보고서

> 완료일: 2026-03-27

---

## 작업 요약

chainsight 앱에 Tier A/B 신호 모델 3개를 추가했습니다. chainsight 앱 총 6개 모델 완성.

## 완료 항목

| # | 항목 | 상태 |
|---|------|------|
| 1 | CompanyInsiderSignal 모델 + 마이그레이션 | ✅ |
| 2 | CompanyNarrativeTag 모델 + 마이그레이션 (ArrayField 확인) | ✅ |
| 3 | CompanyEventReaction 모델 + 마이그레이션 (unique: symbol+event_type) | ✅ |
| 4 | admin 등록 (3개) | ✅ |
| 5 | chainsight/models/__init__.py에 6개 모델 export | ✅ |
| 6 | 기존 코드 영향 없음 | ✅ |

## 생성/수정된 파일

### 신규 생성
- `chainsight/models/insider_signal.py`
- `chainsight/models/narrative_tag.py`
- `chainsight/models/event_reaction.py`
- `chainsight/migrations/0002_companyinsidersignal_companynarrativetag_and_more.py`

### 수정
- `chainsight/models/__init__.py` — 3개 모델 export 추가 (총 6개)
- `chainsight/admin.py` — 3개 모델 admin 등록 추가 (총 6개)

## 검증 결과

```
CompanyInsiderSignal: PK=symbol (OneToOne→Stock)
CompanyNarrativeTag: PK=symbol (OneToOne→Stock), theme_tags=ArrayField
CompanyEventReaction: unique_together=(symbol, event_type), FK→Stock
chainsight __all__: 6개 모델
```

## 모델 구조

### CompanyInsiderSignal (PK: symbol OneToOne→Stock)
- 내부자: insider_buy/sell_count_90d, insider_net_amount_90d, insider_signal
- 기관: institutional_ownership_pct, institutional_change_qoq, top_holder_action
- 공매도: short_interest_pct, short_interest_change, days_to_cover
- 종합: smart_money_signal (bullish/neutral/bearish)

### CompanyNarrativeTag (PK: symbol OneToOne→Stock)
- primary/secondary_narrative, narrative_strength/sentiment
- theme_tags (ArrayField), avg_sentiment_30d, sentiment_trend, news_frequency_30d
- analyst_consensus, analyst_target_vs_price, analyst_revision_trend
- generated_by (llm_batch/rule_based/manual)

### CompanyEventReaction (FK→Stock, unique: symbol+event_type)
- event_type, sample_count
- avg_return_1d/5d, hit_rate_negative, avg_abnormal_return
- reaction_grade (5단계), confidence

## 기존 코드 영향

없음. chainsight 앱 내부 파일만 추가/수정.

# Stock-Vis 데이터 아키텍처 구축 — 프롬프트 실행 가이드

## 파일 구성

```
docs/architecture/
├── claude-code-reference-doc.md    ← 마스터 참고 문서 (모든 PR에서 참조)
└── prompts/
    ├── EXECUTION-GUIDE.md          ← 이 파일 (실행 순서 + 체크리스트)
    ├── PR-1-metrics-foundation.md
    ├── PR-2-metrics-snapshot-peer.md
    ├── PR-3-metrics-benchmarks.md
    ├── PR-4-sp500-validation-setup.md
    ├── PR-5-validation-score-news.md
    ├── PR-6-chainsight-financial-models.md
    ├── PR-7-chainsight-signal-models.md
    └── PR-8-chainsight-profile-news.md
```

## 실행 순서

**반드시 순서대로 실행. 각 PR은 이전 PR의 모델에 의존.**

```
Phase 1: 공통 기반 (metrics/)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PR-1 → PR-2 → PR-3

Phase 2: 1차 검증 (validation/)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PR-4 → PR-5

Phase 3: Chain Sight (chainsight/)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PR-6 → PR-7 → PR-8
```

## PR별 실행 방법

### Claude Code에 전달하는 방식

각 PR 실행 시 Claude Code에게:

1. **먼저 참고 문서를 읽게 한다:**
   "docs/architecture/claude-code-reference-doc.md를 먼저 읽어줘"

2. **그 다음 해당 PR 프롬프트를 전달:**
   "docs/architecture/prompts/PR-1-metrics-foundation.md 에 따라 작업해줘"

3. **작업 완료 후 검증:**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   python manage.py test [앱명] --verbosity=2
   ```

### 주의: Claude Code에게 한 번에 여러 PR을 주지 않는다

- PR-1 완료 확인 → PR-2 전달
- PR-2 완료 확인 → PR-3 전달
- 이런 식으로 한 단계씩

---

## 전체 체크리스트

### Phase 1: metrics/ (PR-1 ~ PR-3)

**PR-1: MetricDefinition + BatchJobRun**

- [ ] metrics/ 앱 생성
- [ ] MetricDefinition 모델
- [ ] BatchJobRun 모델
- [ ] seed_metric_definitions command (34개 지표)
- [ ] admin 등록
- [ ] `python manage.py seed_metric_definitions` 성공
- [ ] settings.py INSTALLED_APPS 추가

**PR-2: CompanyMetricSnapshot + PeerListCache**

- [ ] CompanyMetricSnapshot 모델 (FK: Stock, MetricDefinition)
- [ ] PeerListCache 모델
- [ ] admin 등록
- [ ] unique_together 확인

**PR-3: IndustryMetricBenchmark + PeerMetricBenchmark**

- [ ] IndustryMetricBenchmark 모델 (benchmark_confidence 포함)
- [ ] PeerMetricBenchmark 모델 (benchmark_confidence 포함)
- [ ] admin 등록

### Phase 2: validation/ (PR-4 ~ PR-5)

**PR-4: SP500Constituent 수정 + validation 앱 기본**

- [ ] SP500Constituent에 3개 필드 추가 (마이그레이션)
- [ ] 기존 데이터 영향 없음 확인
- [ ] validation/ 앱 생성
- [ ] CompanyMetricLatest 모델
- [ ] CompanyBenchmarkDelta 모델
- [ ] admin 등록
- [ ] settings.py INSTALLED_APPS 추가

**PR-5: CategoryScore + ValidationNewsSummary**

- [ ] CategoryScore 모델 (score/grade nullable)
- [ ] ValidationNewsSummary 모델
- [ ] admin 등록
- [ ] validation/models/**init**.py 4개 모델 export

### Phase 3: chainsight/ (PR-6 ~ PR-8)

**PR-6: SensitivityProfile + GrowthStage + CapitalDNA**

- [ ] chainsight/ 앱 생성
- [ ] CompanySensitivityProfile 모델
- [ ] CompanyGrowthStage 모델
- [ ] CompanyCapitalDNA 모델
- [ ] admin 등록
- [ ] settings.py INSTALLED_APPS 추가

**PR-7: InsiderSignal + NarrativeTag + EventReaction**

- [ ] CompanyInsiderSignal 모델
- [ ] CompanyNarrativeTag 모델 (ArrayField)
- [ ] CompanyEventReaction 모델 (unique_together)
- [ ] admin 등록

**PR-8: RevenueStructure + ChainProfile + ChainNewsEvent**

- [ ] CompanyRevenueStructure 모델
- [ ] CompanyChainProfile 모델 (ArrayField)
- [ ] ChainNewsEvent 모델 (self FK, ArrayField, unique_together)
- [ ] admin 등록
- [ ] chainsight/models/**init**.py 9개 모델 전체 export
- [ ] 기존 stocks.StockNews 수정 없음 최종 확인

---

## 최종 검증

모든 PR 완료 후:

```bash
# 1. 전체 마이그레이션 상태 확인
python manage.py showmigrations metrics validation chainsight

# 2. 모델 수 확인
python manage.py shell -c "
from metrics.models import *
from validation.models import *
from chainsight.models import *
print('metrics:', len([MetricDefinition, CompanyMetricSnapshot, PeerListCache, IndustryMetricBenchmark, PeerMetricBenchmark, BatchJobRun]))
print('validation:', len([CompanyMetricLatest, CompanyBenchmarkDelta, CategoryScore, ValidationNewsSummary]))
print('chainsight:', len([CompanySensitivityProfile, CompanyGrowthStage, CompanyCapitalDNA, CompanyInsiderSignal, CompanyNarrativeTag, CompanyEventReaction, CompanyRevenueStructure, CompanyChainProfile, ChainNewsEvent]))
"
# 예상 출력: metrics: 6, validation: 4, chainsight: 9

# 3. MetricDefinition 시드 확인
python manage.py shell -c "
from metrics.models import MetricDefinition
print(f'Metric definitions: {MetricDefinition.objects.count()}')
# 예상: 34
"

# 4. 기존 앱 영향 없음 확인
python manage.py test stocks --verbosity=0
python manage.py test thesis --verbosity=0
python manage.py test macro --verbosity=0
```

## 생성되는 테이블 총 목록 (19개)

```
metrics_metric_definition          ← PR-1
metrics_batch_job_run              ← PR-1
metrics_company_metric_snapshot    ← PR-2
metrics_peer_list_cache            ← PR-2
metrics_industry_metric_benchmark  ← PR-3
metrics_peer_metric_benchmark      ← PR-3
validation_company_metric_latest     ← PR-4
validation_company_benchmark_delta   ← PR-4
validation_category_score            ← PR-5
validation_news_summary              ← PR-5
chainsight_sensitivity_profile       ← PR-6
chainsight_growth_stage              ← PR-6
chainsight_capital_dna               ← PR-6
chainsight_insider_signal            ← PR-7
chainsight_narrative_tag             ← PR-7
chainsight_event_reaction            ← PR-7
chainsight_revenue_structure         ← PR-8
chainsight_chain_profile             ← PR-8
chainsight_news_event                ← PR-8
```

- SP500Constituent 마이그레이션 1건 (필드 추가, PR-4)

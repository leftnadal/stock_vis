# CS-2-1: Tier A 프로파일 계산

> **작업 번호**: CS-2-1
> **목표**: GrowthStage, CapitalDNA 자동 계산 (+ API 결과에 따라 SensitivityProfile, InsiderSignal)
> **예상 소요**: 1~2일
> **선행 조건**: Phase 1 완료 + metrics/ 앱 작동 + CS-0-0 API 테스트 결과
> **산출물**: `chainsight/tasks/profile_tasks.py`

---

## 범위 결정 (CS-0-0 결과 기반)

| 프로파일 | 원천 | 조건 |
|---------|------|------|
| **GrowthStage** | metrics/ | ✅ 즉시 가능 |
| **CapitalDNA** | CashFlow + BalanceSheet | ✅ 즉시 가능 |
| **SensitivityProfile** | FMP Revenue Seg. | ⚠️ API 200일 때만 |
| **InsiderSignal** | Finnhub Insider | ⚠️ API 200일 때만 |

⚠️ **점검 결과**: Tier B `EventReaction`은 로드맵에서 "실행 가능 ✅"이나, Tier A 완료 후 별도 작업으로 진행. MVP 범위에서는 Tier A 우선.

## GrowthStage 분류

| Stage | 주요 조건 |
|-------|----------|
| startup | 매출 <$500M, 성장률 >30% |
| growth | 매출 성장률 >15%, 이익 성장률 >10% |
| mature | 매출 성장률 0~15%, 배당 지급 |
| decline | 매출 성장률 음수 2년 연속 |

## CapitalDNA 계산

| 성향 | 계산 | 범위 |
|------|------|------|
| buyback_tendency | 자사주매입 / FCF | 0~1 |
| dividend_tendency | 배당 / FCF | 0~1 |
| capex_tendency | CAPEX / Revenue | 0~1 |
| ma_tendency | M&A / Total Assets | 0~1 |

## 구현

```python
# chainsight/tasks/profile_tasks.py
@shared_task
def calculate_growth_stages(): ...

@shared_task
def calculate_capital_dna(): ...

@shared_task
def calculate_all_profiles():
    """통합 task. Celery Beat 주 1회 호출."""
    results = {}
    results["growth_stage"] = calculate_growth_stages()
    results["capital_dna"] = calculate_capital_dna()
    # 조건부: results["sensitivity"] = ...
    # 조건부: results["insider"] = ...
    return results
```

⚠️ metrics/ 모델의 실제 필드명을 확인한 뒤 `_get_growth_metrics()`, `_calculate_capital_dna()` 구현 조정.

## 사전 확인

```python
# metrics/ 데이터 존재 여부 확인
from metrics.models import CompanyMetricLatest
print(f"metrics 데이터: {CompanyMetricLatest.objects.count()}")
```

## 완료 기준

```
□ GrowthStage 테이블 적재 (~500건)
□ CapitalDNA 테이블 적재 (~500건)
□ (API 200) SensitivityProfile / InsiderSignal 적재
□ calculate_all_profiles 통합 task 동작
```

→ **다음**: cs_22

**END OF DOCUMENT**

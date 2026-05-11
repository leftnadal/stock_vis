# CS-2-1: Tier A 프로파일 계산 Tasks

> **작업 번호**: CS-2-1
> **로드맵 버전**: v1.4 (변경 없음)
> **목표**: GrowthStage, CapitalDNA 테이블 적재
> **예상 소요**: 2~3일
> **선행 조건**: Phase 1 완료 + metrics/ 앱 작동
> **산출물**: `chainsight/tasks/profile_tasks.py`

---

## 범위 (CS-0-0 API 테스트 결과에 따라 결정)

| Tier A 테이블 | 데이터 소스 | 실행 가능 여부 |
|--------------|-----------|-------------|
| GrowthStage | metrics/CompanyMetricLatest | ✅ 즉시 가능 |
| CapitalDNA | stocks/CashFlowStatement + BalanceSheet | ✅ 즉시 가능 |
| SensitivityProfile | FMP Revenue Segmentation | ⚠️ API 테스트 결과에 따라 |
| InsiderSignal | Finnhub Insider Transactions | ⚠️ API 테스트 결과에 따라 |

⚠️ Tier B EventReaction은 별도 작업 지시서로 분리. 현재 미작성 상태 (로드맵에 식별됨).

## GrowthStage 계산 로직

metrics/CompanyMetricLatest에서 매출 성장률, 이익 성장률 조회 → startup/growth/mature/decline 분류.

## CapitalDNA 계산 로직

CashFlowStatement에서 buyback/dividend/capex/m&a 비율 계산 → tendency 값 산출.

## Celery Task

```python
@shared_task
def calculate_all_profiles():
    calculate_growth_stages()
    calculate_capital_dna()
    # API 테스트 결과에 따라:
    # calculate_sensitivity_profiles()
    # calculate_insider_signals()
```

## 완료 기준

```
□ GrowthStage ~500건 적재
□ CapitalDNA ~500건 적재
□ Celery task 수동 실행 성공
```

→ **다음**: cs_22

**END OF DOCUMENT**

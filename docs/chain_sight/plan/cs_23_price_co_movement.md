# CS-2-3: PriceCoMovement 계산

> **작업 번호**: CS-2-3
> **목표**: 같은 섹터 내 종목 쌍 90일 rolling correlation → PriceCoMovement 적재
> **예상 소요**: 1일
> **선행 조건**: Phase 1 완료, stocks/DailyPrice 데이터 존재
> **산출물**: `chainsight/tasks/relation_tasks.py` (calculate_price_co_movement)

---

## 계산 범위 제한

S&P 500 전체 조합 C(500,2) = 124,750 → 비효율.
**같은 섹터 내에서만 계산** → ~10,000~15,000 쌍 (관리 가능).

## 구현

```python
@shared_task
def calculate_price_co_movement(period_days=90, min_correlation=0.5):
    """Celery Beat: 주 1회 (일요일 03:00)"""
    # Neo4j에서 섹터별 종목 그룹 조회
    # 각 섹터 내 모든 쌍의 일간 수익률 상관계수 계산 (numpy)
    # |correlation| >= min_correlation만 PriceCoMovement에 저장
```

⚠️ 실제 DailyPrice 모델 필드명/접근 방식 확인 필요.

## 완료 기준

```
□ PriceCoMovement 적재 확인
□ 상관계수 높은 쌍 합리성 확인
```

→ **다음**: cs_24

**END OF DOCUMENT**

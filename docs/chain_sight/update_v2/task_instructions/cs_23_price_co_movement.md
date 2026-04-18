# CS-2-3: PriceCoMovement 계산

> **작업 번호**: CS-2-3
> **로드맵 버전**: v1.4 (변경 없음)
> **목표**: 90일 rolling correlation 계산
> **예상 소요**: 1~2일
> **선행 조건**: CS-2-2 완료
> **산출물**: `chainsight/tasks/relation_tasks.py` 내 task

---

## 데이터 소스

`stocks/DailyPrice` — 일간 종가 기준 90일 rolling correlation.

## 구현

1. PEER_OF 또는 SAME_INDUSTRY 관계가 있는 종목 쌍 대상
2. 90일 종가 데이터 조회 → Pearson correlation 계산
3. PriceCoMovement 테이블 upsert (symbol_a < symbol_b 사전순)

## Celery Task

```python
@shared_task
def calculate_price_co_movement():
    """주간 실행"""
    # Celery Beat: crontab(hour=3, minute=0, day_of_week=0)
```

## 완료 기준

```
□ PriceCoMovement 적재 (correlation, period=90)
□ -1 ~ 1 범위 확인
□ 주간 Celery task 실행 성공
```

→ **다음**: cs_24

**END OF DOCUMENT**

# CS-2-4: RelationConfidence 종합 판정

> **작업 번호**: CS-2-4
> **로드맵 버전**: v1.4 (변경 없음)
> **목표**: RELATION_CONFIDENCE.md 정책표 기반 판정
> **예상 소요**: 2~3일
> **선행 조건**: CS-2-3 완료
> **산출물**: `chainsight/tasks/relation_tasks.py` 내 task

---

## 핵심 로직 (RELATION_CONFIDENCE.md 참조)

1. **증거 수집**: Peer, Industry, SupplyChain, News, Price, ETF, LLM 소스별 증거 확인
2. **Tier 분류**: Tier 1(API 직접) / Tier 2(파생 계산) / Tier 3(LLM/뉴스)
3. **truth_score 계산**: 상태 대표값 — confirmed(85), probable(60), weak(35), hidden(15)
4. **5단계 상태 판정**: hidden → weak → probable → confirmed / stale
5. **relation_basis_summary 생성**: 템플릿 기반 설명문
6. **7개 bool 플래그 갱신**: has_peer_source, has_industry_source, etc.

## 관계 분류

- **Truth 관계** (PEER_OF, SUPPLIES_TO, COMPETES_WITH, etc.): truth_score 계산 대상
- **Market 관계** (CO_MENTIONED, PRICE_CORRELATED): truth_score 비대상, confirmed 불가

## Celery Tasks

```python
@shared_task
def update_relation_confidence():
    """주간 실행 — 정책표 기반 판정"""
    # Celery Beat: crontab(hour=4, minute=0, day_of_week=0)

@shared_task
def check_stale_and_decay():
    """주간 실행 — 하향 전이"""
    # confirmed→stale, probable→weak, weak→hidden
    # Celery Beat: crontab(hour=4, minute=30, day_of_week=0)
```

## 완료 기준

```
□ RelationConfidence 테이블 적재
□ 5단계 상태 정상 분류
□ relation_basis_summary 생성
□ stale decay 로직 동작
★ M2 달성: "관계 신뢰도 엔진 작동"
```

→ **다음**: cs_25

**END OF DOCUMENT**

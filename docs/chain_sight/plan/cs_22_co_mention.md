# CS-2-2: CoMentionEdge 추출

> **작업 번호**: CS-2-2
> **목표**: Marketaux 뉴스에서 종목 동시출현 쌍 추출 → CoMentionEdge 적재
> **예상 소요**: 1일
> **선행 조건**: Phase 1 완료, news/NewsArticle 데이터 존재
> **산출물**: `chainsight/tasks/relation_tasks.py` (extract_co_mentions)

---

## ⚠️ 점검 결과 반영: ChainNewsEvent 활용

로드맵에 `chainsight_news_event` 테이블이 정의되어 있으나 이전 작업 지시서에서 누락되었다.
뉴스 처리 흐름을 아래와 같이 수정:

```
news/NewsArticle → ChainNewsEvent (중간 저장) → CoMentionEdge
```

ChainNewsEvent에 Chain Sight 관련 뉴스를 저장하면:
- DC-5(뉴스 축적) 추적 가능
- 중복 처리 방지 (event_id 기준)
- 향후 NarrativeTag 추출의 원천

## 구현

```python
@shared_task
def extract_co_mentions(days_back: int = 1):
    """
    Celery Beat: 매일 06:30.
    1) news/NewsArticle에서 최근 N일 뉴스 조회
    2) ChainNewsEvent에 저장 (중복 스킵)
    3) 2개 이상 symbol 포함 뉴스에서 조합 추출
    4) CoMentionEdge upsert (count 누적)
    """
    from news.models import NewsArticle
    from chainsight.models import ChainNewsEvent, CoMentionEdge
    from chainsight.utils import normalize_pair
    from itertools import combinations

    cutoff = timezone.now() - timedelta(days=days_back)
    articles = NewsArticle.objects.filter(published_at__gte=cutoff).exclude(symbols__isnull=True)

    events_created = 0
    for article in articles:
        # ChainNewsEvent 중간 저장
        _, created = ChainNewsEvent.objects.get_or_create(
            event_id=str(article.id),  # ⚠️ 실제 ID 필드에 맞게 조정
            defaults={
                "title": article.title[:200],
                "symbols": article.symbols,
                "event_type": "news",
                "published_at": article.published_at,
            }
        )
        if created:
            events_created += 1

    # CoMentionEdge 추출
    pair_counts = defaultdict(lambda: {"count": 0, "last_date": None})
    events = ChainNewsEvent.objects.filter(published_at__gte=cutoff)
    for event in events:
        symbols = event.symbols or []
        valid = [s for s in symbols if isinstance(s, str) and s.isalpha() and 1 <= len(s) <= 5]
        if len(valid) < 2:
            continue
        for a, b in combinations(set(valid), 2):
            pair = normalize_pair(a, b)
            pair_counts[pair]["count"] += 1
            if not pair_counts[pair]["last_date"] or event.published_at > pair_counts[pair]["last_date"]:
                pair_counts[pair]["last_date"] = event.published_at

    # Upsert
    created, updated = 0, 0
    for (a, b), data in pair_counts.items():
        obj, is_new = CoMentionEdge.objects.get_or_create(
            symbol_a=a, symbol_b=b,
            defaults={"co_mention_count": data["count"], "last_co_mention_date": data["last_date"]})
        if not is_new:
            obj.co_mention_count += data["count"]
            obj.last_co_mention_date = max(obj.last_co_mention_date or data["last_date"], data["last_date"])
            obj.save()
            updated += 1
        else:
            created += 1

    return {"events": events_created, "pairs": len(pair_counts), "created": created, "updated": updated}
```

## 완료 기준

```
□ ChainNewsEvent에 뉴스 이벤트 저장 확인
□ CoMentionEdge 적재 확인
□ 상위 동시출현 쌍 합리성 확인
```

→ **다음**: cs_23

**END OF DOCUMENT**

# CS-2-2: CoMentionEdge 추출

> **작업 번호**: CS-2-2
> **로드맵 버전**: v1.4 (변경 없음)
> **목표**: Marketaux 뉴스에서 동시출현 쌍 추출
> **예상 소요**: 1~2일
> **선행 조건**: CS-2-1 완료
> **산출물**: `chainsight/tasks/relation_tasks.py`

---

## 데이터 흐름

```
news/NewsArticle (symbols JSONB)
    ↓ 전처리
chainsight_news_event (ChainNewsEvent — 중간 저장)
    ↓ 쌍 추출
chainsight_co_mention_edge (CoMentionEdge)
```

⚠️ ChainNewsEvent를 중간 저장소로 활용. NewsArticle에서 직접 CoMentionEdge를 만들지 않음.

## 구현

1. NewsArticle에서 symbols 필드에 2개 이상 ticker가 있는 기사 필터
2. ChainNewsEvent 테이블에 중간 저장 (event_id, title, symbols, event_type, published_at)
3. ChainNewsEvent에서 symbols 내 모든 쌍(combination) 추출
4. CoMentionEdge upsert (symbol_a < symbol_b 사전순, count 증가, last_date 갱신)

## Celery Task

```python
@shared_task
def extract_co_mentions():
    """일간 실행 — 어제 뉴스에서 co-mention 추출"""
    # Celery Beat: crontab(hour=6, minute=30)
```

## 완료 기준

```
□ ChainNewsEvent에 뉴스 이벤트 적재
□ CoMentionEdge에 동시출현 쌍 적재
□ undirected 정규화 확인 (symbol_a < symbol_b)
□ 일간 Celery task 실행 성공
```

→ **다음**: cs_23

**END OF DOCUMENT**

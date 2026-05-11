# CS-5-6: 시드 노드 표시

> **작업 번호**: CS-5-6
> **로드맵 버전**: v1.4 (신규)
> **목표**: Phase A(가격 급변, 거래량 이상) + Phase B(관계 변화) 시드 노드 bounce 애니메이션
> **예상 소요**: 1~2일
> **선행 조건**: CS-5-5 완료
> **산출물**: GraphView 내 시드 노드 강조 로직

---

## 시드 노드 = "지금 탐색 시작하기 좋은 출발점"

### Phase A — 시장 시그널
- 가격 급변 (일간 ±3% 이상)
- 거래량 이상 (20일 평균 대비 2배 이상)
- 52주 신고/저가

### Phase B — 관계 변화
- 새로운 관계 발견 (RelationConfidence 신규)
- 관계 상태 변경 (weak→probable, probable→confirmed)
- 신규 뉴스 co-mention (CoMentionEdge 증가)

## Heat Score (MVP)

```
heat_score = 0.25 × price_signal + 0.25 × volume_signal
           + 0.25 × relation_change_signal + 0.25 × news_activation
```

- MVP: 4 signal 동일 가중치(0.25)
- 각 signal: 0~1 min-max 정규화
- 상위 N개 시드 노드 선정

### 백엔드 계산 방식 (Celery 일간 배치)

heat_score는 **Celery 일간 배치**로 계산 → Neo4j `:Stock` 노드에 `heat_score` 속성 저장.
CS-4-1 API 응답의 node 속성에 자연스럽게 포함.
프론트에서는 `heat_score > threshold`인 노드에 bounce 애니메이션만 적용.

```python
# chainsight/tasks/seed_tasks.py
@shared_task
def calculate_heat_scores():
    """일간 실행 — Celery Beat: crontab(hour=7, minute=0)"""
    stocks = Stock.objects.filter(is_active=True)
    for stock in stocks:
        price_signal = get_price_signal(stock.symbol)      # DailyPrice: 5일 가격 변동률 정규화
        volume_signal = get_volume_signal(stock.symbol)     # DailyPrice: 20일 평균 대비 거래량 비율
        relation_signal = get_relation_change_signal(stock.symbol)  # RelationConfidence: 최근 상태 변경 수
        news_signal = get_news_activation(stock.symbol)     # CoMentionEdge: 최근 7일 co-mention 증가율

        heat = 0.25 * price_signal + 0.25 * volume_signal \
             + 0.25 * relation_signal + 0.25 * news_signal

        repo.run_query(
            "MATCH (s:Stock {ticker: $ticker}) SET s.heat_score = $heat",
            {"ticker": stock.symbol, "heat": round(heat, 4)}
        )
```

⚠️ Celery Beat 등록: cs_25에서 `chainsight-heat-score-daily` 추가 완료.

## 시각적 표현

- bounce 애니메이션 (CSS animation: scale 1.0 → 1.15 → 1.0, 2s infinite)
- 시드 노드 ring glow (heat_score에 비례하는 밝기)
- 툴팁: "📡 거래량 급증 — 탐색 시작점"

## 완료 기준

```
□ 시드 노드 bounce 애니메이션 동작
□ heat_score 기반 상위 N개 선정
□ 시드 노드 탭 → 그래프 중심 이동 + 확장
□ 툴팁 표시
```

→ **Phase 5 완료**. 다음: cs_61 (Phase 6 — Watchlist 백엔드 시작)

**END OF DOCUMENT**

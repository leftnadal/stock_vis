# CS-4-4: Seed Node heat_score 배치

> **완료일**: 2026-04-18
> **브랜치**: `tier1/code-quality-fixes`

## 구현

- `chainsight/tasks/seed_tasks.py`에 `calculate_heat_scores` task 추가
- 4개 signal: price_signal, volume_signal, relation_change_signal, news_activation
- 가중치: 균등 0.25 (MVP)
- Celery Beat: `chainsight-heat-score-daily` (매일 07:00 UTC)

## 실행 결과

- **처리**: 534개 Stock, 에러 0건, 8.4초
- **분포**: avg=0.361, min=0.000, max=0.576
- **범위**: 0~1 정상 ✅

## Top 10 heat_score

| # | 종목 | heat | price | vol | rel | news |
|---|------|------|-------|-----|-----|------|
| 1 | TSLA | 0.576 | 0.97 | 0.00 | 1.00 | 0.33 |
| 2 | HOOD | 0.500 | 1.00 | 0.00 | 1.00 | 0.00 |
| 3 | ORCL | 0.499 | 1.00 | 0.00 | 1.00 | 0.00 |
| 4 | COIN | 0.499 | 1.00 | 0.00 | 1.00 | 0.00 |
| 5 | APP | 0.498 | 0.99 | 0.00 | 1.00 | 0.00 |

## 완료 체크리스트

```
[x] chainsight/tasks/seed_tasks.py 생성
[x] calculate_heat_scores 수동 실행 성공
[x] Neo4j :Stock 534개 heat_score 속성 확인
[x] heat_score 분포 합리성 (avg 0.361)
[x] Celery Beat 등록
```

→ 다음: cs_51 (Phase 5 프론트엔드)

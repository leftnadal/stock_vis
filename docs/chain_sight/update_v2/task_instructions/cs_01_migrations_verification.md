# CS-0-1: Django Migrations 실행 + 검증

> **작업 번호**: CS-0-1
> **로드맵 버전**: v1.4
> **목표**: chainsight/ 테이블 14개 생성 확인
> **예상 소요**: 30분
> **선행 조건**: CS-0-0 완료
> **산출물**: showmigrations 전체 [X] 스크린샷/로그

---

## 실행

```bash
python manage.py showmigrations chainsight
```

## 기대 결과: 14개 테이블 확인

| # | 테이블명 | 구분 |
|---|---------|------|
| 1 | chainsight_sensitivity_profile | Tier A |
| 2 | chainsight_growth_stage | Tier A |
| 3 | chainsight_capital_dna | Tier A |
| 4 | chainsight_insider_signal | Tier A |
| 5 | chainsight_narrative_tag | Tier B |
| 6 | chainsight_event_reaction | Tier B |
| 7 | chainsight_revenue_structure | Tier B |
| 8 | chainsight_chain_profile | 집약 |
| 9 | chainsight_news_event | 뉴스 |
| 10 | chainsight_co_mention_edge | 관계 발견 |
| 11 | chainsight_price_co_movement | 관계 발견 |
| 12 | chainsight_relation_confidence | 관계 발견 |
| 13 | chainsight_saved_path | Path Watchlist ← v1.4 |
| 14 | chainsight_path_action | Path Watchlist ← v1.4 |

```bash
# 테이블 수 확인
python manage.py dbshell <<< "\dt chainsight_*" | grep chainsight | wc -l  # → 14
```

## 완료 기준

```
□ showmigrations 전체 [X]
□ 14개 테이블 존재 확인
□ 각 테이블 빈 상태 (0건) 확인
```

→ **다음**: cs_02 (Neo4j 연결 레이어)

**END OF DOCUMENT**

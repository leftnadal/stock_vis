# CS-0-1: Django Migrations 실행 + 검증

> **완료일**: 2026-04-18
> **브랜치**: `tier1/code-quality-fixes`

## 결과

### showmigrations

```
chainsight
 [X] 0001_initial
 [X] 0002_companyinsidersignal_companynarrativetag_and_more
 [X] 0003_companychainprofile_companyrevenuestructure_and_more
 [X] 0004_companychainprofile_neo4j_synced_and_more
 [X] 0005_add_neo4j_dirty_previous_status
 [X] 0006_add_savedpath_pathaction
```

### 14개 테이블 확인

| # | 테이블명 | 구분 | 존재 |
|---|---------|------|------|
| 1 | chainsight_sensitivity_profile | Tier A | ✅ |
| 2 | chainsight_growth_stage | Tier A | ✅ |
| 3 | chainsight_capital_dna | Tier A | ✅ |
| 4 | chainsight_insider_signal | Tier A | ✅ |
| 5 | chainsight_narrative_tag | Tier B | ✅ |
| 6 | chainsight_event_reaction | Tier B | ✅ |
| 7 | chainsight_revenue_structure | Tier B | ✅ |
| 8 | chainsight_chain_profile | 집약 | ✅ |
| 9 | chainsight_news_event | 뉴스 | ✅ |
| 10 | chainsight_co_mention_edge | 관계 발견 | ✅ |
| 11 | chainsight_price_co_movement | 관계 발견 | ✅ |
| 12 | chainsight_relation_confidence | 관계 발견 | ✅ |
| 13 | chainsight_saved_path | Path Watchlist | ✅ |
| 14 | chainsight_path_action | Path Watchlist | ✅ |

### 빈 상태 확인

- SavedPath: 0 rows ✅
- PathAction: 0 rows ✅

## 완료 체크리스트

```
[x] showmigrations 전체 [X]
[x] 14개 테이블 존재 확인
[x] 각 테이블 빈 상태 (0건) 확인
```

→ **다음**: cs_02 (Neo4j 연결 레이어)

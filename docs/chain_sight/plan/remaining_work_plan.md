# Chain Sight 남은 작업 계획

> **작성일**: 2026-04-04
> **기준**: SEC Pipeline Phase 1~3 완료 후

---

## 완료된 작업

| 작업 | 완료일 | 산출물 |
|------|--------|--------|
| CS-0 인프라 (레거시 정리, Neo4j 연결, 스키마) | 2026-04-02 | Neo4j 드라이버 + 4 제약조건 |
| CS-1 시드 로드 (Stock, Sector, Industry, Peer) | 2026-04-02 | 532 Stock + 17 Sector + 128 Industry + 8,350 PEER_OF |
| CS-2 파이프라인 (GrowthStage, CapitalDNA, CoMention, PriceCoMovement, RelationConfidence) | 2026-04-03 | 480 GrowthStage + 473 CapitalDNA + 2,748 쌍 |
| CS-3 Neo4j 동기화 + GDS (PageRank, Louvain, Betweenness) | 2026-04-03 | M3 마일스톤 달성 |
| CS-4 REST API (Graph, Suggestion, Trace) | 2026-04-03 | 3 엔드포인트 |
| SEC Pipeline Phase 1~3 (17 PR) | 2026-04-04 | 8 모델, 110 관계, 5 BM Snapshot |

## 남은 작업 (우선순위 순)

### 1. CS-2-1b: SensitivityProfile 계산 ⭐ (다음 착수)

- **문서**: `docs/chain_sight/plan/cs_21b_sensitivity_profile.md`
- **원천**: FMP Revenue Geo Segmentation + BalanceSheet + Stock.beta
- **산출물**: CompanySensitivityProfile ~480건
- **예상**: 3~5시간

### 2. CS-2-1c: InsiderSignal 계산

- **문서**: `docs/chain_sight/plan/cs_21c_insider_signal.md`
- **원천**: Finnhub Insider Transactions (무료 60 RPM)
- **산출물**: CompanyInsiderSignal ~480건
- **예상**: 2~3시간

### 3. Celery Beat 일괄 등록

- Chain Sight: calculate_all_profiles (주 1회), relation tasks (일 1회)
- Validation: validation_orchestrator (주 1회)
- SEC Pipeline: sync_dirty_to_neo4j (5분), check_new_filings (월 1회)
- **예상**: 1시간

### 4. DC-2: ETF Holdings

- **방식**: 운용사 CSV 다운로드 (Finnhub 403 → decisions/003)
- **대상**: iShares, SPDR, ARK, Global X 상위 ETF
- **산출물**: Neo4j :Theme 노드 + HAS_THEME 관계 ~390개
- **예상**: 1~2일

### 5. CS-5: Frontend 그래프 시각화 (Phase 5)

- CS-5-1: Graph Visualization (D3/Cytoscape)
- CS-5-2: AI Guide UI
- CS-5-3: Chain Trace UI
- CS-5-4: Stock Detail Integration
- **문서**: `cs_51~54_*.md` (기존)
- **예상**: 3~5일

### 6. Peer System Phase 6~7

- Phase 6: Thematic Presets (Chain Sight DNA 기반)
- Phase 7: LLM 대화형 Peer 조정
- **예상**: 2~3일

---

## 의존 관계

```
CS-2-1b (Sensitivity) ──→ CS-2-1c (Insider) ──→ Celery Beat 등록
                                                      │
                                                DC-2 ETF Holdings
                                                      │
                                                CS-5 Frontend
                                                      │
                                              Peer Phase 6~7
```

## Tier A 완성 후 Neo4j 속성 업데이트

CS-2-1b + CS-2-1c 완료 시 :Stock 노드에 추가되는 속성:
- `sensitivity_vector`: `[rate_sensitivity, forex_sensitivity, commodity_sensitivity]`
- `insider_signal`: smart_money_signal 값
- `regulation_type`: fda/financial/environmental/telecom/none

→ 기존 GDS 알고리즘(PageRank, Louvain) 재실행은 불필요 (노드 속성 추가만, 관계 구조 변경 없음)

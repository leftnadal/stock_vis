# CS-1-3: Peer 관계 로드

> **완료일**: 2026-04-02
> **소요 시간**: ~30분 (API 호출 포함)

## 생성/수정된 파일

- chainsight/services.py (peer 수집/로드 함수)
- chainsight/management/commands/load_peers_to_neo4j.py

## 결과

- Finnhub 성공: 520/1,263
- FMP 사용: Yes (CS-0-0에서 200 확인)
- 고유 pairs: 7,633개
- Neo4j PEER_OF: 2,816개 (Neo4j :Stock 노드 간 매칭분)

## Phase 1 최종 상태 (M1 마일스톤)

| 항목 | 수치 | 로드맵 기대치 | 상태 |
|------|------|-------------|------|
| :Stock | 1,263 | ~500+ | ✅ |
| :Sector | 18 | ~11 | ✅ |
| :Industry | 130 | ~70 | ✅ |
| BELONGS_TO_SECTOR | 1,242 | ~490 | ✅ |
| BELONGS_TO_INDUSTRY | 1,161 | ~485 | ✅ |
| PEER_OF | 2,816 | ~2,500~3,500 | ✅ |
| 전체 노드 | 1,528 | ~580 | ✅ |
| 전체 관계 | 6,217 | ~4,500 | ✅ |

파도타기 2-hop 테스트: AAPL → 20개 종목 도달 ✅

## ★ M1 달성: "그래프에 데이터가 있음"

## 다음 작업

→ Phase 2 (CS-2-1): 파생 데이터 계산 파이프라인
→ 병행: DC-2 (ETF Holdings), DC-3 (수동 시드 Supply Chain)

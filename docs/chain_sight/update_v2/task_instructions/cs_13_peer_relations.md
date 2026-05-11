# CS-1-3: Peer 관계 로드 (Finnhub + FMP)

> **작업 번호**: CS-1-3
> **로드맵 버전**: v1.4 (변경 없음)
> **목표**: PEER_OF 2,500~3,500개 생성
> **예상 소요**: 3~5시간
> **선행 조건**: CS-1-2 완료
> **산출물**: Celery task `fetch_and_load_peers`

---

## 데이터 소스

- Finnhub `/stock/peers` (무료, 확인됨) — 주 소스
- FMP `/stable/stock-peers` — CS-0-0 테스트 결과 200이면 보조 소스로 병합

## 구현

1. S&P 500 각 종목에 대해 Finnhub peers API 호출
2. (FMP 200이면) FMP peers도 호출, 합집합 생성
3. PEER_OF 관계 생성 (undirected — symbol_a < symbol_b 사전순 강제)
4. source 속성 기록 ('finnhub', 'fmp', 'both')

## 완료 기준

```
□ PEER_OF 2,500~3,500개
□ MATCH ()-[r:PEER_OF]->() RETURN count(r)
□ undirected 정규화 확인 (symbol_a < symbol_b)
★ M1 달성: "그래프에 데이터가 있음" — 파도타기 핵심 경험 확인 가능
```

→ **다음**: cs_21 (Phase 2 시작)

**END OF DOCUMENT**

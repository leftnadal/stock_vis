# CS-5-1: 그래프 시각화 컴포넌트

> **작업 번호**: CS-5-1
> **로드맵 버전**: v1.4 (변경 없음)
> **목표**: Spotlight 모드 + lazy expansion
> **예상 소요**: 3~5일
> **선행 조건**: Phase 4 완료
> **산출물**: `components/chainsight/GraphView.tsx`

---

## 핵심 동작

- ForceGraph2D 기반 노드 그래프 렌더링
- 노드 탭 → 중심 이동 + 1-hop 연결 확장 (CS-4-1 API 호출)
- 노드 더블 탭 → 종목 상세 페이지 이동
- 노드 롱프레스 → 컨텍스트 메뉴 (Watch / Alternatives / Deep Dive)
- 핀치 줌 + 빈 영역 드래그
- 엣지 스타일: 관계 타입별 색상/두께 구분
- 엣지 표시 기준: relation_status IN ('confirmed', 'probable')
- SUPPLIES_TO: 방향에 따라 "공급"/"고객" 라벨

## 성능 가드레일

| 항목 | 제한 |
|------|------|
| 초기 렌더링 노드 수 | 최대 50개 |
| 그래프 depth | 최대 2 |
| Neo4j 쿼리 LIMIT | 100 paths |

## 완료 기준

```
□ 노드 탭 → 확장
□ 노드 더블 탭 → 상세 이동
□ 롱프레스 → 컨텍스트 메뉴
□ 엣지 스타일 구분
□ 50노드 이내 렌더링
□ 모바일 터치 타겟 44px+
```

→ **다음**: cs_52

**END OF DOCUMENT**

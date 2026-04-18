# CS-5-1: 그래프 시각화 컴포넌트

> **완료일**: 2026-04-18
> **상태**: 이미 구현됨 — 검증 완료

- `GraphCanvas.tsx`: ForceGraph2D 기반, 노드 탭/중심 이동, 엣지 타입별 스타일
- `MarketGraphCanvas.tsx`: 마켓 뷰 전용 (overview/neighbor 분기)
- 성능 가드레일: 50노드 LIMIT, depth 최대 2
- 시드 노드 색상 구분 (price=빨강, volume=초록, relation=파랑)

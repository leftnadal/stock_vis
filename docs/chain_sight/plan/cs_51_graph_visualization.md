# CS-5-1: 그래프 시각화 컴포넌트

> **작업 번호**: CS-5-1
> **목표**: Spotlight 모드 + lazy expansion 그래프 시각화
> **예상 소요**: 3~5일
> **선행 조건**: CS-4-1 완료
> **산출물**: `components/chainsight/GraphView.tsx` 및 관련 파일

---

## 라이브러리: react-force-graph-2d (MVP)

```bash
cd frontend && npm install react-force-graph-2d
```

원칙 4(단순 구조) 부합. 추후 @visx/network 전환 가능.

## 디렉토리

```
frontend/components/chainsight/
├── GraphView.tsx         ← ForceGraph2D (dynamic import, SSR 불가)
├── GraphControls.tsx     ← depth, reset, 필터
├── NodeDetailPanel.tsx   ← 노드 클릭 시 상세
└── hooks/useGraphData.ts ← API 호출 + state
```

## 핵심 UX

- **Spotlight**: 중심 노드 크게, 1-depth 이웃 주변 배치
- **Lazy expansion**: 노드 클릭 → 새 중심으로 전환 (fetchGraph 재호출)
- **노드 크기**: center > pagerank 비례
- **노드 색상**: 섹터별 (Technology=#3B82F6, Healthcare=#10B981 등)
- **엣지 색상**: confirmed=#22C55E, probable=#3B82F6, 기타=#6B7280
- **Depth 전환**: 버튼으로 1/2/3 전환

## 성능 기준 (원칙 6)

- 1-depth 로드: **3초 이내**
- 모바일 기본 터치 조작 가능

## 완료 기준

```
□ GraphView 렌더링 (노드 + 엣지)
□ Spotlight 모드 (중심 강조)
□ 노드 클릭 lazy expansion
□ 섹터별 색상, confidence 엣지 색상
□ Depth 1/2/3 전환
□ 모바일 터치
```

→ **다음**: cs_52

**END OF DOCUMENT**

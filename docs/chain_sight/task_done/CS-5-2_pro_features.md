# CS-5-2: 프로 기능 (필터 패널) + 버그 수정

> **완료일**: 2026-04-04

## 생성된 파일

| 파일 | 역할 |
|------|------|
| `frontend/components/chainsight/FilterPanel.tsx` | 관계 타입 9종 체크박스 + Depth 전환 + 적용/초기화 |

## 수정된 파일

| 파일 | 변경 |
|------|------|
| `chainsight/api/views.py` | `_sanitize_neo4j()` 추가 — Neo4j DateTime JSON 직렬화 에러 수정 |
| `frontend/components/chainsight/GraphCanvas.tsx` | `nodeVal` prop 추가 (노드 간격 확대), ticker 없는 노드 필터, d3 force 설정 |
| `frontend/components/chainsight/graphStyles.ts` | 중심 노드 r=32, 이웃 r=10~20 |
| `frontend/components/chainsight/GraphMiniView.tsx` | ticker 없는 노드 필터 추가 |
| `frontend/app/chainsight/[symbol]/page.tsx` | FilterPanel 통합 + 필터 state 관리 |

## 버그 수정

| 버그 | 원인 | 수정 |
|------|------|------|
| NVDA graph API 500 에러 | Neo4j DateTime 객체가 JSON 직렬화 불가 | `_sanitize_neo4j()` 재귀 변환 |
| "undefined" 라벨 노드 | Sector/Industry/Theme 노드에 ticker 없음 | `!node.ticker` 필터 추가 |
| 노드 뭉침 | charge strength 부족 | `nodeVal` prop + `d3Force` charge -600 |

## 브라우저 테스트 결과

| 페이지 | 상태 |
|--------|------|
| `/chainsight/AAPL` | ✅ 56 노드, 59 엣지, 621ms |
| `/chainsight/NVDA` | ✅ 22 Stock 노드 퍼짐, 엣지 실선/점선 구분 |
| `/stocks/NVDA?tab=chain-sight` | ✅ 미니 그래프 + 연결 종목 태그 + "전체 탐색" |
| 노드 클릭 → 우측 패널 | ✅ CTA 4개 (가설/Validation/탐색/경로) |
| AI Guide 카테고리 | ✅ 경쟁사/동시출현/같은 섹터 |

## 다음 작업

→ CS-5 task_done 최종 + 모바일 카드 리스트 (추후)

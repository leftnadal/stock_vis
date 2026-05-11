# PR-6: 트레일 + 관계 카드 패널

> **완료일**: 2026-04-10
> **브랜치**: `data_structure_remodeling_V1`

## 목표

③ 탐색 트레일 + ④ 관계 카드 패널 (pre-focus/focused 분기) 구현.

## 생성된 파일

| 파일 | 역할 |
|------|------|
| `frontend/components/chainsight/ExplorationTrail.tsx` | ③ 탐색 트레일 (가로 스크롤 + undo) |
| `frontend/components/chainsight/RelationCardPanel.tsx` | ④ 관계 카드 패널 (SeedCardList + RelationCardGroups) |

## ③ 탐색 트레일

- **위치**: 그래프 바로 아래, 높이 60px
- **노드 크기**: 과거 r=12, 현재 r=18
- **자동 스크롤**: 새 노드 추가 시 오른쪽 끝 (smooth)
- **엣지 라벨**: `PEER_OF` → "peer", `SUPPLIES_TO` → "supply" 등
- **인터랙션**: 노드 클릭 → `undoToTrailNode(depth)` (②③④ + 히스토리 복원)

## ④ 관계 카드 패널

### 3가지 상태

| 상태 | 렌더 |
|------|------|
| !selectedSector && !centerSymbol | Empty state ("섹터를 선택하면...") |
| selectedSector && !centerSymbol | SeedCardList (pre-focus) |
| centerSymbol | RelationCardGroups (focused) |

### Pre-focus: 시드 카드

- 데이터: `seedData.seeds.filter(s => s.sector === selectedSector)`
- 카드: symbol + name + seed_type badge + seed_reasons + daily_return + volume_ratio
- CTA: "여기서 탐색" → `selectNode(symbol)`

### Focused: 관계 카드 그룹

| 그룹 | display_type |
|------|-------------|
| Supply Chain | SUPPLIES_TO, CUSTOMER_OF (badge 구분) |
| Competitors | COMPETES_WITH |
| Peers | PEER_OF |
| Co-mentioned | CO_MENTIONED, PRICE_CORRELATED |

### 관계 카드 1장 구성

| 영역 | 내용 |
|------|------|
| 상단 | symbol + name |
| 관계 | display_type badge + 관계 설명 (1차 템플릿) |
| 시그널 | why now (seed_reasons 기반 or daily_return/volume_ratio fallback) |
| 메타 | confidence (truth_score ?? market_score) |
| CTA | 여기서 탐색 / 가설 생성 / Deep dive |

### CTA 동작

| CTA | 동작 |
|-----|------|
| 여기서 탐색 | `selectNode(symbol, displayType)` → ②③④ 갱신 |
| 가설 생성 | `/thesis/new?symbol={symbol}&from=chainsight` |
| Deep dive | `/chainsight/{symbol}` |

### 1차 템플릿 규칙

```typescript
SUPPLIES_TO: "공급망 상류/하류 연결"
CUSTOMER_OF: "공급망 상류/하류 연결"
COMPETES_WITH: "직접 경쟁 관계"
PEER_OF: "동종 비교 대상"
CO_MENTIONED: "최근 시장/뉴스에서 동시 해석"
PRICE_CORRELATED: "가격 움직임 유사"
```

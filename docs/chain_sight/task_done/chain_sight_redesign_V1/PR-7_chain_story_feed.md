# PR-7: 체인 스토리 피드

> **완료일**: 2026-04-10
> **브랜치**: `data_structure_remodeling_V1`

## 목표

⑤ 체인 스토리 피드 구현. 마켓 뷰 하단의 글로벌 chain flow + discovery 영역.

## 생성된 파일

| 파일 | 역할 |
|------|------|
| `frontend/components/chainsight/ChainStoryFeed.tsx` | ⑤ 체인 스토리 피드 + ChainStoryCard |

## 체인 스토리 카드 구성

| 영역 | 내용 |
|------|------|
| 헤더 | title + category badge + strength badge |
| Mini path | 종목 심볼 → 화살표 → 종목 심볼 (가로 나열) |
| 하단 | trigger_summary + total_confidence 수치 |

## strength 색상

| strength | 색상 |
|----------|------|
| strong (≥70) | 초록 |
| moderate (40~69) | 주황 |
| weak (<40) | 회색 |

## category 라벨

| category | 라벨 |
|----------|------|
| supply_chain | 공급망 |
| competition | 경쟁 |
| co_mention | 동시출현 |
| peer_network | 동종 네트워크 |

## 무한 스크롤

- TanStack Query `useInfiniteQuery` 사용
- IntersectionObserver로 sentinel 요소 감지
- `has_next` 기반 `fetchNextPage`

## 클릭 동작

체인 스토리 카드 클릭 → **새 exploration session 시작**:

```typescript
selectSector(chain.root_sector);           // ① 섹터 바 자동 선택
startChainExploration(sector, firstSymbol); // trail 리셋 + 새 시작
setHighlightedChain(chain.id);             // 그래프 highlight
```

## ④와의 관계

- ④ 관계 카드 = **로컬** (현재 center 기준)
- ⑤ 체인 스토리 = **글로벌** (시장 전체)
- 독립적 동작, 서로 영향 없음

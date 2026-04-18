# CS-5-6: 시드 노드 표시

> **완료일**: 2026-04-18
> **상태**: 이미 구현됨 — 검증 완료

## 구현 현황

- heat_score 배치: CS-4-4에서 구현 (534개 Stock, avg=0.361)
- 시드 선정: `seed_selection.py` (price/volume/sector_outlier/relation/comention 5개 소스)
- 시드 노드 시각: 타입별 색상 (price=빨강, volume=초록, relation=파랑, comention=보라)
- 시드 카드: `RelationCardPanel.tsx` pre-focus 모드
- bounce 애니메이션: 미구현 (CSS 레벨, 향후 추가 가능)

## heat_score Top 5

| 종목 | heat | price | vol | rel | news |
|------|------|-------|-----|-----|------|
| TSLA | 0.576 | 0.97 | 0.00 | 1.00 | 0.33 |
| HOOD | 0.500 | 1.00 | 0.00 | 1.00 | 0.00 |
| ORCL | 0.499 | 1.00 | 0.00 | 1.00 | 0.00 |

→ Phase 5 완료. 다음: cs_61 (Phase 6 Watchlist 백엔드)

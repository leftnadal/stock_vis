# CS-7-3: Full Path View + 액션 UX

> **작업 번호**: CS-7-3
> **로드맵 버전**: v1.4 (신규)
> **목표**: full_path 전체 표시 + 각 노드별 신호 + Recheck headline + Expand + Alternatives 진입
> **예상 소요**: 2~3일
> **선행 조건**: CS-7-2 완료 + CS-6-5~7 API 작동
> **산출물**: Watchlist 카드 펼침 뷰

---

## 화면 구조

```
┌────────────────────────────────────────────────────────┐
│ ← Path Watchlist                                       │
│                                                        │
│ NVDA → TSM → ASML → AMAT → LRCX → KLAC → MU → ...    │
│ 🏷️ 공급망 중심 · 반도체 장비                              │
│ ● watching                                             │
│                                                        │
│ ── Recheck 결과 ──────────────────────────────────────  │
│ 📡 장비 체인 관계 유지 중, AMAT 거래량 급증                │
│ ▲ AMAT: 거래량 2.3배 (strengthened)                     │
│ 추천: Expand — 모든 관계 유지, 확장 탐색 추천              │
│                                                        │
│ ── 경로 노드 ──────────────────────────────────────────  │
│ [NVDA] ──SUPPLIES_TO──▶ [TSM] ──SUPPLIES_TO──▶ [ASML]  │
│         ──PEER_OF──▶ [AMAT] ──PEER_OF──▶ [LRCX] ...   │
│                                                        │
│ 각 노드 탭 → "이 노드 대신? (Alternatives)" 진입         │
│                                                        │
│ ── Expand 후보 ────────────────────────────────────────  │
│ MU (Micron) · SUPPLIES_TO · 78점                       │
│ KLAC (KLA) · PEER_OF · 65점                            │
│                                                        │
│ [Recheck]  [Expand]  [Archive]  [Resolve]              │
└────────────────────────────────────────────────────────┘
```

## 핵심 동작

1. **Recheck headline 표시**: CS-4-8 API 응답의 headline, strengthened/weakened 시각화
2. **경로 노드 시각화**: full_path를 가로 스크롤 노드 체인으로 표시, 각 edge에 relation_type 라벨
3. **노드 탭 → Alternatives**: 특정 노드 탭 시 "이 노드 대신?" 옵션 → CS-4-10 API 호출
4. **Expand 후보**: CS-4-9 API 응답 표시 (마지막 노드 기준)
5. **액션 버튼**: Recheck / Expand / Archive / Resolve

## 이벤트 로깅

```
path_opened, recheck_clicked, expand_clicked,
alternatives_clicked (+ target_ticker), archive_clicked, resolve_clicked
```

## 완료 기준

```
□ full_path 전체 노드 체인 표시
□ Recheck headline + strengthened/weakened 표시
□ 노드 탭 → Alternatives API 호출 + 결과 표시
□ Expand 후보 표시
□ 액션 버튼 4개 동작
□ 이벤트 로깅 동작
□ 모바일 가로 스크롤
★ M5 달성: "사용자 경험 가능" — Chain Sight MVP 릴리즈
```

## MVP 이후

- DC-5: Marketaux 뉴스 자연 축적
- DC-6: 수익화 이후 Finnhub Premium
- 서비스 연계: Thesis Control, Portfolio 등 각 MVP 이후
- v1.3: Strengthening/Weakening/Broken 자동 상태 전환, 개인화 로직 반영, path-level Compare

**END OF DOCUMENT**

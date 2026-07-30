# discovery 재측정 (Q20-DISCOVERY-REMEASURE, 2026-07-30, read-only)

⑳-3 S2-C Part P. 코드 무변경·SELECT만. 직전 기준 = centrality_s19(2026-07-16).
DB = 공유 stock_vis(읽기 전용, 무변경).

## 1. 실측치 (07-30 기준)

| 지표 | 값 | 비고 |
|------|----|------|
| RelationConfidence 총 | **13,699** | S19(07-16)과 **동일 — 무증가** |
| RC 신규(first_observed_at ≥ 07-16) | **2건** | 그중 has_news_source=True = **0** |
| RC 마지막 first_observed_at | **2026-07-16 07:54** | 이후 discovery 실질 정지 |
| CoMentionEdge 총 | 21,092 | discovery **입력**(다종목 뉴스 쌍) |
| CoMentionEdge 신규(created_at ≥ 07-16) | **4,902** | 입력은 활발 유입 |
| CoMentionEdge 마지막 created_at | 2026-07-29 14:01 | 어제까지 유입 |
| 마지막 last_co_mention_date | 2026-07-28 | 뉴스 동시출현 최신 |
| 최근 30일 co-mention edge | 14,632 | 입력 파이프 정상 |

## 2. 판정 — 신규 discovery 여전히 ≈ 0 (분류 b 재확인)

- **입력(CoMentionEdge)은 살아있다**: broad 재개(07-08) 효과로 07-16 이후 4,902
  신규 edge, 07-29까지 유입. 입력 단절(04-25~07-08) 완전 해소.
- **출력(RC discovery)은 정지**: 07-16 이후 신규 RC 단 2건, 그마저 뉴스 무관
  (co-mention 유래 신규 RC = **0**). 마지막 discovery가 정확히 S19 측정일(07-16).
- 즉 **입력 활발 · 출력 0** → 정체 원인 = **입력 부족 아닌 유니버스 포화**
  (S&P500 내 신규 쌍 희소, 신규 edge 4,902는 기존 쌍 재관찰/유니버스 밖 종목).
  D-DISCOVERY-WATCH(07-16)의 "관찰 대기" 가설이 입력 vs 포화를 미확정으로 남겼는데,
  **재측정으로 포화 쪽 확정**.

## 3. 함의

- Q20-DISCOVERY-REMEASURE 판정: "여전히 0이면 유니버스 확장 결정 사이클 개시" 조건 충족.
- 단 **전제 = 지시서⑦(match_score 정규화) 선행**(D-DISCOVERY-WATCH ③ — ⑦ 없이 확장 시
  저품질 엣지 양산). ⑦ 미완이면 확장 착수 불가 → 확장 결정 사이클은 ⑦ 뒤로.
- 이번 세션(S2-C)은 read-only 측정까지. 확장 착수·⑦ 진행은 별도 결정.

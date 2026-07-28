# Slice C — STEP 0 측정 결과 (2026-07-13)

> 브랜치 `monorepo/sess-C-analog-labels` (base HEAD `3d5341e`, Slice B 포함). worktree `../sess-C-analog-labels`.
> 공유 prod DB 측정(read-only, 쓰기 0). FMP economic-calendar 1회 호출(402 확인용).

## G0 게이트 — ✅ PASS
- SPY `MarketIndexPrice(SPY)` **765행**, 2023-07-14 ~ 2026-07-11 연속.
- 완전벡터 모집단(`RegimeSnapshot summary='[BACKFILL_V2]' coverage>=1.0`) **683행**, 2023-08-07 ~ 2026-04-24.
- as-of 과거일 populated 카드 실검증(프로브 = detail 로직 동형, 자기자신 제외):
  - `2024-12-12`: nearest **0.1642**, 이웃 **2**(2024-12-09 d0.16 · 2025-02-20 d0.59), 팬 지평별 populated(median/lo/hi/N/n_eff).
  - `2024-05-29`: 이웃 5. `2025-07-03`: 이웃 6. → populated 팬 실데이터 확인.
- **결론: 라벨 얹기 진입 조건 충족.**

## L2 카테고리 소스 — 지시서 두 후보 모두 과거 불가 → 결정론 대체 확정
| 후보 | 상태 | 근거 |
|------|------|------|
| FMP economic-calendar (과거) | ❌ **402 Premium** | Starter 플랜에서 historical `to` 파라미터 = 유료벽. 2024-12 범위 조회 402. |
| NewsArticle 분류 (과거) | ❌ 데이터 없음 | 저장 범위 2025-12-08~ (아래) — 모집단 대부분 이전. |
| **RegimeSnapshot 벡터+regime (저장됨)** | ✅ **채택** | 683 완전 커버리지, 외부 의존 0, 결정론. regime 분포 TRANSITION 449·LATE_BULL 228·CRISIS 6. 벡터 = vix/move/nfci*/hy_oas/t10y2y/drawdown/return_1d/vol_20d. **카드 취지(국면 유사)와 정합** — "그날이 어떤 국면이었나"를 벡터 z축 + regime 라벨로 결정론 태깅. |

→ 지시서 §2.2 "결정론·저비용 우선"에 정합. L2 어휘 = regime 라벨 + 지배 z축(예: 고변동/신용경색/곡선역전 전환).

## L3 그라운딩 — ⚠️ 전제 어긋남 (지시서 §2.1 "3년 가용" ✗)
- `NewsArticle` 실측: **113,399건, 2025-12-08 ~ 2026-07-12 (약 7개월)**.
- 모집단 이웃일 샘플(2024-12-09/2024-05-29/2023-10-01/2025-07-03) **전부 0건**.
- 대체 뉴스 아카이브 없음. FMP 뉴스 provider = 최근 위주(과거 임의일 조회 불가에 가까움).
- → **L3 헤드라인 그라운딩은 모집단의 ~극소수(2025-12+)만 가능**. 나머지는 §2.2 규정대로 `why=null`.

## 기타
- **shared LLM 래퍼**: `packages/shared/llm/complete()` (provider=gemini 기본, `cost_track`·`response_format`·escape 정책). L3 생성 = 이 경유.
- **뉴스 seam**: `apps/market_pulse/services/news_aggregator.py`(기존, 경계 위반 아님 — shared 가드는 `packages/shared`→`apps` 역방향만 금지).
- **목업**: `analog_card_mockup.html`·`label_l2l3_mockup.html` repo에 **없음** → 지시서 §부록 렌더 스펙 사용.
- **저장 위치**: 라벨은 **날짜 종속**(이웃=과거일, 어느 카드든 같은 날짜면 동일 라벨) → 날짜별 저장(신규 필드/모델, migration 판별 예정).
- Slice B 계약: `neighbors[].cat_slot: null`·`neighbors[].why: null` (cards.py:434-435), FE 슬롯 대기.

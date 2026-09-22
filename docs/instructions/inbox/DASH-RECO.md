---
track: DASH-RECO
status: done @ecdf1e73 (2026-09-17 실행 완료 · 랜딩 승인 대기 · 보고 outbox/DASH-RECO_보고.md)
dispatched: 2026-09-17 (Cowork 디렉터 · dashboard 트랙 슬라이스 3 / 5)
decision: SCAN-UX-2 사이클 2 ② R3 · ④b P3 · 사이클 3 ⑦-4 · E2 D-SCAN-QUAD-EMPTY-HIDE(자동결정 마진 4.45)
base: S0 실측. 디렉터 최종 관측 origin/main = 98055d73 (2026-09-17 18:09:29 KST) — 5분 전 e2e4aa9a였다. **반드시 재측정한 값을 쓴다.**
---

# DASH-RECO — 추천 카드 재정렬·관점 줄·추천 드로어 신설 + 드로어 tiebreak 수리

**세션**: dashboard 실행 세션. 전용 worktree(`scripts/wt-open.sh`). `pwd`가 본체(`~/Desktop/stock_vis`)면 **HALT**.

**소유 구획**: `frontend/app/page.tsx` · `frontend/components/eod/**` · `frontend/types/eod.ts` · `frontend/__tests__/eod/**`.
구획 밖 파일이 diff에 **한 개라도** 나오면 슬라이스 전체를 HALT 후 상신(쪼개지 않는다). `components/charts/**`·`hooks/useSectorQuadrant*` **접촉 금지**.

**랜딩 절차 주의(디렉터 실측 2026-09-17)**: `scripts/ops/land.sh`와 `docs/instructions/approvals/`는 **아직 origin/main에 없다**(OPS-GATE-1 브랜치 `monorepo/sess-ops-gate1` 진행 중). 이 슬라이스는 **현행 절차**로 착지하고 push 전 상신한다. 착지 시점에 `land.sh`가 origin/main에 있으면 **그 절차를 따른다**.

---

## S0 — 실측 (보고에 전부 기재)

1. `pwd` + `git worktree list`. 본체면 HALT.
2. `git fetch origin` → `git rev-parse origin/main` = **base**. base에 detach 체크아웃.
3. `scripts/health_check.py`를 **대상 트리에서** 실행 → 기준선 기록. 판정은 #118(절대값 아님, **신규 델타 0**).
4. `npx vitest run __tests__/eod` 기준선 통과 수.
5. **추천 payload 실측** (`/static/signals/dashboard.json` 실물 — 심볼릭 링크 대상 런타임 트리):
   - 추천 카드 건수 / `symbol`이 `stocks_by_score`에 조인되는 건수 → **조인율 %**
   - `perspectives.fundamental` 비-null 건수 / `perspectives.technical` 비-null 건수
   - 카드에 `dollar_volume`·`market_cap`이 직접 있는가(없으면 조인 경유인가)
   - `sector_quadrant`의 `breadth_curr` 비-null 섹터 수 / 전체 섹터 수
6. `SignalDetailSheet.tsx` 전수 — "껍데기"(오버레이·우측 슬라이드·헤더·ESC·body scroll lock·하단 축 커버리지 줄)와 "내용"의 경계가 각각 몇 번째 줄인지. **추출 범위를 여기서 확정하고 보고에 줄 번호로 적는다.**
7. 슬라이스 2에서 착지한 `SectorChipLine`이 breadth 결측 상태에서 실제로 조용히 생략되는가(육안 또는 테스트).

### S0 게이트 — 아래에 걸리면 **HALT 후 상신**
- 조인율 **80% 미만** → S2의 체급·섹터 표시는 표시 결정이 아니라 데이터 결정이 된다. 멈추고 보고.
- `SignalDetailSheet`의 껍데기/내용 경계가 S6에서 깔끔히 갈라지지 않는다(상태가 얽혀 있다) → 멈추고 보고. 억지 추출 금지.

> `perspectives.fundamental`이 0건이어도 **HALT 아님** — `technical` 폴백 + 드로어 2관점으로 간다(렌더링 정칙 ⑴, 설계 변경 없음).

---

## S1 — 공용 셸 추출 (선행)

`components/eod/DetailSheetShell.tsx` 신설. `SignalDetailSheet`의 껍데기를 옮겨 두 시트가 공유한다.

- ⚠ **하단 축 커버리지 문구는 셸의 prop**으로 뺀다. 스캐너는 "미커버: 가치평가·퀄리티·관계", 추천은 펀더멘털을 실제로 보여준다 — 하드코딩하면 둘 중 하나는 **반드시 거짓말이 된다**.
- **행위보존**: 이 단계에서 `SignalDetailSheet`의 동작은 한 줄도 바뀌지 않는다. `:220` 래퍼 `key` 버그도 **그대로 둔다**(슬라이스 4 소관). 지금 고치면 슬라이스 4의 "remount 제거 전/후" 측정이 불가능해진다.
- 셸 추출로 `SignalDetailSheet`의 줄 번호가 이동한다 → **보고에 이동 후 래퍼 `key` 줄 번호를 적는다**(슬라이스 4 앵커).

## S2 — R3 정렬·표시 (`RecommendationCarousel.tsx` · `RecommendationCard.tsx`)

- **정렬**: 축 수 내림(`getAxisCount`) → 동률 `dollar_volume` 내림 → 동률 `symbol` 오름(안정 정렬).
- **표시**: `#N` 제거 · 강도 spine → **6칸 축 pips**(6개 카테고리) · `신뢰 높음` 라벨 제거 · 헤더에 `N축` 배지를 **1축부터 항상** 표시(`CONFLUENCE_MIN_AXES` 임계는 배지 조건에서 승격, **상수 자체는 스캐너용으로 유지**).
- **0축**: 축 배지·pips **조용히 생략**(정칙 ⑴). 거래대금 순으로 뒤에. "약함"이 아니라 "카드에 없음".
- ⚠ **합류 지도 도착 전까지 캐러셀만 스켈레톤.** 순서가 `useConfluenceMap`에 의존하므로 비차단으로 두면 도착 시 카드가 재정렬되며 튄다. 화면 나머지는 즉시 렌더.
- 제거 근거(재확인용): `composite_score`는 301건 중 258건이 `|1.0|`로 포화 — `#N`·spine·신뢰 배지·동률 폴백 **네 개가 같은 값 하나에서 동시에 죽는다**.

## S3 — P3 관점 한 줄 (`RecommendationCard.tsx`)

`perspectives.fundamental ?? perspectives.technical` 한 줄. 둘 다 없으면 **줄 생략**(정칙 ⑴, "정보 없음" 표기 금지).
기존 `thesis`(2줄 클램프)와 자리 경쟁하지 않게 배치 — 뉴스 문장이 잘리던 건은 ④a N2 전용 슬롯이 이미 처리했다. 카드 폭 `w-64` 유지.

## S4 — 추천 드로어 신설 (`components/eod/RecommendationDetailSheet.tsx`)

- `DetailSheetShell` 소비. 본문 3섹션: **한 줄 요약 · 세 관점(기술/펀더/뉴스) · 체급·기술**.
- 체급·기술 값이 payload에 없으면 `cards/{id}.json` 조인, 그것도 없으면 **그 섹션만 보류**(섹션 제목째 생략).
- **진입**: 카드 **본문 클릭 = 드로어**(주 동선 — 스캐너 카드와 같은 규칙). `체인사이트 →`는 명시 클릭만(부 동선). 링크가 본문 클릭을 삼키지 않도록 이벤트 전파 처리.

## S5 — ⑦-4 + 낡은 주석 (`scannerFilters.ts`)

- **⑦-4**: `:93` 합류순 동률 폴백을 `composite_score` → `dollar_volume` 내림으로. S2의 R3 tiebreak와 **같은 규칙**이 되게 한다. (디렉터 실측 2026-09-17: origin/main에서 `:93`이 `return b.composite_score - a.composite_score;` 맞음.)
- **주석 정리**: `:39` "오늘 데이터는 전건 profile 폴백 → 실뉴스 0 → 뉴스 칩 자연 생략"은 **#128 시절 사실**이다. 09-03 sync·bake 이후 `news_context` 370노드 전량 실뉴스(symbol_today 83.2% · symbol_7d 16.8% · profile 0%) → **`뉴스만` 필터가 실제로 동작한다.** 주석을 놔두면 다음 사람이 "이 필터는 죽었다"고 오독한다.
  *(원래 슬라이스 4 항목이나, 같은 파일을 두 번 여는 비용을 피해 여기로 옮겼다 — 디렉터 판단, 보고에 명기.)*

## S6 — E2 빈 사분면 숨김 (`app/page.tsx`) — 독립 스텝

`sector_quadrant`의 **모든 섹터에서 `breadth_curr`가 null이면 사분면 블록을 렌더하지 않는다**(칸째 생략, 자리표시자 없음).
- 근거: 현재 11/11 섹터 결측 → [시장] 탭 최상단에 **약 407px 빈 상자**가 그려진다. 점 0개 차트는 "데이터 없음"이 아니라 "아무 일도 없다"로 읽힌다(정칙 ⑴ 위반).
- 이건 **가림막이지 수리가 아니다**. 원인은 `DSS-BREADTH-MISSING`(위임 중)이고, 그게 풀리면 이 조건은 자연히 거짓이 되어 차트가 돌아온다 — **되돌리는 작업이 필요 없다.**
- 실패해도 S1~S5에 영향 없게 독립 커밋.

---

## 금지

- 구획 밖 파일 변경(특히 `components/charts/**`·`hooks/useSectorQuadrant*`).
- 메타 4종(TASKQUEUE·PROGRESS·DECISIONS·common-bugs) 변경 — mgmt 전용. 발견 사항은 **채번 후보**로 보고만.
- `SignalDetailSheet`의 `:220` remount 버그 수리(슬라이스 4) · `StockRow` memo(슬라이스 4) · 필터 임계 상수 변경(어느 슬라이스도 아님).
- 살아 있는 서빙 트리에서 `npm ci` (D-DEPLOY-NO-NPM-CI-ON-LIVE). 배포는 `npm run build`.
- force push · 브랜치/worktree 삭제 · 원격 브랜치 삭제 · prod DB 쓰기 · launchd 조작.

## DoD

1. `git diff --name-only <base>..HEAD` **전수**가 소유 구획 안. 구획 밖 1건 = HALT.
2. `npx vitest run __tests__/eod` 기준선 대비 **실패 증가 0**. 신규 테스트: R3 정렬 순서(축수→대금→심볼) · 0축 생략 · P3 폴백·생략 · E2 전건 null 시 미렌더.
3. `tsc --noEmit` 0.
4. health **신규 델타 0**(#118 — 기준선은 rebase 목표 트리에서 측정).
5. 육안: 추천 카드에서 `#N`·신뢰 라벨이 사라지고 축 pips가 보인다 · 카드 본문 클릭 시 우측 드로어가 열린다 · [시장] 탭 최상단 빈 사분면 상자가 사라졌다.

## 보고 (outbox `DASH-RECO_보고.md`, 25줄 이내)

첫 줄 = **판정 1줄**. 이어서: S0 실측값 전부(특히 **조인율 %**·`perspectives` 건수·`breadth_curr` 결측 수) · 셸 추출 경계 줄 번호와 **이동 후 `SignalDetailSheet` 래퍼 key 줄 번호** · 파일 목록 · 게이트 4종 수치 · 채번 후보 · 착지 해시(push 전 상신).

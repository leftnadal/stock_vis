# Slice 18 STEP 0 — ground truth 실측 + HALT 보고 (디렉터 재설계 입력)

> 세션: 실행 세션 진입 → **STEP 0에서 HALT(§7 1순위+2순위) → 사용자 결정 "정지·디렉터 재설계"**.
> 코드 산출 0 (모델·CRUD·테스트·DECISIONS 미기록). 본 문서 + 지시서 배치만 남김.
> 측정일: 2026-07-13 · worktree `monorepo/sess-slice18-container` · base origin/main `a340816`.

---

## STEP 0 (a) git 좌표
- base HEAD: `a340816` (직전 기록 `2d0c605`에서 main 더 전진 — 재측정으로 확정, 그 위에서 분기).
- 작업 브랜치: `monorepo/sess-slice18-container` (신규 worktree).

## STEP 0 (b) baseline pytest (회귀 기준선)
- `pytest apps/portfolio tests/architecture -q` = **574 passed / 0 failed**.
- 직전 기록 567 대비 +7(신규 유입, 전부 green). **red 0 → 깨끗한 출발선**(게이트 통과).

## STEP 0 (c) 기존 영속 모델 전수 (apps/portfolio, 13개)

명령: `grep -nE "^class \w+\(.*models.Model" apps/portfolio/models.py` (단일 파일, 13 모델).

| # | 모델 | 의미 | user 스코프 |
|---|---|---|---|
| 1 | `Wallet` | 사용자 자산 지갑(사용자당 1개) | **user FK 직접** |
| 2 | `WalletHolding` | Wallet 내 실보유 종목 | wallet.user 간접 |
| 3 | `WalletSnapshot` | 시점별 Wallet 상태 스냅샷 | wallet.user 간접 |
| 4 | `Portfolio` | 분석 대상 포트폴리오(Wallet 참조) | wallet.user 간접 |
| 5 | `AnalysisRun` | 분석 실행 레코드 | Portfolio 경유 |
| 6 | `MetricResult` | 종목별 지표 결과 | AnalysisRun 경유 |
| 7 | `DiagnosticCard` | 진단 카드 | AnalysisRun 경유 |
| 8 | `LLMComment` | LLM 코멘트 | AnalysisRun 경유 |
| 9 | `StoredAnalysis` | 저장된 분석(1:1 AnalysisRun) | 경유 |
| 10 | `PercentileCache` | 지표 백분위 캐시 | 없음(전역) |
| 11 | `ChatSession` | 코치 대화 세션 | **user FK 직접** |
| 12 | `Message` | 대화 메시지 | ChatSession 경유 |
| 13 | `Decision` | 사용자 결정 로그 | **user FK 직접** |

## STEP 0 (c★) 신규 4종 재사용/신규 판정 — HALT 1순위

| 신규 요구 | 기존 중복 | 판정 | 근거 |
|---|---|---|---|
| **WalletHolding** (user·종목·수량·평단) | `apps/portfolio.WalletHolding` (models.py:78, **동명·상위집합**) | 🔴 **재사용** | 기존이 `stock`(FK→stocks.Stock)·`shares`·`avg_cost`·`first_bought_at`·`investment_thesis`·`buy_snapshot` 보유 → 신규 요구 전부 포함+풍부. **같은 앱 동명 클래스 = Django 정의 충돌(신규 불가)**. REST 미노출(정의만) |
| **WatchlistItem** (user·종목·note) | `shared/users.WatchlistItem` (users/models.py:215, **동명·상위집합**) | 🔴 **재사용** | 기존이 `stock`(to_field=symbol)·`target_entry_price`·`notes`·`added_at`·`position_order`+`distance_from_entry` 프로퍼티 보유(target_entry_price는 19a 갭매칭에 직접 유용). REST CRUD 완비(users/urls.py: list/create/detail/add-stock/bulk-add) |
| **CashBalance** (user·통화·금액) | 없음 | 🟢 신규 정당 | 유사 모델 0. (단 기존 `Wallet`에 cash 필드 추가 vs 별도 테이블은 재설계 판단) |
| **UserGoal** (목표수익·기간·리스크) | 없음 | 🟢 신규 정당 | 유사 모델 0 (monitor `ResolvedTarget`은 dataclass, 무관) |

## STEP 0 (c★★) 교차앱 소비자 점검 — D1 전제 파기 (HALT 2순위)

D1 전제 = "watchlist 등은 지금 portfolio만 소비" → **실측 결과 거짓**:

| 소비 앱 | 지점 | 소비 대상 |
|---|---|---|
| **dashboard** | `apps/dashboard/services/strip_service.py:84,86,94` — docstring `"T1 보유(WalletHolding)·T3 관심(WatchlistItem)"`, `WatchlistItem.objects.filter(watchlist__user=user)` | shared/users.WatchlistItem 직접 |
| **chain_sight** | `apps/chain_sight/api/urls.py` — `WatchlistViewSet` router 등록 | watchlist |
| portfolio | `apps/portfolio/schemas/analysis_context.py` | watchlist |

→ watchlist는 **이미 다중 앱 소비 = 범용 자산**이라 shared 소속이 정당. **D1(portfolio 소속)의 타이브레이커("교차앱 소비자 부재")가 깨졌다.** D1 재결정 필요.

## STEP 0 (d) shared 자산 실위치
- `AUTH_USER_MODEL = 'users.User'` (config/settings.py:321). `shared/users/models.py`의 `User(AbstractUser)`.
- portfolio → shared import: `packages.shared.llm`(complete/count_tokens) 2건. 종목 마스터 = `stocks.Stock`(FK 대상).

## STEP 0 (e) 하네스
- baseline 원장: cost_ledger `docs/portfolio/coach/cost_ledger.jsonl` 31행 $0.158026(불변, LLM 미사용 슬라이스).
- 충돌 항목: TASKQUEUE `PF-LEGACY-FE`(app/portfolio·users.Portfolio 귀속 경계 미결)가 본 이슈와 인접 — 재설계 시 함께 고려.

---

## HALT 결론 (§7)

- **1순위(의미 중복)**: WalletHolding·WatchlistItem 2종 동명·상위집합 → 재사용.
- **2순위(교차앱 소비→D1 전제 파기)**: WatchlistItem을 dashboard·chain_sight가 이미 소비 → D1 재결정.
- **사용자 결정**: 정지·디렉터 재설계. 이 세션 코드 0 종료.

## 디렉터 재설계에 넘기는 입력 (권고 아님, 사실 기반 선택지)

1. **D1 재결정**: watchlist는 이미 shared 범용 자산(교차앱 소비) → apps/portfolio 신규 생성은 진실 소스 3분할. WalletHolding도 apps/portfolio에 동명 존재.
   - 재사용 시 Slice 18 신규 = **UserGoal·CashBalance 2종**으로 축소 가능.
2. **D2 영향**: 기존 WalletHolding은 `wallet.user` 간접, shared WatchlistItem은 `watchlist.user` 간접 → `UserScopedModel`(직접 user FK) 추상 베이스와 스코핑 방식이 상충. 재사용 2종엔 어댑터, 신규 2종엔 베이스 적용 — 이원화.
3. **D3 영향**: 격리 테스트 대상이 "신규 스코프 모델"이면 재사용 2종(간접 스코프)은 커버 방식이 달라짐.
4. **필드 확정**: 신규 CashBalance/UserGoal 필드는 19a 비교 연산(목표 vs 현재=WalletHolding+CashBalance, 후보=WatchlistItem) 최소로.

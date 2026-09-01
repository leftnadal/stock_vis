# TASKQUEUE.md — 에이전트 간 오케스트레이션 큐

> 에이전트는 자신에게 할당된 태스크 중 `depends_on`이 모두 `done`인 것만 착수한다.
> 상태: `todo` → `in_progress` → `review` → `verified` → `done` / `blocked`

---

## ✅ DSS-BEAT — DSS 주간 적재 자동화 (가동, DSS-BEAT-1 2026-08-31) [theme-heat][dss][infra]
- D-DSS-BEAT-1. celery `chainsight-load-dss-weekly`(Fri 19:00 ET·default 큐) + 폴백 command `load_dss_week`. **2단 스위치**: PeriodicTask enabled=False 등재 → §D 워커 재시작+검증 후 enable.
- **가동 완료(2026-08-31)**: §C push 착지(origin/main `64c5b622`) → 병진 `sv sync`(worker 트리 `835da979` re-detach + celery-worker/beat 재기동·inspect ping ✓) → CC 검증 2종 통과(트리 조상 `64c5b622` 포함 · `inspect registered`에 chainsight-load-dss-weekly) → **PeriodicTask id=143 enabled=True**. **다음 발화 = 09-04(금) 19:00 ET**. 관측 = DSS-BEAT-OBS-1. 폴백(미발화 시) = 착지 트리 `manage.py load_dss_week`.

## DSS-BEAT-OBS-1 — 09-04 발화 후 검증 (등재만·차기, DSS-BEAT-1 2026-08-31) [theme-heat][dss]
- 09-04(금) 발화 후: SymbolDemandSignal anchor 09-04 신규 행 수·Score 11행(**DB 행 증거·last_run_at 불인정**) / flat_ratio 판정(§2) / arrow 상태 / 클린 쌍 5/6 갱신(ε는 09-11 6/6에 개시).

## AGENT-DOGFOOD-DSS-FRESHNESS — dogfood에 DSS/사분면 신선도 커버 추가 (이관 등재, DSS-BEAT-1 0-4 2026-08-31) [agent][dss] — @agent 소관
- 0-4 실측: `auto_agent_system/dogfood/`가 ThemeDemandScore/사분면 API(`/api/v1/chainsight/theme-heat/quadrant/`) 신선도 **미점검**. 주간 적재 자동화(DSS-BEAT) 후 무발화 감지 공백 → dogfood 신선도 타깃에 편입 검토. **구현은 AGENT 트랙 소관**(본 트랙 구현 금지·등재만).

## DSS-QUADRANT — 섹터 사분면 화면 (착수, QUAD-IMPL-1 2026-08-27) [dashboard][dss][chainsight]
- 확정 결정 5건(DECISIONS DSS-QUADRANT). Heat×수요 breadth 2축, ②·④ 하이라이트, 전주 화살표(flat≥90% 숨김), 미산출 하단 목록.
- Slice 1(BE read-only API `/api/v1/chainsight/theme-heat/quadrant/`) → Slice 2(공용 컴포넌트 `components/charts/SectorQuadrant`) → Slice 3(app/page.tsx 최상단 삽입).
- 상태: **Slice 1~3 구현 완료**. 검증 GREEN — pytest 4(quadrant)+chainsight/architecture 791·vitest 12(신규)/1145(전)·tsc0·eslint0·next build OK. 최초 STEP 0 경계 FAIL은 BOUNDARY-TRIAGE-1 동결로 해소(green). arrow suppression 라이브 작동(08-14 flat 99.60% → 화살표 전건 숨김).

## QUAD-VISUAL-CHECK — 섹터 사분면 라이브 육안 검증 (등재, QUAD-IMPL-1 2026-08-27) [dashboard][qa] — 병진 몫
- F2-VISUAL-CHECK 동일 패턴. **자동 테스트로 못 잡는 시각 정합**(점/구역 색·화살표 숨김 각주·미산출 하단 목록·반응형)을 라이브 렌더로 검수. 트리거 = 배포(web 리빌드) 후.
- 현 데이터 특성: heat 6/11 산출(5 하단 목록)·arrow 전건 suppressed(각주 노출)·경계 x=heat 중앙값 50. 배포 전엔 신 UI 미표시가 정상(#62).

## BOUNDARY-BURNDOWN-EOD — shared 경계 동결 #6 소진 (등재, BOUNDARY-TRIAGE-1 2026-08-27) [ops][boundary][harness]
- **동결 1건**: `packages/shared/stocks/services/eod_signal_calculator.py:50` → `apps.monitor.models.monitor` (7ec24c62 EODUNIV-P15-V01, 08-26 유입). BOUNDARY-TRIAGE-1이 KNOWN_VIOLATIONS 양쪽 동결(green 회복).
- **소진 재료(0-4)**: 위반 함수 = `eod_universe_symbols()` — `Monitor(scope=stock).target_ref`를 union. 호출자 전부 packages/shared 내부(`backfill_eod_signals_universe`·`eod_pipeline:297,570`). `apps.monitor.Monitor` = user-data 모델(scope/target_ref).
- **방향 후보(결정=디렉터)**: 방향2(주입=호출자가 watch symbols를 `eod_universe_symbols(extra=...)`로 주입 → shared 무의존) / 방향C(승격=VIXProvider식 포트+등록 패턴 의존역전, BOUNDARY-3 선례). 방향1(소비자 이동)=호출자가 shared 내부라 난도 높음.
- **통지 필요**: EODUNIV-P15 트랙(원 유입)과 소진 방향 조율.
- **목표**: 동결 1→0, green 유지(동결=임시 격리). 상태: **등재(방향 결정 대기)**.
## AGENT 트랙 — 야간 도그푸딩 에이전트 (2026-08-27 개설, D-AGENT-S1)

> 3단계: **1단계 정량**(완료) → 2단계 루브릭 채점 → 3단계 관찰 후보 + 성적 원장. 메일 매일.
> 루브릭·점검 대상 단일 출처 = `frontend/lib/guide/` confirmed 데이터(D-GUIDE-TRACK).

| ID | Task | Agent | Depends On | Status | 근거/비고 |
|----|------|-------|------------|--------|-----------|
| AGENT-S1 | 1단계 — 정량 체크 러너 + diff 3분류 + 메일 + 실행 스크립트/plist 초안 | @infra | D-AGENT-S1 | ✅ **완료·main 착지 `a717a204`** | pytest 신규 48 · 전체 5041 passed/53 skipped · ruff 신규분 0. 수동 1회 실행 성공(정량 16/17)·**메일 실발송 2통**. 점검 대상은 가이드 데이터에서 자동 유도. |
| AGENT-S1-DEPLOY | 운용본 배치 + launchd 등록(05:20 KST) | @infra(CC 집행) | RC-A-1 배포창(done) | ✅ **완료(2026-08-31)** — HALT 해소 | **HALT 해소**: RC-A-1 ②~⑥ 완주로 차단 사유 소멸 → 같은 날 집행. `sv sync`(3트리 `3cf29551`→`705cd0bd` 정렬·celery ping OK·daphne 401) → 운용본 `run_dogfood.sh` 1회 exit 0(정량 **16/17**·메일 1통) → `launchctl bootstrap`+`enable`. **diff 3분류 실작동 실증**(08-27 대비 `신규 0·재발 1(is_stale 2일째)·해소 0`). plist lint OK·`state = not running`(05:20 스케줄 대기). ⚠️중간에 `celery-worker`가 미로드라 첫 `sv sync`가 kickstart에서 중단(web·api 미동기) → 워커 bootstrap 후 재실행으로 해소. |
| AGENT-S1-AUTH | 점검 전용 계정 `DOGFOOD_API_USER/PASSWORD` env 등재 | 병진(수동) | — | 🆕 **todo(2단계 선행)** | 현재는 무인증 축소 모드(401=존재 확인만) → API **스키마·빈 응답 미검사**. 전용 읽기 계정 권장(일반 계정은 실사용 데이터 접촉 여지). credential은 코드 미포함(repo PUBLIC). |
| AGENT-S1-OBSERVE | 익일 2일치 리포트로 **diff 3분류 실작동** 확인 + 로그 위생 | @qa | AGENT-S1-DEPLOY | 🆕 **todo(첫 자동 발화 = 09-01 05:20)** | 첫날은 "기준일" 처리(설계). 2일째부터 신규/재발/해소가 나온다. 합성 데이터로는 이미 실증됨. |
| AGENT-S2 | 2단계 — 루브릭 채점(화면별 coreQuestion 기준) | 미배정 | AGENT-S1-AUTH · GUIDE 검수(done) | 🆕 **todo(별도 지시서)** | 채점 기준 = confirmed `coreQuestion`. 결핍 = ⑴ 인증 계정 ⑵ 화면별 "정상 상태" 정의 ⑶ 렌더 후 DOM 접근 수단(1단계는 SSR HTML만 봄 — 클라이언트 렌더 데이터·`data-guide` 앵커는 HTTP로 안 보임). |
| AGENT-S3 | 3단계 — 관찰 후보 0~5개 + 성적 원장 | 미배정 | AGENT-S2 | 🆕 **todo(별도 지시서)** | — |
| AGENT-API-GAPS | 1단계에서 드러난 **필요 API 목록**(도메인 앱 이관) | 해당 앱 트랙 | — | 🔭 **관찰(등재만·구현 금지)** | ⑴ 무인증 **점검용 요약 엔드포인트 부재** — 화면 데이터 유무를 보려면 사용자 토큰이 필요(EOD만 baked JSON으로 무인증 접근 가능). ⑵ `/api/v2/market-pulse/health`가 **인증 게이트**라 헬스 용도로 못 씀(무인증 `/api/v1/health/`는 있음). |

## GUIDE 트랙 (2026-08-27 개설, D-GUIDE-TRACK)

> 출처: D-GUIDE-TRACK(DECISIONS 2026-08-27). 목표 = 옵션 C(허브 + 화면별 `?` 오버레이). 가이드 데이터 = **야간 도그푸딩 에이전트 루브릭 단일 출처**. 순서 = 가이드 → 에이전트.

| ID | Task | Agent | Depends On | Status | 근거/비고 |
|----|------|-------|------------|--------|-----------|
| GUIDE-S1 | 슬라이스 1 — 데이터 계약(`lib/guide/`) + 렌더러(GuideOverlay·GuideHub) + 네비 삽입 + 핵심 5화면 | @frontend | D-GUIDE-TRACK | ✅ **완료·main 착지 `8aa46ab8`(GUIDE-S1C 동반)** | vitest 1164·tsc 0·lint 순증 0. 행위보존 기계 증명 12/12. |
| GUIDE-S1-REVIEW | 5화면 문구 병진 검수 → `reviewStatus` draft → confirmed 전환 | 병진(사용자) | GUIDE-S1 | ✅ **승인 완료(2026-08-27)** | 5화면 승인. marketPulse만 v1 초안 폐기→v2 문구 교체 후 confirmed. 허브 "초안" 배지 전건 소멸(테스트 고정). |
| GUIDE-S1-SHOT | 5화면 + 허브 라이브 스크린샷 증적 | @qa | GUIDE-S1 랜딩 | 🆕 **todo(잔여)** | [[feedback_ui_slice_live_screenshot]]. browse 데몬 무출력·Chrome 확장 미연결로 S1에서 미수행. HTML 렌더 검증으로 갈음(6라우트 200·`?` 버튼 5/5·`/guide` 미노출 1/1). |
| GUIDE-S2 | 슬라이스 2 — 잔여 사용자-대면 화면 가이드 확장(31화면) | @frontend | GUIDE-S1-REVIEW(done) | 🆕 **todo(선행 해소·착수 가능)** | 톤 확정됨. 권고 순서 = `/stocks/[symbol]`(4단계 갭) → Monitor 심화 4 → Chain Sight 심화 → 나머지. |
| GUIDE-STAGE4-GAP | 플로우 4단계(1차 검증)에 **독립 라우트 부재** — 검증 UI는 `/stocks/[symbol]` 내부 섹션. 허브가 "가이드 준비 중"으로 정직 표시 중 | 미배정 | 설계 | 🔭 **관찰(KEEP/CUT 입력)** | 심볼 없이는 진입 불가 → 플로우 한 바퀴가 끊긴다. 라우트 신설 vs 플로우 정의 수정 = 제품 결정. |
| GUIDE-MP-V1V2 | `/market-pulse` v1↔v2 이중 — 가이드를 어디에 붙일지 | 미배정 | — | ✅ **해소(D-MP-V2-NAV, S1C)** | 가이드·네비 모두 v2로 이설. v1은 가이드 미제공 = 은퇴 신호. 후속 = `MP-V1-RETIRE`. |
| MP-V1-RETIRE | **v1(`/market-pulse`) 은퇴 결정·집행** — 리다이렉트 여부 + MobileNav active prefix 정리 + docs 정리 | 미배정 | GUIDE-S1C §4 측정(done) | 🆕 **todo(결정 대기·재료 확보됨)** | 측정 결과 **실동선 0건**(네비 전환 후 v1로 보내는 Link/href/push 없음·백엔드 알림은 이미 v2·manifest/middleware 무참조). 기술 장애물 없음 → **결정만 남음**(디렉터). 함께 정리할 것 = Header/MobileNav active 판정식 불일치(v1에서 Header 비활성·MobileNav 활성). **리다이렉트 목적지 후보 = `/market-pulse-v2/macro`(MP2-SUBPAGES-S1 허브, 2026-08-31)** — v1 위젯 4/5가 허브에 흡수됨(MarketMovers=S2 잔여, 흡수 완료 후 v1↔허브 완전 대체). |
| GUIDE-S1C-RUNTIME | 런타임 동기(3트리 `418b2a8e`→`8aa46ab8`) + web 프로덕션 리빌드 | 병진(수동) | main 착지(done) | 🆕 **상신 완료·집행 대기** | CC 자기 집행 금지(서비스·launchctl / sv sync 명시 승인 인용 필요). **마이그 0건·`migrate --plan` no-op·lock 무변** 실측 → 안전 확인됨. 명령문 = scratchpad `GUIDE_S1C_런타임동기_상신_20260827.md`(DEPLOY.md 2.1+2.2). 이 동기는 SCAN-B2-FE·CS-UNIVERSE-EXCLUDE·R2-PRE-A·BOUNDARY-TRIAGE-1도 함께 반영. |
| GUIDE-S1C-SHOT | 허브 + 5화면 오버레이 라이브 스크린샷 증적 | @qa | GUIDE-S1C-RUNTIME | 🆕 **todo(잔여·도구 제약)** | S1에서 browse 데몬 무출력·Chrome 확장 미연결로 2회 시도 후 중단. 대체 증적 확보됨: ⑴ 실 페이지 통합 테스트(v2 7영역 앵커 전건 해소 + 배지 7/7) ⑵ 라이브 HTTP 7라우트(`?` 노출/미노출 매트릭스). GUIDE-S1-SHOT 승계. |
| GUIDE-AGENT | 야간 도그푸딩 에이전트(옵션 B+C: 관찰 후보 0~5개 + 성적 원장) — 루브릭 = `coreQuestion` | 미배정 | GUIDE-S1-REVIEW | 🆕 **todo(별도 지시서)** | 검수된 coreQuestion 없이 착수 금지(기준 문장이 흔들리면 채점이 무의미). |


### 질문 불성립 파생 — 앱 백로그 (GUIDE-S1 조사 산출, 2026-08-27 · **등재만·구현 금지**)

> 출처: GUIDE-S1 부록 A. "이 영역이 답하는 질문"이 정직하게 안 써진 자리 = 제품 결함 후보. 가이드 트랙이 아니라 **해당 앱 소관**.

| ID | Task | Agent | Depends On | Status | 근거/비고 |
|----|------|-------|------------|--------|-----------|
| DASH-STRIP-KEEPCUT | 대시보드 3스트립(Coverage·Macro·News) KEEP/CUT — 전부 fail-quiet이라 "무엇을 결정하게 해주는지"가 안 써짐. 배경 장식인지 판단 재료인지 불명 | @frontend (dashboard) | — | 🔭 **관찰(등재만)** | 질문 부여(KEEP) or 제거(CUT). 가이드 regions에서 제외된 상태. **SectorQuadrant 포함 (QUAD Slice 3 fail-quiet 삽입 — 무기 파이프 단절 시 무표시)** (DSS-W8-LOAD-1 2026-08-31). |
| PF-TODAY-GAIN | 포트폴리오 "오늘 수익"이 **항상 0** — `app/portfolio/page.tsx`의 `todayGain={0} // TODO`·`todayGainPercent={0} // TODO` 하드코딩 | @frontend (portfolio) | — | 🔭 **관찰(등재만)** | 표시는 되는데 값이 언제나 0 = "거짓을 조용히 보여주는" 상태. 구현하거나 숨기거나 둘 중 하나. |
| CS-ATTENTION-DEF | Chain Sight 카드 "관심도"(`avg_score`)의 정의가 화면에 없음 — 무엇을 0~100으로 매긴 값인지 답 불가 | chain_sight | — | 🔭 **관찰(등재만)** | 툴팁·범례로 정의 노출 필요. 가이드는 "세 숫자"로 뭉뚱그려 우회. |
| GUIDE-STAGE4-ROUTE | 플로우 4단계(1차 검증) 독립 라우트 부재 — 검증 UI는 `/stocks/[symbol]` 내부 섹션뿐 | 미배정 | 설계 | 🔭 **관찰(등재만)** | GUIDE-STAGE4-GAP과 동일 사안. 라우트 신설 vs 플로우 정의 수정 = 제품 결정. |

## INC-P16 후속 (2026-08-24~27, 홈 429 트랙 — 종결)

> INC-P16-1(핫픽스 A+B+C, `9e2e98f3` 08-26 랜딩)·INC-P16-2(포렌식: FE 루프 부재 확정)·INC-P16-CLOSE(소품 3+등재) 종결. **Phase 1.6 종결**. cf. D-INC-P16-1·D-INC-P16-2.

| ID | Task | Agent | Depends On | Status | 근거/비고 |
|----|------|-------|------------|--------|-----------|
| SMOKE-BROWSER-PATH | 브라우저 경로 재현 스모크 보강 — **재현 기준 = 분당 ~5회 "현실적 새로고침"**(사용자 실사용 상한)에서 429/전면에러 부재 관측. **하드리프레시 연타는 재현 대상 아님**(INC-P16-2 확정: 연타=외부 반복 문서 로드로 throttle 초과가 물리적 정상 — 이때 검증 대상은 "429 무증폭·2초 내 회복"뿐). 단건 curl은 이 유형을 **구조적으로 못 잡음**(200 정상)이 교훈 | @qa (browse) | ✅ INC-P16-1 랜딩(`9e2e98f3`, 08-26) | ✅ **done (P2-DLITE, 2026-08-29)** | `e2e/market-pulse-429.smoke.spec.ts` — ①현실 새로고침 5회 무증폭(로드당 5 일정)·②429 무재시도(overview **1회**·단언 `≤1`로 조임[MGMT-BATCH-39: retry 회귀 감지력 복원])·2초 내 회복(~680ms). route interception(단건 curl 한계 구조적 해소). cf. D-INC-P16-1·D-INC-P16-2·D-P2-ENTRY-1·common-bugs #122/#123 |

## SCANNER-SELECT-UX 트랙 (2026-08-20 개설, D-SCANNER-SELECT-UX)

> 출처: D-SCANNER-SELECT-UX(DECISIONS 2026-08-20). 목표 상태 = 정보안 C · 경로 ㉮(① FE → ② shared BE → ③ 관계·이력). 슬라이스 6+1. RECON = [[project_scanner_ux_recon]].

| ID | Task | Agent | Depends On | Status | 근거/비고 |
|----|------|-------|------------|--------|-----------|
| SCAN-B1-FE | ① 축 슬롯 행 + 필터 바 + 카테고리 합류 + 추천 카드 교차 배지 + 커버리지 창 **w90(ⓐ-1)** — 정칙 ⑴⑵⑸(+⑷ 보유 데이터 범위). **지시서 발급됨**. | @frontend (dashboard) | D-SCANNER-SELECT-UX | 🆕 **todo(지시서 발급)** | 순수 FE·보유 데이터 범위. w90 = D-C2-S2-FUNNEL-COV-A ⓐ-1. |
| RECON-VALUATION-R1 | ② 계약 재료 실측(**읽기 전용**) — 밸류/퀄리티/베타/RSI/52주/MA 필드 소재·계산 가능성·비교군(industry/sector) 표본. **지시서 발급됨**. | 읽기 전용 | — | 🆕 **todo(지시서 발급)** | SCAN-B2-BE 계약 입력. 정칙 ⑶⑷⑺ 실측. |
| SCAN-TELEM-SHARED | 스캐너 표면 상수 + SURFACE_KIND 분류(**shared 위임**) | platform (shared) | — | 🆕 **todo(대기)** | 관찰 ⑴ 미계측 해소 선행. |
| SCAN-TELEM-FE | 스캐너 노출 emit(SHARED 착지 후) | @frontend (dashboard) | SCAN-TELEM-SHARED | 🆕 **todo(대기)** | organic 노출 표본 성장 → ⓐ-2 재개 재료. |
| SCAN-B2-TECH-BE | ② 기술축 베이커 보강 **(선행·초저비용)** — 캘큘레이터 기계산 `rsi_14·high_52w·dist_52w·sma_50/200`를 tagger 고정 키셋 드롭 **해제** + baker `_build_preview_stock` 서피스. 재계산 0. **shared 위임** | platform (shared) | RECON-VALUATION-R1(done) | ✅ **착지(LAND-SCAN-B2TECH, origin/main `1c338dac`, 08-26)** | D-SCAN-B2TECH-CONTRACT. `technical{rsi/rsi_state/dist_52w_high_pct/ma_state}`·pytest 181·makemigrations 무변. **차기 야간 bake부터 산출(prod bake 미실행)**. |
| SCAN-B2-FUND-BE | ② 펀더축 베이커 보강 **(후행·중비용)** — statement enrichment(baker preload 패턴)·**TTM dedupe(period_type)**·밸류=market_cap÷TTM·퀄리티=ROE/margin/debt/current·**sector 중앙값 집계(n·폴백 표기)**. 정칙 ⑶강화·⑷·⑺. **shared 위임** | platform (shared) | SCAN-B2-TECH-BE(done) | 🆕 **설계 대기·후행 유지(폐기 아님, MGMT-BATCH-40 재편)** | D-SCAN-B2-DERIVE. **SCAN-UX-2 후행** — 밸류축은 스토리 프리셋(㉱)에 후속 결합. 입력=사용자 화면 소감 + payload 실측 가드. **STEP 0 payload 실측 가드 필수**(D-SCAN-R1-CORRECTION 관찰 ⑵·TECH 이미 +26%)·초과 시 symbol-ref 축약 편입 상신. |
| SCAN-B2-FE | ② 축 칩 점등 (기술 칩 1차) | @frontend (dashboard) | SCAN-B2-TECH-BE(done) | ✅ **착지+배포 완료 (LAND-SCAN-B2FE `418b2a8e` 08-27 · DEPLOY-EXEC-2 `9460430f` 08-28) · ⑦b 육안 검증 완결(MGMT-BATCH-40)** | D-SCAN-B2TECH-CONTRACT enum 맵. 번들 마커 6종+baked 402/403 확증·점등 조건 성립. **스캐너 아크 ①FE(B1·B2-TECH·B2-FE) 완결·라이브**·08-31 사용자 스크린샷 2매 화면 실재 확인(필터 바·칩 전종·C2 정직성·C3 안내). cf. D-SCAN-DEPLOY-CORR. |
| SCAN-UX-2 | ⑦b 소감 구조화 반영 **(신설·선행·범위 확장 MGMT-BATCH-41)** — ㉮고정영역 컴팩트化(가시 종목 ↑)·㉯연속 상승/하락 방향 분리(`signal_direction` bull160/bear102/neu2)·㉰테마 포함 사유 즉답(`signal_value` 기보유)·㉱스토리 프리셋(목업 동반 결정) + SCAN-FIX-1(strip 라벨) + **⑵성능 수리(key remount 제거·React.memo·useMemo)** + **⑴거래대금 임계 재설계(설계 사안: 상향 vs 분위수 vs 제거)** 편입 | @frontend (dashboard) | D-SCAN-UX2-FEEDBACK·D-SCAN-R1-OBS(판정) | 🆕 **todo(선행·자동 우선순위 마진 1.45)** | ㉮㉯㉰=FE 공짜 필드(베이커 무접촉·저비용)·㉱=목업 결정 후. 설계 입력=RECON-SCANDIAG-R1 판정(⑴⑵ 이관). |
| RECON-SCANDIAG-R1 | ⑦b 관찰·이상 3건 진단(**읽기 전용**) — ⑴거래대금 필터·⑵필터 지연·⑶coverage audit | 읽기 전용 | D-SCAN-R1-OBS | ✅ **done·판정 종결(MGMT-BATCH-41)** | ⑴배선 정상·임계 설계 문제(유니버스 min $53.8M>$50M·시총 $50B+만 변별)→SCAN-UX-2 이관 · ⑵key remount+memo 부재→SCAN-UX-2 이관 · ⑶audit 0·0·0=**정상**(창 이동·w7 34/0/34·w90 114/12/102·조치 불요). cf. D-SCAN-R1-OBS 판정 종결. |
| SCAN-STORY-LLM | 종목 서사 3층 — ①사실 층 → ②서사 층(리스크 서술) → ③story_tag. **착수 A(템플릿)** → B 계층 확장. LLM 층=shared LLMClient 래퍼+circuit breaker+템플릿 폴백·**상위 합류 한정** | @frontend + @rag-llm + platform | D-SCAN-STORY-3LAYER · **NEWSFIX-SYNC-BE(선행·V2)** | 🆕 **todo(SYNC 착지 후)** | 서사 층=실뉴스 의존 → **NEWSFIX-SYNC-BE 착지**(sync beat 실데이터 물질화)가 선행 조건(D-NEWSMATCH-FIX-PATH-V2로 갱신). 서사 본문=per-stock JSON(행 클릭)·행엔 story_tag만(payload ×4 회피). story_tag=SCAN-UX-2 ㉱ 재료. |
| RECON-NEWSMATCH-R1 | **NEWS-MATCH 승격 1단계** — 스캐너 실뉴스 매칭 0건(08-24) 원인 진단(**읽기 전용**) | 읽기 전용 | D-NEWSMATCH-PROMOTE | ✅ **done·판정(MGMT-BATCH-41 in-session)** | **근인=⒜source absent+⒠이원화**: enricher가 `StockNews`(0행·죽은 테이블) 조회→100% profile 폴백. 실뉴스는 `NewsEntity`(587k) 실재·매칭 로직 무결. 추천카드 다운스트림 오염. **수리 3후보 OPEN**(⑴enricher→NewsEntity 재배선[소·@backend] ⑵sync beat[중] ⑶모델통합[대]). cf. D-NEWSMATCH-PROMOTE 판정. |
| NEWSFIX-BE (seam) | enricher `NewsSource` 주입 seam(shared) — 1′ 배선은 ⒝ HALT(트리거 전부 shared·앱 진입점 부재) | @backend (shared) | D-NEWSMATCH-FIX-PATH | 🟡 **커밋만·미머지·LAND 대기 (`614f19db`, sess-newsfix-be)** | ⚠ origin/main **미포함**(별도 LAND 세션 필요·"착지" 아님). seam 존치=테스트 하네스 16건+미래 주입 자산(D-NEWSMATCH-FIX-PATH-V2). 회귀 stocks 225·경계 green·makemig no-op. |
| NEWSFIX-SYNC-BE | **NEWS-MATCH 수리 확정 경로(V2 ⑵)** — 앱측 sync beat: `NewsEntity`→`StockNews` 주기 물질화(멱등·max_retries=3). enricher 무접촉(기본 StockNewsSource가 실데이터 매칭) | @backend/news (services.news) | D-NEWSMATCH-FIX-PATH-V2·D-OWN-NEWS | 🆕 **build 대기(지시서 발급됨)** | bake 오케스트레이션 무접촉·죽은 테이블 물질화. **SYNC 착지 후 효과 3종 검증**: ⓐ스캐너 `news_context`(profile 폴백 이탈) ⓑ추천 카드(다운스트림 자동 치유) ⓒ뉴스 존재 칩(0렌더→점등). **common-bugs `#NN` = 착지 확인 후 차기 mgmt 부여**(비mgmt 채번 금지). |
| SCAN-B3 | ③ 관계 강도·발급 이력 — **착수 전 별도 설계 사이클**(chain_sight/platform 위임) | chain_sight/platform | 별도 설계 | 🆕 **todo(설계 선행)** | 관계 축 강도 우선(정칙 ⑹). |
| SIGNAL-HITRATE | **(예약·착수 아님)** 신호/합류 발생 후 N일 수익률 추적 — Phase 5 캘리브레이션 정합. "배지가 자기 성적표를 갖게 한다." | 미배정 | 예약 | 🔭 **예약(착수 전)** | Phase 5 정합. |

## NEO4J-CLOSE-1 후속 (2026-08-20, sync 재활성화·트랙 종결 후)

> 출처: NEO4J-CLOSE-1(지시서 `be594bd9`). GRAPH-NEO4J-SYNC-DEACTIVATE 종결(위)·OPS-SMTP-CRED 선존(line 235 참조).

| ID | Task | Agent | Depends On | Status | 근거/비고 |
|----|------|-------|------------|--------|-----------|
| NEO4J-RESTORE-P2 | ~~Neo4j launchd 항구화~~ **✅ 종결(OPS-SWEEP-1, 2026-08-20)**: `com.stockvis.neo4j.plist`(JAVA_HOME·KeepAlive·RunAtLoad) 병진 수동 설치 → 08-20 08:14 UTC Started·launchd status 0·bolt LISTEN·.env 인증 통과. 죽은 homebrew.mxcl.neo4j 제거. runbook 보강(mkdir 선결·운영규칙·소스정본). | @infra | 완료 | ✅ done |
| NEO4J-SYNCEDAT-PROBE | synced_at 07-11 스탬프 경위 미해명(homebrew 04-03·타르볼 05-01 어느 쪽도 설명 불가) — `git log neo4j_sync.py` 프로브로 판별 | @backend | — | 🔭 등재(저순위) |
| NEO4J-NODECOUNT-PROBE | 그래프 NODE 1181→1084(−97) 감소가 로그로 미설명(레거시 정리=엣지 삭제만·`_delete_edge`=DELETE r·DETACH 0). 측정 시점 상이 가능 — 필요 시 노드 델타 프로브 | @backend | — | 🔭 등재(저순위) |
| EODDASH-TARGETDATE | `run_eod_pipeline(target_date=)` 재실행 경로가 EODDashboardSnapshot row 미생성(JSON은 bake됨) — target_date 경로에서 요약 스냅샷도 생성하도록 개선 | @backend | — | 🔭 등재(저순위) |
| Q19-REMEASURE | sync 재개 후 Q19(co-mention 04-25 단절) 재측정 — 신규 고유 페어 관측 + 9562 지표 정의 실측 **선행** | @backend | sync 재개(done) | 🔭 등재 |
| WORKTREE-CLEANUP-NEO4J | ~~sess-neo4j-recon 정리~~ **✅ 종결(OPS-SWEEP-1 §3, 08-24 병진 실행)**: worktree `sv-neo4j-recon` remove·브랜치 `sess-neo4j-recon` -d(was cc6cb88b, 거부 없이 정상)·`~/setpw.sh`·`~/alter.sh`·`.cypher_shell_history` 제거. 검증 완료(디렉토리·브랜치·헬퍼 실삭제). | @infra | 완료 | ✅ done |
| OBS-DESKTOP-TREE-OCCUPY | 관찰: `~/Desktop/stock_vis`가 브랜치 `sess-signal-fwd-recon` 점유·dirty 20(미커밋 docs). 해당 트랙 소유 → 본 세션 무조치. worktree-per-세션 규율상 정리/커밋은 소유 트랙 판단 | @infra | 소유 트랙 | 🔭 관찰 등재 |

## CS-P2-8K 후속 (2026-08-13, 8-K 파이프라인 랜딩 후)

> 출처: CS-P2-8K 종결(랜딩 `16060620`, DECISIONS `D-CS-P2-8K`). 착지 15관계·미해소 375·증거 549 보존.

| ID | Task | Agent | Depends On | Status | 근거/비고 |
|----|------|-------|------------|--------|-----------|
| P28K-ACQUIRED-DIR | **8-K ACQUIRED 재해소 정제 + 방향 판정 설계**(CS-P4 0-3 게이트 HALT로 스코프 확대) — ⑴상대 티커 **재해소 정제**(resolved 97 중 fuzzy 32 오매칭 제거·exact/alias만) ⑵**역할 판정**(filer=인수자/매도자/피인수 분류, **item 2.01 완료 vs 1.01 계약 구분**·merger sub/자회사 배제) ⑶방향 엣지(인수자→피인수자, D-ACQ-DIR·무방향병합 금지) 착지 재개 | @backend | F2·D-ACQ-DIR | **todo(설계 사이클)** | CS-P4 0-3: item2.01=취득OR처분→filer=매도자 다수(ALB·AMD·CCI). 별도 결정 사이클 |
| P28K-TICKER-TOKENSET | ticker_matcher token_set_ratio 개선 — fuzzy 오매칭(Masimo→Masco·Synaptics→Snap-on) 근절 | @backend | 독립 | **todo** | F1. 현행 token_sort≥80 오매칭 다발 → 8-K fuzzy 착지 금지 중. 접미사/법인격 정규화 + token_set. 8-K·10-K 공통 |
| P28K-CLIENT-FIX | `SECEdgarClient.download_8k_text` 디렉토리 스크래퍼 수리(`//index.htm` 404) → primaryDocument 직접 URL | @backend | 독립 | **todo** | 이번엔 로컬 헬퍼 우회(공유 client 무접촉 승인). 근본 수리는 공유 client 반영. common-bugs 등재 |
| P28K-BEAT | 8-K 일일 수집 beat 등재 결정(collect_8k_filings→extract_8k_relations 체이닝 주기 실행) | @infra | 별도 결정·병진 | **todo(스케줄 미정)** | Bug #28 준수(register_*_beats DB 등록). LLM 비용·캐이던스 산정 후. 현재 일회성 command만 |
| P28K-ITEM-EXPAND | item 확대 검토(5.02 임원 등 material event) — 관계 신호 가치 평가 | @backend | 별도 결정 | **backlog** | 현재 1.01/2.01만. 5.02(임원)=관계 아님 → 신중. 8-K item 유형별 관계성 평가 |
## MP-STRESS 트랙 (2026-08-13 개설, Crisis/Stress 레이어)

> 출처: MP-STRESS 결정 사이클(D-MPS-* 8건, DECISIONS 2026-08-13). MPS-1 백엔드 코드 랜딩 = worktree `sv-mps1-stress` 커밋 `6c1c3736`(미push). 초판 = 표시 전용(regime 판정 무접촉).

| ID | Task | Agent | Depends On | Status | 근거/비고 |
|----|------|-------|------------|--------|-----------|
| MPS-1 | 스트레스 스코어 엔진 + regime/stress API + 수집 2종 배선 | @backend | — | ✅ **코드 done(`6c1c3736`+`8d868651`)** | 엔진(가족균등가중 z 평균)+카테고리+백분위+방향2종+level_band 잠정. TDD 36 신규 GREEN·전체 4773 pass·경계0·health❌0·regime판정 150 GREEN |
| MPS-1-LAND | level_band 개명(crisis→severe, D-MPS-BAND-NAME) + F5-① l3_why import 수리 + 원장(D-MPS-* 4건 보강) + rebase·push | @backend | MPS-1 | ✅ **landed(origin/main `e42ba9ab`, ff-only, 2026-08-13)** | 개명=문자열만·금지규칙2 계약 테스트. l3_why 신규 GREEN(선존 3→2). 5커밋 union rebase 무손실. (직전 self-referential "착지" 문구 마감) |
| MON-ADVISOR-DATEDEP | **known-fail(OPS 별건)**: `tests/monitor/test_advisor_briefing.py` 2건(`test_creates_note`·`test_coverage_denominator_not_hardcoded_9`) date-dependent 실패(DailyPrice coverage_n=0) | @infra | — | 🕒 **known-fail 등재** | MPS-1 회귀서 발견·클린 트리(내 diff 없는 트리) 재현 확정=선존. 오늘(08-13) 기준 DailyPrice 윈도 정합 깨짐 추정. 레지스트리 미등록이라 등재 — 수리는 OPS(MPS-1 무관) |
| MPS-1-DEPLOY | seed 0007 apply(prod) + 워커 재기동 + 일상 수집 점등 | @infra | MPS-1 push | ✅ **done(2026-08-14, D-MPS-OPS-SYNC)** | sv-worker-runtime ff 동기(c9400d18→24커밋)+launchd kickstart(worker 51619/beat 51624)+seed 0007 적용+수동 트리거 → **DTWEXBGS 97·STLFSI4 100행 유입**(data_source=fred). PeriodicTask 124 무손상. **Part 1.3 정정: setup_marketpulse_beat 재실행 불요**(신규 series=기존 태스크 모듈 상수, 새 PeriodicTask 없음) |
| MPS-1-BACKFILL | 신규 2종 소급 백필 실행(prod write) | @infra | MPS-1-DEPLOY | ✅ **done(2026-08-14)** | --commit 완료: **DTWEXBGS 776·STLFSI4 162행**(2023-07~, ±10% 게이트 PASS)·멱등(재백필 0)·**스코어 무영향**(BEFORE=AFTER -0.197/stable/30.8/804). ⚠️ --econ-only 누락으로 섹터 ETF 7,579행 부작용 → **INC-MPS-BACKFILL-SCOPE 존치**(자연 소멸) |
| MPS-OPS-D1 | 익일 beat 자동 실행으로 DTWEXBGS·STLFSI4 신규행 유입 확인(수동 트리거 성공 ≠ 스케줄 성공) | @infra | MPS-1-DEPLOY | ✅ **확인(2026-08-19 실측, MPS-OPS)** | 스케줄런 정상 실증: **DTWEXBGS**(daily) 08-17 21:41 런이 08-10~14 5행 신규적재 → 08-07에서 **08-14로 전진**(latest data 08-14, 08-15 금은 1영업일 지연 미도달=정상). **STLFSI4**(weekly) latest 08-07 그대로·last_updated 08-17 21:41(런 실행됨·신규 0) = **08-14주 값 FRED 미발행**(주간 지연, 파이프라인 정상). 전진 0 아님·HALT 없음 |
| DEPLOY-RUNBOOK | 런타임 동기 절차 정의(주기·체크리스트·runbook) — api 런타임 포함(스테일 런타임 3개 실증: worker+web+api) | @infra | — | ✅ **done(2026-08-20, RB-1·D-RB-1/D-RB-2)** | `docs/runbook/DEPLOY.md` 4장(1장 고아 스윕·2장 동기 절차[web 리빌드 2.2 수동 명기]·3장 감사·부록 인벤토리/neo4j 예외/주기 조정). 자동 감지 = `runtime_check.py`(read-only 3검사)+launchd `com.stockvis.runtime-check`(3600s). 3전례(SYNC/WEBSYNC/APISYNC) 절차 흡수. SESSION_CONTRACT §H 포인터 편입 |
| SYNC-AUDIT-LOG | `worker_sync.sh`에 집행 감사 로그 1줄 추가(시각·pid·ppid·호출 컨텍스트=tty/parent) — 미귀속 동기 실행 구조적 재발 방지 | @infra (`scripts/worker_sync.sh`) | RB-1 | ✅ **done(2026-08-20, RB-1)** | dry-run exit 직후(실행 최초 지점) `audit_log()` 비차단 추가 → `sync-audit.log`에 `<ts> invoked pid ppid(부모명) tty before[worker/web/api HEAD]` 1줄. diff=18 insertions·0 deletions(행위보존). 다음 미귀속 사건 특정 비용 소거 |
| SYNC-COVERAGE | `worker_sync.sh` web 파트가 **프로덕션 리빌드 미커버**(re-detach만·"next dev 핫리로드"는 prod 빌드엔 거짓) → FE 변경 반영은 현재 런북 2.2 수동 절차. 자동화(빌드+kickstart web-frontend) 후속 검토 | @infra (`scripts/worker_sync.sh`) | RB-1 | 🕒 **후속 등재(RB-1 STEP 0 발견·행위보존으로 이번 미확장)** | worker/api는 kickstart 커버·web은 re-detach만. WEBSYNC 가드레일(빌드 먼저·폴백·스모크)을 스크립트화 시 web도 `sv sync` 1회로 완결. 착수 전 무중단 폴백 안전성 재확인 필요 |
| MPS-OPS-GLD-DASH | 티커 스트립 비주식 ETF 시세 "—"(누락) — Stock 테이블에 레코드 부재(GLD·SLV 등 커모디티 ETF) | @backend | — | 🔎 **소형 조사 후보(MPS-OPS 관찰, 이번 세션 수리 금지)** | DailyPrice 이전에 Stock 시드 없음. 스트립이 GLD 등을 기대하나 종목 미등록 → 시드 필요 여부·대체 소스 판단은 별건. **STEP 0 재료(INC-P16-1 포렌식 관측 인계)**: 16:41 FMP 402 로그(CLUSD·NGUSD·DX-Y.NYB, #23 `.`포함/커모디티 심볼 프리미엄벽 패턴) → 커모디티/FX 시세 대체 소스 결정 시 참조. 본 세션 미검증(포렌식 보고 전사) |
| OPS-NEO4J-TREE | neo4j 워커(pid 15346)가 **미커밋 recon 트리**(`Desktop/stock_vis` sess-signal-fwd-recon)에서 구동 중 — 정리 별건 | @infra | — | 🕒 **별건 등재** | STEP 0 발견. neo4j 워커 cwd=Desktop(로컬 미커밋 변경 다수). #45 트리 표류 리스크. 별도 정리(전용 런타임 트리로 이관) |
| BACKFILL-SCOPE-GUARD | `backfill_v2_a1` 하드닝 — `--series-id` 지정 시 심볼 백필 자동 배제 또는 명시 플래그 강제(위험한 기본값 제거) | @backend | — | 🕒 **소형 하드닝 등재(INC-MPS-BACKFILL-SCOPE 파생)** | --series-id가 econ만 스코프하고 심볼은 전량 백필하는 기본값이 INC 유발. --series-id/--symbol 중 하나만 지정 시 나머지 파트 스킵이 안전 |
| MPS-SOFR | **별건**: SOFR 스프레드 series 전략 확정(**별건 내 프로브 허용**) + 필요시 market_pulse 파생 최소 설계. 소급 백필로 무손실 | @backend | — | 🕒 **보류(기한=S4-REBASE 성분 편입 심사 前)** | market_pulse 파생 인프라 부재로 MPS-1서 배선 보류(D-MPS-INDICATORS). 단일 raw 존재 시 1줄, 파생(SOFR−EFFR)이면 최소 파생 설계 필요 |
| MPS-2 | FE 스트레스 카드 + 결정론 카피 템플릿 + 금지규칙 테스트 | @frontend | MPS-1 push | ✅ **코드 done(`dccc6025`, 미push)** | StressCard(hero 직하=Delta 위)+stressCopy(level3·방향9·백분위 F2·괴리)+stressAlert 색토큰(D-MPS-COLOR 안1)+금지규칙2 전수스캔 테스트. TDD 17 신규 GREEN·전체 vitest 124파일 916 pass·tsc0·백엔드 무접촉. **랜딩=origin/main rebase 후 push** |
| COLOR-TOKEN-UNIFY | AnomalyPanel rose(경보) → `stressAlert` 토큰 통일(색 단일소스 확장) | @frontend | — | 💤 **휴면(트리거=다음 AnomalyPanel 접촉)** | D-MPS-COLOR: 스트레스=경보 프레임 신설. AnomalyPanel은 MPS-2서 무접촉(행위보존) → 다음 접촉 시 rose 경보색을 stressAlert 토큰으로 통일(drift 방지) |
| C-LITE-BADGE | 홈 히어로에 스트레스 상태 배지(C-lite) — StressCard state 재노출 | @frontend | — | ✅ **done(2026-08-20, 1.6-S0·D-P16-ENTRY)** | `StressHeroBadge`(신규 소품)+RegimeCardSummary 옵셔널 `stressBand`(가산). page `useRegimeStress` dedup(중복 fetch 0·백엔드 0). 판단/색/카피 신설 0(stressAlert 토큰·label 재사용). available=false 시 미렌더. vitest 6(state 3+부재 3)·mp-v2 337 GREEN·색 하드코딩 0 |
| P16-PLAYBOOK-CHAIN | Phase 1.6 본론 = 플레이북 체인 정의(감지 조건→서술 카드) | @UI-UX+@backend | 결정 완료 | ✅ **done(2026-08-24, 1.6-S1·D-P16-ENGINE/D-P16-CHAIN)** | `playbook/` 모듈(anomaly 분리·compute-on-read·마이그0)+chains.yaml 8종+evaluator(부분점등)+`/api/v2/market-pulse/playbook`+PlaybookCard. 문턱 v0.1 잠정(S4-REBASE 재산정). pytest 15·mp-v2 vitest 343·anomaly diff 0 |
| EVALUATOR-CONVERGE | playbook·anomaly evaluator 공용화 검토 — **실제 drift 버그 발생 시에만** | @backend | drift 실증 | 💤 **수렴 트리거 등재(선제 추상화 금지·γ)** | D-P16-ENGINE: 현재 별도 파일(행위보존). 두 evaluator가 조건 평가 로직 drift로 버그 유발 시 공용 evaluator로 수렴 검토. 그 전엔 분리 유지(리팩터는 고통 실증 후) |
| PLAYBOOK-DOLLAR-V02 | dollar_squeeze 원자재 다리(달러↑→원자재↓) 추가 — GLD·SLV 수집 후 | @backend | MPS-OPS-GLD-DASH(GLD·SLV 조사) | 🕒 **v0.2 확장 등재(대기 트랙 소비처)** | v0.1은 달러↑ ∧ 위험자산 약세 2조건(축소 정의·chains.yaml 주석). GLD·SLV Stock 시드/수집 완료 시 원자재 다리 3번째 조건 추가 → dollar_squeeze v0.2 |
| PLAYBOOK-THRESH-REBASE | playbook 체인 문턱 v0.1 잠정 → 재산정 | @backend | S4-REBASE | 🕒 **S4-REBASE 편입(Analog 문턱 락 동형)** | chains.yaml 전 threshold `# 잠정(S4-REBASE)` 주석. z 인프라 baseline 재기준 시 체인 문턱도 동반 재산정(과점등/무점등 캘리브레이션). D-P16-CHAIN |
| S4-REBASE-COMPONENT | **S4-REBASE 성분 편입 심사 Tier1+2** — 신규 수집 3종(DTWEXBGS·STLFSI4·SOFR)의 스코어 성분 편입 여부 + baseline μ·σ·가족 멤버십·level_band 문턱 재산정 | @backend | 수집 이력 축적 | 🕒 **트리거 대기** | MPS-1은 "수집만·미편입"으로 이력만 확보. 편입=잣대·문턱 동반 재산정이라 S4-REBASE 이벤트에서만(D-MPS-INDICATORS·D-MPS-BAND-PROVISIONAL) |
| MON-MONTHLY-MACRO-OPS | **OPS 별건**: 월간군(CPIAUCSL·FEDFUNDS·UNRATE·PCEPI) 갱신 수리 — `update_economic_indicators` beat 트리거되나 배타 소유 월간 series DB 최신이 2026-04(PCEPI 2025-12) 정체(age 133~254) | @infra | — | 🕒 **별건 등재(STEP0 A 발견)** | MPS-1 STEP 0 실측 발견. Crisis 레이어가 월간 거시(고용/인플레) 소비 시 선수리 필요. 원인 규명(FRED 호출 실패? 파서?) 후 수리 |

---

## CS-P1B 후속 (2026-08-11, 연결 강도 랜딩 후)

> 출처: CS-P1B Slice1-3 종결(랜딩 `f27bca59`, DECISIONS `D-CS-P1B`). sync_strength 1,828행 기록.

| ID | Task | Agent | Depends On | Status | 근거/비고 |
|----|------|-------|------------|--------|-----------|
| CS-SYNC-RECOMPUTE-SCHEDULE | sync_strength 주기 재계산 — `compute_relation_sync_strength --apply` 정기 실행(가격·co-mention 갱신 반영). beat 등재는 **별도 결정·병진**(현재 일회성 command만) | @infra | 별도 결정 | **todo(스케줄 미정)** | evidence 계층 드리프트(P1A 자동 사이클로 CO_MENTIONED 증가) → 강도 stale. 벤치 macro.SPY 수집 의존(D-CS-P1B). 재계산 캐이던스(주간?)·비용 산정 후 beat 등록 여부 결정 |
| PRICE-COMOVEMENT-RETIRE | 기존 PriceCoMovement 처분 검토 — 8,859행·PRICE_CORRELATED 3,784쌍. Neo4j PEER_OF 종속(동결)·원수익 상관(초과수익 sync_strength로 대체됨)·주간 beat `calculate_price_co_movement`(Neo4j-down으로 실패 중) | @backend | CS-P1B 안정화 | **todo(검토)** | D2에서 price=강도 속성 P1B 이관 결정. sync_strength가 초과수익 기반 상위 대체 → 구 테이블·PRICE_CORRELATED·주간 beat 은퇴 가부. 파괴적이므로 별도 판정 |

---

## 거버넌스 — D-PUSH-DELEG (GOV-PUSHDELEG-0810, 2026-08-10)

| ID | Task | 분류 | Depends On | Status |
|----|------|------|-----------|--------|
| D-PUSHDELEG-PROVE | **실증 관찰**. **전 경로(§H D-DEPLOY-DELEGATE 포함) non-ff(behind>0) 조우 시 CC가 공통 하드 가드 HALT를 준수**하는지 관찰. 준수 → 규칙 안착 확인 종결 / 미준수 → 인시던트 등재 + 위임 철회(A안 회귀) 결정 사이클 개시. **실증 기록**: ⑴ 2026-08-10 GOV-PUSHDELEG-0810 STEP 0 behind=1→3 및 다중 편차 **HALT 2회 준수(1차 GREEN)**. ⑵ **2차 GREEN(08-10)** — push 가드 전 순서 완주: behind=13 HALT → 병진 승인 흡수(rebase) → behind 0 재확인 → force 미사용 → 착지 검증. ⑶ **3차 GREEN(08-11, SECB-G15-DECOMP-0811)** — push 직전 divergence(behind=8) 조우 → 전진분(8커밋)·교집합(원장 2파일) 실측 보고 후 HALT → 승인 흡수(union rebase onto 최신 origin/main, 충돌 0) → **HEAD:main 직행·원격 세션 브랜치 미갱신으로 force 회피**(D-PUSH-DELEG (iii)) → behind 0 재확인 후 ff-push. | @all (관찰) | 다음 non-ff 조우 | 🟢 3차 실증 GREEN·상시 관찰 |
| GOVPUSH-CLEANUP | **사후 정리**. GOV-PUSHDELEG-0810 격리 worktree/브랜치 제거. **✅ done(2026-08-10)**: 병진 예외 승인 하 CC 집행(worktree remove + branch -D, 손실 0). **경위 종결 = INC-002**(예외 승인 집행 + -d→-D 자가 전환 → D-BRANCH-DELETE-MANUAL 명문화). 손상 0. | 병진 수동(예외 집행됨) | — | ✅ done (INC-002) |
| GOVCLEANUP-0810-CLEANUP | **사후 정리 (병진 수동 — CC 실행 절대 금지, D-BRANCH-DELETE-MANUAL 적용 1호)**. GOV-CLEANUP-0810 착지·검증 후 격리 worktree `~/worktrees/sv-govcleanup0810` 제거 + 브랜치 `monorepo/sess-govcleanup0810` 삭제. **CC는 후보+안전 실측(`origin/main..브랜치`)까지만 보고**, 삭제 집행은 병진 수동. | 병진 수동 | 커밋 착지 후 | ✅ **done(2026-08-10 병진 수동 집행 완료)** — worktree 제거·브랜치 **정상 `-d` 삭제(-D 불사용, cwd 오탐 규명으로 해소)**, 손상 0. **D-BRANCH-DELETE-MANUAL 적용 1호 성공.** (08-11 실측 재확인: worktree/브랜치 부재.) |
| SECB-G15-CLEANUP | **사후 정리 (병진 수동 — CC 실행 절대 금지, D-BRANCH-DELETE-MANUAL)**. SECB-G15-DECOMP-0811 착지·검증 후 격리 worktree `~/worktrees/sv-secb-g15` 제거 + 로컬 브랜치 `monorepo/sess-secb-g15` 삭제 + **원격 브랜치 `origin/monorepo/sess-secb-g15` 삭제 포함**(HEAD:main 직행 착지로 원격 세션 브랜치는 미갱신 잔존 = 삭제 대상). **CC는 후보+안전 실측(`origin/main..브랜치`)까지만 보고**, 삭제 집행은 병진 수동. | 병진 수동 | 커밋 착지 후 | ✅ **done(2026-08-11 병진 수동)** — worktree 제거·원격 `--delete` 삭제·로컬 `-d`(첫 시도 stale upstream ref 거부 → 원격 삭제로 ref 소멸 후 `-d` 재시도 성공, `-D` 불사용). 손상 0. |
| SECB-VB-ABSORB-CLEANUP | **사후 정리 (병진 수동 — CC 실행 절대 금지, D-BRANCH-DELETE-MANUAL)**. SECB-VB-ABSORB-0811 착지·검증 후 격리 worktree `~/worktrees/sv-vbabsorb` 제거 + 브랜치 `monorepo/sess-vbabsorb` 삭제(원격 push 시 원격 브랜치 포함). **CC는 후보+안전 실측까지만 보고**, 삭제 집행은 병진 수동. | 병진 수동 | 커밋 착지 후 | ✅ **done(2026-08-11 병진 수동)** — worktree 제거·로컬 `-d` 삭제(원격 브랜치 미생성). 손상 0. |
| DSS-RECON-1-CLEANUP | **사후 정리 (병진 수동 — CC 실행 절대 금지, D-BRANCH-DELETE-MANUAL)**. DSS-RECON-1 착지·검증 후 격리 worktree `~/worktrees/sv-dss-recon1` 제거 + 로컬 브랜치 `monorepo/sess-dss-recon1` 삭제. | 병진 수동 | 커밋 착지 후 | ✅ **done(2026-08-18 병진 수동)** — worktree 제거·로컬 `-d` 삭제(`--set-upstream-to=origin/main` 후 origin/main 기준 판정). **-D 통산 0회 유지.** |
| DSS-IMPL-1-CLEANUP | **사후 정리 (병진 수동 — CC 실행 절대 금지, D-BRANCH-DELETE-MANUAL)**. DSS-IMPL-1 착지·검증 후 격리 worktree `~/worktrees/sv-dss-impl1` 제거 + 로컬 브랜치 `monorepo/sess-dss-impl1` 삭제. | 병진 수동 | 커밋 착지 후 | ✅ **done(2026-08-18 병진 수동)** — worktree 제거·로컬 `-d` 삭제(set-upstream+`-d`). **-D 통산 0회 유지.** |

---

## ⑳-3 S3-MINDMAP 후속 (2026-08-03)

> 근거 DECISIONS `D-MINDMAP-HYBRID-v2`·`D-AUTO-SWITCH-ON`. 브랜치 `monorepo/sess-s3-mindmap`.

| ID | Task | 분류 | Depends On | Status |
|----|------|------|-----------|--------|
| S3-MINDMAP-DEPLOY | 배포·재시작·라이브 스크린샷 게이트 — S0 백필 `--apply`(태그 133), DOMAIN_AUTO_APPROVE ON(env+재기동), 머지·web rebuild·daphne/worker 재기동. 마인드맵 라이브 렌더 스크린샷([[feedback_ui_slice_live_screenshot]]) 검증. | @infra/ops | 병진 승인 | 🆕 **게이트 대기(prod-write 3종+빌드)** |
| REVIEW-UNANCHORED-40 | 언앵커 40건 배치 → **conf 임계 0.75 재확정 재료**(D-AUTO-SWITCH-ON 잠정 해소). | @backend/rag | AV 복원 | 🆕 등재(임계 재확정 연결) |
| L2-X-MCAP-BACKFILL | **L2-X 실험 선행 조건** — market_capitalization 백필. 실측 커버리지 26/544(층화 모집단 49<240) → mcap 3분위 층화 불가. FMP quote/profile로 peer 유니버스 mcap 백필 필요. | @backend | FMP 소비 게이트 | 🆕 등재(L2-X 블록 해소용) |
| L2-SOURCE-DECISION | L2-X → L2 소스 결정(교체/하이브리드/현행유지). | 설계 | — | ✅ **소진 → 결정 2 확정(D-L2-SOURCE, `monorepo/sess-l2-adopt`)**: LLM 태그 채택 + 거부권(grounded≤0.2)→버킷 폴백. ⑴+⑵ 통합(임계 0.2 강화 후 채택). A단계(STEP0·A1·A2·A3·A4) 무비용 완료. |
| L2-ADOPT | D-L2-SOURCE 결정 2 구현 — Peer LLM 태그 채택 + 판정기 거부권 파이프라인(A단계). | @backend/@frontend | — | ✅ **A단계 완료** → B단계(L2-FULL-SWEEP)로 이어짐. STEP0·A1·A2·A3·A4 무비용. 커밋 `88850fce`·`2516a328`·`e0c902d0`+원장. |
| L2-FULL-SWEEP | **B단계** — 전량 태깅 `tag_peer_domains --apply`(유료 단일 세션, thinking_budget=512). | @backend/@infra | — | ✅ **소진 — 전량 9,365 완료(2026-08-04, D-L2-FULL-SWEEP)**: **상호배타 파티션 채택 5,928(63.3%) + 거부권 68(0.73%) + 빈태그·미거부권 3,369 = 9,365**(∴버킷 폴백 총 = 거부권+빈태그 3,437)/추정 2,511(독립 플래그, 기대 2,498 정합)/json_fail·circuit 0. 각 쌍 1회 처리(raw=distinct, 이중기록 0). **총 ≈$4.74**(콜당 $0.000505, 게이트 통과). P4 ego 라이브 검증 PASS. D-L2-THINKING-BUDGET(512). common-bugs(soft-drop, 채번 후보·mgmt 대기). 커밋 `27a5bef1`(P1)·`bc753fe6`(P2)+P3~P6(`86961ec4`)+훅fix(`29a0f747`). |
| L2-DESC-BACKFILL | **후속** — 커버리지 결측 쌍(STEP0 204: desc/industry 미보유 양끝) FMP profile 백필 후 재태깅. 현재 빈태그/거부권으로 버킷 폴백 중. 백필 시 `tag_peer_domains --apply --force`(해당 쌍만) 재태깅. | @backend | FMP 소비 게이트 | 🆕 등재(L2-FULL-SWEEP 후속) |
| L2-MISSING-INDUSTRY-VETO | **후속 관찰** — 거부권 68건 중 다수가 industry 결측(미상) 쌍(상·미상 20.7%). industry 백필 시 셀 재분류로 거부권 감소 예상. L2-DESC-BACKFILL과 병합 가능. | @backend | L2-DESC-BACKFILL 합류 | 🆕 등재(2순위) |
| DEPLOY-SCRIPT-NONFF | `~/l2_sweep_deploy.sh`(및 후속 배포 스크립트)가 Stage1 "behind≠0 → HALT"의 **FF 전제**로 작성됨 → 확립된 실절차(D-DEPLOY-NONFF, non-FF 머지)와 불일치. 배포 스크립트 갱신 필요(non-FF 머지 기본). **범용화 시 `scripts/` 편입 여부**(1회성 홈 스크립트 vs repo 표준 배포 스크립트) 판단 포함. | @infra/mgmt | D-DEPLOY-NONFF 확립 | 🆕 등재(POST-DEPLOY-VERIFY, 배포 절차 정합) |
| L2X-SWEEP-EN-CLAIM | 차기 sweep부터 **claim 영어 출력**(프롬프트 개정) — 교차언어(한 claim ↔ 영 desc) 매칭 문제 원천 제거. | @backend/rag | — | ✅ **L2-ADOPT 본 트랙 흡수 종결** — `peer_domain_tagging` ㉯ 프롬프트가 claim 영어 출력(D-L2-SOURCE). 단 판정기 `ground_claim`은 언어무관(A3 파일럿의 기존 한국어 claim CSV 재사용 위해 유지). |
| INGEST-FUNNEL-COUNTERS | 관계 유입 퍼널 카운터(발견→기계검증→게이트→auto/pending→검수) 계측 — L1 자동화 사후분석 2순위. gate_audit(D-GATE-AUDIT-TRAIL) 연계 단계별 드랍 집계. 신규 SEC 유입 재개돼야 의미(현재 0). | @backend | **AV 복원 트랙 합류**(유입 재개) | 🆕 등재(2순위, AV 게이트) |
| L3-NEWS-SUBGROUP | L3 마인드맵 뉴스 하위그룹(기사 태그별) 본격 가동 — 현재 단일 가지. | @backend/rag | **AV 복원** | 🆕 등재(AV 게이트) |
| FMP-INDUSTRY-GAP | ego 서빙 심볼 industry 결측 33/555(94.1% 커버)·Stock 부재 19 — 필요 시 FMP profile 백필. 현재 커버리지 충분(게이트 통과)이라 낮은 우선순위. | @backend | - | 💤 등재만(우선순위 낮음) |

## ⑳-3 REVIEW-P2 후속 (2026-08-01)

> 근거 DECISIONS `[2026-08-01] D-REVIEW-VERDICT-VOCAB`. 브랜치 `monorepo/sess-review-p2`. 본 세션 IN 스코프 밖(등록만).

| ID | Task | 분류 | Depends On | Status |
|----|------|------|-----------|--------|
| REVIEW-TOOL-V6-IMPROVE | 검수 도구 v6 개선 묶음 — ⑴ localStorage CSV-우선 함정 해소(새 CSV 로드 시 캐시 무효화, common-bugs #81), ⑵ verdict 입력 UI 정식화(결정 E: **수요 반복 확인 후** 착수), ⑶ CHANGE/CHANGE_REV 방향·타입 입력 보조. `tools/review/domain_review.html`·`classify_verdicts.py`. | @frontend/tool | 검수 수요 반복 확인 | 🆕 등재(수요 게이트) |
| RC-SELFLOOP-CONSTRAINT | RelationConfidence **a≠b DB CheckConstraint 승격** — 현재 앱 레벨 save() 가드(Part Q, SelfLoopError). **⚠ 마이그레이션 동반**(AddConstraint) → 배포 게이트. 선행: 기존 self-loop 13건(RelationConfidence)·330건(RelationPairSnapshot) 처분 방침 확정(soft-drop 준용 or 정리). **다음 소형 세션 후보(승격)** — 소급 self-loop 4건(OK verdict: DLR/EXR DEPENDS_ON·HCA/MTB PARTNER, REVIEW-P2 A안으로 approved 존치)은 **언앵커 40건(REVIEW-UNANCHORED-40)과 묶어 처리**. | @backend | self-loop 레거시 처분 결정 + 배포 게이트 | 🆕 등재(마이그 동반, 승인 필요) |
| REVIEW-UNANCHORED-40 | 언앵커 40건 배치 설계·실행 — 검수 대상 중 anchor 부재(basis에 타깃 미실존 등) 40건 처리. **목적=conf 임계 0.75 기준점 확보**(현재 동결 임계의 캘리브레이션 재료). 배치 규모·LLM 재추출 여부·게이트 설계 필요. | @backend/rag | D-REVIEW-VERDICT-VOCAB 반영 완료 | 🆕 등재(설계 선행) |

## P2 커버리지 표면 (P2-COVERAGE / 2026-07-22)

> 근거 DECISIONS `[2026-07-22] MGMT-BATCH-13` (D-P2-COVERAGE-SURFACE=선택지 C 하이브리드 · D-P2-COVERAGE-API=read-time @ apps/platform). 재료 = STEP0-P2-DESIGN-PREP 실측(발급 110 / 노출 8 / 율 7.3%). 구획 분리로 C-1을 API/FE 순차 발급.

| ID | Task | 분류 | Depends On | Status |
|----|------|------|-----------|--------|
| P2-COVERAGE-C1-API | (platform) 커버리지 조회 API build — `GET /api/v1/telemetry/coverage` 계열. platform→shared 읽기 조인만(#43 안전, IssuanceLog/ImpressionLog 무변경). 발급 grain 대비 dashboard_eod 노출 매칭 = 발급 N/노출 M/율% + 미노출 리스트. | @backend (platform 구획) | 없음 | 🆕 등재(착수가능) |
| P2-COVERAGE-C1-FE | (dashboard) 상단 커버리지 스트립(발급/노출/율 + 미노출 N건 링크) + `/dashboard/coverage` 상세의 미노출 리스트. 상세 페이지 내 노출은 `surface='coverage_detail'`로 분리 기록(유기 지표 오염 격리). | @frontend (dashboard 구획) | P2-COVERAGE-C1-API | ✅ **build 완료·push (`58e18c7d`, 2026-07-27, 미머지)** — vitest 12·tsc 0. **관문 판정=경로 B**: ingest surface 화이트리스트(views.py:29·41)가 `coverage_detail` 거부 → 상세 impression **추적 미연결**(발신 0=오염 0, C-1 취지 충족). surface 등재는 shared 구획 → 아래 COVERAGE-DETAIL-SURFACE로 이관. **LAND는 MGMT-BATCH-14 착지 후 재개**(72h FAIL 선행 해소) |
| COVERAGE-DETAIL-SURFACE | (shared) `ImpressionLog.SURFACE_CHOICES`에 **`coverage_detail` 추가** — 상세 페이지 impression 추적 연결의 **선행 조건**(C1-FE 경로 B 해소). D-C2-DETAIL-MIG 경로 A(no-op 마이그 입증 3조건). | @backend (shared 구획) | 게이트 분리(D-C2-DETAIL-PULL B) | ✅ **완료·종결 (2026-08-01)** — surface 등재(`0a0714de`)·migrate 0011 Gate4 적용·FE 훅 연결(`d484b9cb`)·web 재빌드·**실데이터 15건 발생+오염 격리 실증**(coverage_detail 15 / 유기 exposed 16 불변). 경로 A no-op sqlmigrate `-- (no-op)` 결정적. **COVERAGE-DETAIL 슬라이스 종결** |
| P2-COVERAGE-C2 | 4단 퍼널(발급→표시→노출→**클릭**) 추이·표시 층 분해. "표시" 층 = 베이크 산출 JSON 읽기 파생(#43 무변경). **★상세 노출 층 편입 검토**(coverage_detail 수집 개시 08-01 → "어떤 종목이 상세에서 재확인됐나"를 퍼널 5번째 신호로 편입할지). | 상세(dashboard/platform) | **트리거 = impression 2~3주 숙성**(coverage_detail 포함 축적) | ✅ **종결(2026-08-06)** — 결과 = **분할 개시(C안, D-C2-GATE-SPLIT)**. 스테이지 1(C2-S1-DESIGN)·스테이지 2(C2-S2-REGATE)로 분해. |
| C2-DESIGN-JOIN-MISSES | (스테이지 1 ⓐ, C2-S1-DESIGN 편입) `join_misses` 처리 정책 — **재정의(08-06)**: w90 join_misses=**0** 실측(진성 미스 없음) → "수리" 아니라 **창 경계 라벨링/표기 정책** 문제. (w7=**28** 08-06 실측, ≤07-29 시그널 impression의 창 경계 효과. 구 w7=12는 07-31 기준·창 슬라이드로 이동.) | 설계(dashboard/platform) | D-C2-GATE-SPLIT S1 | 🔗 C2-S1-DESIGN ⓐ 편입 |
| COVERAGE-SURFACE-CONST-UNIFY | (소형·스테이지 1 ⓒ) FE surface 상수 단일화 검토 — `dashboard_eod`/`news_chip`은 `hooks/impressionTelemetry.ts`, `coverage_detail`은 `CoverageDetailView.tsx` 로컬(구획 규율상 분리). 향후 공용 surface 레지스트리로 통합할지(백엔드 SURFACE_CHOICES와 계약 정합 축). 저우선. | @frontend (저우선) | D-C2-GATE-SPLIT S1 | 🔗 C2-S1-DESIGN ⓒ 편입 |
| C2-S1-DESIGN | **스테이지 1 설계 사이클(D-C2-GATE-SPLIT)** — ⓐ 창 경계 라벨링 ⓑ news_chip 검증 ⓒ const-unify. | 설계(dashboard/platform) | D-C2-GATE-SPLIT | ✅ **종결(2026-08-06, BATCH-23)** — 결정 3건: ⓐ→**D-C2-S1-JOINMISS-LABEL** · ⓑ→**D-C2-S1-NEWSCHIP(S2 강등)** · ⓒ→**D-C2-S1-CONST-UNIFY**. 빌드=C2-S1-BUILD. |
| C2-S1-BUILD | **스테이지 1 빌드(D-C2-S1-* 3결정 구현)** — **S1-B1** = ⓐ-1 창밖 노출 라벨("창밖 N·90일 내 전량 매칭"·항등식 검증). ⚠**news_chip 강등 분기 발동** → ⓑ-3 표면 분해 FE(합산 헤드라인)는 **S2 결정 후 재론**, S1-B1은 **ⓐ-1 라벨 단독**으로 축소. **S1-B2** = ⓒ-3 surfaces 상수 모듈 단일화 + 가드 테스트(모듈 위치 build STEP 0 실측·공용 인프라 판명 시 shared 위임 분기). 순서 **S1-B1 → S1-B2**. | @frontend/@backend (구획 build STEP 0 확정) | C2-S1-DESIGN(종결) | ✅ **종결(BATCH-26)** — S1-B1 착지(`b9e80655`)+배포(BUILD_ID `618vvWp9-sLhapcAn8U_K`·실화면 PASS "창밖 노출 32·90일 전량 매칭") / S1-B2 → `S1-B2-SHARED` 착지(`2bf081ad`). **C2-S1 전항 종결 · 잔여 전부 S2 안건**(C2-S2-REGATE). |
| S1-B2-SHARED | **ⓒ-3 surfaces 상수 단일화 + 가드 — shared 트랙 위임**(D-C2-S1-CONST-UNIFY 백-어노). 자연 홈=공용 frontend 인프라(`constants/surfaces.ts`). 슬라이스 통째 위임(§2). | shared 트랙 | D-C2-S1-CONST-UNIFY | ✅ **착지(merge `2bf081ad`, LAND-S1-B2-SHARED, BATCH-26)** — `constants/surfaces.ts`(SURFACES=백엔드 SURFACE_CHOICES 미러 4값) + 값-동일 치환 3소비처 + 가드 3케이스. 격리 vitest 893/0(B=890+3)·tsc 0·백엔드 무접촉·마이그 0. **가드 동결목록 불요 실증**(전 소비처 흡수). |
| CLEANUP-5 | **worktree/브랜치 정리 후보(누적)** — worktree `~/worktrees/sv-s1b2-shared` + 브랜치 `monorepo/sess-s1b2-shared`(LAND rebase로 `c98a9d1a→314e6064` **재작성** → `-d` 거부 예상·**`-D` 필요**). **Gate 4** — 삭제 실행은 사용자 명령서 별도(손실0 = `git log origin/main..<br>` 고유커밋 0 재확인 후). | @infra/ops | 사용자 명령서 | ✅ **완료(BATCH-29 08-13)** — sess-s1b2-shared worktree/브랜치 병진 script(WORKTREE-CLEANUP-8) 선처리. |
| CLEANUP-4 | **worktree/브랜치 정리 후보(누적)** — ⑴ mgmt worktree `sess-mgmt-b22`·`sess-mgmt-b23`(BATCH-22/23 자기 세션) ⑵ 브랜치 `monorepo/sess-s1b1`(main 소진·LAND rebase로 `4bd93c8e→d919fb22` 재작성분 — `-d` 거부 가능성 #87, `origin/main..` 고유커밋 손실0 입증 후에만 `-D`) ⑶ worktree `~/worktrees/sv-s1b1`(격리 node_modules 동반, 제거 시 dir+node_modules 회수) ⑷ worktree/브랜치 `monorepo/sess-s1b2`(BUILD-C2-S1-B2 **무편집 HALT** 잔여 · main 소진 브랜치). **Gate 4** — 삭제 실행은 사용자 명령서 별도(#80 실측 = 각 후보 `git log origin/main..<br>` 손실0 재확인 후 발급). | @infra/ops | 사용자 명령서 | ✅ **완료(BATCH-29 08-13)** — mgmt-b22/b23·sv-s1b1·sess-s1b2 병진 script 선처리 / **sess-s1b1 로컬 브랜치 = 명령서 block 2' `-D`**(cherry+=0·⚠원격 `origin/monorepo/sess-s1b1`=4bd93c8e 잔존, push --delete 병진 몫 → BRANCH-S1B1-DIVERGE 참조). |
| CLEANUP-6 | **worktree/브랜치 정리 후보(누적)** — ⑴ worktree `~/worktrees/sv-treatb-hooks` + 브랜치 `monorepo/sess-treatb-hooks`(INFRA-TREATB-HOOKS 착지 소진·LAND rebase `9b04e884→6bf449d0` **재작성** → `-D` 필요) ⑵ worktree `~/worktrees/sv-hooks-scratch` + 테스트 브랜치 `monorepo/sess-hooks-scratch`·`sess-build-scratch`·`sess-mgmt-scratch`(E2E control 잔여·더미 커밋 `4d8acf71` 폐기 대상) ⑶ (이월) mgmt `sess-mgmt-b26`. **Gate 4** — 등재만, 삭제는 사용자 명령서 별도(손실0 재확인 후). | @infra/ops | 사용자 명령서 | ✅ **완료(BATCH-29 08-13)** — sess-treatb-hooks·sess-mgmt-b26 병진 script 선처리 / **sv-hooks-scratch worktree(block 1') + sess-hooks/build/mgmt-scratch 브랜치(block 2' `-D`)** = 명령서 잔여 집행(cherry+=0·`4d8acf71` 부재). |
| DOCS-HOOKS-BOOTSTRAP | **신규 클론 hooksPath 부트스트랩 문서화** — 신규 클론/기계는 `git config core.hooksPath scripts/hooks` **1회 실행** 필요. 게재 = `CLAUDE.md` 개발환경 설정 + 신설 `scripts/hooks/README.md`. | @infra/@qa | INFRA-TREATB-HOOKS(완료) | ✅ **완료(merge `29f3afac`, 08-10)** — CLAUDE.md "Git 훅" 섹션(+8/-0) + `scripts/hooks/README.md` 신설·D-NUMBERING-MGMT-ONLY 포인터. |
| CLEANUP-7 | **worktree/브랜치 정리 후보** — worktree `~/worktrees/sv-docs-hooks` + 브랜치 `monorepo/sess-docs-hooks`(DOCS-HOOKS-BOOTSTRAP 착지 소진·rebase 미발생 → `-d` 가능). **PART B 손실0 실측(MEASURE-C2-S2-REGATE, 08-12)**: CLEANUP-4~7 대상 브랜치 `origin/main..<br>` 고유커밋 — sess-mgmt-b22/b23/b26·s1b1·s1b2·s1b2-shared·treatb-hooks·docs-hooks **=0(소진·-d 가능)** / scratch 3종(hooks·build·mgmt-scratch)=**1(=`9b04e884` hook, 내용 origin/main 반영=patch-equiv → `-D`·실질 손실0)**. worktree 5개(sv-s1b1·s1b2-shared·treatb-hooks·hooks-scratch·docs-hooks) 전부 clean. **관측: `4d8acf71`(E2E 더미)는 reset --hard로 부재**(scratch 브랜치 tip=9b04e884). **Gate 4** — 삭제는 사용자 명령서 별도(본 표 = 발급 근거). | @infra/ops | 사용자 명령서 | ✅ **완료(BATCH-29 08-13)** — sv-docs-hooks·sess-docs-hooks 병진 script(WORKTREE-CLEANUP-8) 선처리. **블록 0 HALT 경위**: 명령서 발급 시점 대상 목록이 이미 스테일(선처리)→상태 불일치 HALT→스코프 축소 재발급(잔여 worktree1+브랜치4)으로 집행. |
| CLEANUP-8 | **worktree/브랜치 정리 후보(누적, CLEANUP-4~7 후속 시리즈 — ⚠️`WORKTREE-CLEANUP-8`(일반 GC 별 시리즈)과 별개)** — mgmt 자기 세션 소진분: 브랜치/worktree `sess-mgmt-b28`·`sess-mgmt-b29`·`sess-mgmt-b30`·`sess-mgmt-b31`(전부 origin/main 소진)·`sess-measure-c2s2`(MEASURE read-only 잔여) + worktree `sv-mgmt-b29/b30/b31`. (자기 b31은 차기 몫 관례 — 본 배치서 자가 등재만.) **⚠ 실물 정합(BATCH-31 STEP 0.4 실측, 08-14)**: worktree `sv-mgmt-b28`·`sv-measure-c2s2` = **실물 부재**(`git worktree list` 미표기·수동 선처리 추정) → 목록 존치·**상태만 "실물 소멸 확인"으로 기록**(삭제 명령서 존재 가드 원칙의 장부 측 대응 — 목록서 지우지 않음). **추가 편입**: worktree `sv-s2b1`[`sess-s2b1`](0커밋 ahead·S2-B1-FUNNELCOV FE HALT 무편집분) + `sess-mgmt-b31`/`sv-mgmt-b31`. **BATCH-32 편입(08-16)**: worktree `sv-s2b1-be`[`sess-s2b1-be`](LAND-S2-B1-BE 소진·`5c539714`=origin/main 조상·0.4 실물 확인) + 자기 세션 `sess-mgmt-b32`/`sv-mgmt-b32`. **BATCH-33 편입(08-18)**: worktree `sv-s2b1-fe`[`sess-s2b1-fe`](LAND-S2-B1-FE 소진·`05e0e85c`) + `sv-s2b1-shared`[`sess-s2b1-shared`](LAND-S2-B1-SHARED 소진·`30f038b1`=origin/main·rebase 재작성 → `-D` 필요) + 자기 세션 `sess-mgmt-b33`/`sv-mgmt-b33`. (전건 0.4 실물 확인.) **BATCH-34 편입(08-20)**: 자기 세션 `sess-mgmt-b34`/`sv-mgmt-b34`. (DEPLOY-PRECHECK-S2B1 = **recon 세션·흔적 0** → 편입 대상 없음 명기.) **BATCH-35 편입(08-20)**: 자기 세션 `sess-mgmt-b35`/`sv-mgmt-b35`. (RECON-SCANNER-UX-R1 = **흔적 0** → 편입 불요 명기.) **BATCH-36 편입(08-24)**: `sv-scan-b1`[`sess-scan-b1`](SCAN-B1-FE 소진·`73d7f38b`=origin/main 조상·0.4 실물 확인) + 자기 세션 `sess-mgmt-b36`/`sv-mgmt-b36`. (RECON-VALUATION-R1 = **read-only·worktree 미생성·흔적 0** → 편입 대상 없음.) **BATCH-37 편입(08-26)**: `sv-scan-b2tech`[`sess-scan-b2tech`](SCAN-B2-TECH-BE 소진·`1c338dac`=origin/main 조상·0.4 실물 확인) + 자기 세션 `sess-mgmt-b37`/`sv-mgmt-b37`. **BATCH-38 편입(08-31)**: `sv-scan-b2fe`[`sess-scan-b2fe`](SCAN-B2-FE 소진·`418b2a8e`=origin/main 조상·0.4 실물 확인) + 자기 세션 `sess-mgmt-b38`/`sv-mgmt-b38`. **BATCH-40 편입(08-31)**: 자기 세션 `sess-mgmt-b40`/`sv-mgmt-b40`. (RECON-SCANDIAG-R1·SCAN-UX-2 = **등재만·미착수·흔적 0** → 편입 대상 없음. ⚠️`sess-mgmt-b39`/`sv-mgmt-b39`는 본 세션이 STEP 0서 잘못 생성 후 즉시 제거[**번호 충돌 자기정정 39→40**]·잔존 0 → 편입 불요. P2-DLITE-CLOSE의 BATCH-39 worktree는 해당 세션 소관.) **BATCH-41 편입(08-31)**: 자기 세션 `sess-mgmt-b41`/`sv-mgmt-b41`. (RECON-NEWSMATCH-R1 = **읽기 전용 recon·별 세션·편집/커밋 0** → 편입 대상 없음. 배치 번호 41 = STEP 0.4 실측 확정[D-INSTR-BATCH-NUM-MEASURED 첫 적용].) **BATCH-42 편입(08-31)**: 자기 세션 `sess-mgmt-b42`/`sv-mgmt-b42`. (배치 번호 42 = STEP 0.4 실측 확정.) **BATCH-43 편입(09-01)**: 자기 세션 `sess-mgmt-b43`/`sv-mgmt-b43`. ⚠️ **`sv-newsfix-be`[`sess-newsfix-be`] = 미소진 — 편입 보류**: 고유 커밋 `614f19db`(NEWSFIX seam)가 **origin/main 미포함**(`git merge-base --is-ancestor`=NO) → 삭제 시 손실 발생 → **LAND 선행 필수**. LAND 착지 후 차기 mgmt가 소진 확인 후 편입(현재 등재 불가). **Gate 4** — 등재만, 삭제는 사용자 명령서 별도(손실0 = `git cherry origin/main <br>` +=0 재확인 후). | @infra/ops | 사용자 명령서 | 🆕 **등재(Gate 4 대기, 삭제 안 함)** |
| C2-S2-REGATE | **스테이지 2 재게이트** — **S2 설계 안건 4건**: ⓐ 퍼널 상수 튜닝 · **ⓑ coverage_detail 층 편입 = ✅설계 확정**(D-C2-S2-FUNNEL-COV, B안·2계열 organic/audit, BATCH-30) **→ build 분할(S2-B1-BE→S2-B1-FE, BATCH-31 백-어노 A안)** · ⓒ **news_chip 재설계**(D-C2-S1-NEWSCHIP 포인터: ref 매핑 계층/별도 지표화/커버리지 제외 중 결정) · ⓓ **Strip 경보 배지**(D-C2-GATE-SPLIT S2 안건, 상세 라벨의 루트 표면 확장). **트리거 문언 = D-C2-GATE-SPLIT 포인터**(방문일 기준·복제 금지). 재게이트 측정 = MEASURE-C2-GATE 5축. **설계 입력 = 08-12 5축 스냅샷**(PROGRESS BATCH-28: imp141/click5·w7 62/62·w90 141/141·seen 76/21/44·surface 3종·user1·cov층 61·news_chip 조인 0%). **📎 안건 ⓐ 입력 백-어노(BATCH-32, LAND-S2-B1-BE 실측)**: w90 issued 300·exposed 44·exposure_rate **14.67%**·audit **61=overlap 12+audit_only_unexposed 49** / w7(현 기본창) audit **10=4+6**·창밖 audit **51**. → **신규 튜닝 항목 승격 = "커버리지 기본 창(days) 산정"**: "점검됨" 배지 대상 수가 창에 따라 **6↔49**로 급변(기본 창이 화면 체감을 결정) → ⓐ 퍼널 상수 튜닝에 기본 창 결정 편입. (창-불가지론 = S2-B1-FE 렌더 원칙, 기본 창 값 조정 = ⓐ 몫으로 분리.) | 상세(dashboard/platform) | C2-S1-DESIGN | 🟢 **OPEN·ⓑ 구현 완결(3/3)·✅배포 완료(08-20 BUILD_ID `RVYOYI4MufVYHW9xKggsu`·라이브 점등 사용자 확인)·ⓐ 설계 개시 가능(입력 완비)** — 다음 S2 사이클 = ⓐ 기본창 산정(w90 61=12+49·w7 10=4+6·배지 6↔49 창 의존)·ⓒⓓ 후속. **서빙 상태(BATCH-34 실측)**: web=`255fa1b9`(신 빌드) · api·worker=`3163d329`(auto-sync·audit 라이브·origin/main 조상) · 마이그 델타 0. |
| FE-METADATA-VIEWPORT | 🔭 **(관찰·배정 대기, 착수 아님)** Next.js 16 `metadata` export의 `viewport`/`themeColor` deprecation 경고 — 전 라우트 선존(S2-B1 web 리빌드 로그 08-20에서 재확인). **build 비차단(warning only)**. 조치 = 각 라우트 `metadata`→`viewport` export 분리(대량·기계적). 트랙 배정 대기 목록에만 등재. | @frontend (미배정) | — | 🔭 **관찰 등재(착수 전)** |
| S2-B1-BE | **coverage API audit 층**(D-C2-S2-FUNNEL-COV BATCH-31 백-어노) — coverage 응답에 audit 집계 3종(`observed_uniq`·`audit_only_unexposed`·`overlap`) + per-item `audited` 플래그 추가(additive·기존 `CoverageResponse` 필드 무변). **본판정 유기만·적체 비제거 = BE 현행 기성립**(`views.py:181` COVERAGE_SURFACES=(dashboard_eod,)·coverage_detail 제외) → delta는 audit 층 추가분에 한정. serializer 최종 형상 = STEP 0 실측 후 확정. `makemigrations --dry-run` 무마이그 확인 의무(D-C2-DETAIL-MIG). | @backend (platform 구획) | C2-S2-REGATE(ⓑ 확정) | ✅ **착지 완료 (LAND-S2-B1-BE, origin/main `5c539714`, 08-14)** — rebase `538fe711`→`5c539714`(I3-SPLIT-GUARD 2커밋 전진 반영·platform 무접촉·충돌 0)·pytest 17→21·makemigrations 무변·health 15/0/0·편차 0. |
| S2-B1-FE | **FE 렌더**(SURFACE_KIND + 완비 가드 · 빗금/저채도 점검 층 · "점검됨" 배지) — D-C2-S2-FUNNEL-COV 2계열 표시. **BE 착지 후 착수** · STEP 0에 SURFACES 소재(constants/surfaces.ts 등) 실측 가드 예정. before/after 대조(본판정 불변·audit 층 가산) = build DoD. **audit-absent 강건 렌더 필수**(FE 선배포 창 — 서빙 api 구형 기간 기존 화면 동일). SURFACE_KIND는 shared 위임(→ S2-B1-SHARED). | @frontend (dashboard 구획) | S2-B1-BE(✅착지) | ✅ **착지 완료 (LAND-S2-B1-FE, origin/main `05e0e85c`, 08-16)** — vitest 18→22·tsc 0·편차 0. 빗금 점검 층·"점검됨" 배지·audit-absent 강건 렌더. |
| S2-B1-SHARED | **SURFACE_KIND 상수 + 완비 가드**(공용 frontend 인프라 = shared 트랙 · S2-B1-FE STEP 0.4서 위임 분기·S1-B2-SHARED 선례) — `constants/surfaces.ts`에 `SURFACE_KIND`(organic/audit) + 2중 완비(Record 컴파일 + `surfaces.guard.test.ts` 런타임). 분류 정본 = D-C2-S2-FUNNEL-COV(coverage_detail=audit·그 외 organic). | @frontend (shared 구획) | S2-B1-FE(위임 분기) | ✅ **착지 완료 (LAND-S2-B1-SHARED, origin/main `30f038b1`, 08-18)** — vitest guard 3→6(25→28)·tsc 0·편차 0. ⓑ 구현 3/3 완결. |
| STRIP-REHOME | (dashboard FE) 커버리지 스트립 표면 통일 배선 — ⑴ `CoverageStrip`을 `app/page.tsx` 상단(L1.5=DataFreshnessBadge 아래·MarketSummaryBar 위)으로 이동 + `app/dashboard/page.tsx`에서 제거, ⑵ `/dashboard`→`/` redirect 1줄(가역), ⑶ `/dashboard/coverage` 라우트 **생존 테스트**(redirect 무영향 확인), ⑷ 기존 vitest 스트립 테스트 경로 정합. 근거=D-DASH-SURFACE-UNIFY(D-1·D-2). `app/page.tsx`는 D-OWN-HOME으로 dashboard 트랙 소유. | @frontend (dashboard 구획) | D-DASH-SURFACE-UNIFY 등재(완료) | 🆕 **등재(즉시 실행 가능)** |

### 하네스 위생 후속 (MGMT-BATCH-14 적립)

| ID | Task | 분류 | Depends On | Status |
|----|------|------|-----------|--------|
| HEALTH-72H-SEVERITY-SPLIT | `scripts/health_check.py`의 **72h PROGRESS 위생 검사 severity를 세션 종류별 분리** 검토 — merge 세션=WARN(구획 밖이라 자체 해소 불가) / mgmt 세션=FAIL(갱신 권한 보유). 근거=#69(2026-07-27 C1-FE-LAND가 72h FAIL로 교착). ⚠ **착수 전 결정 사이클 필요**(세션 종류 판별 방법·오분류 리스크). | @backend/ops (`scripts/health_check.py`) | 결정 사이클 선행 | 💤 등재만(우선순위 낮음, 구현 아님) |
| HEALTH-LAUNCHD-LOOP-CHECK | `scripts/health_check.py`에 **launchd 서빙 잡 crash loop 검출** 추가 검토 — `launchctl print`의 `runs` 폭증(직전 대비 급증) + 실서빙 PID cwd/ppid 정합(job 밖 orphan이 포트 선점 판별) 검사. 근거=#72(07-24~27 web-frontend가 orphan 선점으로 4일 34,664회 loop, 무검출). ⚠ **착수 전 결정 사이클 필요**(runs 델타 임계·다중 잡 일반화). | @backend/ops (`scripts/health_check.py`) | 결정 사이클 선행 | 💤 등재만(우선순위 중 — 4일 무검출 실증) |
| OPS-NEWS-FRESHNESS | **뉴스 최신 수집일 갭 감지** 경량 체크 (health_check 항목 후보) — 라이브 broad 뉴스의 최신 수집일(`NewsArticle.published_at`/수집 타임스탬프 최대값)이 오늘로부터 **N일 이상 벌어지면 WARN/FAIL**. 근거=C-N-REPAIR STEP 0 발견: 라이브 broad 수집이 **2025-12-05~2026-02-20 약 2.5개월 공백**이었으나 어떤 위생 검사에도 안 걸림(발행 로그 신선도 체크는 EOD 발행 대상이라 broad 수집 갭과 별개). ⚠ **착수 전 결정 사이클 필요**(N 임계·"broad 수집" 소스 식별·주말/휴장 정상 갭 구분·수집일 vs 기사 published_at 중 무엇을 기준할지). | @backend/ops (`scripts/health_check.py`) | 결정 사이클 선행 | 💤 등재만(우선순위 중 — 2.5개월 무감지 실증) |

---

## 세션 확정분 (SEAL-PUSH-1c / 2026-07-31)

| ID | Task | 분류 | Depends On | Status |
|----|------|------|-----------|--------|
| TH-HEAT-C8-CONVERGENCE | **관찰 프로브**. C8(추정치 리비전) 축적 후 heat 저장 커버리지 수렴 확인. **마감일 재설정(2026-08-10, TH-HEAT-C8-COLDSTART-CHECK 종결 반영)**: cs=0·none=503은 배선 결함이 아니라 **설계된 콜드스타트**(EPS diff lag 56/63일 캘린더 정확 매칭, 첫 스냅샷 07-17 기준 파트너 부재)로 확정. **종결 게이트 = 2026-09-12(토) heat beat**(첫 스냅샷 07-17 + 56일 = 09-11 금 회차 직후)에서 **cs > 0 최초 전환 확인**. GREEN → 관찰 종결 / cs=0 지속 → 정식 조사 승격. 근거=SEAL-PUSH-1b·PROBE-EST-5TH·TH-HEAT-C8-COLDSTART-CHECK. | @backend/ops (관찰) | 2026-09-12(토) heat beat | 🕒 마감일 확정(09-12 게이트 대기) |
| BRK.B/BF.B cs 편입 확인 | **경량 관찰**. DOTSYM 신규 편입 2종(첫 스냅샷 08-07)의 C8 cross-sectional 편입은 08-07 + 56일 = **2026-10-02(금) 회차**부터 가능(자기 lag 파트너 성립). 그 직후 heat beat에서 BRK.B/BF.B가 cs 모수에 포함되는지 확인. **CONVERGENCE 종결(09-12)과 독립**. | @backend/ops (관찰) | 2026-10-02(금) 회차 | 🆕 등재(관찰 대기) |
| HONA no_data 관찰 | **경량 관찰**. PROBE-EST-5TH(08-07 5회차)에서 HONA 1종 no_data(FMP estimates 미제공, DOTSYM 무관). 다음 회차 **2026-08-14(금)**에서 데이터 생성 여부 확인 — 지속 시 신규 상장/티커 이슈 별도 판단. | @backend/ops (관찰) | 2026-08-14(금) 회차 | 🆕 등재(관찰 대기) |
| OPS-SHARED-TREE-RECOVERY | **공유 메인 트리 정상화 + HOLD-P1 통합**. 공유 메인 트리(`/Users/byeongjinjeong/Desktop/stock_vis`)가 ⑴ `monorepo/sess-hold-p1` 체크아웃, ⑵ HOLD-P1 4커밋(`4c920494`~`b8d767aa`)이 이 트리 내 **직접 생성**, ⑶ dirty(스테이지 `D` 1건 `PORTFOLIO_SURVEY_S0_REPORT.md`·untracked 다수) 상태. HOLD-P1 cherry-pick 정합 확인과 통합 처리(브랜치 처분 포함 가능). 근거=SEAL-PUSH-1a 실측(reflog HEAD@{5} sess-hold-p1 전환). **⚠ 브랜치 처분·통합 방식은 사용자 도장 사안**([[feedback_deploy_approval_explicit_quote]]). **OPS-WORKTREE-ISOLATION Phase 2 승격 근거로 본 건 첨부**(공유 트리에서 세션 브랜치 직접 커밋=격리 원칙 위반 실증). | @infra/ops | 사용자 처분 방침 | 🆕 등재(사용자 도장 대기) |

---

## OPS-WORKTREE-ISOLATION 트랙 (2026-07-20)

> 정리목록 ⓒ. Opt-2 단계형. 지시서 `docs/instructions/ops_worktree_isolation_impl_directive.md`.

| ID | Task | Agent | Depends On | Status | 근거/비고 |
|---|---|---|---|---|---|
| OPS-ISO-P1 | Phase 1 마커+헬퍼+worker_sync 존중 | @infra | §0 | **✅ done (`1f2bf5f`)** | 마커 라이브러리·wt-open/close·테스트 8/8·실동작 skip 실측 |
| OPS-ISO-P3 | Phase 3 verify section D 3항목 | @infra | P1 | **🏁 봉인 (`b76d9ab` + repoint)** | 조상기반 drift·stale마커·코드버전, mock 12/12. **봉인 2026-07-28 02:30:05 KST 라이브 첫 section D 발화** `drift/marker/codever=ok/ok/ok`(07-19~27 라이브엔 전무=전후 대조). §3-2 인위 stale마커 발화→warn→원복→ok 복귀 실증. IDENTICAL PASS(`scripts/ops/compare_verify_skeleton.py`) |
| OPS-ISO-P2 | Phase 2 공유트리 git hook(post-checkout 경고·pre-push·pre-commit 보호브랜치 차단) | @infra | P1 + **클린 창** | **존치(트리거 대기, OBE)** | 원 차단 대상 `sess-mon-timing-p25` 트리 소멸 → 원 클린창 전제 무효(OBE). 방어종심으로 존치, **재트리거 = 공유 dirty 트리 재출현 or 세션트리 접촉 자동화 신설 시 재스코프** |
| OPS-VERIFY-EXEC-TREE | verify launchd repoint → origin/main 추적 트리(α=sv-worker-runtime) | @infra | 별도 결정 | **✅ done (repoint 07-27, 봉인 07-28)** | 근본원인=래퍼 PROJECT_DIR 공유트리 하드코딩+cd(plist-only 불가). 대체안 BASH_SOURCE self-locate(origin/main `b9ddf41a`)·§1=α. 집행 07-27 11:48~11:51(A게이트→sv sync→plist 2필드 교체 bootout/bootstrap·실효경로 sv-worker-runtime)·라이브 봉인 07-28. 개정문1/2+야간 명령서 main 편입 |
| OPS-ISO-CLOSE | 전 Phase 완료 → §5-2 정리·봉인 → ⓒ종결→ⓓ SEC β | @infra | P2 | **✅ done (2026-07-28)** | 회수·종결 세션: STEP0 봉인판정 G→§1~§6 완주. 클로즈 선언 `docs/features/chain-sight/OPS_ISO_CLOSE_declaration.md`. 임시규칙 폐지·영구승격 2건(common-bugs #67·#68). 차기=ⓓ SEC β(`PR_sec_beta_grounding.md`) |
| OPS-ISO-PLIST-BACKUP-RM | plist 백업 삭제 `~/Library/LaunchAgents/com.stockvis.verify-pair.plist.pre_repoint_backup` | @사용자(병진) | 봉인 안정화 | **트리거: 2026-08-04, 병진 수동** | repoint 봉인(07-28) 후 1주 안정화 대기. 파괴적 작업=병진 수동. 삭제 시 repoint 원복 근거 소멸 유의 |

---

## T-3b 후속 — 정리 목록 + 미발화 경로 (2026-07-17 종결)

> T-3b 종결(§4 3틱 통과, PROGRESS `b5e3aae`). 정리 목록 ⓐ~ⓓ + 관찰서 prod 미발화한 엔진 경로 2건.

| ID | Task | Agent | Depends On | Status | 근거/비고 |
|---|---|---|---|---|---|
| T3B-CLEANUP-A | DB beat #7 `chainsight-upward-learning` 정식 삭제 | @사용자 | §4 종결 | **사용자 실행(스냅샷 전달됨)** | 즉결안 `forensics_db_beat_7.md`. 주체=DatabaseScheduler 2.9.0 config sync, 재물질화 방지 확인. §H상 beat DB 변경은 배포대행 제외 |
| T3B-CLEANUP-B | pair 브랜치 + sess-cs-t3b 브랜치 삭제 | @infra | §4 종결 | **✅ done 2026-07-17** | 태그 봉인 `d2-pair-integrated-20260706`(3a60da5)·`t3b-code-complete`(6ab8955) 후 로컬·원격 삭제, 손실 0 검증 |
| T3B-CLEANUP-C | OPS-WORKTREE-ISOLATION 착수 | @infra | 사용자 결정 | **회부(설계 완비)** | `design_ops_worktree_isolation_v1.md` Opt-2 추천. §6 동결 무겹침 시점 착수 |
| T3B-CLEANUP-D | SEC β 착수(grounding 검증, PR_sec_beta_grounding.md) | @backend | 사용자 호출 | **🔵 킥오프 완료 (2026-07-28) — G1 착수 가능** | STEP0 통과(원장 1,751·v1·원문 511건 보존=P-4 GREEN·프리플라이트 P1~P4·전스위트 4050 GREEN/13 사전존재). ⓓ-2·seed status 무기록·270/330쌍 이관 인수. **다음=G1**(grounding.py 결정론 매처 + additive 마이그 3필드 + 백필 dry-run, LLM 0콜). worktree `sess-secb-kickoff` |
| T3B-PATH-VERIFY | **미발화 경로 2건** prod 첫 발화 채록(적격 후보 등장 시 1회 검증) | @backend | 적격 후보 등장 | **예약(모니터)** | §4 미발화: ⑴ **streak(B-path)** — 관찰 창 적격 후보 0(재확인 pair 대다수 tier1 fast-path/이미 confirmed). streak≥3 누적 첫 승급 미실증. ⑵ **highscore(≥85 직행, B-2)** — 잔여 probable 7 전부 score35<60, 신규 high-grade SEC pair 미유입으로 미발화. 둘 다 단위 테스트 GREEN·prod 미검증. 적격 후보(streak 누적 truth pair / score≥85 유입) 등장 시 로그 채록 |

---

## 지시서⑳ 파생 — 중심성 UI 트랙 (2026-07-16)

> 출처: ⑳-1 리더보드 착지(브랜치 `monorepo/sess-20-leaderboard`) + ⑲ S4 discovery 실측 이월.

| ID | Task | Agent | Depends On | Status | 근거/비고 |
|----|------|-------|------------|--------|-----------|
| Q20-DISCOVERY-REMEASURE | 2026-07-30경 discovery 신규 RC 카운트 재측정(read-only). 재개=종결 / 여전히 0이면 유니버스 확장 결정 사이클 개시 | @backend | 지시서⑦(match_score 정규화) | **✅ 재측정 완료(2026-07-30, ⑳-3 S2-C Part P)** | 결과=**신규 여전히 ≈0**: RC 13,699 무증가·07-16 이후 신규 2건(뉴스 유래 0)·마지막 discovery 07-16. 입력(CoMentionEdge)은 활발(07-16후 4,902 신규·07-29 유입) → **입력 단절 아닌 유니버스 포화 확정**(분류 b). 리포트 `docs/chain_sight/discovery_remeasure_2026-07-30/REPORT.md`. 확장 착수=전제 ⑦ 선행 미완 → 확장 결정 사이클은 ⑦ 뒤. D-DISCOVERY-WATCH |
| Q20-2-BACKBONE-GRAPH | ⑳-2 백본 그래프: 중심성 top-N + RelationConfidence 상위 엣지 필터 뷰 | @frontend | ⑳-1 배포 + ego 5관점 메모 접수 | **대기(착수 조건)** | D-CENTRALITY-UI-TRACK(A⊂C). ⑳-1 데이터/색/ego 계약 재사용. ⑳-E로 ego 화면 복구됨→5관점 메모 수집 가능해짐 |
| SECTOR-MODE-DISPOSITION | 섹터 모드 거취: (b) 숨김/비활성 확정 | @frontend | — | **✅종결(⑳-3 S2-B 섹터-b, 07-29)**: 섹터 지도 진입 숨김(MarketGraphCanvas `SECTOR_MAP_ENABLED=false`·인기섹터 버튼 접힘·빈상태 정직화·GraphStatePanel 다시시도 제거). Neo4j 동결·실노출0. **부활 조건 = 백본 트랙(Q20-3-BACKBONE-SECTOR) 재설계** |
| MINDMAP-EGO-VIEW | ⑳-3 S3: ego 관계 마인드맵 뷰(맵-3 접힘 카테고리+클릭 펼침, 도메인 기반). D-MINDMAP | @frontend | **착수조건=S2-B 도메인 반영**(relation_domain 승인본) | **대기(S2-B 후)** | 지도-B/섹터-b로 접은 지도의 근본 대안. 라벨 겹침·초기 뭉침 구조적 회피. 데이터(도메인 태그) 선행 |
| DOMAIN-AUTO-SWITCH | 관계 도메인 자동승인 스위치 활성: 첫 배치 검수 후 `DOMAIN_CONFIDENCE_THRESHOLD` 확정 + `DOMAIN_AUTO_APPROVE=True`. D-DOMAIN-AUTOMATION 안전핀② | @backend | **캘리브레이션(첫 배치 CSV 검수)** | **대기(검수 후)** | ⑳-3 S2-B: `outputs/domain_tagging/review_batch.csv` 병진 검수 → 임계·시그니처 규칙 조정 → 스위치. auto 후보 반영 보류 중(기본 False) |
| DOMAIN-PHASE2-APPLY | 관계 도메인 Phase 2: 마이그 0028 적용(배포) 후 `tag_relation_domains --all`(DB 기록) + 검수 승인본 relation_domain 반영 | @backend+@qa | **DOMAIN-AUTO-SWITCH + 마이그 배포** | **대기(배포·검수 후)** | 이 세션은 CSV까지. draft·machine_check DB 기록은 migrate 후. 승인본은 검수 승인만 |
| EVIDENCE-CAP-REEXTRACT | SEC evidence 100자 캡 확대 + 관계 basis **재추출**. **소급 정정 아님**(기존 basis는 캡 시점 절단본 — 확대해도 과거 행 복구 불가) → 재추출 파이프라인 동반 필수. | @backend | **별도 결정(캡 크기·재추출 비용·SEC 재파싱 경로)** | **💤 보류(등재만)** | ⑳-3 S2-C 발견: target_not_in_basis의 실질 원인 = 100자 캡 절단·filer 암묵(나열 파싱으로 복구 불가). 재분류 dry-run상 target만 막힌 conf통과 62건이 재추출 후보. **감축의 실질 레버**(룰 튜닝 S2-C-1/2로는 volume 미감축=confidence·evidence 지배). 캡 확대는 재추출 없이는 무효 |
| Q20-3-BACKBONE-SECTOR | ⑳-3: 백본 전체 조망(중심성 top-N + RC 상위 엣지 PG 필터 뷰) + 섹터 모드 거취(SECTOR-MODE-DISPOSITION) **통합 재설계**. "지도는 원할 때만" 철학(⑳-2 D-DRILLDOWN-CARD-FIRST 연장) | @frontend | ⑳-2 배포 + 5관점 메모 | **대기(착수 조건)** | ⑳-2로 카드 드릴다운 완료→ego 화면 안정. 백본(전체 조망)은 Q20-2-BACKBONE-GRAPH 흡수. ego 계약·카드 컴포넌트 재사용. Neo4j 미의존(PG centrality+RC) |
| MAP-VISIBILITY | 지도 가시성 개선(본개선): ⑳-G S3는 초기 방사형 뭉침을 프레임 오버레이로 **가림**(표시층 임시). 근본은 초기 배치·force 튜닝. **⑳-3 S2에서 지도-B로 접힘(MAP_ENABLED=false)** — 지금은 미노출이라 우선순위 하락 | @frontend | 지도 부활(D-20-3-MAP-FOLD) | **접힘(지도-B)·부활 조건부** | **부활 조건 = 백본 트랙(Q20-3-BACKBONE-SECTOR) 재설계 시 지도 다시 켤 때 함께 근본 처리**. S3 오버레이·MarketGraphCanvas 코드 보존(회귀 안전) |
| TRACE-PG-REDESIGN | Chain Trace(경로 탐색) PG 재설계: 레거시 `/chainsight/trace/`(Neo4j `repo.run_query`)는 동결 500 → ⑳-3 S2에서 미호출·"준비 중" 처리. 근본은 PG(RC 그래프) 경로탐색 재구현 | @backend+@frontend | 백본 트랙(Q20-3-BACKBONE-SECTOR) | **대기(백본 연계)** | S2 D-1로 오번역(500→"경로 없음") 제거. 백본 PG centrality/RC 그래프 위 경로탐색과 통합 검토 |
| SLICE-A-MARKETGRAPH-EDGECOLORS | MarketGraphCanvas 인라인 EDGE_COLORS/WIDTHS/DASHES(유일 잔여 중복)를 graphStyles RELATION_STYLES로 통합 | @frontend | 지도 부활 or OUT 스코프 해제 | **보류(OUT 스코프)** | ⑳-3 S2 A-1 판정: 다른 8곳은 이미 graphStyles 단일소스. MarketGraphCanvas만 인라인 중복이나 **OUT 스코프(내부 로직 보호)+지도-B로 숨김** → 미접촉. 지도 부활 시 render 콜백과 함께 통합 |
| RELATION-DOMAIN-FIELD | 관계 도메인(제품/시장) 필드 S2-B: RelationConfidence `relation_domain` nullable 추가(dry-run `0019` clean additive 확인) + 도메인 추출(규칙/LLM/수동 — 별도 결정). ego는 이미 null 자리 확보 | @backend | S2-B 경로 결정 | **대기(S2-B 결정)** | STEP 0-2: SEC 270건 basis 실존이나 품질 편차(오라벨·노이즈). LLM 경로 가용(packages/shared/llm, BOUNDARY-LLM=래퍼 경유 허용). C-4 FE는 relation_domain 있으면 즉시 태그 렌더(additive 준비됨) |
| LEGACY-NEO4J-ENDPOINT-REMOVAL | 레거시 Neo4j 엔드포인트 제거 후보: `ChainSightGraphView`(/graph/)·`ChainSightSuggestionView`(/suggestions/)는 ⑳-3 S1로 FE 소비자 0(전 심볼 500 방치). ⚠ `ChainSightTraceView`(/trace/)는 useTrace가 아직 소비 → trace 대체 전엔 제거 불가 | @backend | ⑳-3 S1(소비자 전환) 완료 | **대기(소비자 0 확인 후)** | 지금은 무접촉 방치(D-20-3-LEGACY-CONSUMER-MIGRATION). graph/suggestions 소비자 0 확정 후 제거, trace는 경로추적 PG 재설계 후 |
| SUGGESTIONS-PG-REDESIGN | 탐색 카테고리(suggestions) PG 재설계: 레거시 Neo4j Cypher(peers/same_industry/co_mentioned/same_sector)를 PG(RelationConfidence `has_*_source`·CoMentionEdge) 기반 재구현. ⑳-3 정성화(관계 근거·출처)와 통합 검토 | @backend+@frontend | ⑳-3 정성화 트랙 | **대기(정성화 통합)** | S1에서 AIGuidePanel "준비 중" 정직 표시로 임시 처리. PG 카테고리 집계 = ego 계약 확장 or 신규 엔드포인트 |
| CS-P2-LLM-EVENTTITLE | 이벤트 보드 제목 **본개선**(LLM 네이밍): ⑳-2 S4는 티커 병기 표시 가공(임시). 근본은 EventGroup LLM 작명(name_candidates 활용) | @rag-llm | CS-P2-LLM(BOUNDARY-LLM) | **연결 메모** | ⑳-2 S4가 키워드 문자열("enersys delaney mcclain")을 티커 병기로 우회. 의미있는 그룹명은 LLM 트랙 종속 |
| FE-SERVE-MODE-TIDY | 프론트 서빙 방식 정리: next dev :3000 상시 기동을 LaunchAgent로 편입할지 결정(도그푸딩 마찰 해소) | @infra | 사용자 결정 | **대기** | ⑳-E 라이브 검증 중 :3000 세션 백그라운드 프로세스가 하네스에 반복 리핑됨([[lesson_background_task_reaping]]). 편집 worktree는 node_modules 심링크로 dev 불가(#48)→sv-web-runtime 전용. 상시성 필요 시 launchd 편입 검토 |

---

## 지시서⑲ 파생 — Neo4j 동결 완결 + 중심성 착공 후속 (2026-07-16)

> 출처: ⑲ S4 실측(discovery 정체=분류 b) + ⑱ 판정 이월. 브랜치 `monorepo/sess-19-centrality`.

| ID | Task | Agent | Depends On | Status | 근거/비고 |
|----|------|-------|------------|--------|-----------|
| Q19-PYTEST-FILTERWARN | pytest.ini `filterwarnings`의 stale `RemovedInDjango50Warning`(Django 5.2 제거됨) 정리 → `RemovedInDjango60Warning` | @qa | - | **todo(저우선)** | 평소 `-p no:warnings`가 파싱 차단해 무해, `-o addopts=""` override 시만 config red. ⑱·⑲ STEP 0 재확인 |
| Q19-REDUNDANT-SIGNAL | 잉여 신호층 정리: PRICE_CORRELATED 3,784쌍 **전부** PEER_OF와 겹침(구조 엣지 0 기여) → truth_score 정규화/가중 재설계에 연결 | @backend | 정규화 트랙 | **todo** | ⑱ 검산·⑲ S3 weight=max(truth,market) 확인. 정규화 트랙과 얽힘(단독 착수 금지) |
| Q19-SD-LINKPRED | S-D 링크예측 재도전 — 시간분할 검증(과거→예측→미래 확인) | @backend | RPS 궤적 견고화 + discovery 재가동 | **예약(트리거 대기)** | ⑱ 기각(궤적 깊이 부족). 트리거: RPS 주간 궤적 ~3-4개월 축적 **또는** discovery 재가동(Q19-DISCOVERY-REACT) |
| Q19-A3-SECTOR-MOCKUP | A3 섹터 그래프(Sector 모드 Neo4j) 존치/전환 판단 → 전체 조망 목업 트랙(⑳)으로 회부 | @UI-UX-designer | ⑳ 목업 | **회부** | ⑱ A3 카드: Sector 모드 Neo4j 잔존, PG 전환 비용 중. 살릴지 = 병진 가치판단 |
| RC-WATCHDOG-NEO4J-ALERT | watchdog가 정지 중인 neo4j 워커를 5분마다 kickstart + 실패 경보 메일 | @infra | RC-NEO4J-WORKER-TREE | ✅ **해소(2026-08-31 16:44)** | 근본 해소 = neo4j 워커 정상 기동 + watchdog 트리 교정. watchdog 첫 발화 16:44:14 **"Worker (neo4j) RECOVERED"** + 복구 메일 → 경보 폭탄 종료(누적 "재시작 실패" 28건에서 정지). worker/beat 자동복구 공백도 함께 해소. 잔여 = daphne 미감시(→ RC-WATCHDOG-DAPHNE-COVERAGE). |
| RUNTIME-BEAT-DAPHNE-DOWN-0831 | **beat·daphne가 12:12경 원인 미상으로 정지**(크래시 아님·`Killed 0 pending application instances` 정상 종료 로그) → CC가 12:17 복구 | @infra | — | 🔭 **관찰(원인 미상·복구됨)** | watchdog은 `kickstart`만 하고 `bootout`은 안 하므로 범인 아님. 타 worktree mtime도 11:53 이후 없음. **watchdog 감시 목록에 daphne(`com.stockvis.web`)가 없어 자동 복구되지 않는 것**이 구조적 갭 — API 전면 불가(:18765 응답 000)가 ~5분 방치됨. 감시 대상에 daphne 추가 검토. |
| RC-NEO4J-WORKER-TREE | launchd 실행 트리 교정 — `celery-worker-neo4j` + 동류 2건 | @infra | — | ✅ **done(2026-08-31 16:41 집행·검증 합격)** | STEP 0(래퍼 self-locate) `9a17e324` → **집행 완료**(병진 권한 위임·CC 집행). plist 교체+bootstrap: `celery-worker-neo4j` ✅ · `celery-watchdog` ✅ · `pg-backup` **미집행**(→ RC-LAUNCHD-PGBACKUP-TREE). 검증 = **프로세스 실제 cwd = 런타임 트리**(lsof 확증) · ping pong · 적체 큐 62→0(전건 `synced:0`) · 실효 dirty 0 유지 · watchdog 첫 발화 `RECOVERED`. `sv sync` 미실행(게이트 이미 충족·범위 밖 배포 회피). 백업 `*.plist.bak-20260831` 2건 보존. |
| RC-THETA-BADGE-WIDTH | strip θ가 최상위 계단(0.85)에 얹혀 배지 후보 4배 축소 — 과협 여부 화면 검수 | @frontend (dashboard) | RC-A-1(done) | 🔭 **관찰(등재만)** | PC 3,784행 처분으로 p85가 0.6→0.85로 상향. 배지 후보 9,057→2,131, 0.6 계단 6,926행 전량 탈락. θ는 분포 추종 설계라 의도된 동작이나, 사용자 체감상 배지가 사라진 것으로 보일 수 있음. |
| Q19-DISCOVERY-REACT | discovery 해자 폭 재성장 — 신규 RC 유입 재가동 | @backend | 별도 결정 | **격하: 유니버스 확장 선택 문제(2026-08-27, RC-A-1)** | ⑲ S4 판정 "유니버스 포화·신규 0"는 **RC-A-0/A-1 실측 반증** — 08-10 co-mention 신규생성 재점화(1,679), 이후 매일 56~226, RC 13.7k→17.3k(08-27). 유입 정지는 경로 차단 아니라 7월 뉴스 유니버스/추출 공백(08-10 재개). ⇒ "고장" 아님, 유니버스 확장은 **선택**. cf. DECISIONS [2026-08-27] RC-A-1 |
| Q19-WIDTH-STAGNATION | 해자 폭 정체 실측 — RelationPairSnapshot 매 period 9562행 고정 | @backend | Q19-DISCOVERY-REACT 연계 | **전제 반증(2026-08-27, RC-A-1)** | ~~9562 고정~~ 반증: RPS 555,399행(08-27)·매일 궤적 성장·신규 페어 유입 재개(08-10~). "폭 정체"는 7월 공백 스냅샷의 일시 현상. 저장=PG `chainsight_relation_pair_snapshot`(Neo4j 비의존). cf. Q19-DISCOVERY-REACT 격하 |
| RC-DECAY-EVIDENCE-TS | 감쇠 근본 해소 — `evidence_last_observed_at`(관측 시각) 필드 분리해 감쇠 시계를 auto_now("save 시각")에서 독립. RC-A-1 PART1은 타입 게이트로 오발만 차단(증상), 근본은 시계 의미 분리 | @backend | RC-A-1 배포 후 | 🆕 **후속 후보 등재(2026-08-27)** | D-RC-DECAY-SEMANTIC. auto_now 리셋을 마이그레이션이 밀면 재발 가능 → 관측 시각 별도 필드가 정본. 마이그 동반(additive nullable) |
| RC-SURVEY-0 | RelationConfidence 해자 실측(read-only) | 읽기 전용 | — | ✅ **CLOSE(2026-08-27, RC-A-1로 소진)** | RC-A-0 리콘으로 흡수·처분 완료. 약점 TRUTHSCORE-NORM→D-RC-SCALE, PRICE_CORRELATED 잉여→D-RC-PC-DISPOSE, 감쇠→D-RC-DECAY-SEMANTIC 해소 |
| RC-A-0 | 점수 눈금 위생 설계 실측(read-only) | 읽기 전용 | RC-SURVEY-0 | ✅ **CLOSE(2026-08-27)** | 리콘 완료(scratchpad `RC_A0_RECON_REPORT.md`). 디렉터 회부 3건 → RC-A-1 집행 |
| RC-A-1 | 점수 눈금 위생 실행(write) | @backend/chainsight | RC-A-0 | ✅ **배포 완주(2026-08-31, ②~⑥ 병진 집행·CC 검증)** — PG 17,410→13,626·Neo4j 12,457→11,101·양측 PC 0·v3.0 전건·θ 60.0→0.85. 잔여=⑧ 09-19 beat 확인 | D-RC-DECAY-SEMANTIC·D-RC-SCALE·D-RC-PC-DISPOSE. 커밋 `a396e748`·`23318e25`·`4efdc4c9`·`0d414e62`·A-0보고서 `90558ef9`. ⚠ **폭탄(09-19 감쇠 오발 2,054행) 해제=배포 후**. **병진 순서(D-RC-DEPLOY-WINDOW·혼재창 닫기)**: ①머지 ②worker·beat 정지 ③migrate 0033 ④worker·beat 재기동 ⑤dispose --apply ⑥Neo4j Cypher ⑦after-snapshot(CC) ⑧09-19 beat 확인. 데드라인 09-12 주초 권고·절대 09-19 |

---

## credit_signals — Phase 1 라이브 종결 + Phase 2/2.5 대기 (2026-07-09)

> 출처: credit_signals Phase 1 실가동(origin/main `a27fd14`, ff land). DECISIONS "credit_signals 신규 앱 (§7.2-B)". 소비처(Dashboard) 착수는 **별도 결정** — 현재 수집·계산·API 백본만 가동, 실전 노출 없음(Heat Score 원칙).

| ID | Task | Agent | Depends On | Status | Output Artifact |
|----|------|-------|------------|--------|-----------------|
| CS-CREDIT-P1 | credit_signals Phase 1 실가동 (FRED 6종 수집·MAD z·strip API·beat) | @infra | - | **🏁 종결 2026-07-10** (fresh 07:30 cron tick GREEN, verify OK, unregistered 0) | origin/main `004ba61`, 원장 4600+행, beat 2종 enabled |
| CS-CREDIT-P2 | Phase 2: FMP HYG/LQD ETF flow + 차환 절벽(refinancing cliff) 지표 | @backend | 별도 결정 | **대기(착수 미정)** | - |
| CS-CREDIT-P2.5 | Phase 2.5: SEC 424B2/FWP 발행 신호 파이프라인 | @backend | 별도 결정 | **대기(착수 미정)** | - |
| CS-CREDIT-CONSUME | Dashboard 프론트에 크레딧 신호 스트립 노출 (소비 시작) | @frontend | 별도 결정 | **🏁 종결 2026-07-11** (MacroStrip 라이브 렌더, gray5+yellow1) | `MacroStrip`+`GradeChip`, origin/main `50ec128` |
| CS-CREDIT-MEANING | 의미 2층: 헤드라인(규칙 자동문장) + 하단 리드아웃(정의·상태·밴드) | @frontend | - | **🏁 종결 2026-07-13** (628 GREEN, 라이브 렌더) | `lib/credit/creditMeaning.ts` |
| CS-CREDIT-CAPTION-FIX | 리드아웃 밴드를 백엔드 grading 규칙에서 도출(신호별, signed z·orange 무상한·red 절대레벨) | @frontend | - | **🏁 종결 2026-07-13** (632 GREEN, 라이브 렌더) | `lib/credit/creditGrading.ts` (백엔드 무변경) |
| CS-CREDIT-INFOPANEL | ⓘ 확장 패널 — **TH 밴드 대시보드 합류 시 재검토** (이번 범위 제외) | @frontend | TH 밴드 합류 | **대기(범위 제외)** | - |
| OPS-API-TREE-SYNC | `worker_sync.sh`에 daphne api 트리(`sv-api-runtime`) 포함 + --dry-run + 단계간 health 체크 | @infra | - | **🏁 종결 2026-07-10** | api 트리 포함=`803e9a9`(DAPHNE-BUILD)·자기가드=`942a991`(기해소) + --dry-run/health 체크=`3e774c3`. real run 검증: 3트리 동기화·worker ping·daphne 401·strip 200·기존 서비스 무영향 |

> **배포 절차 (재발 방지)**: credit_signals도 #28 계열 — 신규 task는 ① worktree/api/web/worker 트리 origin/main 동기화(`worker_sync.sh` = worker+web만, **daphne api 트리 `sv-api-runtime`은 별도 수동 sync 필요**) → ② worker+beat+daphne 재시작 → ③ runtime `.env`(Desktop 심링크)에 `CREDIT_SIGNALS_ENABLED=true` → ④ `register_credit_beats` + `PeriodicTask enabled=True`. **worker_sync.sh가 sv-api-runtime 미포함**은 부채(DAPHNE-BUILD 후속) — API 라우트 배포 시 수동 sync 필수.

---

## Theme Heat runtime 배포 — 오늘 배포 포기·C8 1주 연기 (2026-07-10)

> 출처: credit_signals 종결 관찰(TH beat 2종 unregistered 에러). A-0 실측: TH 코드는 `sv-theme-heat`(branch `monorepo/sess-cs-theme-heat`, 26커밋 미머지 WIP)에만 존재, origin/main·runtime worker에 없음. 경로②-머지불가 판정.

| ID | Task | Agent | Depends On | Status | Output Artifact |
|----|------|-------|------------|--------|-----------------|
| TH-RUNTIME-DEPLOY | TH 트랙(sess-cs-theme-heat) 정식 머지 → worker_sync + 재기동 → TH beat 3종 재활성화(C8 EstimateSnapshot 포함) | @infra (TH 소유 세션) | TH 트랙 클린 체크포인트 머지 | **✅ done 2026-07-29** | 마이그 renumber 0016~24→0019~27(`995f8846`)·역병합·push origin/main `f7f3f63d`·DB name UPDATE 9행(showmigrations 0014~27 선형·migrate --check clean)·worker_sync 3트리 f7f3f63d·theme_heat 3종 registered 게이트 통과 |
| TH-BEAT-REENABLE | UNREGISTERED 3 beat(collect-theme-filings·theme-heat-daily·snapshot-analyst-estimates) 재활성화 | @infra | TH-RUNTIME-DEPLOY | **✅ done 2026-07-29** | `PeriodicTask enabled=True` 3행(트랜잭션) + `PeriodicTasks.update_changed()`(DatabaseScheduler Schedule changed 확인). 다음 발화: theme-heat-daily 18:00 ET·filings 17:30 ET·estimates 금 16:30 ET. **익일 산출물 행 확인 대기** |
| TH-RESUME-CORPUS-UNFREEZE | TH 트랙 재개 — ~~corpus unfreeze~~ + TNV 집계 백필 세션 1 (정정: corpus 무동결, 실동결=TNV 집계) | @infra (TH 소유 세션) | **트리거: SEC β 종결(충족)** | **✅ 완료 (TH-SESSION-1 백필 07-26→08-03 + TH-TNV-CHAIN-1 체이닝으로 재동결 구조적 차단)** | G2 앵커(92/19/0/0, ≤07-11 스코프)는 **백필 후 비교 대상 아님** 조항 승계(corpus 확장 시 앵커 무효). override 재산출=TH-OVR-RECUT 분리. cf. D-TH-TRIGGER-CORRECT·D-TH-TNV-CHAIN |
| TH-TNV-CHAIN | TNV 집계를 theme-heat-daily 태스크에 체이닝 — 재동결 구조적 방지 (B안) | @infra/@backend | D-TH-TNV-CHAIN | **✅ 종결 (G-obs 통과 2026-08-10, 종결선언 `9a715196`)** | 코드 `114e1c26`(+18줄 additive·3테스트)·LOGGING 수정 `8351c198`(apps 로거 propagate=True)·배포(worker-runtime 8a41c842+재기동)·**G-fire PASS**(ET18:00 08-06 발화·TNV 22:00:00→heat 22:00:45 DB입증·오류0)·**G-obs PASS**(08-07 `TNV_CHAIN` 파일기록·DB정합, 하단 GOBS 행). §C·§C′(08-04·08-05) 백필 동승. 종결선언 `th_chain_closure.md`. common-bugs #88b·#89·#90 |
| TH-TNV-CHAIN-GOBS | (관찰·게이트 아님) 다음 발화 ET 18:00 08-07에서 `TNV_CHAIN date=2026-08-07` 로그 **파일 기록** 확인 = S1 LOGGING 수정 실증 | @infra (병진 "게이트 확인해줘") | TH-TNV-CHAIN 배포 | **✅ 통과 2026-08-10** | `TNV_CHAIN date=2026-08-07 written=3 zeroed=0` **파일 기록**(S1 실증)·DB TNV 3행 created 22:00:00 UTC·heat 6행 22:00:12~46 인접(체인 정순)·theme-heat-daily total_run **20**. heat E2 증분 로그도 파일 기록(선존갭 해소). **caveat=선존 Neo4j-down**(heat 6/11 status=warning·08-03~09 일관·G-fire에도 동일=회귀 아님→TH-HEAT-NEO4J-DOWN). 종결선언 착지 `9a715196`. §F3 롤백 폐기. 임시 스크립트 4종 정리 병진 대기 |
| TH-HEAT-NEO4J-DOWN | (백로그·비체인) theme-heat 발화 시 Neo4j(localhost:7687) refused → `heat_score` Cypher 실패 → 섹터 6/11만 저장(status=warning) | @infra | **트리거: Neo4j 상시 기동 필요성 실증 or heat 완전화 요구** | 🔭 등재(관찰) | G-obs에서 표면화(08-03~09 일관·G-fire에도 동일=선존 정상상태·TNV_CHAIN 체인과 직교). 미저장 5섹터=Basic Materials·Comm Svc·Consumer Defensive·Real Estate·Utilities. cf. `troubleshoot_neo4j_sync_pipeline` |
| OPS-SMTP-CRED | (백로그→진행) `send_agent_report_task`·`send_daily_report_task` SMTP 535 BadCredentials → 리포트 메일 실패. **OPS-SWEEP-1 §4 실측**: 로테이션 대상 키=**`EMAIL_HOST_PASSWORD`**(Gmail 앱비번 len16), 계정=`EMAIL_HOST_USER`, smtp.gmail.com:587 TLS. 소화 워커=**기본 큐 `com.stockvis.celery-worker`**(재기동 최소 대상). **병진 잔여**: ①Google 앱비번 신규발급 ②`.env EMAIL_HOST_PASSWORD` 교체(4×4 공백 제거) ③`smtp_verify.py` login 검증 ④default 워커 bootout+bootstrap. 검증스크립트·안내문 OPS-SWEEP-1 §4 상신 | @infra | 완료 | ✅ done(08-24 발송 복구) | **§4·§5 종결**: 앱비번 로테이션(.env)·smtp_verify `SMTP_LOGIN_OK`·default 워커 재기동(pid 84739). **§5 발송 실측**: 08-24 리포트 5/5 succeeded·status:sent(agent data/backend/qa/design+daily·recipient jinie545). 신규 535=0(잔존 텍스트=drained retry/digest 본문). |
| TH-TNV-BEAT-SPLIT | (보류) TNV 집계를 heat 태스크 체이닝(B안)에서 **독립 beat로 분리**(A안 승격) | @infra | **트리거: TNV·heat 주기 분화 필요 시** (예: TNV 일중 다회·heat 일 1회) | 💤 보류(등재만) | 현재 체이닝(D-TH-TNV-CHAIN)이 TNV→heat 순서·정합 보장. 분리 시 #28(beat drift) 재노출 — 독립 스케줄 필요성 실증 전 착수 금지. A안 미래 재개점 |

> **오늘 조치(완료)**: UNREGISTERED 3 beat `enabled=False`(에러 플러드 + 깨진 C8 발화 차단). 정상 배포 beat(heat-score-daily·seed-snapshot-cleanup) 무접촉. **C8 첫 EstimateSnapshot(금 16:30 ET) 1주+ 연기** — 시한 때문에 미머지 26커밋 강행 머지 금지(최악). 재개는 TH 트랙 소유자/디렉터가 클린 머지 후.

## 🔴 [P0] chainsight-pair-aggregation beat DB 등록 (버그 #28)

> 출처: RelationPairSnapshot 적립 작업(2026-06-29, 브랜치 `monorepo/sess-cs-pair-relevance`). DECISIONS "RelationPairSnapshot 쌍 relevance 적립 [해자]".

- **증상**: dict 정의 beat(`config/celery.py` `chainsight-pair-aggregation`)가 DatabaseScheduler에서 무시됨 → prod에서 일간 집계 미실행(침묵 실패).
- **영향**: RelationPairSnapshot이 prod에서 적립 안 됨 = **해자 궤적이 안 쌓임**(이 작업 전체의 목적 무력화). GREEN인데 prod 침묵이라 "왜 스냅샷이 안 쌓이지?"로 몇 주 뒤 헤맴.
- **조치 (완료, `bdba71c`)**: B안 — `register_chainsight_beats` BEATS에 pair 엔트리 추가(timezone/day_of_week optional 키 additive 확장). task=`apps.chain_sight.tasks.relation_tasks.aggregate_relation_pairs_task`, **America/New_York 11:30 매일**(confidence 11:00 ET 직후, DST 자동). A안=migration 철회(CI 오염·repo 수동-register 표준 충돌).
- **⚠ 타임존 정정**: 조치 초안의 "11:30 EST"는 부정확 → 실제 celery TZ = **America/New_York(ET, DST 자동)**. confidence도 동일 ET라 순서 보장.
- **Gate 1 (통과, 이번 세션)**: 등록 확인(1행)·import resolve·DatabaseScheduler 스케줄 로드(ModelEntry `30 11 매일 ET`)·idempotent(재실행 updated·중복0·기존 3개 UTC/평일 불변).
- **🔴 migrate 누락 발견 (2026-07-01 실측)**: 마이그레이션 0014가 **dev/prod DB에 미적용**이었음(`showmigrations` `[ ] 0014`). 테스트는 별도 테스트 DB(--reuse-db)에서 돌아 GREEN이었으나 **운영 DB엔 `chainsight_relation_pair_snapshot` 테이블 자체가 없었다**. → beat가 돌아도 task가 `ProgrammingError: relation does not exist`로 crash = **register만으로는 부족, `migrate`가 배포 선행 필수**(claude.ai 체크리스트가 놓친 단계). dev는 `migrate chainsight 0014` 적용 완료.
- **Gate 2 파이프라인 (통과, 2026-07-01 수동 실행 증명)**: migrate 후 `aggregate_relation_pairs_task.apply()` → `{'pairs': 9562, 'created': 9562}` 성공. **period=`2026-07-01` 단일**(중복 주간 행 0) → **드리프트 ⒜는 순수 표기 문제로 확정**(period 로직 정상, 매일 캐이던스 OK). opp 상위 = 순수 truth 쌍(SNDK/WDC opp=0.722). 남은 것 = **beat 자율 틱**(스케줄러가 11:30 ET에 자동 호출)만 익일 로그로 관찰.
- **⚠ 배포 절차(B안 약점 — 순서 필수)**: 배포마다 ① `python manage.py migrate` (0014 — 테이블 선행) → ② `python manage.py register_chainsight_beats` (beat 등록) → ③ 검증. migrate 빠지면 register돼도 task crash(더 깊은 침묵). 배포 체크리스트 영구 등재.
- **드리프트 (목록만, 이번 PR에서 수리 X)**: ⒜ `update_relation_confidence` docstring "주 1회 일요일" vs 실제 매일 11:00 ET — **2026-07-01 실측으로 순수 표기 문제 확정**(당일 단일 period, 로직 정상). ⒝ beat 패턴 혼재(relation_tasks=full-path+ET vs register 기존 3개=별칭+UTC).
- **관찰(PR 밖)**: 11:00→11:30 30분 갭이 confidence 완료를 보장하는지 — 갱신 소요시간 로그 확인 후 갭 재검토.
- **ops 폐기 기록 (재발 방지, 2026-07-02)**: "worker/beat launchd KeepAlive 감독 신규 설치" PR은 **폐기**. STEP 0 실측 = 기존 `com.stockvis.celery-worker`·`celery-beat` 둘 다 이미 `KeepAlive=true`+`RunAtLoad`+`ThrottleInterval`, worker-neo4j·watchdog까지 존재 → 신규는 중복 + **beat 2개 = 스케줄 2배 발화(능동 오작동)**. 07-02 crash 원인은 KeepAlive 부재 아닌 코드 리로드 누락(해법=`kickstart -k`). 향후 "감독 추가" 논의는 이 실측표부터 확인. 대신 관찰가능성만 보강 = `verify_pair_aggregation.py` C항목(직전 11:30 ET 틱 succeeded 부재 시 ALERT — upsert+updated_at 부재라 로그가 유일 증거).

| ID | Task | Agent | Depends On | Status | Output Artifact |
|----|------|-------|------------|--------|-----------------|
| CS-PAIR-BEAT | chainsight-pair-aggregation PeriodicTask DB 등록 (+ migrate 0014 선행) | @infra | - | **Gate1+파이프라인 done / beat 자율틱 익일** | `register_chainsight_beats` (머지 `bdba71c`), dev migrate 완료 |
| CS-PAIR-DEPLOY | prod 배포: migrate 0014 → register_chainsight_beats → 검증 (아래 체크리스트) | @infra | 머지·배포 | todo | 배포 체크리스트 |

### [배포] Chain Sight #28 beat — 순서 필수 (건너뛰면 prod 침묵 실패)

> ⚠️ 이 단계를 건너뛰면 코드가 머지돼도 prod는 RelationPairSnapshot 0으로 침묵한다(등록·테이블은 "코드"가 아니라 "배포 행위"로만 반영됨). migrate→register 순서 준수.

1. [ ] **migrate (테이블 선행)**: `python manage.py migrate chainsight 0014` — 없으면 task가 `relation does not exist`로 crash.
2. [ ] **beat 등록**: `python manage.py register_chainsight_beats` (1회).
3. [ ] **🔴 beat + worker 둘 다 재시작**: `launchctl kickstart -k gui/$(id -u)/com.stockvis.celery-beat` **및** `...celery-worker`(+`worker-neo4j`). **worker 재시작을 빠뜨리면** beat는 발화해도 worker가 신규 task를 모름 → `Received unregistered task ... KeyError` crash(2026-07-02 dev 실측). beat만 재시작하면 안 됨.
4. [ ] **즉시 검증**: `celery -A config inspect registered | grep aggregate_relation_pairs`(등록 확인) + `PeriodicTask...filter(name="chainsight-pair-aggregation")` 1행·enabled·`11:30 America/New_York`.
5. [ ] **익일 검증(진짜 GREEN)**: 다음 11:30 ET 경과 후 ⓐ worker 로그 `aggregate_relation_pairs succeeded`(unregistered 아님) + ⓑ 당일 `period` 행이 **단일 period·count 정상(중복 없음)**.
   > **[v2 멱등 성격 정정]** `RelationPairSnapshot`은 unique `(canonical_a, canonical_b, period)` = **upsert형**이고 **`updated_at` 필드 없음**(created_at만). 따라서 같은 period 재실행은 **count·타임스탬프 모두 불변** → **발화 증거는 ⓐ worker 로그가 유일**(count "안 늘어남"을 실패로 오판 금지 = 위음성 차단). ⓑ count는 **중복(≈2배=멱등 위반) 감지용**이지 발화 증거 아님. verify_pair_aggregation.py가 A(로그)+B(count) 병행으로 이미 커버.
6. [ ] **근본 수리(권장·별도 태스크)**: 위 migrate+register+재시작을 배포 스크립트/릴리스 훅에 넣어 수동 의존 제거 — B안의 "사람이 까먹음" 함정(#28이 한 층 위로 옮겨간 것)의 완결.

---

## Chain Sight M2 v1.1 — theme_tags → EventGroup reader 전환 (Phase 1)

> 보드를 섹터형 theme_tags → 코어-위성 EventGroup + 정합 leadership으로 전환. 2026-06-27 **Phase 1 완료(go-live)**. 결정: DECISIONS "Chain Sight 보드 EventGroup 전환 (2026-06-27)".

| ID | Task | Agent | Depends On | Status | Output Artifact |
|----|------|-------|------------|--------|-----------------|
| CS-EG1 | EventGroup 리더 어댑터 (kept만·n3·core/satellite) | @backend | - | **done** | `event_group_reader.py` (머지 `d787499`) |
| CS-EG2 | C 비대칭 leadership 재컴퓨트 (코어 LOO/위성 코어평균) + L3 오라클 | @backend | CS-EG1 | **done** | `leadership_eventgroup.py` + migration 0013 (머지 `269d1eb`) + prod eg 114행 |
| CS-EG3 | 보드 리스트+드릴다운 플래그 배선 (`CHAINSIGHT_GROUP_SOURCE` OFF 기본) | @backend/@frontend | CS-EG2 | **done** | `flags.py`·attach_leadership_eg·EventBoard.tsx (머지 `202a840`) |
| CS-EG4 | C 컴퓨트 daily beat (22:15 UTC) + 캐시 | @infra | CS-EG3 | **done** | `register_chainsight_beats` + `chainsight-event-group-leadership-daily` 등록·worker 재기동 |
| CS-EG5 | go-live: 플래그 ON + 서버 재시작 = Phase 1 완료 | orchestrator | CS-EG4 | **done** | `.env event_group` + daphne/celery 재시작, beat `.delay()` 검증 |
| CS-EG6 | 옛 theme_tags leadership/그룹핑 디프리케이션 (파괴적, 한참 뒤) | @backend | CS-EG5 안정화 | todo | — (전환 안정 후) |

### Chain Sight Phase 2 백로그 (Phase 1 라이브 후, 2026-06-27 등록)

> 출처: Phase 1 마무리 정리 세션. LLM 묶음은 BOUNDARY-LLM 트랙 의존(메모리 `project_boundary_llm_track`).

| ID | Task | Agent | Depends On | Status | 비고 |
|----|------|-------|------------|--------|------|
| CS-P2-LLM | LLM 의존 묶음 (LLM 레이어 통합 / 10-K 관계추출 / FRED 해석) | @rag-llm/@backend | ~~BOUNDARY-LLM 슬라이스① land~~ **해소(언블록, 2026-07-13)** | todo | ✅ 의존 충족 — `packages/shared/llm` 코어 landed(merge `8be3f65`, ⑪ 실측). 착수 가능 |
| CS-M3 | Path Watchlist (코어-위성 경로 추적) | @backend/@frontend | 독립 | todo | EventGroup 코어-위성 위 경로 추적 |
| CS-P2-GRAPH | 그래프 화면 정제 (EventGroup 시각화) | @frontend | 독립 | todo | redesign v1 그래프 캔버스 위 EventGroup 반영 |
| CS-P2-13F | 13F 버그 + CUSIP 매핑 수정 | @backend | 독립 | todo | 위성 cohold_institutions 정확도 |

---

## Chain Sight 마켓 뷰 (redesign v1)

| ID | Task | Agent | Depends On | Status | Output Artifact |
|----|------|-------|------------|--------|-----------------|
| CS-R1 | Schema 마이그레이션 (previous_status, neo4j_dirty) | @backend | - | done | `chainsight/migrations/0005_add_neo4j_dirty_previous_status.py` |
| CS-R2 | Seed Selection Task (14개 함수, 매일 13:00 UTC) | @backend | CS-R1 | done | `chainsight/services/seed_selection.py`, `chainsight/tasks/seed_tasks.py` |
| CS-R3 | Neo4j Dirty Sync (undirected 정규화) | @infra | CS-R1 | done | `chainsight/services/neo4j_sync.py`, `chainsight/tasks/neo4j_dirty_sync_tasks.py` |
| CS-R4 | 마켓 뷰 4개 API (seeds, sector/graph, neighbors, signals) | @backend | CS-R2, CS-R3 | done | `chainsight/api/views.py`, `chainsight/api/urls.py` |
| CS-R5 | FE 상태 + 섹터 바 + 그래프 캔버스 | @frontend | CS-R4 | done | `explorationStore.ts`, `SectorBar.tsx`, `MarketGraphCanvas.tsx` |
| CS-R6 | 탐색 트레일 + 관계 카드 | @frontend | CS-R5 | done | `ExplorationTrail.tsx`, `RelationCardPanel.tsx` |
| CS-R7 | 체인 스토리 피드 | @frontend | CS-R5 | done | `ChainStoryFeed.tsx` |
| CS-R8 | 코드 리뷰 | @qa | CS-R4~R7 | verified | 📎 `docs/chain_sight/task_done/chain_sight_redesign_V1/qa_evaluator_review_01.md` |
| CS-R9 | 커밋 + 머지 | orchestrator | CS-R8 | **done** | PR #8 / `be2d6c7` 머지 확인 (2026-06-11 CS-RD1 Part A 정합화) |

---

## Chain Sight 이벤트 보드 개편 (redesign 26.06)

> 첫 화면 정보 구조 역전: 이벤트(테마) 보드 → 관심도 랭킹 → 그래프 드릴다운. 결정 근거: DECISIONS "CS-RD (2026-06-11)".

| ID | Task | Agent | Depends On | Status | Output Artifact |
|----|------|-------|------------|--------|-----------------|
| CS-RD1 | 하네스 정합화 + 테마 데이터 적재 (Phase 0–1) | @backend | CS-R9 | **done** | Part A·B 정합화 + Part C 적재 완료(옵션2: sector+theme w≥1.0, DECISIONS CS-RD-C2). 채움률 60.3%/15그룹, Neo4j :Theme 21/HAS_THEME 536 |
| CS-RD2 | 관심도 M1 엔진 (모델·배치·API, Phase 2) | @backend | CS-RD1 | **done** (StockAttentionScore+migration0009 / attention_service(M1+ADV_FLOOR $45.8M 유동성가드) / Celery task / API 2개(events·events/<theme>/stocks) / 테스트 20. 670→634계산 0.16s, score 15.6~99.9, low_liq 34, 멱등Δ0, api/views.py diff0) | v2 지시서 `Cs redesign 02 attention m1 backend v2.md` |
| CS-RD3 | 이벤트 보드·관심도 랭킹 프론트 (Phase 3–4) | @frontend | CS-RD2 | **done** (2026-06-23, `8c276b5`) — QA 4슬라이스 + Slice 2-B(바 정규화 전역0~100) + ⓑ URL 인코딩(common-bugs #38) + ⓐ 소규모 그룹 노출+저신뢰 표식. vitest 387/0·pytest 74/0, 라이브 검증 완료(daphne 재기동) | `docs/chain_sight/redesign(26.06)/Cs redesign 03 event board frontend .md` |
| CS-DATA-HYGIENE | 기존 0행 10종목·<20일 8종목 가격 공백 원인 점검 (z-score 불가 → 관심도서 해당일 제외 중) | @backend | - | **backlog** | CS-RD2 STEP0 발견. 상폐 8종(CTRA·DAY·FI·HOLX·IPG·K·MMC·WBA) 유니버스 정리 포함 |
| CS-BACKFILL | DailyPrice 120일 백필 — `/full` days=200 멱등. ≥120일 7→659/670 | @backend | - | **done** (666 성공·멱등·M1 scorable 634→659. 미달 11=IPO1/상폐8/프리미엄2) | DB 데이터(코드변경 0) |
| CS-M2 | 주도주 지표 엔진 v1 — 종목레벨 4지표(T2/T3/theme_beta/capture) | @backend | CS-RD2·CS-BACKFILL | **done** (StockLeadershipScore+migration0010 적용 / 640행 산출 / beat 2종 등록(leadership+M1 attention 부채) / **옵션Y: T2주·T3보조, ρ실측0.84**) | DECISIONS "CS-M2 (2026-06-16)" |
| CS-M2-DISPLAY | RD3 serializer/프론트에 옵션Y 노출 적용 — T2(trend_quality) 주, theme_beta·capture_spread 주, T3(theme_alpha) 보조 강등. window 파라미터 노출 | @frontend | CS-M2·CS-RD3 | **ready** | CS-M2 6지표 serializer 라이브 |
| CS-M2-V11 | 테마 레벨 지표(응집도·확산도·선행후행) — 테마 재정의(섹터≠테마) 후. O(n²) 상관판 | @backend | CS-M2 | **backlog** (테마 재정의 선행) | STEP0: 현 테마=GICS 섹터 중복 |
| MAIN-SYNC-FIX | 나이틀리 자동화가 로컬 main에 직접 commit(push 없이) → origin과 분기 재발(CS-M2-MERGE에서 ff 거부·잘못된 머지 사고). 자동화가 별도 브랜치 사용 or commit 후 즉시 push하도록 수정 | @infra | - | **자동화 부분 done 2026-06-18** (hook hardening 잔여) | **활성 스크립트 `run_tier3_audits.sh`를 dated 브랜치(`monorepo/nightly-<date>`) 격리로 수정 — 메인 트리 main 무오염 입증**(6/2 결정이 비활성 `nightly_v3.sh`에 오적용됐던 것 정정). DECISIONS "MAIN-SYNC-FIX 적용 (2026-06-18)". ⚠️launchd 재가동(`launchctl load`)은 사용자 승인 대기(현재 unload). **잔여 = hook 근본 hardening**(`scripts/hooks`+`core.hooksPath`, HARNESS-KB S3 .git/hooks 새 클론 미적용 한계) |
| NIGHTLY-BRANCH-GC | dated 나이틀리 브랜치(`monorepo/nightly-<YYYYMMDD>`) 누적 정리 — 매일 신규 브랜치라 시간이 지나면 local·origin에 쌓임. 보존기간/머지정책(리포트를 main에 주기 머지할지 vs N일 후 삭제) 결정 + GC 스크립트 or 주기 작업 | @infra | MAIN-SYNC-FIX | **backlog** | MAIN-SYNC-FIX 적용(2026-06-18)에서 파생. 격리는 됐으나 GC 미정 |
| KB-NIGHTLY-LINK | `docs/nightly_auto_system/reports` 고립 해소 — 나이틀리 감사 리포트가 KB 검색·1차소스로 흘러드는 소비 고리 설계(현재 생성만 되고 KB로 안 옴). 소비 고리 설계 필요 → **HARNESS-KB 범위 밖, 등록만** | @qa/@infra | - | **backlog** (범위 밖) | HARNESS-KB S4-3에서 등록. KB-CENSUS 'nightly 고립' 항목 |
| CS-EXT1 | 외부 API 직접 호출 4곳 → shared FMP 래퍼 경유로 이전 | @backend | - | **backlog** (이번 개편 범위 외 — 등록만) | `insider_tasks.py:38`, `sensitivity_tasks.py:80`, `neo4j_loader.py:132,144` (FMP `requests.get` 직접 호출) |
| CS-COV | 정식 섹터 분류 기반 그룹핑으로 커버리지 확장 검토 (ETF 비중 1% 미만 잔여 편입) | @backend | - | **backlog** | NarrativeTag(LLM) 태깅 병합 + w<1.0 잔여 종목 편입 검토 |
| CS-UNIV | 유니버스 확장 범위 분석 — 디렉터 지시서 발행됨, 별도 read-only 세션에서 실행. 확장 자체는 확정, tier 결정은 측정 후 디렉터 세션 | @backend | - | **active** (측정 완료 `9d80cdc`, 디렉터 결정 대기) | `docs/chain_sight/univ_analysis/REPORT.md` — T1 포화/T2 품질우위, 러셀 프록시 차단 |
| CS-EXP | 테마 ETF holdings 확대 + 유니버스 U2 편입 + 백필 (디렉터 지시서) | @backend | CS-RD1·CS-UNIV | **done** (핵심 목표=게이트 통과 달성: STEP0→(c)복구→GATE/SOURCE 측정→LOAD(ETF 추가)→U2SIM→**U2EXEC 편입으로 게이트 X=8 통과 중앙값26**. 잔여 NEO4J/SECTOR/P1·P2는 별도 트랙) | `Cs exp universe expansion.md` + univ_analysis/CS-EXP-*.md 6종 |
| CS-EXP-U2 | **유니버스 편입(U2)** — 테마 ETF holdings의 비SP500 US 종목을 Stock 유니버스에 편입해 그룹 밀도↑ | @backend | CS-EXP | **done** (U2EXEC로 실행 완료) | `CS-EXP-U2SIM.md` / DECISIONS "CS-EXP-U2 결정" |
| CS-EXP-U2EXEC | U2 실행 — 편입 + DailyPrice 백필 + 게이트 재측정 | @backend | CS-EXP-U2 | **done** (135종 편입·백필 0%실패·**게이트 X=8 통과 중앙값26**·유니버스535→670. `CS-EXP-U2EXEC_measurement.md`) | 예측26=실측26 일치 |
| CS-EXP-NEO4J | Neo4j 그래프 편입 — 신규 테마 ETF(XBI/KRE/PAVE) + 편입 135종을 `ETF_THEME_MAP`(load_themes_to_neo4j.py)에 추가해 :Theme/HAS_THEME MERGE | @backend | CS-EXP-U2EXEC | **todo** (ETF_THEME_MAP 코드 편집 — U2EXEC 범위 밖) | `load_themes_to_neo4j.py` ETF_THEME_MAP |
| CS-EXP-SECTOR | 신규 135종 sector/industry 채움 — FMP profile 엔드포인트 동기화(quote는 미반환) | @backend | CS-EXP-U2EXEC | **backlog** | `StockSyncService` profile sync |
| CS-EXP-P1 | generic 파서 확장 — Roundhill/Amplify 다중펀드 통합 CSV(Account=<ticker> 필터 + `StockTicker`/`Weightings` 컬럼) 지원 → HACK·BETZ holdings 적재 | @backend | CS-EXP | **todo** (shared 파서 코드 변경 — CS-EXP 세션 범위 밖) | URL 확보됨(amplifyetfs/roundhill), `etf_csv_downloader.py` `_parse_csv` 확장 |
| CS-EXP-P2 | KWEB Cloudflare 우회 — `download_holdings` httpx가 Cloudflare 403, curl는 200. 우회 수단 + `parser_map` `kraneshares` 키 누락 보정 | @backend | CS-EXP | **todo** (downloader 코드 변경) | URL 확보됨(date-based), `etf_csv_downloader.py` |
| CS-EXP-P3 | `_parse_ark_csv` 버그 수정 — 면책행 `ticker=None` → `str(row.get("ticker") or "").strip()`. 수정 시 ARKK/ARKG를 ark 파서로 복귀 가능 | @backend | CS-EXP | **todo** (파서 버그) | `etf_csv_downloader.py:786` |
| CS-EXP-TAN | TAN(Invesco Solar) holdings 소스 — Invesco 다운로드 엔드포인트 403, 공개 직접 CSV 부재. 대안 소스 탐색 필요 | @backend | CS-EXP | **backlog** (소스 부재) | 대안: 타 제공자 holdings 또는 수동 |

---

## Monitor 허브 재건 (구 Thesis Control — D-MONITOR-REBUILD 2026-07-08)

> 구 thesis 앱 **전량 폐기 후 재건**. 아래 TC-* 는 **폐기 앱 대상이라 무효화** → Monitor 신축 P2~P3로 승계.

| ID | Task | Agent | Depends On | Status | Output Artifact |
|----|------|-------|------------|--------|-----------------|
| MON-P1 | 아카이브 + thesis 앱 철거 | orchestrator | ADR | ✅ 완료 2026-07-08 (9커밋, **main 랜딩 `c80783a`** `--no-ff` B안) |
| MON-P2-S1 | Monitor·Claim 모델 + ScopeResolver(종목) + 테스트 | @backend | MON-P1 | ✅ 완료 2026-07-08 (`f9754c7`, apps/monitor 신설, 10 passed) |
| MON-P2-S2 | MonitorIndicator·IndicatorReading·Snapshot 모델 + `_reuse` 엔진 4종 이식 + 테스트 | @backend | MON-P2-S1 | ✅ 완료 2026-07-08 (`e62760f`, 모델 3+엔진 4, 테스트 37 누적, BE _reuse 소진) |
| MON-P2-S3 | 파이프라인 서비스 + `api/v1/monitor/` REST + 실 DB migrate + 테스트 | @backend | MON-P2-S2 | ✅ 완료 2026-07-09 (`e37a87e`, **P2 완결**, 테스트 50, 실 DB 5테이블 적용) |
| MON-P2-BEAT | Monitor 평가 beat 주기 등록 (EOD 창 18:00~18:35 ET 경합 설계 + DB PeriodicTask #28) | @infra | MON-P2-S3 land | ✅ 완료 2026-07-09 (**origin/main `924ef96`** `--no-ff`, 배포+워커등록 검증). `sync_monitor_beat` 멱등커맨드·`refresh_monitors_task`(가드+재시도)·health 13항목·구 thesis 4beat 회수. DECISIONS `D-MONITOR-BEAT`. 첫 발화=평일 18:45 ET | ADR §결정6 |
| MON-P3-S0 | FE 데이터 레이어 (types·monitorService·useMonitor 훅) | @frontend | MON-P2 land | ✅ 완료 2026-07-09 (`d281813`, 브랜치 `sess-monitor-p3`, 테스트 5·tsc 0) |
| MON-P3-S1 | IA-2 리스트 페이지 (서버측 트리아지 정렬·필터 + 스코프/가설만 칩 + 빈상태 CTA + 카드) + MoonPhase·Arrow 이식 | @frontend+@backend | MON-P3-S0 | ✅ 완료 2026-07-09 (`278f7b6`·`ede1160`, FE 14·BE 13·tsc 0, _reuse MoonPhase/Arrow 소진) |
| MON-P3-S2 | 빌더 4단계 + 지표 카탈로그(BE) + FE `_reuse` 완전 소진 | @frontend+@backend | MON-P3-S1 | ✅ 완료 2026-07-09 (`f908188`·`49a3fbe`, 카탈로그 3종+source_key, 빌더 4단계, _reuse 소멸, BE 17·FE 16·tsc 0) |
| MON-P2-INGEST | 지표 판독 이식 — `source_key`→EODSignal→IndicatorReading (백필 N=120일, 멱등 unique 0004, 수동 커맨드 ingest_readings·refresh_monitors) | @backend | MON-P3 land | ✅ 완료 2026-07-09 (`6458da5`, E2E: AAPL score 0.1698·display 실값, 테스트 68·collect 3668). 다음=**MON-P2-BEAT** |
| MON-P3-DISPLAY-FILL | (선택, 급하지 않음) BE `display`에 `fill_percent` 포함(FE `scoreToFillPercent` 흡수) — 달 채움도 API 단일 소스로 | @backend | - | 🕒 선택 과제 | ADR 재계산 원칙 |
| MON-P3-S3 | 전역 내비 6칸+아바타 + My 서브탭 M-3 (+ 실렌더 스모크 3화면 + 캐시 무효화 fix) | @frontend | MON-P3-S2 | ✅ 완료 2026-07-09 (`4222e7e`·`65975f7`, 스모크 통과, vitest 544·tsc 0). **MON-P3 = P3 완결** → 병합 대기 |
| MON-P3-PAGINATE | (조건부 메모) DRF 페이지네이션 도입 시 → IA-2 **칩 카운트를 서버 집계로 전환**(현재 list 전량 반환 전제라 클라 카운트. 페이지네이션 켜지면 카운트 정확성 깨짐 → count 엔드포인트 or `?facets=` 응답). 트리거 = REST_FRAMEWORK `DEFAULT_PAGINATION_CLASS` 도입 | @frontend+@backend | 🕒 트리거: 페이지네이션 도입 시 | ADR §결정5 |

> **MON-P3 완료 판정(DoD)**: 단위 테스트(FE vitest·BE pytest·tsc 0) **+ dev 서버 실렌더 스모크 3화면**(리스트 IA-2 / 빌더 4단계 / 전역 내비) — auth 세션 하 실제 브라우저 렌더 확인(좌표 아닌 실 렌더, lesson_visual_verify). 스모크 미수행 시 P3 미완결.
>
> **FE 스모크 정식 항목(MON-CLOSE 추가, 2026-07-13)**: 위 3화면 + **① 대화형 빌더로 두 번째 모니터를 실제 생성**(빌더 4단계 관통 → 생성 후 목록에 반영 확인 — 회귀 시 빌더 경로 생존 보장) + ② authed 픽셀: 데이터 보유 모니터 카드의 StateBandSparkline 렌더(색 밴드+선). 빌더 실사용 검증은 owner 세션에서 수행(owner-scoping).
| MON-P4 | 시장/섹터 scope — shared 수집 태스크 신설(EOD 창 경합 명시) | @backend+@infra | MON-P2 | todo | - |
| MON-P5 | 테마 바스켓(편집 UI + EODSignal 내부 집계) | @backend+@frontend | MON-P4 | todo | - |
| MON-P6 | 펀드 scope (ETF만, 공모펀드 보류) | @backend | MON-P5 | todo | - |
| MON-CLOSE-UX | 마감 UX — 카드 삭제 버튼·마감(종단) 모니터 숨김/접힘 | @frontend+@backend | 🕒 트리거: 첫 실마감 발생 시 (목업 선행 결정 사이클) | - |
| EOD-FRESH | beat 자가 신선도 게이트(B안) — 비편입 보유 종목 DailyPrice 온디맨드 보충 + IONQ/TLN 백필 | @backend | EOD-RECON | ✅ 완료 2026-07-30 (`sess-eod-fresh`, `ensure_price_freshness` @ pipeline 서두, 신규 모델·태스크 0, monitor pytest 226). Phase0 백필 IONQ/TLN 236→266·손익 정정. DECISIONS `D-EOD-FRESH`. A안 승격=추적>30 or 2번째 소비앱 | D-EOD-FRESH |
| ~~TC-3~6~~ | ~~대화형빌더·지표설정·관제실·알림마감~~ | - | - | ❌ 무효 (폐기 앱) → MON-P3 승계 | - |
| MON-P3-ALERT | 전이 알림·다이제스트·상태밴드 스파크라인 (AlertEvent + 인앱 벨 + 이메일 + FE 스파크라인) | @backend+@frontend+@infra | MON-P2-BEAT land | ✅ 완료 2026-07-09 (land `8433fe1`). **배포 완료 2026-07-13**(FIRSTFIRE Case A green → sv sync + migrate 0005 + env `MONITOR_ALERT_RECIPIENT` + 재기동, ALERTFIRE 첫 알림코드 무인 발화 alerts=0 정상). DECISIONS `D-MONITOR-ALERTCLOSE` | ADR §결정1~4 |
| MON-CLOSE | Monitor 검증 단계 4 DoD 종결 + 부수 정리 5건 + 결정 봉인 | @infra+@frontend | MON-P3-ALERT 배포 | ✅ 완료 2026-07-13 (`monorepo/mon-close`). 4 DoD 완결(authed 픽셀=goid545 세션 스파크라인 렌더)·63fa58cb 삭제·라벨 Thesis→Monitor·T-1 정정 각주·common-bugs #51·빌더 스모크 항목화. OWNERFIX 폐기. DECISIONS `MON-CLOSE` | - |
| MON-CLOSE-UI-P1 | 마감 데이터·엔드포인트 (BE) — Claim verdict/회고/동결 + close 액션 | @backend | MON-CLOSE-UI RECON | ✅ 완료 2026-07-13 (`monorepo/mon-close-ui-p1`). ClaimIndicatorResult·ClosureSnapshot·Claim 회고필드(migration 0006 additive)·propose_verdict(±0.333)·close-preview/close 액션. 엔진·beat·shared 불변. DECISIONS `D-MONITOR-CLOSE-UI-P1`. **실 DB migrate 0006은 배포 단계** | - |
| MON-CLOSE-UI-P2 | 마감 FE — `/monitor/[id]` 상세·CloseModal·VerdictBadge·마감 필터탭·동결 카드 | @frontend | MON-CLOSE-UI-P1 | ✅ 완료 2026-07-14 (origin/main `468e29a`, 배포됨). 상세(dangling 해소)·A-1 모달·B-1 세그먼트·동결카드. tsc0·vitest660. 실 DB 0006 선제적용. **갭: ClosureSnapshot 미노출→동결점수 live 근사**(BE 후속 후보). 스모크: dangling해소·모달렌더·콘솔0·실데이터 무변경 | - |
| MON-CLOSE-UI-P1.5 | 동결값 노출(ClosureSnapshot) + FE 우선 표시 + throwaway E2E | @backend+@frontend | MON-CLOSE-UI-P2 | ✅ 완료 2026-07-15 (origin/main `6013865`, 배포됨). ClaimSerializer closure_snapshot nested(마이그레이션0)·frozenScore 우선순위·throwaway E2E(빌더→마감 확정→동결카드 0.000·적중배지·세그먼트 양방향→정리 아티팩트0, c9be8802 불변). **MON-CLOSE-UI 트랙 최종 종결**. DECISIONS 종결선언 | - |
| TIMING-P0 | RECON(실측 전용): Claim 확장지점·state_machine 재정의 가능성·지표 프리셋 EOD 산출가능성(200일SMA·12M수익률·52주고가 소스 전수)·라벨 전수 | @backend | D-MONITOR-TIMING-PIVOT | 🟢 착수 가능(다음 트랙) | ADR §7.1 — 코드 변경 0 |
| TIMING-P1 | 의미 피벗(BE): Claim 가격 시나리오 필드 additive·프리셋 등록·진입 매력도 재해석·verdict 익절/손절/기한만료 매핑 | @backend | TIMING-P0 | 🕒 예약 | 엔진·마감루프 구조 불변, additive-only |
| TIMING-P2 | 어휘 피벗(FE): 상태·알림·카드·빌더 언어 행동어화, 빌더="가설작성"→"매수 시나리오 작성"(진입가·목표가·손절가·기한·신호) | @frontend | TIMING-P1 | 🕒 예약 | 라벨 전수 교체 + 스모크 |
| TIMING-P3 | (백로그) 마감≥20건 후: 밴드 재조정·지표별 승률·백테스트 착수 결정 · **E계열(차트패턴·캔들 탐지=신규 기계 최초구현) 착수 결정 사이클** | (미배정) | TIMING-P2 + 마감≥20 | 💤 백로그 | §5.3 E계열 격리, 근거 혼재(캔들 부정 Marshall 2006) |
| MON-VIZ-ROTATIONMAP | 모니터 회전 맵(RRG 동형 2축 분포) — 상태밴드 스파크라인의 후속 시각화 | @frontend+@backend | **착수조건: 활성 모니터 ≥5** | 🕒 예약(조건 미충족) | ⚠ market_pulse 컴포넌트 **직접 import 금지** — shared 승격 vs 재구현은 착수 시 결정(D-MONITOR-ALERTCLOSE 1b) |
| MON-WALLET | Wallet 금융 API(증권사) 연동 — **별도 트랙**(본 프로젝트는 My 서브탭 자리+thesis 접점만) | (미배정) | - | 💤 별도 트랙 | ADR §결정7 |

---

## 테스트 부채 상환 — pytest 선존 실패 120건 (MON-P2-BEAT §0에서 고정, 2026-07-09)

> **출처**: MON-P2-BEAT preflight에서 전체 pytest 베이스라인 실측 → `18 failed / 102 errors = 120건` 선존 확인(전부 `apps/monitor` disjoint, 신규 회귀 아님). **SSOT 스냅샷** = [`docs/harness/pytest_baseline_failures.md`](../docs/harness/pytest_baseline_failures.md). 세션 게이트가 "green" 대신 **"이 베이스라인 대비 델타 0"**으로 판정되도록 고정. 상환 시 SSOT 목록에서 개별 삭제(줄어드는 방향으로만).

| ID | Task | Agent | Depends On | Status | Output Artifact |
|----|------|-------|------------|--------|-----------------|
| DEBT-TEST-BOUNDARY-LLM | `test_news_deep_analyzer`(102e) + `test_csv_url_resolver`(4f) mock을 **shared LLM 래퍼 seam으로 재작성** (옛 `patch('...genai')` → 래퍼 mock). 근본원인=BOUNDARY-LLM 이관으로 직접 genai import 제거, 코드 정상·테스트 stale | @qa+@rag-llm | - | **🏁 종결 2026-07-13 (지시서⑫ C2)** | seam genai→`complete` 재작성(응답 설정 관성 보존 trick), init 테스트는 제거된 genai.Client 계약 대신 실제 키검증 계약으로 강화. + `test_multiple_symbol_fetches`(S5 키-env) provider 주입으로 env-독립화. **env -i 격리서 deep_analyzer 102 + csv 28 + entity_dedup 1 = 131 green, 은폐(skip/xfail/삭제) 0** |
| DEBT-TEST-CHAINSIGHT | `test_attention`(6f, `assert 'SEMICON' in []`) + `test_leadership_api`(7f, `404==200`) + `test_upward_learning`(1f) = 14f. **pristine 체크아웃 재현으로 판정** — 오탐(stale `_dormant`+공유 test DB, lesson_...)이면 격리 픽스처/시드, 진성이면 코드 수정 | @qa+@backend | - | todo | SSOT C3·C4 |

> **판정 원칙**: DEBT-TEST-CHAINSIGHT는 `.claude/worktrees/`의 stale 워크트리·`_dormant` 잔재가 공유 test DB를 오염시킨 오탐일 수 있음(메모리 `lesson_visual_verify`가 아닌 stale-artifact lesson) → **pristine 격리 체크아웃에서만 진위 확정**. DEBT-TEST-BOUNDARY-LLM은 시그니처가 명확(genai attr 부재)해 즉시 착수 가능.

---

## shared 경계 부채 소진 (#31 / 2026-06-01)

| ID | Task | Agent | Depends On | Status | Output Artifact |
|----|------|-------|------------|--------|-----------------|
| BOUNDARY-1 | ~~shared → apps.market_pulse.utils.circuit_breaker 2건 청소~~ | @backend | - | **done** (2026-06-01, `d30915e`) | circuit_breaker → `packages/shared/api_request/` 승격으로 자연 해소. `KNOWN_VIOLATIONS` 2건 동시 삭제 완료. burn-down 5→3. |
| BOUNDARY-2 | ~~shared → apps.chain_sight.models 1건 청소~~ | @backend | - | **done** (2026-06-01, `80b9280`) | Django `apps.get_model("chainsight", "CompanyChainProfile")` 동적 lookup으로 정적 import 제거 (cross-app aggregator 표준). `KNOWN_VIOLATIONS` 1건 동시 삭제 완료. burn-down 3→2. |
| BOUNDARY-3 | ~~shared → macro.models 2건 청소 (eod_regime_calculator, eod_pipeline, lazy)~~ | @backend | - | **done** (2026-06-04, merge `a9bb229`, slices `[33e5437, 7b6572f, 73861d4, 662fdc4]`, brunch `monorepo/sess-market_pulse`) | 방향2(의존 역전 + 등록 패턴) 채택. `VIXProvider` 포트(`packages/shared/stocks/services/vix_provider.py`) + `MacroVIXProvider`(`apps/market_pulse/services/macro_vix_provider.py`) + `MarketpulseConfig.ready()`에서 `register_vix_provider`. 모델 이동 0 / makemigrations No changes / 회귀 302 GREEN / `KNOWN_VIOLATIONS` 양쪽(tests + health_check) 동시 삭제로 burn-down 2→0. |

> ~~우선순위 1 = `BOUNDARY-1` (top-level이라 가장 위험).~~ **트랙 전체 종결 (2026-06-04, burn-down 5→0)**. 잔여 0건. 동결 추적은 야간 `docs/harness/boundary_ledger.jsonl`에 0 라인이 누적되어 추세 우하향 안정.
> 청소 절차: `docs/harness/SHARED_BOUNDARY_GUARD.md` "소진 절차" 참조 — 향후 새 위반 발견 시 동일 절차 + 본 트랙 close 이후 표준이 된 패턴(common-bugs #31 "패턴 정착").

---

## Iron Trading 출구 (integrations/iron_trading)

> 입력: `docs/trading_bot_api/api_decision_handoff.md` §2-B. 본 트랙은 stock_vis 소유 항목만. verify-first 결정·소비자 구현 지시서는 iron_trading 소유(별 repo).
> 관련 결정: `DECISIONS.md "iron-trading 출구 엔드포인트 STEP 0 발견 — 이미 main 라이브 (2026-06-04)"`.

| ID | Task | Agent | Depends On | Status | Output Artifact |
|----|------|-------|------------|--------|-----------------|
| IT-1 | iron-trading daily-context 라이브 검증 세션 (read-only): 서버 기동 → 실측 200 응답 1건 → 동봉 샘플(`docs/trading_bot_api/samples/200_daily_context_2026-05-22.json`)과 필드 대조(captured_at·snapshot_id 제외) → 에러 샘플(404/400/503) 확인 | orchestrator | - | todo | 검증 로그 (경로 미정) |
| IT-2 | `docs/trading_bot_api/handoff_codex.md` 옛 경로(`iron_trading/`) + 옛 commit(`8c21a52`) → 현재 경로(`integrations/iron_trading/`)로 정리. **수정 전 STEP 0로 실제 경로·commit 재확인(휘발성 — 베이크 금지)** | @backend | - | todo | `docs/trading_bot_api/handoff_codex.md` |
| IT-3 | [보류] 엔드포인트 보강 — 봇이 실제로 필요로 할 때까지 착수 금지. 후보: (a) `exchange` 매핑(현재 광범위 null), (b) `earnings_within_14d` 정확화(현재 `latest_quarter + 90일` 휴리스틱 → 실적 캘린더 기반 — **CalendarEvent(EARNINGS) 소비로 해소 예정, EVT 트랙 참조**), (c) `themes[].tone` 활성화(현재 `"neutral"` 하드코딩 → `CompanyNarrativeTag.narrative_sentiment` 매핑), (d) 다중 유니버스(`us_total` 등, 현재 `us_core`만) | @backend | - | hold | - |

---

## Nightly 트리아지 추적 (git 밖 발견 ↔ git 안 변경)

> 야간 메일 보고서(`~/stock-vis-nightly/reports/YYYYMM/DD/`)의 발견 1건은 분류 → 본 표 등록 → 처리.
> 보고서엔 git 히스토리가 없다 → **처리 추적은 harness가 유일선** → 분류한 발견은 전부 등록 (기각/보류 포함).
> 분류·라우팅 규칙: `DECISIONS.md "Nightly 메일 트리아지 라우팅 규칙 (2026-06-03)"` 참조.

**상태**: `신규` / `라우팅됨` / `진행` / `보류` / `완료` / `기각`
**컬럼 정의**:
- `출처보고서`: `YYYY-MM-DD/섹션명` (예: `2026-06-03/CRITICAL`)
- `분류`: `ops` / `app(<앱명>)` / `shared` / `HALT`
- `목적지`: `ops` 풀 지시서 / `<앱> Claude Project` / `사용자 수동`
- `트리거(보류시)`: 재개 조건 명시 (예: "shared 행위변경 합의 후")
- `처리세션/커밋`: 완료 시 커밋 해시 — **git 밖 발견 ↔ git 안 변경**을 잇는 유일한 끈
- `baseline`: `🆕신규` / `⬆️악화` / `➡️유지`

| ID | 등록일 | 출처보고서 | 분류 | 목적지 | 상태 | 트리거(보류시) | 처리세션/커밋 | baseline |
|----|--------|-----------|------|--------|------|---------------|--------------|----------|
| NT-1 | 2026-06-04 | 2026-06-04/야간자동화 | ops | 📎 `docs/nightly_auto_system/triage/NT-1_nightly_duplicate_run.md` | **완료(재분류)** | - | STEP 0 → 자동화 정상, 메일 본문 표시 버그 (사용자 손 영역) | 🆕신규 |
| NT-2 | 2026-06-04 | 2026-06-04/뉴스LLM | ops (운영) | 📎 `docs/nightly_auto_system/triage/NT-2_llm_analysis_rate_drop.md` | **완료** | - | 좀비 종료(56586/91784) + launchd 재기동(PID 17499) + import 경로 미스매치 해소 검증 (16:17 KST) | 🆕신규 |
| NT-2b | 2026-06-04 | NT-2 후속 | app(news) | apps/news Claude Project | 신규 | - | - | 🆕신규 |
| NT-7 | 2026-06-04 | 2026-06-04/marketpulse | ops (운영) | 📎 § NT-7 종결 (본 파일 하단 §) | **완료 2026-06-06** | - | Bug #28 Beat drift + 좀비 beat 56670 이중 디스패치. ORM UPDATE 11 row(`task` 컬럼) + 좀비 종료 + 정상 beat 재기동(15151→86614). 검증: regime/anomaly 새 경로 succeeded, unregistered ∆=0(1705 후 06-07 신규 0건), 회귀 302 passed, 코드 diff 0. | 🆕신규 |
| NT-8 | 2026-06-04 | NT-2 부산물 | ops (보고서) | 📎 `packages/shared/metrics/services/daily_report.py` + `templates/email/daily_report.html` + `tasks.py` | **완료** | - | 퍼널 N→M→K→J + 실행건강 J/K + 점수 기록률 M/N + null률 NT-2b 포인터. 6/3 K=3·J=3 재현. pytest 132 passed. | 🆕신규 |
| NT-9 | 2026-06-06 | 2026-06-06 archive 시스템 | ops (인프라) | 📎 `packages/shared/metrics/services/daily_report.py` `save_mail_archive()` + `.gitignore` `mail_archive/` | **완료** | - | 메일 발송 직후 `mail_archive/YYYY/MM/DD.md` 마크다운 사본 저장. best-effort(메일·archive 독립). assistant Read 직접 트리아지 자동화. 6/6 archive 5695B 생성 검증. | 🆕신규 |
| NT-10 | 2026-06-06 | 2026-06-06 메일 2회 발송 | ops | ops | **NT-10/7 진단 → kill실행→검증(6/7)** | - | STEP 0 = TaskResult 2 SUCCESS (07:00 + 07:06 KST 매일), Beat 1회만 발사, worker는 2회 received. 원인 = 좀비 Beat 56670 (PPID 13862 살아있음, cwd=`~/.Trash/stock_vis.icloud_backup.20260516_144329`, default scheduler). kill 완료(21:30). 6/7 07:00 메일 1통 검증 대기. 📎 DECISIONS "좀비 Beat 56670 (2026-06-06)" / common-bugs #33. | 🆕신규 |
| NT-11 | 2026-06-06 | beat_schedule_audit | ops | ops(+shared) | **NT-10 후속 / 가드범위 결정대기→git지시서** | - | NT-11-1(validation-weekly-batch DB 미등록) STEP 0 = 이미 DB 등록·정상 작동 중(last_run=6/6 09:00 UTC, total_run=8). 무효(no-op). 잔여 가드 트랙: 다중 Beat 감지(origin/cwd 기반) + 옵션 없는 beat 알림 — 가드 코드 구현 위치(`config/tasks.py` 또는 watchdog 셸 또는 daily report 섹션) **결정 대기**. NT-11-2/3/4(refresh-korean-overviews-monthly RPD / sec-sync-dirty-neo4j */5 / 장중 동시 발사)는 운영 결정 대기 별도 보류. | 🆕신규 |
| NT-11c | 2026-06-10 | NV-1 후속 | ops | `scripts/health_check.py` | 보류 | NT-11b 착수 시 같은 세션에서 묶어 구현 | **health_check.py에 Neo4j 연결 점검 추가** — `RETURN 1` 인증 확인 + `count(n)` 노드 수 보고를 health_check 항목으로 추가. 시크릿 마스킹 정책 준수(`len + head 4자`만). 비밀번호는 `.env`에서 환경변수 경유 전달 — cmdline 평문 금지(NV-1 STEP 2 패턴 재사용). **배경**: 2026-06-10 NEO4J_PASSWORD 회전 검증(NV-1)에서 health_check.py가 Neo4j를 점검하지 않음이 드러남(문서·git 정합만 점검). 자격증명 회전 실수·컨테이너 다운 시에도 "health_check 통과"가 나와 거짓 안심을 줌. **연계**: NT-11b와 동일 파일 → 묶어 구현. 우선순위 = NT-11b 동급(보류). **수용 기준**: ① Neo4j 컨테이너 down → FAIL/WARN ② up → 노드 수 출력 ③ 어떤 출력 경로에도 시크릿 풀 값 0. | 🆕신규 |
| NT-12 | 2026-06-23 | 2026-06-23/대시보드 보고서없음 | ops | `~/stock-vis-nightly/publish_reports.sh` + `run_tier3_audits.sh` 배선(사용자 수동) | **진행** | 인증 A(NT-13) 선결 — 발행 살아도 생성 죽으면 신규 0 | **B-2 발행 단계.** 격리 worktree 리포트 → reader read 경로 단방향 복사. 스크립트 작성 + 6/18·19 backfill(각 12/12, reader 인식 검증 완료) + `.gitignore` 발행본 무시(로컬 커밋). 잔여 = nightly 커밋 phase 다음 1줄 배선(사용자 수동). 📎 DECISIONS "[2026-06-23] B-2 발행본 = 미추적 + gitignore" | 🆕신규 |
| NT-13 | 2026-06-23 | 2026-06-23/tier3 로그 401 | ops | 사용자 수동 (`claude setup-token` + plist `ANTHROPIC_API_KEY`) | **신규(라이브 블로커)** | - | **인증 A.** `run_tier3_audits.sh`의 `claude -p` 호출이 6/20~22 전부 `401 Invalid authentication credentials` → 12 audit 생성 0건. 키체인 OAuth가 launchd 비대화형에서 만료/무효. 처방: 장기 토큰 발급 후 `com.stockvis.nightly.plist` EnvironmentVariables에 `ANTHROPIC_API_KEY` 주입 → unload/load. B-2(NT-12)와 독립. | 🆕신규 |
| NT-14 | 2026-06-23 | NT-12 후속 | ops | 사용자 결정 (선택) | **보류(선택)** | B-2 안정화 후 git 위생 정리 원할 때 | **역사 리포트(≤6/16) 선택 정리.** pre-6/16 리포트가 main에 추적(커밋)된 상태로 잔존 — MAIN-SYNC-FIX 이전 안티패턴 잔재. `git rm --cached docs/nightly_auto_system/reports/<역사경로>`로 untrack 가능(파일 보존). **선택 사항** — 안 해도 기능 무영향(gitignore가 신규만 차단). 사용자 명시 지시 전까지 미실행. | ➡️유지 |
| NT-15 | 2026-06-23 | STEP 0-6 발견 | ops | 사용자 결정 (범위 밖) | **보류** | - | **`monorepo/nightly-reports` 브랜치 처분.** STEP 0 실측 = 집계 타깃 아님(feature 커밋 최신, reports 16일까지뿐 = stale 일반 브랜치). B-2 미사용 확정. 브랜치 자체 삭제/정리는 본 트랙 범위 밖 — 파괴적 작업이라 후보만 등록. | 🆕신규 |
| NT-16 | 2026-06-23 | investigate 부산물 | ops | `agent_reports.py`/`daily_report.py` + 인프라 (NT-11c 연계) | **신규** | - | **이메일 배달 메커니즘 + neo4j down 건강 점검.** ① 대시보드 메일 발송부가 LaunchAgents·daily_report.py grep에 안 잡힘 → 배달 경로 불명확, 확인 필요. ② `neo4j_alive False`(launchd에 neo4j 잡 0) — 실제 down. ③ TL;DR `beat=DOWN` vs 상세 `celery_beat_alive True` 키 표기 불일치(`collect_system_health`). neo4j 건강은 NT-11c와 묶어 처리 권장. | 🆕신규 |
| NT-3 | 2026-06-04 | 2026-06-04/노드속성 | app(chainsight) | 📎 `triage/NT-3to6_app_stubs.md` § NT-3 → chainsight Claude Project | 라우팅됨 | - | - | 🆕신규 |
| NT-4 | 2026-06-04 | 2026-06-04/관계균형 | app(sec_pipeline) | 📎 `triage/NT-3to6_app_stubs.md` § NT-4 → sec_pipeline Claude Project | 라우팅됨 | - | - | 🆕신규 |
| NT-5 | 2026-06-04 | 2026-06-04/구조분석 | app(chainsight) | 📎 `triage/NT-3to6_app_stubs.md` § NT-5 → chainsight Claude Project | 라우팅됨 | - | - | 🆕신규 |
| NT-6 | 2026-06-04 | 2026-06-04/뉴스커버 | app(news) | 📎 `triage/NT-3to6_app_stubs.md` § NT-6 → news Claude Project | 보류 | NT-2 분석률 회복 후 재평가 | - | 🆕신규 |

**STEP 0 부산물 (2026-06-04)**:
- **NT-7 신규 발견** (NT-2 STEP 0 중): `~/Library/Logs/stockvis/celery-worker-error.log`에서 `marketpulse.tasks.regime.mp_calc_regime_15min` + `mp_detect_anomaly_5min` 반복 retry — `FileNotFoundError(2, 'No such file or directory')`. 분류: app(market_pulse), 영향: 5분 단위 시그널 누적 미생성. 별도 STEP 0 후 핸드오프 예정.
- **NT-2b 신규 등록** (NT-2 조치 후): import 미스매치는 해결됐으나 Tier A 임계 0.7이 너무 빡빡(어제 349건 중 3건만 통과 = 0.86%). importance_score null률도 41~68%. 분류: app(news), 한 줄 문제 = "Tier 임계 + ML 채움률 동시 조정 필요", STEP 0 = 임계 통과율 회복(예: 0.5 임계 시 일일 분석 가능 수) 시뮬레이션. 행위보존 = 기존 Tier B/C 로직 손상 금지.
- **NT-8 신규 등록** (NT-2 조치 후 발견): Daily Report 본문의 "LLM 분석률" 지표가 `전체 24h 신규 ÷ 분석`으로 계산 — 시스템 설계(Tier A+ 임계 분석)와 분모/분자 정의 불일치. 보고서 본문 생성 측 보정 필요(사용자 손 영역, `run_tier3_audits.sh` 메일 빌드 또는 별도 본문 빌더).

**2026-06-06 회차 신규 발견**:
- **NT-9 (완료)**: 메일 복붙 부담 → `mail_archive/YYYY/MM/DD.md` gitignored 마크다운 사본 자동 저장. assistant가 `Read /Users/byeongjinjeong/Desktop/stock_vis/mail_archive/<오늘>.md` 로 직접 읽음.
- **NT-10 신규**: 6/6 회차에 동일 보고서가 2회 발송됨 (N=852 / N=840 약 1분 차이). Beat 스케줄은 `metrics-daily-report-7am-kst` 단일이고 cron 비어있음 → `send_daily_report_task`의 `max_retries=2` 또는 워커 재기동 시점 재실행 의심. STEP 0: 워커 로그(`celery-worker.log`)에서 task_id 별 호출 횟수 + retry 흔적 확인.
- **NT-11 신규**: `beat_schedule_audit` 자체 보고서가 발견한 4건 위험.
  - 🔴 `validation-weekly-batch` config dict만 존재 (DB 미등록, 버그 #28 정확 해당) → 주간 배치 자동 실행 미보장
  - 🔴 `refresh-korean-overviews-monthly` 03:00 ≈500 call → RPD 폭발 위험
  - 🔴 `sec-sync-dirty-neo4j` */5 + solo pool → 백로그 누적
  - 🟡 장중 `*/5` 동시 발사 충돌 (`update-realtime-prices` + `update-market-indices`)
- **NT-2b 우선순위 상승**: importance_score null률 5/29(99%) → 6/4(84%) → 6/5(82.7%) → 6/6(80.1%) 정체. 수집 N은 315→852로 2.7배 증가했는데 채움 절대값은 비례 증가 안 됨 → ML/규칙 엔진 처리량 한계. apps/news 핸드오프 우선순위 ↑.

**발견 상세 (요약)**:
- **NT-1**: 야간 보고서 22개 = 11종 ×2 흔적 (첫 12종 + 두 번째 10종, performance/security 누락). 자동화 중복 트리거 의심(launchd + cron 동시 등록 / 수동 재실행). → ops STEP 0: `launchctl list | grep stockvis` + `crontab -l` 동시 등록 여부 확인.
- **NT-2**: 24h 신규 뉴스 315건 중 LLM 분석 3건만 완료, 312건 pending(분석률 1.0%). Gemini paid tier 할당량 / Celery 큐 잠금 / retry backoff 의심. → ops STEP 0: `celery inspect active` + Gemini 콘솔 quota + `news.tasks` retry 로그 확인.
- **NT-3**: Stock 속성 채움률 `business_model_type=0.0%`, `overall_grade=0.0%`, `theme_tags=0.0%` + ChainProfile 미생성 31종목. 모델 필드 추가 후 backfill 미수행 의심. → chainsight 스텁: 한 줄 문제 = "신규 3 필드 + 31 종목 미생성", STEP 0 = "필드 추가 시점·calculate_all_profiles 동작 여부", 행위보존 = "기존 채움 데이터 손상 금지".
- **NT-4**: SUPPLIES_TO 61개 (vs PEER_OF 8674), UnmatchedCompanyQueue 1011건 pending. 상위: Flex Ltd. ×4, Compuware ×4, Adyen ×3, JERA ×3, Mitsui ×3. → sec_pipeline 스텁: 한 줄 문제 = "alias 매핑 미흡 → SUPPLIES_TO 추출률 저조", STEP 0 = "상위 빈도 회사명 수동 alias 룰 / fuzzy threshold 검토".
- **NT-5**: 고립 Stock 5종목 (관계 0). calculate_price_co_movement + update_relation_confidence 누락. → chainsight 스텁: 한 줄 문제 = "5종목 관계 0", STEP 0 = "심볼 식별 + 가격 데이터 존재 여부", 행위보존 = "관계 임계값 변경 금지".
- **NT-6**: 24h 뉴스 커버 51/535=9.5%, 미커버 484종목. → news 스텁: 한 줄 문제 = "종목 단위 수집 제약", STEP 0 = "Finnhub/MarketAux 종목별 vs sector broadcast 비용·rate limit 비교".



## NT-7 — marketpulse Beat schedule drift + 좀비 beat  [완료 2026-06-06]

- 증상: ① unregistered KeyError(regime 등) = Beat DB의 PeriodicTask 11개 task 컬럼이 옛 경로 `marketpulse.tasks.*` (코드는 `apps.market_pulse.tasks.*`). ② FileNotFoundError(anomaly) = 좀비 워커가 옛 yaml 경로 stat 실패 — 좀비 워커 사망으로 이미 정지(613).
- 원인: 코드 경로 이동(PR4) 후 Beat DB 미동기화(Bug #28 drift) + 인터랙티브 zsh에서 띄운 좀비 beat(PID 56670)가 정상 beat(15151)와 동시 가동(이중 디스패치).
- 처리세션(운영 안정화, 코드 0): (B) `kill -TERM 56670` → (A) Django shell ORM UPDATE 11 row(`task` 컬럼만, 옵션②) → 정상 beat 재기동(15151→86614) → 수동 트리거 검증(regime LATE_BULL 0.14s / anomaly CALM 0.09s, 둘 다 새 경로 succeeded). ※ `sync_beat_schedule`은 무용(marketpulse는 `setup_marketpulse_beat`로 DB 직접 등록).
- 검증: unregistered ∆=0 (1704→1705 후 정지, 06-07 신규 0건), FileNotFoundError 613 정체, 좀비 0 / 정상 1셋, `git diff` 빈 결과, 회귀 302 passed.
- 분기: D1(옵션3)대로 intraday 잔류, 구조 이동(STRUCT-CLEANUP)은 DORMANT 유지.

> 기각·보류는 `DECISIONS.md`에 "왜"를 남긴다(미래 세션 오해 방지). 표 행에는 결정 링크/커밋만 박는다.

---

## Trash 청산 트랙 후속 (TR-3/4/4b/NV-2 / 2026-06-11)

> 2026-05-16 `~/.Trash/stock_vis.icloud_backup.20260516_144329` 박제 셸 cwd에서 좀비 Beat 발생(NT-10) → Trash 트리 청산 + 시크릿 전수 회전(FMP `KF9E`→`qA1W` / Anthropic 재발급 / NEO4J `rByK`→재회전) + `.env` 소비자 4종 재기동 완료. 본 표는 청산 트랙의 잔여 후속 9건.

| ID | Task | Agent | Depends On | Status | Output Artifact |
|----|------|-------|------------|--------|-----------------|
| TRASH-1 | `archive/trash-20260516/*` 로컬 태그 5건 — **90일 후(2026-08-14) 처분 검토**. 원격 미push 유지. | orchestrator | - | hold | 재검토일 2026-08-14 |
| TRASH-2 | Trash test 묶음 3건 **cherry-pick 평가 → Tier 2 연계** (~1,662줄, 5/16 기준). 흡수 가치 판정 후 채택/폐기. | @qa | TRASH-1 | todo | - |
| TRASH-3 | **slice8 PROGRESS 정합** — 종결 기록 vs 미흡수 tip 2건 규명 | @qa | - | todo | PROGRESS.md |
| TRASH-4 | **untracked 보존 파일 3건** (`docs/etc/`, `docs/trading_bot_api/{api_decision_handoff,consumer_directive}.md`) commit 여부 결정 | orchestrator | - | todo | - |
| TRASH-5 | **PROGRESS.md L25 stale 해시 갱신** | orchestrator | - | todo | PROGRESS.md |
| TRASH-6 | **Trash 트리 사건 종결 기록** — origin(셸 cwd 박제) + 조치 요약 + D 포렌식 링크 | orchestrator | - | todo | DECISIONS.md |
| TRASH-7 | **worker 로그 FMP 키 평문 기록** — 로그 마스킹 검토 (저위험·위생). 구 `KF9E` 키는 이미 401 dead. | @infra | - | todo | - |
| TRASH-8 | **LLM 인증 실패 가시화** — health_check 기동 ping 검토 (NT-11c 묶음). Anthropic/FMP 키 회전 누락 시 조기 감지. | @infra | NT-11c | todo | `scripts/health_check.py` |
| TRASH-9 | **`.env` 소비자 4종 launchd 일원화** — worker/beat/worker-neo4j는 launchd, daphne만 수동 기동 → daphne plist 등록으로 다음 회전 = `kickstart 4건`. 소비자 목록 문서화. | @infra | - | todo | LaunchAgents + 문서 |
| TRASH-10 | **마스킹 로그 스캔 표준 스크립트 작성** (`scripts/scan_logs_masked.py`) — raw 로그 직접 grep 금지의 구조적 대체. 시크릿 패턴(apikey/api_token/password 등 쿼리파라미터·헤더)을 **값 진입 전 차단**(Python에서 파싱·마스킹, 셸 파이프 미경유)하는 방식. 배경: NV-2/TR-5 마스킹 슬립 2회(`ps\|tr\|sed`, `sed`가 `api_token=` 누락) → 구조적 재발 방지. | @infra | - | todo | `scripts/scan_logs_masked.py` |
| TRASH-11 | **worktree 2건 거취 — DEAD 확정·remove 완료** (TR-7/8 정정). 기존 ALIVE 판정은 **stale 로컬 main 기준 오판**이었음. TR-8 STEP1: unique 커밋 5건(f483634/d4a9690/ce0be51/0b8399a/ef9d064) **전건 origin/main(d5212d4) REACHABLE = DEAD**. `sess-mgmt-phase1-catalog`·`sess-mp-phase1-cleanup` 디렉토리 소멸 + worktree registry 제거 완료(세션 간 외부 선제거, prune 정합). **잔여 결정**: 브랜치 2건 삭제 — 커밋이 origin/main 도달이나 **로컬 main 미도달**이라 `-d` 거부 예상 → 사용자 수동 `-D` 또는 `pull` 후 `-d`. + `sess-mp-kl-f1f3` 머지 시 `82afddb`(TASKQUEUE 9건) 중복은 main `cb5473e`와 동일 → 충돌 시 main 채택. **+ `monorepo/sess-mgmt-llm-decision`(cbc6041, BOUNDARY-LLM 기록): origin push됨·미머지 → consolidation 시 main 머지 후 브랜치 삭제 대상.** **push/pull 통합 결정과 묶음**. | orchestrator | - | todo | 브랜치 삭제 + push/pull 통합 |
| TRASH-12 | **sess-hold-p1 폐기 전 6커밋 main 안착 실측** — 현 공유트리 브랜치 `monorepo/sess-hold-p1`이 origin/main 대비 **+6커밋 미머지**: HOLD-P1 3커밋(`4c92049`·`710520e`·`02cce32`) + 타 커밋 인터리브 `e37b2c7`(leftnadal D2) + verify repoint 지시서 `b8d767aa` + research foundation `6973bda`. HOLD-P1 정합은 별도 worktree `sv-hold-p1-integrate`(origin/main `9f2e6c5` 기반 cherry-pick `4c47744`·`a41a5da`·`54cccc0`)서 처리. **폐기는 메모리 아닌 실측 확인 후**: 6커밋 전건이 origin/main 도달(cherry-pick 등가 포함) 실측 → 인터리브 `e37b2c7`·research `6973bda` 별도 거취 확인 → 그 후 브랜치 삭제. **병진 수동**. | orchestrator | - | todo | 6커밋 main 안착 실측 → 삭제 |
## market_pulse v2 Phase 2 로드맵 (2026-06-23 진입 순서 확정)

> 근거: `DECISIONS.md` "[2026-06-23] Phase 2 진입 순서"·"Alerts 트랙 경계 = O3 하이브리드". Phase 1 종료(코어 대시보드+Translation+화면게이트 조건부통과) 후 진입. 순서 = Analog → Alerts → sub-pages → 데이터게이트(FedWatch/GEX) → cross-surface(게이트). P2 roadmap recon(2026-06-23, [E]~[H]) 기반.

| ID | Track | 우선 | Agent | Status | 근거/게이트 |
|----|-------|------|-------|--------|------------|
| MP2-ANALOG | historical regime matching(유추 분석) — 현재 regime 입력 vs 과거 유사 국면 매칭 + **MOVE 동봉**. **채택 설계**(un-dorm 시) = 입력벡터 z-정규화 최근접(라벨 매칭 아님, D-ANALOG-GATE) | **#1** | @backend | 🟢 **UN-DORMANT (2026-07-10, B1-S2-FIRE)** — B-1 소급 백필 완료로 트리거 (a)(b) 동시 충족: 완전벡터 **683행**(구 22)·비-LATE_BULL 475일(TRANSITION469+CRISIS6)·LATE_BULL 228 = 다양성 게이트 개방. **analog 코드 착수 가능**. 앵커 설계 = 입력벡터 z-정규화 최근접(라벨 매칭 아님, D-ANALOG-GATE) | **#1** | @backend | 🔵 **Slice B 코드 land (2026-07-13, `monorepo/sess-B-analog-card` BE `3e2e875`+FE `e271f27`)** — 매칭 엔진(D-ANALOG-DIST 가족동결 FAM1/FAM2)+②C 경보(D-ANALOG-CARD-K)+①C 정직팬(D-ANALOG-CARD-FWD)+`regime/analog` 엔드포인트+`AnalogCard` UI(label 슬롯 null). pytest 401/vitest mp2 309·mig0·news 무접촉. prod 실측=경보(nearest 1.02). **⚠️ 683 통합검증=A-PREP `--commit`(병진) 후**(현 199). **다음=Slice C(라벨 파이프라인 L2/L3)** |
| ANALOG-SLICE-C | 라벨 파이프라인 — cat_slot(L2 카테고리) + why(L3 cached 맥락). B가 남긴 null 슬롯 채움. STEP 0서 **3분할 확정**: (C-N)뉴스 백필·(C-core)L2 regime+FE·(C-L3)LLM 생성. 원지시서 L2 두 후보(FMP 캘린더·과거뉴스분류) 과거 불가 → L2=RegimeSnapshot 벡터/regime 결정론(683 커버), L3=뉴스 백필 후 | market_pulse+news+rag 트랙 | **Slice B land(충족)** | 🔵 **분할 진행** (C-core done·main 안착·**C-N 전량 완료 07-23**·C-L3 착수 가능) |
| MP2-NEWS-BACKFILL (C-N) | 과거 broad 시장 뉴스 소급 백필 = L3 그라운딩 재료. AV NEWS_SENTIMENT(FMP 402 유료벽 대체, GN 실측 2023-09 도달). `backfill_broad_news` 커맨드(라이브 collect_av_broad 동일 save 경로 재사용·멱등·dry-run 기본·--max-requests 25/day 캡). 미커버 122창(2023-08~2025-12) | @backend(news) | ✅ **전량 완료 (2026-07-23, 122/122창)** — 각 창 317~950행 적재·SATURATED 2구간 실갭없음(매일 기사존재→재패스 불요)·완료 후 AV 0req(전부 skip). 커맨드 land(`monorepo/sess-CN-news-backfill`)·테스트 6 green·경계0. AV 회계 조사(07-22): 로컬 쿼터 카운터 부재=서버측 전용. D-CN-REUSE/-NO-PRESERVE/-SKIP-COVERED | ✅ **완료 → C-L3 언블록** |
| MP2-ANALOG C-core | L2 국면 카테고리(결정론, RegimeSnapshot.regime·enum 라벨 재사용) + cat_slot/cat_key 배선 + FE 태그(regimeTone 재사용) + today 태그 + docs 정착(D-DOCS-PERSIST). D-ANALOG-L2 | @backend+@frontend | 🔵 **done + main 안착 (`monorepo/sess-C-core-l2`)** — `regime/category.py`(5값 전사·미지값 에러)+cards 배선(cat_slot string 유지·cat_key/today_category additive)+FE AnalogCard 태그. 카테고리8+api6+FE8 green·marketpulse 404·tsc0·mig0·경계0·CRISIS 카피게이트 준수. 라이브 today "상승 후반 경계" | ⚠️ **실화면 게이트 이연**(아래 별행) → 그 후 잔여 0(why=C-L3) |
| MP2-ANALOG C-L3 | LLM cached 맥락 생성(그라운딩=C-N 백필, 톤가드·동결) → 이웃 why 채움. 대량 생성 dry-run+수동 유보. ★그라운딩 쿼리 is_archived **무필터**(D-CL3-ARCHIVE-BLIND) | @rag-llm+@backend | ✅ **구현·검증 완료·배포 대기 (`monorepo/sess-C-L3-context`, base `b9ddf41a`)** — 신규 `AnalogDayContext`(mig 0007 additive·dev 적용)·`grounding.py`(결정론 선별 abs(sent)→entity→cap3, importance_score 0% 실측→제외)·`tone_guard.py`·`context_generator.py`·`generate_analog_context` 커맨드(멱등·동결·dry-run 기본)·cards payload why/provenance/version 배선·FE per-neighbor "왜?" 펼침. **LLM=market_pulse `generate_with_circuit` 재사용**(원지시서 "shared complete()"는 실측 정정: BOUNDARY-LLM 종결·경계 통과). 신규 35 green·446 marketpulse·vitest 10·tsc0·경계0·health❌0. 소량 8일 실생성(톤가드 전통과). **배포(07-24~25)**: push→main `96fd17bc`·mig 0007 적용(단일 DB stock_vis)·491일 --commit 진행. ★683 중 **154일 null=상류 C-N 백필 공백**(→`C-N-REPAIR`, C-L3 결함 아님). 실화면 캡처=병진 잔여 | ✅ **배포·491 생성 완료 → 154일은 C-N-REPAIR 후 재생성** |
| C-N-REPAIR | C-N 백필 창 뒷날 누락 보강 — `D-CN-COMPLETE` 폐기 후속. 대상=null 192일(구간내 154 창뒷날 누락 + 뒷단 38 미수집공백). 방식=`backfill_broad_news --dates`(1일 독립 창, 창논리 우회). D-CN-REPAIR-*(#72)·AUTO-*(자동화) | @backend(news)+@infra | ✅ **랜딩 완료 (origin/main `68aeea28`) + 무인 자동화 빌드 완료 (`monorepo/sess-CN-repair`)** — `--dates` 표적모드·계획서 10배치. **AUTOMATION(07-29)**: `scripts/cn_repair_nightly.sh`(체크포인트 순번·1배치/밤·이상치 밴드·완료 자동unload)+`cn_repair_status.py`+launchd plist(22:10 KST)+런북(`automation_runbook.md`). 순번=체크포인트(캘린더 산술 기각=batch1 스킵)·실행트리=sv-worker-runtime. 검증: 신규 pytest 9+backfill 11·dry-run 매핑·완료경로·경계GREEN. D-CN-REPAIR-AUTO-*. **★활성화(launchctl load·kickstart)=prod쓰기+AV소비 게이트** · **✅ CN-AUTO-REVIEW(07-29): 관문 6종 전부 PASS**(G1 쿼터캡·G3 범위한정·G4 멱등순번·G5 경계보안·G6 테스트, **G2 미달→보강**: `status.py check` 리포터+아침루틴, 테스트 9→14). D-CN-REPAIR-AUTO-ADOPT=수동 게이트 공식 대체. **STEP0: status.json 없음=배치 0회, 잔여 10/10(192일)**. **✅ 자동화 랜딩(origin/main `efa927b3`, 07-30)+#73→#74 renumber(`1b46e0df`)**. **✅ 활성화 완료(07-30, 병진 승인)**: worker_sync 3트리 동기화·plist `~/Library/LaunchAgents/` load·launchctl 등록 확인·22:10 KST 예약(runs=0)·kickstart 미실행(첫 발화=22:10 자연). ground truth 재확인(read·AV0): 192일 전부 공백=배치 0회 확정. | ✅ **완주 종결 (2026-08-10, 192/192 DB 일-존재)** — batch1~10 전건 status ok(net 4262~17236·batch10=12일). CHECK-DAILY v2 확증: plan 192일 각 `published_at__date>0`=192/192·≥3 커버=192/192·진짜공백 0. 08-08 완주 시 래퍼 자동 unload(D-CN-REPAIR-AUTO-DONE, launchd list 공백·bootout `No such process`=정상)·plist 잔존(재로드 방지=수동 mv). CN-B7-PROBE: "158/192"는 target_windows 합(skip-covered 저계상)이지 커버일 아님→common-bugs 채번후보 2건. **다음=C-L3-REGEN-V2 진입(조건 충족)** |
| BOUNDARY-LLM-ALIAS-CHECK | `apps/market_pulse/llm/client.py`가 `from google import genai as genai_module` 후 `genai_module.Client(...)` — 경계 테스트 AST(`genai.Client`만 매칭)의 **사각지대**로 우회 중. BOUNDARY-LLM 종결(FROZEN_COUNT=0) 선언과 정합성: 의도 동결(허용)인지 vs 미이관 잔재(경계 강화 대상)인지 확인 필요 | @qa+@infra | ✅ **종결(BOUNDARY-LLM-CB, 2026-08-11)** | 판정=(나) 단순명명(도입 `51046350` 우회의도 무)·효과는 false-negative. C=스캐너 별칭 인지 보강(`_genai_bound_names`)→위반 1 정직 검출. B=`packages/shared/llm/legacy_gemini.py` verbatim 이동→CORE_EXEMPT 면제→FROZEN 0 정직화. common-bugs 등재. D-BOUNDARY-LLM-CB |
| BOUNDARY-LLM-UNIFY | `packages/shared/llm/legacy_gemini.py`(B 이동한 gemini-CB 동기 래퍼) → shared/llm/core(complete/stream) 통합·gemini 경로 중복 제거. 앱 무접촉·shared 내부 리팩터. **Haiku A/B**(providers/anthropic.py 기존재) 동시 검토 | @infra+@rag-llm | **💤 이연** | 트리거 = S4-REBASE 재생성 사이클 진입 시 or 다음 shared/llm 기능 작업 시. 소비처 인터페이스(generate_with_circuit) 어댑테이션=행위보존 검증 슬라이스. D-BOUNDARY-LLM-CB(A 이연분) |
| C-L3-SELECT-V2 | C-L3 그라운딩 선별 품질 개선 — 거시 사건일 맥락 빈약(스팟체크 2024-08-05 급락·2023-10-19 국채·2024-05-15 CPI 전부 "개별 기업 소식"). 원인=broad 피드 거시뉴스 희소(08-05 220건 중 급락 4건)+선별 abs(sent)/entity가 개별기업 상위(D-CL3-QUALITY-LIMIT). 개선안=index/거시 entity 우선·거시 키워드 가중·소스 다양성 재조정 → `--regenerate --prompt-version cl3_v2`. ★근본 한계=broad 거시 절대량 부족→부분 개선만. C-N-REPAIR(창 뒷날 복구)와 시너지 | @rag-llm+@backend | ✅ **선별 모듈 v2 구현·검증 완료 (`monorepo/sess-select-v2`)** — 결정 **D-SELECT-V2-RULE=(나) 어휘·규칙**(가중합 8.55 vs 하이브리드 7.78 vs 메타우선 4.15; (가) 실격=AV topics 미저장·category 재수집 전부 company·sentiment 51/100 불균일). 신설 `apps/market_pulse/regime/grounding_v2.py`(v1 무접촉·additive): 계층 macro 어휘(STRONG/MID)+티커노이즈 가드(×0.3)+소스가중+near-dup 접기+**품질 하한(빈 결과=why=null)**+버전태그 `select_v2.0`. 반환=v1 호환키+score/hits/rank. **결정론**(sentiment/entity는 tie-break만=v1 편향 회피). 초안 N=6·min_score=1.2. 단위 13+regime 회귀 98 green·경계0·LLM0·외부API0·마이그0·야간자동화 무접촉. 스팟 12일 v1대비 압도(macro-rich일 "PCE Inflation/Fed holds/ECB rate"; 저볼륨일 v2 빈결과 vs v1 개별주 억지). broad 희소일은 부분개선(한계 유효). | ✅ **랜딩(origin/main `affd1604`) → REGEN-V2 진입·파이프라인 구현 완료(`monorepo/sess-regen-v2` `64f619c4`)**. C-N-REPAIR 완주(192/192)+SELECT-V2 랜딩 둘 다 충족 → D-REGEN-V2-1~3(v2 additive 배선·prompt_version 태깅·마이그0). 샘플 게이트 12일 write-free 실증(v1↔v2 품질개선·~$0.00184). ✅ **REGEN-V2 종결(2026-08-10)**: 샘플 육안 승인→Part4 dry-run(674 호출·~$0.13)→랜딩(`cd08adc8`/`27ba0518`)→worker 트리 동기화+683 --commit 실행. **결과 cl3_v2 666 + cl3_v1 잔존 12 + 행없음 5**. 톤가드 육안 6/6·마이그0. D-REGEN-V2-EXEC. **CL3-V1-RESIDUAL 후속 종결(2026-08-10)**: cl3_v1 잔존 12 = (b) 백업(`docs/archive/cl3_v1_residual_backup_2026-08.json`) 후 삭제(`purge_analog_v1_residual` 이중조건) → cl3_v1 0·cl3_v2 666·why=null 폴백(D-CL3-V1-RESIDUAL). 다음=BOUNDARY-LLM 진입 or 서빙 표면(범위 밖) | ✅ **종결** |
| MP2-ANALOG C-core 실화면 게이트(이연) | 첫 non-alert 날(analog 이웃 ≥1)에 market-pulse-v2 카드 실화면 캡처 → **이웃 태그 렌더 확인** 후 게이트 닫기. 오늘 카드 alert(이웃 0)라 이웃 태그 off-surface → 실화면 검증 이연(폐기 아님, D-ANALOG-L2 실화면 3택 중 2번) | 병진(아침 루틴) | 🕒 **열림** — non-alert 날 대기 | 증빙=스크린샷, 확인 후 close |
| MP2-ALERTS | 능동 알림. 알림 코어 = `packages/shared/alerting` 신설(D-ALERTS-BOUNDARY-R1), 3단 파이프라인(D-ALERTS-ARCH), 이메일(D-ALERTS-CHANNEL). **승계 게이트 해소 = D-ALERTS-GATE**(serverless 무접촉 격리). S0·S1 land | **#2** | @infra+@backend | ✅ **S0 마감 + S1 done(미머지)** | 다음 슬라이스 후보 = 채널 추가(슬랙 등, delivery port 구현체만) / 트리거 확장(anomaly·dashboard) |
| MP2-ALERTS-S1 | Slice 1(D-ALERTS-RENDER) = regime 알림 본문 **풀 리포트화**(전환 요약·델타·anomaly 활성·섹터 상위/하위). **단일 경로**=판단 화면과 동일 `overview._build_payload()` 소비(재계산 0). **폴백**=풀 렌더 실패 시 디스패처가 S0 최소 본문으로 대체(발송 무실패, `AlertDispatchLog.error` RENDER_FALLBACK 접두로 식별, status=SENT). registry에 fallback 슬롯 additive. 제목 불변·LLM 0·shared→apps 0·마이그레이션 0 | @backend | ✅ **done + 실메일 검증 완료 (2026-07-08 장부 마감)** — pytest 신규7/alerting8·경계3·api80 green·mig0. FE 0. **풀 리포트 실수신 확인**(status=sent·폴백 아님, jinie545@gmail.com) | 검증 완료 → 잔여 없음 |
| MP2-ALERTS-S0 | Slice 0 = regime 전환 트리거 → 3단 파이프라인 → 이메일 1통 + dedup. shared/alerting 신설(AlertSubscription·AlertDispatchLog·registry·dispatcher·EmailProvider) + market_pulse 훅·렌더러 + seed 커맨드. AST 경계 통과, migration 0001 **생성만** | @infra+@backend | ✅ **실적용 완료 (3eb06a7) — 장부 마감 2026-07-06**: migrate·worker_sync·seed·shell 수동 트리거·실발신 전 6단 완료. **실메일 일반 수신함 정상 도착 확정**(스팸 아님, 발신 신뢰도 이슈 없음) + `AlertDispatchLog` status=sent 1행. 멱등 close(이후 재마감 스킵). | 병진 수동 런북(6단, 2026-07-05 확정 — 완료 기록): **① `python manage.py migrate alerting`**(prod DB 테이블 2개 — 워커 재기동 전 선행: 재기동 창에서 실전환 시 테이블 부재 회피) → **② `bash scripts/worker_sync.sh`**(B′ 배포+워커 재기동 — 신규 task·regime.py 수정·신규 앱 로드 필수, 근거 `lesson_celery_task_registration`. beat 무변경이나 스크립트가 함께 kickstart=무해) → **③ `python manage.py seed_alert_subscription --email <주소>`**(멱등) → **④ shell 수동 트리거** `fire_regime_transition_alert(date="2026-07-05",…)`(직접 동기호출 — 워커 무관·이메일 경로 종단 검증, 07-05 과거날짜라 실전환 dedup 충돌 0) → **⑤ 실메일 확인**(제목·본문 링크·소요·스팸함 + `AlertDispatchLog` status=sent 1행) → **⑥ 첫 메일 "스팸 아님" 처리**. ⚠ **배포 전 prod `FRONTEND_BASE_URL` 도메인 설정 확인**(미설정 시 메일 링크=localhost:3000). **migrate 전까지 prod 미반영** |
| SCREENER-ALERT-CONVERGE | (휴면) serverless `ScreenerAlert`/`AlertHistory`(사용자 알림 프레임워크, delivery 미구현) → shared/alerting 코어로 수렴 여부. D-ALERTS-GATE로 현재 **무접촉 격리(KEEP 레거시)** 확정. 전수조사 CUT 판정 없음 → 소멸 예정 아님 | @backend | 🕒 **휴면** | 트리거 = screener 알림 **실활성화** 결정 시(그때 shared 코어 재사용 vs 독립 유지 재평가). 현 시점 착수 금지 |
| MP2-SECTOR-CD | 섹터 판단 화면(CD 4-상태). 순차 연속 슬라이스(D-TREND-CD-SEQ). rel_strength×momentum_5d 사분면 분류(신규 파생 0, baseline=0.0). RRG 회전 맵 = 서브스크린(D-SECTOR-NAV, Slice 3) | **#2.5** | @backend+@frontend | ✅ **트랙 종결 (2026-07-09)** — S1 `32c2390`·S2 `20d2734`·S3 land | 판정 로직 = payload builder 단독·FE 재분류 0 전건 준수. **차순위 = B-1(ANALOG·TREND S4 이중 언락 키)** |
| MP2-SECTOR-CD-S1 | Slice 1 = cd_state additive(payload) + 판단 카드(세그먼트 토글 [판단\|궤적], 디폴트=판단). `classify_cd_state` 순수함수 + `CD_REL_STRENGTH_BASELINE`/`CD_MOMENTUM_BASELINE`=0.0 상수 + FE CD_STANCE 정적 5문구(LLM 0) + 2×2 미니맵 + 유보 처리 | @backend+@frontend | ✅ **done (land `32c2390`)** | additive-only, 회전 맵 어포던스 미포함(Slice 3) |
| MP2-SECTOR-CD-S2 | Slice 2 = 모멘텀 시계열. sector_history[] per-date momentum_5d additive 노출(저장값) + `cd_momentum_baseline` 메타 + FE 모멘텀 모드(디폴트=순위 유지)+판정선 hline(서빙값)+국면 스트립 레인(D-SECTOR-MOM-LANE 변형2, `regime_history_30d` 소비) | @backend+@frontend | ✅ **done (land `20d2734`)** | momentum=저장 노출(재계산0, STEP 0-2: 528행/48일/NULL0). 변형2 확정 |
| CD-FLAP-WATCH | (측정 완료) cd_state 일간 반전 빈도 소급 측정(S3 STEP 0-2, 43일 집계 2026-05-19~07-09, 초기5일 제외). **결과: 총 289반전/11섹터/43일, 일평균 반전 섹터 6.72, 섹터당 일평균 반전율 0.611**(XLI 30 최다~XLV 22 최소). 판정선 근접 상습 섹터 없음(근접 최대 9일=21% → 플래핑 원인은 근접-호버 아닌 실 부호 변화). rel_strength=1일 차분 특성 | @backend | 📊 **측정 완료 — 히스테리시스 여부 디렉터 결정 대기** | 반전율 0.611은 높음(거의 매일 절반+ 섹터 반전). 후속(히스테리시스/장창 x축)은 디렉터 판단 사안. 현 시점 코드 수정 금지 |
| MP2-SECTOR-CD-S3 | Slice 3 = RRG 회전 맵 서브스크린(D-SECTOR-NAV 옵션 B, 라우트 `app/market-pulse-v2/rotation`) + 판단 카드 회전 맵 CTA 활성화 + `cd_rel_strength_baseline` 메타(x축 판정선). 데이터=기존 단일 fetch(sectors[]+sector_history, STEP 0-3 신규 엔드포인트0) | @backend+@frontend | ✅ **done (land, 트랙 종결)** | 사분면 맵(서빙 2축 판정선)+11점 cd_state색+출발섹터 하이라이트+꼬리 5일(D-CD-TRAIL) raw 폴리라인(재분류0). pytest 신규6·vitest 신규14·tsc0 |
| MP2-SECTOR-CD-S3-PERROW | S3 보완 = 판단 카드 per-row 회전 맵 진입(D-SECTOR-NAV 이행 결함 수정). 각 행 전체 탭→`rotation?from=<그 행 symbol>`, 상단 CTA는 "전체 보기"(from=리더)로 의미 교정 | @frontend | ✅ **done (land `ceab955`+`27b5667`)** | 트랙 종결 상태 유지(재개봉 아님). FE 국소·additive·RRGChart/라우트/BE 무변경. vitest 신규7·tsc0 |
| CD-STAB | (측정 완료 2026-07-09 → 처방 확정 D-CD-STAB) cd_state 안정성 축별 분해 + 처방 후보 소급 시뮬. **축별 분해(289반전)**: X기인 63.7% 주범·Y 20.8%·동시 15.6%. 1일유지 0.633. 후보 반전율(원본 0.611): A 0.332·A′ 0.326·B 0.209·C 0.175. **처방 = ③ C 순차 채택**(B→A′) | @backend | 🏁 **트랙 종결 (2026-07-09)** — B land + A′ land 완료. **차순위 = B-1 FRED 백필**(ANALOG·TREND S4 이중 언락 키) | B=STAB-B, A′=STAB-A′ 순차, 둘 다 종결 |
| STAB-B | Slice B = 2일 히스테리시스. `resolve_official_cd_state` 무상태 리플레이(저장 히스토리 결정론적 재생) + 서빙 `cd_state` 의미전환=공식(D-CD-STATE-SEMANTICS) + `cd_state_raw` additive. 수락 앵커=측정 B 재현(≤07-09 창 99반전/0.209) | @backend | ✅ **land (2026-07-09)** | FE 변경 0(전 소비자 서빙값 소비 확증). 모델·마이그레이션 0(무상태 리플레이) |
| STAB-A′ | Slice A′(C 순차 후속) = x축 = 5일 상대수익(mom_5d − bench 5일 수익률, bench=SPY MarketIndexPrice, 서빙 시점 파생·저장 0). rel_strength_5d additive(판단 계열만, D-CD-XAXIS-SCOPE)·기존 rel_strength(1일)·히트맵 무접촉 | @backend+@frontend | ✅ **land (2026-07-09, CD-STAB 트랙 종결 슬라이스)** | **STEP 0 관측**: 방법론 앵커 B=99/0.209 정확 재현. **A′ 서빙 앵커 = 84/0.1776**(저장 momentum_5d 기준, 규칙 #3). 시뮬 목표 83/0.175와 1반전 편차 = XLU 05-19 경계값 + 데이터 드리프트(디렉터 판정 수용). 0-2 실서빙 관측=07-09 이후 신규일 0(축적 대기) |
| CD-TRANSITION-INDICATOR | (선택) "전환 확인 중" 표시 — raw≠official 비교로 FE 파생(분류 아님, 두 서빙값 단순 비교). 히스테리시스 +1일 지연을 사용자에 투명화 | @frontend | ✅ **이행 (CD-READ, 2026-07-09)** — cd_state_raw 첫 소비(칩+보조문+점선 링). 라이브 첫날 실증으로 필요 확정 | D-CD-STATE-SEMANTICS 경계 제외분 소진 |
| CD-READ | 판단 표면 가독성 — RRG 변형 H(포커스 디폴트 + 전체 꼬리 토글) + 고정 3건(미니맵 라벨 제거·전환 확인 중·cache 제거). FE 중심, BE 무변경(표시 전략만) | @frontend | ✅ **land (2026-07-09, D-CD-READ)** | 채점 H 4.35/F 4.10/D 3.90(사용자 선택). vitest 295·tsc 0. **B-1 STEP 0(별도 진행분)와 독립 병렬 가능**(무의존) |
| MP2-SUBPAGES-S1 | 거시 허브(props형 4종) — 라우트 `/market-pulse-v2/macro` + 위젯 4 이식 + 홈 CTA 2 + 가이드 draft + E2E | **#3 (A)** | @frontend | ✅ **done (2026-08-31)** | D-SUBPAGES-LAYOUT(가)·D-SUBPAGES-DATA(i). 허브 페이지(탭 앵커·useMarketPulse 재사용·pulse FREEZE)·CTA 2(링크만·홈 fetch 불변 입증 429① [5,5,5,5,5])·guide draft(검수 대기 병진). 위젯 원위치 재사용(이동 0)·백엔드 0·v1 페이지 0. vitest 1198(+8)·E2E 3스펙 2회 GREEN·실렌더 스크린샷. |
| MP2-SUBPAGES-HOTFIX1 | pulse 스테일-캐시 즉시 응답(SWR) + 허브 로딩 완화 | **#3 (A)** | @backend+@frontend | ✅ **done (2026-08-31, 랜딩 병진 대기)** | D-SUBPAGES-SWR(C). BE: `macro:market_pulse_full{,:stale(24h),:refreshing}` SWR — fresh 미스 시 stale 즉시 반환+백그라운드 갱신 1회(락 dedup), 태스크 `force_refresh=True`. 스키마·뷰 diff 0. **콜드 실측 28.8s→stale 경로 즉시**. FE: `getMarketPulse/useMarketPulse({timeoutMs?})` additive(v1 diff 0), 허브만 20s 타임아웃+재시도 안내+"N분 전 데이터" 배지(amber 토큰 재사용). pytest +6, vitest +8(364 GREEN), tsc 0. |
| MP2-SUBPAGES-WARMWINDOW | pulse 워밍 beat 창 재검토(A안 잔여) — SWR 운영 관측 후 | 미배정 | MP2-SUBPAGES-HOTFIX1 land + 운영 관측 | 🕒 **todo(관측 후 별건)** | 현 `refresh-market-pulse-cache` = ET 장중(9-16, 평일)만. SWR로 콜드 무해화됐으나, KST 사용 케이던스에 맞춘 워밍창(장외 1회 등) 추가 여부는 FMP/FRED 호출량 대비 관측 후 결정. beat DB 엔트리 변경 = 병진 수동(#28). |
| MP2-SUBPAGES-S2 | 거시 허브 무버스 탭 — `MarketMoversSection` 흡수 | **#3 (A)** | @frontend | 🕒 **todo(S1 land 후)** | **S1 STEP 0-7 재료**: 자체 fetch 3훅 — `useMarketMovers`(useQuery·staleTime 5m·**refetchInterval 5m**)·`useSyncMarketMovers`(mutation POST·sync 트리거)·**`useGenerateKeywords`(mutation→`keywordService.generateAllKeywords`=Gemini AI 키워드·Celery async·LLM 비용/rate 주의)**. 엔드포인트=serverless(market_pulse_user 미공유). 인증 경로·비용 게이트는 S2 STEP 0 재확인. 허브 무버스 탭은 현재 "준비 중" 배지. |
| GUIDE-MACRO-REVIEW | 거시 허브 가이드(`marketPulse.macro`) 검수 → draft→confirmed 전환 | 사용자/병진 | MP2-SUBPAGES-S1 land | 🟡 **검수 대기(병진)** | reviewStatus:'draft'로 착지(guideData 테스트 allowlist 등재). coreQuestion="오늘 국면의 거시 근거는 무엇인가"·regions 4(심리/금리/지표/글로벌). 검수 후 confirmed 전환 + allowlist에서 제거. |
| MP2-DATA-FEDWATCH-GEX | FedWatch(fed funds futures)·GEX(감마 익스포저) 외부 데이터원 신설 | **#4** | @infra+@backend | 🔴 **데이터게이트** | recon [E] 코드베이스 흔적 **0**(클라이언트 미보유) → **데이터원 확보 전 착수 금지**. 별도 공급원 조사 선행 |
| MP2-CROSS-SURFACE | cross-surface 통합(대시보드↔chain_sight↔portfolio 교차 표면) | **#5** | TBD | 🔴 게이트 | 선행 트랙(#1~#3) land 후. 범위는 그 시점 재정의 |
| MP2-E2E-SAFETYNET | **E2E 화면 회귀 안전망** — Playwright `/market-pulse-v2` 렌더 회귀(데스크탑 + Pixel5 모바일 에뮬레이션). Phase 2 **첫 인프라** | (인프라) | @qa+@frontend | ✅ **done (P2-DLITE, 2026-08-29)** | Playwright devDep+config·`e2e/market-pulse-v2.smoke.spec.ts`(존재·콘솔에러0·전면에러부재·가로스크롤부재)·route interception 모킹(인증/백엔드/공유DB 무의존). 2회 연속 GREEN(desktop+mobile). 프로덕션 코드 diff 0. **CI 편입 = 후속 별건(E2E-CI-WIRE 미등록)**. |
| E2E-CI-WIRE | Playwright 안전망 CI/스케줄 편입 (P2-DLITE 후속) | (인프라) | @infra | 🆕 **등록(후속)** | 로컬 2회 GREEN 확보. CI 러너 브라우저 캐시·webServer 기동·아티팩트 업로드 배선. 범위 = P2-DLITE 밖. |
| MP2-DATA-BREADTH-CONC | **Breadth/Concentration raw 미수집** 점검 — Breadth 종목별 등락(상승/하락/신고저 0) + Concentration 상위종목 일부 부재. 화면은 graceful fallback 정상(밴드·sense 렌더)이나 raw 데이터원 점검 | (데이터) | @infra | 🆕 등록 (데이터 파이프라인 트랙) | D-P1-SCREENGATE P2-②. 화면 결함 아님(graceful) → 데이터 수집 task/소스 점검. Analog(#1) 입력 품질과도 연관 가능 |
| MP2-MOBILE-EYECHECK | **모바일 실기기 눈확인**(P2-① 권고) — 실기기/브라우저 DevTools 모바일 모드로 `/market-pulse-v2` 1회 눈검증 | (권고) | 사용자/병진 | 🟢 **대부분 흡수(P2-DLITE, 2026-08-29)** | Pixel5 에뮬레이션 안전망(가로스크롤 부재·렌더 존재·풀페이지 스크린샷)이 뷰포트 회귀를 자동 흡수. **잔여 = 실기기 1회 눈확인(비차단·사용자 재량)** — 에뮬레이션≠실기기 폰트/터치 미세차. |
| **MP1.5-FIX** | **단일 FE 슬라이스** — ⒜ A1 brief 모달 `body` fallback 매핑 ⒝ A2 authAxios refresh 인터셉터 401 재시도 ⒞ A3 `<Pie label>` 포맷터(`toFixed`)+레이블 겹침 처리 ⒟ "cache: MISS" 엔드유저 노출 정리 ⒠ **① 유효 종목 수(1/HHI) 카드 표시** | @frontend | ✅ **완료 (2026-06-25, `2c9fbca` + 시각검증) — A3-tail 종결로 "완전 통과"** | D-P15-SCREENGATE. 시각검증 실측: A1 본문·① 유효종목수(≈51종)·cache 가드(dev전용, 프로덕션 비노출 코드입증)·회귀 = PASS / A2 = vitest 갈음 / A3 = MP1.5-A3-TAIL(`77847ca`)로 겹침·클리핑 완전 해소. 커밋 `0f86e55`(A1)·`9529671`(A3)·`a079870`(cache)·`2c9fbca`(①)·`77847ca`(A3-tail) |
| **MP1.5-A3-TAIL** | **A3 도넛 좌상단 소형조각 라벨 겹침** — `ConcentrationDetail.tsx` 라벨 겹침 해소 | @frontend | ✅ **완료 (2026-06-25, `77847ca`)** | **leader-line 외부 라벨**(좌/우 midAngle 분기 + 수직 슬롯 분산) + 상단 클리핑 해소(컨테이너 height 260→320 + nudge 하향 + Y_MIN/MAX 경계 가드) + **전역 가변 제거**(`computeAllLabelLayouts` 순수함수 + useMemo/ref, 다중 인스턴스 안전). 라이브 :3000 데스크탑+모바일(390px) **11개 라벨 전수 가시·클리핑 0·겹침 0** 실측. tsc 0, vitest 신규 28/전체 418. 1차(겹침만 수정)에서 상단 클리핑 결함을 시각검증으로 발견→2차 수정(좌표≠실렌더 교훈) |
| MP2-ANALOG-COND-RESULT | **조건부-과거-결과 primitive (공유)** — D-CONC-RISK-LENSES ②③을 Analog 트랙 산하로 이동. ② 퍼센타일(현재값의 과거 분위) + ③ 조건부 과거결과(고집중→이후 분포, **분포+표본수+신뢰구간만·단일숫자 금지**) | @backend (Analog 산하) | 🔴 **데이터 게이트** | **시간만으로 안 열림**: ②=데이터 깊이(≥1년) + ③=**레짐 다양성**(저집중 표본 필요, 현재 top10 13/13 전부 고집중=변별 0). 집중도뿐 아니라 regime 전반 조건부결과의 공유 primitive로 설계. Analog(#1) 착수 시 통합 |
| **MP-VIX-SRC** | VIX provider 읽기 소스 교체 — `MarketIndex/MarketIndexPrice(volatility, 0건)` → `IndicatorValue(VIXCLS, 232행)`. regime degraded(normal 일색) 복구 | @backend | ✅ **완료 (2026-06-26, `bbe6b1b`)** | STEP 0 측정: volatility 소스 0건 → `_calculate_regime`이 항상 'normal'(EODDashboard 75행 전부). 단일 파일(`macro_vix_provider.py`), VIXProvider 포트 ABC·반환계약 불변(BOUNDARY-3 유지). 행위 델타 재계산 `{normal:75}`→`{normal:57,elevated:10,high_vol:8}`. 신규 6 + 회귀 384/1skip |
| **MP-VIX-BACKFILL** | EODDashboard 76행(2026-02-25~06-26) regime 소급 재적재(B-3) | @backend | ✅ **완료 (2026-06-29)** | `json_data['market_summary']['vix_regime']` 76행 재계산 UPDATE. **18행 변경**(03-03~04-07 고변동 → high_vol/elevated), 분포 `{normal:76}`→`{normal:58,elevated:10,high_vol:8}`. lookback 0부족(MP-VIX-STALE 백필로 전구간 커버) · 결정론적 · **백업 선행**(`eod_regime_backup_20260629.json` normal:76 원본) + 트랜잭션 원자적 + **멱등 재현**(재실행 0행). intraday RegimeSnapshot은 히스테리시스로 forward-only(백필 불가) — EOD만. **MP-VIX 트랙 3종(SRC·STALE·BACKFILL) 전체 종결** ✅ |
| **MP-VIX-STALE** | VIXCLS(+DGS 일간군) sync stale — 자동 재귀 beat 커버리지 갭 수리 | @infra | ✅ **완료 (2026-06-28~29, 코드 `20f0e6d` + 백필 + 워커 재기동)** | STEP 0: VIXCLS·DGS10·DGS2·T10Y2Y가 `FRED_RECURRING_SERIES`(7종) 밖 = 자동 재귀 미커버 → 수동 의존, 06-12 stale. **경우 P 확정**(FRED는 06-25까지 발행, 우리가 안 받음 — 실호출 검증, FRED 지연 Q 반증). 수리: `FRED_RECURRING_SERIES` **7→11**(일간 4종 편입, beat·task 무변경, 멱등 upsert) + PART2 백필 33행(06-13~25) + **워커 재기동**(celery-worker 33397→6413, `.delay()`로 11종 import 입증 7→11). beat `enabled`(평일 NY17:40). 재발방지 4축(코드·워커·sync·beat) 충족 |

> **집중도 카드 점진 공개 (D-CONC-RISK-LENSES)**: **① 유효 종목 수 = now**(MP1.5-FIX 동봉) / **② 퍼센타일 = 데이터 깊이 충족 시**(1년 미만이면 "표본 N일, 잠정" 정직 라벨 필수) / **③ 조건부 과거결과 = Analog 트랙**(MP2-ANALOG-COND-RESULT, 레짐 다양성 게이트). 가짜 절대리스크("40%→X%") 금지.
>
> **STEP 0 케이던스 실측(2026-06-25)**: beat `mp_calc_concentration_daily` = **평일 daily**(17:15 NY, cron `15 17 * * 1-5`). 최근 6/16~6/25 daily 정상. **단 5/7~6/11 35일 갭**(과거 운영 공백 — daily 의도이나 누락, 주간 의도 아님). → ② 타임라인: **현재부터 daily 누적 시 ~1년 후 가능**(과거 갭 미백필). 데이터 트랙 신규 항목 불요(beat 현재 정상 가동, 갭은 과거분).
>
> **Phase 1.5 게이트 = 완전 종결(2026-06-25, D-P15-SCREENGATE)**: MP1.5-FIX 5건 전부 PASS — A1 본문·① 유효종목수·cache 가드·회귀 실측 + A2 vitest 갈음 + **A3 = MP1.5-A3-TAIL(`77847ca`)로 겹침·상단 클리핑 완전 해소**(라이브 데스크탑+모바일 11라벨 전수 가시). 잔여 0. **→ Phase 2(#1 MP2-ANALOG) 진입 가능.** 기존 트랙 유지: MP2-ANALOG(#1, active)·MP2-ANALOG-COND-RESULT(②③ 데이터게이트)·MP2-DATA-BREADTH-CONC(B1)·MP2-E2E-SAFETYNET·MP2-MOBILE-EYECHECK.

---

## market_pulse v2 Phase 1 잔여 (2026-06-07 카탈로그 역산 확정)

> 근거: `DECISIONS.md` "## [2026-06-07] Phase 1 PR 카탈로그 역산 확정". 백엔드 A~J done(J는 I 흡수), FRED fetcher done, Translation/Playbook은 Phase 1.5/1.6 이관(범위 외). 본 표는 출시 전 정리할 6 트랙. **Phase 1 종료(2026-06-23, P1-close + 화면게이트 조건부통과) — 잔여는 위 Phase 2 로드맵으로 재배치.**

| ID | Task | Agent | Depends On | Status | Output Artifact |
|----|------|-------|------------|--------|----------------|
| MP1-K | Phase 1 프론트엔드 Layer0(메인 페이지) — Card A 헤더/지표/regime 표시 | @frontend | - | **완료 2026-06-10 (static 기준)** | `frontend/app/market-pulse-v2/page.tsx` (Layer0) + `cards/RegimeCardSummary.tsx` + `components/{TickerBar,StatusBanner}.tsx`. 5 card_id 라우팅 + `useOverview()` TanStack Query. 라이브 검증은 `MP-LIVE-VERIFY` 게이트로 분리(아래). 직전 "0%" 측정은 없는 src 경로 grep 오류(common-bugs #31) |
| MP1-L | Phase 1 프론트엔드 카드 컴포넌트 — Card B/C/D/E 4종 + news/health 위젯 | @frontend | MP1-K | **완료 2026-06-10 (static 기준)** | `frontend/app/market-pulse-v2/cards/` 5 Summary + `details/` 5 Detail(+Container) + `components/{AnomalyPanel,CardDrawer,NewsPanel,StatusBanner,TickerBar}.tsx` + `lib/api/marketPulseV2.ts` (30+ 타입 + 4 fetch). health 위젯은 `StatusBanner` 매핑 추정(`MP-KL-F3` 확인). 라이브 검증 `MP-LIVE-VERIFY` |
| MP1-C-stress | regime classifier `stress_input` 훅 (1줄 인터페이스, Phase 1.5 무재설계 전제) | @backend | - | **완료 2026-06-10** (`ce0be51`) | `apps/market_pulse/regime/classifier.py:classify_inputs(*, stress_input=None)` keyword-only Optional + 즉시 del. 회귀 138 passed (136+2 신규). 행위보존 |
| MP1-M | runbook task 경로 갱신 — `marketpulse.tasks.*` → `apps.market_pulse.tasks.*` (10 task 전건) | @infra(@qa) | - | **완료 2026-06-10** (`ef9d064`) | `docs/operations/marketpulse_v2_celery_tasks.md` 10건 전수 치환. grep 옛 경로=0 / 새 경로=10. NT-7 정합 잔재 정리 |
| MP1-N | market_pulse 능동 모니터링 자산 — `services/news.tasks.check_pipeline_alerts` 패턴을 market_pulse로 확장 (anomaly engine error rate / regime stale / news feed lag 등) | @infra | - | 🟣 **재배치: Phase 2 백로그 (P1-close, 2026-06-23)** — 신규 기능(저우선 청소 아님) | STEP 0: alerts.py 신설 = 신규 모니터링 기능(코어 대시보드 동작과 무관·게이팅 아님). Phase 1 종료 범위 외 → Phase 2 로드맵 후보 풀로 자연 합류. 트리거 = Phase 2 착수 or 운영 알림 필요 |
| MP1-A3-sep | A3 마이그레이션 3분리 (`BreadthSnapshot`/`SectorFlowSnapshot`/`ConcentrationSnapshot`을 `0002`/`0003`/`0004`로 분리) | @backend | - | 🔴 **HALT/재배치 (P1-close STEP 0, 2026-06-23)** — 전제 stale·파괴적 | STEP 0 실측: marketpulse 0001~0006 **전부 [X] prod DB 적용**·0002~0005는 이미 `pr_a2_*`(field/rename/restructure) 점유·Snapshot 모델은 0001_initial에 통합 생성. 원문 가정("0002/0003/0004로 분리") stale → 적용된 history 사후분리 = 파괴적(행위보존 불가). **닫지 않음 — DORMANT 재배치**(squash는 신규 DB 재구축 시에만 의미) |
| MP1-test-gap | PR-B fetchers 테스트 모듈 (`fmp_weights.py` 커버) — ~~PR-I serializer 도메인별 분리는 STEP 0에서 저실익 판정 스킵~~ | @backend + @qa | - | ✅ **완료 (P1-close, 2026-06-23, `d455382`, 축소)** | STEP 0: serializer `overview.py` 13클래스 통합=145줄(비대 아님)·import 파급 5곳 → 분리 저실익 스킵(재배치 불요·실익 없는 구조변경 영구 보류). fetchers `fmp_weights.py` 테스트 11건 보강(파싱/정규화/rank/skip/가드). additive, pytest marketpulse 226→237. 마이그레이션 0 |
| ~~**[GATE:release] MP-LIVE-VERIFY**~~ | **Phase 1 출시 전 필수 — 라이브 검증 게이트** | @qa + @frontend | MP1-K · MP1-L · MP-KL-F3 | ✅ **전건 통과 (2026-06-11)** — ⒜ 계약(C·D) 전건 PASS(d5212d4 검증: overview concentration 키·/cards/flow 404·i18n·5 카드 렌더·drawer detail) ⒝ Briefing 데이터 = MP-LV-D2 수리(`62d4025`) → brief 카드 재게이트 통과 ⒞ Concentration 데이터 = MP-LV-D1 옵션 B 수리(`c6b7aa0`) → SP500_MCAP 스냅샷 생성 + concentration 카드 재게이트 통과(top5 28.29%·HHI 0.0221, /cards/concentration 200·당일·값 정합, /cards/flow 404 유지). **Phase 1 종료 (2026-06-11)** — 게이트 전건 통과 = Phase 1 범위 완료. **출시는 별도 결정**(운영 자율 가동 확인 `MP-OPS-AUTOGEN-CHECK` + `MP-UX-POLISH` 이후 사용자 선언). 상세 DECISIONS "[2026-06-11] Phase 1 종료 선언" | 검증 보고서(curl + DOM 채증) + DECISIONS "[2026-06-11] 게이트 1차 결과"·"[2026-06-11] MP-LV-D1 옵션 B". 부분 재게이트 원칙(수리가 계약 무관 → 해당 카드 스모크만) 적용 |
| MP-KL-F1 | market-pulse-v2 프론트 테스트 신설 — `frontend/__tests__/` 내 0건 → vitest 기반 단위/통합 추가 | @frontend + @qa | MP1-K · MP1-L | **완료 2026-06-11** (`e538e7f`, 원본 `8f1ba79`) | `frontend/__tests__/market-pulse-v2/{fixtures.ts,page.test.tsx}` 12건 (page 로딩/에러/happy + StatusBanner OK숨김·STALE표시 + 5 카드 펼침 라우팅 + drawer 닫기) + `vitest.setup.ts` ResizeObserver 폴리필. vitest 162→174 |
| MP-KL-F2 | cardId `'flow'` → `'concentration'` 행위보존 리네임 (Summary/Detail 파일명 + `CardId` 타입 + `CARD_TITLE` 매핑 + API 계약 영향 범위) | @frontend | MP1-K · MP1-L | **완료 2026-06-11** (`902ec86`, 원본 `70a00c9`) — **게이트 선행 실행됨**(게이트 의존 표기 삭제, 근거 DECISIONS [2026-06-11] MP-KL-F2 게이트 선행) | BE 7곳(VALID_CARDS·enum·dispatch·overview 키·serializer·i18n·test parametrize) + FE 10곳(Flow→Concentration 파일·타입·page·container·hooks·lib·i18n) 원자적. 동명이의 3종(briefing Literal·flow_proxy·news_classifier) 보존. BE 138 / FE 174 / tsc 0 / card 'flow' 잔존 0 |
| MP-KL-F3 | health 위젯 명세 검증 — `MP1-L`의 "health 위젯"이 `StatusBanner` 매핑인지 별도 위젯 필요한지 `page.tsx` 본문 분석 + `OverviewView` health 필드 대조 | @frontend + @backend | MP1-K · MP1-L | **완료 2026-06-11** (`d5289a2`, 원본 `f16efcb`) — **StatusBanner 확정**(별도 위젯 불요) | 판정: 사용자 대면 health = `StatusBanner`(overview `_meta.status` 5값 전수 매핑, 3중 정합). `/health`는 IsAdminUser ops probe로 프론트 미통합 정상. MP-LIVE-VERIFY health 선결 해소. 📎 `docs/market_pulse_v2/mp_kl_f3_health_widget_verification.md` |
| MP-V1-DECISION | v1 `app/market-pulse/page.tsx` (310 lines, useMarketPulse v1 hook, `/api/v1/macro/pulse/`) 거취 결정 — 폐기 / 리다이렉트(v2로) / 보존(레거시) 중 택1. v1 내부 `MarketNewsSection` "TODO: 컴포넌트 미구현" 주석 처리 포함 | orchestrator + @frontend | - | **완료 2026-06-10 (옵션 D 채택)** | 결정: 보존 + Phase 2 흡수 예약. 가중합 D 3.90 vs C 3.55 (마진 0.35, 타이브레이커: 게이트 안전 순서 + Phase 2 정합). 상세 = DECISIONS "[2026-06-10] v1 거시 대시보드 거취 — 옵션 D". 후속 실행 = `MP-V1-ABSORB`(아래) |
| MP-V1-ABSORB | v1 위젯 5종(`FearGreedGauge` · `YieldCurveChart` · `EconomicIndicators` · `GlobalMarketsCard` · `MarketMoversSection`) v2 하위 페이지로 흡수 + `/market-pulse` → `/market-pulse-v2` 리다이렉트 전환 + v1 코드 제거 + 동결된 `MarketNewsSection` TODO 주석 일괄 처리 | @frontend | Phase 2 sub-pages 트랙 착수 | 🔵 **진행 중 — 4/5 흡수(MP2-SUBPAGES-S1, 2026-08-31)** | 위젯 4종(macro props형) 허브 `/market-pulse-v2/macro`에 흡수 완료(원위치 import 재사용). **잔여 = MarketMoversSection(S2)** + `/market-pulse`→v2 리다이렉트 + v1 코드 제거(MP-V1-RETIRE 결정 종속). `useMarketPulse` v1 훅은 허브가 재사용 중이라 존치(RETIRE 시 정리). |
| MP-LV-D1 | Concentration FMP `/stable/etf/holdings` 프리미엄 402 결함 — 비중 공급원 결정 | orchestrator + @backend | - | **완료 2026-06-11 (옵션 B 채택, `c6b7aa0`)** | 시총 가중 근사(S&P500 심볼 × FMP quote marketCap → weight=cap/Σcap). `fetchers/weight_source.py` seam 분리(MarketCapWeightSource 기본 / HoldingsWeightSource 휴면 / `ACTIVE_WEIGHT_SOURCE` 1곳 전환). 산식·모델·계약 불변, universe='SP500_MCAP'. 회귀 138→146. 호출 ~500 quote/일. 상세 DECISIONS "[2026-06-11] MP-LV-D1 옵션 B" |
| MP-D1-FMP-UPGRADE | FMP 플랜 업그레이드(holdings 엔드포인트 확보) 시 옵션 A 전환 — `weight_source.ACTIVE_WEIGHT_SOURCE`를 'holdings'로 변경 + CB[fmp_etf] 리셋 + Concentration 카드 스모크. 정확한 float-adjust holdings 비중 복원 + ~500 quote/일 호출 제거 | @backend | FMP 플랜 업그레이드 | 🕒 **trigger-gated** — 플랜 업그레이드 전까지 먼저 꺼내지 말 것 | seam 선택 1곳 변경(holdings 경로 휴면 보존 = 코드 그대로) + CB 리셋 + 스모크 |
| **MP-LV-D2** | Briefing task `ModuleNotFoundError: google.generativeai`(구 SDK) → CB[gemini] OPEN, 생성 이력 0 수리 | @backend | - | **완료 2026-06-11** (`62d4025`) | 신 SDK(`from google import genai`, v1.75.0 기설치) import + contents `parts` 포맷 `[string]→[{text}]` 정정(prompt.py+client.py, requirements 변경 0=case ⒜). 검증: `.apply()` SUCCESS → BriefingLog(OK, gemini-2.5-flash) + pytest 138 + brief 카드 재게이트 통과 |
| MP-UX-POLISH | market-pulse-v2 사용자 대면 표면 개선 — raw 전문어/약어 노출(HHI·top5·top10·dispersion·rotation·AD-line·coverage·momentum) + 단위/맥락 없는 raw 숫자(HHI 0.0211) + 용어 도움 인프라 부재(tooltip/glossary 0) + i18n en 백엔드 라벨 0(FE FALLBACK 의존) | @UI-UX-designer → @frontend | MP-LIVE-VERIFY ✅ 통과 | ✅ **자기설명화 완결 close (P1-close, 2026-06-23)** — 중첩 정리 | S1(라벨 단일소스)·S2(의미 밴드)·S3a/S3b(BE history/margin)·TITLE-SOURCE·UX-S5 밴드 전건 완료 + **Translation Layer 본체(S2~S5)로 카드 LLM 해설 중첩분 닫힘**(prose 자기설명 = 사용자 대면 완비). **실질 잔여 = tooltip/glossary 인프라 + EN i18n** → 둘 다 **Phase 1 외 후속 폴리시 이월**(PROGRESS L31 결정, 한국어 모바일-solo 1차 surface, 비게이팅). Phase 1 자기설명화 범위 종료 |
| MP-UX-S1 | 라벨 카탈로그 단일소스화 — KO_LABELS metric/universe/indicator 14키 + raw→translate(요약 5 + detail 4 + StatusBanner) + status·regime detail 이중소스 해소 | @frontend | MP-UX-POLISH | **완료 2026-06-15** (`05e633a`) | KO_LABELS +14키 / 신규 vitest 10 / tsc 0·vitest 184·eslint 0. ff push(ffbe599→05e633a) |
| MP-UX-S2 | 의미 밴드 — 매크로지표 9종 한글 흡수 + Regime 단계 의미 밴드(단계별 색) + Anomaly 모드 의미 밴드 + rule actual↔경보선(`fired[].threshold` FE만) + 직전→현재 전환 | @frontend | MP-UX-S1 | **완료 2026-06-15** (`75eaadb`, rebase 경유) | `meaning.ts` 의미 카피 단일소스 / `indicator.*` 14종 완비(레이더축 raw 0) / 신규 vitest 7 / tsc 0·vitest 191·eslint 0. NEWS-AUTH(`a4c1cc4`) non-ff → rebase(충돌 0/파일 겹침 0) 후 ff push. 근거 DECISIONS "[2026-06-15] MP-UX-S2" |
| MP-UX-S3a | (BE) regime `history_30d` 엔드포인트 — `cards.py _regime_detail`에 추가(breadth/concentration 패턴 재사용) → 국면 타임라인 데이터원 | @backend | - | **완료 2026-06-15** (`abf262a`, S3 Part A) | RegimeSnapshot 41 distinct date → history 30 채움(백필 불요). 무마이그레이션(즉석 쿼리). pytest 4. FE 타임라인 렌더는 후속 FE 슬라이스 |
| MP-UX-S3b | (BE) regime "다음 단계까지 거리"(margin) payload 산출 — 현재 14지표값 vs rules.yaml 다음단계 임계 margin. rules.yaml 백엔드 단일소스 유지(FE 하드코딩 금지) | @backend | - | **완료 2026-06-15** (`6d358e8`, S3 Part B) | `regime/next_stage.py` classifier.load_rules 읽기(임계 하드카피 0) + serializer 즉석 산출(무마이그레이션, `makemigrations --check` No changes). pytest 6. ⚠ 게이지 의미값은 `MP-DATA-MACRO-COVERAGE` 선행. FE 게이지 렌더는 후속 FE 슬라이스 |
| MP-DATA-MACRO-COVERAGE | (ops/data) 거시 시계열 5종(`vix·nfci·hy_oas_pct·t10y2y_pct·t10y3m_pct`) `RegimeSnapshot.inputs` 데이터 공백. **코드 결함 아닌 운영 사안** — fetcher/backfill(`backfill_v2_a1`)/shared 래퍼(`fred_client`)/beat/게이지 경로 전부 기구현(STEP 0 cf82fe9), 원인 = `FRED_API_KEY` 미설정 + 미실행으로 stale(검증 시 5종 19~60일 경과). | @infra(@backend) | - | ✅ **데이터 적재·게이지 점등 검증 완료 (2026-06-16)** — 병진 수동 백필(Economic 153/Market 44 obs) 후 `GET /cards/regime/detail` HTTP 200, 5종 실값(vix 17.68 등)·sources 14/14 OK·coverage 1.0·대기 0·regime=LATE_BULL. serializer/FE 변경 0(신선도가 트리거). **단 지속성=beat 운영 의존**(수동 백필 기반 → beat 미가동 시 ~14일 후 stale 회귀 = 출시 체크리스트). | 신규 코드 0(중복 금지, 규약 10장). `.env.example`에 FRED_API_KEY 추가(재발 방지). 근거 DECISIONS "[2026-06-16] MP-DATA-MACRO-COVERAGE 검증 완결" |
| MP-UX-TITLE-SOURCE | 카드 제목 단일소스 — `card.regime`="시장 레짐"(KO_LABELS) vs CardShell 하드코딩 `"시장 국면"` 불일치(census #4). 표시 용어 '레짐/국면' 산재 → 단일 상수 `REGIME_TERM='국면'` 통일 | @frontend | - | **완료 2026-06-16** (S5 Part C `51303f1`, **origin/main 안착**) | meaning.ts `REGIME_TERM` 단일소스 → RegimeCardSummary/RegimeDetail/RegimeTimeline/page.tsx 치환(표시 문자열만, 로직·enum 불변). vitest +5. 행위보존 PASS(MGMT-FLUSH-2 Phase A) |
| MP-I18N-EN | i18n en 로케일 백엔드 라벨 부재 — `get_labels('en')` 빈 응답 + `_meta.warning='unsupported locale: en'`, FE FALLBACK_LABELS(8키)만 의존. ko 28키 대비 en 백엔드 0 | @backend | - | 🟣 **재배치: Phase 1 외 후속 폴리시 이월 (P1-close STEP 0 확정, 2026-06-23)** | STEP 0 충돌 점검: PROGRESS L31(2026-06-18) "**EN i18n·tooltip/glossary는 Phase 1 외 후속 폴리시로 이월**(게이팅 아님 — 한국어 모바일-solo가 1차 surface)" 명시 결정 존재 → P1-close에서 **닫지 않음**. 한국어 단일 surface 동안 비게이팅. 트리거 = EN surface 필요(국제화 결정) 시 |
| MP-UX-S5-B-SECTOR | 섹터 자금흐름 스파크라인 — SectorCardSummary/SectorDetail에 섹터별 추세선. **선행: `SectorDetail`에 sector history 시계열 부재** → BE 미니슬라이스(additive serializer 필드) 필요. 현재 합성 없이는 불가(합성 금지 원칙) | @backend(history) → @frontend(스파크라인) | MP-UX-S5(머지) | 🕒 **보류 (선행 의존)** — 집중도 스파크라인은 S5 Part B로 완료(`history_30d` 존재). 섹터만 history 부재로 분리 | S5 STEP 0 §0-3 실측: ConcentrationDetail.history_30d 존재 / SectorDetail history 0건. RegimeTimeline·집중도 스파크라인과 동일하게 history 데이터원 확보 후 FE 진행. ⓘ 단서(2026-06-16): FRED 백필로 XL 섹터 ETF bars(Market 44 obs) 신선화됨 → 착수 STEP 0에서 SectorDetail history 필드 존재 여부 재확인 시 선행이 풀렸을 가능성(추측 — 재확인 전 보류 유지) |
| MP-OPS-RESTART | 게이트 후 운영 정합 복구 (병진 수동) — 메인 디렉터리 `main` 복귀 + `git pull --ff-only`(70eb090↑ 정착) + 구 브랜치 `monorepo/sess-mp-kl-f1f3` `-D` + 운영 celery 재기동 + `setup_marketpulse_beat` 재실행(Bug #28 절차) | 병진(수동) | - | ✅ **완료 2026-06-15** | 메인 디렉터리 main 복귀 + merge worktree 제거 + 구 브랜치 `-D`(내용 origin/main 흡수 검증) + celery worker/worker-neo4j/beat kickstart(새 코드 적재) + `setup_marketpulse_beat`(updated=11). 검증 `ACTIVE_WEIGHT_SOURCE=market_cap`/SP500_MCAP + Beat 11종 enabled. 수용 기준 충족 |
| MP-OPS-AUTOGEN-CHECK | 재기동 후 **다음 영업일** 5종 스냅샷(Regime/Breadth/Sector/Concentration/Briefing) beat **자율 생성** 확인 — 이번 게이트는 수동 트리거 검증이었으므로 자율 가동은 별도. ⚠ Briefing은 **LLM 일 1회 과금 시작점** | @infra + @qa | MP-OPS-RESTART | ✅ **완료 (검증 충족, P1-close STEP 0 실측, 2026-06-23)** | STEP 0 실측 수용기준 충족: 5종 스냅샷 전부 당일 row(age=0d, 2026-06-23) + beat **18/18 enabled·최근 72h last_run 보유 18/18**(mp_calc_regime/breadth/sector/concentration·brief·finalize 자율) + Concentration=SP500_MCAP·mp_sync_fred 자율. 재기동(MP-OPS-RESTART 06-15) 후 8일간 매 영업일 자율 생성 지속 = "익영업일 자율 생성" 입증. ⚠ Briefing LLM 과금 가동 중(status=OK) |
| MP-CONC-FREQ-TUNE | 시총 근사 Concentration task ~500 FMP quote/일 — 타 task(EOD/financials/movers) 합산 일 10k 한도 압박 시 주간 빈도 검토 | @infra | - | ✅ **완료 (현행 유지 결정, P1-close 슬라이스 2, 2026-06-23, 코드 0)** | STEP 0 압박 실측: FMP 402/429/rate-limit 로그 **0건** + beat 정상 가동(CB 에러 0) = 일 10k 한도 압박 없음 → **현행 daily(mp_calc_concentration_daily, NY 17:15) 유지** 결정. 코드 변경 0. 재검토 트리거 = 타 task 합산 압박 발생(429/402) 시 |
| MP-OPS-FRED-FRESHNESS | (출시 체크리스트) 배포 환경에서 `update_economic_indicators` beat + RegimeSnapshot 생성 **지속 실행** 확인 → 거시 5종 14일 staleness 방어(미가동 시 게이지 "대기" 회귀). 배포 시 `setup_marketpulse_beat` 재실행(common-bugs #28) + beat DB drift 점검(NT-7) | @infra | MP-DATA-MACRO-COVERAGE | 🟡 **defer/DORMANT (P1-close 결정, 2026-06-23)** — 배포 절차 전용, 출시 없음 | STEP 0: 명시적 "(출시 체크리스트)·배포 환경" = 순수 배포 절차. 개발 중 화면 영향 0(FRED 거시 5종 null 0·regime 정상·mp_sync_fred 자율 3.0h 전). 출시 계획 없음 → defer. 트리거 = **실제 배포 결정 시**. 수용기준(beat 신선·14일 이내·FRED_API_KEY 배포 설정)은 그 시점 검증 |
| MP-OPS-FRED-ENTRYPOINT | v2 11종 + VIXCLS·T10Y2Y를 한 진입점에서 날짜범위 백필하는 **thin wrapper**(기존 `backfill_v2_a1`/`sync_marketpulse_v2_indicators`/`sync_all_indicators` 호출 조합, **신규 fetch 로직 0**). 동기 = VIXCLS·T10Y2Y가 `backfill_v2_a1` 기본목록 밖이라 현재 진입점 분기(`--series-id` 개별 또는 v1 sync 경로) | @infra | - | ✅ **완료 (P1-close, 2026-06-23, `1a25d2a`)** | `backfill_macro_all` 신규 — backfill_v2_a1(기본 econ11+market11) + EXTRA_FRED_SERIES(VIXCLS·T10Y2Y) 개별 호출 조합(**신규 fetch 0·shared 무접촉**). backfill_v2_a1에 `--econ-only` additive 플래그(EXTRA 호출 market 중복 재백필 방지). dry-run 실동작 검증(EXTRA Market=0). 테스트 6 + backfill_v2_a1 기존 7 회귀 0. pytest 237→243. 마이그레이션 0 |
| T-GAUGE-1 | regimeTone 톤 시각 검증 보류 — B-3 게이지(8b14dd8) 라이브 검증 시 5지표 전건 미돌파(LATE_BULL 안정)라 거리 바 중립 slate, regimeTone(돌파 시 강조)은 시각 미노출 = **설계 정합(버그 아님)**. DOM `data-breached=false` 5/5 확인 | @qa | B-3(8b14dd8) | 🆕 경미·데이터종속 | 재개 트리거 = regime 전환 임박/돌파(`to_threshold≤0`) 실발생 시 톤 렌더 재확인 |
| LINK-DATA-FAIL | (트리아지 종결) 메일 CTA 링크 → mp 화면 뜨나 데이터 로드 실패. read-only 트리아지 T1~T6 실측: FE :3000(CORS 포함)·BE :18765 기동·CORS 허용(ACAO 부여)·FE base 정합·CTA 딥링크 파라미터 없음 → **판정 = 인증 게이트(코드 버그 아님)**. overview/cards = `IsAuthenticated`, JWT=localStorage `access_token`. 미로그인 브라우저(로그아웃/토큰삭제/만료+refresh 실패)에서 CTA 오픈 → 401 → "데이터를 불러오지 못했습니다"(mp 페이지 인증 가드 부재). curl `/overview` = 401 실측 | @qa(read-only) | - | ✅ **종결 (2026-07-07, 커밋 0)** — 수리 불요. CORS/base/딥링크 전부 배제(실측). 운영 메모 = common-bugs 등재 | authed 경로 2차 데이터 결함은 미검증(토큰 엔드포인트 상이, 래빗홀 회피) — 인증이 첫 게이트임은 확정 |
| MP-401-MSG | (조건부) mp 페이지 401 구분 문구 — 미인증/세션만료 시 "데이터를 불러오지 못했습니다"(일반 실패)와 구분해 **세션 만료/로그인 안내** + 로그인 리다이렉트(return-to 딥링크). LINK-DATA-FAIL 부 판정(FE UX 갭)의 수리 후보 | @frontend | LINK-DATA-FAIL | 🔒 **조건부 보류** | 트리거 = **실사용 세션만료 혼동 발생**. 그 전 착수 금지 |
| T-GAUGE-2 | 금리차 라벨 절단 — `t10y2y_pct`·`t10y3m_pct` 둘 다 label `w-28`에서 "장단기 금리차(10..."로 절단, 좁은 폭 구분 모호(closest 볼드로 일부 완화). 정확성 문제 아님, 모바일 360px 무오버플로 확인 | @frontend | - | 🆕 경미·UX 저우선 | 후속 라벨 작업 시 묶어 처리(짧은 식별자 "10Y-2Y"/"10Y-3M" 또는 툴팁) |
| MP-UX-BREADTH-BAND | Breadth 의미밴드(변형 A: 종합 밴드 1줄 + 신고저·AD 부제) — `meaning.ts breadthBand`(0.5 중심 ±0.10/±0.20 사다리, 엇갈림 댐핑, FLOW_TONE) + Summary/Detail + `labels.py breadth.*`. **v2 정량 카드 자기설명화 완결**(Regime·Sector·Concentration·Breadth 4/4 밴드) | @frontend | MP-UX-S2 | **완료 2026-06-18** (`43ae93b`) | vitest market-pulse-v2 91→100(+9)·tsc 0·pytest 166·마이그레이션 0. BE serializer/차트 0. ⚠️ 임계 TUNE(dev n=1 미검증) → T-BREADTH-TUNE |
| T-BREADTH-LIVE | dev breadth 실데이터(beat 가동, advance/decline 채워진 뒤) 라이브 밴드 눈검증 — 현재 dev DB 거의 EMPTY(오늘 advance+decline=0→밴드 null)라 라이브 미확인. 컴포넌트 테스트로만 렌더 검증됨 | @qa | breadth beat 데이터 채움 | 🆕 경미·데이터종속 | 재개 트리거 = breadth snapshot 실데이터 누적 후 라이브 카드 밴드 1컷 |
| T-BREADTH-TUNE | 실 SPY breadth(~500종목) 누적 후 `BREADTH_THRESHOLDS`(lean 0.60/broad 0.70) 경계 실분포 재튜닝 — `concentrationBand` TUNE과 **묶음** 처리. 현재 0.5 중심·관례 앵커(STEP 0 dev n=1로 실분포 미검증) | @frontend | breadth 실분포 누적 | 🆕 저우선·TUNE | 실분포 히스토그램으로 5밴드 경계 검증/조정. concentration TUNE 동시 |

## market_pulse Phase 1.5 Translation Layer (2026-06-18 착수)

> 근거: `DECISIONS.md` "[2026-06-18] Phase 1.5 Translation Layer 토대 3결정". 카드 LLM 해설(prose/감각 유추) 레이어. **BOUNDARY-LLM(shared 래퍼)은 별도 트랙 이연 — 본 트랙 무접촉**(래퍼=Brief 패턴 in-zone 재사용). S2~S5 로드맵: TranslationLog → per-card prompt+task → envelope serializer+FE selector+fallback → golden/vcr.

| ID | Task | Agent | Depends On | Status | Output Artifact |
|----|------|-------|------------|--------|----------------|
| MP-TRANSLATION-S1 | Brief LLM plumbing 단일출처 추출 → `apps/market_pulse/llm/` (행위보존 GATE) | @backend | - | **완료 2026-06-18** (`5104635`, origin/main 안착) | `apps/market_pulse/llm/` Brief 플러밍 단일출처. 토대 3결정 DECISIONS 흡수(① 래퍼 in-zone 재사용 ② 별도 translations envelope=TranslationLog ③ golden+vcr) |
| MP-TRANSLATION-S2 | TranslationLog 모델 (BriefingLog 미러, 신규 테이블 1개) — 1 LLM 호출의 카드별 감각 유추 문장 전부를 하루 1행에 담는 그릇 | @backend | MP-TRANSLATION-S1 | **완료 2026-06-18** (`daeef5b`, origin/main 안착) | `apps/market_pulse/models/translation.py` (TranslationLog) + 마이그레이션 0006(CreateModel only, 기존 Alter 0, dry-run No changes) + admin + 모델 테스트 18건. 토큰=BriefingLog 정확 미러(prompt/completion 분리) + created_at만(사용자 결정). 기존 모델 FK 0(decouple). 회귀 pytest marketpulse 166→184(+18). 다음=S3(per-card prompt+task) |
| MP-TRANSLATION-S3 | per-card prompt builder + 생성 task — 1 LLM 호출 → 4카드 감각 유추 JSON → TranslationLog 1행 upsert | @backend | MP-TRANSLATION-S2 | **완료 2026-06-18** (`84b3d76`, origin/main 안착, CS-RD3 drift rebase 경유) | `llm/translation_prompt.py`(SYSTEM_PROMPT+context builder, Brief 패턴 미러) + `llm/translation_safety.py`(validate_senses) + `tasks/translation.py`(`mp_generate_translation_daily`, 공용 `generate_with_circuit` 1회 + JSON 파싱 + `llm.safety` + `update_or_create` upsert) + tasks/__init__ + beat(NY 17:45) + 테스트 11건. **★ HALT 없음, 옵션(a) raw+정성지침(meaning.ts 임계 복제 0).** 마이그레이션 0. 회귀 184→195(+11). 수동 트리거 실 Gemini OK(4 senses, tokens 1129/115). ⚠ cost_usd=null(단가 단일출처 부재, Brief 동일). 다음=S4(envelope serializer+FE) |
| MP-TRANSLATION-S4 | envelope serializer + FE selector + fallback — overview 최상위 `translations` 블록(cards 무변경) + 카드 sense 소비 + 3상태 fallback | @backend + @frontend | MP-TRANSLATION-S3 | **완료 2026-06-18** (`bc01b1e`, origin/main 안착) | BE(`c9a0729`): overview `_build_payload`에 `translations` 블록(senses+model_version+generated_at+status, 없으면 null, 빈senses={}≠null) + `TranslationsSerializer` + cards 불변 가드. FE(`bc01b1e`): `selectSense` selector + 4카드 optional `sense` prop(dumb 유지) + `SenseNote`(없으면 미렌더) + fallback 3상태. 밴드·raw additive 불변. **★ 카드 키 정합, HALT 없음.** 마이그레이션 0. 회귀 pytest 195→200·vitest 100→107·tsc 0. 다음=S5(golden+vcr) |
| MP-TRANSLATION-S5 | golden + vcr 하네스 (+ Brief 동반 보강) — 실 LLM 출력 계약 가드 | @backend + @qa | MP-TRANSLATION-S4 | **완료 2026-06-23** (`4246d48`, origin/main 안착, ff 머지 — push 시 76c0e38→1b28b0c[infra/chainsight] drift는 직전 세션 rebase로 흡수[충돌 0·파일 겹침 0], 본 머지는 1b28b0c→4246d48 FF-SAFE) | **★ STEP 0: vcrpy 미설치·카세트 인프라 0 → HALT 보고 → 사용자 결정 스냅샷 fixture 방식**(실 Gemini 1회 녹화 JSON → golden 재생, 신규 의존성 0·CI 무네트워크). `record_snapshots.py`(수동 recorder) + `snapshots/*.json`(실 Gemini 5개 녹화) + `test_translation_golden.py`(JSON 구조·카드당 길이·`llm.safety` 금지어/refusal 0·**밴드 방향 모순 부재[약한 계약, meaning.ts 임계 복제 0=§10]**·결정론) + `test_brief_golden.py`(Brief golden 부재 종결). 회귀 pytest marketpulse 200→**226(+26, 1 skip)**·마이그레이션 0·프로덕션 로직 무변경(테스트만). **본체 완결(S2~S5) + BOUNDARY-LLM 트리거(a) 충족 플래그**(차터 무접촉) |

## 보류 (On Hold)

| ID | Task | Agent | Reason | Resume Condition |
|----|------|-------|--------|-----------------|
| MM-L | Market Movers AWS Lambda 전환 | @infra | 비용 최적화 우선순위 낮음 | 트래픽 증가 시 |
| GA-1 | Graph Analysis REST API + Frontend | @backend + @frontend | 모델/서비스만 완료 | Chain Sight 안정화 후 |
| SR (트랙) | 서비스 리모델링 — Dashboard / Chain Sight / Portfolio 3탭 전환 (옛 SR-1~4) | orchestrator + @backend + @frontend + @qa | 미시작 계획서. 44일 정체(2026-04-14~). 브랜치 `data_structure_remodeling_V1` 부재. 재개 시 현 시스템(Slice 14~17) 기준 재설계 필요 | 사용자 명시 재개 신호 + 현 코드 기준 설계 재검증. 설계 사고는 `docs/stock_vis_service_remodeling/` 보존 |

---

## [1단 완료·표면 결정 대기] MP-UNIFY — market_pulse v1/v2 공존 통합

- **✅ 1단 = MP-UNIFY-1 백엔드 정리 완료(2026-07-29, `monorepo/sess-MP-unify-1`, base `f7f3f63d`)**: v1 macro 무소비 라우트 7종 제거(fear-greed/interest-rates/inflation/global-markets/calendar/vix/sectors) → v1 API **10→3**(pulse·sync·sync-status). pulse 집계가 5개 섹션 서비스 메서드를 직접 호출하므로 **서비스 로직 전량 존치**(뷰·라우트·개별 serializer 5종만 제거). DELETE 대상 `fred.get_vix()`/`fmp.get_sector_performance()`는 pulse 경유 공유 → 클라이언트 메서드 보존, 뷰만 삭제. 변경 = 백엔드 3파일(−300/+13) + 회귀 테스트 1. **v2·프론트·intraday 무접촉·마이그 0**. 회귀=신규 12 + macro/marketpulse 469 passed·경계 0·health ❌0. 섹터 drift 실노출 소멸(SectorPerformanceView 삭제) — 단 pulse.global_markets.sectors는 FREEZE로 잔존(제품 결정 종속).
- **S0 조사 완료(2026-07-28, read-only)**: 지도 `docs/features/mp_unify/coexistence_map.md`. 브랜치 `monorepo/sess-MP-unify-s0`, base `2a1bd10c`. 코드 변경 0.
- **공존 실체**: v1 = macro 레거시(`/api/v1/macro/*` + `frontend/app/market-pulse`, 라이브 FRED/FMP API, **정식 메뉴 노출 실서빙**). v2 = `/api/v2/market-pulse/*` + `market-pulse-v2`(DB 스냅샷·payload builder, **메뉴 미노출 베타**, v1 배너로만 도달).
- **★타이밍 판정**: 통합은 **서빙 게이트·DB와 독립**(makemigrations 0·v1 전용 테이블 없음·worker_sync=origin/main 통째 checkout 절차 무변경) → **C-N-REPAIR/C-L3 서빙 경로와 무충돌, 서빙 전 완주 가능**(동결 불요). 단 v1 프론트 표면 처분은 제품 결정.
- **분류**: DELETE 후보(v1 `vix/`·`sectors/` 순수 무소비) / MIGRATE(개별 엔드포인트 5종, 서비스 로직은 pulse 경유 유지) / FREEZE(v1 프론트 표면·pulse/sync = 제품 결정 종속).
- **drift**: 섹터 1건(v1 라이브 FMP change_pct vs v2 DB 상대강도·rank) — 코드 존재하나 **v1 sectors 프론트 무소비 + pulse 미포함 = 실노출 0**(대기 불가 버그 아님, 통합 시 v1 삭제로 해소). VIX/금리 source-split(위험 기록).
- **규모 추정**: 엔드포인트 정리 ~1세션 / 표면 통합(메뉴 교체+pulse 처분) ~1~2세션.
- **미해결(read-only 한계)**: v1 실응답 vs v2 실값 비교(서비스 접촉 필요·미측정)·v1 표면 실트래픽·v2 승격 계획·v1 표면 처분 방향 = 디렉터 결정.
- **STRUCT-CLEANUP 대조**: 아래 STRUCT-CLEANUP(intraday→dashboard 이동)과 **별개 축**(intraday=본 조사 "대상 아님"). 병합 불요, 순서 조율만 감안.
- **다음(2단 = 표면 승격 사이클, 제품 결정 선행)**: v1 프론트 표면(`app/market-pulse`) 처분 방향 확정 — v2 흡수 / 리다이렉트 / 메뉴 교체 중 택. 잔여 접촉면 = v1 pulse/sync/sync-status 3라우트 + `components/macro/*` 위젯(`MP-V1-ABSORB` 대상) + Header/MobileNav 메뉴 링크. pulse 응답 계약(fear_greed/interest_rates/economy/global_markets/calendar)은 표면 처분 확정까지 FREEZE.

---

## [보류·DORMANT] STRUCT-CLEANUP — 초기 배포 버전 확정 후 구조 정리

- **상태**: 보류(trigger-gated). 재개 트리거 = **(a) 앱 초기 배포 버전 확정**, OR **(b) 실제 경계 충돌 발생**.
  - ⚠ 명확화(2026-06-11): "(a) 초기 배포 버전 확정" = **출시 선언 시점**을 가리킴. **Phase 1 종료(2026-06-11)로는 미발동** — Phase 1 종료 ≠ 출시. 근거 DECISIONS "[2026-06-11] Phase 1 종료 선언".
- **트리거 전까지**: 세션에서 먼저 꺼내지 않음. (단, 실제 충돌이 생기면 즉시 꺼낼 것)
- **항목**:
  - **intraday(regime/anomaly) → dashboard 도메인 이동.** [STEP 0 완료, **D1 = 보류**, 2026-06-06]
    - 진실의 소스: `DECISIONS.md "D1 — intraday(regime/anomaly) 거취 (2026-06-06)"`.
    - 재개 시 권장: **시나리오 C(포트+레지스트리, BOUNDARY-3 패턴 재활용)** + 모델은 SeparateDatabaseAndState 수동 마이그레이션(자동 makemigrations 금지 — DROP+CREATE = prod 데이터 손실).
    - 재개 시 선결 결정: D1~D5 (dashboard 정의 재정의, anomaly 거시 결합 해소 방향, market_pulse overview 화면 분할 등).
    - dashboard 타 프로젝트 소유 → 양 세션 직렬화(SESSION_CONTRACT.C.3) 필요.
  - *(추가)* 초기 배포 버전 확정 시 함께 정리할 구조 항목들 — 확정 시점에 채움.
- **NT-7과의 관계**: 본 보류에 흡수되지 않음. **NT-7 운영 안정화(Beat 재동기화 + 좀비 워커 정리)는 별도 실행 세션에서 즉시 진행** — 구조 이동과 무관한 운영 트랙.

---

## [🏁 종결·LANDED] BOUNDARY-LLM — shared LLM 래퍼 정합 (옵션 C / burn-down 23→0)

> 형식 결정 = `DECISIONS.md [2026-06-18] BOUNDARY-LLM 통합 래퍼 형식 = 옵션 C`. (라벨 주의: shared 경계 청소 `BOUNDARY-1/2/3`(2026-06-04 종결)과 무관한 별개 트랙.)

- **★ 상태 정정 (2026-07-13, 지시서⑪⑫ origin/main `8dd5ca9` 실측)**: 아래 "DORMANT·미착수" 기록은 **stale**. **실행 완료·landed** — `packages/shared/llm/` 코어(12파일) 존재, LLM 직접호출 **burn-down 23→0** 병합(merge `8be3f65`, 슬라이스①~④), 아키텍처 가드 2종(`test_shared_boundary`·`test_llm_direct_call_boundary`) **KNOWN_VIOLATIONS=0/FROZEN_COUNT=0 7 passed**, `health_check` SSOT 동기. 잔여 테스트 부채 `DEBT-TEST-BOUNDARY-LLM`도 ⑫ C2로 종결. **하류 CS-P2-LLM 언블록.** 아래 원문(트리거·슬라이스 큰그림)은 이력 보존용. (DECISIONS `[2026-07-13] BOUNDARY-LLM 실행 완료` 참조.)
- **상태(원)**: 형식 CLOSED, 실행 DORMANT(trigger-gated). 타 세션 소관 — 본 큐에서 먼저 꺼내지 않음. ← **상기 정정으로 무효**
- **실측 갱신 (STEP 0, HEAD=`feb999b`)**: 통합 대상 = **27파일 / 9 surface**(차터·Translation 인용 "3곳" 무효화). provider 분포 **Gemini 24 : Anthropic 3 : OpenAI 0**.
- **트리거 (차터 §1 "4번째 소비처" 폐기 — 이미 27개로 충족)**:
  - **(a)** Translation 기능이 in-zone 단일출처(`apps/market_pulse/llm/`)로 안정 land 후 "깨끗한 1회 lift" 적기, OR
  - **(b)** escape 없는 신규 LLM surface가 추가되어 보안 회귀가 번질 때, OR
  - **(c)** burn-down 착수 결정 사이클이 별도로 열릴 때.
- **슬라이스 큰그림 (순서·점수는 착수 시 별도 결정)**:
  - ① `packages/shared/llm` 코어 신설 (소비처 0 · portfolio+market_pulse client 합성 · escape/CB/재시도 공통화 · IDENTICAL)
  - ② `korean_overview` 이관 (shared 내부, 최안전 in-zone)
  - ③ 외부-LLM-직접호출 **가드 신설** (코어 land 후 회귀방지 — 현재 가드 부재 = 규약 부채)
  - ④ surface별 점진 (escape 부재 큰 surface 우선)
  - ⑤ rag = **타 surface, 위임/코디** (한 세션에 밀지 않음)
- **착수 전 정정 필요 (2026-06-18 델타 측정)**: DECISIONS BOUNDARY-LLM "코어 베이스 #2" 지칭을 `apps/market_pulse/briefing/client.py` → **`apps/market_pulse/llm/client.py`** 로 정정. (커밋 `5104635`에서 추출·prompt 파라미터화된 정제분; briefing은 위임 잔류, 이 모듈이 정책층 베이스에 더 근접. slice ① "market_pulse client 합성"도 이 경로로 읽을 것.) → DECISIONS 본문 fold-in은 **다음 mgmt 터치 또는 트리거 착수 시**(지금은 메모만).
- **HALT 주의**: 27개 광역 → 한 세션 일괄 금지. cost ledger·BriefingLog·usage 모델 이관이 prod 마이그레이션 건드리면 `makemigrations --dry-run` 후 멈춰 보고.
- **완료정의 (burn-down)**: `packages/shared/llm` 존재 + 27소비처 전부 단일 경유 + 외부-LLM-직접호출 가드 신설 후 위반 0.

### [test 위생 보류] (a)-large stale LLM seam 청소 — 전용 세션 (2026-06-29 등록)
- `tests/news/test_news_deep_analyzer.py` 102e — `mock_genai` fixture 17곳 `.models.generate_content` 직접참조.
- `tests/csv_url_resolver` 계열 `TestLLMAnalysis` 4f — `_llm_client=MagicMock` dead + 3곳.
- 분류 (a) 확정, 프로덕션 정상(이미 이관 완료). mock 본문 재작성이라 기계적 범위 초과 → BOUNDARY-LLM ②③④ 후 전용 세션에서 처리. 동결 카운트 무관.

### [후속 슬라이스] #12 gemini astream 정규화 델타 이관 + #8 shim 제거 (2026-07-02 등록)
- ③b에서 `StreamDelta`/`StreamFinal` 정규화 델타 계약 + anthropic astream 신설 완료. gemini astream은
  #12 IDENTICAL 보존 위해 raw 청크 pass-through 존치(코어가 anthropic만 StreamFinal 인지).
- 후속: `llm_service.py`(#12 gemini stream) 소비처를 정규화 델타(StreamDelta/StreamFinal)로 이관 →
  코어 astream의 gemini 경로도 정규화 yield로 통일 → adaptive #8의 shim(코어 타입→dict) 제거 가능.
- **자기 IDENTICAL 게이트**(delta 시퀀스·usage·봉투 byte 동일). 동결 카운트 무관(이미 #12는 이관 완료 상태).

### [✅ 종결·LANDED] FMP test-debt — env-독립화 (2026-06-29 등록 → 2026-07-14 종결, 지시서⑮)
- ~~`FMP_API_KEY` 요구로 setup 실패 34건: chain_sight 13e · enhanced_screener 12e · provider_factory 9f.~~
- **✅ 해소(브랜치 `monorepo/sess-fmp-testdebt` tip `903e2d7`, 미머지)**: `tests/conftest.py` autouse 픽스처 `_ensure_fmp_api_key`(settings+os.environ 2경로, falsy만 더미 주입=실키 보존, monkeypatch 자동복원). env -i+`FMP_API_KEY=""` → 34 green·라이브 호출 0. "키부재→에러" 계약(`test_fmp_weights::test_missing_api_key_raises`) 보존(PASSED). 전체 회귀 신규 red 0(잔여 13=chainsight, 범위 밖). 프로덕션 코드 변경 0. 결정 `D-FMP-TESTDEBT`.
- LLM 경계 무접촉(버킷A/FMP). BOUNDARY-LLM 범위 밖이었음.

---

## 하네스 구조 개선 (HARN)

| ID | Task | Agent | Depends On | Status | Output Artifact |
|----|------|-------|------------|--------|-----------------|
| HARN-1 | 하네스 4문서(DECISIONS/PROGRESS/TASKQUEUE/common-bugs)의 **append 충돌 구조적 재발** — `.gitattributes merge=union` 적용 또는 세션별 로그 분리 검토 (별도 결정 사안) | orchestrator | - | **완료 2026-06-23** (`642306a`) | 2026-06-12 MAIN-SYNC 머지에서 4문서 전건 충돌 재발(양쪽 append 위치 겹침, 수동 해소). **해소: `.gitattributes`에 4문서 `merge=union` 적용**(`642306a`) → BOUNDARY-LLM consolidation 머지(`63194cd`)에서 DECISIONS/TASKQUEUE 충돌 0 자동 해소 실증(직전 merge-tree는 DECISIONS content 충돌 예측). union=양쪽 라인 보존, 육안검수로 중복 0 확인. 동반: common-bugs **#33 중복**(좀비 Beat ↔ fetch baseline, origin 비고가 예견) 채번 정리 |

---

## dashboard 트랙 보류 (STEP 0 / 2026-06-27)

> dashboard STEP 0 전수 조사 발견 — 전수 조사 단계라 보류, 사라지지 않게 등재. 근거: 보고서 sess-dashboard-step0 @ bbe6b1b.

| ID | Task | 분류 | 트리거(보류시) | Status |
|----|------|------|---------------|--------|
| DASH-TEST | eod 표면 프론트 테스트 0건 (STEP 0 실측 — `app/page.tsx` + `components/eod/**` + `hooks/useEODDashboard` + `services/eodService` 대응 vitest 0건) | dashboard 트랙 직접 | dashboard 표면에 실작업(리팩토링/레거시 정리)이 잡히면 **그 직전 슬라이스** | 🆕 보류 |
| DASH-LEGACY | `app/dashboard/page.tsx`(레거시 계정/네비 페이지, eod 무관) 운명 **KEEP/CUT/MOVE** | 결정 안건 | 전 트랙 STEP 0 완료 후 **일괄 KEEP/CUT 사이클** | 🆕 보류 |
| DASH-VIEWS-EOD | `views_eod` REST API(`/api/v1/stocks/eod/{dashboard,signal,pipeline}`) — 현 프론트 **미소비**(static `/static/signals/*.json`만 소비, 코드젠 타입에만 존재). 존치 vs 폐기 | 결정 안건 | **타 트랙이 이 API를 쓰는지 확인된 뒤**(병렬 경로 안전 폐기 판단 가능) | 🆕 보류 |
## chain_sight 트랙 발견 (STEP 0 / 2026-06-29)

> chain_sight STEP 0 전수 조사 발견 — 사라지지 않게 등재. 근거: 보고서 sess-cs-step0 @ b457bbf.

| ID | Task | 분류 | 트리거(보류시) | Status |
|----|------|------|---------------|--------|
| CS-EXT-API | `insider_tasks`→Finnhub, `sensitivity_tasks`→FMP **직접 `requests.get`**(shared 래퍼·CircuitBreaker 미경유 = 의존 방향 규약 위반) | 결정 안건(이관 설계) + shared 위임 가능 | 전수 조사 후 우선순위 사이클. **※ 행위보존 검증 필수 — 즉시 실행 금지** 📌 **로드맵 Phase 3 선결 조건**(D-ROADMAP-V1) | 🆕 보류 |
| CS-LEGACY | 레거시 serverless Chain Sight v1(`chain_sight_service`·`neo4j_chain_sight_service`·`supply_chain_*`·migr 0009) 흡수 vs serverless 잔류 | 결정 안건(경계) | 전 트랙 STEP 0 완료 후 일괄. 📌 **로드맵 Phase 3 선결 조건**(D-ROADMAP-V1) | 🆕 보류 |
| CS-LAZY | `apps/chain_sight`→`services.{validation,news,serverless}` lazy import 정리 방향(교차 트랙 결합) | 결정 안건(경계) | 동일(전 트랙 STEP 0 후 일괄) | 🆕 보류 |
| CS-CHOICES | ~~`RELATION_TYPE_CHOICES` ↔ DB drift — `PARTNER_WITH`·`DEPENDS_ON` 미정의~~ **✅ PARTNER_WITH·DEPENDS_ON 추가(⑰ S1-a, mig 0017 no-op)**. 잔여=`HAS_THEME`·`HELD_BY_SAME_FUND` **0행 choices 제거 후보**(파괴적, 아래 GRAPH-CHOICES-0ROW로 분리) | chain_sight | ⑰ S1-a | 🟡 부분해소 |
| GRAPH-EGO-NEO4J-REEVAL | Neo4j 거취 재평가 — **동결 중**(D-GRAPH-EGO-BACKEND). **트리거**: 멀티홉(2+hop)·커뮤니티탐지(GDS)·대규모 순회가 제품 요구로 발생 시 Neo4j 재가동+dirty 270 재동기 재평가. 그 전엔 PG 네이티브 ego로 충분 | @backend/@infra | 트리거 충족 시 | 💤 동결 |
| GRAPH-TRUTHSCORE-NORM | truth_score 정규화(0~85 미정규화 → 0~1 또는 0~100). **ego 화면이 소비자가 됨**(truth_score를 굵기/불투명도로 렌더) → 우선순위 상향 후보. 별도 트랙(ego API·기존 소비처 동시 영향, 행위보존 회귀 필요). **★요구사항 추가(S3-LAND, 3순위 사후분석): 재산출 시 산식 버전 + 입력 스냅샷을 기록**(gate_audit·rationale와 동형 감사추적 — "왜 이 점수" 재현 가능하게). | @backend | ego 화면 land 후 | 🆕 후보(상향) |
| GRAPH-CHOICES-0ROW | 0행 choices(`HAS_THEME`·`HELD_BY_SAME_FUND`) 제거 — **파괴적**(choices 제거 시 기존 데이터 유입 경로 확인 필요, migration DDL 가능성). 보고만, 착수 전 영향분석 | @backend | 영향분석 후 | 🆕 후보(보류) |
| GRAPH-NEO4J-SYNC-DEACTIVATE | ~~neo4j sync 3종 Neo4j DOWN → dirty 재동기 실패 반복 → 비활성~~ **✅ 종결(NEO4J-CLOSE-1, 2026-08-20)**: Neo4j 복구·인증 정상화로 조건 충족 → 3종 재활성화(`.save()`+`update_changed()`)·`sync_relations_to_neo4j.delay()` = **synced 14582·dirty 0·neo4j_synced_at 07-11→08-20 06:32 전진**. 레거시 RELATED_TO 정리 1회 발동(10582 reset, 설계된 재생성). | @infra | 완료 | ✅ done |
| CS-TEST | EventBoard/Ranking 테스트 5건 404(`theme_tags` 플래그 OFF ↔ EventGroup 보드 기대, 라우트는 등록됨) | chain_sight 트랙 직접 | 동일(chain_sight 실작업 슬라이스) | 🆕 보류 |

---

## market_pulse + portfolio 트랙 발견 (STEP 0 / 2026-06-29)

> MP STEP 0(sess-mp-step0) + PF STEP 0(sess-pf-step0) 발견 — 사라지지 않게 등재.

| ID | Task | 분류 | 트리거(보류시) | Status |
|----|------|------|---------------|--------|
| MP-FMP-WEIGHTS | `fetchers/fmp_weights.py` raw `requests.get` → FMPClient 경유 통일 (※ **CircuitBreaker는 이미 경유** — 코드 일관성만, chain_sight CS-EXT-API와 급이 다름) | market_pulse 트랙 직접 | market_pulse 실작업 슬라이스 (시급도 낮음) | 🆕 보류 |
| MP-BREADTH-SRC | breadth/concentration **생산(`services.serverless`) ↔ 소비(market_pulse 모델)** 소관 명확화 | 결정 안건(경계) | 로드맵 재검토(Phase 2 촉발 데이터 연계, MP2-DATA-BREADTH-CONC). 📌 **로드맵 Phase 2 촉발 데이터 소관**(D-ROADMAP-V1) | 🆕 보류 |
| MP-NEWS-LAZY | `services/news_aggregator`→`services.news.providers` lazy import 정리 | 결정 안건(경계, news 공통) | 로드맵 재검토 | 🆕 보류 |
| PF-TEST | coach 테스트 **실측 43건**(큐 "5건" 과소평가) `mock.patch("portfolio.…")`·parametrize 문자열 + 경로 오프셋 `parents[2]→[3]` 수정(PR7 이관 후 stale). **✅ 완료** `monorepo/sess-pf-test`(cea40c9 문자열 31건 + e46bb97 오프셋 12건) — pytest apps/portfolio **43 failed→567 passed**(2026-07-13, `pytest apps/portfolio -q --maxfail=1000`), 회귀 0, 로직 회귀 0(전부 이관 잔재), architecture 7 passed. cost_guard 로거명/경로 데이터 3건은 stale 아님→무접촉 | portfolio 트랙 직접 | 완료 2026-07-13 | ✅ 완료 |
| SLICE18-CONTAINER | Slice 18 사용자 상태 그릇. STEP 0 HALT(원안 4모델 중 WalletHolding·WatchlistItem 중복+D1 전제 파기) → 디렉터 재설계(18-R). **✅ 18-R 완료(2026-07-13)** `monorepo/sess-slice18r-container`(base `8dd5ca9`, Part A~F). 신규 **2종만**(UserGoal `user` OneToOne·CashBalance `wallet` OneToOne, D2' house 컨테이너경유 정렬, ScopedManager.for_user)·migration 0002(신규 2 CreateModel만·기존 13 무접촉·--check clean)·services/my_container CRUD·격리 테스트(파라미터라이즈드 누수-0+등록가드+재사용 스모크). WalletHolding·WatchlistItem 재사용(생성 0). **pytest 574→582**(신규 8, 기존 깨짐 0)·architecture 7·health 12✅. 원안 지시서 rev2 교체+REUSE_WIRING. main 랜딩 `50a1738` | portfolio 트랙 | ✅ 완료 | ✅ 18-R 완료 |
| SLICE19A-ENGINE | Slice 19a 목표-대비 권유 엔진. STEP 0 **A-게이트 실패**(forward 기대수익 정본 부재) → 디렉터 재판정 **"정직한 A"**. **✅ 완료(2026-07-13)** `monorepo/sess-slice19a`(base `3d5341e`, Part A~E). ⑴ 카디널리티 전환 CashBalance `OneToOne→FK(Wallet)+unique(wallet,currency)` 다통화(mig 0003·dev·기존 13 무접촉). ⑵ `advisory_engine.py`: 진행 갭(미실현수익률−목표·후행)+배치 갭(유휴현금비중)+모드 분기, 랭킹=RelationConfidence(주)+distance_from_entry(부), 가드레일(유휴현금 억제·집중도 TRIM), 통화 분리. ⑶ 계약 recommend()(BUY/HOLD/TRIM+요약+'예측 아님'). **유령 신호·스코어링 엔진 미참조**(docstring 금지 명시). **pytest 582→592**(신규 10)·architecture 7·health 13✅·--check clean. 미push | portfolio 트랙 | 다음=19b(가중치+교차환전)·Slice 20(화면) | ✅ 19a 완료 |
| SLICE18R-CARDINALITY-REVISIT | 18-R의 `OneToOne` 카디널리티 가정 2건 재검토. **✅ 19a에서 종결(2026-07-13)**: 제품의도 다통화(KRW+USD) 확정 → **CashBalance `OneToOne(Wallet)`→`FK(Wallet)`+`unique(wallet,currency)` 전환**(19a Part A). UserGoal은 단일목표 → **OneToOne 유지**(다중목표 안 함). | portfolio 트랙 | 완료 2026-07-13 | ✅ 종결(19a) |
| SIGNAL-GHOST-FIELDS | `stocks.Stock`의 `analyst_target_price`·`analyst_rating_*`·`forward_pe` = **유령 필드**(선언·serializer 노출되나 writer 전무·항상 null). 프론트로 null 나가 실데이터 오인 위험. → writer 배선 or serializer 노출 중단 결정. 19a 신호 인벤토리(STEP0_SIGNAL_INVENTORY) 발견 | portfolio/stocks | 후보(19a 밖) | 🔶 부채 |
| SCORING-ENGINE-ORPHAN | `apps/portfolio/services/scoring` 12 preset 엔진이 **고아**(종목→정규화 metrics 산출 계산 계층 부재, 유일 호출부 e3_service도 optional skip). 랭킹/기대수익에 미사용. → metrics 리졸버 구축 시 활성화 | portfolio | 후보(19b/미래) | 🔶 부채 |
| FX-PERSIST-ABSENT | 환율 영속 모델 부재. **✅ 19b 종결(2026-07-14)**: `packages/shared/fx.ExchangeRate`(pair,date,close,source) 신설 + `backfill_fx_rates` 백필(USDKRW 1373건/5년) + `get_spot_rate`/`get_rate_on`(영업일 fallback). default-USD 모호는 19a 오배분 규칙 유지 | portfolio/stocks | 완료 2026-07-14 | ✅ 종결(19b) |
| SLICE19B-FXKRW | Slice 19b FX·KRW 기준 통합(토대). STEP 0 게이트1(취득원가 KRW 복원 불가)→디렉터 해소(acquisition_fx_rate ①+수동정정), 게이트2 통과(FMP 5년). **✅ 완료(2026-07-14)** `monorepo/sess-slice19b`(base `bb91c98`, Part A~F). ⑴ `packages/shared/fx` ExchangeRate+백필(1373건). ⑵ `WalletHolding.acquisition_fx_rate`(mig 0004 nullable). ⑶ 갭 KRW 교정(numéraire=KRW, 진행/배치 갭 KRW 통합 정본·통화별 소계 유지, 취득원가 우선순위 exact>approx_first_buy>approx_low_confidence>native_krw). ⑷ fx_context 역사적 백분위(사실, 예측 아님·가중치 X). ⑸ 계약 v2(OUTPUT_CONTRACT_V2). **환율 예측 로직 0**. **pytest 592→602**(신규/갱신)·architecture 7·health ❌0·--check clean. 미push | portfolio 트랙 | 다음=19c(가중치+다이얼+FX매크로)·Slice 20 | ✅ 19b 완료 |
| SLICE19C-ENGINE | Slice 19c 배치 엔진 v2 — 드로다운 비례 다이얼 + 손잡이 5종(A/G/w/L/E, 사용자 주권·기본 보수) + 원장 2종(PortfolioSnapshot·AdvisoryRun). 하드 10%/30% → 산식·L 대체(의도 변경). 코어 랭킹 하이브리드(신뢰도 0.60+진입가 0.25+통화여력 0.15, w 재정규화·상한 0.20 신뢰도 지배 불변식) + 탐험 레인 E(젊음<30일). 원칙 3계층 재정의. 계약 v3. **✅ 완료(2026-07-16)** `monorepo/sess-slice19c-dial`(base `ef8990c`, Part A~G). pytest 602→637(신규/의도갱신 +35·그 외 깨짐 0)·mig 0005(가산만·--check clean)·health ❌0·아키텍처/동결 0. **결정론·LLM 0**. dev만(prod 미적용) | portfolio 트랙 | 다음=랜딩 mgmt·SIGNAL-FORWARD vs Slice 20 순서 | ✅ 19c 완료 |
| FX-ACQ-RATE-WEIGHTED-UPDATE | `WalletHolding.acquisition_fx_rate`(19b 신설)는 매수 시점 USD/KRW 환율. **추가매수로 `avg_cost`가 갱신될 때 acquisition_fx_rate의 가중평균 재계산이 필요**하나 19b 범위 밖. 현재는 사용자 수동 정정으로 커버. Phase 2 Trade 모델 도입 시 자동 계산과 함께 처리 | portfolio | 후보(추가매수 흐름/Trade 모델 시) | 🔶 부채 |
| SIGNAL-FORWARD-INFRA | 기대수익 정본 신호 인프라(analyst target writer / EstimateSnapshot / forward 추정 모델 + PredictionRecord 기록). 완성 시 19a 정직한-A의 갭 계산에 slot-in → **정직한-A → 기대수익-A 승격**. **⬆ 19c에서 우선순위 상승**(원칙 3계층 ⑶ 종목 수익성 예측=목표의 구현 의존물, AdvisoryRun 위 사후분석). 로드맵 배치는 19c 랜딩 후 결정 사이클(Slice 20 화면과 순서 판정) | portfolio 트랙 | **우선순위 상승**(랜딩 후 배치 결정) | 🔮→⬆ 미래 |
| SLICE19D-RECAL | AdvisoryRun 라벨 축적 후 가중치·손잡이 효과 **사후분석 재보정**(성장 부스트 G 실효 검증 포함). 19c 원장이 토대 | portfolio 트랙 | 후보(AdvisoryRun 축적 후) | 🔮 미래 |
| SLICE20A-COACH-UI | Slice 20a — Coach 화면 1부: REST 표면(최신 권유·자산요약·손잡이 읽기·수동진단 POST) + My 탭 권유 읽기 화면 + admin 입력 지름길. AdvisoryRun.trigger 가산(auto/manual, mig 0006) + nightly advisory 태스크. 계약 가산 전용(D0)·유령필드 미노출·손잡이 쓰기 금지(20b). **✅ 완료(2026-07-16)** `monorepo/sess-slice20a-rest`(base `01486cc`, Part A~E). pytest 637→651(+14)·mig 0006 가산만·tsc 0·vitest advisory6/monitor56/coach97·health ❌0. dev만(prod 미적용) | portfolio 트랙 | 다음=랜딩 mgmt·20b | ✅ 20a 완료 |
| SLICE20B-COACH-INPUT | Slice 20b — 손잡이 슬라이더 패널(쓰기 REST, D3=①) + wallet 입력 UI(관심=기존 /watchlist 재사용) + E1~E6 My 탭 연결(D4=섹션만). admin 지름길→지갑 탭 모달 대체. 모델 무변경=REST(knobs PATCH+wallet/cash CRUD)+화면만. **✅ 완료(2026-07-16)** `monorepo/sess-slice20b`(base `8e04a18`, Part A~F). pytest 733→762(+29)·tsc 0·vitest 713→727(+14)·`--check` clean(신규 마이그 0)·health ❌0·손잡이 자동조정 grep 0. 라이브 캡처 3종(지갑탭·손잡이 저장검증 A5 영속화·심층진단). prod 미적용(마이그 0이라 추가분 없음) | portfolio 트랙 | 다음=랜딩 mgmt·beat 등록 결정 | ✅ 20b 완료 |
| COACH-SPECTACULAR-TARGETCLASS | `apps/portfolio/api/openapi_extensions.py`의 coach 확장 12개 `target_class`가 `"portfolio.api.serializers.*"`(apps. 누락) → apps/ 디렉터리 이동 후 `import_string` 실패로 **확장 no-op**(coach e1~e6 spectacular 응답 스키마 빈 상태·"No response body"). committed `lib/coach/api-types.ts`는 이동 전 stale-correct라 화면은 무탈이나 재생성 시 깨짐. 20a advisory_schema는 `apps.` 접두로 수정 완료(동형). **coach도 apps. 접두로 교정 + api-types 재생성 필요** | portfolio/frontend | 후보(20a 밖·선존 버그) | 🔶 부채 |
| MGMT-WORKTREE-VITEST-NOISE | 20b 랜딩 시 발견 — **mgmt 랜딩 worktree(공유 트리 심링크 node_modules)에서 full `vitest` 게이트가 약화됨**. 심링크 node_modules의 이중 React(dual-React) 로 react-query 계열 31~32건이 선존 flake, 병합 표면 스코프도 간헐 1-fail(재실행 green). 병합 결과 게이트를 full vitest 로 못 돌려 **스코프 vitest + 격리 worktree(npm ci) 재측정**으로 대체 중. 근본 해결 후보: 랜딩 worktree 전용 `npm ci`(격리 node_modules) 또는 게이트를 격리 트리에서만 실행하는 규약. 상세=common-bugs "Turbopack 심링크"·[[lesson_turbopack_symlink_and_rq_mutation_test]] | mgmt/frontend | 후보(등재만, 수정 범위 밖) | 🔶 부채 |
| PF-TAX-FEE | 세금·수수료 미반영(KRW 수익률·취득원가에 거래비용·양도세 제외). 19c 범위 밖 부채 | portfolio | 후보 | 🔶 부채 |
| FX-MACRO-B | FX매크로 대체후보(b) — 환율 백분위를 배치 다이얼에 반영하는 대안. 19c에서 **유보**(예측 냄새 평가 필요·다이얼은 dd emergent로 충분). 재검토 후보 | portfolio 트랙 | 유보(19c 밖) | 🔶 유보 |
| PF-LEGACY-FE | `app/portfolio`·`components/portfolio`·`services/portfolio.ts`(레거시 `users.Portfolio` 소비) 귀속 = portfolio 트랙 vs users·auth 표면 | 결정 안건(경계) | 로드맵 재검토(서비스 플로우 "포트폴리오 변화" 표면 연계). 📌 **로드맵 후속 phase**("포트폴리오 변화" 표면, D-ROADMAP-V1) | 🆕 보류 |
| PF-SCORING | `tests/scoring/**` 소속 확정(coach scoring — 소유권 지도 "[경계 보류]" 해소) | 결정 안건(경계) | 로드맵 재검토 | 🆕 보류 |
| PF-LLM-CLIENT | `apps/portfolio/llm/client.py`(anthropic·google.genai 직접) → `packages/shared/llm` 코어 합성 | 타 트랙 위임(BOUNDARY-LLM, portfolio+market_pulse client 합성) | BOUNDARY-LLM 트랙 작업 시 | 🆕 보류 |

---

## B-1 FRED 백필 트랙 처분 (STEP 0.5 / 2026-06-30)

> B-1 깊은 FRED 피처 백필의 STEP 0.5 게이트 결과 등재. 근거: DECISIONS D-B1-SCOPE-DEPTH. B-1 전 사이클 prod 쓰기 0(읽기전용).

> 🏁 **B-1 트랙 종결 보고(MGMT-BATCH-9 실측 정합, 2026-07-13, base origin/main `3b50612`)**: **B-1 코어 트랙 전건 종결 = origin/main에 완전 반영**. 실측 검증: `ef312d6`(S1 백필 land)·`307306d`(S2)·`b45ee1f`(TREND-S4) **전부 origin/main 조상**(머지됨), `monorepo/sess-b1-s2` tip `97f11d2`도 조상(머지됨). **잔여 슬라이스 = 0**(B1-S1 백필+Part4 통과·B1-S2 703행 합성+Part4 통과·B1-S2-FIRE 발화 완료). **두 언락 키 전부 발화**: ⑴ **MP2-ANALOG un-dorm**(D-ANALOG-GATE (a)(b) 충족, 착수 가능) ⑵ **MP2-TREND S4 land + 트랙 재종결**(`b45ee1f`). deferred 잔존 = B1-DEFER(Phase 5 재개 대기)·B1-C2(마이그레이션 결정 사안)·B1-OPS-BEAT(별도 ops 트랙) — B-1 코어와 무관. ⚠️ **stale 전제 정합화**: BATCH-9 지시서는 "ef312d6=s1-fix land, sess-b1-s2 **활성**"을 전제했으나, 실측 origin/main(`3b50612`)에서 s2·FIRE 모두 이미 종결 — 지시서 작성 이후 origin/main 전진(reference lesson: origin/main 세션 중 반복 전진). 종결 보고 요청은 본 실측으로 **자기충족**(별도 보고 세션 불요).

| ID | Task | 분류 | 트리거(재개) | Status |
|----|------|------|-------------|--------|
| B1-DEFER | B-1 FRED 깊은 백필 → Phase 5 Analog 설계 산하로 defer. 사유: 현행 소비자 0(Analog 미구축) + full-vector cap 미해결(조인트 벡터 깊이가 최단 시리즈 HY OAS 2023-06-30에 묶임). 확정 범위·깊이 = A1(활성 11)+B3(2018-01-01). 참조 D-B1-SCOPE-DEPTH. **★착수 STEP 0 필수(2026-07-09 SECTOR-CD S3 추가)**: momentum floor-0 초기 구간 식별·소급 처리 방침 결정 — 계산기가 룩백 부족 구간 momentum을 0으로 floor(SectorFlowSnapshot 초기 5 distinct일 위장), 가짜 0이 소급 차트·cd_state 분석 오염 방지(SECTOR-CD S3 STEP 0-2는 초기 5일 제외로 회피) | market_pulse 트랙(Phase 5 산하) | **Phase 5에서 Analog 매칭 방식(full-vector vs ragged) 확정 시 재개** | 🆕 보류 |
| B1-C2 | C2 처분: (a) PCEPI deprecate(활성 소비처 0), (b) 오라벨 2종(VIX3M·MOVE) data_source 'fred'→'yahoo' 정정. prod DB 필드 변경이라 유보. 참조 D-B1-SCOPE-DEPTH | 병진 수동 | 병진 승인 | 🆕 **보류 확정(B1-S1 STEP 0-5)** — 정정엔 `data_source` choices에 'yahoo' 추가 = 마이그레이션 필요(규칙 #3 HALT). **백필 전제 아님**(data_source=EconomicIndicator 시리즈당 1행, 값 백필이 라벨 증식 0). 별도 마이그레이션 결정 사안 |
| B1-OPS-BEAT | ops: 레거시 경제지표 beat 죽은 정황 — `update_economic_indicators`(celery.py:184)가 FEDFUNDS/UNRATE/CPIAUCSL 1개월 stale(#28 DatabaseScheduler가 dict beat_schedule 무시 패턴). PCEPI 포함 레거시 beat를 한 항목으로 트리아지(piecemeal 금지). B-1과 무관한 ops 트랙 | ops 트랙 직접 | ops 사이클 | 🆕 보류 |
| B1-STEP0 | **STEP 0 전수 실측 완료 (2026-07-09, 읽기전용·FRED 11콜 메타만·DB 쓰기 0, `monorepo/sess-b1-step0` base `e8ffedc`)**. 핵심: ⑴ regime 14지표 = 11 매크로(전부 EconomicIndicator, data_source=fred 라벨) + 3 SPY파생(MarketIndexPrice). ⑵ **FRED obs_start**: NFCI×4=1971-01-08(weekly), **HY pair BAMLH0A0HYM2/H0A3HYC=2023-07-10(daily)=조인트 천장**, T10Y2Y=1976, T10Y3M=1982, VIXCLS=1990. **VIX3M·MOVE=FRED 400(시리즈 아님)→실소스 yfinance `^VIX3M`/`^MOVE`**(현 DB 2026-02-02~, data_source 오라벨=B1-C2). ⑶ 소급경로: FRED 9종=get_series_observations, VIX3M/MOVE=yfinance --period, SPY=yfinance OHLCV → **소급 불가 지표 0**(단 깊이 상이, 조인트 완전벡터 천장=최단 실백필 깊이). ⑷ 완전벡터 **23행**(coverage≥0.999, 2026-07-09 최신, 구 22→23). ⑸ RegimeSnapshot 65행/unique[(date,)]/intraday전용/마이그레이션 불요(과거일 삽입=서빙창 필터). ⑹ **momentum floor-0 = 06-29 XLF 단 1행**(B1-DEFER의 "초기 5일 위장" 가정 **반증** — 초기일 실값 보유). **M8**: 07-09 이후 신규 거래일 **0개**(반전율 미측정, 시뮬 서빙앵커 0.1776 병기). **M9**: health_check 12→11은 항목 제거 아님 = OK/WARN 집계 차(당시 '실행 트리 정합' WARN, `f084cd6`/`ad3ae77`/`04a5b61`서 항목 추가만, 현 13항목). | market_pulse 트랙 | **범위 결정 세션 대기(디렉터)** — full-vector vs ragged·깊이(HY 2023-07-10 vs VIX3M/MOVE yahoo 실깊이)·floor-0 방침·M7 선택지 | ✅ **STEP 0 완료** |
| B1-S1 | 원시 시리즈 백필 (깊이 A 조인트 천장 **2023-07-10**, D-B1-SCOPE). 대상 = FRED 9(NFCI×4·HY×2·T10Y3M·VIXCLS·T10Y2Y) + yahoo 2(VIX3M·MOVE) + SPY OHLCV. 경로 = `backfill_v2_a1 --from 2023-07-10`(창·멱등·FREDClient 단일). 신규 커맨드 0, 스키마 무변경 | market_pulse 트랙(병진 수동 실행) | **병진 수동 백필 실행 대기(재실행)** → 실행 후 Part 4 검증 | 🔵 **장애 triage 종결(2026-07-10)** — 1차 실행서 FRED 전건 0행(Yahoo 3종 정상). 원인=`_fetch_fred`가 get_series_observations limit 미override(기본 100·desc→최신 100건 기존행만→skip). 수정 land(`7759265` limit=100000·asc + fetched/inserted 로깅, `edc25fc` 테스트, common-bugs 2건). 인증·CB·환경 무관. **병진 재실행 = 원 4개 명령 그대로**(멱등, Yahoo 3종 이미 완료분 skip). ✅ **백필 완료·Part 4 검증 통과(2026-07-10)**: 전 daily 시리즈(HY×2·T10Y2Y·T10Y3M·VIXCLS·VIX3M·MOVE·SPY) 최초일 **2023-07-10 정확 도달**(+0일), NFCI×4만 +4일(주간 금요일 구조=정상). 창내 행: HY 787·T10Y2Y/3M 750·VIXCLS 774·VIX3M 753·MOVE 748·SPY 768·NFCI 156(주). +갭(T10Y2Y +35 등)=휴장일(정상). **DGS10/DGS2 각 +507행**(후보리포트 skip 예측 벗어남 — 기본목록 경유 심화, 실 FRED·무해). 원시 14/14 가용=**150 영업일**(=금요일), 10/14=599일(NFCI×4 비-금요일 결측=S2 forward-fill 대상). NFCI 전 156행 **금요일**. **다음=B1-S2**(주간 forward-fill 정렬 + 14벡터 소급 합성 + rules.yaml 소급) |
| B1-S2 | 벡터 소급 합성 (D-B1-SYNTH) = **현행 로직 as_of 매개변수화**(별도 forward-fill 발명 없음 — max_age 캐리가 주간 NFCI 정렬 자연 수행) + 시계열 순차 hysteresis chaining + rules.yaml 소급 적용(과거 국면 재구성, D-ANALOG-GATE 원문 경로). S1 백필 land 의존 | market_pulse 트랙(커맨드 land=Claude Code / 합성 실행=병진 수동) | 커맨드 land(`60e9083`) → 병진 실행(2026-07-10) → Part 4 통과 | ✅ **트랙 종결(B-1 종결, 2026-07-10)** — 병진 합성 완료: **703행**(2023-07-10~2026-04-24)·완전벡터 **683**·분포 TRANSITION469/LATE_BULL228/CRISIS6. **Part 4 전건 통과**: 라이브 66행 불변(2026-04-27~07-10)·겹침0·total 769(66+703)·leading gap 정직(07-10 cov0.500 INSUF/07-11~13 cov0.643 OK)·**멱등 prod 확증**(재-dryrun synth0/skip703, 경계 붕괴 없음) |
| B1-S2-FIRE | **B-1 트랙 종결 발화(완료)** — 병진 합성 + Part 4 통과로 발화: ⑴ **MP2-ANALOG un-dorm** — D-ANALOG-GATE 트리거 (a)(b) 동시 충족(비-LATE_BULL 475일·CRISIS 6·완전벡터 683 재구성 검증 통과). ⑵ **MP2-TREND S4 동면 해제**. | market_pulse 트랙 | 발화 완료(2026-07-10) | ✅ **발화 완료** |

---

## Phase 1 제시 로깅 (STEP 0 / 2026-07-01)

> dashboard Phase 1 제시 로깅 STEP 0(sess-dash-p1-log) 발견. 근거 DECISIONS "[2026-07-01] Phase 1 제시 로깅 STEP 0"(D-P1-STEP0).

| ID | Task | 분류 | 트리거(보류시) | Status |
|----|------|------|---------------|--------|
| P1-REC-PROD | 추천 생산 방식 결정 — **EOD-bake 확장**(shared/stocks) vs **뉴스추천 승계**(services/news). 이게 제시 로그 스키마(signal_tag/horizon)·confidence 출처·impression write 경로를 확정 → 선결 결정 | 결정 안건 | ~~다음 결정 사이클~~ | ✅ **해소 (D-P1-RECPROD, 2026-07-02)** — EOD-bake 확장 + Baked impression + confidence v1 결정식. 실행은 shared/stocks 위임 대기 |
| P5-EXCESS-BACKFILL | `SignalAccuracy.excess_{h}d`(SPY 상대) 백필 — prod 3,611행(~12%)만 채워짐 vs return 29,962. **벤치마크 상대 채점 채택 시 선결**(raw return 채점은 즉시 가능하므로 조건부) | 트랙 위임(shared/stocks) | Phase 5 벤치마크 상대 채점 채택 시 | 🆕 보류 |
| HC-MARKER-TREADMILL | health_check "origin/main 해시" 마커가 **매 mgmt 머지마다 lag=1**(커밋이 자기 머지-후 해시를 스스로 못 적는 구조적 한계). 현재 tolerance N=3가 흡수해 대개 green이나, 마커 3커밋+ 미갱신 시 붉어짐(이전 STEP 0 세션 시작 시 실제 red 이력). **임시 규율**: 매 mgmt에서 마커를 현 origin/main으로 갱신해 lag=1 clean 유지(누적 방지). **durable**: health_check가 "메타-only·lag=1" 시그니처를 허용하도록 수정(하네스 코드 = 별도 슬라이스). **📌 보강(2026-07-02 preflight)**: N=3 tolerance가 lag=1을 흡수 재확인(5d35fa7 마커=3d670ed=HEAD~1 green). ❌는 lag>3에서만 발현 추정 → **durable 긴급도 하향**, 우선 tolerance 경계 문서화. | 하네스 개선(HARN) | durable = 하네스 코드 슬라이스(긴급도↓) / 임시 = 매 mgmt 상시 | 🆕 등재(임시 규율 상시 적용) |
| DASH-FE-GLOB | frontend 실경로 = `frontend/app/page.tsx`(≠ 소유권 글롭 `app/dashboard/**`, 레거시 계정 페이지) 재확인 → 소유권 지도 v2 **실경로 반영**(dashboard 불일치-A 후속) | mgmt | 다음 mgmt(급하지 않음 — 이미 D-P1-STEP0·소유권 지도에 사실 기록됨) | 🆕 보류 |
| P1-BUILD | 병합 스키마(**D-SCHEMA 9필드**)로 **발행 로그 모델 신설**(SignalAccuracy 형제, `packages/shared/stocks`) + **baker `recommend`/`thesis`/`carousel` 필드 add**(dashboard.json 추천 계약 서빙). 빌드용 worktree 브랜치 `monorepo/sess-p1-recprod`. **게이트**: 순수 add(dry-run `No changes` 기저 확인됨)·IDENTICAL(기존 6키 signal_cards 행위보존)·회귀 green·**write 표면 0**(serve 무변경). grain=`(stock,signal_date,signal_tag)`(D-P1-GRAIN) + confidence=formula v1·conf_ver=1(D-P1-CONF). **선결 결정 4종 완비**(참조 D-P1-RECPROD·D-SCHEMA·D-OWN·D-P1-GRAIN·D-P1-CONF) + 정렬·계약 확정(D-P1-REC-RANK·D-P1-REC-CONTRACT). **✅ land `1995f93`**(IssuanceLog 0009 순수 add + baker recommendations additive + 발행로그 write). 완료 근거: 게이트 전건 통과(순수 add·IDENTICAL·회귀 142 green·write표면0·구획 clean·health ✅) + `deece55` 위 rebase clean(4파일 무충돌) → **ff push `deece55..1995f93`**. 첫 실파이프라인 관측은 P1-OBSERVE(후속) | 트랙 위임(shared/stocks · **dashboard 디렉션** D-OWN) | 완료 2026-07-03 | ✅ 완료 |

---

## Phase 2 촉발(제품 로드맵) — ②Viewed defer (2026-07-02)

> 로드맵 Phase 2 촉발 두 축 중 ②만 defer(①촉발 표면화는 즉시 착수). 근거 DECISIONS D-MP2-SEQ. ※ 내부 MP2-ANALOG/MP2-ALERTS 트랙(TASKQUEUE 상단 'market_pulse v2 Phase 2 로드맵')과 **별개** — 라벨 충돌 주의.

| ID | Task | 분류 | 트리거(재개) | Status |
|----|------|------|-------------|--------|
| MP2-VIEWED | ②Viewed enrichment(per-user impression, `presented_as='viewed'`) → **defer**(drop 아님). 사전 조율: 발행 로그에 필요한 필드(`user_id`·`signal_date`·`ticker`·`horizon`·`presented_as`) 요구를 dashboard 세션에 전달. 참조 D-MP2-SEQ | Phase 2 촉발 ② | **Phase 1 발행 로그(shared/stocks) 스키마 land 시** | 🆕 보류 |
| P2-VIEWED-TABLE | **Viewed 별도 테이블 신설**(`presented_as='viewed'` 경로) — **D-SCHEMA의 baked/viewed 분리 결정 후속**. 발행 로그에서 `presented_as` 컬럼을 뺀 대가로, 노출 수준 채점은 이 테이블 join으로 복원(Phase 5). MP2-VIEWED enrichment의 **물리 저장소 스텁**(형제 항목). 참조 D-SCHEMA | Phase 2 촉발 ②(물리 스텁) | ✅ **P1-BUILD land(`1995f93`) 충족** — 잔여 트리거 = Phase 2 진입 결정(별건) | 🆕 트리거 충족·Phase 2 대기 |
| P2-IMPRESSION-BUILD | **ImpressionLog 축 구현**(D-P2-IMPRESSION 실체화 — "봤다"=뷰포트 50%×1초 IntersectionObserver, serve-time 로그, #43 경계 = IssuanceLog 무변경). **슬라이스 예정**: S1 shared 스키마(모델·마이그레이션) → S2 API 수신 엔드포인트 → S3 프론트 훅·표면 연결(5초 flush + visibilitychange/sendBeacon). ~~**구획 메모**: S1·S2 = shared/백엔드 구획~~ **▶ S2 구획 갱신(→ RESOLVED, D-P2-S2-PLATFORM, 2026-07-14)**: **S2는 shared 아닌 신설 `apps/platform`(제3범주 telemetry 홈)** — 상세=아래 P2-IMPRESSION-BUILD-S2 행. S1=shared(완료)·S3=dashboard 구획. **build 지시서는 본 등재 완료 후 별도 발급**(등재→build 규율) | S1 @backend(shared)·S2 @backend(apps/platform)·S3 dashboard FE | Phase 2 진입·build 지시서 발급 시 | ✅ **CLOSE (2026-07-16, MGMT-P2-IMPR-CLOSE)** — S1·S2·S3 + **FIX-1**(`46e6865`, telemetry 절대 base) 전건 완료 + **육안 실증**(양 표면 dashboard_eod·news_chip 수신·upsert·click append). 개통 중 500 2건 해소(DECISIONS "P2-IMPRESSION-500 사건": migrate 0010 미적용·상대 URL stale rewrite). 후속 부채 4건 = 아래 신규 등재 |
| P2-IMPRESSION-BUILD-S2 | **S2 impression 수신 API**(D-P2-S2-PLATFORM 실행) — 신설 `apps/platform`에 `ImpressionIngestView` + URL `/api/v1/telemetry/impressions` + 테스트. write 대상 = shared `ImpressionLog`(S1). 인증 = **IsAuthenticated 전용 시작**(user_id nullable = 익명 예약·현 미사용). 배치 계약 = **sendBeacon 배열 payload + 5초 flush**(선례 0, 신규 설계). #43: IssuanceLog 무접촉. **build 지시서 별도 발급** | @backend (apps/platform 신규 구획) | Phase 2 진입·build 지시서 발급 시 | ✅ **완료** — `ImpressionIngestView` + `/api/v1/telemetry/impressions`, IsAuthenticated. 배치 계약은 실현 시 **keepalive fetch + JWT 헤더**로 조정(sendBeacon 헤더 제약, D-P2-S2-PLATFORM 백-어노테이션 ⑴). 부모 CLOSE에 포함(2026-07-16) |
| PLATFORM-INGEST-DB-ISOLATE | impression ingest 뷰의 `_record` **DB 예외를 per-item 격리** — 한 항목의 구조적 DB 오류가 배치 전체 500을 내지 않도록 surface 유지 설계(DIAG-1 방안 2). 정상 항목 수신 + 오류 항목만 rejected 집계 | @backend (apps/platform) | P2-IMPRESSION-BUILD CLOSE | ✅ **완료 (2026-07-16, `238c410` → merge `4e166d5`)** — per-item `transaction.atomic()` savepoint + rejected_reasons 봉투(invalid/db_error). 테스트 +4(전량유효·혼합격리·전량실패 2xx·빈배치). DECISIONS 백-어노테이션(MGMT-BATCH-10 ①) |
| FE-DEAD-8000-SWEEP | **:8000 참조 일소** — next.config stale rewrite 정정 + authAxios `http://localhost:8000/api/v1` 하드코딩 폴백 제거(ops/env·FE 위생). 앱 API 호출은 절대 base 규약(#55) 단일 준수 | @frontend + @infra | — | ✅ **완료·착지 (2026-07-16, `9f03a30` → merge `af1e37a`)** — `grep ':8000'` 0·fail-fast 단일소스 `lib/api/config.ts`·rewrite 사멸·tsc0·vitest 707·build 성공. **⚠ 착지만 — prod 반영은 FE-8000-PROD-APPLY(별건, #53 착지≠반영)** |
| FE-8000-PROD-APPLY | sv-web-runtime을 `af1e37a`로 갱신(`worker_sync`/re-detach) + **재빌드**(NEXT_PUBLIC_API_URL 빌드 인라인 → 재빌드 필수) + **:3000 재기동**. GATE TRUE(.env.local 키 존재) 확인 완료(MERGE-CLEANUP-2). :3000 서빙 부활 + impression 수집 재개 + **WEB-RUNTIME-RUNBOOK 초안 채록 겸함** | @infra | FE-DEAD-8000-SWEEP 착지(완료) | ✅ **완료 (2026-07-18 집행)** — 트리 `bea1de0`(⊇af1e37a)·`next start` prod 전환·:3000 200·홈+리더보드 실렌더·절대 base(:18765) 확인·**impression 재개 8행**(dashboard_eod 4+news_chip 4). 절차 = WEB-RUNTIME-RUNBOOK 전사. DECISIONS 백-어노테이션(MGMT-BATCH-12) |
| WEB-RUNTIME-RUNBOOK | :3000 서빙 실체(sv-web-runtime) 성문화 — dev/prod 구분·기동/재빌드·번들 검증 절차 | @infra | FE-8000-PROD-APPLY 집행 | ✅ **완료 (2026-07-20, MGMT-BATCH-12)** — `docs/operations/web-runtime-runbook.md` 성문화(서빙 실체 정정: launchd 무감독·`com.stockvis.web`=daphne 별개 / 6단계 절차 / 검증 3종 / 리스크 3). **종전 "launchd 입양 고아" 서술은 오인 → 정정 반영** |
| LAUNCHD-WEB-PLIST-LOAD | `:3000` prod 서버 **launchd 정식 등록**(재부팅 지속) — plist 초안 `docs/operations/com.stockvis.web-frontend.plist` 검토 → `~/Library/LaunchAgents` 복사 + `launchctl bootstrap` **사용자 수동** → 재부팅 후 :3000 자동 부활 검증. ⚠ 적용 전 npm/node 절대경로 실측 교정(초안값) | @사용자수동 | plist 초안 검토(MGMT-BATCH-12 완료) | ✅ **완료 (2026-07-24 집행, Gate4 사용자 명시 승인 절차)** — launchd job `com.stockvis.web-frontend` bootstrap 성공. 검증 3종 PASS: launchctl list `12408 exit0`·lsof :3000 node LISTEN·curl HTTP 200. ⚠ 서빙트리(`sess-hold-p1` base `6973bda`) 디스크 plist=교정 전 초안 → 설치 차단, `git show origin/main:…plist`(nvm 절대경로 교정본) 우회 배치. KeepAlive+RunAtLoad 승격 = orphan 무respawn 근본 해소·impression 재개. 재부팅(집행 7h 전) 선행으로 **다운타임 0**(#66) |
| WEB-NEXTOLD-CLEANUP | `.next.old-1784176095` 격리 백업(구 빌드, `sv-web-runtime/frontend`) 정리 — 무해하나 디스크 점유. 사용자 수동 `rm -rf` | @사용자수동 (저우선) | — | 💤 **등재 (저우선·수동, MGMT-BATCH-12)** |
| IMPR-OBJREF-TRUNC | (저우선) `object_ref` 128자 절단 충돌 부채 — 실데이터는 finnhub 단축 id URL이라 위험 낮음 관측(2026-07-16). 뉴스 식별자 재설계 시 함께 처리 | @backend (저우선) | 뉴스 식별자 재설계 시 | 💤 등재 (저우선·수용, MGMT-P2-IMPR-CLOSE) |
| HEALTH-STALE-FAIL-PROMOTE | **[C] health_check stale pending WARN→FAIL 승격** — `check_stale_pending_backannotation`(MGMT-HARDEN `4ce46ed`)을 1주 클린 관찰 후 FAIL로 격상. 트리거 = **~2026-07-20**(1주 클린) | mgmt(health_check) | ~2026-07-20 (1주 클린 관찰 후) · **HEALTH-BLOCKED-BUILD 착지 선행**(D-HEALTH-BLOCKED-DISTINCTION) | **✅ done 2026-07-20 (승격 완료)** — 근거: DECISIONS.md:740 "[C] HEALTH-STALE-FAIL-PROMOTE(07-20 승격) 후 첫 실측 = 승격 성공 판정" + MGMT-MICRO `75551966`이 이 FAIL-승격 로직 경유로 health **15/0/0** 도달(2026-08-11 재실증). 〔status 교정: 🕓 대기 → done, MGMT-BATCH-A 유령 2건 교정〕 |
| HEALTH-BLOCKED-BUILD | **health_check에 'blocked(외부 의존)' 상태 인식 구현**(D-HEALTH-BLOCKED-DISTINCTION 실행) — `check_stale_pending_backannotation`이 `blocked(dep=<TASK-ID>)` 문법을 파싱: blocked 항목은 **WARN 유지**(FAIL 승격 제외), 순수 부기 누락만 FAIL 대상. **남용 방지**: `dep=<TASK-ID>`의 TASKQUEUE 실존 검증(미실존 시 검사 실패). + 테스트(blocked WARN 유지·부기누락 FAIL·미실존 dep 거부) | @mgmt-tooling (health_check) | D-HEALTH-BLOCKED-DISTINCTION | **✅ done** — 구현 실재 재확인: `scripts/health_check.py` `_BLOCKED_RE`(:917)+`evaluate_stale_pending`(:956, dep 실존 검증)·테스트(`tests/test_health_check_stale_blocked.py` 5 passed)·브랜치 `monorepo/sess-health-blocked-build` origin/main 소진(merge-base ancestor). dep D-HEALTH-BLOCKED-DISTINCTION done. 〔status 교정: 🆕 등재 → done, MGMT-BATCH-A 유령 2건 교정〕 |
| HEALTH-STALE-TRADINGDAY | (저우선) health_check stale pending 임계 **"3 달력일" → "3 거래일" 교체** — 트리거 = **NYSE 거래일 유틸 도입 시**. 현행 WARN 전용이라 달력일 근사 **수용 상태**(비차단, MGMT-HARDEN) | mgmt(health_check, 저우선) | NYSE 거래일 유틸 도입 시 | 💤 등재(수용·게이트) |
| P1-OBSERVE | 첫 EOD-bake 실행 후 **실파이프라인 관측**. **✅ 충족 2026-07-04**(D-P1-OBSERVE-DONE): JSON recommendations N=10·6키 IDENTICAL + DB IssuanceLog 10행=N·grain 중복 0(멱등 실증)·conf_ver=1·published_at·user_id null·매도 30%. 결함 2건(워커 표류·0009 미적용) 경유 해소 | 관측(dashboard 디렉션) | 완료 2026-07-04 | ✅ 충족 |
| P1-B-WORKER-WORKTREE | **worker 전용 worktree**(`~/worktrees/sv-worker-runtime` detached origin/main) + `celery-worker.sh` PROJECT_DIR/plist + 심링크(방향 반전 방식 Y) + `scripts/worker_sync.sh` 신설 — 브랜치 표류 트레드밀 종료. **✅ 완료 2026-07-05**(OPS-B-BUILD): 스크립트 land `921dc0c`, 검증 bake 2회(심링크 생존·6키 IDENTICAL·N=10·IssuanceLog 10행 멱등·HTTP 200). 심링크 방향 반전 = D-B-WORKER-AMEND-1 | ops/infra | 완료 2026-07-05 | ✅ 완료 |
| B-HARDEN-OUTPUT | (휴면) baker `OUTPUT_DIR` **env override** 추가 — 심링크 의존 제거. 트리거: **worker 트리 이전 또는 다중 출력 필요 발생 시**. 현재는 심링크(방식 Y)로 충분 | ops/infra(휴면) | worker 트리 이전·다중출력 시 | 💤 휴면 |
| B-CLEANUP-PREB | `frontend/public/static/signals_pre_b`(B′ 전환 전 백업) **제거**. 트리거: **정상 거래일 자동 beat 1주기(월~금) 무결 통과 후**. **카운트 5/5 도달**(7/6·7/7·7/8·7/9·7/10 전 행 무결 bake). **제거 완료**: 대상 = 5.0M·Desktop 트리·미추적(git 무관)·DB 무관(정적 백업 디렉토리) — STEP 0로 대상 실체 확정 후 **사용자 수동 rm 완료**(2026-07-13, MGMT-BATCH-9). Phase 1 잔여 0 해소의 한 축(D-P1-CLOSE) | ops(정리) | 5/5 발화 → 제거 완료 | ✅ **종결 (2026-07-13)** |
| P1-HC-ISSUANCE | 발행 로그 감시 = **C 계층**(D-HC-ISSUANCE): ⑴ bake 자가검증 ⑵ health_check 최소. **✅ done `2e3b91e`+`ad3ae77`(HC-BUILD)** — 회귀 155·migration 0·실관측 통과(07-08: issuance_verified 10/10 ok·검문소 07-07 행10 OK·무경보). 짝 = common-bugs #46 | ops(health_check) | 완료 2026-07-08 | ✅ done |
| P1-RUNBOOK-MIGRATE | 운영 절차(runbook): **land에 migration 포함 시 운영 DB `migrate`를 배포 단계로 명시**. 0009 미적용 재발 방지 | ops(docs) | 착수가능 | 🆕 등재 |
| P1-TAG-VOCAB | 검증: **signal_tag 어휘 대조** — 실데이터 관측치 `S2`가 등록 태그 집합에 속하는지 + D-P1-GRAIN 표기(V1/P2/S1 예시)와 대조. 불일치 시 장부 표기 정정 안건화(결정 무효 아님, 예시 표기 갱신) | 검증(read-only) | 착수가능 | 🆕 등재 |
| P1-BEAT-PRECHECK | ~~월요일 beat 전 공유 트리 re-detach 점검~~ **✗ 폐기 2026-07-05** — B′ 완료로 목적 소멸. 워커가 공유 트리 **비의존**(전용 worktree + worker_sync.sh)이라 공유 트리 표류가 bake에 영향 없음 | — | — | ✗ 폐기(B′ 완료) |
| CAROUSEL-BUILD | dashboard 추천 캐러셀 A+ 구현(components/eod + page.tsx, D-P1-CAROUSEL). **✅ 완료 2026-07-06**(land `24b0e47`): RecommendationCarousel+Card·types/eod Recommendation·Level 2.5 배선, vitest 7·tsc 0·하위호환 고정·shared 무접촉. ⚠ 화면 도달은 W′ 완료 시 | dashboard FE | 완료 2026-07-06 | ✅ 완료 |
| W-BUILD | **web 전용 서빙 worktree**(`~/worktrees/sv-web-runtime`) + next dev(:3000) 서빙 대상 전환 + `worker_sync.sh` 공통 동기화 확장 + node_modules `npm ci` 설치. **✅ 완료 2026-07-06**(OPS-W-BUILD, D-W-WEB-AMEND-1): 대상 정정(com.stockvis.web=daphne 오지목→next dev), worker_sync.sh land `75cb4d3`, 검증(:3000 web 서빙·bake 통주·공유 트리 무접촉·실화면 캐러셀 렌더). #45 web 판 해소 | ops/infra | 완료 2026-07-06 | ✅ 완료 |
| W-HARDEN-BUILD | (휴면) dev server → `next build`/`next start` 전환 검토. 트리거: **외부 노출 또는 성능 문제 발생 시**. ※ W-HARDEN-LAUNCHD와 한 안건 통합 검토 | ops/infra(휴면) | 외부 노출·성능 문제 시 | 💤 휴면 |
| W-HARDEN-LAUNCHD | (신규) next dev **데몬화**(현재 수동 `nohup`, 재부팅 시 수동 재시작 필요) — W-HARDEN-BUILD(next build/start 전환)와 **한 안건 통합**. 트리거: **재부팅 후 화면 다운 경험 또는 외부 노출** | ops/infra(휴면) | 재부팅 다운·외부 노출 시 | 💤 휴면 |
| DAPHNE-RUNTIME-SURVEY | (신규, read-only) daphne(`com.stockvis.web`, :18765)의 **공유 트리 결합 실측**(#45 세 번째 인스턴스) → B′/W′ 패턴을 daphne로 확장할지 결정 입력. **✅ 완료 2026-07-06** — 실측 입력으로 D-DAPHNE-RUNTIME 확정(마진 1.80). daphne는 API 관문이라 표류 시 백엔드 응답 자체가 구코드 = 피해 최대 | ops(조사) | 완료 2026-07-06 | ✅ 완료 |
| DAPHNE-BUILD | **daphne 전용 서빙 worktree**(`~/worktrees/sv-api-runtime` detached origin/main) + 기동 스크립트 PROJECT_DIR 전환 + `scripts/worker_sync.sh`에 daphne 추가. **✅ 완료 `803e9a9`** — baseline 전후 일치·CWD api트리·WS 101·:3000 200·공유 트리 무접촉. 런타임 3종 격리 완결. #45 세 번째 인스턴스 해소 | ops/infra | 완료 2026-07-06 | ✅ 완료 |
| DAPHNE-GRACEFUL | (휴면) daphne 재기동 시 WS 연결 끊김 → graceful reload. 트리거: **재기동 끊김이 실사용 불편으로 관측 시** | ops/infra(휴면) | 재기동 끊김 관측 시 | 💤 휴면 |
| CAROUSEL-COLOR-REVIEW | 캐러셀 방향 색 크로스-화면 정합 판단. **✅ 결정 완료 2026-07-06** → D-COLOR-SYSTEM(앱 표준 = 한국축: 상승·매수·긍정 rose / 하락·매도·부정 sky, sectorColor.ts 정합). 캐러셀 현행 emerald=매수는 Stage 1(COLOR-STAGE1)에서 rose=매수로 전환 예정, 과도기 반전 명시·수용 | dashboard FE(디자인) | 완료 2026-07-06 | ✅ 결정 완료 |
| COLOR-STAGE1 | **dashboard 구획 한국축 전환** — `components/eod` 로컬 `colorSemantics.ts` 도입, 방향성 색을 D-COLOR-SYSTEM(rose=긍정/매수·sky=부정/매도)으로 통일. **✅ 완료 `3a4706f`**(colorSemantics.ts 신설 + 6컴포넌트, tsc0·vitest509, 실화면 검수 통과 07-06) | dashboard FE | 완료 2026-07-06 | ✅ 완료 |
| COLOR-STAGE2-chain_sight | chain_sight 방향성 색 한국축 전환(EventRanking·MetricCell 등). **✅ 완료 `9fe326f`**(자기 구획 로컬 시맨틱, import 금지 준수) | 트랙 위임 | 완료 2026-07-07 | ✅ 완료 |
| COLOR-STAGE2-market_pulse | market_pulse regime/flow `meaning.ts` 한국축 전환. **✅ 완료 `3253cd1`(merge `9169ea9`)** — CRISIS→sky(라벨 보존)·FLOW_TONE 디커플링·잔여 rose 오버로드 2건 수용(DECISIONS 판정 기록) | 트랙 위임 | 완료 2026-07-07 | ✅ 완료 |
| COLOR-STAGE2-portfolio | portfolio 수익=rose/손실=sky 전환(PortfolioSummary·Table·Chart·Modal·RealtimePortfolio **5파일 글로벌축 잔존**). **💤 보류 확정**(D-COLOR-SYSTEM 추기) — 트리거 = **portfolio 트랙 재개 시 그 첫 슬라이스에 선행**(별도 색 슬라이스 신설 대신 흡수). D-COLOR-TOKEN에 따라 재개 시 shared 토큰 **직소비**(로컬 경유 없음) | portfolio FE | portfolio 트랙 재개 시 | 💤 보류 |
| S3-COLOR-ALIGN | MP2-TREND S3 z-score 멀티라인과 market_pulse 색 시맨틱 겹침 조율. **✅ done** — `CUT_STROKE.CRISIS = HEX_SIGNED` 소비 정합(regime 색 한국축 일치 확인) | market_pulse FE | 완료 2026-07-09 | ✅ done |
| COLOR-WARN-SCHEME | (휴면) rose 의미이동(위기→긍정)으로 발생한 **잔여 rose 오버로드 정리** — 경고/위기 표현을 색 아닌 별도 수단(아이콘·채도·라벨)으로 완전 분리. 트리거: 잔여 rose 오버로드가 실사용 오독으로 관측 시. 참조 D-COLOR-SYSTEM 판정 기록 | FE(디자인) | 오독 관측 시 | 💤 휴면 |
| COLOR-TOKEN-PROMOTE | `colorSemantics` shared 토큰 분할 승격(D-COLOR-TOKEN). **✅ done `694d6f5`** — components/common/colorSemantics.ts 신설(14 export, DIRECTION_HEX 축분리 D-COLOR-TOKEN-AMEND-1) | FE(shared) | 완료 2026-07-09 | ✅ done |
| TOKEN-RECLAIM-eod | eod 로컬 → shared 토큰 회수. **✅ done `d70d665`**(6소비처 전환·로컬 삭제, DIRECTION_HEX→HEX_CHANGE, tsc0·색단언 무수정 green) | dashboard FE | 완료 2026-07-09 | ✅ done |
| TOKEN-RECLAIM-market-pulse | market-pulse-v2 로컬 → shared 회수. **✅ done `8194fd7`**(DIRECTION_HEX→HEX_SIGNED, 행위보존) | market_pulse FE | 완료 2026-07-09 | ✅ done |
| TOKEN-RECLAIM-chainsight | chainsight 로컬 → shared 회수. **✅ done `c9310fb`**(순수 import swap, 행위보존) | chain_sight FE | 완료 2026-07-09 | ✅ done |
| SYNC-ENTRYPOINT | repo 스크립트 실행 고정 진입점(D-SYNC-ENTRYPOINT) = 래퍼 `~/bin/sv` + 자기가드. **✅ done `942a991`·`f084cd6`** — stale abort·health WARN·sv health 12/12·3종 트리 일치 실증. #47 구조 해소 | ops/infra | 완료 2026-07-09 | ✅ done |
| VERIFY-SUITE-BASELINE | full-suite 140 거짓 red 규명(검증 세션, 쓰기 0). **✅ done(판정 a — 환경 아티팩트)** — 격리 npm ci·v22.19.0에서 519/519 green(심링크 실패 파일 실설치 전건 통과). #48 실증 | @qa | 완료 2026-07-09 | ✅ done |
| TEST-ENV-POLICY | full-suite 게이트 환경 정책 결정. **✅ done** — D-TEST-ENV 등재(이원 정책 A)로 종결 | @qa | 완료 2026-07-09 | ✅ done |
| TEST-ENV-GUIDE | (신규, 소형 ops) `sv health`(또는 health_check)에 "**full-suite 전 npm ci 격리 확인**" 안내 추가. 참조 D-TEST-ENV | ops/infra | 트리거: 다음 ops 접점 | 🆕 등재 |
| THEME-HEAT-AUDIT | (신규) 공유 트리 세션의 **메타 직접 편집 흔적** + node_modules **심링크 오염 관여**(#48 원인 환경) 확인 — 4턴 이월 중이므로 큐 등재로 고정 | chain_sight 트랙 | 트리거: chain_sight 다음 접점 | 🆕 등재 |

---

## Phase 2 촉발 표면 구현 (MP2-SURFACE / 2026-07-02)

> D-MP2-SURFACE 확정(B 독립화면 + 변형1 위계). 근거 DECISIONS D-MP2-SURFACE.

| ID | Task | 분류 | 트리거 | Status |
|----|------|------|--------|--------|
| MP2-SURFACE | market-pulse-v2를 **변형1 위계**(regime hero + 국면별 판단 카피 + 촉발 카드 + 섹터 히트맵 + prose)로 재구성. **기존 breadth/concentration/brief 카드 행위보존**(떨어뜨리지 말 것). 국면별 판단 카피 = 정적 테이블(LLM 미사용). 참조 D-MP2-SURFACE | market_pulse 트랙 직접 | 구현 STEP 0 후 착수 | 🆕 착수가능 |

---

## MP2-SURFACE 잔여 (2026-07-02)

> MP2-SURFACE land 후 잔여. 근거 DECISIONS D-MP2-SURFACE / PROGRESS 2026-07-02.

| ID | Task | 분류 | 트리거 | Status |
|----|------|------|--------|--------|
| MP2-SECTOR-COLOR | 섹터 색 관례 불일치 — 신규 `SectorHeatmap`=상승 빨강(한국) vs 기존 `SectorCardSummary`/`SectorDetail` 드로어 `sectorFlow`=상대강세 녹색(서양). 같은 섹터가 요약↔상세 다른 색 → 혼란. 전면 한국 관례 통일(사용자 #1 한국). **완료** — sectorColor.ts 단일유틸(상승 rose/하락 sky) 4컴포넌트 통일, 요약↔상세 뒤집힘 0 | UI 결정+FE | — | ✅ **done (5459bce)** |
| MP2-SECTOR-SENSE | 섹터 요약이 히트맵으로 교체되며 sector 한국어 sense(TranslationLog) 미표시(translation_fallback 4→3). Brief prose는 유지. **완료** — SectorHeatmap에 selectSense sector sense 한 줄 복원(SenseNote, 없으면 미렌더) | FE | — | ✅ **done (5459bce)** |
| MP2-HEATMAP-FETCH | (관찰) 11-타일 히트맵이 요약 화면에서 sector 상세 eager fetch(로드 시 1콜 추가). 계약 무변경·기능 정상 = **버그 아님**. 선제 최적화 지양(측정 우선). overview 11섹터 additive 부착 전환은 실 성능 데이터 확보 후 판단 | 관찰(성능) | 실측 성능 이슈 시 | 🔵 관찰 |
| MP2-COLOR-AUDIT | (C안) 앱 전면 up/down 색 관례 감사 — sector 외(TickerBar·breadth·concentration·시그널 등). sector는 MP2-SECTOR-COLOR로 한국 통일 완료. **착수 트리거 = sector 외에서 실제 색 뒤집힘/불일치 관찰 시**. 선제 감사 지양(측정 우선) | 관찰(UI 일관성) | 색 불일치 관찰 시 | 🔵 관찰 |

---

## News AV broad 백필 옵스 (2026-07-07)

> 배치1 마감(표적 복구 06-18/19 + 갭 07-04~06, 10호출) 세션 잔여. 근거 project_news_av_broad_track / PROGRESS.

| ID | Task | 분류 | 트리거 | Status |
|----|------|------|--------|--------|
| NEWS-AV-SANITIZE-METRIC | sanitize 발동 카운터/메트릭 부재 — 방어 계층별(provider `url>2000` skip · `_save_articles` 기사별 savepoint skip) 발동 통계 없이는 **"포이즌 미조우 vs sanitize 선차단" 구분 불가**. sanitize 유지 가치 판단의 근거로 추후 필요. (배치1 전 창 `skip=0` 로그는 있으나 provider단 선차단 건수는 별도 미집계 — `skip=0`이 "오염 무"인지 "provider가 이미 걸러냄"인지 판별 불가) | @backend/@infra | sanitize 유지·제거 판단 필요 시 | 🆕 저우선 |
| EVENTGROUP-WINDOW | `event_group_pipeline._build_base`가 `ChainNewsEvent` **전량(무윈도우)** 소비, `as_of = max(published_at)`. 데이터 누적 시 오래된 co-mention이 현재 내러티브를 희석(그룹 구성이 최신 신호만 반영 못 함). **날짜 윈도우(half_life 기반 컷오프 또는 최근 N일) 도입 검토** — as_of는 max라 전진하나 클러스터링 입력은 전체라 신선도 편차. | @backend | 그룹 내러티브 신선도 이슈 관측 시 | 🆕 저우선 |
| NEWS-AGG-TEST-ENV | `NewsAggregatorService.__init__`가 `FinnhubNewsProvider`를 즉시 생성 → **Finnhub 키 하드 의존**. 키 부재 환경(settings_test)에서 `ValueError` → savepoint 회귀 테스트(`test_aggregator_savepoint`) 포함 뉴스 계열 테스트가 **침묵 실패**(env 사유로 red). `__init__` 의존 지연/분리(lazy provider init) 또는 테스트에서 provider mock 격리 검토. | @backend/@qa | 뉴스 테스트 green baseline 필요 시 | 🏁 **종결 2026-07-13 (지시서⑦ S5, `3a781a5`)** — finnhub/marketaux 키 조건부 + provider 주입 인자. `test_aggregator_savepoint` env 부재(FINNHUB=[]/MARKETAUX=[]) green 확인. 키 관용화 테스트 3건 |
| MKX-MATCHSCORE-BACKFILL | 기존 저장 `NewsEntity.source='marketaux'` **7,148행 match_score 가 [0,1] 밖**(min 1.75·max 299.6·avg 35.7 — 모델 validator 0~1 위반). S4(`ba…` 지시서⑦)가 **쓰기 경로만** 정규화(100 saturation clamp) → **신규분만 정상**. 기존 7,148행은 `raw/100 clamp` 로 일괄 정규화하는 멱등 backfill 커맨드 필요(읽기 소비처=API serializer 뿐, co-mention 미사용이라 파급 낮음). | @backend | match_score API 노출 정합 필요 시 | 🆕 저우선(backfill 후보) |
| NEWS-URLNORM-IDQUERY | 🔴🔴 **긴급 — S3 이미 배포·활성(게이트 지나침).** 지시서⑨ 실측: 워커 PID 80710이 07-13 11:31 재기동으로 S3 코드(쿼리 전량 제거) **로드·활성**. 기존 저장분은 raw 보존이라 **아직 collapse 미발생(예방 단계)** 이나, **다음 수집 발화(collect_av_broad_news 07-14 01:00 UTC)부터** finviz.com/quote?t=TICKER(AV **1,675**개)·youtube ?v=(FMP 1,961) 등 **공유경로 URL이 붕괴** → 서로 다른 티커가 1건으로 병합돼 **co-mention 조작(허위 공동언급)**. 골든셋: (a+b) 100,268행(88.4%) IDENTICAL 필수, 실위험 22그룹/3,695행(youtube·finviz 2도메인 집중). **교정 = "tracking만 제거, id-쿼리 보존"(+Hybrid 도메인 규칙) — 07-14 01:00 UTC 전 완료 시 순수 예방.** 설계=`docs/news/urlnorm_idquery_survey_2026-07-13.md`. | @backend | **⑩ 즉시(다음 발화 전)** | 🏁 **종결 2026-07-13 (지시서⑩ Blocklist 베이스, `64c8589`)** — normalize id-쿼리 보존(utm_*·fbclid·gclid·ref만 제거). 골든셋 (a)+(b) 100,245행 IDENTICAL 불일치 0, collapse 22그룹 완전분리. STEP1 beat 20건 가역정지→배포→재활성. 기존 저장분 무손상(예방 성공). DECISIONS `[2026-07-13] NEWS-URLNORM-IDQUERY` |
| NEWS-URLNORM-HYBRID | Blocklist 베이스(⑩)가 **과소병합** 잔존: AMBIG 8,856(msn 렌더링 파라미터·finviz 뷰 파라미터 등)이 보존돼 dedup 덜 됨(가역·무해). Hybrid = 도메인별 규칙(예: msn 렌더링 파라미터 제거, finviz 뷰 파라미터 정리)으로 안전 정리. ambiguous key(cid·ocid·mod·amp·lang) 개별 재판정 포함. | @backend | dedup 정밀도 개선 필요 시 | 🆕 저우선(⑩ 후속 최적화) |
| MKX-URLNORM-BACKFILL | S3(지시서⑦)가 AV/FMP url 정규화 forward-only 적용 → 기존 저장 raw url 무변경. **지시서⑧ 재산정**: 잉여 3,954행 중 **안전 병합=139행뿐**(tracking만 빼도 동일=진짜 중복, 대부분 FMP 스토리지 위생), 나머지 3,815=가짜충돌(오병합 위험). **AV 관련 안전 병합=단 1행** → cross-provider co-mention 왜곡 노출 무시가능. backfill 저가치 + **NEWS-URLNORM-IDQUERY 정밀화 선결**. | @backend | 정규화 정밀화 후 + co-mention 교정 필요 시 | 🆕 저우선(저가치, 선결조건 有) |
| EVENTGROUP-WINDOW | ~~`event_group_pipeline._build_base`가 `ChainNewsEvent` **전량(무윈도우)** 소비, 오래된 co-mention이 현재 내러티브 희석.~~ **✅ 완료(2026-07-13, 지시서⑬)**: `_build_base`가 `window_days`(기본 21·config) 실적용 — as_of 기준 ≤window_days만 카운팅. as_of는 window 전 전량 max로 고정. `half_life`→`window_days` 정합 리네임(단일파일). 골든 회귀 in-window IDENTICAL·out 제외 30.2%(1694/5616)·희석 30%→0. 스키마 무변경. 결정 `D-EVENTGROUP-WINDOW`. | @backend | — | ✅ 완료 |
| NEWS-AGG-TEST-ENV | `NewsAggregatorService.__init__`가 `FinnhubNewsProvider`를 즉시 생성 → **Finnhub 키 하드 의존**. 키 부재 환경(settings_test)에서 `ValueError` → savepoint 회귀 테스트(`test_aggregator_savepoint`) 포함 뉴스 계열 테스트가 **침묵 실패**(env 사유로 red). `__init__` 의존 지연/분리(lazy provider init) 또는 테스트에서 provider mock 격리 검토. | @backend/@qa | 뉴스 테스트 green baseline 필요 시 | 🆕 저우선 |

---

## MP2-DELTA — 촉발 심화 축1(어제 대비 변화) (2026-07-03)

> MP2-DEEPEN(전조+원인) 완료 후 남은 심화 축. 근거 D-MP2-DEEPEN / STEP 0 af08007.

| ID | Task | 분류 | 트리거 | Status |
|----|------|------|--------|--------|
| MP2-DELTA | 축1 어제 대비 변화(델타) — regime 전환 · sector rank 이동 · anomaly 신규/소멸. **유일 신규 파생**(데이터 시계열은 완비: RegimeSnapshot previous_regime · SectorFlowSnapshot date별 · AnomalySignalLog triggered_at, 단 2날짜 비교 서비스 신규). 전조·원인(MP2-DEEPEN)보다 손이 감. 참조 D-MP2-DEEPEN | market_pulse 트랙 직접 | 다음 촉발 심화 슬라이스 | 🆕 착수가능 |

---

## MP2-DELTA 슬라이스 (2026-07-03)

> 촉발 심화 축1(어제 대비 변화). 근거 D-DELTA-CALC/SCOPE/YDAY.

| ID | Task | 분류 | 트리거 | Status |
|----|------|------|--------|--------|
| MP2-DELTA-S1 | 슬라이스1 = regime from→to(previous_regime 재사용) + sector 순위 델타(조회-시 파생) + DeltaCard "어제와 달라진 것". prod 0·마이그레이션 0 | market_pulse 트랙 | — | ✅ **done (421fefe)** |
| MP2-DELTA-S2 | 슬라이스2 = **anomaly 신규/소멸/해소** 델타 + 무발동일 표시. "어제"=**직전 발동일 대비**. D-DELTA-QUIET(옵션2 해소 명시) + R3 실측=판별 불가 → **5c-ii 폴백(무발동일 항상 quiet)**. anomaly_delta additive(4상태). 참조 D-DELTA-QUIET | market_pulse 트랙 | — | ✅ **done (b29067e)** ⇒ **MP2-DELTA 트랙 종결** |
| ANOMALY-RUN-EVIDENCE | (관찰 항목, 측정-우선) anomaly engine 실행 흔적(run-marker) 도입 시 D-DELTA-QUIET의 resolving 활성화 가능. 현재 AnomalySignalLog는 발동 행만 적재 → 무발동일 quiet로만 수렴. **실제 오독 사례 관찰 시 착수**(계약엔 resolving/resolved_rules 자리 이미 존재) | market_pulse 트랙 | 오독 관찰 | 👁 관찰 |

---

## MP2-TREND 슬라이스 — 멀티라인 시계열 (2026-07-06) — ✅ **트랙 종결 (2026-07-07)**

> 공용 MultiLineTrendChart + 적용 N곳. 근거 D-TREND-PLAN/BASELINE/TOOLTIP.
> **종결**: S1·S2·S3(R1) 전건 land(origin/main). ~~S4(z-이상도 뷰)는 **동면** — 트리거 B-1 land(Phase 5)까지 착수 금지 유지.~~ → S4 동면 해제(2026-07-10, B1-S2-FIRE) → **S4 land(2026-07-10) = MP2-TREND 트랙 재종결**. z-이상도 뷰는 703 소급 시계열 baseline 위에서 구현 완료.

| ID | Task | 분류 | 트리거 | Status |
|----|------|------|--------|--------|
| MP2-TREND-S1 | 1호 = 공용 `MultiLineTrendChart`(recharts, 크로스헤어+고정 리드아웃·반전축·범위/범례 토글, overlays 타입만) + 11색 팔레트 + sector_history rank additive + 섹터 순위 궤적. emphasis=서버 rank leaders/laggards(FE 델타 재계산 금지). prod 0·마이그레이션 0 | market_pulse 트랙 | — | ✅ **done (c1cdba4)** |
| MP2-TREND-S2 | 2호 = 전환일 오버레이 공용 계약(previous_regime≠regime 파생) + breadth 궤적(A/D + 기준선 MA20) + overlays.vlines·refSeries 렌더 + 델타 강조 복원(옵션 B, D-TREND-EMPHASIS 안전판 통과). 전부 조회-시 파생·계약 additive·마이그레이션 0 | market_pulse 트랙 | — | ✅ **land (7678ec2)** — pytest 신규6/api72·vitest 신규9/전체518·tsc0·mig0 |
| MP2-TREND-S3 | 3호(개정 R1) = **국면 재료 판정-거리 소형 다중**(옵션 B). z-score 전제 STEP 0 반증(classifier=raw 복합 룰, D-TREND-BASELINE-R1) → 룰-구동 7지표 raw 스파크라인 + rules.yaml 실제 컷 hlines + 판정거리. 세그먼트 [판정거리 | 이상도(z)🔒 예약탭](D-TREND-VIEWMODE). 컷 하드코딩 0(rules.yaml 단일소스). 조회-시 파생·마이그레이션 0 | market_pulse 트랙 | — | ✅ **land (R1, 코드머지 `8842531`, COLOR-STAGE2 CUT_STROKE 정합 포함)** — pytest 신규8/api80·vitest 신규8/전체526·tsc0·mig0. **트랙 마지막 슬라이스 → MP2-TREND 종결** |
| MP2-TREND-S4 | 4호 = **z-이상도 뷰** — 예약 placeholder → 실 뷰(절충안 격자형, D-S4-FORM). 전용 엔드포인트 `regime/zscore`(고정 소급 모집단 baseline·serve-time z·24h 캐시·다운샘플 57.1KB, D-S4-ENDPOINT/BASELINE). baseline 순수함수=ANALOG 재사용 단일소스 | market_pulse 트랙 | B-1 land(충족) | ✅ **land (2026-07-10, `monorepo/sess-s4`: BE `e418829` + FE `a9cb79b`)** — pytest 358→374(+16)·vitest 295→304(+9)·tsc0·mig0·health13/0·payload 57.1KB. **MP2-TREND 트랙 재종결** |
| S4-REBASE | z baseline μ·σ **재기준** — 라이브 축적분을 모집단에 포함해 잣대 갱신(현재 = 소급 703 고정). 소급 vintage(D-B1-VINTAGE)와 라이브 실시간 값의 분포 차이 흡수. **재기준 동반: 성분 상관 가족 재판정(현 판정=2단, FAM1{ddown,vix,vix3m}·FAM2{9성분}, 가족간|ρ|0.178)+analog 카드 문턱(K·τ_radius·τ_alert) 재산정+MPS 성분 편입 심사(Tier1+2)+level_band 문턱 재산정+percentile window 정의 재검(803 중 부분벡터 ~120일 혼입 — 분모 순도: 고정 683 vs 가용전체 803)** | market_pulse 트랙 | **라이브 축적 1년 도달** | 🕒 예약(데이터 게이트) |
| A-S0 | analog 사후수익 SPY EOD 보존 예외 — 롤링 purge(`cleanup_old_data` 365일 blanket)가 백필 SPY 매주 삭제(683→199). `PRESERVED_INDEX_SYMBOLS={SPY}` exclude(방식 나, 모델 무변경). 참조 D-ANALOG-SPY-RETENTION | market_pulse 트랙 | — | ✅ **land (2026-07-13, `monorepo/sess-A-spy-restore` `01c99b1`)** — 회귀 3·마이그레이션 0 |
| A-PREP | SPY EOD 3년 재백필 — `backfill_spy_eod`(shared FMP 래퍼·dry-run 기본·멱등). 683 사후수익 모집단 회복. A-S0 의존(재소실 방지) | market_pulse 트랙 | 커맨드 land → **--commit 실행(2026-07-13)** | ✅ **완료 (2026-07-13, `--commit` 병진 승인 실행)** — 500행 삽입, **SPY 765행 2023-07-14~2026-07-11 연속**. **683 통합검증 통과**: 사후 계산가능 ≤20d **683/683**·+60d **678/683**(5 우변절단). A-S0가 이후 purge서 SPY 보존. Slice B DoD 683 통합 GREEN |
| INDVAL-PURGE-LANDMINE | **동류 지뢰 등재** — `cleanup_old_data`가 IndicatorValue 3년 백필도 blanket 삭제 중(A-S0는 SPY만 보존). 현재 analog 벡터=stored(RegimeSnapshot.inputs)라 무영향이나 **S4-REBASE 재합성 시 71% 결손 재현**. 해소=A-S0 동형(시리즈/코드 보존 예외) | market_pulse 트랙 | **S4-REBASE 착수 시 선행** | 🕒 예약(재합성 게이트) — common-bugs [보존 함정] 등재. **A-STRUCT 접점(INC-MPS-BACKFILL-SCOPE)**: 섹터 ETF 3년 이력이 정식 필요해지면 `backfill_v2_a1`(econ+심볼) 재백필 + A-S0식 심볼 보존 예외가 **검증된 경로**(이번 우발 백필이 커맨드 동작 실증) |
| S4-EXPAND | z 뷰 **카드 탭 확대 뷰 + 정렬 토글**(|z|순 ↔ 지표순) — S4 범위 밖(격자형만 land). 종합 이상도 지수도 후보 | market_pulse+FE 트랙 | **MP2-ANALOG 세션에서 순위/확대 시각 어휘 구축 시 함께** | 🕒 예약(어휘 게이트) |

## Carousel LLM 채움 (LLMFILL / 2026-07-09)

> 근거 DECISIONS `[2026-07-09] D-LLMFILL`. CAROUSEL-BUILD(`24b0e47`)가 심은 3키 placeholder(thesis·perspectives·risk)를 EOD-bake 조립 직후(삽입 지점 A)에 shared LLM 래퍼 경유로 채운다. 부분 실패 내성(카드별 개별 호출) + `pipeline_meta.llm_fill` 관측(#46형 검문소 짝).

| ID | Task | 분류 | 트리거 | Status |
|----|------|------|--------|--------|
| LLMFILL-BUILD | `packages/shared/stocks/llm/` 신설(card_fill_prompt + fill_service) + baker 삽입 지점 A additive 배선 + item 가드 테스트. **✅ done `9f2355d`** (scoped 161: 기존 150 IDENTICAL + 신규 11, 실호출 0, diff=자기 구획 6파일, ff push). 편차 1건=닫힌 집합 격리 patch(→ PM-CLOSEDSET-LLMFILL) | @backend (shared/stocks 구획) | 완료 2026-07-09 | ✅ done |
| PM-CLOSEDSET-LLMFILL | `pipeline_meta` 닫힌 집합 단언(test_eod_issuance_log)에 `llm_fill` **정식 등록** + `_bake_patches` 격리 patch 제거(issuance_verified 등록 방식 동형). BUILD의 구조 충돌 편차 정리 | @backend (소형) | 착수가능 | 🆕 등재 |
| LLM-GUARD-3 | 외부-LLM-직접호출 **가드 신설**(BOUNDARY-LLM 슬라이스③ 연동 — 코어 land 후 회귀방지). 본 슬라이스(LLMFILL) 스코프 분리분. 트리거: **다음 shared/llm 접점**(BOUNDARY-LLM 트리거 (b) 누적 또는 burn-down 착수) | @backend (BOUNDARY-LLM 연동) | 다음 shared/llm 접점 | 💤 등재(트리거 게이트) |
| LLMFILL-OBSERVE | LLMFILL-BUILD land 후 첫 무인 bake 관측. **✅ 종결·판정 (a) 전건 성공**(07-09 bake filled 10/10·실패 0·$0.001001·6832tok, 파일↔스냅샷 일치, 7 core 무결, IssuanceLog 10/10 ok, 홈 렌더·콘솔0, fundamental=null 정직 실증). D-LLMFILL 추기 | 관측(dashboard 디렉션) | 완료 2026-07-10 | ✅ done |
| LLMFILL-FUND-MATERIAL | **재료 확장으로 `fundamental` 채움률 개선(수리 아님)**. 관측(MGMT-BATCH-9): `fundamental=null`은 **영구 결손이 아니라 조건부** — 07-09 채움 **0/10**, 07-10 채움 **1/10**. 날조 억제 설계대로 작동(재료 부족 시 채우지 않음 = 정직 null, D-LLMFILL "fundamental=null 정직" 승계). 개선 경로 = **투입 재료(펀더멘털 컨텍스트) 확장**이지 프롬프트/파서 수리가 아님(현행 동작은 결함 아님). 착수 시 STEP 0 = null 사유 실측(재료 부재 vs 게이트 과보수) | @backend (shared/stocks 재료) | 재료 확장 우선순위 결정 시 | 💤 등재(재료 게이트) |
| LLMFILL-PROVENANCE | `pipeline_meta.llm_fill`에 **provider·fallback_from 출처 기록** 정식화(어느 LLM/폴백 경로로 채웠는지 관측 축). shared 트랙 회부 — burn-down·계약 영향 실측 후 착수. 저우선(MGMT-BATCH-13 적립). | @backend (shared 구획) | 없음 | 🆕 등재(저우선) |

---

## MGMT-BATCH-7 후속 (theme-heat 감사·이주 + dedup 부채 / 2026-07-09)

> 근거 DECISIONS D-THEMEHEAT-AUDIT·D-OWN-HOME + common-bugs #44 강화·#49·#50. theme-heat land 게이트 + 선존 union 중복 정산 + stray 문서 회수.

| ID | Task | 분류 | 트리거 | Status |
|----|------|------|--------|--------|
| THEMEHEAT-LAND-GATE | `sess-cs-theme-heat` land 전 **mgmt 선행 정산 세션 필수** — ① 브랜치 #47 → 실측+1 재번호 ② mgmt 밖 등재 결정 3건(결정7·8·9) 정합 검토 ③ 메타 4종 union 중복 #44 전수 스캔. **단순 rebase-push 금지** | mgmt(chain_sight) | theme-heat land 착수 시 | 🔒 게이트(land 전 필수) |
| PROGRESS-DEDUP-MONITOR | PROGRESS 활성 Monitor 블록 **×5**(2939→5482자, 비-동일본) per-copy superset 검증 후 **5→1**. **blind collapse 금지**(#44 ⑶) | mgmt(dedup) | monitor-rebuild 트랙 접점 | 💤 트리거 게이트 |
| PROGRESS-DEDUP-MP2TREND | PROGRESS 활성 MP2-TREND Slice 3 블록 **×2**(2009 vs 2076자, 비-동일본) 동형 superset 검증 후 2→1 | mgmt(dedup) | MP2-TREND 트랙 접점 | 💤 트리거 게이트 |
| STRAY-DOCS-13 | primary 미추적 **13건** 트랙별 회수/폐기 분류(chain_sight redesign 6·thesis 2·trading_bot 2·mp 1·기타 2=.superpowers·worktree forensic) | mgmt(소형) | 착수가능 | 🆕 등재 |
| MGMT-WT-SWEEP | mgmt worktree 6종 tip **전수 측정 → 머지 완료분 제거 후보 보고**(제거는 사용자 수동). **STEP 0 실측(2026-07-13, base origin/main `3b50612`)**: 6종 **전부 ahead=0 = origin/main 완전 머지 = 전량 제거 후보** — sess-mgmt-flush `cf82fe9`·sess-mgmt-flush3 `b8b15cb`·sess-mgmt-ledger `cdbf79e`·sess-mgmt-ledger-s3 `3062bb0`·sess-mgmt-xapp-rule `079f233`·sess-mgmt-v2 `f892d90`. 제거 절차 = `git worktree remove <path>` + `git branch -d monorepo/<b>`(조상 검증 통과 시). **본 세션은 등재·측정만**(실 제거는 사용자 판단·수동, 활성 사용 여부 최종 확인 후) | mgmt(정리) | 사용자 제거 승인 시 | 💤 등재(측정 완료·제거 대기) |
| NEWS-ORPHAN-ASSIGN | 뉴스 무소속 재료 트랙 배정 — NT-2b(미핸드오프)·NT-6(보류)·뉴스 β A(파킹). **결정은 디렉터 사이클**. ※**갱신(2026-07-09, D-DASH-BFF)**: D3(뉴스 축 소비 표면)의 거처 블로커는 **BFF 배치로 해제**(apps/dashboard가 read 소비만) → 잔존 사유는 **NT-2b 등 뉴스 품질 작업 소유 배정**뿐 | 결정 안건 | 디렉터 결정 사이클 | 🕓 대기(결정) |
| BOUNDARY-EXT-5 | shared 미경유 외부 API 직접 호출 **5건**(NEWS-SURVEY N2: chain_sight neo4j_loader×2·insider_tasks·sensitivity_tasks·market_pulse fmp_weights) 처분. **결정은 디렉터 사이클** | 결정 안건 | 디렉터 결정 사이클 | 🕓 대기(결정) |
| PROVIDER-DUAL | 뉴스 provider 3종(Finnhub·Marketaux·AlphaVantage) `services/news/providers` 잔류 vs shared 승격 결정. **결정은 디렉터 사이클** | 결정 안건 | 디렉터 결정 사이클 | 🕓 대기(결정) |

---

## News Axis Phase 1 (하이브리드 뉴스 축 / 2026-07-09)

> 근거 DECISIONS D-NEWS-AXIS(표면 S1×경로 D3)·D-DASH-BFF(apps/dashboard BFF)·소유권 지도 v2 AMEND(apps/dashboard/**). 홈 상단 압축 스트립 + 전용 응축 API. dashboard 트랙 소유.

| ID | Task | 분류 | 트리거 | Status |
|----|------|------|--------|--------|
| NEWSAXIS-CONTRACT | 응축 API **응답 계약 설계** — 관련성 정의·가중, 동일 사건 접기 기준, 관계망 배지 규칙, 캐싱 정책. **✅ 종결**(D-NEWSAXIS-CONTRACT 4항 등재: F2 관련성·자체 접기+제목핵심어 안전핀·RelationConfidence θ배지·15/30 캐싱 + item 계약) | 결정 안건(dashboard) | 완료 2026-07-09 | ✅ done |
| NEWSAXIS-BUILD | `apps/dashboard` BFF(Slice1) + FE 스트립 S1(Slice2). **✅ done `90b04fe`** — BFF θ배지·티어 F2·자체접기 + FE 홈 상단 스트립, scoped BE 12·FE 6·config 예외 2줄. **실가동 확인 07-10**(스트립 라이브: T2/T3/T4 칩·`AAPL↔GOOGL` 배지 발화·카드 LLM 채움 렌더). 후속=STRIP-FOLD-TUNE·URL-V1-ALIGN·STRIP-BADGE-VARIETY | @backend + dashboard FE | 완료 2026-07-10 | ✅ done |
| STRIP-FOLD-TUNE | 접기 안전핀 강화 3종(D-STRIP-FOLD-TUNE): 일반 금융어 stopword·라운드업 배제(언급 심볼 수 상한)·그룹 크기 상한. **AAPL "+10건" 오접합 fixture 박제 의무**. 임계 상수는 STEP 0 실데이터 결정(하드코딩 금지). **✅ done `62eec71`** — 실서빙 실효 채증(MGMT-BATCH-9): "+10건"(오접합)→"+2건"(=`MAX_GROUP_SIZE−1` 상한 준수), 전 칩 ≤+2건. 검증 = live DB×배포 코드 직접 실행(JWT 만료로 서비스-레벨 갈음, 렌더 미변경 등가). 잔여 "+2건" 정밀도는 도그푸딩 관찰 지속, 근본 해소=v2 LLM 클러스터링 예약(D-STRIP-FOLD-TUNE 추기) | @backend (apps/dashboard in-zone) | 완료 2026-07-10(land) | ✅ **done** |
| STRIP-BADGE-VARIETY | 칩별 관련 엣지 다양화 — 동일 `seed↔seed` 배지(AAPL↔GOOGL) 반복 완화(chip이 seed 심볼 언급 시 seed↔seed 최강 선택되는 편향). 외부 노드 연결 우선 등 개선 | dashboard 트랙(개선) | 다음 strip 접점 | 💤 등재(트리거 게이트) |
| URL-V1-ALIGN | BFF 경로 `/api/dashboard/` → `/api/v1/dashboard/` 관례 정렬 + FE stripService의 base 우회(`/api/v1` 제거 로직) 제거. ~~TUNE과 동승 가능~~(TUNE은 `62eec71`로 이미 land). **config 접촉 사전 정당화**: D-DASH-BFF config 예외 범위가 URL-V1-ALIGN 포함으로 확장됨(MGMT-BATCH-9) — root `urls` include 경로 1줄 수정은 내재 산출물로 허용, 그 외 config 변경은 HALT. 착수 시 diff 원문 채증 의무 | @backend + dashboard FE | 다음 apps/dashboard 접점 | 💤 등재(트리거 게이트) |
| HEALTH-13TH-IDENT | sv health 검사 항목 **12→13 증가분** 정체 확인·기록(monitor refresh 신선도 = MON-P2-BEAT 귀속 추정, 실측 확정) | mgmt(소형) | 착수가능 | 🆕 등재 |
| HEALTH-HASH-DISPLAY | **[관찰]** health #13 "실행 트리 정합" 라인의 표시 해시가 STEP 0 실측 HEAD와 불일치 관측 — 2026-08-11 RECON: STEP0 HEAD=`c916b32e`인데 health 라인은 `(f27bca5)` 표시(원인 추정=health_check 내부 fetch로 origin/main 세션중 전진, [[lesson_origin_main_advance_union_rebase]]/health 내부 fetch 계열). 판정 OK 정합은 유지되나 표시 해시 출처(HEAD vs 방금 fetch한 origin) 확인 필요. **재현 시 표시 로직(어느 rev를 print하는지) 점검**. ※ **HEALTH-13TH-IDENT(항목 수 12→13 식별)와는 별건** — 본 건은 개별 라인의 해시 표시값 정합. | mgmt(소형·관찰) | 재현 시 | 💤 관찰 |
| BRANCH-S1B1-DIVERGE | **[관찰]** WORKTREE-CLEANUP-8 집행 중 `sess-s1b1` worktree는 제거됐으나 로컬 브랜치 ref 잔존 — 로컬 tip `d919fb22` ≠ `origin/monorepo/sess-s1b1`(`4bd93c8e`)로 `git branch -d` 거부(자체 upstream 미머지). **origin/main 기준으로는 소진(안전)**이나 자체 추적 원격이 앞서 있어 `-d` 오탐. 분기 원인 미확인(원격에 로컬 미반영 커밋 존재 추정)·**방치 무해**(worktree 없는 브랜치 ref). 처분(`-D`)은 병진 수동(D-BRANCH-DELETE-MANUAL). ※ HEALTH-HASH-DISPLAY와 무관. **[갱신 BATCH-29 08-13]**: **로컬 브랜치 = CLEANUP-4~7 명령서 block 2' `-D` 삭제 완료**(cherry `origin/main..` +=0 손실0·디렉터 명령서 승인). **잔여 = 원격 `origin/monorepo/sess-s1b1`(`4bd93c8e`) 존치** — 원격 삭제(`git push origin --delete`)는 아웃바운드라 병진/명시 승인 몫(4bd93c8e=원 s1b1 커밋, b9e80655로 patch 흡수됨=내용 손실0). **[종결 BATCH-30 08-13]**: **원격 `git push origin --delete monorepo/sess-s1b1` 집행 완료**(디렉터 명령서·cherry `origin/main..origin/…`+=0 손실0 가드·사후 원격 부재 확인). **로컬 -D(BATCH-29) + 원격 --delete(08-13) = 완전 종결.** | 병진 수동(관찰) | 병진 재량 | ✅ **종결(로컬+원격 삭제)** |

---

## 완료 (최근)

| ID | Task | Agent | Completed | Notes |
|----|------|-------|-----------|-------|
| SESS-CONTRACT | 세션 충돌 방지 트랙 (소프트 강제 = worktree + 계약 헤더 선언) | orchestrator | 2026-06-01 | `docs/harness/SESSION_CONTRACT.md` 신규 + CLAUDE.md "Session Lifecycle" 참조 + STARTUP_CHECKLIST Step 0 추가. 시범 worktree `../stock_vis_mgmt` + `sess/mgmt` 생성. |
| SEC-ALL | SEC Pipeline 전체 (17 PR) | @backend + @rag-llm | 2026-04-04 | 📎 `docs/sec_pipeline/task_done/` |
| NI-v3 | News Intelligence v3 (6 Phase) | @backend + @infra | ~2026-03-20 | 607 tests |
| EOD-1 | EOD Dashboard (14 시그널 + 메인 페이지) | @backend + @frontend | ~2026-03-15 | JSON Baking |
| TC-1 | Thesis Control FE-PR-1 (라우팅+공통) | @frontend | ~2026-03-10 | 7개 라우트 + 5개 공통 컴포넌트 |
| TC-2 | Thesis Control FE-PR-2 (목록+변경+진입) | @frontend | ~2026-03-12 | ThesisListCard + TodayChangeCard |
| VAL-1 | 1차 검증 전체 (Peer+LLM필터) | @backend + @frontend | ~2026-03-05 | 6개 프리셋 + Compute-on-Read |

## NT-OPS-HCHECK-REDESIGN — health_check `origin/main-hash` 체크 재설계 [resolved 2026-07-02]
- 상태: **resolved** (D-OPS-HCHECK-B2). 해시 대조 → 시간기반(PROGRESS committer-ts, 임계 M=72h) 교체. 순수함수 `is_progress_stale` 분리 + 자기검증 2방향(`tests/test_health_check_freshness.py`) + 전체 health_check 10 OK.
- 원증상: fast-main(~20min land)+self-ref로 매 세션 blocking ERROR 오발 → resync land 게이트 HALT.
- ※ 병렬 브랜치 주의: `monorepo/sess-mgmt-v2`(미land, 0126af6)가 이 항목을 **open**으로도 추가함 → PHASE 2에서 v2 rebase·land 시 union-merge 중복 → **dedup 필요**(open 제거, 본 resolved 유지).

## NT-OPS-HCHECK-GATEINFO — health_check gate/info 2계층 분리 (C안, 후보)
- 내용: blocking gate(코드diff·경계·동결·arch guard) vs 비-blocking info(캐시 신선도)로 출력 모델 재구조화.
- 이유: 캐시성 체크가 늘면 개념적으로 가장 깨끗(PROGRESS=캐시 규약을 구조에 반영).
- γ규율: 지금은 소비자 미확정 → 짓지 않음. 트리거: 캐시성 blocking 후보 체크 ≥3 누적 시 결정 사이클.
## NT-P1-DELEGATE — Phase 1 발행 로그 + EOD-bake 추천 생산 → Dashboard 앱 위임
- 상태: ops 측정·설계·경계판정 완료. 빌드 실행은 Dashboard 프로젝트 소관(기능 코드).
- 스펙(단일 출처): HANDOFF_p1_recprod_spec.
- 확정: D-P1-GRAIN(wide 형제대칭, key=(stock,signal_date,signal_tag), horizon=컬럼, user_id nullable 예약, unique user 제외) · D-P1-CONF(B+ 발행값 캡처: confidence enum + composite_score float, 신규 생산 0).
- 부착: 모델=SignalAccuracy 형제 / bake=eod_json_baker _build_dashboard_json return / write=Stage6·baker 기존 표면(신규 표면 0) / serve=EODDashboardView 무변경 / Phase5 join 정합.
- open: #4 채점 모드(raw/excess, Phase 5) · user_id 스코프(멀티테넌트 시 unique 확장).
- 참고: D-P1-GRAIN·D-P1-CONF의 DECISIONS.md append는 Dashboard 빌드 커밋에 포함(원자적 land).

## OPS-LOG-FLOOD — celery-worker-error.log 폭주 (등재만, 2026-07-03)
- 상태: **등재만**(수리 안 함, 사용자 지시). 긴급도 낮음.
- 관찰: worker-error.log에 모든 INFO + `missed heartbeat`(고빈도) + 15분 regime 등 전량 적재 → 126MB, ~2,700줄/h.
- 영향: tail-window 로그 도구 오탐 유발(#28 verify E1의 근인). verify는 경계-timestamp 스캔으로 회피 완료 → 판정 정확도 무영향.
- 후속 트리거: 디스크 압박(수백 MB↑) 또는 타 tail-window 도구 오탐 재발 시. 방안 = 로그 레벨/분리/회전, heartbeat 억제.
- 상세: `docs/features/chain-sight/PR_ops_verify_enhancement.md`(등재 절).

## OPS-WORKTREE-ISOLATION — pair 작업 worktree 격리 (등재, 2026-07-04)
- 상태: 등재. **트리거 = pair→main 최종 통합 후** 착수(통합 전엔 pair가 공유 dir 점유 필요라 격리 시 워커 코드 갈림).
- 사건(근거): 2026-07-04 13:13:25 외부 세션이 공유 작업트리 `/Users/byeongjinjeong/Desktop/stock_vis`를 `git checkout origin/main`(detached 7c2f186)으로 탈취 → HEAD가 pair 이탈 + celery-worker 13:13:51 origin/main 코드로 재시작(aggregate 태스크 부재 = 다음 틱 unregistered 위험). 복구: pair(c690307) checkout + 워커 재기동(71696). pair/origin 무손상.
- 근본 원인: 다중 세션이 단일 작업트리(=celery 워커 코드베이스) 공유. 메모리 lesson "공유 main 작업트리 직접 편집 금지"의 구조적 미비(수동 규율만으론 동시 checkout 못 막음).
- **ADR 재평가 트리거(실증)**: DECISIONS:1338 "다중 세션 = **소프트 강제**(worktree 격리 + 계약 헤더, 훅 미도입 — 차선 이탈 반복 시 국소 승격)". 이번 사건(reflog `7c2f186 @2026-07-04 13:13:25 checkout origin/main`)이 소프트 강제가 못 막은 **첫 실증 이탈** → 통합 후 "국소 승격"(hook/worktree 물리격리) 재평가 대상.
- 07-05 후속: worker(71696) + **beat(36421→38604 재기동, 13:13:51 origin/main 재시작분 정정)** 양자 pair코드 정합. 밤사이 자율 틱 period 07-04 적립 = 복구 무인 검증.
- 방안: 활성 작업 브랜치를 `git worktree`로 분리(SESSION_CONTRACT worktree 규율 정합), 워커는 안정 브랜치 dir 고정 import.
- 통합 전 방어(잠정): 세션 시작 시 HEAD·워커 시작시각 대조 수동 스모크 + flag-on/merge 전 재확인(P-0 규율에 편입 검토).
- **2026-07-06 승격 = 대기열 선두**: 트리거("pair→main 통합 후") D2 v5.1 결정 ⑩로 충족 임박. 재발 2차 봉인 추가 — nightly `worker_sync.sh`가 sv-worker-runtime을 origin/main으로 리셋 → 기본 워커가 미머지 pair 태스크 미보유(unregistered) → 궤적 07-05 영구 갭. 遠因 = 본 트리거를 "통합 후"로 잡아 통합 전 재발을 못 막음. 착수는 D2 관찰 창과 겹치지 않게 사용자 호출(§7). 방안 = 워커 runtime을 안정 브랜치 고정 + 활성 트랙 worktree 물리격리 승격(DECISIONS:1338 소프트강제 재평가).
- **후속 메모 (theme-heat 계보, 2026-07-06)**: `monorepo/sess-cs-theme-heat`(TH-1)는 마이그레이션 체인 `0016→0015` 실존 의존으로 **pair HEAD에서 분기**됨. **pair→main 통합 완료 시 theme-heat 에 main 머지(또는 rebase)하여 계보 정리** — pair 전용 `0014·0015`가 main 에 오르면 계보 자연 해소.

## NT-REHOME-GRAPH — graph_analysis CUT [resolved 2026-07-03]
- 상태: **resolved** (D-REHOME-GRAPH). 휴면 상관관계 엔진(1444줄) 제거. STAGE 1=drop-migration 0002 prod 적용(5테이블 DROP, 0 rows) / STAGE 2=INSTALLED_APPS+코드 git rm.
- 검증: makemigrations --dry-run=No changes · check 0 · health 10 · arch 7 · 회귀 delta 0(선존 chainsight 5실패 무관). 복구 SHA f892d90.
- 후속(무해·선택): django_migrations 고아행 정리 · STAGE1 브랜치 삭제 · CLAUDE.md/sub_claude_md 서술 doc 위생.

## TH-SEEDHEAT-RECONCILE — 마켓 뷰 PR-1 선행 조율 의무 (등재, 2026-07-06)
- 상태: 등재(TH-1 종료조건 산출물). **트리거 = 마켓 뷰 PR-1(SeedHeatScore) 착수 시**.
- 의무(선행 강제): `docs/chain_sight/update_v2/task_instructions/cs_44_seed_node_heat_score.md`의 seed node heat 개념과 TH-1 `ThemeHeatScore`의 관계 정리 + `HeatEntity` 재사용 가능성 검토 → heat 개념이 두 벌 생기는 것을 차단(설계서 theme_heat_design.md v1.2 §11).

## TH-INSIDER-DATE-SANITY — 내부자 미래 거래일 위생 (등재+실행, 2026-07-07)
- 상태: **실행**(TH-2 재개 백필에 동승). 적재 단 `upsert_insider_records` 에 `transaction_date > 오늘` 컷 추가 + 기존 미래일 43행 정리(정리 전후 건수 보고).
- 근거: FMP 원천에 미래 거래일(2035·2028 등) 이상치 혼입. 90일 창은 자동 배제이나 적재 위생상 컷. 하한은 없음(원천 전체 이력 유지 = z-히스토리 자산, 설계서 §5.1 v1.2.1).

## ✅ TH-C5-SPDR-SEED — C5 섹터 SPDR 11행 원본 시드 (종결 원본분, 2026-07-09)
- 상태: **원본 시드 종결(TH-7c, 결정12a)**. migration 0018 = SPDR 11종 role=primary·active=True (프로브 11/11 통과). XLE·XLV 승격, 순수 테마 ETF 7행 active=False 불변. 테스트 갱신(18행·active split).
- 잔여 = 레버리지 짝 → **TH-C5-SPDR-LEVERAGED**(아래).

## ✅ TH-C5-SPDR-LEVERAGED — C5 레버리지 짝 시드 + 계산기 배선 (종결, 2026-07-09)
- 상태: **종결(TH-7d, 결정12b=A)**. 레버리지 9종 시드(0021, ERX 승격·XLB/XLC 결측 확정) + EtfDailyBar(0020) 거래량 3년 백필 15,120행 + c5_speculation_from_db + 조립기 _NOT_WIRED 에서 C5 제거. 14 test. 유동성 하한 $1M·배율 3x우선+2x대체 판정.
- 근거: 설계 §6.4 v1.2.4 확정 매핑표 + DECISIONS 2026-07-09 결정12b.

## ✅ TH-C4-COLDSTART — C4 산식 배선 + 콜드스타트 게이트 (종결, 2026-07-09)
- 상태: **종결(TH-8, 결정13=C)**. c4_etf_flow_from_db 게이트(diff<26 결측 / 26≤<60 확장 time_series_expanding / ≥60 정식 time_series, 상수 26/60=결정7 병기, 횡단 z 기각) + 조립기 편입. 14 test. **가동은 EtfSnapshot 축적 자동수렴**(예상 8월 중순, 재비준 지점 없음).
- 근거: DECISIONS 2026-07-09 결정13, 설계 §2 v1.2.5.

## ✅ TH-C6C7-BACKFILL — C6/C7 활성용 구성종목 DailyPrice 3년 백필 (종결, 2026-07-09)
- 상태: **종결(TH-9, 결정14=A)**. stocks `backfill_daily_prices` command(공유 정본 DailyPrice, 겹침 대조 게이트) → 364,827행/487종목(482종목 2023-07 3년 완비). C6/C7 게이트 자연 해제 검증(present 전환). 6 test.
- 근거: DECISIONS 2026-07-09 결정14, 커버리지 리포트.

## ✅ TH-BACKFILL-HALTED-8 — 겹침 정지 8종 정본 통일 (전건 종결, 2026-07-10)
- 상태: **전건 종결**. TH-11(결정18=A) 통과 5종(DD/HON/CRWD=split·GLW/ABBV=배당락) 교체 3,765행. **재정지 3종(MSFT/META/SPGI)은 TH-12b 결정20=A로 삭제+재백필 집행 → 잔여 소멸**(아래 TH-HALTED-3-PROBE 참조).

## ✅ TH-STOCK-REGISTER-6 — 미등록 6종 Stock 등록 (종결, 2026-07-10)
- 상태: **종결(TH-11)**. 6종 sync_overview 등록 + DailyPrice 백필 2,337행 → 커버리지 501/501 수렴. C1(QuarterlyValuation)은 ECHO·HONA 분기 이력 부족으로 499 유지(자연 해소).

## ✅ TH-C3-MATCH-EXPAND — C3 토큰 매칭 가동 (종결, 2026-07-10)
- 상태: **종결(TH-11, 결정17 1차 규칙)**. 토큰 완전 일치(단어=토큰·다단어=구 포함) → 재집계 0→218행 → 4테마 C3 점등(days≥26). ★미배정 57.2%>40% 트리거 초과 → TH-C3-LLM-DICT 상신.

## ✅ TH-C3-LLM-DICT — C3 LLM 큐레이션 정적 사전 (박제 종결, TH-13 2026-07-10, 결정19=A/결정21=C)
- 상태: **종결**. 검수표 671 → `ThemeKeywordH2` 원장 박제(provenance source=h2_v1·applied_at·confidence). migration 0023 + `seed_theme_keyword_h2` 커맨드(멱등). confidence 소문자 정규화(high 616/medium 54/low 1=671). none 251 = `h2_v1_none.json` 보존.
- 재집계·확대: `aggregate_theme_news_volume(use_h2=True)` — 배정률 81.3%(1452/1787, dry-run 정확 일치), Industrials 25→39, ThemeNewsVolume 218→300행, computed 4→5테마(Industrials 신규, 첫 온도 58 주의). 게이트 P1/P2/R1/R2/R3 전건 PASS. 신규 7 test.
- 오배정 재검은 **TH-H2-RECHECK로 이연**(결정21=C, 아래).

## ✅ TH-H2-RECHECK — H2 오배정 재검 + 기배정 재분류 (집행 종결, TH-14 2026-07-12, 결정22)
- 상태: **집행 종결(h2_v1 671)**. K1~K4 기준표 LLM 재검 → 유지 635/재배정 32/강등 4. provenance 선별 회수: 재배정 32 → source h2_v1→h2_v2(교정), 강등 4 → 행 삭제(none 파일 이동). 활성 = h2_v1 635 + h2_v2 32 = 667. 게이트 Q1(변경 36)·Q2(非h2 무접촉)·Q3(computed 5 유지, ★FinSvc 67→65)·Q4(배정률 80.4%) PASS. `load_h2_sector_map` 활성 전체 로드 갱신. 상신물 `h2_recheck_v1.json`.
- **기배정 733 재검은 목록 상신만**(무적용) → 아래 TH-FIRSTRULE-DEFECT.

## TH-FIRSTRULE-DEFECT — 1차 규칙 토큰 오매칭 수정 (등재 상신, TH-14 2026-07-12)
- 상태: **등재**(작업2 상신, `h2_firstrule_recheck.json`). 733 유니크 중 오배정 215(규칙결함 197/개별예외 18). ★"ai" 토큰 75건 최다(회사 종목 뉴스인데 무조건 Technology 배정 — JPMorgan AI→FinSvc·Jabil AI→Industrials·Meta AI→Comm) + macro 토큰(fed/inflation/crypto/geopolitical/regulation → none 대상).
- 수정 후보: KEYWORD_SECTOR_MAP "ai" 등 다의 토큰 제거/맥락화 or MATCH_EXCLUDE_TOKENS 확장. **1차 규칙 로직 변경은 별도 비준**(배정률·정밀도 영향 큼). 트리거 = 유지보수 슬라이스.

## ✅ TH-ESTIMATE-BEAT-ENABLE → TH-15 작업0 흡수 종결 (2026-07-13, 결정26=C)
- 상태: **종결**. TH-15 작업0에서 beat 3종 enabled=True(theme-heat-daily·collect-theme-filings·snapshot-analyst-estimates). snapshot-analyst-estimates 첫 발화 2026-07-17 16:30 ET(주간 금), C8 콜드스타트 60일 시계 개시. **결정26=C 상시 의무: 이후 모든 보고에 beat 3종 상태 1줄**.

## ✅ TH-C1-Z-PROBE — C1 z=7.5 원인 판정 (판정 종결, TH-16 2026-07-13, 읽기전용)
- 상태: **판정 종결**. C1 z = 섹터 EV/Sales 분기중앙값 시계열 z(횡단면 아님, 상한 미적용). FinSvc z=7.513 원인 = **(c) z_mode 라벨 오기 + (d) 이상치 오염**(최신 2026Q2 median=18.07이 n_syms=1=FDS 단독, history 73~75종목 median ~11.6). P5: cross_sectional_z는 C8 전용, C1/C2/C5/C6/C7 전부 timeseries_z인데 API가 cross_sectional 오라벨. 수정은 아래 2건 분리 등재(다음 슬라이스).

## ✅ TH-C1-THIN-QUARTER-GUARD — C1 얇은 분기 가드 (집행 종결, TH-16-RATIFY 2026-07-13, 결정28)
- 상태: **집행 종결**. `representative_series`(heat_components, ratio=0.60, floor=ceil(0.6×median n_syms)) + `c1_valuation_from_db` 배선. G3 재산출: **양방향 교정** — FinSvc 65→**55**(FDS 단독 상방 오염)·ConsCyc 44→**57**(하방 오염, 미예측)·Tech 58→56·Ind 57→56·Energy 58(무영향). 신규 5 test. 향후 daily beat 자동 반영.

## ✅ 결정29 — 전환일 driver 보류 (B 채택, 집행 종결, 2026-07-13)
- 상태: **집행 종결**. `heat_history_markers.HISTORY_MARKERS`(개정일 단일소스, 1건=07-12 c1_thin_quarter_guard) + `crossing_marker` + build_card 배선. delta 구간이 개정일 가로지르면 driver 보류(held=true, direction/basis/% 미표시), 온도·delta·신뢰·성분은 노출. 라이브: 07-12 5테마 전부 held, 07-13 daily beat부터 자동 재개. 신규 5 test.

## ✅ 결정30 — driver 보류 정밀화 지연 반영 (선택지3, 스펙 등재만, 2026-07-13)
- 상태: **스펙 등재**(코드 미적용). 현행 date 기반 전역 보류(결정29) 유지 — 오늘 가시적 손실 0(Energy delta=0 → driver=none, held/none 동일). 정밀화(marker.affected_themes로 보류 한정)는 **TH-HISTORY-MARKER DB 승격 슬라이스**에서 반영. 07-12 백필 = {FinSvc, ConsCyc, Tech, Industrials}(G3 실측 정합, Energy 제외).

## ✅ 프론트 v3 렌더 — 테마 온도계 카드+버튼바 (집행 종결, 2026-07-13, 결정28 #4)
- 상태: **집행 종결**. R0-b z_mode 불변식 잠금(`zmode_violations`, 재발 차단, 3 test). R1~R4: 타입·서비스(fetchThemeHeatBar/Card) + `ThemeHeatBar`(결정23B)·`ThemeHeatCard`(결정24C, 견인칩 결정29 held/결정27 방향 분기)·`themeHeatCopy`(z_mode 근거 문구) + `app/chainsight/theme-heat/` 페이지. R5: 컴포넌트 실렌더 6 vitest 통과(전환일 보류·정상일 방향·의미 레이어·버튼바·D-n·onSelect), tsc 0. 백엔드 433 GREEN.
- ⚠️ 라이브 브라우저 스크린샷 유예(07-13 스냅샷 미도래·dev 스택 미기동) — 컴포넌트 실 DOM 검증으로 계약 A/B 확인. affected_themes(결정30) 미반영=현행 date 기반 렌더.

## ✅ 결정31 — 전환일 delta 개정일 마커 C (집행 종결, 2026-07-13)
- 상태: **집행 종결(프론트 소패치, 백엔드 0)**. ThemeHeatCard delta 영역: driver.held 재사용 → 개정일엔 delta 원값 + 중립 마커 "개정일 재산출"(muted). 신규 2 vitest(총 8). 결정30 반영 시 자동 정밀화.
- ⏸ **R5 라이브 스크린샷 유예**: 본 브랜치 미배포(worker_sync 미실행=라이브에 라우트 부재) + beat 前(07-13 데이터 부재) → 배포 세션에서 촬영. 계약은 컴포넌트 실 DOM(vitest 8)으로 검증.

## 집행 순서 (결정28+29+30+31) — 프론트 렌더 게이트
- 1~2. [DONE] C1-Z-PROBE · THIN-QUARTER-GUARD · 결정29[DONE] · 결정30[등재] · 3. [DONE] ZMODE-LABEL-FIX · 4. [DONE] 프론트 v3 · 4b. [DONE] 결정31 delta 마커
- ⏸ R5 라이브 스크린샷(배포+07-13 데이터 후) · 5. [NEXT] TH-FIRSTRULE-DEFECT(별도 비준) · 후순위: C4(8월)·C8(7/17)·TH-DSS-IMPL(7/24)·TH-HISTORY-MARKER DB 승격(결정30)
- 프론트 게이트 = (A 프로브 ✅) AND (B 가드 ✅) AND (C 재산출 ✅) → **v3 렌더 개방**. FinSvc 재산출 값 55로만 노출. driver 파트는 hold_driver 분기(07-12 보류/07-13 재개).

## ✅ TH-ZMODE-LABEL-FIX — z_mode 라벨 정정 (집행 종결, 2026-07-13, 결정28 #3)
- 상태: **집행 종결**. L0 감사(heat_components): C1~C7 timeseries_z·C8 cross_sectional_z(유일 횡단면). L1: 단일소스 `heat_labels.COMPONENT_Z_METHOD` + build_card(저장 z_mode 우선, 없으면 맵). present 5성분(C1/C2/C5/C6/C7) cross_sectional→time_series 정정. 표시 전용(원장·z·온도 불변). 신규 2 test → 430 GREEN. 의미 레이어 계약: time_series="3년 자기 이력 대비", cross_sectional="동일 시점 동종 대비".
- **게이트: 표시 결함 c 종결 → 결정28 순서 #4(프론트 v3 렌더) 착수 가능.**

## TH-HISTORY-MARKER — heat 이력 방법론 변경 마커 (부분 착수, 결정29 자동연동, 우선순위 상향)
- 상태: **부분 착수**(결정29 초석). `heat_history_markers.py` 단일소스(현 1건 07-12)가 driver 보류 트리거원으로 가동 중. **잔여(정식화)**: DB 원장 승격 + admin 등록 + 프론트 이력 차트 개정일 마커 표시 + 사전 개정(h2_v1→h2_v2 07-12) 마커 추가 검토. 트리거원으로서 결정29와 자동 배선 완료.
- **★결정30 동시 반영(승격 시)**: 마커에 `affected_themes` 필드 추가 → hold 조건 `crossing AND theme∈affected_themes`로 정밀화(미기재=전역 하위호환). 07-12 마커 백필 = {FinSvc, ConsCyc, Tech, Industrials}. 검증: 07-12 재현 시 Energy held:false·나머지 4 held:true.

## TH-HEAT-C1-RETRO — 07-10 heat C1 얇은분기 가드 소급 정정 (등재, 쓰기 3b 2026-07-28)
- 상태: **등재**(별도 승인 대기). 쓰기 3b 경로(b)에서 07-10 무접촉 유지 결정 → 그 07-10 heat 행(FinSvc score=67, C1=7.51 등)이 **C1 얇은분기 가드(결정28, 07-12 도입) 이전 계산값 = 오염 잔존**. 재산출 시 FinSvc 07-10 67→55·CC 07-10 44→57 등 ±12~13 변동 예상(dry 실측).
- **미결 사안(본 세션 묵시 실행 금지 확인)**: 결정28 C1 가드의 07-10 **소급 여부**는 미결정. 소급 정정 = heat delta 불연속(07-10 자체가 방법론 개정 이전) → **TH-HISTORY-MARKER와 통합 검토**(07-10 이전 마커 or 07-10 행 재산출+마커).
- 트리거: 별도 승인. 착수 시 ths_pre 스냅샷 + 롤백(`restore_heat_snapshot`) 경로 재사용.

## TH-DSS-IMPL — DSS 점수화 구현 (🔵 구현 착수, DSS-IMPL-1 2026-08-16)
- 상태: **🔵 구현 착수**(DSS-IMPL-1, 브랜치 `monorepo/sess-dss-impl1`). 전제 충족(EstimateSnapshot 6회차·WoW 4쌍). 결정 5건 착지: D-DSS-AGG(1-B)·D-DSS-SIGNAL(2-A)·D-DSS-LAGPARAM(3-A)·D-DSS-FY-MATCH·D-DSS-ANALYST-FILTER.
- 선행 정찰 = DSS-RECON-1(`7b4775d2`). Slice 1(lag 파라미터화·회귀)→2(SymbolDemandSignal+migrate)→3(계산·적재)→4(백필·검산·Δ분포). A-매칭 성립(99.8%≥95%).
- **HONA no_data 관찰 종결(2026-08-14)**: 07-17~08-07 estimates no_data 지속하던 HONA가 08-14 회차부터 유입(2 FY행) — no_data 해소 확인(TH 관찰 게이트 중계분).

## ✅ DSS-FLAT-OBS — 08-14 near-flat 주간 관찰 (종결, DSS-FLAT-OBS-1 2026-08-24) [theme-heat][dss]
- 08-21(금) 7회차 발화 시 flat 비율 1수치 중계. 재차 ~99%면 FMP 컨센서스 갱신 주기 read-only 정찰 발부, 정상 분포 복귀 시 08-14를 저신호 주간으로 기록 종결. **게이트일 08-21.**
- **판정(2026-08-24, DSS-FLAT-OBS-1)**: 08-21 7회차 발화(EstimateSnapshot rows=1005·syms=503). anchor 08-21 적재(SymbolDemandSignal 502 + ThemeDemandScore 11, date-scoped invariant PASS·append-only). **flat_ratio: 08-14 = 498/500 = 99.60% → 08-21 = 35/467 = 7.49%** (<60% → [정상 복귀]). **08-14 = 저신호 주간(원인: FMP 해당 주 무갱신 추정·재발 없음) 기록 종결.** FMP 0회(§3 미발동). HONA @08-21 missing_prev 아님(dir=−1) 확인.

## TH-HISTORY-MARKER — heat 이력 방법론 변경 마커 (등재 백로그, TH-16 2026-07-13, 우선순위 하)
- 상태: **등재(백로그)**. 사전 개정일(h2_v1→h2_v2 등)·산식 개정 전후로 delta/history 구분 마커. 우선순위 하.

## ✅ TH-15 — Theme Heat API 슬라이스 (집행 종결, 2026-07-13, 결정23B/24C/25③/26C)
- 상태: **종결**. E1 `GET /api/v1/chainsight/theme-heat/`(버튼바 11종, computed score desc→accumulating days desc) + E2 `GET .../theme-heat/{theme}/`(카드: driver·confidence·components8·quadrant·history·z_mode·blocked). 읽기 전용(원장 조회, 재계산 없음). 성분 이름표 `heat_labels.py` 단일 소스(설계 §2 정본). IsAuthenticated.
- 게이트 A1~A5 PASS. 신규 13 test → 417 GREEN/13 사전존재. 파일: heat_labels·heat_api_service·heat_views + urls 2 route. driver 산식·band_display 매핑 = 설계 §2·DECISIONS 결정24.
- ★소비 차단 = blocked 구조(값+사유 동봉). universe_stale 현재 False(TH-6 신선), stale 픽스처 테스트로 검증. 프론트 트랙(버튼바·카드 렌더)은 별도.

## ✅ TH-HALTED-3-PROBE → 교체 집행 (종결, TH-12b 2026-07-10, 결정20=A)
- 상태: **교체 집행 종결**. TH-12 판정(기존 DB 7개월행 오염, FMP 정본) → TH-12b 삭제+재백필 집행. 삭제 522행(MSFT 196·META 174·SPGI 152) → 재백필 2,256행(각 752, 2023-07-11~2026-07-09, 기존 `backfill_daily_prices` 경로·우회 0).
- 게이트 전건 PASS: G1 전 기간 재대조 max_err 0.0·G2 앵커 3종 정본 일치(MSFT 541.55/META 751.44/SPGI 397.37)·G3 행수 미기록 0·G4 회귀 395G/13사전존재(C8 포함). **HALTED-3 해제**.

## TH-C1-FWDPE — C1 Fwd P/E 레그 배선 (등재, 2026-07-10)
- 상태: 등재(TH-10 승인). C1 현재 EV/Sales 단독 → Fwd P/E 레그 추가(§2 "EV/Sales·Fwd P/E 중앙값").
- 원료: forward EPS = analyst estimates(EstimateSnapshot 축적, C8 시간표 동조). 시점 정합 규칙 동일 적용.

## ✅ TH-C1-VALUATION — C1 밸류에이션 배선 (종결, 2026-07-09)
- 상태: **종결(TH-10, 결정15=A)**. EV/Sales = enterprise-values(period=quarter) ÷ income revenue, 동일 fiscal_date 정합. QuarterlyValuation(0022) 백필 7,935행/499종목 + c1_valuation_from_db 조립기 편입. C1 present. Fwd P/E 레그는 결정15 범위 밖(EV/Sales 단독). 13 test 일부.

## ✅ TH-C3-NARRATIVE — C3 내러티브 볼륨 배선 (종결, 2026-07-09)
- 상태: **종결(TH-10, 결정16=A)**. ThemeNewsVolume(0022) 원장 + aggregate 집계(완전 일치) + 결정13 동형 게이트 + 집계 beat(ET17:15) + 조립기 편입. ★완전 일치 실효성 0 → 매칭 확장은 TH-C3-MATCH-EXPAND(상신).

## TH-C8-ZMODE-BADGE — API 단계 카드 z_mode 뱃지 노출 검토 (등재, 2026-07-08)
- 상태: 등재. **트리거 = API/카드 슬라이스**. 근거 = DECISIONS 2026-07-08 결정7(종목별 z_mode 혼재).
- 의무: C8 z_mode 가 종목별 혼재(스냅샷 내 cross_sectional/time_series 공존)이므로, 2축 카드 evidence 에 **z_mode 뱃지**(예: "테마 간 상대"[cs] vs "자기 역사 대비"[ts]) 노출을 검토해 잣대 혼재를 사용자에게 투명화. cross_sectional 기간 evidence 템플릿 = 설계 §5.3-3 "테마 간 상대 +N위/σ".

## TH-UNIVERSE-DUAL-SOURCE — 주 1회 Wiki 교차검증 (등재, 2026-07-09)
- 상태: 등재. **트리거 = 소스 신뢰도 강화 필요 시**. 근거 = DECISIONS 2026-07-09 결정9.
- 의무: 단일 소스(Wikipedia) 위험 완화 — 2차 소스(예: 복구된 FMP 상위플랜, 또는 다른 정본)와 주 1회 교차검증하여 편출입 불일치 감지. 현재는 Wikipedia 단일(datahub 404 대체). 상위플랜 승격 시 FMP 로 승격 검토.

## ✅ TH-UNIVERSE-REFRESH-ALERT — 유니버스 갱신 소스 복구 + 실패 알림 (종결, 2026-07-09)
- 상태: **종결(TH-6)**. 소스 복구(Wikipedia, 결정9 B) + refresh/monitor task + beat 2종 등록 + 실갱신 완료(created 7·deactivated 7, staleness fresh). 근거 = DECISIONS 2026-07-07 결정5 → 2026-07-09 결정9.
- 발견: `sync-sp500-constituents` beat 는 살아 발화(enabled·last_run 2026-07-01·total 5)하나 소스 `datahub.io/.../constituents.csv` = **404** → `sync_constituents` 조기 반환(zero stats·`logger.error`만·**알림 없음**). 마지막 성공 동기화 2026-05-01(전 503행 updated_at 증거). = **(c) 조용한 무-op 사망**.
- 의무: ⑴ 소스 교체(신뢰 소스로 — FMP `/stable/` 구성종목 or 대체) ⑵ **동기화 실패/무-op 시 ops 알림**(zero stats·예외 → 알림, Bug #28 `check_last_tick_succeeded` 대상 등록) ⑶ 성공 시 updated_at 신선도 게이트. UniverseSnapshot 은 정적성 명시화 방어라 즉시 위험은 아니나, 유니버스가 5-01 에 영구 동결되면 신규 상장/편출 미반영.
- **stale 플래그 해제 절차 (TH-5 결정8 연동)**: 소스 복구로 `SP500Constituent.updated_at` 이 신선(30일 이내)해지면, `compute_theme_heat` 재산출 시 `is_universe_stale`=false → 저장 행 components 의 `universe_stale`=false 자연 해제(별도 백필 불요, 멱등 upsert 로 갱신). 소비층은 `universe_stale`=false 확인 후 실전 노출(결정6 게이트 해소). 과거 stale 행은 그대로 두거나(감사 이력) 재산출로 덮어씀.

## TH-HEATENTITY-SECTOR-RECONCILE — HeatEntity 섹터 택소노미 정렬 (등재, 2026-07-09)
- 상태: 등재. **트리거 = 성분 배선 확대 or 시드 정리 슬라이스**. 근거 = DECISIONS 2026-07-09.
- 발견: `HeatEntity.ref_id`(TH-1 시드 = Yahoo/FMP 계열 Technology·Healthcare·Basic Materials 등) ≠ `SP500Constituent.sector`(GICS Information Technology·Health Care·Materials 등), 6/11 명칭 불일치. 설계 §6.0 은 ref_id="GICS 섹터 키"라 시드가 스펙과도 불일치.
- 현재 처리: `heat_beat.HEAT_ENTITY_TO_SP500_SECTOR` 매핑으로 비파괴 해소(구성종목 정상 resolve, 실측 missing=7=C2만 present 확인).
- 의무: 매핑 영구화 vs 시드 GICS 재정렬(ThemeHeatScore 0행·ThemeEtfMap 은 재생성 가능이라 저위험) 중 택일. 재정렬 시 §6.0 "GICS" 정합 + 매핑 삭제.

## TH-UNIVERSE-DOTSYM ✅ (종결, 2026-08-08 최종 게이트 PASS — DOTSYM 옵션 1)
- 발견: SP500Constituent active **503** 중 점(.) 포함 **2종목**(클래스주 BRK.B·BF.B)이 `live_universe_symbols()`에서 제외(dot 배제 6개소 필터, Bug #23 402 회피) → universe **501**. EstimateSnapshot·heat 유니버스 상시 누락.
- 해결: **옵션 1**(DECISIONS D-DOTSYM, 2026-08-01) — 정본=dot 원형, hyphen 변환은 FMPClient 요청/응답 경계 단일 지점(`_make_request`)에 봉인. dot 배제 필터 6지점 전량 제거. 배포 origin/main `18d8c698`(worker_sync 3트리 repoint 완료).
- **최종 게이트 PASS(PROBE-EST-5TH, 2026-08-08, 5회차 snapshot_date=2026-08-07)**: symbols **503**·created 1003·errors 0 / **BRK.B·BF.B dot 원형 저장·하이픈 변형 부재(역변환 정상)** / 기존 종목 무손실(빠진 종목 0=추가만) / SFI-I1 신규 5메서드도 `_make_request` 경유 변환 자동 적용. 부수: no_data 1종=HONA(DOTSYM 무관, FMP estimates 미제공).
- 후속: C8 콜드스타트 대기(아래 TH-HEAT-C8-CONVERGENCE) / BRK.B·BF.B cs 편입(아래 신규).
## CS-EVIDENCE-SEC-COUNT — evidence_count_total SEC 텍스트 미집계 (백로그, 2026-07-22 ⑳-G)
- 상태: **백로그 등재만**(⑳-G OUT 범위 = 파이프라인 변경). ⑳-F 진단 근거.
- 관찰: SEC 10-K 관계(SUPPLIES_TO/COMPETES_WITH/DEPENDS_ON/PARTNER_WITH, 272행)는 `evidence_count_total=0`인데 `relation_basis_summary`에 실제 근거(공시 문장) 존재. 카운터가 co-mention/peer/price만 세고 SEC 텍스트 근거를 세지 않음 → "근거 0건" 오해.
- 잠정 완화(⑳-G): 카드가 공시 관계는 근거건수 미표기 + basis_summary를 근거로 노출(표시층).
- 근본 수정 후보: SEC 관계 생성 파이프라인에서 basis 문장 수/출처를 evidence_count_total·evidence_sources에 반영. 파이프라인 변경 = 별도 트랙.

## CS-RC-NORMALIZE — RC 연속 점수 정규화 (재정의, 2026-07-22 ⑳-G)
- 상태: **재정의**(구 "후순위" → "유형 통합 단일 랭킹이 필요할 때만 선행"). ⑳-G D-GRADE-HONEST-UI.
- 근거: truth_score는 tier 계단값(0/35/60/85), truth/market/SEC-grade가 이질 스케일. 유형 분리 UI(⑳-G)로 "무변별" 인식은 정규화 없이 해소됨 → 정규화는 유형 간 통합 랭킹 요구가 생길 때만 착수.
- 착수 조건: "공급/경쟁/Peer/시장을 하나의 0~100 신뢰도로 합쳐 정렬"하는 요구가 확정될 때. 그 전엔 불필요.

## SLICE-20B-F1 — 매수일 선택화 + 입력일부터 추적 폴백 (실행 세션, 2026-07-28) [portfolio][coach]
- 상태: **진행 중**. worktree `~/worktrees/sv-20bf1` @ `monorepo/sess-20bf1-buydate-fallback`, base origin/main `61abaf21`. 공유 DB 무접촉.
- 결정: DECISIONS `D-20BF1-BUYDATE-OPTIONAL`·`D-20BF1-FALLBACK-A`·`D-DEV-PROD-SHARED-DB`(2026-07-28 등재).
- 범위: ①first_bought_at null=False→null=True(마이그레이션 파일 생성) ②serializer required=False ③생성 뷰 A안 spot 캡처(미입력 한정, 가산) ④프론트 required 제거 + "입력일부터 KRW 추적" 안내 ⑤테스트(test DB).
- **병진 수동 후속(닫기 보고 첨부)**: ⓐ 실 DB migrate(런북 S1 준용·G1 확인 쿼리) ⓑ `sv sync`(재기동) ⓒ 라이브 캡처(미입력 flow) + s20b_demo 삭제·beat 등록 잔여분.

## DEV-PROD-SHARED-DB — dev=prod 물리 DB 공유 거버넌스 (항구 규약, 2026-07-24 발견) [ops][platform]
- 상태: **항구 규약 등재**(DECISIONS `D-DEV-PROD-SHARED-DB`). 조치 트랙 아님 — 모든 세션 준수 대상.
- 규약: dev migrate·shell 쓰기 = prod-write(자율 금지·병진 수동) / 캡처 데모는 생성 세션이 삭제·증명 / "정리 완료" = 검증 쿼리 동반.
- 근거: 2026-07-24 코치 런북 준비 중 dev 작업이 prod DB 반영 확인 + s20b_demo(goal 보유) 잔존 사례.

## GOAL-CREATE-UI — 사용자 목표 생성 UI (본 슬라이스로 종결, 2026-07-31) [portfolio][coach]
- 상태: **종결(20b-f2)**. 20b-f1에서 발견한 제품 갭(목표 생성 화면 부재 — knobs PATCH는 기존 UserGoal 요구, admin/shell만 생성) 해소. B안(전용 폼) = DECISIONS D-f2-0/1/2.
- 산출: POST `advisory/knobs/`(생성, 409 중복) + GoalForm 단일 컴포넌트 2모드(create/edit) + /advisory 목표 부재 온보딩 카드.

## RUN-TOTAL-PERSIST — run별 total_krw 미보존 (백로그, SIGNAL-FORWARD-INFRA 합류 후보, 2026-07-31) [portfolio][coach]
- 상태: **백로그 등재만**. F1 원장 판정(07-31)에서 발견.
- 관찰: 나이틀리 전/후 total_krw 시계열 비교 불가 — (1) PortfolioSnapshot이 동일 ET-date `update_or_create`라 이전 값 덮어씀(1 row/date), (2) AdvisoryRun.output에 total_krw 저장 필드 없음(`{}`).
- 함의: run 시점별 자산 추이·권유 근거 스냅을 사후 재구성 못 함. 판정은 count/run_at으로 우회했으나 값 비교엔 축 부재.
- 후속 후보: run별 total/gap 스냅 저장(AdvisoryRun 확장 또는 별도 원장). SIGNAL-FORWARD-INFRA 설계 사이클에 합류 검토(전방 신호 인프라와 원장 스키마 공통 설계).
- **STEP 0 #5 실측(SFI-I-3, 2026-08-06)**: AdvisoryRun.snapshot(FK PortfolioSnapshot)은 non-null·`holdings_detail=[{symbol,shares,price,fx_rate,value_krw}]`+`total_krw` 보유 → NAV 궤적은 **PortfolioSnapshot 시계열에서 근사 재구성 가능**(단 date-unique update_or_create라 run 시점 값은 여전히 미박제). ⑤ v0는 근사 NAV만 제공하고 "총액 박제 유보" 캐비앗 의무. 본결정(run별 total 영속화)은 표본 성장 후 사이클로 유보.
## SECB-REGRESSION-WATCH — 13건(attention6+leadership7) 재발 감시 (2026-07-31, F5) [testing][sec-beta]
- 트리거: `tests/chainsight/test_attention.py`·`test_leadership_api.py` 29건 중 **재실패 발생 시 즉시 HALT + full traceback 캡처**(직전 시대 결손 증거 = `--reuse-db` 오염 재현 자료). **라벨만 기록 금지**(D-SECB-MISLABEL 재발 방지).
- 근거: R1 결과 D — 재사용 테스트 DB 오염이 원인(D-SECB-MISLABEL). 재발 시 fresh DB(`--create-db`)로 격리 확인. cf. common-bugs #79.

## SECB-V-B-STANDBY — V-B 부분도입 트리거 대기 (2026-07-31, G1.6 §5) [sec-beta]
- 트리거: **잔여 순수 not_found율 >15% 재발 시**에만 재스코프. 범위 = **합성/재서술 클러스터**(G1.6 잔여 nf 유니크 19 ≈ G1.5 합성8+재서술5). **선제 도입 금지**(V-B=2콜, V-A 결정론 계약 위배).
- 현 상태: G1.6 재분류 후 잔여 명목 1.54%/유니크 2.03% ≤15% → **미발동**.

## SECB-PROMPT-V2 — tail 발산 방지 프롬프트 (2026-07-31, G1.6 §5) [sec-beta] ✅ **소비 완료 (G-e, 2026-08-03)**
- 범위: **Gate 2 존치**(이 세션 밖). 표적 = tail 발산 방지 문구(G1.5 부수② 초안, "verbatim exact sentence·리스트 절단 금지"). partial_match 410건이 verbatim tail 규율 대상.
- 근거: G1.6 §3 샘플 = 경쟁사 리스트 접두 verbatim + tail 회사명 발산(원문 실재, 조작 아님) → prompt v2로 verbatim 강제.
- **✅ G-e 측정 완료 (SECB-GE-EXEC-1, 2026-08-03)**: R1~R5 verbatim 규율(`SECB-GE-R1R5-SPEC.md`) 삽입 v2 프롬프트로 표본 5 filings 재추출·paired 측정. **tail율 71.07%→0.72%**(v1 121/86 → v2 139/1). DB 쓰기 0(물리 격리 b·`var/secb_ge_v2_sample/`). 결과 `docs/features/chain-sight/sec_beta_ge_v2_result.md`. ⚠️ caveat=v2 evidence 300자 상시 초과(R2>R3). **전량 롤아웃=별도 결정 사이클**(본 측정 세션 밖).

## SECB-GE-OBS-17ROW — v1 1768 vs marker 1751 — 17행 관찰 (2026-08-03, G-e STEP0) [sec-beta]
- 관찰: SupplyChainEvidence total **1768** / prompt_version='v1' **1768** / grounding_method='deterministic_v1' marker **1751** → **17행이 grounded 미표기**(백필 대상 밖·이후 신규 유입 추정). G-e paired 측정은 marker 1751 기준(무영향). 노출/재백필 필요성은 SECB-EXPOSURE·후속에서 판단(현 저우선·등재만).

## SECB-V2-ROLLOUT — v2 프롬프트 전량 적용 (2026-08-03 결정 → 🔵 실행 → ✅ **done 2026-08-13**) [sec-beta]
- **✅ 종결(2026-08-13)**: v2 프롬프트(캡 제거·verbatim) 전량 롤아웃 완료. **종결 실측**: filing 커버리지 **351/351**(결정론 accession_no ASC·stage1 100+stage2 251·중복0·누락0) · v2 **1718행/341 filings** · **전체 nf율 0.58%**(v1 잔여 2.03% 대비 개선)·verified **96.2%** · 길이정책 발현(캡 제거: p90 480·max 3096·>300 38.8%·2000초과 2행=sanity 경고만·무절단) · **v1 1751 완전 무접촉**(#79 전수: count·prompt_version 전부 v1·max 300 유지) · **V-B=STANDBY 미발동**(nf 0.58%≤15%). 비용 실측 ~$3.3/351콜(2단 체크포인트).
- **§3 경위(절단결함·복구)**: 1단 첫 실행이 안전게이트 통과했으나 길이 미발현(max300·143/497 "..."절단) → 근원=`validator evidence[:297]+"..."`(§0 grep `[:300]`만 봐 누락, D-SECB-V2-LEN=C 미구현) → 수정 `c9400d18`+오염 v2 497 삭제(v1 coexist 무손실)+1단 재실행(max970·verified 67.6%→94.8%) → 2단. common-bugs 2건(supersession 필터·절단 grep 전변형).
- **RESIDUAL-10**: v2 0행 filing **10건**(LLM 관계 0추출·경계성) = **v1 supersession 폴백(무손실)**. 결정 ⓐ 수용(재시도 안 함·저우선). accession: 0000804328-25-000085·0000320193-25-000079·0001193125-26-044769·0001543151-26-000015·0001628280-25-056698·0001037868-26-000016·0001193125-26-074129·0000920148-26-000111·0001674101-26-000008·0000016732-25-000112.
- **🔵 상태 전이(2026-08-10)**: **전제 4건 종결**(SECB-V2-RECON, read-only) → **실행 착수**(지시서 `SECB-V2-ROLLOUT-1`). ⑴ evidence_text=TextField 실존·fill 100%·마이그0 · ⑵ v1 길이=300캡(프롬프트 아티팩트·23% 검열)→**D-SECB-V2-LEN=C**(캡 제거·2000 sanity) · ⑶ bulk_create·unique 없음→**D-SECB-V2-COEXIST=B**(v1 보존·소비 v2 필터) · ⑷ 351 filings/1751행·≤$3.3·go(100건 체크포인트). 서열: 437=G1.5 종결·V-B=STANDBY(하류 조건부, 블로커 아님). 정찰 전문 `docs/features/secb/secb_v2_recon_report.md`.
- **성격**: G-e 표본 측정(tail 71.07%→0.72%)을 근거로 한 **전량 배포·substrate 통합**. 측정 세션이 pass/fail·배포를 하지 않음(D-SECB-GATE-E). ~~전제 4건 해소 전 착수 금지~~ (✅ 종결):
  - ⑴ **`evidence_text` DB 컬럼 실제 max_length 실측** — 300 초과 저장 시 절단/오류 거동 포함(현 모델은 TextField=무제한이나 실 DDL·다운스트림 `[:100]` basis 등 확인).
  - ⑵ **길이 정책 재설계** — R2(완전 문장) vs 300캡 우선순위 확정: 프롬프트를 고칠지(캡 상향/명문화) or 스키마를 고칠지(evidence 길이 정책).
  - ⑶ **인용 집합 변동 취급** — v2 재추출이 인용 수 변경(COR 28→46): 기존 v1 행 **대체**냐 v2 **병존**이냐 결정.
  - ⑷ **1751건 전량 재추출 비용 추정** — 표본 실측 $0.047/5 filings = **$0.0094/filing** 외삽 → deterministic_v1 = **351 distinct filings** × $0.0094 ≈ **$3.3**(LLM 351콜). **오차 명기**: 표본은 인용 풍부 filing(평균 24 cites)이라 substrate 평균(5.0 cites/filing)보다 출력 비용 상향 편향 = **과대추정 방향**(실제 ≤ $3.3 추정). 재시도·quota 미포함.
- 근거: G-e 결과 `docs/features/chain-sight/sec_beta_ge_v2_result.md` + caveat(300자 초과). cf. SECB-PROMPT-V2(소비 완료), D-SECB-GATE-E.
- **체크포인트 합격 기준 추가(2026-08-11, D-SECB-VB-ABSORB)**: 100건 체크포인트 합격 기준에 **"v2 유니크 not_found율 < v1 19.3%(184/952 계열) 대비 유의 개선"** 포함. 측정 = `prompt_version` 필터로 v1/v2 분리 집계. **개선 실패 시 → C(전용 V-B) 결정 사이클 재소집**(D-SECB-VB-ABSORB C 회귀 예약).

## SECB-VB-ABSORB 후속 트랙 (2026-08-11, D-SECB-VB-ABSORB) [sec-beta]
- **SECB-V2-NORMFIX** — grounding 대조기 **소문자 완화 1줄**(NORM-MISS 3건 구제, `services/sec_pipeline/grounding.py`). **V2 grounding 수정에 편승, 단독 세션 금지**(경량). 순위: V2 롤아웃 grounding 재배선 시. @backend
- **SECB-DUP-EXTRACT** — 중복 추출 결함 트랙(동일 (filing,문장) 최대 22회, not_found 중 254건 중복 계상). 조사 범위 = **추출 루프의 중복 생성 지점 + 기존 중복 레코드 정리 방침**(정리 = 파괴적 후보 → 병진 판정). 순위: **V2 체크포인트 이후**. @backend/@qa
- **SECB-VB-ABSORB-DIFF521** — 교집합 차집합 실측 결과 `|F_nb − F_v2| = 1 filing [521]`(PAYX, 미접지 v1 straggler·`grounding_method=NULL`). **✅ 확정 반영(디렉터 판정, MGMT-LEDGER-1 2026-08-19)**: straggler **5건 전체(513·515·519·521·522) V2 편입** — **V2 스코프 356 = 351 + `grounding_method IS NULL` 5**. V2 대상 쿼리에 `grounding_method IS NULL` 포함으로 갱신(자동결정 마진 1.40). **쿼리 갱신 구현은 V2 실행 세션 위임.** 부록 `sec_beta_vb_absorb_intersection.md` A-2.

## TH-TRIGGER-FIRED — TH Session 1 트리거 발화 (2026-08-03, SEC β 종결 선행 충족) [theme-heat] ✅ **소비 완료 (TH-SESSION-1, 2026-08-03)**
- **발화 조건 충족**: SEC β 트랙 종결 선언 확정(`sec_beta_closure_declaration.md`) → TH Session 1 선행 조건 해소.
- **~~Session 1 범위(원안)~~**: ~~Theme Heat corpus unfreeze + ThemeTermOverride 재산출(TNV) 백필 개시(대상 창 = 2026-07-12 → 현재, 50일+)~~ → **정정(TH-RECON-1 실측)**: corpus(DailyNewsKeyword)는 **동결된 적 없음**(08-03 최신). 실동결 = **TNV 집계**(ThemeNewsVolume, beat 부재→수동 의존, 07-25 정지). **정정 스코프 = TNV 집계 백필 07-26→08-03(9일·DB 집계·외부 API 0) + stale heat 재산출**(07-26→08-03 멱등 upsert). '07-12'는 override G2 스코프(≤07-11)의 오전이. cf. D-TH-TRIGGER-CORRECT.
- ⚠️ ThemeTermOverride 215(ovr_v1) **재적재 금지**(기존 override 트랙 계약) — 본 세션 무접촉(사전/사후 스냅샷 입증). override 재산출은 TH-OVR-RECUT(보류)로 분리.
- **결정 후보(등재만·미실행)**: TNV 집계 beat 승격(자동화) 여부 — 이 세션 등록 금지(#28 beat drift·stale dict가 DB 덮어씀, origin/main 정렬 런타임 트리에서만 등록). 별도 결정.

## TH-OVR-RECUT — 확장 corpus 기반 override 재판정 (보류, 2026-08-03) [theme-heat]
- **성격**: 확장된 corpus(07-12 이후분 포함)를 근거로 ThemeTermOverride(현 215 ovr_v1)를 **재판정**하는 별도 결정 사이클. **트리거 = 사전 품질 저하 관측 시**(현 미발동).
- **선행 설계**: G2 앵커(92/19/0/0, ≤07-11 스코프)의 **이관 설계 포함** — 재판정 시 앵커 무효화되므로 신 앵커 정의·비교 기준 재수립 필요. ovr_v2 generation 신설 여부 포함.
- 근거: TH-RESUME-CORPUS-UNFREEZE 조항(corpus 확장 시 G2 앵커 무효). 배제 결정(TH-SESSION-1 판정②, override 재산출 배제·TNV만).

## TH-SUNMON-REEXTRACT-1 — ✅ **종결 (G-sunmon GREEN, MGMT-LEDGER-1 2026-08-19)** [theme-heat][news]
- D-SUNMON-REEXTRACT(①A av-broad 완료 후 failed 재추출 체이닝) 구현·배포·백필 완료(08-10) → **첫 주말 08-16/17 실측 게이트 통과**. **G-sunmon GREEN**: corpus 문서 08-16(일) published_at **1,616** · 08-17(월) **1,610**(양일 >0) + TNV_CHAIN 라인 존재(celery-worker-error.log `date=2026-08-06 written=4` · sv-worker-runtime/stocks.log `date=2026-08-07 written=3`). 일요일 오진 재발 0. 정리 대상 worktree `sv-sunmon-recon`(병진 수동, D-BRANCH-DELETE-MANUAL).

## CORPUS-SUNMON-EMPTYKW — DailyNewsKeyword 일·월요일 빈 키워드 반복 (🔍 정찰 완료 2026-08-10 → 설계 결정 대기) [theme-heat][news]
- **관찰**: DailyNewsKeyword 행은 존재하나 `keywords=[]`(빈 추출)가 **일·월요일 반복** — TH-SESSION-1 백필 창서 07-26(Sun)·07-27(Mon)·08-02(Sun)·08-03(Mon) 확정. **토요일(08-01)은 정상**(3 테마 크레딧). → 해당일 TNV 0행, **당일(특히 월) heat가 뉴스 성분(C3) 0/저값으로 계산**되는 영향.
- **영향 범위**: heat C3=`c3_narrative_from_db`가 롤링 창 참조라 단일 공백일 영향은 완충되나, 일·월 연속 공백은 초반 뉴스 성분 저평가 가능. 6/11 not_computed 전환과는 무관(그 5테마는 C3 외 결측 ≥3).
- **🔍 정찰 결과(SUNMON-RECON, 2026-08-10, read-only)**: 근원 = **추출↔수집 타이밍 레이스**(일요일 공백 오진). 08-09 NewsArticle **1229건 존재**하나 `extract-daily-news-keywords`(매일 16:45 ET·localdate KST) 추출(08-08 20:45 UTC)이 기사 수집(08-10 01:01 UTC, av-broad)보다 ~28h 이르게 발화 → 창내 0 → `status=failed`. `collect-*` 수집 beat 대부분 **평일 전용(`* * 1-5`)** → 주말 창은 av-broad(01:00 UTC 일1회)로만 늦게 채워짐. **failed 행 재추출 트리거 부재** = 공백 고착. 전문 `docs/features/theme-heat/sunmon_recon_report.md`.
- **설계 결정 후보 (조치=다음 사이클)**: **A(주원인)** failed 행 재추출/백필 트리거(av-broad 수집 후 당일+전일 재추출) 또는 추출 스케줄을 수집 뒤로 이동 · **B** collect-* 평일전용→주말 수집 경로 보강 · **C** localdate KST 조기창 완화.

## SECB-EXPOSURE — grounding_status 노출 설계 결정 사이클 (2026-08-01, Gate2 개정 B-2) [sec-beta][ux]
- **성격**: 디렉터 세션·**목업 필수** 결정 사이클(소비자 UX 결정). **소비자 결정 전 구축 금지**(γ 사변 구축 금지, D-SECB-GATE2-AMEND-1).
- **미결 3**: ⑴ attach 지점(후보 `FilingDataView`/`filing/<symbol>/`·IsAdminUser, per-symbol=1-filing 자연 정합) ⑵ 스코핑(글로벌 `SEC_GROUNDING_ENABLED` flag + 1 filing 스모크 vs per-filing allowlist) ⑶ flag 정의 위치(settings) 포함.
- **입력 확보**: grounding 데이터 prod 기록 완료(G-c, 1751·4분포 1273/41/410/27·marker deterministic_v1). partial_match 121 filings/410 rows = 노출 시 신설 등급 표시 대상.
- 근거: G-d(flag-on 1 filing)가 노출 경로 부재로 Gate2 배치서 제거·이관. cf. common-bugs #82.
## F2-VISUAL-CHECK — 온보딩 카드 브라우저 육안 검증 1회 (등재, 2026-08-01)
- 상태: **등재·대기**(트리거 = 다음 라이브 기회에). read-only 육안 확인, 코드 변경 없음.
- 내용: f2 온보딩 카드가 :3000 라이브에서 의도대로 렌더되는지 브라우저 육안 1회 확인(스크린샷 증적). UI 슬라이스 마감 = 라이브 렌더 스크린샷 필수 규율([[feedback_ui_slice_live_screenshot]]) 소급 이행.
- 주의: :3000 web-runtime = prod 빌드 → f2 온보딩 카드 변경분이 라이브 반영됐는지 먼저 확인(미반영 시 rebuild 선행). 판정 = 육안 통과/미통과만, 수정은 별도 슬라이스.
- 출처: SIGNAL-FORWARD-INFRA 프리플라이트 지시서 Part A-3.

## FORWARD-PE-DEFER — forward_pe 유령필드 미러 I-1 제외 (2026-08-01, SFI-I1 Part A-7) [portfolio][coach]
- 상태: **defer(I-2/I-3로 이월)**. I-1 범위 제외 확정.
- 근거: `Stock.forward_pe` 미러 = price ÷ **forward EPS** 의존. forward EPS = analyst-estimates 소관인데 B2 확정으로 SFI는 estimates 무접촉(chain_sight.EstimateSnapshot 단일 정본, D-I1-4). → I-1의 유령필드 미러는 `analyst_target_price + analyst_rating_*×5`만, forward_pe 제외.
- 후속: I-2/I-3에서 chain_sight estimates 정본(eps_avg)을 재사용해 forward_pe 산출·미러(이중 수집 없이). 소비 사이클 소관.

## SFI-I1-BUGNUM — common-bugs 채번 후보 3건 (✅ done, BATCH-20 부여 2026-08-01) [harness]
- 규칙: D-NUMBERING-MGMT-ONLY(채번=mgmt 전용, build 세션은 채번 후보만). SFI-I1이 자가채번 #80/#81/#82 → origin/main 선점(MGMT-BATCH-18 `fa3e20de`)과 충돌 발견 → **채번 회수**(headings "채번 후보"로 정정).
- ✅ **BATCH-20 부여 완료**(push-직전 재grep, 실측+1 from #82):
  ⓐ get_rating `/stable/rating` 404 오경로 → ratings-snapshot = **#83** (backend/stocks)
  ⓑ analyst-estimates `period` 필수(누락=400, 6월 audit http-400 오진) = **#84** (backend/stocks)
  ⓒ RECON-STALE-BASE — 측정 세션 stale base false-missing → fresh origin/main + base HEAD 명기 = **#85** (process/harness/git)
- 부수: SFI-I1 채번 회수의 botched orphan(`get_rating (#80,...)` 본문 없는 중복 헤딩)도 BATCH-20이 제거(bare #80=0 복원).

## I2-NEWS-BADGE-DEFER — 뉴스/chain_sight 애널리스트 슬롯 배선 이월 (2026-08-05, SFI-I-2 Part A) [portfolio][news][chainsight]
- 상태: **defer**. I-2 범위 제외(종목 화면 패널만).
- 내용: `components/news/MarketDataBadge.tsx`의 `AnalystRatingsSection`(market_data.analyst_ratings)·chain_sight `CompanyNarrativeTag.analyst_consensus/target_vs_price/revision_trend` 유령 슬롯을 AnalystSignalSnapshot으로 배선.
- 트리거: I-2 패널 안정화 후. 뉴스 insight market_data 계약·chain_sight narrative 생성 경로 접점 설계 필요(별개 소비처).

## I3-OWN-TIMESERIES — 자체 스냅샷 축적 추세 차트 (2026-08-05, SFI-I-2 Part A) [portfolio]
- 상태: **defer**(데이터 성숙 후). I-2는 FMP 제공 grades_historical(12개월) 사용(D-I2-2).
- 내용: nightly AnalystSignalSnapshot append 축적분으로 우리 자체 시계열 추세(목표가 변화·의견 이동) 구성. 자동발화 표본 충분(수십일+) 시 착수.
- 접점: I-2 조회 API(D-I2-1 공용 설계)를 시계열 조회로 확장(latest 1건 → 기간 N건).

## I2-TREND-YAXIS — 애널리스트 추세 미니차트 y축 눈금/범위 라벨 (2026-08-06, SFI-I-2 Part A) [portfolio][frontend]
- 상태: **backlog**(소액 UX). I-2 `AnalystConsensusPanel` 의견 추세 미니차트.
- 현상: y축 눈금·범위 라벨 부재 → 평평한 추세선이 정보로 읽히지 않음(척도 없는 선).
- 내용: grades_historical(월별) 미니차트에 y축 min/max 또는 눈금 라벨 추가 — 값 대비 변화가 판독되게. 산식·데이터 무변경, 표현만.
- 접점: `AnalystConsensusPanel`(commit 8c5b72bd, SFI-I-2 Part 2).

## I3-PROMOTION-TRIGGER — 신호→기대수익 승격 결정 사이클 소집 기준 (2026-08-06, SFI-I-3 Part A) [portfolio][coach]
- 상태: **감시(자동 해제 아님)**. advisory_engine.py:10-11 금지벽 유지(D-I3-3).
- 기준: **Tier 1 h=63거래일 방향 적중 표본 ≥60 이고 (이항검정 p<0.05 상방 또는 IC 평균 양수 유의)** → 승격 결정 사이클 소집. 도달해도 자동 승격 금지 — 사람 판정으로 벽 해제 여부 결정.
- 근거: 현 표본 미성숙(대부분 만기 미도달). 통계 유의 없이 신호를 기대수익 프록시로 쓰면 STEP0_SIGNAL_INVENTORY의 유령/후행 반복.

## I3-MATERIALIZE-TRIGGER — 채점 원장 물성화(ScoredPrediction) 승격 (2026-08-06, SFI-I-3 Part A) [portfolio]
- 상태: **예약**. 현재 채점 = 파생 계산 계층(D-I3-1, 신규 테이블 없음).
- 트리거: **채점 로직 v2 분기** 또는 **코치 런타임이 채점 결과 참조 개시** 중 선도래 시 → ScoredPrediction append 원장으로 승격.
- 근거: 조기 스키마 고정 위험 회피. 재계산 가능(순수 함수·as_of 재현)하므로 물성화 이득이 참조·버전분기 전엔 없음.

## I2-SUMMARY-LOG-SINK — analyst signals 태스크 SUMMARY 영속 로그 싱크 (2026-08-06, SFI-I-3 Part A) [portfolio][infra][observability]
- 상태: **backlog**(소액, 관측성). 현재 `ingest_analyst_signals` SUMMARY는 `logger.info`뿐 → stocks.log에 미포착(Celery stdout/로테이션), 발화 증거는 DB append 행에만 의존.
- 내용: 발화별 SUMMARY(captured/skipped/failed/universe·as_of)를 영속 싱크(전용 로그 파일 또는 경량 실행이력 행)에 기록 → 발화 관측을 DB 행 카운트 외 독립 증거로 확보.
- 근거: SFI-I-2 종결 검증에서 SUMMARY 로그 원문 부재 확인(DB 행으로 우회).

## I3-SPOT-DAY-CONVENTION — pinned spot 기준일(T vs T−1) 실측·문서화 (2026-08-06, SFI-I-3 Part A) [portfolio][stocks]
- 상태: **✅ 종결(2026-08-07, SPOT-CONV 슬라이스)**. 실측 완료(08-06 발화 9행=6×T·3×T−1) → 원인=발화 18:30 ET가 비S&P500 monitor freshness 적재(18:45 ET) 앞. **수리=beat 18:30→19:30 ET 이동(D-I3-4)** + 혼합 코호트 epoch 태깅(D-I3-5). writer 값 로직 무변경.
- 잔여: 첫 19:30 ET 발화 후 미니 recon(9행 spot 전건 T 일치)이 종결 확인 조건.

## I3-SPLIT-GUARD — 지평 내 액면분할·기업행위 감지 시 unscoreable (2026-08-06, SFI-I-3 Part A) [stocks][portfolio]
- 상태: **✅ 완전 종결 (2026-08-19, 첫 발화 recon GREEN)** — 구현·배포·발화 검증 3단계 완료. [구현 2026-08-13 D-SPLIT-1 B안]: StockSplit(shared.stocks 마이그 0014)+`FMPClient.get_stock_splits`+`ingest_stock_splits`(apps.portfolio)+`sync_stock_splits_beat`+resolve_realized `unscoreable:corporate_action`+재현헤더 additive 2필드. 게이트 회귀 746+신규 11·경계가드·health 15/0/0·산식 IDENTICAL. [배포 2026-08-18 HALT ② 승인 A·B·C]: worker_sync(3트리→`bc2cb7e4`)+재기동→`ingest_stock_splits` registered→beat `portfolio-stock-splits-daily`(enabled·19:45 ET·dow1-5). migrate 0015 no-op merge(0014×2 리프) 동시 적용. **[발화 recon 2026-08-19 GREEN]**: 08-18 첫 발화 `{symbols:9,fetched:15,created:15,skipped:0,errors:{}}`(errors 0)→**StockSplit 15행**(NVDA 6·AAPL 5·TSLA 2·GOOGL 2·나머지 5종 0, date 1987~2024 전건 2026 前=채점 지평 밖·source 전건 fmp)·멱등 재실행 created 0/skipped 15. **발화시각 catch-up 종결**: 첫 발화 20:46 ET(등록 직후 1회 지연)→**2회차 08-19=23:45 UTC=19:45 ET 정시**(BEAT-TZ-OFFSET 불요). 09-01 h21 시한 前 완결.
- 내용(구현 확정): 예측~만기 구간(`capture_date < split.date ≤ realized_date`) 분할 존재 시 `unscoreable:corporate_action`. 감지원 = FMP `/stable/splits` 전용 StockSplit 모델(휴리스틱 아님, D-SPLIT-1).
- 근거: raw close(비조정)는 분할을 series_break gap으로 못 잡음(날짜 홀 무발생) → 전용 감지원 필수. 현 9종 채점 지평 내 분할 0(NVDA/TSLA/GOOGL/AAPL 최근 분할 전부 2026 스냅샷 前). adjClose 도입은 별개 트랙.

## SPLIT-CALENDAR-PREVIEW — 예정 분할 선반영 검토 (등재, 2026-08-13) [stocks][portfolio]
- 내용: FMP `/stable/splits-calendar`(사전 예고, preflight A3 가용 확인)로 **예정 분할을 사후가 아닌 사전에** unscoreable 선반영할지 검토. 현 I3-SPLIT-GUARD는 발효(사후) 분할만 감지 — 예정 분할이 만기 구간에 걸리는 예측을 미리 표시하면 채점 대기 중 사용자 오해 감소.
- 트리거: I3-SPLIT-GUARD 첫 발화 후 예정 분할 실사례 발생 시. 유니버스 9종은 현재 예정 창(2026-08~10) 0건.
- 상태: **EVT 흡수(2026-08-24)** — 예정 분할 = `CalendarEvent(event_type=SPLIT)`로 EVT 트랙이 제공(설계 앵커 `docs/design/event_calendar_design.md` §1·§2). I3-SPLIT-GUARD 소비 계약은 본 원장이 공급, 발효(사후) 분할 기존 경로(StockSplit ← portfolio task) 불변.

## BRANCH-REF-SWEEP — 로컬 브랜치 ref 소진 분류·정리 (등재, 2026-08-13) [harness][ops]
- 내용: 로컬 브랜치 ref **~155개**(대부분 worktree 없는 과거 nightly/세션 ref). `cleanup_worktrees_20260812.sh` 패턴 재사용해 **worktree 없는 소진 브랜치 전용** 정리 스크립트 생성(생성만·집행 병진 수동, D-BRANCH-DELETE-MANUAL). origin/main `merge-base --is-ancestor` 소진 재검증 후 `-d`(거부 시 skip), 활성/미소진 제외.
- 상태: 💤 등재(저우선). 방치 무해(dangling ref)이나 census 위생용.

## CS-REDESIGN-BACKLOG — Chain Sight 재설계 D1/D2 후속 백로그 (등재, 2026-08-10)
출처: D2-LEDGER-PROBE 지시서 Part 1-D. 결정 근거 = [[DECISIONS]] D1·D2. 채번 미부여(백로그).
- **CS-EXP-2 유니버스 확장 2차** — ~~트리거: 8-K 가동 후 미해소 타깃 빈도 N주 실측~~ → **재정의(D-CS-P3 후, 2026-08-13)**: 확장 1차(72티커 편입·SCE.current() 미해소 1759→1435) 후 잔여 미해소 **1,435행** 기준. 트리거 = ⑴ 잔여 미해소를 exact/alias 재대조 시 US상장&유니버스밖 신규 티커가 빈도≥2로 재축적, 또는 ⑵ 8-K beat(P28K-BEAT) 가동 후 미해소 상대 신규 유입. **1차는 exact/alias만이라 잔여 1,435 대부분=해외/비상장/일반명사(구조적 미해소)** → 2차는 신규 유입분 위주. (D2 Phase 4)
- ~~**CS-P3-EXISTING-CIK-BACKFILL 기존 683 CIK 백필**~~ → **✅ CS-P4 완료**: company_tickers.json 매핑 **668 백필**(.update()·FMP 무콜), cik 채움 72→**740/755**. **잔여 15**(AEP·BK·CTRA·DAY·FI·GEVG·HOLX·IPG·IREG·K·MMC·NUVL·OKLL·SATS·WBA=티커개명/특수) → **CS-P4-CIK-RESIDUAL**(FMP 15콜 예산 회부·후속).
- **CS-P3-V2-MATCH-GAP v2 재추출 매칭·시딩 갭** — 08월 v2 재추출(1735행)이 evidence 적재만·매칭→seed 미실행 관찰(D-CS-P3 재해소서 257행 소급). v2 추출 파이프라인에 매칭→seed 체이닝 편입 검토. (신규, 관찰→결정)
- ~~**SCE-POLLUTION-CLEANUP fuzzy-era SCE 오매칭 정제**~~ → **✅ 완료(2026-08-19, D-SCE-POLLUTION-CLEANUP)**: STEP0 전수쿼리로 evidence self-loop **모집단 13**(R-2 휴리스틱은 2만 포착). 집행 = ⑴오 alias Marvell→DIS 2행 하드삭제 ⑵정상 alias 시드→SCE3451 재해소→`FTNT→MRVL` evidence 회수·`FTNT→DIS` excluded ⑶self-loop 13행 excluded(→evidence self-loop 0) ⑷가드=이미 완비(`SelfLoopError`+3경로+test) ⑸추가1 `backfill_serving_layer` 가드 이중화(self-loop→excluded·기존excluded 보존)+pytest3. excluded 14·pytest 7 GREEN. **잔여**: ⑴37 NULL-target v1 SCE 정리(선택·저우선) ⑵self-loop DB CheckConstraint 승격(마이그 동반·SELFLOOP-DBCONSTRAINT).
- **SELFLOOP-DBCONSTRAINT self-loop DB 제약 승격** — 현행 앱 레벨 `SelfLoopError`(save() create 차단)를 DB `CheckConstraint(symbol_a≠symbol_b)`로 승격(마이그 동반). 레거시 13행 excluded 완료라 신규 제약 적용 안전. (신규·CS-P4 A-1 후속)
- **CS-UNIVERSE-EXCLUDE-FLAG 유니버스 제외 2단 승격**(하이브리드 ③ 2단·**R2-PRE-A 후속**) — 1단 착지=`apps/chain_sight/constants.py UNIVERSE_EXCLUDED_INDUSTRIES` industry 필터(`0f07b83e`류, 레버리지 ETF 3종). **2단 = `Stock` 제외 플래그(BooleanField)+사유코드(예: `LEVERAGED_ETF`) 신설** → 카드 유니버스 쿼리가 industry 문자열 대신 플래그 참조로 전환. **SELFLOOP-DBCONSTRAINT 마이그 번들에 편승**(별도 마이그 회피). **DoD**: ⑴Stock 플래그+사유코드 마이그(additive) ⑵3종 플래그 세팅(비파괴·병진 prod-write) ⑶카드 유니버스 쿼리 플래그 참조로 전환 ⑷**1단 필터 상수(`UNIVERSE_EXCLUDED_INDUSTRIES`)+참조 전부 제거** ⑸회귀 0. (신규·병진 마이그 대기)
- **CS-P5-FE-CARD 후속 고도화** — ⑴~~카드 필터·정렬~~ **✅ R1 Phase C**(연결수/그룹수 정렬·연결 유/무 필터·`mindmapConfig`) ⑵ 테마 슬롯 로직(**VOCAB-TAU 선행 대기**·잔여) ⑶ 카드 시각 고도화(잔여) ⑷ 접근성·가상화(잔여). ⑸~~sector 한글화~~ **✅ R1 C-3**(`constants/categoryMap.ts` 13). ⑹~~신규 연결 배지~~ **✅ R1 C-2**(new_conn_7d·recent_new_connections_7d).
- ~~**CS-INDUSTRY-HANGUL-REVIEW industry 137 한글 매핑 검수**(R1 C-3 후속)~~ → **✅ 완료(2026-08-27, R2-PRE-B Phase B, `f8ba6eed`)**: 사용자 승인 부록 A 137건 → `categoryMap.ts INDUSTRY_LABELS` 채움 + `MindmapTreeBoard` `getLabelForIndustry` 배선(sector 선례 동일 패턴·표시만 한글·정렬키 영문). 미매핑 영문 fallback. tsc0·vitest 1138 GREEN. **FE 빌드+재시작=병진**(Rule A·prod web-runtime).
- **CS-INDUSTRY-NORMALIZE 중복 industry 라벨 정규화**(R2-PRE-B Phase A) — 대문자/일반 변형 5행 → 정규 FMP 표기 UPDATE(TSLA `AUTO MANUFACTURERS`→`Auto - Manufacturers`·IREN `CAPITAL MARKETS`→`Financial - Capital Markets`·AAPL `CONSUMER ELECTRONICS`→`Consumer Electronics`·NVDA `SEMICONDUCTORS`→`Semiconductors`·TLN `UTILITIES - INDEPENDENT POWER PRODUCERS`→`Independent Power Producers`). distinct 137→132·반도체 26+1→27. **1차 = ✅ 실행 완료(2026-08-28, 사용자 명시 위임 "실행해줘")**: 5행 트랜잭션 커밋·검증(distinct 132·반도체 27·Stock 757 불변). 마이그0(데이터 UPDATE만)·서빙 반영 api 재기동 병진. 스크립트 `scratchpad/phaseA_normalize_5rows.py`(되돌림 재료 보존). **2차 후보 CS-INDUSTRY-NORMALIZE-2**: `Technology`(2=MSFT·GOOGL)·`Chemicals`(1=DOW) 정규 매핑 확정 시 + **sector 대문자 위생**(이 8종 sector도 대문자 `TECHNOLOGY`/`CONSUMER CYCLICAL` 등·트리 canon_label이 표시 흡수하나 원본 오염 잔존·GICS-유형 소스 유래 유력). (2차 신규 대기)
- **✅ R2-S1 "이 종목의 이야기" 패널 승격**(2026-08-28, 엣지 직접 집계·A안) — BE `services/story_activity.py get_symbol_story_threads`(CoMentionEdge 90d+last / NewsEntity 7d bounded·top10+N) → MindmapCardView additive `story` 필드. FE MindmapCardDetail "같은 그룹"→"이 종목의 이야기"(활동 게이지·7일/주간평균·최신성·quiet=조용함·빈상태). 마이그0·pytest 708·vitest 1190·tsc0(회귀0). 라이브 MRNA 115ms(MRK 7d24/90d25)·NVDA 243ms·AAPL 47ms. 소스 결정=[[DECISIONS]] D-CS-STORY-SOURCE. **랜딩 후 api 재기동 병진**.
- **CS-STORY-ACTIVITY-CACHE S2 전역 활동 물질화 캐시**(R2-S2 선행 후속) — S1은 종목당 라이브(NVDA ~250ms 수용) but **S2 전역 뷰(전 종목 활동 랭킹)는 라이브 집계 불가** → 7일/90일 파트너 활동을 일일 물질화(CoMentionEdge 유사·마이그 번들). `get_symbol_story_threads` 서비스가 캐시 소스로 전환 가능하게 설계됨(재사용). (신규·R2-S2 착수 시)
- **R2-S2 이벤트 피드**(로드맵 R2 다음 슬라이스) — S1 집계 층(`story_activity`)을 "종목 무관 전역 뷰"로 재사용. **착수 준비**: 서비스 함수 분리 완료(A-3 충족)·전역 집계는 CS-STORY-ACTIVITY-CACHE 선행 필요. S3(이야기 명명)=별도 결정(EventGroup 명명 클러스터 후보). (신규·대기)
- **CS-COMENTION-SOURCE-DECISION R2 연료 소스 결정 사이클**(R1 Phase D 후속) — 조사 완료 `docs/news/CS-COMENTION-SOURCE-SURVEY.md`(AV broad multi 9,523 견인·Marketaux native但단일심볼붕괴·FMP 단일태깅·Polygon tickers[]+insights·Alpaca symbols[]). 디렉터 스코어카드로 소스 채택 결정(추천 미기재). (신규·결정 대기) — **★R2-PRE 재프레이밍(2026-08-26)**: "AV broad 동결" 전제 정정 → 동결은 **과거 구간(04-25~07-06)**·의도적 per-symbol 제거 후 07-06 broad 재개로 **이미 복원, 현재 활성 주력**(collect-av-broad-news last_run 08-26·CoMentionEdge 33,555·last 08-24). 따라서 결정 프레임 = **"대체(replacement)" 아닌 "증강(augmentation) 여부"**. Marketaux 403도 R2-PRE probe에서 재현 안 됨(HTTP 200·native 7엔티티 확증 → 일시적 엣지 차단이었음). 증강 후보=Marketaux(정규화 계층 선행)·Polygon(per-ticker sentiment 최상·계정 필요). Marketaux native 다중티커 실증 샘플=`docs/fe/mkx_multi_entity_sample_20260826.json`(1기사 7엔티티·match_score 비정규 8.99~62.79).
- ~~**CS-RESIDUAL-RC-POLLUTION-SWEEP 잔여 RC 오염 sweep**~~ → **✅ 완료(2026-08-20, R-2 한정쓰기)**: fuzzy-era 오매칭 pair 유래 선착지 RC evidence SEC4종 전수 실측 17후보 → **backing SCE 최대유사도 정밀화**로 clear-pollution **15행 비파괴 excluded**(ORCL↔INCY·ALGN 계열[Ablecom/Amkor/IBASE]·AVY↔PPL·DDOG↔SNDK·LII↔PCAR·WDAY→MU[Remote]·WST→ROP 등), **ambiguous 2행 보호**(`FTNT↔MU`=Micron 정당 백킹 sim100·v2 current 존재→보존). evidence 3343→3328·excluded 14→29. 신규 오염 클래스 0(HALT 없음). **R-2 사각 근본**=SCE `current()` 값만 대조하고 supersession 전 선착지 RC 잔존을 미대조(D-SCE-POLLUTION-CLEANUP 부기).
- ~~**CS-SECTOR-BACKFILL 미분류 154 sector 백필**~~ → **✅ 완료(2026-08-24, R1 Phase A)**: sector 154→**0**·**148 FMP** `get_company_profile`(shared 래퍼) + **6 SP500** GICS→FMP(sector만). mindmap sector_count 14→13(미분류 소멸). 잔여 no-industry 6(SP500 6·저우선). 콜 accounting=148.
- **CS-API-ALLOWANY-MULTIUSER 멀티유저 이음새 체크리스트**(CS-P5 B2) — 신설 GET 2종(`mindmap/tree/`·`mindmap/card/<sym>/`)은 **AllowAny**(현행 무인증 서빙 관례=ego/sector 등과 동일). 멀티유저/멀티테넌트 도입 시 점검: ⑴ 유니버스·관계 데이터는 전역 공유(사용자별 격리 불요) 확인 ⑵ rate-limit·캐시 키에 사용자 스코프 불요 재확인 ⑶ 워치리스트 등 사용자별 리소스와 혼입 금지. 현재 전역 읽기 전용이라 무해, 인증 도입 시 재평가. (신규·이음새)
- **BEAT-DICT-RETIRE 레거시 beat dict 은퇴 검토**(CS-P4 추가C, Bug#28 위험) — `config/celery.py:141 app.conf.beat_schedule` dict populated(운영=DatabaseScheduler·DB 121건). dict는 DatabaseScheduler에서 무시되나 존재 자체가 drift 위험(Bug#28). **소거 금지·등재만** — 은퇴는 전 태스크 DB 등록 확인 후 별도. (신규)
- **CS-P4-NONCOMMON-FLAG1 비보통주 판정 대기**(CS-P4 추가B·**R1 B-3 플래그 기록**) — `asset_type` 플래그 기록 완료: **ETF 4**(SPY[벤치마크·정당]·OKLL·IREG·GEVG[레버리지·제외후보]) + **ADR 4**(ABBNY·CAJPY·DKILF·HKHC). **유니버스 제외=결정 사안 미실행**(OKLL/IREG/GEVG 레버리지 ETF 제외 유력·SPY 존치·ADR 모회사 리맵/은퇴). 판정=병진. — **★R2-PRE HALT 실측(2026-08-26)**: 심볼-유니버스 제외 메커니즘 **부재 확정**. 기존 "29 excluded"=`RelationConfidence.serving_layer='excluded'`(**관계층** 제외)로 심볼 카드 은닉 불가. 카드 유니버스(`mindmap_views.py MindmapTreeView`)=`Stock.objects` **757 전량 무필터** 노출. 3종은 RC 연결 0(제외할 관계 자체 없음). 실행하려면 ⑴Stock 쿼리 신규 필터(코드·전 표면 배선) 또는 ⑵Stock 신규 플래그+마이그(신규 메커니즘+prod 스키마 write=병진) 필요. **최소침습 권고=`industry='Asset Management - Leveraged'` 필터**(현재 정확히 3종·`asset_type=ETF`는 SPY까지 제거되어 부적합). 디렉터 결정 회부. — **★R2-PRE-A 1단 착지(2026-08-27, `0f07b83e`)**: 하이브리드 ③ 확정 → industry 필터 구현·랜딩(stock 757→754·업종버킷 소멸·card 404·702 GREEN). **2단 승격=CS-UNIVERSE-EXCLUDE-FLAG**(Stock 플래그·마이그 번들).
- ~~**CS-P4-MC-BACKFILL 신규72 market_cap 백필**~~ → **HALT·재정의(R1 B-1 선probe)**: FMP `/stable/profile`이 **marketCap=None** 반환(SNX·SAP 실증) → profile 경유 백필 무효 확정 → **CS-MC-BACKFILL-QUOTE**로 이관(`/stable/quote` 등 marketCap 제공 엔드포인트 필요·73 신규 대상·별도 승인).
- **CS-MC-RESIDUAL-8 기존 8종 market_cap 결측**(R1 0-4 이탈분) — 예측 72 밖 8종: `BF.B·BRK.B`(듀얼클래스·"." 티커) + `PAL·OKLL·SMR·IREG·XE·GEVG`(07-09 편입 소형/불명·일부 ETF). 사유=FMP marketCap 미제공 의심 + "." 티커 이슈. 조치=CS-MC-BACKFILL-QUOTE와 병합 검토. (신규·R1) — **★R2-PRE 스코프 재계산(2026-08-26)**: 8종 중 **3종(OKLL·IREG·GEVG=레버리지 ETF)은 유니버스 제외 결정 대기**(→ CS-P4-NONCOMMON-FLAG1·Phase A HALT). 제외 확정 시 market_cap 백필 불요 → **잔여 market_cap 스코프 = 5종(BF.B·BRK.B·PAL·SMR·XE)**. 나머지 5종은 CS-MC-BACKFILL-QUOTE 병합 유지.
- ~~**CS-P4-CIK-RESIDUAL 15**~~ → **부분 완료(R1 B-2)**: EDGAR company_tickers.json로 **5 매핑**(MMC·FI·AEP·BK·SATS). **잔여 10**→**CS-CIK-RESIDUAL-10**: 3 레버리지ETF(OKLL·IREG·GEVG=CIK 무·비보통주) + 7 기업(NUVL·DAY·HOLX·IPG·K·WBA·CTRA=현 company_tickers.json 10,403판 미수록) → SEC submissions API·full-text search로 후속(강제 매핑 금지·"없는 관계 있는 척 금지" 준수). (신규·R1 B-2)
- **CS-P4-BEAT-REGISTER ops 태스크 beat DB 등록**(병진 영역) — `sec-8k-daily`·`chainsight-sync-strength-weekly` DB-only 등록(복붙 블록 발행). dict 금지(Bug#28). 워커 재시작 병진. (신규·병진 실행 대기)
- **CS-8K-ITEM-EXPAND 8-K item 확대 검토** — 5.02(임원변동) 등, 최소 슬라이스(1.01/2.01) 가동 후. (D2 Phase 2 후속)
- **CS-STORE-DEDUP 관계 store 이중화 해소 검토** — RelationConfidence 13,701 vs serverless StockRelationship 225,073(HELD_BY_SAME_FUND 197k·SAME_REGULATION 26k). 서빙 소스 단일화 판단.
- **CS-LLMREL-TTL LLMExtractedRelation 30일 TTL 정책 재검토** — Phase 5 산출물 전량 소멸(현재 0행) 재발 방지.
- **CS-FE-MINDMAP FE 마인드맵 카드 화면 구축 페이즈** — D1 구조(업종 2단 주소 + 테마 슬롯 + 확인된연결/같은그룹 이원) 반영. 별도 결정·목업 후 착수.
- 기존 등재분 전건 유지. PROGRESS.md 캐시 갱신 = 본 세션 종료 의식.

## SESS-SIGNAL-FWD-RECON-RETIRE — 브랜치 은퇴 (등재만, 2026-08-10)
- 상태: **등재만**. 브랜치 삭제는 파괴적 → **병진 수동 영역**([[lesson_branch_d_upstream_refusal]] sess-l2-adopt 전례: -d 거부→HALT 주의).
- 사유: `monorepo/sess-signal-fwd-recon` 미push 백로그에 잔류물 — ⑴ 이미 origin/main 랜딩된 monitor/HOLD-P1 **중복 3건**(`4c920494`·`02cce323`·`710520e5` ↔ origin `6a093f16`·`63ed5a16`·`8ace1ed9`, mig 0008 origin 존재) ⑵ research_lab **타트랙**(`6973bda3`, sv-research-os 소관) ⑶ **superseded** governance(`0790c8f8` — D-LAND-ATOMIC·D-PROBE 내용 origin 기반영).
- 이 세션(D2-LEDGER-PROBE) 산출물 `59b9533b`(docs) + vocab_v1 `cc918c40`만 D-LAND-ATOMIC로 별도 랜딩. 잔여 커밋은 중복/타트랙이라 **미랜딩**(딸려보내기 금지).
- 트리거: 위 3부류 중복/랜딩 재확인 후 브랜치 은퇴. 삭제 전 `git merge-base --is-ancestor` 소진 검증.

## CS-P1A 후속 3건 (등재, 2026-08-10, CS-P1A-CLOSE)
- **CS-SAMEGROUP-REFRESH 같은 그룹 갱신 경로 재정의** — CS-P1A가 PEER_OF 착지 루프 제거(Neo4j 유일소스·그래프 동결) → "같은 그룹"(peer+ETF, D1) 관계의 **갱신 경로가 부재**. 기존 PEER_OF 9,365는 무접촉 보존되나 신규/갱신 미발생. Postgres-native 소스(FMP peer 재조달 or ETF 공동편입)로 갱신 경로 재설계 필요. 참조: [[DECISIONS]] D1·D-CS-P1A-RELANDING.
- **VOCAB-TAU-PIPELINE 구축** — Slice3 종목↔카테고리 τ 매칭이 코드·종목별 share 데이터 repo 부재로 미수행. vocab_v1(46카테고리) 배정 로직(D-NEWS-VOCAB Rev.3, τ=4.6% share 매칭)을 코드로 구현 + 종목별 테마 share 재계산. D1 하위결정 ②(슬롯 승격 기준) 재료.
- **NEO4J-QUEUE-WORKER-RETIRE 검토(병진 수동)** — neo4j 큐 전용 워커(`-Q neo4j --pool=solo`, PID 17일 구동)가 worker_sync 재기동 대상 밖. 그래프 동결 상태라 neo4j sync 태스크 비활성 → 은퇴 검토. 재기동/종료는 launchd 서비스 접촉(병진 수동).

## D1-SCOREBOARD 후속 (등재, 2026-08-20)
- **I3-DERIVED-RENDER** — `done`. 본 슬라이스(D1-SCOREBOARD)로 흡수 완결(BE compute-on-read API `761bda33` + FE 성적판 `0bbc089a`).
- 💤 **SCB-BOARD-PROMOTE** — 5-metric(Tier2 포함) 착수 시 성적판을 advisory 편입에서 전용 라우트로 승격 이사. 자립 컴포넌트(types/service/hook/components/scorecard) 그대로 이동. 트리거 = 5-metric 스코프 확정.
- 💤 **SCB-PRECOMPUTE-REEVAL** — 계산 비대(심볼/신호 급증·compute miss 지연 상승) 시 나안 TTL 캐시 → 다안(precompute 배치) 재평가. 현 실측 miss 285ms(139신호). 트리거 = miss 지연 임계 초과 or 심볼 대량 확장.
- 🕒 **SCB-CARD-REUSE** — SignalCard(증거 바 + 판정 문장)를 stock 상세의 AnalystConsensusPanel에 재사용하는 미니 슬라이스. 트리거 = 개별 종목 화면에서 성적 노출 요구 시.

## EVT 트랙 — 이벤트 캘린더 (등재 2026-08-24, 설계 앵커 `docs/design/event_calendar_design.md` v1.1)
- ✅ **EVT-IMPL-1** — 거버넌스 번들 + CalendarEvent 원장 토대 + FMP 래퍼 3종 + 캡 감지 유틸 (본 세션). 범위 밖(2호 이후)=수집 태스크·beat·연합 읽기·FE.
- 💤 **[EVT-P2] Phase 2 백로그** (상세=앵커 §7): P2-i 컨센서스 리비전×어닝 · P2-ii 어닝 반응 히스토리 · P2-iii 어닝콜 AI 요약 · P2-iv 주간 이벤트 브리핑 · P2-v 이벤트행 뉴스 밀도 배지. 진입 게이트 = **G-EVT-2 프로브**(read-only ~6콜: ①transcript ②M&A latest/search ③어닝 서프라이즈 이력 EP).
- 💤 **[EVT-CHAIN] Phase 2 관계망 이벤트 타임라인** (상세=앵커 §6): 시드+RelationConfidence 1-hop 이웃 이벤트, Postgres 단독 조인. v1 파라미터(truth_score≥85·confirmed·top-k10·EARNINGS만·부호중립) 확정=D-EVT-CHAIN-THRESH(실데이터 관찰 게이트). 원장 재작업 0(Phase 1 스키마 충족).
- 💤 **[OPS] FMP 영속 예산 원장 부재** — 현재 in-memory 카운터(`get_rate_limit_status`)뿐, DB 영속 원장 없음. 캘린더 수집 확대 시 일일 소비 추적 재료 부족 → 영속 예산 원장 신설 검토 (백로그).
- 💤 **[EVT-SESSION] earnings session(BMO/AMC) 원천 부재** — FMP 캘린더 응답에 세션·시각 필드 없음(EVT-IMPL-2 dry-run 실측: date/symbol/eps*/revenue*/lastUpdated만). v1은 `session=UNKNOWN` 표기. 보강 원천 후보: transcript dates·프레스릴리스(이연 표 §9 준용). 트리거 = 세션 표기 요구 발생.
- 🔭 **[EVT-OBS-1] collect-calendar-events 자동 발화 관찰 게이트** — beat 등록·enabled(DB PeriodicTask, 17:45 ET). **★신코드(보정2) 첫 발화 = 2026-08-29 17:45 ET → 검증 예정일 = 2026-08-30**. (실측 정정: 08-27·08-28 두 발화[runs 1→2]는 worker_sync 이전이라 **구코드**로 실행됨. 보정2 push+worker_sync는 08-29 착지 = `408cb20e`, worker 트리 c54c7cb3 조상 포함 확인. 디렉터 지시서의 "08-28=신코드 첫 발화"는 push 하루 슬립으로 부정확 → 08-29로 정정.) **증거 = last_run_at 아님, DB 행**: ⑴ 당일 last_seen_at 갱신 행 수(재관측 다수) ⑵ 신규 행 수(<1% 기대) ⑶ stale 전이 수 ⑷ bisect·견고화 텔레메트리(성분별 depth·extra_calls·nulled·skipped, 특히 earnings_fwd_1이 구코드처럼 부분 아닌 완전 적재되는지). **에스컬레이션**: bisect depth 4 도달 또는 콜 상한(12) 근접 → 상한/청크 재결정. **기준선**: 08-28 21:45 UTC 실측 = 13,687행(scheduled 12,498·occurred 1,159·stale 30).
- ✅ **EVT-IMPL-4** — 연합 읽기 서비스(4원천 병합·user 스코프 A3·surprise/trust/KST/D-day 파생·캐시15분) + API 2종(`GET /api/v1/monitor/calendar/`·`GET /api/dashboard/event-strip/`) + FE(캘린더 페이지·홈 EventStrip·6컴포넌트) (본 세션, 로컬 `monorepo/sess-evt-4`). BE `4b7186ab`+`2aa9f588`, FE 미커밋→통합커밋. 테스트 BE 27·FE 12. 안정임계 N=7. push 대기(D-PUSH-DELEG).
- ✅ **[EVT-OBS-1] 종결** — 6증거표 PASS(디렉터 처분 2026-08-31): PT runs=4·재관측 12,499·stale 스윕 동작·earnings_fwd 완전적재·ADTX NULL 유지. 신규율 1.16%=롤링 기대치(~1.1%) 부합. 신규율 기준 재정의=DECISIONS D-EVT-OBS-1(경고≥3%/HALT≥5%).
- 🌱 **[P1-iii 알림 이음새] Phase 1.5** — `event_feed.classify_trigger(item, prev)` 시그니처만 정의(발송 미구현). 전이 판정(occurred/stale/d_minus_n) 계약 = 구독 축(symbols[]·kinds[])과 정렬. 발송 로직은 Phase 1.5.
- 🔒 **[G-EVT-2] Phase 2 진입 게이트 유지** — EVT-CHAIN·노드 미니 위젯(D-EVT-FE1)은 Phase 2. read-only 프로브(~6콜) 선행.
- 📝 **[GUIDE monitor.calendar 슬라이스 2 후보]** — 가이드 스크린(앵커 `monitor.calendar` + 콘텐츠 3~7 region, `reviewStatus:'confirmed'` = 병진 검수) 신설. EVT-IMPL-4에서 3-2 오지시로 부여됐던 페이지 앵커는 제거됨(D-EVT-GUIDE-ANCHOR) → 이 슬라이스에서 앵커+콘텐츠 함께 랜딩.
- 🩹 **[EVT-CORR-3 보정3 후보] (0-5⑹, 보고 전용·디렉터 처분 대기)** — 재관측 시 status stale→scheduled **복원 없음**(`_persist_event`/`record_observation` 코드 확정, b). 계측(a): 재관측(last_seen≥08-29 21:45 UTC)했는데 stale=**47행 전량 future**(EARNINGS 41·DIV 6). 보정안(c) = 수집기 재관측 시 stale→scheduled 복원 + 47행 일괄 치유. **STEP 3 FE stale 기본숨김(off)의 최종 확정 = (a) 처분 후.**
- 📸 **[EVT-IMPL-4-SHOT] 라이브 렌더 잔여** — 조건: 병진 수동 런타임 동기(:3000 재빌드) 후 `/monitor/calendar` 2장(범위 기본·둘 다) + 홈 EventStrip 1장. 운영 config·재기동 조작 금지 유지. (이번 세션 blocker: :3000=prod빌드 신규FE 미포함, API=운영 daphne :18765, :3100 dev는 CORS 허용목록+인증세션=서비스 조작 필요.)

## RC-NEO4J-WORKER-TREE 전수 점검 파생 (등재, 2026-08-31 ops 세션)

> 상신 `scratchpad/RC-NEO4J-WORKER-TREE_상신_20260831.md` · 규칙 [[DECISIONS]] D-LAUNCHD-RUNTIME-TREE

- ✅ **RC-LAUNCHD-WATCHDOG-TREE** (@infra) — **done 2026-08-31 16:44**. plist 교체+bootstrap 완료, 실행 트리 = `sv-worker-runtime`, 첫 발화 `RECOVERED` 정상. 순서 규칙(neo4j 워커 running 확인 후 기동) 준수. ~~STEP 0 랜딩 @`9a17e324`~~(`scripts/celery-watchdog.sh` self-locate 적용). 잔여 = plist 교체·bootstrap(병진). `com.stockvis.celery-watchdog` plist 실행 트리 교정. Desktop 트리의 `.env`·Django `send_mail`을 구 코드로 실행 중. 초안 = `com.stockvis.celery-watchdog.plist.proposed` + self-locate diff. **집행 순서: neo4j 워커 교정·검증 합격 후에 올릴 것**(미교정 잡을 kickstart 방지). 의존 = RC-NEO4J-WORKER-TREE.
- ✅ **RC-LAUNCHD-PGBACKUP-TREE** — **done 2026-09-01(병진 위임·CC 집행)**. plist 교체+bootstrap 완료, `working directory`=`sv-worker-runtime`·스케줄 02:00 등록 확인·**launchd 12건 Desktop 지향 0건**. **health ❌0 복귀**(OPS-GUARD-S1의 "❌1 상수" 해소 → 랜딩 게이트 다시 "❌0" 사용 가능). 백업 `com.stockvis.pg-backup.plist.bak-20260901`. 수동 kickstart 미실행(금지 준수) → **잔여 = 익일 02:00 자연 발화 로그 확인**(`~/Library/Logs/stockvis/pg-backup.log`에 런타임 트리 경로·백업 산출 확인). → **D-LAUNCHD-RUNTIME-TREE 트랙 전건 종결**(결함 A·B·C 완료).
- 🟡 **RC-WATCHDOG-DAPHNE-COVERAGE** (@infra) — **구현·랜딩 완료 · 런타임 반영은 병진 판단 대기**. 상신 `scratchpad/RC-WATCHDOG-DAPHNE_상신_20260831.md`. `check_service "Web (daphne)" "daphne -p 18765" "com.stockvis.web"` 1건 추가(실행 라인 +1/-0, 기존 3종 **삭제 라인 0**). **재등록 불필요**(StartInterval 300 주기 잡 — 다음 발화부터 새 파일 실행). ⚠️ **반영 보류 권고**: `sv sync` 시 **커밋 16건 + 마이그레이션 4건 동반**, 그중 `chain_sight` **0034·0035가 prod 미적용** → MIG-BUNDLE-1 배포창에 편승할 것. ⚠️ **효과 한계**: web은 `KeepAlive=true`라 프로세스 사망은 이미 자동복구 — 이번 추가는 **잡 언로드 시 경보**가 실질이고(kickstart는 언로드 잡에 실패) hang은 감지 불가. 후속 후보 = `RC-WATCHDOG-HTTP-PROBE`(HTTP 헬스 프로브 + 언로드 감지) · `RC-WATCHDOG-MAINTENANCE-MUTE`(수동 정지 중 되살림 방지 — 현재 억제 장치 **없음**). ~~기존: 3종뿐, API 다운 시 자동복구 불가~~ 08-31 12:12 실사고(daphne 다운·수동 복구)와 직결. `check_service "Web (daphne)" "daphne -p 18765" "com.stockvis.web"` 추가 검토. 트리 교정과 함께 처리하면 1회 랜딩.
- ✅ **OPS-WORKER-SYNC-SHARED-SIGNALS** — **측정 완료·종결 2026-08-31(OPS-GUARD-S1, read-only·코드 변경 0)**. 판정 = **잔재 아님, 의도된 가드 대상**(`D-SHARED-SIGNALS-INTENT`). 베이커 `eod_json_baker.OUTPUT_DIR = settings.BASE_DIR/...`가 런타임 트리에 **원본 실디렉터리**를 만들고, `Desktop/stock_vis`·`sv-web-runtime`의 같은 경로는 **그 원본을 가리키는 심링크**(`dashboard.json` **inode 동일 160225849** 확증). `worker_sync.sh`의 `guard_symlink`는 심링크가 **아니면** ERROR+exit — 그 경로가 심링크여야 정상이라는 설계 의도. 조치 없음.
- ✅ **OPS-ENV-SYMLINK-DEPENDENCY** — **done 2026-08-31(OPS-GUARD-S1)**. 병진 결정 = **심링크 유지 + 점검**(독립 사본은 drift 위험 재도입이라 기각) = `D-ENV-SYMLINK-KEEP`. `health_check.py`에 `.env 심링크 실체`(`check_env_symlink`) 추가 — 심링크+대상 실재 OK / 일반 파일 WARN / 대상 소실·부재 **ERROR**. **값 미출력 계약**을 테스트로 박제. 현재 실측 = worker·api 2건 OK. 잔여 리스크(본체 `.env` 소실 시 3트리 동시 붕괴)는 ERROR 표면화로 수용.
- ✅ **OPS-HEALTHCHECK-PLIST-TREE** — **done 2026-08-31(OPS-GUARD-S1)**. `health_check.py`에 `launchd 실행 트리 정합` 추가(`check_launchd_tree_alignment`, stdlib `plistlib` 경유·서브프로세스 0). 공유 편집 트리 지향 = **ERROR**, 허용 목록 밖 = WARN, `LaunchAgents` 부재 = OK-skip. 허용 목록 = `sv-{worker,api,web}-runtime`·`~/neo4j`·`~/stock-vis-nightly`·`~/.nvm`·시스템 경로(STEP 0 plist 12건 실측). **도입 즉시 `pg-backup` 1건 ERROR 포착 = 실효 증명**. 유닛 테스트 37건(3분기·오탐·손상 plist·prefix 유사명). ⚠️ **부작용**: pg-backup 교정 전까지 `health ❌1`이 상수 → 랜딩 게이트는 "❌0"이 아니라 "**신규 ❌ 없음**"으로 읽을 것.
- 🔁 **[EVT-N-REEVAL] 안정 임계 N 재평가 트리거** — 현재 N=7(§0-5⑵ p50, 단 count=7에 시드 백필 스파이크 9,964행). **순수 일간 발화 14회 누적(≈2026-09-13) 후** scheduled `date_observed_count` 실분포로 N 재산정(시드 흔적 배제). 재산정 시 event_feed.STABLE_N 갱신 + trust 라벨 임계 재확정.
- ✅ **[EVT stale 기본숨김 처분]** 디렉터 2026-08-31: FE stale 기본 숨김 **off 확정**(FMP 최신 응답 기준 = 미반환은 숨김이 정직). stale 복원 결함은 EVT-CORR-3(보정3)로 별도 처리. FE 지시서 기본값(off) = 최종값.

## RC-C-1 backbone 뷰 슬라이스 1 (2026-08-31)

> 처분 D-RC-C1-STORAGE=옵션 C(compute-on-read). worktree `sv-rc-c1`[`monorepo/sess-rc-c1`] base origin/main `1ccb6769`.

- ✅ **RC-C-1 슬라이스 1 완료** — BE(compute-on-read 어댑터 + `/api/v1/chainsight/backbone/`) `ec5e18ed` + FE(`/chainsight/backbone` 뷰) `3e7b15c3`. 테스트 BE 15(chainsight+arch 751 GREEN)·FE vitest 9·tsc0·lint순증0. 4-2 실측 582노드/2199엣지/174ms·뷰통합 HTTP200·미인증401. **push·migrate·beat 없음(옵션 C)** — push만 D-PUSH-DELEG 대기.
- 🌱 **[RC-C1-B] 궤적 discriminator append (후속 옵션, 트리거 대기)** — backbone **순위 변동 관측 수요** 발생 시 기존 SymbolCentrality에 `graph_scope`(all/active_moat)+`degree`+`score_version` 추가, unique=(symbol,as_of,scope). **forward-only·소급 백필 금지**. 옵션 C(compute-on-read)로는 궤적 부재 → 시계열 순위 변동 필요 시 승격.
- 📝 **[RC-C1-DOTTED] sub-θ 점선 엣지 (backlog, 2-1 계약 확장 필요)** — STEP 3-1 "그 외 상위 심볼 간 엣지 점선"은 현 `/backbone/`가 θ≥0.85만 반환(2-1 계약 진실)이라 미충족. FE dash 분기 로직은 **구현 완료**(BackboneGraph, score<θ→[4,4]), 데이터만 대기. 승격 시 API에 induced sub-θ 엣지 리스트 additive.
- 📝 **[RC-C1-GUIDE] chainsight.backbone 가이드 콘텐츠** — FE에 `data-guide="chainsight.backbone"` 루트 앵커만 부여(3-3). 콘텐츠(region 3~7·reviewStatus)는 GUIDE 트랙 슬라이스로 이관.
- 📸 **[RC-C1-SHOT] 라이브 브라우저 렌더 잔여** — 조건: route 미배포(push+web 리빌드) → 풀 dev 스택(worktree Django+Next)+인증 필요. 이번 세션 blocker와 동일(:3000=prod빌드 신규 미포함·:18765=운영 API 신규 route 없음). **뷰 통합 증거로 대체**(APIRequestFactory HTTP200·582/2199·미인증401·`scratchpad/rc_c1_view_integration.py`). 배포 후 `/chainsight/backbone` 2장(백본·엣지 선택).
- 🔬 **[RC-PAIR-DEDUP] 동방향 중복 pair 실측 (채번 후보·별건 트랙)** — RC-C-1 엣지 정합에서 발견: status∈CP·max>0 입력 2,365행이 무향 collapse 시 2,199 엣지로 −166(왕복 양방향 33 + **동방향 중복 111쌍**, pair당 2~5행 분포 {2:126,3:15,4:2,5:1}). **동방향 중복 111쌍**(같은 (a,b) 방향에 복수 행)이 주 관심. **프로브 항목**: ⑴ 발생 writer 경로(어느 파이프라인이 동일 방향쌍 중복 생성) ⑵ 유일성 제약 후보 (a,b,relation_type) 적합성 ⑶ pair_aggregation/evidence_count 부풀림(중복 행이 근거·점수 이중계상 여부). read-only 프로브 선행. **이번 머지에 수정 미포함**(관찰 등재).
- 🔴 **[MP2-DOGFOOD-RECONCILE] tests/dogfood/test_targets.py 2 RED (귀책=MP2-SUBPAGES)** — `test_every_screen_declares_anchors_and_is_confirmed`·`test_guide_targets_are_loaded_from_guide_data`가 `marketPulse.macro: draft`로 실패(review_status='draft'≠'confirmed'). **소유 트랙=MP2-SUBPAGES**(draft를 confirmed 승격 or dogfood allowlist 처리 — 소유 트랙 판단). 비고: **origin/main baseline RED**(RC-C-1 역머지 시점 `88f87a48` 이후 확인, HOTFIX-1 `c6a902bd` 후에도 잔존 여부 재검증 필요)·**RC-C-1 델타 무관**(`tests/dogfood/`·`frontend/lib/guide/`·`market-pulse-v2/` 경로 diff 0·`chainsight.backbone` guide_data 미등록 grep 0). RC-C-1 push는 디렉터 게이트 예외 승인으로 진행.
- ✅ **[EVT-CORR-3] 보정3 완료** — 재관측 시 stale→scheduled 복원(`d2bd219b`). 47행 오표시(EARNINGS 41·DIV 6)는 배포 후 수집기 재관측 시 자가치유. **배포=worker_sync(수집기 변경) 별도 병진 필요.**
- 📸 **[EVT-IMPL-4-SHOT] 사용자 캡처 경로로 이관** — 시각 스크린샷은 환경 BLOCKED(Claude-in-Chrome 확장 미연결·헤드리스 SIGKILL) → 사용자가 로그인 브라우저에서 `/monitor/calendar`(범위 기본·둘 다)+홈 EventStrip 캡처. 배포 라이브 확인 완료(daphne 401·:3000 200·인증 API 실데이터 정상).
- 🎛️ **[EVT-FE-TUNE-1 후보] 캘린더 거시 밀도** — 실데이터 캘린더 macro 94(9월 첫주 critical 클러스터: JOLTS·ISM·ADP·NFP…)로 조밀. 기본 유형 필터/접기·거시 중요도 기본 상향(critical만?)·"주요 거시만" 토글 등 밀도 완화 UX 검토(백로그).

## MIG-BUNDLE-1 종결 (2026-08-31, worktree sv-mig-bundle-1, main `78c6b641`)

> 스키마 번들 3건. 병진 관문 정제·migrate 완료·CC L-3 검증 GREEN. 상세 결정 = [[DECISIONS]] D-SELFLOOP-DBCONSTRAINT·D-CS-UNIVERSE-EXCLUDE-FLAG·D-CS-STORY-ACTIVITY-CACHE.

- ✅ **SELFLOOP-DBCONSTRAINT** (A) — a≠b CheckConstraint 3모델(chainsight 0034) + skip_self_loop 로그 가드 3지점 + normalize_self_loops 정제(RC13+RPS649+Neo4j16 제거, 병진 실행). 검증: 3테이블 IntegrityError.
- ✅ **CS-UNIVERSE-EXCLUDE-FLAG** (B) — Stock.universe_excluded(stocks 0017)+데이터 승격(0018·OKLL/IREG/GEVG) + mindmap_views 전환 + 상수 제거. 검증: 행위보존 754==754.
- ✅ **CS-STORY-ACTIVITY-CACHE** (C) — SymbolStoryActivity(chainsight 0035)+물질화 태스크·커맨드+캐시우선 서빙+전역조회. 검증: 31,978행/35.75초·전역조회 0.7ms·캐시 3.9ms vs 라이브 55ms.
- 🔴 **[MIG-BUNDLE-1 관문②]** 병진 잔여 — `register_chainsight_beats`(chainsight-materialize-story-activity ET 12:00 등록) + **worker 재시작**([[lesson_celery_task_registration]]).
- 🟢 **S2 착수 준비 완료** — 캐시·전역조회·(-activity_ratio) 인덱스 = R2-S2 전역 활동 뷰 소스 완비.
- ✅ **[EVT-4B] 완료** — CORR-4(거시 event_time UTC 해석·경계 보정) + FE-TUNE-1(T2 거시 접기·세션 빈칸·서프라이즈 200%). BE `da3a871c`+FE `31bf7791`(로컬 sess-evt-6). 0-3 UTC 게이트 PASS. **push 후 :3000 재빌드 필요(사용자 지시)** — 재빌드 전까지 화면 미반영.
- ✅ **[EVT-IMPL-4-SHOT] 완료** — 증적 = 2026-08-31 디렉터 채팅 첨부 5장·시각 계약 판정 통과.
- 📋 **[MP-MACRO-CAL-1] 별건 — market_pulse 소유** (초안 `docs/instructions/MP-MACRO-CAL-1.md`): 거시 수집기(`apps/market_pulse/tasks/macro.py`) 결함 3건 = ①시각 UTC 저장·help_text만 ET(EVT-CORR-4로 읽기 계층 우회) ②실제값 미백필(수집 창 today..+14일, 과거 이벤트 actual 갱신 안 됨 — 과거7일 거시 34건 전부 actual 빈값) ③중요도 인플레(High→critical 매핑, 97일 창 crit34/high60). **EVT 계약**: event_time 저장 **UTC 유지**+help_text 정정, event_id 해시 유지(변경 시 EVT-CORR-4 파손). 결정·집행은 market_pulse 트랙(제안 A~D는 그쪽 사이클). **EVT/ops는 소비자로서 결함 보고+계약만.**
- 🟡 **[SYNC-SV-WRAPPER-GAP] (비긴급·등재만, @infra)** — `worker_sync.sh` #47 가드 안내문이 권장하는 `sv sync`/`sv health` 래퍼가 **PATH·repo 어디에도 없음**(alias/function/스크립트 전무). 가드가 존재하지 않는 해결책을 안내 중 → 사용자가 stale 사본 재실행 루프에 빠질 수 있음. 대응: `sv` 래퍼 신설(최신 origin/main 사본 self-locate 후 worker_sync 실행) **또는** 안내문을 "origin/main 최신 사본 직접 실행(임시 worktree)"로 수정. 실측 우회법=origin/main detached 임시 worktree에서 `scripts/worker_sync.sh` 실행(MIG-BUNDLE-1 2026-08-31 적용).

## OPS-GUARD-S1 파생 (등재, 2026-08-31)

- 🔴 **OPS-HEALTHCHECK-NIGHTLY-WIRE** (@infra) — **점검을 추가했지만 야간 자동 실행이 되지 않고 있다.** `scripts/run_health_check_nightly.sh`의 `PROJECT_DIR` 기본값이 **`$HOME/stock-vis`(실재하지 않는 경로)**이고, `~/stock-vis-nightly/*.sh` 어디서도 이 wrapper를 **호출하지 않으며**, 최근 14일 `health_check.json` 산출물도 **0건**. → 재발해도 **익일 자동 탐지가 성립하지 않는다**(OPS-HEALTHCHECK-PLIST-TREE의 실효가 수동 실행에 의존). 조치 후보: ⑴ `PROJECT_DIR` 기본값을 런타임 트리로 교정 ⑵ `nightly` 잡(23:00) 또는 `runtime-check`(1h)에서 호출 배선 ⑶ 산출물 경로 확인. **이 티켓이 닫히기 전까지 새 점검 2건은 "사람이 돌려야 보이는" 상태**임을 명심.
- 🧹 **[EVT-FE-CLEANUP-CALFMT 후보]** — EVT-4B FE-TUNE-1에서 세션 빈칸·거시 미리보기 시각 포맷을 `EventRow`/`MacroFoldRow` 로컬 헬퍼로 구현(2-9 파일 범위 준수 위해 `lib/monitor/calendarFormat.ts` 무접촉). 로직 중복 = 후속 정리 시 `calendarFormat.ts`로 통합 검토(FE 백로그).

## OPS-GUARD-S1 부수 교정 (2026-09-01)

- ✅ **OPS-GUARD-S1-FALSEPOS** — `H-LAUNCHD-TREE` 오탐 13건 해소. pg-backup ERROR가 걷히자 가려져 있던 WARN이 드러남(`nightly` plist의 `$NVM_DIR/nvm.sh` 뒤 조각·한국어 주석 슬래시). 정규식에 **토큰 경계 요구** + 경로 끝 셸 구분자 트림. 회귀 테스트 3건 추가(유닛 40 passed). 교훈 = **ERROR가 WARN을 가린다** — 새 점검은 결함을 고친 뒤의 출력까지 확인해야 신뢰도를 안다.

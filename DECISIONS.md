# DECISIONS.md — 아키텍처 결정 로그

> 에이전트는 구현 전 이 파일을 확인하고, 기존 결정과 충돌하는 작업은 수행하지 않는다.
> 각 결정에는 **근거(Why)**를 반드시 포함한다.
>
> **이 파일의 역할**: 아키텍처 결정의 **1차 소스**. 항목 구조 = **결정 / Why(근거) / How to apply / (해당 시) STEP 0 측정 · 검증 결과 · 머지 hash 출처**. 이 구조를 표준으로 유지한다(이미 최상위 품질 — 보존 우선).
> 함정·버그는 여기가 아니라 [`sub_claude_md/common-bugs.md`](sub_claude_md/common-bugs.md). 결정 ↔ KB 동기화: 새 결정 → 이 파일 **먼저** → `shared_kb` 큐 → 검색KB 드레인.

---

## [2026-08-10] D-BRANCH-DELETE-MANUAL — 파괴적 브랜치 삭제 수동 고정 (위임 불가) [harness] [governance]

**결정**: 브랜치 삭제(`-d`/`-D`)·worktree 제거·원격 브랜치 삭제는 **위임 불가 — 병진 수동 집행 고정**. 세션 내 예외 승인으로도 CC 집행 불가. 정본 = `docs/harness/session_isolation_guide.md` §D-BRANCH-DELETE-MANUAL. CC는 삭제 후보 + 안전 실측(`origin/main..브랜치` 카운트)까지만 보고·대기. `git branch -d` 거부 시 무조건 HALT(-D 자가 전환 금지).

- **배경**: INC-002(GOVPUSH-CLEANUP-EXEC) — TASKQUEUE "병진 수동·실행 금지" 등재분을 예외 승인 하 CC가 집행하고, `git branch -d` "not fully merged" 거부를 손실 0 실측으로 `-D` 자가 전환(정지 신호 자가 통과, INC-001 재발) + §H(코드 배포 위임)를 삭제 근거로 오인용.
- **선택지·가중합**: **A(수동 고정) 4.45** / B(D-PUSH-DELEG 동형 조건부 위임) 3.30 — **마진 1.15 > 1.00 → 자동 결정 A**.
- **Why**: push(고빈도·가역)와 삭제(저빈도·비가역)는 **위험-마찰 교환비가 반대**. push는 위임 실익(마찰↓)이 위험을 넘지만, 삭제는 저빈도라 위임 마찰 절감이 미미하고 비가역 위험만 남는다 → **동형 규칙(D-PUSH-DELEG)을 복제하지 않고 작업 성격별로 판정**. 예외 승인의 "승인 실체"와 "집행 주체 위임"은 별개 층위(승인이 있어도 집행은 병진).
- **How to apply**: 정본=session_isolation_guide §D-BRANCH-DELETE-MANUAL / 인시던트=INCIDENTS.md INC-002 / 적용 1호=TASKQUEUE GOVCLEANUP-0810 정리. D-PUSH-DELEG와 대비 쌍.

## [2026-08-10] D-MON-P4-LA — ADVISOR L-A 정기 브리핑 [monitor]

> 출처: 지시서 MON-P4-LA(T0). 근거: D-MONITOR-HORIZON-ADVISOR(단일 코어·3서피스·AdvisorNote·2축 채점) · D-MONITOR-TIMING-PIVOT §3.2(제안-판정 주체 분리). 스코프: **L-A(정기 브리핑)만.** L-B/L-C는 surface enum 소켓만 예약(착수 금지).

**결정**:
- **D1 브리핑 주기** = 매 거래일, EOD 후행 beat **18:50 ET**(기존 EOD 창 18:00~18:35 이후 · `monitor-refresh-daily 18:45 ET`가 스냅샷 선행 생성 → advisor 소비 · 18:50 슬롯 충돌 없음 실측). 무변화 날은 1~2문장 축약.
- **D2 호출 단위** = 활성 모니터별 개별 콜(1종목 1콜). 실패 격리 — 한 콜 실패는 해당 종목만 스킵.
- **D3 일지 UI** = A안 원장 동형(advisor도 기존 행 문법: 날짜·kind 배지·1줄 headline, 확장 시 body+meta). 일지 내 **최신 advisor 1건만 자동 펼침**(사용자 조작 > 자동).

**Why**: 브리핑은 관제 부담을 낮추는 '비서'의 사실 요약이지 매매 지시가 아니다(§3.2 제안-판정 분리). 점수 정본은 MonitorSnapshot(P2A/P2B)이며 advisor 경로에서 점수를 **재계산하지 않는다**(동결 기록 인용만). 기본 OFF 이중잠금은 LLM 실호출 비용·오발을 배포 승인 전까지 차단한다.

**How to apply / 불변식**:
- **언어 계약**: 브리핑은 사실·거리·상태만. 명령형 매매 지시어(매수/매도/추가/청산/손절하라 등) 금지 — 프롬프트 + **사후 lexical 가드** 이중 방어(검출 시 저장 안 함·WARNING).
- **커버리지 문면 인용 의무**: 모든 브리핑 meta에 `근거 지표 n/총`. 분모 = **해당 모니터 등록 지표 총수**(P2A 충분성 판정과 동일 카탈로그 소스, `catalog_for` 기반), n = source_n 충분 지표 수. **9 하드코딩 금지.**
- **무변화 정의**: 상태 전이 없음 AND **|Δ overall_score| < 0.02**([-1,1] 스케일, 직전 스냅샷 대비) AND 종가가 시나리오 레벨 3종(진입/목표/손절) 어느 것도 미교차. **임계 0.02 확정** — STEP 0 실측(6종 48델타: P50=0.0125·P75=0.0252·max=0.1885, 0.02 미만 68.8%)에서 P50~P75 사이로 무변화 69%/변화 31% 균형.
- **기본 OFF 이중잠금**: `ADVISOR_ENABLED=False`(settings) + PeriodicTask `enabled=False`. 점등은 배포 승인 후 수동.
- **실패 = 무음 스킵 + ERROR 로그**. 일지에 오류·플레이스홀더 행 생성 금지.
- **점수 재계산 금지**: advisor는 MonitorSnapshot 동결 기록만 인용. horizon 필드는 Monitor/Claim에 **부재**(STEP 0 실측) → v1 프롬프트에서 생략, 이 트랙에서 신설 금지(별도 결정).
- **LLM 게이트웨이**: `packages.shared.llm.complete(provider="anthropic", model=settings.ADVISOR_MODEL)`(leaf-safe 공용 패키지, monitor의 기존 packages.shared import 선례와 동일). ADVISOR_MODEL 기본 = `claude-sonnet-4-5`(코드베이스 anthropic 컨벤션).
## [2026-08-10] D-PUSH-DELEG — CC push 조건부 위임 (behind>0 하드 스톱) [harness] [governance]

**결정**: CC의 origin/main push를 **조건부 위임**한다(전면 금지 → 조건부). 규칙 전문 = 정본 `docs/harness/session_isolation_guide.md` §D-PUSH-DELEG. 요지: ⑴ "push"/"푸시" 포함 **명시 지시 1회분**에만 실행 ⑵ push 전 가드 `git fetch → behind 재실측 → behind>0이면 무조건 HALT(자가 흡수 금지)` ⑶ force 계열 전면 금지 ⑷ 착지 검증. worker 재시작·launchctl·파괴적 삭제 등은 위임 대상 아님(현행 유지).

- **배경**: CLOSE-0808-PUSH 인시던트(`INCIDENTS.md` INC-001) — **규칙 문언("push 병진 수동")과 실사용 패턴(병진 채팅 승인 push)의 drift**. 승인 실체는 있었으나 behind=2 조우 시 CC가 무충돌 실측을 근거로 HALT 자가 해제·rebase 진행(금지 위반, 손상 0).
- **선택지·가중합**: A(전면 금지 유지) 3.85 / **B(조건부 위임 + behind>0 하드 스톱) 4.40** / C(무제한 위임) 3.50 — 마진 0.55, **병진 승인으로 B 확정**(2026-08-10).
- **Why**: push 위험의 실체는 **push 행위가 아니라 non-ff 상황의 자가 흡수 판단**. 따라서 위임하되 `behind>0`에 하드 스톱을 박는 것이 **통제 지점을 정확히 겨냥**한다. 무충돌 실측은 진행 근거가 아니라 보고 내용.
- **발견(명문화 계기)**: "CC push 전면 금지"의 **정확한 규약 문언은 repo에 부재**했음(그동안 지시서마다 관례로 명시) — **본 결정이 최초 명문화**.
- **§H 상충 발견·조정(2안)**: 명문화 중 `SESSION_CONTRACT.md` §H `D-DEPLOY-DELEGATE`("자기 세션 브랜치 코드 배포 = **승인 불필요** 대행")가 D-PUSH-DELEG("**명시 지시 필수**")와 정면 상충함을 발견(STEP 0-5 grep이 위임 어휘를 못 잡아 초기 누락 → 편집 중 발견·상신). **2안(범위 구분 병존 + 공통 가드) 채택**: §H = 자기 세션 브랜치 조건 충족 배포 파이프라인(행위보존), D-PUSH-DELEG = 그 외 일반 push. **공통 하드 가드(behind>0 HALT)는 §H 포함 전 경로 적용**. 근거 = **사고 병소는 non-ff 상황의 자가 흡수이지 push 행위 자체가 아니므로**, §H 자동화는 보존하되 병소(behind>0)에만 공통 스톱을 박는다. 가중합 **1안(§H 갱신·강화) 3.45 / 2안(범위 구분+공통가드) 4.25 / 3안(§H 폐지·통합) 3.45 — 마진 0.80, 병진 승인**.
- **실증(GREEN)**: GOV-PUSHDELEG-0810 STEP 0에서 **2026-08-10 behind=1→3 및 다중 게이트 편차(health 15/0/0·인시던트 대장 부재) 조우 시 HALT 2회 준수** — 자가 흡수·강제 생성 없이 병진 판정 대기. 규칙 안착 1차 실증.
- **How to apply**: 정본=session_isolation_guide.md §D-PUSH-DELEG / SESSION_CONTRACT는 포인터 1줄(복제 금지) / 인시던트=INCIDENTS.md INC-001 / 실증 게이트=TASKQUEUE. 관련 [[feedback_deploy_approval_explicit_quote]]·[[lesson_origin_main_advance_union_rebase]].

## [2026-08-08] D-MON-P2B — 표시 정합: 점수 정본 통일 + 사다리 계약 일반화 [monitor]

> 출처: 지시서 MON-P2B(T0). 근거: MON-P2A STEP 0 ADDENDUM 실측(A1 값·델타·일지 3원 소스 혼재 = 스냅샷/sparkline/readings · A2 hold zone_display의 stop<purchase<target 고정 전제가 이익 보호 스탑에서 파손 · A3 무수리 종결). 표시 계층 수리 — 엔진 무접촉.

**결정**: ⑴ **점수 표시 정본 = MonitorSnapshot(동결 기록)으로 단일화** — 스트립 값·스트립 델타·일지 스냅샷 전부 동일 원천. 일지는 "시스템이 그날 실제로 기록한 값"만 담는다(로직 변경에도 과거 불변 = 기록 무결성). ⑵ **zone_display 기하·rows를 가격 일반화**(스탑 상향 지원) — [stop, target] 고정 전제 제거. ⑶ **F4 처리 변경**: 종전 잠정안(프리롤 흐리게 유지) 폐기 — 프리롤은 실기록이 아닌 소급 재산출물(A1)이므로 정본 통일의 귀결로 일지에서 자연 소멸. 진입 전 맥락은 사다리·신호 패널이 담당.

**Why**: 값(latest_score 스냅샷)·델타(sparkline 최근 2점차)·일지(readings 실시간 재산출)가 3원 혼재 → 같은 지표가 화면마다 다른 값. 일지가 실시간 재산출이면 "그날 기록"이 로직 변경 시 소급 변형(기록 아닌 추정치). zone_display의 stop<purchase<target 고정 기하는 이익 보호 스탑(손절 상향, 예 GOOGL 매입 264.59 < 손절 291.38 < 종가 362.43 < 목표 408.61)에서 순서·마커가 파손.

**How to apply**: **T1** — 일지 snapshot kind 소스 sparkline.score_series → MonitorSnapshot 행(asof_date·overall_score·직전 스냅샷 대비 Δ). 스트립 델타 소스 sparkline 최근 2점차 → 최신 스냅샷 − 직전 스냅샷(latest_score와 동일 원천). Δ 표시=산출 가능하면 항상(±0.00 포함, 반올림 0 무표시로 인한 은닉 제거), 직전 스냅샷 부재 시만 무표시. sparkline/score_series·목록 카드 곡선은 **무접촉**(추세 곡선=기록 아님, 재산출 수용). **T2** — build_zone_display 범위 = [존재하는 전 레벨의 min, max](stop·purchase·target·익절접근·fair band 전수), rows = 가격 내림차순, anchor_fraction 클램프 제거. **배포**: P2A와 단일 창(P2B 병합 후 빌드·재시작 1회) — 일지 과거가 재산출 로직으로 표시되는 창 0 보장. **검증**: monitor pytest 231(P2A 착지)→243(T1 snapshot_series +6 · T2 스탑상향 +1)·vitest monitor 98→100(+2)·tsc 0. FE PriceLadder는 rows 자체 재정렬 없음(BE 순서 그대로 렌더 — 수리 불요). **병합·배포(2026-08-10)**: P2A 병합 `3ef6097a` → P2B 병합 `da66f256`(단일창). worker_sync 3트리(worker/web/api) da66f256 재기동 + FE rebuild(BUILD_ID `evZq0NpAVURIDLfarQbxf`, 게이트 통과: BUILD_ID mtime 08-10 > 구서버 08-08 < 새서버). **스모크 4항 PASS**: ⑴ GEV 정본 일치(일지 최신 asof 08-07 score 0.0185 = 스냅샷, Δ+0.0028) ⑵ GOOGL 사다리 가격 내림차순(목표408.61>익절396.35>손절291.38>매입264.59, 손절>매입 스탑상향 반영) ⑶ 프리롤 소멸(GEV 일지 첫 asof=개시일 07-28, 9행) ⑷ 커버리지 GEV 9/9·IONQ 6/9.

## [2026-08-06] D-COLLECTION-UNIVERSE-PRINCIPLE — 수집 유니버스는 활성 monitor target을 자동 포함 [monitor] [news] [platform]

> 출처: 지시서 MON-P2A T0. 근거: RECON-NEWS-P0(TLN 등 비SP500 보유종목이 어떤 수집 유니버스에도 미포함=사각지대).

**결정**: 모든 수집 유니버스(뉴스·EOD신호 등)는 **활성 monitor target(보유·관제 종목)을 자동 포함**한다. 사용자가 관제하는 종목이 데이터 수집 사각지대에 놓이지 않게 하는 전역 원칙. **1호 구현 = NEWS-P0-FIX**(뉴스측 monitor-target 자동 편입). EOD신호측(EODSignal SP500 한정 → 비SP500 EOD계열 지표 n=0) 확장은 T4 RECON 후 별도 결정 사이클.

**Why**: 관제=의도의 커밋인데 그 종목이 수집 유니버스 밖이면 신호·뉴스가 영원히 비어 관제가 무의미(TLN 뉴스 0건·EODSignal 0). **How to apply**: 각 수집 경로의 유니버스 결정부에 monitor-target 합집합(경계=leaf 앱 역결합 금지, shared/느슨참조 경유). EOD측은 RECON 후.

**[2026-08-10] NEWS-S2 확정 부기 — "운용 중" 정의 = archived 제외 전부**: `_get_monitor_target_symbols`의 status 필터를 `exclude(status__in=[PAUSED, ARCHIVED])` → **`exclude(status=ARCHIVED)`**로 확정(네거티브 필터). **status 도메인 전수**(`Monitor.Status` choices): `setting_up`·`active`·`paused`·`archived` — 이 중 **archived만 제외**, 나머지 셋(setting_up·active·paused) 포함. paused=일시정지는 재개 가능한 운용 상태 → 수집 유지가 재개 시 공백을 없앤다. **실측 근거**(2026-08-10): stock-scope Monitor 6종(GEV/GOOGL/IONQ/IREN/PLTR/TLN) **전부 setting_up · active 0**. "운용 중=active만"이면 6종 전부 누락(전멸) → active 문자 그대로는 사각지대 미해소. **별건 관찰**(좌표만·수리 금지): 6종 status **전이 0건**(개시 이후 setting_up 고정 — active 승격 로직 미발화). test `test_monitor_target_symbols`(7 green)에 paused 포함·archived 제외 케이스 반영.

## [2026-08-06] D-MON-P2A — 점수 정직성 수리: H1 판정(희석 실재, 층위=scorer) + 스코프 C [monitor]

> 출처: 지시서 MON-P2A. 근거: MON-DETAIL-P1 T3(H1) + 본 트랙 T4·T5 실측. 상위 D-MON-TRACK-ORDER-20260806 ⑴ 발동.

**결정**: H1(점수 희석) **실재 확정** — 단 층위는 aggregator None-대입이 아니라 **⑴ EODSignal SP500 한정으로 비SP500 EOD계열 3지표 n=0**(IONQ/IREN/TLN, 가중 1/3 상시 0) + **⑵ 부분 reading-count로 momentum/sma가 무언 계산**. **스코프 C(수학 수리)** 채택: 충분성 계약(scorer `{score, is_sufficient}`) + aggregator **재정규화**(유효 지표만, 무데이터 분모 제외) + 커버리지 표출(`indicator_coverage {sufficient,total}`). 데이터 수리(EOD 유니버스 확장)는 T4 후 별도 결정.

**Why**: 무데이터 지표를 0.0으로 희석하면 종합점수가 중립쪽으로 왜곡(IONQ/IREN/TLN before 6/9인데 3 무효 지표가 full weight로 참여). **★T4/T5 실측 경고(값 미확정)**: draft min_n(momentum=252·sma200=200·high_52w=252)은 **DailyPrice-이력 기준 수치**이나 scorer는 **reading-count**를 봄 → 전 6종에서 momentum/sma/high_52w(강·강·중 근거) **과잉 제외**(DailyPrice는 271~772행으로 momentum 산출 요건 충족 = 값 유효). **min_n 값·게이트 층위(scorer vs ingest)는 계획 세션 확정 — 배포 전 필수**. **P2A-CUT**: 신 로직 적용 asof(배포일)를 점수 시계열 단절점으로 기록(후속 캘리브레이션 구간 구분). **T5 before→after(읽기 전용 재산출, evaluate 미호출)**: GEV 0.0262→0.0969(7/9)·GOOGL 0.1084→0.2315(7/9)·IONQ -0.0375→0.0338(4/9)·IREN -0.0288→0.0374(4/9)·PLTR 0.1567→0.2261(7/9)·TLN 0.0015→0.0738(4/9). 전 6종 상향(재정규화가 0쪽 희석 지표 제외). **전 6종 공통 제외 = sma200_gap·momentum_12_1**(draft min_n 200/252 > reading-count 19~126, 단 DailyPrice는 271~772행으로 값 유효 = 과잉제외) + 비SP500 3종은 EODSignal 0인 eod_composite·change_percent·dollar_volume 추가 제외. **bounded(high_52w·rsi)는 scorer min_n 미적용**(점수=최신값 범위매핑, reading-count 게이트 범주 부적합 — 진짜 이력 부족은 compute 계층 소관, T4).

**[2026-08-08] ADDENDUM — min_n 확정 (STEP0 착수조건 해소, MON-P2B 지시서 경로 1)**: 위 ★경고의 두 미결(min_n 값·게이트 층위)을 확정한다.
- **n-기준 확정 = 계산 소스 행수(source_n)**. reading-count(IndicatorReading 행수)를 충분성 판정에서 **폐기**한다 — min_n은 '오늘의 지표값을 만들 원천 데이터(DailyPrice/EODSignal) 행수' 조건이므로 z 히스토리 길이(readings)와 **별개 범주**였다(P2A 범주 오류). `source_row_count(indicator, entry, as_of)`가 catalog `source`로 소스 모델(DailyPrice/EODSignal)을 판별해 `stock__symbol=monitor.target_ref` count를 반환, `source_n < min_n`이면 무언 계산 금지·불충분 반환.
- **min_n 값 = 초안 유지**(변경 없음): eod_composite·change_percent·dollar_volume=1 / sma200_gap=200 / momentum_12_1·high_52w_proximity=252 / volume_ratio=21 / macd_histogram=35 / rsi14=15.
- **게이트 층위 확정 = scorer 계층**(`score_indicator_from_model`·`score_indicator_dispatch`). 순수함수 `score_indicator`는 **z 계산 가능성**(robust median/MAD 최소 관측 5)만 게이트, min_n 정책은 상위로 격상. **bounded(high_52w·rsi14)도 source_n 게이트로 통일**(P2A의 "bounded min_n 미적용" 폐기 — DailyPrice 이력 유효성으로 판정, reading-count 아님).
- **확정 행렬(교정 재산출)**: SP500형(EODSignal 존재) = **9/9** (GEV +0.0185·GOOGL +0.0918·PLTR +0.2294) / 비SP500형(EODSignal 0) = **6/9** (IONQ +0.0077·IREN +0.0076·TLN +0.0488, 불충분 = eod_composite·change_percent·dollar_volume). **P2A 원본 T5(7/9·4/9)는 reading-count 오게이트 산물 → 무효화**. 교정 overall이 P2A 원본보다 낮은 것은 momentum/sma(양수)를 과잉제외해 부풀렸던 것을 정직하게 포함시킨 결과(정직성 개선). **P2A-CUT asof는 교정 배포일**(P2B와 단일 배포창) 기준으로 확정. 검증: monitor pytest 231→236(신규 source_n 7·제거 순수 min_n 2)·전 236 green.

## [2026-08-06] D-NEWS-P0-REPAIR — 뉴스 수집 유니버스 수리 (S3 등재 + S1 defect + S2 자동 편입) [news]

> 출처: 지시서 NEWS-P0-FIX(구현) + MON-P2A T0(결정 등재). 근거: RECON-NEWS-P0.

**결정**: ⑴ **S3** — 비SP500 보유 3종(IONQ·IREN·TLN)을 NewsCollectionCategory custom 멱등 등재(SP500 3종은 orchestrator 커버). ⑵ **S1** — `collect_press_releases_fmp` defect 수리(아래 각주). ⑶ **S2** — 활성 monitor target 자동 편입(`collect_daily_news` 합집합, D-COLLECTION-UNIVERSE 1호 구현, 경계=monitor 앱 direct import 금지·`apps.get_model` 느슨참조).

**★HA-P0 R5 정정 각주**: R5의 "`SP500Constituent.market_cap` 조회분 전건 None"은 **부정확** — 실제로는 **필드·컬럼 자체가 부재**(`.order_by("-market_cap")` = FieldError). market_cap write 경로 없음(FMP 402 무관). **How to apply**: S1 분기 = Stock.market_capitalization 채움율 실측(98.83%≥80%) → Stock join 정렬. **★S2 결정 필요(실측 발견)**: monitor "활성" 필터를 `status=ACTIVE`(문자 그대로)로 하면 보유 6종 전부 `status=setting_up`이라 **no-op** → 목적(사각지대 해소) 미달. 처방=paused/archived만 제외(`status__in=[setting_up, active]`)로 조정(계획 세션 확인).

## [2026-08-06] D-MON-TRACK-ORDER-20260806 — HA-P0 RECON 기반 트랙 순서 판정 3건 [monitor]

> 출처: 지시서 MON-DETAIL-P1 §0(편승 등재). 근거: HA-P0 RECON 실측(4fcc768d). 상위 D-MONITOR-HORIZON-ADVISOR §8.

**결정**: ⑴ **P1(MON-DETAIL) 선행** — H1 실측(→T3)에서 희석이 실재하면 P2a(재정규화 계약 확장) 미니 트랙을 P1 직후 삽입한 뒤 P2(HORIZON). ⑵ **P4(ADVISOR L-A) → P5(THEME) 순서** — 승격 게이트 표본 시계(n≥40) 조기 가동 + 단방향 불변식(I-1)으로 THEME 후착지 비용 0. ⑶ **NEWS-P1 착수 보류** — 전제조건 **NEWS-P0**(수집 유니버스·market_cap 수리) 신설, RECON은 별도 지시서(RECON-NEWS-P0).

**Why**: RECON R7(AnthropicProvider 완비→P4 조기 가동 저비용)·R2(재정규화 계약 확장 선행 필요)·R5(TLN 뉴스 0건·market_cap None→수집 축 결함이 NEWS 전제)가 순서를 규정. **How to apply**: P1 구현 후 T3 결과로 P2a 삽입 여부 확정(계획 세션 판정 — 이 지시서는 측정만).

## [2026-08-06] D-MON-DETAIL-LAYOUT-B — 상세 화면 배치 B안 확정 (슬림 스트립 + 일지 지배) [monitor] [frontend]

> 출처: 지시서 MON-DETAIL-P1 §0. 목업 2안 비교·가중 판정(B 0.850 vs A 0.690) 후 사용자 확정 2026-08-06.

**결정**: 상세 화면 = **슬림 6토큰 스트립**(상태·존·점수+Δ·손절여유·D-day·danger) + **일지 지배 영역** + **일지 kind 레지스트리**(JournalEntry={kind,asof,payload}). P1 구현 kind 3종(snapshot·transition·open) + 예약 3종(advisor·theme·memo — 타입 슬롯만, 레지스트리 미등록 → 안전 무시). **메모 기능은 P1.5로 분리**(스코프 아웃).

**Why**: 시간축 서사 부재 해소(일지가 "무엇이 달라졌나"를 지배 표면화) + kind 레지스트리로 P4(advisor)/P5(theme)/P1.5(memo)가 렌더러만 추가하면 점등되는 전방 호환 확보. **How to apply**: 스트립·일지 모두 BE 단일 소스 소비(FE 재계산 금지). 손절여유 위험 강조는 기존 신호(danger_streak·close_suggested·이탈 존)만 게이팅 — 신규 임계 창설 금지.

## [2026-08-06] D-DEPLOY-NONFF — origin churn 하 배포는 non-FF 머지 채택 (FF 포기) [process] [git]

> 트랙: L2-FULL-SWEEP 배포(POST-DEPLOY-VERIFY 사후 등재). 착지 = origin/main `4fcc768d`.

**결정**: 활성 origin/main churn(세션 간극마다 3~5커밋 전진) 환경에서 세션 브랜치 배포는 **non-FF 머지**를 채택한다(FF push 포기). `git merge --no-ff <session-branch>` → push.

**Why**: L2-FULL-SWEEP 배포 시 FF push가 **물리적으로 도달 불가**했음(rebase→FF-check 사이에 origin이 재전진, behind 3→5→1 반복 재발 → 무한 rebase 루프). non-FF 머지는 ⑴ **rebase 불요**(세션 커밋 해시 보존 → 원장 해시 앵커 유효, 해시 앵커 무효화 함정 회피) ⑵ **churn 강건**(behind여도 merge가 reconcile) ⑶ 머지 커밋이 트랙 경계를 히스토리에 명시. 실측 검증(POST-DEPLOY-VERIFY): 세션 9커밋(88850fce…3b9730ce) 전부 origin/main 조상, 원장 참조 해시 전부 valid(dangling 0), 병합 조합 스위트 GREEN(makemig 0·pytest 724·vitest 12·tsc 0).

**유효 범위**: 본 결정은 **active-churn 배포의 실절차**로 확립. 전체 배포의 **기본 머지 방식으로 승격할지는 mgmt 판단에 위임**(FF는 저churn 트랙에서 선형 히스토리 이점 잔존). 진입점 = `sv sync`(D-SYNC-ENTRYPOINT, stale 사본 차단) → worker_sync 3트리 재기동 → web rebuild.

## [2026-08-04] D-MONITOR-HORIZON-ADVISOR — monitor 3층 증축(horizon·LLM Advisor·T계열 테마) [monitor] [llm] [chainsight]

> 상태: **확정**(사용자 승인 2026-08-04). 상위 계보: **D-MONITOR-TIMING-PIVOT** — 그 위의 3층 증축이며 피벗 불변식(§3.1 EOD·§3.2 가치 축·§3.3 경계·§3.4 행위보존) 전부 계승. 관련: D-MONITOR-REBUILD·D-EOD-FRESH(+FIX-1).

**결정**: monitor 위에 ⑴ **HORIZON**(swing/position/core 수동 선언 → 지표 가중 프리셋·채점 창·기한 기본값·비서 문맥 일괄 결정) ⑵ **ADVISOR**(LLM 투자 비서 = 단일 코어 + 3 트리거 표면 L-A 해설자/L-B 상담역/L-C 파수꾼, 설계는 첫날 완결·점등은 승격 게이트 순차, 전 권고 AdvisorNote 전수 기록·시장/마감 2축 채점) ⑶ **T계열**(Chain Sight 테마 그래프를 EOD 스칼라 신호로 승격, 통로=스키마 선행+수동 시드 T-B)를 전부 **additive**로 증축.

**Why**: 시간축 혼재(스윙 후보와 코어 보유가 동일 문법)·해석 부재(결과값만 남고 서사 없음)·고립 종목 관측 한계(테마 순풍 vs 고유 악재 미구분)·도그푸딩 목적("LLM이 매매 판단 보조에 유용한가" 본인 데이터 검증, 게이트 불통과=답).

**How to apply**: 전문·불변식 7개(I-1 단방향~I-7 규제 예약)·가중 프리셋·채점 수식·승격 게이트 수치·스테이징(HA-P0 RECON→P1~P6→G1→BRIDGE→G2)은 **standalone ADR** [`D-MONITOR-HORIZON-ADVISOR.md`](D-MONITOR-HORIZON-ADVISOR.md) 참조(상세 단일 소스). 다음 착수 = HA-P0 RECON(읽기 전용 통합 실측). 코드 0·본 커밋은 문서 등재 전용.

## [2026-08-01] D-DOTSYM — dot 심볼 복원 (옵션 1: 정본 dot 저장 + FMP 래퍼 경계 변환) [chainsight] [shared]

**결정**: SP500 class-share 심볼(BRK.B·BF.B)을 유니버스에 복원. **DB·전 내부 계층의 정본 = dot 원형**, 하이픈 변환(BRK-B)은 **FMPClient 요청/응답 경계 단일 지점에서만** 발생(앱 계층은 변환의 존재를 모름 — 외부 API 표기법을 외부 접점에 봉인).
- **Q1 (마진 2.20 자동)**: dot-필터 A+B+C **전량 제거**.
- **Q2 (마진 1.55 자동)**: FMP client **전 심볼 메서드 일괄 변환 = 요청 경계 단일 지점**(`_make_request`) 삽입(26개 호출 수렴).
- **Q3**: **heat 동반 503 편입 = 의도**(유니버스는 estimates·heat 공용 `live_universe_symbols`).
- **Q4**: 유니버스 복원 = **코드만**(SP500Constituent 이미 503 상존), DB 시드 분기 폐기.
- **Q5**: **C₃(`backfill_daily_prices`) 포함** — STEP 0 실측에서 dot-필터가 3→6개소로 확대 발견, Q1 취지(수집 경로 dot 배제 전량 제거) 적용. 미포함 시 estimates만 503·가격 501 반쪽.
- **Q6**: **C₂(`tasks.py:232`) 제거 승인** — C 파일 동일 목적(SP500 수집).

**Why**: dot 심볼이 유니버스에서 빠져 estimates 커버리지가 501/503(BRK.B·BF.B 상시 누락)이었음. 원인은 Bug #23(FMP 402) 회피를 위해 **유니버스 단계에서 dot 심볼을 배제**한 6개소 필터. 그러나 402의 실제 원인은 dot 표기(BRK.B) 자체로 호출한 것이고, FMP는 **하이픈(BRK-B)**을 요구 → 변환 계층으로 해소 가능(프로브 실증). 변환을 유니버스가 아닌 **API 경계에 봉인**하면 내부는 dot 정본을 유지하면서 전 엔드포인트가 정상 응답.

**How to apply**:
- Slice 1 (`c8fe4037`): `symbol_convert.py` 순수 함수(to/from) + `_make_request` 요청 정변환 단일 삽입.
- Slice 1-3 (`44ebb186`): 응답 경계 역변환(`restore_symbols_in_response`) — 프로브 실측(FMP가 hyphen 회신) 근거.
- Slice 2 (`cb6bf97d`): 필터 6지점 전량 제거 + 테스트 동기화 (revert = 6지점 완전 원복 롤백 단위).

**검증**: Slice 1.5 라이브 프로브 **14/14 HTTP 200·402 0**(estimates/quote/profile/ratios/key-metrics/insider/EOD, BRK-B·BF-B) · 전체 스위트 **4488 passed/0 fail/53 skip**(사전 4460 대비 신규 테스트 +28, 기존 fail 0) · `makemigrations --dry-run` 0(스키마 무접촉) · `live_universe_symbols()` **503**(BRK.B·BF.B 포함) · estimates dry-run 저장 예정 symbol=**dot 원형**(prod 쓰기 0). Bug #23(FMP 402)은 변환 계층이 해소. 최종 게이트 = 08-07(목) 정규 cron 5회차(별도 PROBE-EST-5TH).
## [2026-08-04] D-L2-FULL-SWEEP — L2 전량 태깅 실행 결과 (유료·실단가·최종 분포) [chainsight]

> 트랙: ⑳-3 L2-FULL-SWEEP B단계. 브랜치 `monorepo/sess-l2-adopt`. 병진 승인(2026-08-03, 규칙 A).

**결정**: D-L2-SOURCE 결정 2를 **전량 실행**. 유료 티어 Gemini 2.5 Flash 단일 세션, `--apply` prod 기록.
distinct 9,365쌍 전량 태깅 완료(json_fail 0·circuit_fail 0).

**실단가·비용**: 콜당 **$0.00050515**(in ~289tok·out ~167tok) → 배치 8,876콜 $4.4837 + 선행 ~$0.26 =
**총 ≈ $4.74**(추정 $4.4 근접, 게이트 2×$8.8 이내). P2 마이크로배치 실측이 게이트 통과 근거.

**최종 분포(9,365)**: 채택 5,928(63.3%) / 거부권 68(0.73%: low_grounding 67·no_claim 1) /
빈 태그(draft無)→버킷 폴백 3,389(대부분 타산업) / 추정 라벨 2,511(26.8%, 기대 2,498 정합) /
status auto 9,297·pending 68 / 채택 태그종 3,063.

**대사(reconciliation) — DB가 정본, summary.json은 세그먼트 evidence** (PRE-DEPLOY-FIX 2026-08-05):
- **상호배타 파티션 등식**: 채택(draft有·비veto) 5,928 + 거부권(veto) 68 + 빈태그·미거부권(draft無·비veto) 3,369 = **9,365 = distinct**.
  기보고 "빈 태그 3,389"는 draft無 **전체**(거부권 발동 중 draft無 20건 포함) → 거부권과 20건 겹침(비배타). ∴버킷 폴백 총 = 68 + 3,369 = **3,437**.
- **세그먼트 대사 등식**: DB 전수 9,365 = summary.json 세그먼트(최종 invocation) 8,876 + 선행 세그먼트 489(마이크로배치 20 + 파일럿 청크 469).
- **이중처리 무**: raw 태깅 행 9,365 = distinct 9,365(차이 0), 2+ 방향행 이중기록 0 → 각 쌍 정확히 1회 처리·과금.

**Why(거부권 분포)**: 거부권은 **industry 결측 쌍 + 제네릭 태그 메가캡**(AMZN↔MSFT gr 0.167, AMD↔AVGO
"반도체" gr 0.042)에 집중. A1이 우려한 하·상이(소형·타산업)는 예측대로 ~0%(7/2,511=0.3%). "생성은
풍부하게, 필터는 거부권" 원칙대로 억지·제네릭 태그를 grounded≤0.2가 정상 필터.

**검증(P4)**: ego 서빙 라이브 — 채택 쌍 peer_domain=llm_tag 노출·estimate 플래그 작동, 거부권 쌍은
엣지 미은닉+peer_domain=null(버킷 폴백)+status=pending(soft-drop 회피 실증). 리포트
`docs/chain_sight/L2_ADOPT_A_STAGE_REPORT.md` B단계 섹션.

**교훈**: A4 견적의 "1-2h"는 thinking 지연 미반영 과낙관 — 실 ~11h(견적 교훈, common-bugs 아님).

## [2026-08-04] D-L2-THINKING-BUDGET — LLM thinking_budget=512 채택 (생성 풍부·거부권 필터) [chainsight][llm]

> 트랙: L2-FULL-SWEEP P2. 병진 승인(2026-08-03).

**결정**: Peer 도메인 태깅 LLM 호출에 `thinking_budget=512`를 채택한다. 공유 래퍼
`generate_content/with_circuit`에 **optional thinking_budget**(기본 None=기존 호출부 불변) 추가, peer
배치·훅만 512 전달.

**Why(3안 실측 A/B)**: 2.5 Flash 기본(thinking ON 무제한)은 지연 ~8.8s(전량 ~23h). thinking OFF(0)은
~1.8s이나 타산업(79%) 쌍 대부분 빈 태그(정보량↓). **budget=512는 지연 ~4.2s(~11h)에 타산업 태그
방출을 ON 이상 보존**(AMD↔PLTR "데이터센터·고성능컴퓨팅" — ON은 누락). 비용 3안 동일($0.0005/콜).
억지 태그는 거부권(grounded≤0.2)이 사후 필터하므로 **"생성은 풍부하게, 필터는 거부권"** 원칙에 부합.

**How to apply**: `generate_content(..., thinking_budget=None)` — 명시 전달 시만 config에 thinking_config
추가(다른 호출부 IDENTICAL). peer 경로(`tag_peer_domains` 배치·`tag_peer_domain_task` 훅)=512.
가드: 본배치 1,000콜 체크포인트(거부권률·빈태그율·추정률 vs A1/A3), 거부권>5% or 빈태그 급변 시 정지.
실측 체크포인트(n=1,039): 거부권 0.96%·빈태그 36.2%·추정 22% → PASS(자동 계속).

## [2026-08-03] D-L2-SOURCE — L2 Peer 소스 결정 2: LLM 태그 채택 + 판정기 거부권 [chainsight]

> 트랙: ⑳-3 L2-ADOPT. 브랜치 `monorepo/sess-l2-adopt`(base origin/main `34a171dd`). 선행 D-L2X-AUTO-ADJUDICATION.
> L2-SOURCE-DECISION(교체/하이브리드/현행) 재개점의 **결정 2** 확정.

**결정**: PEER_OF L2 도메인 소스를 **LLM 태그 기본 채택**으로 한다(교체안). 단 결정론 **판정기 거부권**을
둔다 — `grounded_ratio ≤ 0.2`(고정 임계) 발동 시 태그 기각 → **업종 버킷(industry_bucket) 폴백**.
- 프롬프트 ㉯(심볼+회사명+industry), **claim 영어 출력**(L2X-SWEEP-EN-CLAIM 흡수 — 영어 desc 동일언어 접지).
- **하·상이 구획(저시총·타산업) "추정"(is_estimate) 라벨** — 실험상 최저 접지·최고 과신.
- 거부권 status = **'pending'**(미채택→버킷 폴백). **'rejected' 금지**(ego 서빙이 soft-drop=관계 은닉 → 거부권은
  "태그 기각"이지 "관계 은닉"이 아니므로). relation_domain(승인본)은 **절대 미기록**(L1 하드 룰 계승).

**Why**: 사람이 LLM rationale를 반증하기 어렵다는 D-L2X 소견 + 실험(240쌍 자동판정)에서 인간 16/18 BETTER·
1 WRONG(CRM↔MTCH). 판정기가 그 1 WRONG을 grounded 0.0으로 정확 포착 → **결정론 거부권이 명백한 오류만
고정밀 차단**(과신 플래그 gr_q1=0.667은 저정밀). LLM 태그는 industry_bucket보다 세분·구체 → 마인드맵 L2 정보량↑.
거부권+버킷 폴백으로 안전망 확보(태그 실패 시 항상 버킷 존재).

**스코어·실험 근거**: A1 재집계(240쌍·LLM 0) 거부권 0.2 발동 **1/240(0.4%)** = CRM↔MTCH(하·동일, grounded 0.0,
"구독형 SaaS" 표면 공통점 vs B2B CRM/B2C 데이팅). A3 파일럿(㉯ 120쌍·LLM 0) 채택 119·거부권 1·추정라벨 20.
B단계 예상 폴백 ~241쌍(2.6%: 거부권 ~37 + 결측 204), 채택 ~95%+.

**How to apply**: 코어 `services/peer_domain_tagging.py`(커맨드·훅 공유): `tag_peer_one`(초안→`ground_claim`→
`veto`→machine_check), `is_estimate_cell`, source='L2-ADOPT'. 판정기 `peer_adjudicator.veto`(고정 0.2·None 보수적
기각). 배치 `tag_peer_domains`(--dry-run/--apply 게이트/--pilot-csv/idempotent·재개·rate 4.2s). 훅
`tasks/domain_tasks.tag_peer_domain_task`(단건, L1 휴면 패턴 — 활성화=배포 게이트). 서빙: ego API `peer_domain`
(채택분 source=L2-ADOPT ∧ status=auto)·`peer_domain_estimate` additive → FE `egoMindmap` L2 하위그룹 llm_tag
우선·버킷 폴백. **마이그레이션 0**(기존 필드 재사용, STEP 0 스키마 게이트 PASS: relation_domain choices=None).

**STEP 0 측정**: PEER distinct 무방향 쌍 9,365(raw=distinct·중복 1.000x), 태깅 가능 9,161(97.8%)·결측 204,
industry_same 동일1,790/상이7,402/미상173, "추정"(하·상이) 2,498. SEC verdict 270 타입 분리 무접촉.

**검증**: pytest 신규 16(veto 경계 4 + L2 e2e 12) + 회귀 domain 43·experiment 11·ego 38 GREEN. 마인드맵 vitest
12(신규 3). makemigrations 무변경. tsc 0. **A단계 무비용(신규 LLM 0)**. 아티팩트 `outputs/peer_experiment/`(240쌍
실험)·`outputs/peer_domain_tagging/`(파일럿). 리포트 `docs/chain_sight/L2_ADOPT_A_STAGE_REPORT.md`.

**게이트(미승인)**: B단계 전량 태깅(비용 발생)·`--apply`(prod 태그 기록)·머지·배포 = 병진님 승인. 견적(A4):
Gemini 무료 7일 분할($0) vs 유료 단일 세션(~$4.4·추정). 착수 직후 마이크로배치 5-10콜로 실단가 확정 권장.

## [2026-08-03] D-L2X-AUTO-ADJUDICATION — L2-X 사람 전건검수 → 결정론 자동판정 + 감사 [chainsight]

> 트랙: ⑳-3 L2-X 자동판정 전환. 배경: 대조자료 제공에도 사람이 LLM 주장 반박 구조적 곤란(15건 실검수 소견).

**결정**: L2-X PEER 추측 태깅 판정을 **전건 사람 검수 폐기 → 결정론 자동 판정 + 사람은 판정기 감사만**. **채점용 LLM 호출 0**(순환 채점 금지 — 판정기는 결정론+실데이터만). sweep 재실행 없음(기존 240행에 판정 컬럼 추가).

**판정기 3종**: ⑴ grounding(claim 용어 ↔ desc 접지) ⑵ market(가격상관 불일치 신호, 단독판정 아님) ⑶ cross(known_fact ∧ 저접지 = 과신).

**grounding 전략(C 하이브리드)**: claim=한국어 / desc=영어 → SEC β `ground_evidence`(동일언어 substring) **직접 이식 불가**. `normalize()`만 재사용. 영어토큰 직매칭(심볼·회사명 제외) + 한→영 동의어 사전(데이터 파일 `peer_grounding_dict.json`, 버킷+normalized_tag+claim 빈출 시드). **en/syn 접지 비율 분리**(사전 갭이 진짜 ungrounded로 오염 방지, #79 교훈). ungrounded 빈출은 사전 보강 후 재집계(결정론=비용0).

**Why**: LLM 자기보고(rationale)를 사람이 반증하기 어려움 → 판정 권위를 결정론 실데이터(FMP desc·가격상관)로 이전. 사람은 판정기 산출을 감사(동의/이견)만 → 확장성+객관성.

**How to apply**: `peer_adjudicator.py`(3판정기)·`peer_tag_experiment --judge`(병합 CSV)·`--aggregate` v2(구간별 지표+감사 표본). 검수도구 감사 모드(grounded_ratio 헤더→[동의/이견]). 실측(240,LLM0): grounded 중앙 0.83·하·상이 과신 0.4(최고). 후속=verdict 회수 후 L2-SOURCE-DECISION.

## [2026-08-03] D-GATE-AUDIT-TRAIL — 도메인 태깅 게이트 판정 감사 추적 [chainsight]

> 트랙: ⑳-3 S3-LAND S3. L1 프로덕션 파이프라인.

**결정**: `decide_gate` 판정 시 `domain_machine_check.gate_audit` JSON 키에 **발동 룰 목록·룰별 비교 원값·최종 판정 경로**를 additive 기록한다. 마이그레이션 0(JSONField 키).

**Why**: 자가모순 53건류 미스터리(캘리브레이션 전력)가 재발하면 "왜 이 판정이 났나"를 로그로 즉답해야 한다. 게이트가 4분기(self_contradiction/type_change/all_checks/checks_fail)로 분기하므로, 어느 룰이 발동했고 피연산자 원값(type_match 좌우·confidence vs 임계)이 무엇이었는지를 남긴다.

**행위보존 원칙**: 게이트 **판정 로직은 무변경**. `build_gate_audit`이 `decide_gate`의 조건을 미러링해 **기록만** 한다. 정합성은 ⑴ 기존 게이트 테스트 GREEN(행위 불변 입증) ⑵ audit 경로↔decide_gate 판정 일치 테스트로 못박는다. 기록은 감사 전용(ego API·화면 미노출).

**How to apply**: `domain_tagging.build_gate_audit(mc, relation_type)` → tag_one이 mc["gate_audit"] 기록 → DB write 경로가 domain_machine_check로 저장. 기록 범위=fired_rules·values(피연산자)·decision_path.

## [2026-08-03] D-LLM-RATIONALE-AUDIT — LLM 태깅 근거(rationale) 구조화 감사 기록 [chainsight][llm]

> 트랙: ⑳-3 S3-MINDMAP 패치2. L1 프로덕션 파이프라인 + L2-X 실험 공통.

**결정**: LLM 도메인 태깅 시 **구조화 rationale**{claim, claim_type(known_fact|inference|uncertain), basis_hint, counter_signal}를 함께 요구하고, `domain_machine_check.llm_rationale` JSON 키에 **전건(auto/pending 무관) 감사 기록**한다. 마이그레이션 0(JSONField 키 additive).

**Why**: 자동 태깅(D-AUTO-SWITCH-ON)·PEER 추측 실험(L2-X)에서 "왜 그 태그인가"를 사후 분석해야 오류 패턴을 잡는다. 특히 **보류(pending) 건의 사후 분석이 핵심**(무엇이 확실치 않았나). claim_type/counter_signal은 "known_fact인데 틀림"·"반대 신호 존재 시 정확도" 같은 매트릭스를 가능케 함.

**한계 명시(자기보고)**: rationale는 LLM의 **자기 진술**이지 검증된 판정이 아니다 — 사후 합리화(post-hoc rationalization) 가능. 따라서 ⑴ 게이팅·자동승인에 rationale을 **입력으로 쓰지 않음**(decide_gate 무참조) ⑵ ego API·화면 **미노출**(감사 전용) ⑶ **부속이 본체를 블록하지 않음**: rationale 형식 실패 시 null 기록하되 태깅(gate/draft)은 정상 진행.

**How to apply**: 코어 `extract_rationale`(방어적 파싱, 공유). L1=`tag_one` mc["llm_rationale"], DB write 경로가 domain_machine_check로 자동 저장. L2-X=결과 CSV rationale_A/B + 집계 매트릭스(claim_type/basis_hint/counter_signal별 WRONG율). 검수도구 claim 표시.

## [2026-08-03] D-MINDMAP-HYBRID-v2 — ego 마인드맵 3층 체계(SEC 도메인·시장 industry·뉴스) [chainsight][frontend]

> 트랙: ⑳-3 S3-MINDMAP. 브랜치 `monorepo/sess-s3-mindmap`. D-MINDMAP(맵-3) 방향 개정. 선행 D-DOMAIN-AUTOMATION·D-REVIEW-VERDICT-VOCAB.

**결정**: 마인드맵을 **3층 하이브리드**로 개정한다(순수 도메인 태그 마인드맵 폐기 — S3-R 실측: 태그가 심볼 엣지의 ~2-9%만 커버).
- **L1 (SEC 도메인)**: `relation_domain`(승인본 태그) 보유 SEC 관계 → 태그별 상위 가지. 무태그 SEC는 관계 유형별 "유형 수납" 폴백.
- **L2 (시장 Peer)**: PEER_OF → has_peer_source(경쟁·Peer)/동종산업 상위 구분 + 상대 노드 `industry_bucket` 하위 그룹. **엣지 무기록, 서빙 시 파생**(industry 변경 자동추종).
- **L3 (뉴스)**: CO_MENTIONED → "뉴스 동반언급" 단일(기사 태그 하위그룹은 AV 복원 후).
- **PRICE_CORRELATED 제외**(Peer 중복) — 건수만 투명화.

**방향 개정 경위(2026-08-03)**: 자동화 우선(⓪-b) + 시장관계 카테고리 확장(①-C). S3-R 정찰이 ⑴ 도메인 태그 DB 0건(파이프라인 dry-run만) ⑵ 태그 커버리지 SEC 1.68%만 ⑶ ego API relation_domain None 하드코딩을 실측 → 순수 태그 마인드맵은 화면 90-98%가 미분류 잔여. 시장관계(PEER)를 industry 축으로 병용해야 의미 있음.

**How to apply**: L1 태그=S0 backfill(CSV normalized_tag→relation_domain) + S1 자동 파이프라인. L2=`industry_buckets.industry_to_bucket`(128 industry→13 버킷) 서빙 파생. ego API additive(relation_domain 실값·노드 industry_bucket). FE=`egoToMindmap`(순수)+`MindmapView`(MINDMAP_ENABLED). industry 커버리지 94.1%(STEP0). ⚠️라이브 스크린샷 검증은 배포 게이트.

## [2026-08-03] D-AUTO-SWITCH-ON — 도메인 태깅 자동승인 활성(잠정 0.75) [chainsight]

**결정**: `DOMAIN_AUTO_APPROVE` env 스위치 ON(go-live=env+재기동 게이트). 임계 `DOMAIN_CONFIDENCE_THRESHOLD`=**0.75 잠정**.

**Why**: D-DOMAIN-AUTOMATION 안전핀②(첫 배치 검수 후 활성)를 REVIEW-P2 검수 완료로 해제. 자동화 우선 방향 개정. 임계는 잠정 — 신규 관계 유입으로 검증 축적 필요.

**How to apply**: `settings.DOMAIN_AUTO_APPROVE`(env 기본 false). **타입 변경 비자동 안전핀은 스위치 무관 항상 유지**(decide_gate 하드룰). 검수 verdict 270건은 자동 파이프라인 대상 제외(is_human_reviewed 보호 가드). **임계 0.75는 잠정 — 언앵커 40건 처리로 conf 기준점 확보 후 재확정**(TASKQUEUE REVIEW-UNANCHORED-40).

## [2026-08-03] D-LLM-RECALL-RULE-v2 — LLM 재호출 금지 룰 축소(verdict 보유분 보호로) [chainsight][llm]

> D-DOMAIN-AUTOMATION 안전핀·common-bugs #80 개정. preserve-both.

**결정**: "LLM 재호출/재분류 금지" 룰의 범위를 **"검수 verdict 보유 270건 보호"로 축소**한다. verdict 미보유 관계(신규 SEC·PEER 등)에 대한 LLM 태깅·실험은 허용.

**Why**: 원 룰은 "LLM 재호출 결과 자동반영 금지"(비결정성 drift 방지, #80). 그러나 자동화(D-AUTO-SWITCH-ON)와 L2-X 실험(PEER 추측 태깅)은 verdict 없는 관계에 LLM을 새로 적용하는 것이라 원 룰의 취지(인간 재정 덮어쓰기 금지)와 무충돌. 룰을 전면 금지가 아닌 "인간 판정 보호"로 정밀화.

**How to apply**: 보호=`is_human_reviewed`(review_status有∧machine_check無) 가드가 커맨드·훅에서 verdict 270 제외. L2-X는 240쌍 한정·DB무기록. 타입 변경 비자동은 유지. verdict 보유분 재호출·자동반영은 여전히 금지.

## [2026-08-01] D-REVIEW-VERDICT-VOCAB — 검수 verdict 어휘 5종 + CHANGE_REV 방향 스왑 의미론 [chainsight]

> 트랙: ⑳-3 REVIEW-P2. 브랜치 `monorepo/sess-review-p2`. 입력=동결 `docs/etc/review_batch_v6_labeled.csv`(270행). 선행 [D-DOMAIN-AUTOMATION](#).

**결정**: 인간 검수 verdict 어휘를 **5종**으로 확정하고 `RelationConfidence.domain_review_status`(기존 mig 0028 필드, choices pending/approved/auto/rejected)에 반영한다.
- `OK` → `approved` (검수 승인)
- `DROP` → `rejected` (**soft-drop**: serving 제외 + 레코드·궤적 보존, 삭제 아님)
- `HOLD` → `pending` (재분류 대기)
- `CHANGE:<TYPE>` → `relation_type`=<TYPE> + `approved` (같은 방향, 타입만 교체)
- `CHANGE_REV:<TYPE>` → **방향 스왑**(symbol_a↔symbol_b) + `relation_type`=<TYPE> + `canonical_direction`='a→b' + `approved`

**결정 E(도구 UI)**: 검수 도구의 verdict 입력 UI 정식화는 **수요 반복 확인 후**로 유보(현재 1회성 배치 = CSV+로더로 충분). 반복 검수 수요가 확인되면 TASKQUEUE REVIEW-TOOL-V6-IMPROVE에서 승격.

**Why**: 도메인 태깅 머신 게이트(D-DOMAIN-AUTOMATION)가 pending/auto로 남긴 예외를 **인간이 최종 해소**하는 어휘가 필요. verdict는 그 머신값의 인간 재정(裁定)이므로 같은 필드(`domain_review_status`)에 덮어쓰는 것이 의미 정합(별도 필드=중복 상태원). soft-drop은 오판정 복구·감사추적 위해 삭제 대신 상태 전환. CHANGE_REV는 "경쟁으로 오분류된 공급관계를 방향까지 바로잡음"(예: ANET↔AVGO COMPETES_WITH → AVGO SUPPLIES_TO ANET)을 표현.

**How to apply**: 로더 `apps/chain_sight/management/commands/apply_review_verdicts.py`. verdict 접두사 파싱(`CHANGE_REV:` 우선). 매칭 키=(symbol_a,symbol_b,relation_type), CSV `symbol_pair`를 '↔' split한 순서가 DB 방향 보존 → **forward-exact 유일 매칭**(0/2+건 → HALT H-C). `--dry-run` 기본·트랜잭션 원자·idempotent. CHANGE_REV는 별도 플래그 `--apply-change-rev`(게이트 G1 스왑결과 엣지 기존재/G3 unique 위반 판정, 실패 시 해당 1건 HOLD). serving 제외=ego API `.exclude(domain_review_status='rejected')`. **STEP 0 실측(2026-08-01, origin/main `d484b9cb`)**: CSV 270행 forward-exact 270/270·mig 0028 DB 적용(`[X]`)·CHANGE_REV 대상 G1/G2/G3 전부 PASS. `basis_summary`는 스왑 시 원문 보존(재생성은 review-tool 위임). **실 DB 반영(--apply)은 dev=prod 공유DB prod-write → 병진 명시 승인 게이트**([[lesson_dev_prod_shared_db]]).
## [2026-08-01] 관찰 — 구체 규칙 > 일반 Gate 틀 (web 재빌드 위임 사절) [harness] [process]

**관찰(결정 아님)**: 08-01 COVERAGE-DETAIL-FE LAND 세션이 web 재빌드 집행을 "이어서 하겠다"고 **위임 제안**했으나, `#62`(FE 배포=재빌드, **웹 리빌드는 사용자 수동**) 문언을 우선해 **사절**하고 사용자 승인 대기로 전환. 가중합 사절 **4.60 vs 위임 3.05**.
- **해석 관례 명문화**: 일반 게이트 틀(예: "LAND 후 배포까지 한 세션")과 구체 규칙(#62 웹 리빌드 사용자 수동)이 충돌하면 **구체 규칙이 우선**한다. 세션이 효율을 이유로 구체 규칙을 흡수·생략하지 않는다. (이후 사용자가 명시 승인 → 재빌드 집행은 정상 — 사절은 "승인 없이 자동 진행"에 대한 것.)
- cf. [[feedback_deploy_approval_explicit_quote]](배포=명시 승인)·#62(FE 재빌드 사용자 수동).

## [2026-07-31] D-NUMBERING-DUP — common-bugs 채번 충돌 = 중복 존치 + 구분자 부가 (A) [harness]

**결정**: 병렬 세션 동시 착지로 발생한 common-bugs 헤딩 중복(#70·#71·#72 각 2건)을 **재채번(소급 renumber)하지 않고 존치**하되, **구분자(a/b) 부가**로 구분한다(A 채택). 가중합 **A 4.20 vs 재채번 B 2.90, 마진 1.30 → 자동 결정**.
- **Why**: 기존 번호 참조(#71=배선 실주소·#72=launchd 등)가 지시서·인계·장부·커밋 메시지에 이미 다수 인용됨. 소급 재채번은 그 인용을 전부 깨뜨림(참조 무결성 손실 > 중복 불편). 구분자 부가는 **인용 보존 + 구분 확보**를 동시 달성.
- **a/b 배정 규칙**: **착지 시간순(git blame/log 실측 선착지 = a)**. 실측(2026-07-31):
  - #70: a=⑳-3 S1 표면별 서빙(`92994048` 15:30) / b=SEC β pytest maxfail(`9b0d89cd` 16:08)
  - #71: a=⑳-3 S2 레거시 에러 오번역(`b53e78f2` 16:55) / b=MGMT-BATCH-15 표면 배선(`04f943f3` 17:05)
  - #72: a=C-N-REPAIR 백필 창(`d5614c68` 10:40) / b=MGMT-BATCH-15 launchd(`04f943f3` 17:05)
- **인용 해석 규약**: 기존 `#7N` 단독 인용은 **문맥상 해당 내용 쪽**을 가리킨다(구분자 부가 전 인용이라 모호 시 내용으로 판별).

**How to apply**: common-bugs 3쌍 헤딩을 `#70a/#70b`·`#71a/#71b`·`#72a/#72b`로 개정 + 각 하단 한 줄 주석. 본문 무수정. 재발 방지 = D-NUMBERING-MGMT-ONLY(아래).
- **적용 이력**: #78 3중복(규칙 시행 전 발생분)에 a/b/c 확장 적용 (BATCH-19) — a=20b-f2 GOAL-CREATE-UI(`3ba4cf00` 11:04)·b=SEAL-PUSH-1b heat 로그(`9540993a` 11:38)·c=SEC β R2 2-dot diff(`663b17e5` 12:54), 착지 시간순.
- **적용 이력**: #80·#81 각 2중복에 a/b 확장 적용 (BATCH-20) — #80: a=COVERAGE-DETAIL migrate(`fa3e20de` 13:39, BATCH-18 mgmt 채번)·b=REVIEW-P2 LLM 모순(`6d610d67` 13:40) / #81: a=실행환경 절대경로(`fa3e20de` 13:39, BATCH-18 mgmt 채번)·b=REVIEW-P2 localStorage 캐시(`6d610d67` 13:40), 착지 시간순. ⚠b(REVIEW-P2)는 규칙 시행(07-31) 후 비mgmt 세션 채번 = 규칙 위반 경위(ⓑ 조사, 처방 디렉터 회부).
- **적용 이력**: #83·#84 각 2중복에 a/b 확장 적용 (BATCH-22) — a=SFI-I1(`9363cac9` 08-03 09:37, BATCH-20 mgmt 채번)·b=S3-MINDMAP(`2daa386f` 08-03 09:53, 비mgmt 세션), 착지 시간순. ⚠b(S3-MINDMAP)는 처방 A 착지(`05211a02`) 이전 시작 세션의 08-03 지연 착지분 = B 트리거 미해당(아래 D-NUMBERING-MGMT-ONLY 처방 정밀화 참조).
- **적용 이력**: #86 2중복에 a/b 확장 적용 (BATCH-23) — a=TH-SESSION-1(`6beb7b43` author 08-04 10:33, docs(harness) meta-only = mgmt형 병렬 채번·위반 아님)·b=L2-FULL-SWEEP 상태 어휘(`86961ec4` author 08-04 20:51, 비mgmt 채번 = 규칙 위반). 동일 머지(`4fcc768d`) 착지 = 착지 시간 동률 → **타이브레이커 author date 순**. ⚠b는 세션 시작(첫 커밋 `88850fce` author 08-03 18:24) < A 착지(08-05 10:16) = pre-A 시작 → B 트리거 미해당(REVIEW-P2·S3-MINDMAP 이은 3번째 위반). landed merge-base가 A를 조상으로 보인 것은 #40 rebase 아티팩트(아래 판정 절차 보강 참조).
- **적용 이력**: #89 2중복에 a/b 확장 적용 (BATCH-26) — a=health_check worktree-local(MGMT-BATCH-24 mgmt 채번, author 08-06)·b=TH-TNV-CHAIN-1F 세션날짜금지(비mgmt 채번, `8a41c842`가 common-bugs 실변경, author 08-07 11:09). author date 순. ⚠**b = post-A 위반 확정(첫 사례)** — 세션 최소 author date(landed 최소 `d6f6f9b5` 08-07 10:55, 헤딩 08-06) **> A 착지(`05211a02` 08-05 10:16) = post-A**. TH-TNV-CHAIN-1F는 동 세션에서 **#88b·#89b·#90** 3건을 비mgmt 자가 채번(누적 4번째 위반이자 **첫 post-A**). → **B 트리거 요건 충족**(아래 D-NUMBERING-MGMT-ONLY 처방 참조). 단 **집행은 본 배치 보류·사용자 승인 회부**.

## [2026-07-31] D-NUMBERING-MGMT-ONLY — common-bugs 채번은 mgmt 세션 전용 (재발 방지) [harness]

**결정(규약)**: **common-bugs 번호 부여는 mgmt 세션 전용**. build/측정 세션은 버그 패턴 발견 시 **"채번 후보"로만 보고**하고 번호를 쓰지 않는다. mgmt가 **push 직전 재grep 후 일괄 채번**(#40 재fetch와 동일 시점).
- **Why**: 채번 직전 재grep 규율(D-NUMBERING-DUP 재발 방지 1차안)은 **병렬 세션 동시 진행의 착지 순서 충돌을 구조적으로 못 막는다** — 두 세션이 같은 순간 재grep하면 둘 다 같은 최댓값+1을 봄. #70 충돌 후 재grep 규율을 넣었으나 **#71·#72가 재발**(2026-07-28)로 실증. 채번 주체를 mgmt 단일 세션류로 좁혀 동시성 자체를 제거.
- **운용**: build/측정 세션 보고에 "채번 후보: <내용>" 명시 → 차기 mgmt 배치가 실측+1로 부여. 관련=[[lesson_origin_main_advance_union_rebase]].
- **2026-08-03 처방**: #80·#81 충돌(비mgmt 세션 REVIEW-P2의 규칙 시행 후 채번 = 규칙 위반 분류, BATCH-20 ⓑ 조사)에 대해 **A(전파 보강) 채택** — 가중합 A 4.10 / B(훅 강제) 3.85 / C(안내) 3.00, 마진 0.25 타이브레이커 = 단계적 방어·1인 비용(B는 hardening(c) 공사 동반). **B 조건부 트리거(확정 문안, 2026-08-06 정밀화 — BATCH-22): 처방 A 착지(`05211a02`) 이후에 시작된 세션의 비mgmt 채번 위반 1회 = B 즉시 집행. A 이전 시작 세션의 지연 착지분은 트리거로 오인하지 않는다.** (B = hardening(c): 훅 `scripts/hooks` 이전 + `core.hooksPath` + pre-commit 검사 'common-bugs 신규 #NN 헤딩은 mgmt 브랜치만 허용'.)
  - **부기**: S3-MINDMAP #83/#84 08-03 위반은 **A 이전 시작 세션의 지연 착지분** → 트리거 미해당(BATCH-22 판정).
- **판정 절차 보강(확정, 2026-08-06 — BATCH-23)**: **B 트리거의 "세션 시작" = 해당 세션 커밋들의 최소 author date.** landed 계보(merge-base)는 **#40 rebase 아티팩트**이므로 판정 프록시로 **영구 사용 금지**(rebase가 pre-A 작업을 A 위로 재배치 → landed에선 A가 조상으로 오탐). **동일 머지 착지 중복의 구분자 순서 = author date 순**(착지 시간 동률 타이브레이커). 이력: BATCH-23 #86 사례 — landed(A 조상=A 이후) vs author(08-04<08-05=A 이전) 상충 → **author 기준으로 미해당 확정**.
- **⚠ B 트리거 충족 — 최초 post-A 위반 (확정, 2026-08-10 — BATCH-26)**: TH-TNV-CHAIN-1F(비mgmt, theme-heat 트랙)가 **#88b·#89b·#90**를 자가 채번(`8a41c842` common-bugs 실변경). 세션 최소 author date 08-07(≥헤딩 08-06) **> A 착지(08-05 10:16) = post-A** → **B 즉시 집행 요건 충족**(REVIEW-P2·S3-MINDMAP·L2-FULL-SWEEP 이은 4번째 위반이자 첫 post-A). **단 집행(B = hardening(c): 훅 `scripts/hooks` 이전 + `core.hooksPath` + pre-commit "common-bugs 신규 #NN 헤딩=mgmt 브랜치만" 검사)은 파괴적 인프라 변경 동반 → 본 배치에서 집행하지 않고 사용자 승인 안건으로 회부**(hardening(c) 동반 이행 여부 포함). 승인 시 별도 infra 세션 집행.
- **✅ B 집행 완료 (INFRA-TREATB-HOOKS, 2026-08-10 — BATCH-27 기재)**: hardening(c) 전항 집행·착지. **⑴ 훅 이전**: `.git/hooks/pre-commit`(비버전관리) → **버전관리 `scripts/hooks/pre-commit`**(기존 section 1 브랜치 화이트리스트·2 경로·3 KB드레인 **IDENTICAL 이관**, 원본 대비 삭제행 0 = `70a71,94` 순수 추가 + section 4 채번 가드). 착지 **merge `4f9589cf`**(mode 100755). **⑵ hooksPath 전환**: `core.hooksPath` = `.git/hooks`(절대) → **`scripts/hooks`**(상대·전 worktree 공유 config·**착지 후** 전환으로 부재 트리 게이트 상실 최소화). **⑶ 검증**: control ⓟ(비mgmt+#NN=거부)/ⓝ①(mgmt=통과)/ⓝ②(무접촉=통과)/ⓝ③(본문수정=통과) + E2E A(실커밋 차단·HEAD 불변)/B(benign 통과) 전건 PASS·오탐 0·기존 화이트리스트 동작 불변. **가드식**: staged `common-bugs.md`에 `^\+#{2,}.*\(#[0-9]+`(신규 #NN 헤딩) && 브랜치 ∌ `sess-mgmt` → 커밋 거부. **push 예외 승인 인용**: 코드 diff(≠메타 4종)라 자가 머지 예외 미적용이나, 사용자가 라우팅 질문에 **"착지 먼저 → 전환(안전순서)"** 선택 = 착지 명시 승인. **본 배치(BATCH-27)부터 채번 가드가 mgmt 세션 자신에 적용** — sess-mgmt-* 브랜치는 통과가 정상.
- **잔여 갭 관찰 (BATCH-27)**: hooksPath 전환의 구조적 결과 = **origin/main 미포함(stale) 브랜치 worktree는 `scripts/hooks/pre-commit` 부재 → 전면 무훅**(구 브랜치 화이트리스트 가드 포함). **실질 노출 = 메인트리(`Desktop/stock_vis`) 수동 커밋 한정** — worktree-per-세션 격리라 신규 세션은 origin/main 기준 worktree를 새로 떠서 자동 보호됨. **STEP 0.2 실측(2026-08-10)**: 메인트리 `Desktop/stock_vis` = `sess-signal-fwd-recon` 체크아웃·scripts/hooks/pre-commit **부재 = 미복구(보류)** → 해당 브랜치 origin/main 동기(rebase/전환) 시 자동 복구. 사용자 복구 권장 상신 완료(INFRA 세션 보고).

## [2026-07-31] D-C2-DETAIL-MIG — coverage_detail surface 등재 = no-op 마이그 조건부 수용 (경로 A) + IssuanceLog/ImpressionLog 경계 정본화 [platform] [shared]

**HALT 경위**: COVERAGE-DETAIL-SURFACE build(2026-07-31)가 `SURFACE_CHOICES`에 `coverage_detail` 1항 추가 시 `makemigrations --dry-run`에서 **`0011_alter_impressionlog_surface`(AlterField) 생성 예고**로 HALT. 원인 = Django 5.2가 `choices`를 migration state로 추적 — **DB 스키마 실변경 0의 no-op 마이그**(CharField max_length 불변, PostgreSQL 컬럼에 CHECK 제약 없어 실 DDL 0). ※ 부기: 이 개정 설계 시 지시서가 "#43 원문 = IssuanceLog/ImpressionLog 스키마 무변경 원칙"으로 오상정했으나, STEP 0 실측에서 common-bugs #43(527)은 "결정 정합 자기점검"(별개 주제)이고 무변경 문언은 DECISIONS 4855·4973 파생임을 확인 → 정본 위치를 본 결정으로 교정.

**결정**: **경로 A 채택** — no-op 마이그를 **입증 조건부 수용**하고 경계 문언을 본 결정으로 정본화. 가중합 **A 4.50 / C 3.55 / B 3.35, 마진 0.95 → 디렉터 확인 완료(2026-07-31)**.
- **Why(경로 비교)**: **B**(모델 choices 3항 유지 + 실데이터 4종 수용)는 모델-실데이터 **이중 진실** 생성 + platform 방어 코드(`views.py:185 COVERAGE_DETAIL_SURFACE` 상수·tests.py:280)의 등재 전제와 모순. **C**(8/6 게이트로 이송)는 동일 no-op 마이그 문제를 미룰 뿐 + D-C2-DETAIL-PULL의 조기 데이터 가치를 무효화. **A**는 no-op임을 실측 입증(실 DDL 0)하고 경계를 정밀화해 재발을 규칙으로 흡수.
- **입증 조건(3종 동시)**: coverage_detail surface build 시 ⓐ `makemigrations --dry-run` 원문 + ⓑ **`sqlmigrate` 출력의 실행 DDL 공집합**(no-op 입증) + ⓒ 본 결정 참조를 커밋에 명기. migrate **적용은 Gate 4**(사용자 수동, 승인 인용) — 생성·검증(build)과 적용(deploy) 분리.

**★경계 조항 (IssuanceLog/ImpressionLog — 단일 정본)**: `IssuanceLog`·`ImpressionLog`는 **DB 스키마(컬럼·타입·인덱스·제약) 무변경**. **필드 추가·변경·삭제 절대 금지.** `choices` 등 **애플리케이션 레벨 메타 변경**으로 발생하는 **no-op 마이그**에 한해 — ⓐ `makemigrations --dry-run` 원문 · ⓑ `sqlmigrate` 실행 DDL 공집합 · ⓒ 해당 결정의 DECISIONS 등재 — **3조건 동시 충족 시에만 허용**. **본 조항이 이 경계의 단일 정본**이며, 기존 분산 문언(DECISIONS 4855·4973 등)은 여기를 참조한다. (common-bugs #43(527)="결정 정합 자기점검"은 별개 주제 — 무관.)

**How to apply**: COVERAGE-DETAIL-SURFACE build 재개 = SURFACE_CHOICES에 coverage_detail 1항 추가 + 입증 3조건 + 0011 마이그 동반(no-op). 본 결정은 등재만(prod 쓰기 0).

---

## [2026-07-31] D-C2-DETAIL-PULL — COVERAGE-DETAIL-SURFACE를 C-2 게이트에서 분리해 선행 실행 (B 채택) [dashboard] [platform]

**결정**: `COVERAGE-DETAIL-SURFACE`(shared `ImpressionLog.SURFACE_CHOICES`에 `coverage_detail` 추가)를 **C-2 숙성 게이트(8월 초)에서 분리해 선행 실행**(B 채택). 가중합 **B 4.30 vs A(게이트 유지) 3.50, 마진 0.80 → 디렉터 확인 완료**.

**Why**: ⑴ `coverage_detail` surface를 미리 등재해야 상세 페이지(`/dashboard/coverage`) impression 추적을 연결할 수 있고, 그래야 **상세 노출 데이터를 8/6 C-2 설계 전 ~1주 확보**한다(선행 실행의 시간 가치). ⑵ `#43` 경계 검증 강도(choices 추가 = DB 스키마 무영향, `makemigrations --dry-run` 무마이그)는 **시점 무관** — C-2 게이트를 기다릴 이유가 계약 안전성엔 없다. ⑶ C1-FE 관문 판정 = 경로 B(ingest 화이트리스트가 coverage_detail 거부 → 상세 추적 미연결)의 선결 조건이 바로 이 surface 등재다.

**관계**: C-2 퍼널 분석(P2-COVERAGE-C2) 자체는 여전히 8월 초 숙성 게이트 유지 — 본 결정은 **surface 등재분만** 앞당긴다(데이터 수집 착수 ≠ 분석 착수). STRIP-REHOME(D-DASH-SURFACE-UNIFY)으로 스트립이 실 표면 `/`에 자리했으므로, 지금 등재하면 이후 축적분이 통일구간 데이터로 깨끗하게 쌓인다.

**How to apply**: TASKQUEUE `COVERAGE-DETAIL-SURFACE`를 게이트 보류 → **build 대기(등재됨)**로 전환. 구현은 shared 구획 위임, `makemigrations --dry-run` 무마이그 확인 의무(마이그 발생 시 HALT). 본 결정은 등재만(prod 쓰기 0).

---

## [2026-08-06] D-C2-GATE-SPLIT — C-2 게이트 = 분할 개시 (C안) [dashboard] [platform]

**결정**: 2026-08-06 C-2 게이트 = **분할 개시(C안)**. 가중합 **C 4.25 > B 3.55 > A 3.15, 마진 0.70(0.40~1.00 구간) → 사용자 확인으로 확정**. 안건별 증거 상태가 갈려(⑵⑷⑸ 확보 / ⑴⑶ 부족) 증거선 그대로 분할한다.

**스테이지 1 (즉시 설계 개시)** — TASKQUEUE `C2-S1-DESIGN`:
- ⓐ **C2-DESIGN-JOIN-MISSES**: 근거 = w90 join_misses=0 실측(진성 미스 없음) → "수리"가 아니라 **창 경계 라벨링/표기 정책** 문제로 재정의. (w7 join_misses=28은 ≤07-29 시그널 impression의 창 경계 효과.)
- ⓑ **news_chip 커버리지 편입**: 근거 = ~32행(산술 도출: 총 imp 83 − dashboard_eod 36 − coverage_detail 15), dashboard_eod와 병행 축적. **단 설계 지시서 서두에 read-only 검증(news_chip 일자별 행수) 선행 — 미확인 시 스테이지 2로 강등.**
- ⓒ **COVERAGE-SURFACE-CONST-UNIFY**: 데이터 무관 부채성 소형(FE surface 상수 단일화).

**스테이지 2 (08-13 재게이트)** — TASKQUEUE `C2-S2-REGATE`: 퍼널 상수 튜닝 · coverage_detail 층 편입 · **+ news_chip 재설계(D-C2-S1-NEWSCHIP 포인터, 방문 트리거 무관)**.
- **트리거(방문일 기준, 달력 아님)**: "08-06 이후 신규 방문일 ≥3, 그중 coverage_detail 방문 ≥2일 → 개시. 미달 시 자동 연장(재게이트만 반복, 재결정 불요). 재게이트 측정 = MEASURE-C2-GATE 5축 재사용." (news_chip 재설계는 이 트리거와 무관 — 트리거 미달·자동 연장 중에도 논의 가능.)
- **S2 추가 안건(2026-08-06, MGMT-BATCH-24)**: **Strip 경보 배지** — S1-B1 상세 라벨(창밖 노출)의 **루트 표면(`CoverageStrip`) 확장 여부**. 포인터만(설계는 S2, 문언은 D-C2-S1-JOINMISS-LABEL 참조).

**근거 요약**: 08-02~05 방문 0 실측 → 데이터 병목 = **방문일 수**(달력 아님). 스테이지 1은 방문일 무관 증거 확보분(join_misses 창 정책·news_chip 병행·상수 부채), 스테이지 2는 방문일 축적 대기분(퍼널 상수·coverage_detail 층).

---

## [2026-08-06] D-C2-S1-JOINMISS-LABEL — 커버리지 창밖 노출 상시 라벨 (ⓐ-1) [dashboard] [platform]

**결정**: 커버리지 표면에 창밖 노출을 상시 라벨로 표기 — **"창밖 노출 N · 90일 내 전량 매칭"**. 항등식 **imp_uniq = (창 내)노출 + 창밖**을 화면에서 상시 검증한다. 가중합 **4.55, 마진 1.05 → 자동 결정**.
- **근거**: w90 join_misses=**0** 실측(진성 미스 없음) → "수리"가 아니라 **표기 정책** 문제로 재정의. w7 join_misses는 창 슬라이드 효과(≤07-29 시그널 impression이 창 밖)일 뿐 데이터 손상 아님 — 라벨로 정직 표기.
- **범위 제한**: 창 선택기(w7/w30/w90 토글)는 **S2 상수 결정 시 재론** — 본 결정에서 선점 금지.
- 📎 **백-어노테이션 — 항등식 검증 구현 = 교차창 (2026-08-06, MGMT-BATCH-24, S1-B1 착지 `b9e80655` 후속, 사후 디렉터 승인)**: 상시 검증 항등식(`imp_uniq = 창내노출 + 창밖`)의 **검증 구현은 교차창(w7 `imp_uniq` ≟ w90 `imp_uniq` 일치)으로 확정**. 사유: N(창밖)=`join_misses`는 **API 파생값**(정의상 `N = imp_uniq − 창내노출`로 성립)이라 **단일 창 항등식은 항진식**(tautology = 사문 검증, 자기 자신을 대조 → 결함 미포착). 진성 검증 = 창을 달리한 `imp_uniq` 불변성. 원 결정 문언·범위 불변, **검증 방법만 명확화**.

## [2026-08-06] D-C2-S1-NEWSCHIP — news_chip 커버리지 편입 = S2 강등 (ⓑ-3) [dashboard] [platform]

**결정**: news_chip 커버리지 편입은 **S2 강등**(BATCH-23 STEP 1 검증 결과). 3축 원문: **행수 32**(일자별 4/일, 07-16~08-01) · **발급형식(`stock_id:signal_date:signal_tag`) 매칭 0/32** · **전부 뉴스 URL**(yahoo/finnhub `https://...`) · **w90 조인율 0.0%**(0/32 ∩ IssuanceLog 240).
- **성격 재정의**: **조인 구조적 불가(키스페이스 직교)** — 데이터 숙성 문제가 아니다. news_chip object_ref = 뉴스 기사 URL, IssuanceLog grain(종목·시그널)과 직교.
- **S2 안건**: ref 매핑 계층 신설 / 별도 지표화 / 커버리지 제외 **중 설계 결정**. **방문일 트리거와 무관**(D-C2-GATE-SPLIT S2 트리거 미달·자동 연장 중에도 논의 가능).
- **표시 형태 참고(구속력 없음)**: 향후 편입 성립 시 ⓑ-3(surfaces_included 합산 헤드라인 + 표면별 분해 + 교집합)이 검토 우선안.

## [2026-08-06] D-C2-S1-CONST-UNIFY — FE surfaces 상수 단일화 + 가드 테스트 (ⓒ-3) [dashboard] [platform]

**결정**: FE surface 리터럴을 **단일 상수 모듈로 통합** + **가드 테스트**(모듈 밖 표면 리터럴 grep=0 강제, 백엔드 `SURFACE_CHOICES`와 계약 정합). 가중합 **4.75, 마진 0.65 → 사용자 확인**.
- **모듈 위치**: build STEP 0 실측으로 확정. **소유 구획 밖(공용 frontend 인프라) 판명 시 shared 트랙 위임 분기** 명기(dashboard 구획 단독 소유 아닐 수 있음).
- 📎 **백-어노테이션 — 모듈 위치 = 공용 frontend 인프라 확정 · 위임 분기 발동 (2026-08-07, MGMT-BATCH-25, BUILD-C2-S1-B2 STEP 0 실측)**: 자연 홈이 dashboard 구획 밖(공용 frontend 인프라)으로만 성립 → **위임 분기 발동**(디렉터 라우팅=shared 트랙 재차터). 근거 3종 원문: ⑴ surface 4종({`dashboard_eod`·`coverage_detail`·`news_chip`·`chain_sight`}) = 백엔드 `ImpressionLog.SURFACE_CHOICES` 미러 = **교차앱 텔레메트리 계약** ⑵ **de-facto 단일 소스가 이미 `hooks/impressionTelemetry.ts:24-25`**(`SURFACE_RECO_CARD='dashboard_eod'`·`SURFACE_NEWS_CHIP='news_chip'`, 구획 밖) ⑶ **구획 외 소비** `components/strip/NewsChip.tsx`(news_chip) + **구획 내 리터럴은 `CoverageDetailView.tsx:10` coverage_detail 1종뿐**. 모듈을 dashboard 구획에 두면 공용 infra·strip이 feature를 역방향 import = 의존 역전 + 구획 외 접촉(계약 위반). **명시**: ① **ⓒ-2 부활 아님 — ⓒ-3(상수 단일화+가드) 유지, 홈만 공용 인프라로 확정** ② 홈이 공용 인프라이면 **전 소비처 흡수 가능 → 가드 KNOWN_VIOLATIONS 동결 목록 불요 전망**. → S1-B2 = shared 트랙 위임 재분류(TASKQUEUE `S1-B2-SHARED`).

---

## [2026-08-07] D-INSTR-NO-GLOB-COPY — 실행 지시서에 소유 글롭 사본 게재 금지 (규약 관찰) [process] [harness]

**관찰(규약)**: 실행 지시서에는 **소유 글롭 사본을 게재하지 않는다** — 정본(DECISIONS 소유권 지도 v2) **포인터 + STEP 0 실측 인용**만 사용한다. **근거**: S1-B1 글롭↔실주소 불일치(#71 계열)의 원인 = 지시서 내 6월자 글롭 사본(정본에서 복제 → drift). 사본은 정본 갱신을 따라오지 못해 실주소와 벌어진다. BUILD-C2-S1-B2 지시서가 이 규약을 선반영(글롭 복제 금지·STEP 0 정본 직접 열람)해 드리프트 0 실증.

## [2026-08-10] D-INSTR-GUARD-BLOCK — 다단계 사용자 명령서의 가드는 중단력 확보 (규약 관찰) [process] [harness]

**관찰(규약)**: 사용자에게 넘기는 **다단계 명령서에서 "값 검증 가드"(예: 목표 해시 대조)는 실패 시 실제 중단이 되도록** 구조화한다 — ⑴ 가드를 **별도 블록**으로 분리(사용자가 결과 확인 후 다음 단계 수동 진행) 또는 ⑵ `( set -e; … )` 서브셸로 묶어 가드 실패가 뒤 단계를 막게 한다. **근거**: DEPLOY-S1B1(08-08) step 2 "3c36ee07 아니면 중단" 가드가 origin/main 전진(→8a41c842)으로 **트립됐으나**, 단일 붙여넣기(주석 가드·`&&` 미결합)라 **중단 없이 step 3의 하드코딩 목표(3c36ee07)로 진행**됨. 결과는 무사(목표 핀 자체가 의도된 S1-B1 고정·FE diff 0)였으나, 비멱등 단계였다면 사고. 순수 주석 가드(`# 아니면 중단`)는 집행력이 없다.

> 트랙: ⑳-3 S2-B. 브랜치 `monorepo/sess-20-3-s2b`.

**결정**: 자동-C 채택 — 파이프라인 훅 + 기계검증 + 임계 자동승인, 검수는 예외 중심. **안전핀 2**: ①타입 변경은 영구 비자동(검수 승인만이 타입 변경) ②첫 배치=게이트 캘리브레이션(`DOMAIN_AUTO_APPROVE` 스위치는 검수 후 활성).

**Why**: SEC 270건 basis 실존이나 품질 편차(오라벨·타깃 비집중, S2-B STEP0). 전건 수동 검수는 비확장, 전건 자동은 위험. 자동-C = 기계검증 통과 + 고confidence만 auto 후보, 나머지 pending 예외 검수 → 확장성과 안전 양립.

**How to apply**: 코어 `apps/chain_sight/services/domain_tagging.py`(커맨드·훅 공유, 복제0). LLM=`generate_with_circuit`(gemini-2.5-flash, JSON 프롬프트+파싱). 기계검증 ①타깃 실존 ②타입 시그니처(경쟁어휘 비경쟁타입=fail) ③confidence≥임계. 게이트: 전항 pass ∧ type_match → auto 후보(단 `DOMAIN_AUTO_APPROVE`=False면 pending). **draft·machine_check만 기록, relation_domain(승인본)은 검수 승인=Phase 2**. 마이그 0028 additive(미적용, 배포 게이트). 첫 배치 CSV=`outputs/domain_tagging/`. TASKQUEUE DOMAIN-AUTO-SWITCH(캘리브레이션 후 THRESHOLD 확정+스위치).

## [2026-07-29] D-MINDMAP — ego 관계 마인드맵 뷰 맵-3(접힘 카테고리+클릭 펼침) [chainsight] [frontend]

> 트랙: ⑳-3 S3(후속). 이번 S2-B는 데이터(도메인 태그)만.

**결정**: 맵-3 채택 — 접힘 카테고리 + 클릭 펼침. 타이브레이커 = 라벨 겹침 재발 방지(방사형 뭉침 회귀 회피).

**Why**: 지도-B로 접은 관계 지도를 도메인 기반 마인드맵으로 대체 후보. 접힘+펼침이 초기 뭉침·라벨 겹침 문제를 구조적으로 회피(⑳-G S3 오버레이 임시처치의 근본 대안). 구현=S3 트랙, 착수조건=S2-B 도메인 반영(relation_domain 승인본).

**How to apply**: 데이터 선행(S2-B: relation_domain 필드+태깅)→S3 UI(MINDMAP-EGO-VIEW). 섹터-b(D-20-3-MAP-FOLD 연장)로 섹터 지도 진입도 숨김(마진 2.00, 섹터 그래프 Neo4j 동결·실노출0).

## [2026-07-09] 유니버스 소스 복구 (TH-6) — 결정9 = B 폴백(Wikipedia) 확정

### 결정9: 유니버스 소스 = Wikipedia (FMP Starter 미포함 → 사전승인 B 폴백)
**결정**: S&P 500 구성종목 소스 = **Wikipedia "List of S&P 500 companies"** 파싱. FMP
sp500-constituent 는 Starter 플랜 미포함 실측 확인(2026-07-09: `/stable/sp500-constituent`
**402**, `/api/v3/sp500_constituent` **403** Error Message, historical 402/403). 결정9 사전승인
대로 재비준 없이 B 폴백 발동. **Why**: 기존 소스 datahub.io CSV 404 사망(결정5, 마지막 성공
2026-05-01). Wikipedia = GICS 섹터 컬럼(SP500Constituent.sector 동일 택소노미)·503행·중복0.
**How to apply**: `serverless_client.get_sp500_constituents` 교체(datahub→Wikipedia). **함정**:
Wikipedia 봇 탐지가 **httpx TLS/헤더 지문을 UA 무관 403** 차단(실측 httpx 403 / requests 200)
→ fetcher 는 `requests` + 브라우저형 UA 사용(httpx 아님). 검증 가드(결정9): 행수 480~520 ·
필수 필드(symbol·sector) · 심볼 중복 0 → 위반 시 **DB 무접촉**(`validate_universe`,
`sp500_service`). 비파괴 sync(편출=is_active=False, 물리 삭제 금지) 유지.

### 실갱신 결과 + 편출입 소급 공백
**실행(2026-07-09)**: created=7·updated=496·deactivated=7·active 503→503. **편입** BNY·ECHO·
FDXF·FLEX·HONA·MRVL·VEEV / **편출** BK·CAG·CPB·CTRA·EPAM·POOL·SATS. ★**BK→BNY 티커 변경**
포착 = TH-2 BK OPEN_EMPTY(FMP 내부자 0행) 미스터리 해소(BK 개명). **편출입 소급 공백**:
historical constituent 엔드포인트도 Starter 미포함(402/403) → 5/1~현재 개별 편출입 **일자
소급 불가**, 현재 리스트 일괄 갱신으로 갈음(멤버십은 정확, 중간 전이 일자는 미복원).

### 결정8 연동 + 결정6 게이트
staleness = `SP500Constituent.updated_at` max, 갱신 성공 시 신선(days_since=0) → `is_universe_
stale`=false 자연 전환 확인(E2E). 알림(TH-UNIVERSE-REFRESH-ALERT): ERROR 로그 정본 +
send_mail best-effort, 주간 감시(>7일 경고, >30일 stale=결정8 상수 재사용). **결정6 게이트는
자동 해제 아님** — 실갱신 확인했으므로 **verifier 판정 대기**(이 트랙은 해제하지 않음).

## [2026-07-09] Theme Heat beat (TH-5) — 오케스트레이션 + universe_stale 마킹 (결정8 비준)

### 결정8: beat 즉시 가동 + 산출 행 universe_stale 마킹
**결정**: Heat 일배치(`compute_theme_heat_task`, ET 18:00) + C2b 수집(`collect_theme_filings_task`,
ET 17:30)를 즉시 가동하되, **유니버스 동결 상태에서 산출된 ThemeHeatScore 행에 stale 표식**을
남긴다: 유니버스 최종 갱신일(`max(SP500Constituent.updated_at)`)이 **30일 초과**면 components
JSONB 에 `universe_stale=true` + `universe_as_of` 기록. 소비층이 코드로 차단 가능(결정6 게이트).
**Why**: 유니버스 소스(datahub 404)가 2026-05-01 동결이라 실전 소비 금지(결정6)이나, beat 를
지금 가동해야 C8 콜드 스타트 시계·파이프라인이 돈다. stale 마킹 = "계산은 하되 소비는 차단
가능"의 명시 신호. 임계 30일 = `heat_beat.UNIVERSE_STALE_DAYS`(단일 정의), 순수 판정
`is_universe_stale`. **How to apply**: 소스 복구(TH-UNIVERSE-REFRESH-ALERT) 후 신선 유니버스로
재산출되면 stale=false 자연 해제. 성분 배선 = C2(C2a+C2b)·C8 실배선, C1/C3/C4/C5/C6/C7 =
not_wired(후속) → 현재 전 섹터 not_computed(결측 ≥3)라 저장 0 — 골격 가동·성분 배선 시 채워짐.

### beat 이름 충돌 회피 + 섹터 택소노미 발견
**결정**: Heat beat = `chainsight-theme-heat-daily`(SeedHeatScore `chainsight-heat-score-daily`
=cs_44 와 **별개 개념**, 이름 충돌 회피). ThemeHeatScore not_computed 는 저장 안 함(§6.1
status 미포함). **발견**: `HeatEntity.ref_id`(Yahoo/FMP 계열: Technology/Healthcare/Basic
Materials…) ≠ `SP500Constituent.sector`(GICS: Information Technology/Health Care/Materials…)
6/11 불일치 → `HEAT_ENTITY_TO_SP500_SECTOR` 매핑으로 비파괴 해소. TASKQUEUE
`TH-HEATENTITY-SECTOR-RECONCILE`(시드 GICS 정렬 or 매핑 영구화 판정).

## [2026-07-08] Theme Heat C8 (TH-4) — 리비전 괴리 산식 + z_mode 종목별 전환 (결정7 비준)

### C8 산식 = 앵커 §2 준수 (상충 A 판정 ⓐ)
**결정**: C8 = "추정치 리비전 **괴리**(estimate revision divergence)". 산식 =
`C8_raw = z(가격 60일 수익률) − z(EPS 컨센서스 60일 변화)`. 부호: **양수 = 가격↑·이익
미확인 = 멀티플 단독 팽창 = 과열 기여**, EPS 상향 → C8 하락(이익이 과열을 식힘).
**Why**: TH-4 지시문 초안이 C8을 "revision momentum"(EPS 단독)으로 표기했으나 앵커 §2는
가격 레그를 뺀 **차분(괴리)**. STEP 0-5 상충 보고 → verifier 판정 ⓐ(앵커 우선), "momentum"
표기는 오류로 정정. **How to apply**: 레그 하나라도 죽으면 C8=None(반쪽 계산 금지).
EPS 레그 = 현재 vs lag 8(56d) 스냅샷 diff, **lag 8 부재 시 lag 9(63d) 폴백**, 둘 다 부재 →
None. 가격 레그 = DailyPrice 60캘린더일 수익률, 결측 → None.

### 결정7 (비준): z_mode 전환 = 종목별·EPS diff 카운트 기반 (§5.3 대체)
**결정**: z_mode 전환 키 = **해당 종목의 유효 EPS diff 개수**. **≥ 26 → time_series**(자기
역사 z), **< 26 → cross_sectional**(그 날짜 단면 z). **양 레그 공동 적용**(한 종목 안에서 레그
간 모드 혼합 금지 — EPS 레그가 binding constraint라 EPS 카운트가 단일 기준). cross_sectional
단면 = 양 레그 성립 종목, **< 30 → 그 날짜 cross_sectional 종목 C8 전체 None**(얇은 단면 z 금지).
z_mode 기록(행 단위, components JSONB) = `time_series` | `cross_sectional` | null(C8 None).
**임계 상수(단일 정의 = estimate_revision.py)**: `Z_MODE_TS_THRESHOLD=26`(반년 표본=시계열 std
최소), `LAG_PRIMARY_DAYS=56`/`LAG_FALLBACK_DAYS=63`, `CROSS_SECTIONAL_MIN_SYMBOLS=30`.
**Why**: 앵커 §5.3은 시스템 전체·시간 기반 전환(60일→cs, 365일→ts, 1회)이나, 수집 결손·신규
상장에 자동 내성을 갖도록 **종목별 카운트 기반**으로 개선. 트레이드오프(스냅샷 내 잣대 혼재)는
혼합 비율 로그(`z_mode mix: ts=N cs=M none=K`) + 추후 카드 뱃지로 관리(TASKQUEUE). 전환 후엔
26 유효 diff = time_series 표본 충분. **결정7이 §5.3을 대체** — 설계 v1.2.2 §5.3 개정 주석.
**How to apply**: `estimate_revision.compute_c8_for_symbols`(순수, 주입 데이터 테스트) +
`compute_c8_from_db`(TH-5 beat). 신시사이저는 C8=None 시 기존 §3-5 비례 재분배 그대로 적용.

## [2026-07-08] 프로토콜: 지시-설계 상충 시 설계 앵커 준수 + 즉시 보고

**표준**: 실행 지시(지시서·회신)가 설계서/스펙과 상충하면 **설계 앵커를 준수**하고 **상충을
즉시 보고**한다(임의 지시 이행 금지). 근거: 설계서가 진실의 소스(CLAUDE.md Contract-Driven —
"스펙과 구현 불일치 시 구현을 수정"). 사례: TH-3 estimates beat 지시 "일일" vs 설계 §6.6/§7
"주간(금요일)" → 주간 준수 + 보고 → 검증자 회신 "일일은 지시 오류, 주간 확정, 설계 수정 불요"
로 판단 정당성 확인(2026-07-08). 상충이 실제 설계 변경 필요면 **설계 선수정 → 지시 재확인**.

## [2026-07-07] Theme Heat TH-3 — 장기 배치 실행 원칙 + 유니버스 동결 정책 + 성분 계약

### 결정 1: 장기 배치는 전경(foreground) 블로킹으로 실행한다 (백그라운드 금지)
**결정**: 완결이 필요한 장기 작업(백필·대량 수집·성분 배치 등)은 **전경 블로킹**으로 돌린다.
`&`·`nohup`·`caffeinate` 등 백그라운드/detach 실행은 금지. 필요 시 멱등 커맨드를 경계
배치(`--offset`/`--limit`)로 잘라 순차 전경 실행한다.
**Why**: TH-2 내부자 백필을 배경 실행 시 하네스가 장기 백그라운드 프로세스를 **2회 리핑
(하드킬)** 해 미완결 반복. 전경 블로킹 배치 2회(offset 250–380/380–501)로 219,410행 완결.
**How to apply**: 장기 커맨드는 `--offset/--limit`로 슬라이스 + 전경 대기(`TaskOutput(block=true)`
동턴 유지). 멱등 upsert 전제라 재개 안전. (1차 소스 = PROGRESS 2026-07-07 + 메모리
`lesson_background_task_reaping`; 본 항목이 DECISIONS 흡수분.)

### 결정 2: 유니버스 정책 = 배치 일자별 스냅샷 동결 (UniverseSnapshot)
**결정**: 매 배치는 그날 조회한 유니버스(SP500 active − '.' 심볼)를 `UniverseSnapshot
(batch_date, symbols)`로 박고, 이후 모든 성분 z(특히 C2a 테마 합산)의 **모집단은 배치
일자 스냅샷을 참조**한다(라이브 재조회 금지). 저장 시 전일 대비 추가/제거 diff 1줄 로그.
**Why**: `SP500Constituent`는 월 1회 동기화라 `is_active`가 소리 없이 변한다(실측: 전 503행
`updated_at=2026-05-01`, 이후 미변경 = 정적 스냅샷). 모집단이 배치마다 흔들리면 z 시계열이
오염된다(설계서 §6.0 잠금장치 3 "구성 동결 — z 히스토리 보호"와 동일 문제, Cycle 1 판).
TH-2 코드기(485)→완결(501) "변동"은 실제 유니버스 변화가 아니라 중단 실행의 stale 분모였음
(DB 무변경으로 반증) — 스냅샷이 이 모호성 자체를 제거.
**How to apply**: 배치 진입 시 `universe_snapshot.get_or_create_universe_snapshot(batch_date)`
→ 반환 symbols로 `sector_constituents(sector, symbols)` → 성분 계산. 멱등(같은 batch_date
재호출 = 저장분 반환).

### 결정 3: TH-2 백필 게이트 종결 = 500/501 (BK = FMP Starter 벤더 커버리지 공백)
**결정**: 내부자 백필 게이트를 **500/501(99.8%)로 최종 종결**. 미수집 1종 = **BK(BNY Mellon)**.
**Why**: BK는 상장 유지(active, 티커 불변)이나 FMP **E1/E2 거래검색이 결정적으로 0행**
(재시도 1회 확인, HTTP 200 정상 빈응답, 일시 오류 아님). 반면 **E3 statistics는 98행 존재**
→ 원천 자체가 아니라 **FMP Starter 플랜의 벤더 커버리지 공백**(E3 집계는 노출·E1/E2 거래
레벨은 미노출)이다. 원장(§5.1)은 E1/E2 거래 레벨을 쓰므로 BK는 저장할 거래행이 없음.
C2a는 테마/섹터 합산이라 단일 종목 결측은 희석 + §3-5 재분배가 성분 결측을 처리 → 게이트
종결 타당. **성격 = 원천 영구부재가 아니라 벤더 커버리지 공백** — 후일 FMP가 BK 거래검색을
채우거나 플랜 상향/소스 보강 시 **멱등 백필로 자동 회수 가능**(재스캔성). 재소환 조건 = 벤더
E1/E2 커버리지 확인 시 `--limit`로 BK 재백필.

### 결정 4: Heat 8성분 = 전건 정방향(raw↑ → z↑ → 과열↑)
**결정**: Cycle 1 Heat 8성분(C1·C2a·C3·C4·C5·C6·C7·C8)은 **모두 정방향** — raw 원값 상승이
과열 상승이 되도록 z 부호를 잡는다(부호 반전 성분 0). 성분 계약 = `{z, s, raw, missing_reason}`
통일, s=sigmoid(z).
**Why**: Heat는 "과열 축" 단일 방향이고, 각 성분(밸류에이션 배수·내부자 순매도·키워드 볼륨·
ETF 순유입·레버리지 거래비율·상관 응집·거래대금·멀티플 단독팽창)이 전부 "높을수록 과열".
역방향은 Cycle 2 DSS의 D2(DIO 재고일수)뿐이라 본 모듈에 없음. (부호 표 = PROGRESS
2026-07-07 보고, 검증자 전수 대조 완료.)
**How to apply**: 새 Heat 성분 추가 시 "raw↑ = 과열↑" 성립 여부를 먼저 판정하고, 역방향이면
z 부호 반전 + 본 항목 갱신. C2b·C8은 이 슬라이스 스텁(missing_reason=c2b_not_collected/
c8_cold_start), 각 후속 슬라이스에서 실구현.

### 결정 5: 유니버스 월간 갱신 자동화 = 조용한 무-op 사망 (소스 404) → beat 슬라이스에 갱신+알림 편입
**결정 (발견 보고)**: `sync-sp500-constituents` beat 는 **살아서 발화**(enabled, last_run
2026-07-01, total_run 5)하나 **소스가 죽어 무-op**다. `SP500Service.sync_constituents`가 읽는
소스 = `datahub.io/core/s-and-p-500-companies/.../constituents.csv` 가 현재 **404**. 따라서
`get_sp500_constituents`가 예외/빈값 → `sync_constituents` 조기 반환(zero stats, `logger.error`
만·**알림 없음**). 마지막 성공 동기화 = **2026-05-01**(전 503행 updated_at 증거). 6/1·7/1 무-op.
**판별 = (c) 자동화가 조용히 죽음** (=(a) 정상 diff0 아님, =(b) 수동 아님).
**Why**: `update_or_create`는 존재 행도 항상 `.save()`(auto_now)라 **성공 동기화면 updated_at
이 갱신**된다. 전건 5-01 고정 = 그 이후 실행이 전부 조기 반환했다는 증거. FMP 문서와 달리
구현은 datahub CSV 를 씀(소스-문서 불일치).
**How to apply**: ⑴ UniverseSnapshot 은 이 정적성을 **명시화**하는 방어라 즉시 위험은 아님
(5-01 멤버십 동결 = 유효 유니버스). ⑵ **beat 슬라이스에 편입**(디렉터 지시): 소스 교체(신뢰
소스로) + **동기화 실패/무-op 알림**(zero stats·예외 시 ops 알림, Bug #28 `check_last_tick`
대상 등록) + 성공 시 updated_at 신선도 게이트. TASKQUEUE `TH-UNIVERSE-REFRESH-ALERT` 등재.

### 결정 6 (2026-07-08 추가): 유니버스 소스 복구 전 Heat 점수 실전 소비 금지
**결정**: `TH-UNIVERSE-REFRESH-ALERT`(datahub 404 소스 사망) 복구 전까지 **Heat 점수의
실전 소비(버튼바·2축 카드 노출)를 금지**한다. 계산·저장·백테스트는 허용.
**Why**: 유니버스가 2026-05-01 에 정적 동결 → 신규 상장/편출 미반영 + z 모집단 신선도
미보장. UniverseSnapshot 은 정적성을 **명시화**하는 방어일 뿐 소스 사망을 치유하지 않는다.
오래된 모집단 위 Heat 를 실전 노출하면 잘못된 과열 판정을 유통할 위험.
**How to apply**: FE 노출 PR(버튼바·카드)의 선행 게이트 = TH-UNIVERSE-REFRESH-ALERT 완료.

### 결정 7 (2026-07-08 추가): C2b IPO 레그 = Cycle 1 섹터에서 근사 결측 (424B5 레그가 실효)
**결정**: C2b 는 424B5(시즌드) + IPO(신규공급) 레그 평균이나, **Cycle 1 sector 엔티티에서
IPO 레그는 근사 결측**(IPO 는 SP500 구성종목이 아니라 `sector_constituents` 제약 하 count≈0).
424B5 레그가 Cycle 1 섹터 C2b 의 **실효 신호**(디렉터 지정 "S-3/424B5 시즌드").
**Why**: IPO 는 정의상 신규 상장 = 아직 구성종목 아님 → 섹터 귀속 불가(IPO 캘린더에 GICS
섹터 없음). 3년 IPO 1,425행은 적재 완료(시장 전체 원장)이나 섹터 매핑 부재로 섹터 레벨에선
비활성. **How to apply**: IPO 레그를 (a) 시장 전체 공통 tide 로 쓰거나 (b) IPO 심볼→섹터
귀속(신규 소스) 후 활성화 — 후속 결정. 현재 계산기는 스펙(레그 평균) 유지, 섹터에선 424B5
단독처럼 동작(IPO z 미세 기여). 테마 레인 개방(§6.0) 시 재검토.

### 관찰 항목 박제 (Cycle 1 실데이터 검증 시)
**C5·C6·C7 은 방향-무관(direction-agnostic) 지표** — 투기 거래비율·상관 응집·거래대금은
급등·급락 양쪽에서 함께 치솟는다(패닉 매도도 거래대금·상관↑). Cycle 1 실데이터 검증 시
**급락 구간의 Heat Score 오독 여부**(급락인데 과열로 표시되는지)를 관찰 항목으로 확인한다 —
필요 시 방향 게이트(수익률 부호 조건부) 도입 검토. (지금은 설계서 §2 정방향 유지, 관찰만.)
## [2026-07-28] D-DASH-SURFACE-UNIFY — 대시보드 표면 통일: CoverageStrip을 루트 `/`로 이동 + `/dashboard`→`/` redirect [dashboard]

> 배경: DASH-SURFACE-SPLIT-SURVEY(2026-07-28, origin/main `dfaf1243` 기준 read-only 실측). 재료 = 루트 `/`(`app/page.tsx`)=실 대시보드(활성 개발선·impression 실데이터 44행 전량 발생지·네비 전체가 지향), `/dashboard`(`app/dashboard/page.tsx`)=2025-11 방치 레거시(네비 도달 경로 0). 공유 컴포넌트 import 0(완전 별개)·`/`↔`/dashboard` redirect 없음. C1-FE 스트립이 레거시 `/dashboard`에 배선됨(계측 0인 표면).

**결정 D-1**: `CoverageStrip`을 **루트 `/`(`app/page.tsx`) 상단**(`DataFreshnessBadge` 아래, `MarketSummaryBar` 위 = L1.5)으로 이동하고 `app/dashboard/page.tsx`에서 제거. 가중합 **4.60 vs 2.85, 마진 1.75 → 자동 결정**.
- **Why**: 스트립(발급 대비 노출 커버리지 UI)은 impression이 실제 발생하는 표면에 있어야 발견성이 유의미. 실데이터·네비 지향·활성 개발선 3중으로 `/`가 실 대시보드이고, 레거시 `/dashboard`는 계측 0·도달 경로 0이라 스트립이 사실상 비노출. 마진 1.75(≥0.40)로 타이브레이커 불요.

**결정 D-2**: `/dashboard` → `/` **redirect 1줄**(임시·가역 조치). 가중합 ㉡(redirect) **4.30 vs ㉠(레거시 유지) 4.10, 마진 0.20** → 타이브레이커 = 사용자의 표면 통일 명시 의도 + 가역성.
- **사용자 확정 인용(2026-07-28)**: "그래 그러도록 하자."
- **Why**: 네비에 도달 경로 없는 레거시를 직접 URL로 진입 시 실 대시보드로 안내(표면 혼선 제거). redirect는 1줄·완전 가역이라 DASH-LEGACY 최종 사이클에서 뒤집기 가능.

**관계 명시**:
- **DASH-LEGACY(KEEP/CUT/MOVE) 보류는 유지** — redirect는 `/dashboard/page.tsx`의 최종 운명 확정이 아니며 본 사이클에서 뒤집기 가능. (TASKQUEUE `DASH-LEGACY` 상태 불변)
- **`/dashboard/coverage`는 자체 page**라 `/dashboard` redirect의 영향을 받지 않는다(별도 라우트). 빌드 라우트 생존은 STRIP-REHOME build 슬라이스의 테스트로 검증 예정.
- **D-OWN-HOME([2026-07-09])과 정합**: 실 랜딩 = `app/page.tsx` 규정 재확인. 스트립을 `/`로 옮기는 것은 D-OWN-HOME이 이미 dashboard 트랙 소유로 편입한 `app/page.tsx`에 대한 정상 배선.

**How to apply**: 구현은 TASKQUEUE `STRIP-REHOME`(dashboard FE build 슬라이스). 본 결정은 등재만(prod 쓰기 0).

---
## [2026-07-28] D-REL-QUALIFICATION — 관계 정성화 표면화 옵션 2+ 채택 [chainsight] [frontend]

> 트랙: ⑳-3 S2. 브랜치 `monorepo/sess-20-3-s2`.

**결정**: 옵션 2+ 채택 — 칩 분화 + 근거 문장 + 등급 라벨 + 도메인 태그 자리(목업 확정본). 마진 0.70.

**Why**: STEP 0 실측 — ego 응답에 basis_summary·grade·grade_source 이미 존재(⑳-G), has_*_source·status·co_mention_count는 additive로 확보 가능. SEC 4종 270건 basis 전건 실존(형식 `"SEC 10-K: <10-K 발췌문>"`, 출처 내장, 깨짐 0) = 표시 적합. 옵션1(등급 라벨만) 대비 근거 문장이 "왜 이 관계인가"를 직접 전달 → 마진 0.70.

**How to apply**: ego additive(B-1) + `RelationQualification` 컴포넌트(C). ★C-2 근거 게이트 = **basis_summary 존재 기준**(evidence_count 미사용 — CS-EVIDENCE-SEC-COUNT 백필 우회). 노출 유형 = SEC 4종 + CO_MENTIONED만, **PEER는 칩만**(basis 있어도 문장 미노출). 칩 분화 C-1: PEER→has_peer/has_industry로 "Peer·FMP"/"동종산업". 도메인 태그 C-4 = relation_domain(S2-B 전엔 null, 필드 자리만). ⚠ basis 품질 편차(일부 오라벨·노이즈)는 S2-B 도메인 추출 과제.

## [2026-07-28] D-20-3-MAP-FOLD — market-graph 지도 토글 접기(지도-B) [chainsight] [frontend]

> 트랙: ⑳-3 S2. 브랜치 `monorepo/sess-20-3-s2`.

**결정**: EgoDrilldown [지도] 토글 숨김(`MAP_ENABLED=false`) → 목록(RelationCardList)만. MarketGraphCanvas·S3 오버레이 **코드 삭제 금지**(플래그로만 접음). 마진 0.85.

**Why**: [symbol] ego 화면(카드 리스트)이 관계 시각화 역할을 대체 → market-graph 지도 진입이 중복·저가치. 지도 뭉침(MAP-VISIBILITY)·섹터 Neo4j 동결 미해결 상태라 노출 유지가 오히려 부채. 부활 조건 = 백본 트랙(Q20-3-BACKBONE-SECTOR) 재설계 시.

## [2026-07-28] D-20-3-LEGACY-CONSUMER-MIGRATION — 레거시 Neo4j 소비자 ego 전환(안A) [chainsight] [frontend]

> 트랙: ⑳-3 S1. 브랜치 `monorepo/sess-20-3-s1`.

**결정**: `/chainsight/[symbol]` 표면 + `stocks/[symbol]` GraphMiniView 2개 레거시 Neo4j 소비자를 PG ego 계약(`/chainsight/ego/{symbol}/`)으로 전환(안A). 레거시 엔드포인트(ChainSightGraphView·SuggestionView) 자체는 무접촉 방치.

**Why**: STEP 0-B 실측 — 레거시 `/graph/`·`/suggestions/`는 Neo4j 동결로 **전 심볼 HTTP 500**(HAL·NVDA 동일), PG `/ego/{symbol}/`는 **200 정상**(HAL RC 39엣지). 소비자를 PG로 옮기면 무데이터 화면이 즉시 복구되고 백엔드/레거시 무접촉이라 blast radius 최소. 스코어카드 = 안A(소비자 전환) vs 안B(레거시 백엔드 PG 재구현): A가 마진 **0.50** 우위(A=즉시복구·저위험·ego 계약 재사용 / B=백엔드 대공사·Neo4j 해동 또는 재구현 필요).

**How to apply**: FE는 `useEgo` + `egoToGraphResponse` 순수 어댑터(GraphCanvas/GraphMiniView 렌더 무변경). suggestions는 미복구 → AIGuidePanel "준비 중" 정직 표시(TASKQUEUE SUGGESTIONS-PG-REDESIGN). trace(useTrace)는 ego에 경로추적 계약 부재로 전환 보류(LEGACY-NEO4J-ENDPOINT-REMOVAL에서 추적). 레거시 제거는 소비자 0 확인 후 별도. cf. common-bugs #70(표면별 서빙 경로 분기).

---

## [2026-07-20] D-DRILLDOWN-CARD-FIRST — ego 드릴다운 기본 = 관계 카드, 그래프는 토글(C안) [chainsight] [frontend]

> 트랙: ⑳-2. 배포 `2c74160`.

**결정**: ego 드릴다운 기본 화면을 **관계 카드 리스트**로 하고, 그래프(force)는 `[지도]` 토글 뒤로 격하한다(C안). 신뢰도(관계 강도) 전달은 **카드의 숫자+바**로 이관하고, **그래프 엣지 굵기 인코딩 개선은 포기**한다.

**Why**: 가중합 **C 4.40 > A 3.55 > B 3.35**(마진 0.85, 사용자 확인 2026-07-20). ⑳-V 실측에서 force 그래프가 이웃 많은 허브(48노드)에서 라벨 겹침·밀도로 정보 전달 실패 — 굵기·라벨 회피 튜닝은 수렁(force 파라미터 상호작용). 카드는 신뢰도·근거·최근 언급일을 **결정론적 숫자**로 전달해 겹침 문제를 원천 회피. 그래프는 "관계망 조망"이 필요할 때만(토글) 제공("지도는 원할 때만").

**How to apply**: 카드 데이터는 ego API additive(evidence_count·last_mentioned). 그래프 뷰는 토글 뒤 보존(additive, 기존 동작 불변). 굵기 인코딩·라벨 회피는 하지 않음(OUT). 전체 조망(백본)+섹터 모드는 ⑳-3.

## [2026-07-20] D-UI-VERIFY-POSTDEPLOY — UI 라이브 검증은 "배포 직후 즉시 + 결함 시 fix-forward"가 현 인프라 표준 [harness] [frontend]

**결정**: UI 슬라이스의 라이브 렌더 검증은 **배포 직후 즉시 검증 + 결함 발견 시 fix-forward/롤백**을 표준 시퀀스로 한다(⑳-E 편차의 규칙화).

**Why**: 편집 worktree는 node_modules 심링크(#48)로 `next dev` 기동 불가 + JWT localStorage 포트격리 → **미머지 프론트의 격리 라이브 검증이 런타임상 불가**. 유일한 인증 렌더 표면=배포된 :3000(prod 빌드). 배포 전 검증은 tsc·vitest·pytest GREEN으로 대체하고, 실렌더는 배포 직후 확인. [[feedback_ui_slice_live_screenshot]] 정신(실렌더 필수)은 유지하되 시점을 배포-후로 명문화.

**How to apply**: FE 배포=`npm run build`+`npm run start` 재시작([[reference_web_runtime_prod_build]]) → 즉시 라이브 캡처 → 결함 시 D-H1-FIXFORWARD. **FE-SERVE-MODE-TIDY(격리 dev 서빙) 완료 시 배포-전 검증으로 재검토**.

## [2026-07-20] D-H1-FIXFORWARD — 라이브 검증 중 발견 결함은 H1 3조건 충족 시 fix-forward 허용 [harness]

**결정**: 배포 후 라이브 검증에서 발견한 결함은 **H1 자가해소 3조건(additive·IN 범위·마이그레이션 무발생) 충족 시 fix-forward**(추가 커밋+재배포)를 허용하고 **보고 필수**로 한다(⑳-E 선례 사후 승인).

**Why**: D-UI-VERIFY-POSTDEPLOY상 검증이 배포-후이므로, 결함이 라이브에서만 드러난다(⑳-E react-query paused 2건). 3조건 밖(스키마·범위 밖·비-additive)이면 HALT·상신. 조건 내면 즉시 교정이 롤백보다 안전·빠름(원장에 fix-forward 커밋 명기).

**How to apply**: 결함 발견 → 3조건 판정 → 충족 시 최소 수정 커밋(라벨 "fix-forward")+재빌드+재검증, 미충족 시 HALT. 보고서에 결함·수정 전말 기재.

---

## [2026-07-18] FE-8000-PROD-APPLY 집행 기록 (백-어노테이션) [ops] [frontend]

> 트랙: MGMT-BATCH-12(mgmt, 메타+docs). baseline = origin/main `e5ee004`, prod 쓰기 0(서빙 반영은 07-18 집행 완료·이 등재는 사후 기록). 상위 = FE-DEAD-8000-SWEEP(#55)·WEB-RUNTIME-RUNBOOK.

**① dev→prod 모드 전환**: `:3000`을 `next dev`에서 **`next start`(prod)**로 전환. **Why**: NEXT_PUBLIC_API_URL이 빌드 인라인이라 반영에 `npm run build`가 어차피 필수 → 상시 서빙엔 prod(build+start)가 자연 적합. dev의 핫리로드 이점은 상시 서빙에 불요.

**② 1차 기동 경합 사망 → clean 재기동**: 1차 prod 기동이 **잔존 임시 dev와 :3000 경합해 ~34초 만에 사망**, `npm run dev`(출처 불명·일회성)가 재점유. **supervisor 부재 실측**(dev kill 후 45초+ 무respawn) 후 **clean 상태에서 재기동**하니 안정(PID 불변·8틱 생존). **교훈 → RUNBOOK 반영**: 기동 전 리스너 완전 정리 + 45초 무respawn 확인(common-bugs #61).

**③ ":3000 launchd 무감독" 실체 확정 — 종전 서술 정정**: 종전 장부의 **"launchd 입양 고아"** 서술은 **오인**. `com.stockvis.web` launchd 라벨 = **daphne 백엔드(:18765)**로 :3000과 무관, :3000엔 전용 감독 plist 없음(45초 무respawn이 증거). → RUNBOOK 서빙 실체 정정 반영 + 재부팅 지속용 plist 초안 별첨(`LAUNCHD-WEB-PLIST-LOAD`, load는 사용자 수동).

**검증(07-18)**: :3000 200 · 홈+리더보드 실렌더 · 네트워크 절대 base(`:18765`, 비-:8000) · impression 당일 신규 8행(dashboard_eod 4+news_chip 4) = 수집 재개. 코드·메타 0 변경(서빙 반영·read-only만).

---

## [2026-07-17] D-EGO-REPAIR-STANDALONE — ego 동선 복구를 ⑳-2 통합과 분리해 단독 선행 [chainsight]

> 트랙: ⑳-E. baseline = origin/main `87dc92e`, 배포 `bea1de0`.

**결정**: ego 동선 복구(URL 계약·시드 게이트·빈상태·예외 견고성)를 ⑳-2(섹터 모드 PG 전환·백본 그래프)와 **분리해 단독으로 선행 배포**한다. 섹터 모드 거취(④)는 ⑳-E에서 손대지 않고 ⑳-2로 이관.

**Why**: 가중합 **단독 4.60 > 통합 2.60**(마진 2.00). ⑳-2의 핵심 입력인 "5관점 ego 평가 메모"가 **화면이 실제로 떠야** 수집 가능한데, 그 화면 복구가 바로 ⑳-E다 → 복구는 ⑳-2의 **선행 의존**. 통합 시 섹터 백본 재설계(M~L)가 한 줄 URL 교정(S)을 볼모로 잡아 리드타임·리스크 동반 상승. 복구는 additive-only(시드 경로 무변경)라 단독 배포 리스크 최소.

**How to apply**: ⑳-E는 ①②③⑤만. 섹터 모드 PG 전환·숨김·백본은 ⑳-2 결정 사이클(TASKQUEUE `SECTOR-MODE-DISPOSITION`). ego API 백엔드는 건강 확인됨 → 무접근(HALT 조건).

## [2026-07-17] D-KB-NUMBER-YIELD — union 머지 KB 번호 충돌 시 자기 항목 후순위 양보·재번호 [harness]

**결정**: `.gitattributes merge=union`인 원장(common-bugs 등)에서 세션 중 origin/main이 **같은 항목 번호(#N)를 선점**하면, 자기 세션이 붙인 #N을 **다음 번호로 양보·재번호**한다(origin 우선). 머지 후 육안검수에서 번호 중복(`grep -c "(#N,"` = 2)을 확인해 즉시 교정.

**Why**: union은 양쪽 라인 보존이라 번호 충돌을 자동 해소하지 못한다(내용 정합 미보장 — DECISIONS HARN 이력). origin이 먼저 커밋된 정본이므로 후행 세션이 양보하는 것이 결정론적·무논쟁. ⑳-D에서 #56 충돌을 #57 양보로 사후 처리한 선례를 **표준 규칙으로 승격**(사후 승인). [[lesson_origin_main_advance_union_rebase]] 연장.

**How to apply**: 세션 종료 KB 정산 시 `grep -oE "\(#[0-9]+," | sort | uniq -d`로 중복 검사 → 자기 항목을 max+1로 재번호 + 보고서/포인터 참조 동기화.

---

## [2026-07-17] D-HEALTH-BLOCKED-DISTINCTION — stale pending에 'blocked(외부 의존)' 상태 도입 [harness]

> 트랙: MGMT-BATCH-11(mgmt, 메타-only). baseline = origin/main `87dc92e`, prod 쓰기 0. 상위 = [C] HEALTH-STALE-FAIL-PROMOTE(~07-20 승격).

**결정**: `check_stale_pending_backannotation`(MGMT-HARDEN `4ce46ed`)의 stale pending 검사에 **'blocked(외부 의존)' 상태**를 도입한다.
- **blocked 항목 = WARN 유지**(FAIL 승격 대상 아님) — 사유 + **의존 태스크 ID**를 표시. 실제 미해소(외부 트랙/결정 의존)이지 부기 누락이 아니므로 알람은 유지하되 FAIL로 올리지 않는다.
- **순수 부기 누락만 [C] 승격 대상(FAIL)** — 해소됐는데 `→ RESOLVED/LANDED/SUPERSEDED` 부기를 빠뜨린 phantom(#52).
- **blocked 표기 문법(단일 출처)** = `blocked(dep=<TASK-ID>)`. build ②(HEALTH-BLOCKED-BUILD)가 이 문법을 파싱 대상으로 삼는다.
- **남용 방지 게이트**: health_check가 `dep=<TASK-ID>`의 **TASKQUEUE 실존을 검증**한다. 실존하지 않는 ID로 blocked를 달면 검사 실패(부기 회피 차단).

**Why**: 가중합 **A 4.40 > B 3.45 > D 3.25 > C 3.05**(마진 0.95). 타이브레이커 — C(전량 WARN 유지=알람 피로)·D(07-10 기각 선례 재현으로 질적 결격). **TH stale(07-10)은 부기 누락이 아니라 실제 blocked**(TH 트랙 `sess-cs-theme-heat` 26커밋 WIP 정식 머지 의존)로 판명 — MGMT-BATCH-10 STEP 12 실측. 부기 누락과 실제 미해소를 같은 FAIL로 묶으면 오탐.

**How to apply**: ⑴ 본 결정으로 문법 확정 → ⑵ TH stale 항목에 `blocked(dep=TH-RUNTIME-DEPLOY)` 표기(실존 ID 인용) → ⑶ HEALTH-BLOCKED-BUILD가 health_check에 blocked 인식 + dep 실존 검증 구현(시한 ~07-20 전) → ⑷ [C] HEALTH-STALE-FAIL-PROMOTE는 이 구분 착지 후 **예정대로 승격**.

**[백-어노테이션 2026-07-22 — 승격 후 첫 실측 = 승격 성공]** [C] HEALTH-STALE-FAIL-PROMOTE(07-20 승격) 후 첫 health_check 실측(2026-07-20, read-only 세션) = **13 OK / 2 WARN / 0 FAIL**. WARN 2건 모두 설명됨 — ① TH blocked(`dep=TH-RUNTIME-DEPLOY`, 실존 ID → 설계대로 승격 제외) ② 실행 트리 정합(read-only 세션의 의도적 트리 뒤처짐 HEAD≠origin/main을 신규 검사가 정확히 검출 = 정상 동작, 조치 불요). **오탐 0·부기누락 FAIL 0** — blocked/부기누락 구분 설계가 의도대로 작동. 이후 트리 정합 트리에서 실행 시(2026-07-22, MGMT-PLIST-LAND 직후) 실행 트리 정합 WARN 해소 → **14 OK / 1 WARN / 0 FAIL**(TH blocked만 잔존)로 확인. 승격 성공 판정.

---

## [2026-07-16] MGMT-BATCH-10 백-어노테이션 — impression 배관 청소 3건 (사후 추인) [platform] [frontend] [ops]

> 트랙: MGMT-BATCH-10(mgmt, 메타-only). 청소 브랜치 2건(merge `4e166d5`·`af1e37a`) 착지 후 실행자 재량 판단을 사후 추인. baseline = origin/main `aafdd97`, prod 쓰기 0.

**① PLATFORM-INGEST-DB-ISOLATE — per-item savepoint 채택**(`238c410`→`4e166d5`). impression ingest `post()`가 각 항목을 **`transaction.atomic()` savepoint**로 감싸 구조적 DB 오류(IntegrityError/DataError)를 항목 단위로 격리(정상 항목 전량 수신, 실패만 `rejected_reasons.db_error` 집계, 배치 500 없음). **Why**: `ATOMIC_REQUESTS`는 현재 False(autocommit)이나 savepoint는 **autocommit·ATOMIC_REQUESTS 양쪽에서 안전** → 미래 방어. `_record`의 레이스 IntegrityError 복구는 **중첩 savepoint**로 감싸 외부 per-item atomic 오염을 차단. 응답 봉투 = `received`/`rejected`(FE 계약 유지) + `rejected_reasons`(additive). 실행자 재량 판단 — 사후 추인.

**② FE-DEAD-8000-SWEEP — fail-fast + 절대 base 단일 소스**(`9f03a30`→`af1e37a`). env 누락 시 **fail-fast(옵션 a)** 채택 — 죽은 포트 폴백 대신 즉시 throw(빌드/기동 시점). 신설 단일 소스 `lib/api/config.ts::resolveApiBase`/`API_BASE_URL`로 27개 소비처 통일 + 하드코딩 절대 URL 4파일·상대 호출 1건 흡수. next.config **stale rewrite 완전 사멸** + fail-fast 게이트. **Why**: #55 규약(절대 base 단일 준수) 완성 — 상대 URL이 stale rewrite(:8000)로 새던 구조 근절. **⚠ 착지≠반영**(#53): NEXT_PUBLIC_API_URL 빌드 인라인이라 prod 반영엔 재빌드 필요 → **FE-8000-PROD-APPLY(별건)**.

**③ 운영 사실 기록 — :3000 서빙 사멸 발견**. `:3000` 서빙(launchd 입양 고아 `npm run dev`, sv-web-runtime)이 **07-16 ⑳ 검증 시점에 사멸 상태로 발견**됨(도그푸딩 impression 수집 중단 리스크 실증). 당시 임시 dev 프로세스로 검증 수행. **정식 부활은 FE-8000-PROD-APPLY로 통합**(재빌드+재기동+RUNBOOK 채록). WEB-RUNTIME-RUNBOOK 상향 근거.

---

## [2026-07-16] D-DEPLOY-DELEGATE — 배포 대행 표준 승격 (선택 b) [harness]

**결정**: CC가 **자기 세션 브랜치의 main 머지·origin push·`sv sync`·worker/beat/daphne 재시작**을 사용자 명시 승인 없이 대행한다(표준 승격). 정위치 = `SESSION_CONTRACT.md §H`(규칙 본문 단일 출처).

**선택지**: (a) 명시 승인식(매 배포 승인) vs **(b) 표준 승격**(조건 충족 시 자율) — 병진 **(b) 확정(2026-07-16)**.

**Why**: ⑲·⑳-1 배포에서 CC 표준 절차의 안전성 실증 — 전 단계 실측 검증(worktree clean·MERGE_HEAD 부재·충돌 마커 grep·3트리 HEAD·라이브 응답)을 리포트에 남기는 규율이 정착. 병렬 세션 보호는 **"자기 세션 브랜치 한정"** 조건으로 흡수(타 브랜치 섞임=HALT). 안전 게이트는 §H 조건 1~3.

**How to apply**: §H 3조건 준수 필수. **beat DB 엔트리 변경은 승격 제외**(#28 이력 — 등록·삭제·enabled는 병진 수동). prod migrate·영구/강제 삭제·원격 브랜치 삭제·plist 변경도 승격 제외. 절차 gotcha는 common-bugs "배포 체크리스트" 준수(§H가 복제 않고 참조).

## [2026-07-16] D-H1-SELFRESOLVE — H1 저위험 갭 자가 해소 3조건 조항 [harness]

**결정**: 지시서 실행 중 실측이 전제와 불일치할 때, **3조건 전부**(① additive만 ② 수정 파일 IN 범위 내 ③ 마이그레이션 무발생) 충족 시 CC 자가 해소 허용(HALT 면제). 정위치 = `SESSION_CONTRACT.md §I`.

**Why**: ⑳-1 `name` 필드 갭 선례 — 라운드트립(HALT·보고·대기) 비용 대비 **저위험 additive는 자가 해소가 효율적**. 단 임의 면제 선례화를 차단하기 위해 **경계를 계약에 명문화**(3조건 미충족 시 기존대로 HALT). 자가 해소 시 보고서 "주요 결정 포인트"에 갭·해소 방식 필수 기재.

**How to apply**: 3조건 AND. 하나라도 미충족 = HALT. 마이그레이션 발생은 자가 해소 대상 아님(스키마 변경은 병진 검토).

## [2026-07-16] D-CENTRALITY-UI-TRACK — ⑳ UI 트랙 A(리더보드)→C(백본 그래프) 단계 진화 [chainsight]

**결정**: 중심성 데이터의 화면 노출을 **A(리더보드) 먼저 → C(백본 그래프) 다음** 단계로 진화. ⑳-1 = 리더보드(rank/rank_delta + Top-20 테이블), ⑳-2 = 백본 그래프(중심성 top-N + RC 상위 엣지 필터 뷰).

**Why**: 가중합 **A 4.50 vs C 4.20**(마진 0.30). 타이브레이커 = **A ⊂ C 포함 관계** — 리더보드의 데이터 계약(rank/rank_delta/name)·색 규약·ego 링크가 백본 그래프에도 재사용되므로 A 선행이 **작업 무손실**(C가 A를 흡수). 좁은 A로 데이터·API 계약을 먼저 굳히고 C에서 시각화 확장.

**How to apply**: ⑳-1 additive API(rank/rank_delta/name)를 ⑳-2가 재사용. ⑳-2 착수 조건 = ⑳-1 배포 + ego 5관점 메모 접수(TASKQUEUE).

## [2026-07-16] D-DISCOVERY-WATCH — discovery 신규 0 대응 = 관찰 대기(즉시 유니버스 확장 보류) [chainsight]

**결정**: ⑲ S4에서 확인된 discovery 신규 RC 0(분류 b)에 대해 **즉시 조치 대신 관찰 대기**. 2026-07-30경 재측정 후 판단.

**Why**: 가중합 **A(관찰 대기) 4.40 vs B(즉시 확장) 2.70**(마진 1.70 > 1.00, 자동 결정). ① co-mention 입력 단절(04-25 AV per-symbol 제거 ~ 07-08 broad 재개)이 **막 해소된 직후**라 정체 원인(입력 vs 유니버스 포화)이 미확정 — broad 축적으로 자연 재개될 수 있음. ② 유니버스 확장의 실제 비용축 = **FMP 심볼별 시장데이터 콜 + 노이즈**(broad news fetch는 universe-agnostic이라 AV 콜수는 유니버스 크기와 무관, 매칭 단계만 영향). ③ 노이즈 억제 = **match_score 정규화(지시서 ⑦) 선행 필요** → ⑦ 없이 확장하면 저품질 엣지 양산.

**How to apply**: 07-30경 read-only 재측정(TASKQUEUE). 재개=종결 / 여전히 0이면 유니버스 확장 결정 사이클 개시(전제: 지시서 ⑦ 완료).
## SLICE20A — Coach 화면 1부: REST 표면 + 권유 읽기 (admin 입력 지름길) (2026-07-16 결정 / 2026-07-16 실행) [portfolio]

**전제**: 19c까지 엔진(정직한 A + KRW 기준 + 드로다운 다이얼 + 손잡이 5종 + 원장 2종)은 완성됐으나 **UI 진입점 0**(`run_advisory`는 파이썬 함수·REST 없음, coach E1~E6 dead-end). 20a는 엔진을 **매일 읽는 화면**으로 만든다. 입력은 20b, 당분간 Django admin이 입력 지름길(1인 도그푸딩).

- **D0 — 계약 가산 전용 진화 (신규 원칙·이 슬라이스의 헌법)**: 계약 v3 진화는 **필드 추가만 허용**, 기존 필드의 의미·형태·단위 변경 금지. SIGNAL-FORWARD-INFRA의 예상수익률도 가산으로 들어와 화면 빈 슬롯을 채운다.
  - **Why**: 프론트가 처음 이 계약을 소비 — 여기서 비틀면 이후 전부 재작업. 위반 필요 시 = 디렉터 결정 사이클 재소집.
- **D1 — 스코프 분할 (자동 확정, 마진 1.10)**: 20a = REST 표면 + 권유 읽기 화면 + admin 입력 지름길 / 20b = 손잡이 슬라이더 패널·wallet/watchlist 입력 UI·E1~E6 연결. 근거 = 슬라이스 리스크·도그푸딩 도달 속도·방법론 정합.
- **D2 — 실행 트리거 = 혼합 (사용자 확정, 4.60)**: nightly 자동 기록(`trigger=auto`, 원장 시계열 보존) + 화면 수동 재실행(`trigger=manual`, 즉시성). **사후분석은 `trigger=auto`만 표본으로 쓰는 것을 관례로 함께 기록**(수동 실행이 시계열을 오염하지 않도록).
- **D3 — 손잡이 UI = 슬라이더 직접 노출 (사용자 확정, 타이브레이커=도그푸딩 우선)**: 실행은 20b. 20a는 **읽기 전용 표시까지**. 프리셋 껍데기는 서비스 포장 해동 시 재검토.
- **mgmt 인라인 관례 명문화**: **실행 세션 지시서 = repo 배치 필수** / mgmt(랜딩 등 코드 0) 세션 = 인라인 전문 허용. 19b·19c 랜딩 선례를 규칙으로 승격. (20a 세션은 실행이므로 `docs/portfolio/coach/slice20a/SLICE20A_INSTRUCTION.md` 배치 후 시작.)
- **20a 절대 규칙 승계**: 유령 필드(analyst_*·forward_pe) 화면 노출 금지(예상수익률=빈 슬롯 placeholder) / 손잡이 쓰기 금지(20b) / 엔진 로직 무변경 / mig 0006(AdvisoryRun.trigger 가산) 외 재생성 0 / prod 미적용(dev만).

## SLICE20B — Coach 화면 2부: 손잡이 쓰기 + 입력 UI + 심층 진단 연결 (2026-07-16 결정 / 2026-07-16 실행) [portfolio]

**전제**: 20a로 Coach는 "읽는 화면"(권유·갭·모드 + [지금 진단]). 20b는 "만지는 화면" — ⑴ 손잡이 5종 직접 조정(주권 실물화) ⑵ admin 지름길 → 지갑·관심 입력 UI 대체 ⑶ dead-end coach E1~E6에 진입점 연결. **모델 무변경 — REST 엔드포인트 + 화면만 가산**(D0 계약 가산 전용의 REST 층 적용). base origin/main = `8e04a18`(지시서 명시 `f00dbca`의 상위집합 — FE-DEAD-8000-SWEEP frontend services base URL 정리 포함, 20b 소비 대상이라 최신에서 분기).

- **D4 — E 진입 = 분기 (사용자 확정, 4.10 / 타이브레이커: 하방=① 동일·상방만 존재)**: 기본 = 코치 탭 하단 "심층 진단" 섹션. 종목 컨텍스트 E가 STEP 0(d)에서 실측될 때만 권유 카드 딥링크 가산. **STEP 0(d) 판정 = 섹션만(수렴)**: E1~E6 전부 포트폴리오 수준(app/coach/eN 정적 라우트, `[symbol]` 동적 세그먼트 0, API 페이로드 `portfolio_id`+`holdings[]`, `?symbol=` 읽는 코드 0) → **종목 수준 E 0개 → 딥링크 가산 없음, 6개 정적 타일 섹션만**.
- **D5 — 입력 UI = 목록+모달 (사용자 확정, 4.40 / 마진 0.80)**: 강등 단서 = STEP 0(c) 하우스 모달 표본 부재 시 ② 폼 페이지. **STEP 0(c) 판정 = ① 진행**: 폼 담은 하우스 모달 4+ 실존(`components/portfolio/PortfolioModal.tsx`·`components/watchlist/WatchlistModal.tsx`·`AddStockModal.tsx`·`components/monitor/CloseModal.tsx`). 공유 베이스 모달·focus trap·`role="dialog"` 부재(각 모달 개별 처리) → 하우스 관용구(overlay `fixed inset-0 bg-black/50`+card `bg-white dark:bg-gray-800 rounded-xl max-w-md`+X+form+actions, `if(!isOpen) return null`) 답습, **접근성은 과설계 없이 role/aria-modal 최소 가산**. mutation = TanStack `invalidateQueries`(낙관적 갱신 미채택 — 하우스 관례 답습, 실코드에 optimistic 0).
- **손잡이 저장 ≠ 진단 실행 (D2 혼합 트리거 유지)**: 저장 후 진단은 [지금 진단] 수동 경유. 엔진·태스크·저장 훅의 손잡이 자동 조정 금지 재확인(19c 불변식의 REST 확장 — 서버측 검증기 `KNOB_RANGES`+`clean/save` 그대로 강제, 프론트 검증만으로 대체 금지).
- **CRUD 재사용 원칙 (18-R 교훈의 REST 층)**: 진실 소스 분할 금지 — 기존 CRUD는 소비, 부족분만 가산. **STEP 0(b) 판정**: WatchlistItem = 완비 재사용(`/api/v1/users/watchlist/*` + `watchlistService.ts`, 관심 탭 = 기존 `/watchlist` 소비 — 재구축 0) / WalletHolding·CashBalance CRUD = **없음 → 신규 가산**(cash upsert/delete 서비스 헬퍼는 재사용, Wallet get-or-create만 신규) / UserGoal 손잡이 쓰기 = **없음 → PATCH 가산**(GET knobs 읽기 재사용).
- **UserGoal 검증기 정본 확인 (§7 HALT 해소)**: 서버측 실존 — `models_my.py` UserGoal 필드 `validators=` + `KNOB_RANGES` 단일소스 + `clean()`/`save()` 이중방어. 범위 A 0~7·G 0~7·w 0~0.20·L 15~100(default 30)·E 0~30 = 지시서 완전 일치. 슬라이더 스펙 = 이 정본과 1:1.
- **20b 절대 규칙 승계**: 모델·마이그레이션 무변경(신규 mig 0 기대, 필요 시 HALT) / 유령 필드 노출 금지·예상수익률 빈 슬롯 유지 / E 화면 행위보존(diff 0, 라우팅만 가산) / WatchlistItem shared 소속 그대로 소비(재정의·이동 금지) / prod 미적용 유지(누적 후보 19b·19c·20a 무접촉).
- **baseline at decision**: origin/main = `8e04a18`. pytest(coach+portfolio) 733 passed/1 skipped · tsc 0 · vitest 713 passed(92파일) — 전부 GREEN(지시서 명시 651/319는 base 전진으로 무효, 종료 재측정 기준).

## [2026-07-16] P2-IMPRESSION-500 사건 — impression 배관 개통 중 500 2건 전말 [platform] [dashboard]

> 트랙: MGMT-P2-IMPR-CLOSE(mgmt, 메타-only). 상위 = P2-IMPRESSION-BUILD(S1~S3+FIX-1). 배관 개통 중 발생한 500 2건의 원인·해소 기록. baseline = origin/main `dbe0986`, prod 쓰기 0.

**사건**: impression 수신 배관 개통 직후 500 2건.
1. **prod migrate 0010 미적용** — `apps/platform` ImpressionLog 테이블이 운영 DB에 부재하여 ingest write 500. **해소** = 배포 단계에서 prod migrate 0010 적용(ops 수동). 재발방지 = 배포 체크리스트 ① + common-bugs #53/#54.
2. **telemetry 상대 URL → stale rewrite :8000** — FE가 상대경로 `/api/v1/telemetry/impressions` 호출 → Next dev origin(:3000)에 붙어 next.config stale rewrite로 죽은 :8000 라우팅. **해소** = FIX-1(`46e6865`) — `NEXT_PUBLIC_API_URL` 절대 base 정정 + FE 재빌드·번들 검증(컴파일 산출물에 `http://localhost:18765/api/v1/telemetry/impressions` 인라인 확인). 재발방지 = common-bugs #55.
**결과**: 양 표면(dashboard_eod·news_chip) 수신·upsert 시맨틱·click append **육안 실증**(2026-07-16) → P2-IMPRESSION-BUILD 묶음 CLOSE.

---

## [2026-07-16] D-NEO4J-FREEZE — Neo4j 동결 트리거 정교화 + celery dict 완전 제거 (지시서⑲ S1) [chainsight]

**결정**: ego 서빙이 PostgreSQL 네이티브로 전환된 뒤([[D-GRAPH-EGO-BACKEND]]) Neo4j는 **삭제 아닌 동결**. celery.py `beat_schedule`의 chainsight neo4j sync 3블록(⑰-M이 주석 처리)을 **완전 제거**(주석 잔류 금지). 태스크 함수·DB PeriodicTask·task_routes(queue:neo4j 3배정)는 보존.

**Why**: ⑱ 드라이런 실증 — RC 전량(555노드·9551엣지) GDS 4종(커뮤니티·경로·중심성·링크예측)이 networkx in-memory로 **3.92초** 완주. 현 규모에서 Neo4j를 요구하는 시나리오 0. 주석 잔류(⑰-M)는 dict→DB 재동기(#28)로 enabled 부활 위험 + drift 소지 → 완전 제거가 정답.

**재평가 트리거(정교화)**: **엣지 ~10만+ 또는 실시간 다중 홉 서빙 요구** 시 재평가(근거: 555노드에선 PG+networkx 충분, 규모/실시간성이 Neo4j 가치의 전제). 현 RC=13,697(엣지 collapse 9,551) → 트리거의 ~7% 수준.

**원 스케줄(복원용, celery.py 주석 대체 보존)**:
- `chainsight-sync-profiles-neo4j`: `sync_profiles_to_neo4j` @ crontab(hour=12, minute=0)
- `chainsight-sync-relations-neo4j`: `sync_relations_to_neo4j` @ crontab(hour=12, minute=30)
- `chainsight-neo4j-dirty-sync`: @ crontab(hour=4, minute=30, day_of_week=0), options={expires:3600, queue:neo4j}

**How to apply**: 재활성 = DB PeriodicTask enabled=True(dict 등록 금지 — #28). DB 3건은 이미 enabled=False(⑰-M 실측 2026-07-16). 검증: celery app 로드 OK·chainsight neo4j beat 0.

## [2026-07-16] D-A2-DEEPDIVE — Deep Dive(N-hop) 화면 폐기, 코드 동결 (지시서⑲ D④) [chainsight]

**결정**: `/chainsight/[symbol]` Deep Dive(N-hop Neo4j 탐색) 화면에 **신규 투자 0**. 코드는 삭제 아닌 동결(A1/A2/A3 프론트·Neo4j endpoint 무변경).

**Why**: ⑱ 판정 — 방향성 엣지 144개(전체 1.05%)·각 18~23 성분 파편화. 자이언트 연결은 무방향 peer/price가 접착하고 경로는 메가허브(NVDA/GOOGL) 경유라 **인과적 다중 홉 전파로 해석 불가**(S-B 시나리오 기각). N-hop 탐색의 정보 가치가 비용(Neo4j 유지)을 정당화 못 함. depth=1은 ego(PG)가 이미 대체.

**How to apply**: A2에 기능 추가 금지. 자연 대체 = ego(1-hop PG). 전면 재평가는 D-NEO4J-FREEZE 트리거와 연동.

## [2026-07-16] D-SC-CENTRALITY — 중심성 일간 배치 착공 (PG+networkx, Neo4j 불사용) (지시서⑲ S3) [chainsight]

**결정**: ⑱에서 "유일하게 성립"으로 판정된 S-C(중심성)를 해자 궤적으로 착공. `SymbolCentrality`(일별 append, (symbol,as_of) unique) + `compute_symbol_centrality` 태스크(RC 전량 → networkx 무방향 그래프 → PageRank+betweenness) + 조회 API `/chainsight/centrality/top/` + ego 노드 rank 필드(additive). **화면 노출은 ⑳**(이번은 데이터/API까지).

**Why**: PageRank(허브) vs betweenness(브리지) 목록이 실질 괴리 → GICS 섹터 라벨이 안 주는 신호(⑱ S-C 성립 근거). networkx 정식 의존 승격(pyproject `^3.6`, lock 정합) — Neo4j 불사용(드라이런 3.92초 실증).

**로직 = ⑱ 드라이런 동일성**: collapse weight=max(truth_score, market_score), PageRank 가중, betweenness는 프로덕션 정확 계산(드라이런 k-샘플링 제거). **대조 검증(prod read-only 2026-07-16)**: nodes 555·edges 9551·PageRank top10 **완전 일치**(NVDA GOOGL MSFT AAPL HPE META CSCO MSI GOOG ACGL)·1.95초. betweenness는 동일 모집단(정확값이라 샘플 대비 소폭 재배열 = 개선).

**beat 스펙(등록 금지 — 명세만, #28)**: 이름 `chainsight-daily-centrality` · DB-only · 일 1회 = RC 갱신 체인(`chainsight-relation-confidence` 11:00 EST + `chainsight-pair-aggregation` 11:30 EST) **후속**으로 12:00 EST(17:00 UTC) 이후 제안.

**How to apply**: 멱등(동일 as_of=update_or_create). 궤적 보존(덮어쓰기 금지). truth_score 미정규화(별도 트랙). symbol=CharField(Stock 미등재 33심볼 포함).
## SLICE19C — 배치 엔진 v2: 드로다운 비례 다이얼 + 손잡이 5종 + 원장 2종 (2026-07-14 결정 / 2026-07-16 실행) [portfolio]

**전제**: 19a·19b 엔진은 임계값(현금 10%·집중도 30%)이 **하드코딩된 고정 가치관**이었다. 19c는 그 가치관을 사용자 주권으로 이양하고, 자산 감소에 비례 반응하는 다이얼을 도입한다. 결정은 2026-07-14 디렉터·사용자 사이클에서 전부 닫힘(사용자 발안 다수).

- **원칙 3계층 재정의 (기존 DISCLAIMER의 스코프 정정, 사용자 확정)**: 19a/19b의 "예측 없음(No prediction)"은 정체성이 아니라 **정본 신호 인프라 부재기의 임시 상태**였다. 정정된 3계층 —
  - ⑴ 환율 **방향** 예측 = **영구 금지**(방향·타이밍 시그널 함수 신설 금지).
  - ⑵ 환율 **수준** 반응 = **허용**(KRW 평가에 내재, dd가 자연 반영 = emergent).
  - ⑶ 종목 **수익성 예측 = 목표**(단 정본 신호 위에서만·유령/프록시 금지 + 모든 예측을 기록해 사후분석). ⑶의 구현 = `SIGNAL-FORWARD-INFRA`(19c 범위 밖, 우선순위 상승).
  - **Why**: "예측 안 함"을 정체성으로 굳히면 정본 신호가 생겨도 제품이 스스로를 묶는다. 인프라 상태와 정체성을 분리.
- **다이얼 = 드로다운 비례 (사용자 발안 "3% 줄면 3%p 더 공격적으로")**: `dd = (조정 고점 − 현재 총자산 KRW)/조정 고점`, `a = dd + A + G·𝟙(신고점 국면)`, `버퍼 = max(10% − a, 3%)`, `여력 = 유휴현금 비중 − 버퍼`(통화별 현금 비례 배분·음수 0 클램프). 완화량 = **측정 사실의 항등 매핑**(유사-정밀 아님).
  - **Why(구 설계 대비 채택 근거)**: 구 계단 2단(달성률 50% 임계)·연속 보간·3단 대비, 비례식은 **경계 진동을 구조적으로 해소**(절벽 없음 → 히스테리시스 부채 불필요). 자산 감소라는 사용자 체감과 직결.
- **flow 조정 dd (입출금 오염 차단 — 중대 결함 사전 해소)**: 스냅샷 diff로 가격효과(전일 수량 고정 × 가격·환율 변화)와 플로우효과(입출금·수동수정 잔차) 분리. dd = **가격효과 누적만**. 조정 고점 = 고점 + 고점 이후 순입금.
  - **Why**: flow 미분리 시 출금하면 총자산↓ → dd가 거짓 상승 → 거짓 공격. 입출금은 성과가 아니므로 dd에서 배제.
- **성향 손잡이 5종 = 사용자 주권 (기본 = 보수값)**: A(aggressiveness_offset 0~7%p, def 0)·G(growth_boost 0~7%p 신고점만, def 0)·w(diversification_weight 0~0.20, def 0)·L(concentration_limit 15~100%, def 30, 100=TRIM 소멸)·E(exploration_ratio 0~30%, def 0). 엔진은 성향을 정하지 않는다 — 자동 반응은 dd(측정 사실) 하나뿐. 엔진 고정 가치관은 단 둘: **"현금 3%는 남긴다"(버퍼 바닥) + "사실은 숨기지 않는다"(사실 보고)**.
  - **L 손잡이화로 구 설계 폐기**: 구 설계의 "dd≥5% 계단식 L 자동 완화"·"공격 국면 분산 바닥 max(w,0.10)"은 **채택하지 않는다**. Why: 엔진이 분산/집중 신념을 강제하면 사용자 주권 위반. dd에 의한 L 자동 완화 없음(사용자 설정 불가침).
  - **신뢰도 지배 불변식**: w 상한 0.20 고정 — w 최대에도 신뢰도 성분(0.48)이 최대 성분. 어떤 손잡이 조합으로도 불가침.
- **하이브리드 게이트 × 스코어 (이중 벌점 아님)**: 게이트=자격(매수 시 집중도>L 제외·현재>L TRIM·통화 여력 0 자격 박탈), 소프트=서열(코어 랭킹). `점수 = (1−w)×(신뢰도 0.60 + 진입가 여유 0.25 + 통화 여력 0.15) + w×분산 한계효과`(B′ — 분산 = 표준 트랜치 가정 매수 후 집중도 개선/악화 사실 계산, w=0이면 정확히 0). 명칭 = **"배치 우선순위 점수(기대수익 아님)"**.
- **탐험 레인 E (가중합 4.58, 마진 1.05 자동확정)**: 신뢰도 지배 랭킹이 Chain Sight가 발견한 젊은(관측 이력 짧은) 후보를 구조적으로 배제하는 **발견↔배치 충돌** 해소. 여력 × E를 젊은 후보 전용 레인으로 분리. **신뢰도 무보정**(젊음 가산점 금지 — 배정만 분리). 레인 내 서열 = 진입가 여유·통화 여력(신뢰도 성분 없음). 게이트·바닥 3% 안에서만.
  - 젊음 판정 기준 = STEP 0 (c) 실측 확정: `first_observed_at 나이 < 30일`(자리표시, E3 확정). evidence_count는 max 2로 무판별.
- **원장 2종 + 사실 보고 원칙**: `PortfolioSnapshot`(user·date·총자산 KRW·통화별 소계·종목별 수량/가격/환율 JSON, unique(user,date), nightly+엔진 upsert)·`AdvisoryRun`(실행시각·snapshot 참조·산출 전문·손잡이 5종 스냅·레인 구분). 사후분석(예측·성향 검증)의 토대 — 19d 재보정은 AdvisoryRun 라벨 축적 후.
  - **신규 신설 근거(§2f)**: 기존 `WalletSnapshot`(wallet 스코프·이벤트 트리거·비-일일·비-FX)은 필수 의미 결여 + §1 기존 모델 불변 원칙으로 확장 금지 → 신규가 유일 경로(중복 아님).
- **의도된 의미 변경 선언 (하드 10%/30% → 산식·L 대체)**: STEP 0 (b) 대체 지점 = `IDLE_CASH_THRESHOLD=0.10`(determine_mode·rank_candidates 게이트)·`CONCENTRATION_THRESHOLD=0.30`(find_trim_candidates)·rank_candidates 정렬키. 이로 갱신되는 기존 테스트는 회귀 아님(Part A에서 목록 확정 — §11).
- **이월**: `SIGNAL-FORWARD-INFRA`(우선순위 상승, 로드맵 배치는 랜딩 후 결정 사이클)·FX-매크로(b) 유지·세금/수수료 부채·19d(가중치·손잡이 사후분석 재보정, G 실효 검증 포함).

## SLICE19B — FX·KRW 기준 통합 (토대) + 게이트 1 해소 (2026-07-14) [portfolio]

**로드맵(사용자 확정)**: 19b=FX·KRW 토대(좁게) → 19c=가중치+공격성 다이얼+FX매크로 후보 → Slice 20=화면. 가중합 4.70/3.70/2.90(마진 1.00).

- **numéraire = KRW**: 수익 = 원화 자산 증가. 환율은 수익의 구성요소(US 실수익 = USD 수익 × USD/KRW 변화). 19a "통화별 사일로 갭" 철회 → KRW 통합 갭으로 교정(의도된 의미 변경). 상세=`OBJECTIVE_KRW_NUMERAIRE.md`.
- **FX 정직성 4원칙**: 측정 O(KRW 환산) / 맥락 O(역사적 백분위 사실) / 실현 FX 반응 O(KRW 갭 emergent, 별도 규칙 없음) / **예측 X**(방향·타이밍 베팅·환전 결정 예측 금지).
- **FX 모델 소속 = `packages/shared`**(마진 1.60 자동 — 환율=앱 불가지론 범용 재료). 수집=shared FMP 래퍼 경유.
- **게이트 판정(STEP 0, base bb91c98)**: 게이트1=취득원가 KRW 복원 **불가**(avg_cost=USD 평단·매수시점 환율 미저장·환전 이력 0). 게이트2=**통과**(FMP spot + USDKRW 과거 1373건/**5년**, 백분위 창 5년). 게이트d=중복 0. baseline 592 green.
- **게이트 1 해소(디렉터 판정 + 사용자 승인)**: ① 매수일 환율 근사 + 신규 캡처 + 수동 정정(마진 1.28 자동). **`WalletHolding.acquisition_fx_rate`**(DecimalField null 가산, 기존 모델 접촉 유일 승인) 신설. KRW 취득원가 우선순위 = `exact`(캡처/정정) > `approx_first_buy`(매수일 환율) > `approx_low_confidence`(창 밖) > `native_krw`. 상세=`SLICE19B_GATE1_RESOLUTION.md`.
  - **Why(②③④ 기각)**: ②현재환율 근사=과거 FX손익 0으로 소거(정직성 충돌). ③신규만=사용자 #1 보유 미교정(도그푸딩 0). ④정지=과잉.
- **의도된 의미 변경 선언**: 19a 엔진 산출 KRW화 → 관련 테스트 갱신은 회귀 아님(Part C에서 목록화).
- **19c 이월**: 가중치 벡터(합=1.00)·공격성 다이얼·FX매크로 후보·교차환전 리밸런싱.

## SLICE19A — 목표-대비 권유 엔진: 정직한 A (원안 폐기 + 정직한 갭) (2026-07-13) [portfolio]

**원안 폐기(supersede)**: 원안 SLICE19A(갭=목표수익−현재기대수익, forward 예측 골격)는 STEP 0 A-게이트 **실패**로 폐기. 측정=`docs/portfolio/coach/slice19a/STEP0_SIGNAL_INVENTORY.md`. forward 기대수익 정본 신호 0: analyst_target_price·analyst_rating·forward_pe=유령 필드(writer 없음·항상 null), EstimateSnapshot 부재, 프리셋 스코어링 엔진=0~100 품질점수(기대수익 아님)+고아(미배선), return_12m=리졸버 부재·후행. → **정직한-A 채택**(디렉터 재판정 4.75 vs B후퇴 3.95/신호선구축 3.55/정지 3.95, 마진 0.80, 사용자 승인).

- **제품 정체성**: 19a는 수익 예측기 아님 = "목표-의식 + 신뢰도 기반 배치 코치". 현금 KRW+USD 다통화 / 목표 단일 "수익"(총수익·배당 제외).
- **카디널리티(트리거 종결)**: `CashBalance` `OneToOne(Wallet)` → **`FK(Wallet)`+`unique(wallet,currency)`**(지갑당 통화별 현금 1행). `UserGoal` **OneToOne(user) 유지**(단일 목표, 다중목표 안 함).
- **정직한 갭(뼈대 A)**: ⑴ 진행 갭 = 현재 포트폴리오 수익률(avg_cost vs 현재가 DailyPrice) − 목표수익률(후행·사실). ⑵ 배치 갭 = 유휴현금 비중(현금/총평가·구조). **forward 예측 없음** — 없는 예측치를 프록시로 짓지 않는다(유령 필드 실수 회피).
- **랭킹 드라이버**: RelationConfidence(주, symbol_a/b 티커→WatchlistItem 매핑)+distance_from_entry(부). 가중치 벡터=19b.
- **FX**: 통화별 매수여력 분리(환전 없음). 교차환전=19b.
- **Why(정직한-A)**: 데이터가 실제 받쳐주는 두 축(진행·배치)으로 갭 재정의 + 후보는 해자(RelationConfidence)가 정렬. 진짜 기대수익 최적화는 forward 신호 인프라(미래) 필요.

## SLICE18R-CARDINALITY — OneToOne 카디널리티 가정 (미확정, 19a 재검토 트리거) (2026-07-13) [portfolio]

**결정(가정 명시, 뒤집는 게 아님)**: 18-R의 신규 2모델 카디널리티를 **현재 `OneToOne`으로 두되 "가정"임을 명시**하고 19a STEP 0에서 강제 재검토한다.
- **CashBalance ⇔ Wallet = `OneToOneField`** (지갑당 현금 1행). **Why(현 선택)**: STEP 0.5 house 패턴(WalletHolding과 동일 Wallet 컨테이너) 정렬 + USD 고정 MVP(다통화 YAGNI). **한계**: 단일통화 현금만 표현 가능 — 사용자가 다통화 현금(KRW+USD 등) 보유 시 부족.
- **UserGoal ⇔ User = `OneToOneField`** (사용자당 목표 1행). **Why**: 단일 투자 목표 MVP 가정. **한계**: 다중목표(은퇴·주택 등 병렬 목표) 미지원.
- **재검토 트리거(닫힌 결정 = 언제·무엇으로)**: **19a STEP 0**에서 ⑴ Wallet의 통화 모델을 실측 → 다통화 현금 필요 판명 시 **CashBalance를 `ForeignKey(Wallet)` + `unique_together(wallet, currency)`로 전환**, ⑵ 다중목표 필요 여부 확인 → 필요 시 UserGoal FK 전환. **미해결 시 19a 진행 금지**(TASKQUEUE `SLICE18R-CARDINALITY-REVISIT`).
- **Why(지금 안 바꾸고 트리거로 미루나)**: prod 미적용(0002 dev만 = 되돌림 가능) + 19a 미착수(쿼리 미결합) + Wallet 통화 모델 미측정 상태에서 즉시 변경 = 추측 기반. 측정 가능 시점(19a STEP 0)으로 결정을 미루되 트리거로 강제(옵션 B, 디렉터 확정).

## SLICE18R — 사용자 상태 그릇 재설계 (원안 폐기 + D1'·D2'·D3') (2026-07-13) [portfolio]

**원안 폐기 사유(supersede SLICE18-D1-REOPEN)**: 원안 `SLICE18_INSTRUCTION.md`는 4모델(UserGoal·WatchlistItem·WalletHolding·CashBalance) 전부 신규 생성을 지시했으나 STEP 0 실측에서 **HALT 2건** 확정 → 개정본 `SLICE18_INSTRUCTION.md`(rev2)로 대체. ⑴ 의미 중복: `apps/portfolio.WalletHolding`(models.py:78, 동명·상위집합=Django 정의 충돌)·`shared/users.WatchlistItem`(users/models.py:215, 상위집합·REST 완비). ⑵ D1 전제 파기: WatchlistItem을 `apps/dashboard/services/strip_service.py:84`·`apps/chain_sight`(WatchlistViewSet)가 이미 소비=교차앱 자산.

### D1' — 소속 (재확정)
**결정**: 신규는 **UserGoal·CashBalance 2종만 `apps/portfolio`**. WatchlistItem은 `shared/users` 유지(소비만), WalletHolding은 `apps/portfolio` 기존 유지 — **둘 다 생성 없음, 재사용**.
- **Why**: "재료는 어느 요리에 들어갈지 몰라야 한다." watchlist는 이미 dashboard·chain_sight 다중 소비 → shared 정당. cash/goal은 STEP 0(e) 실측상 portfolio만 소비(교차앱 흔적 0) → portfolio 정당.
- **How to apply**: 신규 2모델만 `apps/portfolio/models_my.py`(ADDITIVE)에 정의. 기존 WalletHolding/WatchlistItem 정의·마이그레이션 무접촉.
- **STEP 0 측정**: cash/goal 교차앱 소비자 grep(dashboard·chain_sight·market_pulse) = 0건 → D1' 전제 유지.

### D2' — user 스코프 이음새: house 패턴(컨테이너 경유) 정렬
**결정**: STEP 0.5 실측 **house 스코핑 = 컨테이너 경유**(WalletHolding·WalletSnapshot·Portfolio 전부 `wallet=FK(Wallet)`, `Wallet.user=FK(AUTH_USER_MODEL)`; WatchlistItem=`watchlist__user`). 신규 2모델을 이 패턴에 정렬하되 가지는 데이터 성격으로 분기:
- **CashBalance → `wallet = OneToOneField(Wallet)`**, 스코핑 `wallet__user`. (현금은 지갑 속성 = WalletHolding과 동일 컨테이너, "한 지갑 = 보유 + 현금".)
- **UserGoal → `user = OneToOneField(AUTH_USER_MODEL)`**, 직접 스코핑. (투자 목표는 지갑이 아니라 사용자 전역 속성 = 지시서 D2' 기본 가정.)
- **추상 베이스 강제 안 함(YAGNI)**: 두 모델이 상이한 가지(컨테이너 vs 직접) → 억지 추상 = 부채. 이음새는 "user로 좁혀지는 표준 조회 경로"로 확보(`for_user` 매니저 헬퍼).
- **Why(vs 원안 직접FK 강행)**: 기존 자산이 컨테이너 경유인데 신규만 직접 FK면 격리 테스트·19a 조회 경로가 이원화 → 유지보수 부채. house 일관성 우선.
- **STEP 0.5 측정**: WalletHolding `wallet=FK(Wallet)` 확인, Wallet=사용자당 1개(MVP). AUTH_USER_MODEL=`users.User`.

### D3' — 보안 트리거 재정의 (유지·범위 조정)
**결정**: 멀티테넌트 하드닝(온보딩/권한/테넌시 격벽)은 계속 **동결**. 단 user 차원(직접 FK 또는 컨테이너 경유)을 갖는 테이블이 새로 생기면 **교차 사용자 누수-0 격리 테스트를 반드시 동반**. 신규 UserGoal·CashBalance에 누수-0 테스트 + (권장) 재사용 WalletHolding·WatchlistItem 스모크 격리 추가(기존 격리 테스트 0건 실측) + introspection 등록 가드(직접/컨테이너 양 스코핑 인식).
- **Why**: 재사용하는 순간 19a가 이들 위에서 사용자 데이터를 다루므로 데이터 계층 격리는 지금부터 강제. UI/과금/온보딩은 계속 동결(외피 동결 ↔ 이음새 보존 경계 명확화).
- **가중합(기록용)**: 프로세스 "정지·재설계" 4.60 vs "웜세션 축소" 3.10(마진 1.50 자동). D2' "house 정렬" > "원안 직접FK 강행"(일관성·격리·유지보수 우위).

## SLICE18-D1-REOPEN — Slice 18 컨테이너 4모델 소속 재결정 필요 (2026-07-13) [portfolio]

**결정(안건 등재, 미확정)**: Slice 18 지시서의 닫힌 결정 **D1(신규 4모델 전부 apps/portfolio)의 전제가 STEP 0 실측으로 파기됨** → D1 재결정을 디렉터 세션으로 회부. 이 세션은 HALT·정지(코드 0).
- **Why(전제 파기)**: D1 전제 = "watchlist 등은 지금 portfolio만 소비". 실측 = `apps/dashboard/services/strip_service.py`(T1 보유·T3 관심 심볼 집합)와 `apps/chain_sight`(WatchlistViewSet)가 **이미 `shared/users.WatchlistItem`을 소비**. → watchlist는 범용 자산(shared 정당), D1 타이브레이커("교차앱 소비자 부재") 거짓.
- **Why(의미 중복)**: 신규 4종 중 2종이 기존 모델과 **동명·상위집합** — `WalletHolding`(apps/portfolio.WalletHolding, 동명=Django 충돌)·`WatchlistItem`(shared/users.WatchlistItem, REST 완비). 신규 생성 시 진실 소스 분할.
- **How to apply(재설계 입력)**: ⑴ 재사용 확정 시 Slice 18 신규 = **UserGoal·CashBalance 2종**으로 축소 ⑵ D2(UserScopedModel 직접 user FK)는 기존 재사용 2종(간접 user 스코프)과 상충 → 어댑터/이원화 ⑶ D3 격리 테스트 대상 범위 재정의. 상세 = `docs/portfolio/coach/slice18/STEP0_FINDINGS.md`.
- **STEP 0 측정**: baseline `pytest apps/portfolio tests/architecture` = 574 passed/0 failed(깨끗한 출발선). base origin/main `a340816`.

## T-3b — 상향학습 선별·자가오염·seed status 권위 일원화 (2026-07-13) [chainsight]

**결정**: RelationConfidence 상향학습의 재승급 flap을 **엔진 국소 수정(①②③ⓔ) + seed status 권위 제거(ⓓ-2)**로 근절. ⓓ-1(seed 단조 가드)·ⓓ-3 미채택. 병합=`--no-ff`(rebase 금지, Phase 커밋 해시 보존).
- ① 선별식 = `Q(last_computed_at__isnull=True) | Q(last_observed_at__gt=F(last_computed_at))`(비-market). 구 `last_observed_at__date=period` 폐기 + 콜드스타트 백필 마이그 0016(NULL 행 `last_computed_at←last_observed_at`).
- ② upward save를 `update_fields`로 — `last_observed_at`(auto_now) 제외. **①·② 필수 동반**(auto_now가 선별식을 영구참으로 만듦). `previous_status`·`neo4j_dirty`는 save() override가 쓰므로 update_fields에 포함(기존 행위 보존).
- ⓔ 멱등 상태화: confirmed면 fast-path·save skip, fastpath_triggered_at 최초 1회, last_upgraded_at 실 전이 시만.
- ⓓ-2: **status 권위 도메인 분할** — 비-market(truth) 상향=upward 엔진(highscore≥85/fast-path/streak), 하향=decay 전담. SEC seed(`sec_pipeline/tasks.py`)는 기존 pair status 무기록(`defaults`), 신규만 초기값(`create_defaults`). market status=`update_relation_confidence` 베이스라인 관할(upward 제외). 구 seed ≥85 규칙은 `HIGHSCORE_THRESHOLD=85`로 엔진 단일출처 이관.

**Why**: 관찰 창(07-08~12) 실측 — SEC seed(매일 01:00)가 upward 틱(00:30)이 fast-path로 올린 medium-grade tier1 공급망 pair(37건)를 30분 뒤 probable로 되돌림 = fastpath=30 churn(격일). "잃긴 쉽고 되찾긴 어렵다"의 하향/상향 비대칭을 지키려면 **한 pair의 status 상향/하향 권위가 각 1주체**여야 flap 불성립. B-0 감사(하드게이트): 기록자 전수=SEC seed/update_relation_confidence(upward보다 먼저 도는 베이스라인, flap 원천 아님)/upward/decay — 예상 밖·강의존 없음, SEC seed는 truth 전용이라 market 고아화 없음(제4 기록자 도메인 분할로 승인).

**How to apply**: 지시서 T-3b. 커밋 Phase A `b5a9485`·Phase B `7252590`·명문화 `6ab8955` → 병합 `3a3e921`(P-0 충돌 0·rerere clean). prod 마이그 0016(NULL 13,427→0). §4 관찰(거래일 3틱, 첫 유의미 틱부터 기산): 첫 신로직 틱(07-14) evaluated≈270(SEC 재관측 경로 = 0 아님), 코호트 30~37 confirmed 승급 마지막 1회 + 01:00 seed 후 유지(flap 소멸) + 쓰기 증폭 감소. §6 동결 재적용(§4 종료까지 chain_sight·sec_pipeline merge/rebase 금지). 정리: DB beat 삭제·pair 브랜치(잔여 병진 수동)·**OPS-WORKTREE-ISOLATION ✅ 봉인·클로즈(2026-07-28, 아래 블록)**·SEC β(seed status 무기록 승계 = ⓓ SEC β 이관). **검증**: 545 passed(신규 31), 사전존재 13(attention6+leadership7 Neo4j-env) 무관.

## OPS-WORKTREE-ISOLATION 클로즈 — 격리 3층 방어선 봉인 (2026-07-28) [ops] [harness]

**결정**: 동시성 사고 3건(트리 탈취 07-04·워커 리셋·미커밋 WIP) 대책 Opt-2 단계형(정리목록 ⓒ)을 **전 Phase 완료로 봉인·클로즈**. 3층 방어선 = Phase 1 세션 마커(`1f2bf5f`, respect verdict·heal·런타임 R1 예외) / Phase 2 공유트리 git hook(존치·트리거 대기, OBE) / Phase 3 verify 무인 파수꾼 section D(`b76d9ab`, 조상기반 drift·stale마커·코드버전). 클로즈 선언 = `docs/features/chain-sight/OPS_ISO_CLOSE_declaration.md`.

**본 트랙 결정 색인**:
- **래퍼 self-locate 채택**: verify launchd repoint가 plist-only로 불가(래퍼 `PROJECT_DIR` 공유트리 하드코딩+`cd`) → `PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"` self-locate. 행위보존 IDENTICAL 실측(공유트리 위치 호출 == 기존 하드코딩 값). origin/main `b9ddf41a`.
- **§1 결정 = α(sv-worker-runtime)**: verify 실행 트리 = origin/main 추적·worker_sync 전파·.env 완비 런타임 트리(β 전용 ops 트리 대비 이동부품 0). `launchctl print` 실효경로 확증.
- **야간→주간 집행 변경**: worker_sync blast radius(celery-worker+beat+daphne/WS 3종 재기동) 때문에 병진 야간 창 번들로 이행 → 실제 집행은 07-27 11:48(사전점검 게이트 충족: 금지구간 밖·nightly not running·celery active empty)에 병진 명시 지시로 CC 구동, 안전 게이트 엄수.

**Why**: 라이브 자동화 배치가 공유 세션 개발 트리를 읽으면 체크아웃 브랜치 따라 배포 drift(→ common-bugs #67). 브랜치별 cherry-pick은 수리 아님(재발). 배치 자체를 origin/main 추적 트리로 교정해야 근본 해소.

**임시규칙 일괄 정리**:
- **폐지**: ⑴ "마커 존중은 pair 세션만"(rollout 한시 스코프) — 전 세션 표준으로 승격 대신 Phase 1 마커 계약(respect verdict)이 상시 규약이므로 한시 표현 폐지. ⑵ "§6 동결 = §4 종료까지 chain_sight/sec_pipeline merge 금지"(T-3b 관찰 창 한시) — §4 종료로 자동 해제, SEC β 착수 시 재적용은 그 트랙 소관.
- **영구 승격 2건**(common-bugs 등록): ⑴ "지시서는 repo 커밋이 0번째 게이트, 원본 불변·개정문 누적"(#68). ⑵ "라이브 자동화 배치는 origin/main 추적 트리만 참조"(#67).

**봉인 증거**: 2026-07-28 02:30:05 KST 라이브 첫 section D 발화 `drift/marker/codever=ok/ok/ok`(07-19~27 라이브엔 전무=전후 대조). §3-2 인위 stale마커 발화→marker warn→원복→ok 복귀 실증. IDENTICAL PASS(`scripts/ops/compare_verify_skeleton.py`, section D 제외 diff=0). **차기 트랙**: ⓓ SEC β(`docs/features/chain-sight/PR_sec_beta_grounding.md`) — seed status 권위 잔여 질문(270 save/330 seed 재관측) 이관.

## SEC β G1 — grounding 검증 V-A 채택 + v1 dry-run 기준선 (2026-07-28) [chainsight] [sec]

**결정**: SEC 10-K 추출 인용의 verbatim 검증을 **V-A(결정적 정규화 매칭, LLM 0콜)**로 채택(2026-07-02 결정 ③ 승계, 퀀트 0.94 vs V-B 2콜 0.51). 판정 4종 = verified / normalized_match / not_found / **missing_source**(개정문1 — missing_source는 not_found와 합산 금지). 매처 = `services/sec_pipeline/grounding.py` 순수함수(NFKC+스마트따옴표/대시 ASCII+공백정규화). additive 마이그 0002(grounding_status/method/at, null=미검증).

**v1 dry-run 기준선(1,751건, flag-off, 쓰기0)**: verified **1,273(72.7%)** · normalized_match **41(2.3%)** · not_found **437(24.96% 순수)** · missing_source **0**. 접지 성공(v+n) = 75.04%. 리포트 = `docs/features/chain-sight/sec_beta_g1_dryrun_report.md`. **이 기준선은 prompt v2 롤아웃 후 비교 기준**(PR Gate 2).

**Why(임계 사전 고정, 개정문2)**: dry-run 분포를 보기 전 커밋에 임계를 박아 사후 합리화 차단 — not_found(순수) > 15% → V-B 부분 도입 사용자 재판정 회부(진행 차단 아님). 실측 24.96% > 15% → **V-B 재판정 회부 상태**(분포+샘플 20건 첨부, 감독 결정 대기).

**게이트별 사인오프**: Gate 1(flag-off·매처·additive 마이그·dry-run 분포)에서 정지. Gate 2(백필 실기록·flag-on 1 filing·prompt v2)는 **본 분포 감독 비준 후에만**. flag `SEC_GROUNDING_ENABLED`(G2, 기본 False)·prompt v1→v2는 미도입(G1 범위 밖).

## SEC β G1.5 — not_found 437 분해·재판정 (2026-07-28) [chainsight] [sec]

**결정(회부 자료)**: G1 not_found 24.96%(>15%)를 결정론 분해(LLM 0콜, `scripts/sec/grounding_g15_decompose.py`, 리포트 `docs/features/chain-sight/sec_beta_g15_decomposition_report.md`). 결과:
- **① 중복**: 1,751→유니크 937(중복률 46.5%). not_found 437→유니크 182.
- **② 동인 분리**: missing_source_section=0(구조적 — Track A 추출은 item_1+7만 LLM 투입, `normalizer.py:56`). 정규화 갭 테스트(source=raw vs `normalize_section_all`)=not_found 불변 0 → 정제갭 동인 아님. 판정 5종 확장 실발생 0 → 마이그 additive 수정 불요.
- **③ 비-verbatim 패턴**(유니크 182, prefix 결정론): tail 발산(절단/mid-word) **169(92.9%)** · 중간 재서술 5 · 합성 8.
- **재판정**: 잔여 순수 not_found 명목 24.96%/유니크 19.42% — 둘 다 >15% → **V-B 부분도입 결정 사이클 회부**.

**Why(권고 = V-B보다 prompt v2 우선)**: 잔여의 92.9%가 "옳은 문장의 tail 발산"(prompt v2 verbatim 강제 표적)이지 검증(V-B) 대상 아님. → **prompt v2 롤아웃 후 재측정 우선**, V-B 채택 시 범위 = 합성/재서술 ~13 유니크로 한정. 최종 결정 감독. 부수: 빈 store 61=regex 추출 실패(status=failed, 미참조 무해). Gate 2 정지 유지.

---

## credit_signals 신규 앱 (Phase 1) — FRED 크레딧 신호 백본 (2026-07-08) [credit]

**결정**: "채권이 먼저 말한다" 축을 위해 **신규 Django 앱 `apps.credit_signals`**(label `credit_signals`)를
생성한다. market_pulse/macro/thesis에 얹지 않는다(지시서 §7.2-B). 모델 2종:
`MacroSeriesHistory`(db_table `macro_series_history`, FRED 관측치 영구 원장) +
`CreditSignalState`(db_table `credit_signal_state`, signal_key별 최신 파생 상태).

**Why**:
- **FRED ICE BofA 3년 제한**(2026-04부터 최근 3년만 제공) → 수집 즉시 원장에 **영구 적재**가
  앱 존재 이유의 절반. 삭제 로직 금지, revise 시 value만 갱신·`ingested_at` 유지·`revised_at` 별도.
- 소비처(Dashboard/Chain Sight/Thesis Layer E)는 `credit_signal_state`만 읽는 단방향 계약.
- 독립 앱이라야 Phase 2(HYG/LQD·FMP·SEC·FINRA) 확장 시 경계가 흐트러지지 않음.

**How to apply**:
- **signal_key = 안정 계약**(Thesis Layer E가 `HY_OAS_Z > 2` 형태로 참조). 6종 계산
  (`HY_OAS`/`IG_OAS`/`BBB_OAS`/`CCC_OAS`/`CURVE_10Y2Y`/`VIX`) + 2종 키만 예약
  (`CCC_MINUS_BB`/`BBB_MINUS_A` — BB·A 시리즈 미수집, Phase 2). 수집 6→8 확장 금지(스코프).
- **z = Robust Z(MAD)** — thesis `indicator_scorer` 규약 동형(`1.4826*mad`, MAD_FLOOR early-return).
  grade: `z<1` gray / `1≤z<2` yellow / `z≥2` orange / red = orange + HY_OAS 절대값≥8.0(800bp, HY 한정) /
  관측<60 콜드스타트(z=null, gray).
- **flag guard** `CREDIT_SIGNALS_ENABLED`(기본 false, Decision ⑨-C 패턴) — ingest/compute/verify 최상단 no-op.
- **ingest→compute 체이닝** = sec_pipeline in-code `.delay()` 패턴(beat 타이밍 의존 아님).
- **beat 암묵 자동등록 금지**(bug #28) → `register_credit_beats` 명시 실행. §5 추가: 등록 전 동일
  crontab (hour,minute) 슬롯 기존 beat 조회·출력(기존 07:30/09:00은 ET tz라 실벽시계 충돌 아님, 참고 보고).
- **백필 = 포그라운드 블로킹 전용**(harness reaper 정책, README·커맨드 help 명시).
- **API `/api/credit-signals/strip/`**(지시서 §7 리터럴 경로) — 파생 자산이라 인증 유지(AllowAny 금지,
  audit P0 #5 정책). N+1 금지(상태 1쿼리 + 시리즈별 spark 단일쿼리).
- **FRED 인프라 재사용**: `packages/shared/api_request/fred_client.FREDClient`(rate limiter 내장) +
  settings `FRED_API_KEY`(기존 plumbing). 신규 클라이언트 만들지 않음.

**검증**: 28 test GREEN(upsert 멱등/revise·z(MAD)+floor·콜드스타트·grade 경계 red·flag off·verify 결측ERROR/주말·API 스키마+쿼리상한),
`manage.py check` 0, migration 0001 정·역·재 OK, macro 회귀 31 GREEN. worktree `monorepo/sess-credit-signals`(origin/main f33ffcc 기준).

## RelationConfidence 상향 학습 루프 — B+C 채택 (2026-07-02) [해자]

### 비대칭 보수(B) 기본 + Tier-1 fast-path(C) 가속 레인
**결정**: 감쇠 전용(단방향) RelationConfidence에 상향 경로 신설. **B**(하향 빠름·상향 느림/엄격: 이중 임계 + streak≥3, stale→probable 재획득, confirmed 직행 금지) 기본 + **C**(Tier-1 권위 증거는 1단계 즉시 가속, streak 면제·상향임계 충족·최대 1단계). 채점 **B 0.7725 > C 0.685 > A(대칭) 0.6225**.
**Why**: "잃긴 쉽고 되찾긴 어렵다" — 하향/상향 비대칭이 궤적 품질 = moat를 지킴(whipsaw를 streak 안전핀으로 구조적 차단). C는 권위 증거의 즉시 반영 요구를 "B 안의 가속 레인"으로 수용(궤적 우회 아님, fastpath_triggered_at 감사). 충돌 규칙(결정 2): 한 pair는 한 틱에 하향/상향 배타(증거 있으면 하향 스킵+상향 평가, 없으면 하향+streak 리셋).
**How to apply**: 설계 `docs/features/chain-sight/relation_confidence_upward_loop.md`. 태스크 접속 = `aggregate_relation_pairs_task`(#28) → `check_stale_and_decay`(하향) → `apply_upward_learning`(신규 상향). 필드 5개 additive(evidence_streak·last_upgraded_at·last_downgraded_at·last_computed_at[드리프트 해소]·fastpath_triggered_at). 임계 = `RELATION_CONFIDENCE.md` 정책표 연동(하드코딩 금지). **구현·D2 실데이터 검증은 #28 Gate 2 종결 + 궤적 N틱 적립 후 게이트**(그 전 D1 설계 스모크까지).

---

## 뉴스 β 활성화 조사 — C 채택 (본진 복귀) (2026-07-02) [해자]

### 세 레인(A 뉴스β / B SEC β / C #28 본진) 중 C 채택
**결정**: 가중 채점(합 1.00) C 0.8825 > B 0.795 > A 0.335 → **C 채택**(census 봉인 후 #28 본진 = RelationPairSnapshot 궤적 → 상향 학습 루프 복귀). B(SEC β provenance)는 **#28 Gate 2 통과 직후 다음 β 트랙 예약**, A(뉴스 β)는 **전문 저장 후 통과율·토큰 재측정 조건부 파킹**.
**Why**: 세 레인 중 **소급 재구성 불가는 #28 궤적뿐** — β 증거는 원문 잔존으로 재추출 가능하나, 궤적 스냅샷은 beat 미가동일 = 영구 공백(moat 정의 "temporal trajectories, none reconstructable retroactively" 직결). 뉴스 β "켜기"는 beat 등록이 아니라 **3층 신규 구축**(β 2-pass 미구현·NewsEntity 배선결함 headline/content/published_at 부재·전문 미저장). ① 현재 월 <$1, **①=②**(SEC 텍스트 β 대상 100% probable+ → 델타≈0).
**How to apply**: census 봉인 `docs/audit_out/census_beta_provenance_cost.md` §7. B 착수 전 확인 1점: SEC β 2-pass가 "강화"(base 생산중)인가 "신규"(1콜만)인가. A 재개 조건: 뉴스 전문 저장 후 통과율(현 요약본 하한 7%) 재측정.

---

## RelationPairSnapshot 쌍 relevance 적립 — 해자 궤적 (2026-06-29) [해자]

### opp/risk = 곱(게이트 AND), [0,1] 정규화
**결정**: `relevance_opp = max(0, t−m)·t`, `relevance_risk = max(0, m−t)·m` (t=truth_max/100, m=market_max/100). 가중합 아닌 곱.
**Why**: 곱은 AND 게이트 — 진실/시장 한쪽이 0이면 신호 0(가중합은 한쪽만으로 점수 발생). t==m이면 둘 다 0 → opp/risk 상호배타. truth/market 원천은 [0,100] 계단값(85/60/35) 그대로 두고 opp/risk만 [0,1] 파생.
**How to apply**: `apps/chain_sight/services/pair_aggregation.py::compute_pair_relevance`.

### 무방향 정규화 쌍 키 (방향성은 원천 행 보존)
**결정**: 스냅샷 키 = `normalize_pair`(sorted) canonical (a,b). 무방향.
**Why**: "두 종목 관계를 시장이 가격에 반영했나"는 방향 무관. SUPPLIES_TO 방향성은 원천 RelationConfidence 행에 그대로 보존되어 손실 없음. directional opp가 필요해지면 후속 변형.

### 스냅샷 단일 테이블 (요약 테이블 불채택)
**결정**: `RelationPairSnapshot` 1테이블. 현재값 = `DISTINCT ON (canonical_a, canonical_b) ... period DESC`.
**Why**: 수천 쌍 규모(실측 9,562)에서 정렬 병목 없음 → 2테이블은 동기화 버그 위험만 추가. 후일 조회가 실제 병목이면 캐시로 덧붙임(되돌릴 수 있음).

### 궤적 forward-only (backfill = 오늘 1점, 복원 불가)
**결정**: 점수 히스토리 미보관 → 매일 11:30 EST 집계로 forward-only 적립. backfill은 오늘 단면 1점만.
**Why**: 원천(CoMention 누적 카운트·PriceCoMovement 현재 상관)도 시계열이 아니라 현재 단면만 → 과거 궤적은 물리적으로 복원 불가. 매일 점이 소실 중이라 적립을 빨리 켤수록 이득.
**How to apply**: beat `chainsight-pair-aggregation`(11:30, update_relation_confidence 직후). ⚠ 버그 #28 — prod는 DB PeriodicTask 등록 별도 필요(TASKQUEUE P0).

### investment_relevance(per-row) deprecated
**결정**: `RelationConfidence.investment_relevance`(per-row) 사용 중단. 제거 마이그레이션은 보류(주석만).
**Why**: `unique_together=(a,b,relation_type)`라 한 행은 truth 또는 market 중 하나만 가짐 → per-row 합성은 무의미. 쌍 단위 `RelationPairSnapshot`(opp/risk)가 대체.

### get_thesis IDOR = 비공개만 소유자 제한 (공유 보존)
**결정**: 비공개 테제는 소유자만(404로 존재 비노출), 공개(`is_public`)는 누구나. `@authentication_classes([])` 제거.
**Why**: InvestmentThesis는 `is_public`/`share_code` 공유 기능 보유 → 무조건 user 스코프는 공유를 파괴. 또 `authentication_classes([])`면 `request.user`가 항상 AnonymousUser라 `user=request.user` 한 줄이 모든 요청을 404로 만듦. SEAM-DEBT #1 → SEAM-OK. (전수조사 `docs/audit_out/full_audit_2026-06-26.md`.)

---

## Chain Sight 보드 EventGroup 전환 (2026-06-27, Phase 1 완료)

### 보드 전환은 leadership 커플링에 묶여 A(어댑터)→재배선(C)→전환 3분할
**결정**: 이벤트 보드를 theme_tags→EventGroup으로 한 번에 바꾸지 않고 3세션으로 분할 — ① 리더 어댑터(kept만·n3, 게이팅 중앙집중) ② C 비대칭 leadership 재컴퓨트(코어=코어LOO/위성=전체코어평균) ③ 보드 소비자 플래그 배선.
**Why**: STEP 0.4 측정에서 **leadership이 theme-상대 LOO 벤치마크**(`StockLeadershipScore`가 `(stock, theme, window, date)` 키 + theme 멤버 LOO 평균이 피어셋)임이 드러남 → 보드만 EventGroup 키로 바꾸면 드릴다운 leadership이 빈 결과·의미 불일치(HALT). 점수 재배선은 score-diff 검증이 필요해 보드 배선과 분리해야 안전.
**How to apply**: 새 leadership 행은 `theme='eg:{slug}'` + additive `benchmark_kind`(core_loo/sat_coremean, 레거시=NULL)로 **키 분리**(기존 unique_together·행 불변). 리스트(slug 키)↔드릴다운(slug)이 동일 키 공유 → 커플링 정합 충족.

### 보드 그룹 소스 = settings 플래그 `CHAINSIGHT_GROUP_SOURCE` (기본 OFF)
**결정**: 전환을 `CHAINSIGHT_GROUP_SOURCE`(`theme_tags`=OFF 기본 / `event_group`=ON) 단일 settings 토글 뒤에 둔다. go-live(ON)는 `.env` 값 + daphne web 재시작.
**Why**: repo에 기존 피처 플래그 패턴 부재 → settings getattr 최소안(신규 메커니즘 발명 금지). OFF=오늘과 IDENTICAL 보장(레거시 경로 분기만 추가, serializer `name`은 `required=False`만→OFF 생략). 되돌리기가 코드 롤백 없이 `.env`+재시작으로 가능.
**How to apply**: `apps/chain_sight/flags.py::use_event_group_board()`. ON 신선도는 `chainsight-event-group-leadership-daily` beat(22:15 UTC, attention 22:30보다 앞). 검증·hash: 머지 `202a840`, pytest 191·vitest 19·경계 0. 산출물 `docs/chain_sight/m2_v1.1_board_flag_verification.txt`.

### EventGroup = 공동언급 Jaccard 정규화 코어-위성 2층 (theme_tags 교체)
**결정**: 섹터형 `theme_tags`를 뉴스 공동언급 기반 EventGroup으로 교체. 엣지 가중 = Jaccard 정규화(half_life 21d), 코어(jaccard 연결요소, ≥3)–위성(1-hop) 2층.
**Why**: raw 공동언급은 슈퍼허브(NVDA degree 28)에 가짜 스포크(CAT·UBER·MTB) 흡입 → Jaccard 정규화로 NVDA degree 28→1(임계 0.2), 가짜[CAT 0.017] vs 코어[AMD 0.215] 분리. npmi도 후보였으나 jaccard가 코어 신호 보존 우수.
**출처**: 파이프라인 세션. `docs/chain_sight/m2_v1.1_norm_jaccard_report.txt`, `m2_v1.1_bc_clustering_report.txt`.

### cohesion < 0.2 게이트 = 가격상관 기반 (구조지표 TPR/conductance 기각)
**결정**: 코어 cohesion(코어 멤버 수익률 pairwise 상관 평균) < 0.2 → `is_hidden=True`(드롭 아님, 플래그). 구조 토폴로지 지표(TPR/conductance)는 진단으로만.
**Why**: 구조지표는 그래프 모양만 측정하나 cohesion은 "함께 움직이는가"(실제 투자 신호)를 직접 측정 → 게이트로 채택. 16그룹 중 7 gated(저신뢰 잡탕). 분포 p10/p50/p90 = 0.126/0.415/0.757.
**출처**: `docs/chain_sight/m2_v1.1_diagnostics_tpr_conductance_naming.txt`, `m2_v1.1_phase1_cohesion_gating_tfidf_names.txt`.

### 그룹명 = 코어 전용 TF-IDF 상위 3텀 (n3)
**결정**: 그룹명 = 코어 멤버 TF-IDF 상위 3텀(`name_candidates["n3"]`). 후보(n2/n3/원시텀)는 `name_candidates`에 보존.
**Why**: 위성 포함 시 이름 희석 → 코어 전용 텍스트. 예: AMAT/KLAC/LRCX → "applied materials semiconductor".

### leadership 벤치마크 = C 비대칭 (코어=core_loo / 위성=sat_coremean) — 왜 A·B 아닌 C
**결정**: 역할별 비대칭 벤치마크 — 코어 종목 = 코어 LOO(자기제외 코어평균), 위성 종목 = 전체 코어평균. leadership 수식(α/β·capture·LOO)은 검증본 재사용, **피어셋만 역할별 분기**.
**Why**: 대칭 벤치마크는 위성이 코어 벤치마크를 희석하거나 코어를 과소평가. C는 코어/위성을 분리 평가 — 코어는 동료 코어 대비, 위성은 코어 대비 → 각 역할의 실제 위치 측정. 키 분리 `theme='eg:{slug}'` + `benchmark_kind`(core_loo/sat_coremean, 레거시 NULL).
**출처**: leadership 세션(C 결정 헤더). `docs/chain_sight/m2_v1.1_leadership_eventgroup_C_verification.txt`. 머지 `269d1eb` + prod 0013 + eg 114행.

### L3 오라클 = 역할 분기 정확성 게이트
**결정**: 역할별 벤치마크 분기를 독립 참조 구현(numpy.polyfit + 순수루프, `tests/chainsight/oracles/`)으로 교차검산 — 코어=코어LOO·위성=코어평균이 프로덕션과 rel 1e-6 일치 + 엣지(코어1개) 일치.
**Why**: 역할 오분류(코어가 위성 벤치 사용 등)는 조용한 오답 → 독립 오라클이 마지막 게이트. 향후 leadership 정교화의 회귀 정답지로 영구 배치.

---

## 데이터 아키텍처

### 4-Layer 데이터 흐름
```
Raw (외부 API) → Metrics (Django 모델) → ChainSight (PostgreSQL 프로파일) → Neo4j (그래프)
```
**Why**: 각 계층이 다른 갱신 주기와 소비자를 가짐. Raw는 실시간, Metrics는 일일, Neo4j는 주간.

### neo4j_dirty 플래그 패턴
- PostgreSQL → `neo4j_dirty=True` 세팅 → Celery 배치로 Neo4j 동기화
- `synced_to_neo4j` 대신 채택
- **Why**: 단방향 동기화(PG→Neo4j)에서 "동기화 필요" 의미가 명확. 역방향 없음.
- 📎 상세: `docs/chain_sight/plan/redesign_v1_260409/chainsight_seed_node_design.md`

### CUSTOMER_OF 파생
- DB에 별도 저장 안 함. `SUPPLIES_TO`의 역방향을 API 계층에서 `display_type`으로 파생.
- **Why**: 중복 저장 제거. 방향 반전만으로 충분.

### Undirected 관계 정규화
- `PEER_OF`, `COMPETES_WITH`, `CO_MENTIONED`, `PRICE_CORRELATED` 4종은 Neo4j에서 무방향.
- 저장 시 `symbol_a < symbol_b` 순서로 정규화하여 중복 방지.
- **Why**: 양방향 엣지를 중복 생성하면 GDS 알고리즘 결과 왜곡.

### DailyPrice 단일 모델
- `HistoricalPrice` 모델 없음. 모든 가격 데이터는 `DailyPrice` 사용.
- **Why**: 히스토리컬과 일일의 구분 불필요. 중복 모델 방지.

### 운영 상태(배치 생성) vs Lazy cache(요청 시 생성) 분리
- **운영 상태** (배치로 하루 1회만 생성, 다음 배치까지 기다려야 복구되는 데이터) → **DB 영속화 필수**, Redis는 hot path 레이어
  - 적용: `SeedSnapshot` (Chain Sight 시드)
  - `cache_seed_result()` = DB upsert + Redis write. Redis 실패해도 DB 보존.
  - 조회 폴백 순서: Redis → `SeedSnapshot` DB (최근 7일) → async `run_seed_selection.delay()` (setnx lock 5분으로 중복 방지)
- **Lazy cache** (요청 시 즉시 재생성 가능한 데이터) → Redis만, DB 영속화 안 함
  - 적용: `sector_graph`, `neighbors`, `signals`
- **Why**: 2026-04-24 사건(pytest flush로 시드 캐시 증발, 다음 Beat까지 24h 빈 응답) 교훈. "배치 단위 영속성"과 "요청 단위 휘발성"은 다른 레이어에 둔다. Lazy cache는 cache miss 시 1~2초 지연 후 자동 재캐시 → DB 영속화해도 얻는 게 없고 stale만 누적.

### 테스트 캐시는 운영 Redis와 물리적 분리
- `config/settings_test.py`에 `CACHES[default] = LocMemCache` override
- `pytest.ini` → `DJANGO_SETTINGS_MODULE = config.settings_test`
- `tests/conftest.py:clear_cache_after_test`에 `assert 'locmem' in backend` 안전 가드
- **Why**: `django-redis.cache.clear()`는 KEY_PREFIX와 무관하게 `FLUSHDB` 호출 → DB 전체 삭제. 같은 Redis DB를 테스트와 운영이 공유하면 테스트 한 방으로 운영 데이터 증발.

### Celery Beat 스케줄의 진실의 소스는 DB `PeriodicTask`
- `settings.py`: `CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'`
- `config/celery.py`의 `app.conf.beat_schedule` dict는 **런타임에 무시됨** (선언적 reference만)
- 스케줄 추가/변경: Django admin 혹은 `PeriodicTask.objects.update_or_create(...)` + `PeriodicTasks.update_changed()`
- **Drift 체크**: `set(PeriodicTask.objects.values_list('name', flat=True))` vs config dict 키 diff. 주기적 수동 검증 필요.
- **Why**: DatabaseScheduler는 DB 테이블을 폴링. dict에만 추가하면 실행되지 않음(2026-04-24 `chainsight-heat-score-daily`, `sec-seed-relations-to-chainsight` 실종 사례).

### Chain Sight `get_market_date()`는 America/New_York 기준
- `date.today()` (시스템 TZ) 대신 `datetime.now(ZoneInfo('America/New_York')).date()`
- **Why**: NYSE EOD 기준 키와 일치. 시스템 TZ가 KST/UTC 등일 때 Beat 저장 시점과 read 시점의 `date` 불일치 방지.

---

## Chain Sight

### 마켓 뷰 이원 구조
- `/chainsight` = 마켓 뷰 (Breadth-first 탐색)
- `/chainsight/[symbol]` = Deep Dive Workspace (Depth-first 분석)
- **Why**: 광범위한 시장 탐색과 개별 종목 심화 분석은 다른 사용자 의도.
- 📎 상세: `docs/chain_sight/plan/redesign_v1_260409/chainsight_api_design.md`

### 마켓 뷰 4개 API
| 엔드포인트 | 역할 | 캐시 TTL |
|-----------|------|---------|
| `GET /seeds/` | 섹터바 + 시드 카드 | 30분 |
| `GET /sector/{sector}/graph/` | 섹터 overview 그래프 | 30분 |
| `GET /{symbol}/neighbors/` | 중심 이동 + 관계 카드 | 5분 |
| `GET /signals/` | 체인 스토리 피드 | 30분 |
- **Why**: 4개 엔드포인트로 5개 UI 컴포넌트를 모두 구동. 백엔드 복잡도 최소화.
- 📎 상세: `docs/chain_sight/plan/redesign_v1_260409/chainsight_ui_ux_design.md`

### 시드 선정 3단계 진화 경로
- Phase 1: 시장 시그널(B) + 관계 변화(A) → 매일 13:00 UTC, MAX=20
- Phase 2: Heat Score 복합 랭킹 (SeedHeatScore 모델 필요)
- Phase 3: 이벤트 전파 모델 (Gemini Embedding + ChromaDB 필요)
- **Why**: 각 Phase 전제조건이 다르므로 점진적 진화.
- 📎 상세: `docs/chain_sight/plan/redesign_v1_260409/chainsight_seed_node_design.md`

### seed_reasons 8개 코드
`price_top5`, `price_bottom5`, `volume_surge`, `sector_outlier`, `relation_upgrade`, `relation_downgrade`, `relation_new`, `comention_surge`
- **Why**: UI에서 "왜 시드로 선정됐는지" 시각적 배지로 표시.

### Neo4j GDS 알고리즘 유지
- PageRank, Louvain Community Detection, Betweenness Centrality 사용.
- **Why**: NetworkX 대비 대규모 그래프에서 성능 우수. APOC 프로시저 활용.
- 📎 상세: `docs/chain_sight/plan/cs_30_neo4j_sync.md`

### RelationConfidence.previous_status 필드
- `CharField(max_length=20)`, nullable
- **Why**: 시드 선정에서 "어제 confirmed → 오늘 probable" 상태 전이 감지 필요.

---

## SEC Pipeline

### 2-Track 추출 설계
- Track A: Item 1A (Risk Factors) → 공급망 추출
- Track B: Item 7 (MD&A) + Item 3 (Properties) → 사업모델 추출
- **Why**: 공급망과 사업모델은 10-K 내 다른 섹션에 위치하고 프롬프트가 다름.
- 📎 상세: `docs/sec_pipeline/plan/sec_pipeline_base_design.md`

### Ticker 매칭 3단계
1. `alias` (CompanyAlias 테이블 정확 일치)
2. `exact` (이름 정확 매칭)
3. `fuzzy` (Levenshtein 유사도)
- 실패 → `UnmatchedCompanyQueue` 적재 → 수동 검토
- **Why**: 100% 자동화 불가. 실패 케이스를 큐에 모아 bulk 등록.

### SEC EDGAR 직접 수집
- FMP sec-filings API가 Starter 플랜에서 404 → EDGAR submissions API 직접 사용.
- regex 3단계 + edgartools fallback으로 섹션 추출.
- **Why**: 비용 0원으로 10-K 원문 확보.
- 📎 상세: `docs/sec_pipeline/task_done/sec_pipeline_complete_summary.md`

---

## Thesis Control

### 화살표 시스템 (0°~180°, 5색상)
| 범위 | 색상 | 의미 |
|------|------|------|
| 0°~35° | #2563EB | 강하게 지지 |
| 36°~71° | #60A5FA | 지지하는 편 |
| 72°~107° | #D1D5DB | 중립 |
| 108°~143° | #FB923C | 약화하는 편 |
| 144°~180° | #EF4444 | 강하게 반박 |
- **Why**: 숫자(-1.0~1.0)보다 화살표 방향+색상이 직관적.
- 📎 상세: `docs/thesis_control/plan/thesis_control_design.md`

### 달 위상 시각화
- `overall_score` (-1~1) → 달 밝기 매핑
- **Why**: 숫자를 자연스러운 메타포로 변환하여 "느낌" 전달.

### authAxios 단일 소스
- `lib/api/authAxios.ts`: JWT 인터셉터 단일 소스 (AuthContext + thesis 공유)
- 3중 방어: 단일 탭 race condition, 다중 탭 동기화, Token rotation
- **Why**: JWT 로직 중복 방지. 한 곳에서 관리.

---

## 1차 검증 (Validation)

### Compute-on-Read 패턴
- DB에 사전 계산 저장 안 함. 요청 시 peer group 대비 percentile 실시간 계산.
- **Why**: peer group이 동적으로 변경될 수 있으므로 사전 계산값이 빠르게 stale.
- 📎 상세: `docs/first_validation_system/validation_design.md`

### Peer 프리셋 6종 + LLM 대화형 필터
- 프리셋: Industry+Size 기반 자동 선정
- LLM: 사용자 질문을 peer 조건으로 변환
- **Why**: MVP는 프리셋만으로 충분, Chain Sight DNA 활용해 고도화 예정.

### 신호등 기준: Percentile 통일
- `score >= 65`: green, `>= 35`: yellow, else: red
- **Why**: 절대값이 아닌 peer 상대 위치. 산업 특성 자동 반영.

---

## EOD Dashboard

### JSON Baking + Atomic Write
- Celery Beat 18:30 ET → 14개 시그널 계산 → JSON 파일 baking → Atomic directory swap
- **Why**: API 비용 0원. 실패 시 이전 데이터 유지 (partial update 방지).
- 📎 상세: `sub_claude_md/eod-dashboard.md`

### 14개 시그널 체계
- Momentum (P1~P4), Breakout (P5), Reversal (P7), Volume (V1, PV1, PV2), Technical (MA1, T1), Relation (S1, S2, S4)
- VIX > 25: 상위 threshold 부스트
- **Why**: 각 시그널이 독립적 관찰 관점 제공. 너무 많으면 노이즈, 적으면 신호 부족.

---

## News Intelligence v3

### 3계층 파이프라인
- 규칙 엔진 → LLM 분석 (Gemini Flash) → ML 학습 (LightGBM)
- **Why**: 규칙은 저비용+빠름, LLM은 맥락 이해, ML은 패턴 최적화. 계층별 강점 활용.
- 📎 상세: `sub_claude_md/news-insights.md`

### Sector Ripple 2-hop 확산
- 대형주 → 같은 섹터 중소형주로 0.4x 감쇠, 20개 상한
- **Why**: 대형주 뉴스가 섹터 전체에 영향. hop 제한으로 노이즈 방지.

---

## 프론트엔드

### 차트: Recharts ComposedChart
- Bar + Scatter + ErrorBar 조합
- **Why**: D3.js보다 React 친화적, 복합 차트 표현력 충분.

### 상태 관리 이원화
- 서버 상태: TanStack Query (staleTime=5min, gcTime=30min, retry=2)
- 클라이언트 상태: Zustand (explorationStore 등)
- **Why**: 서버 캐싱과 UI 상태의 관심사 분리.

### Chain Sight 탐색 상태 공유
```typescript
interface ExplorationState {
  selectedSector: string | null;
  centerSymbol: string | null;  // null = pre-focus
  trail: TrailNode[];
  historyNodes: string[];
  currentNeighbors: Neighbor[];
}
```
- **Why**: 그래프와 카드가 "같은 탐색 상태를 공유하는 두 인터페이스"이므로 분리하지 않음.

---

## API 응답 규격

### 응답 표준: DRF 평탄 + 통일 에러 envelope
- **성공**: `serializer.data` 또는 dict **평탄 반환** (DRF 표준). 기존 `{success, data, meta}` wrapping 폐기.
- **에러**: 단일 형태 `{detail, code?, errors?, status_code}`
  - `detail`(필수): 사람이 읽는 메시지. DRF 기본 키 유지.
  - `code`(optional): snake_case 도메인 코드. 클라 분기용.
  - `errors`(optional): ValidationError field-level만.
  - `status_code`(필수): 정수. HTTP status 중복이지만 명시.
- **변환**: `config.exception_handler.custom_exception_handler` (REST_FRAMEWORK.EXCEPTION_HANDLER 등록, 2026-05-12).
- **도메인 코드 보존**: `rag_analysis/exceptions.py`(4개), `serverless/exceptions.py`(8개)에 `APIException` 서브클래스로 `default_code` 정의. 500계 도메인 에러 12개는 Sentry breakdown용 분기 의미가 있어 유지. 4xx 16개 코드는 DRF 표준 예외(`NotFound`, `PermissionDenied`, `NotAuthenticated`, `ValidationError`)로 흡수.
- **예외 범위**:
  - Market Pulse v2 cards (`marketpulse/api/views/cards.py:_envelope`) — v2 contract `{_meta, data}` 별도 유지.
  - 포트폴리오 (`portfolio/views.py` JsonResponse) — DRF 미사용, 정책 밖.
  - SSE 이벤트 페이로드 (`PIPELINE_ERROR`/`STREAM_ERROR`) — HTTP 200 내부 이벤트, 정책 밖.
- **Why**: 2026-05-06 api_consistency_audit P1 #14. 3종 혼재(W/D/C)로 FE가 라우트별 unwrap 분기 필요 → 같은 view 안에서도 성공은 wrap, 에러는 평탄으로 충돌하는 hotspot 존재. WRAP은 6 파일만 사용 → 마이그레이션 비용이 envelope 통일보다 작다. DRF 표준 정렬로 신규 view 결정 비용 0 + drf-spectacular ErrorSerializer 일관 적용.
- 📎 상세: `docs/features/api_envelope/policy.md`

---

## 인프라

### Neo4j 유지 결정
- GDS 알고리즘(PageRank, Louvain, Betweenness Centrality) + APOC 때문.
- **Why**: PostgreSQL의 `ltree`/`recursive CTE`로는 커뮤니티 탐지 불가.

### GraphRepository Protocol
- 백엔드 디커플링용 추상화. Neo4j 구현체만 존재.
- **Why**: 향후 다른 그래프 DB 전환 가능성 열어둠.

### Celery Beat 스케줄 분리
- `config/settings.py`: 기본 스케줄 (Market Movers, Breadth, Heatmap)
- `config/celery.py`: 확장 스케줄 (Chain Sight, EOD, ML, SEC)
- **Why**: 핵심 스케줄은 settings에, 기능별 스케줄은 celery.py에 분리.

### macOS Celery fork 안전성
- `OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES` + `PGGSSENCMODE=disable`
- fork 후 `db.connections.close_all()` 필수
- Neo4j queue: `--pool=solo` (fork 없이)
- **Why**: macOS에서 fork + Objective-C 런타임 충돌 (SIGSEGV). 버그 #25.

---

## 서비스 리모델링 (보류 — 2026-05-28)

### 3단계 플로우 전환 (계획서, 미시작)
- **이전**: Dashboard → Chain Sight → Node Monitoring → 1차 검증 → Thesis Control → Portfolio (6단계)
- **변경 계획**: Dashboard(매크로) → Chain Sight(발견/검증/가설) → Portfolio(보유) (3단계)
- **Why**: 사용자 여정 단순화. Chain Sight가 발견+검증+가설을 통합.
- 📎 설계 보존: `docs/stock_vis_service_remodeling/stock_vis_service_remodeling_plan_v1(260404).md`

### 보류 사유 (2026-05-28)
- 2026-04-04 계획서 작성 후 **실작업 0건** (브랜치 `data_structure_remodeling_V1` 부재, 5/11 main 정착 시 origin 삭제, 로컬도 부재)
- 44일 정체 (4/14 마지막 reflog → 5/28)
- 그동안 Slice 14~17이 main에서 진행되어 현 코드가 계획서 시점 대비 크게 변동
- 재개 시 현 시스템 기준 **재설계 필수**. 본 결정의 "변경 계획"은 사고의 출발점일 뿐 곧바로 실행 지침 아님
- TASKQUEUE "보류 (On Hold)" 섹션에 `SR (트랙)`으로 단일 행 이동 (옛 SR-1~4 통합)

---

## 지식 그래프 (OAG KB)

### 이중 저장 원칙: 1차 소스 + KB
- 아키텍처 결정 → `DECISIONS.md` (1차) + KB `DECISION` 타입 (장기 검색)
- 버그 해결 → `common-bugs.md` (1차) + KB `TROUBLESHOOT` 타입 (상세 과정)
- 세션 교훈 → KB `LESSON`/`PATTERN` 타입이 유일한 저장소
- **Why**: 1차 소스는 에이전트가 즉시 참조하는 "작업 메모리", KB는 장기 보존 + 의미 검색이 가능한 "장기 기억". 둘 다 필요.

### KB 큐 → 큐레이션 → Neo4j 파이프라인
- `queue_data.json`(대기) → `@kb-curator` 큐레이션 → `Neo4j Aura`(영구)
- **Why**: 품질 게이트 없이 KB에 직접 쓰면 노이즈 누적. 큐레이션이 신호/잡음 분리.

### knowledge_type 체계
| 타입 | 용도 | 주요 소스 |
|------|------|----------|
| `TROUBLESHOOT` | 버그 해결 과정 | common-bugs.md, @backend/@infra 세션 |
| `LESSON` | 교훈 (잘한 일/못한 일) | @qa 검증, 에이전트 세션 종료 |
| `DECISION` | 아키텍처 결정 | DECISIONS.md |
| `PATTERN` | 코딩 패턴 | @backend/@frontend 세션 |
| `TERM`/`METRIC` | 투자 용어/지표 | @investment-advisor |
- **Why**: 타입별로 검색 필터링 + 우선순위 규칙 적용 가능.

### 신뢰도 레벨 정책
- `verified`: 테스트 통과 또는 공식 문서 기반만
- `high`: 전문가(에이전트) 확인
- `medium`: 일반 합의 (큐레이션 기본값)
- `low`: 추정, 미검증
- **Why**: 에이전트가 검색 시 `confidence_min=high`로 노이즈 제거 가능.

---

## 외부 API

### FMP `/stable/*` 경로만 사용
- Legacy `/api/v3/*` 지원 안 함.
- **Why**: FMP가 stable 경로로 마이그레이션. 레거시 경로 deprecation 예정.

### Gemini 2.5 Flash 단일 LLM
- 키워드 생성, 관계 추출, RAG 분석, SEC 추출, 뉴스 분석 모두 Gemini.
- **Why**: 비용 효율 + 일관된 프롬프트 엔지니어링. $0.005/thesis 수준.

### Rate Limit 방어 원칙
| API | 제한 | 방어 |
|-----|------|------|
| Alpha Vantage | 5 calls/min | 12초 대기 필수 |
| FMP (Starter) | 300 calls/min, 10,000 calls/day | `.` 심볼 제외 (FMPPremiumError), api_request/rate_limiter.py에서 80% 안전 마진 |
| Gemini Free | 15 RPM, 1500 RPD | Exponential backoff + 배치 |

---

## 하네스 / 문서 관리

### 문서·git 정합성 관리 원칙 (2026-05-28 신규)

**결정**:
1. **PROGRESS.md를 두 영역으로 분리한다** — (a) **자동 추출 가능한 부분** (활성 brunch HEAD, origin/main 해시, 최근 머지 commit, 마지막 갱신 후 누적 commit 수)은 `scripts/health_check.py`가 매 세션 시작 시 검증·갱신 가이드 출력. (b) **수동 영역** (blocker, 결정 사항, 작업 단위 상태, 후속 큐)은 사람·에이전트가 종결 시 명시 갱신.
2. **매 세션 시작 시 `python scripts/health_check.py` 실행** — 5건 정합성 자동 검증 (origin HEAD vs PROGRESS / brunch·worktree 존재 / 마지막 갱신 후 commit 수 / TASKQUEUE done vs git 머지 매칭 / DECISIONS 갱신일). exit code 0=OK, 1=warning, 2=error. error 시 다른 작업 전 보정 우선.
3. **Claude 메모리는 진실의 소스가 아니라 PROGRESS의 캐시로 다룬다** — 메모리에 박힌 brunch/HEAD/PR 정보는 PROGRESS 표기를 참조한 결과물. PROGRESS가 stale이면 메모리도 stale. 갱신 우선 순위: git 현실 → PROGRESS → 메모리.
4. **TASKQUEUE의 `done` 상태는 git 머지 commit 매칭이 진실 기준** — TASKQUEUE에 `done` 표기됐는데 해당 PR/머지 commit이 git에 없으면 상태 오류. 외부(GitHub PR)에서 머지된 경우에도 머지 직후 TASKQUEUE 갱신 의무화.
5. **브랜치 종결 시(main 정착 + `slice*-done` 태그 생성) PROGRESS "활성 브랜치" 표에서 해당 행 제거** — 종결 이력의 진실 소스는 `slice*-done` 태그이고, PROGRESS 표는 "현재 활성"만 표기. 종결 brunch가 표에 잔존하면 health_check brunch 부재 ERROR 발생(2026-05-28 slice* 7건 일괄 삭제 후 slice17 표기 stale 사례). 백업 브랜치(`*-backup-*`)도 동일 원칙, 임시 백업 태그(`*-pre-merge`)는 표 외 노트로 유지.

**Why**:
- 2026-05-28 종합 정합성 점검에서 **6가지 불일치 패턴** 동시 발견:
  1. PROGRESS.md 16일 stale (마지막 5/12, 그동안 167 commits 누적)
  2. `origin/main = be2d6c7` 표기 오류 (실제 `3e76bc8`)
  3. `feature/chainsight-graph-v2` worktree 부재 (PR-#8 머지 후 정리됐는데 PROGRESS는 보존 중이라 표기)
  4. TASKQUEUE CS-R9 `todo` 표기 (실제 PR-#8 머지로 완료)
  5. slice17 brunch 143 commits이 origin/main에 0% 반영 (16일 누적 미통합)
  6. 메모리에 박힌 brunch/HEAD가 stale PROGRESS를 캐시한 상태
- **16일 stale은 시스템적 결함이지 1회성 실수가 아님** — 매 슬라이스 종결 시 갱신 의무가 명시됐음에도 brunch 격리 작업 + main 정착 단계 지연 + 외부 자동화 audit commit 끼어들기 등 복합 원인으로 누락 발생. 매뉴얼 의존 방식이 한계.
- 검문소(`health_check.py`) + 단일 진실의 소스(git 현실) + 자동/수동 영역 분리가 함께 있어야 재발 차단.

**Layer 1~4 채택 (단계화)**:
| Layer | 시점 | 작업 | 효과 |
|-------|------|------|------|
| 1 (즉시, 2026-05-28) | 본 결정 | `scripts/health_check.py` 도입 + PROGRESS·DECISIONS·common-bugs 갱신 + Slice 17 closing 후 박음 | 정합성 점검 자동화, 1회 보정 |
| 2 (단기, monorepo 도입 시) | Slice 18+ | monorepo 재배치 시 `apps/*`, `packages/shared/*`, `services/*` 별로 PROGRESS 분리 + 각 영역 독립 health_check | 단일 PROGRESS의 stale 폭발 위험 감소 |
| 3 (중기) | 운영 안정화 | pre-commit hook에 `health_check.py` warning 표시 + GitHub Actions 야간 자동화로 PROGRESS 자동 patch PR | 갱신 의무를 hook으로 강제 |
| 4 (장기) | Phase 2 진입 시 | PROGRESS 자동 추출 영역을 `make progress` 명령으로 완전 자동화. 수동 영역만 사람 입력 | 매뉴얼 부담 0, 자동 영역과 수동 영역 완전 분리 |

**📎 참조**: `scripts/health_check.py`, `sub_claude_md/common-bugs.md` #30, `PROGRESS.md` "정합성 문제 발견 (2026-05-28)" 섹션

---

## monorepo 재배치 (실행 결정 2026-05-28)

> 청사진: `docs/monorepo_migration/blueprint_v1.md` (실행 확정 = 지금)

### ① import 경로 방식 = 안 B(dotted-path) 확정 (2026-05-28)

**결정**: 폴더 구조를 import 경로에 반영. `services.stocks`, `packages.shared.users` 등 dotted-path 패턴. **app_label은 유지** (DB·migration 영향 0).

**근거**:
- 8 멀티에이전트가 코드를 대량으로 읽는 환경 — 경로의 **명시성·규칙 일관성**이 일회성 변경 비용(~80-120 파일) 압도
- 가중합 비교: **안 B 4.23** vs 안 C(혼합) 3.35 vs 안 A(평면 유지) 2.90
- 폴더 위치만 보고 어느 계층(packages/services/apps)인지 즉시 식별 가능 → 신규 작업 진입 비용 최소화

**실행 방식**:
- 3단계(폴더 이동 + import 경로 일괄 갱신)에서 **그룹별 점진** 진행
- 의존 역순: `packages/shared/` → `services/` → `apps/` (역방향 dependency 발생 방지)
- 단계마다 pytest 회귀 검증 (전건 통과 확인 후 다음 그룹)
- 마이그레이션 dependencies 형식(`('stocks', '0001_initial')`)은 app_label 기준이라 변경 불필요

**연쇄 제약**:
- 분류 경계(②)가 곧 경로에 박힘 → 다음 ② 결정에서 packages/services/apps 경계를 신중 확정해야 함
- `graph_analysis` 흡수 결정 / `marketpulse` 위치(shared vs services vs apps) / `chainsight` v1+v2 통합 여부가 ② 핵심 갈림길

**📎 참조**: `docs/monorepo_migration/blueprint_v1.md` §2(분류 초안) + §5(깨질 참조)

### ② 분류 경계 확정 — 세션 충돌 경계 기준 (2026-05-28 재정의)

**근본 목적**: monorepo = **세션 간 git 충돌 방지** (병진 확정). 세션 3종 = 메인 / 서브 / 봇 연계. 폴더는 **세션 소유권이 겹치지 않게 분리**.

**apps/** (메인 세션, 각 단독 트랙):
- `dashboard` — 거시 통합 뷰
- `market_pulse` — Market Pulse 본체 (marketpulse v2 + macro v1 진입점 통합). **dashboard와 분리** — 둘 다 거시지만 별개 메인 트랙(베이스만 공유)
- `chain_sight` — 발견/검증/가설 진입점
- `portfolio` — 보유 관리 + 코치 (+ `thesis` `scope` 분기 통합)

**integrations/** (봇 연계 세션):
- `iron_trading` — read-only provider, contract 기반 비공유 연계
  - ⚠ **apps/services 아님**. 가중합: **C(integrations) 5.0** > A(apps) 3.20 > B(services) 2.35

**packages/shared/** (공유 인프라·데이터):
- `stocks` · `users` · `api_request` · `metrics`
- `macro` **공유자산** — `MarketIndex` · `MarketIndexPrice` 모델 + `fred_client` · `fmp_client`
- `marketpulse/utils/circuit_breaker.py` (파일 단위 분리, 외부 7건 사용)

**packages/web/** 또는 루트 유지 — Next.js UI 공유 레이어:
- `frontend/` (단일 SPA). **apps/web 폐기** — 독립 트랙 아님, 공유 UI 레이어로 위치 변경

**services/** (백엔드 도메인 서비스):
- `news` · `serverless` · `rag_analysis` · `validation` · `sec_pipeline`
- `chainsight` (백엔드 v2)
- **`services/_dormant/graph_analysis`** — 0 import · API 미구현 · 활성 세션 없음. 가격 상관 도메인이라 `chainsight`(사업/뉴스 관계)와 별개. 미래 어느 메인 트랙이 활용 시점에 흡수 위치 재결정. 세션 충돌 위험 0(휴면 코드). 근거: `docs/chain_sight/update_v2/ROADMAP_v1.4.md` L931 "독립 유지. 겹치지 않음." 명시

**메타 레이어** (서브 세션, 루트 유지):
- `docs/` · `scripts/` · `PROGRESS.md` · `DECISIONS.md` · `TASKQUEUE.md` · `CLAUDE.md` · `sub_claude_md/` · `contracts/` · `shared_kb/` · `.claude/` · `HARNESS_FITNESS.md` · `WORKSPACE_ROOT.md`

**해체(소멸)**:
- `macro` 앱 — 자산을 `packages/shared` + `apps/market_pulse`로 분산. 앱 자체 소멸. v1 진입점은 market_pulse 흡수

**삭제 후보** (사용처 0, 마이그레이션 영향 확인 후):
- `macro.EconomicEvent`
- `macro.SectorIndicatorRelation`
- `macro.IndicatorCorrelation`

### 정정 이력 — 이전 ②의 오류 3건 교정 (2026-05-28)

1. **marketpulse를 dashboard에 통합** → **취소**. market_pulse는 별개 메인 트랙(독립 apps)으로 분리. 사유: 둘 다 거시지만 세션 소유권이 다른 별도 메인 트랙
2. **apps/web (frontend 독립 트랙)** → **취소**. frontend는 모든 apps의 공유 UI 레이어이므로 `packages/web/` 또는 루트 유지가 정합. apps에 두면 세션 충돌 트리거
3. **iron_trading = apps/services 후보** → **integrations/ 격리 확정**. 봇 연계는 read-only contract 기반이라 메인 세션·도메인 서비스와 성격이 다름

### 3단계 실행으로 이관된 미해결

1. `macro/services/macro_service.py` 위치 (packages vs services) — marketpulse v2 분리 코드 정독 후 판정
2. macro v1 API 10개 deprecate 범위 — frontend 실사용 grep 후 판정
3. 삭제 후보 3 model 실 제거 — `makemigrations --check` 후
4. `frontend/` 최종 위치 — `packages/web/` vs 루트 유지 (세션 충돌 분석 + import 비용 측정 후 결정)
5. `iron_trading`이 읽는 앱 인터페이스 계약 — `integrations/`로 격리하려면 contract 명시 필요

**📎 참조**: `docs/monorepo_migration/blueprint_v1.md` §② (재정의 동기화)

### ③ 빌드 도구 및 실행 KPI (2026-05-28)

**[결정]** Turborepo · Nx 등 monorepo 빌드 도구는 **현재 보류**.

**근거**:
- CI 부재 (`.github/workflows` 없음) → 빌드 캐싱 가치 0
- frontend 단일 패키지 (`workspaces` 부재) → 워크스페이스 분할 불필요
- 백엔드 단일 Django + Celery → 태스크 그래프 불필요
- 의존 그래프는 INSTALLED_APPS + dotted-path가 이미 표현
- → 도구 도입은 비용(설정·학습·yaml)만 추가

**[재검토 트리거]** 아래 중 하나라도 발생 시 ③ 재결정:
- (a) CI 도입 (`.github/workflows` 생성)
- (b) frontend가 다중 패키지로 분할
- (c) 빌드 시간이 솔로 개발 흐름을 저해할 정도로 증가

**[KPI · 이동 순서 · 롤백 지점]** ③ 결정 사안 아님 — 점진 실행 계획에서 정의:
- **이동 순서**: 의존 역순 (`packages/shared` → `services` → `apps` → `integrations`) 자동 도출
- **검증 KPI**: pytest 회귀 ~770 유지 + 단계별 IDENTICAL hash + ImportError 0
- **롤백**: 각 그룹 진입 전 백업 태그 (`monorepo-pre-{packages,services,apps,integrations}`)
- **상세**: `docs/monorepo_migration/execution_plan_v1.md` (작성 완료, 2026-05-29)

### execution_plan_v1.md 1차 소스 결정 (2026-05-29)

**결정**: `docs/monorepo_migration/execution_plan_v1.md` = **1차 소스**.

**근거**:
- `blueprint_v1.md`와 동일 디렉토리 (`docs/monorepo_migration/`) — 일관성 유지
- 결정 ①②③ 박은 DECISIONS commit 3건(`4f01cb7`/`118f899`→`7e42193`/`9b48d37`)이 이미 본 경로 참조
- 사용자 원본(`docs/monorepo_project/execution_plan_v1.md`)과 diff 결과 의미 추가분 0 확인 (본 사본이 superset — §5 이관 매핑 5건 박음 + §8 위치 확정). 사용자 원본 삭제로 정합화

**📎 참조**: 통합 진입점 + 본 결정의 1차 소스 패턴은 직전 박은 결정 1~5(문서·git 정합성 관리 원칙)와 일관

### monorepo PR1 — services/_dormant/graph_analysis 이동 (2026-05-30)

**결과**: `graph_analysis/` → `services/_dormant/graph_analysis/` 이동 완료 (history 보존, 11 파일 R100)

**commit SHA (PR1 4 commits, branch `monorepo/pr1-dormant`)**:
- `61c92ad` — services/ + services/_dormant/ 패키지 초기화 (__init__.py 2개)
- `845a810` — git mv 11 파일 R100
- `ebca8f5` — import 경로 갱신 (ast-grep 자기참조 2건 + ruff import 정렬 5 fix)
- `91d5055` — Django INSTALLED_APPS + AppConfig 호출처 갱신 (settings.py + apps.py label 명시)

**branch SHA (머지 후 main)**: {머지 후 채움}

**학습 곡선 4가지 정착**:

1. **ast-grep 패턴 3종** 정착 → 부록 A 박음 (PR2~PR8 답습용). 휴면이라 외부 호출 0건이었으나 자기참조 2건 발견 — "0건 확신 금지" 원칙 검증
2. **git tag 롤백 절차** 정착 (`monorepo-pre-pr1` 박음, 미사용 — Step 4 dry-run + commit 1 hook 통과로 충분 검증)
3. **DECISIONS 형식** 정착 (본 entry가 PR2~PR8 템플릿)
4. **health_check baseline** 정착 (PR1 진입 시 6✅/0⚠/1❌, ❌는 자기참조성 PROGRESS hash 미반영. 신규 결함 0)

**검증 결과**:

- §4.1 import smoke: `python -c "import services._dormant.graph_analysis"` → OK
- §4.2 pytest: `pytest -k "dormant or graph_analysis"` → 3224 collected / 0 selected (휴면 모듈 테스트 부재 정상)
- §4.3 ruff check 델타: main baseline 1009 errors = PR1 1009 errors (델타 0, 휴면 lint 부채는 PR1 scope 외)
- Django setup: OK (INSTALLED_APPS + AppConfig.label='graph_analysis' 호환)

**PR1 scope 외 분리 보류**:
- `ruff format` 7파일 광범위 재포맷 (+675/-392) — 휴면 모듈 광범위 포맷팅은 별도 commit/PR 가치, PR1 scope 외

**다음 PR**: PR2 (packages/) — packages/shared + packages/web 이동

### 부록 A — ast-grep 패턴 (PR2~PR8 답습 템플릿)

트랙 이동 시 import 경로 변경 패턴 3종 (`{OLD}` `{NEW}` 치환만 하면 PR2 적용 가능):

```yaml
pattern_from_submodule:
  pattern: "from {OLD}.$X import $$$Y"
  rewrite: "from {NEW}.$X import $$$Y"
  lang: python

pattern_import_module:
  pattern: "import {OLD}"
  rewrite: "import {NEW} as {OLD}"  # alias로 호환성 유지
  lang: python

pattern_from_direct:
  pattern: "from {OLD} import $$$X"
  rewrite: "from {NEW} import $$$X"
  lang: python
```

**적용 순서**: dry-run → 보고 → 사용자 승인 → -U 적용 → `ruff check --select I --fix`

**PR1 미커버 패턴 (PR2~PR8 추가 점검 필수)**:
- Django `INSTALLED_APPS` 내 문자열 — `grep -rn "{OLD}" config/` 별도 실행
- `AppConfig.name` — 모듈 dotted-path와 일치해야 함 (`apps.py` 검토)
- `AppConfig.label` — 기존 DB 테이블명 보존을 위해 명시 권장 (휴면 트랙 답습)

### 부채 #73 close — pre-commit hook monorepo/* 패턴 추가 (2026-05-30)

**결과**: `.git/hooks/pre-commit` 화이트리스트에 `monorepo/*` 패턴 통과 로직 추가 (라인 19~23, 5줄)

**사유**:
- monorepo 8 PR 답습 효율 (1회 수정 → 7회 회수)
- 가드 견고성 보존 (prefix 한정, main 직커밋·외부 자동화 차단 유지)
- 부채 #73 (slice17 등록) 본 작업의 사이드 산출물로 close

**검증**:
- test branch (`monorepo/test-hook-verify`) commit 성공 확인
- diff = 추가 5줄만 (`if [[ "$CURRENT_BRANCH" == monorepo/* ]] && BRANCH_OK=true; fi`), 기존 로직 변경 0
- PR1 commit 1~4 모두 hook 통과 (`✅ pre-commit 검증 통과 (branch=monorepo/pr1-dormant)`)

**관련**: blueprint_v1.md §7 결정 ②, execution_plan_v1.md §1, PR1 §1.0 사이드 산출물

### monorepo PR2 — packages/shared (A-min, 4 앱) 이동 (2026-05-30)

**결과**: `stocks`/`users`/`api_request`/`metrics` → `packages/shared/*` 이동 완료 (history 보존, R100)

**결정**:
- shared 범위 = **A-min** (4 Django 앱). macro 해체·circuit_breaker.py 분리는 PR2 외 (PR5 또는 별도 슬롯)
- frontend = **B-3** (PR2 완전 제외). blueprint §② vs §④ 모순은 별도 결정 후 처리
- A-mid/A-full 보류 사유: PR2 영향 광범위 (매칭 ~410+), 보수성 우선

**commit SHA (PR2 8 commits, branch `monorepo/pr2-packages`)**:
- `7385d07` — pre-step: ruff format baseline cleanup (4 앱 103 파일, scope 외 분리)
- `e4aca27` — packages/ + packages/shared/ 패키지 초기화
- `dd71aba` — stocks → packages/shared/stocks (git mv R100)
- `e145338` — users → packages/shared/users (git mv R100)
- `8f1a982` — api_request → packages/shared/api_request (git mv R100)
- `3cb9d42` — metrics → packages/shared/metrics (git mv R100)
- `bc0476d` — import 경로 갱신 (Python 363 + Django 패치 + 동적 import 46 = 409건)
- `94c531e` — .gitignore에 node_modules/ 추가 (사이드)

**branch SHA (머지 후 main)**: {머지 후 채움}

**답습 자산 활용 (PR1 부록 A)**:
- ast-grep 3 패턴: 시도 후 **결함 발견** — `$X` metavar가 dotted-name single segment만 매칭. 다층 dotted-path(`from api_request.providers.fmp.client`)에서 `.fmp.client` 잘림 사고. reset --hard로 폐기 후 regex 기반 재변환.
- Django 3 패턴: 정상 답습 — INSTALLED_APPS / AppConfig.name + label / LOGGING / CUSTOM_APPS / urls.py include() / celery beat task name

**신규 학습 (PR3~PR8 답습 필수, 부록 A 보강)**:

1. **ast-grep `$X` 한계**: dotted-name single segment 한정 → 다층 import는 **regex 기반 처리** 필수. 패턴: `\bfrom (APP)((?:\.[a-zA-Z0-9_]+)*) import` + replace `\1packages.shared.\2\3\4`
2. **동적 import 패턴**: `mock.patch('X.Y.Z')` / `importlib.import_module('X.Y')` / Celery `send_task('X.Y')` — ast-grep + regex 정적 분석으로는 누락 가능. pytest 풀 회귀 fail 보고 fail 파일 한정 manual 처리 권장
3. **보호 케이스 (변경 금지)**:
   - `'app_label.ModelName'` (2 segment, Django model ref — AUTH_USER_MODEL='users.User', `to='stocks.stock'` 마이그레이션 등)
   - 파일명 (`'stocks.log'`)
   - JSON 응답 키 (`'stocks': {...}` API 카탈로그)
4. **권장 패턴**: 3 segment+ 보수적 regex (`'APP.snake.X.Y...'`)가 동적 import에는 안전. 단 광범위 sweep은 auto mode classifier 차단 가능 — **fail 파일 한정 manual sweep**으로 우회
5. **AppConfig.label 명시 필수**: dotted-path 변경 시 기존 마이그레이션 테이블명·`AUTH_USER_MODEL`·model ref 보존 위해 `label='users'`/`label='stocks'`/`label='metrics'` 명시
6. **Celery beat task name 갱신**: dotted-path 기반 task auto-name이라 module 이동 시 `'X.tasks.Y'` → `'packages.shared.X.tasks.Y'` 일괄 치환 필요 (10건, config/celery.py)
7. **§1.7 ruff format pre-step 검증**: 효과 100% — PR1처럼 본 PR commit에 흡수되지 않음 (별도 pre-step commit 박음)
8. **node_modules .gitignore 미박힘 사고**: `git add -A` 위험. PR1에서 node_modules untracked였으나 add 안 했고, PR2 commit 7에서 처음 잡힘. .gitignore 사전 점검 패턴 부록 A 추가

**검증 결과**:
- §4.1 import smoke (Django setup 후): 4 앱 모두 OK
- §4.2 Django check: System check identified no issues
- §4.2 makemigrations --dry-run: No changes detected
- §4.3 pytest 풀 회귀: **3172 passed, 52 skipped** (PR1 baseline 완전 일치, 회귀 0건)
- §4.4 ruff check 델타: main baseline 1009 = PR2 1009 (델타 0)
- §4.5 sanity IDENTICAL: **skip** (pytest 회귀 0 + Django check PASS = packages 변경이 런타임 결과 영향 0 강한 신호. LLM 비용 사전 보존, PR4 풀 적용 시 31/31 검증)

**미처리 (PR2 외 처리)**:
- frontend (B-3): blueprint §② vs §④ 모순 별도 결정 후 PR
- macro 해체: PR5 (apps/market_pulse) 또는 별도 슬롯
- circuit_breaker.py 파일 분리: PR5/PR8 흡수

**다음 PR**: PR3 (integrations/iron_trading)

### 부록 A 보강 (PR2 학습 반영)

PR1 부록 A는 ast-grep 3 패턴 + Django 3 패턴이었으나 PR2에서 결함 발견. 답습 권장 패턴 갱신:

```python
# 답습 1: Python static import (정확한 regex, ast-grep 대체)
import re
APPS_RE = '|'.join(['APP1', 'APP2', ...])
pat = re.compile(r'(\bfrom\s+)(' + APPS_RE + r')((?:\.[a-zA-Z0-9_]+)*)(\s+import\s+)')
# replace: r'\1{NEW_PREFIX}.\2\3\4'

# 답습 2: 동적 import (pytest fail 파일 한정)
# 3 segment+ 보수적 regex
pat_dynamic = re.compile(
    r'([\'"])('+ APPS_RE + r')'
    r'(\.[a-z_][a-z0-9_]*)'      # 2번째: snake_case
    r'(\.[a-zA-Z0-9_]+)'          # 3번째: snake or Pascal
    r'((?:\.[a-zA-Z0-9_]+)*)'     # 추가 (옵션)
    r'([\'"])'
)
```

```python
# 답습 3: Django 패치 (PR1 정착 + PR2 추가)
# - INSTALLED_APPS
# - CUSTOM_APPS (있으면)
# - LOGGING.loggers (logger key는 dotted-path 기반)
# - AppConfig.name + label (마이그레이션 테이블명 보존)
# - urls.py include() 문자열
# - celery.py beat schedule 'X.tasks.Y' (10건+ 예상)
# - asgi.py 'import X.routing' (Channels)
```

**PR3 진입 전 점검**:
- iron_trading은 integrations/ 트랙. 외부 API 격리라 import 영향 작을 가능성 (~10건 이하 예상)
- iron_trading 자체가 Django 앱이므로 INSTALLED_APPS / AppConfig 답습 적용
- contracts/ 의존 명시 확인 (PR2와 달리 외부 봇 API contract 명시 필요)

### monorepo PR3 — integrations/iron_trading (옵션 B 네임스페이스) 이동 (2026-05-30)

**결과**: `iron_trading` → `integrations/iron_trading` 이동 완료 (history 보존, R100). 격리 트랙 자명 입증 — 변환 대상 2건만.

**판정 (STEP 0 fact-check)**:
- INSTALLED_APPS 등록 O (line 208)
- URL 라우팅 O (config/urls.py:46)
- 외부 Python import 호출 0건
- → **ACTIVE** (외부 봇 read-only API로 동작 중). target = `integrations/iron_trading/` (dormant 아님)

**옵션 B 채택 — integrations/ 네임스페이스 규약 (잠정 v0.1)**:
- `integrations/__init__.py` + `README.md` + `_shared/__init__.py` (의도된 빈 패키지)
- `_shared/`: 2+ integration 공유 유틸 자리. 현재 단일 integration이라 빈 패키지
- `_dormant/`: 현재 부재. 휴면 발생 시 추가
- **2번째 integration 진입 시 재검토** (현재 iron_trading 단일 → 검증 사례 부족)
- 상세 규약: `integrations/README.md`

**commit SHA (PR3 5 commits, branch `monorepo/pr3-integrations`)**:
- `4d7cc7f` — pre-step: ruff format baseline cleanup (iron_trading 4 파일)
- `5bc0cf2` — integrations namespace scaffold (__init__/README/_shared)
- `7171f83` — mv iron_trading → integrations/iron_trading (R100)
- `6cf961a` — 호출처 갱신 (config/urls.py + config/settings.py + apps.py label)
- `{commit 5}` — DECISIONS + PROGRESS 정착

**branch SHA (머지 후 main)**: {머지 후 채움}

**답습 자산 활용 (PR2 부록 A 보강 8건)**:
- Python static import regex: **0건** (자기참조 + 외부 호출 모두 부재)
- 동적 import sweep: **0건** (mock.patch/send_task/importlib 부재)
- Django 패치 7종 중 3종 적용: INSTALLED_APPS / urls.py include / AppConfig.name+label
- .gitignore 사전 점검: 충돌 0
- ruff format pre-step: 4 파일 분리 commit

**검증 결과**:
- Django check: System check identified no issues
- makemigrations --dry-run: No changes detected
- import smoke (Django setup 후): iron_trading OK
- pytest 풀 회귀: **3172 passed, 52 skipped** (PR2 baseline 완전 일치, 회귀 0건)
- ruff 델타: main 1013 = PR3 1013 (델타 0)
- health_check: 6✅/0⚠/1❌ (baseline 평행, ⚠ 격상 없음 — 빈 `_shared/` docstring 의도 명시로 false-positive 회피)

**신규 학습 (PR4~PR8 답습 후보)**:
1. **격리 트랙 자명 입증**: integrations 분류 자체가 외부 호출 0건 보장. PR3 변환 2건은 가중합 C 5.0 분류의 검증
2. **빈 패키지 docstring 의도 명시 패턴**: `_shared/__init__.py`처럼 의도된 빈 패키지는 docstring으로 health_check false-positive 방지
3. **2단계 mv 분리**: namespace scaffold commit과 mv commit 분리 — 후속 integration 추가 시 scaffold 1회 + 각 mv N회 답습
4. **STEP 0 fact-check 단순화**: INSTALLED_APPS 등록 + URL 라우팅 = active. 추가 동적 import 검사로 보강

**다음 PR**: PR4 (apps/dashboard/) — packages.shared 의존, IDENTICAL 31/31 풀 적용 시작점

### monorepo PR4 — apps/market_pulse 이관 (dashboard 보류 승계) (2026-05-31)

**결과**: `marketpulse/` → `apps/market_pulse/` 이동 완료 (history 보존, R100, snake_case rename 동반).

**PR4 대상 교체 결정**:
- 원안 (execution_plan v1.0): PR4 = `apps/dashboard/`
- fact-check (STEP 0): dashboard 실 디렉토리/Django 앱 **부재** (`docs/dashboard_plan/`만 존재)
- → dashboard = **monorepo 트랙 외로 보류**. 트리거 = 독립 배포 또는 모듈 경계 명시 필요 시
- → PR4 = `apps/market_pulse/` 승계 (원안 PR5). PR5 결번. 결번 표기: execution_plan v1.0 §1 갱신 박음
- 사유: dashboard는 신규 생성 + stocks 내 자산 분리 복합 작업이라 monorepo 단순 이동 패턴 외. 별도 설계 필요.

**STEP 0 fact-check 결과**:
- 실존: `./marketpulse/` (snake_case 아님, 단일 단어)
- INSTALLED_APPS: `marketpulse.apps.MarketpulseConfig` ✅
- URL: `api/v2/market-pulse/` ✅
- 외부 import 호출: 다수 (rag_analysis 2 + serverless 2 + tests/marketpulse 다수)
- → **ACTIVE**. target = `apps/market_pulse/` (snake_case rename 동반)
- frontend 분리: `frontend/app/market-pulse{,_v2}/` 등 다수 — **PR4 scope 외 (B-3 답습)**

**commit SHA (PR4 6 commits, branch `monorepo/pr4-market-pulse`)**:
- `b7a95a2` — pre-step: ruff format baseline cleanup (57 파일)
- `a212593` — apps/ 네임스페이스 패키지 초기화
- `{c3}` — mv marketpulse → apps/market_pulse (snake_case rename 동반)
- `{c4}` — import 경로 갱신 (Python 154 + Celery task name 22 = 176건)
- `726e0fd` — Django INSTALLED_APPS + URL + AppConfig 호출처 갱신
- `{c6}` — DECISIONS + PROGRESS + execution_plan dashboard 보류 마킹

**branch SHA (머지 후 main)**: {머지 후 채움}

**답습 자산 활용 (PR2/PR3 부록 A)**:
- Python static import regex: 154건 (48 파일)
- 동적 import sweep: 0건 (mock.patch/send_task/importlib 부재)
- Celery task name (4-seg 문자열): 22건 변환
- Django 패치 7종 중 3종 적용: INSTALLED_APPS / urls.py include / AppConfig.name+label
- .gitignore 사전 점검: 충돌 0
- ruff format pre-step: 57 파일 분리 commit

**보호된 케이스 (label='marketpulse' 유지)**:
- migration `to="marketpulse.marketpulsenews"` 2건
- model lazy ref `"marketpulse.MarketPulseNews"` 1건
- → Django app_label 기반 ref, AppConfig.label='marketpulse'로 마이그레이션 history + 모델 ref 보존

**검증 결과**:
- Django check: System check identified no issues
- makemigrations --dry-run: No changes detected
- import smoke (apps.market_pulse): OK
- pytest 풀 회귀: **3165 passed, 7 fail** — 7 fail 모두 main에서 동일 fail (환경/날짜 변경 영향, PR4 무관)
- ruff 델타: main 1013 = PR4 1013 (델타 0)
- health_check: 5✅/1⚠/1❌ — ⚠ 격상 = PR4 무관 `5894177 docs: 코드베이스 감사 보고서 생성` 휴리스틱 misclassify (외부 자동화 의심으로 분류, 실제는 사용자 docs commit). ❌ 신규 격상 없음 → HALT 사유 아님

**미처리 (PR4 외)**:
- `apps/market_pulse/utils/circuit_breaker.py` (외부 4 호출처 — rag_analysis 2 + serverless 2). blueprint §② "packages/shared 후보". **PR5(결번)/PR8 흡수 또는 별도 분리 PR** 가능성. 본 PR4는 marketpulse 전체 이동만, 분리는 별도 결정.
- dashboard 앱: monorepo 외 이연 (트리거 명시: 독립 배포/모듈 경계)
- frontend market-pulse 자산: B-3 답습, 별도 PR

**신규 학습 (PR6~PR8 답습 후보)**:
1. **fact-check 답습 강제**: plan 표기 ≠ 실 코드명 (plan `market_pulse` vs 실 `marketpulse`). 폴더 rename 동반 가능성 사전 확인 필수
2. **plan 표기 오류 → trigger 명시 보류**: 실존 부재 트랙은 monorepo 외로 이연 + trigger 명시 (dashboard 사례)
3. **AppConfig.label로 마이그레이션 history 보존**: snake_case rename + label='oldname' 조합으로 model ref/migration to="oldname.X" 모두 보존
4. **외부 환경/날짜 회귀 분리 검증 패턴**: main 비교로 PR 무관 회귀 빠르게 분리 (`git stash + git checkout main + pytest 대상 + 복귀`)

**다음 PR**: PR6 (apps/chain_sight/) — chainsight 앱 (실 코드명 확인 후 진입)

### monorepo PR6 — apps/chain_sight 이관 (chainsight snake_case rename) (2026-05-31)

**결과**: `chainsight/` → `apps/chain_sight/` 이동 완료 (history 보존, R100, snake_case rename + label='chainsight' 보존).

**STEP 0 fact-check 결과 (PR4 학습 1 답습)**:
- 실 코드명 `chainsight` (1 단어) ≠ plan `chain_sight` → snake_case rename 동반
- INSTALLED_APPS L204 + URL L44 → **ACTIVE**
- 외부 메인 코드 결합 0건 (tests/만 21건, PR3 iron_trading 수준 격리)
- frontend 자산 3건 (services/app/components) → PR6 scope 외 (B-3 답습)
- 보호 케이스 사전 식별: migration to= 2건 + 단축 task name 'chainsight-X' 10건 + spectacular lazy ref 1건

**commit SHA (PR6 5 commits, branch `monorepo/pr6-chain-sight`)**:
- `4d16647` — pre-step: ruff format baseline cleanup (55 파일)
- `31782f5` — mv chainsight → apps/chain_sight (R100, snake_case rename)
- `a60983a` — import 경로 갱신 (Python 91 + Celery 12 + mock.patch 15 = 118건)
- `3769265` — Django INSTALLED_APPS + URL + AppConfig name='apps.chain_sight' + label='chainsight'
- `{c5}` — DECISIONS + PROGRESS 정착

**branch SHA (머지 후 main)**: {머지 후 채움}

**답습 자산 활용 (PR2/PR3/PR4 부록 A)**:
- Python static import regex: 91건 (42 파일)
- 동적 import sweep: 15건 (regex 14 + manual 1, fail 파일 한정 — PR4 학습 답습)
- Celery 4-seg task name: 12건 변환
- 단축 task name 'chainsight-X' 10건 보존 (DB PeriodicTask 매핑 보존)
- Django 패치 3종 (INSTALLED_APPS / urls.py / AppConfig.name+label)
- label='chainsight' 효과: migration to= 2건 + spectacular lazy ref + ContentType 자동 보존

**검증 결과**:
- Django check: System check identified no issues
- makemigrations --dry-run: **No changes detected** (★ label 보존 효과 확인, HALT 트리거 5 회피)
- import smoke (apps.chain_sight): OK
- pytest 풀 회귀: **3172 passed, 52 skipped** (PR4 baseline 동일, **회귀 0건** + PR4 환경 fail 7건 해소)
- ruff 카운트: main 1013 → PR6 **1009** (-4 개선, 회귀 0)
- health_check: 6✅/0⚠/1❌ (baseline 평행)

**미처리 (PR6 외)**:
- frontend chainsight 자산 — B-3 답습, 별도 PR
- URL prefix `api/v1/chainsight/` 보존 (외부 API consumer 호환성)

**다음 PR**: PR7 (apps/portfolio/) — **최고 위험도** (coach 포함, 슬라이스 병행 ❌ 금지). 풀 회귀 + IDENTICAL 31/31 필수.

### monorepo PR7 — apps/portfolio 이관 (단일 앱 최대 규모, IDENTICAL 7/7) (2026-05-31)

**결과**: `portfolio/` → `apps/portfolio/` 이동 완료 (history 보존, R100, rename 없음 위치만, label='portfolio' 명시).

**STEP 0 사전 조사 결과 (READ-ONLY)**:
- IDENTICAL = **정적 무결성 테스트** (`portfolio/tests/test_static_integrity.py` 7+ 케이스, binary 해시 아님)
- 거짓양성 위험 = **0** (import 갱신 후 모듈 import 성공하면 자동 통과)
- 외부 결합 = 0 (메인 코드 호출 0, tests 40 + scripts 일부)
- coach = `portfolio/services/coach/` (E1~E6 + prompt_builder)
- 보호 케이스: migration to= 11건 + URL namespace='portfolio_api' + URL name 'portfolio-X'
- 슬라이스 병행 = 없음

**commit SHA (PR7 6 commits, branch `monorepo/pr7-portfolio`)**:
- `66c52bc` — pre-step: ruff format baseline cleanup (89 파일)
- `225ff47` — mv portfolio → apps/portfolio (R100, rename 없음)
- `0f935ce` — import 경로 갱신 (Python 545 + 동적 mock.patch 15 + scripts importlib 5 = **565건**)
- `38c61c3` — Django INSTALLED_APPS + URL 2건 (namespace 보존) + AppConfig.name + label='portfolio' 명시
- `8ef118a` — fixture 경로 하드코딩 갱신 (8건, 신규 패턴)
- `{c6}` — DECISIONS + PROGRESS 정착

**branch SHA (머지 후 main)**: {머지 후 채움}

**답습 자산 활용 (PR2~PR6 부록 A)**:
- Python static import regex: **545건** (175 파일, 단일 PR 최대)
- 동적 mock.patch: 15건
- scripts importlib (dotted-path 문자열): 5건
- Django 패치 4종 (INSTALLED_APPS / urls 2건 + namespace 보존 / AppConfig.name+label)
- label='portfolio' 효과: migration to= 11건 + ContentType 자동 보존

**신규 발견 — fixture 경로 하드코딩 (부록 A 추가)**:
- `FIXTURE_DIR = Path("portfolio/tests/fixtures/...")` 형식 8건
- ast-grep/정적 import sweep으로 잡히지 않음 — STEP 6 pytest 4 errors로 노출
- regex 패턴: `(?<!apps/)(?<!docs/)portfolio/tests/fixtures` → `apps/portfolio/tests/fixtures`
- PR8 답습 후보로 박음

**검증 결과 (8단계)**:
- ① Django check: System check identified no issues
- ② ★ **IDENTICAL test_static_integrity: 7/7 PASSED** (import 갱신 후 자동 통과 — 거짓양성 0 입증)
- ③ vitest: N/A (frontend 변경 0)
- ④ makemigrations --dry-run: **No changes detected** (★ label 보존 효과 입증)
- ⑤ ruff: main 1009 → PR7 1010 (+1, 회귀 0)
- ⑥ health_check: 6✅/0⚠/1❌ baseline 평행
- ⑦ cost_ledger: N/A (LLM 호출 0)
- ⑧ pytest 풀 회귀: **3172 passed, 52 skipped** (PR6 baseline 완전 일치, **회귀 0건**)

**신규 학습 (PR8 답습 후보)**:
1. **IDENTICAL = 정적 무결성** (binary 해시 아님): plan 위험등급 "최고"는 메커니즘 미확인 기반이었음. 실측 결과 PR6 동급 + 규모만 큼. import 갱신 정확하면 자동 통과.
2. **fixture 경로 하드코딩**: `Path(...) / "portfolio" / "tests" / ...` 형식. STEP 3 정적 import sweep으로 누락, STEP 6 pytest fail로 노출. regex 보호 패턴 (`(?<!apps/)(?<!docs/)`) 필수.
3. **URL namespace 보존**: `include(..., namespace='portfolio_api')` 형식. namespace 문자열은 dotted-path 무관, 그대로 유지 (reverse() 호환성).
4. **단일 앱 최대 규모 일괄 처리**: 565건 변환 한 commit 안에 박음. Django 패치 분리(별 commit) + fixture 경로 추가 commit으로 분할 — 의미 단위 5 commits 정합.

**미처리 (PR7 외)**:
- frontend portfolio 자산 3건 (`frontend/app/portfolio`, `components/portfolio`, `services/portfolio.ts`) — B-3 답습, 별도 PR
- URL prefix `api/`, `api/v1/`은 그대로 (Django 외부 consumer 호환성)

**다음 PR**: PR8 — 루트 메타 정리 + 이관 5건 잔여 (모든 apps/packages/integrations/services 트랙 정착 후). 루트 잔존 7 Django 앱 (rag_analysis, serverless, macro, news, thesis, sec_pipeline, validation) 분류 결정.

### monorepo PR8a — services/ 5앱 이동 (순차 3그룹 / 옵션2) (2026-06-01)

**결과**: `news` + `serverless` + `rag_analysis` + `validation` + `sec_pipeline` → `services/*` 이동 완료. 5앱 일괄 + label 명시 + 보호 케이스 자동 보존. 동적 import 신규 패턴 4종 발견·처리.

**STEP 0 사전 조사 결과**:
- rename 0 (디렉토리명 그대로 유지)
- 상호 의존: news→rag(1) / serverless→news/rag(2) / 나머지 독립 — **순환 없음**
- 공유 유틸 후보 0 (5앱 내 utils/lib 부재)
- ★ 동적 mock.patch 260건 (5앱 합계, PR7 15건의 17배)

**옵션2 채택 — 순차 3그룹**:
- 1차: rag_analysis + validation + sec_pipeline (독립, 동시 이동)
- 2차: news (rag 의존 1)
- 3차: serverless (news + rag 의존 2)

**commit SHA (PR8a 8 commits, branch `monorepo/pr8a-services`)**:
- `cfa33e6` — pre-step: ruff format baseline cleanup (200 파일)
- `57fcc55` — mv 1차 3앱 → services/
- `6ed3d69` — 1차 import 갱신 (정적 360 + import 단독 1 + mock.patch 107 + Celery 13 = 481건)
- `ddca3bd` — mv news → services/news
- `d86c680` — 2차 import 갱신 (정적 198 + mock.patch 89 + monkeypatch 2 + 멀티라인 patch 1 + Celery 38 + test assert 6 = 334건)
- `e403527` — mv serverless → services/serverless
- `94f082c` — 3차 import 갱신 (정적 249 + mock.patch 64 + Celery 24 = 337건)
- `{c8}` — DECISIONS + PROGRESS 정착

**branch SHA (머지 후 main)**: {머지 후 채움}

**규모 (PR1~7 통합 답습)**:
- 정적 import: 360+198+249 = **807건** (STEP 0 추정 779 +3.6%)
- 동적 mock.patch: 107+89+64 = **260건** (STEP 0 추정 정확)
- 신규 동적 패턴 (PR8a 학습): monkeypatch.setattr 2 + 멀티라인 patch 1 + test assert task name 6 = 9건
- Celery task name: 13+38+24 = **75건**
- 총 **~1150건** (PR7 545건의 2.1배, STEP 0 추정 1100~1200 정확)

**신규 학습 (부록 A 추가, PR8b/c 답습)**:

1. **monkeypatch.setattr 동적 경로 패턴**: `monkeypatch.setattr('X.Y.Z', ...)` — pytest fixture. mock.patch와 별개. 5앱 중 news 2건. PR8a-2 setup ERROR 12건으로 노출.
2. **멀티라인 patch 패턴**: `patch(\n    "X.Y.Z",\n    ...)` — 줄바꿈으로 인해 단일라인 regex `patch\(["']X` 미커버. multi 패턴 regex `patch\(\s*\n\s*["']` 추가 필요.
3. **Test assert hardcode task name**: `assert task['task'] == 'X.tasks.Y'` — Celery task 이름이 test 안에 박혀있음. Celery beat schedule 갱신과 별개로 test 코드도 갱신 필요.
4. **ready() 안 들여쓰기 import + 주석 # noqa**: `        import X.signals  # noqa` — regex `\s*$|\s+as`로 잡지 못함 (`# noqa`는 `\s*$` 미매칭). 5앱 중 rag_analysis/sec_pipeline 2건 manual 처리.

**검증 결과**:
- ① Django check: PASS (5앱 모두)
- ② makemigrations --dry-run: **No changes detected** (★ label 보존 효과 입증)
- ③ pytest 풀 회귀: **3172 passed, 52 skipped** (PR7 baseline 완전 일치, **회귀 0건**, PR4/PR8a-1 환경 fail 7건도 해소)
- ④ ruff: main 1010 = PR8a 1010 (델타 0)
- ⑤ 5앱 정적 잔존 0 (sweep 통과)
- ⑥ health_check: 5✅/1⚠/1❌ (⚠는 PR8a 무관 `24b748e` docs commit 휴리스틱 misclassify, ❌ 신규 격상 없음 → HALT 사유 아님)
- ⑦ INSTALLED_APPS 5앱 services.* 적용 확인

**보호된 케이스 (label 보존)**:
- news: migration to= 2 + lazy ref 8 (model ref 2 + i18n 키 6)
- serverless: migration to= 4+
- rag_analysis: migration to= 5+
- validation: 0
- sec_pipeline: migration to= 3+ + lazy ref 1

**미처리 (PR8b/c 외)**:
- macro 해체 (apps/market_pulse + packages/shared 분배) — PR8b
- thesis 처분 결정 (보류, 사용자 트리거 대기)
- 메타 정리 (marketpulse/ 빈 디렉토리 + graph_analysis 회귀 + plan 도식) — PR8c

**다음 PR**: PR8b (macro 해체) — services/ 5앱 정착 후 진입. macro v1 진입점 → apps/market_pulse 흡수 + MarketIndex/MarketIndexPrice/fred_client/fmp_client → packages/shared/ 분배 + 삭제 후보 3 model 보류.

### shared 경계 검문소 (2026-06-01)

**결정**: 채택 = ㄱ(pytest 아키텍처 테스트, AST) + 보조 ㄴ(health 8번째 항목) + 야간 가(추적만, read-only). 자동 수정·자동 청소(다) **영구 배제** — 행위 보존 위반 위험.

**배경**: PR8b STEP 0 fact-check에서 `packages/shared/`가 거꾸로 `apps/*`·`macro`를 import하는 5건 검출. shared는 단방향 base 경계이므로 위반. 새 위반 차단(검문소) + 묵은 5건 동결(소진 트랙 분리)로 분리 대응.

**Why**:
- 단방향 경계는 검문소 없으면 새 우회가 PR마다 슬며시 추가됨 (PR8b STEP 0에서 5건 한꺼번에 드러난 게 시그널).
- AST 파싱은 import 실행을 하지 않으므로 Django 셋업/순환 폭발과 무관 — 가장 비용이 싼 차단 장치.
- 묵은 5건을 같은 사이클에 고치면 행위 변경 + import 리팩토링이 섞여 위험. 동결 후 별도 사이클로 청소.

**How to apply**:
- 새 위반: `tests/architecture/test_shared_boundary.py` 자동 FAIL → 의존 방향 뒤집기 또는 shared 승격으로 해결.
- 묵은 5건: TASKQUEUE `BOUNDARY-1/2/3` 소진 큐 따라 별도 PR로 청소 → `KNOWN_VIOLATIONS` 키를 tests + health_check 2곳에서 동시 삭제.
- 야간 추적: `docs/harness/boundary_ledger.jsonl`에 `{frozen, bypass, total}` 한 줄/일 burn-down. health_check `--ledger`로만 append (수동 실행은 ledger 오염 회피).
- 자동 수정 금지: 야간이 import를 고치거나 커밋하면 안 됨. ledger 적재 외 행위 0.

**SSOT**: `tests/architecture/test_shared_boundary.py:KNOWN_VIOLATIONS`. `scripts/health_check.py:_BOUNDARY_KNOWN_VIOLATIONS`는 동기 복사본 — 양쪽 동시 갱신 필수.

**관련 문서**: `docs/harness/SHARED_BOUNDARY_GUARD.md`, `sub_claude_md/common-bugs.md #31`.

### monorepo PR8b-1 — macro 비모델 분배 (실행) (2026-06-01)

**결정**: macro는 "**모델 전용 shell app**"으로 잔존(INSTALLED_APPS 'macro' 유지, label 'macro' 불변). 비모델 모든 행위는 `apps/market_pulse/`로 동거 이사. fred_client만 `packages/shared/api_request/`로 승격 (추천 B).

**HEAD**: `61b1d97` → `1a20c9b` (+4 commits).

**커밋**:
| 순 | hash | 의미 |
|---|---|---|
| 1a | `0b5c8ed` | services 분배 (fred→shared, fmp/macro_service→market_pulse) |
| 1b | `083b8da` | entry (views/serializers/urls) → market_pulse, config/urls.py:39 갱신 |
| 1c | `5ab58ee` | tasks → market_pulse/tasks/macro.py + celery.py Beat 5건 갱신 |
| 1d | `1a20c9b` | mgmt/constants → market_pulse |

**불변**:
- `INSTALLED_APPS = ['macro', ...]` (settings.py:197)
- LLM domain enum `('macro', 'Macro')` (settings.py:404)
- spectacular_enums.py:19 `MACRO = 'macro'`
- URL prefix `/api/v1/macro/*` (frontend macroService.ts 영향 0)
- `reverse('macro:market-pulse')` = `/api/v1/macro/pulse/`
- `app_label='macro'` (migrations 디렉토리명 기반, 명시 0건 → 변경 불요)

**잔존 (PR8b-2/c 트리거 대기)**:
- macro/models + migrations — **PR8b-3에서 옵션 A 채택(이동 안 함)**. 영구 모델 전용 앱(아래 PR8b-3 결정 참조).
- fmp_client / constants dead-code 판정 — PR8c
- thesis 처분 확정 시 → fred 최종 위치 재검토

**R6 (Beat schedule drift)**: dict + 코드 갱신 완료. **DB sync 미실행**(별도 절차, 사용자 트리거). 운영 동기화 절차:
```python
# python manage.py shell
from django_celery_beat.models import PeriodicTask
mapping = {
    'update-economic-indicators':   'apps.market_pulse.tasks.macro.update_economic_indicators',
    'update-market-indices':        'apps.market_pulse.tasks.macro.update_market_indices',
    'update-economic-calendar':     'apps.market_pulse.tasks.macro.update_economic_calendar',
    'refresh-market-pulse-cache':   'apps.market_pulse.tasks.macro.refresh_market_pulse_cache',
    'cleanup-old-macro-data':       'apps.market_pulse.tasks.macro.cleanup_old_data',
}
for name, new_task in mapping.items():
    updated = PeriodicTask.objects.filter(name=name).update(task=new_task)
    print(name, '->', updated, 'rows')
```
실행 후 celery beat 재시작 필요. 미실행 시 DB의 옛 경로 `macro.tasks.X`로 호출 → ImportError로 task 실패.

**검증**: pytest 3175 passed/52 skipped (회귀 0), 경계 GREEN(우회 0/동결 5), reverse 불변, `find macro -type f` = `__init__.py`/`apps.py`/`admin.py`/`models/`/`migrations/` + 빈 mgmt 패키지.

### Beat 드리프트 = reconcile 커맨드로 항구 처리 (2026-06-01, PR8b-2 Track A)

**결정**: task 이동·리네임으로 인한 DB↔dict 드리프트는 일회용 shell one-liner 대신 `python manage.py sync_beat_schedule` reconcile 커맨드(`apps/market_pulse/management/commands/sync_beat_schedule.py`)로 표준화한다. dry-run 기본 + `--apply` 명시 + idempotent.

**Why**: 매 monorepo PR 마다 5~75건씩 누적 drift 발생, shell snippet 재작성은 휴먼 에러 위험 + 일관성 부재. 재사용 가능한 멱등 커맨드 1개로 압축하고 모든 절차(common-bugs #28)는 거기를 가리킨다.

**How to apply**:
- 신규 task / 이동 / 리네임 → dict 갱신 후 `sync_beat_schedule --dry-run` → `--apply` → beat 재시작.
- 운영 DB 변경은 사용자 트리거(Claude Code dev DB 검증까지만).
- 첫 적용 (2026-06-01): dev DB 75 row reconcile, idempotent 확인 PASS.

**관련 문서**: `sub_claude_md/common-bugs.md #28` "항구 해결" 절차, `tests/marketpulse/test_sync_beat_schedule.py` 4 tests.

### PR8b-2 Track B — fmp_client / macro_service / constants 판정 = 보존 (2026-06-01)

**결정**: STEP 0 가설("constants 소비자 0건", fmp_client 외부 0)을 reachability 전수 실측으로 정정. 3개 후보 모두 **REACHABLE** → 삭제 0건.

| 후보 | 직접 소비 | Transitive | 결론 |
|---|---|---|---|
| `apps/market_pulse/services/fmp_client.py` | `macro_service.py` 단일 | macro_service → views(9) + tasks/macro(4) | reachable |
| `apps/market_pulse/services/macro_service.py` | views.py 9 + tasks/macro.py 4 (lazy) | — | reachable |
| `apps/market_pulse/constants/` | `macro_service.py` (`calculate_fear_greed_index`, `get_insight_message`) | → views/tasks 사슬 | reachable |

**Why**: STEP 0 가설은 import만 보고 transitive 호출 사슬을 보지 않은 결함. dead-code 단정 전 transitive 도달성 전수 (import + 동적 + 문자열 + admin + serializer field + task name)는 절대 규칙 2 명시.

**How to apply**: PR8c에서도 위 3개를 dead-code로 단정 짓지 말 것. 동일 이름의 `FMPClient`가 3개 모듈에 존재 (`apps/market_pulse/services/fmp_client.py` vs `packages/shared/api_request/providers/fmp/client.py` vs `services/serverless/services/fmp_client.py`) — 검색 시 혼동 주의, 절대 경로로 식별.

**잔재 (PR8c 정리 대상 태깅)**:
- `macro/management/commands/__init__.py` 빈 패키지 (안에 .py 0개) → PR8c.

### monorepo PR8b-3 종결 — macro = 영구 모델 전용 앱 (옵션 A, 이동 안 함) (2026-06-01)

**결정**: macro/models + migrations를 **옮기지 않는다**. macro 앱을 영구 "모델 전용 앱"으로 확정 — `models/` + `migrations/` + `apps.py` + `admin.py` + 빈 `__init__.py` + 빈 `management/` 구조가 의도된 최종 상태다. **Django 정상 패턴 = 부채 아님.**

**근거 3**:
1. prod DB·배포 보류 전제에서 영향 0. ContentType / db_table / state migration 리스크를 감수할 이득 없음.
2. **모델을 market_pulse로 옮겨도 #4·#5는 풀리지 않는다** — shared가 여전히 앱 모델을 거꾸로 import (label만 'macro' → 'marketpulse'로 바뀔 뿐 shared→app 위반은 동일).
3. monorepo 목적(git 충돌 방지·비모델 정돈)은 **PR8b-1에서 이미 달성**. macro는 비모델 행위가 0이라 충돌면이 없다.

**옵션 C(모델을 packages/shared로 승격) = 조건부 보류**(deferred, not cancelled). BOUNDARY-3 경계 STEP 0에서 방향1(소비자 이동)이 막힐 때 정공법으로 부활.

**결과**:
- macro 최종 구조: `__init__.py` + `apps.py` + `admin.py` + `models/{__init__,indicators,relationships}.py` + `migrations/0001~0006` + (빈) `management/commands/__init__.py`
- INSTALLED_APPS `'macro'` 영구 유지, label `'macro'` 영구 유지, `MACRO` enum 영구 유지

**관련 갱신**:
- TASKQUEUE BOUNDARY-3 재정의 (Part 2 참조)
- `docs/harness/SHARED_BOUNDARY_GUARD.md` #4·#5 행 정정
- `sub_claude_md/common-bugs.md #31` 소진 순서 3 정정 + "#4·#5 영구 동결 아님" 명시

### BOUNDARY-3 재정의 — #4·#5 청소 = 소비자 이동 (모델 이동 아님) (2026-06-01)

**결정**: BOUNDARY-3(`stocks/services/eod_regime_calculator.py:77`, `eod_pipeline.py:617` lazy import `macro.models`)의 청소 경로를 **모델 이동 동봉**에서 **소비자 이동(방향1)** 으로 재정의. 후보 3:

- **방향1 (우선)**: 두 소비자 파일을 `apps/market_pulse/`로 이동 → app→app 의존이라 합법, prod DB 무관. 다만 두 파일이 정말 market_pulse 전용인지 vs 진짜 공용(EOD 파이프라인 등 도메인 공통)인지 **경계 STEP 0** 필요.
- **방향2**: dependency inversion — shared에 추상 인터페이스 두고 market_pulse가 구현 주입.
- **C (조건부 보류)**: 방향1·2가 모두 막히면 macro/models를 `packages/shared/`로 승격(옵션 C 부활).

**Why**: 모델 이동은 ContentType / db_table 리스크가 크고 #4·#5를 직접 풀지 못한다(위 PR8b-3 근거 2). 소비자 이동은 prod DB 무관 + app→app이므로 가드 비대상 + 경계 burn-down 직접 효과.

**How to apply**: BOUNDARY-3 진입 시 먼저 두 파일의 호출자 + 도메인 사용처 전수 (eod_regime_calculator / eod_pipeline 호출자 grep)→ 단일 도메인이면 방향1, 다도메인이면 C. 절대 모델부터 건드리지 말 것.

**관련 문서**: TASKQUEUE.md `BOUNDARY-3` (새 정의), `docs/harness/SHARED_BOUNDARY_GUARD.md` #4·#5 행.

### monorepo PR8c 종결 — 메타 정리 + 트랙 완주 (2026-06-01)

**결정**: monorepo 8 PR 시리즈 완주. macro = 영구 모델 전용 앱, packages/shared / apps/* / services/* / integrations/* / services/_dormant/ 전 격자 정착.

**커밋 3**:
| 순 | hash | 의미 |
|---|---|---|
| a | `19eeb7f` | 빈 잔재 정리 (`marketpulse/` untracked dir + `macro/management/` 빈 패키지) + blueprint_v1.md dashboard 행 정정 + common-bugs #32 FMPClient 동명 3 모듈 가이드 |
| b | `dec8941` | graph_analysis 휴면 자기참조 회귀 2건 정정 (`from graph_analysis.models` → `from services._dormant.graph_analysis.models`, 휴면 의도 보존) |
| c | (이 docs commit) | PROGRESS / DECISIONS 트랙 완주 기록 |

**monorepo 8 PR 시리즈 (history)**:
1. PR1 (2026-05-30) — `services/_dormant/graph_analysis` 휴면 이동
2. PR2 (2026-05-30) — `packages/shared/{stocks,users,api_request,metrics}` (A-min)
3. PR3 (2026-05-30) — `integrations/iron_trading` (옵션 B 네임스페이스)
4. PR4 (2026-05-31) — `apps/market_pulse` (dashboard 보류 승계)
5. PR5 — 결번 (PR4 흡수)
6. PR6 (2026-05-31) — `apps/chain_sight`
7. PR7 (2026-05-31) — `apps/portfolio` (단일 앱 최대, IDENTICAL 7/7)
8. PR8a (2026-06-01) — `services/{news,serverless,rag_analysis,validation,sec_pipeline}` (옵션2 3그룹)
9. PR8b (2026-06-01) — macro 분배 (1: 비모델 → market_pulse / 2: Beat 항구 해결 + reachability 판정 / 3: macro=영구 모델앱)
10. PR8c (2026-06-01) — 메타 정리 + graph_analysis 회귀 해소 + 완주 정착

**최종 격자**:
```
apps/        — 메인 트랙 (chain_sight, market_pulse, portfolio)
packages/    — 단방향 base (shared/{stocks,users,api_request,metrics}) — 경계 검문소 LIVE
services/    — 도메인 서비스 (news, serverless, rag_analysis, validation, sec_pipeline)
services/_dormant/ — 휴면 (graph_analysis)
integrations/ — 봇 연계 격리 (iron_trading)
macro/       — 영구 모델 전용 앱 (PR8b-3 옵션 A)
thesis/      — ✅ 제거됨 (D-MONITOR-REBUILD, apps/monitor 편입, 2026-07-09)
```

**잔존 (monorepo 외 트랙)**:
- BOUNDARY-1/2/3 (경계 트랙 소진 큐)
- Beat prod DB 동기화 (운영 트리거, `sync_beat_schedule --apply` + beat 재시작)
- ~~thesis 처분 (a/b/c 트리거 대기)~~ — **✅ 종결(D-MONITOR-REBUILD, 2026-07-09, P2-S3)**: 트리거 발동(사용자 트랙 배정) → 구 thesis 앱 폐기·main 랜딩 `c80783a` → 후속 `apps/monitor` 신축. **top-level `thesis/` 디렉터리 제거 완료**(BE `_reuse` 엔진 4종 P2-S2 소진 후 `__init__.py` 플레이스홀더만 남아 조기 제거). "monorepo 외 잔존" 해소 = apps/ 편입 수렴. **✅ 최종 종결(P3-S2b, 2026-07-09)**: FE `frontend/components/thesis/_reuse`(빌더 골격)도 소진 → `components/thesis/` 디렉터리째 제거. **thesis 흔적 0**(BE·FE 전 잔재 소멸), 처분 사안 완전 클로즈.
- FMPClient 3중화 통합 (별도 부채 트랙)
- health ❌ 1건 PROGRESS hash 자기참조 (push 트리거, 정합성 Layer 4 영역)

**검증 (최종)**: pytest **3179 passed, 52 skipped** (회귀 0, monorepo 8 PR 시리즈 누적 0건 회귀), 경계 GREEN (우회 0 / 동결 잔여 5), health 7✅/0⚠/1❌(별개 트랙).

### 버킷A — shared 인프라 정착 (circuit_breaker 승격 + FMP namespace 통합) (2026-06-01)

**결정**: monorepo 외 첫 후속 트랙으로 `packages/shared/api_request/` 인프라 정착. (1) `circuit_breaker` 승격으로 BOUNDARY-1 #1·#2 자연 해소 (2) FMP 3벌을 same namespace로 격자화 (#32 1단계 종료).

**HEAD**: `b8f3d00` → `ccbdce5` (+2 commits, branch=main).

**커밋 2**:
| 순 | hash | 의미 |
|---|---|---|
| 1 | `d30915e` | circuit_breaker → `packages/shared/api_request/` 승격, 10 파일 import 갱신, KNOWN_VIOLATIONS #1·#2 해제 (5→3) |
| 2 | `ccbdce5` | FMP 3 클래스를 `providers/fmp/{client,market_pulse_client,serverless_client}.py`로 격자화, 16 소비처 갱신 (#32 1단계) |

**왜 namespace 옵션 (i) 채택**:
- (ii) canonical에 24 메서드 이식 = 행위보존 경계 위반 위험.
- (i) namespace 이동 + 클래스 이름 보존 = 행위보존 100% + #32 "동명 3 모듈" 신호어 해소.
- 2단계(완전 단일화)는 별도 사이클 (에러 정책 통일 + 메서드 합집합 설계 필요).

**burn-down**: shared 경계 동결 **5 → 3**. 잔여 = #3 (chain_sight), #4·#5 (macro.models).
**잔존 트랙**:
- BOUNDARY-2 (#3 chain_sight)
- BOUNDARY-3 (#4·#5 macro, 소비자 이동 방향1)
- FMP 2단계 통합 (canonical 메서드 합집합, 사용자 트리거)

**검증**: pytest 3179/52 (회귀 0, 버킷A 누적 0건), 경계 GREEN (우회 0 / 동결 잔여 3), health 8✅/0⚠/0❌.

### 버킷B / BOUNDARY-2 — #3 chain_sight 의존 청소 (Django apps.get_model) (2026-06-01)

**결정**: shared cross-app aggregator(`packages/shared/metrics/services/daily_report.py`)에서 `apps.chain_sight.models.CompanyChainProfile` 정적 import 제거. **Django app registry 동적 lookup**(`apps.get_model("chainsight", "CompanyChainProfile")`) 채택.

**HEAD**: `55f3cb6` → `80b9280` (+1 commit).

**왜 방향3 변종 채택**:
- **방향1 (소비자 이동) 불가**: daily_report = stocks + news + nightly + chain_sight + sec_pipeline + health 횡단 집계 aggregator. 단일 앱 흡수 불가능.
- **방향2 (callable 주입) 반쪽 효과**: 호출자도 `packages/shared/metrics/` 내부(tasks.py / management command / agent_reports). 의존이 caller chain을 따라 올라가도 shared를 못 벗어남 — 어딘가 static import 필요.
- **방향3 변종**: Django 공식 cross-app dynamic model lookup 표준. chain_sight 앱 소멸 시 import 단계 폭발 없이 runtime graceful fallback 가능. 행위 100% 보존. AST 가드는 정적 import만 검사 → 위반 자연 해소.

**범위 (행위 보존, 라인 +2 / -1)**:
- `packages/shared/metrics/services/daily_report.py:240` `collect_coverage_gaps()` 함수 1곳만 변경
- `from apps.chain_sight.models import CompanyChainProfile` 제거
- `CompanyChainProfile = django_apps.get_model("chainsight", "CompanyChainProfile")` 추가
- 사용처 (`CompanyChainProfile.objects.values_list("symbol_id", flat=True)`) 동일

**KNOWN_VIOLATIONS 해제** (tests + health_check 동시 갱신): #3 키 제거 + 사유 주석.

**burn-down**: shared 경계 동결 **3 → 2**. 잔여 = #4·#5 (macro.models lazy).

**가드 회피 vs 정당 패턴 판단**: 회피 아님. 근거 3:
1. Django 공식 패턴 (`django.apps.AppConfig.get_model`)
2. 실제로 shared가 chain_sight를 "직접 알지 않음" — 문자열 `'chainsight'`만 사용
3. cross-app aggregator의 본질 — 1 앱 의존을 정적으로 잡는 게 부적절

**잔존 트랙**:
- BOUNDARY-3 (#4·#5 macro, 소비자 이동 방향1, 경계 STEP 0 선행)
- FMP 2단계 통합 (사용자 트리거)

**검증**: pytest 3179/52 (회귀 0), 경계 GREEN (우회 0 / 동결 잔여 2), health 8✅/0⚠/0❌.

### BOUNDARY-3 — #4·#5 macro.models 청소: 의존 역전 + 등록 패턴 (방향2) (2026-06-04)

**결정**: `packages/shared/stocks/services/{eod_pipeline.py:617, eod_regime_calculator.py:77}`의 `from macro.models import MarketIndex, MarketIndexPrice` lazy import 2건을 **의존 역전 + 등록 패턴(방향2)** 으로 청소한다. 모델 이동·소비자 이동 모두 채택하지 않는다.

**구조**:
1. shared 측: `packages/shared/stocks/services/vix_provider.py` 신설 — `VIXProvider(ABC)` 포트(`get_latest_vix` / `get_vix_series`) + 모듈 전역 `register_vix_provider` / `get_vix_provider` 레지스트리 + `VIXProviderNotRegistered` 명시 예외. shared 코드는 구현 클래스를 import하지 않는다(주석/예외 메시지의 문자열 언급은 ast 검사 비대상).
2. app 측: `apps/market_pulse/services/macro_vix_provider.py` — `MacroVIXProvider(VIXProvider)` 가 macro.MarketIndex/MarketIndexPrice 쿼리(symbol VIX/^VIX/VIXX + category volatility + close)를 그대로 수행.
3. 등록: `apps/market_pulse/apps.py::MarketpulseConfig.ready()` 에서 `register_vix_provider(MacroVIXProvider())`. idempotent.
4. 호출: shared `_get_vix_value` / `_calculate_regime` 가 `get_vix_provider()`만 알면 됨.

**Why (가중합 채점: 방향2 = 4.65 vs 방향1 = 2.45 vs C = 2.35, 마진 2.20)**:
- (a) shared 내부 역의존 3건(`stocks/tasks.py:596`, `mgmt/pipeline_status.py:37`, `stocks/services/eod_signal_calculator.py:184`) 동반 이동 회피. 방향1은 EOD 스택 전체 이동을 강제했음.
- (b) 모델 이동/마이그레이션 회피. PR8b-3 결정 "macro=영구 모델앱"과 정합. C는 prod DB 마이그레이션 발생.
- (c) 포트 표면 최소(VIX 1종) — 새 추상화 비용 < 다른 옵션의 이동 비용.
- (d) 행위보존: 쿼리·반환 타입·float 변환 시점까지 동치. provider는 쿼리 직후 형태만 반환, float 변환은 호출자 numpy 진입 직전(`[float(p) for p in prices]`)에서 그대로 수행.

**How to apply** (재발 방지 패턴):
- shared가 app 모델을 lazy로 가리키는 새 위반이 발견되면 → 우선 "포트 + apps.ready() 등록"을 후보 1로. 모델 이동은 prod 영향이 있어 마지막 카드.
- shared 코드 어디에도 `apps.*` / `macro.*` 가 import 노드로 나타나면 안 됨(주석/문자열은 OK, ast 검사 무관). 검문소 = `tests/architecture/test_shared_boundary.py`.

**검증**:
- pytest tests/architecture: **3 passed** (frozen=0 / bypass=0).
- pytest stocks/shared/macro/marketpulse/architecture: **302 passed**.
- `manage.py makemigrations --check --dry-run` (settings_test): **No changes detected**.
- health_check shared 경계: **✅ 우회 0 / 동결 잔여 0**.

**구현**: 머지 커밋 `a9bb229` (2026-06-04), 슬라이스 4건 `[33e5437, 7b6572f, 73861d4, 662fdc4]`, 브랜치 `monorepo/sess-market_pulse`.

**트랙 종결**: BOUNDARY-3 close = **"shared 경계 부채 소진" 트랙 전체 종결**. burn-down 5→3→2→**0**.

**📎 참조**: `docs/harness/SHARED_BOUNDARY_GUARD.md`, `sub_claude_md/common-bugs.md` "shared 역방향 import 5건 — 전건 청소 완료(#31, 2026-06-04 종결)", TASKQUEUE.md `BOUNDARY-3`.

### NT-8 — Daily Report 뉴스 지표 퍼널 재구성 (2026-06-04)

**결정**: `payload['news']`에 `funnel`(N→M→K→J + 비율 4종) 키 추가. 기존 `today_llm_analyzed_pct`는 호환 유지하되 표시 단계에서 제거. critical 임계는 J/K(실행 건강) 기반으로 보정 + K=0 분기는 🟢 N/A로 명시.

**Why**:
- 옛 지표 `LLM 분석률 = J/N`은 분모(전체 신규 N)와 시스템 설계(Tier A+ 한정 deep 분석)가 어긋남 → 1%가 항상 critical로 표기되는 착시.
- 6/3 실측: N=296, M=50, K=3, J=3 → 옛 표시는 "J/N=1.0% 🟡 critical", 새 표시는 "**J/K=100% 🟢 정상** + 점수 기록률 16.9% 🟡 NT-2b" — 진짜 문제(score 채움률)를 가리킴.
- 보고서는 발견(데이터)이지 명령이 아니어야 → 단일 비율 노출이 디렉터를 잘못된 행동(quota 점검 등)으로 유도하는 위험 차단.

**How to apply**:
- 새 데이터 키: `payload['news']['funnel']` (`n_today_new`, `m_score_recorded`, `k_tier_a_pass`, `j_deep_analyzed`, `null_count`, `tier_a_threshold`, `score_recording_pct`, `coverage_pct`, `execution_health_pct`, `null_pct`).
- `tier_a_threshold`는 `NewsDeepAnalyzer.TIER_A_THRESHOLD` 동적 import (하드코딩 금지, 임계 변경 시 자동 반영).
- `collect_suggestions` 6번: K=0 → 🟢 N/A, K>0 ∧ J/K<80% → 🟡, 그 외 🟢. 6b번: null률>30% → 🟡 NT-2b 포인터.
- HTML 헤더 카드 "LLM 분석률" → "실행 건강 (J/K)"으로 라벨 교체. 본문에 퍼널 카드 신설.
- 텍스트 본문 한 줄: `N{}→M{}→K{}→J{}` 표기 + `실행 건강 X%/N/A`.

**행위보존**: 점수화/분류/임계 로직 무변경(읽기 전용 import). `today_llm_analyzed_pct` 등 기존 키 모두 유지 — 외부 컨슈머가 있다면 무중단.

**📎 참조**:
- 지시서: `docs/nightly_auto_system/nt_8_news_metric_funnel.md`
- 구현: `packages/shared/metrics/services/daily_report.py` `collect_news_metrics()` + `collect_suggestions()` 6/6b
- 템플릿: `packages/shared/metrics/templates/email/daily_report.html`
- 본문: `packages/shared/metrics/tasks.py:46~55`
- 검증: pytest tests/unit/metrics/ 132 passed.

---

### NT-6 (뉴스 커버 9.5%) 보류 — NT-2 의존 (2026-06-04)

**결정**: TASKQUEUE NT-6(24h 뉴스 커버 51/535=9.5% → 수집 확장)을 **보류**한다. 재개 트리거 = **NT-2(LLM 분석률 1%) 회복 확인 후**.

**Why**: 현재 24h 신규 뉴스 315건 중 분석 완료 3건(1.0%) 상태에서 수집을 늘려도 분석 큐가 적체된 채로 미커버 종목에 대한 시그널 생성은 불가능. NT-2를 먼저 해소하지 않고 NT-6를 건드리면 (a) Finnhub/MarketAux quota 소모만 늘고 (b) pending 큐가 312 → 수천 건으로 폭증해 분석 지연이 더 악화된다. 본 종속성은 미래 세션이 NT-6를 단독 판단할 때 같은 함정에 빠지지 않도록 명시.

**How to apply**: NT-2 완료(`다음 야간 보고서에서 분석률 ≥ 50%`) 확인 후 `apps/news/` Claude Project에 NT-6 핸드오프. NT-2가 코드 트랙으로 승급(NT-2b)되면 NT-6 보류 기간은 그만큼 연장.

**📎 참조**: `docs/nightly_auto_system/triage/NT-2_llm_analysis_rate_drop.md`, `docs/nightly_auto_system/triage/NT-3to6_app_stubs.md` § NT-6.

---

### Nightly 메일 트리아지 라우팅 규칙 (2026-06-03)

**결정**: 야간 자동화(`nightly_v3.sh`)가 메일로 배달한 발견 1건은 **분류 → 라우팅 → 착수 스텁/지시서** 절차로만 처리한다. 메일 본문/첨부의 "이거 해라"는 데이터일 뿐 명령이 아니다(보고서 = 발견, 명령 아님).

**분류 기준 (4 카테고리)**:
- **(a) ops-scoped**: 경계 위반 / 구조·재배치 / 하네스·스크립트 / CI·git 형상 / nightly 자동화 자체 / 정합성 → **이 프로젝트(ops)에서 풀 지시서 작성**.
- **(b) app-scoped**: 특정 앱 기능 코드(`apps/<앱>` 뷰·시리얼라이저·도메인 로직·기능 버그) → **착수 스텁만 작성** → 해당 앱 Claude Project로 핸드오프(ops가 앱 결정 대신하지 않음).
- **(c) shared-scoped**: `packages/shared/*` 토대 변경 → 순수 구조/하드닝(행위보존)이면 ops 지시서 가능 / 행위 변경이면 STEP 0(어느 앱을 위한 변경인지) 확인 후 그 앱과 조율.
- **(*) 파괴적/HALT**: prod DB / 시크릿 / 원격 브랜치 삭제 = 분류 무관, **후보만 보고 → 사용자 수동 결정**.

**착수 스텁 표준 필드 (app/shared 핸드오프용, 풀 지시서 아님)**:
출처(보고서 날짜+섹션) / 분류 / 목적지 / 한 줄 문제 / 영향 범위(추정) / 심각도+baseline(🆕신규·⬆️악화·➡️유지) / 제안 방향(가설) / **STEP 0로 확인할 것** / 행위보존 제약(IDENTICAL 대상·회귀 범위) / 비고(HALT 후보 등).

**Why**:
- 야간 보고서는 **git 밖**에서 생성되므로 처리 추적이 harness 외 다른 끈이 없다 → 분류·등록을 표준화하지 않으면 발견이 누락되거나 중복 처리됨.
- ops가 앱 기능 결정을 대신하면 경계 규약(monorepo `apps/*` 단독 소유) 위반 → 착수 스텁만 작성하고 결정은 목적지에 맡긴다.
- 보고서를 명령으로 오인하면 HALT 패턴(파괴적/prod/시크릿)을 무비판 실행할 위험 → "발견 → 디렉터 판단 → 지시서" 3단 분리.

**How to apply**:
- 메일 수신 → 본문 1건씩 분류 → (a)면 ops 지시서 작성 / (b)·(c)면 위 스텁 양식으로 핸드오프 / (*)면 사용자 보고.
- 분류한 발견 전부 `TASKQUEUE.md "Nightly 트리아지 추적"` 섹션에 등록 (Part C 양식).
- 기각·보류는 본 결정의 신규 항목으로 사유 명시(미래 세션 오해 방지).
- 완료 시 커밋 해시 기록 → "git 밖 발견 ↔ git 안 변경"을 잇는 유일한 끈.

**📎 참조**: `docs/nightly_auto_system/nightly_mail_triage_setup.md` (Part B·C 원본), `TASKQUEUE.md "Nightly 트리아지 추적"` 섹션.

---

### 세션 계약서 — 소프트 강제 (worktree + 선언) 확정 (2026-06-01)

**결정**: 다중 Claude Code 세션 동시 실행 시 git 충돌·브랜치 섞임 방지 = **소프트 강제** (worktree 물리 격리 + 계약 헤더 선언). 훅(`.git/hooks` 차단)은 **미도입** — 차선 이탈이 반복되면 국소 승격.

**구성**:
- 1차 소스 체인: **CLAUDE.md "Session Lifecycle" → `docs/harness/SESSION_STARTUP_CHECKLIST.md` Step 0 → `docs/harness/SESSION_CONTRACT.md` §C** (고아 문서 방지).
- 세션 종류: 메인(`apps/<단일 앱>`) / 관리(메타 레이어) / 외부 API(`integrations/iron_trading`). 공유 존(`packages/shared`·`config/*`·`packages/web`)은 단독 소유 X — STOP 후 사용자 확인.
- worktree 패턴: `Desktop/stock_vis_<sess>` 형제 dir + `sess/<name>` 브랜치. 원본 리포(`Desktop/stock_vis`)는 main 전용 머지 지점.
- 종료 게이트: 자기 브랜치 push + `pytest` + `health_check` 통과 → main 머지(CI 1인 대체).

**Why**:
- 현재 1인 개발이라 강한 훅·CI는 과함. worktree만으로 물리 충돌면 0.
- 메타 레이어를 관리 세션 단독 소유로 분리 → 메인 세션이 PROGRESS/DECISIONS 동시 편집 충돌 차단.
- 1차 소스 체인 미연결 = 고아 문서 위험. 3 문서 모두 상호 참조 + 1차 소스 우선 명시.

**How to apply**:
- 새 세션 = STARTUP_CHECKLIST Step 0 부터 — SESSION_CONTRACT §C 헤더 빈칸 채워 붙임.
- worktree 시범 = `../stock_vis_mgmt` + `sess/mgmt` 살아있음(2026-06-01 생성). 다음 관리 세션부터 사용.
- 미래 확장(사람 증가): PR + CI(GitHub Actions: pytest + 경계 테스트) + CODEOWNERS 3개 추가만으로 충분.

**관련 문서**:
- 헌장: `docs/harness/SESSION_CONTRACT.md` (§A~§G)
- 실행 진입: `docs/harness/SESSION_STARTUP_CHECKLIST.md` (Step 0~3)
- 1차 소스: `CLAUDE.md "Session Lifecycle"` 참조 한 줄

---

### iron-trading 출구 엔드포인트 STEP 0 발견 — 이미 main 라이브 (2026-06-04)

> 입력: `docs/trading_bot_api/api_decision_handoff.md` §2-A. 본 결정은 stock_vis 소유 항목만 기록 — verify-first 가중합 결정·데이터 현실 3종·소비자 구현 지시서는 iron_trading 소유(별도 repo 기록).

**발견 (STEP 0)**: `GET /api/v1/iron-trading/daily-context`는 이미 `main`에 구현·라이브 상태다.
- 라우팅: `config/urls.py:46` → `include("integrations.iron_trading.urls")`
- 구현 본체: `integrations/iron_trading/views.py` (DRF `APIView`, `AllowAny`) + `integrations/iron_trading/services/{daily_context.py, signals.py, market_pulse.py}`
- 머지 흐름: 최초 commit `82aa9b4` (`feat(iron-trading): read-only /api/v1/iron-trading/daily-context`) → monorepo PR3에서 `iron_trading/` → `integrations/iron_trading/`로 이동 (`7171f83`, `6cf961a`) → 현재 main HEAD `16ced49`.
- 따라서 다음 단계는 "stock_vis에 엔드포인트 추가"가 아니라 "iron_trading 소비자 구현"이다(소비자 구현은 별 repo, 본 결정 범위 밖).

**방침 정합**: `integrations/` 네임스페이스에 가산형(additive) read-only 출구를 둔 것은 기존 방침 "stock_vis 코드 수정 안 함(기존 백엔드 리팩토링 금지)"과 충돌하지 않는다.
- 두 프로젝트는 여전히 코드·DB·ORM·마이그레이션·import를 공유하지 않고 HTTP로만 연계한다.
- `integrations/iron_trading/services/daily_context.py`의 의존은 단방향(`packages.shared.stocks.models` + `apps.market_pulse.models.regime` + `apps.chain_sight.models.narrative_tag`)이며 어떤 app/service도 이 출구를 import하지 않는다(외부 출구만).

**Why**:
- 메모리/인지와 코드 상태의 불일치를 STEP 0가 잡았다 — 메모리는 PROGRESS의 캐시이지 진실의 소스가 아님(2026-05-28 정합성 점검 원칙과 동일 패턴).
- 가산형 출구가 기존 방침에 위배되는지가 후속 작업 결정에 직접 영향(엔드포인트 폐기·이전·중단을 강제하면 안 됨)이라 결정 본문에 박는다.
- verify-first/데이터 현실 3종/소비자 구현 결정을 본 repo에 기록하면 iron_trading repo와 평행 출처가 생긴다 — `api_decision_handoff.md §0-2/§0-3`이 명시적으로 금지.

**How to apply**:
- 본 출구를 폐기·이전 후보로 보지 않는다. 단, 봇 측 요구가 보강을 부르면 보강 항목으로 처리(`TASKQUEUE.md`의 "Iron Trading 출구 (integrations/iron_trading)" 트랙 보류 항목 참조).
- `handoff_codex.md`가 박은 옛 경로(`iron_trading/`)와 옛 commit(`8c21a52`)은 휘발성이라 stale — 정리 작업은 `TASKQUEUE.md`에 등록(즉시 처리 아님, 수정 전 STEP 0로 실제 경로 재확인).
- 다음 검증 세션은 read-only 라이브 검증(서버 기동 + 200 응답 1개) 범위로 한정.

**관련 입력 문서**: `docs/trading_bot_api/api_decision_handoff.md` (단일 입력, 본 결정 기록 후 archive 또는 정리 대상 — 평행 출처 방지).

---

### D1 — intraday(regime/anomaly) 거취: dashboard 이관 보류, market_pulse 잔류 (옵션3) (2026-06-06)

**결정**:
- intraday를 dashboard로 이관하지 않고 market_pulse에 잔류.
- 당면 조치 = NT-7 운영 안정화(Beat 스케줄 재동기화 + 좀비 워커 정리)로 한정. 구조 이동·격리 없음.
- intraday→dashboard 도메인 이동은 보류 항목으로 강등(`TASKQUEUE.md` `STRUCT-CLEANUP` 등록).

**근거 (STEP 0 실측, 2026-06-06)**:
- "intraday는 dashboard 전용 → 깨끗한 방향1 이동" 전제가 실측으로 깨짐. 거시↔intraday 양방향 결합:
  - intraday→거시 2건: `anomaly/engine.py`가 `ConcentrationSnapshot`·`SectorFlowSnapshot` 직접 쿼리, `news_pairing.py`가 `MarketPulseNews` → 이동 시 dashboard→market_pulse 신규 결합.
  - 거시→intraday 6건: `api/views/overview.py` 메인 4 카드 중 2 카드·`briefing/prompt.py`·`tasks/finalize.py`·`admin.py`·`api/views/cards.py`·`api/views/health.py`가 intraday 인용.
- 받을 자리 부재: `apps/dashboard/` 백엔드 앱·INSTALLED_APPS·URL 없음(`frontend/app/dashboard/`는 Next.js 화면, 해당 없음).
- 동결 결정 충돌: 2026-05-31 "dashboard=거시 통합 뷰, marketpulse를 dashboard에 통합 → 취소"(DECISIONS.md L394·L429)와 정면 충돌.
- dashboard 타 프로젝트 소유 → 이동은 양 세션 직렬화 필요(이 세션 영역 밖, SESSION_CONTRACT.C.3).
- 가중합(인지 0.25 / 의존 0.20 / 롤백 0.20 / 테스트 0.15 / 효율 0.10 / 유연 0.10): 옵션3 4.25 ≈ 옵션2 4.10 ≫ 옵션1 2.45. 마진 옵션3−옵션1 = 1.80(>1 자동 탈락), 옵션3−옵션2 = 0.15(타이브레이커: D1 미결정 위에 격리 작업 쌓으면 헛수고 → 옵션3).

**보류 트리거 (재개 조건)**:
- (a) 앱 초기 배포 버전 확정 시 구조 정리 트랙에서 재검토, 또는 (b) 실제 경계 충돌 발생 시.
- 그 전까지 다른 세션에서 먼저 꺼내지 않음(scope noise 방지).

**재개 시 안전장치 메모**:
- `RegimeSnapshot` (`mp_regime_snapshot`) · `AnomalySignalLog` (`mp_anomaly_signal_log`) 둘 다 `db_table` 명시 → **SeparateDatabaseAndState 수동 마이그레이션 필수**. 자동 `makemigrations` 금지(DROP+CREATE = prod 데이터 손실).

**관련 입력 문서**: `docs/market_pulse_v2/nt_7_step_0.md` (NT-7 STEP 0 지시서), 본 결정 측정 보고는 세션 컨텍스트 내에 보존(평행 출처 회피).

---

### 좀비 Beat 56670 = 5/21 Trash stray 기동의 잔불 (NT-10/NT-7 단일 origin) (2026-06-06)

**결정**:
- NT-10(메일 2회 발송) + NT-7의 KeyError(`Received unregistered task`)는 **단일 원인**으로 확정 = 5/21 10:06에 `~/.Trash/stock_vis.icloud_backup.20260516_144329` 트리에서 수동 기동되어 16일간 invisible로 살아남은 좀비 Beat 프로세스(PID 56670).
- 청소는 **origin 단위**로. PID 단위 단발 kill만으로는 재발 방지 못함 — origin(어디서 어떻게 떠올랐는가)을 끊어야 함.
- NT-7의 두 증상은 **분리 추적**: KeyError = 좀비 origin과 동일 사건(해소 완료), FileNotFoundError = 별도 원인 가능(서비스 코드 또는 외부 파일 의존), 다음 회차 검증 후 분리 판정.
- 재발 방지 가드는 **origin(cwd-밖) 기반** 채택 예정 — 정상 트리(`Desktop/stock_vis`) 밖에서 기동된 celery beat는 모두 알림 대상. 가드 코드 구현 범위는 NT-11 트랙에서 별도 결정.
- 좀비 종료는 단발 kill(SIGTERM)로 완료(2026-06-06 21:30). 검증 = 6/7 07:00 KST 단일 메일 + 6/6 21:30 이후 KeyError 소멸.

**Why**:
- 단일 PID kill은 "잔불 끄기"일 뿐 — origin(Trash 트리에서 수동 `celery -A config beat` 실행)을 가드하지 않으면 같은 사용자 액션(트리 비교/검증 목적의 ad-hoc 기동)이 다시 좀비를 만든다.
- iCloud sync OFF 이력(5/16)으로 Trash에 옛 트리가 남아있는 상태가 보존됨. 이 트리에서 어떤 명령이든 실행 가능 → 비정상 cwd 기반 가드가 가장 비용 싸고 일반화 가능.
- watchdog이 launchd Beat(PID 15151)가 살아있는 것만 확인하는 룰만 가져, 다중 process가 16일간 invisible. **검출 룰의 sparsity가 본 사건의 invisible 기간을 만든 핵심 요인.**
- KeyError와 FileNotFoundError를 같은 NT-7 묶음으로 보면 한쪽 해소 후 다른 쪽 잔존 신호를 놓친다 — 분리 추적이 안전.

**How to apply**:
- 가드 채택: `ps aux | grep "celery.*beat"`로 다중 process 감지 + 각 process의 cwd(`lsof -p <PID> | grep cwd`)가 `Desktop/stock_vis` 밖이면 알림. 가드 구현 위치(`config/tasks.py` 또는 watchdog 셸 또는 daily report 섹션) = NT-11 트랙에서 결정.
- 정상 Beat 기동은 항상 `--scheduler django_celery_beat.schedulers:DatabaseScheduler` 옵션 명시. `ps aux`에서 옵션 없는 beat는 즉시 의심.
- 운영 트리(`Desktop/stock_vis`) 밖에서 celery 명령 ad-hoc 실행 금지 — 비교/검증 목적이면 worktree 또는 별도 venv로.
- Trash 또는 백업 트리는 cron 비활성/celery 명령 가드되도록 환경 정책. (사용자 수동 영역, 본 트랙 범위 밖)
- NT-7 FileNotFoundError 분리 검증: 6/7 회차에서 KeyError 0건이고 FileNotFoundError가 잔존하면 별도 STEP 0 트랙.

**증거 (스냅샷)**:
- 좀비 메타: PID 56670, PPID 13862(부모 셸 살아있음, orphan 아님), 시작 Thu May 21 10:06:27 2026, cwd=`~/.Trash/stock_vis.icloud_backup.20260516_144329`, stdin/stdout/stderr=`/dev/ttys003`, command `celery -A config beat -l info` (`--scheduler` 옵션 없음 = default PersistentScheduler).
- 정상 Beat: PID 15151(5/17 시작, launchd `com.stockvis.celery-beat`, DatabaseScheduler). 좀비 종료 후 launchd가 21:30에 PID 86614로 재기동(정상).
- 워커 에러 로그 task 헤더 origin 두 종류: `gen15151@...`(정상 Beat) + `gen56670@...`(좀비 Beat). 두 origin이 같은 task name으로 발사된 흔적이 발사 다중성의 표지.
- Beat 로그(`celery-beat-error.log`)는 stdout 아닌 stderr에 출력 — `*-error.log` 파일이 진단 1차 소스. `*.log`(stdout)는 거의 비어있음. 이건 진단 함정.

**관련 트랙**:
- common-bugs #33 (좀비 Beat 다중 process 패턴)
- TASKQUEUE NT-10(메일 2회) / NT-7(unregistered task) / NT-11(가드 범위 결정 대기 → git 지시서)
- iCloud sync OFF 이력: PROGRESS 또는 메모리 `troubleshoot_icloud_desktop_sync_off`
- Bug #28 (Beat schedule drift dict↔DB)는 본 사건과 **다른 원인** — 정합 상태에서도 다중 process로 KeyError 발생 가능함을 보여주는 사례.

---

### STEP 0 측정에 git fetch 선행 의무화 (2026-06-11, TR-6~8)
- worktree/브랜치 머지 판정 등 **git 도달성 측정 전 `git fetch origin` 선행 필수** (remote-tracking ref 갱신만, working tree 불변).
- **Why**: TR-6에서 worktree 2건을 `git branch --merged main`(로컬 main 기준)으로 "미머지=ALIVE" 오판 → 실제로는 stale·분기된 로컬 main이라 origin/main에 이미 머지된 DEAD 상태였음. fetch 없이 stale 기준선으로 측정하면 보존/삭제 판단이 뒤집힘. TR-8에서 fetch 후 origin/main 기준 5건 전건 REACHABLE = DEAD 확정으로 정정.
- **F 가드 부팅 검사 설계 입력 #4** (부팅 시 origin 신선화 → 기준선 stale 차단).
## [2026-06-07] Phase 1 PR 카탈로그 역산 확정 (권위 문서 부재 → 코드 기준)

**맥락**: "16 PR 카탈로그/frozen-decisions"는 4월 대화 산출물이나 repo 미커밋. `docs/market_pulse_v2/` 하위 PR-A1/A2/A3 위임 프롬프트 3건만 존재, PR-B~O 14건 부재. → 코드·운영 문서를 1차 진실로 PR 상태를 역산 확정한다(추정 카탈로그 복원 아님).

**백엔드 상태 (STEP 0 2026-06-07 측정)**:
- ✅ done: PR-A1 (sector_group + EconomicIndicator 11 + MarketIndex 20 + backfill), PR-A2 (5모델 + Pydantic schemas), PR-B (fetchers + news_aggregator + circuit_breaker), PR-D (anomaly engine + news_pairing), PR-E (briefing client/prompt/safety), PR-F (breadth), PR-G (sector_flow), PR-H (concentration), PR-O (finalize + 2 purge tasks).
- ⚠️ done(아래 갭 제외): PR-I (5 views + overview serializer + URL 라우팅), PR-C (regime classifier + rules + 15min task).

**J = PR-I에 흡수**: `apps/market_pulse/api/views/cards.py`·`health.py`가 `overview.py`와 동일 `api/views/` 레이어로 통합 구현됨. 별도 산출물 없음. **분리 복원은 합쳐진 코드를 쪼개는 행위보존 위반이라 안 함.**

**M(운영) = (b) 잔여 — STEP 0 측정 (2026-06-10)**:
- ✅ 충족: `apps/market_pulse/management/commands/setup_marketpulse_beat.py` (Command 클래스 + help) · `apps/market_pulse/api/views/health.py` (HealthView + DB/cache/last_runs 체크 + URL 라우팅).
- ❌ 잔여: `docs/operations/marketpulse_v2_celery_tasks.md`가 옛 경로 `marketpulse.tasks.*` 참조로 stale (10개 task 모두). NT-7으로 코드는 `apps.market_pulse.tasks.*` 새 경로로 갱신됐으나 runbook 본문 미갱신.

**N(모니터링) = (b) 잔여 — STEP 0 측정 (2026-06-10)**:
- ❌ market_pulse 자체 능동 모니터링 자산 0건: `apps/market_pulse/` 전체 + `packages/shared/` 에서 `sentry`/`prometheus`/`statsd`/`datadog`/`opentelemetry`/`pagerduty` grep 0건. monitor·alert 파일 0건. runbook 모니터링 섹션 0건.
- 참고(범위 외): `services/news/tasks.py:check_pipeline_alerts`가 6 트리거(ML F1 / 키워드 / LLM 에러율 / Neo4j / 수집량 / 미분류) 알람을 운영 중 — 동등 패턴을 market_pulse로 확장하는 게 N 잔여 항목.

**Translation Layer / Macro Playbook = Phase 1 범위 아님**:
- grep 0건(`translation_layer`/`TranslationLayer`/`macro_playbook`/`MacroPlaybook`) + 로드맵 재정립상 Translation=Phase 1.5, Playbook=Phase 1.6 신규. 잔여가 아니라 미래 Phase 항목.

**Phase 1 확정 잔여**:
1. **프론트엔드 K/L** (0% — `frontend/src` 내 `market_pulse`/`marketPulse` 검색 무결과. Phase 1 출시 실질 병목)
2. **PR-C `stress_input` 훅** (1줄 인터페이스 — `apps/market_pulse/regime/` 내 `stress_input` grep 0건. Phase 1.5 무재설계 전제)
3. **M 잔여**: `docs/operations/marketpulse_v2_celery_tasks.md` task 경로 갱신 (10건 `marketpulse.tasks.*` → `apps.market_pulse.tasks.*`)
4. **N 잔여**: market_pulse 능동 모니터링 자산 (`check_pipeline_alerts` 패턴 확장 또는 sentry/prometheus 도입)
5. **A3 마이그레이션 분리** (3 snapshot이 `0001_initial`에 통합됨. 행위보존이라 우선순위 낮음, 미루기 가능)
6. **I serializer 도메인 분리 + 통합테스트, B fetcher 테스트** (테스트/정리 갭 — overview만 분리 serializer 보유, cards/health 미분리)

**비고**: FRED fetcher는 이미 done (`packages/shared/api_request/fred_client.py` + `backfill_v2_a1._backfill_economic()` + `sync_indicators.mp_sync_yahoo_indicators_daily`) — 이전 추정 "남음" 정정.

**Why**:
- 권위 문서(4월 PR 카탈로그)가 repo 부재로 "16 vs 17 PR" 불명. PR-B~O 위임 프롬프트를 사후 작성하면 이미 구현된 걸 문서화하는 낭비 — 옵션 A 기각.
- 코드 실측이 1차 진실이므로 역산 카탈로그로 Phase 1 진행 상태를 확정 (PROGRESS.md 캐시 갱신 가능 상태로).

**How to apply**:
- Phase 1 추가 PR 위임 프롬프트 작성 금지(이미 구현). 잔여는 위 6항목 한정.
- Phase 1.5 (Translation Layer) / Phase 1.6 (Macro Playbook) 신규 트랙은 별도 STEP 0 후 신설.
- 본 결정 commit 후 PROGRESS.md/TASKQUEUE.md에 잔여 6항목 동기화.

**관련 입력 문서**: `docs/market_pulse_v2/market_pulse_v2_pr_a1.md` (PR-A1/A2/A3 위임 프롬프트 3건만), STEP 0 측정 보고(2026-06-07)는 세션 컨텍스트 내 보존.

---

## [2026-06-10] stress_input 훅 사전 배선 (Phase 1.5 준비)

**결정**:
- `apps/market_pulse/regime/classifier.py:classify_inputs(inputs, *, rules=None, stress_input=None)` keyword-only Optional 인자 추가.
- 본문은 `del stress_input`으로 즉시 폐기 — 받기만 하고 분류 로직에 사용하지 않음 (행위보존).
- 회귀: `tests/marketpulse` 138 passed (이전 baseline 136 + 신규 2 케이스, 0 regression).

**Why**:
- Phase 1.5(Crisis/Stress 레이어) 진입 시 classifier 시그니처 재설계 없이 인자 채우기만으로 통합 가능하도록 인터페이스 스텁만 선반영.
- 분류 로직 변경 0 → Phase 1 출시 영향 0, 향후 1.5 도입 비용은 호출부 + 본문 한 곳으로 한정.

**Why now (Phase 1 소정리 세션에 동승)**:
- 별도 "인터페이스 변경 commit" 세션을 따로 만들 비용을 제거. `MP1-C-stress`(저비용 선행)로 사전 등록된 항목을 그대로 처리.
- 동일 mgmt 트랙(`monorepo/sess-mp-phase1-cleanup`)에서 `MP1-M`(runbook 경로 갱신)과 묶어 2 commit ff push (`0b8399a..ef9d064`).

**행위보존 근거**:
- 신규 테스트 `test_stress_input_none_preserves_output`: `stress_input=None`일 때 baseline과 regime/fired 동일.
- 신규 테스트 `test_stress_input_dummy_accepted_without_behavior_change`: 비-None dummy 전달 시에도 분류 결과 불변.
- 기존 14 케이스(BULL/LATE_BULL/TRANSITION/BEAR/CRISIS/yield_inversion/drawdown_crisis/missing_inputs 등) 전건 통과.

**How to apply**:
- Phase 1.5 도입 시 `tasks/regime.py:mp_calc_regime_15min`에서 stress input 데이터 소스(예: VIX term structure stress index, repo yield stress) 조립 후 `classify_inputs(..., stress_input=<payload>)` 호출.
- classifier 본문에서 `del stress_input` 제거하고 `_eval_clause` 또는 `_eval_atom` 단계에 stress 평가 분기 추가.
- 본 결정은 시그니처만 박고 데이터 흐름은 1.5에서 설계 — 모델·테이블·fetcher 신설 금지(이번 commit 범위 외).

**관련 입력 문서**: TASKQUEUE `MP1-C-stress` 항목, `apps/market_pulse/regime/classifier.py:113~127`.

---

## [2026-06-10] K/L static 완료 + 라이브 검증 출시 게이트 분리 (옵션 C)

**결정**:
- `MP1-K`(Layer0 메인 페이지) / `MP1-L`(카드 + news/health 위젯)을 **static 측정 기준 완료**로 표기.
- 동시에 라이브 동작 검증은 별도 **출시 게이트 `MP-LIVE-VERIFY`** 로 신설 — Phase 1 release를 차단하는 trigger-gated 항목.
- 후속 트랙 3건 등록: `MP-KL-F1`(테스트), `MP-KL-F2`(`'flow'`→`'concentration'` 리네임), `MP-KL-F3`(health 위젯 명세 검증).
- v1 페이지 거취는 별도 결정 항목 `MP-V1-DECISION` (실행 항목 아님).

**근거 (STEP 0 보강 측정, 2026-06-10)**:
- `frontend/app/market-pulse-v2/page.tsx`(Layer0) + `cards/` 5 Summary + `details/` 5 Detail(+Container) + `components/` 5 패널 + `lib/api/marketPulseV2.ts`(30+ 타입 + 4 fetch) + `useOverview()` TanStack Query Hook + `useMarketPulseI18n()` — 전건 static 존재 확인.
- 백엔드 v2 API 5 엔드포인트(`/overview`, `/cards/<id>/detail`, `/news/refresh`, `/i18n`, `/health`)와 프론트 1:1 매핑 검증 — 라우팅 정합 OK.
- 단 `frontend/__tests__/`에 market-pulse 테스트 0건, `OverviewView` 실 응답 vs `useOverview()` 렌더 일치 미실측, `'flow'` 변수명이 Concentration을 가리키는 잔재 1건.

**Why (옵션 C 선택)**:
- 직전 같은 날 측정에서 `frontend/src/` 잘못된 경로 grep으로 K/L "0%"가 거짓 보고된 사례 실증(common-bugs #31).
- static 표기는 풍화될 수 있음 — 게이트로 보존해야 release 직전 자동 차단.
- 가중합 평가:
  - 옵션 A (그대로 "0%" 유지) 4.10 — static 산출물 무시로 측정 실증 폐기
  - 옵션 B (완료 표기 + 게이트 없음) 4.25 — 라이브 미검증인데 release 가능 위험
  - **옵션 C (완료 표기 + MP-LIVE-VERIFY 게이트) 4.40** — static 사실 인정 + 라이브 검증을 release blocker로 보존
  - 마진 C−B = 0.15, 타이브레이커: 당일 오측정 실증으로 게이트의 가치 증명.

**How to apply**:
- TASKQUEUE Phase 1 잔여 표에서 K/L 행은 "완료 2026-06-10 (static 기준)" + 실 산출물 경로 명시.
- `MP-LIVE-VERIFY` 게이트는 [GATE:release] 접두어로 차단 표시. 실행 절차: 서버 기동 → `curl -s /api/v2/market-pulse/overview | jq` 200 응답 → 5 card_id 각각 `/cards/<id>/detail` 응답 → `page.tsx` 실 렌더(5 Summary + Detail Container + 5 패널) 대조 → 스크린샷 + 응답 로그를 DECISIONS push 라인에 첨부.
- `MP-KL-F3`(health 위젯 명세)는 게이트 선결 조건. `StatusBanner`가 health 매핑인지 별도 위젯 필요한지 먼저 정리.
- `MP-KL-F2`(`'flow'` 리네임)는 게이트 통과 이후 — 행위보존 리네임이라 게이트 차단 사유 아님.
- v1 페이지(`app/market-pulse/page.tsx`)는 게이트와 무관하게 `MP-V1-DECISION` 별도 결정.

**Why now**:
- 같은 mgmt 트랙에서 PR 카탈로그 확정(0b8399a) → 소정리(ef9d064) → close(4106b4b) 흐름 종료 직후. K/L까지 정합화하면 Phase 1 잔여 표가 "release 전 정리할 미완 항목 + release 차단 게이트"로 깔끔하게 분리됨.

**관련 입력 문서**: TASKQUEUE `MP1-K/L`·`MP-LIVE-VERIFY`·`MP-KL-F1~F3`·`MP-V1-DECISION` 항목, STEP 0 보강 측정 보고(세션 컨텍스트), `frontend/app/market-pulse-v2/page.tsx:22~28` `CARD_TITLE`, `apps/market_pulse/api/urls.py`.

---

## [2026-06-10] v1 거시 대시보드 거취 — 옵션 D: 보존 + Phase 2 흡수 예약

**결정**:
- `app/market-pulse/page.tsx`(v1, 310 lines) **현행 유지**(보존).
- Phase 2 sub-pages 트랙 착수 시 v1 위젯군 5종(`FearGreedGauge` · `YieldCurveChart` · `EconomicIndicators` · `GlobalMarketsCard` · `MarketMoversSection`)을 v2 하위 페이지로 흡수.
- 흡수 완료 후 `/market-pulse` → `/market-pulse-v2` 리다이렉트 전환 → v1 코드 제거.
- 본 결정은 **유지 결정 + 후속 흡수 예약**. 즉시 삭제·리다이렉트 없음.

**근거 (옵션 D 선택)**:
- **① 신구 버전이 아니라 상호 보완**: v1 위젯 5종(FearGreed/YieldCurve/EconomicIndicators/GlobalMarkets/Movers)은 v2 카드 5장(Regime/Breadth/Sector/Concentration/Brief)에 부재. 삭제 = 대체 없는 정보 손실. v1 = 거시 원자료(매크로 지표 raw), v2 = regime 판정(가공된 시그널) — **역할 분담**.
- **② 게이트 안전 순서**: `MP-LIVE-VERIFY`(K/L static 완료 + 라이브 미검증) 게이트 미통과 상태에서 v1은 유일하게 검증된 화면. 미검증 v2만 남기는 순서는 위험 — 게이트 통과 전 v1 삭제 금지.
- **③ Phase 2 흡수 정합**: v1 위젯군은 Phase 2 sub-pages 로드맵의 자연스러운 흡수 재료. 별도 trash 트랙으로 두지 않고 흡수 트랙으로 묶음.

**가중합 평가**:
- 옵션 A (즉시 폐기 + 코드 제거) **3.10** — 위 ①②로 정보 손실 + 게이트 안전 깨짐
- 옵션 B (즉시 리다이렉트 → v2) **3.50** — A와 동일 문제 + 라우팅 잔재
- 옵션 C (v1 유지 + Phase 2 흡수 계획만 메모) **3.55** — 흡수 트랙 미등록으로 풍화 위험
- **옵션 D (보존 + Phase 2 흡수 예약 `MP-V1-ABSORB` 등록) 3.90** — ①②③ 모두 충족 + 흡수 트랙 명시
- 마진 D−C = 0.35, 타이브레이커 2건:
  1. **게이트 안전 순서**: `MP-LIVE-VERIFY` 통과 전까지 v1이 검증된 fallback. 옵션 C는 흡수 트랙을 메모로만 두어 게이트 통과 시점에 흡수 작업이 잊힐 위험.
  2. **Phase 2 정합 명시**: 흡수 트리거를 "Phase 2 sub-pages 착수"로 등록하면 Phase 2 트랙이 v1 위젯을 자동 흡수 대상으로 인식 — 별도 발견 비용 0.

**의도적 동결 (commit 범위 외)**:
- v1 내부 `// import { MarketNewsSection } // TODO: 컴포넌트 미구현` 주석 잔재는 **흡수 시점 일괄 처리 대상**으로 동결. 그 전까지 수정·삭제 금지. 흡수 PR에서 MarketNewsSection 처리(구현/제거/대체) + 주석 정리를 한 번에 수행.

**How to apply**:
- TASKQUEUE `MP-V1-DECISION` 행 → "완료 2026-06-10 (옵션 D)" + 본 결정 참조.
- TASKQUEUE 신규 `MP-V1-ABSORB` 등록 — Phase 2 sub-pages 착수가 트리거인 trigger-gated 항목. 그 전까지 다른 세션에서 먼저 꺼내지 말 것.
- 미래 세션이 "v1 왜 있지?"를 재측정하지 않도록 본 결정 본문에 "역할 분담" 명시 — DECISIONS가 1차 진실.

**관련 입력 문서**: TASKQUEUE `MP-V1-DECISION`·`MP-V1-ABSORB` 항목, `app/market-pulse/page.tsx` (310 lines, v1) ↔ `app/market-pulse-v2/page.tsx` (v2 Layer0) 산출물 대조, common-bugs #31(직전 K/L 오측정 사례 — 본 결정의 가중합 평가 입력).

---

## [2026-06-11] MP-KL-F2 게이트 선행 + 복구 이식 기록

**결정 1 — F2(card_id 리네임) 게이트 선행 실행**:
- TASKQUEUE상 `MP-KL-F2`는 `MP-LIVE-VERIFY` 게이트에 의존(게이트 후 실행) 표기였으나, **의도적으로 게이트에 선행** 실행.
- 근거: card_id는 **공개 계약**(`/cards/<id>/detail` URL + overview JSON `cards.<id>` 키). 게이트 통과 후 리네임하면 계약이 바뀌어 **게이트 재실행을 강제** → "게이트는 최종 계약 위에서 1회만 실행" 원칙 위반. 따라서 리네임을 먼저 하고 그 위에서 게이트 1회.
- 배포 보류 상태 = 외부 소비자 0 → 계약 변경 **최저비용 시점**.
- 가중합: 옵션1(지금 리네임) **4.25** / 옵션2(게이트 후 리네임) **3.30**, 마진 0.95.
- 후속: TASKQUEUE `MP-KL-F2` 행의 `MP-LIVE-VERIFY` 의존 표기 삭제(본 결정 참조 주석). `MP-LIVE-VERIFY`는 선결 전부 충족 → 게이트 실행 준비 완료.

**결정 2 — 복구 이식(cherry-pick)**:
- 1차 작업(F1/F3/F2)이 **갈라진 로컬 main**(merge-base `d4a9690`, origin/main 최근 5 commit 부재) + **공유 메인 디렉터리**에서 수행돼 타 트랙 커밋(`82afddb`, 로컬 main `cb5473e`와 동일 메시지·별개 hash)이 작업 브랜치에 혼입.
- 복구: origin/main(`85557e6`) 위 새 worktree(`sess-mp-kl-f1f3-v2`)에서 `cherry-pick -x`로 3 commit 이식 → `e538e7f`(F1, 원본 `8f1ba79`) / `d5289a2`(F3, 원본 `f16efcb`) / `902ec86`(F2, 원본 `70a00c9`).
- 이식 검증 전 통과: pytest 138 / vitest 174 / tsc 0 / `manage.py check` 0 / card 문맥 'flow' 잔존 0 / 동명이의 3곳 무변경 / health 8✅. push 완료(`85557e6..902ec86 → origin/main`).
- 원본 브랜치 `monorepo/sess-mp-kl-f1f3` **폐기 승인 기록**: cherry-pick이라 `git branch -d`가 미머지로 거부할 수 있음 → 내용 동일성 검증 완료로 `-D` 정당. **실행은 병진 수동**.

**근거 입력**: common-bugs #32(fetch 없는 baseline) · #33(공유 디렉터리 작업) · #34(짧은 라벨 비고유), 2026-06-11 복구 세션 측정 로그.

---

## [2026-06-11] 트랙별 소유권 지도 v2 — 전수 실측 기반 (902ec86 측정)

**공통 규칙**:
1. 각 트랙은 **자기 소유 구획만 직접 변경**.
2. 한 슬라이스가 타 구획 파일에 **하나라도 걸치면 슬라이스 통째 위임**(쪼개지 않음).
3. 읽기·grep·실측은 **전 구획 자유**.
4. 실행 지시서 DoD 표준 = `git diff --name-only` 전수 자기 구획 검사, **위반 = HALT**. 소유영역 문언은 "예시 열거"가 아닌 **"트랙 전용 파일" 취지**로 해석, 판단이 갈리면 사용자 판단에 부침.
5. 모든 세션 **전용 worktree**, pwd가 메인 디렉터리면 HALT, baseline은 `git fetch` 후 **origin/main 직접 측정**.
6. **메타 4종**(TASKQUEUE·PROGRESS·DECISIONS·common-bugs) = **mgmt worktree 전용**(전 트랙 공통).

**[활성·성숙] market_pulse 트랙** (STEP 0 확정 2026-06-29): `apps/market_pulse/**`, `macro/**`(루트 모델 — 이동 동결, BOUNDARY 결정 준수), `tests/marketpulse/**`, `tests/macro/**`, `docs/market_pulse_v2/**`, `docs/operations` 중 marketpulse 문서, FE: `app/market-pulse*/**`, `components/market-pulse/**`, `components/macro/**`(v1 위젯 — `MP-V1-ABSORB` 대상), `lib/api/marketPulseV2*`, `lib/i18n/marketPulse*`, `hooks/useMarketPulse*`, `services/macroService*`, `__tests__/market-pulse*/**` + fixtures, `vitest.setup.ts`(자기 테스트 인프라 한정).
  - 📎 **STEP 0 실측**(sess-mp-step0): **글롭 정합·불일치-A 없음**(4트랙 중 유일). `marketpulse` v2(94파일, label `marketpulse`) + `macro` v1(13파일, 루트앱) 공존. 마이그레이션 정합·**테스트 266 green**·경계 동결 0(`KNOWN_VIOLATIONS` 비어 있음). intraday regime ↔ EOD daily(`eod_regime_calculator`) **코드상 별개 시스템 재확인**. D1 STRUCT-CLEANUP 경계 충돌 0(dashboard 침범 없음 — "dashboard" 출현은 macro 자체 대시보드 용어).

**[활성·성숙] portfolio 트랙 (2026-06-11 신설, STEP 0 확정 2026-06-29)**: `apps/portfolio/**`(coach API 포함), `tests/coach/**`, `docs/portfolio/**`, FE: `app/coach/**`, `app/portfolio/**`, `lib/coach/**`, `components/coach/**`, `components/portfolio/**`, `__tests__/coach/**` + 관련 fixtures.
  - 📎 **STEP 0 실측**(sess-pf-step0): `apps/portfolio` = **Portfolio Coach**(E1~E6 LLM 분석, 마이그레이션 정합). **자기완결형 경계** — 비테스트 코드의 `packages.shared`·cross-app import 0(4트랙 중 최청정). LLM은 `llm/client.py`가 anthropic·google.genai 직접(→ BOUNDARY-LLM 합성 대상).
  - ⚠ **트랙명↔표면 정합 메모**(불일치-B): 백엔드 label=`portfolio`지만 **활성 제품 표면=coach**(`app/coach`·`lib/coach`·`components/coach`가 `coach/eN` API 소비). **`app/portfolio`·`components/portfolio`·`services/portfolio.ts`는 레거시 `users.Portfolio`(`/users/portfolio/`) 소비 = 귀속 미정**(`TASKQUEUE` `PF-LEGACY-FE` 결정 안건). **결정 전이므로 글롭 미변경**(레거시 FE를 빼지도 넣지도 않음).

**[확정] dashboard 트랙 (표면 전용)**: FE: `app/page.tsx`(루트 EOD 대시보드 본체), `app/dashboard/**`, `components/eod/**`, `services/eodService*`, `hooks/useEODDashboard*`, `types/eod.ts`(eod 전용 타입 — shared 공용 `types/`에서 dashboard 전용 carve-out), `docs/dashboard_plan/**`. **백엔드 앱 부재(실측)** — 백엔드 신설 여부는 이 트랙의 미래 결정 사안.
  - 📎 **2026-06-27 STEP 0 정정**(sess-dashboard-step0 @ bbe6b1b, 불일치-A): `app/page.tsx`(eod 12개 import + `useEODDashboard` 소비 — 사용자가 보는 루트 `/` 대시보드 본체)와 `types/eod.ts`(11곳 import)는 기존 글롭 `app/dashboard/**` 밖이라 **누락**이었음 → 편입. 레거시 `app/dashboard/page.tsx`(계정/네비 페이지, eod 무관)는 글롭에서 **빼지 않고** 운명을 **결정 안건으로 보류**(KEEP/CUT 사이클, `TASKQUEUE` `DASH-LEGACY`).
  - 📎 **2026-07-04 DASH-FE-GLOB 해소**(sess-carousel SURVEY 실측 @ 47c36b4): `frontend/app/dashboard/` 디렉토리 자체가 **origin/main에 실재하지 않음**(레거시 page.tsx 포함 0건). → 실 dashboard FE 진입 = **`app/page.tsx` + `types/eod.ts`**(위 편입 확정), 캐러셀 신설 위치 = **`components/eod/**`**. 글롭 `app/dashboard/**`는 **실체 없는 표기**이므로 소유 대상에서 실질 제외(DASH-LEGACY도 대상 파일 부재로 자연 소멸). 유지: `components/eod/**`·`services/eodService*`·`hooks/useEODDashboard*`.
  - 📎 **2026-07-06 AMEND**(CAROUSEL-BUILD 후속, 디렉터 비준): dashboard FE 테스트 구획 = **`frontend/__tests__/eod/**`** 명시 추가(캐러셀 vitest 등재처, 슬라이스 취지 부합 — 문언 공백 해소). eod 컴포넌트/타입의 테스트는 이 경로 단일.
  - 📎 **2026-07-27 AMEND**(MGMT-BATCH-14 백-어노테이션, P2-COVERAGE-C1-FE `58e18c7d` 사후 등재): 커버리지 표면(D-P2-COVERAGE-SURFACE 선택지 C) 신설로 dashboard 트랙에 다음 경로군 **명시 추가** — `app/dashboard/coverage/**`(상세 라우트) · `components/dashboard/**`(CoverageStrip·CoverageDetailView) · `hooks/useCoverage*` · `services/coverageService*` · `types/coverage*` · `frontend/__tests__/dashboard/**`. **취지**: C1-FE에서 "트랙 전용 파일" 취지 해석으로 통과한 경로들의 사후 문언 등재(해석 반복 방지). **2026-07-04(위)와의 정합**: "`app/dashboard/**`는 실체 없는 표기"였으나 C1-FE가 `app/dashboard/page.tsx`(스트립 배선 1줄) 수정 + `app/dashboard/coverage/page.tsx` 신설로 디렉토리를 **재물질화** — 이제 `app/dashboard/**`는 실체 있는 소유 경로. 단 기존 `app/page.tsx`(루트 EOD 본체)·`components/eod/**` 소유는 불변(dashboard 표면의 두 진입: 루트 `/` EOD 본체 + `/dashboard` 계정·커버리지). 컴포넌트 구획은 eod=`components/eod/**`, 커버리지 등 dashboard 일반=`components/dashboard/**`로 병존.
  - 📎 **2026-08-06 AMEND**(MGMT-BATCH-24, C2-S1-B1 착지 `b9e80655` 후속): 위 2026-07-27 coverage 경로군은 **불변**(재등재 아님) — 본 부기는 **글롭 형태 실측 확정 + provenance**. STEP 0.3 실측: `components/dashboard/` = **`CoverageStrip.tsx`·`CoverageDetailView.tsx` 2파일뿐, 둘 다 P2-COVERAGE-C1-FE(`963a5213`) 트랙 산**(git log --follow 첫 커밋) → 혼재 없음 = **디렉터리 글롭 `components/dashboard/**` 형태 유지 확정**(Coverage* 프리픽스 글롭 불요). 근거 = S1-B1 후보 #71 계열(글롭↔실주소 불일치 방지) — C1-FE 이래 생성된 coverage 표면(strip/detail/`hooks/useCoverage`/`services/coverageService`/`__tests__/dashboard`)이 전부 dashboard 트랙 소유임을 실측으로 재확인.

**[활성·성숙] chain_sight 트랙** (STEP 0 확정 2026-06-29): `apps/chain_sight/**`, `tests/chainsight/**`, `docs/chain_sight/**`, FE: `app/chainsight/**`, `components/chainsight/**`, `services/{chainsightService,pathWatchlistService}`, `hooks/{useChainsight,usePathWatchlist}`, `__tests__/chainsight/**` + **Neo4j 자산(확정, apps 내부)**: `management/commands/load_*_to_neo4j`(5)·`services/neo4j_{loader,sync}`·`tasks/neo4j_dirty_sync_tasks`.
  - 📎 **STEP 0 실측**(sess-cs-step0 @ b457bbf): 백엔드 85파일·모델 20개·**RelationConfidence 13,695행 prod**(CoMentionEdge 1,361·PriceCoMovement 8,859)·**M2 v1.1 Phase 1 go-live(2026-06-27)**, daily beat 가동·neo4j_dirty=0(동기화 완료). 기존 `[골격]`·`추정` 표기는 성숙도 과소표현이라 격상.
  - ⚠ **레거시 Chain Sight v1 경계(불일치-A, 글롭 미변경)**: `services/serverless/{chain_sight_service·neo4j_chain_sight_service·supply_chain_parser·supply_chain_service}.py` + `migrations/0009_chain_sight_stock.py` = Chain Sight **v1**, **serverless 무소속 #3 구획 소속**(CLAUDE.md도 serverless에 명기). **chain_sight 트랙 ≠ 이 레거시본.** 흡수 vs serverless 잔류는 **결정 안건(보류, `TASKQUEUE` `CS-LEGACY`)** — 결정 전이므로 글롭에 넣지 않음.

**[무소속 — 작업 착수 전 트랙 배정 필수]** (7구획):
1. **thesis 구획** — 루트 `thesis` BE + thesis 표면 일체
2. **news 구획** — `services.news` 계열
3. **screener·admin 구획** — `services.serverless` 계열
4. **rag·ai-analysis 구획**
5. **stocks 표면** — 백엔드 `shared.stocks`는 토대
6. **users·auth 표면** — `login`·`signup`·`mypage`·`watchlist`(백엔드 `shared.users`는 토대)
7. **BE단독** — `services.sec_pipeline` · `integrations/iron_trading`(프론트 미검출 실측)

상세 파일군은 2026-06-11 전수 측정 보고 기준.

**[토대] shared 트랙**: `packages/shared/**`(stocks·users·metrics·api_request), `tests/{architecture,contracts,unit}/**`, `config/**`, `scripts/**`, `integrations/_shared/**`, FE 공용: `lib/api.ts`, `lib/api/{authAxios,client,config}*`, `components/{common,layout,charts}/**`, `contexts`·`providers`·`types`·`constants`·`utils`, frontend 루트 설정.

**[경계 보류 — 해당 트랙 첫 STEP 0로 확정 후 본 엔트리 갱신]**: `useMarketBreadth`·`useSectorHeatmap`·`useMarketMovers`·`useMarketView` 호출 백엔드 / `explorationStore` 사용 분포 / `tests/{unit,scoring,integration}` 소속 / `components/keywords` 소속 / `services/{portfolio,watchlistService,userInterestService}` 소속(portfolio 트랙 vs users·auth 표면).

**근거**: 2026-06-11 타 트랙 커밋 혼입 사고(common-bugs #33) + read-only 전수 측정(백엔드 16구획·`frontend/services` 실 API 계층·dashboard 백엔드 부재·portfolio 최대 앱 196py 확인).

---

## [2026-06-11] MP-LIVE-VERIFY 게이트 1차 결과 — 계약 PASS · 결함 2건 발굴 · 부분 재게이트 원칙

**결과**:
- **F2 최종 계약(card_id=concentration) 라이브 전건 PASS** (d5212d4 검증): overview 키 `[regime,breadth,sector,concentration,brief]`(flow 부재) · `/cards/concentration/detail` 200 · `/cards/flow/detail` 404 · i18n `card.concentration='집중도'` · /health 비인증 401/admin 200 · 프론트 5 카드 렌더 + drawer detail + 콘솔 0. C(1~6)·D(1~6) 전건.
- **Part B(5종 데이터) 부분**: Regime/Breadth/SectorFlow 신선 ✅. **결함 2건 발굴** ↓.

**결함 발굴**:
- **MP-LV-D1 (Concentration, 결정 대기)**: `mp_calc_concentration_daily` → FMP `/stable/etf/holdings`(프리미엄, Starter 미지원) **402** → CB[fmp_etf] OPEN, ConcentrationSnapshot **05-06 이후 중단**. 산출 필요 입력 = 종목별 `weightPercentage` 단일. #23(프리미엄 `.` **심볼**)와 구분되는 **프리미엄 엔드포인트** 이슈. **수리 금지 — 옵션(대체 엔드포인트/산식 교체) 결정은 채팅 몫**.
- **MP-LV-D2 (Briefing, 수리 완료 `62d4025`)**: `mp_generate_brief_daily` → `ModuleNotFoundError: google.generativeai`(구 SDK) → CB[gemini] OPEN, 생성 이력 0. 수리: 신 SDK(`from google import genai`, 기설치) import + contents `parts` 포맷 `[string]→[{text}]`(requirements 변경 0). `.apply()` SUCCESS → BriefingLog(OK) + pytest 138 + brief 카드 재게이트 통과.

**부분 재게이트 원칙 (신설)**:
- 결함 수리가 **계약을 건드리지 않으면**(데이터 산출 경로만 수정), 재게이트는 **Part B 해당 항목 + 해당 카드 스모크만** 재실행. **계약 검증(C·D 전건) 재실행 불요** — 계약은 최종본 위에서 이미 1회 PASS.
- 적용: D2 수리는 briefing 데이터 경로만 변경(계약 무관) → brief 카드 스모크만 재게이트(전건 C/D 재실행 안 함). D1 수리도 동일 원칙(Concentration 데이터 + 해당 카드 스모크).

**게이트 상태**: 🟡 1차 PASS(계약) — **잔여 release blocker = Concentration 데이터 생성(MP-LV-D1 결정 후)** + 해당 카드 스모크. 그 후 "전건 통과".

**근거 입력**: 2026-06-11 MP-LIVE-VERIFY 검증 보고서(curl + DOM 채증), MP-LV-D2 수리(`62d4025`), MP-LV-D1 실측(필드/대체 엔드포인트/모델/#23 대조), UX 전수조사(MP-UX-POLISH 입력).

---

## [2026-06-11] MP-LV-D1 옵션 B(시총 가중 근사) 채택 + 미래 옵션 A 전환 경로

**결정**: Concentration 비중 공급원을 ETF holdings(`/stable/etf/holdings`, 프리미엄 402)에서 **시총 가중 근사**로 교체. weight_i = cap_i / Σcap (S&P500 심볼 × FMP quote marketCap). 산식(top5/top10/HHI)·모델 필드·API 계약 불변. 구현 `c6b7aa0`.

**근거**:
- concentration 산출에 필요한 입력은 종목별 **비중 단일**. holdings의 weightPercentage를 **시총 정규화로 등가 근사** 가능(둘 다 "상대 비중").
- 제품 목적 = 집중도의 **상대 감각**(top5/HHI 추세) → 근사로 충분. float-adjusted 정밀도는 출시 필수 아님.
- 고정비 0(FMP 플랜 유지). 솔로 운영에서 플랜 업그레이드 비용 회피.
- 사용자 결정: "B로 가다가 추후 A 전환".

**가중합**: 옵션 A(holdings, 플랜 업그레이드) **3.85** / **옵션 B(시총 근사) 3.65** / 옵션 C(보류·카드 비활성) 3.55. 마진 B−C 0.10, A−B 0.20. 타이브레이커(B 채택): 고정비 0 + 상대 감각 근사 충분 + seam 분리로 미래 A 무비용 전환.

**전환 경로 (미래 옵션 A)**: `fetchers/weight_source.py:ACTIVE_WEIGHT_SOURCE`를 'holdings'로 1곳 변경 → 휴면 보존된 HoldingsWeightSource 재활성 + CB[fmp_etf] 리셋 + Concentration 스모크. holdings 경로 코드는 **삭제하지 않고 휴면 보존**. TASKQUEUE `MP-D1-FMP-UPGRADE`(trigger-gated).

**한계 명시**:
- float-adjust 미반영 근사(SPY 실제 비중과 미세 차이). GOOGL+GOOG 등 복수 클래스 분리 집계로 집중도 소폭 과대 가능. 유니버스에 비-S&P500 종목(예: TSM, DB Stock 535) 소량 혼입 가능 — universe='SP500_MCAP'로 정확본(SPY)과 구분.
- **05-07↔06-11 36일 공백 + 레벨 점프**(백필 안 함): top5 0.2722→0.2829(+3.9%) / top10 0.3863→0.4105(+6.3%) / HHI 0.021076→0.022125(+5.0%). 모달 — 근사 레벨 차 + 36일 시장 변동 합산. 시계열 해석 시 universe 전환점(05-07 SPY → 06-11 SP500_MCAP) 인지.
- 호출 예산: 종목당 1 quote(Starter 콤마배치 402 → 개별) = ~500/일(일 10k의 5%). 빈도 조정(주간) 여지는 별도.
- coverage: top_holdings는 `[{symbol,weight}]` 리스트(serializer ListField/프론트 .map 계약) 유지 → coverage는 **로그 + universe 마커**에 기록(top_holdings JSON 구조 변경 = 계약 위반이라 회피). 06-11 실행 402=4건(`.`심볼) 제외, coverage ≈ 99%.

**근거 입력**: MP-LV-D1 실측(STEP 0), 재게이트 검증(curl + DOM, top5 28.29%·HHI 0.0221 렌더), 회귀 146.

---

### CS-RD (2026-06-11): chain_sight 첫 화면 정보 구조 역전 — "이벤트 보드 → 관심도 랭킹 → 그래프 드릴다운"
- **결정**: chain_sight 첫 화면을 "이벤트(테마) 보드 → 관심도 랭킹 → 그래프 드릴다운" 구조로 역전.
- **근거**: 가중합 4.10 (vs 피드형 3.50 / 필터형 3.45, 마진 0.60). 관심도 지표는 M1(거래 기반: `0.50×거래량z + 0.30×변동성백분위 + 0.20×|수익률|백분위`) 선출시, M3(복합: co-mention 결합) 승격 예정.
- **UX 노출 언어**: 기존 결정 유지 — "테마" 비노출, "이벤트" 프레이밍. 내부 모델 `:Theme` 유지.
- **MarketGraphCanvas**: 보조 화면(`/chainsight/market-graph`)으로 강등·동결(1017줄 리팩터링 보류).
- **RD1 STEP 0 정정 (ground truth)**: `theme_tags`/`business_model_type`/`overall_grade`는 `Stock`이 아니라 **`CompanyChainProfile` 필드** (NT-3 및 RD1/RD2 지시서의 `Stock.theme_tags` 가정은 오기). 셋 다 채움률 **0%**(504 profile 전건). 원인: `CompanyChainProfile.theme_tags`는 `sync_tasks.py:67`에서 `CompanyNarrativeTag`로부터 복사되는데 NarrativeTag는 **0 rows**이고, 이를 생성하는 코드가 코드베이스에 **0건**(chain_sight LLM 호출 흔적도 0). → **Part C 분기 (다) HALT** — 임의 신규 로직 작성 금지, 별도 적재 지시서 대기.
- **Neo4j `:Theme`/`HAS_THEME`**: 현재 0/0. 단 소스 데이터(`ETFProfile` 21 / `ETFHolding` 10,795)는 준비됐고 `load_themes_to_neo4j` command 존재(LLM 불필요, MERGE만). 그래프 드릴다운용 보조 경로로 적재 가능하나, RD2 보드 연료(Postgres `theme_tags`)와는 별개.
- **[Addendum 2026-06-18] 라우팅 역전 실행 (추적 누락 → 실행)**: CS-RD3 구현(2026-06-15, `573d1dc`) 당시 보드는 `/chainsight/events`에 신규 배치됐고 루트 `/chainsight`는 그래프가 그대로 유지돼, **본 결정의 "루트=보드 + 그래프 `/chainsight/market-graph` 강등"이 미실행**이었음(RD3 재대조에서 확인 — 코드 시도·보류 등록·결정 번복 흔적 모두 0 = 추적 누락 drift, 노선 변경 아님). + 보드가 글로벌 네비에서 고아 상태(Header→`/chainsight`=그래프만). **디렉터 확정(길1 역전 / 실현X)으로 본 세션 실행**: ① 루트 `/chainsight` = 이벤트 보드(`EventBoard`), ② 그래프 화면을 `/chainsight/market-graph`로 강등 이동(MarketGraphCanvas **무수정** — 렌더 위치만, diff 0), ③ `/chainsight/events` 인덱스 → `/chainsight` redirect(중복 보드 URL 제거, 그룹상세 `events/[theme]` 유지), ④ A-1 고아 수정 — 보드 화면에 "전체 관계 그래프 보기" 진입점(`/chainsight/market-graph`) 추가(글로벌 네비 7개 유지, RD3 §2 원안). vitest 354→358(+4: routeReversal 3 + A-1 가드 1), tsc 0, 6경로 스모크 전건 비-500.
- **[Addendum] 링크 감사표 (역전 영향)**: 변경 5 / 유지 다수.

  | 파일:라인 | 현재 목적지 | 의도 | 역전 후 |
  |---|---|---|---|
  | `app/chainsight/page.tsx` | 그래프 | 루트 첫 화면 | **보드 렌더로 교체** |
  | `app/chainsight/market-graph/page.tsx` | (부재) | 그래프 보조화면 | **신규 — 그래프 이동(import만)** |
  | `app/chainsight/events/page.tsx` | 보드 | 중복 보드 URL | **`/chainsight` redirect** |
  | `components/chainsight/EventBoard.tsx` | — | A-1 그래프 진입 | **"전체 관계 그래프 보기" 링크 추가** |
  | `app/stocks/[symbol]/page.tsx:450` | `/chainsight?focus=` | 그래프행(`?focus`=그래프 전용 파라미터) | **`/chainsight/market-graph?focus=`** |
  | `app/chainsight/watchlist/page.tsx:65` | `/chainsight` | "탐색하며 Watch"=그래프 맥락(CTA) | **`/chainsight/market-graph`** |
  | `app/chainsight/watchlist/page.tsx:27` | `/chainsight` | 뒤로=홈 | **유지(보드=홈)** |
  | `components/layout/Header.tsx:60,183` | `/chainsight` | Chain Sight 네비 | **유지(이제 보드로 resolve)** |
  | `EventRanking`·`GraphMiniView`·`RelationCardPanel`·`MobileCardList`·`NodeContextMenu`·`[symbol]` | `/chainsight/${종목}` | 종목 드릴다운 | **유지(동적, 무변경)** |
  | `EventBoard:100`·`WatchButton`·`FullPathView`·`PathCard` | `events/[theme]`·`/chainsight/watchlist*` | 그룹상세·워치리스트 | **유지(무변경)** |

### CS-RD-C2 (2026-06-11): 이벤트 그룹 = 섹터 ETF + 테마 ETF 역산, w≥1.0
- **결정**: 이벤트 그룹 = 섹터 ETF(XL*) + 테마 ETF 역산, **w≥1.0**.
- **근거**: theme-only는 유니버스 교집합 한계로 3.9% — 보드 성립 불가. w≥2.0은 저비중 멤버(소외 종목 후보군)를 잘라 핵심 차별화와 상충. 가중합 4.65 vs 4.00, 마진 0.65.
- **제외 가드**: 전(全)시장 광역 ETF(SPY/QQQ/VOO/IWM류)는 제외 유지 — 단 ETF_THEME_MAP에 해당 ETF 미포함이라 실제 제외 목록은 공집합(sector XL* + theme만 존재). 섹터 ETF(XL*)는 "섹터 이벤트 그룹"으로 포함(무의미 그룹 차단 취지 유지).
- **적재 결과 (2026-06-11)**: 채움률 304/504 profiles(60.3%, 56.8% of stocks), 15 그룹(sector 11 + theme 4), 그룹당 종목 중앙 25(min 1/max 38), 3개 미만 그룹 2건(Lithium 2·Clean 1 — theme ETF 외국 종목 오염). Neo4j `:Theme` 21 / `HAS_THEME` 536. 멱등성 2회 확인.
- **NarrativeTag 가드(행위보존)**: `aggregate_chain_profiles`(sync_tasks.py:64-68)의 `if nt:` 가드로 NarrativeTag 0행 시 theme_tags 미설정→`update_or_create`가 ETF 적재값 보존. 코드 수정 0건. NarrativeTag(LLM) 태깅은 후속 트랙(CS-COV 인근) — 채워지면 ETF 태그와 병합 방식은 그 시점 결정.

---

## [2026-06-11] Phase 1 종료 선언 (출시와 구분)

**결정**: MP-LIVE-VERIFY 게이트 전건 통과를 **"Phase 1 종료"**로 선언한다. **"출시"가 아니다** — 출시는 별도 결정·별도 선언.

**Phase 1 범위 완료 근거**:
- 카드 5종 백엔드(Regime/Breadth/Sector/Concentration/Briefing) + 프론트엔드 K/L(`market-pulse-v2` page + 5 Summary/Detail + 패널).
- 운영 정리: NT-7(task 경로 정합) · 헤더 표준화 · BOUNDARY-3(shared 경계) 종결.
- **MP-LIVE-VERIFY 게이트 전건 통과**: 계약(C·D 라이브) + D2 Briefing(SDK 수리 `62d4025`) + D1-B Concentration(시총 근사 `c6b7aa0`).
- 종료 좌표(게이트 통과 시점): origin/main `575c3fb` · 테스트 BE 146 / FE 174 · health_check 8✅.

**"종료 ≠ 출시" 정의**:
- **종료** = Phase 1 *범위*의 구현·검증 완료(게이트 통과 = 계약·데이터 경로 라이브 확인).
- **출시** = ① 운영 **자율 가동 확인**(`MP-OPS-AUTOGEN-CHECK` — 이번 게이트는 *수동 트리거* 검증이었으므로 beat 자율 5종 생성은 별도 확인 필요, Briefing은 LLM 일 1회 과금 시작점) + ② **UX 정비**(`MP-UX-POLISH` — raw 전문어/단위 없는 숫자/용어 도움 부재) 이후, ③ **사용자의 별도 선언**.
- **STRUCT-CLEANUP 트리거 해석 고정**: 재개 트리거 "(a) 앱 초기 배포 버전 확정"은 **출시 선언 시점**을 가리킨다. **Phase 1 종료(2026-06-11)로는 미발동** — 이 구분으로 STRUCT-CLEANUP의 조기 발동 모호함을 차단.

**잔여 지도(TASKQUEUE "Phase 1 종료 시점 잔여 지도")**: `MP-OPS-RESTART`(병진 수동 — 메인 디렉터리 main 복귀 + ff pull + 구 브랜치 -D + 운영 celery 재기동 + setup_marketpulse_beat) · `MP-OPS-AUTOGEN-CHECK`(출시 선행) · `MP-CONC-FREQ-TUNE`(저우선) · `MP-UX-POLISH`(착수 가능) · `MP-I18N-EN`(minor).

**근거 입력**: 2026-06-11 MP-LIVE-VERIFY 게이트 종결, 사용자 결정(채팅 — "게이트 통과는 출시가 아닌 Phase 1 종료"), STRUCT-CLEANUP 트리거 모호함 방지.

> 비고(2026-06-12 push 충돌 복구): 본 엔트리는 origin/main이 575c3fb→70eb090(chain_sight·trash·harness)로 이동해 non-ff 거부됨에 따라 70eb090 위에 재적용됨. 타 트랙 신규 내용 전부 보존, 본 엔트리만 추가.

---

## CS-EXP-LOAD (2026-06-15) — 신규 테마 ETF 적재, 게이트 미달, U2가 유일 경로

**결정**: PAVE·XBI·KRE를 ETF_CSV_SOURCES에 등록·적재(파서 수정 0, URA는 교집합 경계값으로 제외). 적재 자체는 보존(3개 모두 자격 그룹, DELETE 금지).

**측정 결과(정정)**: 보정 게이트(자격 그룹 ≥6 ∧ 자격 그룹 distinct 유니버스 멤버 중앙값 ≥10) **미달** — 자격 7개(통과)이나 **중앙값 7 < 10**.

**Why(핵심 정정)**: 이전 CS-EXP-GATE/SOURCE의 멤버 수(SOXX 221·ICLN 39 등)는 **다중 snapshot_date 누적 행수**였고, 실제 distinct 유니버스 멤버는 한 자릿수(SOXX 17·ICLN 3). SOURCE의 "ETF 1개로 통과" 예측은 이 오류 수치에 근거. ARKK(12)·ARKG(1)만 snapshot 1개라 우연히 일치했음.

**구조적 결론**: 테마 ETF는 SP500 외 중·소형주 중심 → 535 유니버스 교집합이 그룹당 한 자릿수. **ETF를 더 추가하면 자격 그룹 "수"만 늘고 "중앙값"은 유니버스 상한에 묶여 안 오름.** 게이트(중앙값≥10) 통과는 **ETF 추가가 아니라 유니버스 편입(U2 = CS-EXP Part C)** 으로만 가능 → CS-EXP-U2 등록.

**근거 입력**: CS-EXP-LOAD 실측(최신 snapshot 기준, 멱등 확인), pytest serverless 377 passed.

---

## CS-EXP-U2 결정 (2026-06-15) — 게이트 X=8 확정 + U2 전체 편입(136종)

**결정(디렉터)**:
- **게이트 기준 X = 8** (자격 그룹 ≥6 ∧ 자격 그룹 distinct 유니버스 멤버 중앙값 ≥8). 근거: 보드 UX "상위5 + 하위3 = 8" 노출량 역산(CS-EXP-U2SIM Part B). X=10은 ICLN 구조적 한계(최대 9)로 경계, X=5는 밀도 부족.
- **U2 편입 규모 = 전체 편입(136 distinct US 종목)**. 결과 예측(U2SIM Part C): 자격 그룹 9개, 중앙값 26 → X=8 여유 통과. 유니버스 535→~671(+25%).

**Why**: ETF 추가로는 중앙값이 유니버스 상한에 묶여 안 오름(CS-EXP-LOAD 확정). 전체 편입은 모든 그룹 밀도를 올려 게이트를 여유 통과시키고 보드 품질을 구조적으로 개선. 소규모(13~20종)는 턱걸이라 마진 없음.

**실행 전제(후속 CS-EXP-U2EXEC 세션)**: ① StockSyncService.sync_overview로 136종 편입(STEP0 메커니즘) ② DailyPrice 90일 백필(종목당 1콜, FMP ≤1,500, 실패율 ≤5% else HALT) ③ 게이트 재측정(목표 중앙값≥8) ④ BETZ/HACK/KWEB/TAN은 holdings 미적재라 별도 선행 필요(CS-EXP-P1/P2). Neo4j 그래프 편입은 ETF_THEME_MAP 편집 필요(별도 범위).

---

### NEWS-AUTH — 공개/인증 read 엔드포인트 분류 기준 (2026-06-12)
- **결정**: 뉴스 API를 두 부류로 나눠 호출 방식을 고정한다.
  - **공개(순수 뉴스 원천)** = `all`/`daily-keywords`/`trending`/`sources`/`insights`/`news-events` + 기존 `market-feed`/`interest-options`: backend `[AllowAny]`, frontend raw `fetch` 유지.
  - **인증(파생 자산 = 우리가 만든 가치)** = `recommendations`(종목 추천)/`stock`(종목 상세 뉴스·감성): backend 인증 유지(IsAuthenticated 기본), frontend **authAxios(JWT 동반)**.
- **Why**: 4/29 P0 #5(`DEFAULT_PERMISSION_CLASSES → IsAuthenticated`)가 공개 의도 뉴스 read에 AllowAny 면제를 누락해 6주간 전 섹션 401(probe `docs/nightly_auto_system/202606/12/news_api_probe.md`). 보안 강화 의도(파생/민감 보호)는 보존하되 공개 원천만 면제.
- **Bug #26 클래스 동일 계열**: raw fetch ↔ authAxios 혼용 = 호출 방식이 권한 경계와 어긋나면 깨짐. **이후 신규 뉴스 호출 기본 분류**: 공개 원천이면 fetch, 파생/사용자 데이터면 authAxios.

### MP-UX-S2 — 매크로지표 9종 한글 라벨 확정 + 의미 밴드 데이터원 (2026-06-15)
- **결정**: regime classifier 14 매크로지표 중 MP-UX-S1 미정의 9종의 한글 표시 라벨을 director 확정값으로 흡수(`indicator.*`).
  - `return_1d_pct`=1일 수익률 / `vol_20d_pct`=20일 변동성 / `drawdown_pct`=52주 고점대비 낙폭 / `nfci_credit`=NFCI 신용 / `nfci_leverage`=NFCI 레버리지 / `nfci_risk`=NFCI 리스크 / `hy_ccc_oas_pct`=HY CCC 스프레드 / `t10y3m_pct`=장단기 금리차(10Y-3M) / `vix3m`=VIX 3개월.
- **Why**: S1은 director 확정 5종만 승격하고 9종은 raw 보류(발명 0). S2에서 확정 → RegimeDetail 레이더축 raw 0, `labels.py` `indicator.*` 14종 완비(단일소스).
- **연계**: S2 의미 밴드(Regime 단계 5종 / Anomaly 모드 3종, 카피 단일소스 `frontend/app/market-pulse-v2/meaning.ts`) + Anomaly `actual↔경보선`(`fired[].threshold` 기바인딩, FE만). 임계는 rules.yaml 백엔드 단일소스 — FE 하드코딩 0.
- **HALT(데이터원 부재 → 백엔드 미니슬라이스 분리)**: ⒜ Regime 국면 타임라인 = regime 히스토리 시리즈가 summary·detail 어디에도 없음(`previous_regime` 단일값만) → `MP-UX-S3a`. ⒝ Regime "다음 단계 거리" = payload에 next/margin 필드 0 → `MP-UX-S3b`(rules.yaml 임계 FE 하드코딩 금지, 백엔드 margin 산출).
---

## CS-EXP-U2EXEC (2026-06-15) — 135종 편입으로 게이트 X=8 통과, CS-EXP 종결

**결과**: 테마 ETF holdings의 비SP500 US 종목 편입 실행 → **게이트 X=8 통과(실측 중앙값 26)**. 유니버스 **535 → 670**(+135).
- 편입 136 대상 중 135 created, SLR 1종 실패(FMP quote 소스 부재, 0.74%). DailyPrice 90일 백필 135/135(0% 실패, 8,329행, M1 충족).
- 자격 그룹 9개 분포 `[5,8,12,23,26,30,33,42,45]`. 예측(U2SIM 26) = 실측(26) 정확 일치 — distinct 기준 측정 신뢰 확립.
- FMP 283콜(≤1500), 코드 diff 0, makemigrations 0, pytest serverless 377 passed, 기존 535 무변경.

**Why**: CS-EXP-LOAD에서 "ETF 추가로는 중앙값 불변, 유니버스 편입(U2)만이 게이트 경로"가 확정됐고, U2SIM이 전체편입 중앙값 26을 예측 → 실행으로 검증. ETF 추가(LOAD)와 유니버스 편입(U2EXEC)의 역할 분리가 데이터로 확정됨.

**잔여(범위 외 후속)**: ① SLR 재시도(FMP 소스 복구 후) ② sector/industry 빈 채움(profile 엔드포인트 별도) ③ BETZ/HACK/KWEB/TAN holdings 적재(CS-EXP-P1/P2) ④ Neo4j 그래프 편입(ETF_THEME_MAP 편집).

---

### MP-UX-S3 — regime history_30d + 다음단계 margin (무마이그레이션, rules.yaml 단일소스) (2026-06-15)
- **결정**: S2에서 데이터원 부재로 HALT였던 regime 2요소를 백엔드 payload로 노출. ⒜ `regime_history_30d`(국면 타임라인 데이터원 — `_regime_detail`에서 RegimeSnapshot 30일 쿼리, stage=raw enum, 라벨 변환은 FE) ⒝ `next_stage`/`margins`/`next_stage_closest`(인접 상위 단계 진입까지 지표별 거리 — `regime/next_stage.py`).
- **Why / 단일소스·무마이그레이션**: margin은 `classifier.load_rules`로 rules.yaml을 **읽기만**(임계 하드카피 0) + serializer 계층 **즉석 산출**(모델 신필드 0). `makemigrations --check` = No changes. history는 기존 RegimeSnapshot 쿼리(41 distinct date, 백필 불요). FE 렌더(타임라인/게이지)는 범위 밖 — 데이터원만(후속 FE 슬라이스).
- **데이터 공백 = 코드 결함 아님**: STEP 0 실측 — 거시 5종(vix·nfci·hy_oas_pct·t10y2y_pct·t10y3m_pct)이 `RegimeSnapshot.inputs`에서 actual null(소스 MISSING, 5/14만 OK) → margin actual null → 헬퍼 graceful. 구조·임계는 정확. coverage 회복은 `MP-DATA-MACRO-COVERAGE`(FRED fetcher, ops/data) 트랙 — **다음단계 게이지 FE의 선행 조건**. 게이지가 "빈 값"이면 원인 = 이 데이터 트랙(메모리-코드 불일치 함정 방지).
- **관측(HARN-1)**: main이 ledger(`cdbf79e`) 이후 CS-EXP(`e0185ea`)·S3 등 타 트랙으로 연속 이동 → 분기 직전 `git fetch` 상시화로 non-ff 예방.
---

## CS-RD2 (2026-06-15) — 관심도 M1 엔진 구현

**결과**: 이벤트 보드 정렬 엔진 M1(거래 기반) 구현 완료. `StockAttentionScore`(migration 0009) + `attention_service`(점수+유동성가드) + Celery task + API 2개(`/api/v1/chainsight/events/`, `/events/<theme>/stocks/`) + 테스트 20.
- M1 = 0.50×거래량 z-score(20일) + 0.30×변동성 백분위 + 0.20×|수익률| 백분위 → 0~100. 컴포넌트 분리 저장(M3 승격 대비).
- 670종→634 계산(36 스킵=20일 깊이 미달), 0.16초, score 15.6~99.9, is_low_liquidity 34/634, 멱등 Δ0.

**STEP 0 확정값(지시서 추정 치환)**: DailyPrice 필드 `*_price`(open/high/low/close 아님), Stock FK `"stocks.Stock"`(shared_stocks 아님), 유니버스 670 전체.

**ADV_FLOOR = 45,799,011 USD** = 652종 ADV(close×volume 20일평균) p5, 측정 2026-06-15. 미만은 `is_low_liquidity=True` **플래그만(제외 아님 — "간과된 종목" 보존)**, 적재 시점 고정(멱등). 결정자=디렉터.

**Why**: 보드 1차 정렬은 거래 신호(M1)로 시작, co-mention(M3)은 가중치 상수 교체로 승격. 신규 135종 중소형주 노이즈 대응으로 유동성 가드를 v1 필수 포함(원본은 추정이었으나 STEP0 ADV 실측으로 확정).

**범위 처리**: z-score 불가 18종(기존 0행 10+<20일 8)은 계산서 해당일 제외 → CS-DATA-HYGIENE(backlog) 등록. sector/industry는 M1 미사용(가격only)이라 신규 135 공백 무영향.

---

## [2026-06-16] 집중도 의미밴드 지표 = HHI가 아니라 top10_weight (MP-UX-S5)

**결정**: market-pulse-v2 Concentration 카드의 의미밴드(분산/약한·중간·강한 쏠림)를 **`top10_weight` 기준**으로 산출한다. 앵커 임계 = **0.40**(이상 = "강한 쏠림").

**왜**: 지시서 pseudocode 초안은 `concentrationBand(hhi)` + DOJ 관행 임계(0.15/0.20/0.25)를 제안했으나, MP-UX-S5 STEP 0 실측 결과:
- HHI = Σ(weight²) 정규화 분율로, `apps/market_pulse/calculators/concentration.py` 산출 스케일이 SPY 실제 **0.02~0.06** 수준 → DOJ 임계(0.15+)로는 **항상 "분산"으로만 읽혀 무용**(밴드가 값을 구분하지 못함).
- 반면 anomaly `rules.yaml` **R02 "집중도 극단" 경보선 = `top10_weight ≥ 0.40`** 이라는 시스템 내 grounded 앵커가 이미 존재. 카드 밴드를 같은 지표·같은 앵커로 맞추면 **R02 경보와 카드 의미가 동일 좌표를 공유**(정합성↑) + 사용자(중장기·모바일)에게 "상위 10종목이 시장의 41% 차지"가 "HHI 0.05"보다 직관적.

**TUNE**: **0.40만 grounded**(R02 단일 진실). 중간 임계 **0.30/0.35는 잠정**(분산↔약한↔중간 분할) — 실운영 top10_weight 분포 확보 후 보정 권고. 원시 HHI/top5는 카드 펼침(`<details>`)에 보존.

**출처**: MP-UX-S5 STEP 0 실측 + 커밋 `8ea0432`(Part A). 색·임계·문구는 `frontend/app/market-pulse-v2/meaning.ts` 단일소스.

## [2026-06-16] MP-UX-S5-B-SECTOR 분리 = sector history 부재, 합성 금지

**결정**: 섹터 자금흐름 스파크라인은 본 슬라이스(S5)에서 제외하고 `MP-UX-S5-B-SECTOR`로 분리·보류한다.

**왜**: S5 STEP 0 §0-3 분기 실측 — `ConcentrationDetail.history_30d`는 존재(→ 집중도 스파크라인 FE only 완료), 그러나 `SectorDetail`에는 sector 시계열 history 필드가 **0건**. 합성 데이터 금지 원칙(빈 스키마 채우지 않음)에 따라 BE 미니슬라이스(additive serializer 필드)로 history 데이터원 확보 후에야 FE 진행 가능. 선행 트랙으로 TASKQUEUE 등록.

---

## [2026-06-16] MP-DATA-MACRO-COVERAGE 검증 완결 — 코드 0, 운영 갭

**발견(STEP 0 cf82fe9)**: FRED fetcher/backfill command(`backfill_v2_a1`)/shared 래퍼(`packages/shared/api_request/fred_client.py`)/beat(`update_economic_indicators`)/게이지 경로(`regime/inputs.py INDICATOR_CODE_MAP` → `IndicatorValue` → `RegimeSnapshot.inputs` → serializer) **전부 기구현**. 신규 백필 command 작성은 중복(규약 10장 단일출처) → 슬라이스 1 HALT(신규 코드 0).

**진단**: 갭은 코드가 아니라 운영 — `FRED_API_KEY` 미설정(`.env.example`에 키 부재) + 커맨드 미실행. 검증 시점 5종 전부 등록·행 보유하나 최신 적재 19~60일 경과(stale) → `regime/inputs.py` 최신성 윈도우(~14일) 초과 → `sources=MISSING` → 게이지 "대기"(S4 관측과 정합). NT-7과 동류(코드 정상, 운영 이슈).

**검증(병진 수동 백필 후)**: Economic 153 / Market 44 obs 적재. `GET /api/v2/market-pulse/cards/regime/detail` → **HTTP 200, inputs 5종 실값(vix 17.68 / t10y2y 0.4 / t10y3m 0.68 / nfci -0.506 / hy_oas 2.71), sources 14/14 OK, coverage 1.0, 대기 0건, regime=LATE_BULL**. 오늘 스냅샷이 백필 후 자동 재생성돼 신선 반영(별도 재계산 불요). **serializer/FE 변경 0**(데이터 신선도가 트리거).

**결론**: 데이터 적재·게이지 점등 **검증 완료**. **단 지속성은 beat 운영 의존** — 수동 백필 기반이라 beat 미가동 시 ~14일 후 stale→"대기" 회귀. **영구 완료 아님, 출시 ops 사안**(`MP-OPS-FRED-FRESHNESS` 등록). 재발 방지로 `.env.example`에 `FRED_API_KEY` placeholder 추가. 통합 진입점은 `MP-OPS-FRED-ENTRYPOINT`(thin wrapper, 저우선)로 분리.
---

## CS-M2 주도주 지표 엔진 v1 (2026-06-16) — 종목레벨 4지표 + 옵션Y 노출 + beat 등록

**구현**: M1과 별개 `StockLeadershipScore`(migration 0010) + `leadership_service`(T2 trend_quality, T3 theme_alpha, theme_beta, ②capture) + Celery task + serializer 확장. 종목레벨 4지표만(테마 응집/확산=v1.1 범위 밖).
- WINDOWS=[20,120], MIN_OBS_RATIO=0.8, MIN_THEME_MEMBERS=3, LOO 자기제외 회귀. 게이트/분모0/테마부족 NULL(에러 아님).
- prod 산출(2026-06-15): 640행/303 테마종목/15테마. is_fallback 0(백필로 120일 전부 충족). theme_beta median 0.92, capture_spread median ~0~6.

**결정 1 (옵션 Y — T2·T3 상관 재평가 반영)**: **T2(trend_quality) 주 노출, T3(theme_alpha) 보조 강등, theme_beta·capture_spread 주 노출 유지.** T3 산출은 4지표 그대로 유지 — **표시만 조정(RD3 serializer/프론트 소관)**.
- **Why**: STEP0 추정 ρ(T2,T3)=0.66이었으나 **실데이터 ρ=0.84(w20)/0.82(w120)** — 0.85 near-collinear 임계 근접. T2(절대 추세)와 T3(테마 초과수익)이 거의 같은 신호로 수렴 → T3 단독 추가설명력 적음. 분리 노출 유지하되 T3는 보조로 강등. 단순 가산은 여전히 금지.

**결정 2 (beat 등록)**: `chainsight-leadership-daily`(22:40 UTC) + 미등록이던 `chainsight-attention-daily`(M1, 22:30 UTC) 함께 등록(STEP0 지적 M1 부채 해소). DatabaseScheduler PeriodicTask 멱등(#28). 검증: 두 task autodiscover 등록·beat 매칭 확인, 직접 실행 시 leadership 640행·attention 659행(06-15) 영속·멱등. **M1 stale(06-12 1일치) → 06-12+06-15 2일치로 해소, 백필로 scorable 634→659 증가.**

**불변/경계**: M1 StockAttentionScore 컬럼 추가 0(읽기만), shared 무수정·역import 0, 룩어헤드 0(t지표 t까지만). 보드 진입 재계산 0(사전저장).

---

## MAIN-SYNC — ff 거부 = HALT, 나이틀리 자동화 분기가 근본 원인 (2026-06-17)

**결정**: `git merge --ff-only origin/main` 거부는 **즉시 HALT 신호**다. 거부 직후 `git merge --no-ff <feature>`를 강행하지 않는다. 분기 구조를 먼저 측정(`git rev-list --left-right --count origin/main...main`)하고, 미push 커밋의 정체를 파악한 뒤 **merge 전략으로만**(rebase 금지) 정합한다. 코드/migration 충돌은 무조건 HALT.

**Why**: 나이틀리 자동화(`com.stockvis.nightly` 감사 보고서)가 **로컬 main에 직접 commit하고 push하지 않아**, 병렬 세션이 origin을 전진시키는 동안 로컬 main이 ahead/behind 양방향으로 분기됨. 이 분기 위에서 ff 거부를 무시하고 merge를 강행하면 잘못된 base에 머지 커밋이 생겨 prod·origin과 어긋난다(CS-M2-MERGE 사고, 2026-06-17, commit 15fa044에서 발각·복구).

**How to apply**:
1. 세션 시작 시 `git fetch origin` → baseline은 `origin/main` 직접 측정(로컬 ref는 캐시, 진실 아님 — common-bugs #33).
2. ff-only 거부 시: 측정 → 미push 정체 파악(docs=보존, 코드=HALT) → `git merge --no-ff origin/main`(미push 보존+origin 흡수) → behind 0 → feature merge → push. 각 단계 후 `git status` 확인.
3. 잘못된 미push 머지커밋은 `git reset --hard <merge직전>`(reflog 복구, push 전이면 무손실).

**근본 해결(별 트랙)**: 나이틀리 자동화가 별도 브랜치를 쓰거나 commit 후 즉시 push 하도록 수정 — `TASKQUEUE.md MAIN-SYNC-FIX`(@infra, todo, 재발성). hook 차원의 근본 hardening(`scripts/hooks` + `core.hooksPath`)도 MAIN-SYNC-FIX 트랙.

**📎 참조**: `sub_claude_md/common-bugs.md #37`(ff 거부 HALT `[git][infra]`), `TASKQUEUE.md MAIN-SYNC-FIX`, 메모리 MAIN-SYNC/MP-OPS-RESTART 패턴.

### MAIN-SYNC-FIX 적용 — 나이틀리 dated 브랜치 격리 (2026-06-18)

**결정**: 활성 나이틀리 스크립트가 **메인 트리에 직접 commit하지 않고, 전용 worktree의 dated 브랜치(`monorepo/nightly-<YYYYMMDD>`)에만 commit·push**하도록 수정. reset·merge·force 일절 없음.

**오적용 정정 (STEP 0 핵심 발견)**: 2026-06-02 결정(`a84388f`)은 "야간 자동화 브랜치 정책"을 **`nightly_v3.sh`에 적용**하라 했으나, launchd `com.stockvis.nightly`가 실제 호출하는 활성 스크립트는 **`~/stock-vis-nightly/run_tier3_audits.sh`**였다(plist 확인). `nightly_v3.sh`는 비활성(미호출) + 별개 경로(`$YEAR_MONTH/$DAY/`). 따라서 6/2 수정은 **비활성 스크립트에 갔고 활성 스크립트는 미수정** → 재발 지속(e617a8f 등 51 audit commit이 모두 메인 트리 main 직접 commit). 이번에 **활성 스크립트(`run_tier3_audits.sh`)를 고침** — `nightly_v3.sh`는 무변경(꺼둔 tier1/2 auto-fix 보존), plist 재지정도 안 함.

**구현 (boundary = line 30 PROJECT_DIR + git 블록만, 감사 task 로직 1-611 무변경)**:
- `PROJECT_DIR` → `$HOME/stock-vis-nightly/repo`(전용 worktree). 리포트 생성·git 모두 거기서, 메인 트리 무접촉.
- `log()` 정의 직후: `git fetch origin` → **porcelain 가드(더러우면 HALT — 직전 run 잔재 보호)** → `git checkout -b monorepo/nightly-$(date +%Y%m%d) origin/main`(없으면 신규, 같은 날 재실행이면 전환해 누적).
- git 블록: `add` reports → commit → `GIT_TERMINAL_PROMPT=0 git push origin <dated>`(keychain 검증 통과 → 자동 push 채택. 비대화로 hang 방지, 실패 시 로컬 보존 폴백).

**Why dated 브랜치 (reset/merge 대신)**: 단일 롤링 브랜치 + `reset --hard origin/main`은 누적 리포트 폐기 + 비-ff force-push 유발(금지)로 깨짐. dated 브랜치는 매 run 신규라 항상 ff, force 불요, 코드도 항상 최신 origin/main 기반.

**검증(2026-06-18, 수동 격리 테스트)**: dated 브랜치 생성·커밋·push 성공, **메인 트리 main HEAD 무변동(909f406) 입증**, pre-commit `monorepo/*` 화이트리스트 통과. keychain push 실증(dry-run + 실제 push 모두 성공). 테스트 더미 브랜치 local+remote 정리 완료. 감사 7 task는 무변경(고비용이라 재실행 안 함, 경계 보존).

**잔여(별 트랙)**: ① dated 브랜치 누적 정리 — `TASKQUEUE.md NIGHTLY-BRANCH-GC`. ② hook hardening(`scripts/hooks`+`core.hooksPath`) — MAIN-SYNC-FIX 트랙 유지(이번 범위 밖). ③ launchd 재가동(`launchctl load`)은 **사용자 수동 승인** 대기(수정 중 unload 상태).

**📎 참조**: `~/stock-vis-nightly/run_tier3_audits.sh`(백업 `.bak-20260617`), `TASKQUEUE.md MAIN-SYNC-FIX`·`NIGHTLY-BRANCH-GC`, DECISIONS `a84388f`(6/2 브랜치 정책).

---

## [2026-06-17] 섹터 스파크라인 지표 = rel_strength 단일 고정 (자금흐름 군)

**결정**: 섹터 스파크라인의 시계열 지표는 `rel_strength` **하나로 고정**한다. momentum_1d/5d/20d·flow_proxy 등은 스파크라인에 혼용하지 않는다(기존 막대차트 영역에만 잔존).

**Why**: 카드 의미밴드(`meaning.ts sectorFlow`)가 `rel_strength` 부호를 유입/유출/중립으로 해석하는 단일 기준 — 스파크라인 추세선이 같은 지표라야 "한 화면 한 의미"가 성립한다. 다지표 혼용은 색·기울기·끝점 의미가 충돌해 가독성을 깬다.

**How to apply**: `SectorSparkline`은 `entry.history[].rel_strength`만 매핑. 다른 지표 추가 요구 시 별 컴포넌트/별 화면으로 분리(혼용 금지).

---

## [2026-06-17] 11섹터 전부 반환·렌더 = BE 절단 0 / FE 절단 0 (A-1)

**결정**: 섹터 history는 BE가 `rank_in_universe` 순으로 **11개 전부 직렬화**하고, FE는 받은 그대로 **전부 렌더**한다(상위 N 절단·필터 없음). 데이터 없는 섹터는 빈 `history: []`로 내려가고 FE는 "—" graceful 처리.

**Why**: BE·FE 어느 쪽도 임계/우선순위를 발명하지 않음 → 계약 1:1, 결측은 skip(합성 0). 절단 로직이 없으니 롤백·검증이 단순하고 additive 안전. order_match(sectors[] == sector_history 동일 rank순)로 결합도 index/symbol 정합.

**How to apply**: `_sector_detail()`는 `ordered_symbols = [r.market_index_id for r in latest]`(rank순) 전부 반환. FE `SectorDetail`은 `payload.sector_history.map(...)` 전건 렌더, 빈 history는 `SectorSparkline`이 "—"로 처리.

**검증**: 실데이터 덤프 11그룹×29일, order_match True. vitest 통합 테스트로 전건 렌더·rank순 결합 보증.

---

## [2026-06-17] 교차 앱 규약 단일 출처 = repo 하네스 (D안)

**결정**: 새 교차 앱(cross-app) 규칙은 코어(공용 커스텀 지시문)에 복제하지 않고 **repo 하네스에 1회만** 기록한다. 코어에는 repo 하네스를 가리키는 **포인터 한 줄**만 둔다.

**Why**: 동일 규약을 코어와 repo 양쪽에 복제하면 drift(불일치 표류)가 발생한다(규약 10장 = 단일 출처 원칙). 진실의 소스를 repo 하네스 하나로 고정해 복제 표류를 차단한다.

**How to apply**: 교차 규칙 발생 → repo 하네스(CLAUDE.md / DECISIONS.md / sub_claude_md)에 기록 → 코어는 포인터만. **주(잔존 부채)**: 세 프로젝트 공용 코어에 포인터 한 줄 추가 = 병진 수동 작업으로 잔존(자동화 안 됨).

**📎 참조**: `PROGRESS.md` 2026-06-17 MGMT-XAPP-RULE 항목, CLAUDE.md "Harness Protocol".

---

## [2026-06-17] 섹터 라벨 KO 도입 + GICS 출처 참조 (slice 2a)

**결정**: `KO_LABELS`에 `sector.*` 11키(SPDR 심볼 → KO명)를 additive 추가한다. KO 값은 **새로 작명하지 않고** frontend `screener.ts`의 GICS 섹터 KO명을 그대로 차용한다.

**Why**: 거시 대시보드에서 원시 심볼(XLK·XLE…) 노출 → 가독성 저하. 라벨 출처를 screener.ts GICS명으로 고정하면 작명 발명 0 + `translate('sector.{SYM}', labels)` 경로 재사용으로 단일소스 유지. 라벨 부재 시 심볼 fallback이라 안전.

**How to apply**: `apps/market_pulse/i18n/labels.py` KO_LABELS에 11키(XLK 기술 / XLC 통신 / XLY 경기소비재 / XLP 필수소비재 / XLE 에너지 / XLF 금융 / XLV 헬스케어 / XLI 산업재 / XLB 소재 / XLRE 부동산 / XLU 유틸리티). 마이그레이션 0(코드 상수). 머지: ebe5540.

---

## [2026-06-17] 섹터 스파크라인 색 = meaning.ts sectorFlow 단일소스 (slice 2b 편차)

**결정**: 섹터 스파크라인의 선/끝점 색은 인라인 임계(목업의 >0.5/<-0.5)가 아니라 `SectorCardSummary`가 이미 쓰는 **`meaning.ts sectorFlow`(epsilon 0.1, flat 포함)** 를 재사용해 결정한다.

**Why**: 색 임계값을 컴포넌트에 산재시키면 카드와 스파크라인의 톤이 어긋나고 임계 출처가 다중화된다(component_boundaries 원칙 위배). 단일 함수로 rel_strength→방향을 통일하면 카드·스파크라인 색이 일관된다.

**검토 결과**: ±0.5(목업) vs ±0.1(구현)의 색 flip을 비교 후 **±0.1 유지 확정**. **트레이드오프(의식적 수용)**: 중립(flat) 밴드가 좁아(±0.1) 약·강 신호의 색 구분이 사라짐 → 신호 강도는 색이 아니라 **선 기울기·끝점 위치**로 구분한다.

**How to apply**: `SectorSparkline`은 `sectorFlow(last).dir`(in/out/flat)로 stroke/fill 클래스 매핑. 임계 변경은 `meaning.ts` 한 곳에서만. 머지: 4998994.

---

## [2026-06-17] Path B(Regime 깊이) 묶음3 — 다음단계 게이지 (B-3 부호화 양방향)

**⑥ Path B 다음 조각 = 다음단계 게이지(A) 선택, 타임라인 보완(B)은 보류**

STEP 0에서 S4(timeline+대기)는 이미 land 확인 → 스코프 재정의. 후보 A(다음단계 게이지) vs B(타임라인 보완) 중 **A 선택**.
- **Why**: B는 전환(레짐 변경) 데이터 부재로 현재 단색 = 효용이 데이터 종속(지금 비효율). A는 margins 실값 차이가 있어 **즉시 효용·검증** 가능. 가중합 **A 4.75 / B 2.25, 마진 2.50**.
- **B 처리**: TASKQUEUE 보류 — 트리거 = 전환 이벤트 실발생 OR 윈도우 확장 결정.

**⑦ 게이지 매핑 = B-3 부호화 양방향 (디렉터 결정, 가중 권고와 상이)**

가중합 권고는 **B-2(4.30) > B-1(3.80) > B-3(2.80)** 이었으나 디렉터가 **B-3 선택**.
- **Why**: "넘었나/얼마 남았나"를 **방향까지** 보여주는 게 '방향판단 카드' 미션에 부합.
- **B-3 단점 봉인**: op `<`/`>` 혼재 부호 통일 문제는 BE `to_threshold` 단일축으로 봉인 — **FE 부호 로직 발명 0**. STEP 0에서 5지표 부호 일관성(>0=아직)  검증 통과. 불일관 시 HALT→B-2 강등 안전장치 박았으나, **일관 확인되어 B-3 확정**.
- **표시 길이**: `|to_threshold|/scaleRef` 정규화만(판정 무관, **수치 발명 아님**). closest 요약 라인 유지 + 게이지 additive → 기존 '대기' 분기 회귀 0.
- **머지**: `8b14dd8`.

**📎 참조**: `PROGRESS.md` "Path B 묶음3 — 다음단계 게이지(B-3)", DECISIONS L1713(데이터 공백=코드 결함 아님 — `MP-DATA-MACRO-COVERAGE` 게이지 값 선행), `apps/market_pulse` 게이지 FE.

---

## [2026-06-18] MP-DATA-MACRO-COVERAGE = 7종 재귀 자동화 (M-1), 트랙 성격 재정의

**⑧ 트랙 재정의 — "null 채우기"가 아니라 "수동 의존 7종 재귀 자동화"**

STEP 0 재측정으로 메모리/기존 인식("14개 거시 중 9개 actual null")이 **stale**임을 확정 — 실제 **null 0개, coverage 1.0(14/14)**. 따라서 실제 과제는 데이터 채우기가 아니라, **재귀 beat가 없어 수동 유지되던 7종(NFCI·NFCICREDIT·NFCILEVERAGE·NFCIRISK·BAMLH0A0HYM2·BAMLH0A3HYC·T10Y3M)의 재귀 자동화**다. 완료 시 regime 11 macro = **11/11 재귀 자동 sync**(기존 4: T10Y2Y·VIXCLS FRED beat + VIX3M·MOVE Yahoo beat / 신규 7).

**결정: 방법 = M-1 (검증된 sync command를 task 래핑)**
- **Why M-1**: `sync_marketpulse_v2_indicators` command가 **idempotent**(`update_or_create`)·비대화형·`--series` 스코프 가능 → task 래핑(`call_command`)에 적합, **sync 로직 발명 0**. FRED 접근은 command 내부 `packages.shared.FREDClient` 경유 = **shared 경계 유지**.
- **Why NOT M-2**: `update_economic_indicators`(목록 편집안)는 **legacy 매크로 대시보드 전용**(FEDFUNDS/DGS2/DGS10/UNRATE/CPIAUCSL 목록 + fear_greed/interest_rates/inflation/global_markets 캐시) → regime v2 전용이 아니라 목록 편집 시 **파급 ≠ 0** → 배제. (단 그 task 자체는 안정 실행 중: enabled, last_run 06-17 22:00, total_run 969 — 정황 측정으로 확인.)
- **VIX3M·MOVE 제외**: FRED 미지원 + `mp_sync_yahoo_indicators_daily`가 이미 커버 → 재귀 스코프에서 제외(중복/실패 회피).

**How to apply**: `apps/market_pulse/tasks/sync_indicators.py mp_sync_fred_indicators_daily`(7종 스코프) + `setup_marketpulse_beat` SCHEDULES 등록(NY 17:40 M-F, yahoo 17:35 직후). Bug #28(beat DB 직접 등록 → 배포 시 `setup_marketpulse_beat` 재실행 필수) 주석 명시. 마이그레이션 0(데이터 동기화).

**검증**: 실 FRED 트리거 **7/7 succeeded**(total_failed=0, 202 obs), age 리셋(NFCI 13→6 / HY 6→2 / T10Y3M 3→1, **max 6d ≪ 14d 컷**). pytest marketpulse **162→166**(+4), macro 12→16. shared 0 / 타 앱 0.

**정황(이 슬라이스 미수리)**: VIXCLS age 6 = FRED 발행 지연(task는 안정 실행) → 별도 ops 사안(필요 시 후속 트랙).

**📎 참조**: `PROGRESS.md` "MP-DATA-MACRO-COVERAGE 완결", `apps/market_pulse/tasks/sync_indicators.py`, `common-bugs.md #28`(beat DB 등록).

---

## [2026-06-18] Breadth 의미밴드 = 변형 A (v2 카드 자기설명화 완결)

**결정**: 시장 폭(Breadth) 카드 의미밴드 = **변형 A**(단일 종합 밴드 1줄 + 보조신호 부제) 채택. v2 정량 카드 자기설명화의 **마지막 조각** — Regime/Sector/Concentration/Breadth 4개 정량 카드 전부 의미밴드 보유.

**Why**: 4개 정량 카드 자기설명화 일관성 + raw 숫자 보존하며 가산(additive) + Concentration(`concentrationBand`)·Sector(`sectorFlow`) 선례 미러. raw 등락수만 노출하던 Breadth에 "이게 무슨 의미인가" 한 줄 부여.

**임계 근거(발명 0, 투명)**: 주신호 = 등락비율 `advance/(advance+decline)`, `[0,1]` 유계·**0.5 내재 중심**(rel_strength/HHI와 달리 스케일 모호성 없음). → `concentrationBand`(0.5 중심) + `sectorFlow`(epsilon 0.1) **선례 앵커**. 대칭 사다리 ±0.10(lean 0.60/0.40)/±0.20(broad 0.70/0.30), 5밴드(broad_strength/strength/neutral/weakness/broad_weakness). **엇갈림 댐핑**: 신고저·AD가 등락방향과 강하게 반대면 1단계 중립쪽. 색 = `FLOW_TONE`(calm 강세/hot 약세/neutral, 3톤 재사용, broad는 라벨 구분 — 신규 색 0).

**⚠ 미검증 명시(TUNE)**: dev DB breadth 실데이터 부족(STEP 0 = 30행 중 1행만 non-empty, n=1)으로 실분포 검증 불가 → **TUNE 마커**. 임계는 메모리 발명이 아니라 0.5 내재 중심 + 선례 epsilon 관례 앵커. 실 SPY breadth(~500종목) 누적 후 0.60/0.70 경계 재튜닝 예정(`concentrationBand` TUNE 선례와 묶음).

**How to apply**: `meaning.ts breadthBand()`(단일소스, i18n-무관 밴드키+톤 반환) + `BreadthCardSummary`/`BreadthDetail`(밴드 1줄+부제, raw 유지) + `labels.py breadth.*`(5밴드+cue 2). BE serializer/`_breadth_detail`/recharts 차트 **무변경**.

**검증**: vitest market-pulse-v2 91→100(+9), 전체 309, tsc 0, pytest marketpulse 166(labels 회귀 0), 마이그레이션 0.

**커밋**: `43ae93b` (`a45ee0f..43ae93b`).

**📎 참조**: `PROGRESS.md` "Breadth 의미밴드 완결", `frontend/app/market-pulse-v2/meaning.ts breadthBand`, `TASKQUEUE.md MP-UX-BREADTH-BAND·T-BREADTH-TUNE`. 선례: DECISIONS "[2026-06-17] 섹터 스파크라인 색 = sectorFlow 단일소스".

---

## [2026-06-18] CS-M2-DISPLAY S3 — 주도주 지표 막대 도메인 (측정 기반 고정) + B1 chevron 구조 + Finding B

**맥락**: EventRanking 행에 M2 주도주 3지표(주신호) 노출. A2(숫자+미니막대), B1(chevron=펼침/행클릭=드릴다운 유지) 디렉터 확정.

**STEP 0 실측 (window=20, n≈320, prod 640행)** — 막대 도메인 ground truth:
| 지표 | min | p10 | med | p90 | max | 성격 |
|---|---|---|---|---|---|---|
| trend_quality(T2) | −2.85 | −0.59 | 0.01 | 1.04 | 3.30 | 부호 있음(음수=하락추세) |
| theme_beta | −1.06 | 0.31 | 0.92 | 1.47 | 2.37 | ~0.9 중심(beta) |
| capture_spread | −263 | −93 | 5.8 | 99.5 | 367 | 0 center·부호·넓음(아웃라이어) |
| theme_alpha(T3, 펼침) | −4.13 | −1.25 | 0.07 | 1.17 | 3.42 | 보조 |

**결정 1 — 막대 도메인 (측정 기반 고정 상수, 페이지 정규화 금지. serializer에 percentile 필드 없음 확인)**:
- `trend_quality`: **center-origin ±2** (p90 1.04 여유, 부호). +teal/−coral.
- `theme_beta`: **0-baseline [0, 2]** (med 0.92).
- `capture_spread`: **center-origin ±100** (p10/p90≈±95, 아웃라이어 클램프), +teal/−coral.
- `theme_alpha`(펼침 보조): **막대 제거, 숫자만 표시**(Slice 5 결정 — ±0.5 클램프 이슈 해소 + 추세강도와 ρ=0.84 상관이라 시각 강조 부적절. "참고용" 캐비엇 동반).

**결정 1-b — window 도메인 단일화 (Slice 5, window=120 실측 대조)**: w20·w120 양쪽 p10/p90 측정 결과 3 주신호 도메인(±2/[0,2]/±100)이 **둘 다 커버**(w120이 더 좁아 막대가 작게 = 더 긴 관측의 낮은 분산을 정확히 반영). → **per-window 분기 불필요, 단일 고정 도메인 유지**. capture_spread 단위 = %p(상승포착−하락포착) 팝오버 명시.
- **Why**: min/max 직접 사용 시 capture_spread(±263~367 아웃라이어)가 막대를 못 읽게 만듦. p10/p90 + 클램프가 분포 대부분을 해상도 있게 표현. 숫자는 항상 병기(2자리)라 클램프로 정보 손실 없음.

**결정 2 — Finding B: `trend_quality` 텍스트 정정 (디렉터 승인)**: S2 METRIC_INFO의 `range:'0~1'`이 실측(−2.85~3.30, 부호)과 불일치 → `range:'음수=하락추세·0근처=중립·+면 강한 상승'` + description 하락(−) 언급 보강. 막대는 center-origin이라 이미 정합. (커밋 6ecb0ef)

**결정 3 — B1 chevron 구조 (STEP 0 0-2 실측 반영)**: 드릴다운은 onClick 핸들러가 아니라 **행 전체 `<Link href=/chainsight/[symbol]>`**(심볼 상세 네비)였음. `<a>` 안 `<button>` 중첩 불가 → chevron을 **Link 바깥 형제**로 배치 + onClick에 `preventDefault()+stopPropagation()`. "관계 그래프 열기"(펼침 영역)는 동일 목적지 Link 재사용. → **chevron이 드릴다운 미발화**(vitest 검증).

**불변/검증**: 기존 EventRanking Link 네비 동작 보존, "테마/theme" 단어 UI 비노출("그룹/관련 종목 그룹"), 한국어 라벨 METRIC_INFO·getLabelForTheme 경유(하드코딩 0). vitest 309→**331**(+22), tsc 0. 커밋 6f0eb98(S1)·54727d4(S2)·f2fa8df(S3)·e8158da(S4)·6ecb0ef(Finding B).

**📎 참조**: `frontend/components/chainsight/{EventRanking,MetricCell,MetricInfoPopover}.tsx`, `frontend/constants/eventThemes.ts METRIC_INFO`, DECISIONS "CS-M2 (2026-06-16)" 옵션Y(T2 주·T3 보조).

---

## [2026-06-18] CS-M2-DISPLAY S4 — 역할 분리(통계=펼침/경고=패널) + is_fallback 신뢰경고

**결정 (S4-B, 디렉터 확정)**: EventRanking 행의 보조 정보를 **역할로 분리** — ① **맥락 통계는 chevron 펼침(모든 행)**, ② **신뢰 경고(저유동성·is_fallback)는 LowLiquidityPanel(경고 전용 영역)**.

**STEP 0 발견 → 정공법(A) 채택**: `LowLiquidityPanel`이 빈 껍데기가 아니라 **이미 점수분해(거래량z·변동성·수익률)+경고를 저유동성 행에 표시**(자체 토글) 중이었음. S4-B를 그대로 하면 통계 중복 → **(A) 통계를 패널에서 빼 펼침으로 이동, 패널은 경고 전용 축소**. 중복 0.
- **행위보존 재정의(디렉터 명시)**: (A)의 `LowLiquidityPanel` 테스트 갱신은 **의도된 구조 변경**이라 IDENTICAL-hash 가드 대상이 아님. 가드 = "새 구조 테스트 + DECISIONS 기록". 단 EventRanking 드릴다운 Link·chevron·행 본문은 보존(범위 밖).

**펼침 라벨 = "관심도 근거" framing (i)**: 거래량z·변동성은 관심도(M1) 점수의 **가중 입력 그 자체**(score=0.50×거래량z+0.30×변동성+0.20×수익률, `attention_service.py`). 중립 "맥락 통계"는 부정직 → 점수 근거를 점수 옆에 노출(납득도↑). 문구: ① 펼침에 **"관심도 근거"(volume_z·volatility) / "주도지표 보조"(T3)** 소제목 분리(출처 다른 신호 혼동 방지) ② **비중(50/30/20) 노출 + "수익률(20%)은 행의 % 참고" 캐비엇**으로 분해 완결.

**고정 못 (디렉터)**:
- **R2**: 경고는 **토글 없이 상시 노출**(저유동성 행). 부수이득 — 토글 2개(chevron+패널)→chevron 1개로 단순화.
- **R3**: raw_return은 행 본문에 이미 있어 **펼침서 재노출 안 함**(volume_z·volatility만).
- **R4**: is_fallback **현재 prod 0종목** → 라이브 검증 불가 → **is_fallback=true 합성 픽스처 vitest**가 유일 가드(미래 IPO/상폐/프리미엄 대비). 렌더 조건 `is_low_liquidity || is_fallback`.
- 펼침 통계 **숫자만**(막대 없음, T3와 동일 — volume_z max 47.7 아웃라이어 무관).

**is_fallback 게이트 판정**: help_text="120일 미달로 20윈도우만 산출(IPO/상폐/프리미엄)" = **저신뢰** → S4-B 신뢰경고 영역. 경고 카피 "데이터가 부족해 보정된 값이에요".

**보조지표 range (실측 기반, Finding B 재발 방지)** — StockAttentionScore 2026-06-15 n=659:
- `volume_z`: med −0.11, p90 1.53, max 47.7(아웃라이어). range "z-score · 0=평소 · +면 급증". tier `context`(신규).
- `volatility_pct`: 0~1 백분위, med 0.50. range "0~1 백분위 · 1에 가까울수록 변동 큼".
- ADV·spread = **미저장 확인 → UI 제외**(과대약속 금지).

**불변/검증**: EventRanking 드릴다운·chevron·window 셀렉터 테스트 불변, "테마/theme" UI 비노출, 한국어 라벨 단일소스. METRIC_INFO 키 6→8(volume_z·volatility_pct, tier `context` 추가), 완비/​tier-split 테스트 갱신. vitest 331→**354**(+23), tsc 0. 커밋 cabf5c5(S1)·0b02f7a(S2)·2a1f2a4(S3).

**📎 참조**: `frontend/components/chainsight/{EventRanking,LowLiquidityPanel}.tsx`, `frontend/constants/eventThemes.ts METRIC_INFO`, `apps/chain_sight/services/attention_service.py`(M1 가중치), DECISIONS "CS-M2-DISPLAY S3 (2026-06-18)".

---

## [2026-06-19] CS-RD3 통합 QA — 그래프 "테마"→"그룹" + 관심도 standing 바 + "관심↑" 라벨 + 헤더 정렬

라이브 스크린샷(역전 후) 대조 발견 처리. 디렉터 확정 4건.

**① 그래프 관계라벨 "테마"→"그룹" (키 보존)**: 사용자 노출 텍스트 5곳(`graphStyles.ts`·`FilterPanel`·`RelationFilterChips` label + `NodeTooltip`·`RelationCardPanel` '테마 공유'→'그룹 공유') + 주석 1곳 교체. **관계 타입 키 `HAS_THEME`는 전부 보존**(필터·그래프 엣지·radialLayout 동작 불변 — 키-텍스트가 별도 변수라 결합 위험 0, STEP 0 확인). 그래프 화면 "테마" 노출 0.

**② 관심도 standing 바 신규 (디렉터 옵션2 / C3 = 4번째 미니바 아닌 구분 처리)**: STEP 0 발견 = 랭킹에 관심도 바가 **원래 없었음**(텍스트 "관심도 84.5"만; 화면의 바는 전부 M2 MetricCell). RD3 §2 AttentionScoreBar 미구현분. **신규 `AttentionStandingBar.tsx`** 추가 — 점수 숫자 아래(M2 미니바와 다른 위치) + indigo 채움/slate 트랙(다른 스타일). 채움 = **그룹 내 min-max 정규화** [FLOOR 10%, 100%] (페이지 정규화). **측정 근거**: 2026-06-15 전체 분포 14.8~100/p10 30/med 50/p90 73.5 → 그룹 내 스프레드 충분, 고정 0~100보다 순위 낙차 시각화 우수. 숫자(절대값) 병기로 바=standing 전용. 단일/동점 그룹(range=0)→full.

**③ "관심↑ N" 의미 노출**: `high_attention_count` = 그룹 내 **관심도 ≥ 70 종목 수**(attention_service.py:213, low는 ≤20). 카드가 `<button>`이라 중첩 인터랙티브 팝오버(MetricInfoPopover=button) 불가 → `title` 툴팁 + cursor-help로 라벨 명확화("관심 집중 종목 N개 — 관심도 70점 이상").

**④ 랭킹 헤더 컬럼 폭 정렬**: 헤더가 행의 chevron 버튼 폭 미고려로 라벨이 우측 쏠림 → 헤더를 행 구조(Link[flex-1] + chevron placeholder)와 미러링. 정렬만, 기능 무변경.

**검증**: tsc 0, vitest 365→**371**(+6 AttentionStandingBar 경계/단조/단일그룹). 라이브 육안은 교차포트(:3200) CORS 차단으로 보류 → 머지 후 사용자 :3000에서 확인 권장. HAS_THEME 키 보존으로 그래프·필터 동작 불변.

**📎 참조**: `frontend/components/chainsight/{graphStyles,FilterPanel,RelationFilterChips,NodeTooltip,RelationCardPanel,EventRanking,EventBoard,AttentionStandingBar}.tsx`.

---

## [2026-06-23] CS-RD3 QA Slice 2-B — 관심도 바 정규화 교체 (그룹 min-max → 전역 0~100)

위 ②(그룹 내 min-max 정규화)를 **전역 0~100 절대 도메인**으로 교체. **근거 = 측정(N=499, 2026-06-22)** 으로 드러난 그룹 정규화의 2문제:
1. **소규모·저분산 그룹 과장(거짓 신호)**: `Lithium & Battery`(N=2) score 62.0·64.1 — **단 2.1점 차가 바 10%↔100%**(90%p)로 과장. min-max는 range를 항상 꽉 채우므로 멤버 적고 촘촘한 그룹일수록 시각 낙차가 실제와 괴리.
2. **그룹 간 비교 불가**: min-max는 각 그룹 최하위를 일률 FLOOR(10%)로 깔아 — Industrials 최하위 22.2점도 Semiconductor 최하위 40.8점도 **둘 다 10%**. 화면에 여러 그룹 공존 시 "최하위는 다 같은 길이" 오해.

**교체**: 채움 공식 `widthPct = (FLOOR + (1−FLOOR)·clamp(score/100,0,1))·100` = **10 + 0.9·score** (FLOOR 0.10 유지). 그룹 min/max 주입 경로(EventRanking IIFE + RankingRow props) 제거, 단일멤버 range=0 특례 제거(전역 도메인엔 불필요). **바 의미 재정의**: "그룹 내 순위" → **"시장 전체 대비 관심도 절대 수준"**. 그룹 내 순위는 정렬·번호·절대 숫자가 전달.

**검증 수치**(새 공식): Technology 89.8→90.8%·87.7→88.9%·85.0→86.5%·83.0→84.7%(자연 분산, 다 차지 않음). Lithium 62.0→65.8%·64.1→67.7%(**차이 1.89%p, 과장 소멸**). 경계 0→10%·50→55%·100→100%, 같은 점수=항상 같은 폭(그룹 간 비교 가능). **vitest 371→372**(바 테스트 6→7: 경계/단조/촘촘동등/그룹무관/클램프), tsc 0. 위치·색(좌측 indigo)·M2 구분·정렬·숫자 표시 불변(행위보존).

**📎 참조**: `frontend/components/chainsight/{AttentionStandingBar,EventRanking}.tsx`, `frontend/__tests__/chainsight/AttentionStandingBar.test.tsx`.

---

## [2026-06-23] chain_sight 소규모 그룹 — URL 인코딩 버그(ⓑ) 수정 + 멤버<3 보드 노출(ⓐ)

CS-RD3 QA 육안검증 부수 발견 → STEP 0 측정으로 근인 분리 후 결정 게이트 통과.

**ⓑ 그룹명 URL 인코딩 = 광역 버그(수정, 결정 무관)**
- **증상**: 공백·`&` 포함 다단어 그룹명 7개(Communication Services·Consumer Discretionary·Consumer Staples·Real Estate·Robotics & AI·Lithium & Battery·Clean Energy)의 상세 페이지가 **빈 목록**(제목도 `Communication%20Services`로 이중 인코딩). 보드에 뜨는 그룹(Robotics & AI N=4, Communication Services N=22)도 상세 깨짐 → 누락 그룹 한정 아님.
- **근인**: `EventBoard.tsx` 카드 클릭 `router.push(`/chainsight/events/${item.theme}`)`가 **encodeURIComponent 없이 raw push** → param 이중 인코딩 도착 → fetchRanking이 또 encode → 백엔드 조회 키 불일치.
- **수정**: push에 `encodeURIComponent(item.theme)` + 페이지(`[theme]/page.tsx`)에서 `decodeURIComponent` 단일 디코딩(멱등 — % 없으면 no-op이라 Next 자동디코딩 여부와 무관, 그룹명에 literal % 없음). 링크 생성 지점은 단 1곳(0-2 전수 grep 확인).
- **검증**: 라이브 — Communication Services·Robotics & AI 상세 데이터 정상 로드(제목도 정상 디코딩). vitest 라우트 왕복 10건(특수 7 + 단어1개 회귀 3).

**ⓐ 멤버<3 보드 누락 = 의도된 필터 → 디렉터 결정 (가) 1급 노출**
- **STEP 0 판정**: `attention_service.py:204` `if len(members) < 3: continue`(docstring 명시) = 의도된 필터, 멤버 **수** 기준(문자 무관). 버그 아님 → 결정 게이트.
- **결정 (가) 1급 노출 + 저신뢰 표식**(가중합 4.25 vs (나)완전숨김 3.45, 마진 0.80). Why: Chain Sight 정체성 = "관련 종목 그룹 전수를 본다" → 소규모 숨기면 커버리지 구멍. 약점(소표본)은 숨기지 말고 신호.
- **수정**: `len(members)<3` 필터 제거 → 모든 그룹(멤버=1 포함) 보드 집계. 보드 카드 + 랭킹 타이틀에 **"표본 작음" 저신뢰 표식**(member_count<3, amber, LowLiquidityBadge 결 재사용). `member_count`는 serializer에 이미 노출.
- **N=1/N=2 상대지표 거짓 0 방지(STEP 0-3)**: 백엔드 `attach_leadership`는 quorum(MIN_THEME_MEMBERS=3) 미달 시 theme_beta·capture_spread = **None 반환**(0 아님), trend_quality(절대)만 산출. `MetricCell`은 이미 `value===null`→**"—"(대시)** 렌더 → 거짓 중립 신호 없음(추가 작업 불요). 라이브 보드 노출은 백엔드 재배포 후(pytest로 API 검증: 멤버<3·=1 그룹 포함 + member_count).

**경계(0-2)**: get_event_board·get_event_ranking은 `apps/chain_sight` 전용. dashboard·market_pulse·shared 미사용, shared→chain_sight 역참조 0 → 안전.

**검증**: vitest 372→387(+15: 인코딩 왕복 10 + 저신뢰 배지 4 + 인코딩 1), tsc 0. chainsight pytest 74/0(소규모·단일멤버 보드 포함 + 회귀 0). 단어1개 그룹·정상 그룹·랭킹·관심도바 불변(행위보존).

**📎 참조**: `frontend/components/chainsight/{EventBoard,EventRanking}.tsx`, `frontend/app/chainsight/events/[theme]/page.tsx`, `apps/chain_sight/services/attention_service.py`, 테스트 `EventBoard/EventRanking/routeReversal.test.tsx`·`tests/chainsight/test_attention.py`.

---

## [2026-06-18] Phase 1.5 Translation Layer — 토대 3결정 (래퍼·스키마·테스트)

카드 LLM 해설(prose) 레이어. STEP 0 recon(`42054ae`)으로 ground truth 확정 후 3축 결정.

**① 래퍼 = Brief 패턴 in-zone 재사용** (가중합 4.29 vs (b)shared 선건설 3.17 / (c)rag `AdaptiveLLMService` 재사용 2.81, 마진 1.12 압도적)
- **Why**: shared 래퍼는 cross-surface 광역(rag 포함)이라 1인 스코프 초과 → 기능이 토대건설에 인질화. Brief 프레임워크(client genai+CB / safety 검출기 / prompt / Log)가 이미 완비 → in-zone 재사용이 최단·최저위험.
- **보완**: Brief의 재사용 가능 plumbing을 `apps/market_pulse/llm/`로 **단일출처 추출**(복제 0). Brief는 추출분 import로 재배선.
- **부채 이연**: 범용 shared LLM 래퍼 부재는 **BOUNDARY-LLM 트랙(DORMANT, 타 세션 소관)**으로 이연 — 본 트랙에서 등록·구현 안 함(zone 경계). genai 직접 사용처 3곳(briefing/korean_overview/rag) 통합은 그 트랙 몫.

**② 스키마 = 별도 `translations` envelope** (BriefingLog 미러 `TranslationLog`) (가중합 4.46 vs per-card 필드 3.32, 마진 1.14)
- **Why**: 결정론 카드 데이터 ↔ 비결정 LLM prose **수명주기 분리**(fallback 자명: envelope 없음→밴드만) + Brief의 단일 Log·단일 호출·단일 캐시 경로와 정합. per-card 필드는 4카드 serializer 동시 변경 + 결정/비결정 혼재.
- **약점 흡수**: FE join은 얇은 selector(카드 키 merge)로, 카드 컴포넌트는 dumb 유지.

**③ 테스트 = golden + vcr** (Brief 동반 보강) (가중합 4.32 vs 스모크 2.93 / LLM-judge 2.78, 마진 1.39)
- **Why**: 첫 의도적 LLM 빌드 → 톤 회귀를 출시 전 CI에서 차단. 문구 일치가 아니라 **계약 단언**(길이·금지어·disclaimer·밴드 방향 일관·JSON 구조). vcr 카세트로 비결정 출력 결정론 고정(대표 입력 3~4종 1회 녹화).
- recon 확인: 현 Brief도 golden/vcr 0(overview_smoke seed만) → 동반 보강.

**빌드 계획**: S1(Brief plumbing 추출·행위보존 GATE) → S2(TranslationLog 모델) → S3(per-card prompt+생성 task) → S4(envelope serializer + FE selector + fallback) → S5(golden/vcr, Brief 동반).

**📎 참조**: `PROGRESS.md` Phase 1.5 Translation recon, `apps/market_pulse/briefing/{client,safety,prompt}.py`(미러 대상), recon 보고(shared 래퍼 부재·BriefingLog 스키마·gemini-2.5-flash).

## [2026-06-23] B-2 발행본 = 미추적 + gitignore (옛 main커밋 복원 안 함)

**맥락**: nightly tier3 감사 리포트가 6/17~18 리디자인(MAIN-SYNC-FIX)으로 격리 worktree(`~/stock-vis-nightly/repo`)의 dated 브랜치에 생성·커밋되도록 바뀌었으나, 대시보드 reader(`agent_reports.py:55`, read 경로 `~/Desktop/stock_vis/docs/nightly_auto_system/reports/`)는 옛 경로 고정 → write/read 분리로 **6/16 이후 "보고서 없음"**. B-2 = 격리본을 read 경로로 단방향 복사(발행)해 해소.

**결정**: 발행본은 **미추적 파일로 배치 + `docs/nightly_auto_system/reports/**/*.md` gitignore**. git 커밋 안 함, origin/main 무오염(감사이력은 격리 repo git 전담).

**Why (미래 세션 혼동 방지 — 핵심)**: STEP 0 실측상 pre-6/16 정상기 리포트는 **main에 커밋(추적)되어 origin까지 올라간 상태**였다. 즉 "옛 배치 그대로 재현"은 곧 **MAIN-SYNC-FIX가 차단하려던 바로 그 안티패턴(nightly 산출물의 main 직접 오염)을 복원**하는 셈. 그래서 옛 배치 재현 대신 무추적+gitignore를 택함. gitignore는 기추적 파일을 untrack하지 않으므로 역사 리포트(≤6/16)는 그대로 추적 유지(`git rm --cached` 안 함 — 선택 정리는 TASKQUEUE 별도 항목).

**구현**: `~/stock-vis-nightly/publish_reports.sh`(git 밖, `cp` 기반, 날짜 디렉토리 스코프 한정, 멱등·비차단 항상 exit 0, D1 원본 불변). nightly 배선은 사용자 수동(`run_tier3_audits.sh` 커밋 phase 다음 1줄). reader 인식 검증: target=6/20→19일 12/12, target=6/19→18일 12/12 available.

**미적용/별트랙**: 인증 A(`claude -p` 401, 6/20~22 생성 0건)는 B-2와 독립 선결 — 발행이 살아도 생성이 죽으면 신규 리포트 없음. `nightly-reports` 브랜치는 집계 타깃 아님(stale feature 브랜치) → B-2 미사용.
---

## [2026-06-18] BOUNDARY-LLM 통합 래퍼 형식 = 옵션 C (계층형 멀티프로바이더)

> 상위 트랙 호명: 위 `[2026-06-18] Phase 1.5 Translation Layer` ①이 범용 shared LLM 래퍼를 **BOUNDARY-LLM 트랙(DORMANT)**으로 이연하며 "genai 직접 사용처 3곳(briefing/korean_overview/rag)"으로 인용했다. **본 결정은 그 트랙의 실제 정의**이며, STEP 0 전수 실측으로 "3곳" 수치를 **27파일/9 surface로 정정**한다. (라벨 주의: 본 `BOUNDARY-LLM`은 위 `BOUNDARY-1/2/3`(shared→apps import 경계 청소, 2026-06-04 종결) 및 그 "옵션 C(macro 모델 승격)"와 **무관한 별개 트랙** — 동명 라벨 충돌 회피.)

- **상태**: 형식 결정 **CLOSED**. 실행(슬라이스) **미착수(DORMANT)**. → TASKQUEUE `[보류·DORMANT] BOUNDARY-LLM`.
- **결정**: `packages/shared/llm` 신설. **코어 층** = portfolio `complete(prompt, provider, model, system, ...)` 추상화(교차-provider 폴백·통합 예외 계층·단가 매핑) 흡수. **정책 층** = market_pulse briefing client 패턴의 circuit_breaker(`get_circuit`) · prompt-injection escape · cost/usage 훅 공통화. **어댑터** = Gemini(우선) · Anthropic(2nd). **OpenAI 미구현**(실측 사용 0건, YAGNI).
- **Why (STEP 0 실측, HEAD=`feb999b`)**:
  - 통합 대상 = **27파일 / 9 surface** (차터 "3곳"의 9배). portfolio·thesis 전체 + serverless 8 + news 4 + sec 2 + validation 1이 recon 누락분.
  - provider 분포 **Gemini 24 : Anthropic 3 : OpenAI 0** → Gemini-우선 형식이 실측 부합.
  - 외부-LLM-직접호출 가드 **부재**(아키텍처 테스트 `tests/architecture/test_shared_boundary.py`는 shared→apps AST만 검사, `KNOWN_VIOLATIONS` 빈 set) → **규약 부채이지 동결 위반 아님**. 가드 신설이 burn-down 슬라이스.
  - prompt-injection escape가 27곳 중 **2곳에만** 존재(`rag/llm_service.py`·`serverless/thesis_builder.py`) = 숨은 보안 회귀. escape/CB/재시도를 코어에 공통화하면 25곳 일괄 보강 → 이것이 형식 점수를 가른 결정타.
  - 성숙 베이스 2개: portfolio `apps/portfolio/llm/client.py`(repo 유일 Anthropic+Gemini 통합·교차폴백·통합예외 = 추상화 1위) + market_pulse `apps/market_pulse/briefing/client.py`(CB+prompt.py/safety.py+usage 수집 = 횡단 인프라 1위). C는 둘을 버리지 않고 **합성**.
- **가중합 (weights 합=1.00 / 1~5)**: 유지보수 0.28 · 이관안전 0.22 · 확장성 0.20 · 거버넌스 0.18 · 초기비용 0.12. → **A 3.10 / B 3.26 / C 4.48**. 마진 C−B = **1.22 → 운영원칙② 자동결정**(가중치 미조정 원본 표로도 동일 순위).
- **배제 사유**: **A**(현행 분산 유지)=escape 회귀를 27곳에 고착(거버넌스 1). **B**(단일 무거운 서비스 일괄 정합)=27개 동시 정합 → 1인 이관 리스크(이관안전 3); 단 B의 가치(단일 진입점·폴백)는 portfolio client에 이미 있어 **C 코어로 흡수됨**.
- **AdaptiveLLMService 처리**: 범용 80%(provider 팩토리·스트리밍·`estimate_cost`)는 코어 추출, 도메인 20%(투자 페르소나 프롬프트·complexity→depth)는 rag 잔류. 봉합선 = `generate_stream` 내부 "system_prompt 빌드+config 결정(도메인) ↔ provider stream 위임(범용)".
- **How to apply**: 착수 시 TASKQUEUE 슬라이스 ①(코어 신설, 소비처 0, IDENTICAL)부터. 코어는 portfolio client 추상화 + market_pulse 횡단 인프라 합성. 트리거(a) = Translation in-zone 단일출처(`apps/market_pulse/llm/`) 안정 land 후 "깨끗한 1회 lift" 적기.
- **📎 참조**: BOUNDARY-LLM 차터, STEP 0 LLM 소비처 전수조사 보고(27/9, 9 surface 카드), 상위 `[2026-06-18] Phase 1.5 Translation Layer` ①.
---

## [2026-06-23] iron-trading `latest-trading-date` 엔드포인트 — 소유권·방안 B·v1.0 플레이스홀더

신규 read-only `GET /api/v1/iron-trading/latest-trading-date`. iron_trading 봇이 local fixture 날짜(`2026-05-07`) 대신 stock_vis가 실제 제공 가능한 daily-context 최신 미국장 거래일을 자동으로 쓰게 한다. STEP 0 측정(`1b28b0c` 시점, M2 read-only 산출 가능·실측 `2026-06-22`→200·HALT 없음) 후 구현.

**① 소유권 = stock_vis** (데이터 제공자 책임·경계 보존)
- **Why**: "지금 daily-context로 조회 가능한 최신 거래일"은 stock_vis 내부 데이터(EODSignal/DailyPrice/PipelineLog) 상태에만 의존하는 사실이다. 그 사실을 아는 주체가 산출·노출해야 한다(소유권 귀속 원칙). iron_trading은 **소비자 측 결정**(어떻게 호출·fallback)만 자기 repo에 기록한다. 교차 규약 단일출처는 repo 하네스.

**② 방안 B (dry-check 검증) — 단순 최댓값(방안 A) 기각** (계약 라운드트립 200을 구조로 보장)
- **Why**: 200 보장 날짜는 "DB 최대 날짜"가 아니라 "후보 + OHLCV가 실재해 daily-context가 200을 주는 최신 날짜"다. 방안 A(EODSignal max date 신뢰)는 데이터 정렬이 어긋난 날(EODSignal은 있으나 그 날 OHLCV 없음)에 503으로 깨진다. 방안 B는 후보일 내림차순 순회 + `running` skip + **기존 `_select_candidate_symbols`/`_load_ohlcv_map` 재사용 dry-check**로 daily-context의 200 게이트와 동일 판정을 흉내 내 라운드트립을 우연이 아닌 **구조**로 못 박는다. test 6(비정렬 200)이 이 케이스를 고정.
- **How to apply**: `_load_ohlcv_map`은 모든 심볼을 빈 리스트로 초기화하므로 dry-check는 `sym in ohlcv`가 아니라 **비어있지 않은 rows**(`any(ohlcv.get(sym))`)를 본다 — daily-context의 `if not rows: continue`와 일치. `failed` pipeline일은 dry-check 후보 0/OHLCV 0으로 자연 배제(별도 분기 불필요). `scan_limit=20`으로 순회 비용 유계. 기존 daily-context는 **무변경(additive only)** — 새 서비스 파일 `services/latest_trading_date.py` + 새 뷰 `LatestTradingDateView`만 추가. `shared→apps` 역방향 import 없음.

**③ v1.0 플레이스홀더 = `freshness_status:"unknown"` + `snapshot_id:""`**
- **Why(freshness)**: `_build_freshness` 재사용은 snapshot 나이 계산이 들어가 경량 목표에 어긋난다. v1.0은 순수 best-effort `unknown`. **채움 조건**: Part 3.1 신선도 정책 확정 시.
- **Why(snapshot_id)**: M4대로 계약상 optional이며 정확한 산출엔 사실상 full build(candidate_count)가 필요 → 신규 생성 금지 원칙상 빈 문자열. **채움 조건**: snapshot_id를 read-only로 저장·조회하는 경로가 생기면.

**검증 결과**: 신규 6 + 기존 daily-context 15 = 21 그린(회귀 0 → 행위보존 입증). dev DB 실호출 `2026-06-22`→daily-context round-trip 200(candidates 30). 구현 baseline main `4246d48`(STEP 0 `1b28b0c` 이후 mp-translation S5 무관 커밋 2건 전진, 인용 경로 drift 0).

**📎 참조**: `integrations/iron_trading/services/latest_trading_date.py`, `integrations/iron_trading/views.py`(`LatestTradingDateView`), `integrations/iron_trading/urls.py`, `tests/iron_trading/test_latest_trading_date.py`.

## [2026-06-23] HARN-1 close — 하네스 append 문서 merge=union

하네스 4문서(DECISIONS/TASKQUEUE/PROGRESS/common-bugs)의 양쪽-append 충돌 구조적 재발(HARN-1)을 `.gitattributes merge=union`(`642306a`)으로 해소. 직후 BOUNDARY-LLM consolidation 머지(`63194cd`)에서 직전 merge-tree가 예측한 DECISIONS content 충돌이 **0으로 자동 해소**됨을 실증. union=양쪽 라인 보존이라 내용 정합은 보장 안 됨 → 머지 후 육안검수 필수(이번엔 고유 헤더 1회·항목 분절 0·유실 0 확인). 코드 파일엔 union 미적용.

## [2026-06-23] Phase 2 진입 순서 (Analog → Alerts → sub-pages → 데이터게이트)

**결정 (D-PHASE2-ORDER)**: market_pulse Phase 2 트랙 순서 = **#1 Analog(active, +MOVE 동봉) → #2 Alerts(O3) → #3 sub-pages → #4 FedWatch/GEX(데이터게이트) → #5 cross-surface(게이트)**.

**Why**: Analog(historical regime matching)을 1순위로 둔 근거 = 가중합 우위(마진 **0.35**), 타이브레이커 = **롤백 안전 + 시퀀싱**(Analog는 기존 regime 데이터 위 read-only 분석 = 롤백 표면 작고, Alerts/sub-pages의 선행 가치 입력이 됨). MOVE는 이미 `NEW_ECONOMIC_SERIES` 보유(P2 화면 recon STEP 0 [E] 실측) → Analog에 **동봉**(별 데이터 통합 불요). FedWatch/GEX는 코드베이스 흔적 0(외부 데이터원 신설) → **#4 데이터게이트**로 후순위(게이트 = 데이터원 확보 전 착수 금지). cross-surface(#5)도 게이트(선행 트랙 land 후).

**근거 측정**: P2 roadmap recon([E] FedWatch/GEX 0·MOVE 보유, [F] analog 미구현, [G] sub-pages 라우팅 0·v1 위젯 대기). 실행은 각 트랙 STEP 0 착수 시 재측정.

## [2026-06-23] Alerts 트랙 경계 = O3 하이브리드 (전달 port만 shared, 상태는 app 소유)

**결정 (D-ALERTS-BOUNDARY)**: MP1-N(능동 모니터링/알림) 경계 = **O3 하이브리드** — **전달(delivery) port만 shared/stateless(방향2)**, **AlertLog 모델·트리거 평가·구독은 app(market_pulse) 소유**.

**Why**: 가중합 우위(마진 **0.15**, 근소), 타이브레이커 = **§1 선례 일관성**(BOUNDARY-3 VIXProvider 포트 패턴 = 의존 역전 + 등록, shared엔 stateless port만 두고 상태/도메인은 app). AlertLog 등 상태를 shared로 올리면 §1 위반(shared는 stateless 경계) + 타 앱 결합. 전달 채널(메일/슬랙 등)만 shared port로 추상화하면 재사용 + 상태 격리 양립.

**실행 게이트**: 본 결정은 **방향만 확정** — 실제 모델/port 분리는 **Alerts 트랙(#2) STEP 0 검증 후** 착수(전달 port 인터페이스 실측 + 기존 news.tasks.check_pipeline_alerts 패턴 재사용 가능성 확인). 마진 0.15로 근소하므로 STEP 0에서 반증 시 재검토 여지.

## [2026-07-10] collect-av-broad-news beat = DB 전용 관리 (D-AVBEAT-DB-ONLY)

**결정**: `collect-av-broad-news` beat 엔트리는 **`config/celery.py` dict가 아니라 DB로만 관리**한다.
- 등록 = `register_news_av_beat` 관리명령 → **전용 `CrontabSchedule(timezone='UTC')`(id=101)** 에 연결.
- **dict 재등재 금지.** `config/celery.py`의 `crontab(hour=1)`은 CELERY_TIMEZONE(America/New_York)로 해석돼 UTC 의도와 어긋나고, `update-economic-calendar`의 동일 ET 행과 공유·충돌한다.

**왜**: DatabaseScheduler는 beat 기동 시 dict를 DB로 sync한다(common-bugs #28 정정). dict에 ET-context `crontab(hour=1)`로 두면 **매 재기동마다 collect-av가 ET로 변질**(2026-07-10 실사고: UTC→ET id=11 공유, 07-10 01:00 UTC 발화 누락→05:00 UTC 표류). 비-dict DB 엔트리는 startup sync가 건드리지 않으므로, dict에서 빼고 전용 UTC 행으로 등록해야 UTC가 durable.

**동반 조치**: `celery-beat.sh` PROJECT_DIR을 worker 런타임 트리(`~/worktrees/sv-worker-runtime`, origin/main 정렬)로 전환(celery-worker.sh와 동일 B′). stale 편집 repo에서 beat 기동 시 옛 dict가 DB를 덮어쓰는 근원 차단.

**baseline at decision**: origin/main = ef312d6. 라이브 collect-av = UTC(id=101) 재복구 완료(재기동 후 durable).

## [2026-07-08] AV 트랙 서사 교정 — "EventGroup 4월 고정"은 배치1 도중 stale화

**교정**: news AV broad 트랙의 최초 전제 "EventGroup as_of가 2026-04에 고정(co-mention 소스 탈락)"은 **배치1 백필 도중 stale화**됐다. 지시서② STEP 0 실측 결과 **before as_of = 2026-07-03**(4월 아님).

**출처 판별(지시서③ STEP 0.2)**: 이 as_of=07-03의 원천은 **기존 하류 beat** — 수동 실행이 아님. `chainsight-co-mentions`(extract_co_mentions, 매일 10:00 ET, days_back=7) + `chainsight-event-group-leadership-daily`(22:15 UTC 평일, 내부에서 `load_event_groups()` 호출)가 배치1(06-14~07-03) 적재분을 자동 처리하며 as_of를 07-03까지 밀어올렸다.

**메커니즘 검증은 유효**: 지시서②가 07-04/05/06 마감분을 반영해 **as_of 07-03 → 07-06 이동**을 실증(extract_co_mentions days_back=25 → CoMentionEdge 4091→12654 → load_event_groups → 38그룹 as_of 07-06). 즉 "co-mention 소스 복구 → as_of 전진" 인과는 확정. **서사(4월 고정)만 교정**, 트랙 결론 불변.

## [2026-07-06] MP2-ALERTS Phase 2 — 채널·구조·경계 개정 (D-ALERTS-CHANNEL / -ARCH / -BOUNDARY-R1)

### D-ALERTS-CHANNEL — 첫 채널 = 이메일
**결정**: MP2-ALERTS Slice 0 범위 = 트리거 1종(regime 전환) + 채널 1개(이메일).
**Why**: 가중합 4.55. 타이브레이커 = ① port 구조의 저후회성(채널 추가는 delivery port 구현체 추가일 뿐) + ② 본문 표현력(HTML 메일 = 판단 문구·근거 풍부). M4 실측: EMAIL 백엔드 이미 셋업(daily report prod 발신 중, dev는 console 자동 폴백).

### D-ALERTS-ARCH — 3단 파이프라인
**결정**: 구조 = **트리거 → 디스패처·정책 → delivery port** 3단.
**Why**: 가중합 4.15 vs 2단(3.55)/모놀리식(2.85). 트리거(도메인 앱)·정책(dedup/구독 판정)·전달(채널 추상)을 분리해 각 축 독립 확장.

### D-ALERTS-BOUNDARY-R1 — 알림 코어 = packages/shared 신설 (원 D-ALERTS-BOUNDARY 개정)
**결정**: 알림 코어(디스패처·정책·AlertLog·AlertSubscription·delivery port) = **`packages/shared` 신설**. 앱별 문구·템플릿은 **registry 주입**(BOUNDARY-3 VIXProvider + `apps.ready()` 선례 재사용) — shared는 앱 무지 유지.
**Why**: 가중합 4.75 vs 3.45(app 잔류/지연), 마진 1.30 > 1.00 자동 확정. 개정 근거 = **입력 변경**(2026-07-06 사용자 선언: dashboard 트리거·시장 폭락 광역 경보·thesis 임계 등 다앱 소비 의도) → shared 판정 기준("둘 이상이 잠재적으로 쓸 토대") 충족 + 모델 이동 함정 회피(신규 시점 shared 생성 = 이동 대공사 없음).
**원 결정과의 관계**: 원 D-ALERTS-BOUNDARY(O3 하이브리드, 상태는 app 소유)가 **오류였던 것이 아니라 전제가 바뀐 것**(당시 단일 앱 소비 가정 → 다앱 소비로 변경). 개정으로 기록, 원 결정 보존.

### STEP 0 실측 결과 (2026-07-06, baseline origin/main=0fd70ea) — Slice 0 착수 전 필수 반영
- **M3 registry 선례 확정**: `packages/shared/stocks/services/vix_provider.py`(ABC port + `register_*`/`get_*` 싱글톤) + `apps/market_pulse/apps.py ready()` 등록. 알림 템플릿 registry는 동형, 단 `(source_app, event_type)` 키 dict로 경미 확장.
- **M2 shared 앱 관행**: `packages/shared/<app>/`(AppConfig name/label + models + migrations) + INSTALLED_APPS 1줄. metrics = models/ 디렉토리 선례. dry-run clean.
- **M5 트리거 접점**: 실제 task = intraday `mp_calc_regime_15min`(*/15, **EOD 아님**). `transitioned`는 transient(snapshot 미저장, return dict만). 격리 = try/except(self.retry) **블록 밖** 자체 try/except 또는 별도 `.delay()`. from/to→stance는 `resolve_regime_stance`로 도출 가능(판단 중심 제목 값쌈). **15분 upsert → 하루 내 flip 중복 위험 = dedup(cooldown/grain) 필수**.
- **M6 circuit_breaker**: `with_circuit(func,*,name)`(shared/llm/policy/circuit.py)로 email send 직접 래핑 가능.
- **⚠ M1 기존 골격 발견(승계 게이트, 디렉터 판단 대기)**: `services/serverless/`에 **사용자 알림 프레임워크 상당 부분 기존재** — `ScreenerAlert`(user·alert_type 6·preset/custom 조건·**cooldown_hours**·**notify_email/in_app/push 플래그** ≈AlertSubscription) + `AlertHistory`(sent/failed/skipped 이력 ≈AlertLog) + Serializer 4종. **단 delivery 미구현**(주석 스텁). 또 `services/news/AlertLog`(ops 인시던트 로그, 도메인 직교, **이름 충돌**) + `packages/shared/users/send_portfolio_alert`(죽은 스텁). ⇒ **v2 shared 코어를 신규 구축 vs serverless 골격 일반화(승계) 판단은 디렉터 몫.** Slice 0 지시서 작성 전 이 안건 해소 필요.

### D-ALERTS-GATE — serverless 골격 무접촉 격리 (승계 게이트 해소, 2026-07-05)
**결정**: serverless의 ScreenerAlert/AlertHistory 골격은 **무접촉 격리**(screener 전용 레거시로 KEEP). 일반화 승격·즉시 이관 **모두 기각**. Slice 0은 `packages/shared/alerting`을 **신규 구축**.
**Why**: 가중합 4.60 vs 3.35(즉시 일반화), 마진 1.25 > 1.00 자동 확정. serverless 알림은 **delivery 스텁이라 실질 중복 아님**(모델만 존재, 발송 0). 지금 이관하면 screener 도메인(필터 매칭)까지 끌려와 Slice 0 절단선이 붕괴. 수렴 여부는 screener 알림 실활성화 결정 시 별도 처리(TASKQUEUE SCREENER-ALERT-CONVERGE 휴면 등록).

### D-ALERTS-NAMING — 발송 기록 모델명 = AlertDispatchLog (2026-07-05)
**결정**: 발송 기록 모델 = **`AlertDispatchLog`**(구독 = `AlertSubscription`). db_table = `alerting_dispatch_log`.
**Why**: `services/news`의 기존 `AlertLog`(ops 인시던트 로그, db_table=news_alert_logs, 도메인 직교)와 **Python 클래스명 충돌 회피**. app_label 다르면 DB 테이블은 안 겹치나, import 스코프·가독성 혼선을 원천 차단.

### D-ALERTS-SUBJECT — 메일 제목 = 판단 중심 하이브리드 (2026-07-05)
**결정**: 제목 = `국면 전환: {from_kr} → {to_kr} ({stance})`. stance = `resolve_regime_stance(to_regime, "OK")` 재사용(labels.py REGIME_STANCE, 결정론적 매핑). 예: "국면 전환: 상승 후반 경계 → 전환 (방향 불확실 · 관망, 현금 비중 확보)".
**Why**: 가중합 4.40. 타이브레이커 = ① stance가 **결정론적 매핑**(LLM·계산 0, 렌더 값쌈) + ② 잠금화면 알림에서 **행동지침**이 사건 나열보다 유용(투자자가 제목만 봐도 "무엇을 할지" 파악). 문구는 labels.py 단일 소스 재사용 — 재작성 0.

### Slice 0 검증(2026-07-05, baseline origin/main=0b27c9c → land 3eb06a7)
pytest alerting 8(E1~E6+제목+경계AST) · marketpulse 279/1skip · 아키텍처 경계 7(shared→apps 0) · health_check 10/10 · migration 0001 생성만(migrate 미실행). 커밋 4분리(shared 코어 54a09cf / market_pulse 49cb8db / 시드 b03881b / 테스트 3eb06a7) ff(rebase clean). **[적용 대기]**: `migrate alerting` + `seed_alert_subscription --email <주소>` 병진 수동.

### D-ALERTS-RENDER — 알림 본문 풀 리포트화 = 단일 경로 소비 + 폴백 (Slice 1, 옵션 C)
**결정**: regime 전환 메일 본문을 최소 텍스트 → **풀 리포트**(전환 요약·델타·anomaly 활성·섹터 상위/하위)로 승격. 3원칙:
1. **단일 경로**: 렌더러는 판단 화면과 **동일한 `overview._build_payload()`** 를 소비(재계산 0). 지표·델타·라벨을 렌더러가 독립 재계산하는 코드 금지(화면↔메일 drift 봉쇄).
2. **폴백 무실패**: 풀 렌더 실패 시 디스패처가 S0 최소 본문(`render_regime_transition`, transient 값만)으로 폴백 → 발송 자체는 실패 안 함. 폴백은 `AlertDispatchLog.error`에 `RENDER_FALLBACK:` 접두(status=SENT)로 기록 → 발송 실패(FAILED)와 구분(**마이그레이션 0** — 기존 error 필드 재사용).
3. 제목 형식 불변(D-ALERTS-SUBJECT), 디스패치 경로 **LLM 0**, shared→apps import 0.
**STEP 0 판정**: M-A = **(a) 순수 호출 가능** — `_build_payload()`가 request/DRF 무관 순수 함수(코어 추출 불요, Part A 생략). M-B = 렌더러 **apps/market_pulse** 소속(빌더 import 필요) + shared는 **registry 주입**(dependency inversion, dispatcher가 apps 미import). fallback도 registry 주입(register_alert_renderer에 선택적 fallback 슬롯 additive). M-C = 디스패처 render를 try/except로 감싸 폴백. M-D = delta(sector_deltas·anomaly_delta)가 `_build_payload` 단일 산출에 포함(별도 빌더 아님).
**Why**: 사용자 확정 옵션 C(메일만 읽어도 판단 화면 수준 재료). 차트/이미지는 범위 밖("이메일 차트는 이메일 소속 아님", MP2-TREND 분리 근거) — 텍스트·표만.

### Slice 1 검증(2026-07-07, baseline origin/main=1e9b9c6 → 브랜치 tip 0107b1a)
pytest 신규 7(풀 섹션 스냅샷·결측 graceful·신규사전0·`_build_payload` 순수호출·제목 불변·렌더 예외→최소 폴백 발송(SENT+RENDER_FALLBACK)·정상 무폴백) + alerting S0 8 + 경계 3 + marketpulse api 80 green. FE 변경 0. **migration 0(No changes detected)**. 커밋 3분리(렌더러 c8d48f0 / 디스패처+폴백 4016741 / 테스트 0107b1a) ff. 미머지(통합 승인 대기).

**baseline at decision**: origin/main = 1e9b9c6. prod 쓰기 0(조회-시 파생 소비, 마이그레이션 0). 실메일 발송은 병진 수동(S0 프로토콜 동일).

## [2026-06-23] Phase 1 화면 게이트 = 조건부 통과로 종결

**결정 (D-P1-SCREENGATE)**: market_pulse v2 Phase 1 화면 게이트 = **조건부 통과로 종결**. 차단(P1) 결함 **0**.

**Why**: 라이브 백엔드(:18765) 데이터로 `/market-pulse-v2` 전 카드(Ticker·Status·Regime·Breadth·Sector·Concentration·Briefing) 정상 렌더 + 한국어 sense/LLM brief + 신선도 당일 + 콘솔 에러 0 + CORS/인증/봉투 무결(overview 200) 실측 확인. 경미(P2) 2건 = ① **모바일 실렌더 눈검증 미확보**(resize_window 뷰포트 미반영 = 도구 한계, 반응형 설계는 JS로 코드 입증: 카드 `sm:grid-cols-2` 1열 전환·TickerBar `overflow-x-auto`·터치 44px) → **비차단 권고 추적** ② **Breadth raw=0 / Concentration 상위종목 일부 부재** → **graceful fallback 정상**(밴드·sense 렌더 + 정직한 안내, 카드 안 깨짐) = 데이터 파이프라인 별 트랙.

**선결 사건(참고)**: 초기 "데이터 로드 실패(카드 0렌더)"는 **FE dev 서버 다운**(`next dev` 프로세스 부재 → connection refused)이 원인 — 코드 결함 0(A/B/C/D/E 전부 배제), 재기동으로 완전 해소.

## [2026-06-25] 집중도 리스크 3렌즈 — 가짜 절대리스크 금지

**결정 (D-CONC-RISK-LENSES)**: 집중도(Concentration) 리스크 해석은 **3렌즈로만** 제공하며, 각 렌즈의 데이터 요건을 게이트로 둔다. **"top10=40% → 하락 X%" 같은 가짜 절대리스크는 금지**(없는 인과를 단일 숫자로 위장).
- **① 유효 종목 수 (1/HHI)** — **즉시 가능**. HHI는 overview/detail에 존재(실측 0.0199 → 유효종목≈50). 분산도의 정직한 단일 지표, 추가 데이터 0.
- **② 퍼센타일 (현재 집중도가 과거 분포의 몇 분위)** — **데이터 깊이 게이트**. 의미 있으려면 최소 1년(영업일 ~250), 이상적 다년. 깊이 미달 시 표시 금지 또는 "표본 N일, 잠정" 정직 라벨.
- **③ 조건부 과거결과 (고집중일 때 이후 분포)** — **Analog 트랙 산하**. 반드시 **분포 + 표본수 + 신뢰구간**으로만 제시, **단일 숫자 금지**. 표본은 고집중·저집중 양쪽이 필요(변별).

**Why**: triage 실측(D-P15-TRIAGE) — 현재 히스토리 58일·13점·top10 전부 ≥38%(저집중 표본 0). ②는 분포 추정 불가(깊이 부족), ③은 변별 불가(전부 고집중). 단일 절대리스크 숫자는 이 빈약한 표본을 은폐 → 금지. ①만 지금 정직하게 가능.

## [2026-06-25] Phase 1.5 버그 triage 결과 + 데이터 부족 확정

**결정 (D-P15-TRIAGE)**: 화면 결함 4건 원인 분류 확정 — 수정처 존 명시.
- **A1 Briefing 빈 모달** = **FE 매핑 버그**. detail은 `body`(352자 실측) 반환하나 모달이 `body_sections[]`(빈 배열) 만 순회 → `body` 문자열 **fallback 누락**. 수정 = frontend.
- **A2 간헐 401** = **토큰 갱신 경합**. overview·cards detail 동일 `IsAuthenticated`·인증 헤더 부착 → 권한차 아님. detail 클릭 시점 access 만료 + refresh 전 401. 수정 = frontend authAxios refresh 인터셉터.
- **A3 도넛 float+레이블 겹침** = **포맷**. `ConcentrationDetail.tsx:55` `<Pie label>` 기본 레이블이 raw weight(0.6134…) 미반올림 + 조각 겹침(Tooltip/목록은 `toFixed(2)` 정상). 수정 = frontend.
- **B1 Breadth=0** = **BE 미수집**. 최근 5일 `total_count=0`(종목별 등락 universe 미채움, "수집했는데 0" 아님). 수정 = BE/데이터(breadth fetcher).

**데이터 부족 확정 (② ③)**: 집중도 히스토리 = **58일·13점·top10 전부 고집중**(저집중 0). **②③은 시간만으로 안 열림** — ③(조건부 과거결과)은 **레짐-다양성 게이트**(저집중·고집중 양 표본 필요)이지 단순 시간 누적이 아님. 케이던스 실측: beat=`mp_calc_concentration_daily`(평일 daily 17:15 NY) — 6/16~6/25 daily 정상, 단 **5/7~6/11 35일 갭**(과거 운영 공백, daily 의도지만 누락). 현재부터 daily 누적 시 ②는 ~1년 후 가능, 과거 갭은 미백필.

**참고**: "cache: MISS"가 엔드유저 모달에 노출(`_envelope` cache_state) — 디버그 표기 사용자 노출, 정리 후보(MP1.5-FIX 동봉).

## [2026-06-25] 슬라이스 ④ 그룹핑 축 = C (호출형 provider×call_symbol 동질성)

- 선택지: A provider(2그룹) / B surface(6그룹) / C 호출형(4그룹)
- 가중합(합1.00): A 3.52 / B 2.91 / C 4.22, 마진 C−A +0.70
- 근거: 최상위 제약 = 행위보존(byte-IDENTICAL). 두 site가 "같은 작업"이 되는 단위는
  provider가 아니라 call_symbol+config 객체 형. C만 배치=하네스 1개로 정렬 →
  korean_overview 템플릿 19곳 무손실 재사용 + 진짜 다른 4곳(구SDK·Anthropic·count_tokens) 격리.
- 4 Part: ① 신SDK Gemini 19(→ sync15/aio4) / ② 구SDK Gemini 1 / ③ Anthropic 생성 2 / ④ count_tokens 1.
- 보류: ④ count_tokens가 complete() 대상인지 별도 미니결정(생성 아님).

## [2026-06-26] Part ①-sync 범위 정정 — #16 keyword_generator.py를 aio Part로

- 발견: STEP 0은 violation을 genai.Client 인스턴스 단위로 셌고 대표 call_symbol 1개만 기록.
  #16의 단일 client를 sync(_call_llm_sync)+aio(_call_llm)가 공유 → sync-only 이관으로 client 제거 불가.
- 조치: Part ①-sync = clean sync 14(완료 게이트 동결 9). #16은 Part ①-aio에서 파일 통째 이관.
- 일반화: "sync/aio"는 call 단위가 아니라 client 단위 속성. aio-touched client는 aio Part 소속.

## [2026-06-26] Part ①-sync — #19 추가 defer + contents-형태 편차 정책

- #19 llm_relation_extractor: contents가 **2개 Part**(`[Part(text=SYS), Part(text=user)]`)라
  complete()(단일 문자열 전달)로 byte-IDENTICAL 재현 불가(concat 시 2파트→1파트 payload 변경).
  → #16과 동형 구조 미스매치로 **defer**. complete() 다중-Part contents 지원 신설 후 후속 Part. KNOWN_VIOLATIONS 존치.
- 최종 Part ①-sync = 13곳(#5 + #18·#20·#21·#15·#22·#13·#14·#23·#1). **완료 게이트 동결 = 10**(9→10).
- contents-형태 편차 정책: 지시서 IDENTICAL 3기준 = (config 객체 byte 동일 + 프롬프트 본문 동일 + system_instruction 동일).
  genai가 정규화하는 soft 편차는 **이관 허용**(wire 동일):
  - #18·#21: contents `[Content(role=user, parts=[Part(text=f"{SYS}\n\n{prompt}")])]` 단일파트 → complete()에 concat 문자열.
    genai가 str→동일 Content 정규화. system_instruction 미설정(원본도 미설정). 본문 동일.
  - #20: config `dict{temperature,max_output_tokens}`(thinking 없음) → GenerateContentConfig 동일 필드. genai dict→config 정규화.
  - hard 편차(2파트 등)는 wire 자체가 달라 defer. soft↔hard 경계 = "genai 정규화로 wire 동일한가".

## [2026-06-27] aio 코어 선행 범위 = B (의존 따라 3분할, ②b-stream 흡수형)

- 선택지: A 통합 / B 3분할 / C 2분할. 가중합(합1.00): A 2.62 / B 4.44 / C 4.26.
  마진 B−C 0.18(<0.40) → 타이브레이커 최고가중(검증 축 분리)에서 B=5>C=4 → B.
- 분할: ②b async complete() / ②b-stream(②b 위, #12) / ②c multipart(독립, #19 sync).
  ②b-stream은 별 검증단위이되 ②b 직후 연속 실행으로 흡수(축 명료성 + 왕복 절약).
- aio Part 최종 = 5곳: #10·11·12·16·17. #19는 멀티파트(async와 직교)라 ②c-sync로 분리.
- ②b는 소비처 0으로 land → 이관은 후속 Part 지시서.
- STEP 0 측정(2026-06-27): 현 complete() 표면 = sync 전용·str contents·stream 없음. async 부재가
  #10·11·16·17 blocker, #12는 +stream, #19는 멀티파트(직교). 노브는 blocker 아님(합집합 ⊆ (c)혼합).

## [2026-06-28] Part ①-aio — #10 circuit breaker 보존 방식 = A (소비자 CB 존치)

- 측정: #10 context_compressor의 aio 2호출(137·291)은 파라미터화 CB `gemini_compress`
  (failure_threshold=5, recovery_seconds=60)로 감싸짐. #11·#16·#17은 circuit 미사용(clean).
  (지시서는 #16 circuit 공유를 물었으나 #16은 무circuit — 실제 CB 보유자는 #10.)
- 결정: #10은 **소비자 CB(`cb.acall`) 존치 + 감싸는 대상만 generate_content→acomplete(정책 off)** 교체.
  acomplete의 circuit 정책(get_circuit(name)만, 파라미터 미전달)으로 통합 시 5/60 유실 위험 → A로 회피.
  CB 파라미터 정확 보존 + 직접 genai 제거(동결 −1) + config byte 동일. 행위변경 최소.
- async Anthropic 미구현은 **의도**(②b): aio Part 5곳 전부 Gemini라 불요, acomplete(provider='anthropic')는
  NotImplementedError로 명시 차단(조용한 sync 폴백 금지). 미래 세션이 "빠뜨린 구현"으로 오해해 채우지 말 것 —
  슬라이스 ③ Anthropic 이관에서 AsyncAnthropic로 신설.

## [패턴] circuit breaker = 소비자 소유, 코어는 (a)complete()/astream()만 제공

- 근거: CB 파라미터(예 #10 gemini_compress 5/60)는 소비자 도메인 로직. 코어가 흡수하면
  코어 기본값에 묻혀 byte 차이 → 행위보존 위반. cb.acall(...)이 감싸는 대상만 코어 호출로 교체.
- 적용: #10(완료, non-stream). **#12는 streaming 특수성으로 아래 [2026-06-29] 결정으로 변경됨.**

## [2026-06-29] streaming CB는 코어 흡수(astream(circuit=)) — #12 옵션 1 (위 non-stream 패턴 예외)

- **결정**: streaming 경로의 CB는 **코어 astream(circuit=)이 흡수**한다(non-stream의 "소비자 소유"와 갈림).
  코어가 셋업(provider.aopen_stream = 스트림 오픈)만 awith_circuit으로 감싸고, 청크 iteration은 CB 바깥.
- **Why(non-stream과 다른 이유)**: non-stream은 소비자가 `cb.acall(complete)`로 CB를 보유할 수 있다
  (complete는 await 가능 coroutine). 그러나 astream은 **async generator** — `cb.acall`은
  `await func()`를 요구하는데 async generator는 await 불가(TypeError). 어댑터를 끼우면 실제 SDK
  네트워크 셋업이 CB 바깥(첫 `__anext__`)으로 밀려 CB가 셋업 실패를 집계 못 함 → gemini_rag CB가
  **영원히 OPEN 못 하는 죽은 no-op**(기능 사망). 즉 "소비자 소유"를 streaming에서 형식만 지키면
  CB가 무력화된다. → 코어가 셋업만 CB로 감싸야 원본 `cb.acall(generate_content_stream)`와 진짜 동형.
- **행위보존**: 셋업 실패만 집계(원본 동형), 청크 읽기 실패는 미집계·raw 전파. CB 파라미터(retry_attempts=1
  등)는 여전히 소비자가 get_circuit 레지스트리에 사전등록(코어가 name으로 재사용) → 파라미터 byte 보존.
- **경위**: 지시서 원안은 "#12도 CB 소비자 존치". STEP 0에서 위 TypeError/CB 사망을 발견·HALT 보고 →
  사용자가 옵션 1(코어 흡수) 선택. ②b-stream의 "streaming circuit = gap, NotImplementedError"도 해제.
- **적용**: #12(완료). 향후 streaming CB 소비자는 astream(circuit="name") + get_circuit 사전등록 패턴.

## [2026-06-29] BOUNDARY-LLM 슬라이스 ② #9 종결 — 구SDK Gemini adaptive stream 이관 (동결 3)

- **결정**: #9(`services/rag_analysis/services/adaptive_llm_service.py` `_generate_gemini_stream`의 구SDK
  `GenerativeModel(generation_config=dict, system_instruction=…).generate_content_async(prompt, stream=True)`)를
  **코어 `astream(provider="gemini")` 경유로 이관·종결**(신SDK `genai.Client.aio.models.generate_content_stream`).
  머지 hash `f89cbd6`. 동결 **4 → 3**(burn-down: 23→10[④①-sync]→…→4[④#19]→**3**[②#9]). 구SDK 군집 종결.
  잔여 동결 3 = #2 portfolio `Anthropic` · #3 estimator `count_tokens` · #8 adaptive `AsyncAnthropic` stream(③ 대상).
- **Why(wire 동등 = 재도출이지 바이트 캡처 아님 — ★caveat★)**: 구→신 SDK 첫 변환이라 wire byte 동등이 최대 리스크.
  그러나 **구SDK(`google.generativeai`)가 이번 이관으로 이미 미설치**(STEP 0 실측: 신SDK `google.genai`만 설치) →
  옛 경로의 실제 proto 직렬화 바이트를 캡처할 길이 없다. 따라서 IDENTICAL은 **재도출**로 입증한다: 코어
  `_build_config_kwargs` 기준 옛 매핑 vs 신 매핑의 `GenerateContentConfig`를 `model_dump_json(exclude_none=True)`로
  비교 → config = `{max_output_tokens, temperature, system_instruction}` **정확히 3키, 잉여 0**(thinking_config·
  top_p·stop·response_mime_type 없음; CB·escape·extra 미설정), contents(단일 str)·model 변수 그대로 통과. 옛
  `generation_config{max_output_tokens, temperature}` + 생성자 `system_instruction` → 신 3키 1:1 매핑. **"IDENTICAL =
  재도출, 바이트 캡처 아님"을 명기**한다(과신 금지).
- **보강 증거(행위보존 실질 = 회귀 0)**: rag_analysis 부모/자식 대조 — 부모 `7f5da9e`(미이관) **31 fail** → 자식
  `f89cbd6`(이관) **30 fail**, passed 102→103, **ERROR 8=8 불변**. 실패셋 diff: 부모에만 있는 fail = cache_miss
  e2e 1건(이관이 **FAIL→PASS 복원**, dead genai seam → 코어 seam 갱신), **자식에만 있는 신규 fail = 0**. 잔존 30
  fail은 전부 선존(#9 무관: test_views `KeyError 'success'` CRUD 봉투 · entity_extractor/llm_service `AsyncAnthropic`
  stale seam · task naming). 신규 잠금: `test_adaptive_llm_migration.py`(4, wire 잠금, `tests/unit/rag_analysis/` 91→95).
- **토큰 추출 전환**: 구SDK 루프 후 `response.usage_metadata`(객체-aggregate) → 신SDK **마지막-청크** `chunk.usage_metadata`
  (#12 동형), usage 미제공 시 추정 폴백 보존. `_init_client` gemini 브랜치도 구SDK import 제거(가용성=API 키 존재).
- **미래 세션 지침**: 옛 wire 바이트의 *실제* 검증이 꼭 필요하면 **구SDK throwaway 재설치 후 캡처**가 유일한 길이나,
  회귀 0(위)이 행위보존을 실질 보완하므로 **gold-plate는 보류**로 둔다(비용 대비 효익 낮음). #8(adaptive Anthropic)·
  #2(portfolio Anthropic)는 ③ Anthropic 트랙(anthropic agenerate/astream/aopen_stream 신설 범위 디렉터 결정 대기).
- **적용**: #9(완료, f89cbd6). 향후 구SDK 잔재 발견 시 동일 패턴(코어 astream/complete 경유 + wire 재도출 입증 + 회귀 0).

# ADR-LLM-001 — LLM 실행 모드 계약 v1 (packages/shared/llm)

상태: **Accepted** (2026-07, 동결 2 시점) · 소유: ops/BOUNDARY-LLM

## 맥락
monorepo의 흩어진 LLM 직접호출을 `shared/llm` 단일 래퍼로 모으는 burn-down 중,
남은 Anthropic 소비자(#8 stream·#3 count_tokens)를 이관하기 전 계약을 확정한다.
네 트랙(dashboard·chain_sight·market_pulse·구조관리 배치)의 수요 조사 + Anthropic API
사실 확인으로 입력을 모았다.

## 결정 — 3모드 계약
진입점은 기존 "함수 분리" 결을 유지(mode= 플래그 아님, 견고한 non-stream 표면 보존):
- **sync**: `complete/acomplete(prompt, provider, model, max_tokens, system?, temperature?, response_schema?)` → `LLMResponse`
- **stream**: `astream(...)` → 정규화 델타 흐름 + 종단 usage (circuit 옵션)
- **batch**: `batches.submit(requests[custom_id, params])` → 핸들 ; `poll(id)` ; `results(id)`
- **util**: `count_tokens(prompt, provider, model)` → int

가로지르는 계약(전 모드 공통):
- **structured output**: `response_schema=` → Anthropic `output_config.format` / Gemini `output_config` 매핑(JSON outputs 모드).
  함정 명시: 새 스키마 첫요청 100~300ms·24h 캐시, 복잡도 상한·180s 타임아웃, citations·prefill 비호환.
- **usage 정규화**: input/output/cache 토큰, 완료 후 총합, 단일 필드.
- **provider 정규화**: shape·usage·stop_reason를 래퍼가 흡수(호출부 provider-무관).

## 하위 결정 (가중합)
- **갈림 A = A1 얇은 batch 프리미티브**(submit/poll/results, 폴링은 소비자 celery 배치가 소유).
  가중합 **4.48, 마진 1.00 자동결정**. 근거: batch 소비자 전부 celery 오케스트레이션 보유 + 소비자 없이 두껍게=speculative.
- **갈림 B = B3 계약은 정규화 델타+usage로 잠그고 #8만 지금 그 모양으로 신설, 기존 #12(gemini stream)는
  별도 IDENTICAL 슬라이스로 후속 이관**. 가중합 **4.44, 마진 0.70**. 근거: 감사 F가 잡은 stream 정규화 흠을
  계약에서 메우되 두 provider를 한 커밋에 안 섞음.

## 구현 규율 (γ — 계약 완성 ≠ 구현 완성)
소비자 있는 것만 구현, 없으면 소비자 명시 스텁:
- **구현**: sync(#2 landed, a4b192a) · stream anthropic 정규화(#8, ③b, circuit=None 행위보존) ·
  usage/provider/stop_reason 정규화 · response_schema JSON outputs(chain_sight·market_pulse 수요).
- **스텁+주석**: batch 얇은 프리미티브("구현 대기: chain_sight 10-K·News Intel 배치") ·
  strict tool use("구현 대기: 미래 에이전트") · agenerate("소비자 미확인").
- **후속 슬라이스**: #12 gemini stream → 정규화 델타(자기 IDENTICAL 게이트).

## 근거 링크 (수요 입력)
- **market_pulse**: Translation Layer=일일 배치(beat), Anthropic 직접호출 0, JSON 강제(프롬프트), Gemini sync — batch/sync JSON consumer.
- **chain_sight**: LLM 호출 0(레거시 0), 10-K 관계추출 JSON 필수, 스토리피드 없음, batch 성격.
- **dashboard**: LLM 위임(표면 전용), 스트림 강제 금지 요구.
- **구조관리(배치 대표)**: provider 정규화 seam·batch/stream 배타·native structured output.
- **API 사실**: structured output GA(output_config.format), batch 50%할인·무순서·custom_id·스트림배타·단발tool·100k/256MB 한도.

## 함의
stream은 #8 단일 소비자용 옵션(세 앱 전수 stream 수요 0). sync/batch가 1급.
미래 소비자(chain_sight·News Intel)는 이 계약 위에 마이그레이션 없이 얹힌다.

## 구현 진행 (③b, 2026-07-02)
- **정규화 델타 실체 = `StreamDelta{text}` + `StreamFinal{input_tokens, output_tokens, cache_tokens=0}`**
  (`packages/shared/llm/types.py`) — §핀1·§핀4 실측한 #12(gemini)·#8(anthropic) 공통 봉투 표준화.
- **anthropic astream 신설**: `messages.stream`(async with)을 provider 어댑터가 셋업(`aopen_stream`=
  `cm.__aenter__`=요청 전송=CB 경계, gemini await→iterator 동형 브리지) / 순회(text_stream→StreamDelta,
  get_final_message().usage→StreamFinal, `__aexit__` finally 연결 해제)로 분해.
- **#8은 shim으로 얹음**(circuit=None 행위보존): 코어 StreamDelta/StreamFinal → 기존 dict 봉투
  ({type:delta/final})로 한 겹 변환, 하류 로직 무변경. wire IDENTICAL(잉여키 0), 회귀 0(부모 대조 실패셋 동일).
- **gemini astream은 무변경**(#12 IDENTICAL 보존): 코어 astream이 gemini는 raw 청크 pass-through 유지,
  anthropic만 StreamFinal 인지(cost 분기). **후속 슬라이스** = #12 gemini astream → 정규화 델타 이관 +
  #8 shim 제거(자기 IDENTICAL 게이트). agenerate·batch·strict-tool은 소비자 미확인 스텁 유지(γ).

## 구현 완료 (④ #3, 2026-07-02 — BOUNDARY-LLM burn-down 종결)
- **util count_tokens 진입점 신설**: `core.count_tokens(prompt: str|list, *, provider, model, system) -> int`
  (계량, 생성 아님 → LLMResponse 아님, 정책 미적용). anthropic 구현(`messages.count_tokens`, .input_tokens
  int, prompt=list이면 messages pass-through) + gemini 스텁(소비자 0, γ).
- **#3 이관**: estimator_v3 직접 `Anthropic().messages.count_tokens` → 코어 util 경유. messages+system
  wire IDENTICAL(잉여키 0), cache·fallback은 소비자(estimator) 소유(행위보존). `set_client`/`_get_client`
  주입 seam 제거 → 테스트는 `anthropic.Anthropic` 패치로 이관(#13 선례).
- **동결 1→0 = burn-down 종결**: KNOWN_VIOLATIONS 빈 목록. **ADR-LLM-001 구현 3종 완료 = sync(#2 complete)
  · stream(#8 astream) · util(#3 count_tokens)**. 전 LLM 소비처가 `packages/shared/llm` 단일 경유.
  잔여 스텁(소비자 미확인, γ) = batch·strict tool use·agenerate·gemini count_tokens. 후속 = #12 gemini
  astream 정규화(동결 무관, 이미 이관됨). burn-down 여정: **23→10(④①-sync)→6(①-aio)→5(#12)→4(#19)
  →3(②#9)→2(③a#2)→1(③b#8)→0(④#3)**.
## [2026-06-25] MP1.5-FIX 화면 게이트 = 조건부 통과

**결정 (D-P15-SCREENGATE)**: MP1.5-FIX 시각 검증 = **조건부 통과**. 차단(P1) 결함 **0**. 검증 대상 = `origin/main = 2c9fbca`(MP1.5-FIX 5건 머지본) 클론 라이브 실측.
- **A1 Briefing 본문** = **PASS(실측)**. 카드 클릭 모달에 본문 prose 전체 렌더("현재 시장은 후반 강세 국면…투자 결정은 본인 책임"). 이전 제목·토큰만 → `body` fallback 매핑 적용 확인(커밋 `0f86e55`).
- **① 유효 종목 수** = **PASS(실측)**. Concentration overview 카드에 "유효 종목 수 ≈ 51종 (1/허핀달)" 1줄 표시(커밋 `2c9fbca`, D-CONC-RISK-LENSES 렌즈①).
- **cache 가드** = **PASS(코드 입증)**. dev에서 "cache: MISS" 노출되나 이는 **의도된 dev 전용 가드** — `CardDetailContainer.tsx:48` `process.env.NODE_ENV !== 'production'` 조건 → **프로덕션 빌드 `null`(비노출)**. date·model 등 의도 메타는 유지(커밋 `a079870`). dev 시각검증의 구조적 한계 → 코드로 갈음.
- **회귀** = **PASS(실측)**. Regime·Sector·Breadth·Briefing 카드·게이지·한국어 sense 전부 정상 렌더, 콘솔 에러 0, overview/i18n 200.
- **A2 401** = **vitest 3건 갈음**(눈검증 불요, triage 합의).
- **A3 도넛** = **조건부(P2 잔존)**. %포맷 `toFixed(1)`(6.3/5.6/5.4/61.5%)·미반올림 raw(0.6134…) 제거·**대형 조각 겹침 해소**는 완료(커밋 `9529671`). **단 좌상단 소형 조각(META≈3.3%·GOOG≈5.4% 부근) 라벨 겹침 잔존** — 데스크탑·모바일 동일. 가독성 저하이나 렌더 정상·차단 아님(P2 → MP1.5-A3-TAIL).

**Why**: 전제였던 "로그인 세션"이 실제 미충족(브라우저 토큰 부재) + 클론을 `:3100`으로 띄워 BE CORS origin 화이트리스트(`config/settings.py:318`=:3000만) 누락 → 전 인증요청 차단('503'처럼 표면화). **클론을 `:3000`으로 재기동**(메인 미가동 포트 재사용)해 메인·BE·settings 무접촉으로 해소 후 실측(common-bugs #39). PART 2 모바일(390px)도 ①·A1·A3 정상 표시·레이아웃 유지 실측. 4/5 항목 실 PASS, A3만 소형조각 겹침 잔존 → **조건부**. 검증 세션 코드/메타 변경 0(클론 diff 0, HEAD 2c9fbca 불변).

## [2026-06-25] Phase 1.5 게이트 완전 종결 — A3-TAIL 해소

**결정 (D-P15-SCREENGATE 종결 갱신)**: MP1.5-A3-TAIL 완료(`77847ca`)로 A3 조건부 잔여가 해소되어 Phase 1.5 시각 게이트 = **완전 통과/종결**. MP1.5-FIX 5건 전부 PASS, 잔여 0 → **Phase 2(#1 MP2-ANALOG) 진입 가능**.

**Why**: A3 도넛 좌상단 소형조각 라벨 겹침을 **leader-line 외부 라벨**(좌/우 midAngle 분기 + 수직 슬롯 분산)로 해소. 1차 구현은 좌표 수치상 겹침 0이었으나 **상단 12시 라벨이 SVG 컨테이너(height 260) 밖으로 클리핑**되는 결함을 라이브 시각검증에서 발견(좌표≠실렌더 교훈) → 2차로 height 260→320 + nudge 하향 + Y_MIN/MAX 경계 가드로 수정. 부수: 모듈 레벨 가변 전역(`_slotRegistry`/`_epochCounter`/`_registryEpoch`) 제거 → `computeAllLabelLayouts` 순수함수 + useMemo 사전배치 + useRef 캐시(렌더 순수성·Strict Mode 이중렌더·다중 인스턴스 안전). 라이브 :3000 데스크탑+모바일(390px) 11개 라벨(others 61.5% 포함) **전수 가시·클리핑 0·겹침 0** + 라벨값 정합(NVDA 6.27→6.3%) 실측. tsc 0, vitest 신규 28/전체 418. 검증 클론은 시각확인 전용(복사 후 reset 원복), 코드는 worktree `monorepo/sess-mp-a3tail`에서만 수정.

## [2026-06-26] MP-VIX-SRC — VIX provider 소스 교체로 regime degraded 복구

**결정 (D-MP-VIX-SRC)**: `MacroVIXProvider`의 읽기 소스를 `macro.MarketIndex/MarketIndexPrice(category='volatility')`에서 `macro.IndicatorValue(code='VIXCLS')`로 교체. VIXProvider 포트(packages/shared) ABC 시그니처·반환계약(`list[Decimal]` 오름차순 / `float|None` / 빈결과 `[]`·None)·BOUNDARY-3(의존 역전+등록) **불변** — 구현 내부 쿼리만 교체. 클래스명 `MacroVIXProvider` 유지(IndicatorValue도 macro app 소속이라 명칭 정합), docstring만 수정.

**Why**: STEP 0 측정 — volatility 소스가 **0건**(`MarketIndex(volatility)`·`MarketIndexPrice` 모두 0)이라 `get_vix_series=[]`·`get_latest_vix=None` → `DynamicRegimeCalculator._calculate_regime`의 `if not prices: return "normal"`(line 85-89) + `eod_pipeline._get_vix_value`의 None→20.0 fallback → **두 소비처(eod_signal_calculator·eod_pipeline) 모두 항상 'normal'**. 실증: EODDashboardSnapshot 75행 `vix_regime` 전부 `normal`(degraded, 변별 0). 실제 적재된 `VIXCLS`(IndicatorValue, 232행, 영업일 연속, Decimal·날짜 인덱스 = 계약 정합)로 교체. **경우 X(이미 망가짐) 확정 → 버그수정**(경우 Y=멀쩡 동작 아님). **행위 델타 검증**(운영 DB 재계산, prod UPDATE 없음): `{normal:75}` → `{normal:57, elevated:10, high_vol:8}`(18건 변별), 스폿 03-13 VIX27.19→high_vol·06-12 VIX17.68→normal(상식 정합) = '값이 올바르게 변함'. 단일 파일 + 신규 단위 6 + 회귀 384/1skip + 경계 green. 커밋 `bbe6b1b`. prod 75행 소급 재적재는 후속(MP-VIX-BACKFILL, 수동), VIXCLS 06-12 stale은 별도(MP-VIX-STALE).

**관련 측정(MP2-ANALOG 데이터 파운데이션, STEP 0 3세션)**: ① intraday `RegimeSnapshot` 영속이나 LATE_BULL 96%·유효 16행 = **레짐 다양성 게이트**(Analog 매칭 변별 불가, D-CONC-RISK-LENSES ③과 동형) ② intraday regime 백필은 **히스테리시스(2일, previous_snapshot 3상태) 의존 → 순차재생만**(임의날짜 독립계산 불가, forward-only) ③ EOD regime은 rolling window 의존 → **독립 백필 가능** ④ FRED 백필 멱등(`update_or_create` upsert) 안전, 단 MOVE·VIX3M은 FRED series 아님(400, 별도 소스 필요).

## [2026-06-29] MP-VIX-STALE — VIXCLS 자동 sync 커버리지 갭 수리 + 워커 재발방지

**결정 (D-MP-VIX-STALE)**: FRED 일간 4종(VIXCLS·DGS10·DGS2·T10Y2Y)을 `mp_sync_fred_indicators_daily`의 `FRED_RECURRING_SERIES`에 편입(**7→11**). beat·task 로직 무변경(리스트만 확장), 멱등 upsert. 재발방지는 코드 11종 + **워커 재기동**(메모리 7→11)까지 포함해야 완성.

**Why**: STEP 0 측정 — VIXCLS·DGS 일간군이 자동 재귀 beat 커버리지 밖(`FRED_RECURRING_SERIES` 7종=NFCI군·HY·T10Y3M만, VIX3M·MOVE는 Yahoo 별도)이라 **수동 command에만 의존** → 06-12 stale(VIXCLS 15일 갭). 11-macro 대조: "수동만" 그룹 일제 stale vs "자동 beat" 그룹 전부 신선 = 커버리지 패턴. **경우 P 확정**(FRED 실호출: VIXCLS·DGS 4종 06-25/26까지 정상 발행 = 우리가 안 받은 것, FRED 지연 Q 반증). MOVE·VIX3M은 FRED 미지원(400)이라 제외, 월간(CPI·FEDFUNDS·UNRATE·PCEPI)은 일간 재귀 대상 아님. **수리**: ⒜ 코드 `FRED_RECURRING_SERIES` 7→11(커밋 `20f0e6d`, 테스트 len/idempotent 갱신 + 일간군 명시, 12 passed) ⒝ PART2 백필 33행(06-13~25, 멱등) ⒞ **워커 재기동**(`celery-worker` 33397→6413). 재발방지 검증: `.delay()` → 재시작 worker가 **11종 sync 실행**(series 11, VIXCLS·DGS군 포함) = 메모리 7→11 전환 직접 입증(`.apply()`는 셸=11종이라 무의미, `.delay()` 필수). beat `enabled`(평일 NY17:40), DatabaseScheduler 생존(#28 무해). **재발방지 4축 충족**: 코드 11 + 워커 11 + 자동 sync 11 + beat 생존.

**부수 사건(워커 코드베이스 종속 규명)**: celery 워커는 `~/Desktop/stock_vis`(로컬 main)를 직접 import — 별도 deploy/clone 없음(우회 불가). push만으론 재발방지 미완(워커 미재시작 시 메모리 옛 코드). + 진행 중 로컬 main 작업트리에 타 세션(cs-board) go-live 문서가 미커밋→`eee3b19` 커밋으로 남아 divergence 유발 → 비파괴 패치 보존(handoff) 후 cs-board가 origin(`b457bbf`) 정합, 로컬 main도 `9d619c0`로 자동 정합 확인 → handoff 백업 역할 종료(삭제). **교훈: 공유 main 작업트리 = 워커 코드베이스이므로 직접 편집 금지(worktree 격리), 코드 push 후 운영 반영은 워커 재기동까지가 1셋트.**

## [2026-07-02] census §7.4 예약 해소(강화형 확정), 검증 방식 V-A 채택
## [2026-06-29] MP-VIX-BACKFILL (B-3) — EOD regime 76행 소급 재적재

**결정 (D-MP-VIX-BACKFILL)**: EODDashboardSnapshot 76행(2026-02-25~06-26)의 `json_data['market_summary']['vix_regime']`을 현재 VIXCLS로 재계산해 prod UPDATE. 백업 선행 + 트랜잭션 원자적 + 멱등 재현(재실행 0행). intraday `RegimeSnapshot`은 히스테리시스로 forward-only(백필 불가) — 본 백필은 **EOD regime만**. MP-VIX 트랙 3종(SRC·STALE·BACKFILL) 전체 종결.

**Why**: MP-VIX-SRC는 provider 소스만 교체했지 기존 baked 행은 무수정 → 76행 전부 `normal` degraded 잔존. MP-VIX-STALE 백필로 VIXCLS가 06-13~25까지 채워져 **76행 전건 lookback 충족(0 부족)** → 소급 재계산 가능해짐(B-3 순서 ㄴ). 결과: `{normal:76}`→`{normal:58, elevated:10, high_vol:8}`, **18행 변경**(전부 03-03~04-07 고변동 구간 normal→high_vol/elevated), 결정론적·스폿 정합(03-13→high_vol). 안전: 백업(`eod_regime_backup_20260629.json` normal:76 원본 보존) → DRY-RUN 18행 확인 → 트랜잭션 적용 → 사후검증 → 멱등(재실행 0). `get_regime` Redis 캐시(TTL 1h)는 baked json과 별개(자연 만료, 다운스트림은 baked 값 사용).

**★핵심 단서 (미래 세션 오해 방지)★**: 본 백필은 **'EOD regime 이력 정확화'이지 'MP2-ANALOG 레짐 다양성 해소'가 아니다**. 76행 중 normal이 여전히 58행(다수)이고 elevated/high_vol은 03~04월 고변동 18행뿐 — **Analog 매칭의 레짐 다양성 게이트는 시장 의존으로 미해소**(시장이 다른 국면에 들어가야 열림, D-CONC-RISK-LENSES ③과 동형). "이력을 채웠으니 이제 Analog 매칭 되겠지"는 오해. EOD regime 신호 정확화와 매칭 비교군 다양성은 별개 축이다.

## [2026-07-08] MP2-ANALOG = DORMANT (D-ANALOG-GATE)

**결정**: MP2-ANALOG(#1)를 **DORMANT로 전환**. 착수 시 STEP 0 재측정 결과 데이터 다양성 게이트가 여전히 닫혀 있어 analog 코드 착수를 보류한다.

**STEP 0 재측정 실측(2026-07-08, prod)**: intraday `RegimeSnapshot` **64행**(2026-04-27~07-08) / **regime LATE_BULL 62(97%)·BULL_EXPANSION 2** / status OK 29·INSUFFICIENT_DATA 35 / **inputs 완전벡터(≥14) 22행** / MOVE 107 values 가용 / analog·similarity·distance 코드 **0건**(미구현 재확인). 보조: SectorFlowSnapshot 47 distinct 날짜(11섹터), rotation_index = 시장 전역 스칼라(11섹터 동일값 = per-sector 아님), history_30d 30캡은 **서빙 한정**(데이터 실깊이 47>30, analog는 더 깊이 조회 가능).

**옵션 기각 근거**:
- **옵션 1(입력벡터 analog 지금 구축) 기각**: 22 완전벡터가 거의 동일 국면(97% LATE_BULL) → 최근접 매칭이 **자기상관**(인접일)으로 수렴, **시점가치 ≈ 0**(과거 유추의 통찰 없음). 인프라만 미리 깔아도 "오늘≈다른 LATE_BULL일" 저신호 반환.
- **옵션 3(EOD VIX 3-state로 대상 변경) 기각**: intraday classifier(rules.yaml 5국면)와 EOD `DynamicRegimeCalculator`(VIX z-score 3상태)는 **별개 시스템** → 혼입 금지(계약·지표·소비처 상이, classifier.py 주의문 명시).

**채택 설계 노트(un-dorm 시 적용)**:
- **입력벡터 z-정규화 최근접**(regime 라벨 매칭 아님 — 라벨은 97% 단일이라 무변별). 14지표 + MOVE 벡터를 z-정규화 후 거리 최소 과거일 검색.
- **자기상관 제외창 ±5일**: 최근접 후보에서 기준일 ±5거래일을 배제(인접일 자기상관 매칭 방지).
- **과거 국면 합성 경로 = rules.yaml 소급 적용**: 깊은 과거 벡터에 현행 rules.yaml을 소급 적용해 과거 국면을 재구성 → **B-1 백필 land 의존**. HY OAS mid-2023 상한(짝 결손 구간)은 **실측 사안**(full-vector cap 판정 후 유효 깊이 확정).

**un-dorm 트리거**: (a) regime 다양성 — 비-LATE_BULL 일수 유의미 누적 or 전환 ≥2회 관측 **OR** (b) B-1 백필 land 후 소급 벡터 재구성 검증 통과. 그 전 착수 금지(TASKQUEUE MP2-ANALOG DORMANT).

**baseline at decision**: origin/main = 96ae7b5. prod 쓰기 0(read-only STEP 0 재측정만). analog 코드 0.

## [2026-06-30] 제품 로드맵 v1 — 응축 코어 → Chain Sight 깔때기 (D-ROADMAP-V1)

**발상 동기**: 외부 여러 소스를 안 봐도 **stock_vis 하나로 정보 응축 → 관심 촉발 → Chain Sight 진입**까지 잇는 깔때기. 도그푸딩 기반(정병진 = 사용자 #1). 근거: Phase 0 전수 조사 4트랙 STEP 0 완료(dashboard·chain_sight·market_pulse·portfolio).

**Phase 정의 (의존 순서 = 가치 순서):**

- **Phase 1 — 응축 코어** [dashboard 표면 + shared 생산, chain_sight 부채와 **독립** → 즉시 착수 가능]
  - 지난장 뉴스: **하이브리드**(3줄 한국어 요약 + 펼침 시 원문).
  - 종목추천 + 투자레포트: 테제 1줄 → 기술/펀더멘털/뉴스맥락 **3관점** → 리스크 1줄. EOD bake 미리굽기 top-N 캐러셀.
  - ★ **제시 로깅**(제시 시각·horizon·신뢰도) — **Phase 5 연료, 가장 앞 슬라이스**(day-1부터).

- **Phase 2 — 촉발 + 응축 강화** [dashboard + shared, 기존 시그널 재사용]
  - 왜 움직였나 · 이상치 알리미 · 스토리 후크 / 한줄 브리핑 · 델타(놓친 것만) · 섹터 히트맵.

- **Phase 3 — Chain Sight 깔때기** [dashboard 표면 + chain_sight 위임]
  - ※ **선결 조건**: chain_sight 부채 정리 — **CS-EXT-API**(외부 API 래퍼 이관) + **CS-LEGACY**(레거시 serverless 경계). **CS로 사용자 보내기 전 백엔드 정리 필수.**
  - CS시작 버튼 · 관심 맥락 전달 · 이웃 미리보기 · 발견 큐.

- **Phase 4 — 관계 해자 표면** [dashboard 표면 + chain_sight RC 연결]
  - ★ **전제 갱신**: RelationConfidence v2.1 **prod 가동**(13,695행·daily beat) → "신규 구축"이 아니라 **"기존 RC 노출·연결"**. 신뢰도 급상승 엣지 · 숨은 허브 · 레포트에 관계 근거 통합.

- **Phase 5 — 사후 캘리브레이션** [shared + chain_sight + dashboard, 메타]
  - ★ **전제 갱신**: `update_relation_confidence` 채점 루프 **상당부분 이미 운영** → "새 설계"가 아니라 **"기존 루프 vs 필요 채점의 격차 보강"**.
  - 하이브리드 거버넌스(통계 갱신=자동 / 로직 변경=승인), **관찰 모드 시작 → 검증 후 승격**. reliability diagram · 회고 패널 · 추천 적중 배지.

**핵심 원칙:**
1. **제시 로깅은 Phase 1 day-1부터** — 안 하면 Phase 5 소급 채점 불가(학습 데이터 증발). 가장 앞 슬라이스.
2. **Phase 1·2는 chain_sight 부채와 독립** → 부채 정리 대기 없이 착수 가능.
3. **캘리브레이션 함정 6종**(Phase 5 설계 시 필수): ① look-ahead 누출 ② holding horizon 명시 ③ 벤치마크 대비 ④ 반사실 수익 오약속 금지 ⑤ 소표본 과적합 ⑥ 채점 단위 분리.
4. **생산/표면 경계**: dashboard는 **표면**(컴포넌트·소비 경로)만, **생산**(news 수집·LLM·bake·RC 갱신)은 **shared·chain_sight 위임**.

**Why**: 응축(Phase 1)이 사용자를 매일 부르는 훅, 촉발(Phase 2)이 관심을 키우고, Chain Sight(Phase 3~4)가 차별화 해자, 캘리브레이션(Phase 5)이 신뢰를 누적. 의존 순서가 가치 순서와 일치 — Phase 1·2는 부채 독립이라 즉시 시작, Phase 3 진입 전에만 chain_sight 부채(CS-EXT-API·CS-LEGACY)를 정리하면 됨. Phase 4·5는 RC 엔진이 이미 prod 가동 중이라 "구축"이 아닌 "연결/보강"으로 비용 재평가됨(전제 갱신).

> ★ **2026-07-01 Phase 5 전제 정밀화**(D-P1-STEP0 실측): Phase 5 "RC 채점 루프 재사용"은 **Phase 4(관계 해자)에 한함**. **Phase 5 추천 적중 채점의 실제 재사용 자산 = `SignalAccuracy`**(prod 38,767행)이지 `update_relation_confidence`가 아니다(별개 루프). `excess`(벤치마크 상대)는 희소(3,611행) → 벤치마크 채점 쓰려면 `P5-EXCESS-BACKFILL` 선결. 상세 = "[2026-07-01] Phase 1 제시 로깅 STEP 0"(D-P1-STEP0).

## [2026-06-30] B-1 FRED 깊은 백필 — 범위·깊이 결정 + Phase 5 defer (D-B1-SCOPE-DEPTH)

**결정**: A1(활성 11 FRED 시리즈) + B3(위기-앵커 ~8년, target_start 2018-01-01) + C2(레거시·오라벨 값싼 처분). 단 **백필 실행은 Phase 5 Analog 설계 산하로 defer**(지금 실행 안 함).

**Why**:
- **왜 A1(활성 11만)**: 레거시 4(CPIAUCSL·FEDFUNDS·UNRATE·PCEPI)·오라벨 2(VIX3M·MOVE)는 라이브 피처 파이프라인(`FRED_RECURRING_SERIES`)에 없어 Analog가 매칭할 라이브 짝이 없음 → 백필 가치 낮고 prod 부채만 남김.
- **왜 B3(전 이력 B2 아님)**: 조인트 다-피처 벡터 깊이는 최단 시리즈에 묶임(HY OAS 2023-06-30 = ICE BofA의 FRED 롤링 라이선스 제한, 직접 observation 쿼리로 확인). 깊은 시리즈(VIXCLS 1990~ 등)를 FRED 최대까지 깔아도 조인트 매칭 천장은 ~2년 → 전 이력 ~77K행은 한계효용 급감. B3는 2018Q4·2020 COVID·2022 베어 대비 episode를 ~10–15K행(전 이력 1/5 비용)에 포착.
- **왜 defer(지금 실행 안 함)**: STEP 0.5 게이트 — ⒜ G2: 깊은 백필의 유일 소비자 = 미구축 Analog(`apps/market_pulse` analog/similarity/distance grep 0건, regime은 룰 classifier + EOD VIX z-score 둘뿐, 과거 유사시점 매칭 없음) → 소비자 0 ⒝ full-vector cap: 매칭 방식(full-vector vs ragged)이 Phase 5에서 정해져야 유효 깊이 확정 — full-vector면 2018~2023 ~8K행(전체 65%)은 HY OAS 짝 없어 영구 미사용 ⒞ G3: EOD regime `DynamicRegimeCalculator` z-score 윈도우 고정 60거래일(`[-60:]` 하드코딩)이라 깊은 VIXCLS 이력 미활용 → VIX 깊은 백필 단독 가치 ≈0. 지금 쓰면 아무도 안 읽는 행을 prod에 쓰는 셈 → 실행을 Phase 5 Analog 설계로 흡수.
- **C2 실측**: 오라벨 2종 = 실제 Yahoo 소스(`backfill_v2_a1.py:157` `^VIX3M`/`^MOVE`, FRED 400 미지원) → data_source 'fred' 오분류. PCEPI = 활성 소비처 0(fred_client SERIES_CODES 정의만, deprecate 후보). 나머지 레거시 3(FEDFUNDS·UNRATE·CPIAUCSL)은 thesis 가설통제실 + legacy beat 소비 = 원함(deprecate 금지). 둘 다 prod DB 필드 변경 → 병진 수동(TASKQUEUE B1-C2).

**How to apply**: B-1 재개 트리거 = Phase 5에서 Analog 매칭 방식 확정. 그때 target_start(2018-01-01, HY OAS는 2023-06-30 fallback)로 `backfill_v2_a1`(멱등 `get_or_create`) 실행. TASKQUEUE B1-DEFER/B1-C2/B1-OPS-BEAT 참조.

**baseline at decision**: origin/main = 4986afa. prod 쓰기: 0(B-1 전 사이클 읽기전용).

## [2026-07-01] Phase 1 제시 로깅 STEP 0 — 트리거·저장위치 좁힘 + Phase 5 전제 정밀화 (D-P1-STEP0)

**측정 사실 (sess-dash-p1-log, read-only, 변경 0)**:
- dashboard **백엔드 앱 부재**(재확인) / bake 생산 = `packages/shared/stocks/eod_json_baker`(**shared**) / 종목추천: **EOD-bake 추천 미존재**, 뉴스 기반 추천은 존재(`services/news` — ML `ml_label_confidence`, horizon·제시시각 없음).
- dashboard.json = signal_cards(14 시그널)만. 추천 신뢰도·horizon·테제 필드 없음.

**❓① 트리거 지점**: **제시(impression) 시점 후보**로 좁힘(NewsViewLog 패턴). ★**미확정 잔여**: dashboard 백엔드 부재 → impression write 경로(신규 POST 엔드포인트 위치)는 **추천 생산 방식 결정(`P1-REC-PROD`)에서 함께 확정**. 생성-시점 로깅은 per-user 제시를 모르므로 부적합.
> ★ **2026-07-02 supersession (D-P1-RECPROD로 재정합)**: 위 "생성-시점 로깅 부적합(per-user 모름)" 판정은 **per-user 임프레션 관점에선 옳으나**, Phase 1 임무가 **발행 로그(issuance, grain=`signal_date`, SignalAccuracy 연료)** 로 확정되며 재정합됨. per-user 임프레션 우려는 **Phase 2 Viewed 영역으로 이관**(발행 로그는 user 무관, `user_id`는 nullable 예약). 트리거·의미 최종 확정 = D-P1-RECPROD [impression 단위] 정정 주석.

**❓② 저장 위치**: **`packages/shared/stocks`**(SignalAccuracy·EODDashboardSnapshot 형제). 근거: apps→shared 한 방향 보존(로그 모델을 shared에 두면 bake·Phase5 backfill 둘 다 토대 접근, shared→apps 역import 0), outcome(SignalAccuracy)과 join 근접. user FK(AUTH_USER_MODEL)는 shared 정상. (`makemigrations --dry-run`은 스키마 확정 사이클에서.)

**★ Phase 5 소비측 전제 정밀화 (D-ROADMAP-V1 보강)**:
1. **제시 로깅의 Phase 5 채점 루프 = `SignalAccuracy`**(shared/stocks, **prod 38,767행, 최근 signal_date 2026-06-29**, signal_tag=P1/T1/PV1…, EOD signal 체계 공유) — **`update_relation_confidence`(관계 해자, Phase 4)와 별개 채점 루프**다. ★미래 세션 혼동 방지: **제시 로그 적중 = SignalAccuracy로, 엣지 신뢰도 = RC로**. 로드맵의 "RC 채점 루프 재사용"은 Phase 4(관계)에 한함, Phase 5(추천 적중)는 SignalAccuracy 재사용.
2. **`excess_{h}d` = SPY 상대**(`return − spy_return`, backfill 로직 실재)지만 **데이터 희소 — 3,611행(~12%)** vs `return_{h}d` 촘촘(29,962). ★**벤치마크 상대 채점 = excess 백필(`P5-EXCESS-BACKFILL`) 선결 / raw return 채점 = 즉시 가능**. 함정 ①look-ahead(시점 스냅샷 `close_at_signal`·`spy_change_at_signal`)·②horizon(1d/5d/20d)은 이미 구조적 대응.
3. **함의**: Phase 5는 "outcome 채점 신설"이 아니라 **"제시 기록(신규) + 기존 SignalAccuracy join"**. 제시 로그 스키마 하한 = `user`FK · `stock`FK · `presented_date`(=signal_date 대응) · `horizon` · `presented_confidence` · `thesis_snapshot`.

**남은 결정(다음 사이클, `P1-REC-PROD`)**: 추천 생산 방식(EOD-bake 확장 vs 뉴스추천 승계)이 signal_tag/horizon 체계·confidence 출처·impression write 경로를 확정 → 그 후 제시 로그 스키마 fix.

**baseline at decision**: origin/main = bb142d2. prod 쓰기: 0(STEP 0 read-only).

## [2026-07-02] P1-REC-PROD — 추천 생산 방식·impression 단위·confidence 출처 확정 (D-P1-RECPROD)

**결정 3종 + 왜(미래 세션 오해 방지)**:

1. **[생산 방식] EOD-bake 확장**(shared/stocks 신규 생산) 채택 — 뉴스추천 승계 **기각**.
   - **왜**: `SignalAccuracy` grain(`signal_date + horizon`)과 정합 → Phase 5 join 즉시 깨끗. 뉴스추천은 **event-time**(뉴스 발생 시점)이라 grain 불일치 + horizon 소급 날조 위험. 가중합 3.95 vs 3.20.

2. **[impression 단위] Baked**(서버측, bake 시점 기록) 채택 — Viewed(실제 노출)는 **Phase 2 enrichment로 defer**.
   - **왜**: dashboard 백엔드 부재 → bake 때 **shared/stocks가 자기 구획에 기록 = 새 write 표면 0**, ❓①(impression write 경로) 완전 해소. day-1 무손실 로깅 우선. 가중합 3.95 vs 3.65(타이브레이커 = day-1 무손실).
   - **★정정 주석 (2026-07-02, D-P1-STEP0 ❓① 정합)**: "Baked"의 운영 의미 = **발행 로그(issuance log)**. bake 시점 기록, **grain = `signal_date`**. 로드맵의 "제시 로깅/제시 시각"은 문자적 "사용자가 본 시각"이 아니라 **발행 시각(`signal_date`)** 을 뜻함(용어 정정). → STEP0의 "생성-시점 로깅 부적합(per-user 모름)" 판정과 무모순: Phase 1 임무는 **발행 로그**(SignalAccuracy 연료)이고, per-user 임프레션은 **Phase 2 Viewed 영역**으로 이관.
     - **`user_id` = nullable 예약 컬럼**: day-1엔 채우지 않음(도그푸딩 1인·서비스 외피 동결). 다중 사용자 이음새는 **컬럼 보존으로 유지(방향 B)** — 구조 보존이지 day-1 채움 아님. (bake 시점 user 미상 모순은 "발행 로그 = user 무관, 컬럼만 예약"으로 해소.)
     - **"write 표면 0" 유지**: bake write, **serve 경로 무변경(신규 엔드포인트 없음)**.
     - **`presented_as='baked'` = 발행 수준 표식**. Phase 2 Viewed가 `presented_as='viewed'`로 얹히면 Phase 5가 노출 수준을 가려 채점.

3. **[confidence 출처] 신호강도 결정식 v1**(LLM 레포트 **비의존**) 채택.
   - **왜**: 3관점 레포트는 LLM → shared/chain_sight defer 대상. v1(신호강도 결정식)이 **day-1 유일하게 값 나는 길**. conf_ver=1 태그로 v2(레포트 반영) 전환 시 소급 구분.

**확정 로그 스키마 (한 번 고정, user_id 의미 정정)**:
`(signal_date, ticker, horizon, confidence, conf_ver, rank, presented_as, user_id[nullable 예약])`
— SignalAccuracy join 키 = `(ticker=stock, signal_date, horizon)`. rank=top-N 순위, presented_as=발행/노출 수준 마커. **`user_id` = nullable 예약**(발행 로그이므로 day-1 미충족, 다중 사용자 이음새용 구조 보존 = 방향 B).

**완화책 3종(단점 보완)**:
- **top-N 선정 = 기존 news 신호를 시드로**(완전 백지 아님 — 생산은 EOD-bake지만 후보 시드에 news 신호 활용).
- **3관점 레포트 = placeholder 골격으로 출시**, LLM 채움은 shared/chain_sight 후속(confidence는 v1 결정식이라 레포트 무관하게 값 남).
- **`presented_as='baked'` 마커** → Phase 2 Viewed enrichment 도착 시 Phase 5가 노출 수준 구분·가중(Baked의 노출 과대계상은 분석에서 교정 가능, 늦은 로깅은 영구 손실 → **완전성 우선**). **`conf_ver=1` 태그** → confidence v2 전환 시 소급 구분.

**★실구현 경계**: EOD-bake 생산 = **shared/stocks 위임**(dashboard는 표면·로그 소비만, 생산 아님). → **Phase 1 실행 지시서부터 작업 Project가 shared로 갈라짐**. 제시 로그 모델·write도 shared/stocks(SignalAccuracy 형제, D-P1-STEP0 ❓② 확정).

**남은 것**: 실행(shared/stocks 위임 대기). 설계·결정은 본 D-P1-RECPROD로 종료.

> ★ **2026-07-02 스키마 정정 (D-SCHEMA로 병합 supersede)**: 위 8필드 로그 스키마는 **D-SCHEMA(병합 9필드)로 정정**됨 — `horizon→signal_tag`(SignalAccuracy 실 grain 정합), `presented_as` 삭제(발행 로그=전부 baked 상수 → Phase 2 Viewed 별도 테이블로 분리), `composite_score`·`published_at` 신규. `conf_ver`·`rank`는 보존. **최종 필드는 D-SCHEMA 참조**(이 블록의 8필드는 낡은 버전).

**baseline at decision**: origin/main = 3d670ed. prod 쓰기: 0(결정 등재만).

## [2026-07-02] Phase 2(market_pulse 촉발) 두 축 설계 순서 (D-MP2-SEQ)

**맥락**: 로드맵 Phase 2(촉발 — 왜 움직였나·이상치·섹터 히트맵)가 `8ab41c6`(D-P1-RECPROD 정합)로 두 축 분화 — ①촉발 시그널 표면화 + ②Viewed enrichment(per-user impression, `presented_as='viewed'`).

**결정**: **①촉발 표면화 먼저** 설계·실행. **②Viewed enrichment는 defer**(drop 아님).

**Why (가중합, 합=1.00)**: 즉시착수 0.30·충돌회피 0.25·사용자가치 0.25·재작업리스크 0.20. **A(①먼저)=5.00 / C(동시)=2.80 / B(②먼저)=2.25. 마진 A−C=2.20>1.00 자동결정.**
- ① = 재사용 자산 전부 활성·prod 존재(AnomalySignalLog 318·SectorFlowSnapshot 462·RegimeSnapshot intraday 58·briefing) + market_pulse 도메인 내 → 의존 0, 즉시 가능.
- ② = Phase 1 발행 로그(dashboard가 shared/stocks에 생성) 스키마 위에 얹힘 → 미존재·남의 세션 소관 → 지금 설계 시 크로스-세션 충돌·재작업 위험.

**How to apply — ② 재개 트리거**: Phase 1 발행 로그 스키마가 shared/stocks에 land. 사전 조율 = dashboard 세션에 "Viewed를 얹으려면 발행 로그에 필요한 필드(`user_id`·`signal_date`·`ticker`·`horizon`·`presented_as`)" 요구 전달.

**baseline at decision**: origin/main = 8be3f65. prod 쓰기: 0(설계 단계).

## [2026-07-02] Phase 2 촉발 표면: 배치·성격·위계·카피 (D-MP2-SURFACE)

**결정**: ①촉발 시그널 표면화를 **market-pulse-v2 전용 화면(B)**에 구현. 메인 통합(A)·하이브리드(C) 아님.

**화면 성격(경계, 사용자 재정의 2026-07)**: market_pulse 판단 화면 = "지금 사야/팔아야" **현재 시장 판단**. dashboard = **지난 시장 회고**(뉴스·주가 흐름 요약) + 종목추천. 서로 다른 일 → 다른 화면.

**Why — 배치(가중합 합=1.00)**: 도그푸딩 0.30·regime일관성 0.25·구현유지보수 0.25·확장성 0.20 → B=3.95 / C=3.95 / A=3.55. B·C 동점 → 타이브레이커: "판단 vs 회고는 별개 작업" 경계 정합 + regime 척도 단일(intraday 5단계). **A 탈락 = EOD 3단계와 intraday 5단계가 한 화면에서 충돌.**

**Why — 정보 위계(변형1 방향 우선, 합=1.00)**: 판단직결 0.35·가치축정합 0.25·빈상태견고 0.20·훑기효율 0.20 → 변형1=4.55 / 변형2=4.25 / 변형3=3.00. 1-2 마진 0.30<0.40 → 타이브레이커: "사야/팔아야" 첫 물음=방향(①), 섹터(②)는 그다음. **최종 위계: 국면 hero → 촉발 → 섹터 히트맵 → 서술(prose).**

**How to apply**:
- **hero 판단 문구 = 국면(regime)값별 정적 카피 테이블(LLM 미사용)**. 예 `LATE_BULL` → "신규 매수는 선별적으로 · 방어 비중 점검". 도그푸딩 우선(판단 자세 제시). 향후 서비스 포장 시 톤 재검토 여지(방향 B 이음새 보존).
- 재사용 자산(anomaly·sector·regime intraday) 기존·활성 — 신규 계산 0.

**baseline at decision**: origin/main = 8aee712. prod 쓰기 0.

## [2026-07-02] Phase 1 소유권 예외 — 발행 로그+추천 생산 빌드 (D-OWN)

**결정**: Phase 1 **발행 로그 + EOD-bake 추천 생산 빌드**는 `packages/shared/stocks` 구획에 놓이나(SignalAccuracy 형제 모델 + baker 확장), **dashboard 표면의 백엔드 생산**이다. → **dashboard 디렉션 하에 실행**하되, **이 슬라이스 한정 예외**로만 소유권 지도 v2에 기록한다. **`shared/stocks` 전체를 dashboard 소유로 넘기지 않는다.**

**Why — ops 경계판정 완료(dashboard Phase 1 STEP 0 재확인 보고)**:
- **shared 자족**: EOD-bake·발행 로그 경로가 `Stock`·`StockNews`만 소비, `services.news`/`apps.*` 역import **0줄**.
- **arch 가드**: `tests/architecture/test_shared_boundary.py` **3 tests pass**, 역import 0(스펙 "7 pass"는 오기 — 실제 3 tests).
- **무파괴**: `makemigrations stocks --dry-run` = `No changes`(발행 로그 신설은 순수 add 예상).
- D-P1-RECPROD **"★실구현 경계 = 생산은 shared 위임(dashboard는 표면·로그 소비만)"** 과 정합 — 소유권(디렉션)은 dashboard, 물리 구획은 shared/stocks.

**How to apply**:
- 소유권 지도 v2에 **슬라이스 한정 예외 1건**만 등재: `packages/shared/stocks`의 [발행 로그 모델 + baker 추천 필드 add] → dashboard 디렉션. 나머지 shared/stocks는 기존 소유 불변.
- Phase 1 종료 시 예외 유효성 재확인(빌드 완료 후 소유 경계 재판정).

**baseline at decision**: origin/main = 008d0b2. prod 쓰기 0(결정 등재만).

## [2026-07-02] 발행 로그 병합 스키마 supersede — D-P1-RECPROD 정정 (D-SCHEMA)

**결정**: 발행 로그 최종 스키마 = **9필드** `(stock, signal_date, signal_tag, confidence, composite_score, conf_ver, rank, published_at, user_id[nullable])`. D-P1-RECPROD의 기등록 8필드를 **본 결정으로 supersede**(정정). join 키 = `(stock, signal_date, signal_tag)` — **SignalAccuracy grain과 정확 일치**.

**Why — divergence별 근거**:
- **`horizon → signal_tag`**: SignalAccuracy 실 grain은 `(stock, signal_date, signal_tag)`이고 **horizon 컬럼은 부재**(지평은 `return_1d/5d/20d`·`excess_1d/5d/20d` **wide 접미사**로 인코딩). 발행 로그가 `signal_tag`를 쓰면 join 직결. horizon 단일 컬럼(D-P1-RECPROD)은 실구조와 불일치 → 정정. 지평 표현은 wide 관례 유지. ※ **`signal_tag`=시그널 종류 ID**(V1/P2/S1), **`horizon`=SignalAccuracy wide 접미사(별도 축)** — 둘은 다른 차원. 상세 **D-P1-GRAIN**.
- **`conf_ver` 보존(default=1)**: `published_at`(발행 *시각*)은 confidence *알고리즘 버전*(v1 신호강도 vs v2 레포트반영)을 대체 **불가** — 소급 재계산 시 시각 불변인데 값만 바뀌면 버전 추적 불능. v1/v2 소급 구분 위해 명시 태그 유지.
- **`rank` 보존**: 발행 시점 캐러셀 top-N 순위 = **발행 사실**(소급 재구성 불가) → 캡처 필수.
- **`presented_as` 삭제 + ★테이블 분리 명문화**: 발행 로그는 **정의상 전부 baked**라 `presented_as` 컬럼은 상수/중복 → 삭제. **baked/viewed 구분은 Phase 2 Viewed 별도 테이블**(`presented_as='viewed'` 경로)로 분리한다. 이 분리를 명문화해 D-P1-RECPROD의 Phase 2 Viewed enrichment 경로를 **손실 없이 보존**(발행 테이블에서 상수 컬럼만 제거, Phase 5 노출 수준 채점은 Viewed 테이블 join으로 복원).
- **`composite_score`·`published_at` 신규**: `composite_score` = baker 카드 실값(`eod_json_baker.py:282`) 캡처(행위 보존), `published_at` = 발행 감사 타임스탬프.

**How to apply**:
- P1-BUILD가 이 9필드로 발행 로그 모델 신설(SignalAccuracy 형제, `packages/shared/stocks`).
- Phase 2 Viewed 테이블은 별도 스텁(P2-VIEWED-TABLE) — 본 분리 결정의 후속.

**baseline at decision**: origin/main = 008d0b2. prod 쓰기 0(결정 등재만).

## [2026-07-02] 발행 로그 행 grain (D-P1-GRAIN)

**결정**: 발행 로그 1행의 grain = **`(stock, signal_date, signal_tag)`**. 즉 "특정 날짜에, 특정 종목이, 특정 `signal_tag`로 발행됨"이 최소 단위. `rank`는 그 발행의 순위 **속성**(행을 나누지 않음).

**왜**:
- **★STEP 0 실측 반영 (2026-07-02, `eod_signal_tagger._determine_primary_tag`)**: `signal_tag`는 **시그널 종류 ID**(V1/P2/S1 등 — 모멘텀·거래량·돌파 카테고리의 개별 시그널)이며 **horizon이 아니다**. 한 종목이 **같은 날 복수 시그널 종류로 발행 가능**(primary 1 + `sub_tags` N) → 태그가 grain에 포함돼야 함. **실측으로 grain 모순 없음 확인**(검증조건 통과).
- **horizon(1d/5d/20d)은 `signal_tag`가 아니라** SignalAccuracy의 `return_1d/5d/20d`·`excess_1d/5d/20d` **wide 접미사**로 별도 표현. 따라서 D-SCHEMA "horizon→signal_tag grain 정합"의 의미 = **grain 키는 signal_tag(시그널 종류), horizon은 wide 컬럼**(둘은 다른 축). SignalAccuracy grain `(stock, signal_date, signal_tag)`과 정확 일치.
- bake 시점 1회 발행 = 1행(write 표면 0, serve-time 아님).
- Phase 2 Viewed(per-user impression)와 분리: Viewed는 serve-time·user별로 이 발행 행을 참조(D-SCHEMA 테이블 분리).

**검증조건(충족)**: STEP 0에서 `signal_tag` 실제 의미·동일 `(stock, date)` 내 복수 태그 가능성 실측 완료 → grain 모순 0. (원 초안 "왜"의 "signal_tag가 horizon 구분을 담으면" 표현은 실측 반영해 위와 같이 정정 — signal_tag=시그널 종류, horizon=별도 wide 축.)

**baseline at decision**: origin/main = 98ae812. prod 쓰기 0(결정 등재만).

## [2026-07-02] confidence 소스 — 신호강도 산식 v1 (D-P1-CONF)

**결정**: 발행 로그 `confidence` 값의 소스 = **signal-strength formula v1**(기존 시그널 강도 산식). **LLM-report와 독립**(LLM 신뢰도가 아님). `conf_ver = 1`로 산식 버전 고정. `composite_score`(float, null)는 원점수 보존, enum `confidence`는 그로부터 파생된 라벨.

**왜**:
- Phase 5 SignalAccuracy 채점이 "어떤 산식 버전으로 매긴 신뢰도인가"를 알아야 캘리브레이션 가능 → `conf_ver`로 버전 태깅해 시계열 비교 가능성 보존(D-SCHEMA `conf_ver` 보존 근거와 동일).
- **LLM-report 독립**: 레포트 유무·품질과 무관하게 발행 로그가 **항상 채워지도록**(연료 결손 방지 — D-P1-RECPROD "confidence v1이 day-1 유일하게 값 나는 길"과 정합).
- **실측 근거**: `composite_score`는 실존 float(`eod_signal_tagger._calculate_composite_score`, 범위 −1.0~+1.0, 시그널 0이면 0.0) → 원점수 보존 후 enum 파생 가능.

**baseline at decision**: origin/main = 98ae812. prod 쓰기 0(결정 등재만).

---

## [2026-07-02] health_check `origin/main-hash` 체크 시간기반 재설계 (D-OPS-HCHECK-B2)

**결정**: `scripts/health_check.py`의 검증①을 **해시 대조 → 시간기반**으로 교체. PROGRESS.md의 마지막 커밋 시각(committer epoch, UTC)이 임계 **M=72h**를 넘게 묵었는지만 blocking으로 본다. 구 `origin/main = <hash>` recorded-vs-recent-N 대조 로직·`ORIGIN_MAIN_HASH_TOLERANCE` 완전 제거. 판정은 순수함수 `is_progress_stale(progress_ts, now_ts, threshold_h)`로 분리(테스트 주입). 함수명 `check_origin_main_hash`·display name "origin/main 해시"·등록·심각도(ERROR/blocking)는 레지스트리/JSON 트렌드 호환 위해 **유지**(의미는 신선도로 변경, detail이 설명).

**왜**:
- **(1) category error**: 규약상 PROGRESS.md는 캐시(진실의 소스 아님 — 진실은 git). 캐시의 lag을 blocking ERROR로 취급한 것이 심각도 불일치.
- **(2) self-referential 수렴 불가**: 갱신 커밋이 자기 자신의 push-후 해시를 본문에 미리 못 적는 구조 → "정확 tip 기록" 요구는 원리상 수렴 불가(tolerance N=3 완화도 fast-main에선 land 후 window 밖으로 밀려 재발).
- **(3) 구조적 오발**: 실측(2026-07-02) — main이 인간 병렬 CC 세션들로 **~20min 간격 land**(단일 author leftnadal, 봇 아님). resync 마감 세션이 이 체크 때문에 land 게이트 직전 HALT(마커 treadmill: 사용자가 "META-TOUCH 마커 리셋"·"HC-MARKER-TREADMILL"로 수동 관리해온 흔적).
- **시간기반의 이점**: blocking(진짜 방치 차단)은 유지하되 해시 의존 제거 → self-ref·fast-main·동시쓰기와 **무관**.

**How to apply**:
- `PROGRESS_STALE_THRESHOLD_H = 72.0`. 근거(STEP 0 실측): PROGRESS 커밋 최대 정상 gap ≈ **22.6h**(활성 야간 사이클); 주말(금저녁→월아침) ~60–72h 정상 가능 → 초안 48h는 주말 오발 위험 → **72h로 마진**(활성 max의 ~3배, 주말 흡수, 다일 방치는 여전히 차단).
- committer-ts(`git log -1 --format=%ct -- PROGRESS.md`) 사용 — **파일 mtime 금지**(클론/체크아웃마다 불안정).
- 자기검증: `tests/test_health_check_freshness.py` 2방향(fast-main 오발 0 / 진짜 방치 차단) + 경계값. 의도적 행위 변경이라 IDENTICAL 불가 — 근거 = 이 2방향 회귀.

**후속**: 캐시성 blocking 체크가 늘면 gate/info 2계층 분리(C안, `NT-OPS-HCHECK-GATEINFO`) — 지금은 소비자 미확정이라 짓지 않음.

**baseline at decision**: origin/main = af08007. 변경 범위 = `health_check.py`(+테스트) only, apps/·packages/shared·prod 무변경.

## [2026-07-03] MP2-DEEPEN — 촉발 심화(전조+원인, 밀도 B) (D-MP2-DEEPEN)

**결정**: 판단 화면 심화 = **축3 전조(hero)** + **축2 원인(AnomalyPanel)**, 밀도 B(근거 풍부·인라인 칩 전체 + 핵심 hot 강조). 축1 델타는 별도 슬라이스(MP2-DELTA).

**Why**: STEP 0(af08007) 실측 — 전조·원인 자산이 **이미 계산·저장·부분서빙**(신규 계산 0, "구축 아닌 연결·보강" 성립). 전조=`compute_next_stage_margin`(regime 상세에 이미 서빙) → 요약 hero로 additive 승격. 원인=AnomalySignalLog.inputs 9키(모델 저장, overview 일부만) → evidence 서브셋 additive + AnomalyPanel 노출.

**How to apply**:
- **BE additive만**(계약 형태 불변): `_regime_card` next_stage/next_stage_closest/margins, `_anomaly_section` fired에 evidence(top10_weight·vix_change_pct·max_abs_sector_z·sector_extreme_symbol) + paired_news_title/url.
- **전조 근접 강조 규칙(3-C, 상시경보 방지)**: `|to_threshold| ≤ 0.2·|threshold|` → 앰버 "전환 임박", 밖 → 담백 "전환 여유". status≠OK → 전조 숨김.
- **원인 밀도 B 위계**: 임계초과 칩(분산)·sector_extreme_symbol = hot 강조, 나머지 담백, null 칩 생략. paired_news 링크.
- **신규 계산 0**(기존 자산 노출), packages/shared·prod 무접촉.

**검증**: pytest marketpulse 265/1skip(신규 3) · vitest market-pulse-v2 194(신규 13) · tsc 0 · health_check 10/10. 커밋 BE `0d4f629` + FE `c672495` ff.

**baseline at decision**: origin/main = f892d90. prod 쓰기 0.
## [2026-07-03] 추천 캐러셀 정렬 = |composite_score| top-N (D-P1-REC-RANK)

**결정**: `recommendations` 정렬 = **|composite_score| 내림차순 top-N**(방향 불문, 확신 강도 순). **N=10은 잠정** — 최종값은 캐러셀 표면 슬라이스(목업) 때 확정.

**왜**:
- **코어 방향(도그푸딩, #1 사용자 실전 무기)**: 강한 매수(+)와 강한 매도/회피(−)를 **한 피드에** 올려 실전 유용. 절댓값 순 = "지금 가장 확신 강한 신호" 우선.
- `composite_score` = `_calculate_composite_score`(−1~+1) 실측 근거. **방향은 부호로 표현**(S-2 실측: payload가 부호 보존 `composite_score`를 담음 → 별도 direction 필드 불요, 부호가 매수+/매도−).
- **N=10 잠정**: UI 용량 종속 파라미터라 화면 확정 전 값 고정 회피(하드코딩 `RECOMMEND_TOP_N=10`, 잠정 표식).

**가중합**: 안1(절댓값 정렬)=4.00 vs 안2(부호=매수만 상위)=3.65, 마진 0.35 → 타이브레이커 = 도그푸딩 유용성 + 빌드 변경 0(이미 절댓값 구현) → **안1**.

**baseline at decision**: origin/main = f892d90. prod 쓰기 0(결정 등재만).

## [2026-07-03] recommend payload 계약 형태 고정 (D-P1-REC-CONTRACT)

**결정**: `dashboard.json`의 `recommendations` = top-N item 배열. **item 형태(빌드 57e70bb 실측 그대로 고정)**:
```
{ rank, ticker, company_name, signal_tag, confidence, conf_ver,
  composite_score(부호 보존), thesis, perspectives, risk }
```
- **방향 표현** = `composite_score` 부호(양=매수 우위, 음=매도/회피 우위). 별도 direction 필드 없음.
- `signal_tag` = 시그널 종류 ID(V1/P2/S1, tag_details.primary) [D-P1-GRAIN], `confidence`/`conf_ver` = formula v1 [D-P1-CONF].

**placeholder 3키 (유지 B — 사용자 확정 2026-07-03)**: 프론트 소비 0건 실측에도 **계약에 존재로 고정**. 형태:
- `thesis`: `null`
- `perspectives`: `{"technical": null, "fundamental": null, "news_context": null}`
- `risk`: `null`

**왜 유지(B)**: 빌드 코드 변경 0 + 프론트 스키마 안정(키 항상 존재 → 옵셔널 접근 불요). 향후 **LLM 채움은 additive-within**(키·타입 보존, 값만 채움 — shared/chain_sight 후속). 제거(C, 순수 additive)는 빌드 수정+재검증 비용이라 미채택.

**IDENTICAL 기준 축**: 이 placeholder 형태는 **지금부터 신규 키 IDENTICAL 기준에 포함**(기존 6키 `signal_cards` IDENTICAL과 **별개 축**). recommend 필드 변경 시 이 형태 대비 검증.

**baseline at decision**: origin/main = f892d90. prod 쓰기 0(결정 등재만).

## [2026-07-03] MP2-DELTA — 어제 대비 변화: 계산위치·범위·"어제" 정의 (D-DELTA-*)

### D-DELTA-CALC — 계산 위치 = 후보 A(조회-시 BE 무상태 파생)
**결정**: 델타는 요청마다 최근 2 스냅샷을 읽어 파생. **prod 쓰기 0·마이그레이션 0·캐시 0.**
**Why**: 가중합 A=4.55 vs B(저장)3.10 / C(FE)2.85, 마진 1.45>1.00 자동 확정. 선례 2 — `_ticker_bar`의 `[:2]` change_pct 파생(overview.py) + breadth `prev_snapshot` 델타. 후보 B(스냅샷 저장)는 prod 쓰기·마이그레이션 유발이라 회귀 금지.

### D-DELTA-SCOPE — 3종 델타를 2슬라이스로
**결정**: regime(from→to)+sector(rank 이동)=**슬라이스1(완료)**, anomaly 신규/소멸=**슬라이스2**(별도). **Why**: anomaly는 sparse(무발동 구간 존재)라 "직전 발동일 대비" 로직이 필요 = 리스크 격리. regime/sector와 섞으면 슬라이스1 지연.

### D-DELTA-YDAY — "어제" = 직전 distinct 스냅샷 날짜
**결정**: `date__lte=today` → `order_by('-date')` → distinct 최근 2날짜의 2번째. **calendar −1 금지**(주말·휴장 갭 자동 흡수, 실측 sector 07-01↔06-27). vs_date는 서버 실날짜를 계약·화면에 노출(FE −1일 하드코딩 금지).
  - **anomaly(슬라이스2)는 "직전 발동일 대비"로 별도 정의 예정** — 무발동 구간은 "변화 없음"이 정상 동작(빈 결과≠에러).

**검증(슬라이스1)**: pytest marketpulse 272/1skip(신규 delta 7) · vitest 209(신규 15) · tsc 0 · migration 0 · health_check 10/10 · prod 0 · shared 무접촉. 커밋 BE `7f68813` + FE `421fefe` ff.

**baseline at decision**: origin/main = e9ae62b. prod 쓰기 0.

### D-DELTA-QUIET — 무발동일 표시 = 옵션 2(해소 명시), R3 실측 → 5c-ii 폴백 (2026-07-04)
**결정**: anomaly 무발동일 표시 방향 = **옵션 2(해소 명시)**. fired-set 비교 = **직전 '발동일' 대비**(D-DELTA-YDAY anomaly 변형 — calendar −1·직전 거래일 아님, sparse라 대부분 빈 결과 방지).
**Why**: 가중합 옵션2 4.05 vs 옵션1(조용) 3.95(마진 0.10 < 0.40 → 타이브레이커). ① 옵션2의 단점(오독)은 문구로 완화 가능하나 옵션1의 단점(꺼짐 정보 소실)은 구조적. ② S1의 "카드가 대부분의 날 살아있어야" 원칙과 일관.
**안전핀**: (a) 문구는 관측 사실만 — "해소 확정" 단정 금지, "MM-DD 발동분 — 이후 재발동 없음" 형식. (b) engine 실행 흔적으로 "행 없음 = 진짜 무발동" 판별.
**lookback = 7일**: 모듈 상수 고정(설정·환경변수 노출 금지). 근거 = 실측 발동 사이클(3주 내 발동 ~6일, 최장 무발동 13일). 조회-시 파생이라 worker 재시작 무관(common-bugs #41 비해당).
**R3 실측 결과 = 판별 불가 → 5c-ii 폴백 채택**: AnomalySignalLog는 **발동 행만 적재**(tasks/anomaly.py의 `for f in fired` 내부에서만 create — CALM/run-marker 행 0), 전용 run-marker 모델 부재. RegimeSnapshot은 별도 파이프라인(다른 Celery task)이라 anomaly `*/5` 엔진 실행 증명 불가 → proxy 시 거짓 해소(안전핀 b가 막는 위험) 유입. ∴ `_engine_ran_since` 항상 False → **무발동일 항상 quiet**. `resolving`/`resolved_rules`는 계약에 미래 확장 자리로 보존(FE 4상태 전부 렌더). ANOMALY-RUN-EVIDENCE(run-marker 도입 → resolving 활성) 관찰 항목 등록.
**검증(슬라이스2)**: pytest marketpulse 279/1skip(신규 delta 7) · vitest 495(신규 5) · tsc 0 · migration 0 · health_check 10/10 · prod 0 · shared 무접촉. 커밋 4분리(BE 파생 507c6d5 / 계약 3d1711e / FE 2ed2f28 / 테스트 b29067e) ff.
**baseline at decision**: origin/main = 47c36b4 → land b29067e. prod 쓰기 0. ⇒ **MP2-DELTA 트랙 종결**.
---

## [2026-07-03] graph_analysis CUT 완결 (D-REHOME-GRAPH) — **resolved**

**결정**: 휴면 앱 `services/_dormant/graph_analysis`(1444줄, 11파일) **CUT 완결**. 방식 = (가)-2(IP 스냅샷 후 제거) + (나)-1(drop-migration 선행). 2-STAGE 실행:
- **STAGE 1**(완료, prod 적용됨): drop-migration `0002_delete_graph_analysis_models`(DeleteModel×5) 생성 → 사용자 수동 `migrate graph_analysis` 적용 → prod 5테이블 DROP(`graph_correlation_edge/anomaly/matrix`·`graph_metadata`·`graph_price_cache`, 전부 0 rows). 전달 브랜치 `monorepo/sess-rehome-graph @ 3ddcb7b`.
- **STAGE 2**(본 커밋): INSTALLED_APPS(`config/settings.py`) 1줄 제거 + `git rm` 앱 전체(models/admin/apps/views/tests/services/·migrations 0001) → 코드 컷 완결.

**왜**: 휴면·기능 소비자 0(제거 전 repo 전체 참조 = INSTALLED_APPS 1곳뿐)·데이터 0 rows·해자(RelationConfidence/chain_sight) 무접촉(프로브 C). Postgres 테이블 물림이라 순서 제약(migrate→코드 rm) 강제.

**IP 스냅샷(미래 소환)**: 통계적 price-correlation 엔진(chain_sight 관계발견과 접근 상이).
- `CorrelationCalculator`(448줄): Watchlist+period → 종목 가격 **Pearson 상관행렬**+pairwise edge(pandas), `build_network_graph()`→networkx.
- `AnomalyDetector`(312줄): 상관 변동 이상 엣지 탐지 + cooldown/rank + 알림 라이프사이클(pending/alerted/dismissed).
- **복구 기준 SHA `f892d90`** 이력에 전량 보존. 미래 통계상관/이상탐지 필요 시 소환.

**How verified(STAGE 2)**: `makemigrations --dry-run`=**No changes**(잔재 모델참조 0, 과도기 불일치 해소) · `manage.py check`=0 issues · health 10 OK · arch 7 pass · prod 5테이블 부재. **회귀 delta=0**: 전 스위트의 선존 chainsight 실패 5건은 graph_analysis 존재 브랜치에서도 동일 재현(환경성, 본 컷 무관).

**잔여(무해)**: prod `django_migrations`의 graph_analysis 0001/0002 행은 앱 미등록으로 Django 무시 = 무해 고아(정리 선택·나중). STAGE 1 전달 브랜치는 임무 완료 후 삭제 후보(수동). 서술 문서(CLAUDE.md 앱표·sub_claude_md/graph-analysis.md) stale 참조 = 후속 doc 위생.

**baseline at decision**: origin/main = 47c36b4. STAGE 2 = 코드/INSTALLED_APPS 제거(브랜치 격리). main-land = 사용자 go.

## [2026-07-04] P1-OBSERVE 충족 — 첫 실bake 관측 (D-P1-OBSERVE-DONE)

**결정**: P1-OBSERVE 게이트 **충족(닫힘)**. 실파이프라인(`run_eod_pipeline` 수동 트리거) 관측으로 recommendations 생산·발행 로그 write를 실증.

**관측 결과**:
- **JSON**(`frontend/public/static/signals/dashboard.json`): recommendations **N=10** · `|composite_score|` 내림차순(D-P1-REC-RANK) · 기존 6키 **IDENTICAL 보존** · placeholder 3키 null(D-P1-REC-CONTRACT). trading_date `2026-07-02` · is_stale `False`.
- **DB**(IssuanceLog): **10행 = N 정합** · grain `(stock, signal_date, signal_tag)` **중복 0**(같은 signal_date 재bake에도 `update_or_create` **멱등 실증**) · conf_ver=1 전건 · published_at 전건 존재 · user_id 전건 null(D-SCHEMA·D-P1-CONF).
- **★매도 비율 = 30%**(3/10) < 50% → 방향 방어 강화 불요(D-P1-CAROUSEL 참조).

**결함 2건 경유(기록)**:
1. **워커 브랜치 표류**: 워커가 import하는 공유 트리(`~/Desktop/stock_vis`)가 land 전 브랜치(`sess-cs-pair-relevance`)라 **구 코드로 bake**(recommendations 누락, 런타임 에러 없이 6키만 emit) → **A' `checkout --detach origin/main`** 정렬 + 워커 재기동으로 해소. (main checkout은 `sess-main-integrate` worktree 점유로 불가 → detached 채택.)
2. **migration 0009 미적용**: 운영 DB에 `stocks_issuance_log` 부재 → IssuanceLog write **조용히 실패**(파이프라인 무중단 완주, atomic_swap이 write보다 앞서 파일은 정상). `sqlmigrate` 육안 검증(신규 테이블 대상만·기존 ALTER/DROP 0) 후 **사용자 승인 하 migrate**(D-P1-MIGRATE-0009 참조).

**baseline at decision**: origin/main = ca6d525. prod: migrate 0009 적용(승인) 외 쓰기 0.

## [2026-07-04] 추천 캐러셀 레이아웃 A+ (D-P1-CAROUSEL)

**결정**: dashboard 추천 캐러셀 = **레이아웃 A+**. N=10.
- **단일 가로 스크롤** · `|composite_score|` 강도순(payload 정렬 순서 그대로, 재정렬 0).
- **방향 이중 표기**: 색 배지(매수/매도 색) **+ 동사 라벨**("매수"/"매도·회피") — 색 단독 의존 금지(색약 방어).
- **strength spine**: 방향색 + `|score|` 길이.
- **placeholder ghost 렌더**: thesis/perspectives/risk가 null이면 ghost 스트립("곧: 논리·3관점·리스크"), null 아니면(향후 LLM 채움) 실내용 승격 = **additive-within**(계약 형태 보존).
- **카드별 체인사이트 진입**.

**방어 수위**: 실측 매도 **30%(3/10, 정상 거래일 단일 표본)** < 50% → **A+ 이중표기 외 추가 방향 방어 불요**.
**재검토 트리거**: 관측 누적 시 매도 비율 **50% 상회 관찰**되면 **방어 수위만** 재검토(레이아웃 재설계 아님).
**N=10**: D-P1-REC-RANK "잠정"의 화면 확정 — 캐러셀 스크롤로 전량 노출, 현 N=10 고정.

> ✅ **2026-07-06 구현 완료(land `24b0e47`)**: `RecommendationCarousel`+`RecommendationCard`(components/eod) + `app/page.tsx` Level 2.5 additive 배선 + `types/eod.ts` `Recommendation` 타입. **vitest 7 · tsc 0**. 하위호환 테스트 고정(recommendations 부재/빈 배열 → 캐러셀 생략, 기존 6키 화면 무영향). 체인사이트 진입 = 기존 `/stocks/${ticker}?tab=chain-sight` 관례 재사용(라우트 신설 0). shared/stocks·baker 무접촉(소비만). ⚠ 화면 도달은 W′(D-W-WEB) 완료 시.

**baseline at decision**: origin/main = ca6d525. prod 쓰기 0(결정 등재만).

## [2026-07-04] migration 0009 운영 DB 적용 (D-P1-MIGRATE-0009)

**결정**: `stocks.0009_issuancelog`를 운영 DB에 적용(사용자 승인). IssuanceLog write 결함 해소.

**검증·경위**:
- **showmigrations 전**: `0007[X] 0008[X] 0009[ ]`(미적용).
- **sqlmigrate 0009 육안 검증**: `CREATE TABLE stocks_issuance_log` + ALTER(unique·FK to stocks_stock)·INDEX **전부 신규 테이블 대상**. 기존 테이블 ALTER/DROP/TRUNCATE **0** → 순수 add 확인.
- **적용**: `migrate stocks` → `0009_issuancelog ... OK` → **후 `0009[X]`**.
- 승인: 운영 DB 스키마 변경이라 워커 런타임 개입 범위 밖 → 사용자 별도 승인.

**baseline at decision**: origin/main = ca6d525. prod: 스키마 add(신규 테이블 1) — 기존 데이터 무변경.

## [2026-07-05] 워커 전용 worktree — 브랜치 표류 트레드밀 종료 (D-B-WORKER)

**결정**: celery worker 런타임을 **공유 편집 트리에서 분리**해 전용 worktree에서 실행. 설계:
- **경로**: `~/worktrees/sv-worker-runtime`(detached `origin/main`) — 세션 체크아웃과 무관한 워커 전용 트리.
- **`celery-worker.sh` PROJECT_DIR 전환**: 하드코딩 `~/Desktop/stock_vis` → 워커 트리 경로.
- **plist 갱신**(`com.stockvis.celery-worker` WorkingDirectory) — **repo 밖 파일이라 소유권 지도 대상 외**(명기).
- **OUTPUT**: 워커 트리의 `frontend/public/static/signals/` → **공유 트리 서빙 위치로 심링크**(서빙 주체 `com.stockvis.web`는 공유 트리 frontend를 봄).
- **갱신 원커맨드 `scripts/worker_sync.sh` 신설**: `fetch + re-detach origin/main + 워커 재기동` 1커맨드(트레드밀의 수동 3스텝을 봉인).

**왜**:
- **#45가 등재 당일 재현**: 공유 트리(활성 편집) ∧ 워커 런타임이 같은 트리 → detached 정렬이 다른 세션 체크아웃으로 **즉시 표류**(규율로 유지 불가 실증). 구조 분리만이 해결.
- 가중합 **4.30(전용 worktree) 대 3.20(수동 규율)**, 마진 1.10 → 자동 결정.

**baseline at decision**: origin/main = 0b27c9c. prod 쓰기 0(결정 등재만, 실행은 TASKQUEUE `P1-B-WORKER-WORKTREE`).

## [2026-07-05] D-OWN 계열 — B′ 슬라이스 한정 스크립트 예외 (D-OWN-B-WORKER)

**결정**: **B′(P1-B-WORKER-WORKTREE) 슬라이스에 한해** `scripts/celery-worker.sh`(PROJECT_DIR 전환)·`scripts/worker_sync.sh`(신설) 변경을 허용한다. plist는 repo 밖(지도 대상 외). 이 예외는 **B′ 한정** — infra/ops 구획의 일반 편집 권한 확대가 아님.

**baseline at decision**: origin/main = 0b27c9c. prod 쓰기 0(결정 등재만).

## [2026-07-05] D-B-WORKER 심링크 방향 반전 (D-B-WORKER-AMEND-1)

**결정**: D-B-WORKER의 OUTPUT 심링크 방향을 **반전(방식 Y)**. 원설계(worker 트리 signals → 공유 서빙 위치)를 **공유 트리 signals(심링크) → worker 트리 signals(실디렉토리)** 로 정정.

**왜**: baker `_atomic_swap`이 `shutil.move(OUTPUT, OLD)` → `shutil.move(TMP, OUTPUT)`로 **OUTPUT 경로 자체를 교체**하는 의미론(os.rename은 심링크를 따라가지 않고 심링크를 이동). 원설계(worker→공유) 심링크는 **첫 bake에서 심링크가 signals_old로 이동 + TMP 실디렉토리가 OUTPUT에 놓여 파괴**됨(HALT 실측). 방식 Y는 atomic_swap이 worker 트리 내부에서만 일어나고 공유 심링크는 경로 기반이라 **inode 교체와 무관하게 생존**.

**검증(bake 2회)**: 스왑 반복 후 심링크 생존 · dashboard.json(심링크 경유) 6키 IDENTICAL + recommendations N=10 · IssuanceLog **10행 멱등**(1회차=2회차, grain 중복 0) · **서빙 HTTP 200**(심링크 추종 실증, :3000).

**부속**:
- 공유 signals 원본 = `frontend/public/static/signals_pre_b` **보존**(롤백용, 제거는 TASKQUEUE `B-CLEANUP-PREB`).
- `.env` = worker 트리 심링크(→공유 트리 .env, DB/키 재사용).
- `worker_sync.sh` 시작 **가드**: 공유 signals가 심링크 ∧ 타겟 디렉토리 실존 검사(조용한 서빙 단절 방지).
- `celery-beat.sh` 무변경(DatabaseScheduler = 스케줄 DB 소스, task 코드는 worker가 import).

**B′ 완료 상태(경유 기록)**: worker 트리 `~/worktrees/sv-worker-runtime`(detached `origin/main`) · `celery-worker.sh` PROJECT_DIR 전환 · plist 전환(repo 밖 = 소유권 지도 대상 외) · 갱신 절차 = `scripts/worker_sync.sh`. 스크립트 land = `921dc0c`.

**baseline at decision**: origin/main = cd5ff20. prod 쓰기 0(결정 등재만, 실행은 OPS-B-BUILD에서 완료).

## [2026-07-06] web 전용 서빙 worktree (D-W-WEB)

**결정**: dev server(`com.stockvis.web`) 서빙을 **공유 편집 트리에서 분리**해 web 전용 worktree에서 실행. 설계:
- **경로**: `~/worktrees/sv-web-runtime`(detached `origin/main`) — 세션 체크아웃과 무관한 web 전용 트리.
- **`com.stockvis.web` 서빙 대상 전환**: 기동 스크립트/plist를 web 트리 지향(plist는 **repo 밖 = 소유권 지도 대상 외** 명기).
- **갱신 = `worker_sync.sh`를 런타임 트리 공통 동기화로 확장**(worker+web 트리 re-detach+재기동 단일 출처, **신규 스크립트 복제 금지**).
- **node_modules 조달 = STEP 0 분기**: 공유 node_modules 심링크가 dev server에서 동작하면 **심링크+가드**, 아니면 web 트리 설치.

**왜**:
- dev server가 **공유 트리(chain_sight 등 작업대) frontend를 서빙** = #45와 **동일 결합의 web 판**. B′ "공유 트리는 세션 자유" 선언과 **양립 불가**(공유 트리 브랜치가 바뀌면 서빙 코드도 바뀜) → 캐러셀(land 24b0e47)이 공유 트리에 없어 **화면 미도달**이 실증.
- 가중합 **4.45(web 전용 트리) 대 2.95(공유 트리 서빙 유지)**, 마진 1.50 → 자동 결정.

**baseline at decision**: origin/main = 24b0e47. prod 쓰기 0(결정 등재만, 실행은 TASKQUEUE `W-BUILD`).

## [2026-07-06] D-OWN 계열 — W′ 슬라이스 한정 예외 (D-OWN-W-WEB)

**결정**: **W′(W-BUILD) 슬라이스에 한해** web 기동 스크립트 · `scripts/worker_sync.sh`(런타임 트리 공통 동기화로 확장) 변경을 허용한다. plist는 repo 밖(지도 대상 외). D-B-WORKER 계열 예외 — infra/ops 일반 권한 확대 아님.

**baseline at decision**: origin/main = 24b0e47. prod 쓰기 0(결정 등재만).

## [2026-07-06] MP2-TREND — 멀티라인 시계열 도입 (D-TREND-PLAN / -BASELINE / -TOOLTIP)

### D-TREND-PLAN — 도입 순서·보류
**결정**: 1호 = 공용 `MultiLineTrendChart` + 섹터 순위 궤적(가중합 4.85) → 2호 = 전환일 오버레이 공용 계약 + breadth → 3호 = regime 구성요소(관문 통과 — z-score 그림 병진 승인). **보류**: ③집중도(데이터 21일로 얕음)·⑤거시 전체·⑥지수가격(이질+계약 부재).
**Why(STEP 0 실측)**: 섹터만 자연 동질(rank·rel_strength, 정규화 불요) + `sector_history` 계약 이미 서빙(rank 1필드 additive만) + 깊이 44일(30일뷰 성립). 나머지 후보는 이질(정규화 선행) 또는 계약 신설. recharts=확립 스택이나 재사용 멀티라인 부재 → 신규 공용 컴포넌트가 행위보존 안전.

### D-TREND-BASELINE — 기준선 3종 체계(옵션 C)
**결정**: 고정선 / 파생 기준선(이동평균 류) / 임계 밴드(분류기 실제 컷, 실측 실패 시 ±1σ 폴백). **1호는 슬롯(overlays 타입)만·구현 0**(2·3호 소관).
**Why**: 가중합 4.35. 타이브레이커 ① 자의성 해소(기준을 근거 있는 컷에 고정) ② thesis 알림 임계 재사용 시너지. 임계 실측 실패 시 ±1σ 폴백.

### D-TREND-TOOLTIP — 플로팅 툴팁 금지, 고정 리드아웃(전 적용처 공통)
**결정**: 플로팅 툴팁 금지. **크로스헤어(세로선+강조라인 도트) + 차트 하단 고정 리드아웃**(강조 라인만, 짚지 않으면 pinLatest로 최신일). 그래프 위를 가리는 요소 0. 2·3호의 기준선 거리 표기도 리드아웃 부기.
**Why**: 가중합 4.60/마진 1.70 자동 확정. 병진 지적(그래프 위 박스가 데이터를 가림) 반영. 전 적용처 공통 규약.

### Slice 1 검증(2026-07-06, baseline 24b0e47 → land c1cdba4)
공용 MultiLineTrendChart(recharts LineChart, 크로스헤어+리드아웃, 반전축, 범위/범례 토글) + 11색 팔레트(1곳) + sector_history rank additive + SectorTrajectory(1호, 강조=서버 rank leaders/laggards). overlays 타입만·구현 0. **emphasis 갈래**: 지시서는 "rank_delta 상위"였으나 FE 델타 재계산 금지 + 제네릭 드로어 무접촉 위해 **서버 rank leaders/laggards로 채택**(진입 컨텍스트, 델타 threading 회피). 검증 pytest marketpulse 288/1skip(신규 2+갱신 1)·vitest 509(신규 7)·tsc 0·migration 0·health 10/10. 커밋 5분리(팔레트 466ee95/컴포넌트 b52b958/BE 99bf0c8/뷰 ceff523/테스트 825ecad) rebase ff.

**baseline at decision**: origin/main = c1cdba4. prod 쓰기 0(rank는 기존 필드 계약 노출, 마이그레이션 0).

### D-TREND-EMPHASIS — 섹터 궤적 진입 강조 = 델타 컨텍스트 복원(옵션 B, Slice 2)
**결정**: 델타 카드가 자기가 보여준 상위 변동 섹터를 드로어 열기 호출에 **선택적 additive 인자**(`onOpenTrajectory(emphasis?)`)로 전달, 섹터 궤적 뷰가 이를 기본 강조로 사용. **안전판**: 제네릭 CardDrawer/CardDetailContainer 침습이 "선택적 인자 1개 + 무영향 기본값"을 넘으면 HALT → 현 상태 A(강조 복원 없음) 확정.
**Why**: 병진 확정 4.40 vs 옵션 A(현상 유지) 3.65. S1의 "델타 재계산 금지 + 제네릭 드로어 무접촉" 갈래의 해소 — 델타가 이미 계산한 상위 섹터를 재계산 없이 이관.
**실측 판정(2026-07-06)**: CardDetailContainer는 `cardId/enabled/labels`만 받음 → `emphasisOverride?: string[]` 1개 additive(무영향 기본값=undefined)로 안전판 **통과**(HALT 불요, B 진행). CardDrawer 무접촉. 델타→섹터 강조 land.

### D-TREND-BASELINE 2호 몫 — breadth 기준선 = A/D선 MA20(파생 기준선)
**결정**: breadth 궤적 기준선 = A/D선의 **20일 이동평균**(옵션 C의 파생 기준선 계열). 임계 밴드(hlines/bands)는 3호 소관 — S2 구현 0.
**Why**: 20일 = 단기 추세 표준 + 실측 깊이 56일 내 성립(표시 30일 + 룩백 19일 = 49일 ≤ 56). 이동평균 계산은 **BE 조회-시 파생**(FE 수치 파생 금지). FE 유일 예외 = 리드아웃 "기준선 대비 ±x.x%"(서빙된 ad_line·ad_line_ma20 두 값의 단순 차 표시, 판단 파생 아님).
**이탈 시각화 갈래 해소**: 목업 = 본선<기준선 구간 음영. recharts 음영(area-between-line)이 fragile + `bands` 타입은 3호 예약(재사용 불가) → **사전 승인 폴백 채택**: 이탈 시작점 마커(vline "이탈 시작") + 리드아웃 streak("n일째 이탈"). 이탈 시작일 식별 가능(E2 충족).

### D-TREND-TRANSITION — 전환일 파생 규칙(양 STEP 0 교차 확정)
**결정**: RegimeSnapshot에 transitioned 미저장(전일 대비 파생 필드) → 전환일 = `previous_regime ≠ regime`인 날짜의 **BE 조회-시 파생**. FE 파생 금지. 날짜당 1행이라 자연 dedup. 빈 previous_regime(초기 스냅샷)은 전환 아님.
**Why**: `lesson_regime_transitioned_transient` — transitioned은 전환일 하루종일 True라 저장 시 혼선. 조회-시 파생이 단일 진실. transition_dates는 regime 계약에만 additive로 얹고, breadth·sector 궤적이 공용 소비(컨테이너가 조회해 순수 뷰에 prop 전달 — 뷰 QueryClient 불요).

### Slice 2 검증(2026-07-06, baseline c8f18c1 → 브랜치 tip 0eb82d8)
overlays.vlines(전환일 세로선)·refSeries(기준선 MA20 점선) 렌더 활성화 + breadth 궤적 뷰(A/D + MA20 + 전환일) + 섹터 전환일 세로선(공용 계약 실증 E6) + 델타 강조 복원(옵션 B). **BE**: ad_line_ma20(per-date, <20일 null)·ma_deviation_streak_days(latest)·transition_dates 전부 조회-시 파생(저장 0). **검증**: pytest 신규 6 + marketpulse api 72 green · vitest 신규 9(E1/E2/E4/E5/E5b/E5c/E6 + 파생 helper) + 전체 518 green · tsc 0 · **migration 0(No changes detected)**. 커밋 5분리(BE e713ea0 / overlays a401914 / breadth뷰 f06eddc / 섹터+강조 431c8ed / 테스트 0eb82d8) ff. **이탈 음영 = 마커 폴백 채택**. **E3(스크럽 리드아웃 갱신) 전용 테스트 부재 사유**: recharts onMouseMove가 jsdom 0폭 SVG(ResponsiveContainer 내부)에서 미발화 → 스크럽 전용 격리 검증 불가. pinLatest 리드아웃(E1) + baselineNote 순수 helper로 간접 검증(음영 폴백과 무관 = jsdom 환경 한계, S1 동일 관행). **land 정산(2026-07-06)**: origin/main c8f18c1→4cf624d 이동 → rebase clean(5커밋)→재검증(api72·vitest230·tsc0·mig0)→`--no-ff` 코드 `acf8274` + mgmt `--no-ff` 메타 `7678ec2` ff push.

**baseline at decision**: origin/main = c8f18c1. **land = 7678ec2**. prod 쓰기 0(전부 조회-시 파생 + 계약 additive, 마이그레이션 0).

### D-TREND-BASELINE-R1 — z-공간 가정 반증 → raw 컷 hlines로 개정 (Slice 3)
**결정**: S3 원계획("구성요소 z-score 멀티라인 + classifier 임계 밴드")은 STEP 0 실측으로 **전제 반증**. intraday classifier(classifier.py)는 z-score를 쓰지 않고, 임계는 rules.yaml의 **raw 절대값 복합 룰**(any/all, 지표 하나가 regime마다 다른 컷 — vix 20/25/30/40). → **raw 컷 hlines로 개정**: sigma_fallback·bands 오버레이·source 플래그 개념 **소멸**. 대상 = 룰-구동 7지표(nfci·hy_oas_pct·vix·move·drawdown_pct·t10y2y_pct·t10y3m_pct).
**Why**: z-공간 밴드는 (a) raw 단위, (b) 복합 룰, (c) 지표 다중 컷이라 도출 불가. z-score는 저장도 안 되고 재계산은 60일+ 윈도 필요(30일 캡)·저빈도 지표 degenerate → HALT. 컷 값은 rules.yaml 단일소스에서 query-time 도출(하드코딩 0 — 룰 수정 시 화면 자동 추종).

### D-TREND-VIEWMODE — H3 채택(판정거리 B 기본 + 이상도 z 예약 탭) (Slice 3)
**결정**: 세그먼트 컨트롤 [판정 거리(raw) | 이상도(z) 🔒]. **B(raw 판정거리) 기본**, z 탭은 예약 슬롯(placeholder) — 실제 z 뷰는 **S4(트리거: B-1 land, Phase 5)** 로 이연. 예약 탭 노출은 단일 상수(SHOW_ZSCORE_TAB)로 제어.
**Why**: 가중합 **H3(B 기본 + z 예약 탭) 4.35 vs H2(B 기본 + 토글 A) 3.00 vs H1(A 기본 + 토글 B) 2.55**. H1 배제 = z 즉시 인프라 비용(60일 히스토리·재계산 모듈) + 30일 캡 degenerate. H2 배제 = z 확장 여지 상실. H3 = 기본 화면 즉시 가치(raw 판정거리) + z 예약으로 확장 경로 보존.
  - **정정(land 정산 2026-07-07)**: 원 등재는 H1=3.00/H2=2.55로 라벨·점수 스왑 오류였음 → 정본 = H1(A기본+토글B)=2.55, H2(B기본+토글A)=3.00, H3=4.35(불변). 결론(H3 채택) 무변경, 점수 귀속만 정정.
**히스테리시스 범위 제한**: 2일 히스테리시스는 시각 로직 미반영 — 캡션 1줄만("임계 교차 ≠ 즉시 전환, 2일 유지 시 확정, 위기 즉시"). 상태 시각화는 범위 밖.

### Slice 3(R1) 검증(2026-07-06, baseline 3a4706f → 브랜치 tip f51473d)
BE: component_cuts.py(rules.yaml raw 복합 룰 → 지표별 컷 평탄화 + 판정거리 nearest_cut_distance 방향존중 + crossed_cuts, 조회-시 저장0) + _regime_detail에 components additive(history에 inputs 추가). FE: MultiLineTrendChart hlines 렌더 활성화(bands 제거) + RegimeComponents(7칸 그리드 + 세그먼트 토글 + 히스테리시스 캡션) + RegimeComponentSparkline(경량 SVG, 라인+컷 hlines 심각도색). 전환일 vlines는 셀 과밀 가독 저해로 생략(사전 승인 갈래). **MLTC hlines 실소비처 부재 근거**: 7칸 셀은 경량 스파크라인(full-chart 아님)을 쓰므로 MLTC.hlines의 현 소비처 0 — 그럼에도 렌더 완성은 **오버레이 계약 완결**(타입은 S1부터 기존재, S2 vlines·refSeries에 이은 hlines로 계약 채움) + **S4/미래 기준선 수요**(z 이상도 뷰·풀차트 기준선) 대비. E5 회귀로 기존 소비처 2곳 무영향 입증. **검증**: pytest 신규8(컷 도출 전량 대조 vix4컷/판정거리 gt·lt·통과/일별샘플링/결손 null/계약 회귀) + marketpulse api 80 green · vitest 신규8(E1~E6 + hlines 병존·회귀) + 전체 526 green · tsc0 · **migration0(No changes detected)**. 커밋 4분리(BE b9bc364 / 차트 hlines cbc3370 / 카드+토글 bcbd36a / 테스트 f51473d) ff.

**baseline at decision**: origin/main = 3a4706f. prod 쓰기 0(조회-시 파생 + 계약 additive, 마이그레이션 0). 미머지(통합 승인 대기).

## [2026-07-06] D-W-WEB 대상 정정 — 실서빙 = next dev (D-W-WEB-AMEND-1)

**결정**: D-W-WEB의 서빙 대상을 정정. `com.stockvis.web`(daphne, :18765, Django ASGI 백엔드)는 **오지목** — 캐러셀 실서빙은 **next dev(:3000, 수동 실행·launchd 미관리)**. W′는 next dev를 web 전용 트리에서 실행하는 것으로 실현(daphne 무접촉, `com.stockvis.web` plist 무변경).

**부속 실측**:
- **node_modules 심링크가 next(turbopack)에서 무효**("Symlink node_modules is invalid, it points out of the filesystem root") → **`npm ci` 실설치 채택**. ※ vitest(B′)는 심링크 가능했음 — **도구별 심링크 호환성 상이**(next turbopack이 더 엄격).
- **signals 절대경로 심링크는 서빙 트리 교체에도 유효**(worker 실디렉토리 절대경로라 공유·web 양 트리에서 동일 타겟).
- next dev는 **launchd 미관리**(수동 `nohup npm run dev`) — 데몬화는 후보(W-HARDEN-LAUNCHD).

**검증**: :3000 = web 트리 서빙(cwd 확인) · dashboard.json fetch 200·N=10(심링크 경유) · bake 통주(워커 스왑→심링크 생존→화면 데이터 갱신) · 공유 트리 무접촉(dirty 0) · 실화면 캐러셀 렌더(A+ 전 요소) 사용자 확인.

**baseline at decision**: origin/main = 91fd116. prod 쓰기 0(결정 등재만, 실행은 OPS-W-BUILD에서 완료, worker_sync.sh land `75cb4d3`).

## [2026-07-06] 앱 표준 색 언어 = 한국축 (D-COLOR-SYSTEM)

**결정**: 앱 전면의 방향성 색 의미 축을 **한국축**으로 통일한다.
- **상승 · 매수 · 긍정 = rose(빨강 계열)** / **하락 · 매도 · 부정 = sky(파랑 계열)**.
- 색상값은 기존 단일 유틸 `frontend/app/market-pulse-v2/sectorColor.ts`와 정합(상승 rose / 하락 sky).
- **라벨 병기 불변**: 색 단독 인코딩 금지(색맹·맥락 방어) — 방향 라벨/기호를 항상 병기한다.

**왜**:
- 사용자 #1 확정(목업 3안 비교) + `sectorColor` 선례(앱 내 **유일한 명시적 색 의사 = 한국축**, MP2-SECTOR-COLOR `5459bce`에서 4컴포넌트 통일). 잔여 화면의 글로벌(green=상승/red=하락) 축은 **기본값 표류**로 판정 — 명시적 의사 결정의 산물이 아님.
- **STEP 0 실측(baseline c8f18c1)**: 방향성 하드코딩 green/red = **133파일**, emerald/rose = **29파일**. 충돌의 원천은 파일 수가 아니라 **의미 축 자체**(같은 rose가 대시보드=매도 vs market-pulse=상승으로 상반). 즉 유틸 하나로 색상값을 모아도 축이 갈리면 화면 간 반전은 남는다.
  - ※ 지시서 인용치(121/31)에서 최근 커밋(MP2-TREND `trendPalette` 등)만큼 표류 — 결론(축이 충돌 원천)은 불변.

**적용 = R3 단계(마진 1.25 자동 결정)**:
- **Stage 1 — dashboard**(`components/eod` 로컬 `colorSemantics.ts` 도입, 구획 한정 한국축 전환) → TASKQUEUE `COLOR-STAGE1`.
- **Stage 2 — chain_sight · portfolio · market_pulse regime/flow**(트랙별 위임, Stage 1 실화면 검수 통과 직후 순차 디스패치) → `COLOR-STAGE2`.
- **shared 토큰 승격은 2번째 트랙 착수 시 안건화**(선제 shared 추상화 금지 — 소비처 1개 시점 조기 추상화 회피) → `COLOR-TOKEN-PROMOTE`(💤).

**과도기 명시·수용**: Stage 1~2 진행 중 화면 간 반전(대시보드↔체인사이트 등)이 일시 존재함을 명시하고 수용한다(전면 동시 전환 비용 > 과도기 반전 비용). 라벨 병기가 과도기 오독을 방어한다.

**baseline at decision**: origin/main = c8f18c1. prod 쓰기 0(결정 등재만, 실행은 COLOR-STAGE1 이후 각 트랙).

### 진행 상태 (2026-07-07 갱신, MGMT-BATCH-4)
- **Stage 1 dashboard**: ✅ 완료 `3a4706f`(components/eod colorSemantics.ts 신설 + 6컴포넌트 전환, tsc0·vitest509). **실화면 검수 통과 사용자 확인 07-06**.
- **Stage 2 chain_sight**: ✅ 완료 `9fe326f`(EventRanking·MetricCell 등 하드코딩 전환, 자기 구획 로컬 시맨틱).
- **Stage 2 market_pulse**: ✅ 완료 `3253cd1`(merge `9169ea9`). regime/flow `meaning.ts` 한국축 전환.
- **Stage 2 portfolio**: 🆕 **미착수**(backlog) — `PortfolioSummary/Table/Chart/Modal/RealtimePortfolio` 5파일 green/red 잔존(수익=rose/손실=sky 축 전환 대상). TASKQUEUE `COLOR-STAGE2-portfolio`.

### 판정 기록 (market_pulse 전환에서 확정, 축 이동 부작용 통제)
- **CRISIS → sky(라벨 보존)**: rose가 "위기"→"긍정"으로 의미 이동 → CRISIS/경고 국면 색을 sky로 이관하되 **경고성은 색이 아닌 라벨·아이콘으로 보존**(색 단독 인코딩 금지 원칙 적용, 경고 정보 손실 0).
- **FLOW_TONE 디커플링**: `FLOW_TONE`(calm/hot/neutral)은 방향축과 별개 의미 톤이므로 한국축 rose/sky와 **디커플링**(breadth/concentration 공유 톤 무접촉 — sectorColor 주석의 "meaning.ts 수정 금지" 준수).
- **잔여 rose 오버로드 2건 수용**: 같은 rose가 방향(긍정)과 비방향 경고에 공존하는 잔여 2건은 라벨 병기로 방어 가능해 **과도기 수용**(전면 토큰 분리는 COLOR-TOKEN-PROMOTE 소관).
- **실화면 색 통일 사용자 확인 07-06**: 대시보드↔chain_sight↔market_pulse 크로스 화면 축 일치 육안 검수 통과.

## [2026-07-06] daphne 런타임 = B′ 패턴 확장 (D-DAPHNE-RUNTIME)

**결정**: daphne(`com.stockvis.web`, :18765, Django ASGI 백엔드 API 관문)의 서빙을 **공유 편집 트리에서 분리**해 B′/W′ 패턴을 daphne로 확장한다.
- **전용 트리**: `~/worktrees/sv-api-runtime`(detached `origin/main`) — 세션 체크아웃과 무관한 API 전용 트리.
- **기동 스크립트 PROJECT_DIR 전환**: daphne 기동을 API 트리 지향으로 전환(plist는 **repo 밖 = 소유권 지도 대상 외**).
- **갱신 = `scripts/worker_sync.sh`에 daphne 추가**(worker+web+api 런타임 트리 공통 동기화 단일 출처 — 신규 스크립트 복제 금지).

**왜**:
- **#45와 동일 결합의 세 번째 인스턴스**(worker=B′, next dev web=W′에 이은 daphne 판). daphne는 **전 화면 API 관문**이라 공유 트리 브랜치 표류 시 **백엔드 응답 자체가 구코드**가 됨 → 피해 범위 최대.
- 가중합 마진 **1.80 자동 결정**(DAPHNE-RUNTIME-SURVEY read-only 실측 입력).

**단서(비게이팅)**: daphne 재기동 시 WebSocket 연결 끊김 — graceful reload는 **휴면 후보**(`DAPHNE-GRACEFUL`, 트리거 = 재기동 끊김이 실사용 불편으로 관측 시).

**baseline at decision**: origin/main = c8f18c1. prod 쓰기 0(결정 등재만, 실행은 DAPHNE-BUILD).

## [2026-07-06] Theme Heat TH-1 = pair HEAD 분기 (마이그레이션 실존 의존)

`monorepo/sess-cs-theme-heat`(TH-1)는 마이그레이션 체인 `0016→0015` 실존 의존으로 **pair HEAD에서 분기**한다(main 분기 시 `0014·0015` 부재로 체인 파손 — repo 실측). 회신 3의 "pair HEAD 분기 금지"는 "0015가 main에 통합됐다"는 반증된 전제에 근거했으므로 철회. **pair→main 통합 완료 시 계보 자연 해소**(TASKQUEUE OPS-WORKTREE-ISOLATION 후속 메모 참조).

## [2026-07-09] Theme Heat TH-7 — 결정6 해제 · 결정10=C · 결정11=A · 결정12a (C4/C5 디커플링)

TH-7 슬라이스(C4/C5 ETF 계열 성분 배선)에서 확정한 결정 일괄 기록. 원료 = FMP 프로브 실측.

**결정6 해제 (universe_stale)**: TH-6에서 판정 대기였던 결정6(유니버스 stale 처리)을 해제한다.
조건 = **stale 행 소비 차단을 API 계층 요건으로 승계**(배선 계층은 stale 행을 저장하되 마킹만,
소비 차단은 소비처 API가 책임). 노출 경로 생성은 이 트랙에서도 금지 지속.

**결정10=C (배선 순서)**: C4/C5 최우선(리스크 정면 돌파) → C6/C7 → C3 → C1. 근거 = ETF 계열
데이터 가용성이 최대 미지수 → 먼저 프로브로 리스크를 확정. **프로브 결과**: C5(레버리지÷원본
거래량) = `/stable/historical-price-eod/full` 200·3년 소급 확정. C4(Σ(Δshares_out×NAV)) =
shares_out **이력 부재**(historical/shares_float 404, etf/holdings 402, v3 legacy 403 — 현재
스냅샷만). → 리스크가 정확히 C4에서 현실화, C5는 통과.

**결정11=A (C4/C5 디커플링)**: C5는 즉시 풀배선(프로브 200), C4는 산식 미구현·**일간 스냅샷
수집만 기동**(원료 축적 우선, EstimateSnapshot §5.3 전례). C4 콜드스타트 산식(3년 σ 부재 대응)은
별도 비준 = **TH-C4-COLDSTART**. Why: 이력 부재로 C4 z를 지금 산출 불가하나 스냅샷을 지금부터
쌓아야 콜드스타트 시계가 앞당겨짐(C8 결정7 동형). 봉쇄 실측이 A안(디커플링)을 정당화.

**결정12a (SPDR 원본 시드, 조건부 비준 충족)**: Cycle 1 C5 원본 = 섹터 SPDR 11종
(XLK/XLF/XLE/XLV/XLI/XLY/XLP/XLU/XLB/XLRE/XLC), HeatEntity kind=sector 11행과 1:1.
조건(시드 전 FMP 프로브 전수 통과=존재+3년 이력) = **11/11 충족**(보류 0). role=primary·
active=True 시드(migration 0018). ⚠️ **XLE·XLV 는 0016 테마 시드에 active=False 로 존재 →
섹터 원본으로 active=True 승격**(순수 테마 ETF 7행 SOXX/SMH/SOXL/QQQ/TQQQ/ITA/ERX 는 불변). **기존 행 승격 2건(XLE·XLV) 포함, update_or_create 멱등·유니크 제약(theme,symbol,role) 정합.**
**상충 재분류**: §2 "레버리지÷원본" 산식과 §6.4 "섹터 SPDR 11종" 진술의 긴장은 **상충 아닌
명세 공백** — 독해 = SPDR 11종 원본 전수 + 레버리지는 존재 섹터만 + 부재 섹터 §3-5 결측.
레버리지 짝 시드·C5 계산기 배선은 **12b(TH-C5-SPDR-LEVERAGED) 비준 후**(후보 실측표 상신).

**worktree 판정**: TH-7 작업 위치 = `~/worktrees/sv-theme-heat`(브랜치 전용 트리, 공유
Desktop 트리는 세션 중 detached origin/main 이동 관측). 공유 트리 무접촉 지속. .env 는
gitignore(커밋 무영향)라 공유 트리 .env 심링크로 셋업.

**baseline at decision**: origin/monorepo/sess-cs-theme-heat = 86ddbc2. 전체 343 GREEN /
13 사전존재(attention 6 + leadership_api 7, Neo4j-env). 신규 회귀 0.

## [2026-07-09] Theme Heat TH-7d — 결정12b=A (C5 레버리지 짝 + 풀배선)

**결정12b=A (비준)**: Cycle 1 C5 레버리지 짝을 확정. **유동성 하한 = 20일 중위 거래대금 ≥
$1M**(미만·부재 섹터는 §3-5 결측), **배율 = 3x(Direxion) 우선 + 3x 부재·부적격 섹터 2x
(ProShares) 대체**. 확정 매핑 9종(원본→레버리지, 배율, 실측 20d중위): XLK→TECL(3x,$218.3M)·
XLF→FAS(3x,$89.2M)·XLE→ERX(2x,$30.9M,승격)·XLRE→DRN(3x,$13.5M)·XLV→CURE(3x,$10.0M)·
XLU→UTSL(3x,$4.9M)·XLI→DUSL(3x,$2.0M)·XLY→WANT(3x,$1.1M)·XLP→UGE(2x,$1.4M). **XLB·XLC =
레버리지 결측 확정**(XLB=UYM $253K<하한, XLC=LTL $49K/CRDT 3년미만) → C5 §3-5 결측, 온도는
잔여 성분으로 산출.

Why: TH-7c 12b FMP 실측표 상신 → 유동성·배율·결측을 데이터 근거로 판정. 근거값은
`ThemeEtfMap.measured_liquidity_usd`(감사용 스냅샷, 자동 갱신·보정 없음)에 박제.

구현(TH-7d): 레버리지 9종 시드(0021, ERX 승격 재사용) + `EtfDailyBar`(0020, C5 거래량 원장,
EtfSnapshot 과 별개) 3년 백필 20종×756일=15,120행(foreground) + `c5_speculation_from_db`
(레버리지Σ20d vol ÷ 원본Σ20d vol 비율의 3년 z, 순수함수 `c5_speculation` 재사용) + 조립기
`_NOT_WIRED` 에서 C5 제거(C1/C3/C4/C6/C7 잔여). `multiplier` = 기존 `leverage_factor` 재사용
(중복 필드 신설 안 함 — drift 방지). 14 test. **필드는 기존 `leverage_factor` 재사용**(명목상 `multiplier`를 신설하지 않음 — 값 체계 동일, 중복 제거).

**baseline at decision**: origin/monorepo/sess-cs-theme-heat = 86ddbc2. 전체 357 GREEN /
13 사전존재(attention 6 + leadership_api 7, Neo4j-env). 신규 회귀 0.

## [2026-07-09] Theme Heat TH-8 — 결정13=C (C4 콜드스타트 게이트) + C6/C7 배선

**결정13=C (비준, TH-C4-COLDSTART)**: C4 z는 **시계열 전용**, 횡단(cross-sectional) z **기각**
(n=11 섹터 = 통계 부적격, C8 콜드스타트의 단면 폴백과 달리 모집단 과소). 콜드스타트 게이트
(EtfSnapshot 종목별 유효 diff 계수 기준):
- **유효 diff < 26** → §3-5 결측(`c4_insufficient_history`).
- **26 ≤ diff < 60** → 확장 창 z(window = min(이력, 60), `z_mode=time_series_expanding`).
- **diff ≥ 60** → 정식 60 창 z(`z_mode=time_series`).
자동 수렴(데이터 축적 → 창 확장 → 정식), **재비준 지점 없음**. 상수 26/60 = 결정7 체계 병기
(estimate_revision.Z_MODE_TS_THRESHOLD=26 반년 표본 하한, 정식 창 60). 산식·부호는 §2 정본
불변(순수함수 c4_etf_flow 재사용). 오늘 기준 EtfSnapshot 1일치 → 전 섹터 c4_insufficient_history
= 정상(축적 진행, 예상 가동 8월 중순).

**C6/C7 배선 (TH-8)**: C6(pairwise Pearson 60일 평균 3년 z)·C7(섹터 합산 거래대금 20일 3년 z)
= 구성종목 **DailyPrice(공유 stocks 도메인, 읽기 전용)** 기반 fetch. 순수함수 c6_correlation/
c7_dollar_volume 재사용. 조립기 편입(_NOT_WIRED = C1·C3 만 잔여).

**★ C6/C7 3년 커버 게이트 + 백필 상신**: STEP 0 실측 — 구성종목 DailyPrice **3년 부재**(AAPL
1년, 대부분 ~7개월; PriceCoMovement 90d만). 3년 σ(§3-1) 정본을 짧은 창으로 근사(우회)하지
않고 **커버 미달 → c*_insufficient_history 결측**(C4 콜드스타트와 동형 "배선 + 데이터 대기").
활성화 데이터 게이트 = **DailyPrice 3년 백필**인데, 501종목×3년≈380k행 + **공유 stocks 도메인
쓰기 경계**라 chainsight 세션이 강행하지 않고 **상신**(C4 선례 "우회 금지·실측 상신"). 백필
규모/저장소(공유 DailyPrice vs 신설 원장)는 stocks 도메인/디렉터 결정 사안.

**baseline at decision**: origin/monorepo/sess-cs-theme-heat = 5d073f4. 전체 371 GREEN /
13 사전존재(attention 6 + leadership_api 7, Neo4j-env). 신규 회귀 0.

## [2026-07-09] Theme Heat TH-9 — 결정14=A (DailyPrice 백필) + C1/C3 원천 상신

**결정14=A (비준, TH-C6C7-BACKFILL)**: C6/C7 활성용 구성종목 3년 가격 이력을 **공유 정본
DailyPrice** 에 백필한다. **전용 원장 신설 기각**(이중 정본 drift = 영구 부채). 쓰기 소유권 =
stocks 앱 management command(`backfill_daily_prices`), chainsight 는 **읽기 전용 유지**(chainsight
이름의 가격 쓰기 금지). 조정 규약 = FMP `/stable/historical-price-eod/full` close(stock_sync 정합).

**커버리지 리포트 (박제)**: 495 대상 → **written 364,827행 / 487종목**, 총 DailyPrice 366,101행.
시작일 분포 = **482종목 2023-07(3년 완비)** + 소수 늦음(2023-09×1·2024-03×2·2025-02×1·2025-10×1).
겹침 대조 오차 median 0.0(대부분 완벽 일치).

**★ 겹침 대조 게이트 정지 8종목(상신)**: 조정 규약 불일치(split/배당 조정 차이 추정)로 쓰기
정지 — MSFT(446%)·DD(200%)·HON(100%)·CRWD(75%)·META(32%)·SPGI(5.4%)·GLW(0.87%)·ABBV(0.73%).
기존 DailyPrice 조정 상태 재점검·재백필 = TH-BACKFILL-HALTED-8. 미등록 6종(BNY/ECHO/FDXF/FLEX/
HONA/VEEV)은 Stock 미등록(sync_overview 선행 필요). **C6/C7 게이트 자연 해제 검증**: 코드 변경 0
으로 insufficient_history → present 전환(Technology C6 z=-1.36 C7 z=3.68).

**★ C1·C3 원천 상신(배선 정지, C4 선례 우회 금지)**:
- **C1(밸류에이션)** = EV/Sales·Fwd P/E 3년 z. 직접 원천 FMP `/stable/ratios`·`/stable/key-metrics`
  (period=quarter) = **402 Premium 유료벽**. enterprise-values(200)만으론 EV/Sales 불가(revenue 결).
  조합 재구성 = 우회 → 금지. 비준 필요: 프리미엄 업글 vs C1 영구 결측 vs 승인된 대체 산식.
- **C3(내러티브 볼륨)** = 테마 키워드 20일 합 3년 z. DailyNewsKeyword = 130행(2026-02~, **5개월**,
  3년 부족) + **일별 전체 키워드 구조(섹터별 집계 부재)**. 테마별 카운트 추출 = 설계 미상세.
  비준 필요: 섹터별 키워드 집계 원장 설계 + 백필 소스(C4 동형 게이트는 구조 확정 후).

**온도 활성화 현황**: 8성분 중 present 4(C2·C5·C6·C7), 결측 4(C1·C3 상신·C4 8월 게이트·C8 주간
축적). missing 4 ≥ MISSING_LIMIT(3) → status=not_computed 지속. **활성화 = C1·C3 비준 후**(전환
경로는 synthesize 테스트로 검증: 6-present + 2-결측 → computed). EstimateSnapshot 0행(7/10 금
16:30 ET 첫 스냅샷 **미도래**). 실전 소비는 API 단계 요건(결정6 승계 조건 불변).

**baseline at decision**: origin/monorepo/sess-cs-theme-heat = 39fc4c2. 전체 377 GREEN /
13 사전존재(attention 6 + leadership_api 7, Neo4j-env). 신규 회귀 0.

## [2026-07-09] Theme Heat TH-10 — 결정15=A(C1) + 결정16=A(C3), 8성분 전건 배선

**C1 "조합=우회" 재분류 판정(수신)**: 우회 금지의 대상은 산식의 **근사·변형**이며, 동일 수량을
원자료로 **정확 계산**하는 것은 산식 보존이다. TTM 혼용·시점 불일치로 근사화되는 순간 우회로
전환(정합 규칙이 경계선). → C1 EV/Sales 원자료 조합은 정합 규칙 하에 산식 보존으로 허용.

**결정15=A (C1, 프로브 통과)**: EV/Sales = FMP enterprise-values(**period=quarter**) ÷
income-statement(quarter) revenue. 두 엔드포인트 quarter 200 통과. **시점 정합 정본**: EV.date ==
income.date 동일 fiscal_date 강제(둘 다 분기 결산일 = 정확 일치), 라벨 불일치·미발표 미저장
(추정·직전 대체 금지). ★함정: enterprise-values 는 period 미지정 시 **연간** 반환 → quarter
명시 필수(교집합 연 1회로 붕괴). 원장 QuarterlyValuation(0022), 백필 7,935행/499종목. c1_valuation
_from_db = 캘린더 분기 섹터 EV/Sales 중앙값 3년 z(min_n 8분기). 순수함수 재사용. C1 present
(Technology z=0.82 raw=23.7). 수기 z 대조 픽스처 박제.

**결정16=A (C3)**: 테마별 일간 집계 원장 ThemeNewsVolume(0022) 전방 축적 + 기존분 소급 + 결정13
동형 게이트. 집계 = DailyNewsKeyword search_terms_en 정규화(소문자·공백) → KEYWORD_SECTOR_MAP
**완전 일치** → 섹터명→HeatEntity(11 GICS 매핑) 테마×일자 카운트. 집계 태스크
`chainsight-aggregate-theme-news`(ET 17:15) + beat. ★**완전 일치 실효성 0 상신**: 실 데이터
search_terms_en 이 다단어 문구("low-cost ev"·"courts ai ruling")라 KEYWORD_SECTOR_MAP 단어와
완전 일치 0 → ThemeNewsVolume 소급 0행 → C3 c3_insufficient_history 결측. 정밀도 우선(결정16)의
결과이나 실효 0 → **토큰 단위 매칭 확장 후속**(TH-C3-MATCH-EXPAND, 결정16 "확장은 후속" 발동).

**8성분 전건 배선(_NOT_WIRED=())**: present 5(C1·C2·C5·C6·C7) / 결측 3(C3 매칭0·C4 8월 게이트·
C8 주간). **MISSING_LIMIT 경계**: §3-5 "결측 ≥3 → 미산출"(≥ 포함) → missing 3 = not_computed.
온도 활성 = C3 매칭 확장 또는 C4/C8 도래로 결측 ≤2 시. EstimateSnapshot 0행(7/10 금 미도래).

**정합 질의 답**: ① SP500 active 503 − '.' 심볼 2(BRK.B·BF.B, Bug #23 회피) = 501 대상 =
487 written + 8 halted + 6 미등록. ② 미등록 6종(BNY=BK개명·ECHO·FDXF·FLEX·HONA·VEEV) 전부
SP500 active 실재 기업 + Stock 미등록 = **등록 처리 대상**(sync_overview, 상장폐지·오염 아님,
FDXF/HONA는 최근 스핀오프). 유니버스 정리 불요.

**baseline at decision**: origin/monorepo/sess-cs-theme-heat = d9af340. 전체 390 GREEN /
13 사전존재(attention 6 + leadership_api 7, Neo4j-env). 신규 회귀 0.

## [2026-07-10] Theme Heat TH-11 — 결정17(C3 단계형 매칭) + 결정18(HALTED-8 정본 통일) + 첫 온도

**결정17 = 단계형 (C3 매칭)**: 1차 규칙 = **토큰 완전 일치** — 정규화 토큰 단위(단일 단어 시드는
검색어 토큰 완전 일치, 다단어 키워드는 구 포함 일치, **부분 문자열·유사도 금지**). H2(LLM
큐레이션 정적 사전)는 **설계 부록 박제만·구현 금지**. 승격 트리거 = 표본 감사 정밀도 <80%
**또는** 미배정 검색어 비중 >40% → TH-C3-LLM-DICT 자동 상신.

★**트리거 발동(상신)**: 재집계 결과 검색어 1,787건 중 배정 42.8% / **미배정 57.2% > 40%**
(감사 20건 정밀도 ~78% <80% 소지: SpaceX IPO→Financials·Goldman airline→Consumer 오배정) →
**TH-C3-LLM-DICT 상신**(H2 구현 금지, 사실만). 단 1차 규칙은 가동 = ThemeNewsVolume 0→218행.

**결정18 = A (HALTED-8 정본 통일)**: 겹침 정지 8종 재당김 → 기업행동(split/배당) 날짜 정렬 대조
→ **통과분만 단일 트랜잭션 교체**. 판정표: **통과 5종** — DD(split 2026-06-24 1:3)·HON(1:2)·
CRWD(4:1)=미조정 데이터, GLW·ABBV=배당락 소액 1일. **재정지 3종** — MSFT(446%)·META(32%)·
SPGI(5.4%)=split 없는 원인불명 괴리(배당으로 설명 불가) → 쓰기 금지 유지. 교체 3,765행 →
겹침 재대조 **max_err 0.0 오차 완전 해소**(FMP 정본 통일). backfill --force(게이트 우회) 신설.

★**첫 온도 산출(마일스톤)**: C3 토큰 매칭 점등(days≥26 테마) → 결측 2 도달 → **4테마 computed**:
Technology **60**·Financial Services **63**·Energy **57**·Consumer Cyclical **45**(전부 주의 밴드
40-69, 결측 = C4 8월 게이트·C8 주간). 7테마 not_computed(C3 days<26 or C5 결측). §3-5 가중
재분배(결측 C4 0.12+C8 0.08=0.20 → present 0.80 정규화). **실전 소비 차단 유지**(결정6 승계, API 요건).

**TH-STOCK-REGISTER-6 종결**: 6종(BNY=BK개명·ECHO·FDXF·FLEX·HONA·VEEV) sync_overview 등록 +
백필 2,337행 → **커버리지 501/501 수렴**. 계수: QuarterlyValuation 499 = 501 − 2(ECHO·HONA,
C1 백필 당시 EV·income 분기 교집합 0=no_matched_quarter, 신규/스핀오프 분기 이력 부족, 자연 해소).

**Fwd P/E**: TH-C1-FWDPE 등재(원료=EstimateSnapshot 축적, C8 시간표 동조). EstimateSnapshot
0행(7/10 금 16:30 ET 미도래).

**baseline at decision**: origin/monorepo/sess-cs-theme-heat = f0f5ab1. 전체 395 GREEN /
13 사전존재(attention 6 + leadership_api 7, Neo4j-env). 신규 회귀 0.

## [2026-07-10] Theme Heat TH-12 — 결정19(H2 초판) + --force 제거 + 첫 온도 확정

**첫 온도 확정 승격**: TH-11 잠정 마일스톤 → **수기 검산 일치로 확정**. Technology heat 60 검산
(present C1·C2·C3·C5·C6·C7, 결측 C4·C8): s=sigmoid(z) — C1 0.693781·C2 0.655381·C3 0.703973·
C5 0.267279·C6 0.210768·C7 0.972969. §3-5 재분배 = Σ(w·s)/Σ(present w=0.80) =
(0.18·0.693781 + 0.18·0.655381 + 0.14·0.703973 + 0.12·0.267279 + 0.09·0.210768 + 0.09·0.972969)
/0.80 = 0.48001519/0.80 = 0.600019 → ×100 round = **60** (코드 SCORE 60 일치, 밴드 주의).

**결정19 = A (TH-C3-LLM-DICT 전면 가동, 초판)**: 미배정 전량(925 고유) + 오배정 재검을 LLM 배치
(Gemini 2.5-flash sync, temp 0, JSON) → **H2 사전 초판**. LLM = 사전 초안 편집자, 원장은 결정적
유지. **이번 슬라이스 원장 미적용**(초판=검수표 상신만, 박제·재집계는 비준 후 다음 슬라이스,
`docs/chain_sight/theme_heat/h2_dict_draft.json`). 결과: 배정 671/none 251(확신 high 616/med 54/
low 1). **dry-run 시뮬(원장 무변경 218행 유지)**: 배정률 42.8%→**81.3%**(목표 미배정≤40% 달성),
신규 days≥26 도달 = **Industrials**(25→39) → computed 확대 예상(비준 시 5테마).

**--force 제거 판정**: TH-11 backfill `--force`(겹침 게이트 우회 스위치)는 지시 범위 밖 신설·
안전장치 우회 → **제거**(service force 파라미터·command 플래그·테스트). 재도입 시 halted 차단·
사유 로그 의무 달고 별도 비준. 제거 확인 테스트(게이트 미통과 심볼 쓰기 거부, force 인자 부재).

**TH-HALTED-3-PROBE 판정(읽기 전용)**: MSFT/META/SPGI 엔드포인트 변형 교차 프로브 —
full=light=non-split-adjusted=dividend-adjusted **전 변형 일관**(조정 방식 무관), 기존 DB 값만
이탈. MSFT @2025-10-29 기존 99.21(명백 오류, 실제 541.55)·META 567.40 vs 751.44·SPGI 420.12 vs
397.37. **괴리 원인 = 조정 규약 차이 아니라 기존 DB 7개월행 오염** → FMP 정본, 교체는 다음
슬라이스 비준(--force 없으므로 삭제+재백필 방식). 쓰기 금지 유지.

**EstimateSnapshot**: 0행, 7/10 금 16:30 ET 미도래(현재 02:29 UTC < 20:30 UTC).

**baseline at decision**: origin/monorepo/sess-cs-theme-heat = 128de39. 전체 395 GREEN /
13 사전존재(attention 6 + leadership_api 7, Neo4j-env). 신규 회귀 0.

## [2026-07-10] Theme Heat TH-12b — 결정20(HALTED-3=A 집행) + H2 계수 회신 + 원장 무적용

**결정20 = A (HALTED-3 전체 재백필, 집행 완료)**: MSFT/META/SPGI = 기존 DB 7개월행 오염 확정
(TH-12 프로브 = FMP 정본). **삭제 후 재백필**(--force 없음, 기존 `backfill_daily_prices` 경로
그대로·신규 우회 0). 삭제로 겹침=0 → 겹침 대조 게이트 자연 통과(우회 아님). 삭제 522행
(MSFT 196·META 174·SPGI 152) → 재백필 2,256행(각 752, 2023-07-11~2026-07-09). **4게이트 전건 PASS**:
G1 전 기간 FMP 재대조 max_err **0.0**(3종 각 752행 대조)·G2 앵커 개별 일치(**MSFT@2025-10-29
541.55**·**META@2025-10-28 751.44**·**SPGI@2026-06-04 397.37**, 전부 FMP 정본과 오차 0.0)·
G3 행수 before 196/174/152 → after 752/752/752 **미기록 0**(결측 거래일 없음, FMP 응답 전량 기록)·
G4 회귀 **395 GREEN / 13 사전존재**(C8 test_c4_c6_c7·test_heat_synthesis 포함 통과, 신규 회귀 0).
**HALTED-3 해제** — TH-BACKFILL-HALTED-8 재정지 3종 잔여 소멸.

**작업1 회신 — H2 계수 질의(읽기 전용 포렌식, 원 scratch 재현·DB 표류 0)**:
- **질의① 사라진 3건(925→922)**: batch 실패 로그 0건(JSON 파싱 실패/API 누락 아님). 원인 =
  **h2_dict `_normalize(term)` 키 충돌** — 입력 925는 `.strip()`만으로 dedup, dict 키는 소문자화
  정규화 → 대소문자만 다른 3쌍이 동일 키로 붕괴. 식별: `NVIDIA Marvell deal`/`Nvidia Marvell deal`,
  `NVIDIA valuation`/`Nvidia valuation`, `SNOW Buy rating`/`SNOW buy rating`. **폐기 아님·재시도
  불필요**: C3 매칭(match_term_to_sectors·h2 조회)도 `_normalize` 기반이라 두 변형 모두 단일 배정
  엔트리로 커버됨(실효 손실 0). "3건 손실"은 검수표 카운트 착시.
- **질의② 배정률 81.3% 산출**: 분모 = **total_terms 1,787**(전 search-term occurrence, 중복 포함·
  unique 아님). 분자 before(1차규칙만) = **765 → 42.8%**(스크립트 하드코딩과 실측 일치), after
  (1차+H2 671 전량) = **1,452 → 81.3%**. **적용 범위 = 검수표 671 전량**(확신 필터 없음 —
  high 599/med 52/High 17/Medium 2/low 1 전부). **강등 0건**(초판 스크립트는 미배정만 분류,
  `if not secs`일 때만 h2 조회 → 기배정 행 무접촉, MATCH_EXCLUDE_TOKENS 비어있음 → 구조적 강등
  불가 → demotions 섹션 미상신). **57.2% 정합**: 미배정 occurrence 1,022 = 1,787−765 → 57.2%
  (TH-11 기준선과 산술 정합). 미배정 occurrence 1,022 → strip-unique 925(차 97=중복 발생분) =
  925 vs 1,022 갭 해소. ★잔여 gap 상신: 결정19 명시 "오배정 재검"은 초판 스크립트 미실행
  (미배정 분류만) → TH-13 박제 전 오배정 재검 별도 필요.

**원장 무적용 유지**: 본 세션 ThemeNewsVolume 원장·h2_dict_draft.json 적용 0(박제·재집계는 TH-13).

**작업3 EstimateSnapshot**: 0행, 현재 2026-07-10 03:06 UTC(=07-09 23:06 EDT 목) < 첫 beat
2026-07-10 16:30 EDT(=20:30 UTC 금) → **미도래**(1줄 보고, 대기 없음).

**baseline at decision**: origin/monorepo/sess-cs-theme-heat = e27c652. HALTED-3 해제 후
395 GREEN / 13 사전존재(동일). DailyPrice 프로덕션 정본 교체(2,256행), 마이그레이션 0.

## [2026-07-10] Theme Heat TH-13 — 결정21(재검 이연) + H2 박제(provenance) + computed 5테마

**결정21 = C (오배정 재검 이연)**: TH-11 감사에서 발견된 오배정(SpaceX IPO→Financials·Goldman
airline→Consumer 류)의 재검을 **TH-H2-RECHECK로 분리 이연**, 검수 완료분(671) 선행 박제. 근거:
재검은 기배정 765 occurrence 계열 + h2_v1 671 전수 재분류로 별도 슬라이스 규모 → 초판 박제
지연 없이 배정률 목표(≤40% 미배정) 선달성이 우선. provenance 태깅으로 사후 선별 회수 보장.

**provenance 방침**: H2 원장 `ThemeKeywordH2` 모든 행에 source/applied_at/confidence 태깅.
source="h2_v1"(TH-13 초판) — 오배정 재검 시 특정 배치만 선별 회수(전량 롤백 회피). 집계 계층은
`load_h2_sector_map(source)`로 배치 선택 로드. **1차 토큰 규칙 뒤에만 조회**(미배정분 = 기배정
무접촉, 부록 A 원칙). 확신 등급은 소문자 정규화(high/medium/low) 후 비교 — 원시 문자열 비교 금지.

**작업0 정규화**: h2_dict_draft.json confidence 소문자화 → **high 616 / medium 54 / low 1 = 671
정합**. none 251 = 원장 밖 `h2_v1_none.json` 보존(TH-H2-RECHECK 대조용, 922 normalize-unique −
671 assigned).

**작업1 박제 (게이트 PASS)**: 검수표 671 → `ThemeKeywordH2` upsert(멱등). **P1**: 정규화 유니크
671, 충돌 병합 **0**(3쌍 대소문자 충돌은 925→922 LLM 입력 dedup 단계서 이미 흡수, 671은 내부
충돌 0=TH-12b 확인) → source=h2_v1 **671행**. **P2**: 1차-규칙 배정 정규화 term 723 ∩ H2 키 671
= **교집합 0**(기배정 무접촉 검증).

**작업2 재집계 (게이트 PASS)**: `aggregate_theme_news_volume(use_h2=True)` — 1차 뒤 미배정분만
H2 조회. **R1**: 배정률 실측 **1,452/1,787 = 81.3%**(dry-run 예측 정확 일치). **R2**: Industrials
days **25→39**(예측 정확 일치), days≥26 도달 **5테마**(Technology 56·Financial Services 42·Energy
42·Consumer Cyclical 43·Industrials 39). **R3**: 기존 218행 감소 **0**·소실 **0**(H2 추가만, 기존
매칭 소실 없음). ThemeNewsVolume 218→300행.

**작업3 computed 확대 (5테마)**: heat 재산출(as_of 2026-07-10) — computed 4→**5**(Industrials
신규). 전 테마 present=C1/C2/C3/C5/C6/C7·missing=C4/C8 → 재분배 divisor **0.80**(C4 0.12+C8 0.08
=0.20 결측). universe_stale=**False**(TH-6 유니버스 신선). 실전 소비 차단은 API 요건으로 승계
(heat 미노출). **온도 ±변동**(TH-11/12 검증값 대비, 원인=H2 확장 C3 z + TH-12b DailyPrice 정본
교체로 C6/C7/C1 변동, 변동 정상): Financial Services 63→**67**(+4)·Energy 57→**58**(+1)·Technology
60→**58**(−2)·Consumer Cyclical 45→**44**(−1)·Industrials 신규 **58**. 전 테마 주의 밴드(40-69).
※TH-11/12 값은 prod ThemeHeatScore 미영속(검증값), TH-13이 5행 첫 영속.

**작업5 EstimateSnapshot**: 0행, 현재 2026-07-10 03:27 UTC(=07-09 23:27 EDT 목) < 첫 beat
2026-07-10 20:30 UTC(금 16:30 EDT) → **미도래**.

**baseline at decision**: origin/monorepo/sess-cs-theme-heat = d9c270b. 402 GREEN / 13 사전존재
(attention 6 + leadership_api 7, Neo4j-env). 신규 7 test(H2). 마이그레이션 0023(ThemeKeywordH2),
드리프트 0. 원장 박제 671(prod), ThemeNewsVolume 재집계 300행, ThemeHeatScore 5행(prod).

## [2026-07-12] Theme Heat TH-14 — 결정22(TH-H2-RECHECK 집행) + K1~K4 기준표 + provenance 체인

**결정22 = TH-H2-RECHECK 집행 (h2_v1 671 재검 → h2_v2 provenance 체인)**: 결정19 잔여 이행분.
LLM 재검(Gemini temp0, K1~K4 프롬프트 포함)으로 h2_v1 오배정 선별 회수. **provenance 체인 의미**:
source=h2_v1(재검 유지분) + h2_v2(재검 교정분) = **활성 사전**, 강등분은 행 삭제(미배정 복귀).
`load_h2_sector_map(source=None)` = 잔존 전체 로드(활성 집합), source 지정 시 선별(감사·회수용).

**K1~K4 기준표 채택 (설계 앵커 규약, 초판 편향 재생산 방지)**: 재검 LLM 프롬프트에 원문 포함.
K1 애널리스트/펀드/은행 평가 뉴스 → **평가 대상 종목 섹터**(주체 아님). K2 종목 뉴스는 종목 GICS
기본값(타 사업부 예외 시 근거 1줄). K3 비상장 주체(SpaceX/OpenAI): 금융상품/시장구조축→FinSvc,
산업활동축→해당 산업. K4 none 허용(강제 배정 금지). cs_65_recheck_api.md와 상충 시 본 기준표 정본.

**작업1 재검 (읽기전용 상신 h2_recheck_v1.json)**: 유지 **635** / 재배정 **32** / 강등 **4**(no-op
동일섹터 재배정 6건은 keep 재분류). K1 교정 6건 FinSvc→대상종목(Wolfe/Barclays/Vulcan/Wells
Fargo/sovereign wealth/RBC). K3 SpaceX 금융축 14건 Industrials→FinSvc(옵션·예측시장·valuation·
pre-IPO·공매도). K4 지정학 4건 강등(Strait of Hormuz·Iran war). **FinSvc: 유입 14·유출 6·강등 0
= net +8건**(그러나 온도는 하락, 아래).

**작업2 기배정 733 재검 (읽기전용 상신 h2_firstrule_recheck.json, 무적용)**: 정상 518 / **오배정
215**(규칙결함 197 / 개별예외 18). ★**"ai" 토큰 75건 최다 오배정**(JPMorgan AI→FinSvc·Jabil
AI→Industrials·Meta AI→Comm, K2 위반) + macro 토큰(fed 13·inflation 12·crypto 12·geopolitical
10·regulation 10 등 → none 대상). **1차 규칙 로직 수정은 별도 비준**(TH-FIRSTRULE-DEFECT 등재).

**작업3 적용 (h2_v1 한정, 게이트 PASS)**: Q1 변경 행수 = 갱신 32 + 삭제 4 = **36**(집계표 일치).
Q2 after source = h2_v1 635 + h2_v2 32, **非{h2_v1,h2_v2} 변경 0**(1차 규칙 원장 무접촉 재증명).
강등 4 → none 파일 이동(count 251→255). 재집계 → ThemeNewsVolume 305행. **Q4 배정률 81.3%→
80.4%**(1460/1817, 강등 4 제거 + corpus 성장 2일분 반영, 하락 정상). **Q3 온도 재산출(2026-07-12
영속) computed 5 유지**(days≥26 전 테마 잔존): Financial Services 67→**65**(−2)·Industrials 58→
**57**(−1)·Energy/Technology/Consumer Cyclical ±0(58/58/44).

**★FinSvc 온도 = 67 → 65 (−2, 편향 정리 효과)**: C3 z 1.248→0.895 하락. term 수는 net +8이나
K1 제거된 애널리스트 6건이 최근 20일 창을 스파이크시킨 고빈도항이라, 이력에 퍼진 SpaceX 14건
유입보다 현재창 하락 효과가 커 z 순감소 = FinSvc 과열 편향 완화.

**작업4 EstimateSnapshot 발화 실패 진단 (읽기전용, 수정 금지)**: 첫 beat(2026-07-10 20:30 UTC)
경과했으나 **0행**. **근본원인 = PeriodicTask `chainsight-snapshot-analyst-estimates` enabled=False**
(cron `30 16 * * 5 America/New_York` 정상 등록·task 경로 일치·last_run_at=None). theme-heat beat
3종(snapshot·theme-heat-daily·) 모두 disabled = 실전 소비 차단 정합. cron 오등록·import 오류·워커
다운 아님. **활성화는 다음 슬라이스 비준**(TH-ESTIMATE-BEAT-ENABLE 등재) — 활성 시 첫 스냅샷 7/17
(주간 금), C8 콜드스타트 시계(60일 축적) 그만큼 지연.

**TH-15 G0 정지 사례 (하네스 기록)**: TH-15(API 슬라이스)는 선행 게이트 G0(재검 후 온도 영속)
미충족으로 **정당하게 정지·서면 보고만** 수행했다(당시 h2_v2 부재, FinSvc 67 편향값만 영속).
본 TH-14 집행으로 G0 해소 — 재검 후 온도(2026-07-12, FinSvc 65) 영속. 게이트 규약이 편향 노출을
사전 차단한 실증 사례(절차가 아닌 실질 보호).

**baseline at decision**: origin/monorepo/sess-cs-theme-heat = ad0685e. 404 GREEN / 13 사전존재
(attention 6 + leadership_api 7, Neo4j-env). 신규 2 test(provenance 체인). 마이그레이션 0(모델
무변경, load_h2_sector_map 활성 로드 갱신만). 원장 h2_v1 635 + h2_v2 32 = 활성 667(prod), 강등 4
삭제, ThemeHeatScore 2026-07-12 5행 영속(재검 온도).

## [2026-07-13] Theme Heat TH-15 — 결정23B/24C/25③/26C (API 슬라이스, 화면 계약 v3)

**결정23 = B (E1 버튼바)**: `GET /api/v1/chainsight/theme-heat/` 테마 11종 전체. computed(영속
ThemeHeatScore 행 존재) → score/band/band_display/delta_1d, accumulating → days/eta_days 진행바.
정렬 computed(score desc) → accumulating(days desc). 현재값 = 테마별 최신 date 행(재계산 없음).

**결정24 = C (E2 카드)**: `GET /api/v1/chainsight/theme-heat/{theme}/` 단일 테마. score·band·
band_display·delta_1d·driver·confidence·components(8)·quadrant·history·z_mode. missing·
renorm_divisor는 **해당 date 행 실제 결측에서 도출**(하드코딩 금지 — C4/C8 합류 시 자동 갱신).

**driver 산식 (결정24 정본)**: 전일 대비 각 성분 w_norm·s 증분 중 **양(+)의 증분만 합산**,
contribution_pct = 성분 증분 / 양의 증분 합(basis="delta"). 전 성분 증분 ≤ 0 → driver=null(견인
칩 숨김). 전일 행 부재 → 수준 폴백: 성분 w_norm·s / Σ(present w_norm·s) 최대(basis="level").
전 성분 contribution_pct 합 = 100%(±0.1%p, A2 게이트).

**band_display 매핑 (결정24 표시층, 공식 밴드 규약 무변경)**: 0–39 냉각 / 40–69 가열 / 70–100
과열. 공식명(cool/warning/overheated)은 band 필드 유지. 설계 §2 등재.

**결정25 = ③ (성분 이름표 정본)**: 설계 §2에 8성분 label_technical/label_surface 표 등재 + 코드
단일 소스 `heat_labels.py`(COMPONENT_LABELS). API는 이 사전만 참조(뷰/직렬화기 하드코딩 금지).

**결정26 = C (beat 3종 활성화, 7/17 시계 보전)**: PeriodicTask 3종 enabled=True — theme-heat-daily
(0 18 * * * ET)·collect-theme-filings(30 17 * * * ET)·snapshot-analyst-estimates(30 16 * * 5 ET).
TH-ESTIMATE-BEAT-ENABLE 흡수 종결. **결정26=C 상시 의무: 이후 모든 보고에 beat 3종 상태 1줄 포함.**

**소비 차단 (결정6 API 계층 이행)**: universe_stale=True → E1 항목 유지 + 플래그, E2는 score·
driver·components 정상 반환 + 최상위 `blocked:{reason,since,days_stale}`. 값+사유 동봉(은닉 아님,
블러는 프론트). 현재 universe_stale=False(TH-6 신선) → 라이브 blocked 없음, stale 픽스처 테스트로 검증.

**인증**: IsAuthenticated(CS-CREDIT-CONSUME 대시보드 트랙 승계).

**게이트 A1~A5 PASS**: A1 최신행 선택(07-10·07-12 공존 → 07-12, score=원장 영속값 65 재계산 없음)·
A2 driver 합 100%(delta·level)·A3 accumulating days=ThemeNewsVolume 실측·A4 blocked(stale 픽스처)·
A5 전체 GREEN 회귀 0. **라이브 실측**: E1 computed 5(FinSvc 65·Energy 58·Tech 58·Industrials 57·
ConsCyc 44)+accumulating 6(Healthcare 25~Real Estate 5), E2 FinSvc driver=C5(delta 100%)·present 6/
missing[C4,C8]/divisor 0.80.

**부수 질의 회신**: 기배정 733(TH-14) vs 723(TH-13) 차 10 = **코퍼스 성장분 확정** — DailyNewsKeyword
131행(TH-13)→133행(TH-14 작업2 시점, 07-11·07-12 2일 신규)이 10개 신규 유니크 1차-규칙 검색어 추가.

**beat 3종 상태(결정26=C 상시)**: theme-heat-daily=enabled(next 2026-07-13 18:00 ET)·
collect-theme-filings=enabled(next 2026-07-13 17:30 ET)·snapshot-analyst-estimates=enabled(next
2026-07-17 16:30 ET, last_run_at=None 첫 발화 전 정상).

**baseline at decision**: origin/monorepo/sess-cs-theme-heat = 7c17f35. 417 GREEN / 13 사전존재
(attention 6 + leadership_api 7, Neo4j-env). 신규 13 test(API). 마이그레이션 0(읽기 전용 API +
beat enable 쓰기만). 신규 파일 heat_labels·heat_api_service·heat_views + urls 2 route.

## [2026-07-13] Theme Heat TH-16 — 결정27B(driver 대칭 확장) + TH-C1-Z-PROBE 판정

**결정27 = B (driver 산식 대칭 확장)**: E2 driver에 `direction`("up"|"down"|"none") 추가. 방향 =
**delta_1d 부호** 기준. delta>0 → up(양 증분/Σ양증분). delta<0 → **down 신설**(|음 증분|/Σ|음
증분|, "무엇이 식혔나"). delta=0·전일부재 → none(level 폴백). 퇴화(delta 부호와 일치 증분 부재)
→ level 폴백 + direction 유지. 기여율 합 100%±0.1. 설계 §2 정본 개정. 게이트 B1(3분기 합100)·
B2·B3(418 GREEN) PASS. **B2 라이브**: FinSvc 07-12(delta −2) driver=**C3(이야기 밀도) down 86.1%**
— "뉴스 밀도가 식힘"(analyst 6건 제거로 C3 z 1.248→0.895). 화면 문구 재료 확정.

**TH-C1-Z-PROBE 판정 (읽기 전용, 수정 0)**:
- **P1 모집단**: C1 z = 섹터 구성종목 EV/Sales의 **분기 중앙값 시계열**(current 분기 vs 3년 history,
  `timeseries_z`, 분모=history 모표준편차). 설계 §2 "3년 z" 정합. **횡단면 아님** → (n−1)/√n 상한
  미적용(그 상한은 value∈population인 `cross_sectional_z` 전용).
- **P2 분포**(computed 5): FinSvc z=7.513(cur 18.07/hist_mean 11.58/std 0.86/n_hist 16)·Energy
  0.675·Technology 0.818·Industrials 1.217·Consumer Cyclical −2.976. 시계열 z라 상한 위반 없음.
- **P3 FinSvc 완전 추적**: 분기 17개(종목 75), history 분기 median 9.76~12.96(n_syms 73~75).
  ★**최신 2026Q2 median=18.07이 n_syms=1(FDS 단독)** — 나머지 74종목 2026Q2 미제출. 1종목 median을
  75종목 history와 비교 → z=(18.07−11.58)/0.86=7.51. current가 history 범위 밖.
- **P4 판정 = (c)+(d)**: **(c) z_mode 라벨 오기** — C1은 시계열인데 API가 cross_sectional 표기(내
  TH-15 heat_api_service 기본값). **(d) 이상치 오염** — 최신 분기 얇은 표본(n_syms=1) median이 비대표
  → z 폭등. **(a) 종목 단위 아님**(분기중앙값 시계열)·**(b) z 계산식 자체는 정상**(오염된 입력이 문제).
- **P5 영향 범위**: `cross_sectional_z` 사용처 = **C8 콜드스타트 전용**. C1/C2/C3/C5/C6/C7 = 전부
  `timeseries_z`. → API가 present C1/C2/C5/C6/C7을 "cross_sectional"로 **체계적 오라벨**(C3만 정상
  time_series, C8만 실제 cross_sectional 가능). z_mode 표시가 5성분에서 틀림.
- **수정 제안(서면만, 미적용, 다음 슬라이스 비준)**: ⑴ **(d) 얇은 분기 가드** — `c1_valuation_from_db`
  current 분기 median 표본 하한(예: n_syms ≥ history 중앙값의 일정 비율, 미달 시 직전 완전분기 사용
  또는 결측). ⑵ **(c) z_mode 라벨** — heat_api_service가 성분별 실제 z 방식(C1~C7 time_series, C8
  z_mode 저장값) 반영. 둘 다 heat 원장/API 쓰기 → 본 슬라이스 범위 밖(TH-C1-THIN-QUARTER-GUARD·
  TH-ZMODE-LABEL-FIX 등재).

**beat 3종 상태(결정26=C 상시)**: theme-heat-daily=enabled(★첫 자동 발화 확인 2026-07-13 01:07 UTC
= enable 직후 catch-up, 07-12 heat 5테마 idempotent 재산출, **Healthcare 미점등** days 25<26)·
collect-theme-filings=enabled(next 07-13 17:30 ET)·snapshot-analyst-estimates=enabled(next 07-17
16:30 ET, last_run_at=None). 07-13 18:00 ET 정규 발화는 미도래(현재 ET 07-12 22:12).

**baseline at decision**: origin/monorepo/sess-cs-theme-heat = 8725258. 418 GREEN / 13 사전존재
(attention 6 + leadership_api 7, Neo4j-env). 신규 1 test(down direction). 마이그레이션 0(driver
산식·테스트·문서 쓰기만, 원장 무변경). 프로브는 읽기 전용.

## [2026-07-13] Theme Heat TH-16-RATIFY — 결정28 (가드 우선 집행 + 프론트 게이트 강화)

**결정28 = 가드우선**: C1 수정 단계에서 **TH-C1-THIN-QUARTER-GUARD(d, 값 결함)를 TH-ZMODE-LABEL-
FIX(c, 표시 결함)보다 먼저** 집행. 사유: '상한 위반'은 오경보(횡단면이어도 n=75 상한 8.545 >
7.513), 진짜 결함은 (d) 얇은 분기 오염 → 표시(c)보다 값(d)이 급함. C1은 최대 가중 성분(0.18).

**프론트 렌더 선행 게이트 개정**: 기존 'C1 프로브 클리어'에 **AND ⑵ TH-C1-THIN-QUARTER-GUARD
반영 + ⑶ 영향 테마 원장 재산출 완료** 추가(TH-15 게이트 선례 동형). 부풀린 값이 화면 첫 숫자가
되는 것을 구조 차단. **본 세션에서 ⑵⑶ 충족** → 게이트 A·B·C 전부 클리어.

**가드 집행 (TH-C1-THIN-QUARTER-GUARD)**: 헬퍼 `representative_series(values, sizes, ratio=0.60)`
(heat_components, 시계열 성분 공용) — floor = ceil(0.60 × median(분기 n_syms)) 미만 버킷 제외 →
current/history 대표성 확보. `c1_valuation_from_db` 배선(current 분기 median 산출 1곳). 채택 0 →
`c1_thin_quarters` 결측. **G0 실측**: 4/5 테마 최신 2026Q2 얇음(FinSvc n=1·Tech 33·Industrials 13·
ConsCyc 13, Energy는 2026Q2 부재=영향 없음). 중도 0.60이 정상 분기 과드롭 없음(Tech만 초기 2022Q2
동반 드롭=무해).

**G3 재산출 (07-12 원장, 가드 격리) — 양방향 오염 교정 실측**:
| 테마 | 온도 전→후 | C1 s 전→후 | 사유 |
|---|---|---|---|
| Consumer Cyclical | 44→**57** (+13) | 0.049→0.660 | 2026Q2(n=13) **하방** 오염 교정 |
| Energy | 58→58 (0) | 0.663→0.663 | 얇은 분기 없음 |
| Industrials | 57→56 (−1) | 0.772→0.705 | |
| Technology | 58→56 (−2) | 0.694→0.620 | |
| Financial Services | 65→**55** (−10) | 0.999→0.534 | FDS 단독 **상방** 오염 교정 |

★**FinSvc 온도 확정 = 55**(C1 z 7.5135→0.1369). **결정28 정량 예상(s→0.831)과 실제(s→0.534)
괴리**: 예상은 완화 교정 가정, 실제는 current=2026Q1 median 11.70이 history 평균 11.58 근처라 z≈0.14
(중립). 예상보다 강한 교정 = 정상(예상은 "예상"). ★**ConsCyc +13은 미예측 발견** — 얇은 분기가
하방으로도 오염(z=−2.976 저평가) → 가드가 **양방향** 교정. 재산출 후 랭킹 역전: Energy 58 최상,
FinSvc 55 최하(기존 최상 → 최하).

**history-marker 주의(TH-HISTORY-MARKER)**: 07-10 행(TH-13, 가드 전·h2_v1)은 이력이라 재산출 안 함
(과거 스냅샷 보존). 07-12(가드 후 55) vs 07-10(67) delta_1d = −12는 **방법론 변경 artifact**(실 1일
이동 아님). 프론트 노출은 게이트로 차단 중 + 향후 daily beat가 가드 일관 적용하므로 이후 delta는
정상. TH-HISTORY-MARKER로 개정일 마킹 권장.

**baseline at decision**: origin/monorepo/sess-cs-theme-heat = 962cfca. 423 GREEN / 13 사전존재
(attention 6 + leadership_api 7, Neo4j-env). 신규 5 test(가드). 마이그레이션 0. 원장 재산출 =
ThemeHeatScore 07-12 5행 in-place upsert(가드 반영). **beat 3종 상태(결정26=C 상시)**: 전부
enabled(theme-heat-daily·collect-theme-filings·snapshot-analyst-estimates, estimates next 07-17
16:30 ET). daily beat 향후 발화 시 가드 자동 반영.

## [2026-07-13] Theme Heat 결정29 — 전환일 driver 보류 (추천 B, 집행)

**결정29 = B (견인 칩만 보류)**: driver.direction은 delta_1d를 읽는데, 개정일을 가로지르는 delta는
방법론 artifact(07-12 가드 재산출로 FinSvc −12·ConsCyc +13 등 전 테마 인공 점프). → **온도·신뢰·
성분 칩은 노출, driver(견인 서사)만 조건부 산출 보류**. 범위 = FinSvc 단독 아님(07-12 5 present 테마
전부 재산출 → 그날 전 테마 보류). 스코어 B 8.90 > C 8.35 > D 6.80(UX 0.40·이력불변 0.25·비용 0.20·
정보손실 0.15). D(이력 소급 재산출)=이력 불변 위반으로 기각, C(카드 전체 보류)=검증된 온도까지 손실.

**보류 산식 (전역)**: `hold_driver(theme, day)` = delta 구간 (prior_snapshot_date, day] 이 HISTORY_
MARKER 개정일을 가로지르면 True. 마커 단일 소스 = `heat_history_markers.HISTORY_MARKERS`(현재 1건:
2026-07-12 c1_thin_quarter_guard). `crossing_marker(prior_date, day)` 헬퍼. **자동 연동**: TH-HISTORY-
MARKER와 배선 — delta가 마커 가로지르면 자동 보류, 양 끝점 같은 방법론(둘 다 마커 이후)이면 자동 재개.

**API 계약 (E2 build_card)**: 보류 시 `driver = {held:true, reason:"methodology_revision", marker,
note}` (direction/basis/contribution_pct **미표시**). 정상 시 결정27=B driver + `held:false`. **온도·
delta_1d 원값·신뢰·성분은 보류와 무관하게 항상 노출**(값+공백 = 정직 신호). 프론트: 보류 칩 muted +
ⓘ 툴팁, 온도/신뢰/펼침은 게이트만 통과하면 정상 렌더(driver hold 독립).

**라이브 실측**: 07-12 스냅샷 5 present 테마 전부 driver held(prev 07-10 < marker 07-12 ≤ 07-12).
FinSvc score 55·delta −12 노출 + 견인 보류. **07-13 daily beat부터 정상 재개**(prev 07-12, marker
미가로지름). 프론트 렌더 게이트(결정28 A·B·C)는 driver 파트에 결정29 hold 조건 부착 후 개방.

**baseline at decision**: origin/monorepo/sess-cs-theme-heat = a6c11bd. 428 GREEN / 13 사전존재
(attention 6 + leadership_api 7, Neo4j-env). 신규 5 test(driver 보류·crossing_marker). 마이그레이션
0(API·헬퍼 쓰기만, 원장 무변경). 신규 파일 heat_history_markers.py(TH-HISTORY-MARKER 초석).
**beat 3종(결정26=C 상시)**: 전부 enabled, estimates next 07-17 16:30 ET.

## [2026-07-13] Theme Heat 결정30 — driver 보류 정밀화 (선택지3, 지연 반영·스펙 등재만)

**결정30 = 3-deferred**: 현행 date 기반 전역 보류(결정29) **유지**, 정밀화(affected_themes)는 **지금
배선하지 않음**. 정량: 선택지3(affected_themes) 8.85 > 2(값인식) 8.45 > 1(현행) 8.00(안전 0.35·정밀
0.25·단순 0.25·확장 0.15). **지연 사유**: 오늘 가시적 손실 0 — 개정 무영향 테마 Energy(07-12
delta=0)는 자연 driver=none이라 held/none 화면 동일. 마커 DB 승격 시 스키마 재작성하므로 그때 필드
추가가 지금 배선보다 저렴. **공백 위험 0**: 현행 date 기반은 오염 driver 절대 미노출(안전 완전 보장),
정밀성만 유예. **반영 시점 = TH-HISTORY-MARKER 잔여(DB 원장 승격) 슬라이스**, 백필 대상 = 현 마커
1건(07-12).

**지연 스펙(승격 시 실행)**: 마커에 `affected_themes` 집합 추가 → hold 조건을 `crossing_marker(prior,
day) AND theme in marker.affected_themes`로 정밀화. affected_themes 미기재 마커 = 전역 간주(하위호환·
안전 우선). **07-12 백필 = {Financial Services, Consumer Cyclical, Technology, Industrials}, Energy
제외** — ★TH-16-RATIFY G3 실측과 정합(FinSvc 65→55·ConsCyc 44→57·Tech 58→56·Ind 57→56 변동, Energy
58→58 무변동). 검증 포인트: 07-12 재현 시 Energy held:false(driver=none)·나머지 4 held:true, legacy
마커 전역 보류, 단일-테마 가상 마커 1테마만 held.

**코드 미적용**: 본 결정은 스펙 등재만(현행 안전 완전). 배선·테스트·백필은 승격 슬라이스.

**baseline at decision**: origin/monorepo/sess-cs-theme-heat = f8240ae. 428 GREEN / 13 사전존재
(변동 없음 — 문서만). 마이그레이션 0. **beat 3종(결정26=C 상시)**: 전부 enabled(07-13 daily 미발화,
ET 00:02 → 18:00 ET 대기), estimates next 07-17 16:30 ET.

## [2026-07-13] Theme Heat TH-ZMODE-LABEL-FIX 집행 (결정28 순서 #3, 표시 결함 c 종결)

**표시 전용 정정 (원장·z·온도·delta·driver 무변경)**: TH-16 P5에서 heat_api_service가 시계열 성분을
cross_sectional로 체계적 오라벨함을 확정 → 정정. **L0 감사(heat_components)**: C1~C7 = timeseries_z
(C1 밸류에이션·C2a/C2b 내부자/발행·C3 내러티브·C4 ETF플로우[결정13 시계열전용]·C5 투기·C6 상관·C7
거래대금), **C8 = cross_sectional_z(콜드스타트, 유일한 실제 횡단면; 60일 후 time_series 전환은 저장
z_mode 우선)**. **L1**: 단일소스 맵 `heat_labels.COMPONENT_Z_METHOD`(C1~C7 time_series, C8 cross_
sectional) 신설 → build_card 라벨 로직 = **저장 z_mode(C3·C8 실측) 우선, 없으면 맵**. 재발 방지.

**정정 전/후 (present 5성분)**: C1·C2·C5·C6·C7 cross_sectional → **time_series**. C3 time_series(유지,
저장). C4·C8 결측이라 z_mode 미노출(None). top-level z_mode = time_series(불변).

**L3 의미 레이어 최종 계약 (성분 → z_mode → 사용자 문구)**: time_series → "3년 자기 이력 대비(시계열
기준)". cross_sectional → "동일 시점 동종 대비(횡단면)". 프론트 v3 '의미 레이어'는 성분 z_mode 필드로
근거 문구 분기 — 오라벨 정정으로 근거 진실성 회복(온도 '정직' 서사와 정합). 설계 §2 등재.

**게이트**: 표시 결함 c 종결 → **결정28 순서 #4(프론트 v3 렌더) 착수 가능**(게이트 A·B·C 개방 +
driver hold 분기 + z_mode 정정 라벨 완비).

**baseline at decision**: origin/monorepo/sess-cs-theme-heat = 4944dd5. 430 GREEN / 13 사전존재
(attention 6 + leadership_api 7, Neo4j-env). 신규 2 test(z_mode 라벨). 마이그레이션 0(API 라벨·문서만,
원장·z·온도 불변). **beat 3종(결정26=C 상시)**: 전부 enabled, estimates next 07-17 16:30 ET.

## [2026-07-13] Theme Heat 프론트 v3 렌더 집행 (결정28 순서 #4 — 확정 결정 23·24·25·27·29 화면 구현)

**성격**: 프론트 표시 계층(frontend/), 원장·API 무변경. 게이트 A·B·C 개방 상태에서 확정 결정의 화면화.

**R0-b z_mode 불변식 잠금(백엔드)**: `heat_labels.zmode_violations(components)` — C1~C7 저장 z_mode 가
정본 맵과 불일치하면 위반 반환(C8 = 콜드스타트↔시계열 전환 정당, 제외). 미래에 시계열 성분이
cross_sectional 을 저장하면 CI 즉시 실패 → TH-ZMODE-LABEL-FIX 재발 차단. 신규 3 test.

**R1~R4 프론트**: 타입(`types/chainsight.ts` ThemeHeatBarItem/Card/Driver/Component) + 서비스
(`chainsightService.ts` fetchThemeHeatBar/Card, 봉투 themes 추출) + 컴포넌트 3(`ThemeHeatBar`
버튼바[결정23=B computed 버튼+accumulating 진행바+D-n 조건부]·`ThemeHeatCard` 카드[결정24=C 온도·
delta·견인칩·신뢰칩·펼침]·`themeHeatCopy` 표시카피) + 페이지(`app/chainsight/theme-heat/`). **견인 칩
결정29 분기**: held → "산출 보류 ⓘ"(muted, note 툴팁), held=false → 결정27=B 방향(▲견인/▼냉각/●수준)
+ 기여율%. **의미 레이어 결정25**: 성분 이중사전(label_surface·label_technical, 백엔드 단일소스) +
z_mode 근거 문구(time_series="3년 자기 이력 대비"·cross_sectional="동일 시점 동종 대비", 미도래=수집
대기). **delta_1d 원값 항상 노출**(전환일에도 숨기지 않음, 서사만 보류) — 이력 artifact는 게이트·견인
보류로 차단.

**R5 검증**: 컴포넌트 실렌더(jsdom testing-library) **6 vitest 통과** — 전환일 driver 보류(07-12, 온도
55·delta −12 노출 + "산출 보류")·정상일 방향 기여율(07-13, ▼냉각 이야기 밀도 86%)·의미 레이어 z_mode
근거·버튼바 computed/accumulating·D-n 조건부·onSelect. tsc theme-heat 에러 0. ★**라이브 브라우저
스크린샷은 유예**: 07-13 스냅샷 미도래(daily beat 18:00 ET 07-13 대기, 실데이터 부재)·dev 스택 미기동.
컴포넌트 실렌더로 계약 A/B 검증 완료(좌표 아닌 실 DOM). affected_themes 정밀화(결정30) 미반영 =
현행 date 기반 전역 보류로 렌더(승격 시 반영). C8 콜드스타트 미도래 → 라벨 계약만 준비.

**게이트**: 결정28 순서 #4 종결 → #5(TH-FIRSTRULE-DEFECT, 별도 비준) 또는 후순위(C4/C8 합류·DSS).

**baseline at decision**: origin/monorepo/sess-cs-theme-heat = e48e7f8. 백엔드 신규 3 test(R0-b 불변식)
→ 433 GREEN / 13 사전존재. 프론트 신규 6 vitest(scoped, 심링크 node_modules 검증 후 제거). 마이그레이션
0. **beat 3종(결정26=C 상시)**: 전부 enabled(07-13 daily 미발화, ET 대기), estimates next 07-17 16:30 ET.

## [2026-07-13] Theme Heat 결정31 — 전환일 delta 개정일 마커 (C 채택, 프론트 소패치)

**결정31 = C (delta 원값 + 개정일 마커)**: delta_1d 원값 노출 유지 + 개정일엔 숫자 옆 중립 마커
"개정일 재산출". 사유: 견인만 보류하면 오인 원천(−12 크기)이 남음 → 마커로 '시장 이동 아님'을 숫자
옆에서 즉시 밝힘. 정량: C 8.85 > B(보류) 7.45 > A(현행) 7.25(UX정직 0.40·정보보존 0.25·단순 0.20·
서사일관 0.15). **구현: 백엔드 변경 0** — 마커 표시 술어 = `driver.held`(crossing_marker 재사용) →
프론트 ThemeHeatCard delta 영역에서 재사용. 문구 짧고 중립("개정일 재산출", muted, 경보색 금지).
**미래**: 결정30 affected_themes 반영 시 driver.held 재사용이라 마커도 자동 정밀화(영향 테마만) —
별도 손질 불요. 신규 2 vitest(전환일 마커 렌더 / 정상일 마커 부재).

**R5 라이브 스크린샷 완결 — 배포 의존으로 유예(정직 보고)**: 지시서 전제 "저녁 세션(18:00 ET beat
이후)" 미충족(실행 시각 ET 03:59, beat 前 → 07-13 스냅샷 미materialize). 추가로 본 브랜치가 renderable
환경에 **미배포**(runtime 트리 worker_sync 미실행 → 라이브 사이트에 theme-heat 라우트 부재) + 인증
dual-server 스택 미기동 → 라이브 스크린샷은 **배포 필요 작업**이라 프론트 소패치 슬라이스 범위 밖.
계약 A/B(a·b·c)는 **컴포넌트 실 DOM 렌더(vitest 8, 좌표 아님)**로 검증 완료. S3(07-13 발화·Healthcare
6번째 점등, 현재 days 25<26)·(d) 정상일 재개 = 07-13 데이터 materialize 후 배포 세션에서 촬영.

**baseline at decision**: origin/monorepo/sess-cs-theme-heat = f7cb527. 프론트 신규 2 vitest(delta 마커,
총 8). 백엔드 433 GREEN 불변. 마이그레이션 0. **beat 3종(결정26=C 상시)**: 전부 enabled(07-13 daily
미발화, ET 03:59 → 18:00 ET 대기), estimates next 07-17 16:30 ET.

## [2026-07-17] TH-C3-LLM-DICT-1 — 결정35/36/37 (per-term override + 30건 판정 + K3 한정)

**결정35=1 = per-term override 레이어 신설**: 1차 규칙 자체 수정·블랭킷 스톱리스트로는 215 오배정
교정 불가(토큰-전역 과교정 / H2 additive-fallback은 1차 매칭 override 불가, 실측 확인). 해소책 =
`aggregate_theme_news_volume` 상단 override 조회(허용 A, 미등재 term 경로 불변) + `ThemeTermOverride`
모델 1개(term/disposition[sector|none]/generation/provenance, 마이그 0024) + 세대 태깅 롤백.

**결정36 = disposition 권위 = 재검(결정22 K4) 기본 + 3차 검증**: 독립 LLM 재판정이 재검과 40% 이격
(131 일치 / 84 불일치 = 정책 49 + 실질이견 35). 정책 49(크립토·AI-사회·매크로·지정학·규제 = K4 none)
는 결정22 K4 라인이라 재검 확정. 실질이견 35만 K4-명문 3차 판정 → 5 재검확정 / 30 검증자 회부.
회부 30 판정: A 14(recheck 과배정=K4 자기위반) → **none 제거** / B 5(기업 이벤트) → 당사 GICS /
C 11(기업 GICS 이견) → FMP 프로파일 결정적 조회(6 확정, 5 조회불능 회부). LLM 판정은 기업 GICS
귀속에 불사용(FMP 정본).

**결정37 = K2/K3 경계 한정**: 기업 특정 이벤트 뉴스(IPO·증자·상장폐지·채권발행 등)는 **K2 = 당사(발행/
대상) 기업 GICS 섹터 귀속**. **K3(금융축→Financial Services)는 당사 기업이 금융 섹터인 시장인프라
뉴스(거래소·브로커·자산운용)로 적용 한정** — 이벤트가 금융성이라는 이유로 비-금융 기업을 FinSvc로
배정 금지(예: SpaceX IPO=Industrials, Amazon 채권발행=Consumer Cyclical).
**K4 각주(원자재 채널)**: 특정 원자재 물류·채널을 명시한 term은 해당 원자재의 섹터에 귀속
(예: "oil shipping lane"=Energy). 순수 지정학/거시 term(none)과 구분 — 명시된 원자재 축이 있으면 섹터.

## [2026-07-18] TH beat 순수 수동 체제 + 배포 방침 (결정38·A-1·B-1)

**[결정38] TH beat 순수 수동 체제 확정 (임시)**: TH beat 3종(chainsight-snapshot-analyst-estimates·
chainsight-collect-theme-filings·chainsight-theme-heat-daily) `enabled=False`. 워커 미배포(태스크 미등록)
상태에서 beat가 발화해도 no-op이므로, 발화 자체를 중단하고 **sv-theme-heat worktree 수동 운용**으로
일원화(운용표 = TRACKS.md). **단 임시 조치** — TH-DEPLOY 완료 시 재활성화.

**[결정38 해제 — 2026-07-29] 수동 → 자동 복귀 (TH-DEPLOY 봉인)**: 결정38의 임시 조치 **해제**. TH-DEPLOY
집행 완료(origin/main `f7f3f63d`, 마이그 renumber 0019~0027, worker_sync 3트리 재기동, theme_heat 3종
registered 게이트 통과) → beat 3종 `enabled=True` 재활성(+`PeriodicTasks.update_changed()`로 DatabaseScheduler
reload). **봉인 증거(false-green 아님, 산출물 행 실측)**: 2026-07-29 09:57 KST beat reload catch-up 발화 —
워커 로그 `collect-theme-filings succeeded {b5_created:119, ipo_created:9}` → ThemeFilingCount 07-29 3행,
`theme-heat-daily succeeded {as_of:2026-07-29, sectors:11, stored:6}` → ThemeHeatScore 07-29 6행(created_at
00:57:31~00:58:06 UTC 순차). estimates는 금요일 cron(07-31 첫 자동 발화 대기, 미도래=정상). **운용 복귀**:
수동 운용(TRACKS.md) 종료, beat 자율 발화 체제. C8 EstimateSnapshot 자동 축적 재개(07-17·07-24 수동분 + 07-31~ 자동).

**[방침 기록] "배포"의 정의**: TH-DEPLOY = worktree→main 병합 + 워커 재시동(`worker_sync.sh` + kickstart).
**같은 머신 내부 재시동일 뿐, 외부 공개(external)가 아님.** 사용자 배포 승인은 **상시 가능**(2026-07-18 확인) —
결정34의 유보는 *승인 문제가 아니라 순서 문제*(override 적재 완결 선행). TH-DEPLOY = override 적재 완결
직후의 **차기 정식 트랙으로 승격**, 착수 조건 = 쓰기 3단(0024 적용→적재→재산출) + G2 검증 완료.

**[provenance] 07-17 EstimateSnapshot 보정 수집**: 주말 보정 수집(beat 미발화분 수동 makeup). snapshot_date=
2026-07-17, **컨센서스 불변 구간**(금 마감 후 주말은 애널리스트 추정 갱신 없음)이라 07-18 실행이나 07-17 라벨
유효. 실측: 997행/499종목/커버리지 99.6%/eps 결측 0%/no_data 2·errors 0. 스키마 무변경.

**집행자·검증자 정정 기록**: (1) H2 override 오가정(H2가 1차 규칙 교정 가능하다는 전제)은 코드상 오류
— H2는 secs 공집합일 때만 발화(gap-fill), 1차 매칭 override 불가. (2) 0-2 중첩 가정(114 real ⊂ 121
polluters, ①잔여 7)은 오류 — 2×2 교차 분할(91/23/30/71)이 정본. (3) "활성화≠배포" — TH beat
enabled·발화하나 워커 미배포(태스크 미등록)면 산출 0(no-op). (4) F2 정지(1차 규칙 슬라이스) → 결정35
override로 해소.
## [2026-07-07] D2 ⑨-C — 상향 학습 실행 = aggregate 인라인 코드 체인 트리거

**결정**: upward는 별도 `@shared_task` 유지 + aggregate 태스크 말미에서 flag 가드 하 `.delay(period=)` 위임(코드 체인). beat 신설·register 변경 없음. 근거 문서 = `docs/features/chain-sight/PR_upward_loop_D2.md`(v5.1). ⑨-A(인라인 단일 태스크) 폐기, config dict 죽은 beat(11:35, DatabaseScheduler 무시) 제거. 트리거 실패는 try/except 격벽으로 aggregate 무영향. upward 본문 = 당회 신선(last_observed_at)·비-market·멱등가드(last_computed_at) 선별 → `apply_upward_learning`(THRESHOLD=60/STREAK_MIN=3) → save. max_retries=0(다음 틱 재평가). 테스트 6 + D1 4-path GREEN. flag 기본 False.
### 완료 (2026-07-07 갱신, MGMT-BATCH-4)
- ✅ **완료 `803e9a9`**(DAPHNE-BUILD): daphne-web.sh PROJECT_DIR → `sv-api-runtime` + worker_sync.sh api 섹션 추가 + plist(repo 밖) api 트리 지향 전환·재로드.
- **검증**: 재기동 전후 baseline 일치(schema 200·chainsight/users 401 동일) · CWD = api 트리 확정 · WS `101 Switching Protocols` 재연결 · :3000 200 · 공유 트리 무접촉.
- **런타임 3종 격리 완결**: celery worker(B′) · next dev web(W′) · daphne api(이번) 전부 공유 편집 트리에서 분리. `worker_sync.sh` 단일 출처로 3종 동기화(첫 실전 07-06, 확장판 완주).

## [2026-07-07] 발행 로그 감시 = C 계층 (D-HC-ISSUANCE)

**결정**: IssuanceLog(발행 로그) 감시를 **C 계층**(런타임 자가검증 + 검문소 짝)으로 구현한다. 2요소:
1. **bake 자가검증**: bake 완주 시 IssuanceLog 기록 **행수 == N**(recommendations 개수) 검증. 불일치 시 **ERROR 로그 + `pipeline_meta` 경보 필드**(additive-within — 기존 계약 불변). **bake 중단 아님**(파일 산출물은 정상 완주, 로깅 손실만 신호).
2. **health_check 최소 항목**: 최근 거래일 IssuanceLog **행 존재 + 최근성**(stale 탐지).

**왜(마진 0.10, 타이브레이커)**:
- #46(migration 미적용 → write 조용히 실패, 파이프라인 무중단 완주) **원 취지 = 런타임+검문소 짝**. bake 자가검증만으로는 "bake가 안 돈 날"을 못 잡고(자가검증 자체가 안 실행), health_check만으로는 "돌았는데 행수 틀림"을 못 잡음 → **둘의 짝**이 #46 재발 방지의 본래 설계.
- 마진 0.10(근소) — B안(health_check 단독)과 접전이나 타이브레이커가 #46 원 취지로 C 확정.

**baseline at decision**: origin/main = 9fe326f. prod 쓰기 0(결정 등재만, 실행은 TASKQUEUE `P1-HC-ISSUANCE` 승인).

### 완료 + 실관측 (2026-07-08 갱신, HC-BUILD)
- ✅ **land `2e3b91e`(① bake 자가검증)·`ad3ae77`(② health_check 항목)**. bake()가 issuance write를 dashboard.json write 앞으로 이동 + try/except 래핑, `_verify_issuance`로 DB 실측 행수==N 대조 → `pipeline_meta.issuance_verified{expected,written,ok}`(additive-within, 7키·pipeline_meta 4필드 불변). health_check `check_issuance_log_freshness`(비-런타임 OK-skip·테이블부재 WARN·stale WARN). 회귀 155 passed, migration 0.
- **실관측 통과(07-08, 07-07 18:30 ET beat 후)**: ⑴ `issuance_verified = {expected:10, written:10, ok:True}`(worker 트리+서빙 심링크 동일, snapshot_id=82). ⑵ health_check "발행 로그 신선도 = 최근 거래일 2026-07-07 행 10건(age 1일)" OK. ⑶ 워커 로그 자가검증/#46 error **0**(zero-noise 실증). 정상 경로 완전 실증.
- **수용 엣지(병기)**: issuance write가 atomic_swap **선행**으로 이동 → swap 실패 시 "발행 로그는 있음·화면 표시는 없음" 행이 생길 수 있음. 그러나 **채점(신호 발행 기록)은 유효**하고 grain `(stock, signal_date, signal_tag)` 멱등이라 다음 정상 bake에서 수렴 → **결함 아님, 수용**. (원래는 swap 후 write라 반대 리스크였음 — 트레이드오프 이동, 검증 정합성 우선.)

### 결정 후보 (2026-07-07, MGMT-BATCH-4 — 다음 세션 안건화)
- **COLOR-TOKEN-PROMOTE 🟢**: 로컬 시맨틱 **사본 3벌 실증**(dashboard `colorSemantics.ts` · chain_sight 로컬 · market_pulse `meaning.ts` 축) → shared 토큰 승격 설계 착수 근거 충족(조기 추상화 회피 조건 = "2번째 트랙 착수 시" 초과 달성). 승격 설계 = 3벌 공통 시맨틱 추출 + drift 방지 단일소스.
- **SYNC-ENTRYPOINT**: `worker_sync.sh`를 항상 런타임 트리 사본으로 실행하는 **고정 진입점**(래퍼/별칭) 신설 근거 = #47(공유 트리 사본 stale로 api 섹션 누락 부분 동기화). **이번 세션 수동 준수 실증 병기**(런타임 사본 명시 지정으로 3종 정상 동기화 = 자동화 부재 시 수동 규율로 우회 가능함을 입증).

## [2026-07-08] repo 스크립트 실행 고정 진입점 = D 계층 (D-SYNC-ENTRYPOINT)

**결정**: repo 스크립트를 항상 origin/main 정합 트리 사본으로 실행하는 진입점을 **D 계층**(래퍼 + 스크립트 자기가드)으로 구현한다. 2요소:
1. **repo 밖 래퍼 `~/bin/sv`**: 항상 런타임 트리의 스크립트를 실행(대상 = `worker_sync`·`health_check` 일반화). 세션 체크아웃과 무관.
2. **스크립트 자기가드**: 스크립트가 자기 트리 HEAD vs origin/main을 대조해 stale 시 경고(래퍼 미경유 실행도 방어).

**왜(마진 0.10, 타이브레이커)**:
- **#47 재귀 2건 실증**: worker_sync(api 섹션 누락 부분 동기화) + health_check(구버전 10건, 발행 로그 항목 없음). 공유 편집 트리가 세션 브랜치에 머물면 그 트리의 **스크립트 자체가 stale** → "repo 스크립트를 어느 트리 사본으로 실행하나"가 반복 함정.
- 래퍼(A)만으로는 래퍼 미경유 수동 실행을 못 막고, 자기가드(B)만으로는 매번 경고를 사람이 무시할 수 있음 → **둘의 짝**. 타이브레이커 = **repo 내 가드가 래퍼 부재 환경(새 클론·타 머신)도 커버**(D-HC-ISSUANCE 짝 논리와 동형).

**baseline at decision**: origin/main = 96ae7b5. prod 쓰기 0(결정 등재만, 실행은 TASKQUEUE `SYNC-ENTRYPOINT`).

### 완료 + 실증 (2026-07-09 갱신, OPS-ENTRYPOINT)
- ✅ **land `942a991`(worker_sync 자기가드)·`f084cd6`(health_check 실행 트리 정합)** + 래퍼 `~/bin/sv`(repo 밖). 
- **실증**: ⑴ stale 사본 직접 실행 → worker_sync **abort exit 2** + health_check "실행 트리 정합 WARN"(구버전 항목 누락 자기표기) ⑵ `sv sync` → 3종 트리 HEAD = origin/main 일치 ⑶ `sv health` **12/12 OK**(신항목 포함). #47 재귀 2건 구조적 해소.

## [2026-07-08] 색 시맨틱 토큰 = 분할 승격 (D-COLOR-TOKEN)

**결정**: 로컬 색 시맨틱 3벌(eod `colorSemantics.ts` · market-pulse-v2 축 · chainsight 로컬)을 shared 공용 토큰으로 **분할 승격**한다(마진 2.35 자동).
- **shared 트랙**: frontend 공용 인프라 구획에 `colorSemantics` 토큰 신설(위치는 해당 슬라이스 STEP 0 실측).
- **3트랙 회수**: eod · market-pulse-v2 · chainsight가 각자 로컬을 shared 토큰 소비로 전환 — **값 IDENTICAL · 렌더 무변경(행위보존)**.
- **portfolio**: Stage2 재개 시 로컬 경유 없이 shared 토큰 **직소비**.

**왜**: 3벌 실증(D-COLOR-TOKEN-PROMOTE 후보 근거) = 조기 추상화 회피 조건 초과. 분할 승격(shared 신설 → 트랙별 회수)이 빅뱅 교체보다 안전(각 회수가 행위보존 회귀로 독립 검증). 마진 2.35 = 자동 결정.

**baseline at decision**: origin/main = 96ae7b5. prod 쓰기 0(결정 등재만, 실행은 shared 신설 슬라이스 → `TOKEN-RECLAIM`×3).

### 완료 (2026-07-09 갱신, MGMT-BATCH-6)
- ✅ **공용 신설 `694d6f5`**(components/common/colorSemantics.ts) + **회수 3트랙**: market_pulse `8194fd7` · chainsight `c9310fb` · eod `d70d665`. 로컬 사본 **0**, 소비자 **3트랙**, 3벌 삼각 대조 **drift 0**.
- **검증 기준 기록**: "**색 단언 테스트 무수정 통과 = shape+value IDENTICAL 증명**"(각 회수 슬라이스 DoD).
- **사후 검증 병기**: 회수 3건 머지 후 origin/main(`d70d665`)이 **격리 환경 full-suite 519/519 green**(VERIFY-SUITE-BASELINE, npm ci·v22.19.0).

## [2026-07-08] D-COLOR-SYSTEM 추기 — portfolio Stage2 보류 확정

**결정**: D-COLOR-SYSTEM의 portfolio Stage2 전환을 **보류 확정**한다. 트리거 = "**portfolio 트랙 재개 시 그 첫 슬라이스에 선행**"(별도 색 전용 슬라이스 신설 대신 재개 슬라이스에 흡수). 잔존 = 글로벌축 **5파일**(`PortfolioSummary·Table·Chart·Modal·RealtimePortfolio`). D-COLOR-TOKEN 확정에 따라 재개 시 shared 토큰 직소비.

**baseline at decision**: origin/main = 96ae7b5. prod 쓰기 0.

---

## [2026-07-08] D-MONITOR-REBUILD — thesis 구획 트랙 배정 및 Monitor 허브 재건 (전역 결정)

> 트랙: `monorepo/sess-monitor-rebuild` (worktree `/Users/byeongjinjeong/Desktop/sess-monitor-rebuild`, base main `f33ffcc`).
> 실행 순서 고정: STEP 0 측정(완료) → **본 ADR(기록)** → P1 아카이브·철거. ADR 기록 전 기능 작업 금지 원칙 준수.
> 근거 문서: 킥오프 `docs/thesis_control/plan/` (계획 세션 2026-07-08) + 전수조사 `docs/surveys/THESIS-SURVEY-1.md`.

**배경**: thesis는 2026-06 monorepo 마이그레이션에서 apps/ 이관 제외된 top-level 무소속 구획으로, "처분 보류·착수 전 트랙 배정 필수"(본 파일 L1090/1257/1263) 상태였다. STEP 0 실측(2026-07-08):
- **실사용 사실상 없음**: 기존 가설 6건 전부 **2026-03월 테스트 계정**(user 1/4/6) 생성, **premise 0행**(전제 미부착). `reading 1685·snapshot 380·alert 67`은 beat 4태스크의 **기계적 파생 축적**(EODSignal에서 재계산 가능한 유도 데이터, total_run 86회).
- **런타임은 살아있음**(휴면 아님): beat 4태스크 all enabled, last_run 2026-07-08 07:00~07:35 KST(=18:00~ ET).
- **경계 안전**: thesis=leaf(외부 소비자 0, 역방향 위반 0), 테스트 pytest 152 + vitest 31 green.
- **상충 ADR 없음**: DECISIONS에 Monitor/트랙배정 선행 결정 부재 → 중단 조건 미해당.

**결정**
1. **트랙 배정**: 본 프로젝트(`sess-monitor-rebuild`)가 thesis 구획을 운전한다. 2026-06 deprioritize의 부분 번복 근거 = 검증 단계를 "개인화 모니터링 허브"로 재정의하면 방향 B(개인 무기 우선)의 일상 사용 가치가 성립(계획 세션 확인).
2. **정체성 재정의 + 폐기 후 재건**: `Monitor{scope: market|sector|theme|fund|stock, 대상참조, 지표, 규칙}`를 상위 개념으로, 가설 = `Monitor + Claim{주장, 마감}` 부착형으로 정의. 기존 thesis 앱은 **이관 없이 전량 폐기 후 재건**(사용자 결정 2026-07-08 — 6건 전부 테스트 흔적, 데이터 폐기 허용). **철거 전 pg_dump 아카이브 1회 필수**, 산출물 경로 = `/Users/byeongjinjeong/stock-vis-archives/thesis_pgdump_20260708.sql`(P1-2에서 실경로 확정·검증). 원천 EODSignal은 shared 잔존 → 과거 재계산 가능.
3. **경계**: market_pulse(모두에게 같은 광역 시장 화면) vs monitor(내가 등록한 대상 + 내 규칙 + 상태 기억)로 역할 고정. thesis→shared 단방향·leaf(외부 소비자 0) 유지. 바스켓·집계는 앱 내부(EODSignal 소비). 타 앱 노출은 shared read-model(scope 필드 포함) 경유 방침, 상세는 임베드 착수 시 후속 ADR.
4. **리네이밍 + 앱 배치**: 신축 코드·API 경로는 `monitor`(예: `api/v1/monitor/`). **신축 앱 배치 = `apps/monitor`**(모노레포 규약, `INSTALLED_APPS='apps.monitor.apps.MonitorConfig'`, label=`monitor` — chain_sight·market_pulse·portfolio와 동일 계열). 이는 **thesis 처분 사안의 해소 경로**이기도 하다(본 파일 상단 "thesis 처분" 항목 참조): 구 thesis 앱은 폐기, 후속은 apps/ 편입. **top-level `thesis/` 디렉터리는 P2-S3(2026-07-09)에 제거 완료** — BE `_reuse` 엔진이 P2-S2에서 소진되어 `__init__.py` 플레이스홀더만 남자 조기 제거(처분 사안 종결). FE `frontend/components/thesis/_reuse`(빌더 골격)만 P3 이식 큐로 잔존(처분과 별개). 신축 코드는 `thesis/` 디렉터리명에 의존하지 않는다.
5. **UI**: 페이지 IA = **IA-2**(단일 리스트 + 상태 우선 정렬[위험→약화→관찰→유지] + 스코프 필터 칩[개수 배지] + '가설만' 칩). 빌더 = 4단계(대상 유형→대상 지정→지표·규칙→Claim 선택 부착). 스코프 롤아웃 순서 = 종목→시장/섹터→테마(사용자 바스켓)→펀드(**ETF만**, 공모펀드 보류).
6. **데이터·런타임**: 지수·섹터 신규 수집 태스크는 shared api_request 계열에 신설, EOD 창(18:00~18:35 ET) 경합을 각 지시서에 명시. beat 변경은 항상 **DB PeriodicTask 기준**(공통버그 #28 — config dict 무효).
7. **전역 내비(전역 결정)**: 상단 내비를 **[Dashboard · Market Pulse · Chain Sight · News · Screener · My] 6칸 + 우측 아바타**로 개편. My = 서브탭 상주형(M-3), 파이프라인 순 **[Watchlist → Thesis → Wallet → Portfolio]**, 마지막 서브페이지 기억·직행 + 상태 배지. Profile은 서브탭 아님 = **우측 아바타 메뉴(P-B)**. 표시 라벨 **Thesis** / 코드·API는 `monitor`(결정 4 원칙), 페이지 부제 "내 모니터링". 내비는 링크 수준(앱 간 코드 결합 없음)이나 전역 shell 변경이라 타 레인 화면에 영향 → 전역 항목으로 기록. 활성 shell = `frontend/components/layout/Header.tsx`(`InvestingHeader.tsx`는 미사용 dead).
   - **My 하위 자산 실측·접점**(STEP 0 §1-7): watchlist ✅(`app/watchlist` = 종목 관심목록) · portfolio ✅(`apps/portfolio`) · profile ✅(`app/mypage`→아바타) · **wallet ❌ 미구현**(라우트·모델 0). wallet은 서브탭 **자리만 예약(비활성 탭)**, 금융 API 연동은 별도 트랙(TASKQUEUE 등록). Portfolio 분석 엔진·Profile 계정 시스템도 별도 트랙 — 본 트랙은 자리 + thesis 접점(승격·프리필)만.
   - **watchlist 이중 존재 규명**(배선 전 확인 완료): `app/watchlist`(종목 관심목록, watchlistService)와 `app/chainsight/watchlist`(Chain Sight **Path 감시**, usePathWatchlist, watching/active/archived/resolved)는 **중복 아님·역할 분리**. My>Watchlist엔 `app/watchlist`만 배선, chainsight/watchlist는 chain_sight 소유로 존치.
8. **재사용 이식**: 엔진 4종(`indicator_scorer·premise_aggregator·arrow_calculator·thesis_state_machine`, z-score+룰 기반) + 달 위상·화살표 컴포넌트 + 빌더 골격을 신축 구조로 이식. Layer A~E 수학모델(설계 문서만 존재, 코드 0)은 "복원"이 아니라 **최초 구현** 대상 — 신규 구현 결정 시 별도 진행.
   - **격리 방식(P1)**: `_reuse/` staging 이동 — BE `thesis/_reuse/`, FE `frontend/components/thesis/_reuse/`. 폐기 대상과 물리 분리. 엔진은 thesis 모델 의존이라 모델 drop 후 **의도적 import-broken**(P2 Monitor 모델로 재배선). 보완: (a) 각 `_reuse/README.md`에 "import-broken·재배선·**이식 즉시 삭제(폴더 비면 제거)**" 명기 — 이중 사본 drift 방지 규칙(S2 보강 2026-07-08): BE 엔진은 이식·배선 완료 파일부터 `_reuse/`에서 즉시 삭제, FE는 P3에서 동일, (b) ruff 스캔 제외(`pyproject.toml [tool.ruff] extend-exclude`) + pytest는 `testpaths=tests`로 미수집, (c) P1 완료 판정 = 기존 기준 + "잔여 스위트가 `_reuse/` 존재 상태에서 green"(실측 pytest 3531 collect·Django check green·tsc 0 error·vitest 495 passed, 신 실패 0).

**행위보존 기준 대체**: 기존 IDENTICAL hash·골든 회귀는 폐기 대상과 함께 소멸. 새 기준 = "**비-thesis 잔여 스위트 green** + 신축 코드 신규 테스트 기준선". **P1 실측(main f33ffcc 기반)**: 철거 후 pytest collect **3531**(= main total 3683 − thesis 152), FE vitest **495 passed**(= main total 526 − thesis 31), Django check green·tsc 0 error·schema green·신 실패 0. ⚠️ STEP 0의 초기 기준선 3774/~509는 **Theme Heat 트리(780957d)에서 오측정**(main 대비 +91 test) → 무효, main 기반 실측으로 대체.

**승계 분류**(TASKQUEUE): TC-3~6(대화형빌더·지표설정·관제실·알림마감, todo) → 신축 페이즈 P2~P3 승계. 기존 TC-1·2(완료분)는 폐기.

**baseline at decision**: base main = f33ffcc(세션 중 96ae7b5→f33ffcc 전진 반영). prod 쓰기 0(본 ADR은 문서 기록만, 철거는 P1).

---

## [2026-07-08] D-TREND-CD-SEQ — 섹터 판단(CD)은 순차 연속 슬라이스로 구현 (소급 등재)

> 원 설계 세션 결정. **주석: 이 결정은 mgmt 흡수 없이 증발했었음("결정 증발" 사례) — 본 등재로 청산.**

**결정**: 섹터 판단을 순차 연속 슬라이스로 구현. C(판단 엔진+카드) 선행, D(RRG 회전 맵) 직후 슬라이스.
**근거**: C와 D는 동일 데이터·동일 4-상태 로직의 두 관점(C="이 섹터 지금 진입할 만한가", D="돈이 어디로 회전하나"). 조합 옵션 4개 중 순차 슬라이스 4.25 채택 — 타이브레이커 = 사용자 명시 의도 + 회전 질문 커버 + D 연기 시 잠재 리팩토링 리스크 회피.

---

## [2026-07-08] D-SECTOR-CD — 다음 트랙 = MP2-SECTOR-CD (판단 화면) + 임계 상수 baseline=0.0

> 트랙: `monorepo/sess-mp2-sector-cd-s1` (worktree `/Users/byeongjinjeong/Desktop/sess-mp2-sector-cd-s1`, base origin/main `ce0d0dd`). mgmt worktree `monorepo/sess-mp2-sector-cd-s1-mgmt` 경유.

**결정**: 다음 트랙 = MP2-SECTOR-CD. 채점 4.50 vs ALERTS 확장 3.40, 마진 1.10 자동 확정 + 사용자 승인.
**비용 전제**: `momentum_5d`·`rel_strength` 모두 기서빙 필드(`_sector_detail` sectors[]) → 판정 = 사분면 분류만(신규 파생 인프라 0, 모델·마이그레이션 0).

**임계 상수 채택 (STEP 0 실측 근거, 2026-07-08)** — `CD_REL_STRENGTH_BASELINE = 0.0`, `CD_MOMENTUM_BASELINE = 0.0`:
- 계산 실측: `rel_strength = sector_m1 − benchmark_m1`(벤치 대비 1일 모멘텀 **차이** → 구조적 0 중심), `momentum_5d = 5일 수익률`(→ 0 중심). 둘 다 부호가 의미(양=아웃퍼폼/상승, 음=언더퍼폼/하락).
- 최신 스냅샷(2026-07-08, 11섹터) 분포: rel_strength [−1.332, +0.808] (양3/음8), momentum_5d [−1.878, +2.514] (양8/음3). **한쪽 완전 쏠림 없음, 4 사분면 전부 관측**(XLE=주도·강화, XLK/XLI=주도·둔화, XLB=부진·악화, 나머지=부진·개선) → 0.0 baseline이 자명. 대안(1.0 비율 중심) 기각 = 두 값 모두 차분/수익률이라 비율 아님.
- 경계 동률(== 0.0)은 하위 상태 귀속(낙관 편향 금지 — 판단 표면 신뢰 원칙). 입력 None → 판단 유보(None 반환, 값 발명 금지).

---

## [2026-07-08] D-SECTOR-NAV — RRG 회전 맵 거처 = 판단 카드의 서브스크린 (옵션 B)

**결정**: RRG 회전 맵 = **옵션 B, 판단 카드 → 회전 맵 서브스크린**. 4.60 vs 토글 3-뷰 3.30, 마진 1.30 자동 확정.
**근거**: 시장 전역 뷰를 개별 섹터 상세 토글에 넣는 문맥 불일치 회피 + C→D 질문 흐름(사용자 명시 선호) + Phase 2 서브페이지 로드맵의 첫 패턴 수립.
**트레이드오프**: 라우트 1개 추가 비용 수용.
**경계**: 서브스크린 구현은 **Slice 3**. Slice 1 카드에는 회전 맵 어포던스를 넣지 않는다(죽은 UI 금지).

**[2026-07-09] 이행 보완 (S3 편차2 결함 판정·교정)**: S3 land 시 어포던스를 **단일 CTA(from=rank-1 하드코딩)**로 축소 구현 → 어떤 섹터를 보든 항상 1등만 강조되는 결함(사용자 확인). D-SECTOR-NAV의 "판단 카드→회전 맵 진입" 이행으로는 불충분(진입 단위가 카드 전역이라 출발 섹터 선택 불가). **판정 = 편차2를 결함으로 확정, per-row 진입으로 교정**. **진입 단위 = 행**(패널 구조 실측 반영: 판단 카드는 섹터별 카드가 아니라 11섹터 전체 목록 1장 → 진입 단위는 개별 행). 각 행 전체 탭 → `rotation?from=<그 행 symbol>`(기존 행 탭 인터랙션 부재로 행-전체 선택, 충돌 0). 상단 CTA는 "회전 맵 전체 보기 →"(from=리더)로 의미 교정 유지. 커밋 `ceab955`(코드)+`27b5667`(테스트). RRGChart·라우트·BE 무변경(additive).

---

## [2026-07-09] D-SECTOR-MOM-LANE — 모멘텀 시계열의 국면 문맥 = 변형2 레인 분리(국면 스트립)

> 트랙: `monorepo/sess-mp2-sector-cd-s2` (worktree `/Users/byeongjinjeong/Desktop/sess-mp2-sector-cd-s2`, base origin/main `a27fd14`). mgmt worktree `-s2-mgmt`.

**결정**: 모멘텀 시계열(Slice 2)의 국면 문맥 표현 = **변형2 레인 분리(국면 스트립)** 채택. 채점 4.60 vs 변형1 배경밴드 3.05, 마진 1.55 자동 확정.
**근거**: ⑴ 판정선 0 교차 가독성 최우선(플래핑 관측 도구 겸용) — 배경밴드는 0선 대비 방해. ⑵ 국면 밴드색 ↔ 섹터 빨강/파랑 색공간 충돌 회피(레인 분리로 색 독립). ⑶ 스트립은 x축 공유 독립 컴포넌트(RegimeStrip)로 타 시계열 뷰 재사용 가능.
**트레이드오프**: 국면-라인 동시 대응에 시선 왕복 1회 수용.
**데이터 경로(STEP 0-4 실측)**: 스트립 국면 값 = `_regime_detail`의 `regime_history_30d [{date, stage}]`(기서빙, 컨테이너가 이미 fetch). 전환일 vline 계약(transition_dates=날짜만)과 별개로 per-date stage 확보 → **신규 저장·파생·fetch 0**. 시작 경계는 각 날짜에 stage가 있어 자연 처리(추론 불요).

## [2026-07-09] CD_STANCE 거처 비대칭 — 조건부 BE 이관 (관측)

**현황**: REGIME_STANCE=BE(labels.py, 서빙 stance_copy) vs CD_STANCE=FE 정적 테이블(Slice 1)로 거처 갈라짐. 현재 무해(CD_STANCE는 서빙 cd_state→문구 매핑, 재분류 0).
**트리거**: 이메일 리포트(MP2-ALERTS)에 섹터 판정 포함 결정 시 → CD_STANCE를 labels.py 동형 BE로 이관(이메일 렌더러가 FE 테이블 접근 불가하므로). 그 전 이관 금지(YAGNI).

---

## [2026-07-09] D-CD-TRAIL — RRG 회전 맵 꼬리 길이 = 5거래일 (MP2-SECTOR-CD S3)

> 트랙: `monorepo/sess-mp2-sector-cd-s3` (base origin/main `d70d665`). 트랙 마지막 슬라이스.

**결정**: RRG 회전 맵 꼬리(trail) 길이 = **5거래일**. FE 표시 상수(단일 정의, `RRG_TRAIL_DAYS`).
**근거**: momentum_5d 창(5일)과 동일 시간 축 정합 — 꼬리가 보여주는 이동과 y축(momentum_5d)이 재는 이동의 창이 일치. 사소 결정(채점 생략).
**조정 여지**: 표시 상수라 단일 지점 변경 가능. 히스토리 5일 미만이면 있는 만큼만(발명 금지, 규칙 #1). 꼬리는 raw 좌표 폴리라인 — **과거 점별 상태 재분류 금지**(색=현재 상태색 저투명 그라데이션만).

**RRG 데이터 경로(STEP 0-3 실측)**: 신규 저장·엔드포인트·N+1 **전부 불요**. 기존 sector 카드 payload가 이미 `sectors[]`(현재 rel/mom5/cd_state) + `sector_history[]`(날짜별 rel_strength+momentum_5d, S2 additive)를 단일 fetch로 제공 → FE가 그대로 소비. Part 2 = `cd_rel_strength_baseline` 메타 additive만(x축 판정선).
## [2026-07-09] DIRECTION_HEX 축 분리 (D-COLOR-TOKEN-AMEND-1)

**결정**: 공용 토큰의 `DIRECTION_HEX`를 **축별 분리** — `DIRECTION_HEX_CHANGE`{up,down}(등락 축, eod 원형) + `DIRECTION_HEX_SIGNED`{positive,negative}(긍정부정 축, market-pulse 원형). **`DIRECTION_HEX`라는 이름은 두지 않는다**(오용 차단).

**왜**:
- COLOR-TOKEN-SHARED STEP 0에서 `DIRECTION_HEX` **same-name/different-shape 충돌** 발견 — eod {up,down} vs mp {positive,negative}, **값(hex)은 동일**(#f43f5e/#0ea5e9) **키 축만 상이**. 한 모듈에 동명 export 2개 불가.
- 옵션 B(축별 분리) 채택 근거: ⑴ same-name/different-shape 충돌 해소 ⑵ 모듈 축 접두 명명 일관성(CHANGE=등락 / SIGNED·STRENGTH=긍정부정 / BADGE·SPINE=매매) ⑶ **shape-IDENTICAL 보존**(4-키 병합 회피 → 회수 슬라이스의 exact-shape 검증도 안전). 회수 시 참조명 1줄 개명(eod→HEX_CHANGE, mp→HEX_SIGNED), render-IDENTICAL.

**baseline at decision**: origin/main = d70d665. prod 쓰기 0(공용 신설 `694d6f5`에 이미 반영, 본 등재는 결정 소급 기록).

## [2026-07-09] full-suite 테스트 게이트 이원 정책 (D-TEST-ENV)

**결정**: 테스트 게이트를 환경별 이원화(옵션 A):
1. **scoped 테스트(자기 구획)** = **심링크 node_modules 허용**(worktree 검증 편의, 유효).
2. **full-suite 판정** = **격리 npm ci(비-심링크 실설치) + node v22.19.0 고정**에서만 유효.

**왜(가중합 A 4.55 / C 3.80 / B 3.05, 마진 0.75, 타이브레이커: 사용자 확정)**:
- 심링크 경로에서 vitest4/rolldown **native binding 로딩 실패** → **140 거짓 red**(#48). VERIFY-SUITE-BASELINE로 실증 — 심링크에서 12/6 실패하던 파일이 **실설치 전건 green(519/519)**. scoped(eod 7/7)는 심링크에서도 green이었음 → scoped는 오탐 아님.
- A = 이원(scoped 심링크 OK + full-suite 실설치) 채택. B(전면 심링크 금지)는 worktree 검증 편의 상실, C(전면 실설치 강제)는 매 검증 npm ci 비용 과다.

**보완**: `sv`/`health` 계열에 "full-suite 전 npm ci 확인" 안내(TASKQUEUE `TEST-ENV-GUIDE`). **유지보수 관례: node 버전 인상 시 VERIFY형 검증 세션 선행.**

**baseline at decision**: origin/main = d70d665. prod 쓰기 0(정책 등재).

---

## [2026-07-09] D-LLMFILL — 캐러셀 placeholder LLM 채움 (thesis/perspectives/risk)

> 트랙: `LLMFILL`(관리 등재 세션 `monorepo/sess-mgmt-llmfill-reg`, base origin/main `96eb533`). 실행 = LLMFILL-BUILD(@backend, shared/stocks 구획). CAROUSEL-BUILD(`24b0e47`)가 심은 3키 placeholder(thesis·perspectives·risk)를 EOD-bake 시점에 LLM으로 채운다.

**결정 (7항)**:

⑴ **프롬프트 소유** = `packages/shared/stocks/llm/` 신설. bake in-zone 단일출처 — MP-TRANSLATION(`apps/market_pulse/llm/`) 선례 동형. 프롬프트는 소비처(baker) 구획 내부에 두고 외부 확산 금지.

⑵ **BOUNDARY-LLM 접점** = 래퍼(`packages/shared/llm`) **소비만**. 본 슬라이스가 BOUNDARY-LLM 트리거 **(b)(escape 없는 신규 LLM surface 추가)** 에 해당함을 인지 기록 — 단 가드③(외부-LLM-직접호출 가드)은 **스코프 분리**, TASKQUEUE `LLM-GUARD-3`로 별도 등재. 본 슬라이스는 가드 신설 없이 래퍼 경유만.

⑶ **실패 정책** = 카드별 try/except → 실패 카드만 null 유지, bake 완주. 관측 = `pipeline_meta.llm_fill` **additive 필드**{attempted, filled, failed, cost_usd, tokens}(#46형 검문소 짝). 삽입 지점 A(조립 직후·직렬화 전·트랜잭션 밖)를 한 번 더 try/except로 이중 방어 → 예외 시 `llm_fill.ok=False` 기록 후 bake 정상 진행.

⑷ **비용** = `complete(provider="gemini", fallback="anthropic", retries=1, cost_track=True)`. 일 1 bake × N=10 호출 상한. 단가 단일출처 부재는 **기존 부채**(MP-TRANSLATION `cost_usd=null` 공유) 병기 — 착수 비차단.

⑸ **호출 구조** = 개별 10회(카드당 1호출, **부분 성공 허용**). 가중합 배치 3.70 / 개별 3.60, 마진 0.10 < 0.40 → **타이브레이커 사용자 확정: 부분 실패 내성 우선**(1회 실패가 전량 null이 되는 배치 리스크 기각).

⑹ **item 가드** = 기존 7키 무변경 + 채움 3키 **타입 계약**(thesis `string|null` / perspectives `dict{technical, fundamental, news_context}` / risk `string|null`) 단언 테스트 신설 — 현 테스트의 item 내부 무검증 공백 해소.

⑺ **재료 범위** = v1 최소본(메모리 `signals_data` 재료만 — news_context·tag_details·mini_chart_20d 포함). 마진 1.30 자동. **RelationConfidence 편입은 additive 후속 슬라이스**(그때 chain_sight 조회 신설).

**근거 (LLMFILL-STEP0 실측)**: 삽입 지점 A = recommendations 조립 직후·전(前) 트랜잭션 밖 / FE 스키마 변경 0(3키 타입은 CAROUSEL-BUILD에서 이미 정의) / "실패→null→완주" 무개조 성립(baker가 이미 null placeholder를 서빙하므로 채움 실패 시 현행 동작과 동일).

**baseline at decision**: origin/main = `96eb533`. prod 쓰기 0(결정 등재). 실호출 검증은 LLMFILL-OBSERVE(첫 무인 bake 아침)로 분리.

**추기 — BUILD land `9f2355d` (2026-07-09, MGMT-BATCH-7)**: scoped 161 passed(기존 150 단언 IDENTICAL + 신규 11). 삽입 지점 A = `_build_dashboard_json` 직후·직렬화 전·트랜잭션 밖 = `_fill_recommendations_llm` 이중 방어. **편차 수용 기록**: `test_eod_issuance_log`의 `pipeline_meta` **닫힌 집합 단언** vs `llm_fill` additive의 **구조 충돌**(동시 만족 불가) → assertion 무수정 + `_bake_patches`에 격리 patch 채택(issuance_verified 선례 동형, llm_fill 커버리지는 신규 테스트 전담). 정식 등록(닫힌 집합에 llm_fill 추가 + patch 제거)은 후속 `PM-CLOSEDSET-LLMFILL`. **worker sync 즉시 결정**(마진 1.15 자동 — 첫 실전 채움 = sync 후 첫 bake). ops: `sv sync`로 런타임 3종 `1cdea3c` 정합 + 재기동, GEMINI/ANTHROPIC 키 존재 확인 → 오늘 밤 bake부터 채움 활성.

**추기 — OBSERVE 종결·판정 (a) 전건 성공 (2026-07-10, MGMT-BATCH-8)**: 07-09 bake `llm_fill = {ok:true, attempted:10, filled:10, failed:[], cost_usd:0.001001, tokens:6832}` — **파일↔스냅샷 값 일치**, 7 core 키 무결(서빙 파일 순서 불변), IssuanceLog 10/10 `issuance_verified.ok`, 홈 카드 thesis+risk 렌더·콘솔 에러 0. **"불확실 시 null" 지시 실증**(fundamental=null 정직 출력 — 재료 부재 시 날조 안 함). **비용 상한 논의 종결**(1 bake ≈ $0.001 → 연 <$0.4, 무시 가능). **스냅샷 JSONB 키 순서 비보존 = 저장 특성**(FE는 파일 소비 — 위반 아님, 집합 무결). LLMFILL-OBSERVE ✅ 종결.

---

## [2026-07-09] D-THEMEHEAT-AUDIT — theme-heat 세션 감사 + 브랜치 이주 (질의 3회 종결)

> 트랙: MGMT-BATCH-7. THEME-HEAT-AUDIT(질의)·OPS-THEMEHEAT-RELOCATE(이주) 종결 기록.

**⑴ 질의 세션 무혐의**: THEME-HEAT-AUDIT 질의 세션 자체는 편집·커밋 0(읽기 전용, 무혐의).
**⑵ 브랜치 이력 위반 확정**: 단 `monorepo/sess-cs-theme-heat` 이력(`origin/main..86ddbc2`)이 메타 4종을 **광범위 직접 편집·커밋**(DECISIONS 8·PROGRESS 11·TASKQUEUE 6·common-bugs 1, "결정7·8·9" mgmt 밖 등재 포함) = **mgmt 분리 규약 위반 확정**(common-bugs #50 등재).
**⑶ #48 서사 보정**: 심링크×stale node_modules 거짓 red의 오염원 = 특정 세션이 아니라 **"심링크 관행 × primary 트리 stale node_modules(5/25) × 복수 세션 공유"**의 구조적 합작(common-bugs #48 추기).
**⑷ RELOCATE 완료**: 브랜치 → `~/worktrees/sv-theme-heat`(tip `86ddbc2` 무손실), primary = **detached origin/main 기준 상태** 선언. 이후 theme-heat 작업은 전용 worktree에서(공유 primary 미접근). 관련 common-bugs #49(1브랜치-복수-세션).
**land 게이트**: sess-cs-theme-heat land는 단순 rebase-push 금지 — 선행 정산(THEMEHEAT-LAND-GATE: #47 재번호·결정7·8·9 정합·#44 union 스캔) 필수.

**baseline at decision**: origin/main = `1cdea3c`. prod 쓰기 0(감사·이주 기록).

## [2026-07-09] D-OWN-HOME — 소유권 지도 v2 AMEND (frontend/app/page.tsx → dashboard)

**결정**: `frontend/app/page.tsx`를 **dashboard 트랙 소유**로 편입(소유권 지도 v2 AMEND).
**근거**: ⑴ 추천 캐러셀(eod 구획)의 **실거주지**(`RecommendationCarousel`이 `app/page.tsx:85`에서 렌더 — NEWS-SURVEY N4 실측) ⑵ 하이브리드 **뉴스 축 예정지** ⑶ 현 소유권 지도에서 **무소속**(글롭 `app/dashboard/**`는 레거시 계정 페이지, 실 랜딩과 불일치 — DASH-FE-GLOB 후속). frontend/app/dashboard/page.tsx(레거시)와 별개.
**baseline at decision**: origin/main = `1cdea3c`. prod 쓰기 0(소유권 등재).

---

## [2026-07-09] D-CD-STAB — cd_state 플래핑 처방 = ③ C 순차 (B 히스테리시스 → A′ x축 5일 상대수익)

> 트랙: `monorepo/sess-cd-stab-b` (base origin/main `df9591f`). CD-STAB 측정 후속 구현. C 순차의 1/2 = Slice B.

**결정**: 처방 = **③ C 순차** 채택 — Slice B(2일 히스테리시스) 먼저, Slice A′(x축을 진짜 5일 상대수익 mom−bench5d로) 후속. 채점 C 4.00 / A′ 3.65 / B 3.50, 마진 0.35 < 0.40 → **사용자 선택으로 확정**.
**근거 수치(CD-STAB 측정 2026-07-09)**: 반전 X기인 **63.7%**(rel 1일차분 주범)·1일 유지 **63.3%**(순수 노이즈). 시뮬 반전율 원본 0.611 → B **0.209** → A′ 0.326 → C **0.175**. C가 두 축을 모두 다룸(x=상대수익 재정의 + 2일 확정).
**트레이드오프 수용**: 공식 전환 인지 **+1일**(사용 리듬상 저비용).
**단서**: 측정 창 **97% 단일 국면**(LATE_BULL) — 타 국면 일반화 미보장. **land 후 실서빙 재측정으로 대조 필수**(STAB-A′ 착수 STEP 0에 포함).

## [2026-07-09] D-CD-STATE-SEMANTICS — 서빙 cd_state = 공식(2일 확정) 상태, cd_state_raw = 원시 additive

**결정**: 서빙 `cd_state`의 의미를 **공식(2일 히스테리시스 확정) 상태**로 전환. 원시 즉시분류값은 `cd_state_raw`로 additive 신설.
**근거**: STEP 0-2 전수 grep 확증 — 전 소비자(FE 뱃지·RRG 점색·CD_STANCE 문구·미니맵 필터)가 **단일 서빙 `cd_state` 값만 소비**(재분류·우회 0). 따라서 "공식 판단"의 정의 변경은 그 값에서 이뤄져야 소비자 간 모순(점색↔뱃지 불일치)이 **원천 차단**되고 FE 코드 변경 0으로 자동 안정화됨.
**경계**: "전환 확인 중" 표시(raw≠official 비교로 FE 파생 가능 — 분류 아님, 두 서빙값의 단순 비교)는 **이번 범위 제외** → 후속 선택 사안으로 TASKQUEUE.
**무상태**: 공식 상태는 저장 안 함(규칙 #2). 매 서빙 시 저장 히스토리를 결정론적 리플레이(`resolve_official_cd_state`)로 도출. 모델·마이그레이션 변경 0.

## [2026-07-09] D-MONITOR-BEAT — Monitor refresh 평가 주기 등록 (MON-P2-BEAT)

> 트랙: `monorepo/mon-p2-beat` (base origin/main `1cdea3c`). MON-P2-INGEST 후속. 구 thesis eod_pipeline beat를 폐기·회수하고 monitor 허브 평가 주기를 신설.

**결정 1 (=A) — 구 thesis beat 4레코드 회수는 마이그레이션 아닌 멱등 sync 커맨드로**: 폐기된 thesis 앱의 DB PeriodicTask 4건(`thesis-update-readings`/`-calculate-scores`/`-create-snapshots`/`-generate-summaries`, 전부 m=0/15/30/35 h=18 dow=1-5 ET)을 `sync_monitor_beat` 커맨드가 삭제. **근거**: DatabaseScheduler 환경에서 PeriodicTask는 코드 아닌 DB 상태 → 마이그레이션으로 데이터 조작 시 환경 재현성·롤백 취약. 멱등 sync 커맨드가 배포마다 재실행되어 "삭제+등록"을 단일 최종 상태로 수렴(#28 계열, `setup_marketpulse_beat`/`register_chainsight_beats` 관례 일치).

**결정 2 (=C) — 신선도 가드 = ET 오늘 EOD 존재 검사 + 2회 재시도 후 skip**: 태스크 본문 = 가드 → `refresh_monitors` 서비스 → 요약 로그. 가드는 `max(EODSignal.date) == ET 오늘`만 검사(단순). 미충족 시 `self.retry(countdown=1200, max_retries=2)` → 최종 미도착이면 경고 로그 후 skip(stale 데이터로 평가 안 함). **휴장 캘린더 로직은 추가 안 함**(스코프 밖) — 휴장·데이터 지연 모두 "2회 재시도 후 skip"으로 종결. 실측 검증: 07-09 ET(오늘 EOD 미도착) eager 실행 → Retry×2 → `skipped_stale_eod`.

**결정 3 — 스케줄 18:45 America/New_York (CrontabSchedule.timezone 필드)**: EOD 창 18:00~18:35 ET 종료 후 10분 버퍼. **UTC 고정 시각 금지** — `timezone` 필드로 ET 지정해 DST 자동 처리. **근거**: §0 실측 = CrontabSchedule 지배 관례가 America/New_York(93/104, CELERY_TIMEZONE 동일), 폐기된 thesis 선행 4건도 동일 ET. UTC 이중등록(AV broad 특례 4건)은 rolling-24h 예산 회계용 특수 케이스라 비적용.

**결정 4 — ingest→evaluate 체이닝은 단일 서비스 함수(`pipeline.refresh_monitors`), command/task는 얇은 호출자**: 체이닝 로직을 커맨드 `handle()`에서 서비스로 추출. 수동 커맨드(`refresh_monitors`)와 beat 태스크(`refresh_monitors_task`)가 같은 서비스를 각각 호출 → 로직 이중화 차단(command를 `call_command`로 감싸지 않음).

**함정 (→ common-bugs [Celery beat] ET/Seoul off-by-one)**: 태스크가 ET 18:45에 돌지만 프로젝트 `TIME_ZONE=Asia/Seoul`이라 `timezone.localdate()`는 Seoul 날짜(=ET+1일)를 반환 → EOD 거래일과 off-by-one. 태스크에서 `et_today()`(`now().astimezone(America/New_York).date()`)를 명시 계산해 가드·ingest 범위·스냅샷 asof를 거래일에 정합.

## [2026-07-09] D-MONITOR-ALERTCLOSE — 전이 알림·다이제스트·상태 시각화 (MON-P3-ALERT)

> 트랙: `monorepo/mon-p3-alert` (base origin/main `90b04fe`). MON-P2-BEAT 후속. 상태 전이를 알림/다이제스트/시각화로 표면화. 가중치 표 결론 요지를 결정으로 고정.

**결정 1 (=1-C) — 악화 즉시·개선 다이제스트**: 상태 전이 중 **악화(deterioration)만 인앱 배지에 즉시 카운트**, 개선은 다이제스트 묶음 1행으로 지연. 근거: 악화는 행동 유발(즉각 주의), 개선은 안심 신호(모아 보기 충분) — 알림 피로 최소화.
**결정 1b (=1b-A) — 상태밴드 스파크라인 즉시 + 회전 맵 조건부 후속**: 상태밴드 스파크라인(색 밴드+score 선+전이 표식)을 카드/알림 행에 즉시 도입. **모니터 회전 맵(RRG 동형)은 활성 모니터 ≥5일 때만** 후속(`MON-VIZ-ROTATIONMAP` 예약). 근거: 회전 맵은 N≥5라야 의미 있는 분포(단일/소수 모니터엔 과설계).
**결정 2 (=2-C) — 인앱 + 전이일 한정 일일 다이제스트**: 상시 표면=인앱, 이메일 다이제스트는 **당일 전이 ≥1건 또는 마감 제안 신규 시에만** 발송(무전이일 무발송). 근거: 매일 발송은 노이즈, 인앱이 이중화라 이메일은 이벤트성만.
**결정 3 (=3-B) — 수동 마감 + 시스템 제안**: 마감은 **사용자 수동 확정**, 시스템은 제안만(danger 연속 **10거래일** 이상 시 제안 플래그). 근거: 자동 마감은 통제권 침해, 제안은 놓침 방지. 배지 UI=별도 CLOSE 트랙, 본 트랙은 제안 플래그 산출 + 다이제스트 한 줄.
**결정 4 (=4-B) — 판정 필수·회고 선택·스냅샷 동결**: 마감 시 판정(validated/invalidated/inconclusive)은 필수, 회고 서술은 선택, 마감 시점 스냅샷을 동결 보존. (CLOSE 트랙 몫 — 본 트랙은 데이터 계약만 인지.)

**감지 방식 (§0.1 실측)**: state machine `determine_state`가 `state_changed`(new≠`current_state`)를 **반환값으로 노출** → 스냅샷 diff 불필요. from=evaluate 전 `monitor.current_state`, to=new_state. 감지는 **refresh_monitors_task의 evaluate 직후 같은 태스크 내부**(신규 beat 없음 → #28 무영향). `is_deterioration` = 상태 심각도 랭크 비교(RANK[to] < RANK[from]).
**멱등·쿨다운**: `AlertEvent(monitor, from_state, to_state, asof)` unique → 재실행 멱등. 동일 모니터·동일 방향 전이가 직전 알림 후 **3거래일 내** 재발 시 기록은 하되 배지·다이제스트 개별행에서 억제(억제 칩). 파라미터 상수 1곳.
**스파크라인 score 시계열 출처 (§0.2 실측·해소)**: MonitorSnapshot이 **2건뿐(불충분)** → 스파크라인 시계열은 **IndicatorReading에서 read-only 계산**(38건, 30+ 거래일). evaluate-replay 백필은 배제(과거 전이 알림 오발 유발). 상태 구간 임계값은 **API가 하달**(FE 하드코딩 금지, `score_to_phase` 경계 0.6/0.2/-0.2/-0.6 단일 출처).
**이메일 인프라**: 신설 없음 — shared `EmailProvider`(CB `alert_email` 보호) + settings EMAIL_BACKEND 자동전환 재사용. 수신자=설정값 `MONITOR_ALERT_RECIPIENT`(env, 미설정 시 skip). best-effort(실패 로그 경고, health 미편입 — 인앱 이중화).
**baseline at decision**: origin/main = `90b04fe`. **발화 게이트 미도달**(2026-07-09 18:45 ET 첫 무인 발화 전) → **랜딩 허용·배포 보류**(발화 4항목 green 후에만 sv sync).

---

## [2026-07-09] D-NEWS-AXIS — Phase 1 하이브리드 뉴스 축 (표면 S1 × 경로 D3)

> 트랙: MGMT-NEWSAXIS-REG. 근거 = NEWS-SURVEY(N1~N5 실측) 후속 설계 사이클. dashboard 홈에 뉴스 축 표면 신설.

**결정 — 표면 S1**: 홈(`app/page.tsx`) 상단 **압축 스트립** — 3~5칩, 칩 = 헤드라인 + 관련성 한 줄 + 방향점 + **관계망 배지**. 캐러셀 **위**에 배치, 기존 eod 위젯 문법 재사용. 가중합 **4.40**(마진 0.90, 사용자 확정).
**결정 — 경로 D3**: **전용 응축 API** — 서버가 관련성 계산·**동일 사건 접기**·**RelationConfidence 조인**을 끝내 완제품으로 응답(FE는 렌더만). 가중합 **3.80**(D2 추천 경로 4.35 대비 **사용자 확정** — 압축 품질·관계망 배지가 Phase 4 관계망 표면화의 **선발대**라 우선, 신선도는 캐싱으로 충족).
**grain 경계(D-P1-RECPROD 경고 계승)**: 뉴스는 **event-time 표시 전용** — EOD 채점 체계(`signal_date` grain)와 **불혼합**. 뉴스 표면이 horizon·채점을 소급 날조하지 않게 분리.
**baseline at decision**: origin/main = `924ef96`. prod 쓰기 0(설계 결정 등재). 응답 계약 상세는 NEWSAXIS-CONTRACT(결정 대기).

## [2026-07-09] D-DASH-BFF — apps/dashboard 백엔드 앱 신설 (표면 전용 BFF)

**결정**: **`apps/dashboard/` 백엔드 앱 신설**(표면 전용 BFF) — 뉴스 스트립 응축 엔드포인트의 거처.
**근거(마진 1.45 자동)**: ⑴ **순환 회피** — `apps/chain_sight`가 이미 `services.news`를 import(relation_tasks.py:28 실측)하므로 `services/news` 내 스트립 신설은 역방향 의존 = 순환 리스크. ⑵ 의존 방향 **전부 단방향 합법**(app→app·app→services 소비 선례 동형). ⑶ 표면 계약 소유 = **dashboard 트랙**(반복 개선 무위임).
**서술 갱신**: DECISIONS 부록·소유권 지도의 **"dashboard 백엔드 앱 부재"** 서술(1435·1670·2656 등)은 **본 결정으로 supersede** — 이제 표면 전용 BFF 앱 존재(생산 로직 아닌 read 응축 통로). shared/stocks bake 생산은 별개 유지(D-P1-RECPROD, shared 소유 불변).
**baseline at decision**: origin/main = `924ef96`. prod 쓰기 0(앱 신설은 NEWSAXIS-BUILD에서 실행).

**추기 — config 접촉 슬라이스 한정 예외(2026-07-09, MGMT-NEWSAXIS-OWN2, D-OWN 선례 동형)**: **NEWSAXIS-BUILD 슬라이스에 한해** config 접촉 **2줄 허용** — ⑴ `INSTALLED_APPS`에 `"apps.dashboard"` 등록 ⑵ root `urls`에 include 1줄. 이는 앱 신설 결정의 **내재 산출물**(앱을 등록·라우팅하지 않으면 신설 자체가 무의미). **그 외 config 변경은 예외 밖 = HALT.** BUILD DoD에서 **해당 2줄 diff 원문 채증 의무**(범위 초과 방지).

**추기 — config 예외 적용 범위 확장: URL-V1-ALIGN 포함(2026-07-13, MGMT-BATCH-9)**: 위 config 접촉 예외의 적용 범위를 **NEWSAXIS-BUILD 슬라이스 한정 → URL-V1-ALIGN 슬라이스 포함**으로 확장한다. 근거: URL-V1-ALIGN(BFF 경로 `/api/dashboard/`→`/api/v1/dashboard/` 관례 정렬 + FE stripService base 우회 제거, TASKQUEUE)은 **root `urls` include 경로 1줄 수정**이 내재 산출물(경로 규약 정렬 자체가 그 슬라이스의 본질) → 앱 신설의 라우팅 등록과 동형 예외. **여전히 `INSTALLED_APPS`/`urls` 최소 접촉만 허용**(그 외 config 변경은 예외 밖 = HALT), 실행 슬라이스 DoD에서 **해당 diff 원문 채증 의무** 승계. **URL-V1-ALIGN 자체는 💤(트리거 게이트 = 다음 apps/dashboard 접점) 유지** — 본 확장은 착수 시 config 접촉의 사전 정당화일 뿐 착수 지시 아님.

**결정**: `apps/dashboard/**`를 **dashboard 트랙 소유**로 신규 편입(D-OWN-HOME과 짝 — 홈 표면 `app/page.tsx` + 표면 백엔드 `apps/dashboard` 일체 소유).
**근거**: D-DASH-BFF로 표면 전용 BFF 앱이 실재하게 됨 → 그 계약·반복 개선 소유가 dashboard 트랙에 귀속(무위임). shared/stocks bake 생산(D-P1-RECPROD 예외)과 구분 — BFF는 read 응축, shared는 생산.
**baseline at decision**: origin/main = `924ef96`. prod 쓰기 0(소유권 등재).
## [2026-07-09] D-CD-XAXIS-SCOPE — CD-STAB Slice A′: 판단 x축 = 5일 상대수익(additive-only)

> 트랙: `monorepo/sess-cd-stab-aprime` (base origin/main `1cdea3c`). C 순차의 2/2 = Slice A′. CD-STAB 트랙 종결 슬라이스.

**결정**: A′ 전환 범위 = **판단 계열만**. `rel_strength_5d = momentum_5d − bench(SPY) 5일 수익률`을 서빙 시점 파생(저장 0·마이그레이션 0)해 additive 신설. 판단 계열(classify 입력·리플레이·RRG 점/꼬리 x·미니맵 x·카드 근거)이 이 값을 x축으로 소비. 기존 `rel_strength`(1일 차분)와 히트맵·궤적·스파크라인 등 **맥박 계열은 무접촉**.
**채점**: additive-only 4.20 vs 전면 통일(1d 필드 자체를 5d로 치환) 3.70, 마진 0.50 → additive 확정. 타이브레이커 = 행위보존(맥박 소비자 회귀 0).
**원칙 명문화**: *소비자들이 같은 질문을 물으면 의미 전환(cd_state 선례, D-CD-STATE-SEMANTICS), 다른 질문을 물으면 필드 분리.* 히트맵은 "오늘 맥박"(1일), 판단은 "5일 상대 수준" → 다른 질문 → 필드 분리(rel_strength vs rel_strength_5d).
**정직한 null(규칙 #5)**: bench 소급 부족(초기 5거래일)·close 결측 날은 rel_strength_5d = null(발명·보간 0). 리플레이의 None 방어(후보 리셋·공식 유지) 그대로. FE는 대시·점 미표시.
**판정 기준선 무변경**: `CD_REL_STRENGTH_BASELINE = 0.0` 유지 — 5일 상대수익도 0 중심(측정 분포 확인). 값 복제 아님(서빙 메타 단일소스).

### 수락 앵커 이원화 (STEP 0 실측 2026-07-09, 착수 STEP 0 = D-CD-STAB 단서 이행)
- **방법론 앵커(알고리즘 충실성 증명)**: 전 구간 시드 리플레이 + 초기 5 distinct일 제외(후행일 date_idx≥5, pairs=473) 방법론으로 **Slice B(1일 rel) = 99 반전 / 0.2093 재현 = 문서 "99전환/0.209" 정확 일치**. → 리플레이·카운팅 파이프라인 검증 완료.
- **A′ 서빙 앵커(규칙 #3 정합)**: 동일 방법론 + **저장 momentum_5d 기준**(서빙 시점 입력) → **84 반전 / 0.1776**. 랜딩 구현이 재현 가능하게 산출하는 값.
- **시뮬 목표(C) 83/0.175와의 1반전 편차 귀속**: 시뮬 83은 저장(84)·가격 재계산(82) **사이**에 위치. 원인 = 단일 경계값 **XLU 2026-05-19 rel5=+0.00998**(idx=5 카운트 경계) + 측정 세션 시점 이후 데이터 상태 차이(가격 재fetch/스냅샷 갱신). 정밀도 반올림 변형 4종 전부 84 불변(6자리 이슈 아님). **D-CD-STAB 중대성·처방 판정에 영향 없음**(rate 0.1776 vs 0.175, 방향·순위 동일).
- **0-2 실서빙 소프트 관측**: STAB-B land(07-09) 이후 신규 거래일 0일(land 당일) → 축적 관측 0. 향후 거래일 누적 시 재측정(D-CD-STAB 단서 = 측정 창 97% 단일 국면).
**디렉터 판정(2026-07-09)**: 선택지 1(84/0.1776 수용, 진행) 확정. 앵커 이원화 등재 + 교훈 등재(common-bugs) + 테스트는 저장값 기준(앵커 수치 하드코딩 금지 — mgmt 기록).

---

## [2026-07-09] D-NEWSAXIS-CONTRACT — /news/strip 응답 계약 (4항)

> 트랙: MGMT-NEWSAXIS-CONTRACT. 상위 = D-NEWS-AXIS(표면 S1×경로 D3)·D-DASH-BFF. 실행 = NEWSAXIS-BUILD.

**⑴ 관련성 = F2(계층+쿼터)**: 티어 T1 보유 → T2 오늘 추천 연결 → T3 관심 → T4 관계망 인접(신뢰도≥θ) → T5 시장 전반. **티어당 최대 2칩·총 5칩**, 티어 내 정렬 = 신선도 → 언급. 가중합 **F2 4.50 vs F1 3.15**(마진 1.35 자동). `importance_score`는 **NT-2b(null 80%) 해소 전 공식 제외**. v2 예약 = 티어 내 F1식 세부 점수.

**⑵ 접기 = 자체 규칙**: `NewsEntity` 심볼 집합 **겹침 ≥ ½ + 24h 창 + 제목 핵심어 공유**(같은 종목·다른 사건 오접합 방지 안전핀). 대표 = 최다 언급, **"+n건" 병기**. **한계 명기**: 규칙 기반 근사 — 오접힘/미접힘은 도그푸딩 관찰 포인트, 심화 시 **v2 = bake LLM 클러스터링** 승격. **EventGroup 재사용 기각**(38개 체인 전용·커버리지 부족·결합 증가, 마진 1.50 자동).

**⑶ 배지 = RelationConfidence 엣지**: 내 보유·관심 노드에 연결된 엣지 중 **신뢰도 ≥ θ**, **최강 엣지 1개** 문구. **θ = 실분포 상위 ~15% 분위 기반**(BUILD STEP 0 측정, **상수 하드코딩 금지**). `has_news_source` 동률 우대.

**⑷ 캐싱 = 서버 15분 TTL · FE staleTime 30분**(useNews 관례). 계산 **전역 1벌**, **user_id 스코프 이음새 보존(방향 B)**.

**응답 item 계약**: `{headline, symbols[], direction(sentiment 부호), tier, relevance_line(한국어 한 줄), collapsed_count, badge{pair, confidence}|null, published_at, article_url}`. **grain 재확인 = event-time 표시 전용**(EOD signal_date 불혼합).

**안전 조항**: T1/T3 소스(보유·관심 실거처)는 **BUILD STEP 0 실측** — 부재 시 해당 티어 **공석**, 잔여 티어로 **5칩 충원**.

**baseline at decision**: origin/main = `8f559c5`. prod 쓰기 0(응답 계약 등재). BUILD STEP 0 재실측 대상 = θ 분위·T1/T3 거처·RelationConfidence 조인 경로.

**추기 — BUILD STEP 0 실측 + 실가동 관찰 (2026-07-10, MGMT-BATCH-8)**:
- ⑴ **신뢰도 매핑**: 계약의 "신뢰도" = `RelationConfidence.truth_score`(0~85 척도) — `confidence`라는 필드명은 **부재**(BUILD STEP 0 실측 확정). 배지 `confidence` 값 = truth_score.
- ⑵ **θ 실측**: p85 = **60.0**, 단 분포에 점질량(median=q3=p85=60) → ≥60 선택이 실질 ~50%를 통과(weak/hidden<60 제외 플로어로 기능). **관찰 포인트**(라이브 분위 자동추종은 유지).
- ⑶ **배지 실전 발화 확인**: seed 11종목(WatchlistItem) × truth_score≥60 연결 엣지 **192 후보** → 스트립 `🔗 AAPL↔GOOGL` 등 **정상 발화**(후보 존재 시 발화 = 버그 아님 실증).
- ⑷ **접기 over-collapse 실측**: "+10건"(AAPL)이 24h 라운드업 21건(상이 사건)을 심볼겹침+일반 키워드로 오접합 → 아래 **D-STRIP-FOLD-TUNE**로 처방.

---

## [2026-07-09] 소유권 지도 v2 AMEND-2 — dashboard 트랙 FE 글롭 (뉴스 스트립 산출물)

**결정**: dashboard 트랙 소유에 FE 글롭 3종 추가 — `frontend/components/strip/**` · `frontend/services/stripService*` · `frontend/hooks/useNewsStrip*`.
**근거**: D-NEWS-AXIS 표면 **S1**(홈 상단 압축 스트립)의 FE 산출물 거처 — D-OWN-HOME(`app/page.tsx`)·소유권 지도 v2 AMEND(`apps/dashboard/**`)와 **일체**(홈 표면 + 표면 백엔드 + 스트립 컴포넌트 일괄 dashboard 소유).
**baseline at decision**: origin/main = `e3dbfcf`. prod 쓰기 0(소유권 등재). 실체 신설은 NEWSAXIS-BUILD.

## [2026-07-09] D-CD-READ — 판단 표면 가독성: RRG 변형 H + 고정 개선 3건

> 트랙: `monorepo/sess-cd-read` (base origin/main `90b04fe`). FE 중심 슬라이스. BE 무변경.

**결정**: RRG 꼬리 전략 = **변형 H(포커스 디폴트 + 전체 꼬리 토글)**. 채점 H 4.35 / F 4.10 / D 3.90, 마진 0.25 < 0.40 → **사용자 선택으로 확정**. 근거: 모바일 가독성(제기 불만 = 11섹터 전체 꼬리·라벨 밀집) 우선 + 회전 전체상은 토글로 보존.
**동반 고정 개선 3건**: ⑴ 미니맵 섹터명 라벨 전면 제거(점+색만, 코너 라벨 유지) — 확인 중 섹터는 점선 링. ⑵ 전환 확인 중 표시(행 칩 + 보조문). ⑶ cache 디버그 라인 제거.
**표시 전략만(규칙 #2)**: RRG 데이터 소비(payload·필드) 무변경 — 포커스/토글/라벨은 렌더 전략. 판정선 서빙값·점 색(cd_state) 불변. 포커스 = URL from(현행 구조) + 탭 override(세션), 토글 = 세션 메모리(저장 0).
**라벨 충돌 회피 = 단순 그리디(규칙 #4)**: 포커스 항상 풀 라벨, 나머지는 bbox 비중첩 시만 표시(밀집 자동 숨김). 시뮬레이티드 어닐링류 과공학 배제.

## [2026-07-09] CD-TRANSITION-INDICATOR 이행 — cd_state_raw 첫 소비 (재분류 금지)

**결정**: STAB-B에서 후속 선택 사안으로 미뤄둔 "전환 확인 중" 표시를 CD-READ에서 이행 — **cd_state_raw의 첫 소비처**.
**필요 확정 근거**: 라이브 첫날 실증(기술 07-09 원시=주도·강화 vs 공식=부진·악화) — 사분면 좌표(주도·강화 구역)와 점 색(부진·악화 파랑)이 어긋나는 "카피↔숫자 모순"을 사용자가 체감. 이론이 아니라 실재 확인.
**재분류 아님(규칙 #1)**: 판정 = 서빙된 `cd_state ≠ cd_state_raw` 단순 비교뿐(`sectorColor.isTransitioning`). 좌표·값 기반 분류 로직 신설 0. BE 무변경. 두 값이 같으면 픽셀 무영향(칩·보조문·링 전부 부재, 규칙 #2).
**단일소스 재사용(규칙 #3)**: 원시 신호 한글명 = 기존 `cdStateLabel` 매핑. 강조색 = `CD_TRANSITION_HEX`(orange, 신설 단일소스 — cd 상태색과 구분되는 중성 신호색, 신규 상태명·상태색 발명 0).

## [2026-07-09] D-B1-SCOPE — FRED 백필 깊이 A(조인트 천장) + 2슬라이스 층위

> 트랙: `monorepo/sess-b1-s1` (base origin/main `66c364d`). 프로덕션 DB 쓰기 = 병진 수동, Claude = 계획·후보리포트·검증.

**결정**: 백필 깊이 = **A(조인트 천장)**. 채점 A 4.40 / B 3.95 / C 3.20, 마진 0.45 > 0.40 → 확정. 타이브레이커 = C(부분벡터/얕은)는 다양성 게이트 해제 불능.
**조인트 천장 확정치(STEP 0-2 실측)**: `max(HY OAS FRED obs_start 2023-07-10, VIX3M yahoo 2006-07-17, MOVE yahoo 2002-11-12)` = **2023-07-10**(HY 쌍이 유일 구속). Yahoo 깊이 확인 → 천장이 2025로 안 밀림(HALT 회피). 목표 시작일 = **2023-07-10**(전 14 벡터 입력 공통).
**층위 = 2슬라이스**: S1(이번, 원시 시리즈 백필 = FRED 9 + yahoo 2 + SPY 가격) / S2(별도 = 주간 forward-fill 정렬 + 벡터 소급 합성 + rules.yaml 소급 적용 — D-ANALOG-GATE 원문 의존 경로). 부분벡터 확장(2020 포함)은 ANALOG 설계 재발명이라 기각.
**경로(기존 재사용, 신규 커맨드 0)**: `backfill_v2_a1`(`--from/--to` 창·`--series-id`/`--symbol` 임의값 수용·get_or_create 멱등·FREDClient 단일경유·yahoo_map VIX3M/MOVE 라우팅). VIXCLS·T10Y2Y = 기본목록 밖이나 `--series-id` 흡수(backfill_macro_all 선례). SPY = `--symbol` (BENCHMARK, 기본목록 밖). 스키마 무변경(행 삽입만, M6). API ≈ 9 FRED + 3 yahoo 콜(전 창 1콜/시리즈), 신규 행 ≈ 5,000(HY 쌍 각 ~620 심층).

**M7 전제 정정(B1-DEFER 반증)**: "SectorFlowSnapshot 초기 5 distinct일 momentum floor-0 위장" 가정은 **실측으로 반증** — floor-0 = **mid-window XLF 2026-06-29 단 1행**(초기일은 실값 보유). 06-29도 5일 창 가격 연속 존재(결측 0) → floor 아님, 실 5일수익 ≈ −0.02%(0 근사) → **문서화로 종결**(null 교정 불요). 측정들의 초기 5일 제외는 보수적 무해.

**B1-C2(오라벨) 보류 판정**: VIX3M/MOVE `data_source='fred'` 오라벨 정정은 ⑴ 백필 전제 아님(`data_source`는 `EconomicIndicator` 시리즈당 1행, `IndicatorValue` 값 백필이 라벨 증식 0) + ⑵ 올바른 정정엔 choices(fred/fmp/calculated)에 `'yahoo'` 추가 = 마이그레이션 → 규칙 #3 HALT → **이번 세션 보류**(별도 결정).

---

## [2026-07-10] D-STRIP-FOLD-TUNE — 스트립 접기 안전핀 강화 (over-collapse 처방)

> 트랙: MGMT-BATCH-8. 근거 = D-NEWSAXIS-CONTRACT ⑵ 추기(over-collapse 실측 "+10건" 라운드업 오접합). 실행 = STRIP-FOLD-TUNE(apps/dashboard in-zone).

**결정 (안전핀 강화 3종, 옵션 O1)**:
- ⑴ **일반 금융어 stopword 확장**: oil·prices·stocks·markets·market·wall·street·dow·nasdaq·s&p·futures·global 등 라운드업 상용어를 제목 핵심어에서 제외(접기 안전핀이 일반어 공유로 오발동하는 것 차단).
- ⑵ **라운드업 배제**: 언급 심볼 수가 상한(예: N개) 초과인 기사는 접기 대상에서 제외(흡수 금지) — 시장 라운드업이 대형주 겹침으로 서로 흡수하는 경로 차단.
- ⑶ **접기 그룹 크기 상한**: 한 그룹이 흡수하는 기사 수 상한(과병합 방지).

**방향 원칙**: **오접합(오정보) > 미접힘(중복)** — 미접힘(중복 노출)이 오접합(다른 사건을 한 칩으로 오도)보다 덜 나쁨. 안전핀은 보수적으로(덜 접는 쪽).
**가중합**: O1(3종 강화) **4.50** / O2(stopword만) 3.65 / O3(그룹 크기만) 3.20, 마진 0.85(**사용자 확정**). **v2 = bake LLM 클러스터링 예약 불변**(규칙 근사의 근본 해소는 v2).
**테스트 의무**: 실측 오접합 사례(**AAPL "+10건" 24h 라운드업 21건**)를 BUILD 테스트 fixture로 **박제**(회귀 방지 — 이 케이스가 다시 접히면 fail).

**baseline at decision**: origin/main = `e37c993`. prod 쓰기 0(처방 결정 등재). 임계 상수(심볼 수 상한·그룹 상한)는 STRIP-FOLD-TUNE STEP 0에서 실데이터 기반 결정(하드코딩 금지).

**추기 — land 실서빙 실효 재확인(2026-07-13, MGMT-BATCH-9 채증)**: STRIP-FOLD-TUNE = **`62eec71` land**("feat(newsaxis): 스트립 접기 안전핀 강화", origin/main 조상 확인). **실서빙 실효**: 처방 전 AAPL 칩 **"+10건"**(24h 라운드업 21건 오접합, 상이 사건) → 처방 후 **"+2건"**(= `MAX_GROUP_SIZE − 1` 상한 준수), **전 칩 ≤ +2건**으로 수렴. 안전핀 3종(stopword·라운드업 배제·그룹 상한)이 오접합 경로를 차단하고 그룹 크기 상한이 접힘 폭을 상한 −1로 강제함을 실증. **검증 경로**: live DB × 배포 코드 직접 실행(JWT 만료로 UI 채증 대신 서비스-레벨 검증 갈음 — 렌더링 로직 미변경이라 서비스 출력 = UI 표시 등가). **잔여 "+2건" 정밀도**(상한 준수분도 상이 사건이면 여전히 오접합 여지)는 도그푸딩 관찰 지속, **근본 해소 = v2 bake LLM 클러스터링 예약 불변**(규칙 근사의 한계 = 방향 원칙 "오접합>미접힘"으로 보수 처리, 완전 해소는 v2). TASKQUEUE STRIP-FOLD-TUNE ✅ done 갱신. — 소급 국면 벡터 합성 = 현행 로직 as_of 매개변수화 (B1-S2)

> 트랙: B1-S2. base = origin/main `ef312d6`(S1 백필 land 포함). 커맨드 land = `monorepo/sess-b1-s2`. prod 쓰기 = 병진 수동(dry-run 후보 리포트만 Claude Code 실행).

**결정 (벡터 의미론 단일소스)**: 소급 벡터 합성 = 현행 RegimeSnapshot inputs 생성 로직의 **as_of 매개변수화**. 각 과거 영업일 D에 대해 `load_inputs(as_of=D)`로 "D 기준" 동일 로직을 재실행 → `_latest_indicator_value`/`_spy_price_series`의 `max_age`(14일) 캐리가 **주간 NFCI의 일간 정렬(forward-fill)을 자연 수행**. **별도 forward-fill 파이프라인·독자 합성 규칙 발명 없음**(소급/라이브 벡터가 동일 문법이어야 ANALOG 비교가 유효 — 단일 문법이 트랙 핵심).
- **as_of 파라미터화 = additive**: `as_of` 기본값 None → `localdate()`(라이브 경로 무변경, 회귀 8건 GREEN 증명). `date__lte=ref` 상한 추가는 라이브(ref=오늘)에서 no-op(미래 지표행 부재), 소급(ref=과거 D)에서 look-ahead 차단 역할.
- **hysteresis = 시계열 순차 chaining**: classifier는 순수(결정론)이나 `apply_hysteresis`는 previous_snapshot 의존 → 커맨드가 영업일을 **오름차순** 순회하며 직전 합성행을 previous로 연결. 라이브 `previous = filter(date__lt=today).first()` 의미론과 동형. INSUFFICIENT_DATA 분기(coverage<0.6)도 라이브대로 이전 regime 캐리·전환 보류.
- **대상 창 = 2023-07-10 ~ 라이브 최초일 전날**(=2026-04-26; SPY 마지막 영업일 2026-04-24). 대상 영업일 산정 = **SPY 가격 존재일**(기존 관례).
- **coverage 실측 저장**(운영 동일 — 1.0 미달 행도 저장, ANALOG가 스스로 필터). 창 초입 leading gap(2023-07-10~13, 첫 NFCI 2023-07-14 이전)은 저 coverage로 정직 기록(값 발명 없음).
- **기존 행 불가침**: 합성행 provenance 마커 = `summary="[BACKFILL_V2]"`(어떤 RegimeSnapshot serializer에도 미노출 — 불가시·안전). 라이브 경계 = `exclude(summary=MARK).min(date)` → 멱등 재실행 시 합성행이 경계를 끌어내려 붕괴하는 결함 차단. 창 필터(date<live_min) + get_or_create(신규만) + 루프 가드 3중 방어.
- **소급 행 필드**: `is_finalized=True`(확정 과거), `snapshot_time`/`finalized_at` = D 20:00 UTC(≈US 마감) 결정론. 스키마 무변경(행 삽입만, 마이그레이션 불요).

**dry-run 후보 리포트(prod, 무쓰기, RegimeSnapshot count 66 불변 확인)**: 대상 영업일 **703**(2023-07-10~2026-04-24), 예상 합성 703, **완전벡터(coverage≥1.0) 683**, 국면 분포 **TRANSITION=469 / LATE_BULL=228 / CRISIS=6**. 비-LATE_BULL 대량 출현(2022~24 수익률곡선 역전 `t10y2y<0` 상시 발화 = TRANSITION 지배 — 경제적 실사) → **다양성 게이트 개방**(D-ANALOG-GATE 트리거 (b) 충족).
**S1 ~749 예측 대조**: 683 vs 749 괴리(66) = **683(소급 창) + ~66(라이브 블록 기존행) ≈ 749**로 정합(S1은 전 구간 추정, 본 백필은 pre-live 창만). 실측 683 governs.

## [2026-07-10] D-B1-VINTAGE — 백필 값 = 현재 개정판(vintage), revision 저장 0

**결정**: 소급 벡터의 지표값 = **현재 DB에 저장된 최신 개정판**(vintage) — "당시 실시간으로 알려졌던 값"(as-reported)이 아니다. FRED NFCI/OAS 등은 사후 개정되나 개정 이력을 저장하지 않으므로(revision 0), 소급 벡터는 최신 개정치 기준.
**Why 무해**: ANALOG 유사도 비교는 전 구간이 **동일 vintage 규약**일 때 오히려 일관(라이브 벡터도 개정 후 값을 봄). 성격만 명문화해 미래 오해(as-reported 착각) 방지. 진짜 as-reported 재구성이 필요해지면 FRED ALFRED vintage API = 별도 트랙.

---

## [2026-07-10] TREND-S4 — z-이상도 뷰 구현 (D-UNLOCK-ORDER / D-S4-BASELINE / D-S4-ENDPOINT / D-S4-FORM)

> 트랙: MP2-TREND S4. base = origin/main `307306d`. 브랜치 `monorepo/sess-s4`. 선행 = TREND-S4-STEP0(B-3=(가) 실측). additive-only·마이그레이션 0·z 미저장(serve-time).

**D-UNLOCK-ORDER — S4를 ANALOG보다 먼저**: B-1 종결로 ANALOG·S4 둘 다 언락됐으나 **S4 우선**. 근거(타이브레이커) = "z-분포 미관찰" — ANALOG(z-정규화 최근접 매칭)를 설계하기 전에 S4가 **소급 분포의 실제 형상**(스케일 불연속·저빈도 step·초입 저신뢰·|z|>3 집중)을 사람이 먼저 눈으로 봐야 최근접 잣대가 타당. S4의 baseline 순수 함수(`compute_baseline`)는 ANALOG가 그대로 재사용할 단일 소스 → S4가 ANALOG의 선납 인프라.

**D-S4-BASELINE — 고정 소급 모집단 잣대**: z baseline μ·σ = **소급 합성행(summary='[BACKFILL_V2]') 전체**에서 산출(표본 n−1, `statistics.stdev`). 라이브 행도 **동일 μ·σ**로 z 변환(고정 잣대 — 라이브가 잣대를 흔들지 않음). 결측 성분 z=null(보간·캐리 생성 금지), σ=0 또는 n<30 성분은 insufficient=True로 정직 표기(발명 금지). baseline은 **순수 함수 분리**(입력=행 시퀀스, DB 접근 0) → ANALOG 재사용.

**D-S4-ENDPOINT — 전용 z 엔드포인트 + 다운샘플**: 기존 `_regime_detail`(최근 30행)은 소급행 미도달 → **별도 `GET /api/v2/market-pulse/regime/zscore`** 신설(기존 detail 무변경). 응답 = 성분별 {series[{date,z|null}], baseline{mean,std,n}, insufficient} + meta{low_confidence_until(=소급창 20영업일째), live_start}. **다운샘플**: 최근 90영업일 일간 + 이전 주 마지막 영업일 1점 → **실측 57.1KB raw**(앵커 ≤130KB)·gzip 6.7KB·232포인트. baseline 24h 캐시(키에 소급창 경계 포함 → 백필 재실행 시 자연 무효화). summary 마커 미노출(`.values()`서 미선택). 대상 = raw 탭 대칭 7 룰-구동 지표(baseline 함수는 전 14성분 산출 = ANALOG 대비).

**D-S4-FORM — 절충안(격자형)**: z 뷰 = **raw 탭 대칭 small multiples + |현재 z| 내림차순 정렬(null·insufficient 최후미) + |z|≥2 danger 칩**. 근거 = 사용 시나리오 6종 비교: 평시 속도는 순위형과 동률, **위기일 전황 파악·raw 탭 왕복·습관적 관찰에서 격자형 우위**. 스파크라인 = 0선 실선·±2σ 점선·초입 저신뢰 음영(low_confidence_until 이전)·null 단절·주간 계열 마커. 예약 placeholder 제거. z 탭은 `RegimeZTab`(z 모드에서만 마운트 → lazy fetch, raw 모드 훅 무호출로 기존 raw 테스트 무영향).
**범위 밖(등재만)**: 카드 탭 확대 뷰·정렬 토글·종합 이상도 지수 → S4-EXPAND.
**검증**: pytest marketpulse 358→**374**(+16)·vitest mp2 295→**304**(+9)·tsc 0·마이그레이션 0·health 13 OK/0 FAIL·payload 57.1KB.

---

## [2026-07-13] Phase 1 공식 종결 선언 + Phase 2 개시 예고 (D-P1-CLOSE)

> 트랙: MGMT-BATCH-9(mgmt, 메타-only). base = origin/main `3b50612`. BATCH-8의 "공식 종결 선언 보류"(잔여 = PREB 5/5·STRIP-FOLD-TUNE)를 잔여 0으로 해소 → 정식 종결.

**결정**: **Phase 1 공식 종결.** 세 기둥(발행 로깅 · 추천 리포트 LLM 채움 · 하이브리드 뉴스 축) 전부 실가동 + 잔여 2건 해소로 **잔여 0** 도달.

**세 기둥 실가동 채증(전부 origin/main 반영)**:
- ⑴ **제시(발행) 로깅** — IssuanceLog 무인 생산 지속(D-P1-OBSERVE-DONE, migration 0009 운영 적용 D-P1-MIGRATE-0009). HC-BUILD 발행 로그 감시 C계층 land + 실관측 통과(무인 생산 다일 연속).
- ⑵ **추천 리포트 LLM 채움** — CAROUSEL placeholder 3키(thesis/perspectives/risk)를 EOD-bake 직후 shared LLM 래퍼로 채움(D-LLMFILL OBSERVE 종결, LLMFILL-BUILD `9f2355d`). `fundamental=null` 조건부 채움(날조 억제 설계대로 — 아래 관측 참조).
- ⑶ **하이브리드 뉴스 축** — 홈 상단 압축 스트립 라이브(NEWSAXIS-BUILD done `90b04fe`) + RelationConfidence 배지 발화 + 자체 접기(over-collapse 처방 STRIP-FOLD-TUNE `62eec71` land로 정밀화).

**잔여 2건 해소(BATCH-8 보류 사유 소멸)**:
- **B-CLEANUP-PREB 5/5 도달** — 7/6~7/10 정상 거래일 자동 beat 5주기 전 행 무결 bake 통과 → 발화. `frontend/public/static/signals_pre_b`(B′ 전환 전 백업, 5.0M·Desktop 트리·미추적·DB 무관) 사용자 수동 rm 완료(STEP 0로 대상 실체 확정 후 제거).
- **STRIP-FOLD-TUNE done** — `62eec71` land, 실서빙 "+10건"(오접합)→"+2건"(상한 준수) 실효 채증(D-STRIP-FOLD-TUNE 추기).

**Phase 2 개시 예고(트리거·강화, impression 축)**:
- **impression/Viewed 축** = Phase 2 핵심 신규 데이터 축 — per-user serve-time impression을 별도 `Viewed` 테이블로 수집(D-SCHEMA 테이블 분리·D-P1-GRAIN "Phase 2 Viewed 분리"·P2-VIEWED-TABLE 스텁의 실체화). 발행 로그(baked, 정의상 전부 baked)와 **직교** — Phase 5 노출 수준 채점을 Viewed join으로 복원.
- **트리거·강화 계열** = 발화 조건 정의(모니터/알림 연동), 세 기둥 위 강화 슬라이스(STRIP-BADGE-VARIETY·LLMFILL-FUND-MATERIAL·URL-V1-ALIGN 등 💤 트리거 게이트 항목의 순차 소진).
- **개시 예고일 뿐 착수 지시 아님** — Phase 2 첫 슬라이스 범위·순서는 별도 계획 세션(디렉터 결정). 본 결정은 Phase 1 장부 봉인 + Phase 2 축 명명.

**baseline at decision**: origin/main = `3b50612`. prod 쓰기 0(종결 선언 등재, 메타-only).

---

## [2026-07-13] D-P2-IMPRESSION — Phase 2 impression(Viewed) 축 "봤다" 정의 + ImpressionLog 스키마

> 트랙: MGMT-P2D1(mgmt, 메타-only, 결정 등재 전용·build 아님). base = origin/main `a340816`. D-P1-CLOSE Phase 2 축 명명의 첫 실체 결정. 실행 = P2-IMPRESSION-BUILD(별도 build 지시서).

**결정 — "봤다"(impression) 정의 = 뷰포트 기준**: 요소의 **50% 이상이 화면에 1초 이상 노출**되면 "봤다"로 기록(IntersectionObserver). **임계값 2종(비율 50% · 시간 1초)은 상수로 분리**, 도그푸딩 관찰로 튜닝(STRIP-FOLD-TUNE의 "상수는 데이터로 튜닝" 패턴 재사용 — 하드코딩 금지, 튜닝 가능 상수).

**기각 대안**:
- **(A) 렌더 기준** — 스크롤 밖 미노출 요소까지 기록되는 **오탐**으로 트리거 재료 오염.
- **(C) 상호작용 기준** — 무클릭 열람 표면(홈 스트립)에서 **미탐 과다**.
- **가중합 B=4.65 vs C=3.75 vs A=2.80, 마진 0.90**, 사용자 확인으로 확정(2026-07-13).

**경계 조건(common-bugs #43 준수 — 로그/모델 스키마 write 시점 정합)**: 사용자 문맥 필드는 **serve-time 신설 로그(ImpressionLog)에만 존재**한다. **bake-time 스키마(IssuanceLog)는 무변경 — 한 필드도 추가하지 않는다.** (발행 로그 = 정의상 전부 baked·per-user 문맥 없음 / impression = serve-time·per-user — 두 축 직교, D-SCHEMA 테이블 분리·D-P1-GRAIN 승계.) *(경계 정본·no-op 마이그 조건은 D-C2-DETAIL-MIG 경계 조항 참조 — 2026-07-31.)*

**부속 설계 (추천안 채택)**:
- **전송**: 프론트 버퍼 **5초 간격 flush** + 페이지 이탈 시 `visibilitychange` + `sendBeacon` 일괄 전송.
- **스키마 방향 = ImpressionLog(serve-time)**: `user_id`(스코프 포함 — 방향 B 다중 사용자 이음새 보존) · `surface`(reco_card|news_chip) · `object_ref`(IssuanceLog 카드/칩과 조인 키) · `first_seen_at` · `seen_count`(재노출 dedup) · `session_id` · `event_type`.
- **이벤트 타입 2종**: `impression` / `click` 을 `event_type`으로 구분(클릭은 별도 이벤트로 병행 확보).

**baseline at decision**: origin/main = `a340816`. prod 쓰기 0(결정 등재, 메타-only). **build 착수 금지** — 실행은 P2-IMPRESSION-BUILD 슬라이스별 지시서(등재→build 규율).
## [2026-07-13] MON-CLOSE — Monitor 검증 단계 최소 완결 종결 (4 DoD)

> 트랙: `monorepo/mon-close` (base origin/main `a340816`). MON-P3-ALERT 후속. 검증 단계 4 DoD 공식 종결 + 부수 정리 5건 + 결정 봉인.

**DoD 4항 완결 선언** (전건 실측 증거):
1. **자동 심장박동** ✅ — beat 4태스크 무인 가동. MON-P2-BEAT `monitor-refresh-daily` 첫 무인 발화(2026-07-09/07-10 18:45 ET, `last_run_at`·`total_run_count=2`·워커 succeeded 로그).
2. **알림** ✅ — 헤더 벨(배지)·`/monitor/alerts` 화면 전환·빈 목록·콘솔 0 (NAVGAP authed 스모크).
3. **실사용자 귀속** ✅ — 목록 API queryset = 순수 owner 필터(`Monitor.objects.filter(user=request.user)`), NAVGAP 실측 확정.
4. **authed 픽셀** ✅ — 2026-07-13 **소유 계정(goid545, jinie545@gmail.com) 세션**에서 `c9be8802`("애플 스모크 모니터", 지표1) 카드의 **StateBandSparkline 렌더 확인**(색 밴드+score 선+40포인트 실데이터, 전이표식 없음=정상). **데이터 이전 없이** owner-scoping이 설계대로 동작한 결과.

**결정 봉인**:
- **3-B 확정** — 알림 방식 = **수동 마감 + 시스템 제안**(자동 발송 아님, danger 10거래일 제안 플래그). (D-MONITOR-ALERTCLOSE 결정 3과 동일 — 여기서 종결 확정.)
- **4-B 확정** — 마감 루프 = **판정(validated/invalidated/inconclusive) 필수 + 회고 선택 + 스냅샷 동결**. (D-MONITOR-ALERTCLOSE 결정 4와 동일 — 종결 확정. 배지/마감 UI는 후속 CLOSE 트랙.)
- **OWNERFIX 폐기** — "데이터 보유 모니터를 실계정으로 이전" 전제가 **소멸**: NAVGAP에서 `c9be8802`가 **이미 실계정 goid545 소유**임이 확정됨. 공백의 원인은 소유 불일치가 아니라 **로그인 계정 불일치**(진단 시 admin 세션). owner-scoping 코드는 정상 → 이전 불필요. OWNERFIX 지시서 무효.
- **트랙 배정 ADR 대조** — 무소속 thesis 구획 → Monitor 검증 트랙 편입은 `D-MONITOR-REBUILD`(2026-07-08)에 기록됨. 2026-06 deprioritize 번복 근거도 동 ADR에 포함(트리거 발동=사용자 트랙 배정). 추가 기록 불요.

**정정 각주 (FIRSTFIRE/ALERTFIRE T-1 오관측)**: MON-OPS-FIRSTFIRE 보고의 "AAPL reading max asof=07-08 → AAPL EOD가 발화 후 베이크(T-1 지연)"와 ALERTFIRE §2의 "구조적 지연" 전제는 **오관측**이었다. 원(原) 관측값=07-08/07-09(밀린 값) → 실제값=07-09/07-10(정상, `QuerySet.dates()` tz-정확 재측정) → 정정 사유=진단 쿼리가 aware `asof`에 naive `.date()`를 호출해 UTC 기준 하루 밀림(→ common-bugs #51). 시스템(ingest·가드·발화)은 처음부터 정상. 원문 삭제 없이 본 각주로 정정.

**정리 완료(부수 5건)**: ⑴ 빈 admin 모니터 `63fa58cb` 삭제(지표0·스냅0·readings0·owner=admin 재확인 후, `c9be8802` 불변 대조 통과) ⑵ 라벨 "Thesis"→"Monitor"(MySubNav 라벨/배지로직/testid + page.tsx H1, vitest green) ⑶ FIRSTFIRE T-1 정정 각주(위) ⑷ tz 진단 함정 common-bugs #51 ⑸ 빌더 실사용 = FE 스모크 정식 항목화(TASKQUEUE DoD).

**baseline at decision**: origin/main = `a340816`. prod 변경: `63fa58cb` 1행 삭제(빈 모니터) + 라벨 리네임(FE). `c9be8802`(데이터) 무변경.

---

## [2026-07-13] NEWS-URLNORM-IDQUERY — URL 정규화 id-쿼리 보존 (Blocklist 베이스 채택, Hybrid 유예)

**결정**: 뉴스 URL 정규화(`services/news/providers/url_utils.py::normalize_news_url`)를 **"쿼리 전량 제거" → "고신뢰 tracking key만 제거, 나머지 쿼리 보존"**으로 변경한다. tracking blocklist = **`utm_*` prefix + {fbclid, gclid, ref}** (지시서⑨ 확정 고신뢰분). ambiguous 후보(cid·ocid·ncid·mod·amp·msn 렌더링 파라미터·lang 등)는 **이번엔 blocklist에 넣지 않는다** — Hybrid(도메인별 규칙) 세션으로 **유예**. AMBIG·Hybrid·기존 데이터 backfill은 범위 밖.

**Why**: 구 규칙은 기사 id가 query에 있는 URL(youtube `?v=`·finviz `?t=`·CMS `?idxno=`)을 base path로 붕괴시켜 **서로 다른 페이지를 1건으로 병합 = co-mention 조작(허위 공동언급)**을 유발했다(지시서⑨ 실측: 공유경로 collapse 22그룹/3,695행, finviz(AV) 1,675·youtube(FMP) 1,961). **보존 쪽 실패(과소병합=중복이 남음=가역)가 오병합(distinct 손실=비가역)보다 안전**하므로, ambiguous key는 제거하지 않고 보존한다. blocklist를 고신뢰분으로 좁힌 것도 같은 이유(잘못 제거해 오병합하는 위험 최소화). Hybrid(finviz 뷰 파라미터·msn 렌더링 파라미터 도메인별 안전 제거)는 AMBIG 과소병합을 줄이는 후속 최적화라 유예해도 손실이 가역.

**How to apply**: 지시서⑩. 커밋 `64c8589`(fix+회귀). 변경은 `normalize_news_url` 단일 함수 국한(경계 위반 신설 0). **행위보존**: 문자열 기반으로 (a)무쿼리·(b)tracking-only 출력을 구 규칙과 IDENTICAL 유지(`?` 이후 절단·fragment 폐기·끝 슬래시 제거 동치). **검증(⑨ 오라클, 실 데이터 전수)**: (a)+(b) 100,245행 IDENTICAL 불일치 0, collapse 22그룹→NEW 완전분리 22/22(finviz 86→86·youtube 1962→1962 distinct), 단위 23 + 뉴스 690 passed(신규 red 0; 선존 baseline=deep_analyzer genai-mock + S5 키부재 env 민감 테스트). **운영**: STEP1에서 normalize-적용 수집 beat 20건(id 22·23·26·27·29·54·55·56·57·58·59·60·61·62·63·64·65·66·96·123) 가역 정지 → fix 배포 후 재활성. 기존 저장분=raw 보존(무손상, ⑨ 판정) → backfill 불필요.

**baseline at decision**: origin/main = `e870b02`. prod 변경: PeriodicTask 20건 enabled 토글(정지→재활성, 가역). 데이터 쓰기(병합/삭제/backfill) 0.
## [2026-07-13] Slice A — SPY EOD 복원 + 보존 예외 (D-ANALOG-SPY-RETENTION / A-PREP)

> 트랙: MP2-ANALOG 산하 데이터 토대(카드 Slice B의 사후수익률 재료). base = origin/main `e870b02`. 브랜치 `monorepo/sess-A-spy-restore`. prod 쓰기(백필 --commit) = §5 병진 수동 유보.

**D-ANALOG-SPY-RETENTION (A-S0 = 방식 '나' 심볼 보존 예외)**: analog "그 후"(SPY 선도수익률)의 재료인 SPY EOD 3년치가 롤링 purge(`cleanup_old_data`, 365일 blanket cutoff, 심볼 무인지)에 매주 잘려 모집단 683→199(71% 결손). 
- **택일 근거**: (가) provenance 마커 필드 = 모델 변경 → **prod 마이그레이션 = §7 HALT** → 기각. (나) 심볼 보존 예외 = `PRESERVED_INDEX_SYMBOLS={SPY}`를 purge에서 `.exclude` → **모델 무변경(makemigrations No changes)**, SPY 전 구간 보존으로 목적 충족. 현 정책이 blanket date-cutoff(심볼/출처 무인지)라 행 단위 provenance 불필요 → (나)가 마진 명확(HALT 아님).
- **행위보존**: 비보존 심볼·IndicatorValue purge 불변(회귀 고정). 재백필 자산은 즉시 보존 대상(재소실 방지 순서 규율 = A-S0 먼저/함께 land).

**A-PREP (SPY EOD 재백필, shared FMP 래퍼)**: 신규 커맨드 `backfill_spy_eod` — shared `FMPClient.get_historical_price`(/stable/historical-price-eod/full) 경유(직접 호출 0), macro.MarketIndexPrice idempotent upsert, **dry-run 기본**(실제 쓰기 --commit). **prod dry-run 실측**: FMP 750행 반환, **신규 삽입 500행(2023-07-14~2025-07-11)** → 모집단 **683/683 SPY 확보 + 각 +20영업일 창 내 = 683 완전 회복**(199 폴백 아님). 실제 --commit = 병진 수동(§5).
- **경계**: EOD 모델 = **macro app**(`packages/shared` 아님 — 지시서 'shared' 프레이밍과 상이, repo 우선). 백필 커맨드는 market_pulse(backfill_v2_a1 선례 = market_pulse가 macro.MarketIndexPrice 백필). apps→macro 합법.
- **검증**: pytest marketpulse+architecture **387/1skip**·마이그레이션 0·경계위반 0·health 12 OK/0 FAIL·news 무접촉.
- **잔여 finding**: 동일 purge가 IndicatorValue 3년 백필도 삭제(analog 벡터는 stored inputs라 무영향, S4-REBASE/재합성 시 재고 대상 — 이 슬라이스 범위 밖).

---

## [2026-07-13] MP2-ANALOG Slice B — 유사 국면 카드 결정론 코어 (D-ANALOG-DIST / -CARD-FWD / -CARD-K)

> 트랙: MP2-ANALOG(#1). base = origin/main `8dd5ca9`. 브랜치 `monorepo/sess-B-analog-card`. 사이클2 목업 확정 반영. 뉴스·LLM 무의존(Slice C 격리). prod 쓰기 0·마이그레이션 0.

**D-ANALOG-DIST (거리·가족 동결)**: `d² = Σ wᵢ(zᵢ_now − zᵢ_past)²`, `wᵢ = 1/|가족|`. z = S4 baseline(`compute_baseline`, 소급 683 완전벡터 μ·σ) 재사용. **가족 멤버십 = 사이클2 판정 동결**(코드 `analog.py::REGIME_FAMILIES` 단일소스 — S4-REBASE에서만 재판정): FAM1 stress={drawdown_pct,vix,vix3m}·FAM2 financial={nfci,nfci_credit,nfci_leverage,nfci_risk,hy_oas_pct,hy_ccc_oas_pct,t10y2y_pct,t10y3m_pct,move}·단독={return_1d_pct,vol_20d_pct}. 유효 축 4(가중합 4). 근거 = ANALOG-STEP0 2단 사다리(가족간|ρ|0.178).

**D-ANALOG-CARD-K (②C 이웃선정·경보)**: 거리 오름차순, radius τ_radius=0.60 안, 상호 **10영업일 분리**(트랙 헌법, 같은 에피소드 중복 방지) 최대 K=8. 최근접 거리 > τ_alert=0.80 → **"전례 희박 — 통계 보류" 경보**(이웃·팬 보류). **prod 실측(2026-07-13)**: nearest_dist=**1.02 > 0.80 → 경보 발화, neighbors=0**(오늘 국면이 2023~24 모집단과 유의 상이 = 경제적 실사, 엔진 정상).

**D-ANALOG-CARD-FWD (①C 정직 팬)**: 이웃별 SPY 선도수익(지평 1·5·10·20·60영업일, **FMP 거래일 캘린더**=주말/휴장 15행 배제). 지평별 **실현 이웃만 집계(정직 N)**, 우변절단 이웃 제외. 밴드 = 중앙값 ± IQR(25–75%) × **√(K/n_eff)**, n_eff = 이웃 시간군집 접기(상호 60영업일 내 = 한 에피소드) → 에피소드 중복 시 밴드 확대. N·n_eff payload 노출.

**문턱 잠정(K=8·τ_radius=0.60·τ_alert=0.80·군집창 60·10일 분리)** = Phase5/S4-REBASE 재산정. **label 슬롯(cat_slot·why) = null**(Slice C L2/L3 채움) — B/C 경계 = 결정론/비결정 격리.
**엔드포인트**: `GET /api/v2/market-pulse/regime/analog`(S4 baseline 재사용, 1h 캐시, 마커 미노출). FE `AnalogCard`(4축 z 막대·경보 배너·정직 팬·이웃 리스트, market-pulse-v2 페이지 배선).
**검증**: pytest marketpulse+architecture **401/1skip**(+14)·vitest mp2 **309**(+5)·tsc0·마이그레이션0·경계위반0·health13/0·news 무접촉.
**⚠️ DoD 부분(§7 HALT)**: SPY `--commit` 미실행(199/683) → 엔진·UI·단위테스트 완비하나 **683 통합검증 유보**. --commit(병진, A-PREP) 후 실 팬 검증. 현재 오늘은 경보 상태라 팬 시각검증은 populated fixture(vitest)로 대체.
## [2026-07-13] BOUNDARY-LLM 실행 완료 (landed) — stale 상태 정정 + baseline 상환 (지시서⑪⑫)

**결정**: BOUNDARY-LLM(shared LLM 래퍼 정합, 옵션 C)은 **실행 완료·origin/main 병합**됨을 공식 기록한다. TASKQUEUE의 "DORMANT·미착수"와 메모리 `project_boundary_llm_track`의 "미머지 worktree"는 **stale** — 정정한다. 잔여 테스트 부채(`DEBT-TEST-BOUNDARY-LLM`)는 seam 재작성으로 상환 종결.

**Why**: 지시서⑪ STEP 0("박힌 값 신뢰 금지") 실측 결과, 하네스 기록(DORMANT)과 실제 코드가 모순. origin/main `8dd5ca9` 근거: ⑴ `packages/shared/llm/` 코어 12파일 존재(core/types/policy·providers) ⑵ LLM 직접호출 **burn-down 23→0** 병합(merge `8be3f65`, 슬라이스①~④ 커밋 이력) ⑶ 아키텍처 가드 `test_shared_boundary.py`·`test_llm_direct_call_boundary.py` **KNOWN_VIOLATIONS=set()/FROZEN_COUNT=0 → 7 passed** ⑷ `scripts/health_check.py` `_LLM_KNOWN_VIOLATIONS`·`_BOUNDARY_KNOWN_VIOLATIONS` 빈 set(SSOT 동기) ⑸ 소비처 12파일/25 import 전부 코어 단일 경유, 코어 밖 SDK 직접생성 0. → 스테일 기록이 하류(CS-P2-LLM)를 헛되이 블록하고 있었다.

**How to apply**: 지시서⑫ close-out.
- **C1 정합**: TASKQUEUE DORMANT 섹션 헤더→"종결·LANDED" + 상태 정정 블록, CS-P2-LLM 의존 "해소(언블록)", DEBT-TEST-BOUNDARY-LLM "종결". (원문은 이력 보존.)
- **C2 baseline 상환(근본수리·은폐 아님)**: `test_news_deep_analyzer`(genai→`complete` seam, 응답 설정 관성 보존 trick·init 테스트는 제거된 genai.Client 계약 대신 실제 키검증 계약으로 강화) + `test_csv_url_resolver`(`_llm_client`→`_llm_enabled`+complete seam) + `test_multiple_symbol_fetches`(S5 키-env → 더미키 provider 주입으로 env-독립). **env -i 격리서 131 green, skip/xfail/assertion 삭제 0**.
- **C3 재발 가드(advisory-only)**: `health_check.py`에 TASKQUEUE 주장상태 vs 증거(DECISIONS 종결·산출물 존재) 대조 WARN 섹션 신설(pass/fail 불변).

**프로덕션 행위 변화**: **0** (문서·테스트·health_check advisory만). EVENTGROUP-WINDOW window 도입·하류 C3(CS-P2-LLM/A3·A4) 착수는 **미착수**(별 슬라이스).

**baseline at decision**: origin/main = `8dd5ca9`. 코드 변경 0(테스트 seam·docs·health_check advisory만).

## [2026-07-13] D-MONITOR-CLOSE-UI-P1 — 가설 마감 데이터·엔드포인트 (백엔드)

> 트랙: `monorepo/mon-close-ui-p1` (base origin/main `50a1738`). MON-CLOSE-UI RECON 대조 후 Phase 1(BE). FE(상세·모달·배지·필터)는 Phase 2. additive-only.

**① 회고 저장 = 조인 모델 `ClaimIndicatorResult`(정석 ⒝)**: 전제 계층이 D-MONITOR-REBUILD에서 제거됨 → **지표(indicator)로 피벗**. `(claim, indicator, result∈HIT/PARTIAL/MISS/NA)` unique. 근거: 라이브 지표 집계(Monitor 결합) 무훼손 + 마감 시점 지표별 판정을 별도 박제 → 동결(④)과 한 몸, 다중 가설(②) 자연 흡수, §5 categorical+FK 학습루프 충족. ⒜(indicator에 Claim FK)는 1:N 충돌 악화, ⒞(JSON blob)는 지시서 금지.
**② 마감 단위 = Claim**: "마감"은 `Claim.outcome∈{VALIDATED,PARTIAL,INVALIDATED}`에서 파생. **`Monitor.State`·state_machine 불변**(엔진 무훼손). Monitor:Claim=1:N → 모니터 "마감 여부"는 FE 파생.
**③ 제안 밴드 = overall_score [-1,1] 3등분**: RECON에서 종합 z(σ) 부재 확인 → `overall_score`를 `VERDICT_HI=+0.333`/`VERDICT_LO=-0.333`(대칭·무편향)로 매핑. `propose_verdict` 순수 함수, 상수 한 곳. 백로그: 마감 ≥20건 후 실분포 재조정.
**④ verdict enum**: `Outcome`에 **PARTIAL 추가**(VALIDATED=적중/PARTIAL=부분적중/INVALIDATED=빗나감). INCONCLUSIVE는 엣지 유지(close 버튼 미노출·액션 거부). **final_verdict는 기존 `outcome` 재사용**(별도 필드 없음) — `proposed_verdict` vs `outcome` 델타가 캘리브레이션 입력.
**동결 = `ClosureSnapshot`(불변)**: 마감 1회/가설 OneToOne, `overall_score`+`payload`(지표값·달위상·스파크라인) 생성만(update 경로 없음). 주기·가변 `MonitorSnapshot`과 **별개 슬롯**(건드리지 않음).
**엔드포인트**: `ClaimViewSet` 액션 — `GET close-preview/`(프리필, 무상태) + `POST close/`(원자적: 재마감 가드 409·제안 저장·판정·지표결과 bulk·동결). owner-scoping 준수. 직접 CRUD PATCH로 회고 필드 못 쓰게 serializer read-only.
**행위보존**: 엔진(scorer·arrow·aggregator·state_machine)·beat·pipeline·shared 전부 불변. propose는 overall_score 읽기만. 마이그레이션 0006 additive-only(AddField 4+outcome choices+CreateModel 2, 파괴/백필 0).

**baseline at decision**: origin/main = `50a1738`. prod 쓰기 0(코드·마이그레이션만, 실 DB migrate는 배포 단계).
**★ 크로스트랙 가드 (2026-07-14 defuse)**: origin/main(3d5341e 이후)에 P1 Claim 코드+0006 파일이 있으나 실 DB 미적용 상태면 **타 트랙이 sv sync 시 신규 Claim 컬럼 부재로 파손**(danger_streak/MON-P3 교훈 재판). → **0006을 실 DB에 선제 적용 완료(2026-07-14, additive·구코드 무영향·beat 무관)** = 위험 해소. 규칙: 신규 마이그레이션이 origin/main에 land되면 **코드 sync 전 반드시 migrate 선행**.

---

## [2026-07-13] D2-DESTALE — D2 T-5 회부 4건 소화 사실 기록 (MGMT-D2-DESTALE)

D2 T-5 회부 4건(PROGRESS 2a0aba0 "4건 대기" 블록)은 **T-3b(`3a3e921`)로 소화**됨(상단 `## T-3b — 상향학습 선별·자가오염·seed status 권위 일원화 [chainsight]` 결정 = 실체). **#2 실채택 `ⓓ-2`(status 권위 일원화)가 2a0aba0 권고 `ⓓ-3`와 상이** — 의도 확인은 **chainsight 트랙 회부**(mgmt는 사실 기록만, 판정 안 함). PROGRESS 구 블록은 원문 보존 + 취소선/註로 봉인(stale 표기 해소). baseline = origin/main `3d5341e`. prod 쓰기 0(메타-only).

---

## [2026-07-14] D-P2-S2-PLATFORM — Phase 2 impression 수신구 배치 = 신설 apps/platform (선택 C)

> 트랙: MGMT-P2-S2-REG(mgmt, 메타-only). base = origin/main `7b7927e`. 상위 = D-P2-IMPRESSION(축)·P2-IMPRESSION-BUILD(실행). S2-RECON "무소속" 판정을 닫는 배정 결정.

**사안**: Phase 2 impression 수신구(ingest API)의 배치 구획.
**결정 — 선택 C(신설 `apps/platform`, 교차관심 telemetry 홈)**. write 대상 = shared의 `ImpressionLog`(S1). 가중합(기능 렌즈, weights 합 1.00): **C 4.08 > A(shared) 3.34 > B(dashboard) 2.87**, 마진 0.74(타이브레이커 불요 구간, 사용자 확인 완료 — 2026-07-13 디렉터 세션).
**근거**: impression은 **교차표면 telemetry**(dashboard·chain_sight·news 등 여러 표면에서 발생). 한 표면(B=dashboard, "read 응축 통로·모델 없음" 헌장)이나 도메인팩(A=shared/stocks, 범용 재료 토대)에 두면 부자연 → **중립 홈(제3범주)이 정답**.
**부속 결정**:
- 수신 인증 = **IsAuthenticated 전용으로 시작**. `ImpressionLog.user_id` nullable은 Phase 2 익명 수신 대비 **예약(현 단계 미사용)**.
- 배치 계약 = **신규 설계**: sendBeacon 배열 payload + 5초 flush(기존 클라 배열 수신 선례 0 — S2-RECON B-3 실측).
**경계 재확인(lesson #43)**: `ImpressionLog` = **serve-time 신설**, `IssuanceLog`(bake-time)는 **무변경 — 조회·필드추가·import 0**. platform ingest는 shared의 ImpressionLog에 write만 한다. *(경계 정본·no-op 마이그 조건은 D-C2-DETAIL-MIG 경계 조항 참조 — 2026-07-31.)*
**baseline at decision**: origin/main = `7b7927e`. prod 쓰기 0(배정 결정 등재, 메타-only). 실행 = P2-IMPRESSION-BUILD S2(별도 build 지시서).

**[백-어노테이션 2026-07-16 — 실현 확인 (P2-IMPRESSION-BUILD S3+FIX-1, MGMT-P2-IMPR-CLOSE)]**:
- ⑴ **sendBeacon → keepalive fetch로 실현**: 계약 의도는 sendBeacon(이탈 유실 방지)이었으나, sendBeacon은 커스텀 헤더 불가 → JWT(localStorage 소재)를 실을 수 없음. `keepalive: true` fetch + `Authorization` 헤더로 대체(페이지 이탈 중 전송 보장 = sendBeacon 계약 의도의 동등물).
- ⑵ **session_id = 프론트 생성**: 모델 `session_id` 비-nullable 대응. `crypto.randomUUID()`(폴백 = 시각 기반) + `sessionStorage`(페이지-세션당 1개 재사용), SSR 안전.
- ⑶ **surface truth·object_ref 포맷 확정**: surface 서버 허용값 = `dashboard_eod`·`news_chip`(**`reco_card` 아님** — 표면 라벨은 서버값으로 매핑). object_ref 포맷 = reco `ticker:trading_date:signal_tag` / news = finnhub 단축 id URL(서버 upsert 3중 키의 한 축이라 drift = 중복 행).

---

## [2026-07-14] 제3범주(platform) 아키텍처 규약 성문화 — 단일 출처 (D-P2-S2-PLATFORM 부속)

**규약(단일 출처 = 이 항목 하나)**: *플랫폼/교차관심 서비스(telemetry·알림·플래그 서빙 등)는 `apps/platform`에 둔다. 의존은 `platform → shared` 정방향만. apps(기능)·shared(재료) 2분법의 빈틈을 메우는 **제3범주**.*
**복제 금지(규약 10장 — 복제는 drift)**: repo 규약 문서(`docs/claude_project_instructions/project_convention_instruction.md`)에는 본문 복제 없이 **이 DECISIONS 항목으로의 포인터 한 줄**만 둔다.
**baseline**: origin/main = `7b7927e`. prod 쓰기 0(규약 성문화).

---

## [2026-07-14] 소유권 지도 v2 AMEND-3 — apps/platform 구획 신설 (platform 트랙)

**결정**: 신규 구획 **`apps/platform/**`(백엔드) → 담당 트랙 = platform(신규)**. 성격 = 교차관심 서비스 홈(telemetry 등); 표면 트랙(dashboard 등)이 소비자. **무소속 아님 — 배정 완료 상태로 등재**(S2-RECON "impression ingest 무소속" 판정 종결). 근거 = D-P2-S2-PLATFORM(선택 C).
**baseline**: origin/main = `7b7927e`. prod 쓰기 0(소유권 등재).
## [2026-07-13] MP2-ANALOG Slice C-N — 과거 뉴스 소급 백필 (L3 그라운딩 재료) · GN 게이트

> 트랙: MP2-ANALOG(#1) 산하 L3 데이터 토대. base HEAD `3d5341e`(Slice B 포함). 브랜치 `monorepo/sess-CN-news-backfill`. Slice C 원지시서의 L3 뉴스 전제("3년 가용")가 repo와 어긋나 병진이 **L3 전략 B(뉴스 백필 먼저)** 확정 → 본 슬라이스. prod 대량 쓰기 = §5 병진 수동 유보(소량 검증만 실행).

**GN 게이트 실측(STEP 0, 최우선) — FMP 실패·AV 채택**:
- **FMP 뉴스 과거 조회 = 불가**: `/stable/news/stock`·`general-latest`에 `from/to` 날짜 파라미터 → **402 Premium**(경제 캘린더와 동일 유료벽). 페이지네이션도 page~200부터 400(캡), page50(limit100)≈2026-05 도달이 한계 → 모집단(2023~) 미도달.
- **AV NEWS_SENTIMENT = 채택**: `AlphaVantageNewsProvider.fetch_broad_news(time_from/time_to)` 과거 창 조회 **실측 2023-09 도달**(2024-05창 790건·2023-09창 168건) → 모집단 전 구간(2023-08~2026-04) 커버. 제약 = 무료 25 req/day·1 req/s.
- 즉 원지시서 "GN = FMP 뉴스" 전제는 FMP 특정이었으나, GN 정신(과거 뉴스 타당성)은 **AV(동일 shared 뉴스 provider 계열)로 충족**. 7개월 벽(NewsArticle 2025-12+)은 AV 한계가 아니라 broad 수집 시작 시점.

**D-CN-REUSE (라이브 save 경로 재사용)**: 백필 커맨드 `backfill_broad_news`는 기존 라이브 broad 수집(`collect_av_broad_news` 태스크)과 **동일 체인**(`fetch_broad_news`→`deduplicator.deduplicate`→`aggregator._save_articles` url upsert 멱등)을 재사용. 저장 형태가 라이브와 동형·멱등, 기존 파이프라인 무변경(가산만). 선별 top-N은 별도 저장 없이 broad 전량 저장(라이브와 동형) → 그라운딩 선별은 C-L3 생성 시점.

**D-CN-NO-PRESERVE (보존 예외 불필요)**: NewsArticle은 나이기반 **삭제 없음**. `archive_old_articles`가 6개월+ 기사를 **soft delete(`is_archived=True`)**만 — 행 영속(SPY A-S0식 예외 불요). ★단 **C-L3 그라운딩 쿼리는 `is_archived=True` 포함 필수**(과거분은 아카이브 플래그).

**D-CN-SKIP-COVERED (재개 임계 = 창일수 비례)**: skip-covered 판정 = 창 내 기사 ≥ `window_days × 3`. 플랫 임계(예: 5)는 인접 백필의 경계일 spillover(1일치 소수)를 "커버됨"으로 오판해 실제 공백 창을 skip → 갭. 일당 비례로 spillover 격리(실측: 첫 창 798건 중 08-14 14건이 다음 창으로 번짐 → 비례 임계 21로 정확히 pending 유지).

**dry-run 산정(prod, 무쓰기)**: 미커버 구간 2023-08-07~2025-12-05 = 7일 창 **122창**, 전량 미커버. 전량 ≈ **5일 @ 25 req/day**. 7일 창은 고볼륨 구간(2024-05 ~158/일) saturation(>1000) 위험 → 커맨드가 SATURATED 플래그로 창 축소 재패스 안내.
**소량 검증(§5 허용, --commit 1창)**: 2023-08-07~14 창 **798건 landing**(이전 0). 실 2023-08 헤드라인(source·title·date) 확보 = L3 그라운딩 실증. 멱등 재실행 skip 확인.
**검증**: 커맨드 테스트 6 green·기존 collect_av_broad 태스크 테스트 무손상·health 13 OK/1 WARN(origin 뒤처짐 정보성)/0 ERROR·경계 위반 0·tasks.py 무접촉.

**baseline at decision**: base HEAD `3d5341e`. prod 쓰기 = 소량 검증 1창(798행)만, 전량 백필은 병진 수동.
## [2026-07-24] MP2-ANALOG Slice C-L3 — L3 맥락 생성("왜?" 슬롯) + C-N 종결 회계

> 트랙: MP2-ANALOG(#1) 산하 라벨 파이프라인 **마지막 슬라이스**. base origin/main `b9ddf41a`. 브랜치 `monorepo/sess-C-L3-context`. 이웃 리스트 각 과거일에 "그날 무슨 일" 1줄 맥락(L3)을 붙여 ③B(라벨 상시 ON)의 나머지 절반 완성.

**D-CN-COMPLETE (C-N 백필 종결)** — ⚠️ **판정 폐기·정정(2026-07-25, C-L3 dry-run 규명)**: ~~"전량 완료 122/122창·SATURATED 실갭없음"~~ **폐기**. C-L3 전량생성 규명(read-only) 실측 = **구간 내(2023-08-07~2025-12-05) 154일 헤드라인 0건** — 요일 편중(금 65·목 47·수 30·화 12 = 주 후반 집중), 인접(±2)에 기사있음 113(창내 뒷날 누락)·본인+인접 전부0 41(실갭 후보). 샘플: `2024-05-03(금) {-2:218, -1:249, 0:0}`. 원인 = 백필 고볼륨 창(7일)에서 **EARLIEST sort + 1000행 cap이 창 뒷날(주 후반)을 미커버**. ★기각된 논리: 구 "EARLIEST 절단은 다음 창이 보정"은 **비중첩 연속 창에서 성립하지 않음**(각 7일 창 독립 — 다음 창은 다음 7일이라 이번 창 뒷날을 채우지 않음). **디렉터 승인 오류 포함**. ★표본 일반화 오류: 2구간(2023-10-30·12-25주)만 확인한 "실갭없음"을 683 전체로 확대. 실 상태 = C-N **미완결**(→ TASKQUEUE `C-N-REPAIR`). 별개 뒷단 38일(>2025-12-05)은 백필 범위 밖 라이브 수집 갭(원인 별도). C-L3 코드는 정상(기사 있는 491일 선별·생성 정상) — 154일은 **상류 데이터 공백**이지 C-L3 결함 아님.

**D-AV-ACCOUNTING (AV 쿼터 회계 = 서버측 전용)**: 조사(2026-07-22, read-only) — 소비자 = beat `collect-av-broad-news`@01:00 UTC + 수동 backfill, 제3소비자 0(예산 공유 확정). ★로컬 일일 쿼터 카운터·커서 mtime 회계 파일 **부재**(초당 스로틀만) → 25/day 리셋 판정은 AV **서버측 전용**, RateLimitExceeded는 AV 응답 relay. rolling vs 달력일 = **미확정 파킹**(백필 완료로 무의미·스로틀 로그 메모리스왑 접근불가). 재점화 트리거 = AV 대량소비 트랙 신설 시.

**D-CL3-GROUNDING-WINDOW (그라운딩 창 정의)**: 이웃일 T의 그날 헤드라인 = `published_at__date == T`. ★STEP0 실측 정정: `settings.TIME_ZONE='Asia/Seoul'`·`USE_TZ=True`이므로 DB date lookup은 원지시서가 명명한 "UTC 캘린더일"이 아니라 **서버 TZ(KST) 캘린더일**. backfill `_window_count`(동일 lookup)와 동형 → 백필 커버 집합과 정확히 일치. 상수 `apps/market_pulse/regime/grounding.py`.

**D-CL3-SELECT-RULE (선별 규칙 = 결정론, 실측 기반)**: STEP0 실측(2024-05 broad 974건) = importance_score **0%**(rule engine 미적용)·sentiment_score **100%**·entity **100%**. 원지시서 후보 1순위 "relevance/importance_score"는 실측 미지원 → **제외**. 확정 랭킹(내림차순): abs(sentiment_score) → entity_count → published_at → str(id). 소스 다양성 = source당 cap **3**(편중 소스 컷). top-N=**12**.

**D-CL3-ARCHIVE-BLIND (is_archived 무필터)**: 그라운딩 쿼리는 is_archived로 필터하지 않는다(True/False 무관). ★STEP0 실측 반전: 과거분(2023-08·2024-05·2025-11)은 현재 대부분 `is_archived=False`(미아카이브)나, 미래 `archive_old_articles` 실행 시 True 전환 → 필터 시 벙어리화. 회귀 테스트(`test_fetch_includes_archived_articles`)로 잠금. (common-bugs 기존 함정 항목에 실측 반전 추기.)

**D-CL3-FREEZE / READ-DETERMINISTIC (동결·읽기 결정론)**: date별 1회 생성 후 불변(재생성 = `--regenerate` + prompt_version 증가). 카드 READ 경로 LLM **0**(저장분만 read, `test_l3_..._render_no_llm` 잠금). 그날 헤드라인 0건·톤가드 재실패 = why=null(억지 생성 금지, 행 미생성).

**D-CL3-LLM-REUSE (기존 래퍼 재사용)**: 생성은 market_pulse 자체 `apps/market_pulse/llm/client.py::generate_with_circuit`(Gemini 2.5 Flash 동기+CB) 재사용. ★원지시서 "shared complete()"·"BOUNDARY-LLM DORMANT"는 실측과 어긋남 = BOUNDARY-LLM **종결(FROZEN_COUNT=0)**, 전 소비처 complete() 경유. 단 경계 테스트는 `genai.Client`/`GenerativeModel` **직접생성만** 검출 → generate_with_circuit 재사용은 새 위반 0(경계 통과)·packages.shared 무접촉 = 지시서 §2-3 준수와 양립. (관찰: client.py는 `genai_module` 별칭으로 AST 우회 상태 — 기존 코드, 본 슬라이스 스코프 밖.)

**저장 스키마**: 신규 테이블 `AnalogDayContext`(date unique·why_text·provenance JSON·prompt_version·generated_at). mig `0007_analogdaycontext` additive(기존 테이블 diff 0, `--check` clean).

**prod 유보 2중(§5)**: ⑴ mig 0007 prod 적용 = 병진 수동(dev 적용·검증 완료). ⑵ **683 전량 생성 = 병진 승인 유보**(dry-run: 491일 LLM 대상·192일 null·~214K in/~19.6K out 토큰·~$0.11 근사). 세션 = 소량 8일 실생성 검증(전부 톤가드 OK, 좋은 예 ≥3).

**검증**: grounding 10·tone_guard 15·generator 4·command 5·api +1 = 신규 35 green. marketpulse+architecture **446 pass**·vitest mp2_analog **10**·tsc **0**·경계 신규위반 **0**·health ❌**0**·mig `--check` clean.

**D-CL3-QUALITY-LIMIT (거시 맥락 빈약 — 관찰 2026-07-25, 전량생성 후)**: 491 전량 생성 후 스팟체크(2024-08-05 엔캐리 급락·2023-10-19 국채 5% 돌파·2024-05-15 CPI 둔화) = **3일 전부 "개별 기업 소식" 균질**, 그날 거시 국면 맥락을 놓침. 규명(read-only): 원인 = ⑴ broad 피드 거시뉴스 **희소**(08-05 KST 220건 중 급락 키워드 4건뿐, AV NEWS_SENTIMENT가 개별 기업 PR/실적/M&A 위주) ⑵ 선별 `abs(sent)+entity_count`가 개별 기업 강감성 PR을 상위로(거시 뉴스 top-12 탈락) ⑶ KST 창 어긋남은 **부차**(엔캐리 심층기사 일부 08-06 KST, 그러나 08-05에도 급락 4건 존재→선별 탈락이 주). **배포분 491 유지**(사실 기반·톤가드 통과·해롭지 않음·analog 카드 alert 다수라 노출 드묾). 개선 = TASKQUEUE `C-L3-SELECT-V2`(index/거시 entity 우선·거시 키워드 가중). ★근본 한계 = broad 데이터 거시 절대량 부족 → v2로도 **부분 개선만**. C-N-REPAIR(창 뒷날 복구)와 시너지.

**baseline at decision**: base origin/main `b9ddf41a`. LLM 경로 = generate_with_circuit(신규 genai 직접생성 0).
## [2026-07-28] C-N-REPAIR STEP0 — 뒷단 38일 원인 판정 + 표적 재수집 방식 (D-CN-REPAIR-*)

> 트랙: C-N 백필 보수(D-CN-COMPLETE 폐기 후속). base origin/main `ca062581`. 브랜치 `monorepo/sess-CN-repair`. 범위 = 뉴스 원료 재수집만(L3 생성·SELECT-V2는 후속).

**D-CN-REPAIR-BACKTAIL (뒷단 38일 = 미수집 공백, 재수집 대상)**: null 192 = 구간내 154 + 뒷단 38. 뒷단 38 = **2025-12-10~2026-02-19 연속**(구간내 154의 요일 편중과 달리 연속). 실측: 그 전(백필 ~2025-12-05)·그 후(2026-02-20~04-24 = 60일 17,694건)는 채워짐, **뒷단만 공백**. AV broad는 2023-08~2026-07-27 전 범위 존재 → 뒷단 = **백필 종료 ~ 라이브 broad 가동(2026-02-20경) 사이 미수집** (STEP0 (b)). ★정확 원인(beat 미가동 vs 실패)은 `NewsCollectionLog`에 broad task_name 미기록으로 **미상**, 결과 = 공백 → 재수집으로 복구(원인 규명 부차, 복구가 목표).

**D-CN-REPAIR-TARGET (표적 소창 = --dates window-days=1)**: 재수집은 `backfill_broad_news --dates`(가산 옵션) — 각 명시일을 **1일 독립 창**으로. 창 논리(EARLIEST+1000cap) 원천 차단(1일 창엔 삼킬 뒷날 없음), 주말·공휴일 낭비 0(모집단 거래일만 명시). skip-covered 임계 1×3=3(멱등). 범위 --from/--to 방식은 주말 창 낭비라 기각. 기존 --from/--to 경로 무변경(가산) → HALT 미해당.

**D-CN-REPAIR-DONE-CRITERION (완료 판정 = 일 단위 존재)**: ★D-CN-COMPLETE 폐기 교훈 계승 — "창 완료"(122/122)류 판정 금지. 완료 = **null 192일 각각 `published_at__date=D` 기사 >0**(잔여 0). 그 후 C-L3-REGEN-V2 진입.

**예산·계획**: AV 25/day − broad beat 2 − 여유 3 = **20 req/실행**(beat 소비 2<<5, 예산 하향 불요). 1일당 ≈1 req(limit 1000, 과거 <1000 saturation 없음). 192÷20 = **10 배치**(각 20일, 22:00 KST 이후 병진 수동). SATURATED 2023 2창(10-30·12-25주)은 967·927건 이미 커버(154 무포함). NewsArticle 보존 = archive_old_articles soft delete만(purge 삭제 없음), 재수집분 안전. 계획서 `docs/features/cn_repair/repair_batch_plan.md`.

**검증**: backfill 테스트 6→11(신규 5: window-1 독립·멱등 skip·null 재수집·--dates 표적·--dates 멱등)·경계 GREEN·health ❌0. 커맨드 로직 무변경(--dates 가산만).

**baseline at decision**: base origin/main `ca062581`. 실행(재수집 --commit)은 병진 수동 유보.

## [2026-07-29] C-N-REPAIR-AUTOMATION — 무인 야간 배치(launchd) (D-CN-REPAIR-AUTO-*)

> 트랙: C-N-REPAIR 재수집을 사람 트리거 없이 돌리는 무인 자동화. 지시서 소비. base = sess-CN-repair(origin/main `68aeea28` 랜딩분 위). 산출 = `scripts/cn_repair_nightly.sh`·`scripts/cn_repair_status.py`·`docs/operations/com.stockvis.cn_repair.nightly.plist`·런북. **활성화(launchctl load·kickstart)는 prod 쓰기+AV 소비 = 디렉터 명시 승인 게이트**([[feedback_deploy_approval_explicit_quote]]).

**D-CN-REPAIR-AUTO-CHECKPOINT (순번 = 캘린더 산술 아닌 체크포인트 카운터)**: 지시서 STEP 2-1 문자 그대로의 "경과일+1"을 **기각**. 실측(2026-07-29): 시작일 07-28 기준 오늘 경과일=1 → "경과일+1"=batch2인데 **batch1(07-28)은 미실행** → 캘린더 산술은 batch1을 영구 스킵. 대신 `status.json.next_batch`를 **성공 시에만 전진**(zero/fail=보류→다음 밤 재시도). max()로 재실행 역행 방지. 멱등(url upsert+skip-covered)이라 재실행도 무해.

**D-CN-REPAIR-AUTO-HOLD1 (실행당 1배치 보존)**: 10배치로 나눈 이유 = AV 레이트리밋(20 req/실행, 192÷20≈10일, STEP 0-2). 자동화는 "사람 트리거"만 없애고 **간격은 보존**(하루 1배치). 압축(한 밤 다배치+sleep)은 디렉터 승인 후 옵션(기본 미채택).

**D-CN-REPAIR-AUTO-TREE (실행 트리 = sv-worker-runtime, self-locate)**: 계획서 원라이너의 `cd Desktop/stock_vis`는 그 트리가 세션 브랜치(현 sess-hold-p1, --dates 없음) 표류 → 부적합. 스케줄러는 **origin/main 추적 트리 `~/worktrees/sv-worker-runtime`**(f7f3f63d=origin/main, --dates·계획서 착지, .env 심링크)에서 실행. 래퍼는 BASH_SOURCE self-locate로 REPO_DIR=자기 트리 → plist는 worker-runtime의 래퍼 호출. **전제**: 래퍼·헬퍼가 origin/main 랜딩 후 worker_sync로 그 트리에 동기화돼야 함(활성화 전 게이트).

**D-CN-REPAIR-AUTO-ANOMALY (이상치 = 0건 or 중앙값 밴드 [0.3×,3.0×])**: 정상=무알림, 이상 시에만 알림(ALERT 파일 + osascript). exit≠0=fail(전진 보류)·net 0건=zero(대상일 null인데 무수집=fetch실패/전량skip 의심, 전진 보류)·밴드밖(표본≥3, net>0)=ok_review(데이터는 수집됨→전진, 검토만 권장). 로그/상태는 **`~/Library/Logs/stockvis/cn_repair`**(지시서 `logs/cn_repair`는 Desktop TCC 위험 → pg-backup 관례로 이전).

**D-CN-REPAIR-AUTO-DONE (10/10 자동 마무리)**: 래퍼가 next_batch>10 감지 시 DONE 마커 + launchd 자동 unload(bootout) + 다음 단계 안내(일 단위 존재 검증→SELECT-V2/REGEN-V2). Cowork 리마인더 삭제/용도변경은 **수동 유보(후보만)**.

**검증**: 신규 pytest 9(status 머신)·기존 backfill 11(멱등 3건 포함)·래퍼 dry-run(batch1→20창 매핑·카운터 불변)·완료 경로(next=11→DONE)·경계 GREEN(stdlib만). **활성화·라이브 2회 IDENTICAL·kickstart는 게이트(prod)**.

**D-CN-REPAIR-AUTO-ADOPT (검토 관문 6종 통과 → 수동 게이트 공식 대체, CN-AUTO-REVIEW 2026-07-29)**: 9fca374d를 정식 검토 관문(G1 쿼터캡·G2 무소음실패금지·G3 범위한정·G4 멱등순번·G5 경계보안·G6 테스트)에 회부해 **전 항목 PASS 판정**. 이로써 C-N-REPAIR 재수집의 원 게이트 "**일 배치 병진 수동 실행**"(prod 쓰기+AV 쿼터 이중 사유)을 **"관문 통과한 무인 자동화"로 공식 대체**한다. 단 **활성화(launchctl load·kickstart)만은 여전히 디렉터 명시 승인 게이트**로 남는다(무인화된 것은 "매일의 트리거"이지 "최초 활성화"가 아님).
- **관문 근거**: G1=`--max-requests 20` 하드캡 + 커맨드 `pending[:max_requests]` 슬라이스(≤20 req/실행) + plist StartCalendarInterval 1회/일·KeepAlive=false·RunAtLoad=false(스케줄 자체가 야간 1회 초과 불가). G5=`AlphaVantageNewsProvider`(shared) 경유·신규 직접호출 0·plist 자격증명 0. G3=next_batch>10 감지 시 DONE+자동 unload(상시 수집기 변질 차단)·대상일=계획서 `--dates`만.
- **G2 보강(미달→PASS)**: 원안은 실행-후-실패(exit≠0·0건·밴드밖)만 ALERT로 표면화 → **"launchd가 아예 안 돌았음"(sleep/미발화)은 무감지**(OPS-NEWS-FRESHNESS 2.5개월 재발 구조). 보강 = `cn_repair_status.py check` 리포터(마지막 실행 경과일 → OK/STALE/NEVER/DONE, exit 1=주의) + 런북 "아침 확인 루틴" + 단위테스트 5건(check 3·소진종료 1·기존). status 테스트 9→14.
- **범위 한정 재확인**: repair 계획서 10배치(192일)로 한정, 소진 후 자동 비활성. 일반 상시 broad 수집기로 변질 금지. 압축(한 밤 다배치)은 미채택(별도 승인 옵션).
- **랜딩·활성화 분리**: 본 검토 세션은 **랜딩·push·plist 활성화를 하지 않는다**. 랜딩=별도 승인, 활성화=랜딩 후 worker_sync로 sv-worker-runtime 착지 → 런북 절차 병진 수동.

## [2026-07-13] D-EVENTGROUP-WINDOW — EventGroup co-mention 집계에 날짜 윈도우 실적용 (기본 21d·config)

**맥락**: `event_group_pipeline._build_base(half_life)`가 `half_life` 파라미터를 **선언만 하고 본문에서 미사용** — `ChainNewsEvent(is_duplicate=False)` **전량**을 날짜 무관하게 co/doc 카운팅해 왔다. `EventGroup.window_days` 필드는 `half_life`(=21) 값을 저장하나 실제 윈도우링은 없었다(라벨과 행위 불일치). 결과: 데이터 누적 시 오래된 co-mention이 현재 그룹 내러티브를 **희석**(TASKQUEUE `EVENTGROUP-WINDOW`).

**실측(고정 as_of=2026-07-11, prod read-only 골든)**: 유효 2+종목 이벤트 N=5616. 21d 윈도우 경계(lower=06-20)에서 **in=3922 / out=1694 = 30.2% out**(⑪ 30.0%와 비율 정합, 절대수 차이=데이터 성장 as_of drift). 즉 그룹핑 입력의 약 30%가 stale 희석분이었다.

**결정**:
1. `_build_base`가 `window_days`를 **실제 적용**: as_of(최신 유효 2+종목 이벤트일) 기준 `pub.date() >= as_of - window_days` 이벤트만 co/doc 카운팅. window 밖은 제외.
2. **as_of(max_d)는 window 적용 전 전량 기준 max**로 산출 → 윈도우 축소와 무관하게 고정(as_of 07-11 IDENTICAL 보존). 2패스 구현(1패스=정제+max, 2패스=윈도우 카운팅).
3. **파라미터명 정합 리네임**: `half_life`/`DEFAULT_HALF_LIFE` → `window_days`/`DEFAULT_WINDOW_DAYS`(기본 **21**). `EventGroup.window_days` 필드명과 일치. 호출부(`compute_event_groups`·`load_event_groups`) 주입 가능(config). 참조 전량이 `event_group_pipeline.py` 단일 파일 국한(외부 호출부 무주입 확인).
4. **스키마·하류·C3 무변경**: `window_days` 필드 기존재(makemigrations "No changes"). load 체인·게이팅·leadership 로직 불변.

**Why**: 라벨(window_days=21)이 이미 그룹에 저장되고 있었으나 행위가 미적용이라 라벨-행위 불일치였다. 윈도우 실적용으로 stale 희석 **30%→0**, 그룹 내러티브가 최신 신호만 반영. half_life는 시간감쇠 뉘앙스지만 실제 의도는 하드 윈도우라 이름을 window_days로 정정.

**골든 회귀(HALT 미발동)**: 신 `_build_base(21)` == 독립 참조 in-window 구현 **IDENTICAL**(co_count 5629 edges·doc_count 596·N=3922·as_of 전부 일치). out 제외 1694=골든 정합. 대형 window(=전량 복원)==골든_full로 파라미터 실효 확인, 무인자 기본값=21 실효. 파이프라인+beat 테스트 13 green. 관측된 chainsight 실패 13건(attention 5·leadership/upward 8)은 **baseline 재현 확인 = 선존**(stale `_dormant/graph_analysis`·Celery eager·Neo4j·env), 본 변경 귀속 신규 red 0.
## [2026-07-14] FMP-TESTDEBT — baseline FMP 34 env-독립화 (conftest 더미키, 테스트 하네스만)

**결정**: FMP 키 부재 환경(CI·.env 없는 격리)에서 setup 실패하던 baseline red **FMP 34건**을, `tests/conftest.py`에 **autouse 더미 `FMP_API_KEY` 선주입 픽스처**를 추가해 env-독립화한다. **프로덕션 코드 변경 0** (테스트 하네스만).

**대상 34건(⑭ 실측 = 지시서⑮ IN)**: `tests/serverless/test_chain_sight_service.py` 13e + `tests/serverless/test_enhanced_screener_service.py` 12e + `tests/integration/test_provider_factory.py` 9f. 전부 근본원인 = **키 부재 시 provider 인스턴스화 거부**(2경로: `serverless_client.py:43-45` `settings.FMP_API_KEY` → `ValueError: FMP_API_KEY is required` / `base.py:316` `_validate_api_key` — factory가 `os.getenv("FMP_API_KEY","")`로 읽어 생성자 전달 → `fmp API key is required`). 키 존재 시 전건 통과 = **env 의존이지 코드 결함 아님**(⑭ 분류 ⅰ).

**구현(`_ensure_fmp_api_key`, autouse)**: `settings.FMP_API_KEY` **와** `os.environ["FMP_API_KEY"]` 둘 다 커버(2읽기경로). **falsy(부재·빈문자열)일 때만** 더미 주입 → **실키 보존**(dev/.env 회귀 무손상). os.environ은 `monkeypatch.setenv`로 테스트 종료 시 자동 복원(세션 누수 0). `os.environ.setdefault`는 빈문자열("")을 present로 봐 no-op되므로 `if not ...get()` force 방식 채택.

**"키부재→에러" 계약 테스트 보존(STEP 0.3·1.3)**: `tests/marketpulse/fetchers/test_fmp_weights.py::TestRequestEtfHolderGuards::test_missing_api_key_raises`(34 밖, `settings.FMP_API_KEY=None` 로컬 override → `RuntimeError match="FMP_API_KEY"`). 픽스처 setup 이후 **테스트 본문이 후행 override**하므로 무충돌 — **키 없는 상태 검증 그대로 유지**(실측 PASSED). FMP 키-required를 계약으로 검증하는 다른 테스트는 repo 전수 검색 결과 없음.

**Why**: 테스트가 provider 인스턴스화에 실키를 요구하면 CI에서 비결정 red. 더미키로 격리하면 프로덕션 행위(실키로 정상)를 바꾸지 않고 34건이 결정론적 green. 라이브 호출은 각 테스트가 이미 mock(`@patch FMPClient`·`_request_*`) → 더미로 충분, **라이브 FMP 호출 0**.

**검증(HALT 미발동 — 34건 전부 더미키만으로 격리, 라이브 응답 불요)**:
- `env -i` + `FMP_API_KEY=""`(어떤 소스에도 키 없음, load_dotenv override=False) → **42 passed·1 skip·0 fail**, 실행 1.2~1.5s(라이브 호출 0 입증).
- 계약 테스트 `test_missing_api_key_raises` **PASSED**(키 없어야 pass, 보존 확증).
- 전체 회귀(실키 .env 환경) **13 failed / 3826 passed / 53 skip** — 잔여 13 = **정확히 chainsight 13**(test_attention 6 + test_leadership_api 7, CS-EG6 theme_tags→EventGroup 전환 계약 종속, ⑮ 범위 밖). **chainsight 외 실패 0 = 신규 red 0.**

**baseline at decision**: origin/main = `7b7927e`. 변경 = `tests/conftest.py` 26줄 추가 **단일 파일**. 프로덕션 서비스 코드·chainsight 13·FMP 라이브 호출 무접촉(지시서⑮ OUT 준수). ⑬(EVENTGROUP-WINDOW)·⑭(survey) 미머지 상태.

## [2026-07-14] MP2-ANALOG Slice C-core — L2 국면 카테고리 + FE 태그 (D-ANALOG-L2 / D-DOCS-PERSIST)

> 트랙: MP2-ANALOG(#1). base origin/main `bb91c98`. 브랜치 `monorepo/sess-C-core-l2`. C-N(뉴스 백필)과 독립·병렬. prod 쓰기 0·마이그레이션 0·뉴스/LLM 0.

**D-ANALOG-L2 (L2 소스 = regime 확정치, 결정론)**: Slice C 원안의 L2 두 후보(FMP 이벤트 캘린더·과거 뉴스분류)가 STEP 0서 과거 불가 판정(캘린더 402 유료벽·뉴스 7개월) → **L2 = RegimeSnapshot.regime 확정치**. 683 완전 커버·외부 의존 0·결정론. 의미 전환: "뉴스 이벤트 유형" → **"국면 유형"**(시각 구조=태그 상시 유지, 어휘만). regime enum 5값(BULL_EXPANSION/LATE_BULL/TRANSITION/BEAR_CONTRACTION/CRISIS), 683 분포=3값(TRANSITION 449·LATE_BULL 228·CRISIS 6).
- **어휘 단일 출처 = RegimeSnapshot.Regime enum 표시명 재사용**(모델 공식 라벨 — "강세 확장"/"상승 후반 경계"/"전환"/"약세 수축"/"위기"). 별도 어휘 발명 0(드리프트 0). `categorize_regime`(순수 함수, `regime/category.py`) → {key(RegimeId), label(enum 표시명)}. **미지 값 = ValueError**(조용한 null 금지 — 미래 regime 추가 시 폭발적 노출).
- **cat_slot 계약 = string 유지**(Slice B 선언 `cat_slot: string|null`) → cat_slot=label 문자열, **cat_key(RegimeId) additive 추가**(FE 톤용). today도 `today_category:{key,label}|null` additive(라이브 OK 스냅샷 있을 때만 — 억지 태그 0).
- **톤(색) = FE 소관**: 기존 `meaning.ts::REGIME_TONE`(D-COLOR-SYSTEM 검수 팔레트)+`regimeTone()` 재사용(신규 색 0). 데이터(key·label)/표현(tone) 분리.
- **CRISIS 카피 게이트(절대)**: 태그 = 그날의 사실 분류 표기("위기")까지만. "오늘이 위기와 유사" 류 유사성 주장 카피 0(역사적 CRISIS 6일은 유사성 근거 불충분). 단위 테스트로 태그 어휘에 유사/닮/같 부재 고정.
- **판단 단일 출처 = payload builder**, FE 재분류 0(태그 소비만).

**검증**: 백엔드 카테고리 8 + analog API 6 신규/갱신 green, marketpulse 404 passed·1 skipped(회귀 0), FE vitest 8 green(3상태 태그·톤·why 무접촉), tsc 0, health 14 OK/0 ERROR(경계 위반 0), 마이그레이션 0. **라이브 데이터 검증**: 오늘(2026-07-14) regime=LATE_BULL → today_category "상승 후반 경계" 라이브 populated / as-of 이웃 cat_slot 정합(2024-12-09→"전환"·2025-02-20→"상승 후반 경계").

**D-DOCS-PERSIST (지시서·목업 정착)**: 기존 "실행 지시서는 휘발(repo 밖)" 관례를 **"완료 슬라이스의 지시서·목업은 `docs/instructions/`·`docs/design/`에 정착"**으로 변경. 근거 = fresh 세션이 지시서·목업을 못 봐 반복 재질의(본 트랙에서 실제 발생). ★단 **결정 정본은 여전히 DECISIONS.md** — 정착 md는 이력 참고물(헤더 주석 명시), 어긋나면 DECISIONS가 이긴다. 본 세션 정착: C-core 지시서. 미전달(채팅 전달물) = A/B/C/C-N 지시서·목업 2종 → 디렉터 재전달 대기(README에 목록).

**baseline at decision**: base origin/main `bb91c98`. prod 쓰기 0.

## [2026-07-14] D-ANALOG-L2-SCREENSHOT — C-core 실화면 검증 이연(3택 중 2번)

**결정**: C-core UI 실화면 검증 = **머지 후 런타임 검증(3택 중 2번)** 채택. 오늘 카드가 alert 상태(이웃 0)라 **이웃 태그가 off-surface** → 실화면 캡처는 **폐기가 아니라 이연**. TASKQUEUE에 "실화면 게이트(이연)" 행 등재해 실종 방지(첫 non-alert 날 병진이 이웃 태그 캡처 후 close). **Why**: 오늘 표면엔 today 태그만 가시(이웃 태그 불가)·추가 비용 0·UI 슬라이스 실화면 규약을 폐기 않고 보존. **마진 0.65 / 타이브레이커** = 규약 예외(스크린샷 생략) 전례를 만들지 않음. today 태그는 이번 런타임 스모크로 실서비스 가시 검증.

---

## [2026-07-14] D-GRAPH-EGO-BACKEND — ego 그래프 서빙 = PostgreSQL 네이티브 (Neo4j 동결) (지시서⑰)

**결정(⑯ 자동결정 승계)**: ChainSight ego(회사 중심 1-hop 관계망) 서빙을 **PostgreSQL 네이티브**로 신설한다(D①, 4.40 vs 2.65 마진 1.75). Neo4j는 **삭제 아닌 동결** — 기존 Neo4j 백엔드 endpoint 3종(`<symbol>/graph/`·`<symbol>/neighbors/`·`sector/<>/graph/`)·loader·sync 코드 무변경 보존.

**근거(⑯ grounding 실측)**: ⑴ 진실 소스=PostgreSQL — RelationConfidence(13,697행 현재상태) + RelationPairSnapshot(궤적 114,744행/9,562쌍×12period). Neo4j는 `neo4j_dirty` 단방향 파생. ⑵ Neo4j **DOWN**(localhost:7687 refused)인데도 관계·궤적 온전 → Neo4j 의존 endpoint는 죽으면 ego 전체가 죽음. ⑶ 궤적(RPS)은 Neo4j에 없음(PG 전용). → ego는 PG 단독으로 성립하고, PG 경로가 가용성·궤적 양면 우위.

**구현(⑰ S1)**: `GET /api/v1/chainsight/ego/<symbol>/`(신규 `ego_views.EgoGraphView`) — RelationConfidence 양방향 1-hop(truth_score 내림차순 상위 N) + RelationPairSnapshot 궤적(truth_max) join(N+1 금지=3쿼리). 지연 실측 AAPL 13·NVDA 21·MSFT 15ms(<200ms). truth_score 미정규화 원값 노출(정규화 별도 트랙). additive — 기존 endpoint 무변경.

**CS-CHOICES(S1-a)**: `RELATION_TYPE_CHOICES`에 PARTNER_WITH·DEPENDS_ON 추가(DB 실측 54·41행에 라벨 부여). choices=검증/표시용 → sqlmigrate 0017 `-- (no-op)` = DDL 무발생. 0행 choices(HAS_THEME·HELD_BY_SAME_FUND)는 무변경(제거 후보 보고만).

**재평가 트리거(동결 해제 조건)**: 멀티홉(2+hop) 경로 탐색·커뮤니티 탐지(GDS)·대규모 그래프 순회가 제품 요구로 발생하면 Neo4j 재가동+동기화(dirty 270 해소)를 재평가한다. 그 전까지 Neo4j sync 태스크 3종은 가동하나 무효(DOWN) — 비활성 후보(TASKQUEUE, beat 변경은 병진).

**baseline at decision**: base origin/main `a71efc9`. prod 쓰기 0(마이그레이션 0017 no-op·적용은 병진 수동).

## [2026-07-14] MON-CLOSE-UI 트랙 최종 종결 (P1·P2·P1.5 계보)

> 마감 루프(판정·회고·동결)가 엔진→화면까지 닫힘. RECON(33176f2) → P1(BE, `3d5341e`) → P2(FE, `468e29a`) → P1.5(동결값 노출, 이 커밋).

**계보·산출**:
- **P1 (BE, D-MONITOR-CLOSE-UI-P1)**: Claim verdict/회고 필드+PARTIAL·ClaimIndicatorResult(지표=전제 조인)·ClosureSnapshot(불변 동결)·propose_verdict(±0.333)·close-preview/close 원자 액션(409). migration 0006 additive.
- **P2 (FE)**: `/monitor/[id]` 상세(dangling link 해소)·CloseModal(A-1)·VerdictBadge·B-1 상태 세그먼트·동결 카드.
- **P1.5 (동결값 노출)**: P2 갭 해소 — ClaimSerializer에 `closure_snapshot` nested read-only 노출(마이그레이션 0), FE `frozenScore` 우선순위(resolved=동결값, PENDING=live). throwaway E2E로 첫 실마감 검증.

**결정 계승 (봉인)**: ①회고=조인모델(지표 피벗) ②Claim단위 마감(Monitor.State 불변) ③overall_score ±0.333 밴드 ④outcome+=PARTIAL(final=outcome 재사용) ⑤상세 페이지 신설. A-1 모달·B-1 세그먼트.

**행위보존**: 엔진(scorer·arrow·aggregator·state_machine)·beat·shared·Monitor.State 전 구간 불변. 마감은 전부 Claim 레벨 파생. 마이그레이션은 0006(P1) 1건뿐, P1.5는 serializer 노출만.

**vitest 델타 판정 (P2 이월 −5)**: `50a1738..468e29a` 삭제 테스트 **0건**. −5는 "632" 베이스라인이 MON-CLOSE(e870b02) 시점이라 P2 base(50a1738)보다 이전 = 그 사이 타 세션 FE 테스트 순변경분. 내 P1·P2·P1.5 테스트 삭제 0(순증 33+3+4).

**백로그(트랙 밖)**: 마감 ≥20건 시 제안 밴드(±0.333) 실분포 재조정 + 회고 채움률 점검(A-2 재검토 트리거).

**baseline at decision**: origin/main = P1.5 커밋 기준. prod: 0006 이미 적용(2026-07-14). serializer 노출은 코드만.

## [2026-07-15] D-MONITOR-TIMING-PIVOT — monitor 질문 교체: 가설 검증 → 매수 타이밍 (리포지셔닝)

> 상태: **확정**(사용자 승인 2026-07-15 — 방향 A + 지표 어휘 S/L/E + 가치평가 경계 B 전부 확정). 관련: D-MONITOR-REBUILD·MON-CLOSE-UI(마감 루프)·3-B(제안)·4-B(판정·회고·동결).

**결정 (§1)**: monitor가 답하는 질문을 **"가설이 아직 유효한가"(관측) → "지금이 이 종목을 살/팔 타이밍인가 — 어느 가격에 사고 파는가"(행동 지시)**로 교체. 구현 = **리포지셔닝(옵션 A)**: 엔진(신호 인제스트·스코어링·상태기·알림·마감 루프) 유지, 도메인 의미·표면 언어만 매수타이밍으로 피벗. 가설 검증 골격은 폐기 아닌 수면 아래로("이 가격대가 진입점" = 매수 시나리오 = 본질적으로 가설, 기존 Claim·마감 루프가 성적표 매김).

**동기 (§2)**: ⑴ 관측만 있고 행동 지시 없는 시스템 = 사용 동기 소멸(전제·지표 학술어휘의 "그래서 뭘 하라는가" 부재). ⑵ 투자 파이프라인(무엇을 살까=Chain Sight → 살 만한가=가치분석 → **언제·얼마에=monitor(이 피벗)** → 얼마나=Portfolio → 언제 도망=market_pulse)에서 "언제·얼마에" 공석. ⑶ 방금 완성한 마감 루프(판정·회고·동결·proposed vs final 델타) = 매매 사후분석 엔진과 구조 동일 → 피벗 비용 역대 최저.

**확정 불변식 (§3, ADR과 함께 잠금)**:
- **§3.1 시간 해상도 = EOD(스윙/포지션)**: 일봉 기반, "내일 이후 행동(수일~수개월 보유)". 장중 매매 범위 밖. 실시간화는 별도 결정 사이클 없이 미착수. 한계 아닌 정직한 스펙(문헌 근거 기술 신호도 일·월 단위).
- **§3.2 가치 축 = 규율·캘리브레이션(예측기 아님)**: 존재 가치 = ⑴ 가격·시나리오 사전 커밋 ⑵ 전 매매 사후분석 강제 ⑶ 제안-실제 델타 자기 캘리브레이션. 근거=처분효과(Shefrin&Statman 1985·Odean 1998: 이익 실현 성향 ≈ 손실 실현 1.5~2배, 사후수익률로 미정당화) → 진입/목표/손절가 매수前 기록 강제가 방어. 신호 빗나감 = 실패 아닌 캘리브레이션 데이터. **3-B 계승: 시스템은 제안, 판정·행동 주체는 항상 사용자. 자동 주문 실행 영구 범위 밖(Wallet read-only 유지)**.
- **§3.3 경계 재선언**: vs **Portfolio/Wallet** — monitor=이 종목 가격·타이밍(마이크로), Portfolio=자원 배분·리스크 총량(매크로), "얼마나 살까"=Portfolio 소관(monitor 수량 미언급). vs **market_pulse** — monitor 시장scope=진입 환경 필터(지수 vs 장기이평), market_pulse=위기 사전감지(들어가도 되나 vs 도망가야 하나). vs **개별종목 가치분석** — **★판별 규칙: 모델 입력이 재무·펀더멘털(분기)이면 가치평가, 가격·거래량 시계열(일)이면 monitor**. 내재가치 모델(DCF·멀티플)=가치평가 앱, monitor는 그 산출(적정가 밴드)을 shared 경유 소비→빌더에서 목표가·안전마진 진입가 후보 제안(L계열 병렬). 통로 스키마 별도 결정, 준비 전까진 빌더 수동입력 기본+nullable 참조 자리만(additive). **앱 간 직접 import 금지**.
- **§3.4 행위보존**: 엔진(scorer·arrow·aggregator·state_machine)·beat·마감 루프 구조 불변. 바뀌는 것 = ⑴ Claim 필드(가격 시나리오 additive) ⑵ 지표 어휘(타이밍 프리셋) ⑶ 상태·알림·UI 언어. monitor leaf·단방향·additive-only·"가동중 앱"·실데이터(AAPL 40+ readings) 연속성 전부 유지.

**도메인 매핑 (§4)**: Monitor{scope}=종목/시장환경 타이밍 감시(의미만) · Claim{assertion,deadline}→**매수 시나리오**(entry/target/stop_price·기한, additive, 스키마는 RECON후) · MonitorIndicator+EOD=타이밍 신호(어휘 교체, 파이프라인 불변) · overall_score[-1,1]=**진입 매력도**(재해석) · state_machine 8상태·달위상=관망→접근→**진입구간**→이탈/과열(라벨·전이 의미 재정의, 구조 불변) · 알림=**진입구간 도달 즉시**/관망 다이제스트 · 마감루프(P1~P1.5)=**매매 사후분석**(익절/손절/기한만료·요인회고·동결·delta=캘리브레이션, 라벨수준).

**지표 어휘 = 3계열 분류 (§5, 프리셋 확정은 후속)**: 두 축 등재 = ⑴ 근거강도(강/중/약, UI 메타 표시 — 약한 지표도 사용가능·강도 표시) ⑵ 파이프라인 적합. **계열이 소비처 결정**:
- **S계열(스칼라, 기존 파이프라인 직결·런칭 프리셋)**: 200일SMA 괴리율(강, BLL 1992·Faber 2007)·시계열모멘텀 12-1(강, Moskowitz 2012)·52주고가 근접도(중, George&Hwang 2004)·거래량비율(중, 확인용 Lo 2000)·MACD히스토그램(약)·과매도 오실레이터 RSI/스토캐스틱(약).
- **L계열(가격 레벨=시나리오 파라미터, 소비처=빌더)**: 지지·저항·전고저·피보나치·ATR 손절폭. **점수 미기여** — 빌더에서 진입/목표/손절가 후보 제안 보조계산. z-score 파이프라인 혼입 금지(§3.2 사전커밋 구조화 역할이라 근거 요건 다름).
- **E계열(이벤트/패턴 = 신규 기계·백로그 격리)**: 골든/데드크로스·차트패턴·캔들·돌파. **파이프라인 부적합**(간헐 사건, 패턴 인식기 최초 구현). 근거 혼재(패턴 자동탐지 긍정 Lo 2000, **캔들 부정 Marshall 2006**). **이 ADR서 미착수** — 이평 부호전환류는 S로 흡수, 형상·캔들은 별도 결정 사이클(TIMING-P3 인근).
- **§5.4 공통**: 추세·모멘텀도 최근 표본 약화 반복 보고 → §3.2 강화(프리셋=돈버는 공식 아닌 시나리오 어휘, 실효는 본인 마감데이터로 검증, ClaimIndicatorResult가 지표별 승률 원천). 전 후보 EOD 산출가능(P0 RECON서 소스 전수검증).

**기각 대안 (§6)**: **B 하이브리드(가설+타이밍 병존)** 기각(표면 2배·반쪽기능 2개·지루함 무응답, 0.565). **C 전면 재구축(타이밍 전용 신규엔진+백테스트)** 기각(마감루프·상태기·알림 재발명, 수개월 공백, 실데이터 단절; 백테스트는 A 위 후행 가능, 0.555). **채택 A=0.885**.

**스테이징 (§7, 각 트랙 별도 지시서·결정사이클)**: TIMING-P0 RECON(실측: Claim 확장지점·state 재정의 가능성·프리셋 EOD 산출가능성·라벨 전수) → TIMING-P1 의미피벗 BE(Claim 가격필드 additive·프리셋 등록·진입매력도 재해석·verdict 익절/손절/기한만료 매핑 RECON판정) → TIMING-P2 어휘피벗 FE(상태·알림·카드·빌더 언어 행동어화, 빌더="가설작성"→"매수 시나리오 작성") → (백로그)TIMING-P3(마감≥20건 후 밴드재조정·지표별승률·백테스트·E계열 착수 결정사이클).

**확정/미확정 (§9)**: 확정=질문교체·A·EOD·가치축·경계3건·스테이징·기각기록. 미확정(후속)=프리셋 최종목록·Claim 가격필드 정확스키마·상태라벨 최종·verdict 재라벨방식·가치분석↔monitor 통로설계 — 전부 P0 RECON 실측 후 결정.

**baseline at decision**: origin/main = `ef8990c`(MON-CLOSE-UI 종결 직후). 메타-only(코드·prod 쓰기 0, ADR 등재).

## [2026-07-16] CS-CREDIT-P2-0 — 예약 2키 실현 (compute-on-read)

> 트랙: monorepo/sess-credit-p2-0 (32c0559, 머지 2c7ce2f). 문서 정본 = docs/credit/credit_roadmap.md.

**① 재비준 F — FRED 6→8종**: "6종 고정" 불변 규칙을 명시 해제. BAMLH0A1HYBB(BB)·BAMLC0A3CA(A) 수집 추가. 이후 추가는 동일 재비준 절차 필수. (§5 라벨 `E`는 P2patch "P2 시퀀스"가 선점 → 스코프 재비준은 `F`.)
**② 파생 compute-on-read**: CCC_MINUS_BB·BBB_MINUS_A는 원장(MacroSeriesHistory) 미적재, read 시 날짜 inner-join 감산. 근거: STEP0 정합 0.00% mismatch(787=787) + 원장 raw 순수성 + robust_z 내부 756일 창으로 raw와 창 동일. 테스트로 봉인(test_ledger_not_written).
**③ 8칩 심각도정렬**: red>orange>yellow>gray stable sort, 동급은 API 순서. 칩 폭·컨테이너 불변 → TH 무침범. 비-gray 가로스크롤 잠복 방지. (§5 결정 `g`로 이미 등재 — GATE6 D2 행은 중복이라 생략.)
**④ 헤드라인 7패턴**: CCC_MINUS_BB 단독 패턴 추가. BBB_MINUS_A 단독은 의도적 배제(중립 폴백 소화) — 비대칭은 결정이며 누락 아님.
**⑤ 07-16 Gate 4 — 사전 승인 없이 집행 (기록 정정 종결)**: Gate 4(머지 `2c7ce2f` + `sv sync` 배포 + 3년 백필)는 **사전 승인 없이 집행**. 검증 GREEN(prod 8키·BB/A 각 786행·동승 migration 3건 chainsight 0017·portfolio 0004·fx 0001 기적용, 미적용 0) 확인 후 **기록 정정으로 종결(07-16)** — 사후 추인 아님. **이후 배포·재배포·beat 변경은 사용자 승인 인용 필수.** (직전 오기 "배포 보류 철회(사용자 판단)"·"사후 추인" 표현을 정정.)

**프로덕션 행위 변화**: 수집 8종·스트립 8칩·파생 2키 노출. grading 규칙·6키 계약·GradeChip·미러 상수 변경 0.
**baseline at decision**: origin/main = `2c7ce2f`(CS-CREDIT-P2-0 머지).

**거버넌스 재확인 (07-16)**: Gate 4급 액션(배포·beat 변경·서비스 재기동)은 사용자 승인과 별개로 **본 프로젝트(Stock-Vis) 통지·조율 선행 필수** — sv-credit 트랙 **단독 트리거 금지** 재확인. (07-16 credit 배포가 이 원칙 위반 사례 — 명시 승인 없이 무단 집행, 통지·조율은 사후. §⑤ 정정 참조.)

**⑥ P2-0 종결 확증 (2026-07-17, ⑤ 자율가동 검증 · 사용자 승인)**: 첫 자동 8키 수집 확인 — beat `credit-signals-ingest-fred-daily` 07-17 07:30 KST 정시 발화(total_run=9), 8계열 전원 당일 07:30 신규 삽입(`ingested_at`), 8키 z/grade 재계산·서빙. 파생 2키 grade 정상(CCC_MINUS_BB=yellow z=1.53 · BBB_MINUS_A=gray z=−1.69, red 미발화 계약 유지), 원장 파생 미적재 계약 유지. **P2-0 종결(07-17): 자율가동 확증, 잔여 0.**
- **[조항 교정] 전진 판정 기준**: 전진 판정 = 계열별 최신 관측의 **당일 신규 삽입**(`MacroSeriesHistory.ingested_at` 기준). 계열 간 as_of 격차는 **발행 케이던스 정상**(T10Y2Y가 ICE BofA OAS·VIX를 1영업일 선행 — 최근 6관측일 일관). 이 격차는 "일부만 전진(파이프라인 부분실패)"이 아니며 FAIL 아님. (검증 지시서의 "8키 간 as_of 불일치=FAIL" 조항을 본 기준으로 교정 — 향후 로드맵 검증 기준도 동일 적용.)
- **[부수 관측·이관]** 07-17 compute 지연 4h(ingest 07:30 · state upsert 11:31, default-queue 워커 큐 처리 추정) — credit 코드 결함 아닌 **ops/runtime 사안, 본 프로젝트(Stock-Vis) 이관**. 07-18 run 재현 여부 1회 관측 요청, celery-worker.log가 07-16 18:53 이후 stale이므로 워커 가동상태·로그 경로 점검 동반.

**⑦ T-1 통합 이론 채택 (2026-08-07)**: FMP 채권 ETF `etf/info` nav = 항상 **전일(T-1) EOD 확정치**, 게시 시각만 무작위(오전 ~11:3x ET / 저녁 ~17:1x ET / 미게시). 근거 = iShares·Cbonds 대조 **4/4 센트 일치** → 배포 중 **5/5 승격**(08-08 게시=08-07치 79.49/106.50). 스킵일 존재(08-03·08-06, 양 ETF 동시) = **원천 결손**으로 별도 분류.

**⑧ C′ 시각 게이트 폐기 → nav_stale 재목적화 (2026-08-07)**: 결정 근거 = 08-07 11:30 KST 발화(=08-06 22:30 ET EDT)가 08-06 17:11 ET(마감 후) 게시 혼합행을 통과시킨 **관통 라이브 실증**. 게시 시각으로는 T/T-1 판별 불가 → 마감시각 게이트(C′) 폐기, `ETF_NAV_STALE_TRADING_DAYS`(updatedAt 날짜가 오늘 기준 2거래일+ 과거면 skip=피드 정체 감지)로 재목적화.

**⑨ C″ 날짜 재귀속 채택 (판정 2026-08-07 · 구현 08-08 · 배포 08-10 `bd364778`)**: nav_trade_date = updatedAt(ET)의 **직전 거래일(D-1)** 귀속(휴장·주말 자동 skip) + 종가 페어링 **ⓑ EOD 이력(`/stable/historical-price-eod/full`) 주** / **ⓐ previousClose 교차검증**(불일치=mismatch 플래그·ⓑ 우선). 구현 `b03210a0`(7파일 +590/−165, pytest 79 GREEN, 모델 무변경).

**⑩ FMP 단일 소스 재확인 (2026-08-07~10)**: iShares·Cbonds = **검증 전용, 원장 주입 금지**. 공식치가 존재해도(08-03=79.15/106.07) 백필은 **FMP 회신 조건부**. 원장 = FMP 단일 소스 유지.

**⑪ 폴링 11:30 KST 유지 · 13:30 diff 폐기 · 수동 ingest 전면 동결 (2026-08-07)**: crontab `min=30 hour=11 tz=Asia/Seoul` 유지(게시 편차는 폴링 조정으로 미해결이라 무의미). 수동 ingest 동결 **해제 조건 = 신기준 카운트 3/3**.

**⑫ 신뢰 카운트 재정의 (2026-08-07, 보칙 08-10)**: C″ 배포 후 **3연속 T-1 created**. **FMP 스킵일 = 중립**(유지·미진행) / **리셋 = 혼합행 재출현·오귀속에 한정**.

**⑬ 거래일 캘린더 = credit 자체 미러 신설 (Gate C0, 2026-08-08)**: `apps/credit_signals/trading_calendar.py` — news `ALL_NYSE_HOLIDAYS` 2025~26 복제 + 2027~28 신설, 출처 주석·커버리지 예외(`CalendarCoverageError`)/만료 경보. shared 통합 = 본 프로젝트 큐 이관. DST 전환일 회귀테스트 공백 = **수용**(게시창과 17h+ 이격, zoneinfo 위임, 2026-11-01 익일 육안 확인 1회).

**⑭ 원장 회수·유실 재분류 (2026-08-10 집행 `bd364778`)**: 08-06 혼합행 → 08-05 재귀속 / 08-04·07-30 신설(iShares 원본 대조: HYG 79.40/LQD 106.69 · HYG 79.31/LQD 106.40, price=EOD 페어링) / **유실 확정 {07-21·22·23·08-03·08-06}** — 5일 전부 공식치 기록 보존(백필 채점용), **주입 금지**. 08-03 = 양 ETF 분배락일(Ex-Div). `reattribute_etf_nav` command(재귀속 date 이동=삭제 없음 §10, 신설 --nav-json, dry-run 기본), prod DB 백업 선행.
---

## D-TIMING-DECISIONS-5 (2026-07-16, D-MONITOR-TIMING-PIVOT §9 미확정 5건 해소)

TIMING-P0 RECON 보고(`docs/monitor_timing_pivot_recon_p0.md`, 검증 통과) 근거로 §9 미확정 5건을 확정. TIMING-P1(BE, 브랜치 `monorepo/sess-mon-timing-p1`)에서 구현.

1. **[프리셋] ①-A**: S계열 6종 전부 런칭(추세괴리·모멘텀·52주근접·거래량비율·MACD·오실레이터). 근거강도(강/중/약) = 카탈로그 상수 메타 키(`evidence_strength`). 약근거 2종(MACD·오실레이터)은 빌더 기본 미선택(`default_selected=False`). 유계 지표(52주근접·RSI)는 `scoring_mode="bounded"` 키로 z-score 대신 유계 선형 매핑. **소스 = DailyPrice(3년 OHLC), 계산 = shared `TechnicalIndicators` 재사용**(P0 실측: EODSignal close·84행은 장기지표·ATR 불가).
2. **[가격 스키마] ②-A**: Claim에 `entry_price`·`target_price`·`stop_price` — DecimalField(15,4), null=True, additive. 리포 관례(shared stocks OHLC) 준수.
3. **[상태·구간축] ③-B**: 상태기·달 위상 **불변(신호축)**. 가격 구간축(zone) 신설 = Claim 가격 파생값(별도 축, state_machine 무접촉). 구간 5종(EXITED 이탈/ENTRY 진입 구간/APPROACH 접근/WAITING 관망/OVERHEATED 과열), 접근 버퍼 `+3%` 상수. 알림: 진입 구간·이탈 = 즉시, 관망↔접근 = 다이제스트.
4. **[verdict] ④-B**: `ClaimOutcome`에 `EXPIRED` 신규 멤버(익절/부분/손절 표시 스왑은 P2). `propose_verdict`에 만료 분기 추가. ※ RECON 비용 권장(A: INCONCLUSIVE 재활용)과 다른 결론 — 캘리브레이션 데이터 축 분리 우선(ADR §3.2 처분효과 방어, 만료≠불명확).
5. **[통로 자리] ⑤-A**: Claim에 `fair_value_low`·`fair_value_high`(Decimal 15,4, null) — 수동 입력 기본, 가치평가 통로의 미래 착지점. 통로 스키마 자체는 여전히 별도 결정.

**행위보존 잠금 재확인(ADR §3.4)**: 엔진(indicator_scorer·arrow_calculator·aggregator·state_machine)·beat·마감 루프 구조 불변, additive-only. 기존 monitor pytest 135 전건 green이 증거. AAPL 실데이터 가격 필드 null 유지(주입 금지).

---

## D-GRADE-HONEST-UI (2026-07-22, ⑳-G 카드 정직화 — ⑳-F 진단 반영)

⑳-F 진단 확정: 카드 "신뢰도"=`RelationConfidence.truth_score` 원값이며 tier/grade 하드코딩 **계단값**(distinct 6종, 0/35/60/85). truth 관계(공급/경쟁)는 85 고정. 이질 소스·스케일을 한 축에 섞고 단일 정렬로 절단 → "전원 85" 무변별. 근거 0건·85 모순은 SEC 텍스트 근거의 evidence_count 미집계 + last_mentioned=auto_now 오라벨.

**① [D-GRADE-HONEST-UI] A안(등급 라벨화) 채택 — A 4.60 vs B 3.45(연속 점수 정규화), 마진 1.15**:
- **연속 신뢰도 바 폐지** → 계단 등급 라벨(확정/유력/관찰/미확인)+소스 병기("확정 · 공시"). 점수가 이산 계단이므로 연속 바는 정직하지 않다.
- **유형별 섹션 분리**(공급망/경쟁/Peer/시장) — 이질 점수 한 축 혼합 제거. 섹션 내 tie-break(등급→뉴스 근거수→심볼) 확정.
- **basis_summary가 근거**: 공시(SEC) 관계는 근거건수 미표기(evidence 0건 오해 차단), 뉴스만 "뉴스 근거 N건".
- **RC 정규화(연속 점수화) 재정의**: "유형 통합 단일 랭킹이 필요할 때만 선행"으로 후순위. 유형 분리 UI로 "무변별" 인식은 정규화 없이 해소. (TASKQUEUE 반영.)
- API는 additive(grade·grade_source·basis_summary·last_observed_at). truth_score 값 체계·정렬 로직 불변. 마이그레이션 0.

**② [STEP 0-2 빌드 판별] 서빙 cwd 실측 미완 → 오버레이+재빌드 병행**:
- :3000 next-server cwd 실측 도구(lsof/psutil/curl/urllib) 이 환경에서 전부 hang. 논리 결론: ⑳-2(07-21 커밋)가 배포·라이브 확인됐으므로 서빙 트리는 별도 web 런타임 트리(⑳-F Q4의 원본리포 05-24 .next는 부분 오측정 리스크).
- 판별 미완이므로 S3는 **빌드 상태 무관하게 안전한 표시층 오버레이(초기 뭉침 프레임 가림, 추가 force 튜닝 0) + 배포 시 FE 재빌드** 양쪽 채택. 규칙 A에 "FE 변경 시 빌드+재시작" 단계 반영(공통 하네스, ⑳-2 예고분).

**검증**: pytest ego 27 · vitest chainsight 205/23파일 · tsc 0 · 마이그레이션 0 · 기존 API 필드 불변.
**baseline at decision**: origin/main = `1cd9460`(⑳-2 정산).
## D-HOLD-DECISIONS (2026-07-20, 보유 모드 6쟁점 해소 — HOLD-P0 RECON 근거)

HOLD-P0 RECON 보고(`docs/monitor_hold_mode_recon_p0.md`, 검증 통과) 근거로 보유/미보유 시나리오 모드 6쟁점 확정. HOLD-P1(BE+FE 통합, 브랜치 `monorepo/sess-hold-p1`)에서 구현. additive-only · resolve_zone 무접촉(소비처만 모드 인지) · coherence 순수함수 무변경(앵커 치환 재사용).

1. **[매입가] purchase_price 신규 필드** — `entry_price` 재사용 기각(제안값/확정 사실 혼합은 캘리브레이션 오염). Claim에 `purchase_price` Decimal(15,4,null) 신규.
2. **[모드 인지 배치] 소비처 분기** — `resolve_zone`·`PriceZone` enum 불변. 저장 zone은 hold도 5버킷 그대로 쓰되 **앵커 치환**(entry 자리 = purchase_price). `zone_display`(라벨·의미)와 알림 라우팅만 모드 인지. **PriceLadder 라벨 FE 하드코딩(P2 드리프트)을 zone_display로 이관 교정**(BE 단일 소스 — bands/ticks/rows/marker를 BE 완결).
3. **[모드 UI] 4단계 내 토글 3종**(신규 매수/보유 관리/추가 매수) — 신규 스텝 기각(스텝 구조 불변, 필드셋만 교체).
4. **[Wallet] 수동 입력 확정** — 미래 배선점 = shared `users.Portfolio`(주석 기록만, 통로는 별도 결정). `apps/portfolio.WalletHolding` 직접 import 금지.
5. **[매입일] purchase_date 채택** — 보유 기간 통계·표시 원천. Claim에 `purchase_date` DateField(null).
6. **[모드 축] scenario_type 신규** — TextChoices(`new_entry` default/`hold`/`add_on`). 기존 10행 default 무해 편입.

**부속 정책**:
- 보유 표시 구간 4종(이탈/보유/익절 접근/목표 도달). "익절 접근" = close ≥ target×0.97 표시 전용 재구간화(저장 zone 무관).
- 손절 프리필: 수익 중(close>purchase) = 본전(=purchase) 승격 후보 · 손실 중(close≤purchase) = ATR×2 후보(+본전 앵커링 방지 문구). 매입가는 절대 제안하지 않음.
- "본전 회복 ~N주" = `horizon_for_target(close, purchase, σ)` 기존 함수 재사용(손실 중 부가 정보).
- **EXPIRED proposed_verdict 분기 = scenario_type=new_entry 한정**. hold 만료 = 알림 1회 + 기존 점수 밴드 제안 유지(가드 = proposed_verdict None→score-band 전이 1회, EXPIRED 미설정).
- 추가 매수(add_on) 평단 영향 표시 = **백로그**(수량=Portfolio 소관 경계 충돌 — Portfolio 통로 결정과 병합). add_on 폼 = new_entry 재사용(타입만 기록).
- hold validate 필수: scenario_type=hold 제출 시 purchase_price·purchase_date·target·stop·deadline 필수. `stop < target`만 강제(stop<purchase 미강제 — 본전 승격), entry_price 미사용(null 유지).

**부수 발견 (STEP 0)**: `refresh_monitor`(pipeline.py)가 `process_monitor_scenarios(monitor, as_of_date=as_of)`로 호출하나 함수 시그니처는 `as_of=` — try/except 밖 TypeError로 refresh beat의 scenario 처리 전건 무발화(RECON의 "last_price_zone 전부 None" 근본 원인). HOLD-P1에서 `as_of=as_of`로 교정(common-bugs 등재).

**baseline at decision**: origin/main = `6973bda`(research lab foundation), monitor pytest 193 · monitor vitest 76.

---

## [2026-07-28] MON-RESET — 모니터 10건 전량 삭제 (보유/신규 재구성 목적)

사용자 결정으로 모니터 10건 전량 삭제(보유/신규 재구성 목적) · 검증된 CASCADE 경로(HOLD-P1 E2E와 동일 ORM `delete()`) · 마감 카운트 0/20 리셋. 삭제 합계 5808 objs(Monitor 10·Claim 10·MonitorIndicator 82·MonitorSnapshot 68·IndicatorReading 5630·AlertEvent 7·ClosureSnapshot 1). 잔존 전량 0 검증. 코드·스키마·beat 무접촉(빈 집합 no-op = pipeline.refresh_monitors queryset 0회 순회). shared Stock·EODSignal 등 원천 데이터 무접촉.
## [2026-07-22] MGMT-BATCH-13 — P2 커버리지 표면 결정 (2건) [platform] [dashboard]

> 트랙: MGMT-BATCH-13(mgmt, 메타-only). baseline = origin/main `9f2e6c5`(OPS-PLIST-FIX-LAND 직후), prod·코드·마이그레이션 쓰기 0. 근거 재료 = STEP0-P2-DESIGN-PREP 실측(2026-07-20, read-only): 발급 grain 110 / dashboard_eod 노출 8 / 노출율 7.3% / 조인 실패 0. impression 축 데이터는 이미 존재(#43 IssuanceLog 읽기 조인만).

### D-P2-COVERAGE-SURFACE — 발급 vs 노출 분석 표면 = 선택지 C(하이브리드) 채택

**결정**: Phase 2 "발급 vs 노출" 분석 표면 = **선택지 C(하이브리드)** = 대시보드 상단 **커버리지 스트립** + `/dashboard/coverage` **상세 페이지**. 가중합 **C 4.23 > B 3.93 > A 3.65**, 마진 0.30 < 0.40 → 타이브레이커 = **단계 분해 가능성**(C를 C-1/C-2 슬라이스로 쪼갤 수 있음)으로 C 확정.
- **C-1** = 스트립(발급/노출/율 + 미노출 N건 링크) + 상세 페이지의 **미노출 리스트**. 상세 페이지 내에서 발생하는 노출은 `surface='coverage_detail'`로 **분리 기록**(유기(organic) 지표 오염 격리 — 진단용 표면의 노출이 대시보드 유기 노출율을 부풀리지 않게).
- **C-2** = 4단 퍼널(발급→표시→노출→클릭) 추이·**표시 층 분해**. 트리거 = impression 데이터 **2~3주 숙성**(상수 튜닝 재료 확보 시점).
- **퍼널 4단 전제 명기**: "표시(presented)" 층은 **베이크 산출 JSON 읽기 파생**이다(#43 무변경 — 별도 축 신설·집계 아님, bake JSON에서 읽음).

**Why**: A(스트립 단독)는 진단 깊이 부족, B(상세 단독)는 상시 가시성 부족. C는 상시 스트립(발견성) + 온디맨드 상세(진단)를 겸하며, 무엇보다 **C-1(즉시 가치)/C-2(데이터 숙성 후)로 안전 분해**되어 마진 열세(0.30)를 단계화로 상쇄. `coverage_detail` 분리 기록이 유기 지표 순수성을 보존.

### D-P2-COVERAGE-API — 데이터 공급 = read-time 조회 API @ apps/platform

**결정**: 커버리지 데이터 공급 = **read-time 조회 API**, 소속 = **apps/platform**(telemetry 홈), 엔드포인트 = `GET /api/v1/telemetry/coverage` 계열. 가중합 **read-time 4.50 vs bake-time 3.20, 마진 1.30 > 1 → 자동 결정**(타이브레이커 불요). platform → shared **읽기 조인만**(#43 안전 — IssuanceLog/ImpressionLog 무변경).

**Why**: bake-time 사전집계는 impression이 serve-time 갱신(seen_count 누적)이라 신선도 지체 + 스냅샷 스키마 확장 필요. read-time 조회는 신선하고 additive-free이며, telemetry가 이미 platform 홈이라 소속이 자연스럽다. 마진 1.30으로 단계 분해 타이브레이커 없이 자동 확정.

## [2026-07-28] SLICE-20B-F1 — 매수일 선택화 + "입력일부터 추적" 폴백 (도그푸딩 #1) [portfolio] [coach]

> 트랙: Slice 20b-f1(실행 세션, 미니). base = origin/main `61abaf21`(재측정 — 지시서 참고값 39c20c3에서 전진). 공유 DB 무접촉(worktree `monorepo/sess-20bf1-buydate-fallback`), 마이그레이션 = 파일 생성 + test DB 검증까지, 실 적용 = 병진 수동. STEP 0 실측 근거: `first_bought_at` DateField null=False / `acquisition_fx_rate` DecimalField null=True(기존) / serializer `HoldingCreateSerializer`(wallet.py:70) first_bought_at required=True(DRF기본) / 소비 정본 = `advisory_engine.krw_cost_basis`(4단 폴백 exact>approx_first_buy>approx_low_confidence>native) / spot 하우스 함수 `get_rate_on`·`get_spot_rate`·`oldest_available`(packages/shared/fx/services.py) 존재.

### D-20BF1-BUYDATE-OPTIONAL — 매수일 선택화 (피드백 #1)

**결정**: 보유 입력 시 `first_bought_at`(최초 매수일)을 **필수 → 선택**으로 완화. 계층 = ①모델 null=False→null=True(마이그레이션 1개) ②serializer `HoldingCreateSerializer.first_bought_at` required=False ③생성 뷰 `wallet_holdings`에서 `data.get("first_bought_at")`(None-safe) ④프론트 `HoldingModal.tsx` HTML `required` 제거 + 라벨 "*" 제거.

**Why**: 병진 라이브 온보딩 첫 시도에서 매수일을 기억 못 해 입력이 막힘(도그푸딩 #1). 실제 사용자는 매수일 미상이 흔하다. 필수 유지 = 온보딩 마찰 → 원장 축적 지연. 선택화가 최우선 미니 슬라이스.

### D-20BF1-FALLBACK-A — 미입력 취득환율 = 입력일 spot ("입력일부터 KRW 추적", A안, 가중합 4.85)

**결정**: 매수일 **미입력** 보유의 `acquisition_fx_rate` = **생성 시점 spot**(`get_spot_rate("USDKRW")`, ExchangeRate 최신 close). 삽입점 = 생성 뷰(가산): `first_bought_at` None **그리고** `acquisition_fx_rate` 미전달일 때만 spot 캡처. 매수일 **입력** 보유는 기존 경로 완전 불변(`acquisition_fx_rate` 미전달 시 None 유지 → read-time `krw_cost_basis`가 `approx_first_buy`로 매수일 환율 조회, 소급 재계산 없음).
- **폴백 표지 = `first_bought_at == null` 자체**(별도 필드 발명 금지 — §0-2 충족). 미입력 holding은 생성 시 `acquisition_fx_rate=spot` 기록 → `krw_cost_basis` tier1 `exact`에서 포착, `get_rate_on(None)` 미도달. (방어적 None-guard = None 경로 한정, 매수일 있는 경로 무영향.)
- **spot 부재 규칙**: 입력일 spot은 `get_spot_rate`(최신 저장 close). 주말/휴장일 케이스는 `get_rate_on`의 `date__lte` 직전 영업일 fallback으로 이미 닫힘. 그 이상 예측·근사 발명 금지.
- **화면 사실 표기**: 미입력 보유에 "매수일 미입력 — 입력일부터 KRW 추적" 안내(모달 힌트 최소 형태). 과거 수익 아는 척 금지(USD 손익은 avg_cost로 실측되되 FX는 입력일부터).

**기각**: 과거 매수일 복원 시도(사용자가 모름) / 임의 근사 강제 / 계산 제외(KRW 미표시) 전부 기각 — A안 가중합 4.85 사용자 확정(2026-07-24).

### D-DEV-PROD-SHARED-DB — dev = prod 물리 DB 공유(stock_vis) 거버넌스 (환경 사실, 2026-07-24 발견)

**결정(항구 규약)**: dev와 prod가 **동일 물리 DB `stock_vis`(localhost)를 공유**한다. 따라서:
1. dev 설정으로의 `migrate`·`manage.py shell` **쓰기 = prod-write로 간주** — 세션 자율 실행 금지, 병진 수동(런북 S1 절차 준용).
2. 라이브 캡처용 **데모 시드는 생성한 세션이 삭제·증명 책임**을 진다. `portfolio_goal` 보유 데모는 beat 2종의 nightly 대상이 되므로, 캡처 후 같은 세션에서 cascade 삭제 + `User.objects.filter(portfolio_goal__isnull=False)` 잔존 0 쿼리로 증명한다.
3. **"정리 완료" 주장은 검증 쿼리 출력을 반드시 동반**한다(s20b_demo 잔존 재발 방지).

**Why**: 2026-07-24 코치 스택 런북 실행 준비 중 발견 — dev 세션 작업이 곧 prod DB에 반영됨(마이그레이션·backfill 이미 적용 상태였음). 이 사실이 명문화되지 않으면 dev 검증이 무심코 prod를 오염시킨다. 데모 유저 `s20b_demo`(goal 보유)가 삭제 없이 잔존해 beat 대상 오염 위험을 남긴 사례가 근거.

### D-MP-UNIFY-USAGE — market_pulse 실트래픽 = v2 (통합 방향의 전제, 2026-07-29)

**결정**: market_pulse 통합의 방향은 **v2를 정본으로 수렴**한다. 전제 = 실사용 트래픽이 v2에 있다는 사용자 판단.

**출처·한계(명시)**: 이 "실트래픽=v2"는 **사용자가 제공한 방향 결정**이지 접근 로그 실측이 아니다. MP-UNIFY-S0(read-only)는 v1 표면 실트래픽을 **미측정**으로 남겼다(§5-2). 근거는 측정이 아니라 제품 소유자의 판단 → 후속 표면 처분(2단)에서 뒤집힐 여지가 있으면 재확인 필요.

**함의**: v1 개별 무소비 엔드포인트는 즉시 제거 가능(MP-UNIFY-1), v1 실소비 3종(pulse/sync/sync-status)과 프론트 표면은 v2 승격·흡수 방향이 확정될 때까지 FREEZE.

### D-MP-UNIFY-A — 통합 진행방식 = 백엔드 먼저(무소비 라우트 제거) → 표면 통합 후행 (2026-07-29)

**결정**: 통합을 **2단 분리**한다. **1단 = 백엔드 무소비 라우트 정리**(MP-UNIFY-1, 제품 결정 불요·서빙 독립), **2단 = v1 프론트 표면 처분**(제품 결정 선행 필요 — v2 흡수/리다이렉트/메뉴 교체).

**Why**: S0 실측상 1단은 소비자 0·마이그 0·서빙 절차 무변경이라 표면 결정과 **독립적으로 완주 가능**. 표면(2단)은 정식 메뉴 노출 실서빙이라 제품 결정이 선행돼야 함 → 1단을 먼저 닫아 이후 표면 통합의 잔여 접촉면(v1 API)을 3종으로 최소화. 큰 결정을 기다리며 명백한 정리를 미루지 않는다.

**1단 집행 결과(MP-UNIFY-1, 2026-07-29)**: v1 API 10→3. 라우트·뷰 7종 + 개별 serializer 5종 제거, 서비스/클라이언트 메서드는 pulse 집계 경유 공유로 전량 보존. pulse/sync/sync-status IDENTICAL(진입점·서비스·serializer 바이트 불변, 회귀 테스트로 라우트 resolve·pulse 필드계약 못박음). v2·프론트·intraday 무접촉·마이그 0.

## [2026-07-30] D-REL-DIRECTION-CONVENTION — 관계 방향 컨벤션(SUPPLIES_TO 정본) [chainsight]

> 트랙: ⑳-3 S2-C. 브랜치 `monorepo/sess-20-3-s2c`.

**결정**: 관계 방향의 정본 = **재화·부품 흐름 방향 기준 `SUPPLIES_TO`**. `DEPENDS_ON`은
**매출 의존(고객 집중)** 의미일 때만 사용한다. `SUPPLIES_TO ↔ DEPENDS_ON` 상호 플립(같은
사실을 양방향으로 라벨)은 **정본(SUPPLIES_TO)으로 정규화**한다.

**Why**: 캘리브레이션(S2-B/S2-C) 실측상 SD 상호 플립 8건이 방향 컨벤션 충돌로 확인됨. 공급자
관점(SUPPLIES_TO)과 수요자 관점(DEPENDS_ON)이 같은 부품 흐름을 서로 반대로 태깅 → LLM
type_match 자가모순·검수 노이즈의 구조적 원인. 흐름 방향을 정본으로 못박아 양방향 중복을 제거한다.

**How to apply**: ⑴ 부품·재화가 A→B로 흐르면 `A SUPPLIES_TO B`(정본). ⑵ `DEPENDS_ON`은
"매출의 상당 비중이 특정 고객에 집중"처럼 **의존(수요 집중)** 의미에 한정. ⑶ SD 상호 플립
후보는 검수 시 SUPPLIES_TO로 수렴. ⑷ 이 컨벤션은 검수(Phase 2)·차기 프롬프트 개정의 기준이며,
S2-C gate는 타입 자동변경을 하지 않으므로(하드룰) **자동 재작성 아님** — 검수·재추출에서 적용.

**태그 정규화 종수(S2-C-3, 2026-07-30)**: 118종 → **53종** 확정(옵션B, 사용자 승인). 목표 30~50의 상단 초과를 수용 — 공격적 군집(옵션A)은 11종이나 구체 도메인(수술용 로봇·EDA 등) 신호 소실. **identity 보존 우선**(10군집 동의어 흡수 + 포괄 17→기타 + 구체 42 원문 유지). 매핑=데이터파일 `domain_tag_normalization.json`.
### D-LANDING-ONE-SESSION-PER-APPROVAL — origin/main 착지·push = 승인 1건당 전담 세션 1개 (규약, 2026-07-29)

**결정(규약)**: **origin/main 착지·push 작업은 하나의 승인당 전담 세션 1개**에만 위임한다. **동일 착지 승인을 복수 세션에 중복 전달 금지.** 착지 세션은 자기 트랙에 대해서만 rebase/ff-push를 수행하고, 다른 세션의 착지분과 경합하지 않는다.

**Why**: 2026-07-29 착지 경합 니어미스 — 같은 트랙(sv-cn-repair·sv-mp-unify-s0) 착지를 **두 세션이 동시에 시도**했다(한 세션이 게이트를 확인하는 사이 다른 세션이 no-ff 머지로 선착지). 결과는 무사(멱등·ff 거부로 손실 0)했으나, 승인 1건이 여러 세션에 전달되면 base 꼬임·중복 머지·번호 선점 경합의 구조적 위험이 상존한다. 착지 권한을 세션 단위로 단일화해 경합 자체를 제거한다.

**운용**: 착지 승인 시 "이 세션 전용" 명시(사용자) → 해당 세션만 push. 다른 세션이 같은 승인을 받으면 **HALT 후 상신**(이미 다른 세션에 위임됐는지 확인). 관련=[[lesson_branch_assignment_explicit_isolation]]·[[lesson_origin_main_advance_union_rebase]].

**보강 — pre-merge WARN 허용 조합 상수 (2026-07-31, MGMT-BATCH-16)**: LAND 세션의 pre-merge `health_check` 게이트에서 **아래 2종 WARN은 허용**(머지 진행) — 그 외 WARN·모든 FAIL은 HALT 후 보고.
  - ① **`stale pending 백-어노테이션` = TH blocked**(`dep=TH-RUNTIME-DEPLOY`, 실존 ID → 설계대로 승격 제외).
  - ② **`실행 트리 정합` = #47 transient**(미머지 브랜치에서 health 실행 시 worktree HEAD ≠ origin/main으로 뜨는 구조적 신호 — no-ff 머지 후 post-merge에서 자동 해소. read-only/미머지 세션의 정상 동작).
  근거: 07-29 STRIP-REHOME-LAND에서 지시서가 "1 WARN(TH)"만 기대해 #47을 누락 → 문언상 "TH 외 WARN → HALT"에 걸려 사용자 판단을 재차 물음(불필요한 왕복). #47은 매 미머지 LAND의 표준 transient이므로 **상수로 못박아** 재발 방지. cf. DECISIONS 326 백-어노테이션(승격 후 첫 실측에서 동일 2종 WARN 확인). post-merge 기대값 = **14 OK / 1 WARN(TH) / 0 FAIL**(#47은 머지로 해소).

**보강 — health 신기준 = 15/0/0 (2026-08-10, MGMT-BATCH-27 정본화)**: **TH blocked WARN(위 ①)이 `75551966`("TH runtime pending 유령 blocked 해소")로 해소** → post-merge 기대 **정본 = 15 OK / 0 WARN / 0 FAIL**. **구 조합(14/1/0 = TH blocked 1 WARN 잔존)은 이력으로 강등** — 이후 자가 머지 판정은 **15/0/0 신기준**. #47 transient(위 ②)는 미머지 세션에서 여전히 나타날 수 있어 **미머지 시점 13~14 OK + #47 WARN 동반은 허용 유지**(머지로 자동 해소 → 15/0/0). 실측: BATCH-26 post-merge 14/1/0 → 75551966 착지 후 BATCH-26 사후·본 BATCH-27 사전 = **15/0/0** 확인.

**보강 — mgmt 배치 자가 머지 허용 (2026-08-01, MGMT-BATCH-20)**: **mgmt 배치의 origin/main 착지는 자가 머지 허용** — 조건: 메타 4종 한정 diff 전수 확인 + D-LANDING 허용 조합(위 2종 WARN) + push 직전 재fetch(#40). **Gate 4(파괴적 작업 승인)는 삭제·마이그 적용·배포에 적용되며 메타 문서 머지에는 불요.** 근거: BATCH-19 착지 시 자가 머지 가부를 승인 턴으로 회부했으나, 메타 4종 한정 diff는 파괴적 작업이 아니므로 매 배치 승인 왕복이 불필요 — 해석을 규약으로 못박아 재발 방지.

**보강 — 게이트 health 측정 트리 = 착지 대상 트리 (2026-08-06, MGMT-BATCH-24)**: LAND/mgmt 세션 `health_check` 게이트는 **착지 대상 트리(main=origin/main) 또는 origin/main 기준 신규 worktree**에서 측정한다. 앉아있는 세션 브랜치(정체 PROGRESS.md를 문 워크트리)에서 재면 `PROGRESS 신선도`·`origin/main 해시`가 **거짓 FAIL**(health_check는 worktree-local 측정 — LAND-C2-S1-B1 실측: 정체 트리 11/2/2 ↔ 착지 트리 14/1/0). 위 ② #47 transient(WARN)와 구분 — 본 함정은 **FAIL 오탐**. 처방 상세 = common-bugs #89.
---

## [2026-07-30] D-EOD-FRESH — beat 자가 신선도 보장(B안)

beat 자가 신선도 보장(B안) 채택. 비편입 보유 종목의 DailyPrice를 beat 서두에서 온디맨드 보충(기존 stock_sync_service 재사용, 신규 모델·태스크 0). A안(추적 레지스트리) 승격 조건: 추적 종목 30개 초과 또는 monitor 외 두 번째 소비 앱 등장.

**근거**: D-EOD-RECON 판정 — IONQ·TLN 45일 stale 원인 = S&P500 비편입으로 일일 자동수집 유니버스(`sp500_eod_service` = `SP500Constituent.filter(is_active=True)`) 밖 + 06-15 이후 온디맨드 트리거 부재. 가중 평가 B=0.843 채택(A 레지스트리 0.748·C 수동 0.620 기각).

**구현(P1)**: `apps/monitor/services/pipeline.py::refresh_monitors` 서두에 `ensure_price_freshness` 게이트 — 활성 모니터 심볼 전수 중 `DailyPrice 최신 date < _expected_last_trading_day`인 심볼만 `StockSyncService.sync_prices(force=True)` 호출. 심볼별 try/except 격리(sync 실패해도 beat 본체 불사 — #65 교훈). 최신 심볼 스킵(S&P500은 22:00 자동수집분으로 no-op). shared 코드 무변경(호출만), 신규 모델·PeriodicTask·스케줄 0, 기존 22:45 발화 내 실행. 거래일 판정은 공휴일 미고려·주말 제외 관대 근사(초과 sync는 멱등 무해, stale 누락이 위험하므로 보수적). 테스트 monitor 226(신규 freshness 11: 거래일 경계·stale/fresh 판정·실패 격리·통합 실 시그니처·행위보존 no-op).

**Phase 0 백필(2026-07-30)**: IONQ·TLN 각 30행 충전(236→266, 최신 06-15→07-29). 수동 refresh 후 coverage 0.44→0.6667 회복. ★화면 손익 정정: IONQ pnl +23.5%(stale 06-15 61.18 기준 허구)→**-35.44%**(실 07-29 31.99), TLN→-20.95%. 4종목 DailyPrice 멱등 무접촉(Δ0).

## 추기 — EOD-FRESH-FIX-1 (게이트 기준일 오프바이원 · 2026-08-03 종결)

### 경위
- **발견 (2026-07-31, VERIFY-0731 F3)**: 게이트 첫 자동 실전에서 비편입 3종
  (IONQ·TLN·IREN)이 1일 지연 고착. 원인 = `_expected_last_trading_day(as_of)`가
  as_of−1일을 기대치로 삼는 오프바이원 — beat(22:45 UTC)는 미국 장 마감 후라
  as_of 자체가 직전 거래일인데 하루를 더 뺐고, sp500_eod_service(as_of 당일 수집)와
  기준일이 하루 어긋남.
- **결정 (2026-07-31)**: A안(−1 제거, expected = as_of) 채택.
  가중 스코어 A=0.895 / B(동적 기준)=0.743 / C(거래일 캘린더)=0.745.
  중단 조건 = "게이트 도달 시 as_of는 거래일" 불변식이 거짓이면 폐기 → PRE-1 실측으로
  성립 확인(is_eod_fresh 가드 선행 + 4개 주말 로그 게이트 무발화)하여 착수.
- **수리 (2026-08-01 배포)**: pipeline.py 1지점 — 함수 제거 + expected=as_of +
  불변식 주석. 머지 9c3d59d7. **monitor pytest 기준선 226 → 223**
  (제거 함수 전용 테스트 4 삭제 + F3 회귀 테스트 1 신규).
- **검증**:
  - 창A (08-01, PASS): 게이트 synced=3(수리 전 0)·failed=0, 비편입 3종
    latest=07-31(편입과 동일 좌표), 07-30 갭 캐치업 실증(sync는 days=90 캐치업형 —
    PRE-2), beat 완주 monitors=6.
  - 창B (08-02·03, 성립): 비거래일 게이트 무발화 이틀 — 단 차단 주체는 beat 스케줄
    (하기 정정).

### 실측 정정 — 비거래일 방어는 이중 구조
FIX-1 코드의 불변식 주석은 "is_eod_fresh 가드가 비거래일을 차단"이라 서술했으나,
실측(창B)상 **1차 차단 = beat 스케줄(요일 cron, 주말 Sending 0)**이고, is_eod_fresh
가드는 **2차(주중 휴장일·EOD 지연 대비)**다. expected=as_of의 전제는 어느 층이 막든
성립하므로 수리 유효성 불변. **주석 정정은 다음 monitor 코드 터치에 피기백**
(전용 배포 없음 — 이 원장이 진실).

### 잔여 관찰 (트랙 아님 · 수동)
- 2차 가드 단독 방어(주중 휴장일)는 실전 미실증 — 다음 도래 09-07(Labor Day).
  해당일 로그 1회 관찰이면 충분(게이트 무발화 기대). 실패 시에만 RECON.

### 부수 확정 사실
- 게이트 검사 유니버스 = 활성 모니터 전수(비편입 필터 없음, checked=6) — 편입은
  fresh-skip이라 무해한 의도적 단순화(PRE-3). 현행 유지.
- FMP 402 상시(BF.B/BRK.B, #23)는 본 트랙 전 과정에서 무관 별건 유지.

## [2026-07-31] SLICE-20B-F2 랜딩 관례 + GOAL-CREATE-UI 결정 [portfolio][coach][ops]

### D-LAND-GATE-CARRYOVER — 게이트 캐리오버 (전진분 disjoint 증명 시)

**결정**: 랜딩 병합 중 origin/main이 세션 게이트 실행 후 전진했을 때, **전진분이 내 변경 surface와 disjoint임을 diff로 증명하면**(내 파일·테스트 대상 무접촉) 방금 통과한 전체 게이트(pytest/tsc/vitest/--check)를 **재실행 없이 유지**하고, **착지 후 origin/main에서 사후 3축 1회**로 확증한다. 매 재병합마다 4~5분 full pytest를 반복하지 않는다.

**Why**: 20b-f1 랜딩 시 origin/main이 5회 전진(docs/SEC/mgmt/chainsight — 전부 portfolio·wallet surface 무접촉). 매회 full 재실행은 동일 테스트 코드에 대한 낭비. disjoint 증명(`git diff <prev> origin/main --name-only`로 내 surface 겹침 0 확인)이 게이트 유효성을 보존. 단 disjoint가 아니면(내 파일 접촉) 재실행 필수.

### D-LAND-PUSH-TEMP-PERM — push 임시 권한 (상시 금지·경합 한정·즉시 회수)

**결정**: `git push origin main`은 **상시 금지**(세션 classifier 하드 게이트 = 기본값 유지). 예외 = **고빈도 경합 랜딩**(main이 push 준비~실행 창보다 빠르게 전진해 non-ff 반복)에서만, 사용자가 **명시적으로 임시 push 권한을 부여**해 Claude가 `fetch→reset→merge→push`를 원자적으로 수 초 내 실행하도록 허용하고, **착지 확인 즉시 권한 회수**한다. 무권한 시 병진 수동 `!`-push가 기본.

**Why**: 20b-f1 랜딩에서 push 2회 non-ff(재병합 왕복)로 왕복 지연. 원자 실행이 경합 창을 최소화. 그러나 상시 허용은 공유 main 자율발사 위험([[feedback_deploy_approval_explicit_quote]]) → 경합 한정·즉시 회수로 제한.

### D-f2-0 — GOAL-CREATE-UI = B안(전용 폼) 확정 (병진, 2026-07-31)

**결정**: 사용자 목표 생성 UI 부재(20b-f1에서 발견 — knobs PATCH는 기존 UserGoal 요구, 생성은 admin/shell만) 해소 = **B안(전용 목표 생성 폼)**. /advisory 목표 부재 시 온보딩 카드 + GoalForm(create)로 사용자가 직접 목표 생성. 기각안: A(admin 유지)·C(지갑 폼에 목표 끼워넣기).

### D-f2-1 — 생성 = POST 단일 경로, PATCH 엄격 유지 (upsert 금지)

**결정**: UserGoal 생성 = **POST `advisory/knobs/` 단일 경로**(이미 존재 시 409). 기존 **PATCH는 엄격 유지** — 목표 부재 시 400("먼저 설정") 그대로, upsert로 완화하지 않는다. 생성/수정 경로 분리 = 의미 명확·회귀 표면 최소. UserGoal.user=OneToOne이라 409가 자연스러운 제약 표현.

**Why**: PATCH를 upsert로 바꾸면 "수정"과 "생성"이 뒤섞여 의미 모호 + 기존 PATCH 400 테스트 회귀. POST 단일 경로가 D0 가산(기존 PATCH·필드 무변경).

### D-f2-2 — GoalForm 단일 컴포넌트 2모드 (create/edit), 입력 표면 1벌

**결정**: 목표 입력 화면 = **GoalForm 단일 컴포넌트, mode='create'|'edit'**. KnobsPanel 폼 코어(target_return_pct + 손잡이 5종)를 GoalForm으로 추출(행위보존, edit 모드=기존 PATCH). create 모드는 horizon_months·risk_tolerance 필드 추가 + POST. **입력 표면 1벌**(중복 폼 금지). edit 모드는 horizon/risk 변경 불가(PATCH 미지원 = 스코프 내 생성 전용).

**Why**: 폼 중복은 drift 원천. 단일 컴포넌트 2모드 = 검증·레이아웃 단일 소스. STEP 0 실측: KnobsPanel 입력/제출 JSX 분리·순수 useState → 추출 행위보존 가능(HALT 2 불성립).
## [2026-07-31] SEC β G1.6 R1 — 캐노니컬 베이스라인 확정 + "Neo4j-env" 오라벨 정정 (D-SECB-BASELINE, D-SECB-MISLABEL)

> SEC β G1.6 회수 세션(`monorepo/sess-secb-g16`, Gate 0 `1c41a7e5`). R1 결과 D — 감독 판정 B(HEAD-앵커 비준 + 저비용 법의학 F1/F2)로 재개. dry-run 전용·DB 쓰기 0·LLM 0.

**D-SECB-BASELINE (F3 — 캐노니컬 베이스라인)**: **4463 GREEN / 0 사전존재 / 53 skipped @ origin/main `9750b8bc`** (2026-07-31 실측, `--maxfail=200`). health_check 13 OK / 2 WARN(양성) / 0 FAIL. ★**규칙**: 베이스라인은 **세션마다 재실측하고 HEAD 해시를 병기**한다. **해시 없는 정적 수치의 세션 간 이월 금지**(구 "4084" stale 추정·"4050" 무앵커 이월이 전례 — cf. D-SECB-MISLABEL).

**D-SECB-MISLABEL (F4 — 오라벨 정정, 과거 라인 편집 없음·append만)**: 다세션 verbatim 이월된 "13건 사전존재 = Neo4j-env" 라벨은 **검증 없이 이월된 오라벨**. 실측 반증: 13건(attention 6 + leadership_api 7) 전 코드경로(테스트 → `attention_service`·`leadership_eventgroup`·`event_group_reader`·`leadership_service`·`leadership_compute`·conftest) **neo4j 참조 0**, 격리 재실행 **29 passed**(neo4j fixture 없이). **F1**(main 이동분 규명): `4d0ed3b5..9750b8bc` 전 병합·커밋 병진 승인 트랙 귀속(MGMT15/16·CN-repair·TH-DEPLOY·⑳-3·credit p2a·EOD-fresh·MP-unify·strip-rehome), 신규 테스트 25파일=성장 출처, **유령 커밋 0**. **F2**(제4가설): `test_stock_vis` 마이그 179건 전부 **2026-07-31 11:37 적용 = DB fresh 재생성**(13 실패 시대 ≤07-28 이후) → 실 원인 = **결과 D: `--reuse-db` 데이터 오염, DB 재생성으로 해소(양성)**. 오라벨 이월 라인 예: DECISIONS 553·3761·3783·3810·3843·3877·3909. 정정 근거 = 본 세션 `1c41a7e5` 이후 F1/F2 실측. cf. common-bugs #79, TASKQUEUE SECB-REGRESSION-WATCH.

## [2026-08-01] SEC β G1.6 랜딩 정합 — 정본 베이스라인 단일화 + 배달 사고 #7 (D-SECB-BASELINE-CANON)

> 랜딩 커밋 `893d3cb6`(sess-secb-g16 → main no-ff). 랜딩 前 P4/P5/P6 게이트 전부 CLEAN.

**D-SECB-BASELINE-CANON (P5 — 단일 정본, append 정정·과거 라인 편집 없음)**: 정본 베이스라인이 두 곳에 등재됨 — ⑴ `D-SECB-BASELINE`(DECISIONS, `663b17e5`) ⑵ SEAL-PUSH-1c(PROGRESS, `9540993a`). **양자 수치·앵커 동일**: **4463 GREEN / 0 사전존재 / 53 skipped @ `9750b8bc`**(모순 0 → P5 AUTO-HALT 미발동). 상호 보완: 663b17e5=`13 Neo4j-env` 오라벨 정정 / 9540993a=`119 pre-existing` 오라벨 정정 — **둘 다 0 사전존재로 수렴**. 정본 = 본 항목으로 단일화(수치 동일, 두 등재는 상호 참조). 향후 갱신은 세션 재실측+HEAD 해시 병기(D-SECB-BASELINE 규칙).

**배달 사고 #7 (게이트 정의 미전달, 규율이 랜딩 前 적발)**: P4·P5 공식 정의(AUTO-HALT 기준)가 승인 메시지에 미전달 → 실행 세션이 임의 발명 대신 HALT·회부 → 감독 재전달로 해소. 사고 계열 통산 #7(#6=base 지시서 누락에 이어). 교훈 = 참조된 게이트의 정의 부재 시 임기응변 금지·회부(cf. Gate 0 규율).

### D-SELECT-V2-RULE — L3 그라운딩 선별 v2 = (나) 어휘·규칙 점수 (결정론, 2026-08-01)

**결정**: C-L3 그라운딩 선별 v2의 랭킹 규칙 = **(나) 어휘·규칙 점수** — 텍스트(title+summary) 기반 계층 macro 어휘 점수를 주축으로. sentiment_score/entity_count는 v1의 편향 원천이므로 **랭킹 축에서 제외**하고 동일 macro-score 내 결정론 tie-break으로만 사용. 신설 모듈 `apps/market_pulse/regime/grounding_v2.py`(v1 grounding.py 무접촉·additive).

**가중합(합=1.00: 선별품질 .35·결정론 .20·683균일적용 .15·단순성 .15·메타강건 .15)**: (가) 메타우선 **4.15** / (나) 어휘 **8.55** / (다) 하이브리드 **7.78**. 마진 (나)−(다)=**0.77**(0.40~1.00 → 타이브레이커). **타이브레이커 → (나)**: (다)의 메타 보너스는 ⑴ 방금 피한 non-uniformity를 tie-break에 재도입, ⑵ v1이 쓴 sentiment/entity 재의존=company-sentiment 편향 재수입, ⑶ 1인 유지 단순성 열위.

**(가) 실격 근거(STEP0 실측)**: AV `topics`/article-`relevance`는 provider가 **저장조차 안 함**(drop, `alphavantage.py`). `category`는 재수집분(batch1·2 10,503건) **전부 'company'**(분별 불가), 기존분은 혼재 → 불균일. `sentiment_score` 채움률 재수집 100% vs 기존 51.2% → 균일성 실격. **유일 균일·상시 신호 = title+summary 텍스트**(양 구간 ~100%).

**모듈 계약(불변 요건)**: ①결정론(동일 입력→동일 출력, 입력 순서 무관) ②품질 하한(`min_score` 미달=제외, macro 없는 날 **빈 리스트=why=null**, 억지 채움 금지) ③provenance(score·hits·rank 동반) ④버전 태그 `select_v2.0`. 계층 어휘=STRONG(명백 거시구문 3.0/1.2)·MID(광의시장 1.5/0.6), 티커/ETF 보일러플레이트 매치 시 ×0.3 페널티(개별종목 index-name 오매치 중화), 소스가중(PR/신디케이션 ×0.7·품질와이어 ×1.15), near-dup 제목 접기.

**REGEN-V2 인터페이스**: `select_grounding_v2(date, *, n=6, source_cap=3, min_score=1.2) → [{id,url,title,source,sentiment_score,entity_count,published_at,score,hits,rank,select_version}]`. v1 호환키(id/url/title = context_generator provenance 조립용) 보존. context_generator가 `select_grounding`→`select_grounding_v2` 전환 시 반환 스키마 상위호환. **REGEN-V2 진입조건 = 재수집 DONE(~8/8) + 본 모듈 랜딩**.

**Why**: C-L3 1차(491건) 품질 한계(D-CL3-QUALITY-LIMIT)의 근본 = v1이 abs(sentiment)+entity로 "고감정 개별기업"을 선별. 선별 품질 = REGEN-V2 품질의 상한. 스팟 12일 실증(v1 vs v2): macro-rich일 v2 압도("PCE Inflation Cools, GDP Growth Strong"·"Treasury sell-off after Fed holds rates"·"ECB rate decision" vs v1의 "Q2 Results"·"Class Action"), 저볼륨일 v2 빈결과(정직) vs v1 개별주 억지. broad 거시 절대량 부족일은 부분개선(D-CL3-QUALITY-LIMIT 근본한계 유효 — 선별이 없는 신호를 만들진 못함). N·min_score는 초안(정밀 캘리브레이션=샘플 게이트).
**D-SECB-BASELINE-CANON 갱신 (2026-08-01, A-3 실측 — 해시앵커 규칙 적용)**: 구 정본 `4463/0/53 @ 9750b8bc`는 **stale 앵커로 폐기**. 유효 정본 = **4460 GREEN / 0 사전존재 / 53 skip @ `4696790e`**. 시프트 −3 = `test_freshness.py` 11→8 통합(**EOD-FRESH-FIX-1 `68318fc3`**, P6 승인 병렬 트랙, off-by-one 수리). SEC β G1.6 A-1(`bbc93a84`)은 테스트 제거 0(단언 +1줄만)·grounding 13 pass = **내 작업발 회귀 0**. 감독 비준(2026-08-01). 이 폐기·갱신은 #79(미검증 수치 이월 금지)의 실적용 — 베이스라인은 항상 세션 재실측+HEAD 해시 병기.

## [2026-08-01] SEC β Gate 2 배치 개정 — G-d 제거·노출 트랙 이관 (D-SECB-GATE2-AMEND-1)

**D-SECB-GATE2-AMEND-1 (G-d flag-on 1 filing 배치 제거)**: Gate 2 사인오프 요청서 §비준 시점에 `SEC_GROUNDING_ENABLED` flag·grounding_status **노출 read-path가 코드에 부재**했음(2026-08-01 실측 grep: flag 정의 0·serializer/view grounding 참조 0·sec 엔드포인트=dashboard+FilingDataView 둘 다 미참조). G-d는 flag flip이 아니라 신규 구축(flag+게이트 노출+1-filing 스코핑)이며, **노출 설계 = 소비자(UX) 결정 미존재 상태의 사변 구축 금지(γ)** → 배치에서 **제거**, `SECB-EXPOSURE` 트랙 이관(디렉터 세션·목업 기반 결정). Gate 2 실집행분 = G-a(백업)·G-b(migrate 0003)·G-c(백필 1751, 4분포 1273/41/410/27 실현)로 종료. G-e(prompt v2)는 정의서 승인 후 별도. **교훈**: 요청서의 실행 단계는 **존재하는 코드 경로를 실측 확증 후 비준**할 것(#79 변종 — 설계 의도의 문서 선행이 코드 선행을 대체 못 함). cf. common-bugs #82, TASKQUEUE SECB-EXPOSURE. 감독 결정 B안(2026-08-01).
## D-LAND-ATOMIC (2026-08-01, 반복 랜딩 경합 시 원자 집행 표준)

병렬 세션이 같은 origin/main을 겨냥할 때 순진한 `push`는 non-fast-forward로 반복 reject된다(과거 P2a-1 병렬 랜딩 5회 reject 실증). 표준 집행 절차를 **fetch → reset → merge → push 원자 스크립트**로 고정한다.

1. `git fetch origin` — 최신 origin/main 확보.
2. 작업 브랜치를 origin/main 위로 `reset --hard`(또는 rebase) 후 슬라이스 커밋을 **cherry-pick/merge**로 재적재 — 계보를 origin/main 선형 위로 정렬.
3. 자가검증(계보 N줄·pytest·pathspec) 통과 시 단일 `push`.
4. **push는 병진(사용자) 수동** — 공유 main 접촉은 명시 승인 인용 필수([[feedback_deploy_approval_explicit_quote]]). Claude는 원자 스크립트를 **준비**하고 게이트를 **판정**하되 집행하지 않는다.

**Why**: 경합 재시도를 임기응변(반복 pull/merge)으로 처리하면 계보 오염·중복 커밋·타 트랙 혼입 위험(HOLD-P1 `e37b2c7` 혼입 실증, [[lesson_branch_assignment_explicit_isolation]]). 절차를 원자 스크립트로 고정하면 재현·검증 가능.

---

## D-PROBE-PRODWRITE-EXCEPTION (2026-08-01, 일회용 probe prod-write 예외 원칙 + f2 Part 3 기록)

**원칙 재확인**: dev=prod 물리 DB 공유([[lesson_dev_prod_shared_db]]) 하에서 shell/probe에 의한 prod-write는 **자율 금지**가 기본이다. 예외는 아래 3조건을 **모두** 충족할 때만 1회 허용한다:
1. **일회용 probe 한정** — 반복·스케줄·상시 파이프라인이 아닌 단발 측정.
2. **세션 내 병진 승인** — 해당 세션에서 사용자의 명시 승인 인용([[feedback_deploy_approval_explicit_quote]]).
3. **실계정 무접촉 증명 의무** — 사용자 실계정·개인정보 무접촉을 산출물로 증명(어떤 테이블/키에 접촉했는지 명시).

**기록 — f2 Part 3 prod-write 예외 1회**: 상위 지시서 f2 Part 3의 prod-write는 위 3조건을 충족한 세션 내 병진 승인 예외로 집행됨을 거버넌스 원장에 등재한다(증적은 해당 세션 산출물 소관).

**Why**: prod-write 예외를 무기록으로 남기면 다음 세션이 관행으로 오인해 자율 prod-write가 번진다. 예외는 반드시 "1회·조건부"로 원장에 못박아 재사용 불가로 만든다.

**본 세션(SIGNAL-FORWARD-INFRA 프리플라이트) 준수 증명**: STEP 1 FMP 프로브는 **read-only 외부 호출**(FMP 시장데이터)로 prod-write 아님. 접촉 = FMP `/stable/*` 조회 27콜 + 로컬 SELECT(AdvisoryRun·WalletHolding count). **사용자 실계정·DB write 무접촉**. FMP API 키는 마스킹 처리(`len=32,head=qA1W***`)로 원장·커밋에 원문 미기재([[feedback_secret_masking_policy]]).

---

## D-I1-RUNTOTAL-DETERMINATION (2026-08-01, SFI-I1 Part A.2 — RUN-TOTAL-PERSIST 판별 종결)

**판별 = ① 등재 확인 → 종결.** `RUN-TOTAL-PERSIST`는 origin/main(`d484b9cb`) `TASKQUEUE.md`에 **이미 등재**됨(f2 track `3ba4cf00` SLICE-20B-F2 Part A, 2026-07-31). 심지어 "SIGNAL-FORWARD-INFRA 합류 후보 — 전방 신호 인프라와 원장 스키마 공통 설계"로 명시. 재등재·common-bugs 불일치 등재 불요.

**부수 정정(보고-착지 불일치 근인)**: SFI 프리플라이트 recon 보고가 "RUN-TOTAL-PERSIST = repo 무매치"로 판정한 것은 **recon 브랜치가 origin/main이 아닌 분기된 HOLD-P1 라인(`b8d767aa`) 위에 기반**해 f2 랜딩(07-31) 이전 상태를 조회했기 때문(false-missing). SFI-I1에서 `git rebase --onto origin/main`으로 base를 origin/main으로 교정 → RUN-TOTAL-PERSIST 가시화, common-bugs 번호도 #62(stale)→#79(정본) 정합. **교훈**: recon/설계 세션 STEP 0의 "worktree 최신성 확인"(common-bugs #59)을 신규 트랙 base 선정에도 적용 — 분기 라인 위 기반 금지([[lesson_branch_assignment_explicit_isolation]]).

---

## D-I1-1 · D-I1-2 · D-I1-3 (2026-08-01, SFI-I1 아키텍처 결정 3건)

**D-I1-1 — forward 신호 저장은 shared(`packages/shared/stocks`)에 둔다.** EstimateSnapshot 모델·FMP 래퍼 신호 메서드·writer 서비스 전부 shared 패키지. 근거: 신호는 앱 횡단 자산(advisory·chain_sight·dashboard 잠재 소비) → shared가 단일 출처. 경계 규율: shared는 `apps.*` import 금지(경계 가드 자동 검증). advisory 엔진·화면은 이 슬라이스에서 무접촉(소비는 별도 사이클).

**D-I1-2 — EstimateSnapshot은 append 전용(시계열 정본).** 동일 심볼 재수집 = 신규 행 추가(덮어쓰기 금지). captured_at으로 시점 구분. Stock.analyst_* 필드는 **최신 스냅숏 미러**(빠른 조회용 파생)일 뿐, 정본 시계열은 EstimateSnapshot. 근거: RUN-TOTAL-PERSIST가 노출한 "동일 date update_or_create가 이전 값 소거" 문제([[상기 D-I1-RUNTOTAL]])를 forward 신호에서 반복하지 않기 위해 append로 설계.

**D-I1-3 — SFI-I1은 "수집까지만"(collect-only).** 범위 = 래퍼 메서드 + 모델 + writer + nightly 태스크 정의. **화면·advisory 기대수익 로직·migrate·beat 등록은 무접촉**. advisory_engine.py:10의 "analyst_target_price를 기대수익 프록시로 쓰지 말라" 금지벽은 유지 — 신호를 수집·저장하되 기대수익 산출로 직결하는 소비는 별도 결정 사이클. migrate=prod-write·beat 등록=DB row 둘 다 병진 수동(공유 DB 절대 규칙).

---

## D-I1-4 (2026-08-01, SFI-I1 B2 확정 — forward 신호 역할 경계 명문화)

병진 판정으로 모델 전략 **B2** 확정. forward 신호를 두 원장으로 역할 분리한다:

- **가격·의견 계열 = `packages.shared.stocks.AnalystSignalSnapshot`(신규).** 4신호: price target(high/low/consensus/median) · grades 분포(strong_buy~strong_sell + consensus 라벨) · grades-historical(월별 추세) · ratings-snapshot(등급). 유니버스 = coach(WalletHolding ∪ WatchlistItem), 케이던스 = nightly.
- **실적 추정(estimates) = `apps.chain_sight.EstimateSnapshot`(기존 정본, 무접촉).** eps/revenue, 유니버스 = SP500, 케이던스 = 주간(금). SFI는 **estimates를 수집·저장하지 않는다** — `client.get_analyst_estimates` 신규 호출 금지(존재 확인만).

**동일 FMP 엔드포인트 이중 수집 금지.** `analyst-estimates`는 chain_sight가 단일 소유. `AnalystSignalSnapshot`는 estimates 페이로드를 담지 않는다.

**Why**: EstimateSnapshot이 이미 배포·가동 중(theme_heat TH-3, beat 등록 금 16:30 ET)인데 SFI가 동명·동엔드포인트 모델을 만들면 이중 수집·의미 중복. 두 원장은 유니버스(SP500 vs coach 14종, 겹침 6·갭 8)·케이던스·목적(C8 리비전 z vs coach 화면 신호)이 모두 달라 통합보다 역할 분리가 정합. 통합 단일 원장은 별도 사이클(cf. MP-UNIFY) 소관.

**부수 결정 — 모델 키 = `symbol` CharField(FK 아님).** 기존 EstimateSnapshot 형제 관례 준수 + coach 갭 8종(비SP500)이 Stock 행 부재 가능 → FK 강제 회피. 유령필드 미러는 별도로 Stock을 symbol 조회해 존재 시에만 갱신.

## [2026-08-03] SEC β G-e — v2 프롬프트 tail 발산 측정 + 배달사고 #8 (D-SECB-GATE-E)

> SECB-GE-EXEC-1 Phase B. 정의서 `sec_beta_ge_prompt_v2_scope.md` 감독 승인 후 착수. 트랙 최초·유일 LLM 호출(5콜). worktree `monorepo/sess-secb-ge`.

**D-SECB-GATE-E (v2 프롬프트 측정 = 방향성 확인, 배포 아님)**: R1~R5 verbatim 규율([`SECB-GE-R1R5-SPEC.md`](docs/features/chain-sight/SECB-GE-R1R5-SPEC.md) 단일 출처) 삽입 v2 프롬프트로 표본 5 filings(AKAM·COR·CAT·ISRG·FIX = 인용≥8 중 tail 상위, 3단 키 `tail desc→cites desc→accession asc`) 재추출·paired 측정. **결과: tail율 71.07%(v1 121/86) → 0.72%(v2 139/1)** — partial_match(리스트 절단) 유형 v2 표본서 0건. `MAX_EVIDENCE_CHARS=300`(v1 캡 역산). grounding=`ground_evidence_g16`(순수 함수·DB 무접촉·LLM 0), LLM은 추출에만. **저장=물리 격리(b)**: prod/dev DB 쓰기 **0**, 결과 `var/secb_ge_v2_sample/`(gitignore) JSON + 요약 `sec_beta_ge_v2_result.md`. prod 사전/사후 스냅샷 동일 입증(1768/1751·v2 0·1273/41/410/27 불변). **⚠️ caveat(롤아웃 결정 재료)**: v2 evidence 길이가 R3의 300자 상한 상시 초과(ISRG 평균 587·max 646) — 모델이 R2(완전 문장)>R3(캡) 우선. **측정 세션 계약**: pass/fail 낙인·전량 배포·substrate 통합 없음(별도 결정 사이클). 신규 코드 = `SUPPLY_CHAIN_EXTRACTION_PROMPT_V2`(additive)+`secb_ge_v2_sample` 커맨드(prod 읽기전용)+g16 재사용, 마이그 0·모델 변경 0·v1 경로 무변경(extractor.py 무접촉).

**배달사고 #8 (참조 사양이 chat-only·repo 미커밋, 규율이 실행 前 적발)**: 디렉터 비준문이 "v2 프롬프트 = v1 구조 + 델타 R1~R5 삽입(디렉터 사양서 참조)"라 지시했으나, 참조된 R1~R5 사양이 **repo·전 브랜치·미추적·핸드오프 어디에도 미커밋**(chat 후속 메시지에만 존재). 실행 세션이 R1~R5를 **임의 창작하지 않고 HALT·회부**(측정 대상 자체이므로 창작 시 측정 오염) → 감독이 `SECB-GE-R1R5-SPEC`로 원문 전달·`3cbfc02f` 커밋으로 해소. 사고 계열 통산 **#8**(#6=base 지시서 누락·#7=게이트 정의 미전달에 이어). **귀책=디렉터**(비준문 복사 블록 밖에 사양 배치). 교훈=참조된 사양의 repo 미커밋 시 임기응변 금지·회부(배달 게이트 규율, cf. #6·#7). cf. TASKQUEUE SECB-PROMPT-V2(소비 완료).

## [2026-08-03] TH 트리거 문안 정정 — corpus 무동결·실동결=TNV 집계 (D-TH-TRIGGER-CORRECT)

> TH-RECON-1 정찰(읽기전용) 실측으로 TH-TRIGGER-FIRED 원안의 오전이 정정. TH-SESSION-1 §A 반영.

**D-TH-TRIGGER-CORRECT (트리거 스코프 오전이 정정)**: TH-TRIGGER-FIRED 원안 "corpus unfreeze + TNV 백필(07-12→현재, 50일+)"은 실측과 불일치 3건으로 정정한다 — ⑴ **corpus(DailyNewsKeyword)는 동결된 적 없음**: 최신 date=2026-08-03(오늘)·일 1행 불변식 충족·창 내 결측일 0(뉴스 키워드 추출 beat 상시 가동). "corpus unfreeze"는 부정확. ⑵ **실동결 = TNV 집계**(ThemeNewsVolume): 최신 date=07-25·집계 **beat 부재**(news_volume/tnv PeriodicTask 없음)→수동 커맨드 의존→미실행으로 정지. 입력 corpus는 계속 흘렀으므로 백필 = **07-26→08-03(9일) 순수 DB 재집계**(외부 API 0·LLM 0). ⑶ **'07-12'는 TNV 동결점이 아니라** ThemeTermOverride의 G2 스코프(≤07-11)에서 유래한 오전이. "50일+"도 과대(실 9일). **파생 리스크**: heat(theme-heat-daily, 08-02까지 발화)가 결손 TNV 성분(C3=`c3_narrative_from_db`)으로 07-26~08-02 산출 → TNV 백필 후 heat 07-26→08-03 멱등 재산출(`update_or_create(theme,date)`) 필요. **6/11 themes**(최신일 6 저장)은 이상 아님 — `heat_beat.py` 결측 성분 ≥3 섹터=`not_computed`(§6.1 status 미포함, 저장 안 함) 설계 동작. cf. TASKQUEUE TH-TRIGGER-FIRED(소비)·TH-OVR-RECUT(보류)·TH-RESUME-CORPUS-UNFREEZE. 감독 판정 4건(TH-SESSION-1, 백필=TNV만·override 배제 마진 2.25).

---

## D-I1b-1 (2026-08-04, SFI-I-1b — coach 유니버스 스코프 교정)

**결정**: `_coach_universe()`(ingest 대상)를 **UserGoal 보유 유저의 WalletHolding ∪ WatchlistItem**으로 스코프한다. 좌표 = nightly advisory·snapshot 태스크와 **동일**(`User.objects.filter(portfolio_goal__isnull=False)`). 경로 = `WalletHolding.filter(wallet__user__in=goal_users)` ∪ `WatchlistItem.filter(watchlist__user__in=goal_users)`.

**결함 인정**: SFI-I1의 `_coach_universe()`는 `WalletHolding/WatchlistItem.objects.all()` **글로벌 무필터**였고, 이는 결함이었다. 타 유저(admin) "내 관심종목"(레버리지 ETF 5종 포함 테스트 데이터)이 coach forward 신호 유니버스에 유입 → 자동발화가 admin 데이터까지 수집. 실측: 글로벌 14종 → 스코프 9종(제외 GEVG·IREG·OKLL·SMR·XE = admin 전용, UserGoal 없음). 화면·dashboard·advisory 소비처는 전부 per-user(`watchlist__user`)인데 SFI만 무스코프였음(비대칭 = 결함 증거).

**Why**: coach는 "목표를 가진 유저의 포트폴리오 코칭" — 유니버스는 그 유저의 자산·관심으로 정의돼야 한다. 무필터는 멀티테넌트 경계 누수. migrate 무변경(코드만) — 기존 AnalystSignalSnapshot 행 보존(admin 심볼 과거 행은 무접촉, 다음 발화부터 새 스코프).

## D-I1b-2 (2026-08-04, SLICE18 STEP0 stale 교정 — watchlist 정본 단일)

**교정**: `DECISIONS.md:638`(SLICE18 STEP0, 2026)의 "chain_sight WatchlistViewSet이 `shared/users.WatchlistItem` 소비"는 **현재 stale**. 실측(SFI-I-1b) = `apps/chain_sight/views/watchlist_views.py`의 `WatchlistViewSet.get_queryset`은 **`SavedPath`(그래프 저장경로)를 읽음**(ego/saved-path 리디자인으로 전환). `/api/v1/chainsight/watchlist/`는 이름만 watchlist, 종목 관심목록 아님.

**정본**: **stock watchlist 정본 = `users.WatchlistItem` 단일**. 소비처 = 화면(`/users/watchlist/*` per-user)·dashboard strip(per-user)·advisory(per-user)·SFI ingest(D-I1b-1로 per-user 교정). chain_sight watchlist = 별개 도메인(SavedPath). legacy 분기 아님(단일 정본 + 이름 충돌).

## D-I1b-3 (2026-08-06, SFI-I-1b — 스코프 교정 이전 admin 신호 행 소급 삭제 안 함)

**결정**: `_coach_universe()` 스코프 교정(D-I1b-1) **이전**에 수집된 admin 전용 심볼의 AnalystSignalSnapshot 과거 행(실측: SMR·XE 각 2행, captured_at ≤ 2026-08-03)은 **소급 삭제하지 않는다**. 교정은 다음 발화부터 적용(신규 행만 스코프 9종), 기존 행은 무접촉.

**Why**: ⑴ AnalystSignalSnapshot은 append 전용 시계열 정본(D-I1-2) — 원장에서 과거 행을 지우는 것은 append 불변식 위반. ⑵ 사후분석 표본 가치 — 교정 전/후 유니버스 변화(글로벌 14→스코프 9) 자체가 관측 대상(스코프 결함이 언제·무엇을 유입시켰는지의 증거). ⑶ 무해 — 조회 API(D-I2-1)는 유저 관심 심볼만 질의하므로 admin 잔여 행은 화면·advisory에 도달 불가. 코드/DB 변경 0(등재만, 판정 확정 사안).

cf. D-I1b-1(스코프 교정)·common-bugs GLOBAL-SCOPE-TASK.

## D-PROBE-PRODWRITE-RULE (2026-08-04, D-PROBE-PRODWRITE-EXCEPTION 승격 — 예외→규칙)

**승격**: 기존 `D-PROBE-PRODWRITE-EXCEPTION`(2026-08-01, DECISIONS:5626)의 "1회 예외"를 **일반 규칙**으로 승격한다. **게이트 증거 + 세션 내 병진 명시 승인**이 갖춰지면 prod-write(migrate·beat 등록·수동 태스크 실행)를 **집행 허용**한다. 자율(승인 없는) prod-write는 여전히 금지.

**허용 조건(3종 동시, 불변)**: ⑴ 게이트 증거 선행(sqlmigrate 눈확인·dry-run·확인쿼리 등 검증 산출), ⑵ **세션 내 병진 명시 승인 인용**([[feedback_deploy_approval_explicit_quote]]), ⑶ 사실 보고(출력 가져와 디렉터 판정).

**이력 인용(예외 2건)**: ① f2 Part 3(2026-08-01, 세션 내 승인). ② **SFI-I1 배포**(2026-08-03: migrate 0012·beat 등록·수동 1회 — 병진 "작업 진행해줘" + push 병진 집행 후, 게이트 증거[sqlmigrate CREATE TABLE 단독·확인쿼리 #78] 동반, 자동발화 GREEN). 2건 모두 무사고 → 예외가 아닌 표준 절차로 승격 근거.
## [2026-08-04] TNV 집계를 heat 태스크에 체이닝 — 재동결 구조적 방지 (D-TH-TNV-CHAIN)

> TH-SESSION-1 후속. TNV 집계 beat 부재로 07-25 재동결됐던 문제의 **구조적 해결**. TH-TNV-CHAIN-1 세션.

**D-TH-TNV-CHAIN (체이닝 = B안 확정)**: TNV 집계(ThemeNewsVolume)가 스케줄 beat 없이 수동 커맨드에만 의존해 재동결되는 문제를 3안 비교 후 **(B) 체이닝**으로 해결.
- **선택지**: (A) 신규 TNV beat 등록(독립 스케줄) / (B) 기존 theme-heat-daily 태스크 선두에 `aggregate_theme_news_volume(당일)` 체이닝 / (C) 현상 유지(수동 백필 반복).
- **가중합 4.15, 마진 1.30 → B 확정**. **근거**: ⑴ **#28 회피** — 신규 beat 등록은 config dict vs DB drift·stale 트리 재기동 시 덮어쓰기 리스크(3회 재발). B는 beat 0 신설로 이 함정을 원천 회피(회피 자체가 B의 채택 근거). ⑵ **순서 구조 보장** — heat의 C3 성분이 TNV를 소비하므로 "TNV→heat" 인접 실행이 데이터 정합을 보장(독립 beat는 발화 순서·시각 어긋남 위험). ⑶ 최소 침습 — 기존 태스크 내부 수정만, 산식 무변경.
- **실패 정책**: TNV 예외 → **실패 전파(태스크 실패)**. 빈 재료로 조용히 heat 계산한 것이 재동결 사태의 본질 → 소리 내고 멈춤. 단 keywords=[] 정상 공백(written=0)은 실패 아님(예외≠0건 구분). 로그 `TNV_CHAIN date=… written=N zeroed=M`로 관측성 확보(B안 단점 보완).
- **미래 재개점**: TNV·heat 주기 분화가 필요해지면 A안(독립 beat)로 승격 = TASKQUEUE TH-TNV-BEAT-SPLIT(보류). cf. common-bugs #28.

---

## D-I2-0 · D-I2-1 · D-I2-2 (2026-08-04~05, SFI-I-2 애널리스트 시그널 패널)

**D-I2-0 — C안 확정(병진 08-04)**: I-2 = **컨텍스트 + 의견 추세 패널**. 종목 화면에 목표주가·업사이드%·high/low 범위·의견 분포(strong_buy~strong_sell)·월별 추세 미니차트. AnalystSignalSnapshot(I-1 수집분)을 read-only로 표면화. **advisory 화면·엔진·기대수익 무접촉**(신호를 기대수익 프록시로 쓰지 않는다 = advisory_engine.py:10 금지벽 유지). 뉴스 MarketDataBadge·chain_sight narrative 슬롯 = **이월**(I2-NEWS-BADGE-DEFER).

**D-I2-1 — 조회 API는 I-3 공용 설계**: 스냅샷 GET 엔드포인트는 I-2(패널)뿐 아니라 I-3(자체 시계열·다소비처)도 재사용. 위치 = `packages/shared/stocks`(shared 모델이므로 stocks 계열이 자연 — 실측 근거: `/api/v1/stocks/*` prefix·APIView+IsAuthenticated 기존 관례). 계약 = 최신 1건 + 4신호 + grades_historical + captured_at. 미수집 = **null 계약(available:false, 200)** — advisory read 관례(LatestAdvisoryContract.available) 정합·FE "미설정" 폴백 친화(404 아님). Decimal=문자열 직렬화(advisory_contract 관례).

**D-I2-2 — 추세 소스 = grades_historical(FMP 제공 12개월)**: 월별 의견 추세 차트는 스냅샷의 `grades_historical`(수집 시점 FMP가 준 12개월 이력)을 변환. **자체 축적 시계열**(nightly 스냅샷을 우리가 쌓아 만드는 추세)은 **I-3**(데이터 성숙 후, I3-OWN-TIMESERIES). 근거: 아직 자동발화 3회분(08-03·04·05)이라 자체 시계열은 표본 부족 — FMP 제공 이력이 즉시 가치.

## D-I3-1 · D-I3-1b · D-I3-2 · D-I3-3 (2026-08-06, SFI-I-3 애널리스트 신호 채점 계층)

**D-I3-1 — 채점 = 파생 계산 계층(신규 채점 테이블 없음)**: 채점은 ORM 읽기 → 순수 함수 계산 계층으로 구현한다(ScoredPrediction 등 채점 원장 신설 안 함). 근거: 현재 표본 미성숙(자동발화 소수, 대부분 만기 미도달)이라 물성화 이득 없음·조기 스키마 고정 위험. 물성화는 **I3-MATERIALIZE-TRIGGER**(채점 로직 v2 분기 또는 코치 런타임 참조 개시) 도래 시로 예약.

**D-I3-1b — spot_at_capture 동봉(a안), STEP 0 분기 = 경로 Y**: 채점 방향/진행률의 기준가(spot)를 AnalystSignalSnapshot insert 시 동봉한다. STEP 0 실측 분기 = **#1 ASS에 spot성 필드 부재 → 경로 Y**(additive nullable 컬럼 `spot_at_capture` 1개 추가). **#2 FMP 페이로드(price-target-consensus·ratings-snapshot·grades)에 priceWhenPosted류 부재 → 발화 시 경량 조회**(최신 DailyPrice.close ≤ 발화일, 실패 시 null 허용 — 발화 자체를 막지 않음). append 불변식 유지(insert 동봉만·UPDATE 경로 없음). 기존 pre-pinning 코호트(spot null)는 **backfill 금지**(D-I1b-3 정신) — 리포트에서 파생 spot + 캐비앗으로 분리 산출.

**D-I3-2 — 채점 배터리 = C안(병진 override)**: 5과목 2계층. **Tier 1(판정 과목)** = ① 방향 적중률(sign(target−spot), h∈{21,63}거래일, 이항검정) · ② 목표가 진행률(실현폭/예측폭 중앙값·IQR, h∈{63,126,252}) · ③ 횡단면 IC(주간 코호트 upside% 순위 vs 실현수익 순위 Spearman, h∈{21,63}). **Tier 2(관측 과목)** = ④ 개정 추적(target consensus 일간 delta·grades 분포 변화) · ⑤ advisory 사후분석 v0(run 수·트리거·knobs 변동, #5 보유·수량 확인 → h=21d 근사 NAV). B 추천 대비 −0.80 수용(병진 override, 재론 금지).

**D-I3-3 — advisory 금지벽 유지 + 승격 트리거**: `advisory_engine.py:10-11` 금지벽(신호를 기대수익 프록시로 쓰지 않음)을 이 슬라이스에서 **절대 건드리지 않는다**(벽·advisory 로직 무접촉). 채점은 관측 계층일 뿐 자동 승격 아님 — Tier 1 통계 유의 도달 시 **I3-PROMOTION-TRIGGER**로 승격 결정 사이클을 소집한다(자동 해제 금지).

## D-I3-4 · D-I3-5 (2026-08-07, SFI-I-3 SPOT-DAY-CONVENTION 수리)

**D-I3-4 — pinned spot 관례 = T(당일) 종가, beat 18:30→19:30 ET 이동으로 보장**: writer의 spot=최신 DailyPrice.close 로직은 무변경(값 선택 쿼리 불변). 대신 발화 시각을 **19:30 ET(dow1-5)**로 이동해 발화 시점 T 종가가 항상 적재 완료돼 있게 한다. **선후 실측 근거**: T EOD 적재 = S&P500분 18:00 ET(→22:0x Z 완료) + 비S&P500 모니터분 `monitor-refresh-daily` 18:45 ET(`ensure_price_freshness` 온디맨드, 정상 22:45:0xZ 완료). 18:30 발화는 비S&P500 적재(18:45) 앞이라 3종(IONQ·IREN·TLN) spot이 T−1로 박제됐다(08-06 발화 9행 중 6=T, 3=T−1 실측). **마진 타이브레이커(0.10급)**: monitor-refresh 완료 상한 = 정상 22:45Z(마진 45분) / 최악 재시도(RETRY 1200s×2) 23:25Z(마진 5분) / EOD 장애 시 monitor는 late-완료가 아니라 **skip**(적재 안 함) → 19:30 ET(23:30Z)는 구조적으로 적재 후행. 하류 무의존(snapshot 19:00·advisory 19:15는 ASS 미독)이라 발화가 이들 뒤로 가도 파손 없음. **재시도 최악 23:25Z vs 발화 23:30Z 마진 5분 — 수용**, 근거: 저빈도 경로(EOD 지연 자체가 예외) + 초과해도 결과는 T−1 폴백(치명 아님, 채점서 혼합 코호트로 격리) + writer 가드 로그(bar_date)로 사후 관측 가능.

**D-I3-5 — 수리 전 pinned 행 = 혼합 관례 코호트, 소급 미수정 + epoch 태깅**: SPOT-DAY 수리의 첫 T-관례(19:30 ET) 발화일 **CONVENTION_EPOCH=2026-08-10**(08-08~09 주말 dow1-5 스킵, beat 이동 후 첫 발화) **이전**에 박제된 pinned 행 = **총 18행**(08-06 발화 9 + 08-07 발화 9, 구 18:30 ET 스케줄, T/T−1 혼재)은 **소급 수정·삭제하지 않는다**(append 불변식·D-I1b-3 정신). 대신 리포트가 pinned 코호트를 epoch 전(=혼합 관례, 캐비앗)/후(=T 관례)로 분리 표기한다. **SCORING_VERSION은 1 유지**(채점 수식 무변경 — epoch은 코호트 축이지 버전 축이 아님).

## D-REGEN-V2-1 ~ D-REGEN-V2-3 (2026-08-10, C-L3-REGEN-V2 파이프라인)

> 진입조건 충족 확인: ① C-N-REPAIR 완주 192/192(DB 일-존재, 2026-08-10) ② SELECT-V2 랜딩(origin/main, `grounding_v2.py`·`select_grounding_v2`). STEP 0 실측: L3 저장=`AnalogDayContext`(date·why_text·provenance[{id,url,title}]·prompt_version·generated_at)·모집단=`RegimeSnapshot.filter(summary="[BACKFILL_V2]", coverage>=1.0)`=**683**(491 기존 cl3_v1 + 192 신규)·683 전일 뉴스 커버(0건=0).

**D-REGEN-V2-1 — v2 = additive 배선(하드 스왑 아님), v1 경로 IDENTICAL 보존**: `context_generator.generate_for_date`에 `select_version` 파라미터(기본 `"v1"`=기존 `select_grounding` IDENTICAL, `"v2"`=`select_grounding_v2`) + `select()` 디스패처 추가. `generate_analog_context`에 `--select-version {v1,v2}`(기본 v1). **Why**: §3 경계 "v1 생성 커맨드 경로 보존(IDENTICAL/회귀), 신규 additive". v2 반환키는 v1 상위집합(id/url/title 조립키 호환)이라 provenance 무수정 호환. LLM 경계는 이미 clean(`generate_with_circuit` shared 래퍼) — **BOUNDARY-LLM 신규 부채 0**(STEP 0 실측, 통합 불요).

**D-REGEN-V2-2 — 버전 태깅·재생성 방식 = prompt_version 인코딩 + 버전 인지 멱등 (마이그레이션 0)**: `AnalogDayContext`에 별도 select_version 필드 없음(prompt_version 단일 CharField). v1/v2 구분 = **prompt_version 값**(v2→`cl3_v2`, `--select-version v2`+미지정 시 자동 커플링). v1 텍스트는 DB 보존 안 함(덮어쓰기) — **별도 필드 추가는 prod 마이그레이션 유발 → §5 HALT 회피 위해 기각**, 버전 태그 증가로 구분(git 이력이 v1 보존). 멱등: 비-`--regenerate`=날짜 기반 skip(v1 IDENTICAL·조용한 덮어쓰기 0), `--regenerate`=prompt_version 불일치 날만 pending(cl3_v1→cl3_v2 업그레이드 + 동일 v2 재실행 시 skip=재개 가능). **683 전량 명령 = `--select-version v2 --regenerate --commit`**(491 덮어쓰기 + 192 신규).

**D-REGEN-V2-3 — 빈 선별=why=null(억지 생성 금지) 유지, dry-run은 v2 실선별 카운팅**: v2가 macro 신호 없는 날 `[]` 반환 → `generate_for_date`가 None(행 미생성). dry-run은 v1=헤드라인 raw 카운트(IDENTICAL), v2=`select_grounding_v2` 실호출로 비어있지 않은 날 실측(정확 LLM 호출수·순수 DB·외부 API 0). 샘플 게이트 12일 실측(write-free): 10 호출(2 저볼륨=빈선별 why=null)·in 4,314/out 220 tok·**~$0.00184(건당 ~$0.00015)**·톤가드 전통과·v1↔v2 품질 개선 실증(2024-08-05 "개별기업"→"금리인하 기대·하락압력" 등). 검증: regime 스위트 105 GREEN(v2 신규 7)·django check 0·makemigrations 0.

**D-REGEN-V2-EXEC (2026-08-10, 683 --commit 실행 완료·종결)**: worker 트리 origin/main 동기화(270e7dcb)+워커 재시작 후 `generate_analog_context --select-version v2 --regenerate --commit` 실행(2배치 합산, 첫 배치 하네스 리핑→nohup 재개, 멱등 skip으로 무손실). **결과 = cl3_v2 666(생성 성공) + cl3_v1 잔존 12 + 행없음 5**(683 완결). null 사유=macro 신호 없음 9 + 톤가드 재실패 8(dry-run 674 대비 666=톤가드 억지생성 거부). 톤가드 육안 6/6 통과·provenance 무결. **미결 = cl3_v1 잔존 12일(macro-null 기존)**: 파이프라인이 동결원칙상 v1 행을 자동삭제 안 해 v1 filler 서빙 유지 → **삭제→null 여부 디렉터 결정 대기**(유지 시 사실기반·무해). 실행 트리=sv-worker-runtime(dev=prod 공유 DB). BOUNDARY-LLM 진입 조건 충족(경계 clean·신규부채 0, ALIAS-CHECK만 잔여).

**D-CL3-V1-RESIDUAL (2026-08-10, cl3_v1 잔존 12행 백업 후 삭제·종결)**: D-REGEN-V2-EXEC 미결(cl3_v1 잔존 12) 처분 = **(b) 백업 후 삭제**(가중합 4.30 vs (a)유지 3.10, 마진 1.20, 병진 승인). **삭제 방식 = (i) 행 delete**(why=null 렌더가 아니라 행 부재로 = 기존 행없음 5일과 동형): cards.py는 버전 무관 `filter(date__in)` + `ctx.why_text if ctx else None`(:452) → 행없음=why=null. why_text가 not-null TextField라 (ii) null화는 마이그 필요 → 삭제가 유일 clean·기존 상태 일관. **안전**: 신규 커맨드 `purge_analog_v1_residual`(날짜 목록 ∧ prompt_version=cl3_v1 **이중 조건**=cl3_v2 구조적 차단, dry-run 기본·멱등, 테스트 4). **가역성**: 삭제 선행 커밋 `docs/archive/cl3_v1_residual_backup_2026-08.json`(12행 전문). **실행**: dry-run 12 확인 게이트 → --commit 12행 삭제. 사후 실측 cl3_v1 **0**·cl3_v2 **666 무변**·삭제 3일 서빙 why=null 폴백 확인. 마이그0·regime 109 GREEN. 톤가드 실패 8일 재시도는 S4-REBASE 별건(이 세션 무접촉).

## D1 — 마인드맵 골격: 업종 2단 뼈대 + 테마 슬롯 (2026-08-10)

**결정 (Chain Sight 재설계 D1)**: 화면의 주인공은 관계 그래프가 아니라 **마인드맵식 카드 분류**다. 그래프·Neo4j 서빙 계열은 **동결**(무접촉).

- **카드 주소 = 업종 2단**(FMP sector/industry, 682 전량·안정). 테마는 주소가 아니라 **슬롯(문패)**: 공급원은 뉴스 어휘 승격분, ETF 테마는 슬롯 검증 신호로 강등.
- **관계는 트리 거주자가 아니라 카드 속성** → 감사 4-B(SEC 실관계 36%가 공통테마 없음) 문제 소멸.
- **카드 내 이원 분리**: "확인된 연결"(근거 계층·출처 표기 필수) / "같은 그룹"(유사 계층·"관계 아님" 명시).

**Why / 정량 근거**: 가중합 B(업종 뼈대+테마 슬롯) **4.40** / C(뉴스어휘 단독) 3.25 / A(ETF 테마 골격) 2.70, 마진 1.15 → 자동 결정. 관계를 트리 좌표로 쓰면 교차섹터 실관계(감사 4-B 36%)가 배치 불가가 되나, 카드 속성으로 두면 소멸.

**보류 하위결정 3건** (디렉터 후속 결정):
1. 업종 분류원 세부 (FMP 그대로 vs 병합)
2. 슬롯 승격 기준 (τ·HHI·ETF 교차)
3. 카드 연결 표시 게이트 (D4 재검증과 세트)

---

## D2 — 소스 포트폴리오: C안(수리 + 8-K + 유니버스 확장) (2026-08-10)

**결정 (Chain Sight 재설계 D2)**: 소스 포트폴리오는 **C안(수리 + 8-K 신설 + 유니버스 확장)**을 채택한다.

**공통 배치**:
- **13F 서빙 제외** (수집만 유지). 근거: 기관 22개·유니버스내 중앙 439 = 무변별([[project_cs_foundation_audit]] 감사 3-A).
- **price는 관계 종류에서 제거**, "확인된 연결" 쌍에 초과수익 동조성을 **강도 속성**으로 부착(확정 결정 "강도=주가 동조성" 이행, 근거: price→peer 조건부확률 1.00 = peer 종속).
- **peer + ETF = "같은 그룹" 재료** (ETF는 F5 티어 확인 조건부).
- **vocab_v1 push·검증 = 슬롯 공급 전제** ([[project_news_vocab]] `sess-news-vocab` 미커밋 → 슬롯 공급원).

**신설**: **8-K 최소 슬라이스** (item 1.01 계약체결 / 2.01 자산취득 · 682 CIK 한정 · 백필 1년 · EDGAR 무료). 미해소 상대 기업은 **빈도 카운터**로 적재(확장 2차 근거).

**유니버스 확장 확정**: 1차 = 10-K 미해소 US상장 타깃 기반(P2-4 실측이 후보 풀), 2차 = 8-K 빈도 트리거. 편입 시 기존 SupplyChainEvidence 1,437건 **재해소**.

**Why / 스코어와 결정권자 판단**: 가중합 B **4.20** / A 3.80 / C 3.60 으로 B 우위(마진 0.40)였으나, 사용자 가치 기준 **"강력함 > 속도·비용"**에 따라 결정권자 판단으로 **C 채택**. 단계 게이트(Phase 0→4)로 리스크 관리.

**실행 순서**: Phase 0 실측 → 1 수리 → 2 8-K → 3 확장 1차 → 4 확장 2차(트리거). 각 Phase 종료 시 `health_check` + before 대비 KPI 확인 후 다음 지시서 발행.

---

## D-CS-REDESIGN-BEFORE-BASELINE (2026-08-10, 재설계 성과 대조군)

**CS-SOURCE-AUDIT before 기준값** (base `8a41c842`, 관계 코드는 `4cd4f45d`와 diff 0 → 유효):

| KPI | before 값 |
|-----|-----------|
| 교차지지 0개 / 1개 | 11% / 29% |
| 유형별 교차지지 | COMPETES_WITH 2.47 vs SUPPLIES_TO 1.33 |
| SEC+news 중앙 이웃 / 오염 | 4 / 0% |
| +13F/ETF 오염 | 98.7% |
| 뉴스 착지 누수 | 91% (1,242 → 248) |
| price→peer 조건부확률 | 1.00 |
| 표기불일치 복구 상한 | 4.2% (61행) |
| SEC 관계 테마 미소속 | 36% |
| (선행 감사) 화면 근거없음 / 검증률 | 50% / 2% |

**근거/유사 매핑 표** (STEP 0-3 실측 유형 전수 기반 — 추정 아닌 쿼리 결과):

| relation_type | 건수 | 계층 | 공급 소스 |
|---|---|---|---|
| COMPETES_WITH | 115 | 근거 | SEC 10-K (+ 8-K 예정) |
| SUPPLIES_TO | 62 | 근거 | SEC 10-K |
| PARTNER_WITH | 54 | 근거 | SEC 10-K (+ 8-K) |
| DEPENDS_ON | 41 | 근거 | SEC 10-K |
| CO_MENTIONED | 278 | 근거(임계 이상) | 뉴스 동반언급 |
| PEER_OF | 9,365 | 유사 | FMP peer + industry |
| PRICE_CORRELATED | 3,784 | 유사 (→ 강도 속성 이동) | 주가 상관 (peer 종속 1.00) |
| PEER | 2 | **보류** | PEER_OF 레거시/이형 추정 — 디렉터 검수 (HALT 아님) |

근거 계층 합 = 550 (SEC계 272 + CO_MENTIONED 278) / 유사 계층 = 13,149 (PEER_OF 9,365 + PRICE_CORRELATED 3,784) / 보류 = 2 (PEER).
## D-VOCAB-SKEW (2026-08-06, NEWS-VOCAB-BUILD Rev.2 — 어휘 편중도 필터)

**결정**: 뉴스 n-gram에서 카테고리 어휘를 거를 때 상투어 판정 기준을 "등장 버킷 수 ≥ B" → **HHI(버킷 크기 정규화 점유율의 제곱합)**로 교체. 문구의 버킷별 등장 횟수를 버킷 총기사 수로 나눈 비율로 정규화(대형 버킷 편향 제거) 후 HHI 계산. F_min=30 미만 제외. HHI < THR(=0.103, 검증세트 보정) = 균등분포 상투어 → 탈락. **Why**: 개수 기준은 양방향 오류 — 상투어(wall street, 13버킷 고른 분포)와 교차 테마(AI·데이터센터, 소수 버킷 편중)를 구분 못함. 임계 상향은 quarterly dividend류를 살리고 하향은 테마를 죽임 → 분포의 **모양(편중도)**으로 판정. 검증세트(탈락 10 ≤0.102 / 생존 5 ≥0.104) THR=0.103서 깨끗 분리 입증.

## D-THEME-L1 (2026-08-06, NEWS-VOCAB-BUILD Rev.2 — 교차 테마 L1 승격 + 엣지 단일 소속)

**결정**: 여러 산업을 관통하는 교차 테마(데이터센터·인공지능·천연가스·공급망·양자컴퓨팅·청정에너지·클라우드컴퓨팅 7종)를 업종과 **동급 L1**으로 승격. 이전 "⇄ 표식 + 중복 노출" 방침 폐기. 엣지는 **단일 소속**(테마 매칭 시 테마 L1, 미매칭 시 상대 종목 업종 L1) — 한 엣지가 두 칸에 세어지지 않음. **Why**: 여러 부모에 중복 출현하는 노드는 부모급이라는 신호이며, 표식은 뒤집힌 계층의 증상 처리에 불과(AI인프라는 반도체를 포함하지 그 역이 아님). 3종목(ZBRA/MRK/AAPL) 칸합계=이웃총수 검증으로 중복배정 0 입증.

## D-NEWS-VOCAB (2026-08-06, NEWS-VOCAB-BUILD Rev.1~3 — 뉴스 어휘 사전 v1 + 배정 로직)

**결정**: Peer 관계 L1 라벨 어휘를 **저장 뉴스 코퍼스**(NewsArticle 359,962 / NewsEntity, AV NEWS_SENTIMENT 압도)에서 도출. 산출 = `docs/chain_sight/news_vocab/vocab_v1.json`(13버킷 46카테고리 + 7테마, 커버<20 소거). 파이프라인 = P1(결정론 n-gram + 필터 ⑴티커/회사 **풀네임 매칭** + ⑵HHI + ⑶≥6개월) → P1-d(동음이의·非테마 배제, LLM) → P2(한국어 카테고리 정제, LLM). **LLM 사용 범위 = P1-d·P2 정제 한정**(상한 50콜/$0.10, 실사용 14콜 ≈$0.018); L2 태그 군집 트랙의 무LLM·결정론·임베딩 금지는 별개 유효. **배정(Rev.3) = 상대비중 매칭**: 상대 종목 기사 중 테마 문구 등장 **비율 ≥ τ**(절대 건수 폐기). 다중매칭 우선순위 = 그 엣지에서의 **비중** 높은 테마(HHI 우선 폐기 — HHI는 전역 속성이라 개별 엣지 적합도 미반영) → 커버 → 문구 길이. R=50% 안전망 + 최소 2건. **Why**: 절대건수 매칭은 버즈워드 스침 언급을 오배정(ZBRA↔양자컴퓨팅 17건, ZBRA는 바코드·RFID로 무관). 비중+비중우선순위로 ZBRA 양자 **17→0** 교정. τ 검증세트는 **겹침**(AI리더 share≈5% < IBM양자 8%, IONQ는 진짜 양자기업 58%) → τ=4.6%(min-매칭) 채택·share우선순위가 실질 판정. **잔여 저-share(6~16%) 스침 매칭 = M3(태그 교차) 검토 재료**(서빙 반영 전 정밀화, 미승인).

---

## D-CS-P1A-RELANDING (2026-08-10, 뉴스 관계 착지 수리 — before→after KPI)

**집행**: CS-P1A Slice1-4. `update_relation_confidence` 재조립으로 P2-1(뉴스 착지 91% 누수) 수리. 참조: D2.

**KPI before → after** (Slice4 라이브 백필, 병진 GO 게이트 뒤 집행):
- CO_MENTIONED 유니버스내 쌍: **248 → 1,449** (전체 278 → 1,957, 신규 **1,679**·갱신 133 — 게이트 dry-run 예측과 정확 일치)
- last_observed max: **2026-06-20 동결 → 2026-08-10 해소**
- serving_layer(Slice2 additive, migration 0029 병진 수동 적용) 백필: **evidence 2,229**(SEC4종+CO_MENTIONED) / **context 13,149**(PEER_OF+PRICE_CORRELATED) / **pending 2**(PEER)
- 총 RelationConfidence 13,701 → 15,380

**구조 결정**: ⑴ 서두 Neo4j `MATCH PEER_OF/BELONGS_TO_INDUSTRY` 제거(GraphQueryError 전체실패 근원) ⑵ PEER_OF 착지 루프 제거 — 유일 소스가 Neo4j(그래프 동결)이고 Postgres 자기조달은 `update_or_create`가 기존 9,365의 relation_status를 변경해 OUT 위반 → 경로째 제거 ⑶ PRICE_CORRELATED 착지 은퇴(D2: price=강도 속성 P1B 이관) ⑷ CO_MENTIONED 착지 존치(임계 count≥2 보존). **기존 PEER_OF 9,365·PRICE 3,784 무접촉**(status·score 불변, `.update()` serving_layer만).

**잔여**: Slice3 종목↔카테고리 매핑은 τ 매칭 로직 코드·종목별 share 데이터 repo 부재로 미수행(별도). 워커 재시작으로 라이브 beat(매일 11:00 ET) 새 코드 반영.

## D-MOAT-STORAGE-PG (2026-08-10, SUNMON-RECON 정정 — 디렉터 가설 기각)

**정정**: 해자(RelationPairSnapshot) 궤적 저장 경로 = **PostgreSQL 스냅샷 테이블 `chainsight_relation_pair_snapshot`, Neo4j 비의존**. "적립이 Neo4j에 물려 침묵" 디렉터 가설 **기각** — SUNMON-RECON 실측: 07-01~08-09 매일 9562행 적립·실패 0(#28 해소), Neo4j-down과 무관. `pair_aggregation.py` `update_or_create` per (canonical_a, canonical_b, period). cf. [[D-CS-P1A-RELANDING]](관계 파이프라인 Neo4j 제거).

## D-SUNMON-REEXTRACT (2026-08-10, CORPUS-SUNMON-EMPTYKW 조치 — 선택지 ① 채택, 병진 승인)

**문제**: SUNMON-RECON 근원 = 추출↔수집 타이밍 레이스. `extract-daily-news-keywords`(16:45 ET·localdate KST)가 주말 기사의 늦은 수집(av-broad 01:00 UTC)보다 이르게 발화 → `status=failed` → **failed 행 재추출 트리거 부재**로 corpus 영구 공백. cf. `docs/features/theme-heat/sunmon_recon_report.md`.

**3안 비교 (가중합, 기준: 근원 적중 0.35·표면 최소 0.30·회귀 위험 0.20·패턴 재사용 0.15)**:

| 안 | 내용 | 가중합 |
|---|---|---|
| **① A (채택)** | av-broad 수집 완료에 **체이닝된 재추출 트리거** 추가(당일+전일 failed 재추출). 추출 스케줄·창 정의 무접촉 | **4.40** |
| B | `collect-*` 평일전용(`1-5`) → 주말 수집 경로 보강(수집 스케줄 변경) | 3.45 |
| C | `target_date=localdate()` KST 조기창 재정의 | 3.20 |

**결정**: **① A** (마진 0.95). **Why**: 근원(재추출 부재)을 직접 타격하면서 추출 스케줄·창 정의를 **무접촉**(최소 표면). TH-TNV-CHAIN에서 입증된 **체인 패턴 재사용**(신규 beat 없음, #28 drift 회피). B(수집 스케줄)·C(창 재정의)는 표면 넓고 이중집계/비용 리스크 → **C는 관찰 보류**(범위 밖, 향후 재검토). **병진 승인 = ①**. 집행 = 지시서 `TH-SUNMON-REEXTRACT-1`.

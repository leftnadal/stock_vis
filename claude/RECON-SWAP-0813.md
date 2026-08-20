# RECON-SWAP-0813 — MON SWAP-REVIEW 트랙 전수조사 보고서

> 지시서: DIRECTIVE-MON-RECON-SWAP-0813 (2026-08-13 계획 세션 발행)
> 성격: 전항 읽기 전용 RECON — DB 쓰기·마이그레이션·beat·배포·브랜치 삭제 0
> 보고 규율: 모든 수치에 사용 명령·출력 verbatim 병기 (D-P4-GATE-PROVENANCE 준용). directive 명칭이 repo와 상이하면 repo가 진실 — 조정 내역 명기.
> 브랜치: `monorepo/sess-recon-swap` · 산출물: 본 파일 1건
> 조사 실행일: 2026-08-14 (지시서 발행 08-13 익일)

---

## STEP 0 — 기준선

### git 기준선

```
$ git fetch origin && git rev-parse origin/main
e8d8682bd101dca6c6867c7ce3eb84a9892128c4

$ git log --oneline -5 origin/main
e8d8682b docs(harness): DSS-RECON-1-CLEANUP 등재 + SECB CLEANUP 2건 done 정정
934428f9 docs(governance): MPS-2 원장 — D-MPS-COLOR + MPS-2 done + MPS-1-LAND 마감 + S4-REBASE 트리거
e306a30e feat(marketpulse-v2): MPS-2 StressCard — 결정론 카피 + 경보색 토큰 + hero 직하 삽입
7b4775d2 docs(theme-heat): DSS-RECON-1 정찰 보고 — 커버리지·재사용 표면·함정 A~C 실측
036ce165 docs(harness): DSS-RECON-1 지시서 등재
```

- **origin/main HEAD = `e8d8682b`** — 직전 세션 기준값 `b7d25aff`에서 **이동함**(그 사이 MPS-1/MPS-2 StressCard·DSS-RECON-1 트랙 착지). 정리 트랙(RECON-SWAP)과 무관한 병렬 세션 전진.
- 본 RECON 보고서 브랜치 `monorepo/sess-recon-swap`는 이 HEAD(`e8d8682b`)에서 격리.

### 테스트 3기준선 (pytest monitor / vitest / tsc)

측정 트리 = 메인 `Desktop/stock_vis`(`monorepo/sess-signal-fwd-recon`, HEAD `cca67275`) · node `v22.19.0` · 워크트리 아님(심링크 false-red 회피). ⚠️ 이 트리는 origin/main(`e8d8682b`)보다 뒤 — 기준선은 현 메인 트리 기준값(대부분 동일 예상하나 origin/main 재측정 시 미세 차 가능).

| 항목 | 명령 | 결과 |
|------|------|------|
| pytest (monitor) | `python -m pytest tests/monitor -q` | **215 passed / 0 failed / 0 skipped** (51.67s) |
| tsc | `npx tsc --noEmit` (frontend) | **0 errors** (exit 0) |
| vitest | `npx vitest run` (frontend) | **769 passed / 0 failed** (103 files, 21.45s) |

조정: `apps/monitor`는 테스트 파일 부재(`collected 0 items`) → 실제 monitor 테스트는 `tests/monitor/`에 존재하여 그 경로로 실행(directive "pytest(monitor)"의 repo 실위치 = `tests/monitor`).

```
$ python -m pytest tests/monitor -q
collected 215 items
...
============================= 215 passed in 51.67s =============================

$ npx tsc --noEmit    # frontend/, TSC_EXIT=0, 출력 없음(에러 0)

$ npx vitest run      # frontend/
 Test Files  103 passed (103)
      Tests  769 passed (769)
   Duration  21.45s
```

### 워크트리 산술 2건 묶음 해명 (이월 항목)

측정: `git worktree list | wc -l` = **25** (본 RECON 워크트리 add 직전).

**결론(1줄)**: **워크트리 총수는 다중 동시 세션이 add/remove하는 공유 가변 상태**이므로, 특정 지시서의 "정리 N건"과 시점 델타(count)가 1:1 대응하지 않는다 — 아래 두 산술 불일치는 전부 이 성질에서 나온다(오기 아님).

**⑴ CLEANUP-8 "63→22 vs 40 삭제"** (−41 vs 40):
- "40건"은 **완전 삭제(worktree+branch 동시)** 건수. "63→22"(=41 물리 worktree 제거)는 40 완전삭제 + **1건 부분정리**(⑤ `sess-s1b1`: worktree 제거·로컬 branch ref 잔존 → 완전삭제 40에서 제외)에서 나오는 +1.
- 교차검증: dry-run 45 = 40 삭제 + 5 스킵 ✓ / 41 제거 = 40 완전 + 1 부분(s1b1) → 63−41=22 ✓. CLEANUP-8 원장 ⑵⑤가 이 +1을 자체 문서화.

**⑵ "22→18 vs 정리 3건"** (−4 vs 3):
- RUNBOOK-MANUAL-CLEANUP-0813은 ①②③ 3 worktree 제거로 22→19를 기대. 실측은 ②(sv-theme-heat)·③(sv-mgmt-th-docs) worktree가 **실행 시점 이미 부재**라 실제 live 제거는 ①(sv-p4-final) **1건뿐** → 그것만이면 22→21이어야 함.
- 그런데 실측 22→**18**(−4). 초과 −3은 **발행~실행 창에서 동시 병진/타 세션이 병렬 제거한 분**. = 시점 델타가 단일 지시서 항목수와 어긋나는 전형.
- 오늘(08-14) 25로 재증가 = DSS-RECON-1·MGMT-B29/30/31·MPS1/2·NEO4J-RECON·P3-UNIVERSE·S2B1·SPLIT-GUARD 등 **신규 세션 워크트리 다수 추가** → 공유 가변성 재확인.

---

## PART A — 데이터 지반: EOD·유니버스

**9지표 정본**: `advisor_briefing.build_context`는 `monitor.indicators.filter(is_active=True,is_paused=False)`를 커버리지 분모로 씀("9 하드코딩 금지"). 9지표 단일소스 = `apps/monitor/catalog.py STOCK_INDICATOR_CATALOG` = **EODSignal 파생 3종**(eod_composite/change_percent/dollar_volume ← `stocks.EODSignal`) + **DailyPrice 산출 S계열 6종**(sma200_gap 200일·momentum_12_1 252일·high_52w_proximity 252일·volume_ratio 20일·macd_histogram ~26일·rsi14 14일). 모델 위치 조정: DailyPrice·EODSignal = `packages/shared/stocks/models.py`; IndicatorReading = `apps/monitor/models/indicator.py`(monitor 산출값·symbol 필드 없음).

### A-1. 보유 6종 × 9지표 매트릭스
원천 깊이:
```
PLTR  DailyPrice n=778 2023-07-10..2026-08-13 | EODSignal n=78 latest 2026-08-13
GEV   DailyPrice n=597 2024-03-27..08-13       | EODSignal n=78 latest 08-13
GOOGL DailyPrice n=778 2023-07-10..08-13       | EODSignal n=67 latest 2026-08-11 (stale)
TLN   DailyPrice n=277 2025-07-03..08-13       | EODSignal n=0
IREN  DailyPrice n=277 2025-07-03..08-13       | EODSignal n=0
IONQ  DailyPrice n=277 2025-07-03..08-13       | EODSignal n=0
```
**6×9 IndicatorReading 행수 매트릭스** (●있음 ○공백 △얕음):

| 지표 \ 종목 | PLTR | GEV | GOOGL | TLN | IREN | IONQ |
|---|---|---|---|---|---|---|
| 1 eod_composite | ●66 | ●66 | △61(stale) | ○0 | ○0 | ○0 |
| 2 change_percent | ●66 | ●66 | △61 | ○0 | ○0 | ○0 |
| 3 dollar_volume | ●66 | ●66 | △61 | ○0 | ○0 | ○0 |
| 4 sma200_gap | ●132 | ●132 | ●132 | ●78 | ●78 | ●78 |
| 5 momentum_12_1 | ●103 | ●103 | ●103 | △25 | △25 | △25 |
| 6 high_52w_proximity | ●104 | ●104 | ●104 | △26 | △26 | △26 |
| 7 volume_ratio | ●132 | ●132 | ●132 | ●161 | ●133 | ●161 |
| 8 macd_histogram | ●132 | ●132 | ●132 | ●161 | ●133 | ●161 |
| 9 rsi14 | ●132 | ●132 | ●132 | ●161 | ●133 | ●161 |

- 최신 asof: 5종 `2026-08-12 15:00Z`; **GOOGL EOD계 3종만 08-10**(원천 EODSignal 08-11 정지).
- 공백 축: 비SP500 3종(TLN/IREN/IONQ) 지표 1~3(EODSignal 파생) 전부 0행. 얕음 축: 3종 지표 5·6(252일 요구)이 이력 짧아 ~25행.

### A-2. 비SP500 3종 EOD 수집 경로
**결론: EODSignal은 SP500 전용 → 3종은 구조적 미대상. 단 DailyPrice는 별도 경로로 매일 신선.**
- `SP500EODService.sync_eod_prices`(`packages/shared/stocks/services/sp500_eod_service.py`)는 `SP500Constituent.is_active=True`만 순회, DailyPrice에만 기록. SP500 멤버십 실측: PLTR/GEV/GOOGL=True, **TLN/IREN/IONQ=False**. EODSignal은 `EODPipeline`(SP500 유니버스) 생성 → 3종 0행.
- 3종 DailyPrice는 일반 stock-sync(`stock_sync_service.py:343`/`api_request/stock_service.py` AV TIME_SERIES_DAILY, watchlist/포트폴리오 종목)로 매일 채워짐. monitor `ingest_technical_for_monitor`는 DailyPrice 읽기만.
- `is_eod_fresh`(`apps/monitor/tasks.py:42`) = `latest_eod_date()(EODSignal Max) == ET오늘`(전역 판정·종목 무관). refresh 미도착 시 20분 2회 재시도 후 `skipped_stale_eod`.
- 3종 DailyPrice 최근 14거래일 무결번(최신 08-13, 주말만 결번) → **DailyPrice 경로 건강·EODSignal 경로 미해당**.

### A-3. FMP 커버리지 (외부 API 총 10콜)
클라이언트=`packages/shared/api_request/providers/fmp/client.py`(`/stable/*`). 키 `len=32 head=qA1W***`. 프로브 10콜:
```
[1] EOD IONQ /stable/historical-price-eod/full: keys=[symbol,date,open,high,low,close,volume,change,changePercent,vwap]
    2026-08-13 open=44.9 high=47.95 low=44.73 close=44.98 vol=20945069
[2] EOD TLN : 2026-08-13 open=365.49 high=371.09 low=355.62 close=358.4 vol=578646
[3] EOD IREN: 2026-08-13 open=45.98 high=49.19 low=43.99 close=44.76 vol=71067225
[4] EOD ^GSPC: 2026-08-13 open=7763.18 high=7816.7 low=7763.18 close=7798.99 vol=2684931044
[5-10] /stable/price-target-consensus PLTR/TLN/GEV/GOOGL/IREN/IONQ: 각 LIST len=1 [targetHigh,targetLow,targetConsensus,targetMedian]
TOTAL FMP CALLS = 10
```
- 3종 EOD 정상 응답, 402/프리미엄 없음(`.` 미포함·#23 미해당). **EOD 응답에 open/high/low 포함 = YES**(PART E 전제 충족). 컨센서스 6/6 커버. 지수 `^GSPC` 가용(벤치마크 경로 확보).
- 주: SFI `AnalystSignalSnapshot` ingest는 현 브랜치 워킹트리 부재(미병합) → 컨센서스는 라이브 프로브로만 확인(저장 파이프라인 없음).

### A-4. 뉴스 커버리지 (NewsEntity.symbol 경유)
```
PLTR  NewsEntity=1729 articles=1729 latest 2026-08-13 18:05Z
GOOGL NewsEntity=4758 articles=4758 latest 08-13 13:55Z
GEV   NewsEntity=663  articles=663  latest 08-13 17:12Z
IONQ  NewsEntity=116  articles=116  latest 08-13 02:16Z
IREN  NewsEntity=60   articles=60   latest 08-13 12:46Z
TLN   NewsEntity=5    articles=5    latest 08-13 17:17Z   ← 사실상 공백
```
- 전 종목 최신 발행 08-13(파이프라인 생존). **TLN 공백 확정 = 5건**(GOOGL 4758·PLTR 1729 대비 3자릿수 격차). 심도 서열 GOOGL≫PLTR≫GEV≫IONQ>IREN≫TLN. (구 A-4의 "TLN 0행"은 `entities__source='alpha_vantage'` 필터 한정 관측이었고, 경로 무관 실측 = 5건 — 정정.)
- 필드 조정: `published_at` 사용(created_at 아님).

### A-5. 유니버스 폭·심도
```
DailyPrice distinct symbols=747  total rows=426,641  range 2023-07-10..2026-08-13
EODSignal  distinct symbols=520  total rows=32,376   range 2026-02-25..08-13 (distinct 거래일 109)
DailyPrice depth/symbol: min=1 median=778 max=778 mean=571.1
```
- 폭: DailyPrice 747 ⊃ EODSignal 520(SP500 부분집합). 심도 중앙값 778거래일(~3년), **최소 1행**(신규/오염 의심·좌표만). EODSignal은 distinct 거래일 109인데 종목별 최대 78행 = 일자별 부분수집.
- 6종 심도: PLTR/GOOGL 778, GEV 597, TLN/IREN/IONQ 277(2025-07-03 시작).

### A-6. 백필 볼륨 산술
가정: (i) EODSignal은 기존 DailyPrice(277행/종목)로 EODPipeline 재계산 가능(외부 0콜), (ii) FMP 재검증 시 `historical-price-eod/full` 1콜/종목 full-depth, (iii) window ≥02-25(118거래일/종목).
- **안 A "EOD만"**: 외부 0~3콜(재계산/재검증). 저장 = EODSignal 3×118=354행(window) 또는 3×277=831행(full) + IndicatorReading 지표1~3 재산출 ~594행. 총 ~948~1,425행. LLM 0.
- **안 B "EOD+뉴스"**: 외부 3~12콜(안A + 뉴스 3~9콜, `/stable/news/stock` 페이지네이션). 저장 = 안A + 뉴스 상한 ~1,500행(TLN 발행 희소로 실효 수백 미만 개연). LLM = 뉴스 감성/엔티티 파이프라인 기사당 호출(별도 산정·스코프 밖).
- 판단: EOD 갭 해소 저비용(외부 0~3콜·~1k행). 뉴스 일괄은 호출·행수 크고 TLN 실효는 희소성 제약 → 안A 우선, 뉴스는 TLN 표적 별건 권장.

### A 조정 내역
| directive | repo 실제 |
|---|---|
| advisor_briefing.py | origin/main만(현 브랜치 부재), 9지표 정본=`apps/monitor/catalog.py` |
| "stocks 앱" DailyPrice/EODSignal | `packages/shared/stocks/models.py`; IndicatorReading=`apps/monitor`(산출값·symbol 없음) |
| NewsArticle.created_at | 커버리지는 `published_at` |
| Monitor "6종 active"(memory) | 실측 **6종 전부 setting_up** |
| SFI AnalystSignalSnapshot | 현 브랜치 부재(미병합) |

### A 이상 관측 (수리 금지, 좌표만)
1. **6종 전부 status=setting_up** — memory "6종 active"와 불일치(B-1과 동일 관측). 좌표 monitor_monitor.status.
2. **비SP500 3종 EODSignal 영구 공백** — 지표 1~3 × 3종 = 9셀 0행. `ingest.py:81`이 "EODSignal 없음" warning 로그만·진행(무음 실패 아님, 사용자엔 지표 공백). 좌표 sp500_eod_service.py(SP500 only)·ingest.py:81.
3. **GOOGL EODSignal stale** — SP500인데 EODSignal 최신 08-11(타 08-13), EOD계 Reading 08-10. 좌표 stocks_eod_signal(GOOGL, date>08-11 부재).
4. **EODSignal 일자별 부분수집** — distinct 거래일 109 vs 종목별 최대 78행. 좌표 EODPipeline Stage2.
5. **IndicatorReading asof 1일 지연** — 최신 08-12 15:00Z vs DailyPrice 08-13(모니터 setting_up beat 미가동 정합). 좌표 refresh_monitors_task.
6. **DailyPrice 최소 심도 1행** — 747종 중 depth=1 존재. 좌표 stocks_daily_price.

---

## PART B — 상태·이력·노이즈

조사 모델 확정: `apps.monitor.models.monitor.Monitor`, `.monitoring.MonitorSnapshot`, `.indicator.MonitorIndicator`/`IndicatorReading`, `.alert.AlertEvent`. 지표 판독 = `IndicatorReading`(directive 추정 확정).

### B-1. Monitor.status 전이 실측

**6종 현재 status·current_state** — status 전부 `setting_up` 고착, current_state 전부 `active`:
```
TOTAL monitors: 6
IONQ 아이온큐 status=setting_up current_state=active created=2026-07-28 target_date_end=None
IREN 아이렌   status=setting_up current_state=active created=2026-07-28
PLTR 팔란티어 status=setting_up current_state=active created=2026-07-28
GOOGL 구글    status=setting_up current_state=active created=2026-07-28
TLN  탈렌     status=setting_up current_state=active created=2026-07-28
GEV  GE버노바 status=setting_up current_state=active created=2026-07-28
status 분포={'setting_up': 6}   current_state 분포={'active': 6}
```

**전이 로직 grep**:
```
apps/monitor/services/pipeline.py:77:  monitor.current_state = new_state   # current_state 유일 쓰기
apps/monitor/services/state_machine.py:43:  if monitor.status == 'archived':  # status 읽기(가드)
apps/monitor/services/state_machine.py:59:  if monitor.status == 'paused':    # status 읽기(가드)
apps/monitor/management/commands/evaluate_monitors.py:34:  qs.exclude(status__in=[PAUSED,ARCHIVED])  # status 읽기(제외필터)
```
판정:
- **`Monitor.status`를 setting_up→active로 바꾸는 코드는 repo 전체에 0건** — status는 읽히기만(배치 제외 필터 + archived/paused 가드). 자동 전이 호출 실재 = **없음**.
- status 유일 쓰기 통로 = `MonitorSerializer`(status가 read_only_fields에 **없음**, serializers.py:305-308) → 사용자 PATCH로만 수동 변경 가능(미발생). setting_up은 배치 제외 대상 아님(evaluate_monitors.py:34는 paused/archived만) → **평가는 정상 수행 → current_state만 전진**.
- `current_state` 유일 쓰기 = `pipeline.py:77` `evaluate_monitor` 내부(`save(update_fields=['current_state','updated_at'])`).

**전이 이력 저장처**: `Monitor.status` 전이 이력 = **어디에도 저장 안 됨**(전용 History/Audit 테이블 부재). `current_state` 전이는 `AlertEvent`(from_state→to_state) + `MonitorSnapshot.state`(일별)로 de-facto 보존:
```
TOTAL AlertEvent: 8
PLTR warming_up->active @2026-08-03 | PLTR active->strengthening @08-04(suppressed) | PLTR strengthening->active @08-10(deteriorate)
IONQ/IREN/GOOGL/TLN/GEV warming_up->active @2026-08-03   (전부 current_state 전이·5거래일 warmup 종료·status 무관)
```

**상태 3원 좌표(수리 금지)**: ① `Monitor.status`(사용자 의도, setting_up 고착·자동전이 부재) ② `Monitor.current_state`(엔진, active) ③ `MonitorSnapshot.state`(일별). advisor 프롬프트 "상태"=③ 선행 발견은 코드 정합.

### B-2. MonitorSnapshot 이력 전수

```
TOTAL MonitorSnapshot rows: 78   (6종 × 13행 균일)
per monitor: 각 n=13, asof 2026-07-28 → 2026-08-13 (달력17일=13거래일), created 07-28 22:45Z ~ 08-13 22:45Z
distinct state: {'active':50, 'strengthening':4, 'warming_up':24}
fields: ['id','monitor','asof_date','overall_score','state','data_coverage','created_at']   # 7개
```
- 총 78행, 깊이 = 13 거래일(생성일 07-28부터 매일 upsert). state는 시간축 변동(현 단면 active).
- **필드 7개뿐**. **zone/밴드 저장 안 됨**(PriceZone은 `Claim.last_price_zone`에만·전이감지용). **지표별 z 저장 안 됨**(집계 스칼라 overall_score만).
- **display 전부 런타임 파생**: `MonitorSerializer.get_display`(serializers.py:329-350)가 latest_score에서 score_to_degree/degree_to_color/degree_to_label/score_to_phase(달 위상) 매 응답 계산. overall_score만 저장, degree·color·label·phase·zone은 전량 런타임.

### B-3. IC 패널 가능성 (IndicatorReading z 시계열 재구성)

```
TOTAL MonitorIndicator: 54 (6종×9지표)   TOTAL IndicatorReading: 4536
GEV/GOOGL/PLTR #ind=9 readings=918~933 asof 2026-02-03→2026-08-12
IONQ/TLN        #ind=9 readings=612      asof 2025-12-21→2026-08-12
IREN            #ind=9 readings=528      asof 2026-02-02→2026-08-12
GEV 지표별: sma200_gap/volume_ratio/macd_histogram/rsi14 n=132(technical); momentum_12_1 n=103; high_52w_proximity n=104;
            eod_composite/change_percent/dollar_volume n=66(market_data, 2026-03-29→08-12)
```
판정("6종 × 일별 z 단면 패널 소급 구성 가능 기간"):
- `IndicatorReading`은 raw `value`만 저장 — z는 미저장(`score_indicator_from_model` window=60 MAD robust-z 런타임 계산). **raw 이력이 깊어 z 시계열 소급 재구성 가능**(각 asof를 as_of_date로 재계산).
- 재구성 깊이: **technical 5종 = 2026-02-03부터 ~132 거래일**(IONQ·TLN rsi14 등은 2025-12-21부터 ~156일). **market_data 3종 = 2026-03-29부터 ~66 거래일**(단 IREN·IONQ·TLN은 eod_composite 표본 없음).
- **스냅샷 vs raw**: MonitorSnapshot(집계) 13거래일 얕음 ↔ IndicatorReading raw ~132거래일 깊음. **일별 z 패널은 스냅샷 13일이 아니라 raw 재계산 기준 ~4.5개월(market_data 하한)~6개월(technical) 소급 가능.** 6종 공통: technical-only 패널이면 6종 전부 ~2월초, market_data 포함이면 GEV·GOOGL·PLTR 3종만 ~3월말.

### B-4. 노이즈 플로어 실측 (핵심)

스크립트 전문(repo 미커밋, `python manage.py shell < noise_floor.py` 순수 조회):
```python
import numpy as np
from apps.monitor.models import Monitor, IndicatorReading
from apps.monitor.services.indicator_scorer import score_indicator_from_model
TICKERS = ["PLTR","TLN","GEV","GOOGL","IREN","IONQ"]
Z_KEYS = ["eod_composite","sma200_gap","rsi14"]
def stats(deltas):
    a = np.abs(np.array(deltas, dtype=float))
    if len(a)==0: return None
    return {"n":len(a),"mean_abs":round(float(np.mean(a)),4),"sigma":round(float(np.std(np.array(deltas,dtype=float))),4),
            "p95":round(float(np.percentile(a,95)),4),"max":round(float(np.max(a)),4)}
# (1) overall_score 일간 델타 — MonitorSnapshot 저장값
for tk in TICKERS:
    m = Monitor.objects.get(target_ref=tk)
    scores = list(m.snapshots.order_by("asof_date").values_list("overall_score", flat=True))
    deltas = [scores[i]-scores[i-1] for i in range(1,len(scores))]
    st = stats(deltas); flag = "  << 20거래일 미만 = 표본 부족" if (st and st["n"]<20) else ""
    print(f"{tk:6} snap_n={len(scores):2} delta_n={st['n']:2} mean|Δ|={st['mean_abs']} sigma={st['sigma']} p95={st['p95']} max={st['max']}{flag}")
# (2) z-score 일간 델타 — raw readings as_of 롤링 재계산
for tk in TICKERS:
    m = Monitor.objects.get(target_ref=tk)
    for key in Z_KEYS:
        ind = m.indicators.filter(source_key=key).first()
        if ind is None: print(f"{tk:6} {key:16} (지표 없음)"); continue
        dates = sorted({r.date() for r in ind.readings.filter(validation_status__in=["ok","extreme_jump_allowed"]).values_list("asof",flat=True)})
        z_series = [score_indicator_from_model(ind, as_of_date=d)["raw_z"] for d in dates if score_indicator_from_model(ind, as_of_date=d).get("is_sufficient")]
        deltas = [z_series[i]-z_series[i-1] for i in range(1,len(z_series))]
        st = stats(deltas)
        if st is None: print(f"{tk:6} {key:16} (표본 없음)"); continue
        print(f"{tk:6} {key:16} z_n={len(z_series):3} delta_n={st['n']:3} mean|Δ|={st['mean_abs']} sigma={st['sigma']} p95={st['p95']} max={st['max']}{'  << 표본 부족' if st['n']<20 else ''}")
```
실행 raw 출력 — **(1) overall_score 델타** (전부 표본 부족):
```
PLTR  snap_n=13 delta_n=12 mean|Δ|=0.0295 sigma=0.0537 p95=0.1232 max=0.1885  << 20거래일 미만 = 표본 부족
TLN   snap_n=13 delta_n=12 mean|Δ|=0.0125 sigma=0.0121 p95=0.0229 max=0.0317  << 표본 부족
GEV   snap_n=13 delta_n=12 mean|Δ|=0.0107 sigma=0.0113 p95=0.0246 max=0.0264  << 표본 부족
GOOGL snap_n=13 delta_n=12 mean|Δ|=0.0168 sigma=0.023  p95=0.0459 max=0.0572  << 표본 부족
IREN  snap_n=13 delta_n=12 mean|Δ|=0.0218 sigma=0.0249 p95=0.0494 max=0.0652  << 표본 부족
IONQ  snap_n=13 delta_n=12 mean|Δ|=0.0273 sigma=0.0446 p95=0.0871 max=0.1353  << 표본 부족
```
**(2) z-score(raw_z) 델타** (raw 재계산, 표본 충분):
```
PLTR  eod_composite z_n= 61 delta_n= 60 mean|Δ|=0.3562 sigma=0.7308 p95=1.538  max=2.3975
PLTR  sma200_gap    z_n=127 delta_n=126 mean|Δ|=0.4159 sigma=0.7014 p95=1.1729 max=5.3158
PLTR  rsi14         z_n=127 delta_n=126 mean|Δ|=0.4276 sigma=0.6339 p95=1.3282 max=3.3639
TLN   eod_composite (표본 없음)
TLN   sma200_gap    z_n= 73 delta_n= 72 mean|Δ|=0.4961 sigma=0.6182 p95=1.1683 max=1.5796
TLN   rsi14         z_n=156 delta_n=155 mean|Δ|=0.4776 sigma=0.6986 p95=1.1535 max=3.6667
GEV   eod_composite z_n= 61 delta_n= 60 mean|Δ|=1.2337 sigma=1.8326 p95=3.9671 max=3.9671
GEV   sma200_gap    z_n=127 delta_n=126 mean|Δ|=0.4365 sigma=0.5859 p95=1.2191 max=2.5494
GEV   rsi14         z_n=127 delta_n=126 mean|Δ|=0.3997 sigma=0.559  p95=1.1649 max=2.715
GOOGL eod_composite z_n= 56 delta_n= 55 mean|Δ|=0.0244 sigma=0.1269 p95=0.0045 max=0.6655
GOOGL sma200_gap    z_n=127 delta_n=126 mean|Δ|=0.2367 sigma=0.326  p95=0.5903 max=1.7479
GOOGL rsi14         z_n=127 delta_n=126 mean|Δ|=0.309  sigma=0.4339 p95=0.8215 max=1.8984
IREN  eod_composite (표본 없음)
IREN  sma200_gap    z_n= 73 delta_n= 72 mean|Δ|=0.3658 sigma=0.4698 p95=0.9037 max=1.3745
IREN  rsi14         z_n=128 delta_n=127 mean|Δ|=0.4601 sigma=0.6044 p95=1.2106 max=2.0165
IONQ  eod_composite (표본 없음)
IONQ  sma200_gap    z_n= 73 delta_n= 72 mean|Δ|=0.3636 sigma=0.572  p95=1.1561 max=2.1801
IONQ  rsi14         z_n=156 delta_n=155 mean|Δ|=0.3197 sigma=0.4691 p95=0.9797 max=2.2089
```
판독:
- **(1) overall_score 노이즈 플로어 = 표본 부족 결론.** 6종 전부 델타 12개 < 20거래일. σ(Δ) 0.011(GEV)~0.054(PLTR), mean|Δ| 0.011~0.030. **13거래일 이력(07-28 개시)이 근본 한계.** advisor 무변화 임계 0.02 대조: GEV/TLN/GOOGL mean|Δ|는 임계 근처/이하, PLTR/IONQ 초과 — 표본 부족으로 확정 불가.
- **(2) z 노이즈 플로어 = 표본 충분(재계산).** delta_n 55~155. raw_z 일간 σ(Δ) 0.13~1.83(대다수 0.4~0.7). 이상치: GEV eod_composite σ(Δ)=1.83·mean|Δ|=1.23, PLTR sma200_gap max|Δ|=5.32(EXTREME 5.0 초과 1회), GOOGL eod_composite mean|Δ|=0.024(거의 정지·MAD floor).
- **eod_composite 3종 표본 없음**: TLN·IREN·IONQ(B-3 market_data 66일이 GEV/GOOGL/PLTR에만 존재함과 정합).

### B 조정 내역
- `IndicatorReading` 추정 → 확정. 조정 없음.
- MonitorSnapshot `overall_score`는 directive의 DecimalField가 **아니라 `FloatField`**(monitoring.py:19), data_coverage도 Float(Claim 가격 필드만 Decimal) — repo가 진실.
- advisor "상태"=MonitorSnapshot.state(≠status) 코드 정합.

### B 이상 관측 (수리 금지, 좌표만)
1. **status 자동 전이 완전 부재** — setting_up→active 코드 0건(`apps/monitor/` 전역), status 감사/이력 테이블 부재, 6종 영구 setting_up.
2. **상태 3원화** — status(고착)/current_state(active)/MonitorSnapshot.state(일별). status 기반 필터(evaluate_monitors.py:34)는 setting_up을 활성 취급 → 사용자가 "완료" 의미로 status 쓰기 시작 시 충돌 소지. 좌표: state_machine.py:43,59·evaluate_monitors.py:34·serializers.py:305.
3. **overall_score 이력 13일(얕음) vs 지표 raw ~132일(깊음)** — 노이즈 플로어를 overall_score로 잡으면 표본 부족, z로 잡으면 충분. 스냅샷 백필 부재.
4. **PLTR sma200_gap max|Δ|=5.32** 극단 z 점프(threshold 5.0 초과 1회) + **GEV eod_composite σ(Δ)=1.83** 과변동 — 노이즈 플로어 이상치(관측만).

---

## PART C — 스키마·계약: Claim·빌더·브리핑

> ⚠️ **전 항목 관통 관측**: 현 체크아웃 `monorepo/sess-signal-fwd-recon`(HEAD `cca67275`)는 **advisor 트랙(MON-P4-LA) 전체 미포함** — `apps/monitor/models/advisor.py`·`services/advisor_briefing.py`·mig `0009`·FE `AdvisorEntry.tsx`는 **origin/main에만**. C-4·C-5 advisor 부분은 `git show origin/main:…` 추출. Claim 가격 스키마(mig 0007/0008)·serializer·builder FE는 현 워킹트리 실재.

### C-1. Claim 스키마 전수
**위치**: `apps/monitor/models/monitor.py:79` `class Claim` (docstring "구 thesis 개념의 재정의" — thesis Django 앱 **미존재**, Claim=monitor 앱 소속). `Claim._meta` 실측 주요 필드:
```
assertion TextField(F)   ← 진입/주장 근거 저장처(자유텍스트)      deadline DateField(T) ← 기한
scenario_type CharField(F, new_entry/hold/add_on)               purchase_price/purchase_date Decimal/Date(T)
entry_price Decimal(T)←진입가  target_price Decimal(T)←목표가  stop_price Decimal(T)←손절가
fair_value_low/high Decimal(T)  last_price_zone CharField(T)  entry_reached_at DateTimeField(T)
status(active/resolved)  outcome(pending/validated/partial/invalidated/inconclusive/expired)
proposed_verdict  resolved_by FK  factor_tags ArrayField(timing/ext_shock/indicator_noise/luck)  retro_memo TextField
```
- 가격 필드 마이그: `0007_claim_entry_price…`(2026-07-16 TIMING-P2, decimal_places=4/max_digits=15/null) + `0008_claim_purchase_…`(2026-07-21 HOLD-P1). 기한=`deadline`(mig 0001~).
- **진입 근거 저장 = 전용 구조 필드 없음, 자유텍스트 `assertion` 단일 슬롯이 유일.** 근거를 "신호/지표"로 구조화해 Claim에 매다는 필드 부재. 지표는 Monitor에 `MonitorIndicator`로 부착, Claim↔Indicator 조인은 마감시점 `ClaimIndicatorResult`(C-2)로만. → **생성시점 "근거 신호"는 구조적 미저장**, Monitor 부착 지표가 사실상 근거 풀.
- DB 실측: `Claim.count()=6`(6종 대응), purchase_price notnull=6 · **entry_price notnull=0 → 현행 6 Claim 전부 hold(보유관리) 모드**, 매수-진입 시나리오 0.

### C-2. ClaimIndicatorResult — 트리거유형별 원장 additive 재사용성
**위치**: `apps/monitor/models/closure.py:17` (docstring "가설 마감 시 전제별 hit/miss … 후속 승률·캘리브레이션 학습 루프 붙을 수 있다"). 필드: claim FK · indicator FK · result(HIT/PARTIAL/MISS/NA) · created_at · **UniqueConstraint(claim,indicator)**.
- **판정**: 유일 제약이 (claim,indicator) 2튜플 = Claim당 지표당 1행, 시맨틱 "마감 회고 전용" → 트리거유형·시점 축 부재로 **그대로는 다행 원장 불가**. additive 원장화하려면 `trigger_type`/`asof` 컬럼 + 유일제약 확장 필요(FK2+categorical 골격은 재사용 가능·유일제약이 병목). **DB: ClaimIndicatorResult=0행·ClosureSnapshot=0행**(마감 이력 0 → 스키마 변경 시 데이터 마이그 부담 0).

### C-3. 빌더 FE 현황
**주 파일**: `frontend/app/monitor/new/page.tsx`(`BuilderContent` 848행+, `TOTAL_STEPS=4`). 단계:
- step1(:348) scope · step2(:371) target_ref+name · **step3(:392) 지표(근거) 선택 — 이미 존재하는 "근거 신호 선택 UI"**(`useIndicatorCatalog`·`EVIDENCE_BADGE` 강/중/약 :38/:422·default_selected 프리선택) · step4(:438) scenario_type 토글(:443)+가격3필드(testid :668/686/701)+deadline(:741)+ScenarioSuggest+근거메모(assertion 재라벨 :804).
- 제출(:270-315): `create(monitor)`→picked 지표 `createIndicator` 루프→`createClaim({assertion,scenario_type,entry/target/stop_price,purchase_*,fair_value_*,deadline})`(memo 공란 시 가격으로 assertion 자동합성 :296).
- **근거신호 UI 삽입 지점**: (a) step3 지표선택을 "근거 신호 원장"으로 확장 or (b) step4 근거메모(:804) 옆 구조화 슬롯 신설 — 어느쪽도 createClaim payload(:301) 신규필드 + 백엔드 Claim 스키마 확장(C-1 부재) 동반.
- **터치 파일(v0)**: `app/monitor/new/page.tsx` · `services/monitorService.ts` · `types/monitor.ts` · `hooks/useMonitor.ts` · (선택) `components/monitor/builder/`.

### C-4. L-A 프롬프트 구조 (origin/main 전용)
`origin/main:apps/monitor/services/advisor_briefing.py` — `PROMPT_VERSION="v1.1"`. `SYSTEM_PROMPT_V1`(비서·사실/거리/상태만·매매지시 금지·**수치 기준/부호/정밀도 그대로 인용**·커버리지 n/총·JSON). `_render_user_prompt`(종합 %+.4f·Δ·달위상 display·현재가·`_pct_distance` 레벨거리). `build_context`(점수=MonitorSnapshot 정본 무재계산·커버리지=P2A 충분성·레벨=active Claim zone_anchor/target/stop). `generate_briefing` 멱등·실패무음·`packages.shared.llm.complete(provider="anthropic")`. beat=`tasks.py:117 advisor_briefing_task`(ADVISOR_ENABLED+EOD 신선도 가드).
- **"근거 생사 점검 라인" 삽입 지점**: `build_context` indicators 조립부 + `_render_user_prompt` suff_names 렌더 라인. Claim 근거 구조화 부재라(C-1) 현재 "근거 생사"의 유일 프록시 = 지표 충분성 커버리지.
- **AdvisorNote additive 여지**: `market_score`/`close_score`=2축 채점 **예약 필드(로직 없음)** 존재=확장 소켓, surface L-A/L-B/L-C 예약, 유일제약 (monitor,asof,surface). null=True additive 무해.
- **검증 로직 소재**: lexical 린트 = `advisor_briefing.py` `FORBIDDEN_LEXEMES`(~26개)+`_lexical_guard` → 검출 시 저장 거부. ⚠️ **수치 대조(출력숫자⊆프롬프트숫자) 게이트 = 프로덕션 미구현** — 프롬프트 계약+입력측 테스트(`tests/monitor/test_advisor_briefing.py:67 test_v11_state_display_and_score_precision`)로만 담보. [[lesson_llm_numeric_quote_contract]]는 지향 교훈이며 advisor 코드 미착지 → 출력측 린트 신설 시 additive.

### C-5. monitor serializer 노출 필드 계약
`apps/monitor/api/serializers.py`:
- **MonitorSerializer(:285)**: id,scope,target_ref,name,status,current_state,target_date_end,resolved_label,latest_score,**display**,indicator_count,next_deadline,has_claim,close_suggested,danger_streak,created_at,updated_at. `display`=SerializerMethod `{degree,color,label,phase,phase_label,phase_icon}`(BE 엔진 단일소스). read-only: current_state·close_suggested·danger_streak.
- **ClaimSerializer(:159)**: assertion,deadline,status,outcome,proposed_verdict,factor_tags,retro_memo,scenario_type,entry/target/stop_price,purchase_*,fair_value_*,last_price_zone,entry_reached_at,`zone_display`(:245 build_zone_display bands/ticks/rows/marker),closure_snapshot 등.
- **AdvisorNoteSerializer**(origin/main:16): id,asof,surface,headline,body,coverage_n,coverage_total,model_id,prompt_version,created_at(읽기전용). 엔드포인트=`MonitorViewSet.advisor_notes`(origin/main:views.py:220, GET detail, surface=L-A, limit 1~90). ⚠️ `input_tokens/output_tokens/market_score/close_score` **DB엔 있으나 serializer 미노출**.
- **FE 실소비**: `frontend/types/monitor.ts` interface Claim(:178)·Monitor(:138 latest_score·display)·ZoneDisplay(:56)·ScenarioSuggest(:92). advisor=`origin/main:AdvisorEntry.tsx`(headline·body·coverage_n/total·asof·model_id).
- **계약 테스트**: 전용 스냅샷 계약 테스트 **없음**(tests/monitor/test_api.py 간접만). `contracts/`에 **monitor-api.yaml 없음**(chainsight/sec-pipeline/validation만) → **monitor는 contract-driven 외곽**.

### C-6. watchlist 서피스 실위치
- **앱**: `packages/shared/users/`(apps/ 아래 아님 — directive "users 앱 추정" 물리경로 조정). 모델 `Watchlist`(:186, user FK·db_table users_watchlist)·`WatchlistItem`(:215, watchlist FK·stock FK(to_field=symbol)·**target_entry_price Decimal**·unique(watchlist,stock)). 뷰=`packages/shared/users/views.py`(+chain_sight `WatchlistViewSet` 별도 서피스).
- **monitor와 관계 = 별개 모델·별개 앱, FK/조인/공유제약 없음.** 겹침은 "같은 user·같은 심볼" 값 수준 우연 교집합뿐. WatchlistItem `target_entry_price` ↔ Claim `entry_price` 개념 중복 소지.

### C 조정 내역
- **thesis 앱 Claim → repo 진실 = `apps/monitor/models/monitor.py:79`**(thesis Django 앱 미존재, docstring "구 thesis 재정의". CLAUDE.md thesis 표는 구 아키텍처 잔재, monitor로 흡수).
- advisor = apps.monitor advisor_briefing.py/AdvisorNote/v1.1 **맞음, 단 현 브랜치 미포함 → origin/main 확인**.
- watchlist = **`packages/shared/users`**(users 앱 아님, "추정" 방향 맞고 물리경로 조정).

### C 이상 관측 (수리 금지, 좌표만)
1. **근거 신호 생성시점 구조 저장 부재** — Claim `assertion` 자유텍스트 단일 슬롯, 근거=MonitorIndicator 집합 대행, Claim↔지표 결합은 마감시점 ClaimIndicatorResult(0행)로만. C-3 UI·C-4 프롬프트 라인 모두 이 공백 위.
2. **advisor 수치 대조 게이트 미구현** — `generate_briefing`은 lexical만, 출력측 numeric quote 검증 없음(MEMORY 교훈↔코드 갭).
3. **AdvisorNote 예약필드 미노출** — market_score/close_score/input_tokens/output_tokens DB엔 있으나 serializer 미노출.
4. **monitor serializer 계약 테스트·contracts/ 스펙 부재** — 필드 추가/변경 시 회귀 감지망 약함.
5. **현 브랜치↔origin/main 드리프트** — advisor 트랙 전체(모델·서비스·mig0009·FE)가 현 체크아웃 미반영, 이 브랜치서 advisor 편집·마이그레이션 시 base 불일치 위험.
6. **Claim entry_price ↔ WatchlistItem target_entry_price 개념 중복** — 두 서피스 값 수준 교집합, 심볼 정합·중복입력 주체 불명확.

---

## PART D — 인접 렌즈 재료 (조사만)

### D-1. market_pulse — 지수 EOD 시계열 보유
**앱 조정**: directive `macro`(추정) → 지수 원장은 최상위 **`macro/`**(`macro.MarketIndex`/`MarketIndexPrice`, `macro/models/indicators.py:144/:218`, table macro_market_index_price, OHLCV+change, unique(index,date)), 카드/레짐은 `apps/market_pulse/`.
```
MarketIndex total: 36   MarketIndexPrice total rows: 3256
SPY   us_equity  rows=794  2023-07-14..2026-08-14   ← 시장 벤치마크 ~3년 완비
QQQ/DIA/IWM      rows=132  2026-03-03..08-14        (얕음)
XLB..XLY(sector11) rows=113  2026-04-01..08-14
GCUSD/SIUSD/EURUSD/GBP/CNY/JPY/KRW rows=110  2026-04-03..08-14
^VIX/^GSPC/^IXIC/^DJI/^FTSE/^HSI/^N225 rows=6  2025-12-09..2026-02-26 (정지·사문)  ^GDAXI rows=5
TLT/GLD/SLV/VEA/UUP  rows=0 (등록만·미적재)
```
레짐(`apps/market_pulse/models/regime.py:18 RegimeSnapshot`)은 VIX 원값을 inputs JSON에 일별 적재:
```
RegimeSnapshot count: 804  range 2023-07-10..2026-08-14   (latest LATE_BULL, inputs.vix=14.55)
BreadthSnapshot 91 (2026-04-24~)  SectorFlowSnapshot 869 (04-27~)  ConcentrationSnapshot 50 (04-27~)
```
**판정 — "시장 z" 산출 = 가능(조건부)**: SPY 794일(~3년) OHLCV로 시장 수익률/변동성 z 충분. VIX는 지수테이블 사문이나 **RegimeSnapshot.inputs.vix 804일**로 z 산출 가능(JSON 경로). 부재=^-실지수·채권/원자재 ETF 0행이나 시장 z는 SPY+Regime으로 충족.

### D-2. Chain Sight 테마 히트(TH)
**앱 조정**: 테마 매핑 = **`services/serverless/models.py:1081 ThemeMatch`**(table serverless_theme_match), heat = `apps/chain_sight/tasks/seed_tasks.py:104`가 **Neo4j `:Stock.heat_score`** 기록(Postgres 아님).
```
ThemeMatch total 1270, distinct theme 20, last_updated 2026-03-09..08-10 (현재상태 테이블·시계열 아님)
PLTR: innovation(ARKK)/technology(XLK)   GEV: industrials(XLI)   GOOGL: communication(XLC)/innovation(ARKK)/robotics_ai(BOTZ)
TLN: 0   IREN: 0   IONQ: 0        # 전부 etf_holding high conf 근거
CompanyNarrativeTag total: 0 (전 종목 없음)
Neo4j heat 조회: GraphQueryError localhost:7687 Connection refused (Neo4j 다운)
```
**판정 — "테마 z" 산출 = 불가(현 보유분)**: ① 6종 중 3종(TLN/IREN/IONQ) 테마 0건 ② heat_score는 종목단위·Neo4j 스칼라 현재값 1개(**일자별 이력 미영속**)·현재 Neo4j 다운 ③ Postgres에 ThemeHeatScore/ThemeNewsVolume 시계열 테이블 부재(grep 0). 시계열 z 원천 불가.

### D-3. portfolio/Wallet
모델: `apps/portfolio/models.py:44 Wallet`/`:78 WalletHolding`/`:155 WalletSnapshot`, `models_my.py:52 CashBalance`.
```
Wallet 1  WalletHolding 9  CashBalance 1(USD)  WalletSnapshot 0
holdings(symbol,shares,avg_cost,fx): NVDA 1/191(fx1491.097) TSLA 1/298.2 GEV 3/1040 TLN 4/400 AAPL 10/264.59
  GOOGL 14/318.46 PLTR 10/157.39 IREN 30/63.0 IONQ 104/49.55   (6 타깃 전부 실보유 + NVDA/TSLA/AAPL)
grep realized|pnl|gain: 0건
API _holding_payload(wallet.py:45): symbol,name,currency(=stock.currency),shares,avg_cost,first_bought_at,
  acquisition_fx_rate,investment_thesis,current_price(=stock.real_time_price)   # market_value/weight/pnl 서버 미제공
```
- 평단(avg_cost)·수량(shares) 존재·노출. 통화=stock.currency 파생(전부 USD), 현금 CashBalance 통화별(USD/KRW, 현 USD 1). 매수시점환율 acquisition_fx_rate(NVDA만).
- **실현손익 저장/노출 없음** — 전용 필드·Trade 모델 부재(docstring "Phase 2 Trade 도입 시 자동 계산" 예정). 미실현도 서버 미산출(클라이언트 몫).

### D 조정 내역
- macro(추정) → 원장 `macro/`(MarketIndexPrice)·카드 `apps/market_pulse/`. chainsight/serverless → ThemeMatch=`services/serverless`, heat=`apps/chain_sight`가 Neo4j 기록.

### D 이상 관측 (좌표만)
- **VIX 이중 원장 불일치**: `^VIX` 지수테이블 6행·2026-02-26 정지(사문) ↔ 살아있는 VIX=RegimeSnapshot.inputs.vix(804일). ^-실지수 계열(^GSPC/^IXIC/^DJI/^VIX/^FTSE/^HSI/^N225·^GDAXI) 전부 2025-12~2026-02 6행 정지=적재 파이프라인 끊긴 잔재.
- 지수 커버리지 공백: TLT·GLD·SLV·VEA·UUP 등록만·0행.
- **테마 heat 시계열 부재(구조적)** + Neo4j 다운(:7687) + CompanyNarrativeTag 0행 → 테마 z 원천 불가.
- 테마 매핑 6종 절반 공백(TLN/IREN/IONQ 0, ETF holdings 근거만이라 비ETF편입 미포착).
- 실현손익 미보존(realized P&L·Trade 모델 부재).

---

## PART E — 갭 리스크 실측

_(PART E 에이전트 결과 — 채워짐)_ ⏳

---

## 산술 자기검산

PART 간 교차 정합(전부 일치):
- **IndicatorReading 총합**: A-1 셀 합 = B-3 종목별 = 4,536. 검산 PLTR = 66(eod)×3 + 132+103+104+132+132+132 = 198+735 = **933** ✓(B-3 933). GEV 933·GOOGL 918(61×3+735)·TLN 612(0×3+78+25+26+161×3)·IREN 528(+133×3)·IONQ 612. 합 933+933+918+612+528+612 = **4,536** ✓.
- **MonitorIndicator** 54 = 6종×9지표 ✓(B-3). **MonitorSnapshot** 78 = 6×13 ✓(B-2).
- **E-1 POOL6 gap rows** = PLTR777+TLN276+GEV596+GOOGL777+IREN276+IONQ276 = **2,978** ✓.
- **DailyPrice distinct** 747 (A-5 = E-1) ✓. **6종 심도** A-1/A-5/B-3/E-1 전부 778/778/597/277/277/277 정합 ✓.
- **EODSignal vs IndicatorReading eod_composite 차이 설명됨**: EODSignal 행수(PLTR 78·GOOGL 67)와 IndicatorReading eod_composite(66·61)와 B-4 z_n(61·56)이 다른 이유 = Reading은 2026-03-29부터(66일), z는 is_sufficient warmup 차감. 모순 아님.
- **뉴스 A-4 vs 구 A-4 정정**: 구 관측 "TLN 0행"은 `entities__source='alpha_vantage'` 필터 한정, 경로 무관 실측 = 5건. 오류 아닌 필터 범위 차.

## 미해결·이상 관측 (수리 금지, 좌표만 — 계획 세션 회부)

| # | 관측 | 좌표 | 출처 |
|---|---|---|---|
| ⅰ | **6종 전부 status=setting_up** (memory "6종 active" 불일치) | monitor_monitor.status | A-1·B-1 |
| ⅱ | **Monitor.status 자동 전이 코드 0건** — setting_up→active 경로 부재, 전이 이력/감사 테이블 부재, 수동 PATCH만 가능 | apps/monitor 전역·serializers.py:305 | B-1 |
| ⅲ | **상태 3원화** (status 고착 / current_state active / MonitorSnapshot.state 일별) — status 필터가 setting_up을 활성 취급 | state_machine.py:43,59·evaluate_monitors.py:34 | B-1 |
| ⅳ | **비SP500 3종 EODSignal 영구 공백** (지표 1~3 × 3종 = 9셀 0행), warning 로그만 | sp500_eod_service.py(SP500 only)·ingest.py:81 | A-2 |
| ⅴ | **GOOGL EODSignal stale** (SP500인데 최신 08-11, 타 08-13) | stocks_eod_signal(GOOGL) | A-3 |
| ⅵ | **overall_score 이력 얕음(13일) vs 지표 raw 깊음(~132일)** — 노이즈 플로어 overall_score로는 표본 부족 | MonitorSnapshot(78행) | B-3·B-4 |
| ⅶ | **z 노이즈 이상치**: PLTR sma200_gap max\|Δ\|=5.32(EXTREME 5.0 초과 1회)·GEV eod_composite σ(Δ)=1.83 | B-4 재계산 (2)블록 | B-4 |
| ⅷ | **advisor 수치 대조 게이트 미구현** — lexical만 집행, 출력숫자⊆프롬프트숫자 없음 | advisor_briefing.generate_briefing | C-4 |
| ⅸ | **근거 신호 생성시점 구조 저장 부재** — Claim assertion 자유텍스트 단일 슬롯, 결합은 마감시점 ClaimIndicatorResult(0행)로만 | Claim(monitor.py:79)·closure.py:17 | C-1·C-2 |
| ⅹ | **AdvisorNote 예약필드 미노출** (market_score/close_score/tokens) + monitor 계약 테스트·contracts/ 스펙 부재 | serializers.py·contracts/ | C-5 |
| ⅺ | **현 브랜치↔origin/main 드리프트** — advisor 트랙 전체(모델·서비스·mig0009·FE) 현 체크아웃 미반영 | monorepo/sess-signal-fwd-recon | C·A |
| ⅻ | **VIX 이중 원장** — ^VIX 지수테이블 사문(6행 2026-02-26 정지) ↔ RegimeSnapshot.inputs.vix 804일 생존. ^-실지수 계열 전부 정지 | macro_market_index_price(^*) | D-1 |
| ⅹⅲ | **테마 heat 시계열 구조적 부재** + Neo4j 다운(:7687) + CompanyNarrativeTag 0행 + 6종 절반 테마 공백 | serverless ThemeMatch·chain_sight Neo4j | D-2 |
| ⅹⅳ | **실현손익 미보존** — realized P&L 필드·Trade 모델 부재(Phase 2 예정) | apps/portfolio/models.py | D-3 |
| ⅹⅴ | **6종 갭 체질 유니버스 대비 ~2.7~3배 높음** (IREN 극단 >3% 33.7%), Claim entry_price↔WatchlistItem target_entry_price 개념 중복 | stocks_daily_price·C-6 | E-1·C-6 |
| ⅹⅵ | **DailyPrice 최소 심도 1행** (747종 중 depth=1 존재·신규/오염 의심) · EODSignal 일자별 부분수집 | stocks_daily_price·EODPipeline Stage2 | A-5·A-2 |

## 수리 대장 교차표 (결함 1·3·4·5·7·8·9·10·12)

지시서 PART↔결함 매핑 기준, 각 결함의 재료 확보 상태 3값 판정:

| 결함 | PART | 주제 | 판정 | 근거·비고 |
|---|---|---|---|---|
| **1** | B | 노이즈/히스테리시스 임계 | **부분 확보** | overall_score 노이즈 플로어 = 13거래일·표본 부족(임계 데이터 도출 미달). z-score 노이즈는 raw 재계산으로 충분(σ(Δ) 0.4~0.7 대역). 히스테리시스를 z 기반으로 설계 시 확보, overall_score 기반이면 이력 축적 대기(스냅샷 백필 필요). |
| **3** | B | IC 패널(일별 z 단면) | **재료 확보** | IndicatorReading raw로 z 시계열 소급 재구성 가능 — technical 5종 ~132거래일(2026-02~), market_data 3종 ~66거래일(GEV/GOOGL/PLTR만). 6종 공통 technical-only 패널 ~2월초, market_data 포함 3종 ~3월말. |
| **4** | D | 인접 렌즈 — 시장 성분(3단 분해) | **재료 확보** | 시장 z = SPY 794거래일(~3년 OHLCV) + VIX(RegimeSnapshot.inputs.vix 804일). 시장·변동성 성분 산출 가능. (실지수 ^GSPC 등은 사문이나 SPY로 대체.) |
| **5** | A | 유니버스 폭·심도(기저율) | **재료 확보** | DailyPrice 747종·중앙 778거래일(~3년), 6종 depth 778/778/597/277/277/277. 기저율 버킷·IC 패널 지반 = 최대 3년×747종(6종 공통은 ~277일 하한, TLN/IREN/IONQ 2025-07~). |
| **7** | C | serializer 노출 계약 | **재료 확보** | MonitorSerializer/ClaimSerializer/AdvisorNoteSerializer 노출 필드 전수 확보. FE 실소비 필드(types/monitor.ts) 매핑. ⚠️ 계약 테스트·monitor-api.yaml 부재(감지망 없음) = 결함 실체 확인. |
| **8** | B | 노이즈 플로어(신호/잡음 경계) | **부분 확보** | 결함 1과 동일 재료. z 기반 노이즈 플로어는 실측 확보(지표별 σ(Δ)·p95·max 표), overall_score 기반은 표본 부족. eod_composite는 3종(TLN/IREN/IONQ) 표본 없음. |
| **9** | D | 인접 렌즈 — 테마 성분(3단 분해)·진단 자동화 | **불가** | 테마 z 산출 원천 부재: heat_score = 종목단위·Neo4j 스칼라 현재값 1개(일자 이력 미영속), 현재 Neo4j 다운(:7687), Postgres 테마 시계열 테이블 없음, 6종 중 3종 테마 매핑 0건. 3단 분해의 테마 성분·진단 규칙 자동화 전제 미충족. |
| **10** | E | 갭 리스크 | **재료 확보** | DailyPrice open_price 존재 → 6종 갭 분포 실측(p50/p90/p99·>3%·>5%) + 유니버스 30종 대조. 6종 갭 체질 유니버스 대비 ~2.7~3배(IREN 극단). FMP EOD도 OHLC 완비(A-3)로 실시간 갭 감시 가능. |
| **12** | C | Claim 스키마·빌더 v0 절단면 | **재료 확보(스키마 확장 필요)** | Claim 가격 필드(entry/target/stop/deadline) 실재·마이그 이력·빌더 4단 위저드·근거신호 UI 삽입지점·터치파일 목록 확보. ⚠️ 근거 신호 구조 저장 필드 부재 → v0가 "근거 원장"을 요구하면 Claim 스키마 additive 확장(ClaimIndicatorResult 유일제약 확장 포함) 선행 필요. |

**교차표 요약**: 재료 확보 6건(3·4·5·7·10·12) / 부분 확보 2건(1·8, overall_score 이력 얕음이 공통 병목 — z 재계산으로 우회 가능) / 불가 1건(9, 테마 z = 구조적 원천 부재 + Neo4j 다운). 9건 중 **8건이 착수 가능**(1·8은 z 기반 설계 또는 스냅샷 백필 축적 후), 결함 9만 별도 인프라(테마 시계열 영속화 + Neo4j 복구) 선결.

---

_보고서 끝. 전항 읽기 전용 — DB 쓰기·마이그레이션·beat·배포·브랜치 삭제 0. 외부 API = FMP 10콜(A-3). 산출물 = 본 파일 1건._

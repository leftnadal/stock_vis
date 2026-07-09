# DECISIONS.md — 아키텍처 결정 로그

> 에이전트는 구현 전 이 파일을 확인하고, 기존 결정과 충돌하는 작업은 수행하지 않는다.
> 각 결정에는 **근거(Why)**를 반드시 포함한다.
>
> **이 파일의 역할**: 아키텍처 결정의 **1차 소스**. 항목 구조 = **결정 / Why(근거) / How to apply / (해당 시) STEP 0 측정 · 검증 결과 · 머지 hash 출처**. 이 구조를 표준으로 유지한다(이미 최상위 품질 — 보존 우선).
> 함정·버그는 여기가 아니라 [`sub_claude_md/common-bugs.md`](sub_claude_md/common-bugs.md). 결정 ↔ KB 동기화: 새 결정 → 이 파일 **먼저** → `shared_kb` 큐 → 검색KB 드레인.

---

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

---

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
thesis/      — 처분 보류 (사용자 트리거 대기, monorepo 외)
```

**잔존 (monorepo 외 트랙)**:
- BOUNDARY-1/2/3 (경계 트랙 소진 큐)
- Beat prod DB 동기화 (운영 트리거, `sync_beat_schedule --apply` + beat 재시작)
- thesis 처분 (a/b/c 트리거 대기)
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
섹터 원본으로 active=True 승격**(순수 테마 ETF 7행 SOXX/SMH/SOXL/QQQ/TQQQ/ITA/ERX 는 불변).
**상충 재분류**: §2 "레버리지÷원본" 산식과 §6.4 "섹터 SPDR 11종" 진술의 긴장은 **상충 아닌
명세 공백** — 독해 = SPDR 11종 원본 전수 + 레버리지는 존재 섹터만 + 부재 섹터 §3-5 결측.
레버리지 짝 시드·C5 계산기 배선은 **12b(TH-C5-SPDR-LEVERAGED) 비준 후**(후보 실측표 상신).

**worktree 판정**: TH-7 작업 위치 = `~/worktrees/sv-theme-heat`(브랜치 전용 트리, 공유
Desktop 트리는 세션 중 detached origin/main 이동 관측). 공유 트리 무접촉 지속. .env 는
gitignore(커밋 무영향)라 공유 트리 .env 심링크로 셋업.

**baseline at decision**: origin/monorepo/sess-cs-theme-heat = 86ddbc2. 전체 343 GREEN /
13 사전존재(attention 6 + leadership_api 7, Neo4j-env). 신규 회귀 0.

# Theme Heat 설계서 (테마 온도계 + 수요 지지 축)

- **문서 ID**: `theme_heat_design`
- **버전**: **v1.2.9** (2026-07-10) — v1.2.8 대비: **첫 온도 확정**(수기 검산 일치, Technology 60).
  H2 사전 초판(결정19=A, 검수표 671·dry-run 배정률 81.3%·원장 미적용). backfill --force 제거(TH-12
  판정). HALTED-3 판정(기존 DB 오염, FMP 정본). §2 산식·부호 불변.
- **버전(이전)**: **v1.2.8** (2026-07-10) — v1.2.7 대비: **C3 토큰 매칭 가동(결정17 1차 규칙)** →
  **첫 온도 4테마 산출**(Technology 60·Financial Services 63·Energy 57·Consumer Cyclical 45,
  주의 밴드). HALTED-8 정본 통일(결정18=A, 통과 5종 교체·재정지 3종). H2 부록(§부록 A) 박제.
  ★C3 미배정 57.2%>40% → TH-C3-LLM-DICT 상신. §2 산식·부호 불변.
- **버전(이전)**: **v1.2.7** (2026-07-09) — v1.2.6 대비: **C1·C3 배선(8성분 전건 배선, _NOT_WIRED=())**.
  C1(결정15=A: EV/Sales = enterprise-values[quarter] ÷ income revenue, 동일 fiscal_date 정합) +
  C3(결정16=A: ThemeNewsVolume 테마×일자 집계, 완전 일치 매칭, 결정13 동형 게이트). §2 C3 집계
  규칙 보완 명세(아래). C3 완전 일치 실효성 0(다단어 문구) → 매칭 확장 상신. present 5/결측 3.
- **버전(이전)**: **v1.2.6** (2026-07-09) — v1.2.5 대비: **C6/C7 활성**(결정14=A DailyPrice 3년 백필
  364,827행/487종목, 게이트 자연 해제 present 전환) + **C1·C3 원천 상신**(C1=ratios/key-metrics
  402 유료벽, C3=DailyNewsKeyword 5개월+섹터 집계 부재 → 배선 정지, 우회 금지). 8성분 present
  4(C2·C5·C6·C7)/결측 4(C1·C3 상신·C4 게이트·C8 주간). §2 산식·부호 불변.
- **버전(이전)**: **v1.2.5** (2026-07-09) — v1.2.4 대비: **C4 콜드스타트 게이트**(결정13=C: diff<26
  결측 / 26≤diff<60 확장 창 time_series_expanding / ≥60 정식 time_series, 상수 26/60=결정7 체계
  병기, 횡단 z 기각) + **C6/C7 배선**(구성종목 DailyPrice 3년 커버 게이트). 조립기 _NOT_WIRED =
  C1·C3 만 잔여. C6/C7 활성 = DailyPrice 3년 백필(stocks 도메인, 상신). §2 산식·부호 불변.
- **버전(이전)**: **v1.2.4** (2026-07-09) — v1.2.3 대비: §6.4 C5 레버리지 짝 **확정 매핑 9종 명문화**
  (결정12b=A: 유동성 하한 20일 중위 거래대금 ≥ $1M · 배율 3x 우선+2x 대체 · XLB·XLC 결측 확정).
  C5 **풀배선 완료**(레버리지 시드 0021 + EtfDailyBar 거래량 3년 백필 + c5_speculation_from_db
  fetch + 조립기 _NOT_WIRED 에서 C5 제거). §2 C5 산식 불변.
- **버전(이전)**: **v1.2.3** (2026-07-09) — v1.2.2 대비: §6.4 명세 공백 해소(결정12a) — Cycle 1
  C5 "섹터 SPDR 11종"을 **원본 전수(role=primary, active=True)로 확정**(XLK/XLF/XLE/XLV/XLI/
  XLY/XLP/XLU/XLB/XLRE/XLC), **레버리지 짝은 존재 섹터만·부재 섹터는 §3-5 결측**으로 정합화
  (§2 C5 산식과 §6.4 진술 = 상충 아닌 공백 판정). §7에 C4 원료 스냅샷 beat(EtfSnapshot) 추가.
  C4 산식은 미배선(FMP shares_out 이력 부재 → 원료 축적, TH-C4-COLDSTART 대기). §2 산식 불변.
- **버전(이전)**: **v1.2.2** (2026-07-08) — v1.2.1 대비: §5.3 z_mode 전환을 종목별·유효 EPS diff
  카운트 기반(≥26→time_series)으로 개정(결정7 비준, TH-4 C8 구현 발견). §2 C8 산식 불변(앵커).
- **버전(이전)**: **v1.2.1 FINAL** (2026-07-06) — v1.2 대비: TH-1 구현 발견 정정 2건 —
  §6.6 unique_together = (symbol, snapshot_date, fiscal_year) 3튜플로 정정(fiscal_year
  복수 행 정합), §6.4 = Cycle 1 C5 주 데이터 섹터 SPDR 11종 + 테마 ETF 9행 비활성 보존
  (레인 개방 후 원 테마 복원). v1.2 대비: §6.1/6.3/6.4 외부 참조("v1.0과 동일")를
  필드 표 인라인으로 교체(**자기완결화** — v1.0 은 파일로 존재하지 않음), TH-1 마이그레이션
  전략을 동승 → **독립**으로 전환(마켓 뷰 PR-1 미착수 실측 반영). 측정 단위 = HeatEntity
  (§12-1 C안), 데이터 전제 = 3종 프로브 전건 검증
- **상태**: 확정 — 변경은 본 문서 선수정 → PR 후속의 순서로만 (개정 시 버전 증가)
- **소유 도메인**: Chain Sight (단일 작성자 규칙 적용)
- **관련 결정**: DECISIONS.md `[2026-07-04] FMP Starter 내부자 채택`, `[2026-07-04] 온도계 트랙 귀속 = 위임 + 설계서 앵커(C안)`
- **관련 문서**: `seed_node_design.md`, `ui_ux_design.md`, `api_design.md`, `docs/audits/fmp_insider_access_report.md`

---

## 0. 요약

테마 단위의 **2축 상태 시스템**:

- **Heat Score (과열 축, 0~100, 일간)** — "가격·심리가 얼마나 쏠렸나". 8성분 z-score 가중합.
- **Demand Support Score (DSS, 수요 축, 0~100, 주간)** — "펀더멘털이 받쳐주나". 테마별 수요 프록시 가중합.

두 축은 직교하며 **하나의 점수로 합산하지 않는다** ("과열+수요 견조"와 "과열+수요 이탈"은
투자 판단이 정반대). 계산·저장은 Chain Sight 도메인 단일 소유, 소비는 ①Chain Sight 마켓 뷰
섹터 버튼바(**온도 단일** — 판독 속도 우선), ②Market Pulse 카드(**2축 + 사분면 evidence**).
신규 유료 소스 0 — FMP Starter + 뉴스 파이프라인 + FRED + CBOE 공개 데이터.

출시 순서 (B안 확정): **Cycle 1 = Heat 8성분** → **Cycle 2 = DSS** (Heat의 z 계산기·결측
재분배·beat 골격 재사용). 카드 UI는 Cycle 1부터 2축 레이아웃으로 만들고 DSS 열은 "수집 중"
상태로 출시해 재작업 제거.

## 1. 소유권과 소비처

| 역할                   | 주체                                      | 규칙                                           |
| ---------------------- | ----------------------------------------- | ---------------------------------------------- |
| 스키마·배치·API (쓰기) | Chain Sight 도메인                        | 단일 작성자. `register_chainsight_beats` 패턴  |
| 버튼바 게이지 (읽기)   | Chain Sight 마켓 뷰 FE                    | Heat만 표시 (0.5초 판독 공간, 2지표 과밀 금지) |
| 2축 카드 (읽기)        | Market Pulse 대시보드 FE                  | Heat + DSS + 사분면 evidence                   |
| 주간 교차검증 훅       | **SEC β verify 레이어** (본 설계 범위 밖) | §8                                             |

## 2. Heat Score — 8성분 (Cycle 1)

가중치 산정 원칙: 평균회귀 근거 강도 > 직교성 > 선행성. 합 = 1.00.

| #   | 성분               |   가중치 | 원천                  | 산식 요지                                                             |
| --- | ------------------ | -------: | --------------------- | --------------------------------------------------------------------- |
| C1  | 밸류에이션 z       | **0.18** | FMP                   | 구성종목 EV/Sales·Fwd P/E 중앙값의 3년 z                              |
| C2  | 공급 반응 (복합)   | **0.18** | FMP insider + filings | 내부 배분: C2a 내부자 0.12 + C2b 발행 0.06 (§5)                       |
| C3  | 내러티브 볼륨      | **0.14** | `DailyNewsKeyword`    | 테마 키워드 언급량 20일 합 z                                          |
| C4  | ETF 플로우         | **0.12** | FMP (근사)            | Σ(Δshares_out × NAV) 20일 이동합 z                                    |
| C5  | 투기 심리          | **0.12** | FMP (T1)              | 레버리지÷원본 ETF 거래량 20일 z                                       |
| C6  | 상관 응집          | **0.09** | 가격                  | pairwise rolling Pearson(60일) 평균 z — Layer C 재활용                |
| C7  | 거래대금           | **0.09** | FMP                   | 테마 합산 거래대금 20일 z                                             |
| C8  | 추정치 리비전 괴리 | **0.08** | FMP estimates         | 주가 60일 수익률 z − EPS 컨센서스 60일 변화 z (양수=멀티플 단독 팽창) |

배점 근거: C1·C2 공동 최상(멀티플 평균회귀 + "종이 공급"의 고점 신뢰도), C3 선행성 중상,
C4·C5 직교 프록시, C6·C7 확인성, C8은 커버리지 결손(중소형) 리스크 반영해 최하 배점 —
v1.0의 제외 근거였던 "C4 중첩"은 재검토 결과 기각(C4=돈의 이동, C8=펀더멘털 확인 부재로
측정 대상 상이), 커버리지 문제는 §3-6 결측 재분배로 처리.

보조 지표 (가중합 밖): T0 지수 프록시 — VIX·VXN·OVX·SKEW, CBOE put/call. 카드 툴팁 배경용.

**C1 밸류에이션 조합 (결정15=A, v1.2.7)**: EV/Sales = FMP enterprise-values(**period=quarter**)
÷ income-statement(quarter) revenue. **시점 정합 정본**: EV.date == income.date 동일 fiscal_date
강제(라벨 불일치·미발표 미저장, 추정·대체 금지). 원장 QuarterlyValuation. 섹터 EV/Sales 중앙값의
분기 3년 z(min_n 8분기). Fwd P/E 레그는 결정15 범위 밖(EV/Sales 단독). ★enterprise-values 는
period 미지정 시 연간 → quarter 명시 필수.

**C3 집계 규칙 (결정16=A + 결정17 1차 규칙, v1.2.8)**: 테마별 일간 mention_count =
DailyNewsKeyword search_terms_en 정규화(소문자·공백) 후 테마 키워드 시드(news
`KEYWORD_SECTOR_MAP`)와 **토큰 매칭** — 단일 단어 시드는 검색어 토큰 완전 일치, 다단어 키워드는
구 포함 일치, **부분 문자열·유사도 금지**. → 섹터명 → HeatEntity(11 GICS 매핑) 합산(원장
ThemeNewsVolume). 게이트 = 결정13 동형. 3년 외부 백필 금지(전방 축적 + 소급). ★1차 규칙 배정
42.8%/미배정 57.2% → **승격 트리거(미배정>40%) 초과 → H2(§부록 A) 상신**(TH-C3-LLM-DICT).

**C4 콜드스타트 게이트 (결정13=C, v1.2.5)**: FMP shares_out 이력 부재로 C4 z는 EtfSnapshot
축적 위 **시계열 전용**(횡단 z 기각 — n=11 통계 부적격). 종목별 유효 diff: <26 → 결측
(`c4_insufficient_history`) / 26≤diff<60 → 확장 창(window=min(이력,60), `time_series_expanding`)
/ ≥60 → 정식 60 창(`time_series`). 상수 26/60 = 결정7 체계 병기(반년 표본 하한·정식 창).
**C6/C7**: 구성종목 DailyPrice 3년 커버 미달 시 `c*_insufficient_history`(백필 도달 시 자동 활성).

## 3. 합성 규칙 (양 축 공통 골격)

1. 성분별 z (lookback §2/§4 표 기준, 분모 = 3년 히스토리 σ).
2. 시그모이드: `s_i = 1/(1+exp(-z_i))`.
3. 가중합 → ×100 → round.
4. Heat 밴드: 과열 ≥70 / 주의 40~69 / 냉각 <40.
   DSS 밴드: 지지 ≥60 / 중립 40~59 / 이탈 <40.
5. 결측: 가중치 비례 재분배 + `missing_reason` 기록. Heat 결측 ≥3 또는 DSS 결측 = 전 성분이면
   해당 축 미산출.
6. 사분면 판정 (카드 evidence용): 과열×이탈=`경계`, 과열×지지=`관리`, 냉각×지지=`역발상 후보`,
   냉각×이탈=`관망`. 주의 밴드는 사분면 문장 미생성.

## 4. Demand Support Score — 수요 축 (Cycle 2)

"capex는 AI 인프라의 수요 프록시일 뿐, 테마마다 대응물이 있다"(최초 논의)의 구현.
**공통 골격 + 테마별 오버라이드** 구조. 테마별 가중치 합 = 1.00.

### 4.1 공통 골격 (제조·기술형 테마 기본값)

| 성분                    | 가중치 | 원천                           | 산식 요지                                         |
| ----------------------- | -----: | ------------------------------ | ------------------------------------------------- |
| D1 capex 성장           |   0.40 | FMP 현금흐름표                 | 구성종목 capex TTM YoY 중앙값의 z                 |
| D2 재고일수(DIO) 역방향 |   0.35 | 1차 검증 Inventory 로직 재사용 | 테마 합산 DIO z의 부호 반전 (재고 쌓임=수요 이탈) |
| D3 매출 성장            |   0.25 | FMP                            | 매출 TTM YoY 중앙값 z                             |

### 4.2 테마별 오버라이드

| 테마             | 구성 (가중치 합 1.00)                               | 원천             | 비고                                                   |
| ---------------- | --------------------------------------------------- | ---------------- | ------------------------------------------------------ |
| AI 반도체/인프라 | 공통 골격 + [backlog **결측 예약**]                 | FMP / (SEC β 후) | backlog 편입 시 D1 0.30/D2 0.30/D3 0.20/D4 0.20 재배분 |
| 방산/항공        | D1 0.35 / D3 0.35 / [RPO 결측 예약 0.30→재분배]     | FMP / (SEC β 후) | RPO·backlog는 주석 파싱 — §13                          |
| SaaS             | D3 0.60 / D1 0.40                                   | FMP              | RPO·billings·NRR은 결측 예약                           |
| 은행/금융        | NIM 프록시(순이자마진) 0.60 / 금리커브(10Y-2Y) 0.40 | FMP / FRED       | FRED 백본                                              |
| 소비재           | 소매판매 0.55 / 소비자신용 0.45                     | FRED             |                                                        |
| 클린에너지       | D1 0.50 / 원자재·정책 0.50                          | FMP / FRED·뉴스  | 정책 성분은 뉴스 키워드 재사용                         |
| 바이오           | **DSS 미산출 (결측)**                               | —                | 임상 단계는 정형화 불가 — §13                          |

결측 예약 = 성분 슬롯과 재배분 규칙을 지금 정의하되 데이터는 SEC β 이후 (§3-5 결측 처리로
그때까지 자동 재분배).

## 5. C2 공급 반응 — 복합 성분 상세

### 5.1 C2a 내부자 (배분 0.12) — FMP E1/E2 (검증 PASS 확정)

v1.0 §5 규칙 전체 승계:

- E1/E2 거래 레벨로 90일 rolling 자체 집계, E3는 분기 대조 sanity check(±10%)와 백필 보조.
- 방어 필터: transaction_type 공란 제외 / 매도=S-Sale·매수=P-Purchase만(A-Award·M-Exempt·
  F-InKind·G-Gift 제외) / 금액 가중 시 price=0 제외 / type_of_owner 가중(officer·director
  1.0, 10%주주 0.7, 간접 0.5).
- 산식: `net_sell_ratio_90d = Σ(매도금액×가중)/(Σ매도+Σ매수 금액×가중)` 테마 합산, 3년 z.
- 백필 3년, dedup_key = hash(symbol, reporting_cik, transaction_date, transaction_type,
  securities_transacted, price), upsert 멱등. `backfill_insider_transactions` 커맨드(1회성).
- **저장 = 원천(FMP) 전체 이력, 집계 창 = 스펙대로**(v1.2.1): FMP 는 종목 전 이력을 반환하고
  저활동 종목은 페이지에 담긴 전 이력(예: 2011~)이 그대로 적재된다(cutoff 는 페이지 순회
  중단만 제어). 3년 이전 데이터도 z-히스토리 자산으로 **유지**하고, 90일 rolling 등 집계 창은
  스펙대로 적용한다. 단 미래 거래일(>오늘)은 원천 이상치로 적재 단에서 컷(TH-INSIDER-DATE-SANITY).

### 5.2 C2b 발행 (배분 0.06) — filing 메타데이터 카운팅 (G1 PASS + 검증 라운드 재정의, 2026-07-05)

**본문 파싱 아님** — 폼타입·날짜·심볼 카운팅만.

**성분 재정의 (검증 발견 반영)**: 지시서 2호 검증에서 S-1 패밀리·424B4의 symbol 결측이
60~62%로 실측됨 — S-1/424B4 는 주로 IPO 이전 기업(티커 미부여)의 서류이고, 기상장사
유상증자는 미국 공시 체계상 **S-3 선반등록 + 424B5** 경로를 쓴다. 따라서 S-1/424B4 는
증자 신호로 부적합(오선정)이며, 신규 공급은 IPO 캘린더(symbol 결측 0%)가 상장 시점에
회수한다. C2b 를 다음 두 직교 하위 신호로 재정의한다 (이중 계상 원천 소멸):

- 신호 = [**기상장사 2차발행**: 424B5 90일 건수 z] + [**신규 공급**: IPO 캘린더 90일
  건수 z] 의 평균.
- **G3 확정 (지시서 3호 PASS, 2026-07-05, 4콜)**: 424B5 OPEN·오염 0%·symbol 커버리지
  90%(임계 85% 상회)·3년 백필 동작 — 재정의 가설 실증 완료, FAIL 분기(IPO 단독 축소) 폐기.
  symbol 결측분(~10%)은 카운트 제외하고 결손률을 components 에 기록 (귀속 불가분의
  침묵 유입 방지).
- **424B2 는 제외 확정**: 은행 구조화상품·MTN 발행이 물량 대부분 = 주식 공급 신호 아님
  (신호 순도) + 일 100건 캡 도달로 일 단위 창 설계 파괴 (G3 실측). §13 백로그.
- S-1/424B4 는 카운트 대상에서 **폐기**. S-1 등록 시점의 1~4개월 선행성 포기는 §13
  "CIK→SIC 선행 신호 트랙"으로 이관 (재소환 조건 명시).

**원천 = FMP 단일**: `sec-filings-search/form-type` + `ipos-calendar`. EDGAR 폴백 불요
(지시서 2호 Track A PASS — `docs/audits/fmp_filings_estimates_probe_report.md`).

**수집 규칙 (프로브 실측 단서 반영)**:

1. form-type 필터는 prefix 매칭 → 소비 측 `formType` **정확 일치 자체 필터** 필수
   (S-1 검색에서 오염 실측. 424B5 는 G3 에서 오염 0 확인 — 필터는 방어 목적으로 유지).
2. 응답 ~100건 캡 → 페이지네이션 가정 금지, **일 단위 날짜 창 순회**로 수집·백필
   (G3 실측: 424B5 일 26~40건, 캡 비접촉).
3. IPO 캘린더는 광범위(2026 YTD 895건) — 실측상 NASDAQ/NYSE 98% / OTC·해외 2% →
   **거래소 필터(NYSE/NASDAQ) 적용 확정** (2% 노이즈 제거). 3년 백필 가능 확인(A5).
4. dedup_key = hash(symbol, cik, accession) — accession 은 `link` 필드에 내포.

- 8-K 증자 항목은 본문 판독이 필요하므로 **제외** (SEC β 후 §13에서 재평가).

### 5.3 C8 추정치 리비전 — 스냅샷 diff 전략 (Track B FULL 확정 + 콜드 스타트 규칙)

- **커버리지**: 전 버킷(대형/중형/소형) 100%, 차기연도 Fwd EPS 전 종목 존재 → C8 전 테마
  적용, C1 Fwd P/E 유지 (적자 소형주의 음수 EPS 는 C1 에서 EV/Sales 폴백 대상).
- **산출 구조**: FMP annual estimates 에는 리비전 타임스탬프가 없다 → 엔드포인트는
  **컨센서스 스냅샷 공급원**이고, 리비전 시계열은 우리가 **주간 스냅샷(EstimateSnapshot)
  → 60일 diff** 로 생성한다.
- **콜드 스타트 (B안 확정)**: 리비전 히스토리는 백필 불가(과거 컨센서스는 재구성 불능).
  1. 스냅샷 축적 60일 도달 → C8 을 **크로스섹셔널 z**(당일 전 테마의 리비전 괴리 분포
     내 위치)로 가동. 그때까지는 §3-5 결측 재분배.
  2. diff 히스토리 365일 도달 → **시계열 z**(자기 역사 대비)로 전환. 전환은 1회,
     components JSONB 의 `z_mode` 필드(cross_sectional / time_series)로 감사 기록.
  3. evidence 템플릿 분리: cross_sectional 기간엔 "테마 간 상대 +N위/σ" 표현 사용.

> **[v1.2.2 개정 — 결정7 (2026-07-08 비준), 위 1·2 대체]** z_mode 전환은 시스템 전체·시간
> 기반(60/365일 1회)이 아니라 **종목별·유효 EPS diff 카운트 기반**으로 확정한다: 종목의 유효
> EPS diff **≥ 26 → time_series**, 미만 → **cross_sectional**(양 레그 공동). diff 정의 = 현재 vs
> lag 8(56d) 스냅샷, lag 8 부재 시 lag 9(63d) 폴백. cross_sectional 단면(양 레그 성립 종목)
> < 30 → 그 날짜 C8 전체 None. 근거: 수집 결손·신규 상장 자동 내성. 상세 = DECISIONS
> [2026-07-08] Theme Heat C8. **C8 산식(§2 `z(가격60d) − z(EPS60d변화)`)은 불변** — 앵커 유지.

## 6. 데이터 모델

**TH-1 독립 마이그레이션**으로 생성 (동승 전략은 마켓 뷰 PR-1 미착수 실측으로 폐기 — §14).
Django 앱 경로 = `apps/chain_sight`.

### 6.0 HeatEntity (측정 단위 — §12-1 C안 확정, 2026-07-05)

온도의 단위를 가리키는 얇은 추상 계층. Heat/DSS 의 theme_id 는 이 테이블의 FK.

| 필드               | 타입    | 비고                                                    |
| ------------------ | ------- | ------------------------------------------------------- |
| kind               | varchar | `sector` \| `theme` — **Cycle 1 은 sector 11행만 시드** |
| ref_id             | varchar | sector: GICS 섹터 키 / theme: (미래) 테마 노드 식별자   |
| constituent_policy | varchar | sector: `static` / theme: (미래) `monthly_frozen`       |

**잠금장치 (설계 강제)**:

1. 필드는 위 3개를 초과하지 않는다 (과설계 방지).
2. `kind=theme` 로직은 Cycle 1~2 에서 **구현 금지** — 행 자체를 만들지 않는다.
3. 테마 레인 개방 게이트 = 온도계 6개월 백테스트 통과 (§13). 개방 시 **월 1회 구성 동결**
   (월초 그래프 구성 스냅샷 확정 → 월중 불변 → 변경은 월 경계 이벤트로 기록)이 필수 동반
   조건 — HAS_THEME 은 살아 움직이는 것이 정상 작동이므로, 직접 참조가 아닌 동결 스냅샷
   참조로만 온도계에 연결한다 (z 히스토리 보호).

### 6.1 ThemeHeatScore

| 필드       | 타입            | 비고                                                                             |
| ---------- | --------------- | -------------------------------------------------------------------------------- |
| theme_id   | FK → HeatEntity | §6.0                                                                             |
| date       | date            | unique_together (theme_id, date)                                                 |
| score      | smallint        | 0~100                                                                            |
| status     | varchar         | overheated / warning / cool                                                      |
| components | JSONB           | 성분별 {z, s, raw, missing_reason} 8건 — C2 는 C2a/C2b 분리, C8 은 `z_mode` 포함 |
| evidence   | JSONB           | 근거 한 줄 생성용 상위 기여 성분 2건 (§10.3)                                     |
| created_at | timestamptz     |                                                                                  |

### 6.2 ThemeDemandScore (신규, Cycle 2)

| 필드            | 타입               | 비고                                          |
| --------------- | ------------------ | --------------------------------------------- |
| theme_id / date | FK / date          | unique_together. 주간(금요일 기준일)          |
| score / status  | smallint / varchar | supported / neutral / detached / not_computed |
| components      | JSONB              | 테마별 오버라이드 구성 그대로 기록            |
| created_at      | timestamptz        |                                               |

### 6.3 InsiderTransactionRecord (C2a 원장)

| 필드                                             | 타입           | 비고                                                                                                   |
| ------------------------------------------------ | -------------- | ------------------------------------------------------------------------------------------------------ |
| symbol                                           | varchar        |                                                                                                        |
| reporting_cik / company_cik                      | varchar        |                                                                                                        |
| filing_date / transaction_date                   | date           |                                                                                                        |
| transaction_type                                 | varchar        | S-Sale, P-Purchase, A-Award, M-Exempt, F-InKind, G-Gift, 공란 — **전건 보존**, 필터는 집계 계층 (§5.1) |
| securities_transacted / price                    | numeric        |                                                                                                        |
| type_of_owner / direct_or_indirect / acq_or_disp | varchar        | 노이즈 필터·가중 소재                                                                                  |
| sec_url                                          | text           | SEC 원문 — 교차검증 훅(§8)·감사 추적용                                                                 |
| raw                                              | JSONB          | FMP 응답 원본                                                                                          |
| dedup_key                                        | varchar unique | hash(symbol, reporting_cik, transaction_date, transaction_type, securities_transacted, price)          |

### 6.4 ThemeEtfMap (C4·C5 매핑)

| 필드            | 타입            | 비고                                        |
| --------------- | --------------- | ------------------------------------------- |
| theme_id        | FK → HeatEntity |                                             |
| etf_symbol      | varchar         |                                             |
| role            | varchar         | primary(C4 플로우용) / leveraged(C5 투기용) |
| leverage_factor | smallint        | 1, 2, 3                                     |
| active          | bool            | 상장폐지 대응                               |

초기 시드(§12-2 검수 대기 — fixture 주석 명기): 반도체 SOXX/SMH + SOXL, 기술 QQQ + TQQQ,
방산 ITA, 에너지 XLE + ERX, 헬스케어 XLV. 레버리지 ETF 부재 테마는 C5 결측 처리(§3-5).

**v1.2.1 정정 (§6.0↔§6.4 세분도 해소)**: Cycle 1 의 C5 주 데이터는 **섹터 SPDR 11종**으로
하고, 위 테마 ETF 9행은 **비활성(active=False, 레인 개방 대기)으로 보존**한다. 테마 세분은
테마 레인 개방(§6.0 잠금장치 3) 후 **원 테마 단위로 복원**한다 — ThemeEtfMap 9행은 원
테마명(반도체/기술/방산/에너지/헬스케어)을 시드 상수(committed)에 보존해 복원 가능성을
지킨다(모델 필드 미추가 = §6.0 잠금 준수). 섹터 SPDR 시드 11행 추가는 **C5 구현 PR**에서
수행(TASKQUEUE `TH-C5-SPDR-SEED`).

**v1.2.3 확정 (결정12a, TH-7c)**: 섹터 SPDR 11종 원본 = **XLK(Technology)·XLF(Financial
Services)·XLE(Energy)·XLV(Healthcare)·XLI(Industrials)·XLY(Consumer Cyclical)·XLP(Consumer
Defensive)·XLU(Utilities)·XLB(Basic Materials)·XLRE(Real Estate)·XLC(Communication Services)**
— HeatEntity kind=sector 11행(GICS 정본)과 1:1. `role=primary, active=True`로 시드
(migration 0018, FMP 프로브 11/11 존재+3년 이력 통과). ⚠️ XLE·XLV 는 0016 테마 ETF 9행에
active=False 로 이미 존재 → 섹터 원본으로 **active=True 승격**(순수 테마 ETF 7행 불변).
**레버리지 짝(C5 분자)은 존재·유동성 있는 섹터만 별도 시드(`TH-C5-SPDR-LEVERAGED`=12b 비준
대기), 부재/저유동 섹터는 §3-5 결측** — §2 "레버리지÷원본" 산식과 "SPDR 11종" 진술의 세분도
공백을 이렇게 정합화(상충 아님). C5 계산기 배선은 12b 비준 후.

**v1.2.4 확정 (결정12b=A, TH-7d) — 레버리지 짝 매핑 정본** (migration 0021, role=leveraged,
active=True). 선정 규칙: **유동성 하한 = 20일 중위 거래대금 ≥ $1M**(미만·부재 섹터는 §3-5
결측), **배율 = 3x(Direxion) 우선 + 3x 부재·부적격 섹터 2x(ProShares) 대체**. 값 = TH-7c 12b
FMP 실측(감사용 `measured_liquidity_usd` 저장, 자동 갱신·보정 없음):

| 원본 | 레버리지 | 배율 | 실측 20d중위($) |     | 원본 | 레버리지 | 배율 | 실측 20d중위($) |
| ---- | -------- | ---- | ---------------- | --- | ---- | -------- | ---- | ---------------- |
| XLK  | TECL     | 3x   | 218.3M           |     | XLU  | UTSL     | 3x   | 4.9M             |
| XLF  | FAS      | 3x   | 89.2M            |     | XLI  | DUSL     | 3x   | 2.0M             |
| XLE  | ERX      | 2x   | 30.9M (승격)     |     | XLY  | WANT     | 3x   | 1.1M             |
| XLRE | DRN      | 3x   | 13.5M            |     | XLP  | UGE      | 2x   | 1.4M             |
| XLV  | CURE     | 3x   | 10.0M            |     |      |          |      |                  |

**XLB(Basic Materials)·XLC(Communication Services) = 레버리지 결측 확정**(유동성 있는 짝 부재:
XLB=UYM $253K<하한, XLC=LTL $49K/CRDT 3년미만) → C5 = c5_no_leveraged_etf(§3-5 결측, 온도는
잔여 성분으로 산출). C5 거래량 원장 = **EtfDailyBar**(레버리지 9 + 원본 11 = 20종 × 3년),
계산 = `c5_speculation_from_db`(레버리지Σ20d vol ÷ 원본Σ20d vol 비율의 3년 z, 순수함수
`c5_speculation` 재사용).

### 6.5 ThemeFilingCount (신규, C2b)

| 필드                             | 타입                     | 비고                                                                             |
| -------------------------------- | ------------------------ | -------------------------------------------------------------------------------- |
| symbol / filing_date / form_type | varchar / date / varchar | 정확 일치 필터 통과분만: **424B5, IPO 이벤트** (S-1/424B4 는 §5.2 재정의로 폐기) |
| exchange                         | varchar                  | IPO 레코드용 — NYSE/NASDAQ 필터 검토 (§5.2-3)                                    |
| source                           | varchar                  | fmp 고정 (EDGAR 폴백 불요 확정, 필드는 이음새로 유지)                            |
| dedup_key                        | varchar unique           | hash(symbol, cik, accession) — accession 은 link 에서 추출                       |

### 6.6 EstimateSnapshot (신규, C8 원장 — §5.3)

| 필드                           | 타입           | 비고                                  |
| ------------------------------ | -------------- | ------------------------------------- |
| symbol / snapshot_date         | varchar / date | 주간(금요일)                          |
| fiscal_year                    | smallint       | 당기·차기 연도별 행                   |
| _unique_together_              | —              | **(symbol, snapshot_date, fiscal_year)** — fiscal_year 복수 행 정합 (v1.2.1) |
| eps_avg / eps_high / eps_low   | numeric        |                                       |
| num_analysts_eps / revenue_avg | numeric        | C8 신뢰 가중·보조                     |
| created_at                     | timestamptz    | 스냅샷 diff 의 시간축 = snapshot_date |

## 7. 배치 설계

| Beat                                  | 주기                         | 내용                                                                                      |
| ------------------------------------- | ---------------------------- | ----------------------------------------------------------------------------------------- |
| `compute_theme_heat_task`             | 일간, America/New_York 18:00 | E2 증분 수집 → C1~C8 → Heat upsert                                                        |
| `compute_theme_demand_task` (Cycle 2) | 주간, 토 09:00 KST           | D성분 → DSS upsert (분기 재무 기반이라 주간 충분)                                         |
| `collect_theme_filings_task`          | 일간, heat 직전              | C2b 수집 — 일 단위 날짜 창 순회 + 정확 일치 필터 (§5.2)                                   |
| `snapshot_analyst_estimates_task`     | 주간, 금 마감 후             | C8 원장 스냅샷 (§5.3) — **Cycle 1 첫 배포일부터 가동** (콜드 스타트 시계를 최대한 앞당김) |
| `snapshot_etf_metrics_task` (TH-7c)   | 일간, America/New_York 17:00 | C4 원료 스냅샷 (§2, 결정11=A) — active primary ETF(SPDR 11) shares_out·nav·aum → EtfSnapshot. heat(18:00)·filings(17:30) 앞. FMP shares_out 이력 부재 대응 축적, 산식은 TH-C4-COLDSTART 대기 |
| `aggregate_theme_news_volume_task` (TH-10) | 일간, America/New_York 17:15 | C3 집계 (§2, 결정16=A) — DailyNewsKeyword → ThemeNewsVolume 테마×일자 mention_count. 뉴스 후단·heat 이전 |

공통: 성분별 try/except 실패 격리, `register_chainsight_beats` 명시 등록(Bug #28 교훈),
ops_verify `check_last_tick_succeeded()` 대상 등록.

## 8. 교차검증 훅 경계 (SEC β 소유 — 본 설계 범위 밖)

v1.0 §8 불변: 주 1회, InsiderTransactionRecord 샘플 10건 `sec_url` 원문 대조, **필드 3개만**
(transaction_type, securities_transacted, filing_date), 알림만·자동조치 없음·확장 금지.

## 9. T2 게이트 (IV 스큐)

v1.0 §9 불변: Tradier 계좌 게이트(**G2**) 통과 시 C5(0.12)를 레버리지 비율 0.05 + IV 스큐
0.07로 분할. 실패 시 현행 유지. SEIBro 서학개미는 카드 evidence 후보 백로그.

## 10. 소비처 계약

### 10.1 버튼바 (Chain Sight 마켓 뷰) — Heat 단일

`api_design.md` 섹터 엔드포인트 필드 추가: `heat_score`, `heat_status`. DSS는 버튼바 미노출
(판독 속도 우선 — 표시 절제 원칙). 과열 테마 시드 노드 온도 링(SeedHeatScore 시각 문법 통일).

### 10.2 2축 카드 (Market Pulse)

`GET /api/market-pulse/theme-heat/` — 필드: theme, heat_score, heat_status, demand_score,
demand_status(`not_computed` = "수집 중" 표시), quadrant, evidence_line, chainsight_deeplink.
**Cycle 1부터 2축 레이아웃으로 출시** (DSS 열 "수집 중") — UI 재작업 제거.

### 10.3 evidence line — 결정론적 템플릿 (LLM 미사용)

Heat components |z| 상위 2개 + (DSS 가용 시) §3-6 사분면 문장. 예: "내부자 매도 +2.4σ ·
90일 증자 3건 — 과열이지만 capex +31% 견조: 관리 국면".

## 11. PR 매핑 표

| 작업                                                                                 | 트랙                      | Cycle | 상태                      |
| ------------------------------------------------------------------------------------ | ------------------------- | ----- | ------------------------- |
| G1 프로브: FMP sec-filings·IPO 캘린더 Starter 접근                                   | (지시서 2호, 트랙 무소속) | 0     | ✅ PASS (2026-07-05)      |
| §12-3 프로브: estimates 커버리지                                                     | (지시서 2호 Track B)      | 0     | ✅ FULL (2026-07-05)      |
| G3 프로브: 424B5 커버리지                                                            | (지시서 3호, 트랙 무소속) | 0     | ✅ PASS (2026-07-05, 4콜) |
| **TH-1 독립 마이그레이션** (6.0~6.6 전체 — Cycle 2 모델 포함 선반영, 섹터 11행 시드) | 마켓 뷰(Heat)             | 1     | ✅ (2026-07-06, 0016, 18 test GREEN) |
| 내부자 백필 + 방어 필터                                                              | 마켓 뷰 BE PR             | 1     | ✅ 완료 (2026-07-07, 백필 500/501·219,410행, BK=구조적 OPEN_EMPTY 게이트 종결, 미래일 컷) |
| 유니버스 동결(UniverseSnapshot 0017) + 성분 계산기 C1·C2a·C3~C7 (계약 통일)          | 마켓 뷰 BE PR             | 1     | ✅ 부분 (2026-07-07, C2a 백필 위 즉시 가동·C2b/C8 스텁·57 test). §6.0 잠금3 Cycle1판 |
| C2b 발행 신호 (424B5 일창 수집 + IPO 진성필터 + 계산기 + 3년 백필)                    | 마켓 뷰 BE PR             | 1     | ✅ (2026-07-08, 424B5 21,755행 오염0 + IPO 1,425행 위생·SPAC/파생/ETF 컷. IPO 레그 섹터귀속 후속) |
| estimates 스냅샷 beat (C8 콜드스타트 시계 기동)                                       | 마켓 뷰 BE PR             | 1     | ✅ (2026-07-08, snapshot_analyst_estimates_task + beat 금16:30ET enabled, 필드 8/8) |
| C8 실구현 (리비전 괴리 diff + z_mode 종목별 전환)                                     | 마켓 뷰 BE PR             | 1     | ✅ (2026-07-08, TH-4: z(가격60d)−z(EPS60d) + lag8→9 + z_mode≥26 + 단면30 가드, 22 test. v1.2.2 결정7) |
| Heat beat 오케스트레이션 — compute_theme_heat_task + collect_theme_filings_task       | 마켓 뷰 BE PR             | 1     | ✅ (2026-07-09, TH-5: 유니버스→C2·C8 배선→신시사이저→upsert·universe_stale 결정8·beat 2종 등록. C1/C3~C7 배선·소스 복구 후속. 13 test) |
| 유니버스 소스 복구 + REFRESH-ALERT (Wikipedia 결정9 B)                                | 마켓 뷰 BE PR             | 1     | ✅ (2026-07-09, TH-6: datahub 404→Wikipedia+가드+비파괴 sync·refresh/monitor beat 2종·실갱신 편입7/편출7[BK→BNY]·staleness fresh. 14 test. 결정6 해제=verifier 판정 대기) |
| C5 풀배선 (SPDR 원본 시드) + C4 원료 시계 기동                                        | 마켓 뷰 BE PR             | 1     | 🔶 부분 (2026-07-09, TH-7c: 결정12a SPDR 원본 11종 시드[0018, active primary 11·테마 ETF 7 불변·XLE/XLV 승격] + **C4 원료** EtfSnapshot[0019]·snapshot_etf_metrics_task·beat 17:00ET·스모크 11행 멱등. 12 test. **C5 레버리지 배선·C4 산식은 12b/COLDSTART 대기**) |
| C5 레버리지 시드 + 거래량 백필 + 계산기 배선 + 조립기 편입                            | 마켓 뷰 BE PR             | 1     | ✅ (2026-07-09, TH-7d: 결정12b=A 레버리지 9종 시드[0021, ERX 승격·XLB/XLC 결측] + EtfDailyBar[0020] 거래량 3년 백필 15,120행 + c5_speculation_from_db + 조립기 _NOT_WIRED 에서 C5 제거[C1/C3/C4/C6/C7 잔여]. 14 test. C4 산식만 COLDSTART 대기) |
| C4 콜드스타트 게이트 + C6/C7 배선                                                     | 마켓 뷰 BE PR             | 1     | ✅ (2026-07-09, TH-8: 결정13=C C4 게이트[diff 26/60 3분기·time_series 전용·순수함수 재사용] + C6/C7[DailyPrice 3년 커버 게이트] 배선. 조립기 _NOT_WIRED=C1·C3 잔여. 14 test. **C4 가동=EtfSnapshot 축적 자동수렴, C6/C7 활성=DailyPrice 3년 백필[stocks 도메인 상신]**) |
| DailyPrice 3년 백필(C6/C7 활성) + C1/C3 원천 상신                                     | stocks BE PR + 마켓 뷰    | 1     | 🔶 부분 (2026-07-09, TH-9: 결정14=A stocks `backfill_daily_prices`[겹침 대조 게이트·364,827행/487종목·8종목 정지 상신] → C6/C7 present 전환. **C1=402 유료벽·C3=DailyNewsKeyword 5개월+구조 부재 → 상신**[TH-C1-VALUATION·TH-C3-NARRATIVE]. 6 test. 온도 활성=C1/C3 비준 후) |
| C1 밸류에이션 + C3 내러티브 배선 (마지막 2성분, 8성분 전건)                            | 마켓 뷰 BE PR             | 1     | ✅ (2026-07-09, TH-10: 결정15=A C1[EV/Sales=EV[quarter]÷revenue 동일 fiscal_date·QuarterlyValuation 7,935행·present z=0.82] + 결정16=A C3[ThemeNewsVolume 완전일치 집계·결정13 게이트·beat 17:15ET]. **_NOT_WIRED=() 8성분 전건 배선**. 13 test. C3 완전일치 실효0→매칭확장 상신[TH-C3-MATCH-EXPAND]. present 5/결측 3 not_computed) |
| C3 토큰 매칭 가동 + HALTED-8 정본 통일 + 정비 (🌡️첫 온도)                             | 마켓 뷰 + stocks BE PR    | 1     | ✅ (2026-07-10, TH-11: 결정17 C3 토큰 매칭[0→218행·미배정57.2%→TH-C3-LLM-DICT 상신] → **첫 온도 4테마**[Tech 60·Fin 63·Energy 57·ConsCyc 45 주의밴드] + 결정18=A HALTED-8[통과5 교체 max_err0.0·재정지3] + REGISTER-6[커버리지 501/501]. 5 test. 온도 확대=C3 days≥26 테마·C4/C8 도래) |
| 버튼바 온도 게이지 + 시드 온도 링                                                    | 마켓 뷰 FE PR             | 1     | ☐                         |
| 2축 카드 (DSS "수집 중" 상태 포함)                                                   | Market Pulse FE PR        | 1     | ☐                         |
| DSS 성분 계산 + 주간 beat                                                            | 마켓 뷰 BE PR             | 2     | ☐                         |
| 카드 DSS 열 활성화 + 사분면 evidence                                                 | Market Pulse FE PR        | 2     | ☐                         |
| 주간 교차검증 훅                                                                     | SEC β verify              | —     | ☐                         |

문서 편입 규칙: 설계서 + 지시서 1·2·3호 + 프로브 보고서 **3종**(insider · filings/estimates ·
424b5)은 **TH-1** 에 docs 로 동승 (읽기 전용 지시서는 트랙 무소속 실행, 산출물은
소비 PR 편입 — DECISIONS 규칙). 권장 위치: `docs/chain_sight/theme_heat/`.

**SeedHeatScore 조율 의무**: 마켓 뷰 PR-1 착수 시, `cs_44_seed_node_heat_score.md` 의 seed
node heat 개념과 본 ThemeHeatScore 의 관계 정리 + HeatEntity 재사용 가능성 검토를 **선행
단계로 강제** — heat 개념이 두 벌 생기는 것을 차단한다.

## 12. 오픈 이슈

1. ~~테마 정의 소스~~ → **해소** (사용자 확정 2026-07-05: **C안 — HeatEntity 추상 계층 +
   섹터 11행 시드**, §6.0. 테마 레인은 §6.0 잠금장치 3건 하에 미래 개방).
2. ~~ThemeEtfMap·§4.2 오버라이드 초기값 검수~~ → ThemeEtfMap **해소**(결정12a/12b, §6.4 v1.2.4
   확정 매핑 = 원본 11 + 레버리지 9, FMP 실측 근거). §4.2 오버라이드는 Cycle 2 잔여.
3. ~~C1·C8 estimates 커버리지~~ → **해소** (Track B FULL, §5.3).
4. ~~G1 filings·IPO 접근~~ → **해소** (Track A PASS, §5.2).
5. **G2**: Tradier 계좌 개설 확인 — 사용자 액션 (Cycle 1 무관, C5 분할에만 관여).
6. ~~PROGRESS.md·TASKQUEUE.md 05:50 외부 변경~~ → **해소** (검증 라운드: 커밋 4d7ca26
   정상 문서 커밋 확인, rogue 아님·규율 위반 아님).
7. ~~G3: 424B5 커버리지 프로브~~ → **해소** (지시서 3호 PASS, 2026-07-05 — OPEN·오염 0%·
   symbol 90%·3년 백필. §5.2 재정의 확정, FAIL 분기 폐기).

## 13. 잔여 로드맵 (v1.1에서도 제외 — 근거 기록, 삭제 금지)

v1.0 §13 대비 대부분 편입 완료. 잔여 5건:

- **CIK→SIC 선행 신호 트랙**: S-1 등록은 실제 상장을 1~4개월 선행하나 티커 미부여로 테마
  귀속 불가(symbol 결측 62% 실측). EDGAR submissions 의 SIC 코드로 귀속하는 보강안은
  SIC→섹터 매핑 유지·이중 계상 방지 비용이 커서 보류. **재소환 조건**: 온도계 6개월
  백테스트에서 IPO 성분의 후행성이 실제 문제로 판정될 때.
- **424B2 (shelf takedown)**: G3 실측상 일 100건 캡 도달 + 물량 대부분이 은행 구조화상품·
  MTN 발행이라 주식 공급 신호가 아님 → 제외. **재소환 조건**: 사실상 없음 (신호 정의
  자체가 부적합) — 기록 목적 보존.
- **backlog/RPO**: XBRL 표준화 부재로 주석 파싱 필요 → SEC β 안정화 후. §4.2에 결측 예약
  슬롯과 재배분 규칙 확보됨 (편입 시 설계 변경 불필요, 데이터만 연결).
- **8-K 증자 항목**: 폼타입 카운팅으로 불충분(본문 판독 필요) → SEC β 후 C2b 확장 재평가.
- **바이오 임상 단계**: 정형화 불가 — DSS 미산출 유지, FDA 캘린더류 소스 발견 시 재평가.

## 14. DECISIONS.md 기록 초안

> **[2026-07-04] 테마 상태 시스템 v1.1: 2축(Heat 8성분 + DSS) 확정, "가능한 포함" 방향 반영.**
> Heat에 C8 추정치 리비전(0.08)·C2b 발행 신호(폼타입 메타 카운팅, 파싱 불요) 편입 — v1.0
> 보류 근거 재검토 결과 기각. 수요 프록시는 별도 축 DSS로 신설(합산 금지, 사분면 판정),
> 공통 골격 capex 0.40/DIO 0.35/매출 0.25 + 테마별 오버라이드, backlog/RPO는 결측 예약.
> 출시 순차: Cycle 1 Heat → Cycle 2 DSS (골격 재사용), 카드는 처음부터 2축 레이아웃.
> 게이트: G1 FMP filings·IPO 접근 프로브, G2 Tradier. 상세: `theme_heat_design.md` v1.1.

> **[2026-07-05] 지시서 2호 프로브 = Track A PASS / Track B FULL. C8 콜드 스타트 = B안.**
> C2b 원천 = FMP 단일 확정(EDGAR 폴백 불요) — 단 form-type prefix 오염 → 정확 일치 자체
> 필터, 100건 캡 → 일 단위 날짜 창 순회(페이지네이션 가정 금지), IPO 3년 백필 확인 +
> 거래소 필터 검토. estimates 전 버킷 100% → C8 전 테마·C1 Fwd P/E 유지. 리비전 타임
> 스탬프 부재 → C8 은 주간 EstimateSnapshot diff 로 자체 생성, 콜드 스타트는 60일 후
> 크로스섹셔널 z 가동 → 365일 후 시계열 z 전환(`z_mode` 감사 기록). 스냅샷 beat 는
> Cycle 1 첫 배포일부터 가동. 규칙 신설: 읽기 전용 지시서는 트랙 무소속 실행, 산출물은
> 소비 PR 에 docs 동승.

> **[2026-07-05] C2b 성분 재정의 (검증 라운드 발견 반영).**
> S-1/424B4 는 symbol 결측 60~62%(IPO 이전 기업) + 기상장사 증자는 S-3/424B5 경로라는
> 폼 오선정 확인 → C2b = [기상장사 2차발행 424B5 계열(G3 게이트)] + [IPO 캘린더(거래소
> > 필터 NYSE/NASDAQ 확정)] 로 재정의, S-1/424B4 폐기, 이중 계상 원천 소멸. S-1 선행성은
> §13 CIK→SIC 트랙으로 이관(재소환 조건: 백테스트에서 IPO 후행성 문제 판정 시).
> §12-6(05:50 외부 변경) = 정상 커밋 확인으로 close.

> **[2026-07-05] G3 PASS — C2b 데이터 전제 전건 검증 완료.**
> 424B5 OPEN·오염 0%·symbol 커버리지 90%(임계 85%)·3년 백필 동작 (지시서 3호, 4콜) →
> §5.2 재정의 확정, FAIL 분기 폐기. symbol 결측 ~10%는 카운트 제외 + 결손률 기록.
> 424B2 는 제외 확정(은행 구조화상품 물량 + 일 100건 캡 — §13 기록). 이로써 3종 프로브
> (insider PASS / filings·estimates PASS·FULL / 424b5 PASS) 전부 닫힘 — Heat 8성분의
> 데이터 전제 완전 검증. 잔여 하드 블로커 = §12-1 테마 정의 (사용자 결정) 단독.

> **[2026-07-05] §12-1 확정 = C안 (HeatEntity 추상 계층) → v1.1 FINAL 승격.**
> 온도 측정 단위 = HeatEntity{kind, ref_id, constituent_policy}, Cycle 1 은 kind=sector
> 11행만 시드. 근거: z 히스토리 안정성은 섹터와 동일하게 확보하면서 테마 확장 문을 무
> 마이그레이션으로 유지 (C 8.25 / A 8.00 / B 5.90). B 배제 근거 = HAS_THEME 은 살아
> 움직이는 것이 정상 작동이라 z 시계열과 구조적 상충 + 과거 구성 기록 부재로 백필 불가.
> 잠금장치: 3필드 초과 금지 / kind=theme 로직 Cycle 1~2 구현 금지 / 개방 게이트 = 6개월
> 백테스트 + 월 구성 동결 필수. 하드 블로커 전소진 — Cycle 1 PR 프롬프트 착수.

> **[2026-07-06] v1.2 FINAL — 자기완결화 + 마이그레이션 디커플링 (TH-1 블로커 해소).**
> 블로커 A: v1.1 의 "v1.0 과 동일" 참조가 원본 소멸로 파손(작성 결함 인정) → §6.1/6.3/6.4
> 필드 표 인라인, 스펙 7/7 자기완결. 블로커 B: 마켓 뷰 PR-1·SeedHeatScore 미착수 실측 →
> "동승"은 틀린 전제 위 최적화였으므로 폐기, TH-1 = 독립 마이그레이션 (B안 7.85 / 대기
> 6.65 / 흡수 5.40). 보완: 마켓 뷰 PR-1 착수 시 cs_44 와의 개념 조율 + HeatEntity 재사용
> 검토를 선행 의무로 §11 에 명시. 문서 동승 대상 = TH-1, 위치 `docs/chain_sight/theme_heat/`.

## 부록 A. C3 H2 — LLM 큐레이션 정적 사전 (박제, 구현 금지 — 결정17 승격 대기)

> 결정17 단계형의 2차 규칙. **명세 박제만·구현 금지** — 승격 트리거(정밀도 <80% 또는 미배정
> >40%, TH-11에서 발동) 비준 후 TH-C3-LLM-DICT 에서 착수.

- **문제**: 1차 토큰 매칭은 고유명사·이벤트 문구를 못 잡음(미배정 57.2%). 예 미배정: "SpaceX IPO"
  (우주항공), "BYD performance"(전기차), "Iran attacks"(지정학), "Anthropic Claude"(AI 기업).
  오배정: "SpaceX IPO"→Financials(ipo 토큰), "Goldman Sachs airline"→Consumer(airline 토큰).
- **H2 설계**: LLM(Gemini sync, Celery 동기)으로 미배정·저신뢰 검색어를 배치 큐레이션 →
  **정적 사전(committed dict)** 에 (검색어 정규화형 → 섹터) 확정 매핑 추가. 런타임 LLM 호출 없음
  (정적 사전 조회만 = 결정론·비용 0). 사전은 주기적 재큐레이션(신규 미배정 축적 시).
- **가드**: LLM 배정 신뢰도 임계 + 사람 검수 훅(오배정 교정). 사전은 1차 토큰 규칙 **뒤에** 적용
  (토큰 우선, 미배정분만 사전 조회). 부분 문자열·유사도는 여전히 금지(사전은 정규화형 완전 일치).
- **트리거 재평가**: H2 적용 후 배정률·정밀도 재측정 → 목표 미배정 ≤40% & 정밀도 ≥80%.

# 지표 카탈로그 동기화 감사 보고서

- **감사일**: 2026-05-09 (재감사, 5월 8일자 보고서 갱신)
- **모드**: 읽기 전용 (코드 수정 없음)
- **검사 대상**
  - BE 정의: `thesis/services/prompt_builder.py` (`INDICATOR_CATALOG`, `INDICATOR_FREQUENCY`)
  - BE 후처리: `thesis/services/llm_postprocess.py` (`indicator_db_id` 카탈로그 검증)
  - BE 매칭: `thesis/services/indicator_matcher.py` (`KEYWORD_RULES`, `match_by_keywords`, `match_indicators_for_llm`)
  - FE 표시: `frontend/components/thesis/AddIndicatorSheet.tsx` (`INDICATOR_CATALOG`, `KEYWORD_INDICATOR_MAP`)
- **카탈로그 규모**: BE 64개 / FE 64개 (id 1~73, 결번 17·18·19·27·28·29·48·49·59 정상)

---

## 요약 (동기화 상태)

| 항목 | 상태 | 비고 |
|---|---|---|
| BE↔FE id 일치 | OK | 64/64 완전 일치 (BE-only/FE-only 0건) |
| BE↔FE name 일치 | OK | 64개 id 모두 표시 이름 동일 |
| BE↔FE 업데이트 주기 일치 | OK | `INDICATOR_FREQUENCY`(BE) ↔ `freq`(FE) 64/64 일치 |
| description 결손/단문 | OK | 빈 description 0개, 10자 미만 0개 (최단 16자) |
| KEYWORD_RULES 고아 | OK | 11개 룰 모두 카탈로그 name으로 해소 |
| KEYWORD_RULES 커버리지 | **WARN** | BE 룰은 카탈로그 64개 중 11개(17%)만 커버, FE 룰은 ~50개(78%) 커버 → fallback 품질 BE/FE 비대칭 |
| name 기반 결합 | **WARN** | BE `KEYWORD_RULES`/`_find_in_catalog`가 PK 대신 name 문자열로 카탈로그를 조회 (이름 변경 시 silent break) |
| data_params 형식 일관성 | **WARN** | FMP에 비표준 metric 2건(`foreign_net_buy`, `institutional_net_buy`) + 알려진 미지원 심볼 1건(`DX-Y.NYB`) + 별도 endpoint 필요 1건(`growthRevenue`) |
| `match_by_gemini` 주석 일치성 | OK | `match_indicators_for_llm`은 PK→키워드만 사용, gemini fallback 비활성화(주석/코드 일치) |

총평: **id/name/주기 카탈로그 자체는 BE/FE 완전 동기화 상태**. 다만 (1) BE 키워드 룰이 FE 대비 협소하고 (2) data_params에 데이터 fetcher 측 분기가 필요한 비표준 항목 4건이 카탈로그 내부 `audit_note`/주석으로만 표시되어 있어 정의-소비 계층 간 약결합 위험이 남아 있음.

---

## BE ↔ FE 불일치 목록

### 1. id 차집합

- **BE-only id**: 없음
- **FE-only id**: 없음
- **양쪽 결번 id (사용 안 함, 정상)**: 17, 18, 19, 27, 28, 29, 48, 49, 59

### 2. name 차이 (id별)

64개 id 전체에서 BE name과 FE name이 문자 단위로 일치. 차이 없음.

| 검증 키 | BE 출처 | FE 출처 | 결과 |
|---|---|---|---|
| id 1 외국인 순매수 추이 | `prompt_builder.py:16` | `AddIndicatorSheet.tsx:17` | 일치 |
| id 50 PER (주가수익비율) | `prompt_builder.py:196` | `AddIndicatorSheet.tsx:65` | 일치 |
| id 73 순주주수익률 | `prompt_builder.py:300` | `AddIndicatorSheet.tsx:88` | 일치 |
| ... (전 64개 동일 검증) | - | - | 일치 |

### 3. 업데이트 주기 차이

- BE는 `INDICATOR_FREQUENCY`(`prompt_builder.py:321~342`)에서 id→주기 매핑.
- FE는 카탈로그 항목 자체에 `freq`를 직접 박아둠.
- 64개 id 전수 비교 결과 모든 주기가 일치 (예: `id 6 주간`, `id 7 일간`, `id 30 일간`, `id 37 주간`, `id 34 분기`).

### 4. 분류(category) 표기 차이 — 표시용 차이, 동기화 깨짐 아님

BE는 5개 대분류(`market_data` / `macro` / `technical` / `fundamental` / `sentiment`)를 사용.
FE는 17개 세부 분류(`수급`, `주요 지수`, `원자재`, `암호화폐`, `금리`, `환율/변동성`, `고용/성장`, `물가/주택`, `기술적`, `펀더멘털`, `재무 체질`, `밸류에이션`, `성장`, `운영 효율`, `이익 품질`, `주주환원`, `심리`)로 잘게 쪼갬.

→ 의도된 차이(FE는 UI grouping용). 다만 BE→FE 자동 동기화는 불가능하므로 신규 지표 추가 시 FE category를 수동 지정해야 한다는 제약은 잔존.

---

## description 품질

총 64개 항목 모두 한 문장 이상의 한국어 설명을 보유. 점검 결과:

- **빈 description**: 0건
- **10자 미만 description**: 0건
- **최단 description (16자)**: id 14 코스닥 지수 ("한국 중소형 성장주 시장 지수.")
- **두 번째 최단 (24~26자대)**: id 4 KOSPI 지수, id 22 은(Silver), id 23 구리, id 24 천연가스
- **장문 description (60자+)**: id 50 PER, id 52 ROE, id 65 순부채/EBITDA, id 67 EV/EBITDA 등 비율·밸류에이션 지표 다수

→ description은 카탈로그 단일 소스(`prompt_builder.py`)에만 존재하며 FE 측에는 미러링되지 않음. FE는 name + freq + category만 사용하므로 현재 화면에서는 description 미사용. 향후 FE 툴팁/도움말 노출 요구 시 동기화 대상이 1개 늘어나는 점에 유의.

---

## keyword_rules 고아

### BE `thesis/services/indicator_matcher.py::KEYWORD_RULES`

총 11개 룰. 각 룰의 `indicators[].name`이 `INDICATOR_CATALOG`에 존재하는지 검증:

| # | 룰 키워드 (앞부분) | 매핑 indicator name | 카탈로그 id | 검증 |
|---|---|---|---|---|
| 1 | 외국인/외인/순매수… | 외국인 순매수 추이 | 1 | OK |
| 2 | 금리/연준/FOMC… | 미국 기준금리 (Fed Funds Rate) | 6 | OK |
| 2 | 〃 | 미국 10년 국채 금리 | 7 | OK |
| 3 | VIX/공포/변동성… | VIX (공포지수) | 8 | OK |
| 4 | 환율/달러/원달러… | 원/달러 환율 | 9 | OK |
| 5 | RSI/MACD/기술적… | RSI (14일) | 10 | OK |
| 6 | 센티먼트/여론/뉴스… | 뉴스 센티먼트 | 11 | OK |
| 7 | 실적/EPS/매출/PER… | EPS 추이 | 5 | OK |
| 8 | 기관/연기금… | 기관 순매수 추이 | 2 | OK |
| 9 | S&P/나스닥/다우… | S&P 500 | 3 | OK |
| 10 | 코스피/KOSPI… | KOSPI 지수 | 4 | OK |
| 11 | 선거/정치/정책… | VIX (공포지수) + KOSPI 지수 | 8, 4 | OK |

→ **고아 룰 0건**. 모든 키워드 룰은 카탈로그에 존재하는 name으로 해소.

### 우려 사항 (고아는 아니지만 약결합)

1. **PK가 아닌 name 문자열로 결합**
   - `KEYWORD_RULES`의 `indicators[].name`은 카탈로그 id가 아닌 표시 이름. `_find_in_catalog(name)` (`indicator_matcher.py:332`)이 id 대신 name으로 카탈로그를 순회 매칭함.
   - 카탈로그에서 name을 변경하면 (예: "VIX (공포지수)" → "VIX") 키워드 룰이 silent하게 깨지며, 정적 검사기/타입 시스템이 잡지 못함.
   - 권장: 룰에 `indicator_db_id`를 박아두고 fetch 시점에 카탈로그에서 메타데이터 조회.

2. **카탈로그 64개 중 KEYWORD_RULES 커버리지 11개 (17%)**
   - 미커버 영역: 모든 원자재(20~24), 암호화폐(25·26), 부지수(NASDAQ 12 ~ HSI 16, 단 11 룰의 일반 키워드 일부만 매핑), 거시경제 절반(30·31·33~38), 모든 기술적 보조지표(40~47), 거의 모든 펀더멘털(50~58, 60~73).
   - 영향: LLM이 `indicator_db_id`를 비워서 응답한 전제는 `match_by_keywords`로만 fallback되어 카탈로그의 8% 영역 밖에서는 추천이 비어버림.

3. **FE `KEYWORD_INDICATOR_MAP`은 28개 룰**
   - `AddIndicatorSheet.tsx:109~139`의 KEYWORD_INDICATOR_MAP은 28개 룰로 카탈로그 id 약 50개를 커버.
   - BE/FE 룰 테이블이 별도 정의되어 있어 한쪽에 룰 추가 시 다른 쪽에 자동 반영되지 않음. **BE 룰이 FE 룰보다 17개 적은 비대칭**.

4. **`match_by_gemini`는 보조 함수로 잔존, 호출은 차단됨**
   - `indicator_matcher.py:186~254`에 `match_by_gemini`가 정의되어 있지만 `match_indicators_for_llm`에서는 사용하지 않음 (`indicator_matcher.py:307` 주석: "match_by_gemini fallback은 카탈로그에 없는 환각 지표를 생성하므로 제외").
   - `match_indicators_for_premise`(`indicator_matcher.py:257~268`, 비-LLM 빌더 경로)에서는 여전히 fallback으로 호출 → 이 경로는 카탈로그 외 지표를 생성할 수 있음 (위반 가능). 호출 지점 확인 필요(현 감사 범위 외).

---

## data_params 형식

### 형식 분류

| data_source | 키 패턴 | 카탈로그 사용 항목 수 | 비고 |
|---|---|---|---|
| `fmp` | `symbol` (지수/원자재/코인/환율) | 17 | `^GSPC`, `^VIX`, `BTCUSD`, `USDKRW`, `DX-Y.NYB` 등 |
| `fmp` | `metric` (TTM 비율) | 12 | `eps`, `earningsYieldTTM`, `pbRatioTTM`, `returnOn*TTM` 등 |
| `fmp` | `indicator` (기술적) | 9 | `RSI`, `MACD`, `SMA`, `EMA`, `bollinger`, `OBV` 등 + `period` |
| `fred` | `series_id` | 11 | `FEDFUNDS`, `DGS10`, `CPIAUCSL`, `PAYEMS`, `DEXUSEU` 등 |
| `metrics` | `metric_code` | 14 | `gross_margin`, `roic`, `ev_to_ebitda`, `accruals_ratio` 등 |
| `news_sentiment` | (빈 dict) | 1 | id 11 |

### 외부 API와의 형식 정합성 — 위험 항목

#### A. 비표준 FMP metric (커스텀 키, FMP에 직접 매핑되지 않음)

| id | name | data_params.metric | 우려 |
|---|---|---|---|
| 1 | 외국인 순매수 추이 | `foreign_net_buy` | FMP의 표준 endpoint/필드명 아님. 별도 fetch 어댑터에서 처리되지 않으면 데이터 0건. |
| 2 | 기관 순매수 추이 | `institutional_net_buy` | 동일. FMP `/api/v4/insider-trading` 등은 다른 형식이라 직접 매핑 불가. |

→ 두 항목은 BE 키워드 룰에서도 동일한 `metric` 키로 정의(`indicator_matcher.py:18`, `:105`)되어 있어 카탈로그-룰 사이에선 일관됨. 다만 **데이터 fetcher 단에서 이 키들을 해석하는 어댑터의 존재 여부는 본 감사 범위 내에서 확인되지 않음** (`grep`상 prompt_builder/indicator_matcher 외 사용처 없음).

#### B. 알려진 FMP 미지원 심볼

| id | name | data_params.symbol | 근거 |
|---|---|---|---|
| 39 | 달러 인덱스 (DXY) | `DX-Y.NYB` | `macro/services/fmp_client.py:188` 주석에 "DX-Y.NYB는 FMP Starter 미지원 → 제외" 기록. 동일 클라이언트 `:359`에서 시도하지만 FMP Starter Plan에서는 데이터 미반환 가능. |

→ 카탈로그에 그대로 등록되어 있어 LLM/사용자가 이 지표를 선택하면 실시간 fetch가 실패할 가능성. data_source를 `fred`로 옮기거나(예: `DTWEXBGS`) 별도 fallback 명시 필요.

#### C. TTM endpoint 비표준 — 카탈로그 자체에 audit_note로 주석 처리됨

| id | name | data_params | 처리 위치 |
|---|---|---|---|
| 50 | PER | `metric=earningsYieldTTM`, `inverse=True` | `prompt_builder.py:198`. `eod_pipeline.py:29`에서 `inverse` 분기 처리. |
| 52 | ROE | `metric=returnOnEquityTTM`, `scale_multiplier=100` | 0~1 비율 → % 변환. `eod_pipeline.py:29`에서 처리. |
| 53 | ROA | `metric=returnOnAssetsTTM`, `scale_multiplier=100` | 동일 패턴. |
| 58 | 매출성장률 (YoY) | `metric=growthRevenue`, `endpoint=financial-growth`, `scale_multiplier=100` | `key-metrics-ttm`이 아닌 `/stable/financial-growth` 별도 endpoint 필요. `eod_pipeline.py:48~56`에 분기 명시. |

→ 처리 분기가 데이터 fetcher(`thesis/tasks/eod_pipeline.py`)에 별도 코드로 박혀 있음. 카탈로그 정의(`audit_note`)와 fetcher 분기가 분리되어 있으므로 **신규 비표준 metric을 추가할 때 두 곳을 모두 수정해야 함** (계약 명문화 부재).

#### D. `data_source='fred'`인데 series_id가 일관되지 않은 항목

검토 결과 11개 FRED 항목 모두 표준 series_id 사용 (FEDFUNDS, DGS10, DGS2, MORTGAGE30US, UNRATE, PAYEMS, GDPC1, INDPRO, CPIAUCSL, HOUST, DEXUSEU). 이 부분은 정상.

#### E. `data_source='metrics'` (validation/metrics 시스템 의존)

14개 항목 모두 `metric_code`(`gross_margin`, `roic`, `accruals_ratio` 등)만 지정. 실제 metric 정의는 `metrics` 앱의 메타테이블에 존재해야 하며, 본 감사 범위에서는 `metric_code`의 메타데이터 존재 여부를 검증하지 않음. 별도 점검 권장.

#### F. 빈 data_params (정상)

- id 11 뉴스 센티먼트: `data_params: {}` — `data_source: 'news_sentiment'`이므로 정상.

---

## 권장 후속 조치 (코드 수정 없이 기록만)

1. **단일 소스화 (P1)**: `INDICATOR_CATALOG`을 BE/FE 양쪽에 직접 박지 말고 `contracts/` JSON으로 export → FE는 빌드 타임에 generate. 현재는 64개 항목을 양쪽에 수기로 동기 유지하는 구조.
2. **KEYWORD_RULES 정합 (P2)**: BE 룰을 FE `KEYWORD_INDICATOR_MAP`(28개) 수준으로 보강하거나 FE 룰을 BE에서 가져오도록 통합.
3. **id 기반 결합 (P2)**: BE `KEYWORD_RULES`의 `indicators[]` 항목에 `indicator_db_id`를 추가하고 매칭 시 PK 우선 사용. name 문자열 결합 제거.
4. **DXY 심볼 수정 (P1)**: id 39 `DX-Y.NYB` → FRED `DTWEXBGS` 또는 FMP 지원 대체 심볼로 변경 검토 (`macro/services/fmp_client.py:188` 주석과 일관되게).
5. **비표준 FMP metric 어댑터 명시 (P2)**: `foreign_net_buy`, `institutional_net_buy`에 대한 fetch 어댑터의 위치를 카탈로그 `audit_note`에 명시 또는 어댑터가 부재하면 카탈로그에서 제거.
6. **`match_indicators_for_premise`의 gemini fallback 검토 (P1)**: `match_by_gemini`가 카탈로그 외 지표를 생성할 수 있음. LLM 빌더 경로 외 호출 지점이 남아 있는지 확인 후 동일 정책(PK→키워드만) 적용.
7. **description의 FE 노출 여부 확정 (P3)**: 화면에서 사용 안 한다면 BE 단일 소스로 유지, 노출 시 contracts 동기화 대상 추가.

---

## 부록 — 검사 데이터 출처

- `INDICATOR_CATALOG`: `thesis/services/prompt_builder.py:14~310` (64개 항목)
- `INDICATOR_FREQUENCY`: `thesis/services/prompt_builder.py:321~342`
- `KEYWORD_RULES`: `thesis/services/indicator_matcher.py:12~154` (11개 룰)
- `match_indicators_for_llm`: `thesis/services/indicator_matcher.py:271~329`
- `_find_in_catalog`: `thesis/services/indicator_matcher.py:332~338`
- `normalize_llm_output` (indicator_db_id 검증): `thesis/services/llm_postprocess.py:82~95`
- FE `INDICATOR_CATALOG`: `frontend/components/thesis/AddIndicatorSheet.tsx:15~91` (64개 항목)
- FE `KEYWORD_INDICATOR_MAP`: `frontend/components/thesis/AddIndicatorSheet.tsx:109~139` (28개 룰)
- DXY 미지원 메모: `macro/services/fmp_client.py:188`
- TTM 비표준 처리: `thesis/tasks/eod_pipeline.py:29~56`

# 지표 카탈로그 동기화 감사 보고서

- **감사 일자**: 2026-06-09
- **모드**: 읽기 전용 (코드 수정 없음)
- **대상 파일**
  - BE 정의: `thesis/services/prompt_builder.py` (`INDICATOR_CATALOG`)
  - BE 후처리: `thesis/services/llm_postprocess.py`
  - BE 매칭: `thesis/services/indicator_matcher.py` (`KEYWORD_RULES`)
  - BE fetch: `thesis/tasks/eod_pipeline.py` (`DATA_SOURCE_FETCHERS`)
  - FE 표시: `frontend/components/thesis/AddIndicatorSheet.tsx` (`INDICATOR_CATALOG`, `KEYWORD_INDICATOR_MAP`)

---

## 요약 (동기화 상태)

| 검사 항목 | 결과 | 심각도 |
|----------|------|--------|
| BE ↔ FE 지표 ID/이름 동기화 | ✅ 64개 완전 일치 (불일치 0건) | — |
| BE ↔ FE 업데이트 주기(freq) 동기화 | ✅ 전건 일치 | — |
| BE ↔ FE 카테고리 표현 | ⚠️ 표현 체계 상이 (BE 5분류 / FE 17세분류, 매핑 없음) | P2 |
| description 품질 (BE) | ✅ 빈 값 0건, 10자 미만 0건 | — |
| FE description 보유 | ⚠️ FE 카탈로그에 description 필드 자체 없음 | P3 |
| keyword_rules 고아 규칙 | ✅ BE/FE 모두 고아 0건 | — |
| keyword_rules 이중화 | ⚠️ BE(name 11룰)·FE(id 27룰) 완전 분기, 동기화 메커니즘 없음 | P2 |
| keyword_rules indicator_type 메타 | ⚠️ 카탈로그 category와 4건 불일치 | P2 |
| **data_params ↔ fetcher 형식** | 🔴 **수급 지표 2건 fetch 불가 + news_sentiment fallback 누락 + 미지원 심볼 위험** | **P1** |

**총평**: BE↔FE 카탈로그 골격(ID·이름·주기)은 완벽히 동기화되어 있어 "지표 추가/삭제" 수준의 표면 드리프트는 없다. 그러나 `data_params`가 **실제 데이터 제공자(FMP)의 응답 스키마와 맞지 않는 항목이 존재**하여, 사용자가 선택해도 값이 영구 `None`으로 남는 지표가 확정적으로 존재한다(아래 P1 참조). 이것이 이번 감사의 핵심 리스크다.

---

## BE ↔ FE 불일치 목록

### 지표 항목 (ID·이름)

BE `INDICATOR_CATALOG` 64개와 FE `INDICATOR_CATALOG` 64개를 ID 기준으로 대조:

- **BE에만 있는 항목**: 없음
- **FE에만 있는 항목**: 없음
- **ID는 같으나 이름이 다른 항목**: 없음

> ID 집합(양쪽 동일): 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,20,21,22,23,24,25,26,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,50~58,60~73

**결론: 지표 목록 자체의 BE↔FE 불일치는 0건.**

### 카테고리 표현 (P2)

ID/이름은 같지만 **분류 체계가 서로 다르다.**

| 측 | 분류 키 | 개수 |
|----|--------|------|
| BE (`category`) | `market_data` / `macro` / `technical` / `fundamental` / `sentiment` | 5개 대분류 |
| FE (`category`) | `수급` / `주요 지수` / `원자재` / `암호화폐` / `금리` / `환율/변동성` / `고용/성장` / `물가/주택` / `기술적` / `펀더멘털` / `재무 체질` / `밸류에이션` / `성장` / `운영 효율` / `이익 품질` / `주주환원` / `심리` | 17개 세분류 |

- FE 세분류는 BE 대분류에서 **자동 도출되지 않으며**, FE 소스에 하드코딩되어 있다.
- 위험: 신규 지표를 BE에 추가하면 FE의 `category`(17종 중 하나)와 `categoryOrder` 배열을 **수동으로 채워야** 한다. 누락 시 FE에서 해당 지표가 `byCategory` 그룹에 안 잡혀 **목록에서 사라진다**(`AddIndicatorSheet.tsx:286` `categoryOrder.map`이 미등록 카테고리를 렌더하지 않음).

### 업데이트 주기 (freq)

BE `INDICATOR_FREQUENCY`(id→주기)와 FE `freq` 필드 대조 → **전건 일치**. (예: id6 주간/주간, id7 일간/일간, id37 주간/주간, id34 분기/분기, id31·32·33·35·36 월간/월간)

---

## description 품질

### BE (`prompt_builder.py`)

- 64개 항목 **전부 `description` 보유**.
- **빈 `description`: 0건.**
- **10자 미만 `description`: 0건.** (최단 항목도 한 문장 이상, 예: id4 KOSPI "한국 유가증권시장 전체 종목 시가총액 가중 지수." 25자)
- 품질 양호. `_INDICATOR_NAME_TO_DESC` + `get_indicator_description()`(접두사 매칭)로 LLM 모드의 "EPS 추이 (META)" 같은 심볼 접미 케이스도 커버.

### FE (`AddIndicatorSheet.tsx`) — P3

- FE `CatalogIndicator` 타입은 `{ id, name, category, freq }`만 보유 — **`description` 필드 자체가 없음.**
- 즉 사용자가 지표 추가 시트에서 보는 정보는 이름·주기뿐, 설명 툴팁이 없다. BE가 보유한 73개 description 자산이 FE에 노출되지 않는다(기능 부재이며 동기화 버그는 아님).

---

## keyword_rules 고아

### BE `KEYWORD_RULES` (`indicator_matcher.py`, name 기반 11개 룰)

각 룰의 `indicators[].name`이 카탈로그에 존재하는지 대조:

| 룰 키워드 | 참조 지표 name | 카탈로그 매칭 |
|----------|---------------|--------------|
| 외국인/외인/순매수… | 외국인 순매수 추이 | ✅ id1 |
| 금리/연준/FOMC… | 미국 기준금리 / 미국 10년 국채 금리 | ✅ id6, id7 |
| VIX/공포/변동성… | VIX (공포지수) | ✅ id8 |
| 환율/달러… | 원/달러 환율 | ✅ id9 |
| RSI/MACD/기술적… | RSI (14일) | ✅ id10 |
| 센티먼트/여론… | 뉴스 센티먼트 | ✅ id11 |
| 실적/EPS/매출… | EPS 추이 | ✅ id5 |
| 기관/연기금… | 기관 순매수 추이 | ✅ id2 |
| S&P/나스닥… | S&P 500 | ✅ id3 |
| 코스피/KOSPI… | KOSPI 지수 | ✅ id4 |
| 선거/정치/정책… | VIX / KOSPI 지수 | ✅ id8, id4 |

- **고아 규칙(카탈로그에 없는 지표를 가리키는 룰): 0건.**
- ⚠️ **메타 불일치 (P2)**: `KEYWORD_RULES`의 `indicator_type` 값이 카탈로그 `category`와 어긋난다.
  - `EPS 추이`: 룰 `indicator_type='market_data'` ↔ 카탈로그 `category='fundamental'`
  - `외국인 순매수 추이`·`기관 순매수 추이`·`S&P 500`·`KOSPI 지수`: 룰 `market_data` ↔ 카탈로그 `market_data` (일치)
  - 실질 위험은 낮음 — `match_indicators_for_llm()`이 `_find_in_catalog()`로 카탈로그 엔트리를 우선 사용(`indicator_matcher.py:316-322`)하므로 룰의 `indicator_type`은 LLM 경로에서 덮어쓰여진다. 단 레거시 직접 경로 `match_indicators_for_premise()`는 룰 dict를 그대로 반환하므로 잘못된 `indicator_type`이 노출될 수 있다.

### FE `KEYWORD_INDICATOR_MAP` (`AddIndicatorSheet.tsx`, id 기반 27개 룰)

- 모든 `indicatorIds`(1,2,3,4,5,6,7,8,9,10,11,12,15,16,20,21,23,24,25,26,30,31,32,33,34,35,36,37,39,50~58,60~73)가 카탈로그 ID에 존재 → **고아 ID 0건.**

### 이중 키워드 시스템 분기 (P2)

BE와 FE가 **완전히 다른 키워드 매핑을 각자 보유**한다.

| | BE `KEYWORD_RULES` | FE `KEYWORD_INDICATOR_MAP` |
|--|--------------------|----------------------------|
| 식별자 | 지표 **name** 문자열 | 지표 **id** 숫자 |
| 룰 개수 | 11개 | 27개 |
| 커버 지표 | 11개 (id 1~11 중심) | 50+ 개 (재무 체질·밸류에이션 포함) |
| 용도 | 레거시 텍스트 fallback 추천 | "전제 관련 추천" UX |

- 두 테이블은 동기화 메커니즘이 없다. 예: FE는 `유가/원유/WTI`→id21, `금/gold`→id20, `반도체/AI`→id12·3 등 풍부하지만, BE `KEYWORD_RULES`에는 원자재·반도체 키워드 룰이 아예 없다.
- 위험: 키워드 추천 동작이 BE 경로(서버 자동매칭)와 FE 경로(클라이언트 추천 시트)에서 서로 다른 결과를 낸다. CLAUDE.md 버그 #(지표 카탈로그 3곳 미러)와 동일한 "분산 미러" 구조적 부채.

---

## data_params 형식

`eod_pipeline.py`의 `DATA_SOURCE_FETCHERS`는 `data_source`별로 fetcher를 분기한다(`fmp`/`fred`/`news_sentiment`/`metrics`). 각 fetcher가 기대하는 `data_params` 키와 카탈로그 정의를 대조했다.

### ✅ 정상 동작 확정

| data_source | 기대 키 | 카탈로그 일치 | 비고 |
|-------------|--------|--------------|------|
| `fred` | `series_id` | ✅ 11건 모두 유효 FRED 시리즈 (FEDFUNDS, DGS10, DGS2, MORTGAGE30US, UNRATE, PAYEMS, GDPC1, INDPRO, CPIAUCSL, HOUST, DEXUSEU) | `get_latest_value(series_id)` |
| `metrics` | `metric_code` | ✅ 14건 모두 validation/metrics 코드 | symbol은 `thesis.target` fallback 있음 (`eod_pipeline.py:236`) |
| `fmp` TTM/growth | `metric`(…TTM) + `inverse`/`scale_multiplier`/`endpoint` | ✅ #14 회귀 방지 후처리 정상 | `_apply_value_postprocess` (PER 역수, ROE ×100 등) |
| `fmp` quote | `symbol` 또는 `metric`(price/eps 등) | ✅ id5 EPS 등 quote 필드 매핑 정상 | `value_map` (`eod_pipeline.py:128`) |

`inverse`/`scale_multiplier`/`endpoint`/`audit_note` 같은 메타 키는 fetcher(`_apply_value_postprocess`, `_fetch_fmp_ttm_or_growth`)가 정확히 해석하도록 구현되어 있어 **#14 회귀 위험은 코드 레벨에서 차단**되어 있다.

### 🔴 P1 — fetch 불가 / 형식 불일치 (값이 영구 None)

#### 1. 수급 지표 2건 — FMP quote에 해당 필드 없음
- **id1 외국인 순매수 추이** `{'metric': 'foreign_net_buy'}`
- **id2 기관 순매수 추이** `{'metric': 'institutional_net_buy'}`

`_fetch_fmp_value`의 quote 분기에서 `field = value_map.get(metric, metric)` → `value_map`에 `foreign_net_buy`/`institutional_net_buy`가 **없으므로** 키가 그대로 사용되어 `quote.get('foreign_net_buy')` 조회 → FMP `/stable/quote` 응답에 그런 필드는 존재하지 않음 → **항상 `None` 반환**.

추가로 FMP(미국 시장 중심)는 한국식 "외국인/기관 순매수" 데이터 자체를 제공하지 않는다. 이 2개 지표는 키워드 룰(BE/FE 모두)에서 1순위로 추천되지만 **실제로는 값을 절대 채울 수 없다.** → 사용자가 추천대로 선택하면 관제실에 빈 지표로 남음.

#### 2. news_sentiment — symbol fallback 누락
- **id11 뉴스 센티먼트** `data_params = {}` (빈 dict)

`_fetch_news_sentiment_value`는 `params.get('symbol')`을 요구하며, 없으면 즉시 경고 후 `None` 반환(`eod_pipeline.py:204-208`). **`fmp`/`metrics` fetcher와 달리 `thesis.target` fallback이 없다.** 카탈로그가 `data_params`를 빈 dict로 정의하므로, 지표 생성 시 `target_symbol`이 주입되지 않으면(또는 `thesis_builder.py:1182`의 symbol 주입 경로를 타지 않으면) 영구 `None`.

> 참고: `thesis_builder.py:1182`에서 `target_sym and 'symbol' not in data_params`일 때 symbol을 주입하는 로직이 있어 일부 경로는 구제되나, news_sentiment fetcher 자체에 target fallback이 없는 것은 다른 fetcher와의 **형식 비대칭**이다.

#### 3. FMP 미지원/프리미엄 심볼 위험 (P1~P2)
quote 분기로 가는 지수·환율 심볼 중 FMP Starter 플랜에서 미지원이거나 형식이 다른 후보:

| id | 이름 | data_params symbol | 위험 |
|----|------|-------------------|------|
| 4 | KOSPI 지수 | `^KS11` | FMP 한국 지수 미지원/프리미엄 가능 → `FMPPremiumError`로 graceful None |
| 14 | 코스닥 지수 | `^KQ11` | 동상 |
| 15 | 니케이 225 | `^N225` | 아시아 지수 커버리지 불확실 |
| 16 | 항셍 지수 | `^HSI` | 동상 |
| 39 | 달러 인덱스 (DXY) | `DX-Y.NYB` | **Yahoo Finance 형식** — FMP는 다른 티커 사용, 인식 실패 가능 |
| 9 | 원/달러 환율 | `USDKRW` | FMP forex 형식 확인 필요(`USDKRW` vs `KRWUSD`) |

`FMPPremiumError`/`FMPClientError`는 잡혀서 `None`을 반환하므로 **크래시는 없으나**, 해당 지표들은 조용히 빈 값으로 남을 수 있다. 실데이터 검증(별도 라이브 호출)이 필요하나 본 감사는 읽기 전용이라 코드 레벨 위험만 식별한다.

### data_params 키 형식 요약표

| data_source | 필수 키 | 선택 메타 키 | fetcher fallback |
|-------------|--------|-------------|------------------|
| `fmp` (quote) | `symbol` 또는 `metric` | — | symbol 없으면 `thesis.target` ✅ |
| `fmp` (TTM/growth) | `metric`(…TTM) | `inverse`, `scale_multiplier`, `endpoint`, `audit_note` | symbol 없으면 `thesis.target` ✅ |
| `fred` | `series_id` | — | 없음 (series_id 필수) |
| `metrics` | `metric_code` | `symbol` | symbol 없으면 `thesis.target` ✅ |
| `news_sentiment` | `symbol` | — | **❌ fallback 없음** |

---

## 권고 (참고용, 코드 미수정)

> 본 보고서는 읽기 전용 감사이며 아래는 후속 작업 제안이다.

1. **[P1] 수급 지표(id1, id2) 재정의 또는 비활성화** — FMP quote로 fetch 불가. 한국 수급 데이터 제공자를 별도 확보하거나, 카탈로그에서 `data_source`를 `manual`로 전환하거나, 제거 검토.
2. **[P1] news_sentiment fetcher에 `thesis.target` fallback 추가** — 다른 fetcher와 형식 대칭화. (또는 카탈로그 차원에서 symbol 주입 보장)
3. **[P1] FMP 미지원 심볼 라이브 검증** — `^KS11`/`^KQ11`/`^N225`/`^HSI`/`DX-Y.NYB`/`USDKRW`의 실제 FMP 응답을 1회 호출로 확인 후, 미지원 시 FRED 대체 시리즈(예: DXY→`DTWEXBGS`) 검토.
4. **[P2] 키워드 시스템 단일화** — BE `KEYWORD_RULES`(name)와 FE `KEYWORD_INDICATOR_MAP`(id)을 단일 소스(id 기반)로 통합하거나 codegen으로 미러링.
5. **[P2] 카테고리 매핑 명세화** — BE 5분류 → FE 17세분류 매핑을 contract로 박제하여 신규 지표 추가 시 FE 누락 방지.
6. **[P2] `KEYWORD_RULES`의 `indicator_type` 정정** — `EPS 추이` `market_data`→`fundamental`.
7. **[P3] FE 카탈로그에 description 노출** — BE의 73개 description 자산을 codegen으로 FE에 전파(툴팁).

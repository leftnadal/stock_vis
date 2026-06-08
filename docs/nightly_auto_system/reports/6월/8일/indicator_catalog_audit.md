# 지표 카탈로그 동기화 감사 보고서

> 감사 일시: 2026-06-08 · 범위: 읽기 전용 (코드 무수정)
> 대상 파일:
> - BE 정의: `thesis/services/prompt_builder.py` (`INDICATOR_CATALOG`, 64개)
> - BE 매칭: `thesis/services/indicator_matcher.py` (`KEYWORD_RULES`, 11개)
> - BE 후처리: `thesis/services/llm_postprocess.py`
> - BE fetch: `thesis/tasks/eod_pipeline.py` (data_params 실소비 계층)
> - BE 검증: `thesis/serializers/indicator_serializers.py` (`ALLOWED_DATA_PARAM_KEYS`)
> - FE 표시: `frontend/components/thesis/AddIndicatorSheet.tsx` (`INDICATOR_CATALOG` 미러 + `KEYWORD_INDICATOR_MAP`)

---

## 요약 (동기화 상태)

| 검사 항목 | 상태 | 비고 |
|----------|------|------|
| BE ↔ FE 지표 ID/이름 동기화 | 🟢 **완전 일치** | 양쪽 64개, ID·이름 1:1 동일 |
| BE ↔ FE category 필드 | 🟡 **의도된 분기** | BE 5개 도메인 / FE 17개 표시 그룹 — 미문서화 |
| FE description 표시 | 🟡 **누락** | FE 미러는 description 필드 자체 없음 (지표 설명 미표시) |
| description 품질 (BE) | 🟢 **양호** | 64개 전부 비어있지 않음, 전부 ≥ 10자 |
| BE keyword_rules 고아 | 🟢 **없음** | 11개 규칙명 전부 카탈로그에 존재 |
| FE keyword_rules 고아 | 🟢 **없음** | 참조 ID 전부 카탈로그에 존재 |
| BE↔FE keyword_rules 동기화 | 🔴 **별도 시스템** | BE 11규칙(이름기반) vs FE 28규칙(ID기반), 상호 미동기화 |
| data_params ↔ serializer 허용키 | 🔴 **불일치** | 카탈로그 8개 키가 serializer allowlist에 없음 |
| data_params ↔ FMP 제공자 형식 | 🟡 **일부 위험** | 수급 2건 항상 실패 + 심볼/TTM 형식 검증 필요 다수 |

**총평**: 지표 **목록 자체(ID·이름)는 BE↔FE 완벽 동기화**되어 있다. 위험은 (1) data_params 어휘가 serializer 검증 계약과 어긋난 점, (2) keyword 매칭 로직이 BE/FE 이중 구현되어 따로 노는 점, (3) 일부 FMP 심볼/필드 형식이 실제 제공자와 맞지 않을 가능성에 집중된다.

---

## BE ↔ FE 불일치 목록

### 1. 지표 ID/이름 — 불일치 없음 🟢

BE `INDICATOR_CATALOG`와 FE `INDICATOR_CATALOG` 미러 모두 동일한 64개 ID를 보유:

```
1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,20,21,22,23,24,25,26,30,31,32,
33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,50,51,52,53,54,55,56,57,
58,60,61,62,63,64,65,66,67,68,69,70,71,72,73
```

- BE에만 있는 ID: **없음**
- FE에만 있는 ID: **없음**
- 이름 표기 불일치: **없음** (예: id 13 `다우존스`, id 39 `달러 인덱스 (DXY)` 양쪽 동일)

### 2. category 필드 분기 🟡 (의도된 차이, 미문서화)

| 위치 | category 값 | 용도 |
|------|------------|------|
| BE | `market_data` / `macro` / `technical` / `fundamental` / `sentiment` (5개) | LLM 프롬프트 도메인 분류 |
| FE | `수급` / `주요 지수` / `원자재` / `암호화폐` / `금리` / `환율/변동성` / `고용/성장` / `물가/주택` / `기술적` / `펀더멘털` / `재무 체질` / `밸류에이션` / `성장` / `운영 효율` / `이익 품질` / `주주환원` / `심리` (17개) | UI 표시 그룹핑 |

- 구조적으로 BE 1개 도메인 = FE 여러 표시 그룹 (예: BE `fundamental` → FE `펀더멘털`+`재무 체질`+`밸류에이션`+`성장`+`운영 효율`+`이익 품질`+`주주환원`).
- **버그는 아님** — 두 필드는 목적이 다름. 다만 "미러"라는 주석(`// INDICATOR_CATALOG 미러`)과 달리 category는 미러가 아니므로, 신규 지표 추가 시 FE category를 수동 분류해야 하는 동기화 부담이 존재한다.

### 3. FE description 누락 🟡

- BE는 64개 모두 `description` 보유 (관제실/프롬프트에서 사용).
- FE `CatalogIndicator` 인터페이스는 `{ id, name, category, freq }`만 — **description 없음**.
- 결과: 지표 추가 시트(`AddIndicatorSheet`)에서 사용자에게 지표 설명이 노출되지 않는다. FE는 대신 keyword 규칙의 `reason` 문구만 "전제 관련 추천" 맥락에서 표시.

### 4. freq(업데이트 주기) 동기화 🟢

- BE `INDICATOR_FREQUENCY` (id→주기 매핑)와 FE 각 항목의 `freq` 필드 표본 대조 시 일치 (예: id 6 주간, id 7 일간, id 34 분기, id 50 분기).

---

## description 품질

### BE (`prompt_builder.py`) — 🟢 이슈 없음

- **빈 description**: 0건. 64개 전부 비어있지 않음.
- **10자 미만**: 0건. 최단 항목도 충분한 길이 (예: id 14 `한국 중소형 성장주 시장 지수.` 17자).
- 형식 일관성 양호: 대부분 "정의 + 투자적 함의" 2문장 구조 (예: id 23 `구리 선물 가격. 경기 선행지표로 "Dr. Copper"라 불림.`).

### FE — 해당 없음

- FE 미러에 description 필드가 존재하지 않아 품질 평가 대상 아님 (위 §3 참조).

---

## keyword_rules 고아

키워드 매칭은 **BE/FE에 서로 다른 두 시스템**으로 이중 구현되어 있다.

### A. BE `KEYWORD_RULES` (`indicator_matcher.py`, 11개 규칙) — 🟢 고아 없음

규칙은 **지표 이름 문자열**로 카탈로그를 참조한다 (`_find_in_catalog(name)`). 11개 규칙이 가리키는 이름:

| 규칙 키워드(대표) | 지표 이름 | 카탈로그 존재 |
|---|---|---|
| 외국인/외인/순매수 | 외국인 순매수 추이 (id 1) | ✅ |
| 금리/연준/FOMC | 미국 기준금리 (id 6), 미국 10년 국채 금리 (id 7) | ✅ |
| VIX/공포/변동성 | VIX (공포지수) (id 8) | ✅ |
| 환율/달러 | 원/달러 환율 (id 9) | ✅ |
| RSI/MACD/기술적 | RSI (14일) (id 10) | ✅ |
| 센티먼트/뉴스 | 뉴스 센티먼트 (id 11) | ✅ |
| 실적/EPS | EPS 추이 (id 5) | ✅ |
| 기관/연기금 | 기관 순매수 추이 (id 2) | ✅ |
| S&P/나스닥 | S&P 500 (id 3) | ✅ |
| 코스피 | KOSPI 지수 (id 4) | ✅ |
| 선거/정치/정책 | VIX (id 8), KOSPI 지수 (id 4) | ✅ |

- **매칭 안 되는 고아 규칙: 0건.**
- ⚠️ **인라인 메타 drift 1건**: `실적/EPS` 규칙의 인라인 `indicator_type`이 `'market_data'`이나, 카탈로그 id 5의 `category`는 `'fundamental'`. 규칙이 data_source/data_params/type을 카탈로그와 **중복 하드코딩**하고 있어 향후 drift 위험. (현재 매칭 시 `_find_in_catalog`가 이름으로 정본 항목을 다시 끌어오므로 실사용 값은 카탈로그 기준으로 복원됨.)

### B. FE `KEYWORD_INDICATOR_MAP` (`AddIndicatorSheet.tsx`, 28개 규칙) — 🟢 고아 없음

규칙은 **지표 ID 배열**(`indicatorIds`)로 참조한다. 28개 규칙이 참조하는 모든 ID(1,2,3,4,6,7,8,9,10,11,12,15,16,20,21,23,24,25,26,30,31,32,33,34,35,36,37,39,40,50,51,52,53,54,55,56,57,58,60,61,62,63,64,65,66,67,68,69,70,71,72,73)는 전부 카탈로그에 존재.

- **고아 ID 참조: 0건.**

### C. BE↔FE keyword 시스템 미동기화 🔴

- BE는 **11규칙·이름기반·Gemini fallback 포함**, FE는 **28규칙·ID기반·점수 정렬**으로 완전히 다른 구현.
- FE가 훨씬 풍부 (유가/금/구리/비트코인/밸류에이션/재무건전성/주택 등 BE에 없는 키워드 다수).
- 동일 전제 텍스트에 대해 BE 추천(서버)과 FE 추천(클라이언트)이 **다른 지표 집합**을 낼 수 있다. 단일 소스가 아니므로 한쪽 수정 시 다른 쪽 누락 위험.

---

## data_params 형식

### 1. serializer 허용 키 ↔ 카탈로그 어휘 불일치 🔴 (핵심 발견)

`indicator_serializers.py`의 검증 계약:

```python
ALLOWED_DATA_PARAM_KEYS = {'symbol', 'series_id', 'metric', 'indicator', 'period'}
MAX_DATA_PARAMS_SIZE = 5
```

그러나 카탈로그가 실제 사용하는 키 중 **8개가 allowlist에 없음**:

| 미허용 키 | 사용 지표 | 용도 |
|---|---|---|
| `metric_code` | id 60~73 (재무 체질 14개, `data_source='metrics'`) | 분기 지표 코드 |
| `inverse` | id 50 PER | `1/value` 후처리 |
| `scale_multiplier` | id 52 ROE, 53 ROA, 58 매출성장률 | `×N` 후처리 |
| `audit_note` | id 50, 52, 53, 58 | 회귀 방지 주석 |
| `endpoint` | id 58 매출성장률 | financial-growth 분기 |
| `fast`/`slow`/`signal` | id 40 MACD | 기술 지표 파라미터 |

**영향 경로 분석**:
- 카탈로그 → ThesisIndicator 생성은 `thesis_builder.py`가 **ORM `ThesisIndicator.objects.create(data_params=...)`로 직접 저장** → serializer `validate_data_params`를 **우회**하므로 카탈로그 항목은 정상 저장됨 (현재 런타임 깨지지 않음).
- 그러나 **사용자/FE가 동일 형식으로 지표를 POST/PATCH**하면 (`ThesisIndicatorSerializer` 경유) 위 키들이 `허용되지 않은 키` 에러로 **거부**된다. 즉 카탈로그가 쓰는 어휘를 사용자 입력에선 재현 불가 — 계약 불일치.
- `MAX_DATA_PARAMS_SIZE=5`: 카탈로그 최대 키 수는 id 58의 4개(`metric/endpoint/scale_multiplier/audit_note`)로 개수 한도는 통과. 문제는 키 **종류**(allowlist)뿐.

**권장(보고용)**: allowlist에 `metric_code, inverse, scale_multiplier, endpoint, fast, slow, signal` 추가, 또는 카탈로그 후처리 메타(`audit_note` 등)를 data_params 밖으로 분리. (코드 수정은 본 감사 범위 외)

### 2. data_source별 fetch 형식 정합성 (`eod_pipeline.py`)

| data_source | 기대 키 | fetcher 처리 | 정합 |
|---|---|---|---|
| `fred` | `series_id` | `_fetch_fred_value` | 🟢 일치 |
| `metrics` | `metric_code` | `_fetch_metrics_value` → `fetch_quarterly_metric` | 🟢 일치 |
| `news_sentiment` | (id 11은 `{}`) | `_fetch_news_sentiment_value`는 `params['symbol']` 요구 | 🟡 §3 참조 |
| `fmp` (symbol) | `symbol` | `client.get_quote` | 🟡 §4 참조 |
| `fmp` (TTM/growth) | `metric`(+endpoint/inverse/scale) | `_fetch_fmp_ttm_or_growth` | 🟡 §5 참조 |

### 3. 뉴스 센티먼트 data_params 공백 🟡

- 카탈로그 id 11 `뉴스 센티먼트`의 data_params는 `{}` (빈 dict).
- `_fetch_news_sentiment_value`는 `params.get('symbol')`이 없으면 `symbol 없음` 경고 후 `None` 반환.
- 빌더(`thesis_builder.py` L1180~1183)가 생성 시 `target_symbol`을 data_params에 병합하므로 실제 저장 시점엔 symbol이 채워질 수 있으나, **카탈로그 정의 자체로는 fetch 불가**한 상태 (symbol 주입 의존).

### 4. FMP 심볼 형식 — 제공자 불일치 위험 🔴/🟡

| id | 지표 | 카탈로그 metric/symbol | 위험 | 근거 |
|---|---|---|---|---|
| 1 | 외국인 순매수 추이 | `metric: foreign_net_buy` | 🔴 **항상 실패** | `_fetch_fmp_value` value_map에 없음 → `quote.get('foreign_net_buy')` → FMP `/stable/quote`에 해당 필드 부재 → `None` |
| 2 | 기관 순매수 추이 | `metric: institutional_net_buy` | 🔴 **항상 실패** | 동일 (FMP quote는 외국인/기관 순매수 미제공) |
| 4 | KOSPI | `symbol: ^KS11` | 🟡 검증 필요 | FMP `/stable` 한국 지수 지원 여부 불확실 |
| 14 | 코스닥 | `symbol: ^KQ11` | 🟡 검증 필요 | 동일 |
| 9 | 원/달러 환율 | `symbol: USDKRW` | 🟡 검증 필요 | FMP forex 심볼 표기 형식 확인 필요 |
| 39 | 달러 인덱스 | `symbol: DX-Y.NYB` | 🟡 검증 필요 | `DX-Y.NYB`는 Yahoo 표기 — FMP DXY 심볼과 다를 가능성 |

> id 1·2는 정적 분석만으로 **항상 `None` 반환**이 확정적(FMP quote 필드 부재). 한국 시장 수급 데이터는 FMP(미국 중심) 제공 범위 밖이므로 별도 제공자 필요.

### 5. FMP TTM 필드 — key-metrics-ttm 존재 여부 🟡

`_fetch_fmp_ttm_or_growth`는 `metric.endswith('TTM')`이면 무조건 `/stable/key-metrics-ttm`의 `data[0].get(metric)`을 읽는다. audit_note로 명시 검증된 것은 일부뿐:

| id | metric | audit_note 여부 | 비고 |
|---|---|---|---|
| 50 | earningsYieldTTM (+inverse) | ✅ 명시 (#14) | PER=1/값 |
| 52 | returnOnEquityTTM (+×100) | ✅ 명시 (#14) | ROE % 변환 |
| 53 | returnOnAssetsTTM (+×100) | ✅ 명시 | ROA % 변환 |
| 58 | growthRevenue (financial-growth) | ✅ 명시 | endpoint 분기 |
| 51 | pbRatioTTM | ❌ 미검증 | key-metrics-ttm 존재 가정 |
| 54 | debtToEquityTTM | ❌ 미검증 | 동일 |
| 55 | freeCashFlowTTM | ❌ 미검증 | 동일 |
| 56 | dividendYieldTTM | ❌ 미검증 | ratios-ttm 소속일 가능성 |
| 57 | operatingProfitMarginTTM | ❌ 미검증 | ratios-ttm 소속일 가능성 (key-metrics-ttm 부재 시 `None`) |

> #14 회귀(필드명/스케일 불일치)와 동일 계열 위험. 미검증 5개 필드는 FMP 실응답으로 존재·스케일을 확인해야 한다. 특히 `operatingProfitMarginTTM`/`dividendYieldTTM`은 통상 key-metrics가 아닌 ratios 계열 엔드포인트에 존재 → 현재 코드 경로(key-metrics-ttm 단일)에서 누락 시 조용히 `None`.

---

## 결론 및 우선순위

| 우선순위 | 항목 | 분류 |
|---|---|---|
| **P0** | id 1·2 수급 지표 FMP fetch 항상 실패 (필드 부재) | 데이터 갭 — 제공자 부재 |
| **P0** | serializer allowlist ↔ 카탈로그 data_params 어휘 불일치 (8키) | 계약 불일치 |
| **P1** | FMP 심볼 형식 검증 (^KS11/^KQ11/USDKRW/DX-Y.NYB) | 제공자 형식 |
| **P1** | TTM 미검증 5필드 (특히 operatingProfitMarginTTM/dividendYieldTTM) | #14 계열 회귀 위험 |
| **P2** | BE/FE keyword 매칭 이중 구현 미동기화 | 단일 소스 부재 |
| **P2** | FE category 수동 분류 + description 미표시 | UX/동기화 부담 |
| **P3** | indicator_matcher EPS 규칙 indicator_type drift | 인라인 중복 |

**동기화 핵심**: 지표 목록(ID/이름) 동기화는 모범적. 그러나 **data_params 어휘·keyword 매칭 로직·category 분류**가 BE/FE/serializer 3곳에 분산 미러되어 있어, 신규 지표 추가 시 수동 동기화 지점이 최소 4곳(BE 카탈로그, FE 미러, FE keyword map, serializer allowlist)이다. 단일 소스화가 근본 개선 방향.

*— 본 보고서는 정적 분석 기반이며, FMP 실응답 검증(P1 항목)은 런타임 확인이 필요하다. 코드는 수정하지 않았다.*

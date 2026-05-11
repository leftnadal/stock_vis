# 지표 카탈로그 동기화 감사 보고서

- 작성일: 2026-04-28
- 대상 브랜치: feature/chainsight-graph-v2
- 감사 범위: thesis 앱 INDICATOR_CATALOG 단일 소스 정합성 (BE 정의 / FE 미러 / keyword_rules / EOD 데이터 파이프라인)
- 작성자: Claude (read-only audit, 코드 변경 없음)

## 요약 (동기화 상태)

| 검사 항목 | 결과 | 비고 |
|---|---|---|
| BE ↔ FE 카탈로그 ID 일치 | OK | 64개 ID 완전 동일 |
| BE ↔ FE 카탈로그 이름 일치 | OK | 64개 모두 동일 문자열 |
| BE ↔ FE 빈도(frequency) 일치 | OK | 14건 spot check 모두 일치 |
| description 빈/과소 | OK | 64/64 모두 description 존재 (≥16자) |
| keyword_rules 고아 | OK | indicator_matcher.py의 11개 name 모두 카탈로그에 존재 |
| keyword_rules 커버리지 | **WARN** | BE는 64건 중 11건만 fallback 매칭 (17%). FE는 27 그룹·40+ ID로 더 광범위 — BE/FE 매칭 규칙 미러링 자체가 안 됨 |
| BE keyword_rules 표현 방식 | **WARN** | name 문자열 참조 (id 미사용). 카탈로그 이름 변경 시 silent break 위험 |
| data_params ↔ EOD fetcher 정합 | **CRIT** | 64건 중 19건이 현재 fetcher로 값 수집 불가 (technical 9건 + TTM ratio 9건 + custom_metric 1건). 자세한 목록은 §5 참조 |
| FE 미러 위치 | NOTE | sub_claude_md/coding-rules.md 등 사이드 문서가 "INDICATOR_CATALOG 미러는 3곳"이라고 명시하나, 실제 코드에서 확인된 미러는 prompt_builder.py·llm_postprocess.py·indicator_matcher.py(BE)와 AddIndicatorSheet.tsx(FE) 외에 추가 미러는 발견되지 않음 |

핵심 결론: **카탈로그 정의 자체(ID/이름/description)는 완벽히 동기화되어 있다. 그러나 카탈로그가 약속한 `data_source/data_params`를 실제로 fetch하는 EOD 파이프라인 함수가 19개 지표를 처리하지 못한다.** 카탈로그에서는 RSI·MACD·PER 등이 "fmp 데이터 소스에서 자동 fetch되는 지표"처럼 보이지만, 실제 `_fetch_fmp_value`는 `/stable/quote` 한 종류만 호출한다. 이는 동기화 문제라기보다는 카탈로그-파이프라인 계약의 단절이다.

---

## 1. BE ↔ FE 불일치 목록

### 결과: 불일치 없음

`thesis/services/prompt_builder.py:14-294`(BE, 64개)와 `frontend/components/thesis/AddIndicatorSheet.tsx:15-91`(FE, 64개)의 ID·이름·빈도 비교:

- **BE-only 지표**: 0건
- **FE-only 지표**: 0건
- **이름 불일치**: 0건 (`'외국인 순매수 추이'`, `'EPS 추이'`, `'미국 기준금리 (Fed Funds Rate)'` 등 64개 한글/괄호 표기까지 동일)
- **빈도(`INDICATOR_FREQUENCY` vs FE `freq`) spot check**: id 6 주간/주간 ✓, id 7 일간/일간 ✓, id 31 월간/월간 ✓, id 34 분기/분기 ✓, id 37 주간/주간 ✓, id 50~73 전부 분기 ✓ — 일치

다만 카테고리 라벨 분류는 BE 5개(`market_data/macro/technical/fundamental/sentiment`)인 반면 FE는 17개(`수급/주요 지수/원자재/암호화폐/금리/환율·변동성/고용·성장/물가·주택/기술적/펀더멘털/재무 체질/밸류에이션/성장/운영 효율/이익 품질/주주환원/심리`)로 더 세분화된다. 이는 BE의 5개 카테고리를 FE에서 표시 목적으로 쪼갠 것이라 데이터 정합성 문제는 아니다. 다만 **BE에서 카테고리를 추가/이동할 때 FE도 같은 시점에 라벨 매핑을 손봐야** 한다 (현재는 두 곳 모두 정적 상수).

---

## 2. description 품질

### 결과: 양호

전체 64개 항목을 검토한 결과 **빈 description 0건, 10자 미만 description 0건**. 가장 짧은 description도 16자 이상 ("한국 중소형 성장주 시장 지수.", id 14).

품질 측면에서 추가 관찰:

- 모든 description이 "지표 설명 + 활용 맥락" 1~2문장 패턴을 일관되게 따른다. 예: id 23 "구리 선물 가격. 경기 선행지표로 'Dr. Copper'라 불림."
- support_direction의 의도가 description에 자연스럽게 녹아 있는 항목이 많다 (id 6/7/30 모두 'negative' + "금리 인상은 주식에 부정적" 류 문장).
- 정량적 임계치를 포함한 항목: id 10 "과매수(>70)/과매도(<30)" — 좋은 예. 다만 RSI 외 ATR(43)·OBV(44) 등은 임계치 없음 (개선 여지: 임계치 또는 "방향만 본다" 명시).
- prompt_builder.py의 `get_indicator_description()`(:335-345)이 접두사 매칭을 지원하므로, LLM이 "EPS 추이 (META)"처럼 심볼을 붙여도 description 조회가 동작한다. 이 helper 자체는 문제 없음.

---

## 3. keyword_rules 고아 / 커버리지

### 3.1 고아 규칙: 없음

`thesis/services/indicator_matcher.py:12-154` KEYWORD_RULES가 참조하는 11개 지표 이름 (전부 카탈로그에 존재):

| keyword_rules name | 카탈로그 ID | 존재 |
|---|---|---|
| `'외국인 순매수 추이'` | 1 | ✓ |
| `'기관 순매수 추이'` | 2 | ✓ |
| `'미국 기준금리 (Fed Funds Rate)'` | 6 | ✓ |
| `'미국 10년 국채 금리'` | 7 | ✓ |
| `'VIX (공포지수)'` | 8 | ✓ |
| `'원/달러 환율'` | 9 | ✓ |
| `'RSI (14일)'` | 10 | ✓ |
| `'뉴스 센티먼트'` | 11 | ✓ |
| `'EPS 추이'` | 5 | ✓ |
| `'S&P 500'` | 3 | ✓ |
| `'KOSPI 지수'` | 4 | ✓ |

### 3.2 커버리지 갭

BE keyword_rules는 **카탈로그 64개 중 11개(17%)만 fallback 매칭**한다. 53개 지표는 LLM이 indicator_db_id를 잘못 반환했을 때 텍스트 fallback이 동작하지 않는다. 특히 다음 카테고리는 fallback 0건:

- 원자재/암호화폐 (id 20~26): 7개 미커버 — FE에는 '유가/wti/구리/금/비트코인' 등 키워드가 있음
- 추가 금리/환율 (id 30, 37, 38, 39): 4개 미커버 — FE에는 '강달러/달러인덱스' 등 키워드 있음
- 거시 고용/성장/물가/주택 (id 31~36): 6개 미커버 — FE에는 'cpi/실업/nfp/gdp/주택' 등 키워드 있음
- 기술적 지표 RSI 외 (id 40~47): 8개 미커버
- 펀더멘털 비율/재무 체질 전체 (id 50~73): 24개 미커버 — FE에는 'per/pbr/roe/부채/배당/회전율/이익품질' 등 키워드 있음
- 추가 지수 (id 12~16): 5개 미커버 — FE에는 '나스닥/항셍/니케이' 등 키워드 있음

대비되는 위치: **FE `KEYWORD_INDICATOR_MAP`** (`AddIndicatorSheet.tsx:109-139`)는 27개 키워드 그룹 × 40+ 카탈로그 ID를 매핑한다. 즉 추천 규칙의 두 미러가 **이름이 같은데 내용이 다른** 상태. UI에서 추천된 지표가 LLM fallback에서는 매칭되지 않는 비대칭이 존재한다.

### 3.3 표현 방식 위험

`KEYWORD_RULES`는 카탈로그 이름 문자열로 지표를 참조한다 (`'name': '미국 기준금리 (Fed Funds Rate)'`). 카탈로그에서 이름을 미세하게 바꾸면(예: "Fed Funds" → "FFR") 매칭이 조용히 사라진다. 반면 FE `KEYWORD_INDICATOR_MAP`은 ID 정수로 참조하므로 안전하다. **BE도 ID 기반으로 통일하는 편이 안전하다.**

또한 BE keyword_rules의 indicators 항목은 카탈로그 정보(`data_source`, `data_params`, `indicator_type`, `support_direction`)를 다시 한 번 인라인으로 복제한다. 카탈로그에서 한쪽 값이 바뀌어도 keyword_rules에는 반영되지 않으므로 데이터 소스 변경 시 정합성이 깨질 수 있다. (예시: 카탈로그에서 어떤 지표를 `fmp` → `metrics`로 바꿔도 keyword_rules는 여전히 fmp를 반환할 수 있음.)

---

## 4. data_params ↔ EOD fetcher 형식 불일치

### 4.1 fetcher가 기대하는 형식 (`thesis/tasks/eod_pipeline.py:25-194`)

| data_source | 필수 키 | 선택 키 | fetcher 동작 |
|---|---|---|---|
| `fmp` | `symbol` | `metric` (기본 'price') | `client.get_quote(symbol)` 호출, value_map에서 `metric` → quote 응답 필드명 변환 |
| `fred` | `series_id` | — | `FREDClient.get_latest_value(series_id)` |
| `news_sentiment` | `symbol` | — | `NewsArticle.objects.filter(entities__symbol=symbol, ...)` 평균 |
| `metrics` | `metric_code` | `symbol` (없으면 `thesis.target`) | `fetch_quarterly_metric(symbol, metric_code)` |

`_fetch_fmp_value`의 value_map (라인 53-63)은 다음 9개 metric만 처리한다:
`price, change_percent, volume, pe, eps, market_cap, previous_close, day_high, day_low`

위 9개 외의 metric 값은 `value_map.get(metric, metric)` 폴스루로 metric 문자열 자체를 quote 응답의 필드명으로 사용한다. FMP `/stable/quote` 응답에는 그런 필드가 없어 항상 `None` 반환.

### 4.2 카탈로그 항목별 fetcher 정합 분석

#### A. 정상 동작 (45건)

- **시장 지수** (3,4,12,13,14,15,16): `data_params={'symbol':'^GSPC'}` 등 → quote price ✓
- **원자재/암호화폐** (20,21,22,23,24,25,26): `data_params={'symbol':'GCUSD'}` 등 → quote price ✓
- **변동성·환율** (8,9,39): symbol 정상 ✓
- **FRED 거시** (6,7,30,31,32,33,34,35,36,37,38): series_id 정상 ✓
- **펀더멘털 metrics** (60~73, 14건): `data_source='metrics'` + `metric_code` → `_fetch_metrics_value`가 `thesis.target`으로 symbol 보충 → ✓
- **EPS** (id 5): `metric='eps'`는 value_map에 존재. **단 `target_symbol`이 LLM에서 채워져야 동작.** thesis_builder.py:1156이 LLM의 target_symbol을 `data_params['symbol']`로 병합하므로 LLM이 메타프롬프트(`prompt_builder.py:399-403`)대로 종목 ticker를 넣어주면 ✓.

#### B. 부분 동작 / 의존성 있음 (1건)

- **뉴스 센티먼트** (id 11): `data_params={}` 비어있음. `_fetch_news_sentiment_value`는 `symbol` 필수. LLM이 `target_symbol`을 채워야만 builder가 `data_params['symbol']`을 주입(thesis_builder.py:1156). **target_symbol 누락 시 항상 None.**

#### C. 잘못된 형식 — fetcher 미지원 (19건, **CRIT**)

| ID | 이름 | 카탈로그 data_params | 실제 문제 |
|---|---|---|---|
| 1 | 외국인 순매수 추이 | `{'metric':'foreign_net_buy'}` | `metric='foreign_net_buy'`는 value_map에 없음. fmp 단순 quote 응답에 해당 필드 없음. **항상 None.** symbol도 누락 |
| 2 | 기관 순매수 추이 | `{'metric':'institutional_net_buy'}` | 동일 — value_map miss + symbol 없음 |
| 50 | PER (TTM) | `{'metric':'peRatioTTM'}` | TTM 비율은 FMP `/stable/key-metrics-ttm` 또는 `/stable/ratios-ttm`에서 와야 함. 현 fetcher는 quote만 호출. value_map에 'peRatioTTM' 없음 → quote.get('peRatioTTM') = None |
| 51 | PBR (TTM) | `{'metric':'pbRatioTTM'}` | 동일 |
| 52 | ROE (TTM) | `{'metric':'returnOnEquityTTM'}` | 동일 |
| 53 | ROA (TTM) | `{'metric':'returnOnAssetsTTM'}` | 동일 |
| 54 | 부채비율 | `{'metric':'debtToEquityTTM'}` | 동일 |
| 55 | FCF (TTM) | `{'metric':'freeCashFlowTTM'}` | 동일 |
| 56 | 배당수익률 | `{'metric':'dividendYieldTTM'}` | 동일 |
| 57 | 영업이익률 | `{'metric':'operatingProfitMarginTTM'}` | 동일 |
| 58 | 매출성장률 | `{'metric':'revenueGrowthYoY'}` | FMP TTM 엔드포인트에 그런 키 없음. financial-growth 또는 income-statement-growth 호출 필요 |
| 10 | RSI (14일) | `{'indicator':'RSI','period':14}` | `_fetch_fmp_value`는 `params.get('symbol')`로 시작 → symbol 누락이라 **즉시 None 반환**. 또한 fetcher는 quote만 호출하고 `/stable/technical-indicators/RSI` 엔드포인트는 부르지 않음 |
| 40 | MACD | `{'indicator':'MACD',...}` | 동일 |
| 41 | 스토캐스틱 %K | `{'indicator':'stochastic',...}` | 동일 |
| 42 | 볼린저 밴드 %B | `{'indicator':'bollinger',...}` | 동일 |
| 43 | ATR | `{'indicator':'ATR',...}` | 동일 |
| 44 | OBV | `{'indicator':'OBV'}` | 동일 |
| 45 | SMA 50일 | `{'indicator':'SMA','period':50}` | 동일 |
| 46 | SMA 200일 | `{'indicator':'SMA','period':200}` | 동일 |
| 47 | EMA 12일 | `{'indicator':'EMA','period':12}` | 동일 |

19건 중 **technical 9건은 두 단계 결함** (symbol 누락 + 전용 endpoint 미호출). LLM이 `target_symbol`을 채워줘도 quote 가격만 가져오고 RSI 값은 못 가져온다.

**TTM 펀더멘털 9건**은 카탈로그가 `metric_code` 키마저 일관성 없이 사용 — id 50~58은 `metric` 키에 TTM 필드명을 박았지만 id 60~73(같은 펀더멘털 카테고리)은 `metric_code` 키에 metrics 앱 코드를 사용한다. 같은 가설에서 PER(50)와 ROIC(62)를 동시에 추천하면 한쪽은 동작하고 한쪽은 동작하지 않는 비대칭이 발생한다.

### 4.3 normalize 단계의 ID 교정만 있고 형식 검증은 없음

`thesis/services/llm_postprocess.py:84-89`는 LLM이 카탈로그에 없는 `indicator_db_id`를 반환하면 `None`으로 교정한다. 그러나 **카탈로그 자체의 `data_params` 형식이 fetcher와 맞는지는 검증하지 않는다.** 결과적으로 잘못된 형식이 그대로 ThesisIndicator에 저장되고 매일 EOD 파이프라인에서 조용히 None이 쌓인다 (`validation_status='null_value'`).

---

## 5. 권장 조치 (제안만, 본 보고서는 코드 수정하지 않음)

### 5.1 즉시 (Critical)

1. **technical 9건 (id 10, 40~47)**: `data_source`를 `fmp`가 아닌 `fmp_technical`로 분리하고 전용 fetcher 추가, 또는 `_fetch_fmp_value`에서 `params.get('indicator')`가 있을 때 `/stable/technical-indicators/{indicator}` 호출 분기. `data_params`에 `symbol` 키 강제 (LLM target_symbol 의존 금지).
2. **TTM 펀더멘털 9건 (id 50~58)**: `data_source`를 `fmp_ttm`으로 분리하거나, 기존 `metrics` 데이터 소스로 통일하고 metric_code를 매핑 (이미 id 60~73이 같은 펀더멘털 카테고리에서 metrics를 쓰고 있으므로 통일이 자연스러움).
3. **id 1, 2 (외국인/기관 순매수)**: FMP에 직접 대응 엔드포인트가 없음. 별도 데이터 소스를 정의하거나 `data_source='manual'`로 마킹.
4. **id 11 (뉴스 센티먼트)**: `data_params={'symbol': null}` 같은 placeholder를 두고 빌더에서 `target_symbol` 누락 시 검증 실패시키기.

### 5.2 구조 개선

5. **카탈로그 ↔ fetcher 계약 검증 테스트** 추가: `tests/thesis/test_indicator_catalog_fetchers.py`에서 64건 모두 dummy input으로 fetcher 분기를 통과하는지(KeyError·None 반환 사유) 단위 테스트.
6. **keyword_rules ID 통일**: BE `KEYWORD_RULES`를 ID 참조로 바꾸고 indicators 인라인 복제를 제거. `match_by_keywords`가 카탈로그를 lookup하도록.
7. **BE/FE 키워드 매핑 단일 소스**: `KEYWORD_INDICATOR_MAP`(FE)을 BE에 옮기고 API로 노출, 또는 contracts/에 JSON 단일 소스 두기. 현재 BE 11그룹/FE 27그룹은 sub_claude_md/coding-rules.md의 "3곳 동시 업데이트" 원칙을 이미 위반.

### 5.3 운영 가시성

8. EOD 파이프라인에서 `validation_status='null_value'` 누적 카운트가 특정 지표에서 7일 이상 연속이면 alert 또는 admin 대시보드에 표시 (현재 로그에만 집계).

---

## 6. 검사한 파일 목록

| 파일 | 용도 |
|---|---|
| thesis/services/prompt_builder.py:14-294 | INDICATOR_CATALOG (BE 단일 소스, 64개) |
| thesis/services/prompt_builder.py:305-326 | INDICATOR_FREQUENCY (빈도 매핑) |
| thesis/services/prompt_builder.py:335-345 | get_indicator_description (접두사 매칭) |
| thesis/services/llm_postprocess.py:82-89 | indicator_db_id 정규화 (카탈로그 검증) |
| thesis/services/indicator_matcher.py:12-154 | KEYWORD_RULES (BE keyword fallback) |
| thesis/services/indicator_matcher.py:271-329 | match_indicators_for_llm (PK 우선 매칭) |
| thesis/services/thesis_builder.py:1148-1173 | ThesisIndicator 생성 (target_symbol 주입) |
| thesis/tasks/eod_pipeline.py:25-194 | DATA_SOURCE_FETCHERS (실제 fetch 진입점) |
| thesis/models/indicator.py:6-106 | ThesisIndicator 모델 |
| frontend/components/thesis/AddIndicatorSheet.tsx:15-91 | INDICATOR_CATALOG (FE 미러, 64개) |
| frontend/components/thesis/AddIndicatorSheet.tsx:109-139 | KEYWORD_INDICATOR_MAP (FE keyword 매핑) |

본 보고서는 정적 분석만 수행했으며 실제 EOD 파이프라인 실행 결과(IndicatorReading 테이블의 validation_status 분포)는 별도 SQL 검증이 필요하다. 추가 검증 쿼리 예시:

```sql
SELECT ind.name, count(*) FILTER (WHERE r.validation_status='null_value') AS nulls,
       count(*) AS total
FROM thesis_indicatorreading r
JOIN thesis_thesisindicator ind ON ind.id = r.indicator_id
WHERE r.fetched_at > now() - interval '7 days'
GROUP BY ind.name
HAVING count(*) FILTER (WHERE r.validation_status='null_value') = count(*)
ORDER BY total DESC;
```

이 쿼리에서 항상 null만 나오는 지표 이름이 §4.2.C 19건과 일치하면 본 보고서 분석이 운영 데이터로 입증된다.

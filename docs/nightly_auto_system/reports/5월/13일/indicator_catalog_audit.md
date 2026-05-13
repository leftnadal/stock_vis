# 지표 카탈로그 동기화 감사 보고서

- 생성일: 2026-05-13
- 감사 범위: BE 카탈로그(`thesis/services/prompt_builder.py`), FE 미러(`frontend/components/thesis/AddIndicatorSheet.tsx`),
  BE 키워드 룰(`thesis/services/indicator_matcher.py` `KEYWORD_RULES`), FE 키워드 룰(`AddIndicatorSheet.tsx` `KEYWORD_INDICATOR_MAP`),
  후처리(`thesis/services/llm_postprocess.py`), 데이터 fetch(`thesis/tasks/eod_pipeline.py`), 분기 엔진(`thesis/services/quarterly_metric_fetcher.py`)
- 모드: 읽기 전용 (코드 수정 없음)

---

## 요약 (동기화 상태)

| 항목 | 상태 | 비고 |
|------|------|------|
| BE↔FE 지표 ID 집합 동기화 | ✅ 100% (64개 동일) | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 20~26, 30~47, 50~58, 60~73 |
| BE↔FE 지표 이름 동기화 | ✅ 64/64 완전 일치 | 표기/괄호 포함 모두 일치 |
| BE↔FE 주기(frequency) 동기화 | ✅ 64/64 완전 일치 | 일/주/월/분기 매핑 동일 |
| BE description 누락 | ✅ 없음 | 64/64 모두 존재 |
| BE description 너무 짧음(<10자) | ✅ 없음 | 최단 33자 ('한국 중소형 성장주 시장 지수.') |
| BE↔FE 카테고리 라벨 | ⚠️ 의도적 불일치 | BE 5개 광역(`market_data/macro/technical/fundamental/sentiment`) vs FE 17개 세분 UI 라벨 |
| `KEYWORD_RULES`(BE) ↔ `INDICATOR_CATALOG` 매핑 | ✅ 11/11 지표 이름 카탈로그에 존재 | 고아 규칙 없음 |
| `KEYWORD_RULES`(BE) ↔ `KEYWORD_INDICATOR_MAP`(FE) 커버리지 | ⚠️ BE 11종 vs FE 28종 (큰 격차) | BE는 펀더멘털·원자재·섹터 키워드 대다수 누락 |
| `data_params` 형식 — fmp 일반(symbol/metric) | ✅ `eod_pipeline._fetch_fmp_value` 분기 처리 |
| `data_params` 형식 — fmp TTM/growth(`endpoint`, `inverse`, `scale_multiplier`) | ✅ `_fetch_fmp_ttm_or_growth` + `_apply_value_postprocess` 처리 |
| `data_params` 형식 — `data_source='metrics'`(`metric_code`) | ⚠️ `quarterly_metric_fetcher`의 14개 코드와 1:1 매칭되지만, **eod_pipeline 측 metrics 분기 라우팅은 본 감사 범위에서 미확인** |
| 자가 표시 audit_note 위반(prompt_builder.py 자체 코멘트) | ⚠️ id 58 매출성장률은 `권장: data_source='metrics'` 코멘트와 실제 구현(`fmp`) 불일치 |

전반: **BE↔FE 카탈로그 64개는 ID/이름/주기 완벽 동기화**. 문제는 (a) BE 키워드 룰이 FE 대비 매우 얕음, (b) PER/ROE/ROA/매출성장률 같은 펀더멘털이 `data_source='fmp'`로 잔존(`metrics` 로 일원화하지 못함), (c) BE 키워드 룰 일부는 `S&P` / `RSI` 등 영문이 대문자 토큰 그대로 들어가 있어 `text_lower.includes` 또는 정확 일치 비교 흐름과 어긋날 수 있음 (아래 keyword_rules 절 참조) 정도다.

---

## BE ↔ FE 불일치 목록

### 지표 ID/이름/주기 — 불일치 없음
- BE 카탈로그 ID 집합: {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 20, 21, 22, 23, 24, 25, 26, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 50, 51, 52, 53, 54, 55, 56, 57, 58, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73} (총 64)
- FE 카탈로그 ID 집합: 위와 동일 (총 64)
- 차집합: ∅ / ∅
- 이름 일치: 64/64 (예: id 3 `S&P 500`, id 39 `달러 인덱스 (DXY)`, id 41 `스토캐스틱 %K` 등 특수문자 포함 표기까지 일치)
- 주기(`INDICATOR_FREQUENCY` vs FE `freq`): 64/64 일치

### 카테고리 라벨 — 의도적 차이 (참고용)
| ID 범위 | BE `category` | FE `category` |
|---------|---------------|---------------|
| 1, 2 | `market_data` | `수급` |
| 3, 4, 12~16 | `market_data` | `주요 지수` |
| 20~24 | `market_data` | `원자재` |
| 25, 26 | `market_data` | `암호화폐` |
| 6, 7, 30, 37 | `macro` | `금리` |
| 8, 9, 38, 39 | `macro` | `환율/변동성` |
| 31, 32, 34, 35 | `macro` | `고용/성장` |
| 33, 36 | `macro` | `물가/주택` |
| 10, 40~47 | `technical` | `기술적` |
| 5, 50~58 | `fundamental` | `펀더멘털` |
| 60~66 | `fundamental` | `재무 체질` |
| 67, 68 | `fundamental` | `밸류에이션` |
| 69 | `fundamental` | `성장` |
| 70, 71 | `fundamental` | `운영 효율` |
| 72 | `fundamental` | `이익 품질` |
| 73 | `fundamental` | `주주환원` |
| 11 | `sentiment` | `심리` |

판정: 이 매핑은 BE 백엔드 그룹핑(5분류, 프롬프트 카탈로그 출력용 `CATEGORY_LABELS`)과 FE UI 분류(17분류, `AddIndicatorSheet`의 `categoryOrder`)가 의도적으로 다른 것으로 보임. 단, FE→BE 단방향 매핑 함수가 없으므로 향후 BE→FE category로 자동 변환을 시도할 때 깨질 수 있음. 변환 함수가 새로 필요해질 경우 위 매핑표를 단일 소스로 사용 권장.

### description 동기화
- BE `INDICATOR_CATALOG` 64개 전부 `description` 필드 보유.
- FE `CatalogIndicator` 타입은 `description` 필드 자체가 없음(`id/name/category/freq`만). 따라서 FE는 BE description 변화에 영향받지 않음 — 동기화 의무 없음.
- 단, 향후 FE에서 카탈로그 항목 위에 hover 툴팁/설명 UI를 도입할 경우 BE의 description을 API로 노출하거나 FE 미러에 추가해야 함 (현재는 미노출).

---

## description 품질

### 누락
- 없음 (64/64 모두 존재).

### 너무 짧음 (<10자)
- 없음. 최단 description은 id 14 `코스닥 지수` → `한국 중소형 성장주 시장 지수.` (15자, 마침표 포함). 다른 모든 항목 20자 이상.

### 품질 관찰
- 평균 길이 약 35~50자, 모두 마침표로 종결되어 일관성 양호.
- audit_note가 별도 필드(`data_params.audit_note`)로 들어간 4개 항목(id 50, 52, 53, 58)은 description과 데이터 처리 메타가 분리되어 있어 가독성 양호.
- (참고) 카테고리 라벨이 description에 반복되지 않는다는 점에서 토큰 효율 OK. 변경 권고 없음.

---

## keyword_rules 고아

### BE `KEYWORD_RULES`(`indicator_matcher.py:12`) — 11개 룰, 모두 카탈로그에 존재
| 룰 # | 키워드 (대표) | 매핑 지표(name) | 카탈로그 존재 |
|------|--------------|----------------|--------------|
| 1 | 외국인/외인/순매수/foreign | `외국인 순매수 추이` | ✅ id 1 |
| 2 | 금리/연준/FOMC | `미국 기준금리 (Fed Funds Rate)`, `미국 10년 국채 금리` | ✅ id 6, 7 |
| 3 | VIX/공포/변동성 | `VIX (공포지수)` | ✅ id 8 |
| 4 | 환율/달러/원달러/USD/KRW | `원/달러 환율` | ✅ id 9 |
| 5 | RSI/MACD/기술적 | `RSI (14일)` | ✅ id 10 |
| 6 | 센티먼트/여론/뉴스 | `뉴스 센티먼트` | ✅ id 11 |
| 7 | 실적/EPS/매출/PER/earnings | `EPS 추이` | ✅ id 5 |
| 8 | 기관/연기금/보험 | `기관 순매수 추이` | ✅ id 2 |
| 9 | S&P/S&P500/나스닥/NASDAQ | `S&P 500` | ✅ id 3 |
| 10 | 코스피/KOSPI | `KOSPI 지수` | ✅ id 4 |
| 11 | 선거/정치/정책/대통령/국회 | `VIX (공포지수)`, `KOSPI 지수` | ✅ id 8, 4 |

**고아(카탈로그 미존재) 규칙: 0건**

### BE `KEYWORD_RULES`의 잠재 결함(매칭 로직)
- `indicator_matcher.match_by_keywords` 본문(line 161~165):
  ```python
  text_lower = premise_text.lower()
  for rule in KEYWORD_RULES:
      for keyword in rule['keywords']:
          if keyword.lower() in text_lower or keyword in premise_text:
  ```
- 룰 #5(`'RSI'`)와 #8(`'NASDAQ'`)처럼 영문 키워드가 대문자로 정의되어 있어도 `keyword.lower()` 비교가 있어 동작. 다만 `'S&P'`, `'MA'`(이동평균 약어, 룰 #5에 존재)는 다른 한국어 텍스트에서 `'MA'` → `'서머'`처럼 부분 매칭 오탐 우려. 이는 BE 키워드 룰 자체 결함으로 보임 (별도 이슈).
- 룰 #7의 `'PER'`는 키워드 매칭 시 `'super'`, `'experienced'` 같은 텍스트도 트리거함 (`.includes` 의미상). 한국어 전제 위주이므로 실제 영향은 낮지만 잠재 위험.

### FE `KEYWORD_INDICATOR_MAP`(`AddIndicatorSheet.tsx:109`) — 28개 룰
- 모든 `indicatorIds`가 BE `INDICATOR_CATALOG` ID 집합 부분집합:
  - 사용 ID: {1, 2, 3, 6, 7, 8, 9, 10, 11, 12, 16, 20, 21, 23, 24, 25, 26, 30, 31, 32, 33, 34, 35, 36, 37, 39, 40, 50, 51, 52, 53, 54, 55, 56, 57, 58, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73} → 모두 카탈로그에 존재.
  - **카탈로그에 있는데 FE 키워드 룰에 등장하지 않는 ID**: 4(KOSPI 지수), 5(EPS 추이 — `실적` 키워드 매핑에는 50/57/58/60/61/69만 들어있음), 13(다우존스), 14(코스닥 지수), 15(니케이 225), 22(은), 38(달러/유로), 41~47(기술적 보조지표), 73(순주주수익률 — `주주환원` 키워드에서는 매핑됨, 재확인 필요).
  - 정밀 확인:
    - id 4 `KOSPI 지수` — FE 키워드 룰 미사용 (수동 추가만 가능)
    - id 5 `EPS 추이` — `'실적'` 룰의 `indicatorIds` 배열에 5 미포함(50/57/58/60/61/69만 있음). 사용자가 'EPS' 입력 시 매핑 안 됨 — **잠재 문제**
    - id 13 `다우존스` — 미사용
    - id 14, 15, 22, 38 — 미사용 (수동 추가만)
    - id 41~47(스토캐스틱/볼린저/ATR/OBV/SMA/EMA) — 미사용. `'rsi','macd'` 룰이 10/40만 매핑.
  - 판정: **고아 카탈로그(키워드 룰 미커버)** 항목 약 16종, 가장 눈에 띄는 누락은 `id 5 EPS 추이`가 `실적` 키워드에서 빠진 부분.

### BE↔FE 키워드 룰 커버리지 격차
- BE `KEYWORD_RULES`(11종)은 FE `KEYWORD_INDICATOR_MAP`(28종)에 비해 **17종 부족**.
- BE만에 있고 FE에 없는 키워드 룰 셋: 사실상 없음 (BE의 모든 키워드는 FE도 유사 키워드로 커버).
- FE만에 있는 키워드 룰(BE에 미존재): 유가/금/구리/천연가스/암호화폐/PBR/ROE-ROA/부채/배당-FCF/회전율/이익 품질/CPI/고용/GDP/주택/반도체-AI/중국/일본/광고 — **펀더멘털·원자재·섹터 키워드 대부분이 BE 측에 누락**.
- 영향: LLM 빌더가 `recommended_indicators`에 PK를 정확히 채워주면 무관하지만, PK가 비어 fallback이 발동하면(`indicator_matcher.match_by_keywords` → `match_indicators_for_llm` 경로) BE 측은 펀더멘털 전제(예: "ROE 개선", "구리 가격 상승 수혜")에 대해 빈 매칭을 반환하여 추천 누락이 발생할 수 있다.

---

## data_params 형식

### 1) BE 카탈로그가 정의하는 형식 (실제 데이터 fetch 코드와 매칭)

| `data_source` | 예시 `data_params` | 처리 위치 | 일치 여부 |
|---------------|--------------------|-----------|----------|
| `fmp` (수급) | `{'metric': 'foreign_net_buy'}` / `{'metric': 'institutional_net_buy'}` | `eod_pipeline._fetch_fmp_value` → quote 매핑(`value_map`에 없으므로 `field=metric` 그대로 사용) | ⚠️ `value_map`에 등록 안 됨 → 실제 `quote.get('foreign_net_buy')` 호출 시 FMP `/stable/quote`에 해당 필드가 없을 가능성 매우 높음 (시세 quote ≠ 수급 데이터). 별도 endpoint 필요. **잠재 결함** |
| `fmp` (지수/원자재/암호화폐) | `{'symbol': '^GSPC'}` 외 12종 | `client.get_quote(symbol)` | ✅ 정합 |
| `fmp` (TTM) | `{'metric': 'pbRatioTTM'}` / `{'metric': 'debtToEquityTTM'}` 등 | `_fetch_fmp_ttm_or_growth` → `/stable/key-metrics-ttm` | ✅ 정합 (`metric.endswith('TTM')` 분기) |
| `fmp` (TTM + inverse) | `{'metric': 'earningsYieldTTM', 'inverse': True, 'audit_note': '...'}` (id 50) | 위 + `_apply_value_postprocess` | ✅ 정합, audit_note는 표시용 (fetch에 영향 없음) |
| `fmp` (TTM + scale_multiplier) | `{'metric': 'returnOnEquityTTM', 'scale_multiplier': 100}` (id 52, 53) | 위 + 백분율 변환 | ✅ 정합 |
| `fmp` (financial-growth) | `{'metric': 'growthRevenue', 'endpoint': 'financial-growth', 'scale_multiplier': 100}` (id 58) | `_fetch_fmp_ttm_or_growth` → `/stable/financial-growth` | ✅ 정합. 단, 카탈로그 코멘트는 `data_source='metrics'`로 분기를 권고하지만 실제 구현은 fmp 유지 — **자가 표시 audit_note 위반** |
| `fred` (거시) | `{'series_id': 'FEDFUNDS'}` 등 | (감사 범위 외 — FRED fetcher) | 표면적 정합 (FRED API 표준 series_id 사용) |
| `news_sentiment` | `{}` (id 11) | 별도 처리 | 정합 (파라미터 없음) |
| `metrics` (재무 체질, id 60~73) | `{'metric_code': 'gross_margin'}` 등 | `quarterly_metric_fetcher.fetch_quarterly_metric(symbol, metric_code)` | ✅ 14개 metric_code 전부 `COMPARISON_TYPE_MAP`/`RATIO_METRICS`에 등록 — 정합. 단 **`eod_pipeline.py`에서 `data_source='metrics'` 분기 라우팅 구현은 본 감사에서 확인 안 됨** (별도 호출 경로일 수 있음). |
| `fmp` (technical) | `{'indicator': 'RSI', 'period': 14}` 등 (id 10, 40~47) | (감사 범위 외 — technical indicator fetcher) | 키 형식이 다른 분기와 다름(`indicator/period` vs `symbol/metric`) → eod_pipeline 표준 경로에 매핑되는지 검증 필요 |

### 2) 잠재적 형식 불일치 / 운영 리스크 — TOP 5

1. **`foreign_net_buy` / `institutional_net_buy` (id 1, 2)**
   - 카탈로그: `data_source='fmp', data_params={'metric': 'foreign_net_buy'}`
   - eod_pipeline 분기: `_fetch_fmp_value` → `client.get_quote(symbol)` → `value_map`에 없으므로 `field='foreign_net_buy'` → `quote.get('foreign_net_buy')` 반환 → **거의 확실히 None**.
   - FMP `/stable/quote`는 시세 데이터를 반환하며 외국인/기관 매매 필드를 노출하지 않는다 (해당 데이터는 KRX 별도). 또한 id 1, 2는 카탈로그에서 `symbol`이 비어 있음 → eod_pipeline은 `thesis.target`에서 symbol을 끌어다 quote 호출 시도 → 의미가 없는 매핑.
   - **결론**: 형식상 BE 카탈로그가 정의한 metric이 FMP 표준 quote 필드와 매칭되지 않음. 별도 데이터 공급원이 필요한데 그 라우팅 정의가 없음.

2. **`growthRevenue` (id 58) — audit_note 위반**
   - 카탈로그 자체 코멘트(prompt_builder.py:236~238): "권장: data_source='metrics' (quarterly_metric_fetcher의 'revenue_growth_yoy' RATIO_METRICS) 분기."
   - 실제 정의: `data_source='fmp', data_params={'metric': 'growthRevenue', 'endpoint': 'financial-growth', 'scale_multiplier': 100}`
   - `quarterly_metric_fetcher`에 `revenue_growth_yoy`는 이미 `COMPARISON_TYPE_MAP`(YoY) + `RATIO_METRICS`(0~1→%)로 정상 등록됨.
   - **결론**: 동일 지표를 두 경로(metrics 분기 엔진 vs fmp /financial-growth)로 동시에 조회 가능한 상태. 일관성을 위해 metrics 단일화 권장.

3. **`returnOnEquityTTM` (id 52, ROE) — 분기 엔진과의 중복**
   - 카탈로그: `data_source='fmp', metric='returnOnEquityTTM', scale_multiplier=100`
   - `quarterly_metric_fetcher`에 `roe`가 이미 정의(QoQ 비교, %로 노출). 다른 metrics 항목과 일관성 위해 id 52도 `data_source='metrics', metric_code='roe'`로 통일하는 게 자연스러움.
   - 동일 패턴: id 53(ROA, TTM 사용)이지만 quarterly_metric_fetcher의 `COMPARISON_TYPE_MAP`/`MetricCalculator`에 `roa`가 있는지는 본 감사 범위에서 미확인 (감사 대상 파일에 `roa` 키워드 없음 — 확인 필요).
   - **결론**: PER/ROE/ROA를 어느 파이프라인 한쪽으로 모으는 의사결정이 필요. 현 상태는 양다리.

4. **`technical` 지표 — `indicator/period` 키 형식**
   - 카탈로그(id 10, 40~47): `{'indicator': 'RSI', 'period': 14}`, `{'indicator': 'MACD', 'fast': 12, 'slow': 26, 'signal': 9}` 등.
   - `eod_pipeline._fetch_fmp_value`의 분기 1(TTM/growth)과 분기 2(quote)는 모두 `symbol/metric` 키 형식을 가정. `indicator/period`를 받는 코드 경로는 본 감사 파일들에서 확인되지 않음.
   - **결론**: 기술적 지표가 EOD 파이프라인을 통과하면 quote의 `field='RSI'`로 잘못 매핑돼 None을 반환할 가능성. 별도 technical fetcher 경로가 분리되어 있는지 확인 필요.

5. **`audit_note`는 fetch 무영향, 그러나 LLM 응답에 노출 위험**
   - id 50, 52, 53, 58은 `data_params.audit_note`에 자유 텍스트 메모 보유.
   - LLM 응답 후 `merge_to_collected`(llm_postprocess.py)는 `data_params`를 직접 다루지 않으므로 LLM 출력에 새지는 않지만, 향후 카탈로그 dict가 API로 그대로 직렬화되면 사용자에게 audit_note가 노출될 수 있음. 별도 디버그 메타로 분리 권장.

---

## 부록 — 빠른 재현 명령

```bash
# 본 감사 재실행용 (코드 수정 금지)
grep -n "'id':" thesis/services/prompt_builder.py | head -80
grep -n "id: [0-9]" frontend/components/thesis/AddIndicatorSheet.tsx | head -80
grep -n "'name':" thesis/services/indicator_matcher.py
grep -n "endpoint.*financial-growth\|scale_multiplier\|inverse" thesis/services/prompt_builder.py
```

- 본 보고서는 코드/문서/카탈로그를 변경하지 않았으며, `git status`에 본 .md 파일 외 변경은 없습니다.
- 후속 액션(권장):
  1. id 58(매출성장률), 52(ROE), 53(ROA), 50(PER) — `data_source='metrics'` 일원화 PR.
  2. id 1, 2(외국인/기관 수급) — FMP `/stable/quote`가 아닌 별도 데이터 공급원 분기 추가 또는 카탈로그에서 `data_source` 정정.
  3. BE `KEYWORD_RULES` 확장 — 펀더멘털/원자재/섹터 키워드 17종 추가하여 FE 측 커버리지에 근접.
  4. FE `KEYWORD_INDICATOR_MAP`의 `'실적'` 항목에 id 5(EPS 추이) 추가, 누락 카탈로그 항목 16종 일부를 룰에 편입.
  5. `audit_note` 필드를 `data_params`에서 분리(예: 카탈로그 항목 최상위 `notes` 키)하여 fetch 영역과 디버그 메모를 분리.

# 지표 카탈로그 동기화 감사 보고서

> **생성일**: 2026-05-29
> **모드**: 읽기 전용 (코드 수정 없음)
> **범위**: `thesis/services/prompt_builder.py`(BE 정의) · `frontend/components/thesis/AddIndicatorSheet.tsx`(FE 미러) · `thesis/services/indicator_matcher.py`(KEYWORD_RULES) · `thesis/tasks/eod_pipeline.py`(data_params 소비 경로)

---

## 요약 (동기화 상태)

| 검사 항목 | 결과 | 비고 |
|----------|------|------|
| **BE ↔ FE 지표 ID 동기화** | ✅ 일치 (64/64) | ID·이름·업데이트 주기(freq) 전부 일치 |
| **BE ↔ FE 카테고리 분류** | ⚠️ 의도적 분기 | BE 5개 macro 분류 vs FE 17개 표시 분류 — 동기화 깨짐 아님(표시용) |
| **description 품질** | ✅ 양호 | BE 64개 전부 채워짐, 빈/단문 0건. FE는 description 미보유(설계상 정상) |
| **KEYWORD_RULES 고아 규칙** | ✅ 0건 | BE 11개 규칙 모든 지표명이 카탈로그에 존재 |
| **BE KEYWORD_RULES 커버리지** | 🔴 심각한 격차 | 64개 중 **11개만** 키워드 자동매칭 가능 (ids 1~11). 신규 53개 미커버 |
| **BE ↔ FE 키워드 룰 정합성** | ⚠️ 분기 | BE `KEYWORD_RULES`(11규칙) vs FE `KEYWORD_INDICATOR_MAP`(27규칙) 독립 관리 |
| **data_params 형식** | 🔴 3건 불일치 | id 1·2(합성 metric 미지원), id 39(DXY 심볼 Starter 미지원) |

**총평**: 지표 **목록 자체**(ID/이름/주기)는 BE↔FE 완전 동기화 상태. 그러나 (1) data_params가 실제 데이터 제공자와 맞지 않아 **항상 빈 값**을 반환하는 지표 3건, (2) BE 키워드 자동매칭이 초기 11개 지표에서 멈춰 신규 53개 지표가 LLM PK 매칭 실패 시 자동 추천 불가, 두 가지가 핵심 리스크.

---

## BE ↔ FE 불일치 목록

### 1. 지표 ID/이름/주기 — 완전 일치 ✅

BE(`INDICATOR_CATALOG`)와 FE(`INDICATOR_CATALOG` 미러) 모두 동일한 64개 지표:

```
공통 ID(64): 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,20,21,22,23,24,25,26,
            30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,
            50,51,52,53,54,55,56,57,58,60,61,62,63,64,65,66,67,68,69,70,71,72,73
```

- **BE에만 있는 지표**: 없음
- **FE에만 있는 지표**: 없음
- **이름 불일치**: 없음 (64건 전수 대조 완료)
- **freq 불일치**: 없음 (FE `freq` 필드 ↔ BE `INDICATOR_FREQUENCY` dict 전수 일치)

> ✅ 미러 동기화가 잘 유지되고 있음. (memory: `feedback_indicator_catalog_sync` — 3곳 동시 업데이트 원칙이 지켜진 결과)

### 2. 카테고리 분류 체계 분기 ⚠️ (동기화 깨짐 아님)

| | BE (`category`) | FE (`category`) |
|--|----------------|-----------------|
| 분류 수 | 5개 (macro 분류) | 17개 (표시용 세분류) |
| 값 | `market_data` / `macro` / `technical` / `fundamental` / `sentiment` | `수급` / `주요 지수` / `원자재` / `암호화폐` / `금리` / `환율/변동성` / `고용/성장` / `물가/주택` / `기술적` / `펀더멘털` / `재무 체질` / `밸류에이션` / `성장` / `운영 효율` / `이익 품질` / `주주환원` / `심리` |

- BE의 `market_data` 1개가 FE에서 `수급/주요 지수/원자재/암호화폐` 4개로 분할됨.
- BE의 `fundamental` 1개가 FE에서 `펀더멘털/재무 체질/밸류에이션/성장/운영 효율/이익 품질/주주환원` 7개로 분할됨.
- **판정**: FE는 BottomSheet UI 그룹핑 목적의 표시용 세분류이므로 **의도된 분기**. 단, BE `CATEGORY_LABELS`와 FE 분류가 1:1 매핑되지 않아 향후 "카테고리 기준 필터" 기능 추가 시 정합화 비용 발생 가능 → **문서화만 권장**.

### 3. 키워드 자동매칭 룰 분기 ⚠️

| | BE `KEYWORD_RULES` (indicator_matcher.py) | FE `KEYWORD_INDICATOR_MAP` (AddIndicatorSheet.tsx) |
|--|------------------------------------------|--------------------------------------------------|
| 규칙 수 | 11개 | 27개 |
| 식별 방식 | 지표 **이름**(name) 문자열 | 지표 **ID**(number) |
| 커버 지표 | ids 1~11 (11개) | ids 약 53개 (12~73 다수 포함) |
| 추천 이유 | `reason` 필드 | `reason` 필드 |

- BE/FE가 키워드 룰을 **독립적으로 이중 관리** 중. FE가 훨씬 포괄적.
- 동일 의미 지표에 대해 키워드 셋이 다름 (예: 금리 — BE `['금리','연준','FOMC','fed','기준금리','금리인하','금리인상']` vs FE `[...,'이자율','통화정책']` 추가).
- **리스크**: 한쪽 키워드만 갱신되면 BE 서버 추천과 FE 클라이언트 추천 결과가 어긋남.

---

## description 품질

### BE (`prompt_builder.py` INDICATOR_CATALOG)

| 검사 | 결과 |
|------|------|
| 빈 description (`''` 또는 누락) | **0건** |
| 너무 짧은 description (< 10자) | **0건** (최단도 약 20자 내외, 모두 완결된 문장) |
| 총 점검 항목 | 64건 |

✅ **전 항목 양호.** 모든 지표가 "정의 + 투자적 함의" 구조의 한국어 문장을 보유.
예) id 23 구리 — `"구리 선물 가격. 경기 선행지표로 \"Dr. Copper\"라 불림."`

### FE (`AddIndicatorSheet.tsx`)

- FE `CatalogIndicator` 타입은 `{ id, name, category, freq }`만 보유 — **description 필드 자체가 없음**.
- BottomSheet 선택 UI는 설명을 표시하지 않으므로 **설계상 정상**(미러 최소화). description이 필요한 화면은 별도 API(`get_indicator_description`)로 BE에서 조회.
- **권장**: 현 구조 유지. 단, FE에서 지표 설명 툴팁을 추가할 경우 BE description을 API로 끌어오고 FE에 하드코딩 미러를 만들지 말 것.

---

## keyword_rules 고아

### 고아 규칙 (카탈로그에 없는 지표를 가리키는 규칙) — 0건 ✅

BE `KEYWORD_RULES`의 11개 규칙이 참조하는 모든 지표명이 `INDICATOR_CATALOG`에 존재:

| KEYWORD_RULES 지표명 | 카탈로그 매칭 | ID |
|---------------------|:---:|:---:|
| 외국인 순매수 추이 | ✅ | 1 |
| 기관 순매수 추이 | ✅ | 2 |
| S&P 500 | ✅ | 3 |
| KOSPI 지수 | ✅ | 4 |
| EPS 추이 | ✅ | 5 |
| 미국 기준금리 (Fed Funds Rate) | ✅ | 6 |
| 미국 10년 국채 금리 | ✅ | 7 |
| VIX (공포지수) | ✅ | 8 |
| 원/달러 환율 | ✅ | 9 |
| RSI (14일) | ✅ | 10 |
| 뉴스 센티먼트 | ✅ | 11 |

> 이름 기반 매칭은 `match_indicators_for_llm`의 2순위 fallback(`_find_in_catalog`)에서 최종 검증되므로, 이름이 1글자라도 어긋나면 매칭 실패. 현재는 11건 전부 정확히 일치.

### 🔴 커버리지 격차 (역방향 고아 — 규칙이 없는 지표) — 53건

`KEYWORD_RULES`는 **ids 1~11(11개)만** 자동 추천 가능. 신규 추가된 53개 지표(12~73)는 BE 키워드 룰에서 **추천 불가**:

- 미커버 예시: 다우존스(13), 코스닥(14), 니케이(15), 항셍(16), 금/은/구리/천연가스(20~24), BTC/ETH(25,26), 2년물(30), 모기지(37), 달러인덱스(39), MACD~EMA(40~47), PER/PBR/ROE 등 펀더멘털 전체(50~58), 재무 체질 metrics 전체(60~73)
- **영향**: LLM 빌더에서 `indicator_db_id`(PK) 매칭이 실패하면 키워드 fallback으로 넘어가는데, 이 fallback이 11개 지표만 알고 있어 신규 지표 추천이 누락됨.
- **완화 요인**: `match_indicators_for_llm` 1순위가 LLM의 `indicator_db_id` 직접 매칭이라, LLM이 ID를 정확히 반환하면 키워드 fallback 자체가 불필요. 키워드 fallback은 어디까지나 안전망 → **현재 LLM PK 매칭 의존도가 높음**.
- **참고**: `match_by_gemini` fallback은 "카탈로그에 없는 환각 지표 생성" 때문에 의도적으로 제외됨(코드 주석, line 307 / memory `feedback_llm_indicator_hallucination`).

### indicator_type 분류 불일치 (경미) ⚠️

`KEYWORD_RULES` 내 `EPS 추이`의 `indicator_type='market_data'`이나, 카탈로그 id 5의 `category='fundamental'`. 추천 결과 표시 시 분류 라벨이 어긋날 수 있음 (실데이터 fetch에는 영향 없음).

---

## data_params 형식

### 🔴 불일치 3건 (실제 제공자와 형식 어긋남 → 항상 빈 값)

| ID | 지표 | data_params | 문제 | 근거 |
|:--:|------|-------------|------|------|
| **1** | 외국인 순매수 추이 | `{'metric': 'foreign_net_buy'}` | FMP `/stable/quote` 응답에 `foreign_net_buy` 필드 없음. `_fetch_fmp_value`의 `value_map` 미등록 → `quote.get('foreign_net_buy')` = **항상 None** | `eod_pipeline.py:126-140` |
| **2** | 기관 순매수 추이 | `{'metric': 'institutional_net_buy'}` | 위와 동일. FMP가 한국 외국인/기관 순매수를 제공하지 않음 → **항상 None** | `eod_pipeline.py:126-140` |
| **39** | 달러 인덱스 (DXY) | `{'symbol': 'DX-Y.NYB'}` | **FMP Starter 플랜 미지원 심볼.** macro 모듈에서 이미 `"DX-Y.NYB는 FMP Starter 미지원 → 제외"`로 명시적 차단 | `macro/services/fmp_client.py:188`, `:359` |

> id 1·2는 한국 시장 수급 데이터로, FMP(미국 중심 제공자)가 구조적으로 제공 불가. 데이터 소스 자체를 KRX 등으로 교체하거나 카탈로그에서 보류 표시 필요.
> id 39는 macro 모듈이 이미 동일 심볼을 차단한 전례가 있으므로, 동일하게 대체 심볼/소스 적용 필요.

### ✅ 형식 정상 + 후처리 메타 패턴 (양호)

`#14`(FMP 필드명/스케일 불일치) 회귀 방지를 위한 `audit_note` + 후처리 플래그가 잘 적용됨:

| ID | 지표 | data_params 후처리 | 처리 경로 |
|:--:|------|-------------------|----------|
| 50 | PER | `{'metric':'earningsYieldTTM','inverse':True}` | `_apply_value_postprocess`로 역수 계산 |
| 52 | ROE | `{'metric':'returnOnEquityTTM','scale_multiplier':100}` | 0~1 → % 변환 |
| 53 | ROA | `{'metric':'returnOnAssetsTTM','scale_multiplier':100}` | 동일 패턴 |
| 58 | 매출성장률 | `{'metric':'growthRevenue','endpoint':'financial-growth','scale_multiplier':100}` | `/stable/financial-growth` 분기 |

### data_source별 fetcher 매핑 (정상 동작 확인)

| data_source | fetcher | 비고 |
|-------------|---------|------|
| `fmp` | `_fetch_fmp_value` | quote / key-metrics-ttm / financial-growth 3분기. `^GSPC`,`^KS11`,`^VIX` 등 인덱스 심볼은 Starter 지원 여부 추가 점검 권장(미검증) |
| `fred` | `_fetch_fred_value` | ✅ `FRED_API_KEY`(settings.py:25) + `macro.services.fred_client.FREDClient` 정상 구현. **고아 아님** — ids 6,7,30,37,38,31,32,34,35,33,36(11개) 정상 fetch 가능 |
| `metrics` | (metrics 시스템) | ids 60~73(14개), `quarterly_metric_fetcher`의 `metric_code` 연동 |
| `news_sentiment` | `_fetch_news_sentiment_value` | id 11, `NewsArticle.sentiment_score` 48h 윈도우 |

> ⚠️ **추가 점검 권장(미검증)**: `^GSPC`/`^IXIC`/`^DJI`/`^KS11`/`^KQ11`/`^N225`/`^HSI`/`^VIX` 등 `^` 접두 인덱스 심볼이 FMP Starter `/stable/quote`에서 실제 응답을 주는지 본 감사에서는 확인하지 못함. id 39 사례로 보아 인덱스/환율 심볼은 플랜 제약 가능성 있음.

---

## 권장 조치 (우선순위)

| # | 우선순위 | 대상 | 조치 |
|---|:--:|------|------|
| 1 | 🔴 P0 | id 1, 2 (외국인/기관 순매수) | FMP로 fetch 불가 — 데이터 소스 KRX 등으로 교체하거나 카탈로그에서 휴면 표시. 현재 무한 None 반환 |
| 2 | 🔴 P0 | id 39 (DXY) | `DX-Y.NYB` → FMP Starter 지원 대체 심볼/소스로 교체 (macro 모듈 처리 방식 참조) |
| 3 | 🟡 P1 | BE `KEYWORD_RULES` | ids 12~73 키워드 룰 보강 (FE `KEYWORD_INDICATOR_MAP` 53개를 BE로 역이식). LLM PK 매칭 실패 시 안전망 복원 |
| 4 | 🟡 P1 | `^` 인덱스 심볼 11종 | FMP Starter `/stable/quote` 실응답 여부 실측 검증 |
| 5 | 🟢 P2 | BE↔FE 키워드 룰 | 단일 소스화 검토(BE가 키워드맵을 API로 노출, FE 미러 제거) |
| 6 | 🟢 P2 | id 5 indicator_type | `KEYWORD_RULES` `'market_data'` → `'fundamental'` 정정 (카탈로그 일치) |

---

*본 보고서는 읽기 전용 정적 분석 결과이며, 실제 API 응답을 호출해 검증하지 않았습니다. data_params 불일치 3건은 코드 경로 추적 + macro 모듈의 명시적 차단 주석을 근거로 합니다.*

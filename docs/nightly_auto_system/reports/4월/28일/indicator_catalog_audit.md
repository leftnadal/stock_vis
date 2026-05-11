# 지표 카탈로그 동기화 감사 보고서

- 작성일: 2026-04-28
- 범위: `INDICATOR_CATALOG`(BE 단일 진실 소스) ↔ `AddIndicatorSheet.tsx`(FE 미러) ↔ `KEYWORD_RULES`(BE 매칭) ↔ EOD fetcher(`thesis/tasks/eod_pipeline.py`)
- 모드: 읽기 전용. 코드 수정 없음.

---

## 요약 (동기화 상태)

| 항목 | 상태 | 근거 |
|------|------|------|
| BE ↔ FE id 집합 | ✅ 일치 (총 64개) | 양쪽 모두 `1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,20–26,30–47,50–58,60–73` |
| BE ↔ FE name | ✅ 1:1 일치 | 64개 항목 모두 한글 표기 동일 |
| 카테고리 그룹화 | ⚠️ 표기/세분화 차이 | BE: `market_data/macro/technical/fundamental/sentiment` 5종 ↔ FE: `수급/주요 지수/원자재/암호화폐/금리/환율·변동성/...` 17종 |
| description 필드 | ⚠️ FE에 description 자체가 없음 | BE 카탈로그만 `description` 보유, FE는 `id/name/category/freq`만 |
| description 품질(BE) | ✅ 64/64 채워짐, 모두 ≥ 15자 | 빈 description 0건, 짧은 description(<10자) 0건 |
| `KEYWORD_RULES` 커버리지 | ❌ 11/64 (17%)만 매칭 룰 보유 | `indicator_matcher.py`는 11개 지표 이름만 룰화 |
| `KEYWORD_RULES` 고아 규칙 | ✅ 0건 (참조 이름 모두 카탈로그에 존재) | 11개 모두 카탈로그 name과 정확히 일치 |
| `data_params` 형식 ↔ FMP fetcher | ❌ 펀더멘털 ID 50–58 fetcher 미지원 | `_fetch_fmp_value`는 `/quote` 엔드포인트만 사용 → `peRatioTTM/returnOnEquityTTM` 등은 항상 `None` |
| `data_params` 형식 ↔ 수급/EPS | ⚠️ 카탈로그에 `symbol` 누락 | id 1·2·5·11 — `_fetch_fmp_value` 진입 시 `symbol` 필수 → 빌더에서 `target_symbol` 자동 주입에 의존 |
| FE `KEYWORD_INDICATOR_MAP` 커버리지 | ✅ 카탈로그 64개 중 50+ 커버 | BE 11개 룰 대비 5배 이상 풍부 — BE/FE 룰 분기됨 |

**총평**: 카탈로그 자체(id/name)는 BE/FE 완벽 동기화. 그러나 ① BE 키워드 룰이 매우 협소(11개), ② 펀더멘털 지표(id 50–58) 데이터 fetcher 미구현, ③ FE/BE 키워드 룰 이중화(중복 관리 부담)가 핵심 이슈.

---

## BE ↔ FE 불일치 목록

### 1. id 단위 불일치
없음. 양쪽 64개 id 모두 1:1 매칭.

### 2. name 단위 불일치
없음. 모든 한글 표기 동일.

### 3. 메타데이터 필드 불일치
| BE 필드 | FE 필드 | 비고 |
|---------|---------|------|
| `id` | `id` | ✅ |
| `name` | `name` | ✅ |
| `category` (`market_data` 등 영문 키) | `category` (`주요 지수` 등 한글 라벨) | ⚠️ 의미는 같으나 표기/세분도 다름 |
| `data_source`, `data_params`, `support_direction` | (없음) | ❌ FE는 보유하지 않음 — 사용 안 함이라면 OK |
| `description` | (없음) | ❌ FE는 카탈로그에 description 미보유 (사용처 별도 API 필요 시 결손) |
| `INDICATOR_FREQUENCY[id]` (별도 dict) | `freq` (인라인 필드) | ⚠️ 위치만 다름, 값은 일치 |

### 4. 카테고리 그룹화 차이 (대조표)
| BE category | FE category 예시 | 비고 |
|-------------|------------------|------|
| `market_data` | `수급`, `주요 지수`, `원자재`, `암호화폐` | FE가 4단으로 세분 |
| `macro` | `금리`, `환율/변동성`, `고용/성장`, `물가/주택` | FE가 4단으로 세분 |
| `technical` | `기술적` | 동일 |
| `fundamental` | `펀더멘털`, `재무 체질`, `밸류에이션`, `성장`, `운영 효율`, `이익 품질`, `주주환원` | FE가 7단으로 세분 |
| `sentiment` | `심리` | 동일 |

→ FE가 더 세분화된 UI 그룹핑을 자체 정의. BE의 `category`만 보고 FE 그룹을 재구성하기 어려우므로, FE 카테고리 라벨이 별도 진실 소스로 동작 중. 카탈로그 항목이 추가될 때 양쪽을 모두 갱신해야 한다.

### 5. INDICATOR_FREQUENCY ↔ FE freq 일치 검증
BE `INDICATOR_FREQUENCY` dict와 FE `freq` 값 64개 모두 비교한 결과 동일. 단, BE에 `INDICATOR_FREQUENCY[id]`가 없으면 빈 문자열로 폴백되므로 새 지표 추가 시 두 곳을 모두 채워야 함.

---

## description 품질

### BE 검사 결과
- 검사 대상: `thesis/services/prompt_builder.py:14-294` `INDICATOR_CATALOG` 64개
- 빈 description (`''`/없음): **0건**
- 너무 짧은 description (< 10자): **0건** (최단 길이 ≈ 25자)
- 평균 길이: 약 35–55자, 모두 1문장 이내 — LLM 프롬프트/UI 툴팁 양쪽에 적합

샘플 검증 (대표 2개):
- id 1 외국인 순매수 추이: "외국인 투자자의 일별 순매수/순매도 금액. 시장 방향을 선행하는 수급 지표." (37자)
- id 73 순주주수익률: "배당 + 자사주 매입 - 신주 발행의 순 환원율. 주주 환원 종합 지표." (33자)

### FE 검사 결과
- FE `CatalogIndicator` 인터페이스에 `description` 필드 자체가 없음 (`AddIndicatorSheet.tsx:8-13`)
- 즉 FE 시트는 description을 표시하지 않으며, 사용자에게 지표 의미를 노출하지 않음
- 결손 시 사용자 UX: 새 지표 이름만 보고 선택해야 함 → 의미 모호
- BE → FE description을 동기화하려면 (a) FE에 description 필드 추가 + 64개 복제, 또는 (b) `/api/v1/thesis/indicator-catalog/` 같은 API로 BE에서 가져오는 구조 필요. **현재는 (a)도 (b)도 미구현.**

---

## keyword_rules 고아

### `KEYWORD_RULES` 참조 이름 ↔ `INDICATOR_CATALOG` 일치 여부
`thesis/services/indicator_matcher.py:12-154` 의 11개 룰이 가리키는 지표 이름:

| 룰 위치 | 가리키는 indicator name | 카탈로그 매칭 | 카탈로그 id |
|---------|--------------------------|--------------|------------|
| 14 | 외국인 순매수 추이 | ✅ | 1 |
| 28 | 미국 기준금리 (Fed Funds Rate) | ✅ | 6 |
| 36 | 미국 10년 국채 금리 | ✅ | 7 |
| 48 | VIX (공포지수) | ✅ | 8 |
| 59 | 원/달러 환율 | ✅ | 9 |
| 70 | RSI (14일) | ✅ | 10 |
| 81 | 뉴스 센티먼트 | ✅ | 11 |
| 92 | EPS 추이 | ✅ | 5 |
| 103 | 기관 순매수 추이 | ✅ | 2 |
| 114 | S&P 500 | ✅ | 3 |
| 125 | KOSPI 지수 | ✅ | 4 |
| 137·145 (중복) | VIX/KOSPI | ✅ | 8, 4 |

→ **고아 규칙 0건.** 모든 keyword 룰이 카탈로그에 존재하는 정확한 name을 가리킴.

### 역방향: 카탈로그에는 있으나 룰이 없는 지표 (Gap)
| 카탈로그 그룹 | 룰 미보유 ID | 개수 |
|--------------|------------|-----|
| 주요 지수 (NASDAQ/다우/코스닥/니케이/항셍) | 12, 13, 14, 15, 16 | 5 |
| 원자재 (금/원유/은/구리/천연가스) | 20, 21, 22, 23, 24 | 5 |
| 암호화폐 (BTC/ETH) | 25, 26 | 2 |
| 금리 (2년/모기지) | 30, 37 | 2 |
| 환율·변동성 (DXY/유로) | 38, 39 | 2 |
| 거시 고용/성장/물가/주택 | 31, 32, 33, 34, 35, 36 | 6 |
| 기술적 (MACD~EMA12) | 40, 41, 42, 43, 44, 45, 46, 47 | 8 |
| 펀더멘털 (PER~매출성장률) | 50–58 | 9 |
| 재무 체질 (Gross Margin~순주주수익률) | 60–73 | 14 |
| **합계** | **53/64 (83%)** | |

→ `match_by_keywords`는 폴백 경로에 불과(주 경로는 LLM의 `indicator_db_id` 추천)이므로 운영 영향은 작지만, LLM이 id를 누락한 폴백 케이스에서 다양성이 크게 떨어진다.

### BE ↔ FE 키워드 룰 이중화
- BE: `KEYWORD_RULES` (11개 indicator → 룰 11개)
- FE: `KEYWORD_INDICATOR_MAP` (`AddIndicatorSheet.tsx:109-139`, 룰 28개 — 50+ 지표 매핑)
- FE는 `findRelatedIndicators()`에서 전제 텍스트와 매칭하여 추천 카드 생성. BE는 `match_by_keywords()`에서 폴백 추천.
- **두 룰셋이 분리되어 있어** 같은 전제 텍스트가 BE/FE에서 다른 지표를 추천할 수 있음 (예: "유가" → FE는 id 21 매칭, BE는 룰 미보유 → Gemini 폴백 또는 빈 결과).

---

## data_params 형식

### EOD fetcher 진입 규칙 (`thesis/tasks/eod_pipeline.py`)
| data_source | 필요 키 | fetcher가 사용하는 엔드포인트 |
|-------------|---------|------------------------------|
| `fmp` | `symbol` (필수) + `metric` (옵션, 기본 `price`) | `FMPClient.get_quote(symbol)` — `/stable/quote` |
| `fred` | `series_id` (필수) | `FREDClient.get_latest_value(series_id)` |
| `news_sentiment` | `symbol` (필수) | `NewsArticle.objects.filter(entities__symbol=...)` |
| `metrics` | `metric_code` (필수) + `symbol`(없으면 thesis.target) | `quarterly_metric_fetcher.fetch_quarterly_metric` |

### 카탈로그 ↔ fetcher 적합성 검사

#### ✅ 정상 매핑
- id 3, 4, 12–16 (주요 지수): `data_source='fmp'`, `data_params.symbol='^GSPC'` 등 — `get_quote`로 가격 조회 가능. `metric` 미지정 → 기본 `price`로 동작.
- id 20–26 (원자재/코인): 동일 패턴, 정상.
- id 8, 9, 38, 39 (변동성/환율): 동일 패턴, 정상.
- id 6, 7, 30, 37, 31–36 (FRED): `data_source='fred'`, `series_id` 보유 — 정상.
- id 60–73 (재무 체질 metrics): `data_source='metrics'`, `metric_code` 보유 — `_fetch_metrics_value`가 `metric_code` + thesis.target 조합으로 분기 fetch. 정상.

#### ⚠️ symbol 누락 — thesis_builder 자동 주입에 의존
| ID | 카탈로그 data_params | 위험 |
|----|----------------------|------|
| 1 | `{'metric': 'foreign_net_buy'}` | symbol 없음 → `_fetch_fmp_value` 라인 36 `if not symbol: return None`. 빌더 측 `thesis/services/thesis_builder.py:1153-1157`에서 `target_symbol`을 data_params에 자동 주입할 때만 동작. 빌더를 우회한 경로는 무조건 None. |
| 2 | `{'metric': 'institutional_net_buy'}` | 동일 |
| 5 | `{'metric': 'eps'}` | 동일. 또한 `_fetch_fmp_value`의 value_map에서 `eps`는 quote의 `eps` 필드 매핑은 OK이나, target_symbol 없으면 fail. |
| 11 | `{}` | `_fetch_news_sentiment_value`가 symbol 필수, 동일하게 빌더 주입 필요. |

추가로 id 1·2의 metric 값(`foreign_net_buy`, `institutional_net_buy`)은 `_fetch_fmp_value`의 value_map에 없어 그대로 quote field로 폴백되는데, FMP `/quote`에 그런 필드가 없음 → symbol을 정상 주입해도 `quote.get('foreign_net_buy')` = None. **이 두 지표는 fetcher가 사실상 동작 불가**.

#### ❌ 펀더멘털 TTM 지표 — fetcher 미구현
| ID | 카탈로그 metric | FMP `/quote` 응답에 존재? |
|----|-----------------|----------------------------|
| 50 | `peRatioTTM` | ❌ (quote는 `pe`만 제공) |
| 51 | `pbRatioTTM` | ❌ |
| 52 | `returnOnEquityTTM` | ❌ |
| 53 | `returnOnAssetsTTM` | ❌ |
| 54 | `debtToEquityTTM` | ❌ |
| 55 | `freeCashFlowTTM` | ❌ |
| 56 | `dividendYieldTTM` | ❌ |
| 57 | `operatingProfitMarginTTM` | ❌ |
| 58 | `revenueGrowthYoY` | ❌ |

`_fetch_fmp_value` 라인 64 `field = value_map.get(metric, metric)` 폴백 → `quote.get('peRatioTTM')` = None → 9개 지표 모두 항상 None 반환.

**해결 방향 제안 (코드 수정 금지이므로 지적만)**:
- 옵션 A: id 50–58을 `data_source='metrics'`로 변경하고 `metric_code`를 사용 (id 60–73과 동일 패턴).
- 옵션 B: `_fetch_fmp_value`에 TTM metric 분기를 추가해 `FMPClient`의 `key-metrics-ttm` 또는 `ratios-ttm` 엔드포인트를 호출.
- 어느 쪽이든 카탈로그 metric 키 명명 규칙과 fetcher가 일치해야 함.

#### ⚠️ 기술적 지표 — `indicator` 키는 fetcher 미해석
| ID | data_params | 처리 |
|----|-------------|------|
| 10 | `{'indicator': 'RSI', 'period': 14}` | `_fetch_fmp_value`는 `indicator` 키를 인식하지 않음. `metric` 미지정 → `price` 기본값으로 quote 조회. RSI 값 fetch 안 됨. |
| 40–47 | `{'indicator': 'MACD'/'EMA'/...}` | 동일. 모두 quote price만 가져옴. |

→ 9개 기술 지표 모두 카탈로그 의도와 fetcher 동작이 다름. 별도 indicator endpoint 호출이 필요한데 미구현.

### 요약 표 (data_params ↔ fetcher 호환성)
| 그룹 (id) | 항목 수 | 호환성 |
|-----------|--------|--------|
| 주요 지수 / 원자재 / 코인 (3,4,12–16,20–26) | 14 | ✅ |
| 변동성 / 환율 FMP (8,9,39) | 3 | ✅ |
| FRED (6,7,30,37,31–36,38) | 11 | ✅ |
| metrics 재무 체질 (60–73) | 14 | ✅ |
| 수급·EPS·뉴스 (1,2,5,11) | 4 | ⚠️ symbol 자동 주입 의존 + id 1·2는 metric 자체가 quote 미지원 |
| 펀더멘털 TTM (50–58) | 9 | ❌ fetcher 미구현 |
| 기술 지표 (10,40–47) | 9 | ❌ fetcher 미구현 |
| **합계** | **64** | **49 호환 / 4 부분 / 18 불호환** |

---

## 권고 (액션 없음, 다음 세션 백로그 후보)

1. **데이터 fetcher 미구현 18종 수습** — 펀더멘털 TTM 9종을 `data_source='metrics'`로 이전하거나 FMP TTM 엔드포인트 분기 추가. 기술 지표 9종은 `_fetch_fmp_value`에 `indicator` 분기 또는 `data_source='technical'` 신설.
2. **id 1·2 metric 정의 재검토** — FMP `/quote`에 없는 `foreign_net_buy`/`institutional_net_buy`는 별도 엔드포인트(예: 한국거래소 자체 데이터 또는 FMP `/historical-stock-list-by-exchange`)로 옮기거나 `data_source` 변경.
3. **FE 카탈로그에 description 필드 추가** — UI 툴팁/접근성 개선. 또는 `/api/v1/thesis/indicator-catalog/` 단일 엔드포인트로 FE가 BE 카탈로그를 직접 받는 구조로 전환(이중 미러 제거).
4. **BE `KEYWORD_RULES` 보강 또는 FE 룰과 통합** — 53/64 미보유 갭이 LLM 폴백 다양성을 크게 떨어뜨림. FE `KEYWORD_INDICATOR_MAP`(28개 룰)을 BE로 이전하고 FE는 API 호출로 받게 하면 단일 진실 소스 확보 가능.
5. **새 지표 추가 시 동기화 체크리스트 명문화** — `INDICATOR_CATALOG`(BE), `INDICATOR_FREQUENCY`(BE), `AddIndicatorSheet` 카탈로그(FE), `KEYWORD_RULES`(BE), `KEYWORD_INDICATOR_MAP`(FE), fetcher value_map 6곳을 모두 업데이트해야 함.

---

## 참고 — 검사한 파일
- `thesis/services/prompt_builder.py:14-345` (BE `INDICATOR_CATALOG`, `INDICATOR_FREQUENCY`, `_INDICATOR_NAME_TO_DESC`)
- `thesis/services/llm_postprocess.py:82-93` (indicator_db_id 카탈로그 대조 정규화)
- `thesis/services/indicator_matcher.py:12-172` (`KEYWORD_RULES`, `match_by_keywords`)
- `thesis/services/thesis_builder.py:1150-1170` (target_symbol → data_params 주입)
- `thesis/tasks/eod_pipeline.py:25-194` (fetcher 4종 + DATA_SOURCE_FETCHERS)
- `frontend/components/thesis/AddIndicatorSheet.tsx:6-139` (FE 미러 + `KEYWORD_INDICATOR_MAP`)

# 지표 카탈로그 동기화 감사 보고서

- 감사 일자: 2026-05-24
- 감사 범위: `INDICATOR_CATALOG` (BE/FE), `KEYWORD_RULES` (BE), `KEYWORD_INDICATOR_MAP` (FE), `data_params` 형식
- 대상 파일
  - BE 카탈로그: `thesis/services/prompt_builder.py`
  - BE 후처리: `thesis/services/llm_postprocess.py`
  - BE 매칭: `thesis/services/indicator_matcher.py`
  - FE 표시/매칭: `frontend/components/thesis/AddIndicatorSheet.tsx`

---

## 요약 (동기화 상태)

| 항목 | 상태 | 비고 |
|------|------|------|
| BE ↔ FE id 집합 | **동기화됨** | 양쪽 모두 64개 (`{1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,20~26,30~39,40~47,50~58,60~73}`) |
| BE ↔ FE name 문자열 | **동기화됨** | 64/64 완전 일치 |
| BE category(5종) ↔ FE category(17종) | **의도된 차이** | FE는 UX용 하위 카테고리로 분할 — 매핑은 일관됨 |
| BE description 품질 | **양호** | 64/64 모두 채워짐, 모두 20자 이상 |
| BE `KEYWORD_RULES` → catalog name | **1건 type 불일치** | `EPS 추이`의 `indicator_type` ↔ catalog `category` 차이 |
| BE ↔ FE keyword 룰 커버리지 | **비대칭** | BE 11개 룰 (11개 지표) vs FE 28개 룰 (40+개 지표) |
| FMP `data_params` 형식 | **3건 비표준** | `id:50 PER`, `id:52 ROE`, `id:53 ROA`, `id:58 매출성장률` — 후처리 의존 |

전체적으로 카탈로그 본체(id/name)는 BE/FE가 완전히 일치한다. 다만 (1) 매칭 룰 풍부도, (2) `data_params` 후처리 의존(`inverse`, `scale_multiplier`, `endpoint`), (3) `EPS 추이` type 표기 차이 — 3개의 잠재 운영 리스크가 있다.

---

## BE ↔ FE 불일치 목록

### id 집합 비교

- BE 정의 (`prompt_builder.py:14-310`): 64개
- FE 정의 (`AddIndicatorSheet.tsx:15-91`): 64개
- BE에만 존재: **없음**
- FE에만 존재: **없음**
- 양측 id ↔ name 매핑: 64/64 완전 일치

### category 표기 차이 (의도된 분할이지만 명시)

| id | BE `category` | FE `category` (display) |
|----|---------------|--------------------------|
| 3,4,12~16 | `market_data` | `주요 지수` |
| 1,2 | `market_data` | `수급` |
| 20~24 | `market_data` | `원자재` |
| 25,26 | `market_data` | `암호화폐` |
| 6,7,30,37 | `macro` | `금리` |
| 8,9,38,39 | `macro` | `환율/변동성` |
| 31,32,34,35 | `macro` | `고용/성장` |
| 33,36 | `macro` | `물가/주택` |
| 10,40~47 | `technical` | `기술적` |
| 5,50~58 | `fundamental` | `펀더멘털` |
| 60~66 | `fundamental` | `재무 체질` |
| 67,68 | `fundamental` | `밸류에이션` |
| 69 | `fundamental` | `성장` |
| 70,71 | `fundamental` | `운영 효율` |
| 72 | `fundamental` | `이익 품질` |
| 73 | `fundamental` | `주주환원` |
| 11 | `sentiment` | `심리` |

→ 사실상의 불일치는 아니다 (FE는 UX 목적의 17개 sub-category로 분할). BE 5개 → FE 17개 매핑은 코드 어디에도 명시되지 않아 **암묵적 합의**에 의존한다. 향후 BE에 `display_category` 보조 필드 또는 매핑 테이블 도입 검토 가치 있음.

### 키워드 매칭 룰 커버리지 비대칭

- BE `KEYWORD_RULES` (`indicator_matcher.py:12-154`): **11개 룰**, 다루는 카탈로그 항목 11개
- FE `KEYWORD_INDICATOR_MAP` (`AddIndicatorSheet.tsx:109-139`): **28개 룰**, 다루는 카탈로그 항목 약 40개

BE 룰에서 누락되어 있고 FE에는 있는 도메인:
- 유가/원유(`id:21`), 금(`id:20`), 구리(`id:23`), 천연가스(`id:24`)
- 비트코인/이더리움(`id:25,26`)
- PER/PBR/밸류에이션(`id:51,67,68`)
- ROE/ROA/마진(`id:52,53,62,60,61`)
- 부채/레버리지/유동성(`id:54,63,64,65`)
- 배당/현금흐름/주주환원(`id:55,56,66,68,73`)
- 회전율/효율(`id:70,71`)
- 이익 품질/발생액(`id:72`)
- 인플레/CPI(`id:33`), 고용/실업(`id:31,32`), GDP/성장(`id:34,35`), 주택/모기지(`id:36,37`)
- 중국/일본/반도체 등 섹터·지역 룰

영향: BE의 `match_indicators_for_premise()` (`indicator_matcher.py:257-268`)는 키워드 매칭 실패 시 `match_by_gemini()` fallback으로 흐른다. fallback은 카탈로그 외 환각 지표를 만들 수 있어 LLM 빌더에서는 이미 비활성화됨(`indicator_matcher.py:306-307` 주석). 그러나 비-LLM 경로(`match_indicators_for_premise`)는 여전히 Gemini fallback을 호출 → **운영 위험**.

---

## description 품질

- 항목 수: 64
- 빈 description: **0건**
- 10자 미만 description: **0건**
- 평균 길이: 약 35자 (모두 한 문장으로 정의됨)
- 가장 짧은 항목 (참고용):
  - `id:24 천연가스` — "천연가스 선물 가격. 에너지 비용과 계절적 수요 반영." (28자)
  - `id:14 코스닥 지수` — "한국 중소형 성장주 시장 지수." (16자)
  - `id:22 은 (Silver)` — "은 현물 가격(USD/oz). 산업 수요와 안전자산 이중 역할." (33자)

→ description 자체는 기준치를 만족한다. 다만 FE는 description 필드를 표시하지 않는다(현재 `AddIndicatorSheet.tsx`는 name + category + freq만 노출). BE description은 (a) LLM 프롬프트 컨텍스트와 (b) `get_indicator_description()` 헬퍼 두 곳에서만 소비됨. **FE 툴팁/설명 UX 도입 시 BE description을 그대로 활용 가능**.

---

## keyword_rules 고아

### BE `KEYWORD_RULES` → catalog name 매칭

| 룰 키워드 | 참조 name | 카탈로그 존재? | indicator_type 일치? |
|----------|----------|---------------|---------------------|
| 외국인/외인/순매수 | `외국인 순매수 추이` | ✓ | `market_data` = `market_data` ✓ |
| 금리/연준/FOMC | `미국 기준금리 (Fed Funds Rate)` | ✓ | `macro` = `macro` ✓ |
| 금리/연준/FOMC | `미국 10년 국채 금리` | ✓ | `macro` = `macro` ✓ |
| VIX/공포/변동성 | `VIX (공포지수)` | ✓ | `macro` = `macro` ✓ |
| 환율/달러/원달러 | `원/달러 환율` | ✓ | `macro` = `macro` ✓ |
| RSI/MACD/기술적 | `RSI (14일)` | ✓ | `technical` = `technical` ✓ |
| 센티먼트/여론/뉴스 | `뉴스 센티먼트` | ✓ | `sentiment` = `sentiment` ✓ |
| **실적/EPS/매출/PER** | **`EPS 추이`** | ✓ | **`market_data` ≠ catalog `fundamental` ❌** |
| 기관/연기금 | `기관 순매수 추이` | ✓ | `market_data` = `market_data` ✓ |
| S&P/나스닥/다우 | `S&P 500` | ✓ | `market_data` = `market_data` ✓ |
| 코스피/KOSPI | `KOSPI 지수` | ✓ | `market_data` = `market_data` ✓ |
| 선거/정치/정책 | `VIX (공포지수)` | ✓ | `macro` = `macro` ✓ |
| 선거/정치/정책 | `KOSPI 지수` | ✓ | `market_data` = `market_data` ✓ |

**고아 룰**: 없음 (모든 룰의 참조 name이 카탈로그에 존재).

**type 불일치 1건**:
- `indicator_matcher.py:95` — `EPS 추이` 룰의 `indicator_type='market_data'`
- 카탈로그(`prompt_builder.py:190`)의 `category='fundamental'`
- 영향: `match_by_keywords()`의 반환 결과를 `category`로 그룹핑/필터하는 호출 측이 있으면 EPS가 잘못 분류됨. 현재 직접 그룹핑하는 코드는 발견되지 않았으나, **단일 소스 위반**.

### FE `KEYWORD_INDICATOR_MAP` → catalog id 매칭

- 28개 룰의 모든 `indicatorIds`가 카탈로그에 존재 (전부 검증됨)
- 고아 id 참조: 없음

### 카탈로그 항목 중 어느 룰에도 잡히지 않는 id (BE 기준)

BE `KEYWORD_RULES`가 다루는 11개 외 나머지 53개 항목은 BE 키워드 매칭 경로에서 추천되지 않는다. 결과적으로 비-LLM 경로에서는 대부분 **Gemini fallback에 의존**한다(상기 위험 항목 참조).

---

## data_params 형식

### 형식 분류

| data_source | data_params 패턴 | 예시 |
|-------------|-----------------|------|
| `fmp` (지수/원자재/암호/환율) | `{'symbol': '<SYM>'}` | `^GSPC`, `GCUSD`, `BTCUSD`, `USDKRW` |
| `fmp` (수급/펀더멘털 단순) | `{'metric': '<field>'}` | `eps`, `pbRatioTTM`, `dividendYieldTTM`, `freeCashFlowTTM` |
| `fmp` (기술적) | `{'indicator': '<NAME>', 'period': N}` (+`fast/slow/signal`) | `RSI/14`, `MACD/12/26/9` |
| `fred` | `{'series_id': '<ID>'}` | `FEDFUNDS`, `DGS10`, `UNRATE`, `CPIAUCSL` |
| `metrics` | `{'metric_code': '<code>'}` | `gross_margin`, `roic`, `fcf_margin` |
| `news_sentiment` | `{}` | — |

### 비표준 (후처리 의존) — 4건

`prompt_builder.py:190-245`에 audit_note로 명시되어 있고, common-bugs #14의 회귀 방지 흔적이 보임:

| id | name | 비표준 처리 | 위험 |
|----|------|-----------|------|
| **50** | PER (주가수익비율) | `metric='earningsYieldTTM'` + **`inverse=True`** | FMP `/key-metrics-ttm/`에 `peRatioTTM` 미존재. 호출자가 `inverse` 플래그를 인지하지 못하면 1/PER을 PER로 잘못 표시 |
| **52** | ROE (자기자본이익률) | `metric='returnOnEquityTTM'` + **`scale_multiplier=100`** | FMP가 0~1 비율로 반환. 호출자가 ×100 안 하면 0.15가 ROE 0.15%로 표시 (실제 15%) |
| **53** | ROA (총자산이익률) | `metric='returnOnAssetsTTM'` + **`scale_multiplier=100`** | 위와 동일 |
| **58** | 매출성장률 (YoY) | `metric='growthRevenue'` + **`endpoint='financial-growth'`** + `scale_multiplier=100` | `/key-metrics-ttm/`이 아닌 `/financial-growth/` 엔드포인트 사용. 일반 fetcher가 자동으로 다른 endpoint를 호출하지 않으면 N/A |

→ 4건 모두 audit_note로 의도가 문서화되어 있으나, **이를 해석하는 fetcher 측 분기가 어디 있는지** 확인 필요. `data_params`만으로 fetching하는 일반 경로가 있다면 silent fail/오류값 위험.

### 잠재 의심 항목 (FMP 심볼 표준 점검)

- `id:39 달러 인덱스 (DXY)` — `{'symbol': 'DX-Y.NYB'}`
  - `DX-Y.NYB`는 Yahoo Finance 표기. FMP 표준 심볼은 일반적으로 `DXY` 또는 별도 endpoint. FMP 응답 검증 필요.
- `id:9 원/달러 환율` — `{'symbol': 'USDKRW'}`
  - FMP forex는 `/fx/USDKRW` 또는 `USDKRW=X` 변형 가능. 현재 호출자가 어떤 endpoint로 보내는지 확인 필요.

### `KEYWORD_RULES`의 `data_params` vs 카탈로그 `data_params`

`indicator_matcher.py`의 룰 내 `data_params`는 카탈로그의 단순 케이스를 그대로 복사한 형태이며, **`inverse`/`scale_multiplier`/`endpoint`/`audit_note` 등 후처리 메타가 없음**. 룰이 다루는 11개 항목 중 후처리 필요 항목은 `EPS 추이` 하나뿐(단순 `{'metric': 'eps'}`이라 일치). 즉 룰 자체의 `data_params`로 인한 추가 위험은 없음.

다만 BE 룰의 `data_params`는 카탈로그의 진실값과 중복 정의되어 있어 **단일 소스 원칙 위반**. 카탈로그가 바뀌면 룰 쪽이 자동으로 따라가지 않는다. 향후 룰은 `name` 또는 `id`만 보유하고, 호출 시 카탈로그에서 lookup하는 구조가 안전.

---

## 권고 (참고용, 코드 미수정)

1. **BE `KEYWORD_RULES` 확장** — FE의 28개 룰 수준으로 보강하거나, 공유 JSON으로 단일화. 현재는 BE의 비-LLM 경로가 Gemini fallback에 과도 의존.
2. **`EPS 추이` type 표기 통일** — `indicator_matcher.py:95`의 `indicator_type='market_data'` → `'fundamental'`로 수정.
3. **`data_params` 후처리 분기 위치 명문화** — `inverse`/`scale_multiplier`/`endpoint` 플래그를 해석하는 fetcher 모듈을 1곳으로 통일, 카탈로그에 "참조 fetcher 명" 주석 추가.
4. **`KEYWORD_RULES`의 `data_params` 중복 제거** — 카탈로그 `name` lookup 방식으로 전환하여 단일 소스 보장.
5. **FE description 활용** — BE description 64건을 FE 툴팁/상세에 노출하면 사용자 이해도 향상 + BE description 변경에 대한 가시성 확보.
6. **BE→FE category 매핑 명시화** — 현재 암묵적 합의를 `contracts/` 또는 공유 모듈로 코드화.

— end of audit —

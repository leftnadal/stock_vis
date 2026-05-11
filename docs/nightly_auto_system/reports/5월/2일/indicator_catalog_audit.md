# 지표 카탈로그 동기화 감사 보고서

- **감사 일시**: 2026-05-02
- **대상 범위**: Thesis 지표 카탈로그 (BE 정의/후처리/매칭 + FE 표시)
- **모드**: 읽기 전용 (코드 수정 없음)

---

## 요약 (동기화 상태)

| 검사 항목 | 결과 | 비고 |
|----------|------|------|
| BE/FE ID 집합 일치 | ✅ 일치 | 양쪽 모두 64개 ID, 1:1 매핑 (1~16, 20~26, 30~47, 50~58, 60~73) |
| BE/FE 지표 이름 일치 | ✅ 일치 | 64개 모두 동일 한글 표기 |
| BE description 누락/짧음 | ✅ 양호 | 64개 전부 채워짐, 모두 16자 이상 |
| keyword_rules 고아 (BE) | ✅ 없음 | KEYWORD_RULES 11개 모두 카탈로그 이름과 매칭 |
| 카테고리 분류 체계 | ⚠️ 불일치 | BE 5개 vs FE 17개 (정밀도 다름) |
| 빈도(freq) 필드 정합성 | ⚠️ 미러 분산 | BE는 `INDICATOR_FREQUENCY` 별도 dict, FE는 `freq` 필드 — 동기화 깨질 위험 |
| 키워드 매칭 풍부도 | 🔴 BE 빈약 | BE 11개 룰 vs FE 28개 룰. BE는 폴백이 약해 환각 위험 가중 |
| 키워드 룰 매칭 방식 | ⚠️ 비대칭 | BE는 name 기반(취약), FE는 ID 기반(견고) |
| FMP data_params 정합성 | 🔴 위험 | TTM 비율 필드(`returnOnEquityTTM` 등) `* 100` 처리 가정이 카탈로그에 명시되지 않음 |
| `peRatioTTM` 필드 존재 여부 | 🔴 가능 미존재 | 버그 #14: FMP는 `earningsYieldTTM` 역수로 PE 산출 — 카탈로그에 박힌 `peRatioTTM`이 응답에 없을 위험 |
| 자체 계산 metric 위장 | ⚠️ data_source 모호 | `foreign_net_buy`, `institutional_net_buy`, `revenueGrowthYoY` 등은 FMP 단순 조회로는 못 받음 |

**총평**: ID/이름/description 차원에서는 동기화가 깔끔하지만, **(1) 카테고리 라벨 체계 + (2) 빈도(freq) 미러 + (3) 키워드 룰 풍부도/매칭 방식 + (4) FMP data_params 형식 가정** 4축에서 운영 위험이 누적되고 있다. 특히 (3)/(4)는 사용자에게 보이는 추천/렌더 결과 품질에 직접 영향한다.

---

## BE ↔ FE 불일치 목록

### 1. ID 집합

- **결과: 완전 일치 (64개)**
- 양쪽 모두 다음 ID 보유: `1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 20, 21, 22, 23, 24, 25, 26, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 50, 51, 52, 53, 54, 55, 56, 57, 58, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73`
- 빈 ID: `17, 18, 19, 27, 28, 29, 48, 49, 59` — 향후 추가용 갭으로 보임. 양쪽 동일.
- BE 카운트: `len(INDICATOR_CATALOG) == 64` (CLAUDE.md에 적힌 "73개"는 마지막 ID 73을 가리키는 표기 오해석으로 보임 — **실제 항목 수는 64개**)
- FE 카운트: 동일

### 2. 지표 이름 (정확 일치 검사)

64개 모두 한글 이름 1:1 매칭. 차이 없음.

### 3. 카테고리 라벨 체계 (⚠️ 불일치)

- **BE 카테고리 (5종)**: `market_data`, `macro`, `technical`, `fundamental`, `sentiment`
- **FE 카테고리 (17종)**: `수급`, `주요 지수`, `원자재`, `암호화폐`, `금리`, `환율/변동성`, `고용/성장`, `물가/주택`, `기술적`, `펀더멘털`, `재무 체질`, `밸류에이션`, `성장`, `운영 효율`, `이익 품질`, `주주환원`, `심리`

**같은 ID라도 카테고리 표기가 다른 사례**

| ID | 이름 | BE category | FE category |
|----|------|-------------|-------------|
| 1 | 외국인 순매수 추이 | market_data | 수급 |
| 3 | S&P 500 | market_data | 주요 지수 |
| 20 | 금 (Gold) | market_data | 원자재 |
| 25 | 비트코인 (BTC) | market_data | 암호화폐 |
| 6 | 미국 기준금리 | macro | 금리 |
| 8 | VIX | macro | 환율/변동성 |
| 33 | CPI | macro | 물가/주택 |
| 67 | EV/EBITDA | fundamental | 밸류에이션 |
| 69 | 영업이익 성장률 | fundamental | 성장 |
| 72 | 발생액 비율 | fundamental | 이익 품질 |

**위험**: BE에 카테고리 단일 소스가 있는데 FE가 **자체 분류**로 재정의 중. 신규 지표 추가 시 누락된 분류는 FE에서 어느 카테고리에도 들어가지 못해 화면에서 사라질 수 있다 (FE의 `categoryOrder`가 화이트리스트로 동작 — `AddIndicatorSheet.tsx:211`).

**대응 권고 (수정 금지 모드라 기록만)**: BE 카탈로그에 `subcategory` 또는 `display_category` 필드를 추가하고 FE는 그것만 미러하도록 단방향 동기화.

### 4. 빈도(freq) 표기 (⚠️ 미러 분산)

- **BE**: `INDICATOR_CATALOG`에 `freq` 필드 없음 → 별도 dict `INDICATOR_FREQUENCY`로 ID→빈도 분리 보관 (`prompt_builder.py:305-326`)
- **FE**: `freq` 필드를 카탈로그 항목 안에 직접 보유 (`AddIndicatorSheet.tsx:11`)
- **불일치 검사**: 이번 감사에서 모든 64개 ID에 대해 BE `INDICATOR_FREQUENCY` ↔ FE `freq` 비교 시 **모두 일치**했음. 현재로서는 데이터 차이 없음.
- **위험**: 한쪽에서 freq 변경 시 다른 쪽이 따라가지 않으면 즉시 깨짐. 단일 소스 부재 (3곳 분산: `prompt_builder.INDICATOR_CATALOG`/`INDICATOR_FREQUENCY`/`AddIndicatorSheet`).

### 5. description 필드 (FE 측면)

- BE: 모든 64개 항목에 한글 description 있음.
- FE: `CatalogIndicator` 타입에 `description` 필드 자체가 없음 (id/name/category/freq만 보유).
- **결과**: FE 사용자는 카드 hover/탭 시 description을 볼 수 없음. 사용자에게 의미 전달이 약화되고, BE가 가진 73개 카탈로그 description의 가치가 화면에 흘러나오지 못한다.

---

## description 품질

### 빈 description

- **없음**. 64/64 모두 채워짐.

### 너무 짧은 description (< 10자)

- **없음**. 최소 길이 16자 (`'코스닥 지수'` → `'한국 중소형 성장주 시장 지수.'`).

### 길이 분포 (참고)

| 구간 | 개수 |
|------|------|
| 16~25자 | ~12개 (코스닥/항셍/금/은/구리/천연가스/실업률/CPI 단형) |
| 26~40자 | ~38개 (대다수) |
| 41~50자 | ~14개 (외국인 순매수, 금리류, 모기지 금리 등 부연 포함) |

전반적으로 "1문장 정의 + 1문장 활용/맥락" 패턴이 일관됨. 품질 양호.

### 일관성 점검 — 사소한 표기 흔들림

대부분 일관되나 다음 항목들은 **stylistic drift** 정도의 미세 차이:

- 일부는 끝맺음 마침표(`.`) 사용, 일부는 마침표 두 번 연결(`. ...`). 통일 강제 불필요.
- `support_direction`이 모든 카탈로그 항목에 `positive` 또는 `negative`로 채워져 있음. **금(Gold), 은, 구리, 비트코인** 등 양면적 자산이 일률 `positive`로 표기 — 가설 컨텍스트(인플레 헤지 vs 위험자산)에 따라 해석이 달라야 하므로 추후 가설 유형별 가변 매핑 검토 가치 있음. (현재는 결함 아님, 단순 메모.)

---

## keyword_rules 고아

### BE `KEYWORD_RULES` (`indicator_matcher.py:12-154`) — 룰 11개

| # | 키워드 그룹 | 매칭 지표 이름 | 카탈로그 매핑 | 상태 |
|---|------------|--------------|---------------|------|
| 1 | 외국인/외인/순매수/순매도/foreign | 외국인 순매수 추이 | id:1 | ✅ |
| 2 | 금리/연준/FOMC/fed/기준금리/금리인하/금리인상 | 미국 기준금리 (Fed Funds Rate) + 미국 10년 국채 금리 | id:6, id:7 | ✅ |
| 3 | VIX/공포/변동성/변동성지수/volatility | VIX (공포지수) | id:8 | ✅ |
| 4 | 환율/달러/원달러/USD/KRW/원화 | 원/달러 환율 | id:9 | ✅ |
| 5 | RSI/MACD/기술적/과매수/과매도/이동평균/MA | RSI (14일) | id:10 | ✅ |
| 6 | 센티먼트/여론/뉴스/심리/감성 | 뉴스 센티먼트 | id:11 | ✅ |
| 7 | 실적/EPS/매출/영업이익/순이익/PER/earnings | EPS 추이 | id:5 | ✅ |
| 8 | 기관/기관투자자/연기금/보험/자산운용 | 기관 순매수 추이 | id:2 | ✅ |
| 9 | S&P/S&P500/나스닥/NASDAQ/미국시장/다우/DOW | S&P 500 | id:3 | ✅ |
| 10 | 코스피/KOSPI/종합주가지수 | KOSPI 지수 | id:4 | ✅ |
| 11 | 선거/정치/정책/대통령/국회 | VIX (공포지수) + KOSPI 지수 | id:8, id:4 | ✅ |

**고아 규칙: 0건.** 모든 BE 룰이 카탈로그 이름과 정확히 매칭됨.

### 매칭 방식의 구조적 위험 (⚠️ 정상 매칭이지만 취약)

- BE는 `'name': '외국인 순매수 추이'`처럼 **문자열 이름**으로 카탈로그를 가리킨다. `_find_in_catalog(name)`(`indicator_matcher.py:332-338`)이 이름으로 검색.
- 만약 카탈로그에서 한글 이름이 살짝 변경되면(예: `'외국인 순매수 추이'` → `'외국인 순매수'`), 룰이 **조용히 깨진다 (런타임 None)**.
- 권고: BE 룰을 FE처럼 `indicatorIds: [1]` 패턴으로 옮기거나, 모듈 임포트 시 한 번 검증.

### BE 룰 누락 — FE에는 있는데 BE에는 없는 키워드 카테고리

FE의 `KEYWORD_INDICATOR_MAP`(`AddIndicatorSheet.tsx:109-139`)에는 28개 룰이 있지만 BE는 11개. 다음 도메인은 **BE에서 키워드 매칭이 전혀 안 되어 Gemini 폴백(`match_by_gemini`)에 의존**한다 — 카탈로그에 없는 환각 지표 생성 위험을 키운다:

| 누락 키워드 그룹 | FE에서 매핑되는 ID |
|---|---|
| 유가/원유/wti/석유/에너지/opec/오일 | 21 |
| 금/gold/금값/안전자산 | 20 |
| 구리/copper/산업금속/경기선행 | 23 |
| 천연가스/lng/가스 | 24 |
| 비트코인/btc/암호화폐/크립토/코인 | 25, 26 |
| per/pbr/밸류에이션/저평가/고평가/가치 | 50, 51, 67, 68 |
| roe/roa/수익성/이익률/roic/마진 | 52, 53, 57, 62, 60, 61 |
| 부채/레버리지/debt/재무건전/유동성/현금 | 54, 63, 64, 65 |
| 배당/dividend/현금흐름/fcf/자사주/주주환원 | 55, 56, 66, 68, 73 |
| 회전율/효율/재고/매출채권/운영 | 70, 71 |
| 이익 품질/발생액/accrual/분식/회계 | 72, 66 |
| 인플레/cpi/물가/소비자물가 | 33 |
| 고용/실업/nfp/비농업/일자리 | 31, 32 |
| gdp/성장/경기/산업생산 | 34, 35 |
| 주택/부동산/모기지/reit | 36, 37 |
| 반도체/테크/ai/엔비디아/nvidia/칩 | 12, 3 |
| 중국/항셍/홍콩 | 16 |
| 일본/니케이/엔화 | 15 |
| 광고/디지털/플랫폼/meta/구글/google | 3, 12 |

> 참고: `match_indicators_for_llm`(`indicator_matcher.py:271-329`)은 LLM 빌더에서 PK 매칭이 실패하면 `match_by_keywords`만 폴백하고 `match_by_gemini`는 의도적으로 제외 — 환각 방지 차원. 그래서 **위 누락 룰은 LLM 빌더 경로에서 추천 누락으로 직결**된다.

---

## data_params 형식

### BE 카탈로그가 사용하는 4가지 형식

1. **FMP 자체 metric 키** — `{'metric': 'foreign_net_buy'}`, `{'metric': 'institutional_net_buy'}`, `{'metric': 'eps'}`, `{'metric': 'revenueGrowthYoY'}` 등 (id 1, 2, 5, 58)
2. **FMP 심볼** — `{'symbol': '^GSPC'}`, `{'symbol': 'GCUSD'}`, `{'symbol': '^VIX'}` 등 (지수/원자재/환율)
3. **FRED 시리즈 ID** — `{'series_id': 'FEDFUNDS'}`, `{'series_id': 'DGS10'}` 등 (금리/거시)
4. **FMP technical 지시자** — `{'indicator': 'RSI', 'period': 14}` 등 (id 10, 40~47)
5. **FMP key-metrics-ttm 비율 필드** — `{'metric': 'peRatioTTM'}`, `{'metric': 'returnOnEquityTTM'}` 등 (id 50~58)
6. **내부 metrics 시스템 코드** — `{'metric_code': 'gross_margin'}` 등 (id 60~73)

### 위험 영역 1 — `peRatioTTM` 필드 존재 여부 (🔴)

- 카탈로그 id:50 PER → `{'metric': 'peRatioTTM'}`
- CLAUDE.md 버그 #14 적시: **"FMP Key Metrics는 `earningsYieldTTM`을 제공 — 그 역수로 PE 계산"**
- 즉 FMP `/stable/key-metrics-ttm` 응답 키에 `peRatioTTM` 자체가 없을 가능성. 그렇다면 단순 dict 조회는 `None` 반환.
- 카탈로그가 이 변환 규칙을 표기하지 않아, data_params만 보고 구현하는 사람이 동일 버그를 반복할 위험.

### 위험 영역 2 — TTM 비율 필드의 단위 처리 (🔴)

CLAUDE.md 버그 #14 적시: **"`returnOnEquityTTM` * 100 = ROE(%)"**. FMP는 비율(0~1) 또는 100분율 — 일관성 부족. 카탈로그에 단위 표기가 없는 항목들:

| ID | 이름 | data_params metric | 단위 처리 위험 |
|----|------|--------------------|----------------|
| 52 | ROE (자기자본이익률) | `returnOnEquityTTM` | 비율 → `*100` 명시 안 됨 |
| 53 | ROA (총자산이익률) | `returnOnAssetsTTM` | 동일 |
| 54 | 부채비율 (Debt/Equity) | `debtToEquityTTM` | 비율 표기 통일 필요 |
| 56 | 배당수익률 | `dividendYieldTTM` | 비율 → `*100` 가능 |
| 57 | 영업이익률 | `operatingProfitMarginTTM` | 동일 |

→ 사용자에게 노출되는 값이 0.15 vs 15.0으로 100배 차이. CLAUDE.md 버그 #15(캐시 키 불일치)·#22(필드명 불일치)와 같은 카테고리의 잠재적 회귀 가능성.

### 위험 영역 3 — 자체 계산 metric의 data_source 위장 (⚠️)

다음은 카탈로그상 `data_source: 'fmp'`로 표기되었지만, FMP의 단일 endpoint 호출로는 즉시 못 받는 합성 metric:

- id:1 `foreign_net_buy` — 외국인 순매수 (자체 일별 집계 필요)
- id:2 `institutional_net_buy` — 기관 순매수 (동일)
- id:58 `revenueGrowthYoY` — FMP는 `/stable/financial-growth`에 `revenueGrowth`로 제공 (이름 mismatch 가능)

→ data provider 어댑터에서 metric 키 매핑 테이블이 따로 있어야 정상 동작. 그러나 카탈로그만으로는 그 사실이 드러나지 않아 신규 개발자에게 **유령 endpoint 가설**을 심을 수 있다.

### 위험 영역 4 — 내부 metrics 시스템 (`metric_code`) 의존 (⚠️ 정상이나 노출)

id 60~73은 `data_source: 'metrics'` + `{'metric_code': '...'}`. 이는 `metrics` 앱(공유 지표 메타데이터)을 거치는 정상 분리. 다만 `metric_code` 값들이 metrics 앱의 등록된 코드와 정확히 일치하는지는 이번 감사 범위 외 (확인 권고: `metrics/registry.py` 또는 `MetricMetadata.code` 테이블).

### FE 측 data_params

- FE `CatalogIndicator`는 data_params 자체를 들고 있지 않다 (`AddIndicatorSheet.tsx:8-13` 참조: id/name/category/freq만).
- 이는 **의도된 분리**: FE는 ID만 알고, 실제 데이터 호출은 BE가 담당. 따라서 "data_params 형식 BE/FE 불일치"는 발생할 여지가 없다 — 단, 이로 인해 BE 어댑터 한 곳이 모든 form을 정확히 처리해야 한다는 책임이 가중된다.

---

## 결론 및 권고 우선순위 (참고용 메모, 수정 없음)

1. **🔴 즉시 검증 필요**: `peRatioTTM` 키 존재 여부 + `returnOnEquityTTM` 등 비율 필드의 `*100` 변환 — 어댑터 통합 테스트 1회.
2. **🔴 LLM 추천 품질**: `KEYWORD_RULES` 11개를 FE의 28개 수준으로 보강. 특히 유가/금/PER/ROE/배당/CPI/고용/GDP 도메인은 반드시 추가 — Gemini 폴백 의존도와 환각 위험 직결.
3. **⚠️ 단일 소스화**: 카테고리 라벨 + freq를 BE 카탈로그 항목 내부로 흡수, FE는 컨트랙트 미러만 유지.
4. **⚠️ 매칭 방식 통일**: BE `KEYWORD_RULES`를 name 기반에서 ID 기반(`indicator_ids: [1, 7]`)으로 마이그레이션 → 이름 변경 회귀 차단.
5. **ℹ️ description의 FE 노출**: 카탈로그 description을 contracts에 포함시켜 FE가 hover로 보여주면 사용자 가치 상승 + 가설 빌더의 "왜 이 지표"를 보강.

---

*감사 완료. 코드 변경 없음 — 본 보고서만 산출.*

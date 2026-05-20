# 지표 카탈로그 동기화 감사 보고서

- **생성일**: 2026-05-21
- **대상**: 64개 지표 카탈로그 (BE/FE/Matcher 3원천 미러)
- **검사 범위**: 코드 읽기 전용 — 수정 없음
- **소스 파일**:
  - BE 카탈로그: `thesis/services/prompt_builder.py:14-310`
  - BE 후처리: `thesis/services/llm_postprocess.py:82-95`
  - BE 매처: `thesis/services/indicator_matcher.py:11-154` (`KEYWORD_RULES`)
  - FE 카탈로그: `frontend/components/thesis/AddIndicatorSheet.tsx:15-91`
  - FE 매처: `frontend/components/thesis/AddIndicatorSheet.tsx:109-139` (`KEYWORD_INDICATOR_MAP`)

---

## 요약 (동기화 상태)

| 항목 | 결과 | 비고 |
|------|------|------|
| BE ↔ FE 지표 ID 집합 | ✅ 일치 (64개) | 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,20–26,30–47,50–58,60–73 |
| BE ↔ FE 지표명 | ✅ 일치 | 한글 표기 64건 모두 동일 |
| BE ↔ FE 업데이트 주기 | ✅ 일치 | 일/주/월/분기 라벨 일치 |
| description 필드 | ✅ 64건 모두 보유 (10자 이상) | 빈 항목 없음 |
| BE `KEYWORD_RULES` 지표명 ↔ 카탈로그 | ✅ 명칭 일치 | 11개 룰의 indicator name 모두 카탈로그에 존재 |
| BE `KEYWORD_RULES` ↔ FE `KEYWORD_INDICATOR_MAP` 커버리지 | ⚠️ **불균형** | BE 11개 룰 vs FE 29개 룰 — FE가 약 2.6× 더 넓음 |
| 분류(category) 라벨 | ⚠️ **체계 차이** | BE: 5개 상위(`market_data/macro/technical/fundamental/sentiment`) ↔ FE: 17개 세분류 |
| `data_params` 형식 | ⚠️ **잠재 위험 1건** | ID 39 `DX-Y.NYB` FMP 호환성 의심 |
| `data_source='metrics'` 14건 (60–73) | ℹ️ 별도 채널 | `metric_code` 키 + `quarterly_metric_fetcher` 의존 |

**한 줄 요약**: 핵심 64개 지표 정의(ID/이름/주기/description)는 BE-FE 완전 동기화 상태. **단, 키워드 매칭 규칙(추천 엔진)이 BE에서 11개로 빈약해 LLM 빌더 PK 매칭 실패 시 fallback 품질이 FE 대비 크게 떨어진다.** 카테고리 분류 체계도 BE/FE 간 1:N 관계로 추후 유지보수 부담.

---

## BE ↔ FE 불일치 목록

### 지표 정의 (ID / 이름 / 주기)

**불일치 없음.** 64개 항목 모두 BE(`prompt_builder.py` `INDICATOR_CATALOG`)와 FE(`AddIndicatorSheet.tsx` `INDICATOR_CATALOG`)에서 id·name·freq가 1:1 매칭.

검증한 ID 집합:
```
1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,
20,21,22,23,24,25,26,
30,31,32,33,34,35,36,37,38,39,
40,41,42,43,44,45,46,47,
50,51,52,53,54,55,56,57,58,
60,61,62,63,64,65,66,67,68,69,70,71,72,73
```

BE/FE 모두 동일. 누락 ID 없음.

### 카테고리 분류 (구조적 차이)

BE의 5개 상위 카테고리 vs FE의 17개 세분류 매핑:

| BE category | FE category(들) | 비고 |
|-------------|-----------------|------|
| `market_data` | 수급 / 주요 지수 / 원자재 / 암호화폐 | FE가 4개로 쪼갬 |
| `macro` | 금리 / 환율/변동성 / 고용/성장 / 물가/주택 | FE가 4개로 쪼갬 |
| `technical` | 기술적 | 동일 |
| `fundamental` | 펀더멘털 / 재무 체질 / 밸류에이션 / 성장 / 운영 효율 / 이익 품질 / 주주환원 | FE가 7개로 쪼갬 |
| `sentiment` | 심리 | 동일 |

**리스크**: 새 지표 추가 시 BE는 5개 중 선택만 하면 되지만 FE는 적절한 세분류를 별도로 결정해야 함. 두 곳 동시 갱신 누락 가능성 존재 (CLAUDE.md "feedback_indicator_catalog_sync"와 일치).

### `data_source` 분포

| data_source | 개수 | ID 예시 |
|-------------|------|---------|
| `fmp` | 36 | 1,2,3,4,5,8,9,10,12–16,20–26,39,40–47,50–58 |
| `fred` | 11 | 6,7,30,31,32,33,34,35,36,37,38 |
| `metrics` | 14 | 60–73 |
| `news_sentiment` | 1 | 11 |

FE는 `data_source`를 보유하지 않으므로 직접적 mismatch 없음. 다만 FE 매칭/표시 로직이 `data_source`를 모르는 채 동작하므로, BE가 ID로 조회만 잘 되면 문제없음.

---

## description 품질

### 빈 description

**없음**. 64개 모두 `description` 필드 보유.

### 짧은 description (10자 미만)

**없음**. 최단 사례를 발견 못함. 표본:
- ID 4 KOSPI: "한국 유가증권시장 전체 종목 시가총액 가중 지수." (29자)
- ID 14 코스닥: "한국 중소형 성장주 시장 지수." (16자)
- 평균 30~50자 수준.

### 검토 의견

- 모든 description은 "정의 + 의미/용도" 패턴으로 일관성 유지.
- 일부 길이는 짧지만(15~20자) 정보량은 충분.
- 개선 여지: ID 14("한국 중소형 성장주 시장 지수.")는 코스피와 비교했을 때 정보가 다소 빈약. 우선순위 낮음.

---

## keyword_rules 고아

### BE `KEYWORD_RULES` (indicator_matcher.py)

전체 11개 룰의 indicator `name` 값이 카탈로그에 존재하는지 검증:

| 룰 키워드 그룹 | 추천 지표명 | 카탈로그 매칭 | 상태 |
|---|---|---|---|
| 외국인/외인/순매수 | 외국인 순매수 추이 | id:1 | ✅ |
| 금리/연준/FOMC | 미국 기준금리 (Fed Funds Rate) | id:6 | ✅ |
| 금리/연준/FOMC | 미국 10년 국채 금리 | id:7 | ✅ |
| VIX/공포/변동성 | VIX (공포지수) | id:8 | ✅ |
| 환율/달러 | 원/달러 환율 | id:9 | ✅ |
| RSI/MACD/기술적 | RSI (14일) | id:10 | ✅ |
| 센티먼트/여론/뉴스 | 뉴스 센티먼트 | id:11 | ✅ |
| 실적/EPS/매출 | EPS 추이 | id:5 | ✅ |
| 기관/기관투자자 | 기관 순매수 추이 | id:2 | ✅ |
| S&P/나스닥/다우 | S&P 500 | id:3 | ✅ |
| 코스피/KOSPI | KOSPI 지수 | id:4 | ✅ |
| 선거/정치/정책 | VIX (공포지수) | id:8 | ✅ |
| 선거/정치/정책 | KOSPI 지수 | id:4 | ✅ |

**고아 룰: 없음.** 모든 추천 지표명이 카탈로그에 존재.

### 구조적 위험 1: 이름 기반 매칭

`KEYWORD_RULES`는 `name` 문자열로 카탈로그를 역참조 (`_find_in_catalog()`, `indicator_matcher.py:332-338`). PK(id) 기반이 아니므로 카탈로그에서 이름만 바꿔도 매칭이 silently 실패할 수 있음. 예:
- 카탈로그 ID 8 이름을 "VIX (공포지수)" → "VIX 변동성 지수"로 개명하면 KEYWORD_RULES 변경 없이도 매칭 실패.

권고: KEYWORD_RULES도 `indicator_db_id` 키를 추가해서 PK 기준 매칭으로 통일 (수정 미수행).

### 구조적 위험 2: BE ↔ FE 키워드 커버리지 격차

| 위치 | 룰 개수 | 커버리지 |
|---|---|---|
| BE `KEYWORD_RULES` (indicator_matcher.py) | 11 | 외국인/기관/금리/VIX/환율/RSI·MACD/실적/S&P/코스피/센티먼트/선거 |
| FE `KEYWORD_INDICATOR_MAP` (AddIndicatorSheet.tsx) | 29 | + 유가/금/구리/천연가스/비트코인/PER·PBR/ROE·ROA/부채·레버리지/배당·FCF/회전율/이익품질/CPI/고용/GDP/주택·모기지/반도체·AI/중국/일본/광고·플랫폼 |

**임팩트**:
- LLM 빌더 흐름에서 LLM이 `indicator_db_id`를 반환하지 못한 경우(`match_indicators_for_llm` 2순위, `indicator_matcher.py:312-326`) BE `match_by_keywords()`로 fallback.
- BE 룰에 PER, 유가, CPI, 부채 등 18개 카테고리가 누락되어 있어 fallback이 빈 결과 반환 → premise에 지표 0개 결과 가능 (`llm_postprocess.py:159-162` warning 트리거).
- FE UI에서는 동일 키워드로 풍부한 "전제 관련 추천" 표시 → **사용자 체감: FE는 추천 풍부, BE 자동 매핑은 인색**한 모순.

권고: BE `KEYWORD_RULES`에 FE의 18개 추가 룰을 미러링 (수정 미수행, 의사결정 필요).

### 매칭되지 않는 키워드

`match_by_gemini()` (`indicator_matcher.py:186-254`)는 카탈로그 외 지표명을 생성할 수 있어 환각 위험. **이미 `match_indicators_for_llm`에서 제외 처리됨** (`indicator_matcher.py:306-307` 주석). 단, `match_indicators_for_premise()` (general path, `indicator_matcher.py:257-268`)에서는 여전히 fallback으로 호출. 호출 경로 추가 점검 필요.

---

## data_params 형식

### 출처별 형식 표

| data_source | 필수 키 | 예시 |
|-------------|---------|------|
| `fmp` (지수/원자재/암호) | `symbol` | `^GSPC`, `^VIX`, `GCUSD`, `BTCUSD`, `USDKRW` |
| `fmp` (펀더멘털) | `metric` | `eps`, `earningsYieldTTM`, `returnOnEquityTTM` |
| `fmp` (기술적) | `indicator` + `period` (or `fast/slow/signal`) | `{indicator: RSI, period: 14}` |
| `fred` | `series_id` | `FEDFUNDS`, `DGS10`, `UNRATE` |
| `metrics` | `metric_code` | `gross_margin`, `roic`, `net_debt_to_ebitda` |
| `news_sentiment` | `{}` (빈 dict) | — |

### 잠재 위험

| ID | 이름 | data_params | 위험 |
|----|------|-------------|------|
| 39 | 달러 인덱스 (DXY) | `{symbol: 'DX-Y.NYB'}` | ⚠️ FMP에서 `DX-Y.NYB` 표기는 Yahoo Finance 스타일. FMP 자체 심볼은 `DXY` 또는 `USDX` 가능성. 실제 fetch 시 404 가능. |
| 58 | 매출성장률 (YoY) | `{metric: 'growthRevenue', endpoint: 'financial-growth', scale_multiplier: 100, audit_note: ...}` | ℹ️ 표준 key-metrics-ttm 경로가 아닌 `/financial-growth` 별도 엔드포인트 사용. fetch 코드 분기 처리 필요 (audit_note에 명시됨, common-bugs #14 회귀 방지 적용). |

### 이미 적용된 #14 회귀 방지 (audit_note)

| ID | 패턴 | 비고 |
|----|------|------|
| 50 PER | `inverse: True`, `metric: earningsYieldTTM` | `peRatioTTM` 미존재 회피 |
| 52 ROE | `scale_multiplier: 100` | 0~1 ratio → % 변환 |
| 53 ROA | `scale_multiplier: 100` | 동일 패턴 예방 |
| 58 매출성장률 | `endpoint: financial-growth` | 별도 경로 필요 명시 |

이 4건은 CLAUDE.md common-bugs #14 / audit P0 #11 대응이 정상 반영됨. ✅

### `metrics` data_source (14건, ID 60–73)

`{metric_code: <value>}` 형식. 별도 fetch 채널인 `thesis/services/quarterly_metric_fetcher.py` 경유 (audit 시 별도 파일 검증 미실시). 카탈로그-fetcher 간 metric_code 화이트리스트 동기화 여부는 본 감사 범위 밖.

---

## 종합 권고 (참고용, 수정 미수행)

1. **BE `KEYWORD_RULES` 보강** (P1) — FE의 18개 미러 룰 추가. fallback 빈도 높음.
2. **이름 기반 매칭 → PK 기반 통일** (P2) — `KEYWORD_RULES`에 `indicator_db_id` 키 추가.
3. **카테고리 분류 통일** (P3) — BE를 FE의 17개 세분류로 확장하거나, FE를 5개 상위로 축소.
4. **ID 39 `DX-Y.NYB` FMP 실호출 검증** (P2) — 운영 로그 또는 한 번의 수동 fetch로 확인.
5. **`metric_code` 화이트리스트 동기화** — `quarterly_metric_fetcher`와 카탈로그(60–73) 대조 감사 별도 수행 권장.

---

**감사 종료**. 코드 변경 없음. 다음 액션은 사용자 결정 사항.

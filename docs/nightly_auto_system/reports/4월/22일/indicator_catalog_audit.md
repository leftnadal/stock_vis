# 지표 카탈로그 동기화 감사 보고서

**감사일**: 2026-04-23
**범위**: Thesis Control 지표 카탈로그의 BE↔FE 동기화, description 품질, keyword_rules 정합성, data_params 형식 정합성
**감사 대상 파일**:
- BE 정의: `thesis/services/prompt_builder.py` (INDICATOR_CATALOG)
- BE 후처리: `thesis/services/llm_postprocess.py` (indicator_db_id 교정)
- BE 매칭: `thesis/services/indicator_matcher.py` (KEYWORD_RULES)
- BE 소비: `thesis/tasks/eod_pipeline.py` (_fetch_fmp/fred/metrics_value)
- FE 미러: `frontend/components/thesis/AddIndicatorSheet.tsx`

---

## 요약 (동기화 상태)

| 항목 | 결과 | 심각도 |
|------|------|--------|
| ID 일치 (BE 64개 ↔ FE 64개) | ✅ 완전 일치 | — |
| 이름 동기화 | ⚠️ **4건 불일치** (ID 6, 7, 30, 54) | **중** |
| description 누락 | ✅ 없음 (모두 ≥15자) | — |
| description 10자 미만 | ✅ 없음 | — |
| keyword_rules 고아 (카탈로그에 없음) | ✅ 없음 | — |
| keyword_rules 미커버 카탈로그 지표 (BE) | ⚠️ **53개/64개** (82%) | **중** |
| keyword_rules 미커버 카탈로그 지표 (FE) | ℹ️ 약 12개/64개 (19%) | 낮음 |
| BE KEYWORD_RULES vs FE KEYWORD_INDICATOR_MAP 규칙 차이 | ⚠️ **BE 11개 / FE 29개** 비대칭 | **중** |
| data_params 소비자 vs CATALOG 형식 | ❌ **fundamental 9건 치명 불일치** | **높음** |
| FMP symbol 형식 불일치 (`DX-Y.NYB`) | ⚠️ 1건 | 중 |

**가장 심각한 이슈 (우선순위 P0)**
1. **펀더멘털 TTM 지표 9개(ID 50~58)는 `data_source='fmp'` + metric 명은 `peRatioTTM` 등**이지만, `thesis/tasks/eod_pipeline.py:_fetch_fmp_value`는 `FMPClient.get_quote(symbol)` 응답에서만 값을 추출. `get_quote`는 `/stable/quote`로 주가만 반환하며 `peRatioTTM` 필드를 포함하지 않음 → 런타임에서 **모두 fetch 실패** 가능 (`/stable/key-metrics` 미호출).
2. BE KEYWORD_RULES 커버리지 82% 누락 — 카탈로그 확장에 맞춰 보강 필요 (FE는 이미 29개 규칙으로 훨씬 촘촘).

---

## BE ↔ FE 불일치 목록

### 1) 이름 불일치 (같은 ID, 다른 이름)

| ID | BE (prompt_builder.py) | FE (AddIndicatorSheet.tsx) | 영향 |
|----|------------------------|----------------------------|------|
| 6  | `미국 기준금리 (Fed Funds Rate)` | `미국 기준금리` | FE 화면에 "지표 추가" 버튼으로 추가 후 저장 시, BE가 name으로 표시하는 곳(예: LLM prompt `build_indicator_block`)과 다른 라벨이 노출될 수 있음. `get_indicator_description()`은 prefix 매칭이므로 BE name을 기준으로 정상 조회. |
| 7  | `미국 10년 국채 금리` | `미국 10년 국채` | 동일 |
| 30 | `미국 2년 국채 금리` | `미국 2년 국채` | 동일 |
| 54 | `부채비율 (Debt/Equity)` | `부채비율 (D/E)` | 동일 + FE 라벨 축약 표기 일관성 문제 |

### 2) BE에만 있거나 FE에만 있는 항목
- **없음** — 64개 ID 기준 전체 양방 존재 (ID 1~16 일부, 20~26, 30, 31~39, 40~47, 50~58, 60~73, 5, 6, 7, 8, 9, 10, 11).

### 3) FE가 BE 대비 부족한 메타데이터
- FE 카테고리(`수급 / 주요 지수 / 원자재 / 암호화폐 / 금리 / 환율·변동성 / 고용·성장 / 물가·주택 / 기술적 / 펀더멘털 / 재무 체질 / 밸류에이션 / 성장 / 운영 효율 / 이익 품질 / 주주환원 / 심리`) 17종 **세분화**.
- BE 카테고리(`CATEGORY_LABELS`) 5종(`market_data / macro / technical / fundamental / sentiment`)만 정의 → FE와 의미가 일치하는 1:1 매핑 없음.
- 결과: FE에서 "재무 체질"을 선택한 사용자 의도를 BE에서는 `fundamental`로만 인지.

### 4) FE category 문자열과 BE CATEGORY_LABELS 키 불일치 (정보성)
FE는 한국어 세분 카테고리 (`category: '재무 체질'` 등), BE는 영어 기준 5분류 (`category: 'fundamental'`). 프론트엔드는 자체 분류만 사용하므로 **현재 기능상 문제 없음**이나, 추후 BE가 UI 메타데이터를 응답할 경우 동기화 규칙 재정의 필요.

---

## description 품질

### 요약
- **전체 64개 지표 모두 description 존재**
- **10자 미만 없음** — 가장 짧은 것도 16자 (ID 14 "한국 중소형 성장주 시장 지수.")
- 평균 길이 약 35~50자, 문장 마침표 일관

### 짧은 description 목록 (참고, 30자 미만)
| ID | 이름 | 길이 | description |
|----|------|------|-------------|
| 14 | 코스닥 지수 | 16자 | 한국 중소형 성장주 시장 지수. |
| 4 | KOSPI 지수 | 24자 | 한국 유가증권시장 전체 종목 시가총액 가중 지수. |
| 35 | 산업생산지수 | 27자 | 제조업/광업/전력 생산량 지수. 실물 경기 활동도 대리 지표. |

→ 품질 이슈 없음, 모두 지표 역할을 이해 가능한 수준.

### 빈 description
- 없음 ✅

### 테스트 커버
`tests/unit/thesis/test_llm_builder.py:144`의 `test_indicator_catalog_has_all_fields` 가 `id / name / category / data_source / data_params / support_direction / description` 필수 필드를 검증 중 — 회귀 방지 장치 존재.

---

## keyword_rules 고아 및 커버리지

### BE `thesis/services/indicator_matcher.py`의 KEYWORD_RULES

총 **11개 규칙**이 다음 **12개 카탈로그 지표**만 참조 (모두 CATALOG에 존재):

| KEYWORD_RULES indicator name | CATALOG ID | 상태 |
|------------------------------|------------|------|
| 외국인 순매수 추이 | 1 | ✅ |
| 미국 기준금리 (Fed Funds Rate) | 6 | ✅ |
| 미국 10년 국채 금리 | 7 | ✅ |
| VIX (공포지수) | 8 | ✅ (2회 중복 — "VIX" 규칙 + "선거" 규칙) |
| 원/달러 환율 | 9 | ✅ |
| RSI (14일) | 10 | ✅ |
| 뉴스 센티먼트 | 11 | ✅ |
| EPS 추이 | 5 | ✅ |
| 기관 순매수 추이 | 2 | ✅ |
| S&P 500 | 3 | ✅ |
| KOSPI 지수 | 4 (2회 중복) | ✅ |

→ **카탈로그에 존재하지 않는 고아 rule 없음** ✅

### BE KEYWORD_RULES 미커버 CATALOG 지표 (53개 / 64개 = 82% 미커버)

다음 지표는 keyword 룰로 매칭 불가 (LLM이 `indicator_db_id`를 직접 반환하지 못할 경우 fallback이 작동하지 않음):

| 카테고리 | 미커버 ID 목록 | 개수 |
|----------|----------------|------|
| market_data (인덱스 확장) | 12 NASDAQ, 13 다우, 14 코스닥, 15 니케이, 16 항셍 | 5 |
| market_data (원자재) | 20 금, 21 WTI, 22 은, 23 구리, 24 천연가스 | 5 |
| market_data (암호화폐) | 25 BTC, 26 ETH | 2 |
| macro (금리) | 30 2년 국채, 37 30년 모기지 | 2 |
| macro (환율) | 38 유로달러, 39 DXY | 2 |
| macro (고용/성장) | 31 실업률, 32 NFP, 34 GDP, 35 산업생산 | 4 |
| macro (물가/주택) | 33 CPI, 36 주택착공 | 2 |
| technical (확장) | 40 MACD, 41 스토캐스틱, 42 볼린저, 43 ATR, 44 OBV, 45 SMA50, 46 SMA200, 47 EMA12 | 8 |
| fundamental | 50 PER, 51 PBR, 52 ROE, 53 ROA, 54 D/E, 55 FCF, 56 배당, 57 영업이익률, 58 매출성장 | 9 |
| fundamental (재무 체질) | 60~73 | 14 |
| **합계** | | **53** |

**해석**: `match_by_keywords()`는 `match_indicators_for_llm()`의 2순위 fallback이므로, LLM이 `indicator_db_id`를 제대로 채운다면 당장의 UX 파괴는 없음. 다만 **키워드 매칭 경로만 타는 호출 지점** (`match_indicators_for_premise` → 카드 생성 전 단순 전제 텍스트 매칭) 에서는 위 53개 지표가 거의 추천되지 않을 수 있음.

### FE `AddIndicatorSheet.tsx`의 KEYWORD_INDICATOR_MAP (29개 규칙)

FE는 BE 대비 3배 가까이 촘촘한 키워드 룰을 이미 보유:
- 커버 지표 ID (약 52개): 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 15, 16, 20, 21, 23, 24, 25, 26, 30, 31, 32, 33, 34, 35, 36, 37, 39, 40, 50, 51, 52, 53, 54, 55, 56, 57, 58, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73
- FE에서도 미커버 약 12개: 13 다우, 14 코스닥, 22 은, 38 유로달러, 41~47 기술적 지표 확장(스토캐스틱, 볼린저, ATR, OBV, SMA50, SMA200, EMA12)

**BE ↔ FE 규칙 비대칭**: 동일 전제 텍스트라도 "FE가 추천한 관련 지표 리스트"와 "BE가 저장 시 auto_matched로 붙여주는 매칭"이 다르다 → Thesis 생성 후 재진입했을 때 지표 자동 매칭 결과가 UI 기대와 어긋날 수 있음.

### FE KEYWORD_INDICATOR_MAP 내 카탈로그 부재 참조
- 없음 ✅ (모든 `indicatorIds`가 BE CATALOG 기준 유효 ID)

---

## data_params 형식

### 1) data_source 분포

| data_source | 사용 ID 수 | 형식 규약 |
|-------------|-----------|-----------|
| `fmp`       | 33건 | `{symbol: str}` 또는 `{metric: str}` 또는 `{indicator: str, period: int, ...}` |
| `fred`      | 11건 | `{series_id: str}` |
| `metrics`   | 14건 (ID 60~73) | `{metric_code: str}` |
| `news_sentiment` | 1건 (ID 11) | `{}` (빈 객체) |

### 2) 소비자 매핑 (`thesis/tasks/eod_pipeline.py`)

| data_source | 소비 함수 | 응답 경로 | 지원하는 metric 키 |
|-------------|-----------|-----------|-------------------|
| `fmp` | `_fetch_fmp_value()` | `FMPClient.get_quote(symbol)` → `/stable/quote` | `price, change_percent, volume, pe, eps, market_cap, previous_close, day_high, day_low` |
| `fred` | `_fetch_fred_value()` | `FREDClient.get_latest_value(series_id)` | series_id |
| `metrics` | `_fetch_metrics_value()` | `fetch_quarterly_metric(symbol, metric_code)` | metric_code |
| `news_sentiment` | `_fetch_news_sentiment_value()` | `NewsArticle.objects.filter(entities__symbol=symbol)` | symbol (선택적, data_params에 없어도 `indicator.thesis.target`에서 추론) |

### 3) 🔴 P0 치명 불일치 — fundamental TTM metric (ID 50~58)

CATALOG 정의:
```python
{'id': 50, 'name': 'PER (주가수익비율)', ...,
 'data_source': 'fmp', 'data_params': {'metric': 'peRatioTTM'}}   # symbol 없음
{'id': 52, 'name': 'ROE ...', 'data_source': 'fmp', 'data_params': {'metric': 'returnOnEquityTTM'}}
{'id': 58, 'name': '매출성장률 (YoY)', 'data_source': 'fmp', 'data_params': {'metric': 'revenueGrowthYoY'}}
# ... ID 5, 50, 51, 52, 53, 54, 55, 56, 57, 58 전부 동일 패턴
```

소비자 `_fetch_fmp_value()` 동작:
```python
symbol = params.get('symbol')   # None → early return ❌
metric = params.get('metric', 'price')
# 이후 client.get_quote(symbol) 호출
# value_map = {price, change_percent, volume, pe, eps, market_cap, previous_close, day_high, day_low}
# metric이 매핑에 없으면 field = metric 그대로 → quote 응답에 'peRatioTTM' 키 존재하지 않음
```

**문제 세부**:
1. **symbol 누락**: fundamental 전체에 `symbol`이 없음 → `_fetch_fmp_value`의 `if not symbol: return None, None` 가드에 걸림. 현재는 `indicator.thesis.target` fallback이 fundamental 경로에만 없음 (`_fetch_metrics_value`는 `getattr(indicator.thesis, 'target', '').upper()` fallback 있음, `_fetch_fmp_value`는 없음).
2. **엔드포인트 불일치**: `peRatioTTM`, `returnOnEquityTTM` 등은 `/stable/key-metrics` 응답 필드 (FMPClient.get_key_metrics). `get_quote`는 주가용. metric 이름을 `eps`처럼 quote 필드에 매핑된 것만 정상 동작.
3. **revenueGrowthYoY 존재 여부 미검증**: FMP `/stable/*` 엔드포인트에 해당 정확한 키가 있는지 불명 (KB CLAUDE.md 버그 14 참조: `earningsYieldTTM` 역수 = PE, `returnOnEquityTTM`은 decimal × 100 = %).
4. **sub_claude_md/common-bugs.md 버그 #14**: 이미 `peRatioTTM` 필드가 존재하지 않는다고 명시 → `earningsYieldTTM` 사용해야 함. CATALOG는 버그를 재현하는 방향으로 정의됨.

**영향**:
- Thesis 사용자가 PER/PBR/ROE/ROA/D/E/FCF/배당/영업이익률/매출성장 지표를 선택해 가설을 만들면, EOD 파이프라인에서 매일 `symbol 없음` 또는 필드 불일치로 **값 0개 저장**. UI 차트가 공란, 알림도 발생 불가.

### 4) 🟡 P1 — FMP symbol 포맷 불일치

| ID | 이름 | CATALOG symbol | 잠재 이슈 |
|----|------|----------------|-----------|
| 39 | 달러 인덱스 (DXY) | `DX-Y.NYB` | Yahoo Finance 형식. FMP는 일반적으로 `DXY`/`USDX` 사용. `/stable/quote?symbol=DX-Y.NYB` 응답 유효성 미검증 |
| 3, 4, 12~16, 8 | 지수 캐럿(^) 심볼 | `^GSPC, ^KS11, ^IXIC, ^DJI, ^KQ11, ^N225, ^HSI, ^VIX` | FMP `/stable/quote`는 인덱스 별도 처리 가능 — 환경에서 전부 검증되었는지 확인 필요 |
| 20~26 | 원자재·암호화폐 | `GCUSD, CLUSD, SIUSD, HGUSD, NGUSD, BTCUSD, ETHUSD` | FMP commodity/crypto 엔드포인트가 `quote`로 동일 키를 반환하는지 확인 필요 |
| 9 | 원/달러 환율 | `USDKRW` | FMP forex는 `USDKRW` 형식 일반 OK, 소비자 `_infer_unit`은 'KRW' 포함 시 `'원'` 단위 반환 — 일관 |

`_fetch_fmp_value`는 `get_quote` 단일 엔드포인트 전제 → 지수/원자재가 quote API에서 정상 응답하지 않으면 전부 빈값. 최소 런타임 샘플 1건 이상 확인 권장.

### 5) ✅ 정합 — FRED

CATALOG의 `series_id` 값 전부 FRED 공식 코드:
- `FEDFUNDS, DGS10, DGS2, MORTGAGE30US, DEXUSEU, UNRATE, PAYEMS, GDPC1, INDPRO, CPIAUCSL, HOUST` — 모두 유효. `_fetch_fred_value`는 단순 `series_id` 전달 → 문제 없음.

### 6) ✅ 정합 — metrics (ID 60~73)

CATALOG `metric_code` 값: `gross_margin, net_margin, roic, current_ratio, interest_coverage, net_debt_to_ebitda, fcf_margin, ev_to_ebitda, fcf_yield, operating_income_growth, dso, asset_turnover, accruals_ratio, net_shareholder_yield` (14개).

소비자 `fetch_quarterly_metric(symbol, metric_code)` — `thesis/services/quarterly_metric_fetcher.py`가 각 코드를 `metrics` 앱에 위임. metric 코드 일치 여부는 `metrics/` 앱 DB 스키마와의 별도 감사 필요 (본 감사 범위 외). CATALOG ↔ 소비자 호출 시그니처는 일치.

### 7) news_sentiment 심볼 의존

`_fetch_news_sentiment_value()`는 `params.get('symbol')`을 요구하지만 CATALOG ID 11은 `data_params: {}`로 비어있음. 가설 저장 시 `indicator.data_params`에 `symbol`을 사용자/LLM이 주입한다고 가정 → 주입 경로가 문서화되지 않음.

- 확인된 주입 지점 없음 → 런타임에 `symbol 없음` 경고 뒤 `None, None` 반환 가능.
- 현재 설계 의도가 "CATALOG는 기본값만, `Indicator` 모델 저장 시 target symbol 추가"라면 설계 문서 보강 + 테스트 추가 필요.

---

## 종합 우선순위

| 우선 | 항목 | 권장 조치 (코드 수정 없음, 감사용) |
|------|------|-----------------------------------|
| **P0** | fundamental TTM 지표 9개 FMP 연동 실패 가능성 | (1) CATALOG의 `data_source`를 `fmp` → `fmp_key_metrics`로 바꾸고 `_fetch_fmp_value`에서 분기. (2) 버그 #14와 동일하게 `peRatioTTM`→`earningsYieldTTM` 등 필드명 실측 후 정정. (3) symbol fallback(`indicator.thesis.target`) 추가 |
| **P0** | FE/BE 이름 4건 불일치 (ID 6, 7, 30, 54) | 단일 소스(프롬프트 빌더 정의) 기준으로 FE 미러 동기화. `get_indicator_description()`의 prefix 매칭이 동작하므로 당장 장애는 아니나, UI 텍스트 일관성 및 `INDICATOR_BY_ID` lookup 안정성 확보 |
| **P1** | BE KEYWORD_RULES 82% 미커버 | FE KEYWORD_INDICATOR_MAP의 규칙을 BE로 역이식하여 단일 소스 또는 대칭 미러 유지. 최소 카테고리 커버리지(인덱스/원자재/암호화폐/물가/고용/펀더멘털)는 BE에도 추가 권장 |
| **P1** | `DX-Y.NYB` + 지수 캐럿 심볼 실측 | `/stable/quote` 샘플 호출로 비어있는 응답 여부 검증. 무효 심볼은 CATALOG에서 대체 심볼로 변경 |
| **P2** | news_sentiment symbol 주입 경로 | Indicator 저장 시 target symbol을 `data_params`에 복사하는 로직 문서화 + 테스트 추가 |
| **P2** | FE 세분 카테고리 vs BE 5분류 | 단일 카테고리 모델을 contracts/로 정의 후 양쪽 참조 구조화 |

---

## 부록 A — BE ↔ FE 이름 대조 전체 (64개)

참고용 스냅샷. 한글 동일 행은 생략, 불일치 4건만 굵게.

| ID | BE name | FE name |
|----|---------|---------|
| 1 | 외국인 순매수 추이 | 외국인 순매수 추이 |
| 2 | 기관 순매수 추이 | 기관 순매수 추이 |
| 3 | S&P 500 | S&P 500 |
| 4 | KOSPI 지수 | KOSPI 지수 |
| 5 | EPS 추이 | EPS 추이 |
| **6** | **미국 기준금리 (Fed Funds Rate)** | **미국 기준금리** |
| **7** | **미국 10년 국채 금리** | **미국 10년 국채** |
| 8 | VIX (공포지수) | VIX (공포지수) |
| 9 | 원/달러 환율 | 원/달러 환율 |
| 10 | RSI (14일) | RSI (14일) |
| 11 | 뉴스 센티먼트 | 뉴스 센티먼트 |
| 12 | NASDAQ | NASDAQ |
| 13 | 다우존스 | 다우존스 |
| 14 | 코스닥 지수 | 코스닥 지수 |
| 15 | 니케이 225 | 니케이 225 |
| 16 | 항셍 지수 | 항셍 지수 |
| 20 | 금 (Gold) | 금 (Gold) |
| 21 | 원유 (WTI) | 원유 (WTI) |
| 22 | 은 (Silver) | 은 (Silver) |
| 23 | 구리 (Copper) | 구리 (Copper) |
| 24 | 천연가스 | 천연가스 |
| 25 | 비트코인 (BTC) | 비트코인 (BTC) |
| 26 | 이더리움 (ETH) | 이더리움 (ETH) |
| **30** | **미국 2년 국채 금리** | **미국 2년 국채** |
| 31 | 실업률 | 실업률 |
| 32 | 비농업 고용 (NFP) | 비농업 고용 (NFP) |
| 33 | 소비자물가지수 (CPI) | 소비자물가지수 (CPI) |
| 34 | 실질 GDP | 실질 GDP |
| 35 | 산업생산지수 | 산업생산지수 |
| 36 | 주택착공건수 | 주택착공건수 |
| 37 | 30년 모기지 금리 | 30년 모기지 금리 |
| 38 | 달러/유로 환율 | 달러/유로 환율 |
| 39 | 달러 인덱스 (DXY) | 달러 인덱스 (DXY) |
| 40 | MACD | MACD |
| 41 | 스토캐스틱 %K | 스토캐스틱 %K |
| 42 | 볼린저 밴드 %B | 볼린저 밴드 %B |
| 43 | ATR (평균진폭) | ATR (평균진폭) |
| 44 | OBV (거래량 누적) | OBV (거래량 누적) |
| 45 | SMA 50일 | SMA 50일 |
| 46 | SMA 200일 | SMA 200일 |
| 47 | EMA 12일 | EMA 12일 |
| 50 | PER (주가수익비율) | PER (주가수익비율) |
| 51 | PBR (주가순자산비율) | PBR (주가순자산비율) |
| 52 | ROE (자기자본이익률) | ROE (자기자본이익률) |
| 53 | ROA (총자산이익률) | ROA (총자산이익률) |
| **54** | **부채비율 (Debt/Equity)** | **부채비율 (D/E)** |
| 55 | 잉여현금흐름 (FCF) | 잉여현금흐름 (FCF) |
| 56 | 배당수익률 | 배당수익률 |
| 57 | 영업이익률 | 영업이익률 |
| 58 | 매출성장률 (YoY) | 매출성장률 (YoY) |
| 60 | 매출총이익률 (Gross Margin) | 매출총이익률 (Gross Margin) |
| 61 | 순이익률 (Net Margin) | 순이익률 (Net Margin) |
| 62 | ROIC (투하자본이익률) | ROIC (투하자본이익률) |
| 63 | 유동비율 (Current Ratio) | 유동비율 (Current Ratio) |
| 64 | 이자보상배율 | 이자보상배율 |
| 65 | 순부채/EBITDA | 순부채/EBITDA |
| 66 | FCF 마진 | FCF 마진 |
| 67 | EV/EBITDA | EV/EBITDA |
| 68 | FCF 수익률 | FCF 수익률 |
| 69 | 영업이익 성장률 | 영업이익 성장률 |
| 70 | 매출채권 회전일수 (DSO) | 매출채권 회전일수 (DSO) |
| 71 | 총자산회전율 | 총자산회전율 |
| 72 | 발생액 비율 (Accruals) | 발생액 비율 (Accruals) |
| 73 | 순주주수익률 | 순주주수익률 |

---

## 부록 B — 참고 이슈 링크

- `CLAUDE.md` 버그 #14: FMP Key Metrics 필드명 불일치 (`earningsYieldTTM` 역수 = PE)
- `sub_claude_md/coding-rules.md`: FMP `/stable/*` 경로만 사용
- Memory: `feedback_indicator_catalog_sync.md` — 카탈로그 3곳 미러 동시 업데이트 원칙 (본 보고서가 동일 지침 연장선)
- Memory: `feedback_llm_indicator_hallucination.md` — `match_by_gemini` 제거 완료, 카탈로그 외 지표 생성 금지 재확인

— 끝 —

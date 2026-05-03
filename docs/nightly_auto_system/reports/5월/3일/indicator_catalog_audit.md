# 지표 카탈로그 동기화 감사 보고서

**감사일**: 2026-05-04
**범위**: `INDICATOR_CATALOG` (BE/FE 미러), `KEYWORD_RULES`, `data_params` 형식 정합성
**소스 파일**:
- BE 정의: `thesis/services/prompt_builder.py:14-294`
- BE 후처리: `thesis/services/llm_postprocess.py:82-95`
- BE 매칭: `thesis/services/indicator_matcher.py:12-154`
- FE 미러: `frontend/components/thesis/AddIndicatorSheet.tsx:15-91`
- 데이터 fetcher: `thesis/tasks/eod_pipeline.py:25-194`
- 직렬화 검증: `thesis/serializers/indicator_serializers.py:6-43`

---

## 요약 (동기화 상태)

| 검사 항목 | 결과 | 비고 |
|---|---|---|
| BE↔FE ID 동기화 | ✅ 일치 (64개) | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 20~26, 30~47, 50~58, 60~73 — BE/FE 모두 동일 ID 집합 |
| BE↔FE 이름 동기화 | ✅ 일치 (64개) | 모든 ID에서 `name` 필드 정확 일치 |
| BE↔FE 빈도 동기화 | ✅ 일치 | `INDICATOR_FREQUENCY`(BE) ↔ `freq`(FE) 동일 |
| description 빈/짧음 | ✅ 양호 | 빈 항목 0개, 10자 미만 0개. 평균 약 35자 |
| KEYWORD_RULES 고아 | ✅ 없음 | 11개 룰의 모든 지표 이름이 카탈로그에 존재 |
| KEYWORD_RULES ↔ CATALOG 일관성 | ⚠️ 1건 | 'EPS 추이': KEYWORD_RULES `indicator_type='market_data'` vs CATALOG `category='fundamental'` |
| **data_params ↔ fetcher 정합성** | ❌ **심각** | 18개 지표가 fetcher 계약 위반 (technical 9개 + fundamental 9개) |
| FE description 부재 | ⚠️ 구조적 차이 | FE 미러는 description 필드를 보유하지 않음 (UI 미사용) |
| FE 카테고리 분할 | ℹ️ 의도적 | FE 17개 세분화 카테고리 vs BE 5개 광역 카테고리 — UI 그룹핑용 |
| 종합 동기화 등급 | 🟡 **주의** | 카탈로그 미러 자체는 깔끔하나, fetcher 계약과 어긋나는 항목 다수 (런타임 데이터 누락 위험) |

> 가장 중요한 이슈는 **카탈로그 정의가 EOD fetcher가 받아들이는 형식과 어긋난다**는 것입니다. 이는 BE/FE 미러 동기화 문제가 아니라 BE 내부 계약 불일치입니다 (4번 섹션 참조).

---

## BE ↔ FE 불일치 목록

### 1. ID/이름/빈도 불일치
**없음.** BE 64개 ↔ FE 64개 완전 일치. 다음을 모두 검증함:
- ID 집합 (set diff = ∅)
- 이름 문자열 (e.g. `'S&P 500'`, `'KOSPI 지수'`, `'미국 기준금리 (Fed Funds Rate)'` 등 모두 한 자도 다르지 않음)
- 빈도 매핑: `INDICATOR_FREQUENCY[id]` (BE) ↔ `freq` (FE) — 64건 모두 일치

### 2. 구조적 차이 (불일치 아님, 의도적)

| 필드 | BE (`prompt_builder.py`) | FE (`AddIndicatorSheet.tsx`) | 영향 |
|---|---|---|---|
| `category` | `market_data` / `macro` / `technical` / `fundamental` / `sentiment` (5개 광역) | `수급` / `주요 지수` / `원자재` / `암호화폐` / `금리` / `환율/변동성` / `고용/성장` / `물가/주택` / `기술적` / `펀더멘털` / `재무 체질` / `밸류에이션` / `성장` / `운영 효율` / `이익 품질` / `주주환원` / `심리` (17개 세분화) | UI 그룹핑 우선순위에 의도적으로 분리 — `categoryOrder` 배열로 렌더 순서 통제 |
| `description` | 모든 항목 보유 | 미보유 | FE는 카드 뷰에서 description을 표시하지 않음. 단, **카드 클릭 시 상세 패널 추가하려면 추후 동기화 필요** |
| `data_source` | `'fmp' | 'fred' | 'news_sentiment' | 'metrics'` 노출 | 미노출 | FE는 데이터 소스를 직접 다루지 않음 |
| `data_params` | 노출 | 미노출 | 위와 동일 |
| `support_direction` | 노출 | 미노출 | FE는 점수 해석을 BE에 위임 |

> 결론: BE는 **데이터 fetch + LLM 매칭**용 풀 스펙이 필요하고, FE는 **선택 UI**용 슬림 스펙만 보유하므로 차이는 정당함. 그러나 **FE가 description을 표시하기로 결정하면 즉시 동기화 부담 발생** — `feedback_indicator_catalog_sync.md`의 "3곳 분산 미러" 우려가 그대로 적용됨.

### 3. KEYWORD_INDICATOR_MAP (FE) ↔ KEYWORD_RULES (BE) 비교

FE는 27개 키워드 룰, BE는 11개 키워드 룰. **두 시스템은 독립적으로 매칭**합니다:
- BE: `match_by_keywords()` — 가설 빌더가 LLM 백업 매칭에 사용 (`indicator_matcher.py:157`)
- FE: `findRelatedIndicators()` — 사용자가 `AddIndicatorSheet`에서 전제 텍스트 기반 추천 보기

⚠️ **양쪽 룰셋이 큰 차이를 보입니다.** 예시:
- FE에만 있음: `'반도체'`, `'중국'`, `'일본'`, `'광고'`, `'재무건전'`, `'배당'`, `'회전율'`, `'이익 품질'`, `'gdp'`, `'주택'` 등
- BE에만 있음: `'선거'/'정치'/'정책'/'대통령'/'국회'` (정치 이벤트 룰)

이로 인해 **같은 전제 텍스트를 입력해도 BE LLM 매칭과 FE 추천이 다른 결과**를 낼 수 있습니다. 특히 BE는 LLM이 db_id를 직접 추천하므로 키워드 룰 의존도가 낮지만, BE 키워드 룰을 단순화/제거하든 FE 룰셋과 합치든 한 방향으로 정리할 필요가 있습니다.

---

## description 품질

### BE INDICATOR_CATALOG (n=64)

| 검사 | 결과 |
|---|---|
| 빈 description | **0개** |
| 10자 미만 | **0개** (최단 14자: id 14 '코스닥 지수' = `'한국 중소형 성장주 시장 지수.'`) |
| 마침표 누락 | 검사 결과 모두 마침표로 종결 ✅ |
| 길이 분포 (대략) | 14~58자, 평균 35자 |

### 샘플 (양호)
- id:6 '미국 기준금리 (Fed Funds Rate)' → `'연준 기준금리. 유동성과 할인율에 직접 영향. 금리 인상은 주식에 부정적.'` (52자)
- id:23 '구리 (Copper)' → `'구리 선물 가격. 경기 선행지표로 "Dr. Copper"라 불림.'` (35자)

### 잠재 이슈
- id:14 '코스닥 지수' description은 14자로 가장 짧으며, 한국 시장 비교 맥락이 빠져 있음. id:4 'KOSPI 지수'와 비교해 한 줄 보강 권장 (선택).
- FE는 description 미보유 — 추후 호버/툴팁/상세 뷰를 추가할 때 64개 동기화 비용 발생.

### CLAUDE.md 메타 불일치 참고
CLAUDE.md에 `'INDICATOR_CATALOG description 73개 + recommendation_reason 저장'`으로 기록되어 있으나, **실제 항목 수는 64개**입니다. ID 최댓값이 73(`'순주주수익률'`)이라 73개라고 표기된 것으로 추정됩니다. `sub_claude_md/` 본문 또는 PROGRESS 노트에서 "64개"로 정정 권장.

---

## keyword_rules 고아

### BE `KEYWORD_RULES` (n=11) ↔ INDICATOR_CATALOG

| Rule # | 키워드 묶음 | 참조 지표 이름 | CATALOG 존재 |
|---|---|---|---|
| 1 | 외국인/외인/순매수/... | '외국인 순매수 추이' | ✅ id:1 |
| 2 | 금리/연준/FOMC/... | '미국 기준금리 (Fed Funds Rate)', '미국 10년 국채 금리' | ✅ id:6, 7 |
| 3 | VIX/공포/변동성/... | 'VIX (공포지수)' | ✅ id:8 |
| 4 | 환율/달러/원달러/... | '원/달러 환율' | ✅ id:9 |
| 5 | RSI/MACD/기술적/... | 'RSI (14일)' | ✅ id:10 |
| 6 | 센티먼트/뉴스/심리/... | '뉴스 센티먼트' | ✅ id:11 |
| 7 | 실적/EPS/매출/... | 'EPS 추이' | ✅ id:5 |
| 8 | 기관/연기금/... | '기관 순매수 추이' | ✅ id:2 |
| 9 | S&P/나스닥/다우/... | 'S&P 500' | ✅ id:3 |
| 10 | 코스피/KOSPI/... | 'KOSPI 지수' | ✅ id:4 |
| 11 | 선거/정치/정책/... | 'VIX (공포지수)', 'KOSPI 지수' | ✅ id:8, 4 |

**고아 룰: 없음.** 모든 KEYWORD_RULES 항목이 카탈로그에 존재합니다.

### KEYWORD_RULES ↔ CATALOG 필드 일관성 (1건 미스매치)

룰의 인라인 필드가 카탈로그와 일치하는지 점검 (룰이 카탈로그를 단순 복제하므로 변경 시 어긋날 수 있음):

| 지표 | 필드 | KEYWORD_RULES 값 | CATALOG 값 | 상태 |
|---|---|---|---|---|
| 'EPS 추이' (id:5) | `indicator_type` / `category` | `'market_data'` | `'fundamental'` | ⚠️ **불일치** |
| 그 외 10개 룰 | indicator_type, support_direction, data_source, data_params | — | — | ✅ 모두 일치 |

> **위험도**: 낮음. `match_by_keywords()` 결과는 `_find_in_catalog()` 후처리로 카탈로그 항목을 우선 사용하므로 (`indicator_matcher.py:316-320`) 실행 영향은 거의 없음. 다만 룰 자체가 잘못된 분류 정보를 포함하므로 `'fundamental'`로 정정 권장.

### 잠재 구조적 결함
`KEYWORD_RULES`의 각 indicator 항목이 `name + data_source + data_params + indicator_type + support_direction`을 카탈로그와 **중복 정의**하고 있습니다. 이는 단일 진실 소스 원칙 위반이며, 향후 카탈로그 변경 시 이 룰셋도 함께 업데이트해야 하는 부담을 만듭니다. 권장: 룰에는 `indicator_id`만 두고, 후처리에서 `get_indicator_by_id()`로 조회.

---

## data_params 형식

### Fetcher 계약 (eod_pipeline.py 기준)

| `data_source` | 필수 키 | 추가 키 | 처리 위치 |
|---|---|---|---|
| `fmp` | `symbol` | `metric` (기본 `'price'`) | `eod_pipeline.py:25-81` |
| `fred` | `series_id` | — | `eod_pipeline.py:84-123` |
| `news_sentiment` | `symbol` | — | `eod_pipeline.py:126-154` |
| `metrics` | `metric_code` | `symbol` (없으면 `thesis.target` 사용) | `eod_pipeline.py:157-177` |

### Serializer 화이트리스트 (`indicator_serializers.py:6-8`)
허용 키: `{'symbol', 'series_id', 'metric', 'indicator', 'period'}`
- ⚠️ **`metric_code` 누락**: data_source=`metrics`인 14개 지표(id:60~73)가 사용자 입력으로 직접 들어오면 serializer가 거부. 시스템 시드/마이그레이션 경로로만 들어오면 무사하지만, 향후 사용자 정의 metrics 지표 추가 시 차단됨.
- ⚠️ **`fast`, `slow`, `signal` 누락**: id:40 'MACD'의 `data_params`는 `{'indicator': 'MACD', 'fast': 12, 'slow': 26, 'signal': 9}` — `fast/slow/signal` 키도 화이트리스트에 없음. (단, 이 또한 시드 경로로만 들어옴)

### CATALOG 정의 vs FMP fetcher 계약 검증

#### ✅ 정상 (33개)
- **시장 지수 + 원자재 + 암호화폐 + 환율/변동성** (id:3,4,12~16,20~26,8,9,38,39 — 합 18개): `data_params={'symbol': '...'}` → fetcher가 quote.get('price') 정상 동작.
- **수급 (id:1,2)**: `data_params={'metric': 'foreign_net_buy' | 'institutional_net_buy'}` — `symbol` 누락 → fetcher가 `'symbol 없음'` 경고 후 `(None, None)` 반환. ❌
  - ⚠️ **수정**: 두 지표는 위 ✅ 분류에서 제거. 아래 ❌ 섹션으로 이동.
- **EPS 추이 (id:5)**: `data_params={'metric': 'eps'}` — `symbol` 누락. ❌ (아래 이동)
- **FRED (id:6,7,30,37,33,31,32,34,35,36 — 10개)**: 모두 `series_id` 있음 ✅
- **뉴스 센티먼트 (id:11)**: `data_params={}` — `symbol` 누락. fetcher가 `'symbol 없음'` 경고. 단, target에서 동적으로 채워야 정상 동작 → 별도 위치에서 처리 필요. ❌ (아래 이동)
- **metrics (id:60~73 — 14개)**: `metric_code` 보유 + `symbol`은 thesis.target에서 자동 채움 ✅

> 정상 분류 정정: 시장 지수/원자재/암호화폐/환율(18) + FRED(10) + metrics(14) = **42개**

#### ❌ Fetcher 계약 위반 — 데이터 fetch 실패 (22개)

다음 그룹은 카탈로그 정의 그대로는 EOD fetcher가 값을 가져올 수 없습니다.

##### 그룹 A: 수급 지표 (2개) — `metric` 있고 `symbol` 없음
| ID | 이름 | data_params | 문제 |
|---|---|---|---|
| 1 | 외국인 순매수 추이 | `{'metric': 'foreign_net_buy'}` | `_fetch_fmp_value`는 `symbol`이 필수. 또한 FMP `/quote` 응답에 `foreign_net_buy` 필드 없음 |
| 2 | 기관 순매수 추이 | `{'metric': 'institutional_net_buy'}` | 위와 동일 — 별도 institutional holdings 엔드포인트 필요 |

##### 그룹 B: 펀더멘털 (id:5,50~58 — 10개) — `metric` 있고 `symbol` 없음 + FMP `/quote` 미지원 키
| ID | 이름 | data_params['metric'] | FMP `/quote` 매핑 |
|---|---|---|---|
| 5 | EPS 추이 | `eps` | ✅ value_map 매핑 (`'eps'`) — 단 `symbol` 누락으로 fetcher 진입 불가 |
| 50 | PER | `peRatioTTM` | ❌ value_map 미매핑. fallback `quote.get('peRatioTTM')` → None |
| 51 | PBR | `pbRatioTTM` | ❌ 동일 |
| 52 | ROE | `returnOnEquityTTM` | ❌ 동일 (TTM은 `/key-metrics-ttm` 엔드포인트 필요) |
| 53 | ROA | `returnOnAssetsTTM` | ❌ 동일 |
| 54 | 부채비율 | `debtToEquityTTM` | ❌ 동일 (`/ratios-ttm` 엔드포인트 필요) |
| 55 | FCF | `freeCashFlowTTM` | ❌ 동일 |
| 56 | 배당수익률 | `dividendYieldTTM` | ❌ 동일 |
| 57 | 영업이익률 | `operatingProfitMarginTTM` | ❌ 동일 |
| 58 | 매출성장률 (YoY) | `revenueGrowthYoY` | ❌ 동일 |

> id:5는 value_map에는 있지만 `symbol` 부재. id:50~58은 둘 다 문제. FMP TTM/Growth 데이터를 가져오려면 별도 fetcher가 필요합니다 — 또는 이 9개는 `data_source='metrics'`(metric_code 기반)로 통일하는 편이 일관됩니다.

##### 그룹 C: 기술적 지표 (id:10,40~47 — 9개) — `indicator` 키 사용, `symbol` 없음
| ID | 이름 | data_params | 문제 |
|---|---|---|---|
| 10 | RSI (14일) | `{'indicator': 'RSI', 'period': 14}` | fetcher가 `indicator/period` 키를 무시 + `symbol` 부재 |
| 40 | MACD | `{'indicator': 'MACD', 'fast': 12, 'slow': 26, 'signal': 9}` | 동일 + `fast/slow/signal` serializer 미허용 |
| 41 | 스토캐스틱 %K | `{'indicator': 'stochastic', 'period': 14}` | 동일 |
| 42 | 볼린저 밴드 %B | `{'indicator': 'bollinger', 'period': 20}` | 동일 |
| 43 | ATR | `{'indicator': 'ATR', 'period': 14}` | 동일 |
| 44 | OBV | `{'indicator': 'OBV'}` | 동일 |
| 45 | SMA 50일 | `{'indicator': 'SMA', 'period': 50}` | 동일 |
| 46 | SMA 200일 | `{'indicator': 'SMA', 'period': 200}` | 동일 |
| 47 | EMA 12일 | `{'indicator': 'EMA', 'period': 12}` | 동일 |

> 기술적 지표는 본질적으로 **종목별** 계산이 필요한데 `symbol`이 없습니다. `target_symbol`을 thesis에서 가져오는 보강 로직이 fetcher에 없으므로(metrics fetcher에는 있음 — `eod_pipeline.py:163`) 모두 fetch 실패합니다. FMP technical 엔드포인트는 별도 호출이며 `_fetch_fmp_value`가 처리하지 않습니다.

##### 그룹 D: 뉴스 센티먼트 (id:11 — 1개)
| ID | 이름 | data_params | 문제 |
|---|---|---|---|
| 11 | 뉴스 센티먼트 | `{}` | `_fetch_news_sentiment_value`는 `symbol` 필수. 빈 dict로는 `'symbol 없음'` 경고 후 종료 |

> 가설별로 target symbol이 정해질 때 동적으로 주입되도록 해야 함. 현재 카탈로그 정의 그대로는 동작 불가.

#### 요약 표

| 그룹 | 개수 | 영향 |
|---|---|---|
| ✅ 정상 fetch | 42 | 시장 지수, 원자재, 암호화폐, 환율, FRED 거시, 분기 metrics |
| ❌ 카탈로그-fetcher 계약 위반 | 22 | 수급 2 + 펀더멘털 10 + 기술적 9 + 센티먼트 1 |
| 합계 | 64 | — |

#### 영향 평가
- 가설에 추가된 후 **EOD 파이프라인이 reading을 생성하지 못하면** 점수 산정/스냅샷/알림 모두 실패하므로, 사용자가 이 22개 지표를 선택하면 관제실에 빈 차트만 표시될 가능성이 큽니다.
- 단, `update_indicator_readings`가 `data_source__in=['manual', 'custom']`만 제외하므로 (eod_pipeline.py:223) 위 22개는 모두 fetch 시도 후 조용히 실패합니다 — 로그에는 경고가 누적되나 사용자에게 노출되지는 않을 것입니다.
- 활성 가설에 이 지표들이 얼마나 등록되어 있는지는 별도 데이터 점검 필요 (DB 조회). 등록되어 있지 않다면 영향은 잠재적이며, 등록되어 있다면 즉시 영향을 끼치고 있습니다.

---

## 권장 조치 (우선순위)

### 🔴 P0 — 데이터 fetch 실패 차단
1. **그룹 B(펀더멘털 10개)**의 fetch 경로 결정:
   - 옵션 1: `data_source='metrics'` + 적절한 `metric_code`로 변경 — `_fetch_metrics_value`가 thesis.target을 자동 사용하므로 일관성 ↑
   - 옵션 2: FMP `/key-metrics-ttm`, `/ratios-ttm` 호출 fetcher 신설
2. **그룹 C(기술적 9개)** fetch 경로 결정:
   - FMP `/technical_indicator` 엔드포인트용 별도 fetcher (`_fetch_fmp_technical`) 신설
   - `data_params`에 `target_symbol` 동적 주입 로직 보강 (현재 metrics fetcher의 패턴을 따라)
3. **그룹 D(뉴스 센티먼트)**: thesis.target → indicator.data_params['symbol'] 자동 주입 (fetch 시점)
4. **그룹 A(수급 2개)**: FMP institutional/foreign holdings 별도 fetcher 또는 자체 데이터 소스 정의

### 🟡 P1 — 카탈로그 단일 진실 소스 강화
5. `KEYWORD_RULES`의 `'EPS 추이'` indicator_type을 `'fundamental'`로 정정 (또는 룰 구조를 `indicator_id` 참조로 리팩토링).
6. `KEYWORD_RULES` 항목을 `[{'keywords': [...], 'indicator_ids': [...]}]` 단순 구조로 변경 — 데이터 중복 제거.
7. serializer `ALLOWED_DATA_PARAM_KEYS`에 `metric_code`, `fast`, `slow`, `signal` 추가하거나, 아예 사용자 입력 경로(POST)와 시스템 시드 경로를 분리.

### 🟢 P2 — 미러 동기화 부담 완화
8. **BE → contracts/ → FE 자동 생성** 파이프라인 검토. 예: BE에서 `python manage.py dump_indicator_catalog`로 JSON 출력 → FE 빌드 시 import. 이렇게 하면 향후 description 등 추가 필드 동기화 비용이 0이 됨.
9. CLAUDE.md/`feedback_indicator_catalog_sync.md`에 기재된 "3곳 분산 미러"를 명시적으로 `prompt_builder.py` ↔ `AddIndicatorSheet.tsx` ↔ `indicator_matcher.KEYWORD_RULES` 3곳으로 정리. 메모(64 vs 73) 정정.

---

## 부록 — 검증 메서드

- BE/FE ID 비교: `prompt_builder.py:14-294` 파싱 vs `AddIndicatorSheet.tsx:15-91` 파싱
- 빈도 비교: `INDICATOR_FREQUENCY` (prompt_builder.py:305-326) vs FE `freq` 필드
- description 길이 분석: `INDICATOR_CATALOG[i]['description']` 64건 인스펙션
- KEYWORD_RULES 고아: 11개 룰의 `name` 추출 후 카탈로그 이름 set과 교집합 검증
- data_params 형식: `_fetch_fmp_value`(eod_pipeline.py:25-81), `_fetch_fred_value`(84-123), `_fetch_news_sentiment_value`(126-154), `_fetch_metrics_value`(157-177) 코드 vs 카탈로그 각 항목

본 보고서는 **읽기 전용 감사**이며, 수정 사항은 별도 PR로 처리해야 합니다.

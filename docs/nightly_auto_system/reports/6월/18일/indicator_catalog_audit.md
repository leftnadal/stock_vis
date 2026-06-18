# 지표 카탈로그 동기화 감사 보고서

- **감사 일자**: 2026-06-18
- **대상 프로젝트**: `/Users/byeongjinjeong/Desktop/stock_vis`
- **모드**: 읽기 전용 (코드 무수정)
- **감사 범위**: `thesis/services/prompt_builder.py`, `thesis/services/indicator_matcher.py`, `thesis/services/llm_postprocess.py`, `frontend/components/thesis/AddIndicatorSheet.tsx`, `packages/shared/metrics/management/commands/seed_metric_definitions.py`(교차 검증)

---

## 요약 (동기화 상태)

| 검사 항목 | 상태 | 비고 |
|----------|------|------|
| BE ↔ FE 지표 항목(id/name) | 🟢 **완전 일치** | 양쪽 64개, id/이름/주기 모두 동일 |
| description 필드 품질 | 🟢 양호 | BE 64개 전건 채움, 빈/단문(<10자) 0건 |
| FE의 description 보유 여부 | 🟡 주의 | FE 미러는 description 미포함(표시 불가) |
| BE `KEYWORD_RULES` 고아 규칙 | 🟢 없음 | 11개 규칙 모두 카탈로그 이름 존재 |
| BE `KEYWORD_RULES` 분류 일관성 | 🔴 **1건 불일치** | EPS `indicator_type='market_data'` vs 카탈로그 `fundamental` |
| BE ↔ FE 키워드 매핑 동기화 | 🟡 주의 | BE 11규칙(이름 기반) vs FE 27규칙(id 기반) — 독립 관리 |
| `metrics` data_source(60–73) metric_code | 🟢 **완전 일치** | 시드 정의 14개 전건 매칭 |
| FMP 심볼/필드 형식 | 🟡 주의 | DXY `.` 포함 심볼, FMP TTM 비표준 필드 4건(이미 audit_note 기재) |

**총평**: 지표 항목 자체(id·name·주기)는 BE/FE가 **완벽히 동기화**되어 있다. 가장 큰 구조적 위험은 **4중 분산 미러**(BE 카탈로그 / FE 카탈로그 / BE 키워드룰 / FE 키워드맵)가 단일 출처 없이 독립 하드코딩되어 있다는 점이며, 실제 발생한 드리프트는 **EPS 분류 불일치 1건**이다.

---

## BE ↔ FE 불일치 목록

### 1) 지표 항목(id/name) — 불일치 없음 🟢

양쪽 모두 동일한 64개 지표(id 기준)를 보유한다. 예약(미사용) id 슬롯: `17,18,19,27,28,29,48,49,59`.

```
공통 id (64개):
1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,
20,21,22,23,24,25,26,
30,31,32,33,34,35,36,37,38,39,
40,41,42,43,44,45,46,47,
50,51,52,53,54,55,56,57,58,
60,61,62,63,64,65,66,67,68,69,70,71,72,73
```

- **BE에만 있는 항목**: 없음
- **FE에만 있는 항목**: 없음
- 이름(name)·업데이트 주기(freq) 전수 대조 결과 불일치 0건.

### 2) 카테고리 분류 체계 차이 🟡 (구조적 차이, 항목 누락 아님)

- **BE**(`prompt_builder.py`): 5개 대분류 — `market_data / macro / technical / fundamental / sentiment`
- **FE**(`AddIndicatorSheet.tsx`): 17개 세분류 — `수급 / 주요 지수 / 원자재 / 암호화폐 / 금리 / 환율·변동성 / 고용·성장 / 물가·주택 / 기술적 / 펀더멘털 / 재무 체질 / 밸류에이션 / 성장 / 운영 효율 / 이익 품질 / 주주환원 / 심리`

→ 항목 누락은 아니지만, **분류 기준이 양쪽에서 별도 정의**되어 있어 카테고리 추가/이동 시 동기화가 보장되지 않는다. (FE의 `categoryOrder` 배열도 별도 하드코딩.)

### 3) FE 미러의 필드 축소 🟡

FE `INDICATOR_CATALOG`는 BE의 일부 필드만 미러링한다.

| 필드 | BE | FE |
|------|----|----|
| `id`, `name` | ✅ | ✅ |
| `freq`(주기) | ✅(`INDICATOR_FREQUENCY` 별도 dict) | ✅(항목 내 인라인) |
| `category` | ✅(5분류) | ✅(17분류, 재정의) |
| `data_source` | ✅ | ❌ |
| `data_params` | ✅ | ❌ |
| `support_direction` | ✅ | ❌ |
| `description` | ✅ | ❌ |

→ FE 주석은 "`prompt_builder.py`와 동기화"라고 명시하나 실제로는 **표시용 부분 미러**다. 특히 `description` 미보유로 인해 지표 선택 UI(`AddIndicatorSheet`)에서 지표 설명 툴팁/보조문구를 제공할 수 없다.

---

## description 품질

### BE (`prompt_builder.py` INDICATOR_CATALOG) — 🟢 양호

- **총 64개 지표 전건 `description` 보유** (빈 문자열 0건).
- **10자 미만 단문**: 0건. 최단 항목도 완결된 한 문장 형태.
  - 예) id 14 코스닥: "한국 중소형 성장주 시장 지수." / id 4 KOSPI: "한국 유가증권시장 전체 종목 시가총액 가중 지수."
- `get_indicator_description()`(라인 351)이 정확 매칭 → 접두사 매칭(예: "EPS 추이 (META)") 순으로 조회하도록 구현되어 있어 LLM 모드의 심볼 접미사도 처리됨.

### FE — 🟡 (해당 없음 / 부재)

FE 미러는 `description` 필드를 아예 가지지 않으므로 품질 평가 대상 외. **권장**: 설명을 FE에 하드코딩 복제하기보다, BE 카탈로그를 API/스키마로 노출해 FE가 소비하도록 단일화.

---

## keyword_rules 고아

> 참고: 사전 grep의 소문자 `keyword_rules`는 0건. 실제 정의는 `indicator_matcher.py`의 **`KEYWORD_RULES`**(대문자, 라인 12) 및 FE의 **`KEYWORD_INDICATOR_MAP`**(`AddIndicatorSheet.tsx` 라인 109).

### 1) BE `KEYWORD_RULES`(이름 기반) — 고아 규칙 없음 🟢

11개 규칙이 참조하는 지표 이름이 모두 카탈로그에 존재한다.

| 규칙 키워드 대표 | 참조 지표(name) | 카탈로그 매칭 |
|---|---|---|
| 외국인/순매수 | 외국인 순매수 추이 (id 1) | ✅ |
| 금리/연준 | 미국 기준금리(6), 미국 10년 국채(7) | ✅ |
| VIX/변동성 | VIX (공포지수) (8) | ✅ |
| 환율/달러 | 원/달러 환율 (9) | ✅ |
| RSI/기술적 | RSI (14일) (10) | ✅ |
| 센티먼트/뉴스 | 뉴스 센티먼트 (11) | ✅ |
| 실적/EPS | EPS 추이 (5) | ✅ |
| 기관 | 기관 순매수 추이 (2) | ✅ |
| S&P/나스닥 | S&P 500 (3) | ✅ |
| 코스피 | KOSPI 지수 (4) | ✅ |
| 선거/정치 | VIX(8), KOSPI(4) | ✅ |

→ **참조 무결성 OK**(존재하지 않는 지표를 가리키는 규칙 없음).

### 2) 🔴 분류(indicator_type) 불일치 1건 — EPS

`KEYWORD_RULES`의 '실적/EPS' 규칙(라인 90–98)이 EPS를 `'indicator_type': 'market_data'`로 지정하나, 카탈로그(`prompt_builder.py` id 5)는 `'category': 'fundamental'`이다.

```python
# indicator_matcher.py L90-98 (KEYWORD_RULES)
'name': 'EPS 추이', ... 'indicator_type': 'market_data',   # ← 불일치
# prompt_builder.py L190-193 (INDICATOR_CATALOG)
{'id': 5, 'name': 'EPS 추이', 'category': 'fundamental', ...}  # ← 정답
```

→ 키워드 매칭 경로(`match_by_keywords`)로 EPS가 추천될 때 카테고리가 `market_data`로 잘못 전파될 수 있음. (단, LLM 빌더의 주 경로인 `match_indicators_for_llm`은 PK 매칭 시 카탈로그 원본을 사용하므로 영향 제한적.)

### 3) 🟡 BE ↔ FE 키워드 시스템 미동기화 (이중 관리)

| 구분 | BE `KEYWORD_RULES` | FE `KEYWORD_INDICATOR_MAP` |
|---|---|---|
| 식별 방식 | 지표 **이름(name)** 문자열 | 지표 **id(숫자)** |
| 규칙 수 | 11개 | 27개 |
| 커버 지표 수 | 11개 | 약 40개 이상 |
| 데이터 | `data_params` 등 **카탈로그 값 복제** | id만 참조(복제 없음) |

- FE `KEYWORD_INDICATOR_MAP`의 모든 `indicatorIds`는 카탈로그에 실존(고아 id 없음) 🟢.
- 그러나 두 키워드 엔진이 **독립 진화** 중이라 동일 전제 텍스트에 대해 BE/FE 추천 결과가 달라질 수 있음.
- BE `KEYWORD_RULES`는 `data_source`·`data_params`를 **카탈로그에서 복사**(이름 기반)하므로, 카탈로그의 `data_params`가 바뀌면 키워드룰 사본이 **stale**해지는 드리프트 위험.

### 4) 🟡 키워드 미커버 지표

BE `KEYWORD_RULES`는 64개 중 11개만 커버한다. 나머지(원자재·암호화폐·재무 체질 metrics 14종·기술적 세부지표 등)는 키워드 fast-path가 없고 PK/Gemini 경로에 의존. 설계 의도(키워드는 빠른 경로)와 부합하나, FE는 동일 키워드를 더 넓게 커버하므로 BE 측 커버리지 보강 여지가 있음.

---

## data_params 형식

### 1) data_source별 형식 — 내부 일관성 🟢

| data_source | 형식 | 사용 지표 |
|---|---|---|
| `fmp` (지수/원자재/암호/환율) | `{'symbol': '...'}` | 3,4,12~16,20~26,8,9,39 등 |
| `fmp` (펀더멘털 TTM) | `{'metric': '...TTM'}` | 5,50~58 |
| `fmp` (기술적) | `{'indicator': '...', 'period': N}` | 10,40~47 |
| `fred` | `{'series_id': '...'}` | 6,7,30,37,38,31~36 |
| `metrics` | `{'metric_code': '...'}` | 60~73 |
| `news_sentiment` | `{}` | 11 |

### 2) 🟢 `metrics`(60–73) metric_code ↔ 시드 정의 완전 일치

`seed_metric_definitions.py`와 교차 검증한 결과 14개 전건 매칭:

```
gross_margin(60) net_margin(61) roic(62) current_ratio(63)
interest_coverage(64) net_debt_to_ebitda(65) fcf_margin(66) ev_to_ebitda(67)
fcf_yield(68) operating_income_growth(69) dso(70) asset_turnover(71)
accruals_ratio(72) net_shareholder_yield(73)
```

→ `metrics` data_source 측은 불일치 0건. (validation/metrics 시스템과 정합.)

### 3) 🟡 FMP 비표준 필드 — 카탈로그에 이미 audit_note 기재 (회귀 방지 완료)

`common-bugs #14`(FMP Key Metrics 필드명 불일치) 관련 4건이 `data_params` 내 `audit_note`로 명시되어 있음 — **양호한 방어 패턴**:

| id | 지표 | 비표준 처리 | 근거 |
|---|---|---|---|
| 50 | PER | `earningsYieldTTM` + `inverse:True` (PER = 1/EY) | FMP key-metrics-ttm에 `peRatioTTM` 부재 |
| 52 | ROE | `returnOnEquityTTM` + `scale_multiplier:100` | 0~1 비율 → % 변환 |
| 53 | ROA | `returnOnAssetsTTM` + `scale_multiplier:100` | 0~1 비율 → % |
| 58 | 매출성장률 | `growthRevenue` + `endpoint:financial-growth` + `×100` | key-metrics-ttm 비표준, 별도 엔드포인트 |

### 4) 🟡 FMP 심볼 형식 비일관 — 점검 권장

- **`.` 포함 심볼**: id 39 달러 인덱스 `'DX-Y.NYB'`. `common-bugs #23`(FMP 프리미엄 `.` 심볼 402 → 배치 제외) 패턴에 걸려 **배치에서 누락/402 위험**. fetch 경로에서 별도 예외 처리 여부 확인 필요.
- **`^` 접두 혼재**: 지수는 `^GSPC/^KS11/^IXIC/^DJI/^KQ11/^N225/^HSI/^VIX`(접두 O), 원자재·암호·환율은 `GCUSD/CLUSD/USDKRW/BTCUSD`(접두 X). FMP 엔드포인트별 심볼 규칙 차이로 정상일 수 있으나, **`^KQ11`(코스닥)·`^KS11`(코스피)의 FMP 지원 여부** 실데이터 검증 권장.
- **FX/변동성 소스 혼재**: 원/달러(id 9)·VIX(id 8)는 `fmp` symbol, 달러/유로(id 38)는 `fred` series_id. 동종 지표가 서로 다른 소스를 사용 — 의도된 분기인지 확인 권장.

### 5) 🟢 `llm_postprocess` 교정 안전망 동작 확인

`normalize_llm_output()`(라인 82–89)이 `indicator_db_id`가 카탈로그에 없으면 `None`으로 교정하고, `match_indicators_for_llm`은 환각 방지를 위해 Gemini fallback을 **제외**(라인 306–307)하도록 되어 있어, 카탈로그 외 지표 유입은 차단됨. (`feedback_llm_indicator_hallucination` 정책과 정합.)

---

## 권장 조치 (우선순위)

1. **[P1] EPS 분류 불일치 수정** — `indicator_matcher.py` `KEYWORD_RULES`의 EPS `indicator_type`을 `'market_data'` → `'fundamental'`로 정정(카탈로그 일치).
2. **[P1] DXY(`DX-Y.NYB`) fetch 경로 검증** — `.` 심볼 402/배치 제외(#23) 영향 실측 확인.
3. **[P2] 단일 출처화** — BE 카탈로그를 진실의 소스로 두고 FE 미러·키워드맵을 빌드/스키마(`contracts/`)로 파생 생성하여 4중 하드코딩 드리프트 제거. (메모리 `feedback_indicator_catalog_sync` "동시 업데이트 필수"의 근본 해소.)
4. **[P3] `^KQ11/^KS11` FMP 지원 실데이터 검증** 및 FX 소스 혼재(9/38) 일관화 검토.
5. **[P3] BE `KEYWORD_RULES` data_params 복제 제거** — 이름 복제 대신 카탈로그 id 참조로 전환해 stale 위험 제거.

---

## 부록: 검사 메타데이터

- **확인 파일 라인 수**: prompt_builder.py(995L), indicator_matcher.py(339L), llm_postprocess.py(218L), AddIndicatorSheet.tsx(308L)
- **카탈로그 항목 수**: BE 64 / FE 64 (일치)
- **키워드 규칙 수**: BE `KEYWORD_RULES` 11 / FE `KEYWORD_INDICATOR_MAP` 27
- **metrics 시드 매칭**: 14/14
- **발견 이슈**: 🔴 1건(EPS 분류) · 🟡 6건(FE 미러 축소·분류체계 차이·키워드 이중관리·키워드 미커버·심볼 형식·FX 소스) · 🟢 무결성 대부분 양호

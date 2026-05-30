# 지표 카탈로그 동기화 감사 보고서

> **감사 일자**: 2026-05-30
> **모드**: 읽기 전용 (코드 수정 없음)
> **대상 파일**:
> - BE 정의: `thesis/services/prompt_builder.py` (`INDICATOR_CATALOG`, `INDICATOR_FREQUENCY`)
> - BE 후처리: `thesis/services/llm_postprocess.py`
> - BE 매칭: `thesis/services/indicator_matcher.py` (`KEYWORD_RULES`)
> - FE 표시: `frontend/components/thesis/AddIndicatorSheet.tsx` (`INDICATOR_CATALOG`, `KEYWORD_INDICATOR_MAP`)

---

## 요약 (동기화 상태)

| 검사 항목 | 상태 | 비고 |
|----------|:----:|------|
| BE↔FE 지표 ID 집합 | ✅ 완전 일치 | 양쪽 64개, ID·이름 100% 동일 |
| BE↔FE 업데이트 주기(freq) | ✅ 완전 일치 | `INDICATOR_FREQUENCY` ↔ FE `freq` 64개 매칭 |
| BE↔FE 카테고리 체계 | ⚠️ 의도적 불일치 | BE 5개 대분류 vs FE 17개 세분류 |
| BE↔FE description 미러 | ⚠️ FE 누락 | FE에 description 필드 자체 없음 (id/name/category/freq만) |
| BE description 품질 | ✅ 양호 | 64개 전부 존재, 빈/단문(<10자) 0건 |
| keyword_rules → 카탈로그 매핑 | ⚠️ 1건 drift | EPS `indicator_type` 불일치 (고아는 0건) |
| keyword_rules data_params | ✅ 일치 | 11개 룰 전부 카탈로그와 동일 형식 |
| data_params ↔ FMP 실제 형식 | ⚠️ 4건 특수 처리 | PER/ROE/ROA/매출성장률 (이미 audit_note 문서화) |
| BE↔FE keyword_rules 커버리지 | ⚠️ 비대칭 | BE 11룰(name 기반) vs FE 28룰(id 기반) |

**종합 판정**: 🟢 **핵심 동기화 양호**. ID/이름/주기는 완전 일치하여 LLM 추천 → FE 표시 경로에 깨짐 없음. 다만 (1) keyword_rules가 카탈로그와 **별도 데이터로 중복 관리**되어 1건 drift 발생, (2) FE에 description 미러 부재, (3) BE/FE keyword 매칭 로직이 **이중 소스**로 분기되어 향후 drift 위험. 즉시 장애는 없으나 **단일 소스화(SSOT)** 미적용에 따른 구조적 부채가 식별됨.

---

## BE ↔ FE 불일치 목록

### 1) 지표 항목 (ID + 이름) — ✅ 불일치 0건

양쪽 모두 **64개 지표**, ID 집합·이름 문자열 완전 일치.

```
ID 집합 (양쪽 동일, 64개):
1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,
20,21,22,23,24,25,26,30,31,32,33,34,35,36,37,38,39,40,
41,42,43,44,45,46,47,50,51,52,53,54,55,56,57,58,
60,61,62,63,64,65,66,67,68,69,70,71,72,73
```

- **BE에만 있는 항목**: 없음
- **FE에만 있는 항목**: 없음
- **이름 불일치**: 없음 (예: `금 (Gold)`, `원유 (WTI)`, `PER (주가수익비율)` 등 괄호 표기까지 동일)

> ℹ️ ID는 1~73 연속이 아니라 **의도적 비연속**(17~19, 27~29, 48~49, 59 결번). 향후 신규 지표 추가 시 결번 재사용 충돌 주의.

### 2) 업데이트 주기 (freq) — ✅ 불일치 0건

BE `INDICATOR_FREQUENCY`(dict) ↔ FE `freq`(필드) 64개 전부 매칭.

| 주기 | 대표 ID | BE | FE |
|------|---------|----|----|
| 금리 6 (기준금리) | 6 | 주간 | 주간 ✓ |
| 금리 37 (모기지) | 37 | 주간 | 주간 ✓ |
| 실질 GDP | 34 | 분기 | 분기 ✓ |
| 고용/물가 | 31,32,33,35,36 | 월간 | 월간 ✓ |
| 재무 체질 | 60~73 | 분기 | 분기 ✓ |

### 3) 카테고리 체계 — ⚠️ 구조적 차이 (의도적 추정)

| | BE (`category`) | FE (`category`) |
|---|---|---|
| 분류 수 | **5개 대분류** | **17개 세분류** |
| 값 | `market_data`, `macro`, `technical`, `fundamental`, `sentiment` | `수급`, `주요 지수`, `원자재`, `암호화폐`, `금리`, `환율/변동성`, `고용/성장`, `물가/주택`, `기술적`, `펀더멘털`, `재무 체질`, `밸류에이션`, `성장`, `운영 효율`, `이익 품질`, `주주환원`, `심리` |

- BE의 `CATEGORY_LABELS`는 프롬프트 그룹핑용(5개), FE는 UI 표시용 세분류(17개)로 **목적이 달라 직접 동기화 대상 아님**.
- 단, FE 세분류가 BE에 역매핑되지 않으므로 "어떤 BE category가 어떤 FE 세분류로 나뉘는지"의 **매핑 정의가 코드 어디에도 명시되지 않음** → FE 카테고리는 사람이 수동 배치. 신규 지표 추가 시 FE category 누락 위험.

### 4) description 미러 — ⚠️ FE 누락

- BE: 64개 전부 `description` 보유 (지표 의미·해석 설명).
- FE `CatalogIndicator`: `{ id, name, category, freq }`만 — **description 필드 없음**.
- 영향: FE 지표 추가 시트(`AddIndicatorSheet`)에서 사용자는 **지표 이름과 주기만** 보고 선택. BE가 보유한 풍부한 설명(예: 구리 "Dr. Copper", VIX "공포지수 내재변동성")이 UI에 노출되지 않음. 툴팁/설명 UX 개선 여지.

---

## description 품질

**대상**: BE `INDICATOR_CATALOG` 64개 (FE는 description 필드 부재로 평가 제외)

| 검사 | 결과 |
|------|:----:|
| 빈 description (`''`) | **0건** |
| 단문 description (<10자) | **0건** |
| 누락 (`description` 키 없음) | **0건** |

- 최단 description 예시(전부 10자 이상, 의미 충실):
  - id 14 코스닥: `한국 중소형 성장주 시장 지수.` (15자)
  - id 4 KOSPI: `한국 유가증권시장 전체 종목 시가총액 가중 지수.`
- 품질 일관성 양호: 대부분 "정의 + 해석/용도" 2문장 구조. 투자 맥락 설명 포함(예: 금리 negative 방향 근거, "Dr. Copper" 등 통념 반영).

> ✅ **품질 이슈 없음**. description 자체는 모범적. 개선 포인트는 품질이 아니라 **FE 미러링 부재**(위 BE↔FE 섹션 4 참조).

---

## keyword_rules 고아

**대상**: `indicator_matcher.py` `KEYWORD_RULES` (11개 룰), `match_by_keywords()`

### 고아 규칙 — ✅ 0건

KEYWORD_RULES는 `indicator_db_id`가 아니라 **지표 이름 문자열**(`name`)로 카탈로그를 간접 참조. 11개 룰이 참조하는 모든 이름이 카탈로그에 존재:

| 룰 키워드(대표) | 참조 지표명 | 카탈로그 ID | 존재 |
|----------------|------------|:----------:|:----:|
| 외국인/순매수 | 외국인 순매수 추이 | 1 | ✓ |
| 금리/연준 | 미국 기준금리 / 미국 10년 국채 금리 | 6, 7 | ✓ |
| VIX/공포 | VIX (공포지수) | 8 | ✓ |
| 환율/달러 | 원/달러 환율 | 9 | ✓ |
| RSI/MACD | RSI (14일) | 10 | ✓ |
| 센티먼트/뉴스 | 뉴스 센티먼트 | 11 | ✓ |
| 실적/EPS | EPS 추이 | 5 | ✓ |
| 기관 | 기관 순매수 추이 | 2 | ✓ |
| S&P/나스닥 | S&P 500 | 3 | ✓ |
| 코스피 | KOSPI 지수 | 4 | ✓ |
| 선거/정치 | VIX + KOSPI 지수 | 8, 4 | ✓ |

→ **매칭되지 않는 고아 규칙 없음**. `_find_in_catalog(name)` 최종 검증(line 332)도 정상 통과 가능.

### ⚠️ drift 1건: EPS `indicator_type` 불일치

| 항목 | KEYWORD_RULES (`indicator_matcher.py:95`) | INDICATOR_CATALOG (`prompt_builder.py:190`) |
|------|------|------|
| 지표 | EPS 추이 (id 5) | EPS 추이 (id 5) |
| 분류 | `indicator_type: 'market_data'` | `category: 'fundamental'` |

- KEYWORD_RULES의 EPS는 `indicator_type='market_data'`로 선언되어 있으나, 카탈로그의 EPS(id 5)는 `category='fundamental'`. **동일 지표의 분류가 두 소스에서 다름**.
- 나머지 10개 룰의 `indicator_type`은 카탈로그 `category`와 일치(기관 순매수=market_data ✓, 금리=macro ✓ 등).
- 원인: KEYWORD_RULES가 카탈로그를 참조하지 않고 **분류값을 하드코딩 중복 보유**. 카탈로그 단일 소스를 따르지 않아 발생한 drift.
- 영향: `match_by_keywords()` 결과의 `indicator_type`이 키워드 경로일 때만 `market_data`로 잘못 표기될 수 있음(PK 경로 `match_indicators_for_llm`은 카탈로그 직조회라 영향 없음). 표시/집계 시 EPS가 시장데이터로 분류되는 경미한 일관성 오류.

### ⚠️ 구조: keyword 매칭이 BE/FE 이중 소스

| | BE `KEYWORD_RULES` | FE `KEYWORD_INDICATOR_MAP` |
|---|---|---|
| 룰 개수 | 11개 | **28개** |
| 참조 방식 | 지표 **이름 문자열** | 지표 **ID 배열**(`indicatorIds`) |
| 데이터 중복 | name/data_source/data_params/reason 전부 재선언 | id + reason만 |
| 커버리지 | 수급·금리·VIX·환율·기술·실적·지수·정치 | + 유가/금/구리/가스/암호화폐/밸류/재무건전/배당/회전율/이익품질/물가/고용/GDP/주택/반도체/중국/일본/광고 |

- FE `KEYWORD_INDICATOR_MAP`의 `indicatorIds`는 28개 룰 전부 카탈로그 존재 ID만 참조 → **FE 고아 0건**.
- 그러나 BE(11룰)와 FE(28룰)의 키워드 커버리지·매핑이 **완전히 다른 데이터로 별도 관리**됨. 동일 키워드라도 추천 지표가 갈릴 수 있음(예: BE "정치"→VIX+KOSPI, FE "정치"→뉴스센티먼트+VIX). 이중 소스 drift 위험 구조.

---

## data_params 형식

### data_source별 형식 (BE 카탈로그 기준)

| data_source | data_params 형식 | 대표 ID | 제공자 |
|-------------|------------------|---------|--------|
| `fmp` (지수/원자재/암호화폐/환율) | `{'symbol': '^GSPC'}` | 3, 20, 25, 8 | FMP quote |
| `fmp` (기술적) | `{'indicator': 'RSI', 'period': 14}` | 10, 40~47 | FMP technical |
| `fmp` (펀더멘털) | `{'metric': 'eps'}` | 5, 51, 54~57 | FMP key-metrics-ttm |
| `fmp` (수급) | `{'metric': 'foreign_net_buy'}` | 1, 2 | FMP |
| `fred` | `{'series_id': 'FEDFUNDS'}` | 6, 7, 30~38 | FRED |
| `metrics` | `{'metric_code': 'gross_margin'}` | 60~73 | quarterly_metric_fetcher (내부) |
| `news_sentiment` | `{}` | 11 | 내부 |

→ data_source별 키 형식 일관성 양호. keyword_rules의 data_params도 위 형식과 11건 전부 일치.

### ⚠️ FMP 실제 형식과의 불일치 — 4건 (이미 audit_note로 문서화됨)

카탈로그 내부 주석으로 common-bugs #14 회귀 방지가 명시된 특수 처리 항목:

| ID | 지표 | 기대 필드 | 실제 FMP 차이 | 처리 플래그 |
|----|------|----------|--------------|-----------|
| 50 | PER | `peRatioTTM` | key-metrics-ttm에 **없음** → `earningsYieldTTM` 역수 | `inverse: True` |
| 52 | ROE | % 값 | `returnOnEquityTTM`이 **0~1 스케일** | `scale_multiplier: 100` |
| 53 | ROA | % 값 | `returnOnAssetsTTM`이 **0~1 스케일** | `scale_multiplier: 100` |
| 58 | 매출성장률 | key-metrics-ttm | **없음** → `/financial-growth/`의 `growthRevenue`(0~1) | `endpoint: 'financial-growth'`, `scale_multiplier: 100` |

- 이 4건은 FMP 표준 필드명/스케일과 다르다는 점이 **카탈로그 주석(audit_note)에 명시**되어 있어 회귀 방지 장치 존재. 단, 실제 fetch 로직이 `inverse`/`scale_multiplier`/`endpoint` 플래그를 **소비하는지**는 본 감사 범위(4개 파일) 밖 — fetcher 측 구현 검증 권장.

### ⚠️ '.' 포함 심볼 리스크 — 1건

| ID | 지표 | symbol | 리스크 |
|----|------|--------|--------|
| 39 | 달러 인덱스 (DXY) | `DX-Y.NYB` | common-bugs #23(FMP 프리미엄 `.` 심볼 402) 패턴. `.` 포함 심볼이 배치 제외 로직에 걸리거나 402 유발 가능 |

→ DXY는 `.` 포함 심볼이라 FMP 호출 시 402/제외 가능성. 실제 fetch 동작 확인 권장(본 감사 범위 밖).

---

## 결론 및 권고 (참고용 — 코드 미수정)

### 즉시 장애 없음 🟢
- BE↔FE ID/이름/주기 완전 일치 → LLM 추천 PK 경로(`match_indicators_for_llm`) 및 FE 표시 정상.
- description 품질 양호, keyword_rules 고아 0건, data_params 형식 일관.

### 구조적 부채 (drift 위험) ⚠️
1. **EPS `indicator_type` drift** (`indicator_matcher.py:95`): `market_data` → `fundamental`로 정정 시 카탈로그와 정합.
2. **keyword_rules 이중 소스**: BE(name 기반 11룰) / FE(id 기반 28룰)가 별도 데이터. 단일 소스(카탈로그 id 참조)로 통합 시 drift 원천 제거.
3. **FE description 부재**: BE description을 FE로 미러(혹은 API 노출)하면 지표 선택 UX 개선.
4. **FE category 매핑 미명시**: BE 5분류 → FE 17세분류 매핑 규칙이 코드에 없어 신규 지표 추가 시 FE 누락 위험.
5. **카탈로그 DB 마이그레이션 검토**: `prompt_builder.py` 상단 주석("향후 DB 모델로 마이그레이션 가능") — 단일 소스화의 근본 해법.

### 감사 범위 밖 (후속 검증 권장)
- PER/ROE/ROA/매출성장률 `inverse`/`scale_multiplier`/`endpoint` 플래그를 fetcher가 실제 소비하는지.
- DXY(`DX-Y.NYB`) `.` 심볼의 FMP 호출 동작.

---

*본 보고서는 읽기 전용 감사 결과이며 어떤 코드도 수정하지 않았습니다.*

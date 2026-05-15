# 지표 카탈로그 동기화 감사 보고서

- 감사일: 2026-05-15
- 감사자: Claude (읽기 전용 정적 분석)
- 감사 범위:
  - BE 정의: `thesis/services/prompt_builder.py` (`INDICATOR_CATALOG`, `INDICATOR_FREQUENCY`, `CATEGORY_LABELS`)
  - BE 후처리: `thesis/services/llm_postprocess.py` (`normalize_llm_output` → `get_indicator_by_id`)
  - BE 매칭: `thesis/services/indicator_matcher.py` (`KEYWORD_RULES`, `match_by_keywords`, `_find_in_catalog`)
  - FE 표시: `frontend/components/thesis/AddIndicatorSheet.tsx` (`INDICATOR_CATALOG`, `KEYWORD_INDICATOR_MAP`)

> 본 보고서는 정적 분석만으로 작성됨. 런타임 호출/실데이터 fetch 결과는 검증하지 않음.

---

## 요약 (동기화 상태)

| 검사 항목 | 결과 | 비고 |
|---|---|---|
| BE/FE 카탈로그 ID 셋 일치 | ✅ 완전 일치 (각 64개) | 양쪽 모두 동일한 64개 정수 ID |
| BE/FE 지표 이름 일치 | ✅ 완전 일치 | 64건 모두 문자열 동일 |
| 업데이트 주기(freq) 일치 | ✅ 완전 일치 | BE `INDICATOR_FREQUENCY` ↔ FE `freq` 동일 |
| BE 카테고리 ↔ FE 카테고리 의미 일치 | ⚠️ 다층 비대칭 | BE 5종 vs FE 17종, 파생 관계 없음 |
| `description` 결락/짧음 | ✅ 결락 0건 | 최단 15자, 모두 10자 이상 |
| BE `KEYWORD_RULES` 고아 규칙 | ✅ 고아 0건 | 11건 모두 카탈로그 이름과 매칭 |
| BE `KEYWORD_RULES` ↔ FE `KEYWORD_INDICATOR_MAP` 균형 | ❌ 큰 비대칭 | BE 11개 인디케이터 커버 vs FE 30+ 키워드 그룹·50+ ID 매핑 |
| BE `KEYWORD_RULES` 카탈로그 참조 방식 | ⚠️ 이름 기반 | ID가 아닌 문자열로 참조 → silent break 위험 |
| BE 내 `KEYWORD_RULES.data_params` ↔ `INDICATOR_CATALOG.data_params` 일치 | ✅ 일치 | 11건 모두 동일 형식·값 |
| FE에 `data_params` 존재 여부 | ⚠️ 없음 | FE는 id/name/category/freq만 노출 → 데이터 형식 불일치 자체는 발생하지 않음 |
| FMP 응답 형식 vs 카탈로그 `metric` | ⚠️ 4건 audit_note로 명시된 비표준 처리 필요 | id 50/52/53/58 |

핵심 판정:
- **카탈로그 정의 동기화는 양호**(ID·이름·freq 일치).
- **카탈로그 활용층 동기화는 비대칭**(BE matcher가 FE에 비해 매우 빈약, BE는 이름 기반 참조라 취약).
- **FE에 `data_params`가 부재**해서 형식 불일치는 표면화되지 않지만, 펀더멘털/기술 지표용 `target_symbol` 입력 UI도 함께 부재 → BE fetch 시 누락 가능성.

---

## BE ↔ FE 불일치 목록

### 1. 항목(ID/이름) 불일치
- **없음.** BE/FE 모두 동일한 64개 ID + 동일 이름.
- 양쪽 정렬한 ID 셋: `{1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 20, 21, 22, 23, 24, 25, 26, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 50, 51, 52, 53, 54, 55, 56, 57, 58, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73}`.

### 2. ID 번호 갭(둘 다 동일)
양쪽 카탈로그 모두 `17–19`, `27–29`, `48–49`, `59`가 비어 있음. 향후 추가 예약 슬롯으로 보임. 문제 없음.

### 3. 카테고리(category) 의미 불일치 — **표시상 비대칭**
BE 카테고리(5종, `CATEGORY_LABELS` 정의):
- `market_data`, `macro`, `technical`, `fundamental`, `sentiment`

FE 카테고리(17종, `categoryOrder` 배열):
- `수급`, `주요 지수`, `원자재`, `암호화폐`, `금리`, `환율/변동성`, `고용/성장`, `물가/주택`, `기술적`, `펀더멘털`, `재무 체질`, `밸류에이션`, `성장`, `운영 효율`, `이익 품질`, `주주환원`, `심리`

영향:
- FE 카테고리가 BE에서 파생되지 않고 손수 박혀 있음 → BE에서 새 지표 추가 시 FE에서 별도로 분류 필요.
- 예: BE에서 모두 `fundamental`인 id 67(`EV/EBITDA`)·68(`FCF 수익률`)·70(`DSO`) 등은 FE에서 각각 `밸류에이션`/`밸류에이션`/`운영 효율`로 세분됨.

### 4. 프로퍼티 셋 불일치
| 필드 | BE 보유 | FE 보유 |
|---|---|---|
| `id` | ✅ | ✅ |
| `name` | ✅ | ✅ |
| `category` | ✅ (5종 표준화) | ✅ (17종, BE와 별개 분류) |
| `freq` (업데이트 주기) | ✅ `INDICATOR_FREQUENCY` 별도 dict | ✅ 인라인 |
| `data_source` | ✅ (`fmp`/`fred`/`news_sentiment`/`metrics`) | ❌ |
| `data_params` | ✅ | ❌ |
| `support_direction` | ✅ (`positive`/`negative`) | ❌ |
| `description` | ✅ | ❌ |

→ FE는 화면에 노출되는 최소 메타만 보유. 데이터 fetch와 매칭 시맨틱(positive/negative)은 BE 전유.

### 5. freq 비교 (스팟 체크)
- id 1·2·3·4·12·13·14·15·16: 양쪽 모두 `일간` ✅
- id 6: 양쪽 모두 `주간` ✅, id 7: 양쪽 모두 `일간` ✅
- id 30: 양쪽 모두 `일간` ✅, id 37: 양쪽 모두 `주간` ✅
- id 31·32·33·35·36: 양쪽 모두 `월간` ✅, id 34: 양쪽 모두 `분기` ✅
- id 10·40–47: 양쪽 모두 `일간` ✅
- id 5·50–58·60–73: 양쪽 모두 `분기` ✅
- 64건 전수 일치.

---

## description 품질

### 결락 / 빈 description
- **결락 0건.** 모든 64개 항목이 `description` 키 보유, 모두 비어 있지 않음.

### 짧은 description (< 10자)
- **0건.** 가장 짧은 항목은 id 14 `코스닥 지수` → `한국 중소형 성장주 시장 지수.` (15자).

### 참고: 길이 분포 (대표 표본)
- 최단: 15자 (id 14)
- 중앙값 부근: 30–35자 ("주가를 EPS로 나눈 값. 수익 대비 주가 수준(밸류에이션) 측정." 등)
- 최장: 약 45–50자 ("연준 기준금리. 유동성과 할인율에 직접 영향. 금리 인상은 주식에 부정적." 등)

전체적으로 "정의 1문 + 의미/용도 1문" 패턴으로 일관됨.

### 잠재 개선 포인트 (품질 결함은 아님)
- id 14 `코스닥 지수` 설명이 가장 빈약. 다른 지수(NASDAQ/다우/니케이/항셍)는 "성격 + 대표성"을 명시한 반면 코스닥은 분류만 진술.
- id 21 `원유 (WTI)`·id 24 `천연가스` 등은 한국 주식 가설에서의 인플레/원자재 연관 의미를 추가하면 더 유용. 현 description도 사용 가능.

---

## keyword_rules 고아

### 정의 (`indicator_matcher.py:12–154`)
`KEYWORD_RULES`는 11개 규칙. 각 규칙은 `keywords[]` + `indicators[]` 보유. `indicators[].name`이 카탈로그 `INDICATOR_CATALOG[].name`과 문자열 매칭되어야 `_find_in_catalog`(`indicator_matcher.py:332-338`)가 카탈로그 항목을 반환.

### 매칭 결과
| KEYWORD_RULES 인디케이터 이름 | BE 카탈로그 매칭 | 카탈로그 ID |
|---|---|---|
| `외국인 순매수 추이` | ✅ | 1 |
| `미국 기준금리 (Fed Funds Rate)` | ✅ | 6 |
| `미국 10년 국채 금리` | ✅ | 7 |
| `VIX (공포지수)` | ✅ | 8 |
| `원/달러 환율` | ✅ | 9 |
| `RSI (14일)` | ✅ | 10 |
| `뉴스 센티먼트` | ✅ | 11 |
| `EPS 추이` | ✅ | 5 |
| `기관 순매수 추이` | ✅ | 2 |
| `S&P 500` | ✅ | 3 |
| `KOSPI 지수` | ✅ | 4 |

**고아 규칙 0건.** 11개 모두 카탈로그와 정확히 매칭.

### ⚠️ 구조적 약점 — 이름 기반 결합 (silent-break 위험)
- `KEYWORD_RULES`는 `indicator_db_id` 없이 `name` 문자열만 보유. `_find_in_catalog`도 `ind['name'] == name` 비교.
- 카탈로그의 `name`을 한 글자라도 변경하면 키워드 매칭 결과의 후처리(`indicator_matcher.py:317`)에서 `catalog_entry`가 `None`이 되어 LLM 빌더가 카탈로그 미연결 dict를 그대로 사용 → 그래프/패널 일관성 깨질 수 있음.
- 권장: `KEYWORD_RULES` 항목에 `indicator_db_id`(int) 필수 필드를 두고 ID 기반으로 카탈로그 lookup. (FE `KEYWORD_INDICATOR_MAP`은 이미 ID 기반.)

### ⚠️ 커버리지 격차 (BE matcher가 FE 추천에 비해 매우 빈약)
- BE `KEYWORD_RULES`: 11개 인디케이터, 11개 키워드 그룹.
- FE `KEYWORD_INDICATOR_MAP` (`AddIndicatorSheet.tsx:109–139`): 30개 키워드 그룹, 약 50+ ID 매핑.
- FE 단독 커버 키워드(예시): `구리`, `천연가스`, `비트코인`, `암호화폐`, `밸류에이션`, `ROE/ROA/ROIC`, `부채/레버리지`, `배당/FCF/주주환원`, `회전율/효율`, `이익 품질/발생액`, `CPI/인플레`, `GDP/산업생산`, `주택/모기지`, `반도체/AI`, `중국/항셍`, `일본/니케이`, `광고/플랫폼` 등.
- 결과: 동일 전제 텍스트에 대해 FE 추천 UI가 보여주는 후보와 BE matcher가 가설 빌더 fallback에서 산출하는 후보가 크게 다름. BE matcher fallback이 비어 있으면 `match_by_gemini`로 가지만, `indicator_matcher.py:307` 주석대로 LLM 빌더 경로에서는 환각 회피를 위해 Gemini fallback을 의도적으로 막아둠 → **BE 매칭 누락은 곧 추천 누락**.

---

## data_params 형식

### BE 내부 일관성 (`INDICATOR_CATALOG.data_params` 형식)
| `data_source` | `data_params` 스키마 | 대표 ID |
|---|---|---|
| `fmp` | `{symbol: "<ticker>"}` | 3, 4, 8, 9, 12–16, 20–26, 38, 39 |
| `fmp` | `{metric: "<key>"}` | 1, 2, 5, 51, 54, 55, 56, 57 |
| `fmp` | `{indicator: "<name>", period: n}` (또는 `fast/slow/signal`) | 10, 40, 41, 42, 43, 44, 45, 46, 47 |
| `fmp` | `{metric, inverse, audit_note}` | 50 (PER) |
| `fmp` | `{metric, scale_multiplier, audit_note}` | 52 (ROE), 53 (ROA) |
| `fmp` | `{metric, endpoint, scale_multiplier, audit_note}` | 58 (매출성장률 YoY) |
| `fred` | `{series_id: "<FRED code>"}` | 6, 7, 30, 31, 32, 33, 34, 35, 36, 37, 38 |
| `news_sentiment` | `{}` | 11 |
| `metrics` | `{metric_code: "<snake_case>"}` | 60–73 |

BE 내 `KEYWORD_RULES.indicators[].data_params`와 `INDICATOR_CATALOG.data_params` 11건 비교 → **전부 일치**(symbol/series_id/metric 키와 값 동일, 추가 필드 없음).

### FMP 응답 형식 불일치 — 카탈로그 안에 이미 명시된 4건
| ID | 이름 | `data_params` 처리 | 비고 |
|---|---|---|---|
| 50 | PER (주가수익비율) | `{metric: 'earningsYieldTTM', inverse: True, audit_note: 'PER = 1 / earningsYieldTTM (#14 회귀 방지)'}` | FMP `key-metrics-ttm`에 `peRatioTTM` 부재. 역수 변환 필요. |
| 52 | ROE | `{metric: 'returnOnEquityTTM', scale_multiplier: 100, audit_note: 'ratio 0~1 → % (#14 회귀 방지)'}` | FMP는 0~1 ratio 반환 → ×100 변환 필요. |
| 53 | ROA | `{metric: 'returnOnAssetsTTM', scale_multiplier: 100, audit_note: 'ratio 0~1 → % (#14 동일 패턴)'}` | 동일. |
| 58 | 매출성장률 (YoY) | `{metric: 'growthRevenue', endpoint: 'financial-growth', scale_multiplier: 100, audit_note: 'FMP /financial-growth/ growthRevenue (#14 표준 필드 아님)'}` | 표준 endpoint(`key-metrics-ttm`)가 아니라 `/financial-growth/`로 분기 필요. |

→ 이 4건은 **카탈로그 차원에서는 명시 완료**(audit_note + flag 필드 추가). 실제 fetcher가 `inverse`/`scale_multiplier`/`endpoint`를 해석하는지가 별도 검증 대상(본 감사 범위 밖).

### FE ↔ BE data_params 형식 차이
- FE `INDICATOR_CATALOG`는 `data_params` 자체를 보유하지 않음 → **형식 불일치는 발생하지 않음**.
- 단, FE에서 펀더멘털/기술 지표를 선택할 때 `target_symbol`(예: NVDA, META) 입력이 BE 빌더 프롬프트에서는 필수(`prompt_builder.py:414–419`)지만, `AddIndicatorSheet.tsx`에는 `target_symbol` 입력 UI가 없음. 사용자가 시트에서 선택할 경우 BE fetch가 어떤 심볼로 가는지 불분명.
  - LLM 빌더 경로에서는 LLM이 `target_symbol`을 자체 생성하므로 충돌 없음.
  - 사용자 수동 추가(`AddIndicatorSheet`) 경로에서는 `target_symbol` 누락 위험.

---

## 부록 — 코드 위치 인덱스
- BE 카탈로그 정의: `thesis/services/prompt_builder.py:14-310`
- BE freq 매핑: `thesis/services/prompt_builder.py:321-342`
- BE ID/이름 인덱스: `thesis/services/prompt_builder.py:345-348`
- BE `get_indicator_by_id`: `thesis/services/prompt_builder.py:598-600`
- BE `KEYWORD_RULES`: `thesis/services/indicator_matcher.py:12-154`
- BE `_find_in_catalog`: `thesis/services/indicator_matcher.py:332-338`
- BE 후처리 ID 정규화: `thesis/services/llm_postprocess.py:82-93`
- FE 카탈로그: `frontend/components/thesis/AddIndicatorSheet.tsx:15-91`
- FE 키워드 매핑: `frontend/components/thesis/AddIndicatorSheet.tsx:109-139`
- FE 카테고리 순서: `frontend/components/thesis/AddIndicatorSheet.tsx:211-216`

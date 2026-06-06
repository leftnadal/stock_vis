# 지표 카탈로그 동기화 감사 보고서

> 생성일: 2026-06-06 · 모드: 읽기 전용 (코드 수정 없음) · 감사 범위: INDICATOR_CATALOG BE/FE 동기화 + keyword_rules + data_params 형식

## 검사 대상 파일

| 역할 | 파일 | 내용 |
|------|------|------|
| BE 카탈로그 정의 | `thesis/services/prompt_builder.py` | `INDICATOR_CATALOG` (64개) + `INDICATOR_FREQUENCY` + `CATEGORY_LABELS` |
| BE 후처리 | `thesis/services/llm_postprocess.py` | `indicator_db_id` 카탈로그 외 값 → None 교정 |
| BE 매칭 | `thesis/services/indicator_matcher.py` | `KEYWORD_RULES` (11개, name 기반) |
| BE 소비(fetch) | `thesis/tasks/eod_pipeline.py` | `data_params` → FMP/FRED/news/metrics fetcher |
| BE DB 모델 | `thesis/models/indicator.py` | 런타임 `Indicator` 레코드 (`data_source`, `data_params`) |
| FE 표시 | `frontend/components/thesis/AddIndicatorSheet.tsx` | `INDICATOR_CATALOG` 미러 (64개) + `KEYWORD_INDICATOR_MAP` (id 기반) |

---

## 요약 (동기화 상태)

| 검사 항목 | 결과 | 판정 |
|-----------|------|------|
| BE↔FE 지표 ID 집합 (64개) | 완전 일치 (BE-only 0, FE-only 0) | ✅ 양호 |
| BE↔FE name (동일 ID 기준) | 64개 전부 일치 | ✅ 양호 |
| BE↔FE freq (`INDICATOR_FREQUENCY` vs FE `freq`) | 64개 전부 일치 | ✅ 양호 |
| description 빈/짧음(<10자) | 0건 (64개 전부 10자 이상) | ✅ 양호 |
| BE keyword_rules 고아 (name→카탈로그) | 0건 | ✅ 양호 |
| FE keyword map 고아 (id→카탈로그) | 0건 | ✅ 양호 |
| `INDICATOR_FREQUENCY` 키 정합성 | 누락/잉여 0건 | ✅ 양호 |
| **카탈로그 단일 소스 부재 (3중 미러)** | static catalog + DB model + FE mirror | ⚠️ 구조 리스크 |
| **data_params ↔ fetcher 형식 불일치** | 2~3건 (아래 상세) | ⚠️ 운영 영향 |
| keyword_rules 커버리지 격차 | BE 11/64 vs FE 53/64 | 🔸 참고 |

**종합 판정**: 카탈로그 항목 자체(ID·name·freq·description)의 BE/FE 동기화 상태는 **매우 양호**(불일치 0건). 단, ① 단일 소스 없이 3중으로 미러링되는 구조와 ② 일부 `data_params`가 실제 fetcher가 요구하는 형식과 맞지 않는 점이 잠재 리스크다.

---

## BE ↔ FE 불일치 목록

### 항목 동기화: 불일치 0건

- BE(`prompt_builder.py`) 64개 ↔ FE(`AddIndicatorSheet.tsx`) 64개
- **ID 집합 완전 일치** — 어느 한쪽에만 존재하는 지표 없음
- **name 완전 일치** — 동일 ID에서 이름 다른 항목 없음
- **freq 완전 일치** — BE `INDICATOR_FREQUENCY`와 FE `freq` 필드 64개 모두 동일

> 과거 CLAUDE.md 메모리(`feedback_indicator_catalog_sync` — "3곳 분산 미러, 동시 업데이트 필수")의 우려와 달리, 현재 시점 스냅샷에서는 **수동 동기화가 잘 유지되고 있음**.

### ⚠️ category 체계는 BE/FE 의도적 비대칭

| | BE | FE |
|---|---|---|
| 분류 키 | `category` 5개 대분류 (`market_data`, `macro`, `technical`, `fundamental`, `sentiment`) | `category` 17개 세분류 (`수급`, `주요 지수`, `원자재`, `금리`, `재무 체질`, `밸류에이션` 등) |
| 용도 | LLM 프롬프트 블록 그룹핑(`build_indicator_block`) | UI 카테고리 헤더 표시 |

- 두 체계는 **목적이 달라** 1:1 매핑되지 않음 (문제 아님).
- 다만 FE는 `category` 외에 BE 대분류 정보를 갖고 있지 않아, 향후 "펀더멘털 전체" 같은 BE 기준 필터를 FE에서 재현하려면 별도 매핑이 필요하다. **현 상태로는 영향 없음**.

### ⚠️ 동일 이름 컴포넌트 2개 (혼동 위험)

- `frontend/components/thesis/AddIndicatorSheet.tsx` — **카탈로그 미러 보유** (동기화 대상, 본 감사의 FE 소스)
- `frontend/components/thesis/indicators/AddIndicatorSheet.tsx` — `RecommendedIndicator[]` props만 받는 **AI 추천 전용** 시트 (카탈로그 미러 없음)
- 동기화 리스크는 없으나, 같은 이름의 컴포넌트가 2개 존재해 유지보수 시 잘못된 파일 수정 위험. (참고용 기록)

---

## description 품질

- **빈 description: 0건**
- **10자 미만 description: 0건**
- 64개 전부 한 문장 이상의 의미 있는 설명을 보유 (예: id 23 구리 — "구리 선물 가격. 경기 선행지표로 \"Dr. Copper\"라 불림.")
- **판정: ✅ 양호** — 추가 조치 불필요

> 참고: description은 BE에만 존재하며 FE 미러에는 포함되지 않음(`get_indicator_description()`으로 BE 프롬프트/응답에서만 사용). FE에서 지표 설명 툴팁이 필요해지면 별도 동기화 포인트가 됨.

---

## keyword_rules 고아

### BE `KEYWORD_RULES` (`indicator_matcher.py`, name 기반) — 고아 0건

- 11개 규칙이 참조하는 지표 name **전부 카탈로그에 존재**
- 규칙 내 `data_source`/`data_params`도 카탈로그 동일 항목과 일치
- **커버리지: 11/64 (17%)** — 키워드 룰로 직접 추천되는 지표는 11개뿐
  - 나머지는 LLM 빌더의 `indicator_db_id`(PK) 경로로 추천됨. `match_indicators_for_llm`은 PK 매칭 우선이고 실패 시에만 키워드 룰 fallback이므로, **낮은 커버리지 자체가 버그는 아님**.
  - 단, LLM을 거치지 않는 순수 텍스트 매칭(`match_indicators_for_premise`) 경로에서는 11개 외 지표가 추천되지 않는다는 점은 인지 필요.

### FE `KEYWORD_INDICATOR_MAP` (`AddIndicatorSheet.tsx`, id 기반) — 고아 0건

- 모든 `indicatorIds`가 FE 카탈로그에 존재 (존재하지 않는 id 참조 0건)
- **커버리지: 53/64 (83%)**
- **키워드 룰에서 한 번도 추천되지 않는 지표 11개** (UI '전제 관련 추천'에 자동 노출 안 됨):
  - `13`(다우존스), `14`(코스닥), `22`(은/Silver), `38`(달러/유로 환율)
  - `41`(스토캐스틱 %K), `42`(볼린저 밴드 %B), `43`(ATR), `44`(OBV), `45`(SMA 50일), `46`(SMA 200일), `47`(EMA 12일)
  - → 이들은 전체 카탈로그 목록에서 수동 선택만 가능. 기능상 결함은 아니나, 보조 기술적 지표/세부 지수는 "전제 관련 추천" 혜택을 못 받음. (개선 후보)

### ⚠️ BE/FE keyword 룰은 별개 구현 (동기화 미보장)

- BE는 **name 기반 11개 규칙**, FE는 **id 기반 26개 규칙** — 키워드 세트·매핑 대상·추천 이유가 모두 독립적으로 작성됨.
- 동일 키워드에 BE/FE가 서로 다른 지표를 추천할 수 있음 (예: '금리' → BE는 6,7 / FE는 6,7,30).
- 카탈로그 항목과 달리 keyword 룰은 **검증된 단일 소스가 없음**. 현재 고아는 없지만, 카탈로그에서 지표가 제거되면 FE id 참조가 깨질 수 있어 향후 회귀 지점.

---

## data_params 형식

`thesis/tasks/eod_pipeline.py`의 fetcher 4종(`fmp`/`fred`/`news_sentiment`/`metrics`)이 `data_params`를 소비하는 방식과 카탈로그 정의를 대조한 결과.

### data_source 분포 (64개)

| data_source | 개수 | fetcher | 요구 키 |
|-------------|------|---------|---------|
| `fmp` | 38 | `_fetch_fmp_value` | `symbol` 또는 `metric` |
| `fred` | 11 | `_fetch_fred_value` | `series_id` |
| `metrics` | 14 | `_fetch_metrics_value` | `metric_code` (+symbol/target) |
| `news_sentiment` | 1 | `_fetch_news_sentiment_value` | `symbol` |

### ✅ 정상 처리되는 형식

- **fred** (11개): 전부 `{'series_id': ...}` — fetcher 요구와 일치
- **metrics** (14개, id 60~73): 전부 `{'metric_code': ...}` — fetcher 요구와 일치, symbol은 thesis.target fallback
- **fmp symbol형** (지수/원자재/암호화폐/VIX/환율 등): `{'symbol': ...}` — `get_quote` 정상
- **fmp 기술적** (RSI/MACD 등): `{'indicator': ..., 'period': ...}` — ⚠️ 단, fetcher는 `metric`만 분기하고 `indicator`/`period` 키는 읽지 않음 → quote의 `price`로 폴백될 가능성 (아래 P2 참조)
- **fmp TTM** (id 50/52/53/58 등): `metric.endswith('TTM')` 또는 `endpoint='financial-growth'` 분기 + `inverse`/`scale_multiplier` 후처리 정상 적용. **#14 회귀 방지 메타데이터(`audit_note`)가 코드와 일치** ✅

### ⚠️ P1 — `news_sentiment` (id 11): data_params 빈 dict, fetcher는 symbol 필수

```python
# 카탈로그 (prompt_builder.py:306)
{'id': 11, 'name': '뉴스 센티먼트', 'data_source': 'news_sentiment', 'data_params': {}, ...}

# fetcher (eod_pipeline.py:203-208)
params = indicator.data_params or {}
symbol = params.get('symbol')
if not symbol:
    logger.warning(...); return None, None   # ← fallback 없이 즉시 실패
```

- `fmp` fetcher는 symbol 없을 때 `thesis.target`으로 fallback하지만, **`news_sentiment` fetcher에는 fallback이 없음**.
- 카탈로그의 `data_params`가 `{}`라서, 런타임 DB Indicator에 symbol이 채워지지 않으면 **뉴스 센티먼트 지표는 항상 None 반환**.
- 영향: 사용자가 종목 가설에 '뉴스 센티먼트'를 추가해도 값이 수집되지 않을 수 있음. (DB 등록 시 symbol 주입 여부 확인 필요 — 본 감사는 정적 분석이므로 런타임 DB 미확인)

### ⚠️ P1 — id 1·2 (외국인/기관 순매수): FMP 미제공 metric

```python
{'id': 1, 'name': '외국인 순매수 추이', 'data_source': 'fmp', 'data_params': {'metric': 'foreign_net_buy'}}
{'id': 2, 'name': '기관 순매수 추이', 'data_source': 'fmp', 'data_params': {'metric': 'institutional_net_buy'}}
```

- fetcher 동작: `field = value_map.get(metric, metric)` → `value_map`에 `foreign_net_buy`/`institutional_net_buy` 없음 → `quote.get('foreign_net_buy')` 직접 조회.
- **FMP `/stable/quote`는 외국인/기관 순매수 필드를 제공하지 않음** (한국 시장 수급 데이터는 FMP 커버리지 밖).
- 결과: 두 지표 모두 **항상 `None`** 반환 가능성 높음. 카탈로그에 정의되어 LLM이 추천할 수 있으나 실제 값 수집 불가.
- 권장(코드 수정 없음, 기록만): 데이터 소스 확보 전까지 `data_source='manual'` 처리 또는 카탈로그 비활성 검토.

### 🔸 P2 — fmp 기술적 지표(id 10/40~47): `indicator`/`period` 키 미사용

- 카탈로그는 `{'indicator': 'RSI', 'period': 14}` 형식이나, `_fetch_fmp_value`는 `metric` 키만 분기하고 `indicator`/`period`는 읽지 않음.
- `metric` 키가 없으므로 `params.get('metric', 'price')` → `'price'` → 기술적 지표 자리에 **종가가 들어갈 가능성**.
- FMP 기술 지표 전용 endpoint(`/technical-indicators/`) 분기가 fetcher에 없음 → 기술적 지표 9종의 실제 값 정확성 미보장. (운영 데이터 확인 권장)

### data_params 단일 소스 부재 (구조)

- `data_params`는 ① static catalog(`prompt_builder.py`), ② 마이그레이션/시드로 생성되는 **DB `Indicator` 레코드**, ③ FE 미러(FE는 data_params 없이 id/name/freq만) 에 분산.
- 실제 fetch는 **DB 레코드의 data_params**를 사용하므로, static catalog와 DB가 어긋나면 카탈로그 감사만으로는 잡히지 않음. (DB ↔ catalog 정합성은 별도 런타임 점검 필요)

---

## 권장 후속 조치 (참고 — 본 보고서는 수정 없음)

| 우선순위 | 항목 | 내용 |
|----------|------|------|
| P1 | id 11 news_sentiment | data_params 빈 dict + fetcher symbol fallback 부재 → 값 미수집 점검 |
| P1 | id 1·2 순매수 | FMP 미제공 metric → 데이터 소스 확보 또는 manual 전환 검토 |
| P2 | id 10/40~47 기술적 | fetcher가 `indicator`/`period` 미사용 → 기술 지표 endpoint 분기 필요성 확인 |
| P3 | 단일 소스화 | static catalog ↔ DB Indicator ↔ FE 미러 3중 구조 → contracts/ 또는 codegen 기반 단일 소스 검토 |
| P3 | FE 추천 사각 | 키워드 룰 미커버 11개(13,14,22,38,41~47) "전제 관련 추천" 노출 보강 |

---

## 결론

- **카탈로그 항목 동기화(ID·name·freq·description)는 불일치 0건으로 매우 양호**하다. 수동 미러링이 현재까지 정확히 유지되고 있다.
- 실질 리스크는 **항목 일치가 아니라 ① data_params↔fetcher 형식 불일치(P1 2건 + P2 1건)와 ② 단일 소스 부재**에 있다.
- 즉시 운영 영향이 있는 것은 **id 1·2(순매수)와 id 11(뉴스 센티먼트)** — 카탈로그에는 멀쩡히 존재하나 실제 값이 수집되지 않을 가능성이 높다.

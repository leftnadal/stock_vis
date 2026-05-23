# 지표 카탈로그 동기화 감사 보고서

- **감사 일자**: 2026-05-23
- **감사 범위**: 읽기 전용 (코드 수정 없음)
- **대상 파일**
  - BE 정의: `thesis/services/prompt_builder.py` (`INDICATOR_CATALOG`)
  - BE 후처리: `thesis/services/llm_postprocess.py`
  - BE 매칭: `thesis/services/indicator_matcher.py` (`KEYWORD_RULES`)
  - FE 미러: `frontend/components/thesis/AddIndicatorSheet.tsx` (`INDICATOR_CATALOG`, `KEYWORD_INDICATOR_MAP`)

---

## 요약 (동기화 상태)

| 검사 항목 | 결과 | 비고 |
|---|---|---|
| BE ↔ FE 카탈로그 ID 동기화 | ✅ **완전 일치** | 양쪽 64개 항목, ID 집합 동일 |
| BE ↔ FE 카탈로그 이름 동기화 | ✅ 일치 | 모든 ID의 `name` 문자열 동일 |
| BE ↔ FE 카테고리 라벨 체계 | ⚠️ **분기 존재** | BE 5개 대분류 vs FE 17개 세부 카테고리 |
| description 필드 품질 | ✅ 양호 | 64/64 항목 모두 30자 이상 충실히 채워짐 |
| KEYWORD_RULES 고아 규칙 | ✅ 없음 | 11개 규칙 모두 카탈로그 이름과 매칭 |
| KEYWORD_RULES 커버리지 | ⚠️ **53/64 미커버** | BE 측은 11개 지표(17%)에만 키워드 매칭 등록 |
| FE KEYWORD_INDICATOR_MAP 커버리지 | ✅ 광범위 | FE는 28개 룰로 50+ 지표 커버 — BE보다 풍부 |
| BE/FE 키워드 룰 동기화 | ❌ **불일치 (구조 차이)** | BE는 이름 기반 dict 7~11개, FE는 ID 기반 룰 28개 — 동기화 의도 없음 |
| data_params 특수 처리 | ⚠️ 주의 항목 4건 | PER/ROE/ROA/매출성장률 (audit_note 명시) |

**결론**: 카탈로그 본체(ID/이름/카테고리/주기)는 BE↔FE 완전 동기화. 다만 **키워드 매칭 레이어가 BE와 FE에서 독립적으로 유지**되고 있어, 한쪽 갱신 시 다른 쪽 누락 위험이 상존한다.

---

## BE ↔ FE 불일치 목록

### 1. 카탈로그 항목 ID 동기화 ✅

양쪽 모두 동일한 64개 ID 보유.

```
공통 ID 집합 (BE = FE):
1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16,
20, 21, 22, 23, 24, 25, 26,
30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
40, 41, 42, 43, 44, 45, 46, 47,
50, 51, 52, 53, 54, 55, 56, 57, 58,
60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73
```

- **BE에만 있는 ID**: (없음)
- **FE에만 있는 ID**: (없음)
- **번호 갭**: 17~19, 27~29, 48~49, 59 비어 있음 → 양쪽 동일하게 비어 있어 영향 없음

### 2. 카테고리 라벨 체계 불일치 ⚠️

BE와 FE의 카테고리 분류가 **다른 차원**에서 운영된다.

| 측면 | BE (`category` 필드) | FE (`category` 필드) |
|---|---|---|
| 분류 수 | 5개 대분류 | 17개 세부 분류 |
| 사용처 | 프롬프트 생성 시 `[label]` 그룹핑 | UI 카테고리 헤더 (`categoryOrder` 배열) |
| 예: `id=50` PER | `fundamental` | `펀더멘털` |
| 예: `id=67` EV/EBITDA | `fundamental` | `밸류에이션` |
| 예: `id=70` DSO | `fundamental` | `운영 효율` |
| 예: `id=20` 금 | `market_data` | `원자재` |

**BE 카테고리 (5개)**: `market_data`, `macro`, `technical`, `fundamental`, `sentiment`
**FE 카테고리 (17개)**: `수급`, `주요 지수`, `원자재`, `암호화폐`, `금리`, `환율/변동성`, `고용/성장`, `물가/주택`, `기술적`, `펀더멘털`, `재무 체질`, `밸류에이션`, `성장`, `운영 효율`, `이익 품질`, `주주환원`, `심리`

**판단**: 의도된 차이로 보임 (BE=프롬프트용 대분류, FE=UX용 세분류). 단, FE가 카테고리를 자체 정의하기 때문에 **BE 카탈로그에 신규 지표 추가 시 FE 카테고리 매핑이 수동 결정**되어야 함. 자동화/검증 장치 없음.

### 3. FE 누락 필드 ⚠️ (정보 손실)

FE `CatalogIndicator` 타입은 `{id, name, category, freq}` 만 보관. BE의 다음 필드가 FE 미러에 부재:

- `data_source` (fmp/fred/metrics/news_sentiment)
- `data_params` (실제 수집 파라미터)
- `support_direction` (positive/negative)
- `description` (지표 설명문)

**영향**: FE는 PK(id)만 선택해 BE로 송신하므로 기능적 문제는 없으나, FE 측 툴팁/설명 표시 시 BE description 재조회가 필요(API 또는 별도 동기화).

---

## description 품질

### 통계

- 전체 항목: 64개
- description 보유: **64/64 (100%)**
- 빈 description: **0건**
- < 10자 짧은 description: **0건**
- 평균 길이: 약 35~45자

### 가장 짧은 description (참고)

| ID | 이름 | description (글자 수) |
|---|---|---|
| 4 | KOSPI 지수 | "한국 유가증권시장 전체 종목 시가총액 가중 지수." (24자) |
| 14 | 코스닥 지수 | "한국 중소형 성장주 시장 지수." (16자) |

모두 10자 초과 — **기준 위반 없음**.

### 일관성 점검

- ✅ 한국어 문장체 통일
- ✅ 마침표로 끝남
- ✅ 1~2문장 길이 균일
- ⚠️ 일부 지표는 "측정/지표/대리 지표"가 중복 사용 (스타일 통일 여지)

### 데이터 무결성 메모

- `id=50` (PER), `id=52` (ROE), `id=53` (ROA), `id=58` (매출성장률)에 `audit_note` 주석이 `data_params`에 포함됨.
  → common-bugs #14 회귀 방지용. fetcher에서 `inverse`/`scale_multiplier`/`endpoint` 키를 인식해야 함.

---

## keyword_rules 고아

### `thesis/services/indicator_matcher.py` `KEYWORD_RULES` 분석

총 11개 룰, 각 룰은 `indicators[].name` 으로 카탈로그 지표를 참조.

#### ✅ 카탈로그 매칭 (고아 없음)

| 룰 # | 키워드 (대표) | 참조 지표 이름 | 카탈로그 ID |
|---|---|---|---|
| 1 | 외국인 | 외국인 순매수 추이 | 1 ✓ |
| 2 | 금리/FOMC | 미국 기준금리 (Fed Funds Rate) | 6 ✓ |
| 2 | 금리/FOMC | 미국 10년 국채 금리 | 7 ✓ |
| 3 | VIX/공포 | VIX (공포지수) | 8 ✓ |
| 4 | 환율/달러 | 원/달러 환율 | 9 ✓ |
| 5 | RSI/MACD | RSI (14일) | 10 ✓ |
| 6 | 센티먼트/뉴스 | 뉴스 센티먼트 | 11 ✓ |
| 7 | 실적/EPS | EPS 추이 | 5 ✓ |
| 8 | 기관 | 기관 순매수 추이 | 2 ✓ |
| 9 | S&P/나스닥 | S&P 500 | 3 ✓ |
| 10 | 코스피 | KOSPI 지수 | 4 ✓ |
| 11 | 선거/정치 | VIX (공포지수) | 8 ✓ |
| 11 | 선거/정치 | KOSPI 지수 | 4 ✓ |

**모든 룰이 카탈로그에 존재 → 고아 규칙 0건.**

#### ⚠️ 미커버 지표 53건 (카탈로그에는 있으나 keyword 룰 부재)

BE `KEYWORD_RULES`가 다루지 않는 카탈로그 지표:

- 주요 지수: 12, 13, 14, 15, 16 (NASDAQ, 다우, 코스닥, 니케이, 항셍)
- 원자재/암호화폐: 20~26 (금, WTI, 은, 구리, 가스, BTC, ETH)
- 금리/환율 보조: 30 (2년), 37 (모기지), 38 (EUR), 39 (DXY)
- 고용/성장/물가: 31, 32, 33, 34, 35, 36
- 기술적 보조: 40~47 (MACD, 스토캐스틱, 볼린저, ATR, OBV, SMA50/200, EMA12)
- 펀더멘털: 50~58 (PER, PBR, ROE, ROA, 부채비율, FCF, 배당, 영업이익률, 매출성장)
- 재무 체질: 60~73 (Gross/Net Margin, ROIC, Current Ratio, 이자보상, ND/EBITDA, FCF Margin, EV/EBITDA, FCF Yield, Op Income Growth, DSO, Asset TO, Accruals, Net Shareholder Yield)

**영향**: `match_indicators_for_premise()` 호출 시 키워드 매칭 실패 → `match_by_gemini()` fallback 진입. 단, `match_indicators_for_llm()` (PK 우선)에서는 fallback이 제외되어 있음(L307 주석: "환각 지표 생성 방지"). LLM 빌더 외 경로에서는 환각 위험 잔존.

#### FE `KEYWORD_INDICATOR_MAP` 대비

FE는 28개 룰로 ID 기반 매칭 (50+ 카탈로그 ID 커버). BE보다 광범위함.

| 측면 | BE `KEYWORD_RULES` | FE `KEYWORD_INDICATOR_MAP` |
|---|---|---|
| 룰 수 | 11 | 28 |
| 매칭 키 | 이름(string) | ID(number) |
| 키워드 케이스 | 혼합 (kor + eng 대소문자) | 모두 lowercase |
| 결과 형식 | `{name, data_source, ..., reason}` dict | `{indicatorIds, reason}` |
| 동기화 의도 | ❌ 없음 (독립적으로 진화) | ❌ 없음 |

**판단**: BE와 FE의 키워드 룰은 **별도 정책으로 운영**되는 듯하나, 의도된 분리인지 코드 진화 누락인지 불명. 양쪽 동기화 문서 부재.

---

## data_params 형식

### BE INDICATOR_CATALOG의 data_params 패턴

| `data_source` | `data_params` 키 | 카탈로그 예시 |
|---|---|---|
| `fmp` (수급) | `metric` | `{'metric': 'foreign_net_buy'}` (id=1) |
| `fmp` (지수/원자재/암호화폐) | `symbol` | `{'symbol': '^GSPC'}` (id=3) |
| `fmp` (기술적) | `indicator`, `period`, `fast/slow/signal` | `{'indicator': 'RSI', 'period': 14}` (id=10) |
| `fmp` (펀더멘털 key-metrics-ttm) | `metric` (+ `inverse`/`scale_multiplier`/`endpoint`) | `{'metric': 'pbRatioTTM'}` (id=51) |
| `fred` | `series_id` | `{'series_id': 'FEDFUNDS'}` (id=6) |
| `metrics` (재무 체질) | `metric_code` | `{'metric_code': 'roic'}` (id=62) |
| `news_sentiment` | (없음, 빈 dict) | `{}` (id=11) |

### 특수 처리 주의 항목 (audit_note 명시)

| ID | 지표 | 특수 키 | 의미 | 원인 |
|---|---|---|---|---|
| 50 | PER | `inverse: True` | `value = 1 / earningsYieldTTM` | FMP key-metrics-ttm에 `peRatioTTM` 부재 (common-bugs #14) |
| 52 | ROE | `scale_multiplier: 100` | `value = returnOnEquityTTM × 100` | FMP ratio 0~1 스케일 → % 변환 |
| 53 | ROA | `scale_multiplier: 100` | 동일 패턴 | #14 동일 패턴 예방 |
| 58 | 매출성장률 | `endpoint: 'financial-growth'`, `scale_multiplier: 100` | FMP `/financial-growth/` 별도 호출 | `revenueGrowthYoY` 미존재 → `growthRevenue` 0~1 스케일 |

**검증 필요 사항** (코드 수정 없이 보고만):
- Fetcher (예: `quarterly_metric_fetcher.py`)가 `inverse`/`scale_multiplier`/`endpoint`/`audit_note` 키를 모두 인식하는지 별도 확인 필요.
- FE 측 카탈로그 미러에는 `data_params`가 보관되지 않음 → 클라이언트에서 이 특수 처리 표시가 불가능 (BE 응답 의존).

### `KEYWORD_RULES` 내부 data_params 동기화

`indicator_matcher.py` `KEYWORD_RULES`는 카탈로그와 독립적으로 `data_params`를 복제 저장한다.

```python
# 예: id=6 (Fed Funds Rate)
# CATALOG: {'series_id': 'FEDFUNDS'}
# KEYWORD_RULES: {'series_id': 'FEDFUNDS'}  ← 동일
```

11개 룰 모두 카탈로그 값과 일치. **단, 카탈로그가 변경되면 KEYWORD_RULES의 사본도 수동 동기화 필요** (자동화 없음). 위험 케이스: `audit_note` 같은 특수 키가 추후 RSI(id=10) 등에 추가되면 KEYWORD_RULES 측은 누락될 가능성 큼.

---

## 권고 사항 (참고용 — 실행 보류)

1. **KEYWORD_RULES 카탈로그 참조화**: `indicators[]` 안에 `data_source`/`data_params`를 복제하지 말고 `indicator_id` 만 보관하면 단일 진실 소스 확보.
2. **FE 카테고리 매핑 자동화**: BE `category` → FE 세부 카테고리 매핑 테이블을 `contracts/`에 정의해 신규 지표 추가 시 양쪽 동시 갱신 보장.
3. **카탈로그 동기화 테스트**: `tests/unit/thesis/test_llm_builder.py:144`에 ID/이름 집합 비교 테스트가 있다면 FE TS 파일까지 포함하도록 확장(별도 스크립트로 TS 파싱).
4. **KEYWORD_RULES 커버리지 확장**: 53개 미커버 지표 중 자주 등장하는 키워드(예: 부동산/모기지, CPI, GDP, DXY)를 추가 등록 — `match_by_gemini` fallback 의존도 감소.
5. **카테고리 라벨 단일화 검토**: BE 5개 대분류와 FE 17개를 모두 보관하는 이중 키 구조(예: `category_group`, `category_detail`)로 통합.

---

## 부록: 검증 명령

```bash
# BE 카탈로그 ID 목록
grep "'id':" thesis/services/prompt_builder.py | grep -oE "'id': [0-9]+" | sort -t: -k2 -n -u

# FE 카탈로그 ID 목록
grep "id:" frontend/components/thesis/AddIndicatorSheet.tsx | grep -oE "id: [0-9]+" | sort -u

# KEYWORD_RULES 참조 이름
grep "'name':" thesis/services/indicator_matcher.py
```

# Stock-Vis Portfolio Coach — 문서 인덱스

> 최종 갱신: 2026-04-18 v3 (Dictionary ↔ 코드 동기화 완료)
> 상태: Metric Dictionary v1.2 + 구현 코드 완전 동기화. 세션 D(LLM 프롬프트 설계) 진입 가능

---

## 1. 폴더 구조

```
docs/portfolio/
├── INDEX.md                                  ← 이 파일
│
├── design/                                   ← 최신 설계 문서 (5개)
│   ├── preset-design-v3.1.md                 ← 프리셋 시스템 설계서 (확정 결정 38개)
│   ├── preset-metrics-matrix.md              ← 12개 프리셋 × 지표 × 계층 매트릭스
│   ├── metric-dictionary-v1.2.md             ← 57개 지표 정의서 (Type1: 39 / Type2: 13 / Type3: 5)
│   ├── portfolio-requirements-v0.2.md        ← Portfolio 기능 요구사항
│   └── service-restructure.md                ← 서비스 아키텍처 재설계
│
├── reference/                                ← 레퍼런스 (1개, 변경 없이 유지)
│   └── preset-reference.md                   ← 투자 전략 40개 + 포트폴리오 이론 17개
│
├── implementation/                           ← 구현 산출물 (7개)
│   ├── models.py                             ← Django DB 모델 9개
│   └── metrics/definitions/
│       ├── __init__.py
│       ├── metrics.py                        ← 57개 지표 코드 상수 (Dictionary와 1:1 대응)
│       ├── presets.py                        ← 12개 프리셋 코드 상수
│       ├── preset_metrics.py                 ← 136개 프리셋-지표 매핑
│       └── versions.py                       ← 버전 번들 (metric_version=1.2)
│
└── archive/                                  ← 이력용 (3개)
    ├── preset-design-v1.md
    ├── preset-design-v2.md
    └── portfolio-requirements-v0.1.md
```

**파일 수 합계**: 16개 (`.md` 10개 + `.py` 6개), 약 8,944줄

---

## 2. 현재 상태 (2026-04-18 기준)

### 2-1. Metric & Preset

| 항목 | 수량 | 비고 |
|---|---|---|
| **총 지표 (Dictionary = 코드)** | **57개** | Type 1 (stock_level) 39 + Type 2 (portfolio_level) 13 + Type 3 (composite) 5 |
| **MVP 프리셋** | **12개** | Value 2, Growth 2, Income 2, Factor 4, Special 2 |
| **프리셋-지표 매핑** | **136개** | 모든 57개 지표가 최소 1개 프리셋에서 사용 (미참조 0개) |
| **Piotroski 서브** | **9개** | Dictionary §5 #37 내부 표로 통합 (f_score_total + details JSON 철학) |

### 2-2. 버전

| 버전 항목 | 현재 | 직전 변경 |
|---|---|---|
| `metric_version` | **1.2** | 2026-04-18: Dictionary ↔ 코드 완전 동기화 |
| `preset_version` | 1.0 | — |
| `scoring_version` | 1.0 | — |
| `prompt_version` | 1.0 | — |
| `universe_version` | sp500_v1 | — |

### 2-3. 프리셋별 tier 분포

| 프리셋 | Core | Supporting | Context | 총 |
|---|---|---|---|---|
| buffett_quality_value | 4 | 7 | 4 | 15 |
| piotroski_f_score | 1 | 3 | 3 | 7 |
| garp | 3 | 4 | 3 | 10 |
| quality_growth | 4 | 5 | 4 | 13 |
| dividend_growth | 3 | 4 | 3 | 10 |
| shareholder_yield | 4 | 3 | 3 | 10 |
| quality_factor | 4 | 4 | 3 | 11 |
| low_volatility | 5 | 6 | 3 | 14 |
| price_momentum | 4 | 3 | 3 | 10 |
| multi_factor | 5 | 5 | 2 | 12 |
| contrarian | 4 | 5 | 3 | 12 |
| concentrated_portfolio | 7 | 2 | 3 | 12 |

---

## 3. 2026-04-18 동기화 작업 (완료)

INDEX.md v2에서 계획된 "동기화 20건 + Piotroski 서브 9건"이 이번 세션에 전부 완료되었고, placeholder 확장 작업도 포함해 **총 57건이 한 번에 처리**됨.

### 3-1. Batch 1 — Dictionary (v1.1 → v1.2)

| 작업 | 건수 | 상세 |
|---|---|---|
| Rename | 4 | `stock_count`→`holding_count`, `factor_value/quality/momentum`→`composite_*` |
| 재구성 | 2 | `factor_size`→`composite_growth` (EPS/매출 성장 합성으로 교체), `factor_balance_score`→`composite_low_vol` (변동성 합성으로 교체) |
| 신규 엔트리 | 4 | `f_score_total` (Piotroski 9개 서브 표 포함), `ulcer_index`, `up_capture_ratio`, `dividend_yield_portfolio` |
| Piotroski 서브 정의 | 9 | #37 엔트리 내부에 판정 조건 + FMP 필드 매핑 + 결측 처리 표로 통합 |
| 번호 재정렬 | — | Type 1: 36→39, Type 2: 12→13, Type 3: 5 유지. 총 53→57 |
| 섹션 동기화 | — | §4 (목록), §9 (버전 예시), §11 (변경이력) 모두 v1.2 반영 |

### 3-2. Batch 2 — metrics.py (Dictionary 1:1 대응)

| 작업 | 건수 | 상세 |
|---|---|---|
| f_score_total 보강 | 1 | 서브 9개 참조 + FMP 필드 9개 명시 + `aggregation_type=composite_checklist` |
| placeholder → full detail | 25 | Type 1 13개 (beta, return_*, volatility_1y 등), Type 2 7개, Type 3 5개 모두 확장 |
| 신규 지표 추가 | 8 | Type 1: `volume_change_ratio`, `buyback_yield`. Type 2: `portfolio_volatility`, `sharpe_ratio`, `sortino_ratio`, `avg_correlation`, `max_risk_contribution`, `max_position_weight` |
| 헤더 docstring | — | v1.1 → v1.2, Type별 개수 명시 |

**파일 크기**: 526줄 → **1,105줄**

### 3-3. Batch 3 — preset_metrics.py + versions.py

| 프리셋 | 변경 |
|---|---|
| Contrarian | `volume_change_ratio` Supporting 추가 |
| Buffett Quality Value | `buyback_yield` Supporting 추가 |
| Low Volatility | `portfolio_volatility` Core 추가. `sharpe_ratio`, `sortino_ratio`, `max_risk_contribution` Supporting 추가 |
| Concentrated Portfolio | `max_position_weight`, `avg_correlation` Core 추가. `portfolio_volatility` Context 추가 |
| versions.py | `metric_version` 1.0 → **1.2** + pre-MVP 버전 정책 주석 |

**매핑 엔트리**: 126개 → **136개** (+10)

### 3-4. 부가 수정 (이번 세션 발견)

- Dictionary 헤더의 "총 지표 수 53개" → 57개 (Batch 1 수정 중 놓친 부분)
- Dictionary §1 본문 "53개 지표" → 57개 (2곳)

---

## 4. 확정된 설계 결정 — 누적 52개+

### 4-1. 설계서 v3.1 내 (38개)
→ `design/preset-design-v3.1.md` 부록 참조

### 4-2. Metric Dictionary 공통 결정 (8개, D-1 ~ D-8)
→ `design/metric-dictionary-v1.2.md` 부록 A 참조

### 4-3. Django 모델 결정 (6개, M-1 ~ M-6)
→ `implementation/models.py` 헤더 docstring 참조

### 4-4. 네이밍 결정 (7개, N-1 ~ N-7, 2026-04-18 확정)

| # | 대상 | 결정 |
|---|---|---|
| N-1~3 | Multi-Factor 합성 | `composite_*` 통일 |
| N-4 | 5번째 팩터 슬롯 | `composite_low_vol` (저변동성) |
| N-5 | 보유 종목 수 | `holding_count` |
| N-6 | 집중도 지표 | `hhi_concentration` + `sector_hhi` (2개 분리) |
| N-7 | 상위 종목 비중 | `top3_weight` |

---

## 5. 다음 작업 로드맵

### 5-1. 즉시 (현재 사이클)

| 순위 | 작업 | 예상 | 상태 |
|---|---|---|---|
| 1 | Dictionary ↔ 코드 동기화 | ~1세션 | ✅ **완료** |
| C | Piotroski 서브 9개 내부 스펙 | 0.5세션 | ✅ **완료** (Dictionary §5 #37) |
| **D** | **Portfolio Coach LLM 프롬프트 설계** | **2~3세션** | **다음 작업** |

### 5-2. 다음 사이클 (MVP 준비)

| 작업 | 산출물 |
|---|---|
| 비교군 정책 상세화 | 산업 분류, fallback, 최소 표본, 특수군 처리 |
| 강점/약점 선정 알고리즘 | 단일 이상치 vs 구조적 약점 구분, Core 우선 + 비중 가중 영향도 |
| API 설계 | 분석 요청/결과/저장 REST 스펙 |
| UI 와이어프레임 | 현황 ↔ 코칭 전환, 진단 카드 레이아웃 |

### 5-3. Phase 2+ (MVP 이후)

| 시점 | 작업 |
|---|---|
| Phase 2 | Core 세분화 (Definitional/Evaluative), Hard Gate, Chain Sight/Thesis Layer 2, Screener, 대화형 Coach, 비교 뷰, Russell 3000, 글로벌 세율 테이블 |
| Phase 3 | 행동 편향(BPT), 글로벌 유니버스, 시뮬레이션 진단 |

---

## 6. 핵심 문서 안내

### 처음 읽을 순서

1. **`design/preset-design-v3.1.md`** — 전체 시스템 철학과 설계 결정 이해
2. **`design/metric-dictionary-v1.2.md`** — 57개 지표의 정확한 정의, FMP 매핑, 결측 처리
3. **`design/preset-metrics-matrix.md`** — 12개 프리셋 각각의 상세 (진단 카드 예시, 차별화)
4. **`implementation/metrics/definitions/*.py`** — 설계 → 코드 구현 결과
5. **`reference/preset-reference.md`** — 이론적 배경 (투자 전략, 포트폴리오 이론)

### 목적별 참조

| 목적 | 문서 |
|---|---|
| 특정 지표 산식·FMP 필드 | `design/metric-dictionary-v1.2.md` |
| 프리셋 철학과 진단 카드 예시 | `design/preset-metrics-matrix.md` |
| 설계 결정 배경 (왜 이렇게?) | `design/preset-design-v3.1.md` 부록 |
| 구현 시 유효 metric_id 검증 | `implementation/metrics/definitions/metrics.py` |
| DB 스키마 | `implementation/models.py` |
| Portfolio 기능 스펙 (CandidateHolding 등) | `design/portfolio-requirements-v0.2.md` |
| 서비스 플로우 (Dashboard → Chain Sight → Portfolio) | `design/service-restructure.md` |

---

## 7. 파일 상세 정보

### design/ (5개, 4,454줄)

| 파일 | 줄 | 내용 |
|---|---|---|
| preset-design-v3.1.md | 804 | 프리셋 시스템 설계서. 확정 결정 38개 |
| preset-metrics-matrix.md | 1,001 | 12개 프리셋 상세 (해설·진단 카드·차별화) |
| **metric-dictionary-v1.2.md** | **1,464** | 57개 지표 정의 (+Piotroski 9서브 통합) |
| portfolio-requirements-v0.2.md | 851 | Portfolio 기능 요구사항 |
| service-restructure.md | 334 | 서비스 3단계 플로우 |

### reference/ (1개, 759줄)

| 파일 | 줄 | 내용 |
|---|---|---|
| preset-reference.md | 759 | 투자 전략 40 + 포트폴리오 이론 17 |

### implementation/ (7개, 2,121줄)

| 파일 | 줄 | 내용 |
|---|---|---|
| models.py | 608 | Django 모델 9개 |
| **metrics.py** | **1,105** | 57개 지표 코드 상수 |
| presets.py | 107 | 12개 프리셋 |
| **preset_metrics.py** | **263** | 136개 매핑 |
| versions.py | 25 | 버전 번들 (metric_version=1.2) |
| __init__.py | 13 | 패키지 초기화 |

### archive/ (3개, 1,610줄)

| 파일 | 줄 | 용도 |
|---|---|---|
| preset-design-v1.md | 459 | 방향 설계 이력 |
| preset-design-v2.md | 566 | 중간 리뷰 반영 이력 |
| portfolio-requirements-v0.1.md | 585 | 요구사항 초안 이력 |

---

## 8. Git 커밋 권장 구조

동기화 작업을 기능 단위 3개 커밋으로 나눠 기록하면 이력 추적과 롤백이 쉬워:

```bash
# Commit 1: Dictionary 동기화
git add docs/portfolio/design/metric-dictionary-v1.2.md
git commit -m "docs(metrics): sync v1.1→v1.2 — rename 4 + restructure 2 + add 4 + Piotroski 9 subs"

# Commit 2: metrics.py Dictionary 1:1 대응
git add docs/portfolio/implementation/metrics/definitions/metrics.py
git commit -m "feat(metrics): expand 25 placeholders to full detail + add 8 new metrics"

# Commit 3: 프리셋 배정 + 버전업
git add docs/portfolio/implementation/metrics/definitions/preset_metrics.py
git add docs/portfolio/implementation/metrics/definitions/versions.py
git commit -m "feat(presets): assign 8 new metrics to presets + bump metric_version 1.0→1.2"

# Commit 4: 문서 이력
git add docs/portfolio/INDEX.md
git commit -m "docs: update INDEX.md v3 (sync completion reflected)"
```

---

## 9. 변경 이력

| 날짜 | 버전 | 변경 |
|---|---|---|
| 2026-04-18 | v3 | Dictionary ↔ 코드 동기화 완료 반영. 지표 53→57개, 매핑 126→136개, metric_version 1.0→1.2. Piotroski 서브 9개 Dictionary 통합 완료. 파일명 정리 (`metric-dictionary-v1.1.md` → `metric-dictionary-v1.2.md`). Dictionary 본문 "53개" 잔재 수정 (3곳) |
| 2026-04-18 | v2 | 파일 16개 실물 분석 + 대화 이력 교차 검증. 누락 파일 2건 정정, Dict 53 ↔ 코드 49 불일치 발견. 네이밍 결정 7건 확정 + 코드 일부 반영. 동기화 액션 플랜 20건 작성 |
| 2026-04-18 | v1 | 초판 (대화 기반 추정) |

# Slice 12 Part 3 — Smoke + 부분 Matrix (E3 + E3 concentrated 통합)

> **사전 결정 채택 (Part 3 진입 직전 확정)**
>
> - **D1-B**: E3 + E3 concentrated 호출자 통합 (E1/E2/E5/E6은 Slice 13+ 분산)
> - **D2-B**: 5 카테고리 × 3 fixture = 15 case smoke matrix (정상 / edge / gate 발동)
> - **D3-B**: #59 E5 격리 지속 (Slice 13 Step 0 multi-debt mini 두 번째 사례로 #51과 동시 처리)
> - **D4-A**: Slice 12 종결 시 신규 슬라이스 유형 "component buildup +30~40" KPI 9 matrix 등록

---

## 0. 진입 Baseline (실행 전 확인 필수)

| 항목          | 값                                                                                               |
| ------------- | ------------------------------------------------------------------------------------------------ |
| 브랜치        | `slice12`                                                                                        |
| 선행 commit   | `88f6274` (Part 2 종결)                                                                          |
| 회귀 baseline | **641 passed**                                                                                   |
| 누적 비용     | $2.6998 / $4.00 (마진 32.5%)                                                                     |
| Slice cap     | $0.0554 / $1.00 (마진 94.46%)                                                                    |
| LLM 호출      | 4 / 50 (마진 46)                                                                                 |
| 잔존 부채     | #51 (S13 Step 0 1순위), #59 E5 (PS 0.5, D4-A 격리)                                               |
| Part 2 산출물 | PresetSpec schema + 5 풀 ScoringEngine + gate 패턴 3건 (income 2 / factor low_vol 1) + 12 preset |

**진입 전 검증 명령**:

```bash
git log --oneline -1                      # 88f6274 확인
pytest --co -q | tail -5                  # 641 collected 확인
git status                                # clean tree
git branch --show-current                 # slice12
```

---

## 1. Part 3 본질 (외부 호출자 첫 발생)

Part 2까지 외부 호출자 0건 → **Part 3에서 처음 진입점과 통합**.

Part 3의 책임:

1. **E3 + E3 concentrated 호출자 통합** — 점수가 실제 LLM commentary에 공급되는 경로 첫 구축
2. **Smoke matrix 15 case 실행** — 5 카테고리 × 3 fixture, 비용 발생 단계
3. **Gate 발동 검증 자연 포함** — Part 2 동작 검증 표(income yield 0.01 cut / factor low_vol beta 1.5 cut)를 자동화
4. **IDENTICAL 7/7 + KPI 9 검증** — 호출자 통합에도 기존 7 진입점 hash 불변 보장

**Scope 격리 (D1-B + D3-B)**:

- E1 / E2 / E5 / E6 호출자 통합 ❌ (Slice 13+ 분산)
- action_items 변경 ❌ (#59 E5는 Slice 13 Step 0 multi-debt mini로 #51과 묶음 처리)
- analysis_engine 의존 ❌ (5슬라이스 일관)
- 12 preset 또는 PresetSpec.gate 임계 변경 ❌ (Part 2 동결)

---

## 2. Step 0: E3 호출자 통합 (`portfolio/services/e3_coach.py`)

### 2.1 통합 패턴

E3 진입점은 개별 종목 코칭을 담당. Part 2의 5 카테고리 ScoringEngine 결과를 LLM prompt context로 공급.

**현재 구조 (Part 2까지)**:

```
e3_coach.py
  └─ run_e3_coach(symbol, preset_id, ...)
       └─ prompt builder → LLM 호출 → commentary 반환
```

**Part 3 통합 후**:

```
e3_coach.py
  └─ run_e3_coach(symbol, preset_id, metrics, ...)
       ├─ category = resolve_category(preset_id)  # 신규 helper
       ├─ scorer = get_scorer(category)
       ├─ scores = scorer.score(metrics)  # {preset_id: score, _category_score: avg}
       └─ prompt builder (scores 포함) → LLM 호출 → commentary 반환
```

### 2.2 신규 helper: `resolve_category(preset_id) -> str`

```python
# portfolio/services/scoring/__init__.py 에 추가
PRESET_ID_TO_CATEGORY: dict[str, str] = {
    # value
    "buffett_quality_value": "value",
    "piotroski_f_score": "value",
    # growth
    "garp": "growth",
    "quality_growth": "growth",
    # income
    "dividend_growth": "income",
    "shareholder_yield": "income",
    # factor
    "quality_factor": "factor",
    "low_volatility": "factor",
    "price_momentum": "factor",
    "multi_factor": "factor",
    # special
    "contrarian": "special",
    "concentrated_portfolio": "special",
}

def resolve_category(preset_id: str) -> str:
    if preset_id not in PRESET_ID_TO_CATEGORY:
        raise KeyError(f"Unknown preset_id: {preset_id!r}")
    return PRESET_ID_TO_CATEGORY[preset_id]
```

> ⚠️ **preset_id 명명은 Part 2 결과(`88f6274`)와 정확히 일치시킬 것**. 위 mapping은 Part 2 보고 기준이며, 코드 작성 전 실제 preset 파일 5개의 `*_SPECS` list를 1차 source로 검증.

### 2.3 e3_coach.py 수정 사양

**수정 원칙**:

- 기존 시그니처 가능한 한 유지 (frontend 보호, Slice 11 P3 정책 정합)
- `metrics: dict[str, float] | None = None` 추가 (기본값 None, 후방 호환)
- metrics=None이면 기존 동작 (점수 계산 skip)
- metrics 제공 시 scores를 prompt context에 주입

**코드 패턴**:

```python
from portfolio.services.scoring import get_scorer, resolve_category

def run_e3_coach(
    symbol: str,
    preset_id: str,
    metrics: dict[str, float] | None = None,  # 신규 (기본 None)
    # ... 기존 파라미터
) -> dict:
    # ... 기존 로직

    scores_context = ""
    if metrics is not None:
        category = resolve_category(preset_id)
        scorer = get_scorer(category)
        scores = scorer.score(metrics)
        scores_context = format_scores_for_prompt(scores)  # 신규 helper

    # prompt builder에 scores_context 전달
    # ...
```

### 2.4 `format_scores_for_prompt(scores) -> str` 신규 helper

```python
# portfolio/services/scoring/__init__.py 에 추가
def format_scores_for_prompt(scores: dict[str, float]) -> str:
    """Score dict → LLM prompt 친화 문자열.

    Gate 발동(0점)은 명시적 표시.
    """
    lines = []
    for key, value in scores.items():
        if key.startswith("_"):
            continue
        if value == 0.0:
            lines.append(f"- {key}: 0.0 (gate 미통과)")
        else:
            lines.append(f"- {key}: {value:.2f}")
    category_score = scores.get("_category_score", 0.0)
    lines.append(f"\n카테고리 평균: {category_score:.2f}")
    return "\n".join(lines)
```

---

## 3. Step 1: E3 concentrated 호출자 통합

### 3.1 e3_concentrated_coach.py 수정 사양

E3 concentrated는 portfolio 전체 관점. preset_id가 `concentrated_portfolio` (special 카테고리)에 자연 매핑.

```python
# portfolio/services/e3_concentrated_coach.py
from portfolio.services.scoring import get_scorer, resolve_category, format_scores_for_prompt

def run_e3_concentrated_coach(
    portfolio_metrics: dict[str, float] | None = None,  # 신규
    # ... 기존
) -> dict:
    # ... 기존

    scores_context = ""
    if portfolio_metrics is not None:
        # special 카테고리 직결 (concentrated_portfolio preset)
        scorer = get_scorer("special")
        scores = scorer.score(portfolio_metrics)
        # concentrated만 추출 (다른 special preset인 contrarian 제외)
        scores_context = format_scores_for_prompt({
            "concentrated_portfolio": scores.get("concentrated_portfolio", 0.0),
            "_category_score": scores.get("concentrated_portfolio", 0.0),  # single preset
        })

    # ...
```

### 3.2 IDENTICAL 보장 메커니즘

기존 호출자(테스트·view)는 새 파라미터(`metrics=`, `portfolio_metrics=`)를 **전달하지 않음** → 기본값 None → 점수 계산 skip → prompt 동일 → 응답 hash 동일.

```bash
# 검증
pytest tests/ -k "identical" -v
# 7/7 PASS 필수
```

---

## 4. Step 2: Smoke fixture 작성 (D2-B 핵심)

### 4.1 디렉토리 구조

```
tests/scoring/fixtures/
├── value_normal.json
├── value_edge.json
├── value_gate.json        # gate 없는 카테고리는 "두 번째 정상 case"로
├── growth_normal.json
├── growth_edge.json
├── growth_gate.json       # 위와 동일 (gate 없음 → 두 번째 정상)
├── income_normal.json
├── income_edge.json
├── income_gate.json       # yield 0.01 < 0.02 → gate 발동
├── factor_normal.json
├── factor_edge.json
├── factor_gate.json       # beta 1.5 > 1.2 → low_volatility gate 발동
├── special_normal.json
├── special_edge.json
└── special_gate.json      # esg/concentrated 등 (Part 2 설계 확인 필요)
```

**총 15 fixture**.

### 4.2 fixture 표준 schema

각 JSON 파일:

```json
{
	"category": "income",
	"case_type": "gate",
	"preset_id": "dividend_growth",
	"symbol": "TEST_INCOME_GATE",
	"metrics": {
		"dividend_yield": 0.01,
		"payout_ratio_inv": 0.5,
		"dividend_growth": 0.3
	},
	"expected_gate_triggered": true,
	"expected_category_score_range": [0.0, 0.0]
}
```

### 4.3 fixture 작성 가이드

| 카테고리 | normal 케이스                          | edge 케이스                    | gate 케이스                                            |
| -------- | -------------------------------------- | ------------------------------ | ------------------------------------------------------ |
| value    | 모든 지표 중간값, 정상 점수 30~70 기대 | 모든 지표 부재 (빈 dict) → 0점 | (gate 없음) 두 번째 정상값 변형                        |
| growth   | 동일                                   | 동일                           | 동일                                                   |
| income   | yield 0.05 정상                        | 빈 dict → gate 미통과로 0      | **yield 0.01 → gate 발동, score=0**                    |
| factor   | beta 0.9 정상                          | 빈 dict                        | **beta 1.5 → low_volatility gate, 다른 3 preset 정상** |
| special  | esg/concentrated 정상값                | 빈 dict                        | Part 2 special.py 확인 후 결정                         |

### 4.4 fixture loader

```python
# tests/scoring/conftest.py
import json
from pathlib import Path
import pytest

FIXTURE_DIR = Path(__file__).parent / "fixtures"

@pytest.fixture
def load_fixture():
    def _load(name: str) -> dict:
        with open(FIXTURE_DIR / f"{name}.json") as f:
            return json.load(f)
    return _load
```

---

## 5. Step 3: Smoke matrix 실행 (LLM 호출 발생 — Part 2 이후 첫 비용)

### 5.1 Smoke 실행 스크립트

```
portfolio/services/coach/smoke/slice12_smoke.py
```

**책임**:

1. 15 fixture 순회
2. 각 fixture → e3_coach 호출 (preset_id + metrics)
3. score + LLM commentary 결과 수집
4. JSON dump → `docs/portfolio/coach/slice12/part3_smoke_results.json`

**예시 구조**:

```python
def run_slice12_smoke() -> dict:
    results = []
    for fixture_name in FIXTURE_NAMES:  # 15건
        fixture = load_fixture(fixture_name)
        result = run_e3_coach(
            symbol=fixture["symbol"],
            preset_id=fixture["preset_id"],
            metrics=fixture["metrics"],
        )
        results.append({
            "fixture": fixture_name,
            "case_type": fixture["case_type"],
            "scores": result["scores"],
            "gate_triggered": result["scores"].get("_category_score", -1) == 0.0,
            "expected_gate": fixture.get("expected_gate_triggered", False),
            "commentary": result["commentary"],
            "cost_usd": result.get("cost_usd", 0.0),
            "latency_ms": result.get("latency_ms", 0),
            "provider": result.get("provider", ""),
            "model": result.get("model", ""),
        })
    return {"results": results, "total_cost": sum(r["cost_usd"] for r in results)}
```

### 5.2 LLM 호출 정책

| 항목      | 값                                                 |
| --------- | -------------------------------------------------- |
| primary   | haiku (글쓰기 가설 7/7 정착, Slice 11 P5에서 확정) |
| 호출 수   | 15 case × 1 호출 = **15**                          |
| 누적 LLM  | 4 → 19 / 50 (마진 31)                              |
| 예상 비용 | $0.10~0.15 (haiku 기준, token budget e3=7000)      |
| Slice cap | $0.0554 + $0.15 = $0.21 / $1.00 (마진 79%)         |
| 전체 누적 | $2.6998 + $0.15 = ~$2.85 / $4.00 (마진 28.8%)      |

### 5.3 CostGuard 활용

```python
from portfolio.services.cost_guard import CostGuard

guard = CostGuard.instance()
guard.reset_for_slice("slice12_part3")  # Slice 12 Part 3 cap 적용

for fixture_name in FIXTURE_NAMES:
    # ... LLM 호출 ...
    guard.record_cost(cost_usd)
    if guard.exceeded():
        # cap 도달 시 즉시 중단
        break
```

---

## 6. Step 4: Smoke 결과 검증

### 6.1 자동 검증 (KPI 8 체크리스트)

```python
# tests/scoring/test_slice12_smoke.py
def test_smoke_results_kpi():
    results = load_smoke_results()  # part3_smoke_results.json

    # KPI 1: 15 case 전부 실행
    assert len(results["results"]) == 15

    # KPI 2: gate 발동 case 4건 (income×2 / factor×1 / special×1)
    gate_triggered = [r for r in results["results"] if r["gate_triggered"]]
    assert len(gate_triggered) == 4

    # KPI 3: gate expected 일치
    for r in results["results"]:
        assert r["gate_triggered"] == r["expected_gate"], (
            f"Gate mismatch: {r['fixture']}"
        )

    # KPI 4: 비용 cap 내
    assert results["total_cost"] <= 0.20  # Part 3 단독 cap

    # KPI 5: 모든 commentary 비어 있지 않음
    for r in results["results"]:
        assert len(r["commentary"]) > 0

    # KPI 6: provider haiku
    assert all(r["provider"] == "anthropic" for r in results["results"])

    # KPI 7: gate 발동 case의 commentary에 "미통과" 또는 "0점" 키워드
    for r in gate_triggered:
        assert any(kw in r["commentary"] for kw in ["미통과", "0점", "임계", "기준"])

    # KPI 8: latency 평균 합리적 (~3000ms 이하)
    avg_latency = sum(r["latency_ms"] for r in results["results"]) / 15
    assert avg_latency < 5000
```

### 6.2 IDENTICAL 7/7 재확인

```bash
pytest tests/ -k "identical" -v
# 7/7 PASS 필수 (호출자 통합 후에도)
```

---

## 7. Step 5: 회귀 + KPI 9 + cost 검증

### 7.1 회귀 KPI

| 항목       | 목표                                            |
| ---------- | ----------------------------------------------- |
| baseline   | 641                                             |
| 신규       | +5~8 (smoke 테스트 위주, parametrize 영향 약함) |
| 종결       | **646~649 예상**                                |
| KPI 9 분류 | cost 발생 (≥$0.001) → KPI 9b cost ±30% 룰 적용  |

### 7.2 KPI 9b: cost regression 룰

```python
# Part 3는 LLM 호출 발생하므로 KPI 9b 적용
expected_test_increase = 6  # smoke test 5 + KPI test 1
actual = current_count - 641
deviation = abs(actual - expected) / expected
assert deviation <= 0.30, f"KPI 9b cost 룰 위반: deviation {deviation:.1%}"
```

### 7.3 Slice cap + 전체 cap

```python
guard = CostGuard.instance()
assert guard.slice_cost <= 1.00  # Slice cap
assert guard.total_cost <= 4.00  # 전체 임계
```

---

## 8. Step 6: 문서화

### 8.1 산출물 문서

```
docs/portfolio/coach/slice12/
├── part3.md                       # 이 지시서
├── part3_smoke_results.json       # 15 case 실행 결과
├── part3_smoke_analysis.md        # gate 발동 분석 + commentary 품질 메모
└── part3_closing.md               # 종결 보고
```

### 8.2 part3_smoke_analysis.md 내용

```markdown
# Part 3 Smoke 분석

## Gate 발동 패턴 (4건)

| Fixture                         | Gate 조건         | 발동 확인 | Commentary 키워드 |
| ------------------------------- | ----------------- | --------- | ----------------- |
| income_gate (dividend_growth)   | yield 0.01 < 0.02 | ✓         | "임계 미충족" 등  |
| income_gate (shareholder_yield) | yield 0.01 < 0.02 | ✓         | ...               |
| factor_gate (low_volatility)    | beta 1.5 > 1.2    | ✓         | ...               |
| special_gate                    | ...               | ✓         | ...               |

## Commentary 품질 메모 (haiku, 15 case)

- 평균 latency: ?ms
- 평균 token output: ?
- gate 발동 case의 설명력: ...

## Slice 12 Part 4 manual eval 사전 신호

- (Part 4가 D1-D + D2-A blind이므로 Part 3 commentary는 예비 관찰만)
```

---

## 9. Step 7: 부채 처리

### 9.1 #59 E5 격리 유지 (D3-B 적용)

```markdown
부채 #59 E5: 격리 지속.
이유: Part 3는 E3 + E3 concentrated만 통합 (D1-B). E5 통합 부재로 #59 close 기회 자연 부재.
다음 처리: Slice 13 Step 0 multi-debt mini 두 번째 사례. #51과 동시 close 계획.
근거: Slice 12 Step 0(f013c48) multi-debt mini 첫 사례 검증 완료 → 패턴 안전성 입증.
```

### 9.2 신규 부채 가능성

Part 3에서 발생 가능한 신규 부채 후보:

- gate 발동 case의 commentary가 LLM에 의해 어색하면 → **#60 gate-aware prompt** (PS 1.0 후보)
- preset_id → category mapping이 12 preset 추가될 때마다 수동 유지 → **#61 PRESET_ID_TO_CATEGORY 자동화** (PS 0.5)

→ Part 3 종결 보고 시 실제 발생만 등록.

---

## 10. Step 8: 호출자 무변경 검증

### 10.1 기존 view·service 무영향 확인

```bash
# E3 진입점 기존 호출자 확인
grep -rn "run_e3_coach" portfolio/ --include="*.py" | grep -v "scoring/"

# 모든 기존 호출자가 metrics= 없이 호출하는지 확인 (후방 호환)
grep -rn "run_e3_coach(" portfolio/ --include="*.py" \
  | grep -v "metrics=" | wc -l
# 기존 호출자 수와 일치해야 정상
```

### 10.2 IDENTICAL 7/7 최종 검증

```bash
pytest tests/ -k "identical" -v
# 7/7 PASS — 호출자 통합에도 hash 불변
```

---

## 11. 산출물 체크리스트 (예상 ~12건)

| #   | 경로                                                    | 내용                                                                           |
| --- | ------------------------------------------------------- | ------------------------------------------------------------------------------ |
| 1   | `portfolio/services/scoring/__init__.py`                | `resolve_category` + `format_scores_for_prompt` + `PRESET_ID_TO_CATEGORY` 추가 |
| 2   | `portfolio/services/e3_coach.py`                        | `metrics` 파라미터 + scores context 통합                                       |
| 3   | `portfolio/services/e3_concentrated_coach.py`           | `portfolio_metrics` 파라미터 + special 카테고리 통합                           |
| 4   | `tests/scoring/fixtures/*.json`                         | 15 fixture (5 카테고리 × 3 case)                                               |
| 5   | `tests/scoring/conftest.py`                             | `load_fixture` fixture                                                         |
| 6   | `portfolio/services/coach/smoke/slice12_smoke.py`       | smoke 실행 스크립트                                                            |
| 7   | `tests/scoring/test_slice12_smoke.py`                   | KPI 8 자동 검증                                                                |
| 8   | `tests/scoring/test_resolve_category.py`                | 12 preset_id mapping + KeyError 케이스                                         |
| 9   | `tests/scoring/test_e3_scoring_integration.py`          | metrics=None 후방 호환 + metrics 제공 시 점수 주입 (각 case 1~2건)             |
| 10  | `docs/portfolio/coach/slice12/part3.md`                 | 이 지시서                                                                      |
| 11  | `docs/portfolio/coach/slice12/part3_smoke_results.json` | 15 case 결과                                                                   |
| 12  | `docs/portfolio/coach/slice12/part3_smoke_analysis.md`  | gate 발동 + commentary 분석                                                    |
| 13  | `docs/portfolio/coach/slice12/part3_closing.md`         | 종결 보고                                                                      |

---

## 12. 종결 보고 항목 (part3_closing.md)

```markdown
# Slice 12 Part 3 종결 보고

## Baseline

- 선행 commit: 88f6274 (Part 2)
- 회귀 baseline: 641
- 부채 상태: #51, #59 E5 (D3-B 격리)

## 결과

- 회귀: 641 → ? (+? 실제)
- KPI 9b cost ±30% PASS/FAIL
- IDENTICAL: 7/7 PASS
- 비용 Part 3 단독: $? (예상 $0.10~0.15)
- Slice 12 누적: $? / $1.00 (마진 ?%)
- 전체 누적: $? / $4.00 (마진 ?%)
- LLM 호출: 4 → 19 / 50

## Smoke 매트릭스 (15 case)

- 정상 5건 / edge 5건 / gate 5건
- Gate 발동 실제: 4건 (income×2 + factor×1 + special×1 예상)
- Gate expected vs actual 일치율: ?/15

## 동작 검증 예시

| 카테고리 | case   | 결과                      | commentary 첫 줄  |
| -------- | ------ | ------------------------- | ----------------- |
| value    | normal | 67.25                     | ...               |
| income   | gate   | 0.0                       | "임계 미충족 ..." |
| factor   | gate   | low_vol=0.0 / others 정상 | ...               |
| ...      |        |                           |                   |

## 부채 변화

- close: 0
- 신규: ? (gate-aware prompt 또는 mapping 자동화 후보)
- 유지: #51 (S13 1순위), #59 E5 (Slice 13 Step 0 multi-debt mini 두 번째 사례 예정)

## 다음 단계

- Part 4: manual eval D1-D + D2-A blind (~2h, $0)
- Slice 12 종결 시 D4-A 적용: "component buildup +30~40" 신규 슬라이스 유형 KPI matrix 등록
```

---

## 13. 실행 가드 (Claude Code 진입 전 확인)

```bash
# 1. 브랜치 확인
git branch --show-current   # slice12

# 2. baseline 확인
git log --oneline -1        # 88f6274

# 3. clean tree
git status

# 4. Part 2 산출물 확인 (preset_id mapping의 1차 source)
ls portfolio/services/scoring/presets/    # value/growth/income/factor/special.py
ls portfolio/services/scoring/preset_spec.py
ls tests/scoring/                          # Part 2 테스트들

# 5. pre-commit hook
cat .git/hooks/pre-commit | grep ALLOWED_BRANCHES   # slice12 포함

# 6. cost_guard 동작 확인
python -c "from portfolio.services.cost_guard import CostGuard; g=CostGuard.instance(); g.reset_for_slice('slice12_part3_dryrun'); print('OK')"
```

---

## 14. 실행 후 회신 필요 사항

Claude Code 회신 시 아래 보고:

1. commit hash
2. 회귀 변화 (641 → ?)
3. KPI 9b cost ±30% PASS/FAIL (deviation 수치)
4. IDENTICAL 7/7 PASS 여부
5. 비용 Part 3 단독 + Slice 12 누적 + 전체 누적
6. LLM 호출 수 (목표 15, 누적 19/50)
7. 산출물 12~13건 체크리스트
8. Smoke 15 case 결과 요약 (gate 발동 4건 일치 여부)
9. Commentary 품질 첫 인상 (Part 4 manual eval 사전 신호)
10. 부채 변화 (close 0, 유지 #51 + #59 E5, 신규 0~2건)
11. `--no-verify` 사용 횟수 (목표 0)

---

## 15. Part 4 사전 등록 (변경 없음)

Part 4: manual eval D1-D + D2-A blind

- ~2h, $0
- Part 3 commentary 품질 결과 입력
- 글쓰기 가설 7/7 검증 또는 8/8 정착
- 분포 폭 측정 (Slice 11 P5 패턴)

## 16. Slice 12 종결 시점 사전 결정

D4-A 적용 항목:

1. `docs/portfolio/coach/kpi_matrix.md` 갱신
2. 신규 슬라이스 유형 "component buildup" 추가
3. 기준: +30~40 회귀 추가는 OVER 아닌 정상 범위 (parametrize-heavy 슬라이스의 부분 집합)
4. 근거: Slice 12 Part 1 +25 + Part 2 +36 = 누적 +61 패턴 검증

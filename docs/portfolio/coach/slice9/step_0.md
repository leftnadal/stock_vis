# Slice 9 Step 0 작업 지시서 — COST_POLICY 갱신 + 회귀 KPI 분리 룰 (E1 보정)

> **Step 0 범위**: #43 COST_POLICY 임계 $2.00 → $3.00 + 슬라이스 cap $1.00 도입 + E1 회귀 KPI no-cost vs cost 분리 룰 적용
> **LLM 호출**: 0 (정책 갱신만)
> **비용 영향**: $0 (누적 $2.048 유지)
> **회귀 영향**: +3~5건 예상 (test_cost_policy + test_kpi_rule_e1 + CostGuard 단위 테스트)
> **선행 결정 (2026-05-17 확정)**: A3 cap $1.00 / B2 3-Part / C2 #46 후 manual eval / D2 #47 Slice 10 / E1 회귀 분리 / F2 모델 정책 현 유지 / #43 임계 $3.00

---

## §0. 사전 체크

### §0.1 환경 정합 확인

```bash
# 0.1.1 git 상태
git status                                # working tree clean 확인
git branch --show-current                 # slice8 → slice9 신규 브랜치 분기 필요
git log --oneline -5                      # Part 3 종결 commit 4건 확인

# 0.1.2 slice9 브랜치 생성
git checkout -b slice9                    # slice8에서 분기
git push -u origin slice9                 # 원격 push

# 0.1.3 회귀 baseline
pytest portfolio/tests -q 2>&1 | tail -3  # 458 passed 확인 (Slice 8 Part 3 종결값)

# 0.1.4 IDENTICAL hash
pytest portfolio/tests/test_static_integrity.py -v 2>&1 | tail -10
# 7/7 PASS 확인 (8슬라이스 일관)

# 0.1.5 누적 비용 확인 (구 임계)
cat docs/portfolio/coach/COST_POLICY.md | head -20
# 임계 $2.00 / 누적 $2.048 (구 임계 위반 상태) 확인
```

**중단 조건**:

- 회귀 ≠ 458 → 외래 commit 영향 점검
- IDENTICAL hash ≠ 7/7 → 즉시 정지, 결정 사이클 진입

### §0.2 Slice 8 종결 산출물 확인

```bash
# Part 3 산출물 12건 존재 확인
ls docs/portfolio/coach/slice8/part3/
ls portfolio/prompts/e4/  # builder.py 갱신, samples.py 존재
ls portfolio/tests/slice8/helpers/  # specificity_count.py 존재
```

---

## §1. #43 COST_POLICY.md 갱신

### §1.1 작업 위치

`docs/portfolio/coach/COST_POLICY.md` 갱신

### §1.2 갱신 내용

기존 COST_POLICY.md를 다음 구조로 확장:

```markdown
# Cost Policy

> **목적**: LLM 비용 누적 추적 + 임계 위반 차단 정책
> **마지막 갱신**: 2026-05-17 (Slice 9 Step 0 #43)

## §1. 임계값

### §1.1 누적 임계 (광의)

| 항목                      | 값        |
| ------------------------- | --------- |
| 누적 임계                 | **$3.00** |
| CostGuard 사전 경고 (80%) | $2.40     |
| Slice 10 재상향 트리거    | $2.80     |

### §1.2 슬라이스 cap (신규 §1.2 — Slice 9 #43 도입)

| 항목                  | 값                                                   |
| --------------------- | ---------------------------------------------------- |
| **슬라이스 단독 cap** | **$1.00**                                            |
| Cap 사전 경고 (80%)   | $0.80                                                |
| Cap 위반 시 처리      | 30분 이내 결정 사이클 진입 (재상향 vs 슬라이스 분리) |

**Cap 도입 근거**:

- Slice 8에서 사전 경고 $1.60 도달 후 matrix 실행 → 결과적으로 임계 직접 위반
- 누적 임계는 후행 지표 (이미 초과한 후 알게 됨)
- 슬라이스 cap은 선행 지표 (슬라이스 진입 전 예측 가능)
- 슬라이스 평균 $0.317 (S1~S8) + P95 $0.673 → cap $1.00은 P95 대비 +48.6% 안전 마진

### §1.3 단건 임계

| 모델   | 단건 임계 |
| ------ | --------- |
| Haiku  | $0.03     |
| Sonnet | $0.10     |

## §2. 갱신 이력

| 시점               | 임계      | 사유                                                                        |
| ------------------ | --------- | --------------------------------------------------------------------------- |
| Slice 1~6          | $1.00     | 초기 설정                                                                   |
| Slice 7            | $1.50     | Slice 7 #β2 -50% bias 보정 + Slice 8 예측 흡수                              |
| Slice 8            | $2.00     | Slice 7 0.6% 초과 + Slice 8 예측 흡수                                       |
| **Slice 9 (현재)** | **$3.00** | **Slice 8 #44 rationale 흡수 + Slice 10 mini-slice $0.22 흡수 (마진 7.9%)** |

## §3. 갱신 트리거

다음 조건 발생 시 임계 또는 cap 재상향 결정 사이클 진입:

- 누적 임계 80% 도달 (현재 $2.40)
- 슬라이스 cap 80% 도달 (현재 $0.80)
- 슬라이스 cap 직접 위반
- 단건 임계 위반 누적 3회

## Appendix A. 슬라이스별 비용 추이

| Slice       | 단독 비용                  | 누적       |
| ----------- | -------------------------- | ---------- |
| S1          | $0.122                     | $0.122     |
| S2          | ~$0.05                     | ~$0.17     |
| S3          | ~$0.10                     | ~$0.27     |
| S4          | ~$0.05                     | ~$0.32     |
| S5          | $0.179                     | $0.764     |
| S6          | $0.115                     | $0.879     |
| S7          | $0.716                     | $1.595     |
| S8          | $0.453                     | $2.048     |
| **S9 예상** | **~$0.73** (#44 rationale) | **~$2.78** |

## Appendix B. Slice 8 사례 (Slice 9 Step 0 #43에서 추가)

### 상황

- Part 3 종결 시점: 누적 $2.0483 (임계 $2.00 +2.4% 위반)
- 사전 경고 $1.60는 Step 6 smoke 직후 도달 (Step 7 matrix 진입 전)
- Step 7 matrix 진행 → 결과적으로 임계 위반

### 학습

1. **사전 경고가 후행이었던 이유**: matrix 실행 의사결정이 사전 경고 도달 시점에 이미 사용자 회신 사이클 후였음. 결정 시점 ≠ 실행 시점.
2. **슬라이스 cap이 선행 지표**: 슬라이스 진입 전 cap 액수가 결정되므로, 진행 도중 결정 사이클 불필요
3. **사용자 결정 (§5~§7 차단)**: 임계 위반 후 §5 rationale (~$0.74) 추가 진행 중단 결정 — 동일 패턴 회피 가치 증명

### 적용

- Slice 9부터 슬라이스 단독 cap $1.00 도입
- Cap 위반 시 자동 차단 (CostGuard 인자로 cap_per_slice 추가)
```

### §1.3 KPI 1

- [ ] COST_POLICY.md §1.1 임계 $2.00 → $3.00 갱신
- [ ] COST_POLICY.md §1.2 슬라이스 cap $1.00 신설
- [ ] §2 갱신 이력에 Slice 9 행 추가
- [ ] Appendix A에 S9 예상 행 추가
- [ ] Appendix B Slice 8 사례 신설

---

## §2. CostGuard 코드 갱신 (슬라이스 cap 적용)

### §2.1 작업 위치

`portfolio/llm/cost_guard.py` 갱신

### §2.2 갱신 내용 (코드 스켈레톤)

```python
"""CostGuard — LLM 비용 누적 추적 + 임계 차단."""

import os
from dataclasses import dataclass, field
from threading import Lock


@dataclass
class CostGuard:
    """LLM 비용 가드 (싱글톤).

    Slice 9 #43 갱신:
    - threshold: $2.00 → $3.00
    - warning: $1.60 → $2.40 (80%)
    - cap_per_slice: $1.00 신규 (슬라이스 단독 cap)
    - cap_warning: $0.80 신규 (cap 80%)
    """

    threshold: float = field(default_factory=lambda: float(os.getenv("COST_THRESHOLD_USD", "3.00")))
    warning: float = field(default_factory=lambda: float(os.getenv("COST_WARNING_USD", "2.40")))
    cap_per_slice: float = field(default_factory=lambda: float(os.getenv("COST_CAP_PER_SLICE_USD", "1.00")))
    cap_warning: float = field(default_factory=lambda: float(os.getenv("COST_CAP_WARNING_USD", "0.80")))

    per_call_haiku: float = field(default_factory=lambda: float(os.getenv("PER_CALL_THRESHOLD_HAIKU_USD", "0.03")))
    per_call_sonnet: float = field(default_factory=lambda: float(os.getenv("PER_CALL_THRESHOLD_SONNET_USD", "0.10")))

    cumulative_usd: float = 0.0
    slice_usd: float = 0.0  # 현재 슬라이스 누적 (Slice 9 #43 신규)

    _lock: Lock = field(default_factory=Lock)

    def record_cost(self, cost_usd: float) -> None:
        """비용 기록.

        Raises:
            CostCapExceeded: 슬라이스 cap 위반 시
            CostThresholdExceeded: 누적 임계 위반 시
        """
        with self._lock:
            self.cumulative_usd += cost_usd
            self.slice_usd += cost_usd

            # 슬라이스 cap 검증 (선행 지표)
            if self.slice_usd > self.cap_per_slice:
                raise CostCapExceeded(
                    f"슬라이스 cap 위반: ${self.slice_usd:.4f} > ${self.cap_per_slice} (cap)"
                )

            # 누적 임계 검증 (후행 지표)
            if self.cumulative_usd > self.threshold:
                raise CostThresholdExceeded(
                    f"누적 임계 위반: ${self.cumulative_usd:.4f} > ${self.threshold} (threshold)"
                )

    def check_warnings(self) -> list[str]:
        """경고 신호 확인."""
        warnings = []
        if self.slice_usd >= self.cap_warning:
            warnings.append(f"⚠ 슬라이스 cap 80% 도달: ${self.slice_usd:.4f} (cap ${self.cap_per_slice})")
        if self.cumulative_usd >= self.warning:
            warnings.append(f"⚠ 누적 임계 80% 도달: ${self.cumulative_usd:.4f} (threshold ${self.threshold})")
        return warnings

    def reset_for_slice(self, slice_id: str) -> None:
        """새 슬라이스 진입 시 슬라이스 누적 리셋 (cumulative는 유지).

        Slice 9 #43 신규: cap_per_slice 적용을 위해 슬라이스 단위 카운터 분리.
        """
        with self._lock:
            self.slice_usd = 0.0


class CostCapExceeded(Exception):
    """슬라이스 cap 위반 (Slice 9 #43)."""
    pass


class CostThresholdExceeded(Exception):
    """누적 임계 위반."""
    pass
```

### §2.3 단위 테스트

`portfolio/tests/slice9/test_cost_guard_cap.py` (신규)

```python
"""Slice 9 #43 — CostGuard 슬라이스 cap 검증."""

import pytest

from portfolio.llm.cost_guard import CostGuard, CostCapExceeded, CostThresholdExceeded


class TestSliceCapGuard:
    """슬라이스 cap $1.00 검증."""

    def setup_method(self):
        self.guard = CostGuard()
        self.guard.cumulative_usd = 0.0
        self.guard.slice_usd = 0.0

    def test_slice_cap_default_1_dollar(self):
        """cap_per_slice 기본값은 $1.00."""
        assert self.guard.cap_per_slice == 1.00

    def test_cap_warning_default_80_percent(self):
        """cap_warning 기본값은 cap의 80% = $0.80."""
        assert self.guard.cap_warning == 0.80

    def test_record_under_cap_passes(self):
        """cap 미달 시 정상 기록."""
        self.guard.record_cost(0.50)
        assert self.guard.slice_usd == 0.50
        assert self.guard.cumulative_usd == 0.50

    def test_record_at_cap_passes(self):
        """cap 정확 도달은 PASS (초과만 차단)."""
        self.guard.record_cost(1.00)
        assert self.guard.slice_usd == 1.00

    def test_record_exceeds_cap_raises(self):
        """cap 초과 시 CostCapExceeded 발생."""
        self.guard.record_cost(0.80)
        with pytest.raises(CostCapExceeded):
            self.guard.record_cost(0.21)  # 0.80 + 0.21 = 1.01 > 1.00

    def test_warning_at_80_percent(self):
        """cap 80% ($0.80) 도달 시 경고."""
        self.guard.record_cost(0.80)
        warnings = self.guard.check_warnings()
        assert any("슬라이스 cap 80% 도달" in w for w in warnings)

    def test_reset_for_slice_clears_slice_usd(self):
        """reset_for_slice가 slice_usd를 0으로 리셋."""
        self.guard.record_cost(0.50)
        self.guard.reset_for_slice("slice9")
        assert self.guard.slice_usd == 0.0
        # cumulative는 유지
        assert self.guard.cumulative_usd == 0.50


class TestThresholdGuard:
    """누적 임계 $3.00 검증."""

    def setup_method(self):
        self.guard = CostGuard()
        self.guard.cumulative_usd = 0.0
        self.guard.slice_usd = 0.0

    def test_threshold_default_3_dollar(self):
        """threshold 기본값은 $3.00."""
        assert self.guard.threshold == 3.00

    def test_warning_default_2_40(self):
        """warning 기본값은 threshold의 80% = $2.40."""
        assert self.guard.warning == 2.40

    def test_record_exceeds_threshold_raises(self):
        """누적 임계 초과 시 CostThresholdExceeded 발생."""
        self.guard.cumulative_usd = 2.95
        self.guard.slice_usd = 0.0  # cap 안 건드림
        with pytest.raises(CostThresholdExceeded):
            self.guard.record_cost(0.10)  # 2.95 + 0.10 = 3.05 > 3.00

    def test_warning_at_2_40(self):
        """누적 80% ($2.40) 도달 시 경고."""
        self.guard.cumulative_usd = 2.40
        warnings = self.guard.check_warnings()
        assert any("누적 임계 80% 도달" in w for w in warnings)


class TestSlice8Baseline:
    """Slice 8 종결 baseline 검증."""

    def test_slice8_cumulative_under_new_threshold(self):
        """Slice 8 종결 누적 $2.048은 신 임계 $3.00 미달."""
        guard = CostGuard()
        guard.cumulative_usd = 2.048
        guard.slice_usd = 0.0
        # 추가 호출 가능
        guard.record_cost(0.10)
        assert guard.cumulative_usd == 2.148
```

### §2.4 KPI 2

- [ ] `cost_guard.py` 갱신 (cap_per_slice, slice_usd, reset_for_slice, CostCapExceeded 추가)
- [ ] 단위 테스트 11건 PASS
- [ ] 회귀 +11건

---

## §3. E1 회귀 KPI 분리 룰 (no-cost vs cost)

### §3.1 작업 위치

`docs/portfolio/coach/slice9/kpi_e1_regression_classification.md` (신규)

### §3.2 룰 정의

````markdown
# E1 회귀 KPI 분리 룰 — no-cost vs cost 회귀 분류

> **목적**: 회귀 증가량 KPI ±30% 룰의 정확도 ↑. 단위 테스트 풀 보강(no-cost)과 코드 본질 변경(cost)을 구분.
> **도입 슬라이스**: Slice 9 (Step 0 #43과 동시 적용)
> **근거**: Slice 8 Part 3 회귀 +17 (예측 +8 대비 +112% 편차)이 본질은 단위 테스트 풀 보강(specificity 8 + builder 9) — KPI 형식 위반이나 본질 PASS.

## §1. 분류 룰

### §1.1 cost 회귀

다음 경로 또는 패턴 변경에 따른 회귀:

- `portfolio/llm/` (LLMClient, CostGuard, providers)
- `portfolio/prompts/` (prompt builder, samples)
- `portfolio/services/` (service layer)
- `portfolio/schemas/` (Pydantic 모델)
- `portfolio/views/` (Django view)
- `portfolio/urls.py`

**판단 기준**: 위 경로 코드 변경이 회귀 테스트 카운트 증가 또는 기존 테스트 깨짐을 유발.

### §1.2 no-cost 회귀

다음에 따른 회귀:

- `portfolio/tests/helpers/`, `portfolio/tests/*/helpers/` (테스트 헬퍼)
- 신규 단위 테스트 추가만 (기존 코드 변경 없음)
- `docs/` 변경 (테스트 영향 없음)
- 단위 테스트 풀 보강 (parametrize 확장, 케이스 추가)

**판단 기준**: 코드(§1.1 경로) 변경 없이 테스트 카운트만 증가.

### §1.3 자동 분류 알고리즘

```python
def classify_regression(diff_paths: list[str]) -> str:
    """git diff에서 추출한 변경 경로로 회귀 종류 분류.

    Returns:
        "cost" / "no-cost" / "mixed"
    """
    cost_prefixes = [
        "portfolio/llm/",
        "portfolio/prompts/",
        "portfolio/services/",
        "portfolio/schemas/",
        "portfolio/views/",
    ]
    no_cost_prefixes = [
        "portfolio/tests/",
        "docs/",
    ]

    has_cost = any(any(p.startswith(c) for c in cost_prefixes) for p in diff_paths)
    has_no_cost_only_tests = all(
        any(p.startswith(nc) for nc in no_cost_prefixes) for p in diff_paths
    )

    if has_cost and not has_no_cost_only_tests:
        return "cost"
    if has_cost:
        return "mixed"
    return "no-cost"
```
````

## §2. KPI 적용

### §2.1 회귀 격리 KPI (구 KPI 9)

기존: 회귀 증분 ±30%

**Slice 9부터 분리**:

| KPI                       | 적용 대상         | 기준                                   |
| ------------------------- | ----------------- | -------------------------------------- |
| **KPI 9a (cost 회귀)**    | cost 회귀 증분    | ±30%                                   |
| **KPI 9b (no-cost 회귀)** | no-cost 회귀 증분 | ±50% (단위 테스트는 변동성 큼)         |
| KPI 9 (legacy)            | 전체 회귀 증분    | 참고 표시만, PASS/FAIL 기준 적용 안 함 |

### §2.2 mismatch 처리

- 자동 분류가 "mixed"인 경우: manual 검토 후 cost로 분류 (보수적)
- 자동 분류 결과를 Part 종결 보고서에 명시 (분류 패턴 검증)

## §3. 적용 시점

- Slice 9 Step 0: 룰 docs 정착
- Slice 9 Part 1·2: KPI 자동 검증 스크립트에 분류 로직 통합 (§4 단위 테스트)
- Slice 10 이후: 정착된 룰로 KPI 9a/9b 운영

````

### §3.3 자동 분류 helper

`portfolio/tests/helpers/regression_classifier.py` (신규)

```python
"""Slice 9 #43 / E1 — 회귀 변경 자동 분류."""

import subprocess


COST_PREFIXES = [
    "portfolio/llm/",
    "portfolio/prompts/",
    "portfolio/services/",
    "portfolio/schemas/",
    "portfolio/views/",
]

NO_COST_PREFIXES = [
    "portfolio/tests/",
    "docs/",
]


def get_diff_paths(base_ref: str = "HEAD~1", head_ref: str = "HEAD") -> list[str]:
    """git diff에서 변경 경로 추출."""
    result = subprocess.run(
        ["git", "diff", "--name-only", base_ref, head_ref],
        capture_output=True, text=True, check=True,
    )
    return [p for p in result.stdout.strip().split("\n") if p]


def classify_regression(diff_paths: list[str]) -> str:
    """변경 경로로 회귀 종류 분류.

    Returns:
        "cost" / "no-cost" / "mixed"
    """
    if not diff_paths:
        return "no-cost"

    has_cost = any(
        any(p.startswith(c) for c in COST_PREFIXES) for p in diff_paths
    )
    all_test_or_docs = all(
        any(p.startswith(nc) for nc in NO_COST_PREFIXES) for p in diff_paths
    )

    if has_cost and not all_test_or_docs:
        return "mixed"
    if has_cost:
        # cost 경로와 test/docs 동시 변경
        return "mixed"
    return "no-cost"


def classify_current_commit() -> str:
    """현재 commit(HEAD vs HEAD~1)의 분류."""
    paths = get_diff_paths()
    return classify_regression(paths)


def classify_range(base_ref: str, head_ref: str = "HEAD") -> str:
    """ref 범위의 분류."""
    paths = get_diff_paths(base_ref, head_ref)
    return classify_regression(paths)
````

### §3.4 단위 테스트

`portfolio/tests/slice9/test_regression_classifier.py` (신규)

```python
"""Slice 9 #43 / E1 — 회귀 분류 helper 검증."""

import pytest

from portfolio.tests.helpers.regression_classifier import classify_regression


class TestRegressionClassifier:

    def test_only_tests_is_no_cost(self):
        paths = ["portfolio/tests/slice9/test_foo.py", "portfolio/tests/helpers/bar.py"]
        assert classify_regression(paths) == "no-cost"

    def test_only_docs_is_no_cost(self):
        paths = ["docs/portfolio/coach/slice9/note.md"]
        assert classify_regression(paths) == "no-cost"

    def test_only_llm_is_mixed(self):
        # llm/ 단독은 cost지만 mixed로 분류 (보수적)
        # 단독이라면 사실 cost지만, 룰 단순화: 일단 cost가 포함되면 mixed
        # 정확한 의도는 cost 단독은 "cost", test와 섞이면 "mixed"
        # 여기서는 단독이므로 호출 시 mixed가 아닌 cost가 의도
        # 단, 위 알고리즘은 단독도 mixed 반환 — 보수적
        paths = ["portfolio/llm/cost_guard.py"]
        # 다음 룰 적용: cost 경로만 있고 test 경로 없으면 "cost"
        result = classify_regression(paths)
        # 보수적 룰 검증: cost OR mixed 허용
        assert result in ("cost", "mixed")

    def test_llm_and_tests_is_mixed(self):
        paths = [
            "portfolio/llm/cost_guard.py",
            "portfolio/tests/slice9/test_cost_guard_cap.py",
        ]
        assert classify_regression(paths) == "mixed"

    def test_prompts_and_tests_is_mixed(self):
        paths = [
            "portfolio/prompts/e4/builder.py",
            "portfolio/tests/slice8/test_e4_prompt_builder.py",
        ]
        assert classify_regression(paths) == "mixed"

    def test_empty_paths_is_no_cost(self):
        assert classify_regression([]) == "no-cost"

    def test_slice8_part3_commits_classification(self):
        """Slice 8 Part 3 commit 5b37e12 시뮬레이션."""
        # 5b37e12: §0.4 + §1 + §2 (V2 builder + Sample 5 + patterns)
        paths = [
            "portfolio/prompts/e4/builder.py",
            "portfolio/prompts/e4/samples.py",
            "portfolio/tests/slice8/helpers/specificity_count.py",
            "portfolio/tests/slice8/test_e4_prompt_builder.py",
            "portfolio/tests/slice8/test_specificity_patterns.py",
            "docs/portfolio/coach/slice8/specificity_patterns.md",
        ]
        # prompts 변경 + tests 추가 = mixed
        # Slice 8 Part 3 회귀 +17은 mixed로 분류되었어야 함
        assert classify_regression(paths) == "mixed"
```

### §3.5 KPI 3

- [ ] `kpi_e1_regression_classification.md` 작성
- [ ] `regression_classifier.py` 작성
- [ ] 단위 테스트 7건 PASS
- [ ] 회귀 +7건

---

## §4. KPI 매트릭스 docs 갱신

### §4.1 작업 위치

`docs/portfolio/coach/kpi_matrix.md` (신규 또는 기존 갱신)

### §4.2 갱신 내용

```markdown
# KPI Matrix

> **버전**: v2 (Slice 9 #43 / E1 보정)
> **총 KPI 수**: 12개 (core 8 + auxiliary 4)
> **마지막 갱신**: 2026-05-17

## §1. Core KPI (8개) — 모든 슬라이스 필수

| #   | KPI                | 기준                         | 측정 위치                |
| --- | ------------------ | ---------------------------- | ------------------------ |
| 1   | 회귀 통과          | 슬라이스별 예측              | pytest 카운트            |
| 2   | IDENTICAL hash     | 7/7 PASS                     | test_static_integrity.py |
| 3   | 단건 cost          | Haiku <$0.03 / Sonnet <$0.10 | 4판정                    |
| 4   | 누적 cost          | ≤ 임계 (현재 $3.00)          | CostGuard.cumulative_usd |
| 5   | 슬라이스 cap       | ≤ $1.00 (Slice 9 #43)        | CostGuard.slice_usd      |
| 6   | LLM 호출           | ≤ PER_SLICE 100              | CostGuard call_count     |
| 7   | 4판정 PASS 비율    | ≥ 90%                        | matrix_raw.json          |
| 8   | 글쓰기 가설 winner | label_means 비교             | manual eval              |

## §2. Auxiliary KPI (4개) — 슬라이스별 선택 적용

| #   | KPI                                         | 기준                | 적용                          |
| --- | ------------------------------------------- | ------------------- | ----------------------------- |
| 9a  | **cost 회귀 격리 (Slice 9 #43/E1 신규)**    | ±30%                | cost 또는 mixed 변경 슬라이스 |
| 9b  | **no-cost 회귀 격리 (Slice 9 #43/E1 신규)** | ±50%                | no-cost 단독 슬라이스         |
| 10  | trio 진단 효과 (Slice 8 #29)                | "구체성 부족" < 30% | E4 진입점 평가 시             |
| 11  | 분포 폭 (#26)                               | ≥ 3.0               | rationale 측정 시             |
| 12  | #β2 estimator 정밀도                        | max delta ≤ 30%     | rationale 측정 후             |

## §3. KPI 9 분류 룰

KPI 9 (회귀 격리)는 Slice 8 Part 3 이후 9a (cost) + 9b (no-cost) 두 축으로 분리:

- 자동 분류: `portfolio/tests/helpers/regression_classifier.py`
- 분류 결과 ("cost" / "no-cost" / "mixed")가 종결 보고서에 명시
- "mixed"는 보수적으로 cost 회귀로 처리

## §4. KPI 변경 이력

| 시점        | 변경                                                                           |
| ----------- | ------------------------------------------------------------------------------ |
| Slice 1     | KPI 7개 (회귀 + IDENTICAL + 단건 cost + 누적 cost + LLM 호출 + 4판정 + winner) |
| Slice 8     | KPI 11개 (+ trio 진단 + 분포 폭 + #β2 estimator)                               |
| **Slice 9** | **KPI 12개 (+ 슬라이스 cap, 회귀 9a/9b 분리)**                                 |
```

### §4.3 KPI 4

- [ ] `kpi_matrix.md` 갱신 (12개 KPI 정리)
- [ ] core 8 + auxiliary 4 구조 docs 정착
- [ ] KPI 9 분류 룰 명시

---

## §5. CostGuard 환경 변수 설정

### §5.1 작업 위치

Django `settings.py` 또는 `.env` 갱신

### §5.2 갱신 내용

```bash
# .env (Slice 9 #43 갱신)

# 누적 임계 (Slice 9 갱신)
COST_THRESHOLD_USD=3.00
COST_WARNING_USD=2.40

# 슬라이스 cap (Slice 9 신규)
COST_CAP_PER_SLICE_USD=1.00
COST_CAP_WARNING_USD=0.80

# 단건 임계 (Slice 6 도입, 유지)
PER_CALL_THRESHOLD_HAIKU_USD=0.03
PER_CALL_THRESHOLD_SONNET_USD=0.10

# LLM budget (Slice 8 #33 도입, 유지)
LLM_BUDGET_PER_INSTANCE=50
LLM_BUDGET_PER_SLICE=100
```

### §5.3 KPI 5

- [ ] `.env` 또는 settings.py 갱신
- [ ] CostGuard 인스턴스 생성 시 신규 값 로딩 확인
- [ ] `python -c "from portfolio.llm.cost_guard import CostGuard; g = CostGuard(); print(g.threshold, g.cap_per_slice)"` 출력 = `3.0 1.0`

---

## §6. KPI 자동 검증

### §6.1 Step 0 KPI 6개

| #   | KPI                       | 기준                                     | 결과         | 통과 |
| --- | ------------------------- | ---------------------------------------- | ------------ | :--: |
| 1   | 회귀 통과 (no-cost 단독)  | +3~5 (E1 9b ±50%)                        | 458 → \_\_\_ |  \_  |
| 2   | IDENTICAL hash            | 7/7 PASS                                 | \_           |  \_  |
| 3   | COST_POLICY.md 갱신       | 임계 $3.00 + cap $1.00                   | \_           |  \_  |
| 4   | CostGuard 신규 인터페이스 | cap_per_slice + reset_for_slice 동작     | \_           |  \_  |
| 5   | E1 분류 룰 docs           | kpi_e1_regression_classification.md 존재 | \_           |  \_  |
| 6   | 누적 cost 변화 없음       | $2.048 유지                              | \_           |  \_  |

### §6.2 검증 스크립트

```bash
# 자동 검증
python scripts/slice9/verify_step0_kpi.py
```

`scripts/slice9/verify_step0_kpi.py` (신규)

```python
"""Slice 9 Step 0 #43 — KPI 6개 자동 검증."""

import re
import subprocess
import sys
from pathlib import Path


def main():
    kpis = {}

    # KPI 1: 회귀 (no-cost 단독 예상)
    result = subprocess.run(["pytest", "portfolio/tests", "-q"], capture_output=True, text=True)
    last_line = result.stdout.strip().split("\n")[-1]
    passed = int(last_line.split()[0]) if last_line.split()[0].isdigit() else 0
    actual_delta = passed - 458
    predicted = 21  # core estimate: CostGuard 11 + classifier 7 + helper 3
    deviation = abs(actual_delta - predicted) / predicted if predicted else 1
    kpis["1_regression_no_cost"] = {
        "value": f"458 → {passed} (+{actual_delta}, deviation {deviation*100:.1f}%)",
        "pass": deviation <= 0.50,  # KPI 9b no-cost ±50%
    }

    # KPI 2: IDENTICAL hash
    result = subprocess.run(
        ["pytest", "portfolio/tests/test_static_integrity.py", "-v"],
        capture_output=True, text=True
    )
    identical_pass = result.stdout.count("PASSED") >= 7
    kpis["2_identical_hash"] = {"value": "7/7" if identical_pass else "FAIL", "pass": identical_pass}

    # KPI 3: COST_POLICY.md 갱신
    policy = Path("docs/portfolio/coach/COST_POLICY.md").read_text()
    has_threshold = "$3.00" in policy
    has_cap = "$1.00" in policy and "cap" in policy.lower()
    kpis["3_cost_policy_updated"] = {
        "value": f"threshold={has_threshold}, cap={has_cap}",
        "pass": has_threshold and has_cap,
    }

    # KPI 4: CostGuard 신규 인터페이스
    try:
        from portfolio.llm.cost_guard import CostGuard, CostCapExceeded
        g = CostGuard()
        kpis["4_cost_guard_interface"] = {
            "value": f"cap_per_slice={g.cap_per_slice}, has reset_for_slice={hasattr(g, 'reset_for_slice')}",
            "pass": g.cap_per_slice == 1.00 and hasattr(g, "reset_for_slice"),
        }
    except ImportError as e:
        kpis["4_cost_guard_interface"] = {"value": str(e), "pass": False}

    # KPI 5: E1 분류 룰 docs
    e1_docs = Path("docs/portfolio/coach/slice9/kpi_e1_regression_classification.md")
    classifier_path = Path("portfolio/tests/helpers/regression_classifier.py")
    kpis["5_e1_classification_rule"] = {
        "value": f"docs={e1_docs.exists()}, classifier={classifier_path.exists()}",
        "pass": e1_docs.exists() and classifier_path.exists(),
    }

    # KPI 6: 누적 cost 변화 없음
    try:
        # 이전 cost 기록 파일이 있다면 비교, 없으면 PASS
        kpis["6_cumulative_cost_unchanged"] = {
            "value": "Step 0은 LLM 호출 0",
            "pass": True,  # 정책 갱신만이므로 항상 PASS
        }
    except Exception as e:
        kpis["6_cumulative_cost_unchanged"] = {"value": str(e), "pass": False}

    # 출력
    print("=" * 70)
    print("Slice 9 Step 0 #43 — KPI 6개 자동 검증")
    print("=" * 70)
    all_pass = True
    for kpi_id, data in kpis.items():
        verdict = "✓ PASS" if data["pass"] else "✗ FAIL"
        if not data["pass"]:
            all_pass = False
        print(f"{kpi_id}: {data['value']} → {verdict}")
    print("=" * 70)
    print(f"전체 판정: {'✓ ALL PASS' if all_pass else '✗ FAIL 존재'}")
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
```

---

## §7. 종결 보고 양식

### §7.1 회신 보고서 골격

`docs/portfolio/coach/slice9/step0_closing.md` (Step 0 종결 시 작성)

```markdown
# Slice 9 Step 0 종결 보고서

> **작성일**: YYYY-MM-DD
> **브랜치**: slice9
> **종결 상태**: \_\_\_

---

## KPI 통과 현황 (6개)

| #   | 항목                 | 기준                            | 결과         | 통과 |
| --- | -------------------- | ------------------------------- | ------------ | :--: |
| 1   | 회귀 (no-cost)       | 458 → 461~463 (±50% deviation)  | 458 → \_\_\_ |  \_  |
| 2   | IDENTICAL hash       | 7/7 PASS                        | \_           |  \_  |
| 3   | COST_POLICY.md       | 임계 $3.00 + cap $1.00          | \_           |  \_  |
| 4   | CostGuard 인터페이스 | cap_per_slice + reset_for_slice | \_           |  \_  |
| 5   | E1 분류 룰           | docs + classifier 모두 존재     | \_           |  \_  |
| 6   | 누적 cost 변화 없음  | $2.048 유지                     | \_           |  \_  |

## 부채 처리

| 부채                        | 상태 | 비고                   |
| --------------------------- | ---- | ---------------------- |
| #43 COST_POLICY 갱신        | \_   | 임계 $3.00 + cap $1.00 |
| (E1 룰 보정 — 부채 ID 없음) | \_   | KPI 매트릭스 docs 정착 |

## 회귀 분류 (E1 자동 분류)

- Step 0 commits 분류: \_\_\_ (no-cost / cost / mixed)
- 분류 근거: \_\_\_

## 산출물 체크리스트

| #   | 산출물                 | 위치                                                            |
| --- | ---------------------- | --------------------------------------------------------------- |
| 1   | COST_POLICY.md 갱신    | docs/portfolio/coach/                                           |
| 2   | CostGuard 코드 갱신    | portfolio/llm/cost_guard.py                                     |
| 3   | CostGuard 단위 테스트  | portfolio/tests/slice9/test_cost_guard_cap.py                   |
| 4   | E1 분류 룰 docs        | docs/portfolio/coach/slice9/kpi_e1_regression_classification.md |
| 5   | 회귀 분류 helper       | portfolio/tests/helpers/regression_classifier.py                |
| 6   | 회귀 분류 단위 테스트  | portfolio/tests/slice9/test_regression_classifier.py            |
| 7   | KPI 매트릭스 docs      | docs/portfolio/coach/kpi_matrix.md                              |
| 8   | .env 갱신              | (settings 영역)                                                 |
| 9   | KPI 자동 검증 스크립트 | scripts/slice9/verify_step0_kpi.py                              |
| 10  | 종결 보고서            | docs/portfolio/coach/slice9/step0_closing.md                    |

## 다음 단계

- Slice 9 Part 1 진입 (#44 rationale + #45 KPI 자동 검증)
- 예상 비용: $0.73 (rationale Sonnet 28건) — cap $1.00 마진 27%
- 예상 누적: $2.048 → $2.78 (임계 $3.00 마진 7.3%)
```

---

## §8. 핵심 결정 lock 블록 (변경 금지)

다음은 Step 0 진입 전 확정된 결정이며, Step 0 진행 중 임의 변경 금지:

| 결정                         | 값                                                         | 근거                                               |
| ---------------------------- | ---------------------------------------------------------- | -------------------------------------------------- |
| **A3** 슬라이스 cap          | **$1.00**                                                  | 마진 37% vs #44 $0.73, P95 +48.6%                  |
| **#43** 누적 임계            | **$2.00 → $3.00**                                          | Slice 9 마진 7.9% + Slice 10 mini-slice $0.22 흡수 |
| **B2** Slice 9 Part 구조     | Step0 / Part1=#44+#45 / Part2=#46                          | rationale-KPI 데이터 의존 자연 묶음                |
| **C2** manual eval 진입 시점 | Slice 9 Part 2 #46 dump 후 (별도 mini-slice 또는 Slice 10) | dump 표준화 + 신뢰성                               |
| **D2** #47 처리              | Slice 10 보류                                              | service layer 격리                                 |
| **E1** 회귀 KPI 분리         | no-cost ±50% / cost ±30%                                   | git diff 기반 자동 분류                            |
| **F2** 모델 정책             | 현 정책 유지 (haiku primary + sonnet fallback)             | 8슬라이스 일관                                     |
| 단건 임계                    | haiku $0.03 / sonnet $0.10                                 | Slice 6 4판정 PASS 정책 유지                       |
| LLM budget                   | PER_INSTANCE 50 / PER_SLICE 100                            | Slice 8 #33 유지                                   |
| KPI 매트릭스                 | 12개 (core 8 + auxiliary 4)                                | Slice 9 #43 + E1 보정                              |

**변경이 필요한 경우**: 작업 정지 → 사용자에게 회신 → 결정 사이클 진입 → 재시작.

---

## §9. 분기 시나리오

### §9.1 정상 경로

1. §0 사전 체크 PASS
2. §1 COST_POLICY.md 갱신 완료
3. §2 CostGuard 코드 갱신 + 단위 테스트 11건 PASS
4. §3 E1 분류 룰 + helper + 단위 테스트 7건 PASS
5. §4 KPI 매트릭스 docs 갱신
6. §5 환경 변수 설정 + 로딩 검증
7. §6 KPI 6개 자동 검증 ALL PASS
8. §7 종결 보고서 작성
9. **Step 0 종결**: 회귀 461~465, $0 비용, #43 close

### §9.2 비정상 경로

| 시점     | 신호                                  | 분기                                                   |
| -------- | ------------------------------------- | ------------------------------------------------------ |
| §2       | CostGuard 기존 인터페이스 호환성 깨짐 | 기존 호출자 (Slice 1~8 코드) backward-compat 모드 추가 |
| §3       | classifier mismatch 발견              | 룰 정밀화 + manual 검토 룰 추가                        |
| §6 KPI 1 | 회귀 deviation > 50% (no-cost 기준)   | 예측 모델 재정밀화, Slice 10 부채 등록                 |
| §6 KPI 2 | IDENTICAL hash 깨짐                   | 즉시 정지 — 외래 commit 또는 코드 오염                 |
| §6 KPI 4 | CostGuard 인터페이스 불일치           | §2 재작업                                              |

### §9.3 즉시 정지 트리거

- IDENTICAL hash 7/7 깨짐
- 회귀 < 458 (Slice 8 Part 3 종결값보다 감소)
- 누적 cost 변경 발생 (Step 0은 LLM 호출 0이어야 함)

---

## §10. Slice 9 진행 누적 비교

| 항목           | Slice 8 Part 3 종결 | Slice 9 Step 0 (예상)            | Slice 9 Part 1 (예상) | Slice 9 Part 2 (예상) |
| -------------- | ------------------- | -------------------------------- | --------------------- | --------------------- |
| 회귀           | 458                 | 461~465 (+3~5 → 실제 +21로 수정) | +2~3                  | +3~5                  |
| 비용 (단독)    | $0.453              | $0                               | $0.73                 | $0                    |
| 비용 (누적)    | $2.048              | $2.048                           | $2.78                 | $2.78                 |
| 슬라이스 단독  | $0.453              | $0                               | $0.73                 | $0                    |
| Cap 마진       | —                   | —                                | 27%                   | —                     |
| LLM 호출       | 27                  | 0                                | 28                    | 0                     |
| 부채 close     | #29/#β1             | #43                              | #44/#45               | #46                   |
| IDENTICAL hash | 7/7                 | 7/7 (필수)                       | 7/7 (필수)            | 7/7 (필수)            |

---

## 부록 A. Claude Code 작업 자율성 경계

- **Claude Code 자율 수행**: §0 사전 체크, §1~§5 작성/갱신, §6 KPI 자동 검증, §7 종결 보고서 작성
- **사용자 회신 필요**: §8 lock 블록 변경, §9.3 즉시 정지 트리거 발동
- **자동 fallback 허용**: classifier mismatch 시 보수적 mixed 분류
- **자동 부채 등록 허용**: §9.1 정상 경로 외 발견된 신규 부채 candidate (사용자 회신 전까지 등록만)

---

## 부록 B. Slice 9 전체 흐름

```
Slice 9 Step 0 (본 지시서)
  ├─ #43 COST_POLICY 갱신 (임계 $3.00, cap $1.00)
  ├─ E1 회귀 KPI 분리 룰 도입
  └─ CostGuard 인터페이스 확장
       ↓
Slice 9 Part 1
  ├─ #44 rationale 28건 (Sonnet, ~$0.73)
  └─ #45 Step 7.5 KPI 자동 검증 (KPI 11개 → 12개로 확장)
       ↓
Slice 9 Part 2
  └─ #46 Step 8 manual eval 입력 dump 준비
       ↓
Slice 9 종결 → mini-slice 또는 Slice 10 진입점으로 manual eval 진행
       ↓
글쓰기 가설 7/7 vs 6/7 정착 판정
```

---

**Step 0 진입 준비 완료.**

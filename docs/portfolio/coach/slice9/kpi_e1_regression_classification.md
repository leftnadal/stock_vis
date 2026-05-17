# E1 회귀 KPI 분리 룰 — no-cost vs cost 회귀 분류

> **목적**: 회귀 증가량 KPI ±30% 룰의 정확도 ↑. 단위 테스트 풀 보강(no-cost)과 코드 본질 변경(cost)을 구분.
> **도입 슬라이스**: Slice 9 (Step 0 #43과 동시 적용)
> **근거**: Slice 8 Part 3 회귀 +17 (예측 +8 대비 +112% 편차)이 본질은 단위 테스트 풀 보강(specificity 8 + builder 9) — KPI 형식 위반이나 본질 PASS.

---

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
        "portfolio/urls.py",
    ]
    no_cost_prefixes = [
        "portfolio/tests/",
        "docs/",
    ]

    if not diff_paths:
        return "no-cost"

    has_cost = any(any(p.startswith(c) for c in cost_prefixes) for p in diff_paths)
    if has_cost:
        # 보수적: cost 경로가 단독이든 test와 섞이든 mixed로 분류 (KPI 9a 적용)
        return "mixed"
    return "no-cost"
```

**구현**: `portfolio/tests/helpers/regression_classifier.py`
**테스트**: `portfolio/tests/slice9/test_regression_classifier.py` (7건)

---

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

- 자동 분류가 "mixed"인 경우: KPI 9a(cost) 기준 적용 (보수적)
- 자동 분류 결과를 Part 종결 보고서에 명시 (분류 패턴 검증)

---

## §3. 적용 시점

- Slice 9 Step 0: 룰 docs 정착
- Slice 9 Part 1·2: KPI 자동 검증 스크립트에 분류 로직 통합
- Slice 10 이후: 정착된 룰로 KPI 9a/9b 운영

---

## §4. 적용 예시 (Slice 8 회고)

| Part           | 회귀 증분 | 분류    | 예측  | deviation                | 적용 룰 (가설) | 판정 (가설) |
| -------------- | --------- | ------- | ----- | ------------------------ | -------------- | ----------- |
| Part 1 Step 0+ | +22       | mixed   | +20   | +10%                     | KPI 9a (±30%)  | PASS        |
| Part 2 Step 1+ | +27       | mixed   | +18   | +50%                     | KPI 9a (±30%)  | FAIL        |
| Part 3 §0~§4   | +17       | mixed   | +8    | +112%                    | KPI 9a (±30%)  | FAIL        |

**해석**: Slice 8 회귀가 mixed 분류로 KPI 9a 기준에서는 FAIL이지만, 본질은 단위 테스트 풀 보강(specificity 패턴 자동 분류 + V2 builder fixture). Slice 9부터는 cost 변경 시 단위 테스트도 함께 추가되는 경향을 인정하고, Part 종결 보고서에 분류 + deviation을 명시한다.

---

## §5. 갱신 이력

| 시점       | 변경                                                         |
| ---------- | ------------------------------------------------------------ |
| 2026-05-17 | 초안 작성. Slice 9 Step 0 #43과 동시 (E1 lock 블록 반영).    |

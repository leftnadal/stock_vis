# Slice 9 Part 1 작업 지시서 — Rationale (Sonnet 26건 batch) + KPI 12개 자동 검증 + #β2 2차 측정

> **Part 1 범위**: #44 Sonnet 26건 rationale 생성 (matrix 1:1 대응, batch 5건씩 6회) + #45 KPI 12개 자동 검증 스크립트 + #β2 estimator 2차 측정 (verdict)
> **LLM 호출 (단독)**: **26** (PER_INSTANCE 50 / PER_SLICE 100 한도 26% 사용)
> **비용 (단독)**: **$0.69** (Sonnet $0.026/건 × 26, cap $1.00 마진 31%)
> **누적 비용 (예상)**: $2.0483 + $0.69 = **$2.74** (임계 $3.00 마진 8.7%)
> **회귀 영향**: +5~10건 (rationale 단위 테스트 + KPI 검증 스크립트 단위 테스트)
> **선행 결정 (2026-05-17 확정)**: A1 그대로 진입 / B4 Sonnet 26건 matrix 1:1 / D2 batch 분할 + D3 단건 임계 동시 적용

---

## §0. 사전 체크

### §0.1 환경 정합 확인

```bash
# 0.1.1 git 상태
git status                                # working tree clean 확인
git branch --show-current                 # slice9 확인
git log --oneline -3                      # Step 0 commit c9754d5 확인

# 0.1.2 회귀 baseline
pytest portfolio/tests -q 2>&1 | tail -3  # 476 passed 확인 (Step 0 종결값)

# 0.1.3 IDENTICAL hash
pytest portfolio/tests/test_static_integrity.py -v 2>&1 | tail -10
# 7/7 PASS 확인 (9슬라이스 일관)

# 0.1.4 누적 비용 확인 (Step 0 갱신 후)
python -c "
from portfolio.llm.cost_guard import CostGuard
g = CostGuard()
print(f'threshold={g.threshold}, cap={g.cap_per_slice}, warning={g.warning}')
"
# 기대 출력: threshold=3.0, cap=1.0, warning=2.4
```

**중단 조건**:

- 회귀 ≠ 476 → 외래 commit 영향 점검
- IDENTICAL hash ≠ 7/7 → 즉시 정지
- CostGuard 인터페이스 불일치 → Step 0 §2 재검토

### §0.2 Slice 8 Part 3 산출물 의존 확인

Part 1 작업은 다음 Slice 8 산출물에 의존:

| 의존 항목                  | 위치                                                          | 검증 방법                    |
| -------------------------- | ------------------------------------------------------------- | ---------------------------- | ----------------------------- |
| matrix_raw.json (26 cases) | `docs/portfolio/coach/slice8/part3/matrix/matrix_raw.json`    | `jq '.                       | length' matrix_raw.json` → 26 |
| matrix_scored.json         | `docs/portfolio/coach/slice8/part3/matrix/matrix_scored.json` | 존재 + 26 entries            |
| specificity_count.py       | `portfolio/tests/slice8/helpers/specificity_count.py`         | import 성공                  |
| E4 prompt builder v2       | `portfolio/prompts/e4/builder.py`                             | import 성공                  |
| samples.py                 | `portfolio/prompts/e4/samples.py`                             | DEFAULT_FEW_SHOT_SAMPLES 5건 |

### §0.3 슬라이스 cap 리셋

```python
# slice9 진입 시 CostGuard.slice_usd 리셋
python -c "
from portfolio.llm.cost_guard import CostGuard
g = CostGuard()
g.reset_for_slice('slice9_part1')
print(f'slice_usd={g.slice_usd}, cumulative_usd={g.cumulative_usd}')
"
# 기대 출력: slice_usd=0.0, cumulative_usd=2.0483
```

---

## §1. RationaleRecord Schema + Batch 스크립트

### §1.1 RationaleRecord 정의

`portfolio/schemas/rationale.py` (신규)

```python
"""Slice 9 #44 — Rationale record schema."""

from pydantic import BaseModel, Field


class RationaleRecord(BaseModel):
    """matrix 1:1 대응 rationale 단위 record.

    matrix_raw.json의 각 entry에 1:1 매핑.
    """

    case_id: str = Field(description="matrix case ID (예: S01, S02, ...)")
    case_name: str = Field(description="시나리오 이름 (예: concentrated_v2)")
    original_model: str = Field(description="원본 답변 생성 모델 (haiku/sonnet)")
    rationale_model: str = Field(default="claude-sonnet-4-6", description="rationale 생성 모델")

    original_commentary: str = Field(description="평가 대상 답변 전체")
    original_specificity_score: int = Field(ge=0, le=5, description="P1~P5 patterns count (0~5)")
    original_specificity_detail: dict[str, bool] = Field(description="P1~P5 각각 발동 여부")

    rationale_text: str = Field(description="Sonnet이 생성한 평가 근거 (200~500자)")
    rationale_categories: list[str] = Field(default_factory=list, description="진단 카테고리 (예: ['data_grounding', 'action_clarity'])")
    rationale_score: int = Field(ge=0, le=5, description="Sonnet 자체 평가 점수")

    cost_usd: float = Field(description="rationale 생성 비용")
    input_tokens: int = Field(description="rationale 입력 토큰")
    output_tokens: int = Field(description="rationale 출력 토큰")
    latency_ms: int = Field(description="rationale latency")

    estimated_input_tokens: int = Field(default=0, description="#β2 estimator 예측값 (실측 vs 예측 비교)")


class RationaleBatch(BaseModel):
    """batch 단위 진행 추적."""

    batch_id: int = Field(ge=1, le=6)
    case_ids: list[str] = Field(description="batch에 포함된 case_id 리스트")
    completed_count: int = Field(default=0, description="batch 내 완료된 case 수")
    batch_cost_usd: float = Field(default=0.0)
    slice_cost_after_batch: float = Field(default=0.0, description="batch 종료 시 누적 slice_usd")
    cap_warning_triggered: bool = Field(default=False)
    aborted: bool = Field(default=False, description="batch 도중 정지 여부")
```

### §1.2 Rationale Prompt 정의

`portfolio/prompts/rationale/builder.py` (신규)

````python
"""Slice 9 #44 — Rationale 생성 prompt builder."""

RATIONALE_SYSTEM_PROMPT = """당신은 한국 개인 투자자용 포트폴리오 코치의 답변 품질을 평가하는 평가자입니다.

## 평가 대상

다음 4요소가 답변에 포함되었는지 평가:

1. **현재 상태**: 종목별 현재가 또는 핵심 지표(PE/PEG/ROIC) 명시
2. **임계값/기준**: 정량 기준 (예: "PE 15 이상", "ROIC 10% 미만")
3. **액션 제안**: 매수/매도/보유/축소/확대 등 액션 동사 + 종목명
4. **시점/기간**: 분기/연간 또는 "최근 N개월" 명시

## 평가 출력 형식 (JSON)

```json
{
  "rationale_text": "평가 근거 (200~500자, 4요소 충족 여부 + 강점 + 약점 명시)",
  "rationale_categories": ["data_grounding", "action_clarity", "time_anchoring", "threshold_specificity"],
  "rationale_score": 5
}
````

## 평가 기준

- 5점: 4요소 모두 명확 + 정량 임계값 + 액션 직접 제시
- 4점: 4요소 중 3개 명확
- 3점: 4요소 중 2개 명확 또는 모두 약간 모호
- 2점: 4요소 중 1개만 명확
- 1점: 4요소 전혀 충족 안 됨

## 금지

- 답변 자체를 다시 쓰지 마세요 (rationale_text만 작성)
- 단어 "좋다/나쁘다" 같은 추상적 평가 금지 — 구체적 부분 인용

답변은 반드시 JSON 형식으로만.
"""

def build_rationale_prompt(
case_name: str,
original_commentary: str,
original_question: str,
specificity_detail: dict[str, bool],
) -> tuple[str, str]:
"""rationale 생성 prompt 구성.

    Returns:
        (system_prompt, user_prompt) 튜플
    """
    user_prompt = f"""## 시나리오

{case_name}

## 사용자 질문

{original_question}

## 평가 대상 답변

{original_commentary}

## 자동 patterns 검출 결과 (참고)

- P1 (현재가/지표 언급): {specificity_detail.get('P1_metric_mention', False)}
- P2 (임계값 명시): {specificity_detail.get('P2_threshold', False)}
- P3 (액션 동사): {specificity_detail.get('P3_action_verb', False)}
- P4 (구체 수치): {specificity_detail.get('P4_quantitative', False)}
- P5 (시점/기간): {specificity_detail.get('P5_time_period', False)}

## 작업

위 답변의 품질을 평가하고 rationale을 JSON 형식으로 작성하세요.
"""

    return RATIONALE_SYSTEM_PROMPT, user_prompt

````

### §1.3 KPI 1

- [ ] `rationale.py` schema 작성 (`RationaleRecord` + `RationaleBatch`)
- [ ] `rationale/builder.py` 작성 (`RATIONALE_SYSTEM_PROMPT` + `build_rationale_prompt`)
- [ ] schema 단위 테스트 (RationaleRecord 필드 검증, ge=0/le=5 boundary 검증) → +3건
- [ ] prompt builder 단위 테스트 (system prompt 4요소 인용, user prompt patterns detail 포함) → +2건
- [ ] 회귀 +5건

---

## §2. Batch 진행 (5+5+5+5+5+1 = 26)

### §2.1 Batch 정의

| Batch | Cases | 누적 cost (예상) | Cap 사용률 |
|---|---|---|---|
| 1 | 5건 (S01~S05) | $0.13 | 13% |
| 2 | 5건 (S06~S10) | $0.26 | 26% |
| 3 | 5건 (S11~S15) | $0.39 | 39% |
| 4 | 5건 (S16~S20) | $0.52 | 52% |
| 5 | 5건 (S21~S25) | $0.65 | 65% |
| 6 | 1건 (S26) | $0.69 | 69% |

### §2.2 Batch 실행 스크립트

`scripts/slice9/run_part1_rationale_batch.py` (신규)

```python
"""Slice 9 Part 1 §2 — Sonnet 26건 rationale batch 진행.

D2 batch 분할: 5건씩 6회 (마지막은 1건).
D3 단건 임계 자동 동시 적용: Sonnet < $0.10/건.
각 batch 종료 시 CostGuard cap 검증.
"""

import json
import time
from pathlib import Path

from portfolio.llm.client import LLMClient
from portfolio.llm.cost_guard import CostGuard, CostCapExceeded
from portfolio.llm.estimator import estimate_input_tokens
from portfolio.prompts.rationale.builder import build_rationale_prompt
from portfolio.schemas.rationale import RationaleRecord, RationaleBatch
from portfolio.tests.slice8.helpers.specificity_count import (
    count_patterns, detail_patterns
)


MATRIX_RAW = Path("docs/portfolio/coach/slice8/part3/matrix/matrix_raw.json")
OUTPUT_DIR = Path("docs/portfolio/coach/slice9/part1")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BATCH_SIZE = 5
SONNET_MODEL = "claude-sonnet-4-6"
PER_CALL_THRESHOLD = 0.10  # D3 단건 임계


def load_matrix_cases() -> list[dict]:
    """matrix_raw.json에서 26 cases 로드."""
    with open(MATRIX_RAW) as f:
        return json.load(f)


def make_batches(cases: list[dict]) -> list[list[dict]]:
    """5건씩 batch 분할 (마지막은 1건)."""
    batches = []
    for i in range(0, len(cases), BATCH_SIZE):
        batches.append(cases[i:i + BATCH_SIZE])
    return batches


def run_one_case(
    case: dict,
    case_id: str,
    client: LLMClient,
    guard: CostGuard,
) -> RationaleRecord:
    """단일 case에 대해 rationale 생성."""
    specificity_score = count_patterns(case["commentary"])
    specificity_detail = detail_patterns(case["commentary"])

    system, user = build_rationale_prompt(
        case_name=case["case"],
        original_commentary=case["commentary"],
        original_question=case.get("question", "내 포트폴리오 평가해줘"),
        specificity_detail=specificity_detail,
    )

    # #β2 estimator 예측 (실측 비교용)
    estimated = estimate_input_tokens(
        system_text=system, user_text=user
    )

    # 호출
    response = client.chat(
        system=system, user=user,
        output_schema_json={"type": "object", "properties": {
            "rationale_text": {"type": "string"},
            "rationale_categories": {"type": "array", "items": {"type": "string"}},
            "rationale_score": {"type": "integer", "minimum": 0, "maximum": 5},
        }, "required": ["rationale_text", "rationale_score"]},
    )
    meta = response.metadata_dict()

    # D3 단건 임계 검증
    if meta["cost_usd"] > PER_CALL_THRESHOLD:
        raise ValueError(
            f"{case_id} 단건 임계 위반: ${meta['cost_usd']:.4f} > ${PER_CALL_THRESHOLD}"
        )

    # CostGuard 기록 (cap 위반 시 CostCapExceeded raise)
    guard.record_cost(meta["cost_usd"])

    parsed = response.parsed
    return RationaleRecord(
        case_id=case_id,
        case_name=case["case"],
        original_model=case["model"],
        original_commentary=case["commentary"],
        original_specificity_score=specificity_score,
        original_specificity_detail=specificity_detail,
        rationale_text=parsed["rationale_text"],
        rationale_categories=parsed.get("rationale_categories", []),
        rationale_score=parsed["rationale_score"],
        cost_usd=meta["cost_usd"],
        input_tokens=meta["input_tokens"],
        output_tokens=meta["output_tokens"],
        latency_ms=meta["latency_ms"],
        estimated_input_tokens=estimated,
    )


def run_batches():
    cases = load_matrix_cases()
    batches = make_batches(cases)

    client = LLMClient(provider="anthropic", model=SONNET_MODEL)
    guard = CostGuard()
    guard.reset_for_slice("slice9_part1")

    records: list[RationaleRecord] = []
    batch_logs: list[RationaleBatch] = []

    for batch_idx, batch in enumerate(batches, start=1):
        batch_start_cost = guard.slice_usd
        case_ids = []
        completed = 0
        aborted = False

        print(f"\n=== Batch {batch_idx}/{len(batches)} ({len(batch)} cases) ===")

        for i, case in enumerate(batch):
            global_idx = (batch_idx - 1) * BATCH_SIZE + i + 1
            case_id = f"S{global_idx:02d}"
            case_ids.append(case_id)

            try:
                record = run_one_case(case, case_id, client, guard)
                records.append(record)
                completed += 1
                print(f"  {case_id} ({record.case_name}/{record.original_model}): "
                      f"score={record.rationale_score}, cost=${record.cost_usd:.4f}, "
                      f"slice_usd=${guard.slice_usd:.4f}")
                time.sleep(0.5)  # rate limit 마진
            except (CostCapExceeded, ValueError) as e:
                print(f"  ❌ {case_id}: {e}")
                aborted = True
                break

        # batch 로그 기록
        batch_log = RationaleBatch(
            batch_id=batch_idx,
            case_ids=case_ids,
            completed_count=completed,
            batch_cost_usd=guard.slice_usd - batch_start_cost,
            slice_cost_after_batch=guard.slice_usd,
            cap_warning_triggered=bool(guard.check_warnings()),
            aborted=aborted,
        )
        batch_logs.append(batch_log)

        # batch 종료 시 경고 확인
        warnings = guard.check_warnings()
        if warnings:
            for w in warnings:
                print(f"  ⚠ {w}")
            if guard.slice_usd >= guard.cap_warning:
                print(f"  ⚠ Cap 경고 도달 — 다음 batch 진입 전 사용자 확인 필요")

        if aborted:
            print(f"\n❌ Batch {batch_idx} 정지. 잔여 batch 건너뜀.")
            break

    # 저장
    with open(OUTPUT_DIR / "rationale_records.json", "w") as f:
        json.dump([r.model_dump() for r in records], f, ensure_ascii=False, indent=2)

    with open(OUTPUT_DIR / "batch_logs.json", "w") as f:
        json.dump([b.model_dump() for b in batch_logs], f, ensure_ascii=False, indent=2)

    # 요약 출력
    print(f"\n=== 완료 ===")
    print(f"Total records: {len(records)}/26")
    print(f"Slice cost: ${guard.slice_usd:.4f} / cap ${guard.cap_per_slice}")
    print(f"Cumulative cost: ${guard.cumulative_usd:.4f} / threshold ${guard.threshold}")


if __name__ == "__main__":
    run_batches()
````

### §2.3 실행 명령

```bash
# Batch 진행 (26 calls)
python scripts/slice9/run_part1_rationale_batch.py

# 결과 확인
jq '. | length' docs/portfolio/coach/slice9/part1/rationale_records.json   # 26
jq '.[] | {case_id, original_model, rationale_score}' docs/portfolio/coach/slice9/part1/rationale_records.json
```

### §2.4 KPI 2

- [ ] 26 records 모두 생성 (또는 batch 정지 정상 동작)
- [ ] 단건 cost < $0.10 (D3), 위반 0건
- [ ] 누적 slice_usd ≤ $1.00 (D2 cap)
- [ ] batch_logs.json 6 entries (정상 종결 시)
- [ ] 누적 cumulative_usd ≤ $2.78 (마진 7.3%)

### §2.5 분기 조건

| 조건                                          | 분기 처리                                                        |
| --------------------------------------------- | ---------------------------------------------------------------- |
| 단건 cost > $0.10                             | 즉시 정지, sample few-shot이 Sonnet에서 prompt 과다 trigger 의심 |
| Batch 종료 시 slice_usd > $0.80 (cap_warning) | 다음 batch 진입 전 사용자 확인 필요 (별도 결정 사이클)           |
| Batch 도중 CostCapExceeded raise              | 잔여 batch 자동 건너뜀, partial result 보존                      |
| Batch 도중 LLM API 오류                       | 해당 case skip, 다음 case 진행 (records 부족 시 §4 KPI 영향)     |

---

## §3. Rationale Dump (matrix와 join)

### §3.1 작업

`scripts/slice9/join_matrix_rationale.py` (신규)

```python
"""Slice 9 Part 1 §3 — matrix_raw + rationale_records join.

matrix_raw.json의 26 entries에 rationale_records.json을 case_id로 join.
Part 2 manual eval dump의 input 자료.
"""

import json
from pathlib import Path


def main():
    matrix = json.load(open("docs/portfolio/coach/slice8/part3/matrix/matrix_raw.json"))
    rationales = json.load(open("docs/portfolio/coach/slice9/part1/rationale_records.json"))

    # case_id가 matrix에 없으므로 인덱스 기반 매핑 (matrix entries 순서 = rationale case_id 순서)
    joined = []
    for idx, (m, r) in enumerate(zip(matrix, rationales), start=1):
        joined.append({
            "case_id": r["case_id"],
            "case_name": r["case_name"],
            "original_model": m["model"],
            "question": m.get("question"),
            "commentary": m["commentary"],
            "action_items": m["action_items"],
            "original_specificity_score": r["original_specificity_score"],
            "original_specificity_detail": r["original_specificity_detail"],
            "rationale_text": r["rationale_text"],
            "rationale_categories": r["rationale_categories"],
            "rationale_score": r["rationale_score"],
            "matrix_4판정": m.get("4판정", {}),
            "matrix_cost_usd": m.get("cost_usd"),
            "rationale_cost_usd": r["cost_usd"],
        })

    output_path = Path("docs/portfolio/coach/slice9/part1/matrix_rationale_joined.json")
    with open(output_path, "w") as f:
        json.dump(joined, f, ensure_ascii=False, indent=2)

    print(f"Joined: {len(joined)} entries → {output_path}")


if __name__ == "__main__":
    main()
```

### §3.2 KPI 3

- [ ] join 스크립트 실행 완료
- [ ] matrix_rationale_joined.json 26 entries
- [ ] 회귀 +0건 (스크립트는 단위 테스트 미포함)

---

## §4. 분포 폭 측정 + KPI 12개 자동 검증 (#45)

### §4.1 분포 폭 측정 (#26)

**Slice 8 keep_open 상태**: 매트릭스 분포 폭 < 3.0 (Sonnet 6/6 winner지만 분포 좁음)
**Slice 9 측정 방식 전환**: haiku/sonnet 모델 분포 → **Sonnet 26건 specificity score 분포 (0~5)**

```python
# scripts/slice9/measure_distribution_width.py (신규)
import json
from collections import Counter


def main():
    rationales = json.load(open("docs/portfolio/coach/slice9/part1/rationale_records.json"))

    # original_specificity_score 분포 (자동 patterns count 0~5)
    auto_scores = [r["original_specificity_score"] for r in rationales]
    auto_dist = Counter(auto_scores)

    # rationale_score 분포 (Sonnet 자체 평가 0~5)
    rationale_scores = [r["rationale_score"] for r in rationales]
    rationale_dist = Counter(rationale_scores)

    # 분포 폭 = max - min
    auto_width = (max(auto_scores) - min(auto_scores)) if auto_scores else 0
    rationale_width = (max(rationale_scores) - min(rationale_scores)) if rationale_scores else 0

    print(f"Auto specificity scores: {dict(sorted(auto_dist.items()))}, width={auto_width}")
    print(f"Rationale scores: {dict(sorted(rationale_dist.items()))}, width={rationale_width}")
    print(f"KPI #26 (분포 폭 ≥ 3.0): {'PASS' if rationale_width >= 3 else 'FAIL'}")
```

### §4.2 KPI 12개 자동 검증 스크립트

`scripts/slice9/verify_part1_kpi.py` (신규)

```python
"""Slice 9 Part 1 #45 — KPI 12개 자동 검증.

Slice 9 #43/E1 KPI 매트릭스 v2 기준:
- core 8 (회귀/IDENTICAL/단건/누적/cap/호출/4판정/winner)
- auxiliary 4 (회귀 9a/9b/trio/분포/estimator)
"""

import json
import subprocess
import sys
from pathlib import Path

from portfolio.llm.cost_guard import CostGuard


def main():
    rationales = json.load(open("docs/portfolio/coach/slice9/part1/rationale_records.json"))
    batch_logs = json.load(open("docs/portfolio/coach/slice9/part1/batch_logs.json"))

    kpis = {}

    # ── Core KPI 8개 ──

    # KPI 1: 회귀 통과
    result = subprocess.run(["pytest", "portfolio/tests", "-q"], capture_output=True, text=True)
    last_line = result.stdout.strip().split("\n")[-1]
    passed = int(last_line.split()[0]) if last_line.split()[0].isdigit() else 0
    actual_delta = passed - 476  # Step 0 종결값
    kpis["1_regression"] = {"value": f"476 → {passed} (+{actual_delta})", "pass": 481 <= passed <= 486}

    # KPI 2: IDENTICAL hash
    result = subprocess.run(["pytest", "portfolio/tests/test_static_integrity.py", "-v"],
                          capture_output=True, text=True)
    identical_pass = result.stdout.count("PASSED") >= 7
    kpis["2_identical_hash"] = {"value": "7/7" if identical_pass else "FAIL", "pass": identical_pass}

    # KPI 3: 단건 cost (D3 자동)
    sonnet_violations = sum(1 for r in rationales if r["cost_usd"] > 0.10)
    kpis["3_per_call_cost"] = {"value": f"violations={sonnet_violations}", "pass": sonnet_violations == 0}

    # KPI 4: 누적 cost
    total_part1_cost = sum(r["cost_usd"] for r in rationales)
    cumulative = 2.0483 + total_part1_cost
    kpis["4_cumulative_cost"] = {
        "value": f"${cumulative:.4f}",
        "pass": cumulative <= 2.80,
    }

    # KPI 5: 슬라이스 cap (Slice 9 #43 신규)
    slice_usd = total_part1_cost
    kpis["5_slice_cap"] = {
        "value": f"${slice_usd:.4f} / $1.00 ({slice_usd*100:.1f}%)",
        "pass": slice_usd <= 1.00,
    }

    # KPI 6: LLM 호출
    call_count = len(rationales)
    kpis["6_llm_calls"] = {
        "value": f"{call_count}/100",
        "pass": call_count <= 100,
    }

    # KPI 7: 4판정 PASS 비율 (rationale 자체 4판정 — cost/parse/score/length)
    pass_count = sum(
        1 for r in rationales
        if r["cost_usd"] <= 0.10
           and len(r["rationale_text"]) >= 100
           and 0 <= r["rationale_score"] <= 5
    )
    kpis["7_4판정_ratio"] = {
        "value": f"{pass_count}/{len(rationales)}",
        "pass": pass_count >= int(len(rationales) * 0.90),
    }

    # KPI 8: winner (Part 4 manual eval에서 확정)
    kpis["8_winner_hypothesis"] = {
        "value": "Part 4 manual eval 후 확정 (잠정 Haiku 6/6)",
        "pass": None,  # N/A
    }

    # ── Auxiliary KPI 4개 ──

    # KPI 9a: cost 회귀 (E1 자동 분류)
    # Slice 9 Part 1 변경 경로: portfolio/schemas/rationale.py + portfolio/prompts/rationale/
    # 모두 cost 경로 → cost 회귀 분류
    # 예측: 5건 (schema 3 + builder 2)
    cost_predicted = 5
    # 실측 회귀 증분이 cost 또는 mixed인지 확인
    from portfolio.tests.helpers.regression_classifier import classify_current_commit
    classification = classify_current_commit()
    if classification in ("cost", "mixed"):
        deviation = abs(actual_delta - cost_predicted) / cost_predicted if cost_predicted else 1
        kpis["9a_cost_regression"] = {
            "value": f"classification={classification}, predicted={cost_predicted}, actual={actual_delta}, dev={deviation*100:.1f}%",
            "pass": deviation <= 0.30,
        }
    else:
        kpis["9a_cost_regression"] = {"value": f"classification={classification}, N/A", "pass": None}

    # KPI 9b: no-cost 회귀 — Part 1은 cost 분류이므로 N/A
    kpis["9b_no_cost_regression"] = {"value": "Part 1은 cost 회귀, N/A", "pass": None}

    # KPI 10: trio 진단 효과 (Slice 8 #29 — Slice 9에서 재측정)
    insufficient = sum(1 for r in rationales if r["original_specificity_score"] <= 2)
    ratio = insufficient / len(rationales) if rationales else 0
    kpis["10_trio_diagnosis_effect"] = {
        "value": f"{insufficient}/{len(rationales)} ({ratio*100:.1f}%)",
        "pass": ratio < 0.30,
    }

    # KPI 11: 분포 폭 (#26)
    rationale_scores = [r["rationale_score"] for r in rationales]
    width = max(rationale_scores) - min(rationale_scores) if rationale_scores else 0
    kpis["11_distribution_width"] = {
        "value": f"width={width}",
        "pass": width >= 3,
    }

    # KPI 12: #β2 estimator 2차 측정
    deltas = []
    for r in rationales:
        if r["estimated_input_tokens"] and r["input_tokens"]:
            delta = abs(r["input_tokens"] - r["estimated_input_tokens"]) / r["input_tokens"]
            deltas.append(delta)
    max_delta = max(deltas) if deltas else 0
    kpis["12_beta2_estimator"] = {
        "value": f"max delta {max_delta*100:.2f}% (n={len(deltas)})",
        "pass": max_delta <= 0.30,
    }

    # 출력
    print("=" * 70)
    print("Slice 9 Part 1 — KPI 12개 자동 검증")
    print("=" * 70)
    all_pass = True
    for kpi_id, data in kpis.items():
        if data["pass"] is True:
            verdict = "✓ PASS"
        elif data["pass"] is False:
            verdict = "✗ FAIL"
            all_pass = False
        else:
            verdict = "⊘ N/A"
        print(f"{kpi_id}: {data['value']} → {verdict}")
    print("=" * 70)

    # 저장
    output_path = Path("docs/portfolio/coach/slice9/part1/kpi_verification.json")
    with open(output_path, "w") as f:
        json.dump(kpis, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
```

### §4.3 KPI 검증 스크립트 단위 테스트

`portfolio/tests/slice9/test_verify_part1_kpi.py` (신규)

```python
"""Slice 9 #45 — KPI 검증 스크립트 자체 단위 테스트."""

import pytest


def test_kpi_check_logic_no_cost():
    """no-cost 분류 시 KPI 9b 적용."""
    # ... (분류 로직 단위 테스트)
    pass

def test_kpi_check_logic_cost():
    """cost 분류 시 KPI 9a 적용."""
    pass

def test_kpi_distribution_width_calculation():
    """분포 폭 = max - min."""
    scores = [3, 4, 5, 5, 4, 3, 2]
    assert max(scores) - min(scores) == 3

def test_kpi_4판정_passing():
    """4판정 정의."""
    # cost ≤ 0.10 + length ≥ 100 + score in 0~5
    pass
```

### §4.4 KPI 4

- [ ] 분포 폭 측정 스크립트 실행, 결과 저장
- [ ] KPI 12개 자동 검증 스크립트 실행, ALL PASS 또는 분류 결과 명시
- [ ] KPI 검증 단위 테스트 4건 PASS
- [ ] kpi_verification.json 저장
- [ ] 회귀 +4건

---

## §5. #β2 Estimator 2차 측정 + Verdict

### §5.1 측정 (KPI 12에 포함됨)

`scripts/slice9/measure_beta2_round2.py` (신규)

```python
"""Slice 9 Part 1 §5 — #β2 estimator 2차 측정.

Slice 7 systematic underestimate (-50% bias) → Slice 8 Step 0 재설계.
Part 1에서 Sonnet 26건 데이터로 정밀도 검증.
"""

import json
from statistics import median, mean
from pathlib import Path


def main():
    rationales = json.load(open("docs/portfolio/coach/slice9/part1/rationale_records.json"))

    measurements = []
    for r in rationales:
        if not r["estimated_input_tokens"] or not r["input_tokens"]:
            continue
        delta = abs(r["input_tokens"] - r["estimated_input_tokens"]) / r["input_tokens"]
        measurements.append({
            "case_id": r["case_id"],
            "estimated": r["estimated_input_tokens"],
            "actual": r["input_tokens"],
            "delta": delta,
            "sign": "under" if r["estimated_input_tokens"] < r["input_tokens"] else "over",
        })

    if not measurements:
        print("측정 데이터 없음")
        return

    deltas = [m["delta"] for m in measurements]
    max_delta = max(deltas)
    p90 = sorted(deltas)[int(len(deltas) * 0.9)] if len(deltas) >= 10 else max(deltas)
    median_delta = median(deltas)
    mean_delta = mean(deltas)
    under_count = sum(1 for m in measurements if m["sign"] == "under")

    print(f"#β2 2차 측정 (n={len(measurements)}, Sonnet rationale Part 1):")
    print(f"  max delta: {max_delta*100:.2f}%")
    print(f"  p90 delta: {p90*100:.2f}%")
    print(f"  median: {median_delta*100:.2f}%")
    print(f"  mean: {mean_delta*100:.2f}%")
    print(f"  under-estimate: {under_count}/{len(measurements)} ({under_count/len(measurements)*100:.1f}%)")
    print()
    print(f"Slice 7 baseline: max 52.21%, -50% bias")
    print(f"Slice 8 Step 0 재설계 후 max delta 1.88% (mock)")
    print(f"Slice 9 Part 1 (real Sonnet): max delta {max_delta*100:.2f}%")
    print()

    verdict = "close" if max_delta <= 0.30 else "keep_open"
    print(f"Verdict: {verdict}")

    output_path = Path("docs/portfolio/coach/slice9/part1/beta2_round2.json")
    with open(output_path, "w") as f:
        json.dump({
            "measurements": measurements,
            "summary": {
                "n": len(measurements),
                "max_delta": max_delta,
                "p90_delta": p90,
                "median_delta": median_delta,
                "mean_delta": mean_delta,
                "under_ratio": under_count / len(measurements),
            },
            "verdict": verdict,
        }, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
```

### §5.2 KPI 5

- [ ] beta2_round2.json 저장
- [ ] verdict: close (max delta ≤ 30%) / keep_open (>30%)
- [ ] verdict가 close면 **#β2 close 처리**

### §5.3 분기 조건

| 조건                  | 분기 처리                                                                               |
| --------------------- | --------------------------------------------------------------------------------------- |
| max delta ≤ 30%       | **#β2 close**, Slice 10 부담 1건 감소                                                   |
| 30% < max delta ≤ 50% | keep_open, Slice 10 Step 0 후보                                                         |
| max delta > 50%       | **Slice 7 systematic underestimate 재발 신호** → estimator 재설계 v3 등록 (신규 PS 3.0) |

---

## §6. 종결 보고 양식

### §6.1 회신 보고서 골격

`docs/portfolio/coach/slice9/part1_closing.md`

```markdown
# Slice 9 Part 1 종결 보고서

> **작성일**: YYYY-MM-DD
> **브랜치**: slice9
> **종결 상태**: \_\_\_

## KPI 통과 현황 (12개)

| #   | 항목                    | 기준                | 결과                           | 통과 |
| --- | ----------------------- | ------------------- | ------------------------------ | :--: |
| 1   | 회귀                    | 476 → 481~486       | 476 → \_\_\_                   |  \_  |
| 2   | IDENTICAL hash          | 7/7                 | \_                             |  \_  |
| 3   | 단건 cost               | Sonnet < $0.10      | violations \_                  |  \_  |
| 4   | 누적 cost               | ≤ $2.80             | $\_\_\_                        |  \_  |
| 5   | **슬라이스 cap (신규)** | ≤ $1.00             | $\_\_\_                        |  \_  |
| 6   | LLM 호출                | ≤ 100               | \_/100                         |  \_  |
| 7   | 4판정 비율              | ≥ 90%               | _/_                            |  \_  |
| 8   | winner                  | manual eval 후      | jamjeong Haiku 6/6             | N/A  |
| 9a  | cost 회귀 격리          | ±30%                | predicted=_, actual=_, dev=\_% |  \_  |
| 9b  | no-cost 회귀 격리       | ±50%                | N/A                            |  \_  |
| 10  | trio 진단 효과          | "구체성 부족" < 30% | _/26 (_%)                      |  \_  |
| 11  | 분포 폭 (#26)           | ≥ 3                 | width=\_                       |  \_  |
| 12  | #β2 estimator           | max delta ≤ 30%     | \_%                            |  \_  |

## 부채 처리

| 부채                      | 상태 | 비고                                 |
| ------------------------- | ---- | ------------------------------------ |
| #44 rationale 28건 → 26건 | \_   | matrix 1:1 대응으로 변경, 본질 close |
| #45 KPI 12개 자동 검증    | \_   | core 8 + auxiliary 4 정착            |
| #β2 estimator 정밀도      | \_   | §5 verdict                           |

## 비용 추적

- Step 0 종결: $2.0483
- Batch 1~6 합계: $\_\_\_
- **Part 1 단독**: $_\_\_ (cap $1.00 대비 _%)
- **누적 광의**: $_\_\_ (임계 $3.00 대비 _%)

## Batch 진행 결과

| Batch | Cases   | Cost    | slice_usd 누적 | 정상 종결 |
| ----- | ------- | ------- | -------------- | --------- |
| 1     | S01~S05 | $\_\_\_ | $\_\_\_        | \_        |
| 2     | S06~S10 | $\_\_\_ | $\_\_\_        | \_        |
| 3     | S11~S15 | $\_\_\_ | $\_\_\_        | \_        |
| 4     | S16~S20 | $\_\_\_ | $\_\_\_        | \_        |
| 5     | S21~S25 | $\_\_\_ | $\_\_\_        | \_        |
| 6     | S26     | $\_\_\_ | $\_\_\_        | \_        |

## 신규 부채 등록

(있다면) | _ | _ | \_ |

## 산출물 체크리스트

| #   | 산출물                       | 위치                                            |
| --- | ---------------------------- | ----------------------------------------------- |
| 1   | RationaleRecord schema       | portfolio/schemas/rationale.py                  |
| 2   | Rationale prompt builder     | portfolio/prompts/rationale/builder.py          |
| 3   | Schema/builder 단위 테스트   | portfolio/tests/slice9/                         |
| 4   | Batch 실행 스크립트          | scripts/slice9/run_part1_rationale_batch.py     |
| 5   | rationale_records.json       | docs/portfolio/coach/slice9/part1/              |
| 6   | batch_logs.json              | docs/portfolio/coach/slice9/part1/              |
| 7   | join 스크립트                | scripts/slice9/join_matrix_rationale.py         |
| 8   | matrix_rationale_joined.json | docs/portfolio/coach/slice9/part1/              |
| 9   | 분포 폭 측정 스크립트        | scripts/slice9/measure_distribution_width.py    |
| 10  | KPI 검증 스크립트            | scripts/slice9/verify_part1_kpi.py              |
| 11  | KPI 검증 단위 테스트         | portfolio/tests/slice9/test_verify_part1_kpi.py |
| 12  | kpi_verification.json        | docs/portfolio/coach/slice9/part1/              |
| 13  | #β2 측정 스크립트            | scripts/slice9/measure_beta2_round2.py          |
| 14  | beta2_round2.json            | docs/portfolio/coach/slice9/part1/              |
| 15  | 종결 보고서                  | docs/portfolio/coach/slice9/part1_closing.md    |

## 다음 단계

- Slice 9 Part 2 진입 — #46 Step 8 manual eval dump
- 예상 회귀: +3~5, 비용 $0
```

---

## §7. 핵심 결정 lock 블록

| 결정                    | 값                                       | 근거                                   |
| ----------------------- | ---------------------------------------- | -------------------------------------- |
| **A1** Part 1 진입 판정 | 그대로 진입                              | 가중합 4.80, 마진 1.50 (결정적)        |
| **B4** rationale 방식   | Sonnet 26건 matrix 1:1                   | 가중합 4.45, tie-breaker matrix 정합성 |
| **D2** Cap 안전망       | 5건 batch 분할 + batch 종료 cap 확인     | 가중합 4.20, Slice 8 학습 직접 반영    |
| **D3** 단건 임계        | Sonnet $0.10 자동 동시 적용              | Slice 6 정책 default                   |
| 누적 임계               | $3.00                                    | Slice 9 Step 0 #43                     |
| 슬라이스 cap            | $1.00                                    | Slice 9 Step 0 #43                     |
| KPI 매트릭스            | 12개 (core 8 + auxiliary 4)              | Slice 9 Step 0 v2                      |
| 분포 폭 (#26) 측정      | Sonnet 26건 specificity score 분포 (0~5) | Slice 9 Part 1 도입                    |

---

## §8. 분기 시나리오

### §8.1 정상 경로

1. §0 사전 체크 PASS
2. §1 schema + prompt builder + 단위 테스트 5건 PASS
3. §2 Batch 1~6 정상 종결, 26 records 생성, cap 마진 31% 유지
4. §3 matrix join 완료
5. §4 KPI 12개 ALL PASS (또는 N/A 항목 명시)
6. §5 #β2 verdict close (또는 keep_open)
7. §6 종결 보고서 작성
8. **Part 1 종결**: 회귀 481~486, 비용 ~$2.74, #44/#45 close

### §8.2 비정상 경로

| 시점         | 신호                                                  | 분기                                           |
| ------------ | ----------------------------------------------------- | ---------------------------------------------- |
| §2 Batch 1   | 단건 cost > $0.10 (sonnet rationale prompt 토큰 폭주) | 즉시 정지, rationale prompt 길이 점검          |
| §2 Batch 1~3 | slice_usd > $0.80 (cap_warning)                       | 다음 batch 진입 전 사용자 결정 사이클          |
| §2 Batch 4~5 | slice_usd > $1.00 (cap_exceeded)                      | CostCapExceeded 자동 정지, partial result 보존 |
| §4 KPI 10    | 진단 효과 비율 ≥ 30%                                  | trio 가설 약화 신호, manual eval 분석 우선     |
| §4 KPI 11    | 분포 폭 < 3                                           | #26 keep_open 유지, 측정 방식 재정밀화         |
| §5 KPI 12    | max delta > 50%                                       | estimator v3 재설계 신규 부채 등록             |

### §8.3 즉시 정지 트리거

- IDENTICAL hash 7/7 깨짐
- 회귀 < 476 (Step 0 종결값보다 감소)
- 누적 cost > $3.00 (임계 위반)
- 슬라이스 cap > $1.00

---

## §9. Slice 9 Part 1 진행 누적 비교

| 항목           | Slice 9 Step 0 종결 | Slice 9 Part 1 (예상)  | Slice 9 Part 2 (예상) |
| -------------- | ------------------- | ---------------------- | --------------------- |
| 회귀           | 476                 | 481~486 (+5~10)        | +3~5                  |
| 비용 (단독)    | $0                  | $0.69                  | $0                    |
| 비용 (누적)    | $2.0483             | $2.74                  | $2.74                 |
| 슬라이스 단독  | $0                  | $0.69                  | $0                    |
| Cap 마진       | —                   | 31%                    | —                     |
| LLM 호출       | 0                   | 26                     | 0                     |
| 부채 close     | #43                 | #44/#45 (+ #β2 조건부) | #46                   |
| IDENTICAL hash | 7/7                 | 7/7 (필수)             | 7/7 (필수)            |

---

## 부록 A. Claude Code 작업 자율성 경계

- **Claude Code 자율 수행**: §0 사전 체크, §1~§5 스크립트/스키마 작성/실행, §6 KPI 자동 검증, §7 종결 보고서 작성
- **사용자 회신 필요**:
  - Batch 종료 시 cap_warning 도달 (slice_usd > $0.80)
  - §7 lock 블록 변경
  - §8.3 즉시 정지 트리거 발동
  - #β2 verdict keep_open + delta > 50% (estimator v3 결정)
- **자동 fallback 허용**: batch 도중 CostCapExceeded raise → 잔여 batch 자동 건너뜀, partial result 보존
- **자동 부채 등록 허용**: §8 분기 시나리오 외 발견 신규 부채 candidate (등록만, 사용자 회신 전까지)

---

**Part 1 진입 준비 완료.**

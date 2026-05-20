# Slice 12 Part 4 — Manual Eval (Haiku vs Sonnet Blind + Gate Clarity)

> **사전 결정 채택 (Part 4 진입 직전 확정, 2026-05-20)**
>
> - **D1-B**: haiku + sonnet 15 batch blind comparison (글쓰기 가설 8/8 정착 시도)
> - **D2-B**: 3축 평가 (naturalness + insight + gate_clarity)
> - **D3-A**: 15 case 전체 평가 (30 commentary blind)
> - **D4-A.2**: KPI matrix 갱신은 Slice 12 종결 closing에서 처리 (Part 4 scope 보호)

---

## 0. 진입 Baseline (실행 전 확인 필수)

| 항목          | 값                                                                                 |
| ------------- | ---------------------------------------------------------------------------------- |
| 브랜치        | `slice12`                                                                          |
| 선행 commit   | `8c5bb6d` (Part 3 종결)                                                            |
| 회귀 baseline | **668 passed**                                                                     |
| 누적 비용     | $2.7989 / $4.00 (마진 30.0%)                                                       |
| Slice cap     | $0.1545 / $1.00 (마진 84.55%)                                                      |
| LLM 호출      | 19 / 50 (마진 31)                                                                  |
| 잔존 부채     | #51 (S13 1순위), #59 E5 (D3-B 격리), #60 후보 (gate-aware prompt, Part 4에서 결정) |
| Part 3 산출물 | 15 fixture + smoke results JSON + 30 unit tests + E3 통합                          |

**진입 전 검증 명령**:

```bash
git log --oneline -1                                # 8c5bb6d 확인
pytest --co -q | tail -5                            # 668 collected
git status                                          # clean
ls docs/portfolio/coach/slice12/part3_smoke_results.json   # 존재 확인
ls tests/scoring/fixtures/*.json | wc -l            # 15 확인
```

---

## 1. Part 4 본질 (Manual Eval + 가설 정착 결정)

Part 3까지는 자동 단계 (코드 작성·smoke 실행). **Part 4는 사람 평가 단계**로 본질이 다르다.

Part 4의 책임:

1. **Sonnet 15 batch 매트릭스 dump** (Step 0, 자동) — 비교 대상 commentary 생성
2. **HTML eval 도구 셋업** (Step 1, 자동) — blind A/B 평가 인터페이스
3. **Manual eval 30 commentary blind** (Step 2, 병진 수행) — 핵심 데이터 생성
4. **결과 집계 + 가설 검증** (Step 3, 자동) — 8/8 정착 / #60 활성화 결정
5. **종결 보고** (Step 4) — Slice 12 종결 사이클 입력

**Scope 격리 (D4-A.2 적용)**:

- KPI matrix 갱신 ❌ (Slice 12 종결 closing 단계)
- 코드 prod 변경 ❌ (eval은 smoke + HTML 도구만, IDENTICAL 7/7 절대 사수)
- 새 fixture 추가 ❌ (Part 3 15 fixture 그대로)
- #60 부채 코드 작업 ❌ (활성화/보류 결정만, 실제 prompt 수정은 Slice 13+)

---

## 2. Step 0: Sonnet 15 Batch 매트릭스 Dump (자동, ~30분, ~$0.34)

### 2.1 작업 개요

Part 3 fixture 15건을 sonnet으로 재실행하여 비교 commentary 생성. **prod 코드 무변경**, smoke 스크립트만 사용.

### 2.2 스크립트 위치

```
portfolio/services/coach/smoke/slice12_part4_sonnet_batch.py
```

### 2.3 스크립트 사양

```python
"""Slice 12 Part 4 Step 0: Sonnet 15 batch 매트릭스.

Part 3 fixture 15건을 sonnet으로 실행하여 blind eval 비교 대상 생성.
prod 코드 무변경. CostGuard 슬라이스 cap 적용.
"""
import json
from pathlib import Path
from portfolio.services.e3_service import run_e3_coach
from portfolio.services.cost_guard import CostGuard

FIXTURE_DIR = Path("tests/scoring/fixtures")
OUTPUT = Path("docs/portfolio/coach/slice12/part4_sonnet_results.json")

# Part 3와 동일 순서로 15건 로드
FIXTURE_NAMES = [
    f"{cat}_{case}"
    for cat in ["value", "growth", "income", "factor", "special"]
    for case in ["normal", "edge", "gate"]
]


def run_sonnet_batch() -> dict:
    guard = CostGuard.instance()
    # Slice 12 누적 cap은 그대로, Part 4 단독 sub-cap 사용
    # (Part 3에서 이미 $0.0991 사용 → Part 4 sub-cap $0.45 여유)

    results = []
    for name in FIXTURE_NAMES:
        with open(FIXTURE_DIR / f"{name}.json") as f:
            fx = json.load(f)

        result = run_e3_coach(
            symbol=fx["symbol"],
            preset_id=fx["preset_id"],
            metrics=fx["metrics"],
            provider="anthropic",
            model="claude-sonnet-4-5",  # Sonnet 명시 (haiku와 동일 LLMClient)
        )
        results.append({
            "fixture": name,
            "case_type": fx["case_type"],
            "preset_id": fx["preset_id"],
            "scores": result.get("scores", {}),
            "gate_triggered": result.get("scores", {}).get("_category_score", -1) == 0.0,
            "expected_gate": fx.get("expected_gate_triggered", False),
            "commentary": result["commentary"],
            "cost_usd": result.get("cost_usd", 0.0),
            "latency_ms": result.get("latency_ms", 0),
            "provider": result.get("provider", ""),
            "model": result.get("model", ""),
            "input_tokens": result.get("input_tokens", 0),
            "output_tokens": result.get("output_tokens", 0),
        })

    summary = {
        "results": results,
        "total_cost": sum(r["cost_usd"] for r in results),
        "total_latency_ms": sum(r["latency_ms"] for r in results),
        "avg_latency_ms": sum(r["latency_ms"] for r in results) / len(results),
        "model": "claude-sonnet-4-5",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


if __name__ == "__main__":
    s = run_sonnet_batch()
    print(f"15 case complete, cost ${s['total_cost']:.4f}, avg latency {s['avg_latency_ms']:.0f}ms")
```

### 2.4 비용·LLM 가드

| 항목                | 목표                                   | 가드                                           |
| ------------------- | -------------------------------------- | ---------------------------------------------- |
| Sonnet 15 호출 비용 | ~$0.34 (Slice 8/9 cost 3.4× 패턴 기반) | 슬라이스 cap $1.00 - 누적 $0.1545 = $0.85 여유 |
| LLM 호출            | +15 (누적 19 → 34)                     | 50 cap 마진 16                                 |
| Slice cap 도달 위험 | $0.50 미만 예상                        | 마진 $0.50 충분                                |

### 2.5 IDENTICAL 검증

```bash
pytest tests/ -k "identical" -v
# 7/7 PASS 필수 — sonnet 매트릭스는 prod 영향 0
```

---

## 3. Step 1: HTML Eval 도구 셋업 (자동, ~30분)

### 3.1 작업 개요

Slice 9 P2 HTML eval 자산 재활용 또는 Slice 12 신규 구축. 30 commentary를 blind A/B로 표시 + nat/ins 슬라이더 + gate 4 case에 gate_clarity 추가.

### 3.2 도구 위치 확인

```bash
# Slice 9 P2 HTML eval 도구 존재 확인
find . -name "*.html" -path "*slice9*" 2>/dev/null
find . -name "blind_eval*" 2>/dev/null
ls docs/portfolio/coach/slice9/
```

**시나리오 A: Slice 9 자산 발견** → 재사용, Slice 12 fixture로 input 교체  
**시나리오 B: 자산 부재** → 신규 구축 (단순 단일 HTML, ~30분)

### 3.3 HTML 도구 사양 (신규 구축 또는 갱신)

```
docs/portfolio/coach/slice12/part4_blind_eval.html
docs/portfolio/coach/slice12/part4_blind_eval_input.json   # generated
docs/portfolio/coach/slice12/part4_blind_eval_truth.json   # generated, 평가 후 공개
docs/portfolio/coach/slice12/part4_blind_eval_output.json  # 병진 입력 결과
```

**HTML 도구 요구사항**:

1. `part4_blind_eval_input.json` 로드 (A/B label 랜덤화된 30 commentary)
2. 각 case 카드:
   - case 이름 (e.g. "income_gate")
   - 카테고리 + preset_id + case_type
   - **commentary A** (상단) + **commentary B** (하단)
   - **nat slider** (1~5) × 2 모델
   - **ins slider** (1~5) × 2 모델
   - **gate_clarity slider** (1~5) × 2 모델 — **gate case 4건만 활성화**
3. 진행률 표시 (e.g. 12/15 case 완료)
4. localStorage 자동 저장
5. "Export JSON" 버튼 → `part4_blind_eval_output.json` 다운로드

### 3.4 Input JSON 생성 스크립트

```
portfolio/services/coach/smoke/slice12_part4_build_eval_input.py
```

```python
"""Part 4 blind eval input 생성: A/B 랜덤화."""
import json
import random
from pathlib import Path

HAIKU_RESULTS = Path("docs/portfolio/coach/slice12/part3_smoke_results.json")
SONNET_RESULTS = Path("docs/portfolio/coach/slice12/part4_sonnet_results.json")
INPUT_OUT = Path("docs/portfolio/coach/slice12/part4_blind_eval_input.json")
TRUTH_OUT = Path("docs/portfolio/coach/slice12/part4_blind_eval_truth.json")

random.seed(42)  # 재현성

def build_eval_input():
    haiku = json.loads(HAIKU_RESULTS.read_text())["results"]
    sonnet = json.loads(SONNET_RESULTS.read_text())["results"]
    assert len(haiku) == 15 and len(sonnet) == 15

    cases = []
    truth = []
    for h, s in zip(haiku, sonnet):
        assert h["fixture"] == s["fixture"]
        # 50% 확률로 A/B swap
        if random.random() < 0.5:
            commentary_a, model_a = h["commentary"], "haiku"
            commentary_b, model_b = s["commentary"], "sonnet"
        else:
            commentary_a, model_a = s["commentary"], "sonnet"
            commentary_b, model_b = h["commentary"], "haiku"

        is_gate = h["case_type"] == "gate" and h["gate_triggered"]
        cases.append({
            "fixture": h["fixture"],
            "category": h["fixture"].split("_")[0],
            "preset_id": h["preset_id"],
            "case_type": h["case_type"],
            "is_gate_case": is_gate,
            "commentary_a": commentary_a,
            "commentary_b": commentary_b,
        })
        truth.append({
            "fixture": h["fixture"],
            "model_a": model_a,
            "model_b": model_b,
        })

    INPUT_OUT.write_text(json.dumps({"cases": cases}, ensure_ascii=False, indent=2))
    TRUTH_OUT.write_text(json.dumps({"truth": truth}, ensure_ascii=False, indent=2))
    print(f"Input {len(cases)} cases written. Gate cases: {sum(c['is_gate_case'] for c in cases)}")

if __name__ == "__main__":
    build_eval_input()
```

### 3.5 HTML 도구 자체 (단일 파일)

> HTML 파일은 본 지시서에서 코드 골격만 명시. 상세 구현은 Claude Code가 작성:
>
> - 단일 HTML (CSS/JS 인라인)
> - tailwind CDN 사용 가능
> - 외부 라이브러리 최소화
> - **localStorage 자동 저장** (실수로 새로고침해도 보존)
> - **A/B 카드 순서는 input JSON 그대로 표시** (이미 랜덤화됨)
> - **gate case 표시**: `is_gate_case: true`인 경우 gate_clarity 슬라이더 표시, 나머지는 숨김

---

## 4. Step 2: Manual Eval 실행 (병진 수행, ~1.5h)

### 4.1 실행 절차 (병진 액션)

1. `slice12_part4_sonnet_batch.py` 실행 결과 확인 (Claude Code 자동)
2. `slice12_part4_build_eval_input.py` 실행 결과 확인 (Claude Code 자동)
3. `part4_blind_eval.html` 브라우저에서 열기 (병진)
4. 15 case 각각:
   - commentary A / B 읽기
   - nat A, nat B 슬라이더 설정 (1=어색, 5=매우 자연스러움)
   - ins A, ins B 슬라이더 설정 (1=일반론, 5=구체적 통찰)
   - gate case 4건만: gate_clarity A, B 슬라이더 (1=gate 사실 누락, 3=언급하나 임계 모호, 5=임계+실제값 명시)
5. "Export JSON" 클릭 → `part4_blind_eval_output.json` 다운로드
6. 다운로드 파일을 `docs/portfolio/coach/slice12/` 에 저장

### 4.2 평가 가이드라인

**naturalness 기준**:

- 5: 매우 자연스러운 한국어, 어색한 표현 없음
- 4: 대체로 자연스러움, 1~2개 어색
- 3: 의미는 통하나 어색
- 2: 어색한 표현 다수
- 1: 의미 파악 어려움

**insight 기준**:

- 5: 구체적 수치+해석+다음 액션 명확
- 4: 구체적이나 1개 요소 누락
- 3: 일반론과 구체 혼재
- 2: 대부분 일반론
- 1: 어떤 종목/카테고리에도 적용 가능한 boilerplate

**gate_clarity 기준 (gate 4 case만)**:

- 5: 임계값(e.g. "yield 2%")과 실제값(e.g. "1.0%") 모두 명시
- 4: 임계값 또는 실제값 중 하나만 명시
- 3: gate 미통과 사실은 언급, 수치 부재
- 2: 점수 0임은 언급, gate 개념 부재
- 1: gate 발동 사실 자체를 commentary에 반영 못함

### 4.3 평가 시간 예상

| 단계                    | 시간               |
| ----------------------- | ------------------ |
| nat + ins 30 commentary | ~60분 (case당 4분) |
| gate_clarity 4 case     | ~15분              |
| 결과 export + 저장      | ~5분               |
| 검토 + 재평가           | ~10분              |
| **합계**                | **~1.5h**          |

---

## 5. Step 3: 결과 집계 + 가설 검증 (자동, ~20분)

### 5.1 집계 스크립트

```
portfolio/services/coach/smoke/slice12_part4_aggregate.py
```

```python
"""Part 4 결과 집계: blind unmask + 가설 검증."""
import json
from pathlib import Path
from collections import defaultdict

INPUT = Path("docs/portfolio/coach/slice12/part4_blind_eval_input.json")
TRUTH = Path("docs/portfolio/coach/slice12/part4_blind_eval_truth.json")
OUTPUT = Path("docs/portfolio/coach/slice12/part4_blind_eval_output.json")
HAIKU_RESULTS = Path("docs/portfolio/coach/slice12/part3_smoke_results.json")
SONNET_RESULTS = Path("docs/portfolio/coach/slice12/part4_sonnet_results.json")
REPORT = Path("docs/portfolio/coach/slice12/part4_aggregate.json")


def aggregate():
    truth = {t["fixture"]: t for t in json.loads(TRUTH.read_text())["truth"]}
    eval_out = {e["fixture"]: e for e in json.loads(OUTPUT.read_text())["evaluations"]}
    haiku = {h["fixture"]: h for h in json.loads(HAIKU_RESULTS.read_text())["results"]}
    sonnet = {s["fixture"]: s for s in json.loads(SONNET_RESULTS.read_text())["results"]}

    # case별 unmask
    rows = []
    haiku_scores = defaultdict(list)
    sonnet_scores = defaultdict(list)
    haiku_gate = []
    sonnet_gate = []

    for fixture, t in truth.items():
        e = eval_out[fixture]
        if t["model_a"] == "haiku":
            haiku_nat, sonnet_nat = e["nat_a"], e["nat_b"]
            haiku_ins, sonnet_ins = e["ins_a"], e["ins_b"]
            haiku_gc, sonnet_gc = e.get("gc_a"), e.get("gc_b")
        else:
            haiku_nat, sonnet_nat = e["nat_b"], e["nat_a"]
            haiku_ins, sonnet_ins = e["ins_b"], e["ins_a"]
            haiku_gc, sonnet_gc = e.get("gc_b"), e.get("gc_a")

        haiku_scores["nat"].append(haiku_nat)
        haiku_scores["ins"].append(haiku_ins)
        sonnet_scores["nat"].append(sonnet_nat)
        sonnet_scores["ins"].append(sonnet_ins)
        if haiku_gc is not None:
            haiku_gate.append(haiku_gc)
            sonnet_gate.append(sonnet_gc)

        rows.append({
            "fixture": fixture,
            "haiku": {"nat": haiku_nat, "ins": haiku_ins, "gc": haiku_gc},
            "sonnet": {"nat": sonnet_nat, "ins": sonnet_ins, "gc": sonnet_gc},
        })

    def mean(xs): return sum(xs) / len(xs) if xs else 0

    haiku_means = {k: mean(v) for k, v in haiku_scores.items()}
    sonnet_means = {k: mean(v) for k, v in sonnet_scores.items()}
    haiku_gate_mean = mean(haiku_gate)
    sonnet_gate_mean = mean(sonnet_gate)

    # case별 winner
    haiku_wins_nat = sum(1 for r in rows if r["haiku"]["nat"] > r["sonnet"]["nat"])
    haiku_wins_ins = sum(1 for r in rows if r["haiku"]["ins"] > r["sonnet"]["ins"])
    haiku_combined_wins = sum(
        1 for r in rows
        if (r["haiku"]["nat"] + r["haiku"]["ins"]) > (r["sonnet"]["nat"] + r["sonnet"]["ins"])
    )

    # cost/latency (Part 3 + Step 0 데이터)
    haiku_cost = sum(haiku[f]["cost_usd"] for f in truth.keys())
    sonnet_cost = sum(sonnet[f]["cost_usd"] for f in truth.keys())
    haiku_latency = sum(haiku[f]["latency_ms"] for f in truth.keys()) / 15
    sonnet_latency = sum(sonnet[f]["latency_ms"] for f in truth.keys()) / 15

    # efficiency = quality / cost
    haiku_quality = haiku_means["nat"] + haiku_means["ins"]
    sonnet_quality = sonnet_means["nat"] + sonnet_means["ins"]
    haiku_eff = haiku_quality / haiku_cost if haiku_cost > 0 else 0
    sonnet_eff = sonnet_quality / sonnet_cost if sonnet_cost > 0 else 0
    eff_gap_pct = ((haiku_eff - sonnet_eff) / sonnet_eff * 100) if sonnet_eff > 0 else 0

    # 글쓰기 가설 8/8 정착 룰
    # haiku가 nat에서 winner 또는 combined에서 winner면 정착
    hypothesis_8th = "haiku" if haiku_combined_wins >= 8 else "sonnet"

    # #60 활성화 룰
    # gate_clarity 평균 (haiku 기준) ≤ 3.0이면 active
    gate_60_decision = "active" if haiku_gate_mean <= 3.0 else "hold"

    report = {
        "haiku_means": haiku_means,
        "sonnet_means": sonnet_means,
        "haiku_gate_clarity_mean": haiku_gate_mean,
        "sonnet_gate_clarity_mean": sonnet_gate_mean,
        "case_wins": {
            "haiku_nat_wins": haiku_wins_nat,
            "haiku_ins_wins": haiku_wins_ins,
            "haiku_combined_wins": haiku_combined_wins,
            "total_cases": 15,
        },
        "cost": {
            "haiku_total": haiku_cost,
            "sonnet_total": sonnet_cost,
            "ratio_sonnet_to_haiku": sonnet_cost / haiku_cost if haiku_cost > 0 else 0,
        },
        "latency": {
            "haiku_avg_ms": haiku_latency,
            "sonnet_avg_ms": sonnet_latency,
            "ratio_sonnet_to_haiku": sonnet_latency / haiku_latency if haiku_latency > 0 else 0,
        },
        "efficiency": {
            "haiku": haiku_eff,
            "sonnet": sonnet_eff,
            "gap_pct": eff_gap_pct,
        },
        "writing_hypothesis_8th_slice": hypothesis_8th,
        "writing_hypothesis_cumulative": "8/8" if hypothesis_8th == "haiku" else "7/8 (S12 반례)",
        "debt_60_decision": gate_60_decision,
        "debt_60_rule": "gate_clarity_haiku_mean <= 3.0 → active",
        "rows": rows,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"Aggregate: haiku combined wins {haiku_combined_wins}/15, "
          f"hypothesis {hypothesis_8th}, #60 {gate_60_decision}")
    return report

if __name__ == "__main__":
    aggregate()
```

### 5.2 가설 검증 룰

**글쓰기 가설 8/8 정착 조건**:

- haiku가 `haiku_combined_wins >= 8` (nat+ins 합산에서 case 과반 우세)
- 또는 `haiku_nat_wins >= 9` (nat 단독에서 압도)

위 조건 충족 → **8/8 정착 (8슬라이스 누적 강건)**  
미충족 → **7/8 (S12 반례, S2 E5 추출 반례와 동일 패턴), 가설 재검토**

**#60 부채 활성화 조건**:

- `haiku_gate_clarity_mean <= 3.0` → **#60 active** (Slice 13+ gate-aware prompt 작업 우선순위)
- `> 3.0` → **#60 hold** (현재 prompt가 충분)

### 5.3 분포 폭 측정 (Slice 11 P5 패턴)

```python
# 분포 폭 = (max - min) per dimension
nat_distribution_width = max(haiku_scores["nat"]) - min(haiku_scores["nat"])
ins_distribution_width = max(haiku_scores["ins"]) - min(haiku_scores["ins"])
# 분포 폭 < 3.0이면 #26 패턴 재발 (Slice 9 #26 close됨, 재발 검증)
```

---

## 6. Step 4: 종결 보고 (자동, ~15분)

### 6.1 part4_closing.md 템플릿

```markdown
# Slice 12 Part 4 종결 보고

## Baseline

- 선행 commit: 8c5bb6d (Part 3)
- 회귀 baseline: 668
- 부채 상태: #51, #59 E5 (D3-B 격리), #60 후보

## Step 0: Sonnet 매트릭스 dump

- 15 case 모두 PASS / cost $? / avg latency ?ms
- Schema fitting 15/15 (Slice 12 Step 0a #58 효과 재확인)

## Step 1-2: Manual eval

- 30 commentary blind, 15 case × 2 모델
- nat / ins / gate_clarity (4 case) 평가
- 평가 시간: ~1.5h

## Step 3: 결과 집계

- haiku 평균: nat ?.? / ins ?.?
- sonnet 평균: nat ?.? / ins ?.?
- haiku gate_clarity: ?.?
- sonnet gate_clarity: ?.?
- haiku combined wins: ?/15
- cost gap: sonnet/haiku = ?.?×
- latency gap: sonnet/haiku = ?.?×
- efficiency gap: ?%

## 가설 검증

- 글쓰기 가설 8/8: 정착 / 반례 (반례 시 사유)
- 분포 폭: nat ? / ins ? (S11 P5 #26 재발 여부)

## 부채 결정

- #60: active / hold (gate_clarity 기준)
- #51: 유지 (S13 Step 0 1순위)
- #59 E5: 유지 (S13 multi-debt mini 두 번째 사례 예정)

## 회귀 + IDENTICAL

- 회귀: 668 → ? (eval 단계라 코드 변경 작음, +0~5 예상)
- IDENTICAL: 7/7 PASS
- 비용 Part 4 단독: ~$0.34
- Slice 12 누적: $0.4? / $1.00 (마진 51%)
- 전체 누적: ~$3.1? / $4.00 (마진 ?%)
- LLM 호출: 19 → 34 / 50 (마진 16)

## Slice 12 종결 사전 등록

- D4-A.2 적용: KPI matrix "component buildup +30~40" 등록 예정
- 메모리 압축: B-Pattern (S11 종결 패턴 재활용)
- 누적 부채 처리: Slice 13 Step 0에서 #51 + #59 E5 multi-debt mini
```

---

## 7. 산출물 체크리스트 (예상 ~10건)

| #   | 경로                                                               | 내용                        |
| --- | ------------------------------------------------------------------ | --------------------------- |
| 1   | `portfolio/services/coach/smoke/slice12_part4_sonnet_batch.py`     | Sonnet 15 batch 스크립트    |
| 2   | `portfolio/services/coach/smoke/slice12_part4_build_eval_input.py` | A/B 랜덤화 input 생성       |
| 3   | `portfolio/services/coach/smoke/slice12_part4_aggregate.py`        | 결과 집계 + 가설 검증       |
| 4   | `docs/portfolio/coach/slice12/part4.md`                            | 이 지시서                   |
| 5   | `docs/portfolio/coach/slice12/part4_sonnet_results.json`           | Sonnet 15 case 결과         |
| 6   | `docs/portfolio/coach/slice12/part4_blind_eval.html`               | HTML eval 도구              |
| 7   | `docs/portfolio/coach/slice12/part4_blind_eval_input.json`         | A/B 랜덤화 input            |
| 8   | `docs/portfolio/coach/slice12/part4_blind_eval_truth.json`         | A/B 정답 (eval 후 unmask용) |
| 9   | `docs/portfolio/coach/slice12/part4_blind_eval_output.json`        | 병진 평가 결과              |
| 10  | `docs/portfolio/coach/slice12/part4_aggregate.json`                | 집계 보고                   |
| 11  | `docs/portfolio/coach/slice12/part4_closing.md`                    | 종결 보고                   |

테스트 신규: 0건 (eval 단계라 회귀 +0~5만 예상, smoke 스크립트의 idempotency 테스트 1~2건 가능)

---

## 8. KPI 9 분류 (cost 발생)

Part 4는 Sonnet LLM 호출 발생 → **KPI 9b cost ±30% 룰 적용**:

| 항목           | 값                                    |
| -------------- | ------------------------------------- |
| Expected       | 회귀 +0~5 (eval 단계, 코드 변경 최소) |
| Cost           | ~$0.34                                |
| KPI 9b         | cost ±30% 룰                          |
| Deviation 허용 | ±30% (no-cost 룰보다 엄격)            |

회귀가 +5 초과 시 사유 명시 (예: smoke 스크립트 idempotency 테스트 추가 등).

---

## 9. 실행 가드 (Claude Code 진입 전 확인)

```bash
# 1. 브랜치 + commit
git branch --show-current   # slice12
git log --oneline -1        # 8c5bb6d

# 2. clean tree
git status

# 3. Part 3 산출물 의존
ls docs/portfolio/coach/slice12/part3_smoke_results.json  # 필수
ls tests/scoring/fixtures/*.json | wc -l                  # 15

# 4. LLMClient 모델 지원 확인
python -c "from portfolio.services.llm_client import LLMClient; c = LLMClient(); print(c.SUPPORTED_MODELS)"
# claude-sonnet-4-5 포함 확인

# 5. CostGuard cap 여유
python -c "from portfolio.services.cost_guard import CostGuard; g = CostGuard.instance(); print(f'slice {g.slice_cost:.4f}, total {g.total_cost:.4f}')"

# 6. pre-commit hook
cat .git/hooks/pre-commit | grep ALLOWED_BRANCHES  # slice12 포함
```

---

## 10. 실행 절차 (Claude Code → 병진 → Claude Code 흐름)

| 단계       | 실행자      | 작업                                | 예상 시간 |
| ---------- | ----------- | ----------------------------------- | --------- |
| Step 0     | Claude Code | Sonnet 15 batch dump                | ~30분     |
| Step 1a    | Claude Code | input 빌드 + HTML 도구 작성         | ~30분     |
| Step 1b    | Claude Code | 회신 (Step 2 진입 전 확인)          | —         |
| **Step 2** | **병진**    | **Manual eval (HTML 도구 사용)**    | **~1.5h** |
| Step 2c    | 병진        | `part4_blind_eval_output.json` 저장 | —         |
| Step 3     | Claude Code | 집계 + 가설 검증 + closing 작성     | ~30분     |
| Step 4     | Claude Code | commit + 회신                       | —         |

**중간 체크포인트**: Step 1b 회신 시 병진이 HTML 도구 동작 확인 후 Step 2 진입.

---

## 11. 회신 필요 사항 (Claude Code → 병진)

### 11.1 Step 1b 회신 (Manual eval 진입 전)

1. Sonnet 15 case 결과 요약 (cost / latency / schema fitting)
2. HTML eval 도구 정상 동작 확인 (input 30 commentary 로드)
3. gate 4 case 표시 확인
4. CostGuard 잔여 cap

### 11.2 Step 4 최종 회신

1. commit hash
2. 회귀 변화 (668 → ?)
3. KPI 9b cost ±30% PASS/FAIL
4. IDENTICAL 7/7 PASS 여부
5. Part 4 단독 비용 + Slice 12 누적 + 전체 누적
6. LLM 호출 (목표 +15, 누적 34/50)
7. **글쓰기 가설 결과** (8/8 정착 / 7/8 반례)
8. **#60 결정** (active / hold) + gate_clarity 평균
9. 분포 폭 (#26 재발 여부)
10. 산출물 11건 체크리스트
11. `--no-verify` 사용 횟수 (목표 0)

---

## 12. Slice 12 종결 사이클 사전 등록 (Part 4 회신 후)

Part 4 종결 후 진입할 결정 사이클:

1. **D4-A.2 적용**: `docs/portfolio/coach/kpi_matrix.md`에 "component buildup +30~40" 신규 슬라이스 유형 등록
   - 근거: S12 누적 +88 (P1 +25 / P2 +36 / P3 +27)
   - 룰: "parametrize-heavy + 구조 빌드업 슬라이스" 분류
2. **누적 부채 처리 계획**:
   - #51 → Slice 13 Step 0 1순위
   - #59 E5 → Slice 13 Step 0 multi-debt mini 두 번째 사례 (#51과 동시)
   - #60 (Part 4 결정 의존) → active 시 Slice 13 작업 등록 / hold 시 백로그
3. **메모리 압축 B-Pattern**:
   - Line 20 (S12 Step 0) + 신규 entries (P1~P4) → 1~2 entry로 압축
   - 현재 메모리 21/30 → 압축 후 19~20/30 예상

---

## 13. 핵심 검증 룰 요약

| 검증            | 룰                      | 후속 액션              |
| --------------- | ----------------------- | ---------------------- |
| IDENTICAL       | 7/7 PASS 절대 사수      | FAIL 시 즉시 rollback  |
| KPI 9b cost     | 회귀 deviation ±30%     | OVER 시 사유 명시      |
| CostGuard slice | $1.00 미만              | 도달 시 sonnet 중단    |
| CostGuard total | $4.00 미만              | 도달 시 즉시 보고      |
| LLM cap         | 50 미만                 | 34/50 예상, 마진 16    |
| 글쓰기 가설 8/8 | haiku combined wins ≥ 8 | 8/8 정착 또는 7/8 반례 |
| #60 결정        | gate_clarity 평균 ≤ 3.0 | active or hold         |
| 분포 폭 #26     | nat/ins width ≥ 3.0     | < 3.0 시 재발 메모     |

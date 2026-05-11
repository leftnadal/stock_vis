# Slice 6 Part 4 작업 지시서 — Manual Eval 통합

> **목적**: Part 3에서 자동 단계로 측정 불가능한 질적 신호(naturalness/insight)를 인간 평가로 확보하고,
> winner 판정 + 글쓰기 가설 5/5 정착 검증 + V4 G6 분기 자동 처리를 한 사이클에 종결한다.
>
> **선행 결정 (Part 4 진입 전 확정)**:
>
> - 평가 범위 = **풀 매트릭스** (10 entries × naturalness/insight 2축 = 20 평점)
> - G6 처리 = **manual eval 후 자동 분기** (V4 vs V5 비교 기반)
> - winner 판정 = **efficiency (label_mean ÷ cost)** — Slice 1·3·4·5 일관
>
> **회귀 영향 정책**: Part 3와 동일. 코드 변경 0, scripts/slice6/ + docs만 추가.

---

## §0. 사전 체크 (5초)

```bash
# 브랜치 + 누적 회귀
git status
git log --oneline -5
pytest -q  # 395 passed 확인 (목표 KPI: 변화 없음)

# 입력 자료 확인
ls -la docs/portfolio/coach/slice6/step8_2way_e3_portfolio_raw.json
ls -la docs/portfolio/coach/slice6/step8_2way_e3_portfolio_scored.json
ls -la docs/portfolio/coach/slice6/step7_5_summary.md
```

- [ ] 395 passed
- [ ] raw.json 10 entries 존재
- [ ] scored.json stub 존재
- [ ] step7_5_summary.md 존재

---

## §1. Step 9.1 — Manual Eval 가이드 생성

### 1.1 평가 표 양식 생성 스크립트

`scripts/slice6/prepare_manual_eval.py` 생성:

````python
"""
Slice 6 Part 4 Step 9.1: manual eval 표 양식 생성

raw.json (10 entries) → eval_form.md (blind 평가 표) 변환.
- LLM provider 라벨 제거 (haiku/sonnet 구분 가림)
- entry 순서 randomize (seed=42 고정, 재현 가능)
- naturalness/insight 평점 입력 칸 제공 (1~5)
- preset_id는 V1~V5 표시 유지 (preset 외삽 분석에 필요)
"""

import json
import random
from pathlib import Path

RAW_PATH = Path("docs/portfolio/coach/slice6/step8_2way_e3_portfolio_raw.json")
OUT_PATH = Path("docs/portfolio/coach/slice6/step9_1_eval_form.md")
KEY_PATH = Path("docs/portfolio/coach/slice6/step9_1_eval_key.json")  # blind 해제용

def main():
    raw = json.loads(RAW_PATH.read_text(encoding="utf-8"))
    entries = raw["entries"] if isinstance(raw, dict) else raw
    assert len(entries) == 10, f"expected 10 entries, got {len(entries)}"

    # randomize with fixed seed (재현 가능)
    indexed = list(enumerate(entries))
    random.Random(42).shuffle(indexed)

    # blind key 저장 (eval_id → original_idx, provider)
    key_map = {}
    lines = ["# Slice 6 Part 4 Manual Eval Form\n"]
    lines.append("> **평가 방법**: 각 entry에 대해 naturalness (자연스러움) / insight (통찰력)를 1~5점으로 평가.")
    lines.append("> **blind**: provider 라벨 가림. preset_id만 노출 (외삽 분석용).")
    lines.append("> **scale**: 1=매우 부족, 2=부족, 3=보통, 4=좋음, 5=매우 좋음\n")
    lines.append("---\n")

    for eval_id, (orig_idx, entry) in enumerate(indexed, start=1):
        provider = entry.get("provider", "unknown")
        preset_id = entry.get("preset_id", "unknown")
        commentary = entry.get("commentary", entry.get("output", ""))
        key_map[str(eval_id)] = {
            "original_idx": orig_idx,
            "provider": provider,
            "preset_id": preset_id,
        }
        lines.append(f"## Eval #{eval_id} (preset={preset_id})\n")
        lines.append(f"```\n{commentary}\n```\n")
        lines.append(f"- naturalness: [   ] / 5")
        lines.append(f"- insight:     [   ] / 5\n")
        lines.append("---\n")

    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    KEY_PATH.write_text(json.dumps(key_map, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✓ eval form: {OUT_PATH} ({len(indexed)} entries)")
    print(f"✓ blind key: {KEY_PATH}")

if __name__ == "__main__":
    main()
````

### 1.2 실행

```bash
python scripts/slice6/prepare_manual_eval.py
```

**기대 출력**:

```
✓ eval form: docs/portfolio/coach/slice6/step9_1_eval_form.md (10 entries)
✓ blind key: docs/portfolio/coach/slice6/step9_1_eval_key.json
```

### 1.3 검증

- [ ] eval_form.md에 10 Eval # 블록 존재
- [ ] 각 블록에 naturalness / insight 입력 칸 존재
- [ ] provider 라벨 노출 없음 (preset_id만 노출 OK)
- [ ] eval_key.json에 10개 매핑 (eval_id → original_idx + provider + preset_id)

---

## §2. Step 9.2 — 병진 manual eval 수행

> **이 단계는 사용자(병진)가 수동으로 수행**. Claude Code는 대기.

### 2.1 평가 절차

1. `docs/portfolio/coach/slice6/step9_1_eval_form.md` 열기
2. 각 Eval #1 ~ #10에 대해 naturalness / insight 평가 입력 (1~5점)
3. 평가 완료 후 저장
4. 평가 결과를 `step9_2_eval_filled.md`로 복사 저장 (원본 보존)

### 2.2 평가 기준 (가이드)

- **naturalness (자연스러움)**: 한국 개인 투자자가 읽었을 때 어색함 없이 자연스럽게 흘러가는가?
  - 1점: 기계 번역 같음, 어색한 표현 다수
  - 3점: 무난, 약간 어색한 부분 있음
  - 5점: 사람이 쓴 것처럼 자연스러움

- **insight (통찰력)**: 포트폴리오 지표(hhi/sector_hhi/top3_weight 등)를 의미 있게 해석하는가?
  - 1점: 숫자만 나열, 통찰 없음
  - 3점: 기본 해석만 제공
  - 5점: 지표 간 관계 + preset 의도 반영 + 행동 시사점 명확

### 2.3 예상 소요

- entry당 ~1.5분 × 10 = **약 15~25분**

---

## §3. Step 9.3 — 평가 결과 파싱 + 자동 분기 처리

### 3.1 파서 + 분기 스크립트

`scripts/slice6/score_step9.py` 생성:

```python
"""
Slice 6 Part 4 Step 9.3: manual eval 결과 파싱 + 자동 분기 처리

step9_2_eval_filled.md → step9_3_scored.json
- naturalness/insight 평점 추출
- blind 해제 (eval_key.json 매핑)
- efficiency 계산 (label_mean ÷ cost) — Slice 1·3·4·5 일관
- V4 vs V5 비교 → G6 자동 분기 처리
- winner 판정 (haiku vs sonnet, efficiency 우위)
- 글쓰기 가설 5/5 정착 검증
"""

import json
import re
from pathlib import Path
from collections import defaultdict

FILLED_PATH = Path("docs/portfolio/coach/slice6/step9_2_eval_filled.md")
KEY_PATH = Path("docs/portfolio/coach/slice6/step9_1_eval_key.json")
RAW_PATH = Path("docs/portfolio/coach/slice6/step8_2way_e3_portfolio_raw.json")
SCORED_PATH = Path("docs/portfolio/coach/slice6/step9_3_scored.json")
REPORT_PATH = Path("docs/portfolio/coach/slice6/step9_3_report.md")

EVAL_BLOCK = re.compile(
    r"##\s*Eval\s*#(\d+).*?naturalness:\s*\[?\s*(\d+(?:\.\d+)?)\s*\]?.*?insight:\s*\[?\s*(\d+(?:\.\d+)?)\s*\]?",
    re.DOTALL,
)


def parse_eval_form(text: str) -> dict:
    """eval_form 파싱 → {eval_id: {naturalness, insight}}"""
    results = {}
    for match in EVAL_BLOCK.finditer(text):
        eid, nat, ins = match.group(1), float(match.group(2)), float(match.group(3))
        # 1~5 범위 검증
        assert 1 <= nat <= 5, f"naturalness out of range at eval #{eid}: {nat}"
        assert 1 <= ins <= 5, f"insight out of range at eval #{eid}: {ins}"
        results[eid] = {"naturalness": nat, "insight": ins}
    return results


def load_costs(raw_path: Path) -> dict:
    """raw.json → {original_idx: cost_usd}"""
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    entries = raw["entries"] if isinstance(raw, dict) else raw
    return {i: e.get("cost_usd", 0.0) for i, e in enumerate(entries)}


def main():
    filled_text = FILLED_PATH.read_text(encoding="utf-8")
    key_map = json.loads(KEY_PATH.read_text(encoding="utf-8"))
    costs = load_costs(RAW_PATH)

    parsed = parse_eval_form(filled_text)
    assert len(parsed) == 10, f"expected 10 evals, got {len(parsed)}"

    # blind 해제 + 비용 결합
    entries = []
    for eid, scores in parsed.items():
        meta = key_map[eid]
        orig_idx = meta["original_idx"]
        provider = meta["provider"]
        preset_id = meta["preset_id"]
        cost = costs[orig_idx]
        label_mean = (scores["naturalness"] + scores["insight"]) / 2
        efficiency = label_mean / cost if cost > 0 else 0.0
        entries.append({
            "eval_id": int(eid),
            "original_idx": orig_idx,
            "provider": provider,
            "preset_id": preset_id,
            "naturalness": scores["naturalness"],
            "insight": scores["insight"],
            "label_mean": round(label_mean, 4),
            "cost_usd": round(cost, 6),
            "efficiency": round(efficiency, 2),
        })

    # provider별 집계
    by_provider = defaultdict(list)
    for e in entries:
        by_provider[e["provider"]].append(e)

    provider_stats = {}
    for prov, es in by_provider.items():
        label_means = [e["label_mean"] for e in es]
        costs_list = [e["cost_usd"] for e in es]
        effs = [e["efficiency"] for e in es]
        provider_stats[prov] = {
            "n": len(es),
            "label_mean_avg": round(sum(label_means) / len(label_means), 4),
            "cost_avg": round(sum(costs_list) / len(costs_list), 6),
            "efficiency_avg": round(sum(effs) / len(effs), 2),
            "naturalness_avg": round(sum(e["naturalness"] for e in es) / len(es), 4),
            "insight_avg": round(sum(e["insight"] for e in es) / len(es), 4),
        }

    # winner 판정 (efficiency 우위)
    haiku_eff = provider_stats.get("anthropic_haiku", {}).get("efficiency_avg", 0)
    sonnet_eff = provider_stats.get("anthropic_sonnet", {}).get("efficiency_avg", 0)
    winner = "haiku" if haiku_eff > sonnet_eff else "sonnet"
    eff_gap_pct = round((haiku_eff - sonnet_eff) / sonnet_eff * 100, 2) if sonnet_eff > 0 else None

    # 글쓰기 가설 5/5 정착 검증
    # 가설: S1 E1, S3 E2, S4 E6, S5 E3 모두 winner=haiku.
    # S6 e3_portfolio도 winner=haiku면 5/5 정착.
    hypothesis_5_of_5 = (winner == "haiku")

    # G6 자동 분기 (V4 vs V5)
    # V4 = concentrated_value (fixture expected=aligned, LLM=partial)
    # V5 = aligned (fixture expected=aligned, LLM=aligned)
    # V4 label_mean ≥ V5 label_mean → LLM partial 평가 합리적 → fixture aligned→partial 수정
    # V4 < V5 → Buffett 스타일 차별성 약함 → fixture 유지 + 부채 등록
    v4_label = [e["label_mean"] for e in entries if e["preset_id"] == "V4"]
    v5_label = [e["label_mean"] for e in entries if e["preset_id"] == "V5"]
    v4_avg = sum(v4_label) / len(v4_label) if v4_label else None
    v5_avg = sum(v5_label) / len(v5_label) if v5_label else None

    if v4_avg is not None and v5_avg is not None:
        if v4_avg >= v5_avg:
            g6_resolution = "fixture_update"  # aligned → partial 수정
            g6_action = (
                f"V4 label_mean {v4_avg:.4f} ≥ V5 {v5_avg:.4f} → "
                f"LLM partial 평가가 합리적. concentrated_value fixture expected=aligned → partial 수정."
            )
            g6_debt_delta = -1  # 분기 해소
        else:
            g6_resolution = "fixture_keep_with_debt"  # 유지 + 부채 등록
            g6_action = (
                f"V4 label_mean {v4_avg:.4f} < V5 {v5_avg:.4f} → "
                f"Buffett 스타일 차별성 약함. fixture 유지 + prompt 튜닝 부채 #23 등록 (PS 2.0)."
            )
            g6_debt_delta = +1  # 신규 부채
    else:
        g6_resolution = "indeterminate"
        g6_action = "V4 or V5 entries missing — manual review required."
        g6_debt_delta = 0

    # preset 외삽 robustness (haiku만 — Slice 5와 비교)
    # Slice 5 e3: haiku insight 그룹차 ≤ 0.50 (small_diff). S6 e3_portfolio도 동일한지 확인.
    haiku_entries = by_provider.get("anthropic_haiku", [])
    haiku_by_preset = defaultdict(list)
    for e in haiku_entries:
        haiku_by_preset[e["preset_id"]].append(e["insight"])
    haiku_insight_means = {p: sum(v) / len(v) for p, v in haiku_by_preset.items()}
    if haiku_insight_means:
        max_i = max(haiku_insight_means.values())
        min_i = min(haiku_insight_means.values())
        haiku_insight_gap = round(max_i - min_i, 4)
    else:
        haiku_insight_gap = None
    robust_safe = haiku_insight_gap is not None and haiku_insight_gap <= 0.50

    # 결과 저장
    result = {
        "entries": entries,
        "provider_stats": provider_stats,
        "winner": winner,
        "winner_efficiency_gap_pct": eff_gap_pct,
        "writing_hypothesis_5_of_5": hypothesis_5_of_5,
        "g6_resolution": g6_resolution,
        "g6_action": g6_action,
        "g6_debt_delta": g6_debt_delta,
        "g6_v4_label_mean": round(v4_avg, 4) if v4_avg else None,
        "g6_v5_label_mean": round(v5_avg, 4) if v5_avg else None,
        "preset_extrapolation_haiku_insight_gap": haiku_insight_gap,
        "preset_extrapolation_safe": robust_safe,
        "preset_extrapolation_slice5_baseline": 0.50,
    }
    SCORED_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    # 리포트
    md = [
        "# Slice 6 Part 4 Step 9.3 — Manual Eval 결과 보고\n",
        "## Provider 집계\n",
        "| provider | n | label_mean | cost_avg | efficiency | naturalness | insight |",
        "|---|---|---|---|---|---|---|",
    ]
    for prov, st in provider_stats.items():
        md.append(
            f"| {prov} | {st['n']} | {st['label_mean_avg']} | ${st['cost_avg']} | "
            f"{st['efficiency_avg']} | {st['naturalness_avg']} | {st['insight_avg']} |"
        )

    md.append("\n## Winner 판정")
    md.append(f"- winner: **{winner}** (efficiency gap = {eff_gap_pct}%)")
    md.append(f"- 글쓰기 가설 5/5 정착: {'**PASS** ✓' if hypothesis_5_of_5 else '**FAIL** ✗'}")

    md.append("\n## G6 (V4 alignment) 자동 분기")
    md.append(f"- resolution: **{g6_resolution}**")
    md.append(f"- action: {g6_action}")
    md.append(f"- 부채 변화량: {g6_debt_delta:+d}")

    md.append("\n## Preset 외삽 robustness (haiku, Slice 5 비교)")
    md.append(f"- haiku insight 그룹차: {haiku_insight_gap} (Slice 5 baseline ≤ 0.50)")
    md.append(f"- 판정: {'**SAFE** ✓' if robust_safe else '**WARN** ⚠'}")

    md.append("\n## 개별 평가 (eval_id 순)")
    md.append("| eval_id | preset | provider | nat | ins | label_mean | cost | efficiency |")
    md.append("|---|---|---|---|---|---|---|---|")
    for e in sorted(entries, key=lambda x: x["eval_id"]):
        md.append(
            f"| {e['eval_id']} | {e['preset_id']} | {e['provider']} | {e['naturalness']} | "
            f"{e['insight']} | {e['label_mean']} | ${e['cost_usd']} | {e['efficiency']} |"
        )

    REPORT_PATH.write_text("\n".join(md), encoding="utf-8")
    print(f"✓ scored: {SCORED_PATH}")
    print(f"✓ report: {REPORT_PATH}")
    print(f"  winner: {winner} (eff gap {eff_gap_pct}%)")
    print(f"  hypothesis 5/5: {hypothesis_5_of_5}")
    print(f"  G6: {g6_resolution} (debt delta {g6_debt_delta:+d})")
    print(f"  extrapolation: insight gap {haiku_insight_gap} ({'SAFE' if robust_safe else 'WARN'})")


if __name__ == "__main__":
    main()
```

### 3.2 실행 (병진 평가 완료 후)

```bash
# 평가 결과를 step9_2_eval_filled.md로 저장한 뒤
python scripts/slice6/score_step9.py
```

### 3.3 검증 체크리스트

- [ ] scored.json에 10 entries 존재
- [ ] provider_stats에 haiku/sonnet 각 5건
- [ ] winner 필드 확정 (haiku 또는 sonnet)
- [ ] writing_hypothesis_5_of_5 boolean 확정
- [ ] g6_resolution = fixture_update / fixture_keep_with_debt / indeterminate 중 하나
- [ ] preset_extrapolation_safe boolean 확정
- [ ] step9_3_report.md 가독성 검증

---

## §4. Step 9.4 — G6 분기 후속 작업

### 4.1 g6_resolution = "fixture_update" 인 경우 (V4 ≥ V5)

```python
# scripts/slice6/apply_g6_fixture_update.py
"""
G6 분기: fixture aligned → partial 수정.
대상: tests/fixtures/portfolio/preset_alignment/V4_concentrated_value.json
영향: 회귀 hash 변화 가능 → 재실행 필요.
"""
```

작업 순서:

1. V4 fixture의 `expected_alignment`를 `aligned` → `partial`로 수정
2. 관련 회귀 테스트 재실행 → `pytest -q tests/portfolio/`
3. 회귀 변화 확인 (목표: 395 → 395 유지, V4 fixture 검증만 갱신)
4. commit: `fix(slice6/part4): V4 concentrated_value fixture aligned→partial (G6 resolution)`

### 4.2 g6_resolution = "fixture_keep_with_debt" 인 경우 (V4 < V5)

부채 등록 (메모리 + 백로그 문서):

```
#23 concentrated_value preset prompt 튜닝 (PS 2.0)
- 원인: V4 label_mean < V5 label_mean → Buffett 스타일 차별성 약함
- 조치: prompt에 "intentional concentration" 명시 강화
- 슬롯: Slice 7 Step 0 또는 Slice 8
```

### 4.3 g6_resolution = "indeterminate" 인 경우

- 사용자에게 알림: "V4 또는 V5 entries 누락. eval_form 재확인 필요."
- Part 4 종결 보류

---

## §5. Step 10 — Slice 6 종결 보고

### 5.1 종결 보고서 작성

`docs/portfolio/coach/slice6/slice6_final_report.md`:

```markdown
# Slice 6 (concentrated_portfolio E3) 최종 종결 보고

## KPI 종합

- 회귀: 395 → ??? (Step 9.4 후 확정)
- 누적 광의 비용: $0.879 (Part 4 LLM 호출 0)
- KPI 8/8 자동 + manual 4 = 12/12 (winner / 가설 / G6 / 외삽)

## Winner & 가설

- winner: {winner}
- efficiency gap: {gap}%
- 글쓰기 가설 5/5 정착: {PASS/FAIL}
  - S1 E1·S3 E2·S4 E6·S5 E3·S6 e3_portfolio = haiku winner (목표)

## Preset 외삽 robustness

- haiku insight 그룹차: {gap} (Slice 5 baseline 0.50)
- 5슬라이스 efficiency 추세: S1 142% → S4 181% → S5 145% → S6 {gap}%

## G6 처리

- resolution: {fixture_update / fixture_keep_with_debt / indeterminate}
- 부채 변화량: {-1 / +1 / 0}

## Slice 7 진입점 재평가

- 사전 등록: E4 대화 Q&A
- 재평가 신호: G6 처리 결과에 따라
  - fixture_update + 가설 5/5 → E4 그대로 진입
  - fixture_keep_with_debt → Slice 7 Step 0에서 #23 처리 후 E4
```

### 5.2 commit 메시지

```
feat(slice6/part4/step9.1): manual eval form 생성 (10 entries blind)
feat(slice6/part4/step9.3): manual eval 결과 파싱 + winner/G6/외삽 자동 분기
fix(slice6/part4/step9.4): {G6 resolution별 차등 commit}
docs(slice6/part4/step10): Slice 6 최종 종결 보고
```

---

## §6. 회귀 영향 KPI

| 단계                | 회귀 영향                                             | 비용 | 부채 변화  |
| ------------------- | ----------------------------------------------------- | ---- | ---------- |
| §1 (eval form 생성) | 0 (scripts/docs only)                                 | $0   | 0          |
| §2 (병진 평가)      | 0                                                     | $0   | 0          |
| §3 (score + 분기)   | 0 (scripts/docs only)                                 | $0   | 0          |
| §4 (G6 후속)        | fixture_update 시 회귀 재실행 (변화 없을 것으로 예상) | $0   | -1 또는 +1 |
| §5 (종결 보고)      | 0 (docs only)                                         | $0   | 0          |

**총 회귀 변화 예상**: 0 (G6 fixture_update 시 V4 fixture 갱신은 회귀 hash에 영향 없음 — Slice 1 e1 / Slice 3 e2 IDENTICAL hash와 분리)

---

## §7. 완료 보고 양식 (§I~§V — Part 3과 동일 양식)

```
[Slice 6 Part 4 완료 보고]

== Step 9.1 (Eval Form 생성) ==
- eval_form.md 10 entries blind: ✓
- eval_key.json 매핑 10건: ✓

== Step 9.2 (Manual Eval 수행) ==
- 병진 평가 완료: ✓
- 평점 범위 1~5 검증: ✓

== Step 9.3 (Score + 자동 분기) ==
- provider_stats: haiku/sonnet 각 5건
- winner: ???
- efficiency gap: ???%
- writing hypothesis 5/5: ???
- g6_resolution: ???
- preset 외삽 insight gap: ???

== Step 9.4 (G6 후속) ==
- 경로: fixture_update / fixture_keep_with_debt / indeterminate
- 회귀: 395 → ???

== Step 10 (Slice 6 종결) ==
- 최종 회귀: ???
- 누적 광의 비용: $???
- Slice 7 진입점 재평가 결과: ???

§I. 산출물 (5~7건)
§II. G6 분기 처리 결과
§III. Slice 6 → Slice 7 핸드오프
§IV. Commit 메시지 권장
§V. 핵심 결과 (글쓰기 가설 정착 여부 / efficiency 추세 / 부채 변화)
```

---

## §8. 분기 시나리오 (Part 4 안에서)

| 시나리오 | 트리거                                | 조치                                    |
| -------- | ------------------------------------- | --------------------------------------- |
| H1       | eval_form 파싱 실패 (정규식 미스매치) | 정규식 디버그, manual eval 양식 재확인  |
| H2       | winner = sonnet (가설 깨짐)           | 즉시 보고, Part 5 추가 manual eval 검토 |
| H3       | preset 외삽 insight gap > 0.50        | Slice 7 진입 전 추가 검증 슬롯 추가     |
| H4       | G6 = indeterminate                    | V4/V5 entries 누락 점검, 재평가         |

---

## §9. 완료 기준 (Part 4 종결 조건)

- [x] eval_form.md 10 entries 생성
- [ ] 병진 평가 완료 (10 × 2 = 20 평점)
- [ ] score_step9.py 실행 + scored.json + report.md 생성
- [ ] g6_resolution 자동 결정 (fixture_update / fixture_keep_with_debt)
- [ ] G6 후속 작업 완료 (fixture 수정 또는 부채 등록)
- [ ] slice6_final_report.md 작성
- [ ] commit 4건 완료
- [ ] 누적 광의 비용 $0.879 유지 ($1.00 임계 12% 마진)

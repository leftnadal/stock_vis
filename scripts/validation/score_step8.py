"""
Slice 1 Part 2 — Step 8 점수 산출 (Slice 2 Step 9에서 entrypoint 일반화).

산식 (entrypoint별):
  e1 (Slice 1, 글쓰기 차원):
    1차 필터:  schema_pass=True AND naturalness>=3 AND insight>=3
    2차 efficiency:  sqrt(naturalness * insight) / sqrt(cost_usd * latency_s)
    Fallback: 0.25/0.25/0.25/0.15/0.10 (schema/n/i/cost_inv/lat_inv) — 동적 normalize
  e5 (Slice 2, 추출 차원):
    1차 필터:  schema_pass=True AND intent>=3 AND no_extra>=3
              AND cost<=$0.020 AND latency<=5000ms
    2차 efficiency:  sqrt(intent_match * no_extra_changes) — cost/lat은 임계로 분리
    Fallback: 동일 가중, 정적 normalize (THRESHOLDS 기반)
    → score_step8_e5.py로 위임 (Slice 3 진입 시 통합 가능)

Usage:
    python -m scripts.validation.score_step8                  # default e1 (Slice 1)
    python -m scripts.validation.score_step8 --entrypoint e5  # Slice 2 (delegate)
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

# Slice 2 Step 9 일반화 — entrypoint별 메타데이터 단일 출처.
# 새 entrypoint 추가 시 (예: e2 진단 카드) 여기 한 곳만 갱신.
DIMENSION_LOOKUP = {
    "e1": {
        "dim1": {"key": "naturalness", "manual_field": "naturalness"},
        "dim2": {"key": "insight", "manual_field": "insight"},
        "model_label_field": "label",
        "result_structure": "flat",  # naturalness/insight 등이 result 최상위
        "default_raw": "docs/portfolio/coach/slice1/step8_3way_raw.json",
        "default_scored": "docs/portfolio/coach/slice1/step8_3way_scored.json",
        "weight": 0.5,
    },
    "e5": {
        "dim1": {"key": "intent_match", "manual_field": "intent_match_manual"},
        "dim2": {"key": "no_extra_changes", "manual_field": "no_extra_changes_manual"},
        "model_label_field": "model_label",
        "result_structure": "nested",  # judgments + metadata 분리
        "default_raw": "docs/portfolio/coach/slice2/step8_2way_e5_raw.json",
        "default_scored": "docs/portfolio/coach/slice2/step8_2way_e5_scored.json",
        "weight": 0.5,
        "delegated_to": "scripts.validation.score_step8_e5",
    },
    "e2": {  # Slice 3 — e1 산식 그대로 + completeness 자동 보강 (additional_lex_check)
        "dim1": {"key": "naturalness", "manual_field": "naturalness_manual"},
        "dim2": {"key": "insight", "manual_field": "insight_manual"},
        "model_label_field": "model_label",
        "result_structure": "nested",  # judgments + metadata 분리
        "default_raw": "docs/portfolio/coach/slice3/step8_2way_e2_raw.json",
        "default_scored": "docs/portfolio/coach/slice3/step8_2way_e2_scored.json",
        "weight": 0.5,
        "additional_lex_check": "completeness_auto",  # Q3.C 자동 측정
    },
    "e6": {  # Slice 4 — e2 패턴 mirror (글쓰기 + completeness 자동)
        "dim1": {"key": "naturalness", "manual_field": "naturalness_manual"},
        "dim2": {"key": "insight", "manual_field": "insight_manual"},
        "model_label_field": "model_label",
        "result_structure": "nested",  # judgments + metadata 분리 (E2 mirror)
        "default_raw": "docs/portfolio/coach/slice4/step8_2way_e6_raw.json",
        "default_scored": "docs/portfolio/coach/slice4/step8_2way_e6_scored.json",
        "weight": 0.5,
        "additional_lex_check": "completeness_auto",  # E2 mirror
    },
    "e3": {  # Slice 5 — e2/e6 패턴 mirror (글쓰기 + completeness 자동)
        "dim1": {"key": "naturalness", "manual_field": "naturalness_manual"},
        "dim2": {"key": "insight", "manual_field": "insight_manual"},
        "model_label_field": "model_label",
        "result_structure": "nested",  # judgments + metadata 분리
        "default_raw": "docs/portfolio/coach/slice5/step8_2way_e3_raw.json",
        "default_scored": "docs/portfolio/coach/slice5/step8_2way_e3_scored.json",
        "weight": 0.5,
        "additional_lex_check": "completeness_auto",  # E2/E6 mirror — comments ≥ 1
    },
    "e3_portfolio": {  # Slice 6 Part 1 Step 1 — e3 mirror 100% (path만 변경)
        "dim1": {"key": "naturalness", "manual_field": "naturalness_manual"},
        "dim2": {"key": "insight", "manual_field": "insight_manual"},
        "model_label_field": "model_label",
        "result_structure": "nested",
        "default_raw": "docs/portfolio/coach/slice6/step8_2way_e3_portfolio_raw.json",
        "default_scored": "docs/portfolio/coach/slice6/step8_2way_e3_portfolio_scored.json",
        "weight": 0.5,
        "additional_lex_check": "completeness_auto",  # E3 mirror
    },
    "e4_conversation": {  # Slice 7 Part 4 §1 — e3_portfolio mirror + tier_aware
        "dim1": {"key": "naturalness", "manual_field": "naturalness_manual"},
        "dim2": {"key": "insight", "manual_field": "insight_manual"},
        "model_label_field": "model_label",
        "result_structure": "nested",
        "default_raw": "docs/portfolio/coach/slice7/step8_2way_e4_conversation_raw.json",
        "default_scored": "docs/portfolio/coach/slice7/step8_2way_e4_conversation_scored.json",
        "weight": 0.5,
        "additional_lex_check": "completeness_auto",  # E3 mirror
        "tier_aware": True,  # Slice 7 신규 — score_final.py에서 Tier별 보조 분석에 참조
    },
}


RAW_PATH = Path(DIMENSION_LOOKUP["e1"]["default_raw"])
SCORED_PATH = Path(DIMENSION_LOOKUP["e1"]["default_scored"])


def lexicographic_filter(r: dict) -> bool:
    return (
        r.get("schema_pass") is True
        and isinstance(r.get("naturalness"), (int, float))
        and r["naturalness"] >= 3
        and isinstance(r.get("insight"), (int, float))
        and r["insight"] >= 3
    )


def efficiency_score(r: dict) -> float:
    n = r["naturalness"]
    i = r["insight"]
    c = max(r.get("cost_usd") or 1e-6, 1e-6)
    lat_s = max((r.get("latency_ms") or 1) / 1000.0, 1e-6)
    return math.sqrt(n * i) / math.sqrt(c * lat_s)


def fallback_score(r: dict, all_results: list[dict]) -> float:
    schema = 1.0 if r.get("schema_pass") else 0.0
    n_norm = (r.get("naturalness") or 0) / 5.0
    i_norm = (r.get("insight") or 0) / 5.0

    costs = [x["cost_usd"] for x in all_results if x.get("cost_usd") is not None]
    latencies = [x["latency_ms"] for x in all_results if x.get("latency_ms") is not None]
    if not costs or not latencies:
        return 0.0
    max_c, min_c = max(costs), min(costs)
    max_l, min_l = max(latencies), min(latencies)
    cost_v = r.get("cost_usd")
    lat_v = r.get("latency_ms")
    if cost_v is None or lat_v is None:
        return 0.0
    cost_inv = (max_c - cost_v) / (max_c - min_c) if max_c > min_c else 1.0
    lat_inv = (max_l - lat_v) / (max_l - min_l) if max_l > min_l else 1.0
    return (
        0.25 * schema
        + 0.25 * n_norm
        + 0.25 * i_norm
        + 0.15 * cost_inv
        + 0.10 * lat_inv
    )


def _normalize_results(results: list[dict], structure: str) -> list[dict]:
    """Result structure에 따라 flat dict 리스트로 변환 (Slice 4 Step 9 통합).

    flat (e1): 그대로 반환 (raw 필드가 이미 flat).
    nested (e2/e6): judgments + metadata → flat dict로 평탄화.

    Raises:
        ValueError: 미등록 structure
    """
    if structure == "flat":
        return list(results)
    if structure == "nested":
        flat: list[dict] = []
        for r in results:
            if "error" in r:
                flat.append({
                    "label": r.get("model_label"),
                    "fixture": r.get("fixture"),
                    "fixture_group": r.get("fixture_group"),
                    "schema_pass": False,
                    "completeness_auto": False,
                    "naturalness": None,
                    "insight": None,
                    "cost_usd": None,
                    "latency_ms": None,
                    "error": r["error"],
                })
                continue
            j = r.get("judgments", {}) or {}
            m = r.get("metadata", {}) or {}
            flat.append({
                "label": r["model_label"],
                "fixture": r["fixture"],
                "fixture_group": r.get("fixture_group"),
                "schema_pass": j.get("schema_pass"),
                "completeness_auto": j.get("completeness_auto"),
                "naturalness": j.get("naturalness_manual"),
                "insight": j.get("insight_manual"),
                "cost_usd": m.get("cost_usd"),
                "latency_ms": m.get("latency_ms"),
                "fallback_from": m.get("fallback_from"),
            })
        return flat
    raise ValueError(f"Unknown result_structure: {structure!r}")


def _build_lex_filter(additional_check: str | None):
    """e1 base lex (schema + nat>=3 + ins>=3) + optional additional_check.

    additional_check 예: "completeness_auto" (e2/e6용).
    """
    def _filter(r: dict) -> bool:
        if not lexicographic_filter(r):
            return False
        if additional_check and not r.get(additional_check):
            return False
        return True
    return _filter


def _build_output_dict(
    entrypoint: str,
    scored: list[dict],
    label_means: dict[str, float],
    use_fallback: bool,
    winner: str | None,
) -> dict:
    """entrypoint별 출력 형식 분기 (IDENTICAL 보존 KPI).

    e1: scored_results / label_means / use_fallback / winner (4 키)
    e2/e6: scored_at / scored_results / label_means / use_fallback / winner / thresholds (6 키)
    """
    if entrypoint == "e1":
        return {
            "scored_results": scored,
            "label_means": label_means,
            "use_fallback": use_fallback,
            "winner": winner,
        }
    # e2 / e6 — Slice 3·4 형식 (scored_at + thresholds 추가)
    return {
        "scored_at": "2026-05-07",
        "scored_results": scored,
        "label_means": label_means,
        "use_fallback": use_fallback,
        "winner": winner,
        "thresholds": {
            "naturalness_min": 3,
            "insight_min": 3,
            "completeness_auto_required": True,
        },
    }


def _main_unified(entrypoint: str) -> int:
    """e1/e2/e6 통합 score 산출 (Slice 4 Step 9 백로그 #2 PS 3.0).

    e5는 산식 본질 차이로 delegation 유지 (`score_step8_e5.main()`).

    구조:
      1. config 로드 (DIMENSION_LOOKUP 메타)
      2. raw → _normalize_results (flat/nested 분기)
      3. _build_lex_filter (additional_check 분기)
      4. efficiency / fallback / label_means 산출 (e1 헬퍼 재사용)
      5. _build_output_dict (entrypoint별 출력 형식 — IDENTICAL 보존)

    회귀 KPI: Slice 1 e1 / Slice 3 e2 산출물 hash IDENTICAL 유지.
    """
    config = DIMENSION_LOOKUP[entrypoint]
    raw_path = Path(config["default_raw"])
    scored_path = Path(config["default_scored"])

    if not raw_path.exists():
        print(f"[ERROR] {raw_path} 없음.")
        return 1

    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    flat_results = _normalize_results(raw["results"], config["result_structure"])

    # 수동 평가 누락 검증
    missing = [
        f"{r.get('label')}×{r.get('fixture')}"
        for r in flat_results
        if not r.get("error")
        and (r.get("naturalness") is None or r.get("insight") is None)
    ]
    if missing:
        print(f"[ERROR] 다음 entry 평가 미완료: {missing}")
        return 1

    lex_filter = _build_lex_filter(config.get("additional_lex_check"))
    passed = [r for r in flat_results if lex_filter(r)]
    use_fallback = len(passed) == 0

    print("=" * 60)
    print(f"Step 8 {entrypoint.upper()} Scoring Result (unified)")
    print("=" * 60)
    if config.get("additional_lex_check"):
        print(
            f"\n1차 필터 통과 (schema+nat≥3+ins≥3+{config['additional_lex_check']}): "
            f"{len(passed)} / {len(flat_results)}"
        )
    else:
        print(f"\n1차 필터 통과: {len(passed)} / {len(flat_results)}")
    print(f"Mode: {'FALLBACK' if use_fallback else 'EFFICIENCY'}")

    scored: list[dict] = []
    for r in flat_results:
        if use_fallback:
            score = fallback_score(r, flat_results)
            score_type = "fallback"
        elif lex_filter(r):
            score = efficiency_score(r)
            score_type = "efficiency"
        else:
            score = None
            score_type = "filtered_out"
        scored.append({**r, "score": score, "score_type": score_type})

    # Per label (gemini/sonnet/haiku) 평균
    label_scores: dict[str, list[float]] = defaultdict(list)
    for r in scored:
        if r["score"] is not None:
            label_scores[r.get("label") or r.get("provider", "?")].append(r["score"])
    label_means: dict[str, float] = {
        label: sum(v) / len(v) for label, v in label_scores.items() if v
    }
    winner = max(label_means.items(), key=lambda x: x[1])[0] if label_means else None

    # 콘솔 표
    has_completeness = config.get("additional_lex_check") == "completeness_auto"
    print("\n=== Per Call ===")
    if has_completeness:
        header = (
            f"{'Fixture':<22} {'Label':<8} {'Schema':>6} {'Comp':>5} "
            f"{'Nat':>4} {'Ins':>4} {'Cost':>9} {'Lat(s)':>7} {'Score':>10}"
        )
    else:
        header = (
            f"{'Fixture':<14} {'Label':<8} {'Schema':>6} {'Nat':>4} {'Ins':>4} "
            f"{'Cost':>9} {'Lat(s)':>7} {'Score':>10} {'Type':<14}"
        )
    print(header)
    for r in scored:
        score_str = f"{r['score']:.2f}" if r["score"] is not None else "-"
        sch = "OK" if r.get("schema_pass") else "FAIL"
        cost = r.get("cost_usd") or 0
        lat_s = (r.get("latency_ms") or 0) / 1000
        nat = r.get("naturalness") if r.get("naturalness") is not None else "-"
        ins = r.get("insight") if r.get("insight") is not None else "-"
        if has_completeness:
            comp = "OK" if r.get("completeness_auto") else "FAIL"
            print(
                f"{r.get('fixture','') or '':<22} {r.get('label','') or '':<8} "
                f"{sch:>6} {comp:>5} {nat!s:>4} {ins!s:>4} "
                f"${cost:>7.5f} {lat_s:>7.2f} {score_str:>10}"
            )
        else:
            print(
                f"{r.get('fixture','') or '':<14} {r.get('label','') or '':<8} "
                f"{sch:>6} {nat!s:>4} {ins!s:>4} "
                f"${cost:>7.5f} {lat_s:>7.2f} {score_str:>10} {r['score_type']:<14}"
            )

    print("\n=== Per Label (mean score) ===")
    for label, m in sorted(label_means.items(), key=lambda x: -x[1]):
        print(f"  {label:<8}: {m:.4f}  (n={len(label_scores[label])})")
    if winner:
        print(f"\n[WINNER] {winner}")

    output = _build_output_dict(entrypoint, scored, label_means, use_fallback, winner)
    scored_path.parent.mkdir(parents=True, exist_ok=True)
    scored_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n[Saved] {scored_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--entrypoint",
        choices=list(DIMENSION_LOOKUP),
        default="e1",
        help="평가 진입점 (default: e1). e5는 score_step8_e5에 위임. e1/e2/e6는 _main_unified.",
    )
    args = parser.parse_args()

    # e5 → score_step8_e5에 delegation (산식 본질 차이로 별도 모듈 유지)
    if args.entrypoint == "e5":
        from scripts.validation import score_step8_e5
        return score_step8_e5.main()

    # e1/e2/e6 → _main_unified (Slice 4 Step 9 백로그 #2 PS 3.0 통합)
    return _main_unified(args.entrypoint)


# Backwards compatibility — 기존 호출자가 _main_e2() 직접 사용했을 가능성 (없음)
def _main_e2() -> int:
    """[Deprecated] Slice 4 Step 9 통합 — _main_unified('e2') 호출로 대체."""
    return _main_unified("e2")


if __name__ == "__main__":
    sys.exit(main())

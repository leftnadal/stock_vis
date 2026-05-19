"""Slice 11+ Manual Eval Shuffle Script (D2-A blind).

- 입력: part{N}_matrix.json
- 출력: part{N}_shuffled_view.md + part{N}_label_mapping.json
- seed=42 고정 (재현성)
- Slice 12+ 매트릭스 슬라이스 manual eval 자연 재활용
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


def shuffle_matrix(
    matrix_json_path: Path,
    output_dir: Path,
    seed: int = 42,
    prefix: str = "part5",
) -> None:
    """24 케이스를 무순으로 셔플하여 blind view 생성."""
    with open(matrix_json_path, encoding="utf-8") as f:
        data = json.load(f)

    cases = data["cases"]
    indices = list(range(len(cases)))
    rng = random.Random(seed)
    rng.shuffle(indices)

    view_lines = [f"# Slice 11 {prefix.capitalize()} — Manual Eval Blind View (D2-A)", ""]
    view_lines.append(f"**Total cases**: {len(cases)}, **Seed**: {seed}")
    view_lines.append("")
    view_lines.append(
        "> **평가 가이드**: `manual_eval_rubric.md` 참조 "
        "(3축 하이브리드: nat 1~5 / ins 1~5 / actionability OK·NG·N/A)"
    )
    view_lines.append(">")
    view_lines.append("> **blind 유지**: 평가 완료까지 `label_mapping.json` 열지 말 것")
    view_lines.append(">")
    view_lines.append(
        "> **분포 폭 의식**: 1~5 양극단 적극 활용 (Slice 9 폭 2 → Slice 11 폭 ≥3 목표)"
    )
    view_lines.append("")
    view_lines.append("---")
    view_lines.append("")

    label_mapping: dict[int, dict] = {}

    for view_idx, original_idx in enumerate(indices, start=1):
        case = cases[original_idx]
        label_mapping[view_idx] = {
            "entry": case["entry"],
            "model": case["model"],
            "repeat": case["repeat"],
            "original_index": original_idx,
            "schema_fitting_pass": case["schema_fitting_pass"],
        }

        view_lines.append(f"## Case #{view_idx}")
        view_lines.append("")
        view_lines.append(f"- output_tokens: {case['output_tokens']}")
        view_lines.append(f"- latency_ms: {case['latency_ms']}")
        view_lines.append(
            f"- schema_fitting: {'PASS' if case['schema_fitting_pass'] else 'FAIL'}"
        )
        view_lines.append("")
        view_lines.append("### Response")
        view_lines.append("")
        view_lines.append("```")
        view_lines.append(case["response_text"])
        view_lines.append("```")
        view_lines.append("")
        view_lines.append("### Manual Eval (병진 입력)")
        view_lines.append("")
        view_lines.append("- naturalness: ___/5")
        view_lines.append("- insight: ___/5")
        view_lines.append("- actionability: [OK/NG/N/A]")
        view_lines.append("- note: ")
        view_lines.append("")
        view_lines.append("---")
        view_lines.append("")

    view_path = output_dir / f"{prefix}_shuffled_view.md"
    view_path.write_text("\n".join(view_lines), encoding="utf-8")

    mapping_path = output_dir / f"{prefix}_label_mapping.json"
    mapping_path.write_text(
        json.dumps(label_mapping, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"Shuffled view: {view_path}")
    print(f"Label mapping: {mapping_path}")
    print(f"N cases: {len(cases)}, Seed: {seed}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Slice 11+ Manual Eval Shuffle (D2-A blind)"
    )
    parser.add_argument(
        "--matrix", required=True, type=Path, help="Path to part{N}_matrix.json"
    )
    parser.add_argument(
        "--output-dir", required=True, type=Path, help="Output directory"
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="Random seed (default: 42)"
    )
    parser.add_argument(
        "--prefix",
        type=str,
        default="part5",
        help="Output filename prefix (default: part5)",
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    shuffle_matrix(args.matrix, args.output_dir, args.seed, args.prefix)

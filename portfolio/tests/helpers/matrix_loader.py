"""Slice 9 Part 1 — matrix 26 cases loader.

지시서의 matrix_raw.json은 부재 (개별 26 파일 + matrix_summary.json의 results 키).
실제로는 `matrix_summary.json`의 `results` 키가 26 entries 통합 데이터.

각 entry는 다음 키를 포함 (Slice 8 Part 3 §4):
- case (S01~S14, S13 skip)
- fixture_file
- model (claude-haiku-4-5 / claude-sonnet-4-5)
- provider
- cost_usd, input_tokens, output_tokens, latency_ms
- answer_length, patterns_score
- raw_text (LLM raw)
- parsed (E4PortfolioCommentary dict: answer, referenced_metrics, follow_up_suggestions,
  confidence, action_items)
- kpi_4판정 (cost_pass, length_pass, actions_pass, parse_pass)
- score_pass, all_pass
- cumulative_after
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

DEFAULT_MATRIX_SUMMARY = Path("docs/portfolio/coach/slice8/part3/matrix_summary.json")


def load_matrix_cases(
    summary_path: Optional[Path] = None,
) -> list[dict]:
    """Slice 8 Part 3 matrix 26 entries 로드.

    Args:
        summary_path: matrix_summary.json 경로 (default: DEFAULT_MATRIX_SUMMARY).

    Returns:
        26 entries 리스트 (case S01~S14 except S13, model haiku/sonnet 각각).

    Raises:
        FileNotFoundError: summary_path 부재.
        ValueError: results 키 부재.
    """
    path = summary_path or DEFAULT_MATRIX_SUMMARY
    with open(path) as f:
        data = json.load(f)

    if "results" not in data:
        raise ValueError(f"results key missing in {path}")

    results = data["results"]
    return results


def get_commentary(case: dict) -> str:
    """matrix case entry에서 commentary 본문 추출.

    parsed.answer (E4PortfolioCommentary.answer) 필드를 우선 사용. 부재 시 raw_text fallback.
    """
    parsed = case.get("parsed", {})
    if isinstance(parsed, dict):
        answer = parsed.get("answer")
        if isinstance(answer, str):
            return answer
    return case.get("raw_text", "")


def assign_case_ids(cases: list[dict]) -> list[str]:
    """26 entries에 순서대로 rationale_case_id 부여 (S01_haiku, S01_sonnet, ..., S14_sonnet).

    matrix_summary.json의 results 순서를 기준으로 1:1 매핑.
    각 entry의 ('case', 'model')에서 short 형 case_id 생성.
    """
    case_ids: list[str] = []
    for entry in cases:
        case_short = entry["case"]  # S01, S02, ..., S14
        model = entry["model"]
        suffix = "haiku" if "haiku" in model else "sonnet"
        case_ids.append(f"{case_short}_{suffix}")
    return case_ids

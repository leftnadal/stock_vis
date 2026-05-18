"""Slice 10 Step 0 §1 — Slice 1~9 LLM raw call 통합 dump.

각 슬라이스는 산출 schema가 다름 (flat vs nested in metadata).
이 스크립트는 모든 entry를 평탄 schema (input_tokens / output_tokens / cost_usd /
model / latency_ms / provider 등)로 정규화 → JSONL로 출력한다.

산출: docs/portfolio/coach/all_llm_calls.jsonl (한 줄 = 한 LLM 호출)

멱등성: 재실행 시 동일 결과 (정렬은 슬라이스 번호 → source_file → 원본 순서).
신규 슬라이스 추가 시 `SLICE_SOURCES`에 한 줄 추가하면 흡수된다.

Slice 9 `estimated_input_tokens`는 보존 (#48 v3 backtest 비교 기준).
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
COACH_ROOT = REPO_ROOT / "docs" / "portfolio" / "coach"
DEFAULT_OUT = COACH_ROOT / "all_llm_calls.jsonl"

# 통합 평탄 schema의 필수 필드
REQUIRED_FIELDS = ("input_tokens", "output_tokens", "cost_usd", "model")


# ============================================================
# 정규화 헬퍼
# ============================================================


def normalize_entry(
    entry: dict,
    slice_n: int,
    source_file: str,
    extra: dict | None = None,
) -> dict:
    """flat or nested entry → 평탄 schema dict.

    Args:
        entry: 원본 entry (`metadata` 키가 있으면 nested로 간주).
        slice_n: 슬라이스 번호 (1~9).
        source_file: 원본 파일 경로 (REPO_ROOT 기준 상대).
        extra: 추가 필드 (예: scenario_id, label) — 평탄 위로 머지.
    """
    # output_chars 추출 (Slice 11 §1 output estimator fitting용)
    output_chars = _extract_output_chars(entry)

    if "input_tokens" in entry:
        norm = {k: v for k, v in entry.items() if not _is_nonscalar_payload(k)}
    else:
        meta = entry.get("metadata", {}) or {}
        norm = {
            **{k: v for k, v in entry.items() if k != "metadata" and not _is_nonscalar_payload(k)},
            **meta,
        }
    norm["slice"] = slice_n
    norm["source_file"] = source_file
    if output_chars is not None:
        norm["output_chars"] = output_chars
    if extra:
        for k, v in extra.items():
            norm.setdefault(k, v)
    return norm


# 응답 텍스트 후보 키 (Slice별 형식 차이)
_OUTPUT_TEXT_KEYS = ("raw_text", "raw_content", "commentary", "rationale_text", "insight")


def _extract_output_chars(entry: dict) -> int | None:
    """원본 entry에서 응답 텍스트 길이(char count) 추출.

    slice 별 응답 필드 이름 상이 → 후보 키 순회.
    metadata nested일 경우 entry root + metadata 양쪽 확인.
    """
    if not isinstance(entry, dict):
        return None
    for k in _OUTPUT_TEXT_KEYS:
        v = entry.get(k)
        if isinstance(v, str):
            return len(v)
    meta = entry.get("metadata")
    if isinstance(meta, dict):
        for k in _OUTPUT_TEXT_KEYS:
            v = meta.get(k)
            if isinstance(v, str):
                return len(v)
    return None


# 비-스칼라 페이로드 키는 dump에서 제외 (JSONL 크기 + noise 방지)
_NONSCALAR_KEYS = {
    "raw_text",
    "raw_content",
    "parsed",
    "judgments",
    "request",
    "request_summary",
    "fixture",
    "fixture_group",
    "evaluation_guide",
    "thresholds",
    "expected",
    "expected_alignment",
    "insight",
    "commentary",
    "original_commentary",
    "rationale_text",
    "rationale_categories",
    "original_specificity_detail",
    "cost_guard_status",
    "status_summary",
    "cumulative",
    "cumulative_after",
    "provider_meta",
    "kpi_4판정",
}


def _is_nonscalar_payload(key: str) -> bool:
    return key in _NONSCALAR_KEYS


def _rel(p: Path) -> str:
    """저장용 상대 경로 (REPO_ROOT 기준)."""
    try:
        return str(p.relative_to(REPO_ROOT))
    except ValueError:
        return str(p)


# ============================================================
# 슬라이스별 loader (한 파일 → entry list)
# ============================================================


@dataclass(frozen=True)
class SliceSource:
    slice_n: int
    path: Path
    loader: Callable[[dict | list, int, Path], list[dict]]


def _load_flat_metadata_single(
    data: dict | list, slice_n: int, path: Path
) -> list[dict]:
    """Smoke output: 단일 dict + metadata에 input_tokens 위치.

    응답 텍스트(raw_text/raw_content)는 top-level에 있으므로 data 전체를 전달.
    normalize_entry는 input_tokens 키 위치로 flat/nested 분기.
    """
    if not isinstance(data, dict):
        return []
    md = data.get("metadata", {}) or {}
    if "input_tokens" not in md:
        return []
    return [normalize_entry(data, slice_n, _rel(path))]


def _load_flat_root_single(
    data: dict | list, slice_n: int, path: Path
) -> list[dict]:
    """Smoke output 변형: root에 input_tokens 직접 (slice8 step6, slice8 matrix/*)."""
    if not isinstance(data, dict):
        return []
    if "input_tokens" not in data:
        return []
    return [normalize_entry(data, slice_n, _rel(path))]


def _load_results_list(
    data: dict | list, slice_n: int, path: Path
) -> list[dict]:
    """{'results': [...]} 구조 — 각 item은 flat 또는 nested.metadata."""
    if isinstance(data, dict):
        items = data.get("results", []) or []
    else:
        return []
    if not isinstance(items, list):
        return []
    src = _rel(path)
    out = []
    for item in items:
        if not isinstance(item, dict):
            continue
        # flat (input_tokens at top) or nested (metadata.input_tokens)
        flat_has = "input_tokens" in item
        nested_has = "input_tokens" in (item.get("metadata") or {})
        if not (flat_has or nested_has):
            continue
        extra = {}
        # 식별자 보존
        for k in ("scenario_id", "fixture_id", "label", "preset_id", "model_label"):
            if k in item:
                extra[k] = item[k]
        out.append(normalize_entry(item, slice_n, src, extra=extra))
    return out


def _load_root_list(
    data: dict | list, slice_n: int, path: Path
) -> list[dict]:
    """root가 list (slice7 step7_matrix_raw, slice9 rationale_records)."""
    if not isinstance(data, list):
        return []
    src = _rel(path)
    out = []
    for item in data:
        if not isinstance(item, dict):
            continue
        flat_has = "input_tokens" in item
        nested_has = "input_tokens" in (item.get("metadata") or {})
        if not (flat_has or nested_has):
            continue
        extra = {}
        for k in (
            "scenario_id",
            "fixture_id",
            "label",
            "preset_id",
            "case_id",
            "case_name",
            "tier",
            "estimated_input_tokens",  # Slice 9 #48 backtest 보존 키
            "rationale_model",
            "original_model",
        ):
            if k in item:
                extra[k] = item[k]
        # slice9 rationale_records: model 필드 없음 → rationale_model이 실제 호출 모델
        if not item.get("model") and item.get("rationale_model"):
            extra["model"] = item["rationale_model"]
        out.append(normalize_entry(item, slice_n, src, extra=extra))
    return out


# Anthropic pricing (per token) — model 추론용 (slice7 step8 entries 보강).
# claude-haiku-4-5: $1 / $5 per MTok (input/output)
# claude-sonnet-4-5: $3 / $15 per MTok
_PRICING = {
    "claude-haiku-4-5": (1e-6, 5e-6),
    "claude-sonnet-4-5": (3e-6, 15e-6),
}


def _infer_model_from_cost(input_tokens: int, output_tokens: int, cost_usd: float) -> str | None:
    """cost_usd가 haiku/sonnet 중 어느 가격에 가까운지로 모델 추론.

    캐시 할인으로 ±20% 어긋날 수 있으나 두 모델 가격이 ~3배 차이라 안전.
    """
    if not (isinstance(cost_usd, (int, float)) and cost_usd > 0):
        return None
    best_model = None
    best_diff = float("inf")
    for model, (in_rate, out_rate) in _PRICING.items():
        expected = input_tokens * in_rate + output_tokens * out_rate
        diff = abs(cost_usd - expected) / expected if expected else float("inf")
        if diff < best_diff:
            best_diff = diff
            best_model = model
    # 둘 다 50% 이상 어긋나면 신뢰 불가
    if best_diff > 0.5:
        return None
    return best_model


def _load_entries_list(
    data: dict | list, slice_n: int, path: Path
) -> list[dict]:
    """{'entries': [...]} 구조 (slice7 step8_2way_e4_conversation).

    이 파일 entry는 model 필드가 없음 → cost_usd로 haiku/sonnet 추론하여 채움.
    """
    if not isinstance(data, dict):
        return []
    items = data.get("entries", []) or []
    if not isinstance(items, list):
        return []
    src = _rel(path)
    out = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if "input_tokens" not in item and "input_tokens" not in (item.get("metadata") or {}):
            continue
        extra = {}
        for k in ("scenario_id", "tier", "preset_id", "trigger_case"):
            if k in item:
                extra[k] = item[k]
        # model 결측 보강 (cost 기반 추론)
        if not item.get("model") and not (item.get("metadata") or {}).get("model"):
            inferred = _infer_model_from_cost(
                int(item.get("input_tokens", 0)),
                int(item.get("output_tokens", 0)),
                float(item.get("cost_usd", 0) or 0),
            )
            if inferred:
                extra["model"] = inferred
                extra["model_inferred_from"] = "cost"
        out.append(normalize_entry(item, slice_n, src, extra=extra))
    return out


# ============================================================
# 소스 매핑 (지시서 §1 사용자 회신 기반)
# ============================================================


def _matrix_files() -> list[Path]:
    """slice8 part3/matrix/*.json (정렬)."""
    mdir = COACH_ROOT / "slice8" / "part3" / "matrix"
    return sorted(mdir.glob("*.json"))


def build_slice_sources() -> list[SliceSource]:
    """모든 슬라이스의 raw 파일 경로 + loader 매핑."""
    sources: list[SliceSource] = []

    # Slice 1
    sources.append(SliceSource(1, COACH_ROOT / "slice1" / "step6_smoke_output.json", _load_flat_metadata_single))
    sources.append(SliceSource(1, COACH_ROOT / "slice1" / "step8_3way_raw.json", _load_results_list))

    # Slice 2~5: step6_smoke + step8_2way
    sources.append(SliceSource(2, COACH_ROOT / "slice2" / "step6_smoke_e5_output.json", _load_flat_metadata_single))
    sources.append(SliceSource(2, COACH_ROOT / "slice2" / "step8_2way_e5_raw.json", _load_results_list))

    sources.append(SliceSource(3, COACH_ROOT / "slice3" / "step6_smoke_e2_output.json", _load_flat_metadata_single))
    sources.append(SliceSource(3, COACH_ROOT / "slice3" / "step8_2way_e2_raw.json", _load_results_list))

    sources.append(SliceSource(4, COACH_ROOT / "slice4" / "step6_smoke_e6_output.json", _load_flat_metadata_single))
    sources.append(SliceSource(4, COACH_ROOT / "slice4" / "step8_2way_e6_raw.json", _load_results_list))

    sources.append(SliceSource(5, COACH_ROOT / "slice5" / "step6_smoke_e3_output.json", _load_flat_metadata_single))
    sources.append(SliceSource(5, COACH_ROOT / "slice5" / "step8_2way_e3_raw.json", _load_results_list))

    # Slice 6: smoke + step7_matrix + step8_portfolio
    sources.append(SliceSource(6, COACH_ROOT / "slice6" / "step6_smoke_result.json", _load_flat_metadata_single))
    sources.append(SliceSource(6, COACH_ROOT / "slice6" / "step7_matrix_raw.json", _load_results_list))
    sources.append(SliceSource(6, COACH_ROOT / "slice6" / "step8_2way_e3_portfolio_raw.json", _load_results_list))

    # Slice 7: step7_matrix (root list) + step8 (entries)
    # ⚠️ step9_1_rationales.json은 토큰 없음(rationale_cost_usd만) → 제외
    sources.append(SliceSource(7, COACH_ROOT / "slice7" / "step7_matrix_raw.json", _load_root_list))
    sources.append(SliceSource(7, COACH_ROOT / "slice7" / "step8_2way_e4_conversation_raw.json", _load_entries_list))

    # Slice 8: step6_smoke + matrix/*.json
    sources.append(SliceSource(8, COACH_ROOT / "slice8" / "part3" / "step6_smoke_result.json", _load_flat_root_single))
    for mf in _matrix_files():
        sources.append(SliceSource(8, mf, _load_flat_root_single))

    # Slice 9: rationale_records (root list, flat with estimated_input_tokens)
    sources.append(SliceSource(9, COACH_ROOT / "slice9" / "part1" / "rationale_records.json", _load_root_list))

    return sources


# ============================================================
# Dump main
# ============================================================


def collect_entries(sources: Iterable[SliceSource]) -> list[dict]:
    """모든 source를 로드하여 평탄 entry list로 반환."""
    all_entries: list[dict] = []
    for src in sources:
        if not src.path.exists():
            raise FileNotFoundError(f"source missing: {src.path}")
        with open(src.path, encoding="utf-8") as fp:
            data = json.load(fp)
        entries = src.loader(data, src.slice_n, src.path)
        all_entries.extend(entries)
    return all_entries


def validate_entries(entries: list[dict]) -> tuple[int, list[dict]]:
    """필수 필드 누락 entry 검출. (missing_count, missing_entries) 반환."""
    missing: list[dict] = []
    for e in entries:
        if any(e.get(k) is None for k in REQUIRED_FIELDS):
            missing.append(
                {
                    "source_file": e.get("source_file"),
                    "slice": e.get("slice"),
                    "missing": [k for k in REQUIRED_FIELDS if e.get(k) is None],
                }
            )
    return len(missing), missing


def write_jsonl(entries: list[dict], out_path: Path) -> None:
    """JSONL 파일로 저장 (idempotent — 동일 입력 = 동일 출력)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fp:
        for e in entries:
            # 키 정렬 + ensure_ascii=False → 동일 입력 시 동일 출력
            fp.write(json.dumps(e, sort_keys=True, ensure_ascii=False))
            fp.write("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Slice 1~9 LLM raw calls dump")
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"출력 JSONL 경로 (default {DEFAULT_OUT})",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="필수 필드 누락이 있으면 실패 (default: warn).",
    )
    args = parser.parse_args(argv)

    sources = build_slice_sources()
    entries = collect_entries(sources)
    missing_count, missing = validate_entries(entries)

    write_jsonl(entries, args.out)

    print(f"dump 완료: {args.out}")
    print(f"  총 entry: {len(entries)}")
    print(f"  필수 필드 누락: {missing_count}")
    if missing_count and args.strict:
        for m in missing[:10]:
            print(f"    - {m}")
        return 1

    # 슬라이스별 카운트
    from collections import Counter

    by_slice = Counter(e["slice"] for e in entries)
    for s in sorted(by_slice):
        print(f"  slice {s}: {by_slice[s]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

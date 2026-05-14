"""Slice 7 Part 4 공용 헬퍼.

3개 슬라이스(5/6/7)의 raw 답변 구조 차이를 흡수.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


SLICE5_FIELDS = ["one_liner", "comment", "answer"]
SLICE6_FIELDS = [
    "holistic_assessment",
    "diversification_comment",
    "sector_balance_comment",
    "risk_concentration_comment",
]


def _strip_fence(text: str) -> str:
    t = (text or "").strip()
    if t.startswith("```"):
        first_nl = t.find("\n")
        if first_nl != -1:
            t = t[first_nl + 1 :]
        if t.endswith("```"):
            t = t[:-3]
    return t.strip()


def extract_answer(entry: dict, source_slice: str) -> str:
    """slice별 답변 추출 (slice5: parsed.comments[].one_liner / slice6: parsed.{5 fields} / slice7: commentary)."""
    if source_slice == "slice5":
        parsed = entry.get("parsed") or {}
        comments = parsed.get("comments") if isinstance(parsed, dict) else None
        if isinstance(comments, list):
            parts = []
            for c in comments:
                if not isinstance(c, dict):
                    continue
                for f in SLICE5_FIELDS:
                    v = c.get(f)
                    if v:
                        parts.append(str(v))
                        break
            if parts:
                return "\n".join(parts)
        return _strip_fence(entry.get("raw_content", ""))
    if source_slice == "slice6":
        parsed = entry.get("parsed") or {}
        if isinstance(parsed, dict):
            parts = []
            for f in SLICE6_FIELDS:
                v = parsed.get(f)
                if v:
                    parts.append(f"[{f}] {v}")
            if parts:
                return "\n".join(parts)
        return _strip_fence(entry.get("raw_content", ""))
    if source_slice == "slice7":
        commentary = entry.get("commentary") or ""
        if isinstance(commentary, dict):
            answer = commentary.get("answer") or ""
            return str(answer)
        text = _strip_fence(str(commentary))
        try:
            data = json.loads(text)
            if isinstance(data, dict) and data.get("answer"):
                return str(data["answer"])
        except Exception:
            pass
        return text
    return entry.get("raw_content") or entry.get("answer") or ""


def load_raw(path: Path) -> list[dict]:
    """slice5/6 (data['results']) 또는 slice7 (data['entries']) 호환 로드."""
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("entries") or data.get("results") or []
    return []


def referenced_metrics(entry: dict, source_slice: str) -> list[str]:
    """slice별 referenced_metrics 추출."""
    if source_slice == "slice7":
        commentary = entry.get("commentary") or ""
        if isinstance(commentary, str):
            text = _strip_fence(commentary)
            try:
                data = json.loads(text)
                refs = data.get("referenced_metrics", [])
                if isinstance(refs, list):
                    return [str(r) for r in refs]
            except Exception:
                pass
        return []
    parsed = entry.get("parsed") or {}
    if isinstance(parsed, dict):
        refs = parsed.get("referenced_metrics", [])
        if isinstance(refs, list):
            return [str(r) for r in refs]
        # slice5의 comments[].metric_id로도 fallback
        comments = parsed.get("comments") or []
        if isinstance(comments, list):
            ids = [c.get("metric_id") for c in comments if isinstance(c, dict) and c.get("metric_id")]
            if ids:
                return [str(i) for i in ids]
    return []


def portfolio_metrics_keys(entry: dict) -> set[str]:
    """raw entry에 portfolio_metrics dict이 있다면 키만 추출."""
    pm = entry.get("portfolio_metrics")
    if isinstance(pm, dict):
        return set(pm.keys())
    # slice7 fixture 안에는 input_metrics 별도 위치일 수 있음
    inp = entry.get("input") or entry.get("fixture_data")
    if isinstance(inp, dict):
        pm2 = inp.get("portfolio_metrics")
        if isinstance(pm2, dict):
            return set(pm2.keys())
    return set()

"""AGENT-S2 ⑵ — 루브릭 채점 ("이 화면이 오늘 데이터로 내 질문에 답했는가").

루브릭 단일 출처 = `frontend/lib/guide/`의 confirmed `coreQuestion`(D-GUIDE-TRACK).
채점 입력은 **화면에서 추출한 텍스트뿐**이다 — 모델의 사전지식으로 화면을 평가하면
"관점 간극"이 재생산되므로(A안 기각 사유), 인용이 없는 근거는 무효 처리한다.

비용 통제: claude -p **1회 호출로 전 화면 일괄** 채점(tier3 패턴).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from datetime import date
from pathlib import Path
from typing import Any

from .check_quant import OUT_DIR
from .targets import rubric_targets

CLAUDE_BIN = os.getenv(
    "DOGFOOD_CLAUDE_BIN", str(Path.home() / ".nvm/versions/node/v22.19.0/bin/claude")
)
TIMEOUT_S = int(os.getenv("DOGFOOD_SCORE_TIMEOUT", "300"))
MIN_SCORE, MAX_SCORE = 1, 5
# 인용 대조 시 공백·따옴표 차이를 흡수할 최소 길이(너무 짧은 인용은 우연 일치한다).
MIN_QUOTE_CHARS = 8


def _norm(text: str) -> str:
    """인용 대조용 정규화 — 공백 접기 + 따옴표류 통일."""
    t = re.sub(r"\s+", " ", text or "")
    for ch in "“”‘’`":
        t = t.replace(ch, "'")
    return t.strip().lower()


# 앵커에서 이만큼도 못 건지면 fallback 본문을 함께 쓴다(render_screens.mjs와 같은 기준).
MIN_ANCHOR_CHARS = int(os.getenv("DOGFOOD_MIN_ANCHOR_CHARS", "200"))


def screen_body(screen: dict[str, Any]) -> str:
    """채점·인용 검증에 쓰는 화면 본문.

    앵커 텍스트가 사실상 비면(가이드 앵커 이름이 실제 DOM과 어긋난 화면이 있다)
    fallback 본문을 합친다 — 그러지 않으면 모델이 인용할 문장 자체가 없어
    무효 처리만 쌓인다(2026-09-03 monitor 실측).
    """
    parts = [r.get("text", "") for r in screen.get("regions", []) if r.get("text")]
    if sum(len(x) for x in parts) < MIN_ANCHOR_CHARS and screen.get("fallback_text"):
        parts.append(screen["fallback_text"])
    return " ".join(parts)


def screen_texts(rendered: dict[str, Any]) -> dict[str, str]:
    """화면별 '추출된 전체 텍스트' — 인용 검증의 기준이 된다."""
    return {s.get("id", ""): screen_body(s) for s in rendered.get("screens", [])}


def build_prompt(rendered: dict[str, Any]) -> str:
    targets = {t.id: t for t in rubric_targets()}
    blocks: list[str] = []
    for s in rendered.get("screens", []):
        t = targets.get(s.get("id", ""))
        if t is None:
            continue
        body = screen_body(s) or "(추출된 텍스트 없음)"
        learn = "\n".join(f"  - {x}" for x in t.learnings)
        blocks.append(
            f"""### 화면 id: {t.id}
질문(coreQuestion): {t.core_question}
이 화면에서 알 수 있어야 하는 것:
{learn}
--- 화면에서 실제로 추출된 텍스트 시작 ---
{body}
--- 화면에서 실제로 추출된 텍스트 끝 ---"""
        )

    screens_joined = "\n\n".join(blocks)
    ids = ", ".join(t.id for t in rubric_targets())
    return f"""당신은 이 서비스의 사용자입니다. 아래 각 화면에 대해, **오늘 그 화면이 보여준 내용만으로** 질문에 답이 되었는지 채점하세요.

절대 규칙:
1. 당신이 이 서비스에 대해 알고 있는 지식을 쓰지 마세요. **추출된 텍스트 안에 있는 것만** 근거로 씁니다.
2. 근거에는 추출된 텍스트에서 **그대로 복사한 구절**을 최소 1개 포함하세요(8자 이상). 인용이 없으면 그 채점은 무효 처리됩니다.
3. 점수는 1~5 정수입니다. 5 = 질문에 오늘 데이터로 분명히 답했다. 3 = 부분적으로 답했다. 1 = 답하지 못했다(빈 화면·로딩·낡은 데이터 포함).
4. 근거는 2문장 이내로 씁니다.
5. "있으면 좋겠다"는 **전체를 통틀어 최대 1건**만 씁니다(없으면 빈 문자열).

{screens_joined}

아래 JSON만 출력하세요. 다른 말은 쓰지 마세요.
{{
  "scores": [
    {{"id": "<{ids} 중 하나>", "score": <1-5>, "reason": "<2문장 이내, 인용 포함>", "quote": "<추출 텍스트에서 그대로 복사한 구절>"}}
  ],
  "wish": "<있으면 좋겠다 1건 또는 빈 문자열>"
}}"""


def call_claude(prompt: str) -> str:
    proc = subprocess.run(  # noqa: S603 - 고정 바이너리
        [CLAUDE_BIN, "-p", prompt],
        capture_output=True,
        text=True,
        timeout=TIMEOUT_S,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"claude 호출 실패(rc={proc.returncode}): {proc.stderr[-400:]}")
    return proc.stdout


def parse_response(raw: str) -> dict[str, Any]:
    """코드펜스/여담이 섞여도 첫 JSON 객체를 건져낸다."""
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("응답에서 JSON을 찾지 못했습니다")
        text = text[start : end + 1]
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("JSON 최상위가 객체가 아닙니다")
    return data


def validate_scores(data: dict[str, Any], texts: dict[str, str]) -> list[dict[str, Any]]:
    """인용 검증 + 범위 검증. 실패는 '채점 불가'로 남기고 전체를 중단하지 않는다."""
    by_id = {s.get("id"): s for s in data.get("scores", []) if isinstance(s, dict)}
    out: list[dict[str, Any]] = []
    for t in rubric_targets():
        row = by_id.get(t.id)
        base = {"id": t.id, "route": t.route, "title": t.title}
        if row is None:
            out.append({**base, "score": None, "reason": "", "quote": "", "invalid": "미채점"})
            continue

        try:
            score = int(row.get("score"))
        except (TypeError, ValueError):
            score = None
        quote = str(row.get("quote") or "")
        reason = str(row.get("reason") or "")
        source = texts.get(t.id, "")

        if score is None or not (MIN_SCORE <= score <= MAX_SCORE):
            out.append({**base, "score": None, "reason": reason, "quote": quote, "invalid": "점수 범위 밖"})
            continue
        if len(quote.strip()) < MIN_QUOTE_CHARS:
            out.append({**base, "score": None, "reason": reason, "quote": quote, "invalid": "인용 없음"})
            continue
        if _norm(quote) not in _norm(source):
            out.append(
                {**base, "score": None, "reason": reason, "quote": quote, "invalid": "인용 불일치(화면에 없는 문구)"}
            )
            continue
        out.append({**base, "score": score, "reason": reason, "quote": quote, "invalid": None})
    return out


def average(scores: list[dict[str, Any]]) -> float | None:
    vals = [s["score"] for s in scores if s.get("score") is not None]
    return round(sum(vals) / len(vals), 1) if vals else None


def load_previous(out_dir: Path, today: date) -> dict[str, int]:
    """전일 이전의 가장 최근 루브릭 → {id: score}."""
    best: tuple[date, dict[str, int]] | None = None
    for path in sorted(out_dir.glob("rubric_*.json")):
        m = re.match(r"^rubric_(\d{8})\.json$", path.name)
        if not m:
            continue
        stamp = m.group(1)
        try:
            day = date(int(stamp[:4]), int(stamp[4:6]), int(stamp[6:]))
            data = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, json.JSONDecodeError, OSError):
            continue
        if day >= today:
            continue
        prev = {s["id"]: s["score"] for s in data.get("scores", []) if s.get("score") is not None}
        if best is None or day > best[0]:
            best = (day, prev)
    return best[1] if best else {}


def build_report(
    rendered: dict[str, Any], data: dict[str, Any], out_dir: Path, today: date | None = None
) -> dict[str, Any]:
    day = today or date.today()
    scores = validate_scores(data, screen_texts(rendered))
    prev = load_previous(out_dir, day)
    for s in scores:
        before = prev.get(s["id"])
        s["prev_score"] = before
        s["delta"] = (s["score"] - before) if (s["score"] is not None and before is not None) else None
    return {
        "date": day.isoformat(),
        "authenticated": bool(rendered.get("authenticated")),
        "average": average(scores),
        "scores": scores,
        "wish": str(data.get("wish") or ""),
        "invalid_count": sum(1 for s in scores if s.get("invalid")),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="AGENT-S2 루브릭 채점")
    parser.add_argument("--out-dir", help="리포트 디렉터리")
    parser.add_argument("--rendered", help="렌더 JSON 경로(기본: out-dir의 오늘자)")
    parser.add_argument("--dry-run", action="store_true", help="claude 호출 없이 프롬프트만 출력")
    args = parser.parse_args()

    out_dir = Path(args.out_dir) if args.out_dir else OUT_DIR
    rendered_path = (
        Path(args.rendered) if args.rendered else out_dir / f"rendered_{date.today():%Y%m%d}.json"
    )
    if not rendered_path.exists():
        raise SystemExit(f"렌더 결과가 없습니다: {rendered_path}")
    rendered = json.loads(rendered_path.read_text(encoding="utf-8"))

    prompt = build_prompt(rendered)
    if args.dry_run:
        print(prompt)
        return 0

    report = build_report(rendered, parse_response(call_claude(prompt)), out_dir)
    path = out_dir / f"rubric_{date.today():%Y%m%d}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"루브릭 평균 {report['average']}/5 (무효 {report['invalid_count']}) → {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

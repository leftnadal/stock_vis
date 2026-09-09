"""AGENT-SHOT-1 — 온디맨드 화면 캡처 (야간 렌더러 재사용·채점/메일 없음).

야간 `collect_rendered.run_render`(인증·Playwright·render_screens.mjs)를 그대로 타고
PNG 캡처만 추가한다(mjs가 `DOGFOOD_SHOT_DIR`/`DOGFOOD_SHOT_FULL`을 보고 스크린샷).
**신규 인증 코드 0** — S2.1 `.env` 명시 로드(dogfood_env)와 mjs login()을 재사용.

출력은 야간 원장과 **분리**: `stock-vis-nightly/adhoc/<YYYYMMDD_HHMM>/` (PNG + 텍스트 +
meta.json). `rendered_/quant_/rubric_` 파일명 규칙 무접촉. 채점·메일 없음 → LLM 비용 0.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from .collect_rendered import WEB_TREE, dogfood_env, run_render
from .targets import load_guide_targets

ADHOC_BASE = Path(
    os.getenv("SHOT_OUT_BASE", str(Path.home() / "stock-vis-nightly" / "adhoc"))
)


def _safe(s: str) -> str:
    return re.sub(r"[^\w.-]", "_", s or "").strip("_") or "screen"


def _tree_hash(tree: Path) -> str:
    try:
        r = subprocess.run(
            ["git", "-C", str(tree), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return r.stdout.strip() or "unknown"
    except Exception:  # noqa: BLE001 - 해시 부재는 캡처를 막지 않는다
        return "unknown"


def build_screens(path: str | None, screens_csv: str | None) -> list[dict[str, Any]]:
    """--path(임의 1건) 또는 --screens(기존 목록 부분 선택)로 screens 페이로드 조립."""
    if path:
        if not path.startswith("/"):
            raise SystemExit(f"--path 는 '/'로 시작해야 합니다: {path!r}")
        return [{"id": "adhoc_" + _safe(path), "route": path, "title": path, "anchors": []}]
    if screens_csv:
        wanted = {k.strip() for k in screens_csv.split(",") if k.strip()}
        targets = [g for g in load_guide_targets() if g.id in wanted]
        missing = wanted - {g.id for g in targets}
        if missing:
            raise SystemExit(f"알 수 없는 screen id: {sorted(missing)}")
        return [
            {"id": g.id, "route": g.route, "title": g.title, "anchors": g.anchors}
            for g in targets
        ]
    raise SystemExit("--path 또는 --screens 중 하나가 필요합니다.")


def screen_text(s: dict[str, Any]) -> str:
    """렌더 결과에서 페이지 텍스트(앵커 영역 우선, 없으면 fallback)."""
    joined = " ".join(r.get("text", "") for r in s.get("regions", []) if r.get("text"))
    return joined or s.get("fallback_text", "")


def write_outputs(out_dir: Path, raw: dict[str, Any]) -> dict[str, Any]:
    """per-screen 텍스트 + meta.json 기록. meta 반환."""
    screens = raw.get("screens", [])
    authed = bool(raw.get("authenticated"))
    for s in screens:
        (out_dir / f"{_safe(s.get('id', 'screen'))}.txt").write_text(
            screen_text(s), encoding="utf-8"
        )
    meta = {
        "generated_at": datetime.now().isoformat(),
        "base_url": raw.get("base_url", ""),
        "authenticated": authed,
        "auth_fail_reason": raw.get("auth_fail_reason", ""),
        "web_tree_hash": _tree_hash(WEB_TREE),
        "screens": [
            {
                "id": s.get("id"),
                "route": s.get("route"),
                "url": raw.get("base_url", "") + (s.get("route") or ""),
                "ok": s.get("ok"),
                "screenshot": s.get("screenshot"),
                "screenshot_error": s.get("screenshot_error"),
                "error": s.get("error"),
            }
            for s in screens
        ],
    }
    (out_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return meta


def main() -> int:
    p = argparse.ArgumentParser(description="AGENT-SHOT-1 온디맨드 캡처(채점 없음)")
    p.add_argument("--path", help="임의 경로 1건 (예: /monitor/<id>)")
    p.add_argument("--screens", help="기존 목록 부분 선택 (csv id)")
    p.add_argument(
        "--full", dest="full", action="store_true", default=True, help="풀페이지 캡처(기본 on)"
    )
    p.add_argument("--no-full", dest="full", action="store_false", help="뷰포트만 캡처")
    # 온디맨드 주 용도 = 캡처. 채점·메일은 항상 생략(LLM 비용 0). 플래그는 명시 확인용.
    p.add_argument(
        "--no-score",
        action="store_true",
        default=True,
        help="채점·메일 생략(기본값·유일 지원 — 캡처 전용)",
    )
    args = p.parse_args()

    screens = build_screens(args.path, args.screens)
    out_dir = ADHOC_BASE / datetime.now().strftime("%Y%m%d_%H%M")
    out_dir.mkdir(parents=True, exist_ok=True)

    # mjs가 볼 캡처 플래그(collect_rendered.run_render가 os.environ를 subprocess로 전달).
    os.environ["DOGFOOD_SHOT_DIR"] = str(out_dir)
    os.environ["DOGFOOD_SHOT_FULL"] = "1" if args.full else "0"

    creds = "있음" if dogfood_env().get("DOGFOOD_USER") else "없음"
    print(f"자격증명 {creds}(.env 포함 조회) · full={args.full}")
    raw = run_render(screens)  # 인증 + 렌더 + 스크린샷(재사용)
    meta = write_outputs(out_dir, raw)

    auth_s = "인증" if meta["authenticated"] else f"미인증({meta['auth_fail_reason']})"
    print(f"캡처 {len(meta['screens'])}건 ({auth_s}) → {out_dir}")
    for s in meta["screens"]:
        print(f"  {s['route']} → {s.get('screenshot') or '(png 없음)'}")

    ok = meta["authenticated"] and all(s.get("screenshot") for s in meta["screens"])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

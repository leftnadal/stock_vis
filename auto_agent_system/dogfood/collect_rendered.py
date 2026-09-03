"""AGENT-S2 ⑴ — 렌더 후 화면 텍스트 수집 (Playwright 경유).

`render_screens.mjs`를 subprocess로 돌려 결과를 `rendered_YYYYMMDD.json`으로 적재한다.

**실행 트리 주의**: dogfood가 도는 `sv-worker-runtime`에는 `frontend/node_modules`가
없다(실측 2026-09-02). playwright는 `sv-web-runtime`에만 있으므로 node를 그 트리의
`frontend`를 cwd로 실행한다. 스크립트 파일 자체는 어느 트리에서 읽어도 같다.

1단계(정량)와 독립이다 — 여기서 실패해도 정량 체크와 메일은 산다.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any

from .check_quant import OUT_DIR
from .targets import rubric_targets

SCRIPT = Path(__file__).with_name("render_screens.mjs")
# playwright가 설치된 트리(실측: web 런타임에만 node_modules 존재).
WEB_TREE = Path(os.getenv("DOGFOOD_WEB_TREE", str(Path.home() / "worktrees" / "sv-web-runtime")))
NODE_BIN = os.getenv("DOGFOOD_NODE", str(Path.home() / ".nvm/versions/node/v22.19.0/bin/node"))
TIMEOUT_S = int(os.getenv("DOGFOOD_RENDER_TIMEOUT", "300"))


def screens_payload() -> list[dict[str, Any]]:
    """채점 대상 화면 정의(목록 단일 출처 = 가이드 데이터)."""
    return [
        {"id": t.id, "route": t.route, "title": t.title, "anchors": t.anchors}
        for t in rubric_targets()
    ]


def node_cwd() -> Path:
    """playwright를 해석할 수 있는 디렉터리. 없으면 사유를 담아 예외."""
    fe = WEB_TREE / "frontend"
    if not (fe / "node_modules" / "playwright").exists() and not (
        fe / "node_modules" / "@playwright" / "test"
    ).exists():
        raise RuntimeError(
            f"playwright를 찾지 못했습니다: {fe}/node_modules — "
            "web 런타임 트리에 npm ci가 되어 있어야 합니다(DOGFOOD_WEB_TREE로 지정 가능)."
        )
    return fe


def run_render(screens: list[dict[str, Any]]) -> dict[str, Any]:
    cwd = node_cwd()
    proc = subprocess.run(  # noqa: S603 - 고정 바이너리 + 고정 스크립트
        [NODE_BIN, str(SCRIPT)],
        input=json.dumps(screens),
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=TIMEOUT_S,
        env={
            **os.environ,
            # ESM은 NODE_PATH를 무시한다 → playwright 진입점을 절대 경로로 넘긴다.
            "DOGFOOD_PLAYWRIGHT_MODULE": (cwd / "node_modules" / "playwright" / "index.js").as_uri(),
        },
    )
    if proc.returncode != 0:
        raise RuntimeError(f"render_screens.mjs 실패(rc={proc.returncode}): {proc.stderr[-500:]}")
    if not proc.stdout.strip():
        raise RuntimeError(f"render_screens.mjs 출력이 비었습니다: {proc.stderr[-500:]}")
    return json.loads(proc.stdout)


def build_report(raw: dict[str, Any], today: date | None = None) -> dict[str, Any]:
    day = today or date.today()
    screens = raw.get("screens", [])
    return {
        "date": day.isoformat(),
        "base_url": raw.get("base_url", ""),
        "authenticated": bool(raw.get("authenticated")),
        "screen_count": len(screens),
        "ok_count": sum(1 for s in screens if s.get("ok")),
        "screens": screens,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="AGENT-S2 렌더 수집")
    parser.add_argument("--out-dir", help="출력 디렉터리")
    parser.add_argument("--dry-run", action="store_true", help="저장 없이 요약만")
    args = parser.parse_args()

    out_dir = Path(args.out_dir) if args.out_dir else OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    screens = screens_payload()
    if not screens:
        print("채점 대상 화면이 없습니다(confirmed + coreQuestion 0건).", file=sys.stderr)
        return 1

    report = build_report(run_render(screens))
    auth = "인증" if report["authenticated"] else "미인증"
    print(f"렌더 수집 {report['ok_count']}/{report['screen_count']} ({auth})")

    if args.dry_run:
        return 0

    path = out_dir / f"rendered_{date.today():%Y%m%d}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"→ {path}")
    return 0 if report["ok_count"] == report["screen_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

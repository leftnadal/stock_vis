#!/usr/bin/env python3
"""
OAG KB 큐 미드레인 경고 (게이트 A — soft warning)

`shared_kb/queue_data.json` 큐에 N일(기본 3) 이상 검색KB로 드레인되지 않은
항목이 있으면 stderr로 경고를 출력한다. **차단하지 않는다 — 항상 exit 0.**

설계 원칙 (HARNESS-KB S3, 게이트 A):
- 경고만. 커밋·세션을 차단(exit 1)하지 않는다.
- **의존성 0** — 큐 JSON을 직접 파싱한다(shared_kb 패키지 import 안 함).
  shared_kb/__init__.py가 neo4j를 끌어오므로, 패키지 경유 import는 git hook
  환경(시스템 python3, neo4j 미설치)에서 깨진다. 그래서 stdlib만 쓴다.
- 어떤 예외가 나도 exit 0 (KB 점검이 commit을 막으면 안 됨).
- 큐 파일은 gitignore된 트리별 로컬 상태 — worktree에서는 비어 있을 수 있고
  무경고가 정상이다.

사용:
    python3 shared_kb/queue_drain_check.py            # 3일+ 미드레인 경고
    python3 shared_kb/queue_drain_check.py --days 7   # 임계 조정
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

QUEUE_FILE = Path(__file__).resolve().parent / "queue_data.json"


def check(days: int) -> int:
    """미드레인 N일+ 항목을 세어 경고. 항상 0 반환(비차단)."""
    try:
        if not QUEUE_FILE.exists():
            return 0
        with open(QUEUE_FILE, "r", encoding="utf-8") as f:
            items = json.load(f)
        if not items:
            return 0

        now = datetime.now()
        stale = []
        for it in items:
            raw = it.get("created_at")
            if not raw:
                continue
            try:
                created = datetime.fromisoformat(raw)
            except (ValueError, TypeError):
                continue
            age = (now - created).days
            if age >= days:
                stale.append(age)

        if not stale:
            return 0

        print(
            f"⚠️  KB 큐 미드레인 {len(stale)}건, 최古 {max(stale)}일 "
            f"(임계 {days}일) — 드레인 권장: python -m shared_kb.curate",
            file=sys.stderr,
        )
        print(
            "    (경고만 — 커밋 차단 아님. 세션 종료 의식 4-2 참조)",
            file=sys.stderr,
        )
    except Exception as e:  # noqa: BLE001 — 어떤 이유로든 commit을 막지 않는다
        print(f"(kb-drain-check skipped: {e})", file=sys.stderr)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="KB 큐 미드레인 경고 (비차단)")
    parser.add_argument("--days", type=int, default=3, help="미드레인 임계 일수 (기본 3)")
    args = parser.parse_args()
    return check(args.days)


if __name__ == "__main__":
    sys.exit(main())

"""shared 경계 검문소.

`packages/shared/` 하위 모듈은 `apps/*`, `macro` 같은 상위 앱 패키지를 import하면
안 된다(단방향 경계). 새 위반이 생기면 이 테스트가 FAIL한다.

현재 묵은 부채 5건은 `KNOWN_VIOLATIONS`로 동결되어 있다 — 이 테스트는 "새 위반"만
잡는다. 동결 항목은 별도 소진 트랙(TASKQUEUE)에서 청소한다.

구현 메모:
    - 모듈 import 금지 (Django 셋업/순환 폭발 회피). source를 `ast.parse`로 파싱.
    - `ast.walk`로 Import / ImportFrom 전수 — top-level + 함수 내 lazy 모두 검출.
    - 세그먼트 단위 비교: `macrodata` 같은 prefix 오탐 회피.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SHARED_ROOT = Path(__file__).resolve().parents[2] / "packages" / "shared"

FORBIDDEN_TOP_SEGMENTS = ("apps", "macro")

# 키 = (packages/shared 기준 상대경로 POSIX, import된 module 문자열)
# 라인번호는 키에 포함하지 않는다 — 드리프트로 깨지기 때문.
KNOWN_VIOLATIONS: set[tuple[str, str]] = {
    # #1·#2 (sp500_eod_service, sp500_service → circuit_breaker): 2026-06-01 BOUNDARY-1 청소
    # 완료 (circuit_breaker → packages/shared/api_request 이동, 이제 shared→shared).
    # #3 (daily_report → apps.chain_sight.models): 2026-06-01 BOUNDARY-2 청소 완료
    # (Django apps.get_model 동적 lookup으로 변환, cross-app aggregator 표준 패턴).
    ("stocks/services/eod_regime_calculator.py", "macro.models"),
    ("stocks/services/eod_pipeline.py", "macro.models"),
}


def _is_forbidden(module: str) -> bool:
    """세그먼트 단위로 금지 prefix 매칭. `macrodata` 같은 오탐 회피."""
    if not module:
        return False
    top = module.split(".", 1)[0]
    return top in FORBIDDEN_TOP_SEGMENTS


def _collect_violations() -> list[tuple[str, str, int]]:
    """packages/shared 전 .py에서 (rel_path, module, lineno) 위반 전부 수집."""
    found: list[tuple[str, str, int]] = []
    for py in SHARED_ROOT.rglob("*.py"):
        try:
            source = py.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(py))
        except (SyntaxError, UnicodeDecodeError):
            continue

        rel = py.relative_to(SHARED_ROOT).as_posix()

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                # 상대 import (`from . import x`, level >= 1)는 shared 내부 — 제외
                if node.level and node.level > 0:
                    continue
                mod = node.module or ""
                if _is_forbidden(mod):
                    found.append((rel, mod, node.lineno))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if _is_forbidden(alias.name):
                        found.append((rel, alias.name, node.lineno))
    return found


def test_shared_root_exists() -> None:
    assert SHARED_ROOT.is_dir(), f"packages/shared 누락: {SHARED_ROOT}"


def test_no_new_boundary_violations() -> None:
    """KNOWN_VIOLATIONS에 없는 새 우회는 즉시 FAIL."""
    violations = _collect_violations()
    new = [(rel, mod, line) for (rel, mod, line) in violations if (rel, mod) not in KNOWN_VIOLATIONS]
    if new:
        lines = "\n".join(f"  - {rel}:{line}  ← from {mod}" for (rel, mod, line) in new)
        pytest.fail(
            "packages/shared 경계 위반 새로 검출됨 "
            "(shared는 apps/* / macro/* 를 import 금지):\n"
            f"{lines}\n\n"
            "해결: 의존 방향을 뒤집거나 shared 쪽으로 필요 심볼을 승격. "
            "정당한 사유로 임시 동결이 필요하면 "
            "tests/architecture/test_shared_boundary.py:KNOWN_VIOLATIONS에 "
            "(상대경로, module) 키로 추가 + TASKQUEUE 소진 항목 등록 필수."
        )


def test_known_violations_still_present() -> None:
    """동결 키가 실제로 살아있는지 확인. 사라졌으면 KNOWN_VIOLATIONS에서 빼야 함(드리프트 방지)."""
    violations = _collect_violations()
    present_keys = {(rel, mod) for (rel, mod, _line) in violations}
    stale = KNOWN_VIOLATIONS - present_keys
    if stale:
        stale_lines = "\n".join(f"  - {rel}  ← from {mod}" for (rel, mod) in sorted(stale))
        pytest.fail(
            "KNOWN_VIOLATIONS에 등록된 항목이 실제 코드에 더 이상 없음. "
            "청소가 끝났다면 KNOWN_VIOLATIONS에서 삭제하라:\n"
            f"{stale_lines}"
        )

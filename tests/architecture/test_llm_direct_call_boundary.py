"""외부-LLM-직접호출 검문소 (BOUNDARY-LLM 슬라이스 ③).

`apps/`·`packages/`·`services/` 하위에서 외부 LLM SDK를 **직접** 인스턴스화/호출하면
안 된다 — 모든 호출은 `packages/shared/llm/`의 단일 진입점(`complete()`)을 경유해야 한다.
직접 호출 패턴(`genai.Client(...)`, `X.GenerativeModel(...)`, `Anthropic(...)`,
`AsyncAnthropic(...)`)이 **새로** 생기면 이 테스트가 FAIL한다.

현재 미이관 부채 23건은 `KNOWN_VIOLATIONS`로 동결되어 있다 — 이 테스트는 "새 위반"만
잡는다(이관분 회귀 잠금). 동결 항목은 슬라이스 ④ 소진 트랙에서 청소한다.
동결 N = 슬라이스 ④ 진행 게이지(이관 1곳 = 동결 1곳 해제, 0 = 완료).

예외(가드 통과):
    - `packages/shared/llm/providers/**` — 코어 provider는 직접 호출이 정상(여기로 모으는 게 목적).
    - korean_overview_service: 슬라이스 ②에서 이미 이관됨 → 동결에 **없음**.
      다시 genai 직접호출하면 이 가드가 즉시 FAIL(회귀 잠금 작동).

구현 메모:
    - 모듈 import 금지(Django 셋업/순환 폭발 회피). source를 `ast.parse`로 파싱.
    - `ast.walk`로 `ast.Call` 노드 전수 — 코멘트/독스트링/mock 속성대입은 Call이 아니라
      자연 제외(grep과 달리 오탐 0).
    - 키 = (repo 기준 상대경로 POSIX, 호출 식별자). 라인번호는 키에서 제외(드리프트 방지).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCAN_DIRS = ("apps", "packages", "services")

# 코어 provider는 정상 직접호출 — 가드 예외(여기로 모으는 게 목적).
CORE_EXEMPT_PREFIX = "packages/shared/llm/"

# func=Name() 호출로 잡는 SDK 생성자.
NAME_CALLS = frozenset({"Anthropic", "AsyncAnthropic"})

# 키 = (repo 기준 상대경로 POSIX, 호출 식별자). 라인번호는 키에 포함하지 않는다.
# 슬라이스 ②에서 korean_overview는 이관 완료 → 목록에 없음(회귀 잠금 작동).
# 동결 23 = 슬라이스 ④ 진행 게이지. 이관 1곳마다 여기서 1키 삭제 + health_check 동시 갱신.
KNOWN_VIOLATIONS: set[tuple[str, str]] = {
    ("apps/portfolio/llm/client.py", "Anthropic"),
    ("apps/portfolio/measure/estimator_v3.py", "Anthropic"),
    ("services/rag_analysis/services/adaptive_llm_service.py", "AsyncAnthropic"),
    ("services/rag_analysis/services/adaptive_llm_service.py", "GenerativeModel"),
    ("services/rag_analysis/services/llm_service.py", "genai.Client"),
    ("services/serverless/services/keyword_generator.py", "genai.Client"),
    ("services/serverless/services/llm_relation_extractor.py", "genai.Client"),
}

# health_check.py와 반드시 일치(규약: 양쪽 동시 갱신). 불일치 시 두 곳 다 깨진다.
# Part ①-aio burn-down: 10 → 9 → 8 → 7(keyword_generator_v2) → 6(keyword_generator #16)
FROZEN_COUNT = 7


def _call_identifier(node: ast.Call) -> str | None:
    """직접-LLM-호출이면 식별자 문자열, 아니면 None.

    - `Anthropic(...)` / `AsyncAnthropic(...)`     → func=Name
    - `genai.Client(...)`                          → func=Attribute(value=Name('genai'), attr='Client')
    - `X.GenerativeModel(...)`                     → func=Attribute(attr='GenerativeModel')
    """
    func = node.func
    if isinstance(func, ast.Name) and func.id in NAME_CALLS:
        return func.id
    if isinstance(func, ast.Attribute):
        if func.attr == "Client" and isinstance(func.value, ast.Name) and func.value.id == "genai":
            return "genai.Client"
        if func.attr == "GenerativeModel":
            return "GenerativeModel"
    return None


def _collect_violations() -> list[tuple[str, str, int]]:
    """SCAN_DIRS 전 .py에서 (rel_path, identifier, lineno) 직접호출 전부 수집.

    코어 provider(CORE_EXEMPT_PREFIX)는 제외.
    """
    found: list[tuple[str, str, int]] = []
    for d in SCAN_DIRS:
        root = REPO_ROOT / d
        if not root.is_dir():
            continue
        for py in root.rglob("*.py"):
            rel = py.relative_to(REPO_ROOT).as_posix()
            if rel.startswith(CORE_EXEMPT_PREFIX):
                continue
            try:
                tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
            except (SyntaxError, UnicodeDecodeError):
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    ident = _call_identifier(node)
                    if ident is not None:
                        found.append((rel, ident, node.lineno))
    return found


def test_scan_dirs_exist() -> None:
    present = [d for d in SCAN_DIRS if (REPO_ROOT / d).is_dir()]
    assert present, f"스캔 대상 디렉토리 전무: {SCAN_DIRS} under {REPO_ROOT}"


def test_no_new_direct_llm_calls() -> None:
    """KNOWN_VIOLATIONS에 없는 새 외부-LLM-직접호출은 즉시 FAIL."""
    violations = _collect_violations()
    new = [(rel, ident, line) for (rel, ident, line) in violations if (rel, ident) not in KNOWN_VIOLATIONS]
    if new:
        lines = "\n".join(f"  - {rel}:{line}  ← {ident}(...)" for (rel, ident, line) in new)
        pytest.fail(
            "외부-LLM-직접호출이 새로 검출됨 "
            "(모든 LLM 호출은 packages/shared/llm 의 complete() 단일 진입점 경유):\n"
            f"{lines}\n\n"
            "해결: genai.Client/GenerativeModel/Anthropic/AsyncAnthropic 직접 생성 대신 "
            "packages.shared.llm.complete() 를 호출하라. "
            "정당한 사유로 임시 동결이 필요하면 "
            "tests/architecture/test_llm_direct_call_boundary.py:KNOWN_VIOLATIONS 에 "
            "(상대경로, 식별자) 키 추가 + FROZEN_COUNT/health_check 동시 갱신 + "
            "슬라이스 ④ 소진 항목 등록 필수."
        )


def test_known_violations_still_present() -> None:
    """동결 키가 실제 코드에 살아있는지 확인. 이관/삭제됐으면 KNOWN_VIOLATIONS에서 빼야 함.

    슬라이스 ④에서 소비처를 이관하면 해당 키가 사라지므로 여기서 stale로 잡힌다 →
    KNOWN_VIOLATIONS·FROZEN_COUNT·health_check를 동시에 줄이라는 신호.
    """
    violations = _collect_violations()
    present_keys = {(rel, ident) for (rel, ident, _line) in violations}
    stale = KNOWN_VIOLATIONS - present_keys
    if stale:
        stale_lines = "\n".join(f"  - {rel}  ← {ident}" for (rel, ident) in sorted(stale))
        pytest.fail(
            "KNOWN_VIOLATIONS에 등록된 직접호출이 실제 코드에 더 이상 없음(이관/삭제됨). "
            "KNOWN_VIOLATIONS에서 삭제하고 FROZEN_COUNT·health_check를 동시에 줄여라:\n"
            f"{stale_lines}"
        )


def test_frozen_count_matches_known_violations() -> None:
    """FROZEN_COUNT(=health_check와 공유하는 숫자)가 KNOWN_VIOLATIONS 크기와 일치하는지.

    규약: 동결 목록과 게이지 수치는 양쪽 동시 갱신. 어긋나면 둘 중 하나만 고친 것.
    """
    assert FROZEN_COUNT == len(KNOWN_VIOLATIONS), (
        f"FROZEN_COUNT({FROZEN_COUNT}) != len(KNOWN_VIOLATIONS)({len(KNOWN_VIOLATIONS)}). "
        "동결 항목을 추가/삭제했다면 FROZEN_COUNT와 scripts/health_check.py 를 동시에 갱신하라."
    )

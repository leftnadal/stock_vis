"""정책: 신뢰경계 escape (prompt injection 차단). escape=True일 때만 prompt 변환.

베이스 패턴(성숙 2곳 — services/rag_analysis/services/llm_service.py·
services/serverless/services/thesis_builder.py): 신뢰경계 래퍼의 *닫는 태그*를 escape해
비신뢰 입력이 경계를 위조하지 못하게 차단. 27곳 중 2곳에만 존재하던 보호를 코어로 끌어올림.
"""

from __future__ import annotations

# 신뢰경계 닫는 태그 — 위조 시 escape 대상 (성숙 2곳 패턴 흡수).
_DEFAULT_BOUNDARY_TAGS = (
    "</context_data>",
    "</user_question>",
    "</user_note_untrusted>",
)


def escape_untrusted(
    value: str, *, tags: tuple[str, ...] = _DEFAULT_BOUNDARY_TAGS
) -> str:
    """비신뢰 입력의 닫는 태그를 escape(`</x>` → `</x_escaped>`)해 경계 위조 차단."""
    out = value
    for tag in tags:
        out = out.replace(tag, tag[:-1] + "_escaped>")
    return out

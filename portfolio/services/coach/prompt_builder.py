"""Slice 11 Part 3 — A2 통합 진입점용 prompt builder.

Base + 6 sub class (E1~E6). Part 1 `commentary_input` + Part 2 `commentary_output`
schema와 1:1 대응. Anthropic Messages API 호출용 messages list 생성.

설계 원칙 (지시서 §1.2):
  - **stateless classmethod** (인스턴스 X) — Part 1/2 schema의 frozen=True 미러.
  - `build_system_prompt`은 base에서 통합 (output schema JSON 자동 injection).
  - `build_user_prompt`는 sub class별 구현.
  - `build_messages`는 base에서 통합 — `[system, user]` 2개 메시지 배열.

scope (Part 3):
  - **E1PromptBuilder**: 풀 구현 (smoke 검증).
  - E2~E6PromptBuilder: 스켈레톤 — `build_user_prompt` 호출 시 `NotImplementedError`
    (Part 4에서 마이그레이션 예정).
"""

from __future__ import annotations

import json
from typing import Any, ClassVar

from portfolio.schemas.commentary_input import (
    CommentaryInputBase,
    CommentaryInputE1,
    CommentaryInputE2,
    CommentaryInputE3,
    CommentaryInputE4,
    CommentaryInputE5,
    CommentaryInputE6,
)
from portfolio.schemas.commentary_output import (
    COMMENTARY_OUTPUT_CLASSES,
    CommentaryOutputBase,
    E1Output,
    E2Output,
    E3Output,
    E4Output,
    E5Output,
    E6Output,
)


# ============================================================
# Base
# ============================================================


class PromptBuilderBase:
    """공통 prompt builder. Base는 stateless classmethod 패턴 (인스턴스 X).

    sub class가 정의해야 할 ClassVar:
        - entry_point: "e1"~"e6"
        - input_schema: CommentaryInputBase 하위 type
        - output_schema: CommentaryOutputBase 하위 type
    """

    entry_point: ClassVar[str] = ""
    input_schema: ClassVar[type[CommentaryInputBase]] = CommentaryInputBase
    output_schema: ClassVar[type[CommentaryOutputBase]] = CommentaryOutputBase

    SYSTEM_HEADER: ClassVar[str] = (
        "당신은 한국어 투자 포트폴리오 코치입니다. 정확한 사실 + 자연스러운 한국어로 답변하세요.\n"
        "응답은 반드시 다음 JSON schema를 준수해야 합니다 (extra 필드 금지):"
    )

    @classmethod
    def build_user_prompt(cls, input_data: CommentaryInputBase) -> str:
        """진입점별 user prompt — sub class에서 구현."""
        raise NotImplementedError(
            f"{cls.__name__}.build_user_prompt — sub class에서 구현 필요."
        )

    @classmethod
    def build_system_prompt(cls) -> str:
        """공통 system prompt — output schema JSON 형식 자동 injection."""
        schema = cls.output_schema.model_json_schema()
        schema_json = json.dumps(schema, ensure_ascii=False, indent=2)
        return f"{cls.SYSTEM_HEADER}\n\n{schema_json}"

    @classmethod
    def build_messages(cls, input_data: CommentaryInputBase) -> list[dict[str, str]]:
        """LLM Messages API 용 [system, user] 2개 메시지 배열.

        Note: Anthropic Messages API는 system을 별도 인자로 받음. 본 메서드는 일반화된
        OpenAI 호환 형식을 반환. Anthropic 호출 시 system을 분리해 전달.
        """
        return [
            {"role": "system", "content": cls.build_system_prompt()},
            {"role": "user", "content": cls.build_user_prompt(input_data)},
        ]


# ============================================================
# E1 — Full implementation
# ============================================================


def _format_holdings(holdings: list) -> str:
    """holdings list → 가독성 좋은 markdown bullet."""
    lines = []
    for h in holdings:
        meta = []
        if h.sector:
            meta.append(f"sector={h.sector}")
        if h.asset_class:
            meta.append(f"class={h.asset_class}")
        meta_str = f" ({', '.join(meta)})" if meta else ""
        name_str = f" — {h.name}" if h.name else ""
        lines.append(f"- {h.ticker}{name_str}: 비중 {h.weight:.2%}{meta_str}")
    return "\n".join(lines)


class E1PromptBuilder(PromptBuilderBase):
    """E1 GARP 스코어링 commentary prompt."""

    entry_point: ClassVar[str] = "e1"
    input_schema: ClassVar[type[CommentaryInputE1]] = CommentaryInputE1
    output_schema: ClassVar[type[E1Output]] = E1Output

    @classmethod
    def build_user_prompt(cls, input_data: CommentaryInputE1) -> str:
        holdings_md = _format_holdings(input_data.holdings)
        metrics_json = json.dumps(input_data.garp_metrics, ensure_ascii=False, indent=2)
        return (
            f"# 포트폴리오 GARP 분석 요청\n\n"
            f"- portfolio_id: {input_data.portfolio_id}\n"
            f"- preset: {input_data.preset}\n"
            f"- fetched_at: {input_data.fetched_at.isoformat()}\n\n"
            f"## 보유 종목 ({len(input_data.holdings)}개)\n{holdings_md}\n\n"
            f"## GARP 지표 (종목별 PER/PEG/ROE/yield)\n```json\n{metrics_json}\n```\n\n"
            f"## 작업\n"
            f"포트폴리오의 GARP(Growth at a Reasonable Price) 적합성을 한국어로 평가하세요.\n"
            f"- summary: 1줄 요약\n"
            f"- key_observations: 핵심 관찰 사항 (최대 5개)\n"
            f"- action_items: 실행 가능 액션 (없으면 빈 배열)\n"
            f"- risk_flags: 위험 신호 (없으면 빈 배열)\n"
            f"- metrics_table: deprecated — 빈 문자열 ''\n"
            f"- confidence: high/medium/low 중 하나\n"
        )


# ============================================================
# E2~E6 — Skeletons (Part 4에서 마이그레이션 예정)
# ============================================================


class _NotImplementedBuilderMixin:
    """sub class build_user_prompt 호출 시 일관된 NotImplementedError 발생."""

    @classmethod
    def build_user_prompt(cls, input_data: Any) -> str:
        raise NotImplementedError(
            f"{cls.__name__}.build_user_prompt — Part 4에서 마이그레이션 예정. "
            "현재 Part 3은 E1만 풀 구현."
        )


class E2PromptBuilder(_NotImplementedBuilderMixin, PromptBuilderBase):
    """E2 종합 진단 (Part 4 skeleton)."""

    entry_point: ClassVar[str] = "e2"
    input_schema: ClassVar[type[CommentaryInputE2]] = CommentaryInputE2
    output_schema: ClassVar[type[E2Output]] = E2Output


class E3PromptBuilder(_NotImplementedBuilderMixin, PromptBuilderBase):
    """E3 집중도 분석 (Part 4 skeleton)."""

    entry_point: ClassVar[str] = "e3"
    input_schema: ClassVar[type[CommentaryInputE3]] = CommentaryInputE3
    output_schema: ClassVar[type[E3Output]] = E3Output


class E4PromptBuilder(_NotImplementedBuilderMixin, PromptBuilderBase):
    """E4 대화 Q&A (Part 4 skeleton)."""

    entry_point: ClassVar[str] = "e4"
    input_schema: ClassVar[type[CommentaryInputE4]] = CommentaryInputE4
    output_schema: ClassVar[type[E4Output]] = E4Output


class E5PromptBuilder(_NotImplementedBuilderMixin, PromptBuilderBase):
    """E5 추출 (Part 4 skeleton)."""

    entry_point: ClassVar[str] = "e5"
    input_schema: ClassVar[type[CommentaryInputE5]] = CommentaryInputE5
    output_schema: ClassVar[type[E5Output]] = E5Output


class E6PromptBuilder(_NotImplementedBuilderMixin, PromptBuilderBase):
    """E6 분석엔진 (Part 4 skeleton)."""

    entry_point: ClassVar[str] = "e6"
    input_schema: ClassVar[type[CommentaryInputE6]] = CommentaryInputE6
    output_schema: ClassVar[type[E6Output]] = E6Output


# Registry — Part 1/2 registry 미러.
PROMPT_BUILDER_CLASSES: dict[str, type[PromptBuilderBase]] = {
    "e1": E1PromptBuilder,
    "e2": E2PromptBuilder,
    "e3": E3PromptBuilder,
    "e4": E4PromptBuilder,
    "e5": E5PromptBuilder,
    "e6": E6PromptBuilder,
}


# Sanity check: Part 2 output classes registry와 키 1:1 대응.
assert set(PROMPT_BUILDER_CLASSES) == set(COMMENTARY_OUTPUT_CLASSES), (
    "PROMPT_BUILDER_CLASSES와 COMMENTARY_OUTPUT_CLASSES 키 불일치"
)

"""Slice 11 Part 3 — A2 통합 진입점용 prompt builder.

Base + 6 sub class (E1~E6). Part 1 `commentary_input` + Part 2 `commentary_output`
schema와 1:1 대응. Anthropic Messages API 호출용 messages list 생성.

설계 원칙 (지시서 §1.2):
  - **stateless classmethod** (인스턴스 X) — Part 1/2 schema의 frozen=True 미러.
  - `build_system_prompt`은 base에서 통합 (output schema JSON 자동 injection).
  - `build_user_prompt`는 sub class별 구현.
  - `build_messages`는 base에서 통합 — `[system, user]` 2개 메시지 배열.

scope (Part 4):
  - **E1~E6PromptBuilder**: 풀 구현. portfolio_a2 fixture로 모두 검증.
  - 기존 production endpoint (E2/E3/E5/E6)는 무변경. 본 builder는 Part 1/2 통합
    schema 전용 신규 A2 진입점.
"""

from __future__ import annotations

import json
from typing import ClassVar

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
# E2 — 포트폴리오 종합 진단
# ============================================================


class E2PromptBuilder(PromptBuilderBase):
    """E2 종합 진단 commentary prompt. portfolio_return_1y + sector_allocation 활용."""

    entry_point: ClassVar[str] = "e2"
    input_schema: ClassVar[type[CommentaryInputE2]] = CommentaryInputE2
    output_schema: ClassVar[type[E2Output]] = E2Output

    @classmethod
    def build_user_prompt(cls, input_data: CommentaryInputE2) -> str:
        holdings_md = _format_holdings(input_data.holdings)
        sector_json = json.dumps(
            input_data.sector_allocation, ensure_ascii=False, indent=2
        )
        return (
            f"# 포트폴리오 종합 진단 요청\n\n"
            f"- portfolio_id: {input_data.portfolio_id}\n"
            f"- preset: {input_data.preset}\n"
            f"- fetched_at: {input_data.fetched_at.isoformat()}\n"
            f"- portfolio_return_1y: {input_data.portfolio_return_1y:.2f}%\n\n"
            f"## 보유 종목 ({len(input_data.holdings)}개)\n{holdings_md}\n\n"
            f"## 섹터 비중\n```json\n{sector_json}\n```\n\n"
            f"## 작업\n"
            f"포트폴리오 1년 수익률과 섹터 비중을 바탕으로 종합 진단을 한국어로 작성하세요.\n"
            f"- summary: 1줄 요약 (수익률 + 핵심 특징)\n"
            f"- key_observations: 핵심 관찰 사항 (최대 5개, 섹터 편중/수익률 해석)\n"
            f"- quoted_metrics: 인용한 지표 dict (예: {{\"top_sector\": \"consumer_staples 35%\", \"return_1y\": \"8.2%\"}})\n"
            f"- metrics_table: deprecated — 빈 문자열 ''\n"
            f"- confidence: high/medium/low 중 하나\n"
        )


# ============================================================
# E3 — 집중도 분석
# ============================================================


_E3_ACTION_RULES = (
    "### action_items 작성 규칙 (필수 준수, Slice 12 Step 0 #59)\n"
    "1. 구체성 필수 — description에 다음 중 하나 이상 포함:\n"
    "   - 종목 ticker (예: \"VYM 비중 조정\")\n"
    "   - 정량 지표 (예: \"HHI 0.2125 → 0.18 목표\")\n"
    "   - 비율/수치 (예: \"소비재 35% → 25% 축소\")\n"
    "2. 측정 가능성 필수 — description에 다음 중 하나 이상 포함:\n"
    "   - 목표 수치 (예: \"Top3 비중 65% → 50%\")\n"
    "   - 기한/시기 (예: \"분기 리밸런싱 시\", \"현재 분기 내\")\n"
    "3. 금지 패턴 (단독 사용 금지, 구체 수치 함께면 OK):\n"
    "   - \"모니터링 필요\" 단독\n"
    "   - \"검토하세요\" 단독\n"
    "   - \"주시하세요\" 단독\n"
    "   - 종목/지표 인용 없는 일반론 (예: \"장기적 관점에서 다각화\")\n"
    "4. priority 정합성:\n"
    "   - high: 즉각 행동 (예: \"1주 내 비중 조정\")\n"
    "   - medium: 분기 단위 검토 (예: \"다음 리밸런싱 시\")\n"
    "   - low: 장기 모니터링 (단, 구체적 지표 + 임계 명시 필수)\n"
)


class E3PromptBuilder(PromptBuilderBase):
    """E3 집중도 분석 commentary prompt. concentration_metrics (hhi/top3 등) 활용.

    Slice 12 Step 0 #59: action_items measurability 규칙 4종 명시.
    Slice 11 Part 5 E3 NG ratio 50% → 운영 기준 < 30% 목표.
    """

    entry_point: ClassVar[str] = "e3"
    input_schema: ClassVar[type[CommentaryInputE3]] = CommentaryInputE3
    output_schema: ClassVar[type[E3Output]] = E3Output

    @classmethod
    def build_user_prompt(cls, input_data: CommentaryInputE3) -> str:
        holdings_md = _format_holdings(input_data.holdings)
        metrics_json = json.dumps(
            input_data.concentration_metrics, ensure_ascii=False, indent=2, default=str
        )
        return (
            f"# 포트폴리오 집중도 분석 요청\n\n"
            f"- portfolio_id: {input_data.portfolio_id}\n"
            f"- preset: {input_data.preset}\n"
            f"- fetched_at: {input_data.fetched_at.isoformat()}\n\n"
            f"## 보유 종목 ({len(input_data.holdings)}개)\n{holdings_md}\n\n"
            f"## 집중도 지표 (hhi/top3_weight/sector_top_weight/single_name_max 등)\n"
            f"```json\n{metrics_json}\n```\n\n"
            f"## 작업\n"
            f"포트폴리오 집중도 위험을 한국어로 평가하세요.\n"
            f"- summary: 1줄 요약 (집중 수준 + 핵심 위험)\n"
            f"- key_observations: 핵심 관찰 사항 (최대 5개)\n"
            f"- action_items: 실행 가능 액션 (재조정/검토 위주, 없으면 빈 배열)\n"
            f"- risk_flags: 위험 신호 (집중 위험, 섹터 편중 등; 없으면 빈 배열)\n"
            f"- confidence: high/medium/low 중 하나\n\n"
            f"{_E3_ACTION_RULES}"
        )


# ============================================================
# E4 — 대화 Q&A
# ============================================================


class E4PromptBuilder(PromptBuilderBase):
    """E4 대화 Q&A commentary prompt. user_question + conversation_history 활용."""

    entry_point: ClassVar[str] = "e4"
    input_schema: ClassVar[type[CommentaryInputE4]] = CommentaryInputE4
    output_schema: ClassVar[type[E4Output]] = E4Output

    @classmethod
    def build_user_prompt(cls, input_data: CommentaryInputE4) -> str:
        holdings_md = _format_holdings(input_data.holdings)
        if input_data.conversation_history:
            history_json = json.dumps(
                input_data.conversation_history, ensure_ascii=False, indent=2
            )
            history_block = f"\n## 대화 이력\n```json\n{history_json}\n```\n"
        else:
            history_block = "\n## 대화 이력\n(없음 — 첫 질문)\n"
        return (
            f"# 포트폴리오 Q&A 요청\n\n"
            f"- portfolio_id: {input_data.portfolio_id}\n"
            f"- preset: {input_data.preset}\n"
            f"- fetched_at: {input_data.fetched_at.isoformat()}\n\n"
            f"## 보유 종목 ({len(input_data.holdings)}개)\n{holdings_md}\n"
            f"{history_block}\n"
            f"## 사용자 질문\n\"{input_data.user_question}\"\n\n"
            f"## 작업\n"
            f"사용자의 질문에 한국어로 답변하세요. 단순 수치 나열 금지, 의미 있는 해석 포함.\n"
            f"- summary: 답변 1줄 요약\n"
            f"- key_observations: 핵심 관찰 사항 (질문 답변 근거; 최대 5개)\n"
            f"- confidence: high/medium/low 중 하나\n"
            f"\n주의: 매수/매도 추천 금지. 구조적 해설만.\n"
        )


# ============================================================
# E5 — 추출 + 시계열 해설
# ============================================================


class E5PromptBuilder(PromptBuilderBase):
    """E5 추출 commentary prompt. extraction_targets + time_series_context 활용."""

    entry_point: ClassVar[str] = "e5"
    input_schema: ClassVar[type[CommentaryInputE5]] = CommentaryInputE5
    output_schema: ClassVar[type[E5Output]] = E5Output

    @classmethod
    def build_user_prompt(cls, input_data: CommentaryInputE5) -> str:
        holdings_md = _format_holdings(input_data.holdings)
        targets_str = ", ".join(input_data.extraction_targets)
        if input_data.time_series_context is not None:
            ts = input_data.time_series_context
            ts_lines = [f"- current: {ts.current}"]
            if ts.window_1q is not None:
                ts_lines.append(f"- window_1q: {ts.window_1q}")
            if ts.window_4q is not None:
                ts_lines.append(f"- window_4q: {ts.window_4q}")
            if ts.window_12q is not None:
                ts_lines.append(f"- window_12q: {ts.window_12q}")
            if ts.delta_4q_pct is not None:
                ts_lines.append(f"- delta_4q_pct: {ts.delta_4q_pct:.2f}%")
            ts_block = "\n## 시계열 컨텍스트\n" + "\n".join(ts_lines) + "\n"
        else:
            ts_block = "\n## 시계열 컨텍스트\n(없음)\n"
        return (
            f"# 포트폴리오 추출 + 시계열 해설 요청\n\n"
            f"- portfolio_id: {input_data.portfolio_id}\n"
            f"- preset: {input_data.preset}\n"
            f"- fetched_at: {input_data.fetched_at.isoformat()}\n\n"
            f"## 보유 종목 ({len(input_data.holdings)}개)\n{holdings_md}\n\n"
            f"## 추출 대상\n{targets_str}\n"
            f"{ts_block}\n"
            f"## 작업\n"
            f"추출 대상 항목을 분석하고, 시계열 컨텍스트가 있다면 변화율과 추세까지 해석하세요.\n"
            f"- summary: 1줄 요약 (추출값 + 추세 핵심)\n"
            f"- key_observations: 핵심 관찰 사항 (최대 5개)\n"
            f"- action_items: 실행 가능 액션 (시계열 추세 기반; 없으면 빈 배열)\n"
            f"- quoted_metrics: 추출한 지표 dict (예: {{\"dividend_yield\": \"3.45% (12분기 +30bp)\"}})\n"
            f"- confidence: high/medium/low 중 하나\n"
        )


# ============================================================
# E6 — 종목별 분석 결과 종합
# ============================================================


class E6PromptBuilder(PromptBuilderBase):
    """E6 분석 결과 종합 prompt. analysis_results (종목별 score/signals/notes) 활용."""

    entry_point: ClassVar[str] = "e6"
    input_schema: ClassVar[type[CommentaryInputE6]] = CommentaryInputE6
    output_schema: ClassVar[type[E6Output]] = E6Output

    @classmethod
    def build_user_prompt(cls, input_data: CommentaryInputE6) -> str:
        holdings_md = _format_holdings(input_data.holdings)
        results_json = json.dumps(
            input_data.analysis_results, ensure_ascii=False, indent=2, default=str
        )
        return (
            f"# 종목별 분석 결과 종합 요청\n\n"
            f"- portfolio_id: {input_data.portfolio_id}\n"
            f"- preset: {input_data.preset}\n"
            f"- fetched_at: {input_data.fetched_at.isoformat()}\n\n"
            f"## 보유 종목 ({len(input_data.holdings)}개)\n{holdings_md}\n\n"
            f"## 종목별 분석 결과 (score / signals / notes)\n```json\n{results_json}\n```\n\n"
            f"## 작업\n"
            f"종목별 분석 결과를 종합하여 포트폴리오 차원의 평가를 한국어로 작성하세요.\n"
            f"- summary: 1줄 요약 (포트폴리오 종합 평가)\n"
            f"- key_observations: 핵심 관찰 사항 (강점/약점 균형; 최대 5개)\n"
            f"- risk_flags: 위험 신호 (낮은 score 종목, yield trap 등; 없으면 빈 배열)\n"
            f"- quoted_metrics: 인용한 지표 dict (예: {{\"VZ\": \"score 6.8, yield trap risk\"}})\n"
            f"- confidence: high/medium/low 중 하나\n"
        )


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

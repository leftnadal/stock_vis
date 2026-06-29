"""provider 프로토콜 — generate(prompt, model, system, max_tokens) -> LLMRawResponse."""

from __future__ import annotations

from typing import Optional, Protocol

from packages.shared.llm.types import LLMRawResponse


class Provider(Protocol):
    """LLM provider 어댑터 프로토콜. 구현체는 SDK 예외를 코어 예외 계층으로 분류한다."""

    name: str
    default_model: str

    def generate(
        self,
        prompt: str,
        *,
        model: Optional[str],
        system: Optional[str],
        max_tokens: Optional[int],
        temperature: Optional[float] = None,
        response_format: Optional[str] = None,
        extra: Optional[dict] = None,
    ) -> LLMRawResponse:
        ...

    async def agenerate(
        self,
        prompt: str,
        *,
        model: Optional[str],
        system: Optional[str],
        max_tokens: Optional[int],
        temperature: Optional[float] = None,
        response_format: Optional[str] = None,
        extra: Optional[dict] = None,
    ) -> LLMRawResponse:
        """비동기 생성 (슬라이스 ②b). 미구현 provider는 NotImplementedError."""
        ...

    async def aopen_stream(
        self,
        prompt: str,
        *,
        model: Optional[str],
        system: Optional[str],
        max_tokens: Optional[int],
        temperature: Optional[float] = None,
        response_format: Optional[str] = None,
        extra: Optional[dict] = None,
    ):
        """비동기 스트림 셋업만 — 요청 전송 + 스트림 오픈 후 SDK async iterator 반환 (슬라이스 ④).

        청크 읽기는 호출자가 수행. 코어 astream(circuit=)이 이 셋업 coroutine만 CB로 감싸기 위한
        경계 분리점. 미구현 provider는 NotImplementedError. coroutine(async def), not generator.
        """
        ...

    def astream(
        self,
        prompt: str,
        *,
        model: Optional[str],
        system: Optional[str],
        max_tokens: Optional[int],
        temperature: Optional[float] = None,
        response_format: Optional[str] = None,
        extra: Optional[dict] = None,
    ):
        """비동기 스트리밍 — 청크 증분 yield하는 async generator (슬라이스 ②b-stream).

        미구현 provider는 NotImplementedError(반복 시점). 반환 타입은 AsyncGenerator.
        """
        ...

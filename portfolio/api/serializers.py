"""Slice 13 Part 1 — DRF serializers (Pydantic 어댑터).

설계 원칙 (지시서 §1):
  - Pydantic 단일 진실 소스: `CommentaryInputE1` / `E1Output`이 검증 로직 보유.
  - DRF serializer는 얇은 어댑터 — 필드별 비즈니스 검증을 중복 구현하지 않는다.
  - Pydantic ValidationError → DRF ValidationError로 변환해 400 응답으로 흐르게.

본 모듈은 Slice 13 Part 1에서 E1만 구현. Part 2+에서 E2~E6 동일 패턴 확장 예정.
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError as PydanticValidationError
from rest_framework import serializers

from portfolio.schemas.commentary_input import (
    CommentaryInputE1,
    CommentaryInputE2,
    CommentaryInputE3,
)
from portfolio.schemas.commentary_output import E1Output, E2Output, E3Output


class E1RequestSerializer(serializers.Serializer):
    """E1 coach 요청 어댑터.

    검증 책임은 Pydantic `CommentaryInputE1`에 위임. DRF serializer는
    원시 dict를 받아 Pydantic 모델 생성 시도 → 실패 시 DRF ValidationError로 변환.
    """

    def to_internal_value(self, data: Any) -> CommentaryInputE1:
        """원시 dict → CommentaryInputE1 인스턴스.

        DRF 표준 패턴: to_internal_value가 검증 + 변환 진입점.
        Pydantic 검증 실패 시 DRF ValidationError(400) raise.
        """
        if not isinstance(data, dict):
            raise serializers.ValidationError(
                {"detail": "Request body must be a JSON object."}
            )
        try:
            return CommentaryInputE1(**data)
        except PydanticValidationError as exc:
            # Pydantic 에러 → DRF 에러 형식으로 변환 (필드별 에러 보존)
            raise serializers.ValidationError(_pydantic_errors_to_dict(exc))

    def to_representation(self, instance: CommentaryInputE1) -> dict:
        """CommentaryInputE1 인스턴스 → dict (echo / debug용)."""
        return instance.model_dump(mode="json")


class E1ResponseSerializer(serializers.Serializer):
    """E1 coach 응답 어댑터.

    `run_e1_coach()` 반환 dict 형식:
        {
            "output": E1Output.model_dump() dict,
            "llm_metadata": {...},
            # Step 0a #60 옵션: gate_tier, preset_id (kwarg 전달 시만)
        }

    응답 스키마 계약: `output`은 반드시 E1Output 형식 — Part 1 contract test가 회귀 보호.
    """

    def to_representation(self, instance: dict) -> dict:
        """run_e1_coach 결과 dict → 응답 JSON.

        ★ E1Output 계약 검증을 본 어댑터에서 한 번 더 수행 — service 응답이 schema
        드리프트하면 즉시 ValidationError 발생 → 운영 안전망.
        """
        if not isinstance(instance, dict) or "output" not in instance:
            raise serializers.ValidationError(
                "run_e1_coach 응답에 'output' 키가 없습니다 (계약 위반)."
            )
        try:
            validated = E1Output(**instance["output"])
        except PydanticValidationError as exc:
            raise serializers.ValidationError(
                {"output_schema_drift": _pydantic_errors_to_dict(exc)}
            )

        result = {
            "output": validated.model_dump(mode="json"),
            "llm_metadata": instance.get("llm_metadata", {}),
        }
        # Step 0a #60 옵셔널 필드 — 존재 시만 응답 포함
        for opt_key in ("gate_tier", "preset_id", "scores"):
            if opt_key in instance:
                result[opt_key] = instance[opt_key]
        return result


class E2RequestSerializer(serializers.Serializer):
    """E2 coach 요청 어댑터 (E1 패턴 복제).

    검증 책임은 Pydantic `CommentaryInputE2`에 위임. Slice 13 Part 2 신규.
    """

    def to_internal_value(self, data: Any) -> CommentaryInputE2:
        if not isinstance(data, dict):
            raise serializers.ValidationError(
                {"detail": "Request body must be a JSON object."}
            )
        try:
            return CommentaryInputE2(**data)
        except PydanticValidationError as exc:
            raise serializers.ValidationError(_pydantic_errors_to_dict(exc))

    def to_representation(self, instance: CommentaryInputE2) -> dict:
        return instance.model_dump(mode="json")


class E2ResponseSerializer(serializers.Serializer):
    """E2 coach 응답 어댑터 (E1 패턴 복제).

    `run_e2_coach()` 반환 dict 형식:
        {"output": E2Output.model_dump() dict, "llm_metadata": {...}}

    응답 스키마 계약: `output`은 반드시 E2Output 형식 — contract test 회귀 보호.
    """

    def to_representation(self, instance: dict) -> dict:
        if not isinstance(instance, dict) or "output" not in instance:
            raise serializers.ValidationError(
                "run_e2_coach 응답에 'output' 키가 없습니다 (계약 위반)."
            )
        try:
            validated = E2Output(**instance["output"])
        except PydanticValidationError as exc:
            raise serializers.ValidationError(
                {"output_schema_drift": _pydantic_errors_to_dict(exc)}
            )

        result = {
            "output": validated.model_dump(mode="json"),
            "llm_metadata": instance.get("llm_metadata", {}),
        }
        for opt_key in ("gate_tier", "preset_id", "scores"):
            if opt_key in instance:
                result[opt_key] = instance[opt_key]
        return result


class E3RequestSerializer(serializers.Serializer):
    """E3 coach 요청 어댑터 (E2 패턴 복제).

    Slice 13 Part 3 신규. 검증 책임은 `CommentaryInputE3`에 위임.

    ★ preset_id / metrics 필드는 두지 않는다 (Part 3 v2 §6 원칙).
      preset 점수 기능 API 노출은 #66로 분리 (분석엔진 #12 Phase 2 의존).
    """

    def to_internal_value(self, data: Any) -> CommentaryInputE3:
        if not isinstance(data, dict):
            raise serializers.ValidationError(
                {"detail": "Request body must be a JSON object."}
            )
        try:
            return CommentaryInputE3(**data)
        except PydanticValidationError as exc:
            raise serializers.ValidationError(_pydantic_errors_to_dict(exc))

    def to_representation(self, instance: CommentaryInputE3) -> dict:
        return instance.model_dump(mode="json")


class E3ResponseSerializer(serializers.Serializer):
    """E3 coach 응답 어댑터 (E2 패턴 복제).

    `run_e3_coach()` 반환 dict 형식:
        {"output": E3Output.model_dump() dict, "llm_metadata": {...}}
    응답 스키마 계약: `output`은 반드시 E3Output 형식 — contract test 회귀 보호.
    """

    def to_representation(self, instance: dict) -> dict:
        if not isinstance(instance, dict) or "output" not in instance:
            raise serializers.ValidationError(
                "run_e3_coach 응답에 'output' 키가 없습니다 (계약 위반)."
            )
        try:
            validated = E3Output(**instance["output"])
        except PydanticValidationError as exc:
            raise serializers.ValidationError(
                {"output_schema_drift": _pydantic_errors_to_dict(exc)}
            )

        result = {
            "output": validated.model_dump(mode="json"),
            "llm_metadata": instance.get("llm_metadata", {}),
        }
        for opt_key in ("gate_tier", "preset_id", "scores"):
            if opt_key in instance:
                result[opt_key] = instance[opt_key]
        return result


def _pydantic_errors_to_dict(exc: PydanticValidationError) -> dict:
    """Pydantic ValidationError → DRF 형식 dict.

    각 에러를 `{loc.join('.'): msg}` 형태로 평탄화.
    여러 에러를 그대로 보존해 클라이언트가 모든 필드 오류를 한 번에 받도록.
    """
    out: dict[str, list[str]] = {}
    for err in exc.errors():
        loc = ".".join(str(x) for x in err.get("loc", ()))
        key = loc or "__root__"
        out.setdefault(key, []).append(err.get("msg", "invalid"))
    return out

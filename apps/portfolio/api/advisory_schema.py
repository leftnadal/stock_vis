"""Slice 20a — advisory serializer ↔ Pydantic 계약 spectacular 브릿지.

advisory.py의 앵커 serializer(빈 필드)는 spectacular 기본 추론으로 텅 빈다.
실 스키마는 Pydantic 계약(advisory_contract). coach와 동일 원리이나 LLM 봉투는 없다
(봉투 없이 Pydantic 모델을 그대로 매핑 — `_pydantic_to_openapi` 재사용).

import만으로 확장 4개가 자동 등록된다 (apps.py ready()에서 import).
"""

from __future__ import annotations

from typing import Any

from drf_spectacular.extensions import OpenApiSerializerExtension

from apps.portfolio.api.openapi_extensions import _pydantic_to_openapi
from apps.portfolio.schemas.advisory_contract import (
    AssetSummaryContract,
    KnobsReadContract,
    LatestAdvisoryContract,
)


def _make_plain_extension(serializer_path: str, model: type, name: str) -> type:
    """봉투 없이 Pydantic 모델을 그대로 OpenAPI 스키마로 매핑."""

    class _Ext(OpenApiSerializerExtension):
        target_class = serializer_path

        def get_name(self) -> str:  # type: ignore[override]
            return name

        def map_serializer(self, auto_schema, direction) -> dict[str, Any]:  # type: ignore[override]
            return _pydantic_to_openapi(model)

    _Ext.__name__ = f"_{name}Extension"
    _Ext.__qualname__ = _Ext.__name__
    return _Ext


# ★ target_class는 serializer의 실제 __module__ 경로 = `apps.portfolio...`(apps. 접두 필수).
# apps/ 디렉터리 구조에서 `portfolio...`로 쓰면 import_string 실패 → 확장 no-op(빈 스키마).
# (coach openapi_extensions.py는 apps. 누락된 선존 버그 — 20a 범위 밖, TASKQUEUE 플래그.)
_MAPPINGS: list[tuple[str, type, str]] = [
    ("apps.portfolio.api.advisory.LatestAdvisorySerializer", LatestAdvisoryContract, "LatestAdvisory"),
    ("apps.portfolio.api.advisory.AssetSummarySerializer", AssetSummaryContract, "AssetSummary"),
    ("apps.portfolio.api.advisory.KnobsReadSerializer", KnobsReadContract, "KnobsRead"),
]

_EXTENSIONS = [_make_plain_extension(p, m, n) for p, m, n in _MAPPINGS]

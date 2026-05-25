"""drf-spectacular 확장 — coach serializer ↔ Pydantic 스키마 브릿지.

배경:
- `portfolio/api/serializers.py`의 coach serializer 12개(E1~E6 req/res)는 검증/직렬화 위임 어댑터.
  DRF `fields`가 비어있어 spectacular의 기본 추론으로는 OpenAPI 스키마가 텅 빈다.
- 실제 스키마는 Pydantic 모델 (`portfolio/schemas/commentary_input.py`, `commentary_output.py`)에 있음.

해결:
- 각 serializer에 1:1 OpenApiSerializerExtension을 붙여 `map_serializer`가 Pydantic
  `model_json_schema()` 결과를 반환하도록 한다.
- Pydantic 스키마는 `$defs` 키로 nested 모델을 분리·참조하는데, 이를 그대로 두면
  spectacular의 component registry에 등록되지 않아 `$ref`가 깨진다. 따라서
  `_inline_pydantic_refs()`로 `$defs`를 본 스키마에 inline 한다 (audit: 코치 모델
  12개에 self-reference 없음 — 무한 재귀 위험 0).

이 모듈을 import하면 12개 확장이 자동 등록된다 (`apps.py` ready()에서 import).
"""

from __future__ import annotations

import copy
from typing import Any

from drf_spectacular.extensions import OpenApiSerializerExtension

from portfolio.schemas.commentary_input import (
    CommentaryInputE1,
    CommentaryInputE2,
    CommentaryInputE3,
    CommentaryInputE4,
    CommentaryInputE5,
    CommentaryInputE6,
)
from portfolio.schemas.commentary_output import (
    E1Output,
    E2Output,
    E3Output,
    E4Output,
    E5Output,
    E6Output,
)

_MAX_DEPTH = 20


def _inline_pydantic_refs(schema: dict[str, Any]) -> dict[str, Any]:
    """Pydantic `$defs` 참조를 재귀적으로 inline 한다.

    Pydantic이 생성한 JSON schema에는 `#/$defs/<Name>` 형태의 ref가 들어있다.
    이를 그대로 OpenAPI 컴포넌트로 매핑하지 않고, ref 자리에 정의 자체를 inline
    하여 자기충족적 단일 스키마로 만든다. coach 모델은 self-ref가 없어 안전.
    """

    defs = schema.pop("$defs", {})
    if not defs:
        return schema

    def resolve(node: Any, depth: int = 0) -> Any:
        if depth > _MAX_DEPTH:
            return {}
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/$defs/"):
                name = ref.split("/")[-1]
                if name in defs:
                    return resolve(copy.deepcopy(defs[name]), depth + 1)
            return {k: resolve(v, depth) for k, v in node.items()}
        if isinstance(node, list):
            return [resolve(item, depth) for item in node]
        return node

    return resolve(schema)


def _pydantic_to_openapi(model: type) -> dict[str, Any]:
    """Pydantic 모델 → inline-resolved OpenAPI-호환 schema dict."""
    raw = model.model_json_schema()
    return _inline_pydantic_refs(raw)


def _make_extension(serializer_path: str, pydantic_model: type, name: str) -> type:
    """OpenApiSerializerExtension subclass를 동적 생성.

    target_class는 import 경로 문자열이라 lazy resolution이 가능하다.
    """

    class _Ext(OpenApiSerializerExtension):
        target_class = serializer_path

        def get_name(self) -> str:  # type: ignore[override]
            return name

        def map_serializer(self, auto_schema, direction) -> dict[str, Any]:  # type: ignore[override]
            return _pydantic_to_openapi(pydantic_model)

    _Ext.__name__ = f"_{name}Extension"
    _Ext.__qualname__ = _Ext.__name__
    return _Ext


# ── 12 coach serializer × Pydantic 모델 매핑 ──
_MAPPINGS: list[tuple[str, type, str]] = [
    ("portfolio.api.serializers.E1RequestSerializer", CommentaryInputE1, "CoachE1Request"),
    ("portfolio.api.serializers.E1ResponseSerializer", E1Output, "CoachE1Response"),
    ("portfolio.api.serializers.E2RequestSerializer", CommentaryInputE2, "CoachE2Request"),
    ("portfolio.api.serializers.E2ResponseSerializer", E2Output, "CoachE2Response"),
    ("portfolio.api.serializers.E3RequestSerializer", CommentaryInputE3, "CoachE3Request"),
    ("portfolio.api.serializers.E3ResponseSerializer", E3Output, "CoachE3Response"),
    ("portfolio.api.serializers.E4RequestSerializer", CommentaryInputE4, "CoachE4Request"),
    ("portfolio.api.serializers.E4ResponseSerializer", E4Output, "CoachE4Response"),
    ("portfolio.api.serializers.E5RequestSerializer", CommentaryInputE5, "CoachE5Request"),
    ("portfolio.api.serializers.E5ResponseSerializer", E5Output, "CoachE5Response"),
    ("portfolio.api.serializers.E6RequestSerializer", CommentaryInputE6, "CoachE6Request"),
    ("portfolio.api.serializers.E6ResponseSerializer", E6Output, "CoachE6Response"),
]

# 12 확장 클래스를 모듈 레벨에 노출 (자동 등록 트리거).
_EXTENSIONS = [_make_extension(*m) for m in _MAPPINGS]
for _ext_cls in _EXTENSIONS:
    globals()[_ext_cls.__name__] = _ext_cls

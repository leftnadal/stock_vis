# api_request/providers/fmp/symbol_convert.py
"""
FMP 심볼 표기 변환 (경계 격리) — DOTSYM 옵션 1.

원칙 (DECISIONS DOTSYM Q1~Q4, 2026-08-01):
- DB·전 내부 계층의 정본 = dot 원형 (BRK.B, BF.B).
- 하이픈 변환(BRK-B)은 **FMP API 호출 직전 경계에서만** 발생 — 앱 계층은 이 변환의
  존재를 모른다 (의존 방향: 외부 API 표기법은 외부 접점에 봉인).
- 삽입 지점 = FMPClient._make_request (요청 조립 단일 경로, params["symbol"/"symbols"]).

class-share 표기 규약:
- 내부 정본:  ROOT.CLASS  (예 BRK.B, BF.B)  ← dot
- FMP API:    ROOT-CLASS  (예 BRK-B, BF-B)  ← hyphen
"""

from typing import Optional


def to_fmp_symbol(symbol: Optional[str]) -> Optional[str]:
    """
    내부 정본(dot) → FMP API 표기(hyphen).

    dot 없는 심볼은 passthrough (행위보존 — 501 유니버스 전원 무변환).
    BRK.B → BRK-B, BF.B → BF-B, AAPL → AAPL.
    """
    if not symbol:
        return symbol
    return symbol.replace(".", "-")


def from_fmp_symbol(symbol: Optional[str]) -> Optional[str]:
    """
    FMP API 표기(hyphen) → 내부 정본(dot).

    응답에서 심볼이 하이픈으로 회신될 때 원형 복원. 하이픈 없는 심볼은 passthrough.
    BRK-B → BRK.B, BF-B → BF.B, AAPL → AAPL.
    """
    if not symbol:
        return symbol
    return symbol.replace("-", ".")


def to_fmp_symbols_param(value: Optional[str]) -> Optional[str]:
    """
    params 의 "symbol"/"symbols" 값을 변환 (콤마 구분 복수 대응).

    단일 심볼(AAPL)·콤마 구분(AAPL,BRK.B) 모두 처리. 각 성분에 to_fmp_symbol 적용.
    빈 값/None passthrough.
    """
    if not value:
        return value
    return ",".join(to_fmp_symbol(s) for s in str(value).split(","))


def restore_symbols_in_response(data):
    """
    FMP 응답의 최상위 "symbol" 필드를 내부 정본(dot)으로 역변환 (응답 경계 단일 지점).

    Slice 1.5 프로브 실측: FMP 는 class-share 를 hyphen(BRK-B) 으로 회신 →
    응답 symbol 을 신뢰-저장하는 소비처가 dot 정본을 받도록 여기서 복원.
    - list[dict] / dict 모두 처리. "symbol" 없는 응답·비-class-share 심볼은 무변경(passthrough).
    - 원본 객체를 in-place 로 갱신하고 그대로 반환(_make_request 반환 경로 단일 삽입용).
    """
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and item.get("symbol"):
                item["symbol"] = from_fmp_symbol(item["symbol"])
    elif isinstance(data, dict) and data.get("symbol"):
        data["symbol"] = from_fmp_symbol(data["symbol"])
    return data

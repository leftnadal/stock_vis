"""L2 국면 카테고리 — regime 확정치 → 유사 국면 카드 태그 (Slice C-core).

소속: apps/market_pulse/regime (Phase2 촉발 표면, analog 카드 소비).
역할: 각 이웃일(및 오늘)의 regime 확정치를 "그날의 국면 유형" 태그로 결정론 파생.
  판단 로직 단일 출처 = 이 순수 함수(payload builder 경유). FE는 태그를 소비만 하고
  분류를 재구현하지 않는다.

규약(§Slice C-core):
  - **결정론·저장 0·뉴스 0·LLM 0**: 입력 = 확정 regime 값(이미 DB 박제), 부작용 없음.
  - **어휘 단일 출처 = RegimeSnapshot.Regime enum**(모델 공식 표시명 재사용 → 드리프트 0).
    태그 label = enum 한국어 표시명 그대로("그날의 사실 분류 표기"). key = enum 값(FE RegimeId).
  - **미지 값 = 명시적 에러**(조용한 null 금지 — 미래 regime 값 추가 시 폭발적으로 드러나게).
  - **CRISIS 카피 게이트**: 태그는 사실 분류(그날이 '위기' 국면이었음)까지만. "오늘이 위기와
    유사" 류 유사성 주장 카피는 이 함수·소비처 어디에도 넣지 않는다(카드 카피 책임 분리).
  - **톤(색)은 FE 소관**: key(RegimeId) 기반 `regimeTone()`(기존 REGIME_TONE 재사용). 여기선
    데이터(key·label)만 반환 — 프레젠테이션 토큰 미포함(데이터/표현 분리).
"""
from __future__ import annotations

from apps.market_pulse.models.regime import RegimeSnapshot


def categorize_regime(regime_value: str) -> dict:
    """regime 확정치 → {key, label}. 미지 값이면 ValueError(조용한 null 금지)."""
    regime_enum = RegimeSnapshot.Regime
    if regime_value not in regime_enum.values:
        raise ValueError(
            f"미지 regime 값 '{regime_value}' — 카테고리 매핑 누락. "
            f"RegimeSnapshot.Regime enum에 값 추가 시 어휘 확정 필요(디렉터). 유효값: {list(regime_enum.values)}"
        )
    return {"key": regime_value, "label": regime_enum(regime_value).label}


def categorize_or_none(regime_value: str | None) -> dict | None:
    """확정치 없음(None/빈값)은 태그 없음(null). 값이 있으면 categorize_regime(미지값은 에러 전파)."""
    if not regime_value:
        return None
    return categorize_regime(regime_value)

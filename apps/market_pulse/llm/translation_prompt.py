"""
Translation Prompt Template (Phase 1.5 S3) — 카드별 감각 유추 프롬프트 빌더.

소속: apps/market_pulse/llm (app 레이어 LLM 프롬프트 빌더, Brief 패턴 미러).
역할: 4 정량 카드(regime/breadth/sector/concentration)의 백엔드 raw(+regime enum 라벨)를
  Gemini 입력으로 직렬화 → 1회 호출로 카드별 "감각 유추" 1~2문장을 JSON으로 받는다.
주요 심볼: SENSE_KEYS, SYSTEM_PROMPT, build_translation_context, render_user_prompt,
  few_shot_messages.
소비처: tasks/translation.py(mp_generate_translation_daily).

설계 메모(옵션 a — STEP 0 결정):
  - regime은 백엔드 enum 라벨(5단계)을 그대로 주고, breadth/sector/concentration은 raw 값 +
    **정성 해석 지침**을 SYSTEM_PROMPT에 둔다. meaning.ts의 수치 임계는 Python에 복제하지
    않는다(§10 단일출처 — FE 밴드 임계가 진실의 소스, 여기선 방향 해석만 LLM에 위임).
  - 스냅샷 로딩은 Brief의 build_context_from_snapshots를 재사용(중복 쿼리 0).
"""

from __future__ import annotations

import json
from datetime import date as date_cls

# senses 키 = overview serializer 카드 키와 정합(regime/breadth/sector/concentration).
SENSE_KEYS = ("regime", "breadth", "sector", "concentration")


SYSTEM_PROMPT = """당신은 시장 카드 데이터를 일반 투자자가 체감할 수 있는 한 문장으로 풀어주는 해설자입니다.

규칙:
1. 4개 카드 각각에 대해 **한국어 1~2문장(카드당 약 40~90자)**의 '감각 유추'를 작성하세요.
   숫자 나열이 아니라, 그 숫자가 주는 시장 분위기를 풀어줍니다.
2. **방향 일관**: 신호가 위험회피/약세면 방어적 톤, 강세/광범위 참여면 강세 톤으로.
   같은 카드 안에서 모순된 방향을 섞지 마세요.
3. **예측·투자권유·과장 금지**: "오를 것", "하락할 것", "매수/매도 추천", "목표가", "확실" 등 금지.
   사실(주어진 raw·단계)에 근거한 현재 상태 묘사만 하세요.
4. 카드별 해석 지침:
   - regime(시장 국면): 5단계 톤 — BULL_EXPANSION(차분한 긍정), LATE_BULL(후반부 경계),
     TRANSITION(중립·분기), BEAR_CONTRACTION(신중·방어), CRISIS(긴장·안정 우선).
   - breadth(시장 폭): 상승 종목이 하락 종목보다 많으면 광범위한 참여(긍정),
     하락이 우위면 약세 폭. 엇비슷하면 팽팽한 균형.
   - sector(섹터 흐름): 앞선(leader) 섹터로 자금이 쏠리고 뒤처진(laggard) 섹터는 소외됨을 묘사.
   - concentration(쏠림): top10 비중·HHI가 높을수록 소수 대형주에 쏠려 시장 폭이 좁음,
     낮을수록 분산.
5. 응답은 다음 JSON 형식만 반환:
   {"regime": "<문장>", "breadth": "<문장>", "sector": "<문장>", "concentration": "<문장>"}

추가 텍스트, 설명, 마크다운 코드블록, ```json ``` 표기 금지. JSON 객체 하나만 출력하세요.
"""


FEW_SHOTS = [
    {
        "context": {
            "date": "2026-04-27",
            "regime": {"stage": "BULL_EXPANSION", "status": "confirmed"},
            "breadth": {"advance": 340, "decline": 150, "unchanged": 10},
            "sector": {"leader": "XLK", "laggard": "XLU"},
            "concentration": {"top10_weight": 0.31, "hhi": 0.018},
        },
        "response": {
            "regime": "강세 확장 국면이 이어지며 시장 전반에 차분한 긍정이 감돕니다.",
            "breadth": "오르는 종목이 내리는 종목을 크게 앞서 참여가 폭넓습니다.",
            "sector": "기술 섹터로 자금이 쏠리고 유틸리티는 상대적으로 소외돼 있어요.",
            "concentration": "top10 비중 31%로 쏠림은 평균 수준, 시장 폭이 비교적 고릅니다.",
        },
    },
    {
        "context": {
            "date": "2026-04-27",
            "regime": {"stage": "BEAR_CONTRACTION", "status": "confirmed"},
            "breadth": {"advance": 120, "decline": 370, "unchanged": 10},
            "sector": {"leader": "XLP", "laggard": "XLY"},
            "concentration": {"top10_weight": 0.42, "hhi": 0.031},
        },
        "response": {
            "regime": "수축 국면으로 접어들며 방어적으로 살펴야 할 시점입니다.",
            "breadth": "내리는 종목이 크게 우위라 약세가 광범위합니다.",
            "sector": "필수소비재로 방어 수요가 몰리고 경기소비재는 뒤처져 있어요.",
            "concentration": "top10 비중 42%로 소수 대형주 쏠림이 커져 시장 폭이 좁습니다.",
        },
    },
]


def build_translation_context(today: date_cls) -> dict:
    """Brief의 스냅샷 로더를 재사용해 4 카드 raw를 per-card dict로 재구성(중복 쿼리 0)."""
    from apps.market_pulse.briefing.prompt import build_context_from_snapshots

    ctx = build_context_from_snapshots(today)
    return {
        "date": ctx.date,
        "regime": {"stage": ctx.regime, "status": ctx.regime_status},
        "breadth": {
            "advance": ctx.breadth_advance,
            "decline": ctx.breadth_decline,
            "unchanged": ctx.breadth_unchanged,
        },
        "sector": {"leader": ctx.sector_leader, "laggard": ctx.sector_laggard},
        "concentration": {"top10_weight": ctx.top10_weight, "hhi": ctx.hhi},
    }


def is_sufficient(context: dict) -> bool:
    """regime 단계·breadth 상승수가 있어야 방향-일관 해석 가능(Brief 충분성 기준 미러)."""
    return (
        context.get("regime", {}).get("stage") is not None
        and context.get("breadth", {}).get("advance") is not None
    )


def render_user_prompt(context: dict) -> str:
    payload = {"today": context.get("date"), "cards": {
        k: context.get(k) for k in SENSE_KEYS
    }}
    return (
        "오늘의 카드 데이터입니다. 각 카드의 감각 유추를 JSON 한 객체로 작성하세요.\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )


def few_shot_messages() -> list[dict]:
    out: list[dict] = []
    for ex in FEW_SHOTS:
        out.append(
            {"role": "user", "parts": [{"text": json.dumps(ex["context"], ensure_ascii=False)}]}
        )
        out.append(
            {"role": "model", "parts": [{"text": json.dumps(ex["response"], ensure_ascii=False)}]}
        )
    return out

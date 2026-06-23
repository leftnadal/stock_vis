"""
Phase 1.5 S5 — 실 Gemini 응답 스냅샷 recorder (vcr 대체, 사용자 결정).

vcrpy/카세트 인프라 부재(STEP 0) → 실 LLM을 1회 호출해 raw 응답을 JSON 스냅샷으로
저장하고, golden 테스트는 그 스냅샷을 **재생만**(무비용·결정론·CI 무네트워크).
HTTP 카세트가 아니라 "응답 레벨 스냅샷"이지만 golden의 목적(실 모델 출력에 계약을 거는 것)을
동일하게 충족한다.

재녹화(프롬프트 변경 시):
    set -a; source .env; set +a
    python manage.py shell -c "from tests.marketpulse.golden.record_snapshots import record_all; record_all()"
  → snapshots/*.json 갱신 후 golden 테스트 재실행으로 계약 재확인.

⚠ 이 파일은 test_ 접두어가 아니라 pytest가 수집하지 않음(수동 recorder). API 키 필요.
"""
from __future__ import annotations

import json
from pathlib import Path

SNAP_DIR = Path(__file__).parent / "snapshots"

# Translation 시나리오 — build_translation_context() 출력 형태(카드별 raw).
TRANSLATION_SCENARIOS = {
    "bullish": {
        "date": "2026-06-19",
        "regime": {"stage": "BULL_EXPANSION", "status": "confirmed"},
        "breadth": {"advance": 360, "decline": 130, "unchanged": 10},
        "sector": {"leader": "XLK", "laggard": "XLU"},
        "concentration": {"top10_weight": 0.30, "hhi": 0.017},
    },
    "risk_off": {
        "date": "2026-06-19",
        "regime": {"stage": "CRISIS", "status": "confirmed"},
        "breadth": {"advance": 70, "decline": 420, "unchanged": 10},
        "sector": {"leader": "XLP", "laggard": "XLY"},
        "concentration": {"top10_weight": 0.45, "hhi": 0.034},
    },
    "neutral": {
        "date": "2026-06-19",
        "regime": {"stage": "TRANSITION", "status": "confirmed"},
        "breadth": {"advance": 250, "decline": 245, "unchanged": 15},
        "sector": {"leader": "XLV", "laggard": "XLB"},
        "concentration": {"top10_weight": 0.37, "hhi": 0.022},
    },
    "late_bull": {
        "date": "2026-06-19",
        "regime": {"stage": "LATE_BULL", "status": "confirmed"},
        "breadth": {"advance": 300, "decline": 190, "unchanged": 10},
        "sector": {"leader": "XLE", "laggard": "XLRE"},
        "concentration": {"top10_weight": 0.40, "hhi": 0.026},
    },
}


def _record_translation(name: str, context: dict) -> dict:
    from apps.market_pulse.llm import translation_prompt as tp
    from apps.market_pulse.llm.client import DEFAULT_MODEL, generate_with_circuit

    contents = tp.few_shot_messages()
    contents.append({"role": "user", "parts": [{"text": tp.render_user_prompt(context)}]})
    raw = generate_with_circuit(system_instruction=tp.SYSTEM_PROMPT, contents=contents)
    return {
        "scenario": name,
        "kind": "translation",
        "model": DEFAULT_MODEL,
        "context": context,
        "raw_text": raw.text,
    }


def _record_brief() -> dict:
    from apps.market_pulse.briefing import client as bc
    from apps.market_pulse.briefing.prompt import BriefingContext
    from apps.market_pulse.llm.client import DEFAULT_MODEL

    ctx = BriefingContext(
        date="2026-06-19",
        regime="LATE_BULL",
        regime_status="confirmed",
        breadth_advance=300,
        breadth_decline=190,
        breadth_unchanged=10,
        sector_leader="XLE",
        sector_laggard="XLRE",
        top10_weight=0.40,
        hhi=0.026,
        anomaly_mode="CALM",
        fired_rules=[],
    )
    raw = bc.generate(ctx)
    return {
        "scenario": "late_bull",
        "kind": "brief",
        "model": DEFAULT_MODEL,
        "context": ctx.as_dict(),
        "raw_text": raw.text,
    }


def record_all() -> None:
    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    for name, ctx in TRANSLATION_SCENARIOS.items():
        snap = _record_translation(name, ctx)
        path = SNAP_DIR / f"translation_{name}.json"
        path.write_text(json.dumps(snap, ensure_ascii=False, indent=2) + "\n")
        print(f"[recorded] {path.name} (len={len(snap['raw_text'])})")
    brief = _record_brief()
    bpath = SNAP_DIR / "brief_late_bull.json"
    bpath.write_text(json.dumps(brief, ensure_ascii=False, indent=2) + "\n")
    print(f"[recorded] {bpath.name} (len={len(brief['raw_text'])})")

"""LLMFILL — 캐러셀 추천 3키 LLM 채움 테스트. [D-LLMFILL]

실호출 금지(mock only — 실검증은 LLMFILL-OBSERVE 실 bake). 검증 축:
  - item 가드: 7 core 키 이름·순서 불변 + 3 fill 키 타입 계약(⑹).
  - 채움 mock ⒜ 전건 성공 ⒝ 부분 실패 ⒞ 전체 예외 ⒟ 파싱/타입 불량.
"""

import json

import pytest

from packages.shared.llm.types import LLMResponse
from packages.shared.stocks.llm import fill_service

CORE_KEYS = [
    "rank",
    "ticker",
    "company_name",
    "signal_tag",
    "confidence",
    "conf_ver",
    "composite_score",
]
FILL_KEYS = ["thesis", "perspectives", "risk"]


def _rec(rank: int, ticker: str = "AAA") -> dict:
    """추천 항목(7 core + 3 placeholder), _build_recommendations 산출 형태."""
    return {
        "rank": rank,
        "ticker": ticker,
        "company_name": f"{ticker} Inc",
        "signal_tag": "V1",
        "confidence": "high",
        "conf_ver": 1,
        "composite_score": 0.5,
        "thesis": None,
        "perspectives": {"technical": None, "fundamental": None, "news_context": None},
        "risk": None,
    }


def _material(ticker: str = "AAA") -> dict:
    return {
        "stock_id": ticker,
        "sector": "Tech",
        "close": 100.0,
        "change_pct": 1.2,
        "composite_score": 0.5,
        "tag_details": {"primary": "V1"},
        "signals": [{"id": "V1", "label": "Vol Spike", "direction": "up", "value": 2.0}],
        "news_context": {"headline": "X 신제품", "match_type": "direct", "age_days": 1},
    }


def _resp(text: str, cost: float = 0.001, itok: int = 100, otok: int = 50) -> LLMResponse:
    return LLMResponse(
        text=text,
        provider="gemini",
        model="m",
        latency_ms=10,
        input_tokens=itok,
        output_tokens=otok,
        cost_usd=cost,
    )


_GOOD = json.dumps(
    {
        "thesis": "좋은 신호다.",
        "perspectives": {"technical": "t", "fundamental": "f", "news_context": "n"},
        "risk": "거래량이 하루 만에 꺾이면 무효.",
    },
    ensure_ascii=False,
)


# ── item 가드 (D-LLMFILL ⑹) ────────────────────────────────────────────


def test_build_recommendations_item_contract():
    """실제 _build_recommendations 산출 = 7 core 순서 + 3 fill 키·기본 null."""
    from packages.shared.stocks.services.eod_json_baker import EODJSONBaker

    baker = EODJSONBaker()
    baker._company_name_cache = {"AAA": "AAA Inc"}
    signals = [
        {
            "stock_id": "AAA",
            "composite_score": 0.7,
            "tag_details": {"primary": "V1"},
            "signals": [{"id": "V1"}],
            "news_context": {},
        }
    ]
    recs = baker._build_recommendations(signals)
    assert len(recs) == 1
    rec = recs[0]
    # 7 core 키 이름·순서 + 3 fill 키 (순서 불변)
    assert list(rec.keys()) == CORE_KEYS + FILL_KEYS
    # 3 fill 키 타입 계약(기본값)
    assert rec["thesis"] is None
    assert rec["perspectives"] == {
        "technical": None,
        "fundamental": None,
        "news_context": None,
    }
    assert rec["risk"] is None


# ── ⒜ 전건 성공 → 3키 채움 · 7키 IDENTICAL ──────────────────────────────


def test_all_success_fills_and_core_identical(monkeypatch):
    monkeypatch.setattr(fill_service, "complete", lambda *a, **k: _resp(_GOOD))
    items = [_rec(i) for i in range(1, 11)]
    core_before = [{k: it[k] for k in CORE_KEYS} for it in items]

    out, meta = fill_service.fill_recommendations(items, [_material()])

    assert meta["attempted"] == 10
    assert meta["filled"] == 10
    assert meta["failed"] == []
    assert meta["cost_usd"] > 0
    assert meta["tokens"] == 10 * 150
    for it, core in zip(out, core_before):
        assert {k: it[k] for k in CORE_KEYS} == core  # 7키 IDENTICAL
        assert it["thesis"] == "좋은 신호다."
        assert it["perspectives"]["news_context"] == "n"
        assert it["risk"].startswith("거래량")


def test_complete_called_with_policy(monkeypatch):
    """gemini→anthropic fallback·retries=1·cost_track=True 정책 전달. [D-LLMFILL ⑷⑸]"""
    captured = {}

    def fake(prompt, **kwargs):
        captured.update(kwargs)
        return _resp(_GOOD)

    monkeypatch.setattr(fill_service, "complete", fake)
    fill_service.fill_recommendations([_rec(1)], [_material()])

    assert captured["provider"] == "gemini"
    assert captured["fallback"] == "anthropic"
    assert captured["retries"] == 1
    assert captured["cost_track"] is True


def test_code_fence_stripped(monkeypatch):
    fenced = "```json\n" + _GOOD + "\n```"
    monkeypatch.setattr(fill_service, "complete", lambda *a, **k: _resp(fenced))
    out, meta = fill_service.fill_recommendations([_rec(1)], [_material()])
    assert meta["filled"] == 1
    assert out[0]["thesis"] == "좋은 신호다."


# ── ⒝ 부분 실패(3/10) → 실패 카드만 null · filled=7 ─────────────────────


def test_partial_failure_isolates_cards(monkeypatch):
    calls = {"n": 0}

    def fake(*a, **k):
        calls["n"] += 1
        if calls["n"] in (2, 5, 8):
            raise fill_service.LLMError("boom")
        return _resp(_GOOD)

    monkeypatch.setattr(fill_service, "complete", fake)
    items = [_rec(i) for i in range(1, 11)]

    out, meta = fill_service.fill_recommendations(items, [_material()])

    assert meta["attempted"] == 10
    assert meta["filled"] == 7
    assert {f["rank"] for f in meta["failed"]} == {2, 5, 8}
    for it in out:
        if it["rank"] in {2, 5, 8}:
            assert it["thesis"] is None
            assert it["risk"] is None
            assert it["perspectives"] == {
                "technical": None,
                "fundamental": None,
                "news_context": None,
            }
        else:
            assert it["thesis"] == "좋은 신호다."


# ── ⒞ 전체 예외 → 전 카드 null · bake 산출물 정상 · llm_fill.ok=False ────


def test_baker_outer_defense_ok_false(monkeypatch):
    """fill_recommendations 자체가 터져도 placeholder null 유지 + ok=False, bake 진행."""
    import packages.shared.stocks.llm.fill_service as fs
    from packages.shared.stocks.services.eod_json_baker import EODJSONBaker

    def boom(*a, **k):
        raise RuntimeError("total failure")

    monkeypatch.setattr(fs, "fill_recommendations", boom)

    baker = EODJSONBaker()
    dashboard_json = {
        "recommendations": [_rec(1), _rec(2)],
        "pipeline_meta": {"run_id": "r"},
    }
    baker._fill_recommendations_llm(dashboard_json, [_material()])

    assert dashboard_json["pipeline_meta"]["llm_fill"] == {"ok": False}
    # bake 산출물(기존 pipeline_meta·recommendations 골격) 정상
    assert dashboard_json["pipeline_meta"]["run_id"] == "r"
    for it in dashboard_json["recommendations"]:
        assert it["thesis"] is None
        assert it["risk"] is None


def test_baker_success_writes_meta(monkeypatch):
    """정상 경로: pipeline_meta.llm_fill additive 기입(ok=True + 집계)."""
    import packages.shared.stocks.llm.fill_service as fs
    from packages.shared.stocks.services.eod_json_baker import EODJSONBaker

    monkeypatch.setattr(fs, "complete", lambda *a, **k: _resp(_GOOD))

    baker = EODJSONBaker()
    dashboard_json = {
        "recommendations": [_rec(1)],
        "pipeline_meta": {"run_id": "r"},
    }
    baker._fill_recommendations_llm(dashboard_json, [_material()])

    fill_meta = dashboard_json["pipeline_meta"]["llm_fill"]
    assert fill_meta["ok"] is True
    assert fill_meta["filled"] == 1
    assert dashboard_json["recommendations"][0]["thesis"] == "좋은 신호다."


# ── ⒟ 파싱 불량 / 타입 불일치 → 해당 카드 null ─────────────────────────


def test_bad_json_keeps_null(monkeypatch):
    monkeypatch.setattr(fill_service, "complete", lambda *a, **k: _resp("not json {"))
    out, meta = fill_service.fill_recommendations([_rec(1)], [_material()])
    assert meta["filled"] == 0
    assert len(meta["failed"]) == 1
    assert out[0]["thesis"] is None


def test_type_violation_keeps_null(monkeypatch):
    bad = json.dumps({"thesis": 123, "perspectives": {}, "risk": None})
    monkeypatch.setattr(fill_service, "complete", lambda *a, **k: _resp(bad))
    out, meta = fill_service.fill_recommendations([_rec(1)], [_material()])
    assert meta["filled"] == 0
    assert meta["failed"][0]["reason"] == "type_contract_violation"
    assert out[0]["thesis"] is None


def test_perspectives_non_dict_violation(monkeypatch):
    bad = json.dumps({"thesis": "t", "perspectives": "nope", "risk": "r"})
    monkeypatch.setattr(fill_service, "complete", lambda *a, **k: _resp(bad))
    out, meta = fill_service.fill_recommendations([_rec(1)], [_material()])
    assert meta["filled"] == 0
    assert out[0]["perspectives"] == {
        "technical": None,
        "fundamental": None,
        "news_context": None,
    }


def test_empty_items_returns_zero_meta():
    out, meta = fill_service.fill_recommendations([], [_material()])
    assert out == []
    assert meta == {
        "attempted": 0,
        "filled": 0,
        "failed": [],
        "cost_usd": 0.0,
        "tokens": 0,
    }

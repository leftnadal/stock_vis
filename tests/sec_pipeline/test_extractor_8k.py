"""CS-P2-8K: 8-K 추출기 순수 로직 단위 테스트 (DB·LLM 무의존)."""

from services.sec_pipeline import extractor_8k as e8


# ─────────────── extract_item_bodies (순수 파싱) ───────────────

def test_extract_item_bodies_basic():
    text = (
        "FORM 8-K header boilerplate. "
        "Item 1.01 Entry into a Material Definitive Agreement. "
        "The Company entered into an agreement with Acme Corp. "
        "Item 9.01 Financial Statements and Exhibits. Exhibit 10.1."
    )
    bodies = e8.extract_item_bodies(text, {"1.01", "2.01"})
    assert "1.01" in bodies
    assert "Acme Corp" in bodies["1.01"]
    # 9.01은 대상 아님 → 1.01 본문은 9.01 직전에서 끊김
    assert "Exhibit 10.1" not in bodies["1.01"]
    assert "2.01" not in bodies


def test_extract_item_bodies_two_items():
    text = (
        "Item 1.01 Material agreement with Partner Inc. "
        "Item 2.01 Completion of Acquisition. Acquired Target LLC. "
        "Item 5.02 Officers."
    )
    bodies = e8.extract_item_bodies(text, {"1.01", "2.01"})
    assert "Partner Inc" in bodies["1.01"]
    assert "Target LLC" in bodies["2.01"]
    assert "Officers" not in bodies["2.01"]


def test_extract_item_bodies_none_when_no_target():
    text = "Item 5.02 Departure of Directors. Item 9.01 Exhibits."
    assert e8.extract_item_bodies(text, {"1.01", "2.01"}) == {}


# ─────────────── extract_counterparties (분류 정규화, mock LLM) ───────────────

class _Resp:
    def __init__(self, text):
        self.text = text


def _mock(text):
    def fn(prompt):
        return _Resp(text)
    return fn


def test_extract_counterparties_classifies_and_maps():
    payload = (
        '{"counterparties":['
        '{"name":"Acme Corp","category":"commercial","confidence":0.9,"item":"1.01","evidence":"agreement with Acme"},'
        '{"name":"JPMorgan","category":"financing","confidence":1.0,"item":"1.01","evidence":"credit agreement"},'
        '{"name":"Target LLC","category":"acquisition","confidence":0.8,"item":"2.01","evidence":"acquired Target"}'
        ']}'
    )
    r = e8.extract_counterparties("AAA", "Alpha Inc", {"1.01": "x"}, complete_fn=_mock(payload))
    cps = r["counterparties"]
    assert len(cps) == 3
    cats = {c["name"]: c["category"] for c in cps}
    assert cats["JPMorgan"] == "financing"
    assert e8.CATEGORY_TO_RELATION["commercial"] == "PARTNER_WITH"
    assert e8.CATEGORY_TO_RELATION["acquisition"] == "ACQUIRED"
    assert "financing" not in e8.LAND_CATEGORIES


def test_extract_counterparties_unknown_category_becomes_unclear():
    payload = '{"counterparties":[{"name":"X Co","category":"weird","confidence":0.5}]}'
    r = e8.extract_counterparties("AAA", "Alpha", {"1.01": "x"}, complete_fn=_mock(payload))
    assert r["counterparties"][0]["category"] == "unclear"


def test_extract_counterparties_drops_nameless():
    payload = '{"counterparties":[{"name":"","category":"commercial","confidence":0.9}]}'
    r = e8.extract_counterparties("AAA", "Alpha", {"1.01": "x"}, complete_fn=_mock(payload))
    assert r["counterparties"] == []


def test_extract_counterparties_empty_bodies_no_llm_call():
    called = {"n": 0}

    def fn(prompt):
        called["n"] += 1
        return _Resp("{}")

    r = e8.extract_counterparties("AAA", "Alpha", {}, complete_fn=fn)
    assert r == {"counterparties": []}
    assert called["n"] == 0  # 본문 없으면 LLM 호출 안 함


def test_extract_counterparties_bad_json_returns_error():
    r = e8.extract_counterparties("AAA", "Alpha", {"1.01": "x"}, complete_fn=_mock("not json"))
    assert r["counterparties"] == []
    assert "error" in r

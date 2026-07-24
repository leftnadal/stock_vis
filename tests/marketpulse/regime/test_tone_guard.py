"""C-L3 톤가드 테스트 — 결정론 금지패턴 스캔(LLM 무의존)."""

from __future__ import annotations

import pytest

from apps.market_pulse.regime.tone_guard import check_tone


@pytest.mark.parametrize("text", [
    "규제 강화 우려가 부각된 국면.",
    "빅테크 실적 발표가 몰린 날.",
    "뚜렷한 시장 주제 없이 개별 종목 뉴스가 오간 날.",
    "인플레이션 지표 공개를 앞둔 관망 국면.",
])
def test_pass_valid_context(text):
    ok, reason = check_tone(text)
    assert ok, f"정상 맥락이 거부됨: {reason}"


@pytest.mark.parametrize("text,cat", [
    ("금리 인상 때문에 증시가 하락했다.", "causal"),
    ("실적 부진 탓에 약세를 보였다.", "causal"),
    ("연준 발언의 여파로 흔들렸다.", "causal"),
    ("규제 이슈로 인해 조정을 받았다.", "causal"),
    ("이 흐름이면 곧 오를 것이다.", "direction_predict"),
    ("단기적으로 하락할 전망이다.", "direction_predict"),
    ("지금은 매수 시점이다.", "advice"),
    ("비중 확대를 고려할 만하다.", "advice"),
])
def test_reject_banned(text, cat):
    ok, reason = check_tone(text)
    assert not ok
    assert reason.startswith(cat), f"기대 카테고리 {cat}, 실제 {reason}"


def test_reject_empty():
    assert check_tone("")[0] is False
    assert check_tone("   ")[0] is False


def test_reject_too_many_sentences():
    ok, reason = check_tone("첫 문장이다. 둘째 문장이다. 셋째 문장이다.")
    assert not ok
    assert reason == "too_many_sentences"


def test_allow_single_terminator():
    ok, _ = check_tone("규제 우려가 부각된 국면이었다.")
    assert ok

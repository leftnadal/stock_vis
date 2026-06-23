"""
Phase 1.5 S5 — Translation golden 계약 테스트 (실 Gemini 스냅샷 재생).

스냅샷(snapshots/translation_*.json)은 실 Gemini 1회 출력(record_snapshots.py).
여기선 **재생만** — 무비용·결정론·CI 무네트워크. 문구 일치가 아니라 **계약**을 단언:
  1. JSON 구조 — validate_senses가 OK + 기대 카드 키
  2. 길이 — 카드당 prose가 너무 짧지/길지 않음(프롬프트 "1~2문장" 가이드)
  3. 안전 — llm.safety 금지어 0 · refusal 0
  4. ★ 밴드 방향 모순 부재(약한 계약) — 입력 raw 방향과 prose 반대 어휘 공존 안 함.
     입력 raw(regime enum·advance/decline)에서만 방향을 도출 — **meaning.ts 임계 복제 0(§10)**.

재녹화: record_snapshots.py docstring 참조.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from apps.market_pulse.llm.safety import detect_refusal, scan_banned
from apps.market_pulse.llm.translation_prompt import SENSE_KEYS
from apps.market_pulse.llm.translation_safety import validate_senses

SNAP_DIR = Path(__file__).parent / "snapshots"

# 카드당 길이 계약 — 너무 짧으면(무의미) / 너무 길면(문단화) fail. 가이드 40~90자 ± 여유.
MIN_SENSE_LEN = 10
MAX_SENSE_LEN = 150

# 방향 모순 어휘(테스트-로컬, meaning.ts 무관). 입력 raw 방향과의 모순만 검사.
STRONG_BULL = ("강세", "급등", "낙관", "우호", "랠리")
STRONG_BEAR = ("급락", "폭락", "패닉", "침체", "수축", "위기", "공포", "약세")


def _load(name: str) -> dict:
    return json.loads((SNAP_DIR / name).read_text())


TRANSLATION_SNAPSHOTS = sorted(p.name for p in SNAP_DIR.glob("translation_*.json"))


def _input_direction(context: dict) -> str | None:
    """입력 raw(regime enum + advance/decline)에서만 방향 도출. meaning.ts 미참조.

    regime 단계와 breadth가 **둘 다** 같은 방향일 때만 'bull'/'bear'(강신호),
    아니면 None(중립 — 방향 모순 단언 생략).
    """
    stage = context["regime"]["stage"]
    adv = context["breadth"]["advance"]
    dec = context["breadth"]["decline"]
    bull_stage = stage in ("BULL_EXPANSION", "LATE_BULL")
    bear_stage = stage in ("CRISIS", "BEAR_CONTRACTION")
    bull_breadth = adv > dec * 1.2
    bear_breadth = dec > adv * 1.2
    if bull_stage and bull_breadth:
        return "bull"
    if bear_stage and bear_breadth:
        return "bear"
    return None


@pytest.mark.parametrize("snap_name", TRANSLATION_SNAPSHOTS)
class TestTranslationGolden:
    def test_structure_ok(self, snap_name):
        snap = _load(snap_name)
        result = validate_senses(snap["raw_text"])
        assert result.status == "OK", f"{snap_name}: {result.issues}"
        # 4 카드 키 전부 생성됐는지(스냅샷은 정상 시나리오)
        assert set(result.senses.keys()) == set(SENSE_KEYS), snap_name

    def test_length_contract(self, snap_name):
        result = validate_senses(_load(snap_name)["raw_text"])
        for key, text in result.senses.items():
            assert MIN_SENSE_LEN <= len(text) <= MAX_SENSE_LEN, (
                f"{snap_name}:{key} len={len(text)}"
            )

    def test_safety(self, snap_name):
        snap = _load(snap_name)
        for key, text in validate_senses(snap["raw_text"]).senses.items():
            assert scan_banned(text) == [], f"{snap_name}:{key} banned"
            assert detect_refusal(text) is False, f"{snap_name}:{key} refusal"

    def test_band_direction_no_contradiction(self, snap_name):
        """★ 약한 계약 — 입력 raw 방향과 prose(regime·breadth) 반대 어휘 공존 금지."""
        snap = _load(snap_name)
        direction = _input_direction(snap["context"])
        if direction is None:
            pytest.skip("중립 입력 — 방향 모순 단언 생략")
        result = validate_senses(snap["raw_text"])
        # 방향이 명확한 카드(regime·breadth)에만 적용
        checked = " ".join(
            result.senses[k] for k in ("regime", "breadth") if k in result.senses
        )
        forbidden = STRONG_BEAR if direction == "bull" else STRONG_BULL
        hits = [w for w in forbidden if w in checked]
        assert not hits, f"{snap_name}: {direction} 입력에 반대 어휘 {hits} 공존: {checked}"

    def test_deterministic_replay(self, snap_name):
        raw = _load(snap_name)["raw_text"]
        a = validate_senses(raw)
        b = validate_senses(raw)
        assert a.status == b.status and a.senses == b.senses


def test_all_scenarios_present():
    """4 시나리오 스냅샷 누락 가드(평상/위험회피/강세/전환)."""
    expected = {
        "translation_bullish.json",
        "translation_risk_off.json",
        "translation_neutral.json",
        "translation_late_bull.json",
    }
    assert expected.issubset(set(TRANSLATION_SNAPSHOTS))

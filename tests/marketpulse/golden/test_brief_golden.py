"""
Phase 1.5 S5 — Brief golden 계약 테스트 (동반 보강, 실 Gemini 스냅샷 재생).

recon 지적 "Brief golden/vcr 부재"를 종결. Brief 프로덕션 로직은 무변경(테스트만 추가 —
S1 추출이 이미 testable). briefing.safety.validate를 통과시켜 실 응답 계약을 단언:
  - JSON {headline, content} 파싱 → status OK
  - 길이 계약(content 너무 짧지/길지 않음)
  - 금지어 0 · disclaimer 정책 일관(본문 말미 포함)
  - 결정론(재생 2회 동일)
"""
from __future__ import annotations

import json
from pathlib import Path

from apps.market_pulse.briefing.prompt import DISCLAIMER
from apps.market_pulse.briefing.safety import MAX_LENGTH, MIN_LENGTH, validate
from apps.market_pulse.llm.safety import scan_banned
from apps.market_pulse.models.briefing import BriefingLog

SNAP_DIR = Path(__file__).parent / "snapshots"


def _brief():
    return json.loads((SNAP_DIR / "brief_late_bull.json").read_text())


class TestBriefGolden:
    def test_structure_and_status_ok(self):
        result = validate(_brief()["raw_text"])
        assert result.status == BriefingLog.Status.OK, result.issues
        assert result.headline
        assert result.content

    def test_length_contract(self):
        result = validate(_brief()["raw_text"])
        assert MIN_LENGTH <= len(result.content) <= MAX_LENGTH

    def test_no_banned_terms(self):
        result = validate(_brief()["raw_text"])
        assert scan_banned(result.content) == []
        assert scan_banned(result.headline) == []

    def test_disclaimer_present(self):
        """disclaimer 정책 일관 — 본문 말미에 면책 조항."""
        result = validate(_brief()["raw_text"])
        assert result.content.rstrip().endswith(DISCLAIMER)

    def test_raw_is_valid_json_envelope(self):
        payload = json.loads(_brief()["raw_text"])
        assert "headline" in payload and "content" in payload

    def test_deterministic_replay(self):
        raw = _brief()["raw_text"]
        a = validate(raw)
        b = validate(raw)
        assert a.status == b.status and a.content == b.content

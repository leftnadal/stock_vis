"""Phase 1.5 Translation Layer S3 — 생성 task + senses 파싱 결정론 검증.

LLM 호출은 mock으로 고정(실 Gemini·톤 golden·vcr는 S5). 검증 대상:
  - 정상 JSON → senses 4키 파싱·TranslationLog upsert·tokens 기록
  - upsert 멱등(같은 date,model_version 재실행 → 1행 덮어쓰기)
  - 부분 실패(키 누락·malformed·refusal·banned) → status·senses 처리
  - 데이터 부족 → LLM 미호출 + REFUSED
"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from apps.market_pulse.llm.client import DEFAULT_MODEL, LLMRawResponse
from apps.market_pulse.llm.translation_safety import validate_senses
from apps.market_pulse.models.translation import TranslationLog

PROMPT_PATH = "apps.market_pulse.llm.translation_prompt.build_translation_context"
GEN_PATH = "apps.market_pulse.tasks.translation.generate_with_circuit"

_SUFFICIENT_CTX = {
    "date": "2026-06-18",
    "regime": {"stage": "LATE_BULL", "status": "confirmed"},
    "breadth": {"advance": 300, "decline": 180, "unchanged": 20},
    "sector": {"leader": "XLK", "laggard": "XLU"},
    "concentration": {"top10_weight": 0.33, "hhi": 0.021},
}


def _raw(text: str, pt: int = 1200, ct: int = 300, lat: int = 800) -> LLMRawResponse:
    return LLMRawResponse(text=text, prompt_tokens=pt, completion_tokens=ct, latency_ms=lat)


def _full_envelope() -> str:
    return json.dumps({
        "regime": "후반부 강세가 이어지며 경계가 필요한 국면이에요.",
        "breadth": "오르는 종목이 더 많아 참여가 폭넓습니다.",
        "sector": "기술이 앞서고 유틸리티는 뒤처져 있어요.",
        "concentration": "상위 종목 쏠림이 다소 높은 편입니다.",
    }, ensure_ascii=False)


def _run():
    from apps.market_pulse.tasks.translation import mp_generate_translation_daily
    return mp_generate_translation_daily.apply(kwargs={}).get()


@pytest.mark.django_db
class TestTranslationTaskHappy:
    def test_normal_json_parses_four_senses(self):
        with patch(PROMPT_PATH, return_value=_SUFFICIENT_CTX), \
             patch(GEN_PATH, return_value=_raw(_full_envelope())):
            summary = _run()
        log = TranslationLog.objects.get()
        assert log.status == TranslationLog.Status.OK
        assert set(log.senses.keys()) == {"regime", "breadth", "sector", "concentration"}
        assert log.prompt_tokens == 1200
        assert log.completion_tokens == 300
        assert log.latency_ms == 800
        assert log.model_version == DEFAULT_MODEL
        assert summary["status"] == "OK"

    def test_upsert_idempotent_overwrite(self):
        first = json.dumps({"regime": "첫 번째 해석.", "breadth": "폭 넓음.",
                            "sector": "기술 우위.", "concentration": "쏠림 보통."},
                           ensure_ascii=False)
        with patch(PROMPT_PATH, return_value=_SUFFICIENT_CTX), \
             patch(GEN_PATH, return_value=_raw(first)):
            _run()
        with patch(PROMPT_PATH, return_value=_SUFFICIENT_CTX), \
             patch(GEN_PATH, return_value=_raw(_full_envelope(), pt=999)):
            _run()
        assert TranslationLog.objects.count() == 1
        log = TranslationLog.objects.get()
        assert log.senses["regime"].startswith("후반부")  # 두 번째 값으로 덮어씀
        assert log.prompt_tokens == 999


@pytest.mark.django_db
class TestTranslationTaskFailureModes:
    def test_malformed_json_refused(self):
        with patch(PROMPT_PATH, return_value=_SUFFICIENT_CTX), \
             patch(GEN_PATH, return_value=_raw("이건 JSON이 아니라 그냥 문장이에요")):
            _run()
        log = TranslationLog.objects.get()
        assert log.status == TranslationLog.Status.REFUSED
        assert log.senses == {}

    def test_refusal_hint_refused(self):
        with patch(PROMPT_PATH, return_value=_SUFFICIENT_CTX), \
             patch(GEN_PATH, return_value=_raw("죄송하지만 응답할 수 없습니다")):
            _run()
        log = TranslationLog.objects.get()
        assert log.status == TranslationLog.Status.REFUSED

    def test_missing_key_partial_ok(self):
        partial = json.dumps({"regime": "강세 국면.", "breadth": "폭 넓음.",
                              "concentration": "쏠림 보통."}, ensure_ascii=False)  # sector 누락
        with patch(PROMPT_PATH, return_value=_SUFFICIENT_CTX), \
             patch(GEN_PATH, return_value=_raw(partial)):
            summary = _run()
        log = TranslationLog.objects.get()
        assert log.status == TranslationLog.Status.OK
        assert set(log.senses.keys()) == {"regime", "breadth", "concentration"}
        assert "missing:sector" in summary["issues"]

    def test_banned_phrase_discards_all(self):
        # 기존 llm.safety BANNED `\b매수\s*추천\b` 가 잡으려면 경계 성립 필요(뒤에 공백/구두점).
        bad = json.dumps({"regime": "단기 매수 추천 의견.", "breadth": "폭 넓음.",
                          "sector": "기술 우위.", "concentration": "쏠림 보통."},
                         ensure_ascii=False)
        with patch(PROMPT_PATH, return_value=_SUFFICIENT_CTX), \
             patch(GEN_PATH, return_value=_raw(bad)):
            _run()
        log = TranslationLog.objects.get()
        assert log.status == TranslationLog.Status.REFUSED
        assert log.senses == {}

    def test_insufficient_data_skips_llm(self):
        insufficient = {**_SUFFICIENT_CTX, "regime": {"stage": None, "status": None}}
        with patch(PROMPT_PATH, return_value=insufficient), \
             patch(GEN_PATH) as gen:
            _run()
        gen.assert_not_called()
        log = TranslationLog.objects.get()
        assert log.status == TranslationLog.Status.REFUSED
        assert log.senses == {}
        assert log.prompt_tokens == 0


class TestValidateSenses:
    """validate_senses 순수 함수 (DB 불필요)."""

    def test_strips_codeblock_and_parses(self):
        wrapped = "```json\n" + _full_envelope() + "\n```"
        result = validate_senses(wrapped)
        assert result.status == TranslationLog.Status.OK
        assert len(result.senses) == 4

    def test_empty_response_refused(self):
        result = validate_senses("   ")
        assert result.status == TranslationLog.Status.REFUSED
        assert result.issues == ["empty_response"]

    def test_non_object_envelope_refused(self):
        result = validate_senses(json.dumps(["a", "b"]))
        assert result.status == TranslationLog.Status.REFUSED
        assert "envelope_not_object" in result.issues

    def test_all_keys_missing_refused(self):
        result = validate_senses(json.dumps({"foo": "bar"}))
        assert result.status == TranslationLog.Status.REFUSED

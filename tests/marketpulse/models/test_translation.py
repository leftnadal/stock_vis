"""Phase 1.5 Translation Layer S2 — TranslationLog 모델 제약·라운드트립 검증.

S2 범위: 모델 전용(LLM 호출·생성 task·envelope serializer는 S3~S5).
BriefingLog 미러 정합(토큰 분리 정수 필드 + created_at만)을 함께 검증한다.
"""
from __future__ import annotations

from datetime import date as dt_date
from decimal import Decimal

import pytest
from django.db import IntegrityError
from django.db import models as dj_models


def _make(**overrides):
    from apps.market_pulse.models.translation import TranslationLog
    defaults = {'date': dt_date(2026, 6, 18)}
    defaults.update(overrides)
    return TranslationLog.objects.create(**defaults)


@pytest.mark.django_db
class TestTranslationLogRoundtrip:
    """생성·조회 라운드트립 + 기본값."""

    def test_create_and_fetch(self):
        from apps.market_pulse.models.translation import TranslationLog
        t = _make(model_version='gemini-2.5-flash')
        fetched = TranslationLog.objects.get(pk=t.pk)
        assert fetched.date == dt_date(2026, 6, 18)
        assert fetched.model_version == 'gemini-2.5-flash'

    def test_senses_default_empty_dict(self):
        """빈 senses 기본값 = {} (default=dict)."""
        t = _make()
        assert t.senses == {}

    def test_prompt_inputs_default_empty_dict(self):
        t = _make()
        assert t.prompt_inputs == {}

    def test_token_cost_latency_defaults(self):
        """토큰/지연 기본 0, cost_usd 기본 None."""
        t = _make()
        assert t.prompt_tokens == 0
        assert t.completion_tokens == 0
        assert t.latency_ms == 0
        assert t.cost_usd is None

    def test_created_at_autoset(self):
        t = _make()
        assert t.created_at is not None

    def test_str_renders(self):
        t = _make()
        rendered = str(t)
        assert isinstance(rendered, str) and rendered


@pytest.mark.django_db
class TestTranslationLogSensesJson:
    """senses JSON 라운드트립 — 다중 카드 키."""

    def test_multi_card_senses_roundtrip(self):
        from apps.market_pulse.models.translation import TranslationLog
        senses = {
            'regime': '시장이 천천히 식는 분위기예요.',
            'concentration': '소수 대형주에 쏠림이 강해지고 있어요.',
            'breadth': '오르는 종목과 내리는 종목이 팽팽해요.',
        }
        t = _make(senses=senses)
        t.refresh_from_db()
        assert t.senses['regime'].startswith('시장이')
        assert t.senses['concentration'] == senses['concentration']
        assert set(t.senses.keys()) == {'regime', 'concentration', 'breadth'}

    def test_prompt_inputs_roundtrip(self):
        from apps.market_pulse.models.translation import TranslationLog
        inputs = {'regime': {'band': 'LATE_BULL'}, 'raw': {'vix': 17.68}}
        t = _make(prompt_inputs=inputs)
        t.refresh_from_db()
        assert t.prompt_inputs['regime']['band'] == 'LATE_BULL'
        assert t.prompt_inputs['raw']['vix'] == 17.68

    def test_cost_and_tokens_set(self):
        t = _make(prompt_tokens=1200, completion_tokens=340, latency_ms=850,
                  cost_usd=Decimal('0.0012'))
        t.refresh_from_db()
        assert t.prompt_tokens == 1200
        assert t.completion_tokens == 340
        assert t.latency_ms == 850
        assert t.cost_usd == Decimal('0.0012')


@pytest.mark.django_db
class TestTranslationLogStatus:
    """status 기본/세팅 (S2 = OK/REFUSED만)."""

    def test_status_default_ok(self):
        from apps.market_pulse.models.translation import TranslationLog
        t = _make()
        assert t.status == TranslationLog.Status.OK

    def test_status_choices_ok_refused(self):
        from apps.market_pulse.models.translation import TranslationLog
        choices = dict(TranslationLog.Status.choices)
        assert set(choices.keys()) == {'OK', 'REFUSED'}

    def test_status_set_refused(self):
        from apps.market_pulse.models.translation import TranslationLog
        t = _make(status=TranslationLog.Status.REFUSED)
        t.refresh_from_db()
        assert t.status == TranslationLog.Status.REFUSED


@pytest.mark.django_db
class TestTranslationLogUnique:
    """unique(date, model_version) 제약 + BriefingLog 미러 정합."""

    def test_unique_date_model_version(self):
        _make(model_version='gemini-2.5-flash')
        with pytest.raises(IntegrityError):
            _make(model_version='gemini-2.5-flash')

    def test_same_date_diff_model_version_ok(self):
        """같은 date, 다른 model_version은 제약 통과."""
        _make(model_version='gemini-2.5-flash')
        _make(model_version='gemini-2.5-pro')

    def test_tokens_are_separate_integer_fields(self):
        """BriefingLog 미러: 토큰은 JSON 단일이 아닌 분리 정수 필드."""
        from apps.market_pulse.models.translation import TranslationLog
        pt = TranslationLog._meta.get_field('prompt_tokens')
        ct = TranslationLog._meta.get_field('completion_tokens')
        assert isinstance(pt, dj_models.PositiveIntegerField)
        assert isinstance(ct, dj_models.PositiveIntegerField)

    def test_no_updated_at_field(self):
        """BriefingLog 미러: created_at만, updated_at 미보유."""
        from apps.market_pulse.models.translation import TranslationLog
        names = {f.name for f in TranslationLog._meta.get_fields()}
        assert 'created_at' in names
        assert 'updated_at' not in names

    def test_no_fk_to_existing_models(self):
        """decouple: 기존 모델로의 FK 0 (기존 테이블 변경 0 보장)."""
        from apps.market_pulse.models.translation import TranslationLog
        fks = [
            f for f in TranslationLog._meta.get_fields()
            if isinstance(f, (dj_models.ForeignKey, dj_models.OneToOneField))
        ]
        assert fks == []

    def test_db_table_name(self):
        from apps.market_pulse.models.translation import TranslationLog
        assert TranslationLog._meta.db_table == 'mp_translation_log'

"""D-8 Static integrity tests."""

from __future__ import annotations

import pytest


def test_all_modules_importable():
    """모든 핵심 모듈이 import 에러 없이 로드되는지."""
    from portfolio import models, schemas  # noqa: F401
    from portfolio.prompts.e1 import build_e1_prompt  # noqa: F401
    from portfolio.prompts.e2 import build_e2_prompt  # noqa: F401
    from portfolio.prompts.e3 import build_e3_prompt  # noqa: F401
    from portfolio.prompts.e4 import build_e4_prompt  # noqa: F401
    from portfolio.prompts.e5 import build_e5_prompt  # noqa: F401
    from portfolio.prompts.e6 import build_e6_prompt  # noqa: F401
    from portfolio.prompts.tier0 import build_tier0  # noqa: F401
    from portfolio.schemas import (  # noqa: F401
        AdjustmentComparison,
        AdjustmentIntent,
        AnalysisContext,
        ConversationResponse,
        DiagnosticCards,
        MetricComments,
        OneLineDiagnosis,
        UserProfile,
    )


def test_preset_metric_consistency():
    """PRESET_METRICS에 참조된 모든 metric_id가 METRICS에 존재해야 함."""
    from portfolio.metrics.definitions.metrics import METRICS
    from portfolio.metrics.definitions.preset_metrics import PRESET_METRICS

    all_metric_ids = set(METRICS.keys())
    for preset_id, entries in PRESET_METRICS.items():
        for entry in entries:
            assert entry["metric_id"] in all_metric_ids, (
                f"{preset_id} references unknown metric {entry['metric_id']}"
            )


def test_metric_count():
    """지표 수 57 (stock_level 39 + portfolio_level 13 + composite 5)."""
    from portfolio.metrics.definitions.metrics import METRICS, get_metrics_by_type

    assert len(METRICS) == 57
    assert len(get_metrics_by_type("stock_level")) == 39
    assert len(get_metrics_by_type("portfolio_level")) == 13
    assert len(get_metrics_by_type("composite")) == 5


def test_preset_count():
    """프리셋 12개."""
    from portfolio.metrics.definitions.presets import PRESETS

    assert len(PRESETS) == 12


def test_version_bundle():
    """버전 번들 키/값 정합성."""
    from portfolio.metrics.definitions.versions import CURRENT_VERSIONS

    assert CURRENT_VERSIONS["metric_version"] == "1.2"
    for key in ("preset_version", "prompt_version", "scoring_version", "universe_version"):
        assert key in CURRENT_VERSIONS


def test_schema_pv3_field_names():
    """AnalysisContext의 PV3 필드명(analysis_target_portfolio/wallet_background) 준수."""
    from portfolio.schemas import AnalysisContext

    fields = set(AnalysisContext.model_fields.keys())
    assert "analysis_target_portfolio" in fields
    assert "wallet_background" in fields
    assert "portfolio" not in fields
    assert "wallet" not in fields


def test_django_models_importable():
    """D-0a 13개 모델 import 가능."""
    from portfolio.models import (  # noqa: F401
        AnalysisRun,
        ChatSession,
        Decision,
        DiagnosticCard,
        LLMComment,
        Message,
        MetricResult,
        PercentileCache,
        Portfolio,
        StoredAnalysis,
        Wallet,
        WalletHolding,
        WalletSnapshot,
    )

    with pytest.raises(ImportError):
        from portfolio.models import Holding  # noqa: F401
    with pytest.raises(ImportError):
        from portfolio.models import CandidateHolding  # noqa: F401

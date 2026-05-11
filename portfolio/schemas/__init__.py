"""
Stock-Vis Pydantic Schemas for LLM Tier 2.5 Context.

Usage:
    from portfolio.schemas import AnalysisContext, ReturnBreakdown
"""

from .analysis_context import (
    AnalysisContext,
    AnalysisTargetPortfolioContext,
    WalletBackgroundContext,
)
from .diagnostic import DiagnosticCard, Severity, StructuralOrSingle
from .holding import HoldingSummary
from .llm_outputs import (
    AdjustmentComparison,
    AdjustmentIntent,
    AdjustmentIntentType,
    AdjustmentOverride,
    ConversationResponse,
    DiagnosticCards,
    MetricComment,
    MetricComments,
    OneLineDiagnosis,
)
from .metric_result import MetricResult, MetricTier, StrengthWeakness
from .return_breakdown import (
    CategoryBreakdown,
    ContributionItem,
    ReturnBreakdown,
    ReturnBreakdownWithTime,
    ScopeType,
)
from .user_profile import UserProfile

__all__ = [
    # holding
    "HoldingSummary",
    # metric_result
    "MetricResult",
    "StrengthWeakness",
    "MetricTier",
    # diagnostic
    "DiagnosticCard",
    "Severity",
    "StructuralOrSingle",
    # return_breakdown
    "ReturnBreakdown",
    "ReturnBreakdownWithTime",
    "ContributionItem",
    "CategoryBreakdown",
    "ScopeType",
    # analysis_context
    "AnalysisContext",
    "AnalysisTargetPortfolioContext",
    "WalletBackgroundContext",
    # user_profile
    "UserProfile",
    # llm_outputs (E1~E6)
    "OneLineDiagnosis",
    "DiagnosticCards",
    "MetricComment",
    "MetricComments",
    "ConversationResponse",
    "AdjustmentOverride",
    "AdjustmentIntent",
    "AdjustmentIntentType",
    "AdjustmentComparison",
]

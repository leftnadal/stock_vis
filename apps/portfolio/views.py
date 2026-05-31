"""
Portfolio Coach Django views (deprecated module).

Slice 13 #65 (2026-05-21~22): legacy view 전수 제거 완료.
- pilot: E1 (`coach_e1_garp`) 제거
- E2 (`coach_e2_diagnostic_card`) 제거
- E3 (`coach_e3_metric_comment`) 제거
- E5 (`coach_e5_adjustment`) 제거
- E6 (`coach_e6_comparison`) 제거

모든 진입점이 `/api/v1/coach/eN/` (`portfolio/api/views.py`)로 단일화됨.
본 모듈은 portfolio.urls에서 더 이상 import되지 않으나, 외부 import 호환성 보존을
위해 비어 있는 상태로 유지한다. 향후 정리 시점에 모듈 자체 제거 검토 (#65 후속).
"""

from __future__ import annotations

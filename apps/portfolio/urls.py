"""Portfolio Coach URL routes.

Slice 13 #65 (2026-05-21~22): 모든 legacy view 5건 제거 완료.
- coach/e1/garp/ → /api/v1/coach/e1/
- coach/e2/diagnostic-card/ → /api/v1/coach/e2/
- coach/e3/metric-comment/ → /api/v1/coach/e3/
- coach/e5/adjustment/ → /api/v1/coach/e5/
- coach/e6/comparison/ → /api/v1/coach/e6/

E4는 legacy view 부재 (special case).

본 urlpatterns는 빈 상태로 유지된다. `config/urls.py`에서 본 모듈을 include하지만
모든 경로는 `portfolio.api.urls`로 단일화됨. 향후 include 자체 제거 검토 (#65 후속).
"""

from __future__ import annotations

from django.urls import path

from apps.portfolio import views  # noqa: F401 — backward-compat 모듈 노출

app_name = "portfolio"

urlpatterns: list = []

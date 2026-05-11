"""
SEC-PR-14: Admin 대시보드 뷰.
SEC-PR-15: On-demand filing data API.
"""

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from rest_framework.permissions import IsAdminUser
from rest_framework.views import APIView
from rest_framework.response import Response

from .quality_checks import get_dashboard_stats, run_post_batch_quality_checks


@staff_member_required
def sec_pipeline_dashboard(request):
    """SEC Pipeline 품질 대시보드 (Admin 전용)."""
    stats = get_dashboard_stats()
    alerts = run_post_batch_quality_checks(hours_back=24)

    context = {
        'title': 'SEC Pipeline Dashboard',
        'stats': stats,
        'alerts': alerts,
    }
    return render(request, 'admin/sec_pipeline/dashboard.html', context)


class FilingDataView(APIView):
    """On-demand filing data API. GET → 200(있음) 또는 202(수집 트리거됨).

    audit P0 #6: IsAdminUser — 외부 SEC fetch 트리거가 비용을 발생시키므로 admin 한정.
    """
    permission_classes = [IsAdminUser]

    def get(self, request, symbol):
        from .on_demand import get_or_collect_filing

        result = get_or_collect_filing(symbol)

        if result is None:
            return Response(
                {'symbol': symbol.upper(), 'status': 'collecting',
                 'message': 'Collection triggered. Check back shortly.'},
                status=202,
            )

        if result.get('status') == 'available':
            return Response(result, status=200)

        return Response(result, status=200)

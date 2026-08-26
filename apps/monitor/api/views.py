"""Monitor API views (MON-P2-S3).

user 스코프 격리: 모든 queryset은 request.user 소유로 제한(IDOR 방지).
평가 트리거 = MonitorViewSet.evaluate action (수동). beat 주기 등록은 별도 스텝.
"""
from datetime import date

from django.db.models import (
    Case,
    Count,
    Exists,
    F,
    IntegerField,
    Min,
    OuterRef,
    Q,
    Subquery,
    Value,
    When,
)
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.monitor.catalog import catalog_for

from apps.monitor.api.serializers import (
    AdvisorNoteSerializer,
    AlertEventSerializer,
    ClaimEvidenceSerializer,
    ClaimSerializer,
    DecisionJournalEntrySerializer,
    IndicatorReadingSerializer,
    MonitorIndicatorSerializer,
    MonitorSerializer,
    SwapHoldLogSerializer,
)
from apps.monitor.models import (
    AdvisorNote,
    AlertEvent,
    Claim,
    ClaimEvidence,
    DecisionJournalEntry,
    IndicatorReading,
    Monitor,
    MonitorIndicator,
    MonitorSnapshot,
    SwapHoldLog,
)
from apps.monitor.services import closure
from apps.monitor.services.evidence_judge import judge_claim_evidences
from apps.monitor.services.pipeline import evaluate_monitor
from apps.monitor.services.sparkline import score_series
from apps.monitor.services.snapshot_series import snapshot_series

# 상태 심각도 랭크: 위험(0) → 약화(1) → 관찰(2) → 유지(3). 트리아지 정렬 1차 키.
_SEVERITY_WHENS = [
    When(current_state__in=["critical", "expired", "needs_review"], then=Value(0)),
    When(current_state="weakening", then=Value(1)),
    When(current_state__in=["warming_up", "active"], then=Value(2)),
    # strengthening·paused → 유지(3, default)
]


class IndicatorCatalogView(APIView):
    """scope별 지표 카탈로그 (빌더 3단계). GET /monitor/catalog/?scope=stock."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        scope = request.query_params.get("scope", "stock")
        return Response({"scope": scope, "indicators": catalog_for(scope)})


class ScenarioSuggestView(APIView):
    """L계열 가격 제안 (빌더 4단계, 읽기 전용). GET /monitor/scenario-suggest/?symbol=AAPL.

    DailyPrice에서 지지선(스윙 저점)·ATR×2 손절 폭 산출(서버측 — 3년 OHLC 클라 전송 금지).
    확정은 항상 사용자(3-B). 히스토리 부족 시 available=False.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.monitor.services.scenario_suggest import (
            recompute_coherence,
            suggest_hold_scenario,
            suggest_scenario,
        )

        symbol = (request.query_params.get("symbol") or "").strip()
        if not symbol:
            return Response(
                {"detail": "symbol 파라미터가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST
            )

        # 보유 관리 프리필 (D-HOLD-DECISIONS 부속) — mode=hold + purchase_price. 기존 키 불변.
        mode = (request.query_params.get("mode") or "").strip()
        if mode == "hold":
            purchase = request.query_params.get("purchase_price")
            if not purchase:
                return Response(
                    {"detail": "mode=hold는 purchase_price 파라미터가 필요합니다."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                return Response(suggest_hold_scenario(symbol, purchase))
            except (ValueError, ArithmeticError):
                return Response(
                    {"detail": "purchase_price가 올바른 숫자여야 합니다."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        payload = suggest_scenario(symbol)

        # 정합 재계산(additive, TIMING-P2.5): entry + (target|deadline) 제공 시 나머지 후보.
        qp = request.query_params
        entry = qp.get("entry")
        if entry:
            try:
                payload["coherence"] = recompute_coherence(
                    symbol,
                    entry=entry,
                    target=qp.get("target") or None,
                    deadline=qp.get("deadline") or None,
                    stop=qp.get("stop") or None,
                )
            except (ValueError, ArithmeticError) as e:
                payload["coherence"] = {"error": "정합 계산 실패", "detail": str(e)}
        return Response(payload)


class MonitorViewSet(viewsets.ModelViewSet):
    serializer_class = MonitorSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # 카드 렌더 데이터 + 트리아지 정렬을 서버에서 확정(페이지네이션 하 클라 정렬 금지).
        latest_snap = (
            MonitorSnapshot.objects.filter(monitor=OuterRef("pk"))
            .order_by("-asof_date")
            .values("overall_score")[:1]
        )
        # MON-P2A T3: 커버리지 표출용 — 최신 스냅샷 data_coverage(유효 비율).
        latest_cov = (
            MonitorSnapshot.objects.filter(monitor=OuterRef("pk"))
            .order_by("-asof_date")
            .values("data_coverage")[:1]
        )
        qs = (
            Monitor.objects.filter(user=self.request.user)
            .annotate(
                severity_rank=Case(
                    *_SEVERITY_WHENS, default=Value(3), output_field=IntegerField()
                ),
                latest_score=Subquery(latest_snap),
                latest_coverage=Subquery(latest_cov),
                indicator_count=Count(
                    "indicators",
                    filter=Q(indicators__is_active=True),
                    distinct=True,
                ),
                # 커버리지 분모 = 활성·비일시정지 지표 수(coverage 산정 기준과 일치).
                active_unpaused=Count(
                    "indicators",
                    filter=Q(indicators__is_active=True, indicators__is_paused=False),
                    distinct=True,
                ),
                next_deadline=Min(
                    "claims__deadline", filter=Q(claims__status="active")
                ),
                has_claim=Exists(Claim.objects.filter(monitor=OuterRef("pk"))),
            )
        )

        # filter: scope, has_claim (Exists로 distinct 회피)
        scope = self.request.query_params.get("scope")
        if scope:
            qs = qs.filter(scope=scope)
        has_claim = self.request.query_params.get("has_claim")
        if has_claim == "true":
            qs = qs.filter(Exists(Claim.objects.filter(monitor=OuterRef("pk"))))

        # 정렬: 심각도 → 마감 임박(nulls last) → 최근 갱신
        return qs.order_by(
            "severity_rank", F("next_deadline").asc(nulls_last=True), "-updated_at"
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"])
    def evaluate(self, request, pk=None):
        """지표 스코어 → 집계 → 스냅샷 → 상태 판정 파이프라인 실행(수동 트리거)."""
        monitor = self.get_object()  # user 스코프 자동 적용
        result = evaluate_monitor(monitor)
        return Response(result, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"])
    def sparkline(self, request, pk=None):
        """상태밴드 스파크라인 데이터 — 최근 N거래일 score 시계열 + 밴드 + 전이 표식."""
        monitor = self.get_object()  # user 스코프 자동 적용
        try:
            window = int(request.query_params.get("window", 30))
        except (TypeError, ValueError):
            window = 30
        window = max(5, min(window, 120))
        return Response(score_series(monitor, window=window))

    @action(detail=True, methods=["get"])
    def snapshots(self, request, pk=None):
        """점수 정본 시계열 — MonitorSnapshot(동결 기록) 기반 {asof, score, delta} (MON-P2B T1).

        스트립 델타·일지 스냅샷의 단일 원천. sparkline(추세 곡선, 재산출)과 별개 —
        여기는 '그날 실제로 기록한 값'만 담아 로직 변경에도 과거 불변.
        """
        monitor = self.get_object()  # user 스코프 자동 적용
        try:
            window = int(request.query_params.get("window", 30))
        except (TypeError, ValueError):
            window = 30
        window = max(5, min(window, 120))
        return Response(snapshot_series(monitor, window=window))

    @action(detail=True, methods=["get"])
    def advisor_notes(self, request, pk=None):
        """ADVISOR L-A 브리핑 목록 (MON-P4-LA T3) — 일지 advisor kind 소스.

        단일 모델 조회(aggregate 창설 아님). 최신순, surface=L-A 한정.
        """
        monitor = self.get_object()  # user 스코프 자동 적용
        try:
            limit = int(request.query_params.get("limit", 30))
        except (TypeError, ValueError):
            limit = 30
        limit = max(1, min(limit, 90))
        qs = monitor.advisor_notes.filter(
            surface=AdvisorNote.Surface.L_A
        ).order_by("-asof")[:limit]
        return Response(AdvisorNoteSerializer(qs, many=True).data)


class AlertEventViewSet(viewsets.ReadOnlyModelViewSet):
    """전이 알림 — 인앱 패널·헤더 벨 (user 스코프, 읽기 + 읽음 처리 action)."""

    serializer_class = AlertEventSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # MON-DETAIL-P1 T2: ?monitor=<id> = 상세 일지(journal)용 전이 전체 타임라인.
        # 지정 시 해당 모니터로 스코프 + 억제 전이도 포함(일지는 완결 타임라인 — 억제 표기).
        # 미지정(전역 배지·목록) = 기존 의미론 불변: 억제 제외(결정 1-C 쿨다운, 행위보존).
        monitor_id = self.request.query_params.get("monitor")
        if monitor_id:
            qs = AlertEvent.objects.filter(
                monitor__user=self.request.user, monitor_id=monitor_id
            ).select_related("monitor")
        else:
            qs = AlertEvent.objects.filter(
                monitor__user=self.request.user, is_suppressed=False
            ).select_related("monitor")
        if self.request.query_params.get("unread") == "true":
            qs = qs.filter(read=False)
        if self.request.query_params.get("deterioration") == "true":
            qs = qs.filter(is_deterioration=True)
        return qs

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """헤더 벨 배지용 — 미확인 악화 알림 수(악화만 카운트, 결정 1-C)."""
        count = AlertEvent.objects.filter(
            monitor__user=request.user,
            is_suppressed=False,
            is_deterioration=True,
            read=False,
        ).count()
        return Response({"unread_deterioration_count": count})

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        """개별 알림 읽음 처리."""
        alert = self.get_object()
        if not alert.read:
            alert.read = True
            alert.save(update_fields=["read"])
        return Response(self.get_serializer(alert).data)

    @action(detail=False, methods=["post"])
    def read_all(self, request):
        """미확인 알림 일괄 읽음 처리."""
        n = self.get_queryset().filter(read=False).update(read=True)
        return Response({"marked_read": n})


class _OwnedByMonitorMixin:
    """monitor__user 소유 검증 공통 로직."""

    permission_classes = [IsAuthenticated]
    monitor_lookup = "monitor"  # override: 'indicator__monitor' 등

    def _assert_owner(self, obj_monitor):
        if obj_monitor.user_id != self.request.user.id:
            raise PermissionDenied("본인 소유 Monitor가 아닙니다.")


class MonitorIndicatorViewSet(_OwnedByMonitorMixin, viewsets.ModelViewSet):
    serializer_class = MonitorIndicatorSerializer

    def get_queryset(self):
        qs = MonitorIndicator.objects.filter(monitor__user=self.request.user)
        # ?monitor= 존중 — 상세 페이지가 특정 모니터 지표만 조회(모니터 2개+ 시 교차 표시 방지).
        monitor_id = self.request.query_params.get("monitor")
        if monitor_id:
            qs = qs.filter(monitor_id=monitor_id)
        return qs

    def perform_create(self, serializer):
        self._assert_owner(serializer.validated_data["monitor"])
        serializer.save()


class ClaimViewSet(_OwnedByMonitorMixin, viewsets.ModelViewSet):
    serializer_class = ClaimSerializer

    def get_queryset(self):
        return Claim.objects.filter(monitor__user=self.request.user)

    def perform_create(self, serializer):
        self._assert_owner(serializer.validated_data["monitor"])
        serializer.save()

    @action(detail=True, methods=["get"], url_path="close-preview")
    def close_preview(self, request, pk=None):
        """마감 모달 프리필 — 제안 판정·종합점수·지표 목록 (상태 변경 없음)."""
        claim = self.get_object()  # owner 스코프 자동 적용
        return Response(closure.close_preview(claim), status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        """가설 마감 (원자적) — 판정·회고·지표별 결과·동결 스냅샷."""
        claim = self.get_object()
        data = request.data
        try:
            closed = closure.close_claim(
                claim,
                final_verdict=data.get("final_verdict"),
                factor_tags=data.get("factor_tags", []),
                retro_memo=data.get("retro_memo", ""),
                indicator_results=data.get("indicator_results", []),
                user=request.user,
            )
        except closure.AlreadyClosedError as e:
            return Response({"detail": str(e)}, status=status.HTTP_409_CONFLICT)
        except closure.ClosureValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(closed).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="evidence-status")
    def evidence_status(self, request, pk=None):
        """근거 생사 판정 조회 (RECON-SWAP-0813 PART 3-BE, 읽기 전용) —
        judge_claim_evidences 산출을 FE 대결 화면 계약층에 노출. DB 쓰기 없음."""
        claim = self.get_object()  # owner 스코프 자동 적용

        as_of_raw = request.query_params.get("as_of")
        as_of = timezone.localdate()
        if as_of_raw:
            try:
                as_of = date.fromisoformat(as_of_raw)
            except ValueError:
                return Response(
                    {"detail": "as_of는 YYYY-MM-DD 형식이어야 합니다."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        results = judge_claim_evidences(claim, as_of_date=as_of)
        evidences_by_id = {
            ev.id: ev for ev in claim.evidences.select_related("indicator").all()
        }
        enriched = []
        for r in results:
            ev = evidences_by_id.get(r["evidence_id"])
            enriched.append({
                **r,
                "indicator_name": (
                    ev.indicator.name if ev is not None and ev.indicator_id else None
                ),
                "description": ev.description if ev is not None else "",
            })

        return Response({
            "claim_id": claim.id,
            "as_of": as_of.isoformat(),
            "total": len(enriched),
            "alive": sum(1 for r in enriched if r["status"] == "alive"),
            "results": enriched,
        })


class SwapHoldLogViewSet(_OwnedByMonitorMixin, viewsets.ModelViewSet):
    """교체 검토 "보류" 클릭 이력 (RECON-SWAP-0813 PART 3-BE). ClaimEvidenceViewSet과
    동일 관례 — claim 하위 별도 엔드포인트, 소유자 체크는 claim.monitor.user."""

    serializer_class = SwapHoldLogSerializer
    monitor_lookup = "claim__monitor"

    def get_queryset(self):
        # select_related — hold_performance_pct가 claim.monitor.target_ref를 매 로그마다
        # 참조(SwapHoldLogSerializer, C-BE) → N+1 방지.
        qs = SwapHoldLog.objects.filter(
            claim__monitor__user=self.request.user
        ).select_related("claim__monitor")
        claim_id = self.request.query_params.get("claim")
        if claim_id:
            qs = qs.filter(claim_id=claim_id)
        return qs

    def perform_create(self, serializer):
        self._assert_owner(serializer.validated_data["claim"].monitor)
        serializer.save()


class DecisionJournalEntryViewSet(_OwnedByMonitorMixin, viewsets.ModelViewSet):
    """마감/재커밋 결정 일지 (RECON-SWAP-0813 PART 3-BE). P-4 회고 재인용 대비 —
    Claim 상태 전이 자체는 다루지 않음(FE가 기존 마감/재커밋 경로와 조립)."""

    serializer_class = DecisionJournalEntrySerializer
    monitor_lookup = "claim__monitor"

    def get_queryset(self):
        qs = DecisionJournalEntry.objects.filter(claim__monitor__user=self.request.user)
        claim_id = self.request.query_params.get("claim")
        if claim_id:
            qs = qs.filter(claim_id=claim_id)
        return qs

    def perform_create(self, serializer):
        self._assert_owner(serializer.validated_data["claim"].monitor)
        serializer.save()


class IndicatorReadingViewSet(_OwnedByMonitorMixin, viewsets.ModelViewSet):
    serializer_class = IndicatorReadingSerializer

    def get_queryset(self):
        return IndicatorReading.objects.filter(
            indicator__monitor__user=self.request.user
        )

    def perform_create(self, serializer):
        self._assert_owner(serializer.validated_data["indicator"].monitor)
        serializer.save()


class ClaimEvidenceViewSet(_OwnedByMonitorMixin, viewsets.ModelViewSet):
    """Claim 근거 CRUD (RECON-SWAP-0813 PART 1). ClaimSerializer.evidences는 읽기 전용
    nested — 생성/수정은 여기서(MonitorIndicatorViewSet과 동일 관례)."""

    serializer_class = ClaimEvidenceSerializer
    monitor_lookup = "claim__monitor"

    def get_queryset(self):
        qs = ClaimEvidence.objects.filter(claim__monitor__user=self.request.user)
        # ?claim= 존중 — 특정 Claim의 근거만 조회(상세 화면 교차 표시 방지, indicators와 동일 관례).
        claim_id = self.request.query_params.get("claim")
        if claim_id:
            qs = qs.filter(claim_id=claim_id)
        return qs

    def perform_create(self, serializer):
        self._assert_owner(serializer.validated_data["claim"].monitor)
        serializer.save()

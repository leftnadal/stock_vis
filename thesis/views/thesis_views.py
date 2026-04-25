"""Thesis CRUD + Premise/Indicator ViewSets"""

import logging

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from thesis.models import (
    Thesis, ThesisPremise, ThesisIndicator,
    HypothesisEvent, ValidityRecord, InvestorDNA,
)
from thesis.serializers import (
    ThesisListSerializer, ThesisDetailSerializer, ThesisCreateSerializer,
    ThesisPremiseSerializer, ThesisIndicatorSerializer,
)
from thesis.services.indicator_matcher import match_indicators_for_premise

logger = logging.getLogger(__name__)


class ThesisViewSet(viewsets.ModelViewSet):
    """
    가설 CRUD + close 액션.
    list   → GET /              내 가설 목록
    create → POST /             가설 직접 생성
    retrieve → GET /{id}/       가설 상세
    partial_update → PATCH /{id}/ 가설 수정
    close  → POST /{id}/close/  가설 마감
    """
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'head', 'options']  # PUT/DELETE 제한

    def get_serializer_class(self):
        if self.action == 'list':
            return ThesisListSerializer
        if self.action == 'create':
            return ThesisCreateSerializer
        return ThesisDetailSerializer

    def get_queryset(self):
        qs = Thesis.objects.filter(user=self.request.user)
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    def perform_create(self, serializer):
        thesis = serializer.save()
        try:
            HypothesisEvent.objects.create(
                user=self.request.user,
                thesis=thesis,
                event_type='thesis_created',
                event_data={'entry_source': thesis.entry_source},
            )
        except Exception as e:
            logger.warning(f"Failed to record thesis_created event: {e}")

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """가설 마감 + ValidityRecord + InvestorDNA 갱신."""
        thesis = self.get_object()  # get_queryset()에서 user 필터 적용됨

        if thesis.status == 'closed':
            return Response(
                {'error': '이미 마감된 가설입니다.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        outcome = request.data.get('outcome')
        if outcome not in ('correct', 'incorrect', 'neutral'):
            return Response(
                {'error': 'outcome은 correct/incorrect/neutral 중 하나여야 합니다.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        outcome_note = request.data.get('outcome_note', '')
        thesis_correct = (outcome == 'correct')

        # ValidityRecord 생성
        for indicator in thesis.indicators.filter(is_active=True):
            indicator_aligned = (indicator.current_score or 0) > 0
            score = _compute_validity_score(indicator_aligned, thesis_correct)
            data_key = _get_data_key(indicator)

            try:
                ValidityRecord.objects.create(
                    thesis_type=thesis.thesis_type,
                    indicator_data_key=data_key,
                    market_regime='normal',  # Phase 1: 고정
                    indicator_aligned=indicator_aligned,
                    thesis_correct=thesis_correct,
                    score=score,
                    thesis=thesis,
                    indicator=indicator,
                )
            except Exception as e:
                logger.warning(f"Failed to create ValidityRecord: {e}")

        # HypothesisEvent 기록
        try:
            HypothesisEvent.objects.create(
                user=request.user,
                thesis=thesis,
                event_type='thesis_closed',
                event_data={
                    'duration_days': (timezone.localdate() - thesis.created_at.date()).days,
                },
            )
            outcome_event_map = {
                'correct': 'outcome_correct',
                'incorrect': 'outcome_incorrect',
                'neutral': 'outcome_neutral',
            }
            HypothesisEvent.objects.create(
                user=request.user,
                thesis=thesis,
                event_type=outcome_event_map[outcome],
                event_data={
                    'outcome_return': request.data.get('outcome_return'),
                },
            )
        except Exception as e:
            logger.warning(f"Failed to record close events: {e}")

        # thesis.save() 먼저 → InvestorDNA에서 closed_theses 카운트 정확하게
        thesis.status = 'closed'
        thesis.outcome = outcome
        thesis.outcome_note = outcome_note
        thesis.closed_at = timezone.now()
        thesis.save(update_fields=['status', 'outcome', 'outcome_note', 'closed_at'])

        # InvestorDNA 갱신 (save 이후여야 closed_theses 카운트 정확)
        try:
            _update_investor_dna(request.user, thesis, outcome)
        except Exception as e:
            logger.warning(f"Failed to update InvestorDNA: {e}")

        return Response({'status': 'closed', 'thesis_id': str(thesis.id)})


class ThesisPremiseViewSet(viewsets.ModelViewSet):
    """
    부모: thesis/{thesis_id}/premises/
    """
    serializer_class = ThesisPremiseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        thesis_id = self.kwargs['thesis_id']
        thesis = get_object_or_404(Thesis, id=thesis_id, user=self.request.user)
        return ThesisPremise.objects.filter(thesis=thesis)

    def perform_create(self, serializer):
        thesis_id = self.kwargs['thesis_id']
        thesis = get_object_or_404(Thesis, id=thesis_id, user=self.request.user)
        premise = serializer.save(thesis=thesis)

        try:
            HypothesisEvent.objects.create(
                user=self.request.user,
                thesis=thesis,
                event_type='premise_added',
                event_data={
                    'premise_id': str(premise.id),
                    'category': premise.category,
                },
            )
        except Exception as e:
            logger.warning(f"Failed to record premise_added event: {e}")

    def perform_destroy(self, instance):
        try:
            HypothesisEvent.objects.create(
                user=self.request.user,
                thesis=instance.thesis,
                event_type='premise_removed',
                event_data={'premise_id': str(instance.id)},
            )
        except Exception as e:
            logger.warning(f"Failed to record premise_removed event: {e}")
        instance.delete()


class ThesisIndicatorViewSet(viewsets.ModelViewSet):
    """
    부모: thesis/{thesis_id}/indicators/
    + auto_recommend: POST /indicators/auto/
    """
    serializer_class = ThesisIndicatorSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        thesis_id = self.kwargs['thesis_id']
        thesis = get_object_or_404(Thesis, id=thesis_id, user=self.request.user)
        return ThesisIndicator.objects.filter(thesis=thesis)

    def perform_create(self, serializer):
        thesis_id = self.kwargs['thesis_id']
        thesis = get_object_or_404(Thesis, id=thesis_id, user=self.request.user)
        indicator = serializer.save(thesis=thesis)

        # AI 추천 수락 이벤트
        is_ai = self.request.data.get('is_ai_recommended', False)
        event_type = 'ai_suggestion_accepted' if is_ai else 'indicator_added'

        try:
            HypothesisEvent.objects.create(
                user=self.request.user,
                thesis=thesis,
                event_type=event_type,
                event_data={
                    'indicator_id': str(indicator.id),
                    'indicator_type': indicator.indicator_type,
                    'data_source': indicator.data_source,
                },
            )
        except Exception as e:
            logger.warning(f"Failed to record {event_type} event: {e}")

    def perform_destroy(self, instance):
        try:
            HypothesisEvent.objects.create(
                user=self.request.user,
                thesis=instance.thesis,
                event_type='indicator_removed',
                event_data={'indicator_id': str(instance.id)},
            )
        except Exception as e:
            logger.warning(f"Failed to record indicator_removed event: {e}")
        instance.delete()

    @action(detail=False, methods=['post'])
    def auto(self, request, thesis_id=None):
        """AI 자동 지표 추천."""
        thesis = get_object_or_404(Thesis, id=thesis_id, user=request.user)
        premise_id = request.data.get('premise_id')

        if premise_id:
            premise = get_object_or_404(ThesisPremise, id=premise_id, thesis=thesis)
            premise_text = premise.content
        else:
            # 모든 활성 전제의 텍스트 결합
            premise_text = ' '.join(
                thesis.premises.filter(is_active=True).values_list('content', flat=True)
            )

        indicators = match_indicators_for_premise(premise_text, thesis, request.user)

        # HypothesisEvent 기록
        try:
            HypothesisEvent.objects.create(
                user=request.user,
                thesis=thesis,
                event_type='ai_suggestion_shown',
                event_data={
                    'premise_id': premise_id,
                    'count': len(indicators),
                },
            )
        except Exception as e:
            logger.warning(f"Failed to record ai_suggestion_shown event: {e}")

        return Response({
            'indicators': indicators,
            'count': len(indicators),
        })


def _compute_validity_score(indicator_aligned, thesis_correct):
    """2x2 매트릭스 점수 계산."""
    if indicator_aligned and thesis_correct:
        return 0.3
    elif indicator_aligned and not thesis_correct:
        return -0.2
    elif not indicator_aligned and thesis_correct:
        return -0.15
    else:
        return 0.05


def _get_data_key(indicator):
    """지표의 data_params에서 핵심 키 추출."""
    params = indicator.data_params or {}
    return params.get('symbol') or params.get('series_id') or params.get('metric') or indicator.name


def _update_investor_dna(user, thesis, outcome):
    """InvestorDNA 집계 갱신."""
    dna, _ = InvestorDNA.objects.get_or_create(user=user)

    dna.total_theses = Thesis.objects.filter(user=user).count()
    dna.closed_theses = Thesis.objects.filter(user=user, status='closed').count()
    dna.correct_count = HypothesisEvent.objects.filter(
        user=user, event_type='outcome_correct',
    ).count()
    dna.incorrect_count = HypothesisEvent.objects.filter(
        user=user, event_type='outcome_incorrect',
    ).count()

    # premise_category_counts 집계
    premise_events = HypothesisEvent.objects.filter(
        user=user, event_type='premise_added',
    )
    cat_counts = {}
    for event in premise_events:
        cat = (event.event_data or {}).get('category', 'custom')
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
    dna.premise_category_counts = cat_counts

    # indicator_type_counts 집계
    ind_events = HypothesisEvent.objects.filter(
        user=user, event_type__in=['indicator_added', 'ai_suggestion_accepted'],
    )
    type_counts = {}
    for event in ind_events:
        itype = (event.event_data or {}).get('indicator_type', 'custom')
        type_counts[itype] = type_counts.get(itype, 0) + 1
    dna.indicator_type_counts = type_counts

    # AI 수락률
    dna.ai_suggestions_shown = HypothesisEvent.objects.filter(
        user=user, event_type='ai_suggestion_shown',
    ).count()
    dna.ai_suggestions_accepted = HypothesisEvent.objects.filter(
        user=user, event_type='ai_suggestion_accepted',
    ).count()

    dna.save()

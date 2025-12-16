"""
Cost Tracker Service - 비용 추적 서비스

LLM API 사용량과 비용을 추적하고 관리합니다.

Features:
    - 모델별 가격 정보 관리
    - 실시간 비용 계산
    - 사용량 로깅
    - 예산 관리 (일일/월간 제한)
    - Prometheus 메트릭 연동
"""

import logging
from decimal import Decimal
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


class CostTracker:
    """
    비용 추적 서비스

    LLM API 사용량과 비용을 추적합니다.
    """

    # LLM 모델별 가격 (USD per 1M tokens)
    # 2025년 1월 기준
    PRICING = {
        # Gemini 모델
        'gemini-2.5-flash': {
            'input': 0.15,      # $0.15/1M input tokens
            'output': 0.60,     # $0.60/1M output tokens
            'name': 'Gemini 2.5 Flash',
        },
        'gemini-2.5-flash-thinking': {
            'input': 0.15,
            'output': 3.50,     # Thinking mode는 더 비쌈
            'name': 'Gemini 2.5 Flash (Thinking)',
        },
        'gemini-2.5-pro': {
            'input': 1.25,
            'output': 10.00,
            'name': 'Gemini 2.5 Pro',
        },
        # Claude 모델
        'claude-3-5-sonnet': {
            'input': 3.00,
            'output': 15.00,
            'name': 'Claude 3.5 Sonnet',
        },
        'claude-sonnet-4': {
            'input': 3.00,
            'output': 15.00,
            'name': 'Claude Sonnet 4',
        },
        'claude-3-5-haiku': {
            'input': 0.80,
            'output': 4.00,
            'name': 'Claude 3.5 Haiku',
        },
        'claude-3-haiku': {
            'input': 0.25,
            'output': 1.25,
            'name': 'Claude 3 Haiku',
        },
        'claude-3-opus': {
            'input': 15.00,
            'output': 75.00,
            'name': 'Claude 3 Opus',
        },
        # 기본값 (알 수 없는 모델)
        'default': {
            'input': 1.00,
            'output': 5.00,
            'name': 'Unknown Model',
        }
    }

    # 일일/월간 예산 제한 (USD)
    DEFAULT_DAILY_LIMIT = 10.0    # $10/일
    DEFAULT_MONTHLY_LIMIT = 100.0  # $100/월

    def __init__(
        self,
        daily_limit: Optional[float] = None,
        monthly_limit: Optional[float] = None
    ):
        """
        Args:
            daily_limit: 일일 예산 제한 (USD)
            monthly_limit: 월간 예산 제한 (USD)
        """
        self.daily_limit = daily_limit or getattr(
            settings, 'RAG_DAILY_COST_LIMIT', self.DEFAULT_DAILY_LIMIT
        )
        self.monthly_limit = monthly_limit or getattr(
            settings, 'RAG_MONTHLY_COST_LIMIT', self.DEFAULT_MONTHLY_LIMIT
        )

    def get_model_pricing(self, model: str) -> Dict[str, float]:
        """
        모델 가격 정보 조회

        Args:
            model: 모델명 (예: 'gemini-2.5-flash', 'claude-3-5-sonnet')

        Returns:
            {'input': float, 'output': float, 'name': str}
        """
        # 정확한 매칭
        if model in self.PRICING:
            return self.PRICING[model]

        # 부분 매칭 (모델 버전 포함된 경우)
        model_lower = model.lower()
        for key, pricing in self.PRICING.items():
            if key in model_lower:
                return pricing

        # 기본값
        logger.warning(f"Unknown model pricing: {model}, using default")
        return self.PRICING['default']

    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """
        비용 계산

        Args:
            model: 모델명
            input_tokens: 입력 토큰 수
            output_tokens: 출력 토큰 수

        Returns:
            비용 (USD)
        """
        pricing = self.get_model_pricing(model)

        input_cost = (input_tokens / 1_000_000) * pricing['input']
        output_cost = (output_tokens / 1_000_000) * pricing['output']

        return input_cost + output_cost

    def calculate_cost_saved(
        self,
        model: str,
        estimated_input_tokens: int,
        estimated_output_tokens: int
    ) -> float:
        """
        캐시 히트로 절감된 비용 계산

        Args:
            model: 사용했을 모델명
            estimated_input_tokens: 예상 입력 토큰
            estimated_output_tokens: 예상 출력 토큰

        Returns:
            절감된 비용 (USD)
        """
        return self.calculate_cost(
            model, estimated_input_tokens, estimated_output_tokens
        )

    async def log_usage(
        self,
        user_id: Optional[int],
        session_id: Optional[int],
        message_id: Optional[int],
        model: str,
        model_version: str,
        request_type: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int,
        cached: bool = False,
        cache_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[int]:
        """
        사용량 로깅

        Args:
            user_id: 사용자 ID
            session_id: 세션 ID
            message_id: 메시지 ID
            model: 모델 타입 (gemini-flash, claude-sonnet 등)
            model_version: 정확한 모델 버전
            request_type: 요청 타입 (analysis, entity_extraction 등)
            input_tokens: 입력 토큰
            output_tokens: 출력 토큰
            latency_ms: 응답 시간 (ms)
            cached: 캐시 히트 여부
            cache_id: 캐시 ID
            metadata: 추가 메타데이터

        Returns:
            생성된 UsageLog ID
        """
        # 비용 계산 (캐시 히트면 0)
        cost = 0.0 if cached else self.calculate_cost(
            model_version or model, input_tokens, output_tokens
        )

        try:
            usage_log = await self._create_usage_log(
                user_id=user_id,
                session_id=session_id,
                message_id=message_id,
                model=model,
                model_version=model_version,
                request_type=request_type,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost,
                latency_ms=latency_ms,
                cached=cached,
                cache_id=cache_id or '',
                metadata=metadata or {}
            )

            # Prometheus 메트릭 기록
            self._record_metrics(
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=cost,
                latency_ms=latency_ms,
                cached=cached
            )

            logger.debug(
                f"Usage logged: {model} - {input_tokens}+{output_tokens} tokens, "
                f"${cost:.6f}, cached={cached}"
            )

            return usage_log.id if usage_log else None

        except Exception as e:
            logger.error(f"Failed to log usage: {e}")
            return None

    @sync_to_async
    def _create_usage_log(
        self,
        user_id: Optional[int],
        session_id: Optional[int],
        message_id: Optional[int],
        model: str,
        model_version: str,
        request_type: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        latency_ms: int,
        cached: bool,
        cache_id: str,
        metadata: dict
    ):
        """UsageLog 생성 (sync)"""
        from ..models import UsageLog

        return UsageLog.objects.create(
            user_id=user_id,
            session_id=session_id,
            message_id=message_id,
            model=model,
            model_version=model_version,
            request_type=request_type,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=Decimal(str(cost_usd)),
            latency_ms=latency_ms,
            cached=cached,
            cache_id=cache_id,
            metadata=metadata
        )

    def _record_metrics(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        latency_ms: int,
        cached: bool
    ):
        """Prometheus 메트릭 기록"""
        try:
            from ..metrics import (
                record_token_usage,
                record_cost,
                record_cost_saved,
                record_cache_operation
            )

            # 토큰 사용량
            record_token_usage(input_tokens, output_tokens, model)

            # 비용
            record_cost(cost, model, cached)

            # 캐시 히트 시 절감 비용
            if cached:
                estimated_cost = self.calculate_cost(model, input_tokens, output_tokens)
                record_cost_saved(estimated_cost)
                record_cache_operation('check', 'hit')
            else:
                record_cache_operation('check', 'miss')

        except ImportError:
            pass  # 메트릭 모듈 없으면 무시

    async def check_budget(
        self,
        user_id: int,
        estimated_cost: float
    ) -> Dict[str, Any]:
        """
        예산 확인

        Args:
            user_id: 사용자 ID
            estimated_cost: 예상 비용

        Returns:
            {
                'allowed': bool,
                'reason': str | None,
                'daily_used': float,
                'daily_limit': float,
                'monthly_used': float,
                'monthly_limit': float
            }
        """
        daily_used = await self._get_daily_cost(user_id)
        monthly_used = await self._get_monthly_cost(user_id)

        result = {
            'allowed': True,
            'reason': None,
            'daily_used': daily_used,
            'daily_limit': self.daily_limit,
            'monthly_used': monthly_used,
            'monthly_limit': self.monthly_limit,
        }

        # 일일 한도 확인
        if daily_used + estimated_cost > self.daily_limit:
            result['allowed'] = False
            result['reason'] = f'일일 예산 초과 (${daily_used:.4f} / ${self.daily_limit:.2f})'
            return result

        # 월간 한도 확인
        if monthly_used + estimated_cost > self.monthly_limit:
            result['allowed'] = False
            result['reason'] = f'월간 예산 초과 (${monthly_used:.4f} / ${self.monthly_limit:.2f})'
            return result

        return result

    @sync_to_async
    def _get_daily_cost(self, user_id: int) -> float:
        """일일 사용 비용 조회"""
        from ..models import UsageLog
        from django.contrib.auth import get_user_model

        User = get_user_model()
        try:
            user = User.objects.get(pk=user_id)
            return UsageLog.get_user_daily_cost(user)
        except User.DoesNotExist:
            return 0.0

    @sync_to_async
    def _get_monthly_cost(self, user_id: int) -> float:
        """월간 사용 비용 조회"""
        from ..models import UsageLog
        from django.contrib.auth import get_user_model

        User = get_user_model()
        try:
            user = User.objects.get(pk=user_id)
            return UsageLog.get_user_monthly_cost(user)
        except User.DoesNotExist:
            return 0.0

    async def get_usage_summary(
        self,
        user_id: Optional[int] = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        사용량 요약 조회

        Args:
            user_id: 사용자 ID (None이면 전체)
            hours: 조회 기간 (시간)

        Returns:
            사용량 통계
        """
        return await self._get_usage_stats(user_id, hours)

    @sync_to_async
    def _get_usage_stats(
        self,
        user_id: Optional[int],
        hours: int
    ) -> Dict[str, Any]:
        """사용량 통계 조회 (sync)"""
        from ..models import UsageLog
        from django.contrib.auth import get_user_model

        User = get_user_model()

        if user_id:
            try:
                user = User.objects.get(pk=user_id)
                return UsageLog.get_usage_stats(user, hours)
            except User.DoesNotExist:
                return {'error': 'user_not_found'}
        else:
            return UsageLog.get_usage_stats(None, hours)

    def estimate_cost(
        self,
        model: str,
        prompt_length: int,
        max_tokens: int
    ) -> float:
        """
        예상 비용 추정

        Args:
            model: 모델명
            prompt_length: 프롬프트 길이 (문자)
            max_tokens: 최대 출력 토큰

        Returns:
            예상 비용 (USD)
        """
        # 대략적인 토큰 추정 (4자 = 1토큰)
        estimated_input = prompt_length // 4
        estimated_output = max_tokens // 2  # 보수적 추정

        return self.calculate_cost(model, estimated_input, estimated_output)


# 싱글톤 인스턴스
_cost_tracker_instance: Optional[CostTracker] = None


def get_cost_tracker() -> CostTracker:
    """CostTracker 싱글톤 반환"""
    global _cost_tracker_instance
    if _cost_tracker_instance is None:
        _cost_tracker_instance = CostTracker()
    return _cost_tracker_instance

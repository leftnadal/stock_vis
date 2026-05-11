"""
Thesis snapshot AI 요약 생성 task (audit P0 #15).

ThesisSnapshot.ai_summary가 빈 문자열이면 Frontend AISummarySection이 렌더되지 않음.
본 task는 EOD pipeline 직후 (또는 사용자 요청 시) 빈 요약을 채운다.

Gemini 2.5 Flash 동기 호출 (Bug #8 회피).
멱등: 이미 ai_summary가 있는 snapshot은 skip (force=True 시 재생성).

Schedule 권장:
    create_snapshots_and_alerts 직후 (NY 18:35 평일).
    또는 별도 Beat 등록 (NY 18:45 평일, 5분 버퍼).
"""
from __future__ import annotations

import logging
from datetime import date as date_cls
from typing import Any

from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """당신은 투자 가설 모니터링 요약 작성자입니다.

규칙:
1. 한국어로 1~2문장 요약 (80~200자).
2. 제공된 점수와 상태에 기반하여 사실만 기술.
3. 종목 추천, 가격 예측, 정치 코멘트 금지.
4. 응답은 평문 텍스트만. 마크다운 / JSON / 인용 부호 금지.
"""


def _build_user_prompt(thesis, snapshot) -> str:
    parts = [
        f'가설: "{thesis.title}"',
        f'방향: {thesis.direction} / 상태: {snapshot.state}',
        f'전체 점수: {snapshot.overall_score:.1f}',
    ]
    if snapshot.data_coverage < 0.6:
        parts.append(f'(데이터 coverage: {snapshot.data_coverage:.0%}, 낮음)')
    if snapshot.notable_changes:
        notable = ', '.join(
            f"{c.get('label', '?')}({c.get('delta', 0):+.2f})"
            for c in snapshot.notable_changes[:3]
        )
        parts.append(f'주요 변화: {notable}')
    parts.append('한 문단으로 한국어 80~200자 요약을 작성하세요.')
    return '\n'.join(parts)


def _generate_via_gemini(prompt: str, *, model: str = 'gemini-2.5-flash') -> str:
    """Gemini 동기 호출 (Bug #8). 실패 시 빈 문자열."""
    api_key = (
        getattr(settings, 'GOOGLE_AI_API_KEY', None)
        or getattr(settings, 'GEMINI_API_KEY', None)
    )
    if not api_key:
        logger.warning('GEMINI_API_KEY not configured — skipping AI summary')
        return ''
    try:
        import google.generativeai as genai_module
        client = genai_module.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=[{'role': 'user', 'parts': [prompt]}],
            config={'system_instruction': SYSTEM_PROMPT},
        )
        text = (getattr(response, 'text', '') or '').strip()
        return text[:500]
    except Exception as exc:  # noqa: BLE001
        logger.exception('Gemini summary generation failed: %s', exc)
        return ''


@shared_task(
    bind=True,
    name='thesis.tasks.summary.generate_thesis_summaries',
    max_retries=2,
    default_retry_delay=300,
    soft_time_limit=300,
    time_limit=420,
)
def generate_thesis_summaries(
    self,
    *,
    target_date: str | None = None,
    force: bool = False,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    오늘 자(또는 target_date) ThesisSnapshot에 ai_summary 채움.

    Args:
        target_date: ISO 'YYYY-MM-DD'. None이면 today.
        force: True면 ai_summary가 이미 있어도 재생성.

    Returns:
        {'updated': int, 'skipped': int, 'failed': int, 'date': iso}
    """
    from thesis.models import ThesisSnapshot

    if target_date:
        try:
            day = date_cls.fromisoformat(target_date)
        except ValueError:
            day = timezone.localdate()
    else:
        day = timezone.localdate()

    qs = ThesisSnapshot.objects.filter(asof_date=day).select_related('thesis')
    updated = skipped = failed = 0

    for snapshot in qs:
        if snapshot.ai_summary and not force:
            skipped += 1
            continue
        try:
            prompt = _build_user_prompt(snapshot.thesis, snapshot)
            summary = _generate_via_gemini(prompt)
            if not summary:
                failed += 1
                continue
            snapshot.ai_summary = summary
            snapshot.save(update_fields=['ai_summary'])
            updated += 1
        except Exception as exc:  # noqa: BLE001
            logger.exception('thesis %s summary failed: %s', snapshot.thesis_id, exc)
            failed += 1

    summary = {
        'updated': updated,
        'skipped': skipped,
        'failed': failed,
        'date': day.isoformat(),
        'force': force,
    }
    logger.info('generate_thesis_summaries: %s', summary)
    return summary

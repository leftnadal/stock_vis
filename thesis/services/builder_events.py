"""Builder Events: 구조화된 이벤트 로깅 (Phase A-MVP)"""

import json
import logging

from django.utils import timezone

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Event Catalog
# ──────────────────────────────────────────────
EVENT_BUILDER_STARTED = 'builder_started'
EVENT_PROPOSAL_GENERATED = 'proposal_generated'
EVENT_LLM_PARSE_FAILED = 'llm_parse_failed'
EVENT_FALLBACK_TRIGGERED = 'fallback_triggered'
EVENT_PRESET_SELECTED = 'preset_selected'
EVENT_CONFIRM_CLICKED = 'confirm_clicked'
EVENT_THESIS_CREATED = 'thesis_created'


def log_event(name, data=None):
    """구조화된 JSON 이벤트 로그."""
    event = {
        'event': name,
        'timestamp': timezone.now().isoformat(),
        'data': data or {},
    }
    logger.info(json.dumps(event, ensure_ascii=False))

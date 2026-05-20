"""security audit P0 #1 (2026-05-19) — Celery async LLM 호출 회귀 방지.

common-bugs #8: Celery 워커(macOS fork + Obj-C)에서 asyncio.run_until_complete
사용 시 SIGSEGV/좀비 워커 위험. keyword_generator.generate_keywords_sync는
동기 API만 사용해야 한다.
"""
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from serverless.services import keyword_generator as kg


def test_module_does_not_import_asyncio():
    """asyncio import 자체가 제거됐는지 확인 (run_until_complete 경로 차단)."""
    assert not hasattr(kg, 'asyncio'), (
        'keyword_generator.py는 asyncio를 import하면 안 됨 '
        '(common-bugs #8 — Celery 워커 SIGSEGV 위험).'
    )


def test_service_has_sync_methods():
    """동기 호출 경로가 노출됐는지 확인."""
    cls = kg.KeywordGeneratorService
    assert hasattr(cls, '_call_llm_sync')
    assert hasattr(cls, 'generate_keywords_for_movers_sync')


@pytest.mark.django_db
def test_generate_keywords_sync_uses_sync_api_only():
    """generate_keywords_sync 호출 경로에 비동기 API(aio.*) 사용 없음."""
    with patch.object(kg.KeywordGeneratorService, '__init__', return_value=None) as _init, \
         patch.object(
             kg.KeywordGeneratorService,
             'generate_keywords_for_movers_sync',
             return_value=[{'symbol': 'AAPL', 'keywords': [], 'summary': ''}],
         ) as mock_sync:
        result = kg.generate_keywords_sync(
            mover_date=date(2026, 5, 19),
            mover_type='gainers',
            language='ko',
            max_stocks=5,
        )
    assert result == [{'symbol': 'AAPL', 'keywords': [], 'summary': ''}]
    mock_sync.assert_called_once_with(
        mover_date=date(2026, 5, 19),
        mover_type='gainers',
        max_stocks=5,
    )


@pytest.mark.django_db
def test_call_llm_sync_uses_non_aio_endpoint():
    """_call_llm_sync는 client.models.generate_content(동기) 사용."""
    with patch.object(kg.KeywordGeneratorService, '__init__', return_value=None):
        svc = kg.KeywordGeneratorService()
        svc.MODEL = 'gemini-2.5-flash'
        svc.MAX_TOKENS = 100
        svc.TEMPERATURE = 0.3
        svc.prompt_builder = MagicMock()
        svc.prompt_builder.get_system_prompt.return_value = 'sys'
        svc.client = MagicMock()
        response = MagicMock()
        response.text = 'ok'
        svc.client.models.generate_content.return_value = response

        out = svc._call_llm_sync('user prompt')

    assert out == 'ok'
    svc.client.models.generate_content.assert_called_once()
    # 비동기 경로(aio.models)는 사용하지 않아야 함
    svc.client.aio.models.generate_content.assert_not_called()

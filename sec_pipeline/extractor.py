"""
Gemini Flash 추출기.

Track A — supply chain 관계 추출 (Phase 1)
Track B — business model 분류 (Phase 2)
"""

import json
import logging

from django.conf import settings

from .prompts import BUSINESS_MODEL_EXTRACTION_PROMPT, SUPPLY_CHAIN_EXTRACTION_PROMPT

logger = logging.getLogger(__name__)


class GeminiExtractor:
    """Gemini 2.5 Flash 기반 관계 추출기."""

    def __init__(self):
        self._client = None

    def _get_client(self):
        """Lazy initialization (Celery fork 안전)."""
        if self._client is None:
            from google import genai

            api_key = getattr(settings, "GEMINI_API_KEY", None)
            if not api_key:
                raise ValueError("GEMINI_API_KEY not configured")
            self._client = genai.Client(api_key=api_key)
        return self._client

    def extract_supply_chain(
        self, symbol: str, company_name: str, filtered_paragraphs: list
    ) -> dict:
        """
        Track A: supply chain 관계 추출.

        Args:
            symbol: 종목 심볼
            company_name: 회사명
            filtered_paragraphs: Pass 1에서 필터링된 단락 리스트

        Returns:
            {'relationships': [...]} 또는 {'relationships': [], 'error': str}
        """
        if not filtered_paragraphs:
            return {"relationships": []}

        paragraphs_text = "\n\n---\n\n".join(filtered_paragraphs)

        prompt = SUPPLY_CHAIN_EXTRACTION_PROMPT.format(
            symbol=symbol,
            company_name=company_name,
            paragraphs=paragraphs_text,
        )

        try:
            from google.genai import types

            client = self._get_client()
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            )

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=config,
            )

            text = (
                response.text if hasattr(response, "text") and response.text else "{}"
            )
            result = json.loads(text)

            if "relationships" not in result:
                result = {"relationships": []}

            logger.info(
                f"{symbol}: extracted {len(result['relationships'])} "
                f"supply chain relationships"
            )
            return result

        except json.JSONDecodeError as e:
            logger.error(f"{symbol}: JSON parse error: {e}")
            return {"relationships": [], "error": f"JSON parse: {e}"}
        except Exception as e:
            logger.error(f"{symbol}: Gemini extraction error: {e}")
            raise

    def extract_business_model(
        self, symbol: str, company_name: str, filtered_paragraphs: list
    ) -> dict:
        """
        Track B: business model 5개 필드 분류.

        Returns:
            {
                'direct_customer_contact': {'value': str, 'evidence_text': str, 'confidence': float},
                'contract_model': {...},
                'recurring_revenue_signal': {...},
                'channel_dependency': {...},
                'customer_concentration': {...},
            }
        """
        if not filtered_paragraphs:
            return {}

        paragraphs_text = "\n\n---\n\n".join(filtered_paragraphs)

        prompt = BUSINESS_MODEL_EXTRACTION_PROMPT.format(
            symbol=symbol,
            company_name=company_name,
            paragraphs=paragraphs_text,
        )

        try:
            from google.genai import types

            client = self._get_client()
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            )

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=config,
            )

            text = (
                response.text if hasattr(response, "text") and response.text else "{}"
            )
            result = json.loads(text)

            logger.info(f"{symbol}: extracted business model classification")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"{symbol}: BM JSON parse error: {e}")
            return {"error": f"JSON parse: {e}"}
        except Exception as e:
            logger.error(f"{symbol}: BM Gemini error: {e}")
            raise

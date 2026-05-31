"""
SEC-PR-4: 에러 유형별 재시도 정책.

| 예외                    | retry | backoff |
|------------------------|-------|---------|
| FMPApiError            | 3     | 60s exp |
| SECFetchError          | 5     | 10s exp |
| SectionExtractionError | 1     | fallback |
| LLMExtractionError     | 2     | 30s     |
"""


class FilingCollectionError(Exception):
    """SEC filing 수집 기본 예외."""

    pass


class FMPApiError(FilingCollectionError):
    """FMP API 호출 실패 (메타데이터 조회)."""

    pass


class SECFetchError(FilingCollectionError):
    """SEC EDGAR HTML 다운로드 실패."""

    pass


class SectionExtractionError(FilingCollectionError):
    """섹션 추출 실패 (fallback 시도 후에도 실패)."""

    pass


class LLMExtractionError(FilingCollectionError):
    """Gemini LLM 추출 실패."""

    pass

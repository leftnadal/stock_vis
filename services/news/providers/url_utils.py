"""뉴스 URL 정규화 — provider 공통 단일 소스 (S3).

cross-provider dedup 은 `NewsArticle.url` exact match(+ url_hash)에 의존한다.
provider마다 정규화가 달라(과거: finnhub·marketaux 만 정규화, AV·FMP 는 raw url) 같은
기사가 provider별로 다른 url 로 저장돼 이중 NewsArticle → 이중 NewsEntity → co-mention
가중치 왜곡 위험이 있었다. 정규화 로직을 이 함수 하나로 통일해 **모든 provider 가
동일 규칙**으로 저장하도록 한다.

정규화 규칙(기존 BaseNewsProvider.normalize_url 과 동치, 행위 보존):
    - 앞뒤 공백 제거 + 소문자화
    - 쿼리스트링(? 이후) 전체 제거 (utm_* 등 추적 파라미터 제거)
    - 마지막 슬래시 제거

⚠ forward-only: 이 함수는 **신규 수집분**에만 적용된다. 기존 저장 url(raw)은 건드리지
않으므로, 정규화 도입 직후 재수집되는 일부 기사는 옛 raw row 와 새 normalized row 로
잠시 병존할 수 있다(전환 아티팩트). 기존 중복 backfill 은 별도 결정(TASKQUEUE 후보).
"""

from __future__ import annotations


def normalize_news_url(url: str | None) -> str:
    """뉴스 기사 URL 을 dedup 용으로 정규화한다. None/빈값은 "" 반환."""
    normalized = (url or "").strip().lower()

    # 쿼리 파라미터 제거 (utm_source 등 추적 파라미터로 인한 중복 방지)
    if "?" in normalized:
        normalized = normalized.split("?")[0]

    # 마지막 슬래시 제거
    if normalized.endswith("/"):
        normalized = normalized[:-1]

    return normalized

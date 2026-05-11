"""
SEC-PR-11: Track B 키워드 사전.

5개 비즈니스 모델 필드별 키워드.
"""

import re

BM_KEYWORDS = {
    'direct_customer_contact': [
        'direct sales', 'retail', 'consumer', 'B2C', 'end user',
        'direct-to-consumer', 'online store', 'retail store', 'showroom',
        'direct channel', 'our stores', 'our website',
        'indirect', 'B2B', 'enterprise', 'wholesale',
        'through distributors', 'through resellers',
    ],
    'contract_model': [
        'subscription', 'SaaS', 'recurring', 'license', 'one-time',
        'hardware', 'software license', 'annual contract', 'monthly',
        'per-unit', 'per-seat', 'usage-based', 'consumption-based',
        'perpetual license', 'term license', 'multi-year',
        'project-based', 'milestone', 'fixed-price contract',
    ],
    'recurring_revenue_signal': [
        'ARR', 'MRR', 'recurring', 'retention', 'churn', 'renewal',
        'annual recurring revenue', 'monthly recurring revenue',
        'net revenue retention', 'dollar-based retention',
        'customer lifetime value', 'backlog', 'deferred revenue',
        'subscription revenue', 'maintenance revenue',
    ],
    'channel_dependency': [
        'distribution partner', 'reseller', 'OEM', 'direct',
        'channel', 'value-added reseller', 'VAR', 'system integrator',
        'independent distributor', 'authorized dealer', 'franchise',
        'marketplace', 'platform', 'app store',
        'our own sales force', 'direct sales team',
    ],
    'customer_concentration': [
        # 집중 신호
        'accounted for', 'significant customer', 'major customer',
        'largest customer', 'top customer', 'represented approximately',
        'more than 10%', 'exceeded 10%',
        # 분산 신호
        'no single customer', 'diversified customer base',
        'no material concentration', 'no customer accounted for more than',
        'broad customer base', 'thousands of customers',
        'no individual customer', 'widely diversified',
    ],
}


def filter_paragraphs_track_b(text: str, max_paragraphs: int = 15) -> list:
    """
    Track B 키워드로 관련 단락 필터링.

    Item 1 위주 (비즈니스 모델 서술).
    """
    # 모든 필드의 키워드 합침
    all_keywords = []
    for kw_list in BM_KEYWORDS.values():
        all_keywords.extend(kw_list)

    paragraphs = re.split(r'\n', text)
    paragraphs = [p.strip() for p in paragraphs if len(p.strip()) >= 50]

    scored = []
    seen = set()
    for para in paragraphs:
        lower = para.lower()
        hits = sum(1 for kw in all_keywords if kw.lower() in lower)
        if hits > 0:
            key = para[:200]
            if key not in seen:
                seen.add(key)
                scored.append((hits, para))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [para for _, para in scored[:max_paragraphs]]

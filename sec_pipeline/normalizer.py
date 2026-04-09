"""
SEC-PR-3: 섹션 텍스트 정규화 + Pass 1 키워드 필터

Track A (Supply Chain) 키워드로 관련 단락만 선별.
"""

import re

# Track A 키워드 — supply chain 관계 추출용
SUPPLY_CHAIN_KEYWORDS = [
    'supplier', 'customer', 'supply chain', 'partnership', 'contract',
    'manufacture', 'distribute', 'compete', 'vendor', 'procurement',
    'outsource', 'subcontract', 'license', 'OEM', 'foundry',
    'sole source', 'single source', 'key supplier', 'major customer',
    'principal supplier', 'third party', 'third-party',
    'distributor', 'wholesaler', 'retailer', 'reseller',
    'raw material', 'component', 'assembly', 'fabricat',
    'joint venture', 'strategic alliance', 'collaboration',
    'competitor', 'competitive', 'market share',
    'depend', 'rely', 'reliance',
]


def normalize_section_all(sections: dict) -> str:
    """추출된 섹션들을 하나의 정제된 텍스트로 합침."""
    parts = []
    for key in ['item_1', 'item_7']:  # Track A는 Item 1 + Item 7
        text = sections.get(key, '')
        if text:
            parts.append(_clean_text(text))
    return '\n\n'.join(parts)


def filter_paragraphs(text: str, track: str = 'supply_chain',
                      max_paragraphs: int = 15) -> list:
    """
    키워드 기반 Pass 1 필터. 관련 단락 상위 N개 반환.

    Args:
        text: 정제된 텍스트
        track: 'supply_chain' (Track A)
        max_paragraphs: 최대 반환 수

    Returns:
        키워드 히트 수 기준 상위 단락 리스트
    """
    keywords = SUPPLY_CHAIN_KEYWORDS

    # 단락 분리 — SEC filing은 단일 줄바꿈(\n)으로 구분되는 경우 많음
    paragraphs = re.split(r'\n', text)
    paragraphs = [p.strip() for p in paragraphs if len(p.strip()) >= 50]

    # 키워드 히트 수 계산
    scored = []
    for para in paragraphs:
        lower = para.lower()
        hits = sum(1 for kw in keywords if kw.lower() in lower)
        if hits > 0:
            scored.append((hits, para))

    # 히트 수 내림차순 정렬 → 중복 제거 → 상위 max_paragraphs개
    scored.sort(key=lambda x: x[0], reverse=True)
    seen = set()
    unique = []
    for _, para in scored:
        key = para[:200]  # 앞 200자 기준 중복 판단
        if key not in seen:
            seen.add(key)
            unique.append(para)
            if len(unique) >= max_paragraphs:
                break
    return unique


def _clean_text(text: str) -> str:
    """HTML 잔여물, 과도한 공백 정리."""
    # HTML 엔티티 정리
    text = re.sub(r'&[a-z]+;', ' ', text)
    text = re.sub(r'&#\d+;', ' ', text)
    # 연속 공백 정리
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

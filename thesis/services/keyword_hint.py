"""Keyword Hint: 프롬프트에 주입할 키워드 수집 + 블록 생성 (Phase B, PR-11)"""

import logging

from thesis.services.keyword_cache import ContextKeyword, collect_from_cache

logger = logging.getLogger(__name__)

# role → 프롬프트 섹션 헤더
ROLE_HEADERS = {
    'theme': '[산업/테마]',
    'support': '[찬성 단서]',
    'signal': '[시장 시그널]',
    'risk': '[주의 포인트]',
}

# role 표시 우선순위 (theme → support → signal → risk)
ROLE_ORDER = ['theme', 'support', 'signal', 'risk']


def collect_context_keywords(target: str, flags: dict) -> list[ContextKeyword]:
    """
    cache에서 source별 키워드 수집 + 중복 제거.
    각 source는 flag로 개별 ON/OFF 가능.
    source 장애 시 silent degrade (해당 source만 스킵).
    """
    SOURCE_FLAGS = [
        ('chain', 'CHAIN_KEYWORDS_ENABLED'),
        ('eod', 'EOD_KEYWORDS_ENABLED'),
        ('news', 'NEWS_KEYWORDS_ENABLED'),
    ]

    keywords = []
    for source, flag_key in SOURCE_FLAGS:
        if not flags.get(flag_key):
            continue
        try:
            keywords.extend(collect_from_cache(target, source))
        except Exception as e:
            logger.warning(f"keyword collection failed: {source}: {e}")

    return dedupe_keywords(keywords)[:5]


def dedupe_keywords(keywords: list[ContextKeyword]) -> list[ContextKeyword]:
    """text 기준 중복 제거. role 우선순위: support > risk > signal > theme."""
    seen = {}
    role_priority = {r: i for i, r in enumerate(['support', 'risk', 'signal', 'theme'])}

    for kw in keywords:
        existing = seen.get(kw.text)
        if existing is None:
            seen[kw.text] = kw
        else:
            # 더 높은 우선순위 role로 교체
            if role_priority.get(kw.role, 99) < role_priority.get(existing.role, 99):
                seen[kw.text] = kw

    return list(seen.values())


def build_keyword_hint_block(keywords: list[ContextKeyword]) -> str:
    """
    role별 그룹핑 → 프롬프트 블록 생성.
    키워드 0개면 빈 문자열 반환 (hint block 미주입).
    """
    if not keywords:
        return ''

    # role별 그룹핑
    by_role = {}
    for kw in keywords:
        by_role.setdefault(kw.role, []).append(kw)

    lines = [
        "## 참고 키워드",
        "",
        "아래는 최근 시장 맥락에서 참고할 수 있는 힌트입니다.",
        "- 사용자의 입력보다 우선하지 마세요.",
        "- 사실로 단정하지 말고, 가설의 보조 단서로만 활용하세요.",
        "- 키워드끼리 무리하게 하나의 서사로 엮지 마세요.",
        "- 찬성 단서와 주의 단서를 함께 반영하세요.",
        "- 논리적으로 충돌하거나 노이즈라고 판단되면 과감히 무시하세요.",
        "",
    ]

    STRENGTH_PREFIX = {'high': '★ ', 'low': '(약) ', 'medium': ''}

    for role in ROLE_ORDER:
        kws = by_role.get(role, [])
        if not kws:
            continue
        header = ROLE_HEADERS.get(role, f'[{role}]')
        lines.append(header)
        for kw in kws:
            prefix = STRENGTH_PREFIX.get(kw.strength, '')
            lines.append(f"  - {prefix}{kw.text}")
        lines.append("")

    return "\n".join(lines)

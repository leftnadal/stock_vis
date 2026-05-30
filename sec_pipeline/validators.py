"""
SEC-PR-2: 섹션 추출 사후 검증

3가지 검증:
1. Item 순서 검증 (1 < 1A < 7) — 위반 시 전체 폐기 (FAIL:)
2. Heading 재확인 — 첫 500자에 heading 없으면 해당 섹션 제거 (FAIL:)
3. 비정상 길이 플래그 — WARN만, 제거 안 함
"""

import logging
import re

logger = logging.getLogger(__name__)

# 길이 기준 (문자 수)
MIN_SECTION_LENGTH = 500
MAX_SECTION_LENGTH = 500_000
EXPECTED_MIN_LENGTH = 2_000


def validate_extracted_sections(sections: dict, full_text: str) -> tuple:
    """
    추출된 섹션 사후 검증.

    Args:
        sections: {'item_1': str, 'item_1a': str, 'item_7': str}
        full_text: 원문 전체 텍스트 (순서 검증용)

    Returns:
        (validated_sections, warnings)
        - warnings: 'FAIL:...' → 치명적, 'WARN:...' → 경고만
    """
    warnings = []
    validated = dict(sections)

    # ── Check 1: Item 순서 검증 ──
    # 원문에서 각 Item 헤딩의 첫 출현 위치 확인
    order_fail = _check_item_order(full_text)
    if order_fail:
        warnings.append(f'FAIL: {order_fail}')
        # 전체 폐기
        return {'item_1': '', 'item_1a': '', 'item_7': ''}, warnings

    # ── Check 2: Heading 재확인 ──
    heading_patterns = {
        'item_1': [
            r'(?i)(?:Item\s*1[\.\s:\-—]|Description\s+of\s+Business|Business\s+Overview)',
        ],
        'item_1a': [
            r'(?i)(?:Item\s*1A[\.\s:\-—]|Risk\s+Factors)',
        ],
        'item_7': [
            r'(?i)(?:Item\s*7[\.\s:\-—]|Management.s?\s+Discussion|MD\s*&\s*A)',
        ],
    }
    for key in ['item_1', 'item_1a', 'item_7']:
        text = validated.get(key, '')
        if not text:
            continue
        first_500 = text[:500]
        has_heading = any(
            re.search(pat, first_500) for pat in heading_patterns[key]
        )
        if not has_heading:
            # heading 없음 → 잘못 추출 가능성 높음
            warnings.append(f'FAIL: {key} heading not found in first 500 chars')
            validated[key] = ''

    # ── Check 3: 비정상 길이 플래그 ──
    for key in ['item_1', 'item_1a', 'item_7']:
        text = validated.get(key, '')
        if not text:
            continue
        length = len(text)
        if length < MIN_SECTION_LENGTH:
            warnings.append(
                f'WARN: {key} too short ({length} chars < {MIN_SECTION_LENGTH})'
            )
        elif length > MAX_SECTION_LENGTH:
            warnings.append(
                f'WARN: {key} unusually long ({length} chars > {MAX_SECTION_LENGTH})'
            )
        elif length < EXPECTED_MIN_LENGTH:
            warnings.append(
                f'WARN: {key} shorter than expected ({length} chars < {EXPECTED_MIN_LENGTH})'
            )

    return validated, warnings


def _check_item_order(full_text: str) -> str:
    """
    원문에서 Item 1, 1A, 7, 8 순서가 맞는지 확인.

    Returns:
        에러 메시지 (순서 위반 시) 또는 빈 문자열 (정상)
    """
    item_positions = {}
    order_patterns = {
        'item_1': r'(?i)(?:Item|ITEM)\s*1\b(?!\d|A)',
        'item_1a': r'(?i)(?:Item|ITEM)\s*1A\b',
        'item_7': r'(?i)(?:Item|ITEM)\s*7\b(?!\d|A)',
        'item_8': r'(?i)(?:Item|ITEM)\s*8\b',
    }

    for key, pat in order_patterns.items():
        match = re.search(pat, full_text)
        if match:
            item_positions[key] = match.start()

    # 최소 item_1, item_7은 있어야 함
    if 'item_1' not in item_positions or 'item_7' not in item_positions:
        return ''  # 위치 확인 불가 → 순서 검증 스킵

    # 순서 검증: 1 < 1A < 7 < 8
    expected_order = ['item_1', 'item_1a', 'item_7', 'item_8']
    present = [(k, item_positions[k]) for k in expected_order if k in item_positions]

    for i in range(len(present) - 1):
        curr_key, curr_pos = present[i]
        next_key, next_pos = present[i + 1]
        if curr_pos >= next_pos:
            return (
                f'Item order violation: {curr_key}(pos={curr_pos}) '
                f'>= {next_key}(pos={next_pos})'
            )

    return ''

/**
 * formatMemberTitle (⑳-2 S4) — 티커 병기·대문자·4개 초과 "외 N".
 */
import { describe, it, expect } from 'vitest';
import { formatMemberTitle } from '@/components/chainsight/eventBoardTitle';

describe('formatMemberTitle', () => {
  it('대문자 · 병기', () => {
    expect(formatMemberTitle(['lrcx', 'klac', 'ter'])).toBe('LRCX · KLAC · TER');
  });

  it('4개 이하는 전부 표기', () => {
    expect(formatMemberTitle(['a', 'b', 'c', 'd'])).toBe('A · B · C · D');
  });

  it('4개 초과는 상위 4 + "외 N"', () => {
    expect(formatMemberTitle(['a', 'b', 'c', 'd', 'e', 'f'])).toBe('A · B · C · D 외 2');
  });

  it('빈/undefined → 빈 문자열(폴백 유도)', () => {
    expect(formatMemberTitle([])).toBe('');
    expect(formatMemberTitle(undefined)).toBe('');
  });
});

import { describe, it, expect } from 'vitest';
import {
  INDUSTRY_LABELS,
  getLabelForIndustry,
  getLabelForSector,
} from '@/constants/categoryMap';

describe('categoryMap — industry 한글 라벨 (부록 A 137건)', () => {
  it('INDUSTRY_LABELS = 137건', () => {
    expect(Object.keys(INDUSTRY_LABELS)).toHaveLength(137);
  });

  it('알려진 industry는 한글 반환', () => {
    expect(getLabelForIndustry('Semiconductors')).toBe('반도체');
    expect(getLabelForIndustry('Biotechnology')).toBe('바이오');
    expect(getLabelForIndustry('Banks - Regional')).toBe('은행 - 지역');
    expect(getLabelForIndustry('Aerospace & Defense')).toBe('항공우주·방위');
  });

  it('미매핑(신규 유입) industry는 영문 원문 fallback(빈 값 금지)', () => {
    expect(getLabelForIndustry('Totally New Industry')).toBe('Totally New Industry');
    expect(getLabelForIndustry('')).toBe('');
  });

  it('대문자 변형 5건 = 정규 표기와 동일 한글(정규화 착지 전 fallback 안전망)', () => {
    const pairs: [string, string][] = [
      ['AUTO MANUFACTURERS', 'Auto - Manufacturers'],
      ['CAPITAL MARKETS', 'Financial - Capital Markets'],
      ['CONSUMER ELECTRONICS', 'Consumer Electronics'],
      ['SEMICONDUCTORS', 'Semiconductors'],
      ['UTILITIES - INDEPENDENT POWER PRODUCERS', 'Independent Power Producers'],
    ];
    for (const [variant, canon] of pairs) {
      expect(getLabelForIndustry(variant)).toBe(getLabelForIndustry(canon));
    }
  });

  it('sector 라벨 회귀(R1 C-3)', () => {
    expect(getLabelForSector('Financial Services')).toBe('금융');
    expect(getLabelForSector('미분류')).toBe('미분류');
    expect(getLabelForSector('Unknown Sector')).toBe('Unknown Sector');
  });
});

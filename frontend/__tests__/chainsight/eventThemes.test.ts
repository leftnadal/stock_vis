import { describe, it, expect } from 'vitest';
import { THEME_LABELS, getLabelForTheme } from '@/constants/eventThemes';

describe('THEME_LABELS', () => {
  it('알려진 테마 semiconductor → 한글 라벨 반환', () => {
    const entry = THEME_LABELS['semiconductor'];
    expect(entry).toBeDefined();
    expect(entry.ko).toBe('반도체');
    expect(typeof entry.icon).toBe('string');
  });

  it('모든 항목이 ko(문자열)와 icon(문자열)을 가진다', () => {
    for (const [key, value] of Object.entries(THEME_LABELS)) {
      expect(typeof value.ko, `${key}.ko should be string`).toBe('string');
      expect(typeof value.icon, `${key}.icon should be string`).toBe('string');
      expect(value.ko.length, `${key}.ko should not be empty`).toBeGreaterThan(0);
      expect(value.icon.length, `${key}.icon should not be empty`).toBeGreaterThan(0);
    }
  });
});

describe('getLabelForTheme', () => {
  it('알려진 테마는 매핑된 라벨을 반환한다', () => {
    const result = getLabelForTheme('semiconductor');
    expect(result.ko).toBe('반도체');
  });

  it('미매핑 테마는 theme 문자열 자체를 ko로 반환한다', () => {
    const result = getLabelForTheme('unknown_future_theme');
    expect(result.ko).toBe('unknown_future_theme');
  });

  it('미매핑 테마의 icon은 문자열이다', () => {
    const result = getLabelForTheme('some_new_theme_xyz');
    expect(typeof result.icon).toBe('string');
    expect(result.icon.length).toBeGreaterThan(0);
  });

  it('빈 문자열 theme도 폴백 처리된다', () => {
    const result = getLabelForTheme('');
    expect(typeof result.ko).toBe('string');
    expect(typeof result.icon).toBe('string');
  });

  it('robotics_ai 매핑 확인', () => {
    const result = getLabelForTheme('robotics_ai');
    expect(result.ko).toBe('AI·로보틱스');
  });
});

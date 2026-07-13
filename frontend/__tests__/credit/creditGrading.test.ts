import { describe, it, expect } from 'vitest';

import { bandCaption, CREDIT_GRADING } from '@/lib/credit/creditGrading';

describe('bandCaption — 백엔드 grade_from_z 규칙 도출', () => {
  it('상수는 백엔드 소스 미러 (Z_YELLOW=1, Z_ORANGE=2, HY 800bp)', () => {
    expect(CREDIT_GRADING.Z_YELLOW).toBe(1.0);
    expect(CREDIT_GRADING.Z_ORANGE).toBe(2.0);
    expect(CREDIT_GRADING.HY_CRISIS_BP).toBe(800);
    expect(CREDIT_GRADING.RED_SIGNAL).toBe('HY_OAS');
  });

  it('signed z 하방 미발화(음수 포함) · orange 무상한 — 공통', () => {
    const cap = bandCaption('IG_OAS');
    expect(cap).toContain('gray z<1(음수 포함)'); // |z| 아님 = 하방 미발화
    expect(cap).toContain('orange z≥2'); // 상한 표기 없음(무상한)
    expect(cap).not.toContain('2–3'); // 옛 상한 문구 제거
    expect(cap).not.toContain('|z|');
  });

  it('비-HY 신호는 red 없음 (red는 HY 한정)', () => {
    for (const k of ['IG_OAS', 'BBB_OAS', 'CCC_OAS', 'CURVE_10Y2Y', 'VIX']) {
      expect(bandCaption(k)).not.toContain('red');
    }
  });

  it('HY_OAS만 red = 절대 레벨 기준(z≥2 & 값≥8.0%(800bp))', () => {
    const hy = bandCaption('HY_OAS');
    expect(hy).toContain('red z≥2 & 값≥8.0%(800bp)');
    // z 기반 red(≥3)가 아니라 절대값 기준임이 드러남
    expect(hy).not.toContain('red ≥3');
  });
});

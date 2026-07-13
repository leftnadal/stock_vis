import { describe, it, expect } from 'vitest';

import {
  deriveHeadline,
  worstGrade,
  sparkDirection,
  signalStateLine,
  buildChipInfo,
  GRADE_BAND_TEXT,
} from '@/lib/credit/creditMeaning';
import type { CreditSignal } from '@/services/creditSignalsService';
import type { Grade } from '@/components/common/colorSemantics';

function sig(key: string, grade: Grade, over: Partial<CreditSignal> = {}): CreditSignal {
  const names: Record<string, string> = {
    HY_OAS: 'US HY OAS',
    IG_OAS: 'US IG OAS',
    BBB_OAS: 'BBB OAS',
    CCC_OAS: 'CCC- OAS',
    CURVE_10Y2Y: '10Y-2Y',
    VIX: 'VIX Close',
  };
  return {
    key,
    name: names[key] ?? key,
    value: 1,
    z: grade === 'gray' ? 0.2 : 1.5,
    grade,
    spark: [
      { date: 'a', value: 1 },
      { date: 'b', value: 1.2 },
    ],
    ...over,
  };
}

const SIX_GRAY = [
  sig('HY_OAS', 'gray'),
  sig('IG_OAS', 'gray'),
  sig('BBB_OAS', 'gray'),
  sig('CCC_OAS', 'gray'),
  sig('CURVE_10Y2Y', 'gray'),
  sig('VIX', 'gray'),
];

function withGrades(map: Partial<Record<string, Grade>>): CreditSignal[] {
  return SIX_GRAY.map((s) => (map[s.key] ? sig(s.key, map[s.key]!) : s));
}

describe('worstGrade', () => {
  it('최악 grade 반환 (red > orange > yellow > gray)', () => {
    expect(worstGrade(SIX_GRAY)).toBe('gray');
    expect(worstGrade(withGrades({ CCC_OAS: 'yellow', HY_OAS: 'orange' }))).toBe('orange');
    expect(worstGrade(withGrades({ HY_OAS: 'red' }))).toBe('red');
  });
});

describe('deriveHeadline 패턴 매칭 (초기 6건)', () => {
  it('① 전부 gray → 안정 문장 + grade gray', () => {
    const h = deriveHeadline(SIX_GRAY);
    expect(h.text).toBe('크레딧 전반 안정 — 특이 신호 없음');
    expect(h.grade).toBe('gray');
  });

  it('② CCC 단독 → HY 내부 분화', () => {
    const h = deriveHeadline(withGrades({ CCC_OAS: 'yellow' }));
    expect(h.text).toBe('HY 내부 분화 — CCC 스프레드 단독 상승');
    expect(h.grade).toBe('yellow');
  });

  it('③ HY + CCC 동반 → 광범위 확대 (최악 grade)', () => {
    const h = deriveHeadline(withGrades({ HY_OAS: 'yellow', CCC_OAS: 'orange' }));
    expect(h.text).toBe('광범위 신용 확대 — HY·CCC 동반 상승');
    expect(h.grade).toBe('orange');
  });

  it('④ CURVE 단독 → 금리 축', () => {
    const h = deriveHeadline(withGrades({ CURVE_10Y2Y: 'yellow' }));
    expect(h.text).toBe('금리 곡선 축 신호 — 10Y-2Y 이례적');
  });

  it('⑤ VIX 단독 → 변동성 축', () => {
    const h = deriveHeadline(withGrades({ VIX: 'orange' }));
    expect(h.text).toBe('변동성 축 신호 — VIX 이례적');
  });

  it('⑥ 기타 조합 → 중립 폴백 "관찰 n건" + 심각도순 나열', () => {
    const h = deriveHeadline(withGrades({ IG_OAS: 'yellow', BBB_OAS: 'orange' }));
    // 심각도순: orange(BBB) 먼저, yellow(IG) 나중
    expect(h.text).toBe('관찰 2건 — BBB OAS, US IG OAS');
    expect(h.grade).toBe('orange');
  });
});

describe('sparkDirection', () => {
  it('상승/하락/횡보 판정', () => {
    expect(sparkDirection([1, 1.5])).toBe('상승');
    expect(sparkDirection([2, 1])).toBe('하락');
    expect(sparkDirection([1, 1.001])).toBe('횡보');
    expect(sparkDirection([1])).toBe('횡보'); // 결손
  });
});

describe('signalStateLine + buildChipInfo', () => {
  it('값·z·30일 방향 템플릿', () => {
    const s = sig('HY_OAS', 'gray', {
      value: 2.7,
      z: -1.08,
      spark: [
        { date: 'a', value: 2.8 },
        { date: 'b', value: 2.7 },
      ],
    });
    expect(signalStateLine(s)).toBe('현재 2.70 · z -1.08 · 최근 30일 하락');
  });

  it('콜드스타트(z=null) 표기', () => {
    const s = sig('VIX', 'gray', { value: 16.9, z: null, spark: [] });
    expect(signalStateLine(s)).toBe('현재 16.90 · 콜드스타트(관측 부족)');
  });

  it('buildChipInfo = 정의 + 상태 + 고정 밴드', () => {
    const info = buildChipInfo(sig('CCC_OAS', 'yellow', { value: 9.75, z: 1.11 }));
    expect(info.def).toContain('최저신용');
    expect(info.state).toContain('현재 9.75');
    expect(info.band).toBe(GRADE_BAND_TEXT);
    expect(info.band).toBe('gray |z|<1 · yellow 1–2 · orange 2–3 · red ≥3');
  });
});

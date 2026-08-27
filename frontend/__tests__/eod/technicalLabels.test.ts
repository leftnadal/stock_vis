import { describe, it, expect } from 'vitest';
import {
  RSI_STATE_LABEL,
  MA_STATE_LABEL,
  formatDist52wHigh,
  formatRsi,
  formatMaState,
  buildTechnicalDetail,
} from '@/components/eod/technicalLabels';
import type { TechnicalBlock } from '@/types/eod';

describe('enum → 표시어 맵 (D-SCAN-B2TECH-CONTRACT · 정칙 ⑵)', () => {
  it('rsi_state 전수', () => {
    expect(RSI_STATE_LABEL).toEqual({ oversold: '과매도', overbought: '과매수', neutral: '중립' });
  });
  it('ma_state 전수', () => {
    expect(MA_STATE_LABEL).toEqual({
      golden_cross: '골든크로스', dead_cross: '데드크로스', above: '정배열', below: '역배열',
    });
  });
  it('매매 지시어 미포함 — 정칙 ⑵ (과매수/과매도 상태어는 허용)', () => {
    const all = [...Object.values(RSI_STATE_LABEL), ...Object.values(MA_STATE_LABEL)].join(' ');
    // '과매수'의 '매수'는 상태 서술 → 제외. 단독 매수/매도 지시어·buy/sell만 금지.
    expect(all).not.toMatch(/(?<!과)매수|(?<!과)매도|buy|sell/i);
  });
});

describe('formatDist52wHigh — dist 표시 변환', () => {
  it('98.1 → "52주 고점 −1.9%"', () => {
    expect(formatDist52wHigh(98.1)).toBe('52주 고점 −1.9%');
  });
  it('90 → "52주 고점 −10.0%"', () => {
    expect(formatDist52wHigh(90)).toBe('52주 고점 −10.0%');
  });
  it('100 → "52주 신고가"', () => {
    expect(formatDist52wHigh(100)).toBe('52주 신고가');
  });
  it('100 초과(신고가 갱신) → "52주 신고가"', () => {
    expect(formatDist52wHigh(100.3)).toBe('52주 신고가');
  });
  it('undefined → null(정칙 ⑴)', () => {
    expect(formatDist52wHigh(undefined)).toBeNull();
  });
});

describe('formatRsi / formatMaState', () => {
  it('RSI 값+상태어', () => {
    expect(formatRsi({ rsi: 72, rsi_state: 'overbought' })).toBe('RSI 72 · 과매수');
    expect(formatRsi({ rsi: 25.4, rsi_state: 'oversold' })).toBe('RSI 25.4 · 과매도');
  });
  it('RSI 결측(값 또는 상태 부재) → null', () => {
    expect(formatRsi({ rsi: 50 })).toBeNull();
    expect(formatRsi({ rsi_state: 'neutral' })).toBeNull();
    expect(formatRsi(undefined)).toBeNull();
  });
  it('MA 상태어 / 결측 null', () => {
    expect(formatMaState({ ma_state: 'golden_cross' })).toBe('골든크로스');
    expect(formatMaState({})).toBeNull();
    expect(formatMaState(undefined)).toBeNull();
  });
});

describe('buildTechnicalDetail — 4값 전체(present만·순서 RSI·52주·MA)', () => {
  it('전체 present', () => {
    const t: TechnicalBlock = { rsi: 72, rsi_state: 'overbought', dist_52w_high_pct: 98.1, ma_state: 'above' };
    expect(buildTechnicalDetail(t)).toEqual(['RSI 72 · 과매수', '52주 고점 −1.9%', '정배열']);
  });
  it('부분 결측 → present만(정칙 ⑴)', () => {
    expect(buildTechnicalDetail({ ma_state: 'dead_cross' })).toEqual(['데드크로스']);
    expect(buildTechnicalDetail({ rsi: 55, rsi_state: 'neutral' })).toEqual(['RSI 55 · 중립']);
  });
  it('전건 결측/undefined → 빈 배열', () => {
    expect(buildTechnicalDetail({})).toEqual([]);
    expect(buildTechnicalDetail(undefined)).toEqual([]);
  });
});

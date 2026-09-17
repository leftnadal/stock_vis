import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import {
  DataFreshnessBadge,
  countMissedBakeSlots,
  formatTradingDate,
  MISSED_SLOT_WARN_THRESHOLD,
} from '@/components/eod/DataFreshnessBadge';

// 2026-09 = EDT(UTC-4). bake 슬롯 = ET 평일 18:30.
const FRI = '2026-09-11';
const MON = '2026-09-14';

describe('countMissedBakeSlots', () => {
  it('금요일 거래일 + 일요일(ET) 접속 = 0 — 주말에는 결번이 없다', () => {
    expect(countMissedBakeSlots(FRI, new Date('2026-09-14T01:00:00Z'))).toBe(0);
  });

  it('금요일 거래일 + 월요일 ET 18:30 이전 접속 = 0 — 아직 슬롯이 오지 않았다', () => {
    expect(countMissedBakeSlots(FRI, new Date('2026-09-14T14:00:00Z'))).toBe(0);
  });

  it('월요일 슬롯 경과 직후 = 1 — 경고 임계 미만', () => {
    const missed = countMissedBakeSlots(FRI, new Date('2026-09-15T00:00:00Z'));
    expect(missed).toBe(1);
    expect(missed).toBeLessThan(MISSED_SLOT_WARN_THRESHOLD);
  });

  it('수요일까지 금요일 데이터면 3회 결번 — 경고 임계 이상', () => {
    const missed = countMissedBakeSlots(FRI, new Date('2026-09-16T23:00:00Z'));
    expect(missed).toBe(3);
    expect(missed).toBeGreaterThanOrEqual(MISSED_SLOT_WARN_THRESHOLD);
  });

  it('당일 슬롯으로 구운 데이터 = 0', () => {
    expect(countMissedBakeSlots(MON, new Date('2026-09-15T00:13:00Z'))).toBe(0);
  });

  it('거래일 문자열이 깨져도 0을 돌려 경고를 켜지 않는다', () => {
    expect(countMissedBakeSlots('not-a-date', new Date('2026-09-16T23:00:00Z'))).toBe(0);
  });
});

describe('formatTradingDate', () => {
  it('요일을 붙인다', () => {
    expect(formatTradingDate(MON)).toBe('2026년 09월 14일(월)');
    expect(formatTradingDate(FRI)).toBe('2026년 09월 11일(금)');
  });
});

describe('DataFreshnessBadge', () => {
  const generatedAt = '2026-09-14T22:30:56.630909+00:00';

  it('baker가 is_stale=true여도 제목을 대체하지 않는다 (stale 이분법 폐기)', () => {
    render(
      <DataFreshnessBadge
        tradingDate={MON}
        generatedAt={generatedAt}
        isStale
        now={new Date('2026-09-15T00:13:00Z')}
      />,
    );
    expect(screen.getByRole('heading', { name: '오늘의 시그널' })).toBeInTheDocument();
    expect(screen.queryByText('어제 데이터입니다')).not.toBeInTheDocument();
  });

  it('거래일·요일·생성시각을 사실로 서술한다', () => {
    render(
      <DataFreshnessBadge
        tradingDate={MON}
        generatedAt={generatedAt}
        now={new Date('2026-09-15T00:13:00Z')}
      />,
    );
    expect(screen.getByText('2026년 09월 14일(월) 장 마감 기준')).toBeInTheDocument();
    expect(screen.getByText(/생성$/)).toBeInTheDocument();
  });

  it('금요일 데이터 + 월요일 접속에 경고를 켜지 않는다', () => {
    render(
      <DataFreshnessBadge
        tradingDate={FRI}
        generatedAt="2026-09-11T22:30:00+00:00"
        isStale
        now={new Date('2026-09-14T01:00:00Z')}
      />,
    );
    expect(screen.getByRole('heading', { name: '오늘의 시그널' })).toBeInTheDocument();
    expect(screen.queryByText(/건너뛰어졌습니다/)).not.toBeInTheDocument();
  });

  it('2회 이상 결번일 때만 경고 줄이 붙는다', () => {
    render(
      <DataFreshnessBadge
        tradingDate={FRI}
        generatedAt="2026-09-11T22:30:00+00:00"
        now={new Date('2026-09-16T23:00:00Z')}
      />,
    );
    expect(screen.getByRole('heading', { name: '오늘의 시그널' })).toBeInTheDocument();
    expect(screen.getByText('이후 3회 갱신이 건너뛰어졌습니다')).toBeInTheDocument();
  });
});

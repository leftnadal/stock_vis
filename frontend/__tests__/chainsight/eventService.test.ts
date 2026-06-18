import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock authAxios
vi.mock('@/lib/api/authAxios', () => ({
  authAxios: {
    get: vi.fn(),
  },
}));

import { authAxios } from '@/lib/api/authAxios';
import { fetchEvents, fetchEventStocks } from '@/services/chainsightService';
import type { EventBoardItem, EventRankingItem } from '@/types/chainsight';

const mockEvents: EventBoardItem[] = [
  {
    theme: 'semiconductor',
    member_count: 12,
    avg_return: 0.045,
    avg_score: 85.3,
    high_attention_count: 8,
    low_attention_count: 2,
  },
  {
    theme: 'clean_energy',
    member_count: 6,
    avg_return: -0.012,
    avg_score: 62.1,
    high_attention_count: 3,
    low_attention_count: 1,
  },
];

const mockStocks: EventRankingItem[] = [
  {
    symbol: 'NVDA',
    name: 'NVIDIA Corporation',
    score: 92.5,
    raw_return: 0.08,
    volume_z: 3.2,
    volatility_pct: 0.45,
    is_low_liquidity: false,
    trend_quality: 0.81,
    theme_alpha: 0.05,
    theme_beta: 1.34,
    up_capture: 1.18,
    down_capture: 0.99,
    capture_spread: 19,
    is_fallback: false,
  },
  {
    symbol: 'SMCI',
    name: 'Super Micro Computer',
    score: 41.0,
    raw_return: 0.02,
    volume_z: 0.8,
    volatility_pct: 0.72,
    is_low_liquidity: true,
    // 게이트 미달(예: 관련주<3) → M2 NULL
    trend_quality: null,
    theme_alpha: null,
    theme_beta: null,
    up_capture: null,
    down_capture: null,
    capture_spread: null,
    is_fallback: false,
  },
];

describe('fetchEvents', () => {
  beforeEach(() => vi.clearAllMocks());

  it('올바른 엔드포인트를 호출하고 데이터를 반환한다', async () => {
    vi.mocked(authAxios.get).mockResolvedValueOnce({ data: mockEvents });
    const result = await fetchEvents();
    expect(authAxios.get).toHaveBeenCalledWith('/chainsight/events/');
    expect(result).toHaveLength(2);
    expect(result[0].theme).toBe('semiconductor');
  });

  it('EventBoardItem 필드가 모두 파싱된다', async () => {
    vi.mocked(authAxios.get).mockResolvedValueOnce({ data: mockEvents });
    const result = await fetchEvents();
    const item = result[0];
    expect(typeof item.theme).toBe('string');
    expect(typeof item.member_count).toBe('number');
    expect(typeof item.avg_return).toBe('number');
    expect(typeof item.avg_score).toBe('number');
    expect(typeof item.high_attention_count).toBe('number');
    expect(typeof item.low_attention_count).toBe('number');
  });
});

describe('fetchEventStocks', () => {
  beforeEach(() => vi.clearAllMocks());

  it('theme 파라미터로 올바른 엔드포인트를 호출한다 (window 기본 20)', async () => {
    vi.mocked(authAxios.get).mockResolvedValueOnce({ data: mockStocks });
    const result = await fetchEventStocks('semiconductor');
    expect(authAxios.get).toHaveBeenCalledWith('/chainsight/events/semiconductor/stocks/', {
      params: { window: 20 },
    });
    expect(result).toHaveLength(2);
  });

  it('window=120을 params로 전달한다', async () => {
    vi.mocked(authAxios.get).mockResolvedValueOnce({ data: mockStocks });
    await fetchEventStocks('semiconductor', 120);
    expect(authAxios.get).toHaveBeenCalledWith('/chainsight/events/semiconductor/stocks/', {
      params: { window: 120 },
    });
  });

  it('EventRankingItem 필드가 모두 파싱된다', async () => {
    vi.mocked(authAxios.get).mockResolvedValueOnce({ data: mockStocks });
    const result = await fetchEventStocks('semiconductor');
    const item = result[0];
    expect(typeof item.symbol).toBe('string');
    expect(typeof item.name).toBe('string');
    expect(typeof item.score).toBe('number');
    expect(typeof item.raw_return).toBe('number');
    expect(typeof item.volume_z).toBe('number');
    expect(typeof item.volatility_pct).toBe('number');
    expect(typeof item.is_low_liquidity).toBe('boolean');
  });

  it('is_low_liquidity가 true인 항목을 올바르게 파싱한다', async () => {
    vi.mocked(authAxios.get).mockResolvedValueOnce({ data: mockStocks });
    const result = await fetchEventStocks('semiconductor');
    expect(result[1].is_low_liquidity).toBe(true);
  });

  it('특수문자 포함 theme을 encodeURIComponent로 인코딩한다', async () => {
    vi.mocked(authAxios.get).mockResolvedValueOnce({ data: [] });
    await fetchEventStocks('clean energy');
    expect(authAxios.get).toHaveBeenCalledWith('/chainsight/events/clean%20energy/stocks/', {
      params: { window: 20 },
    });
  });
});

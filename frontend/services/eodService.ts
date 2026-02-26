import type { EODDashboardData, SignalCardDetail } from '@/types/eod';

const SIGNALS_BASE = '/static/signals';

export const eodService = {
  async getDashboard(): Promise<EODDashboardData> {
    const res = await fetch(`${SIGNALS_BASE}/dashboard.json`);
    if (!res.ok) throw new Error(`Dashboard fetch failed: ${res.status}`);
    return res.json();
  },

  async getSignalDetail(category: string): Promise<SignalCardDetail> {
    const res = await fetch(`${SIGNALS_BASE}/cards/${category}.json`);
    if (!res.ok) throw new Error(`Card detail fetch failed: ${res.status}`);
    return res.json();
  },

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  async getStockHistory(symbol: string): Promise<any> {
    const res = await fetch(`${SIGNALS_BASE}/stocks/${symbol}.json`);
    if (!res.ok) throw new Error(`Stock history fetch failed: ${res.status}`);
    return res.json();
  },
};

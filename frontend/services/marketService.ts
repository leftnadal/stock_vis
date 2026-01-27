import axios from 'axios';
import type { MarketMoversResponse } from '@/types/market';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_URL,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const marketService = {
  async getMarketMovers(limit: number = 10): Promise<MarketMoversResponse> {
    const response = await api.get('/stocks/api/market-movers/', {
      params: { limit },
    });
    return response.data;
  },
};

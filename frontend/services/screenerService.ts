import axios from 'axios';
import type {
  MarketBreadthResponse,
  SectorHeatmapResponse,
  ScreenerPresetsResponse,
  ScreenerResponse,
  ScreenerFilters,
  CreatePresetPayload,
  ScreenerPreset,
  ChainSightResponse,
  ScreenerStock,
  ThesisResponse,
  MyThesesResponse,
  GenerateThesisPayload,
} from '@/types/screener';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_URL,
});

api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

export const screenerService = {
  /**
   * Market Breadth 조회
   * @param date - 조회 날짜 (YYYY-MM-DD, 선택사항)
   */
  async getMarketBreadth(date?: string): Promise<MarketBreadthResponse> {
    const params: Record<string, string> = {};
    if (date) {
      params.date = date;
    }

    const response = await api.get('/serverless/breadth', { params });
    return response.data;
  },

  /**
   * Sector Heatmap 조회
   * @param date - 조회 날짜 (YYYY-MM-DD, 선택사항)
   */
  async getSectorHeatmap(date?: string): Promise<SectorHeatmapResponse> {
    const params: Record<string, string> = {};
    if (date) {
      params.date = date;
    }

    const response = await api.get('/serverless/heatmap/sectors', { params });
    return response.data;
  },

  /**
   * Screener Presets 조회
   * @param category - 카테고리 필터 (선택사항)
   */
  async getPresets(category?: string): Promise<ScreenerPresetsResponse> {
    const params: Record<string, string> = {};
    if (category) {
      params.category = category;
    }

    const response = await api.get('/serverless/presets', { params });
    return response.data;
  },

  /**
   * Screener Preset 생성
   * @param payload - 프리셋 생성 데이터
   */
  async createPreset(payload: CreatePresetPayload): Promise<ScreenerPreset> {
    const response = await api.post('/serverless/presets', payload);
    return response.data.data;
  },

  /**
   * Screener Preset 삭제
   * @param presetId - 프리셋 ID
   */
  async deletePreset(presetId: number): Promise<void> {
    await api.delete(`/serverless/presets/${presetId}`);
  },

  /**
   * Advanced Screener 실행
   * @param filters - 필터 조건
   * @param page - 페이지 번호 (기본값: 1)
   * @param pageSize - 페이지 크기 (기본값: 20)
   */
  async runScreener(
    filters: ScreenerFilters,
    page: number = 1,
    pageSize: number = 20
  ): Promise<ScreenerResponse> {
    const response = await api.post('/serverless/screener', {
      filters,
      page,
      page_size: pageSize,
    });
    return response.data;
  },

  // ========================================
  // Alert System APIs (Phase 1)
  // ========================================

  /**
   * Get user's screener alerts
   */
  async getAlerts(): Promise<{
    success: boolean;
    data: { count: number; alerts: any[] };
  }> {
    const response = await api.get('/serverless/alerts');
    return response.data;
  },

  /**
   * Create a new alert
   * @param payload - Alert creation data
   */
  async createAlert(payload: {
    name: string;
    description?: string;
    preset?: number;
    filters_json?: ScreenerFilters;
    alert_type?: string;
    target_count?: number;
    cooldown_hours?: number;
    notify_in_app?: boolean;
    notify_email?: boolean;
  }): Promise<{ success: boolean; data: { id: number } }> {
    const response = await api.post('/serverless/alerts', payload);
    return response.data;
  },

  /**
   * Update an alert
   * @param alertId - Alert ID
   * @param payload - Update data
   */
  async updateAlert(alertId: number, payload: Partial<{
    name: string;
    description: string;
    filters_json: ScreenerFilters;
    target_count: number;
    is_active: boolean;
    cooldown_hours: number;
    notify_in_app: boolean;
    notify_email: boolean;
  }>): Promise<{ success: boolean; data: any }> {
    const response = await api.patch(`/serverless/alerts/${alertId}`, payload);
    return response.data;
  },

  /**
   * Delete an alert
   * @param alertId - Alert ID
   */
  async deleteAlert(alertId: number): Promise<{ success: boolean }> {
    const response = await api.delete(`/serverless/alerts/${alertId}`);
    return response.data;
  },

  /**
   * Toggle alert active status
   * @param alertId - Alert ID
   */
  async toggleAlert(alertId: number): Promise<{
    success: boolean;
    data: { id: number; is_active: boolean };
  }> {
    const response = await api.post(`/serverless/alerts/${alertId}/toggle`);
    return response.data;
  },

  /**
   * Get alert history
   * @param limit - Max number of history items
   * @param unreadOnly - Only return unread alerts
   */
  async getAlertHistory(
    limit: number = 20,
    unreadOnly: boolean = false
  ): Promise<{
    success: boolean;
    data: { count: number; history: any[]; unread_count: number };
  }> {
    const response = await api.get('/serverless/alerts/history', {
      params: { limit, unread_only: unreadOnly },
    });
    return response.data;
  },

  /**
   * Mark alert history as read
   * @param historyId - Alert history ID
   */
  async markAlertRead(historyId: number): Promise<{ success: boolean }> {
    const response = await api.post(`/serverless/alerts/history/${historyId}/read`);
    return response.data;
  },

  /**
   * Dismiss alert history
   * @param historyId - Alert history ID
   */
  async dismissAlert(historyId: number): Promise<{ success: boolean }> {
    const response = await api.post(`/serverless/alerts/history/${historyId}/dismiss`);
    return response.data;
  },

  // ========================================
  // Preset Sharing APIs (Phase 2.1)
  // ========================================

  /**
   * Share a preset
   * @param presetId - Preset ID to share
   */
  async sharePreset(presetId: number): Promise<{
    success: boolean;
    data: { share_code: string; share_url: string; expires_at: string };
  }> {
    const response = await api.post(`/serverless/presets/${presetId}/share`);
    return response.data;
  },

  /**
   * Get shared preset by share code
   * @param shareCode - Share code from URL
   */
  async getSharedPreset(shareCode: string): Promise<{
    success: boolean;
    data: {
      id: number;
      name: string;
      description_ko: string;
      category: string;
      filters_json: ScreenerFilters;
      created_by_username: string;
      created_at: string;
      share_code: string;
      expires_at: string;
    };
  }> {
    const response = await api.get(`/serverless/presets/shared/${shareCode}`);
    return response.data;
  },

  /**
   * Import a shared preset
   * @param shareCode - Share code from URL
   * @param newName - Optional custom name for the imported preset
   */
  async importPreset(shareCode: string, newName?: string): Promise<{
    success: boolean;
    data: ScreenerPreset;
  }> {
    const response = await api.post(`/serverless/presets/import/${shareCode}`, {
      custom_name: newName,
    });
    return response.data;
  },

  // ========================================
  // Chain Sight APIs (Phase 2.2)
  // ========================================

  /**
   * Get chain sight analysis
   * @param symbols - Current filtered stock symbols
   * @param filters - Applied filters
   */
  async getChainSight(
    symbols: string[],
    filters: ScreenerFilters
  ): Promise<ChainSightResponse> {
    const response = await api.post('/serverless/screener/chain-sight', {
      symbols,
      filters,
      use_ai: true,  // AI 인사이트 활성화
    });
    return response.data;
  },

  // ========================================
  // Investment Thesis APIs (Phase 2.3)
  // ========================================

  /**
   * Generate investment thesis
   * @param stocks - Filtered stocks
   * @param filters - Applied filters
   * @param userNotes - Optional user notes
   */
  async generateThesis(
    stocks: ScreenerStock[],
    filters: ScreenerFilters,
    userNotes?: string
  ): Promise<ThesisResponse> {
    const response = await api.post('/serverless/thesis/generate', {
      stocks,
      filters,
      user_notes: userNotes,
    });
    return response.data;
  },

  /**
   * Get thesis by ID
   * @param thesisId - Thesis ID
   */
  async getThesis(thesisId: number): Promise<ThesisResponse> {
    const response = await api.get(`/serverless/thesis/${thesisId}`);
    return response.data;
  },

  /**
   * Get user's theses
   */
  async getMyTheses(): Promise<MyThesesResponse> {
    const response = await api.get('/serverless/thesis/my-theses');
    return response.data;
  },
};

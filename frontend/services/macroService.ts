/**
 * 거시경제 데이터 API 서비스
 */
import type {
  MarketPulseDashboard,
  FearGreedIndex,
  InterestRatesDashboard,
  InflationDashboard,
  GlobalMarketsDashboard,
  EconomicCalendar,
} from '@/types/macro';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

class MacroService {
  private baseUrl = `${API_BASE_URL}/macro`;

  /**
   * 전체 Market Pulse 대시보드 데이터
   */
  async getMarketPulse(): Promise<MarketPulseDashboard> {
    const response = await fetch(`${this.baseUrl}/pulse/`);
    if (!response.ok) {
      throw new Error('Failed to fetch market pulse data');
    }
    return response.json();
  }

  /**
   * 공포/탐욕 지수
   */
  async getFearGreedIndex(): Promise<FearGreedIndex> {
    const response = await fetch(`${this.baseUrl}/fear-greed/`);
    if (!response.ok) {
      throw new Error('Failed to fetch fear/greed index');
    }
    return response.json();
  }

  /**
   * 금리 & 수익률 곡선
   */
  async getInterestRates(): Promise<InterestRatesDashboard> {
    const response = await fetch(`${this.baseUrl}/interest-rates/`);
    if (!response.ok) {
      throw new Error('Failed to fetch interest rates');
    }
    return response.json();
  }

  /**
   * 인플레이션 & 고용
   */
  async getInflationData(): Promise<InflationDashboard> {
    const response = await fetch(`${this.baseUrl}/inflation/`);
    if (!response.ok) {
      throw new Error('Failed to fetch inflation data');
    }
    return response.json();
  }

  /**
   * 글로벌 시장
   */
  async getGlobalMarkets(): Promise<GlobalMarketsDashboard> {
    const response = await fetch(`${this.baseUrl}/global-markets/`);
    if (!response.ok) {
      throw new Error('Failed to fetch global markets');
    }
    return response.json();
  }

  /**
   * 경제 캘린더
   */
  async getEconomicCalendar(
    days: number = 7,
    importance?: 'critical' | 'high' | 'medium'
  ): Promise<EconomicCalendar> {
    const params = new URLSearchParams({ days: days.toString() });
    if (importance) {
      params.append('importance', importance);
    }

    const response = await fetch(`${this.baseUrl}/calendar/?${params}`);
    if (!response.ok) {
      throw new Error('Failed to fetch economic calendar');
    }
    return response.json();
  }

  /**
   * VIX 지수
   */
  async getVIX(): Promise<{ value: number; level: string; date: string }> {
    const response = await fetch(`${this.baseUrl}/vix/`);
    if (!response.ok) {
      throw new Error('Failed to fetch VIX');
    }
    return response.json();
  }

  /**
   * 섹터 성과
   */
  async getSectorPerformance(): Promise<Record<string, unknown>> {
    const response = await fetch(`${this.baseUrl}/sectors/`);
    if (!response.ok) {
      throw new Error('Failed to fetch sector performance');
    }
    return response.json();
  }

  /**
   * 데이터 동기화 시작
   */
  async startDataSync(): Promise<{ status: string; message: string }> {
    const response = await fetch(`${this.baseUrl}/sync/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    if (!response.ok) {
      throw new Error('Failed to start data sync');
    }
    return response.json();
  }

  /**
   * 동기화 상태 확인
   */
  async getSyncStatus(): Promise<{
    status: 'idle' | 'running' | 'completed' | 'error';
    progress: {
      current_step: string;
      steps_completed: number;
      total_steps: number;
      message: string;
    };
  }> {
    const response = await fetch(`${this.baseUrl}/sync/status/`);
    if (!response.ok) {
      throw new Error('Failed to fetch sync status');
    }
    return response.json();
  }
}

export const macroService = new MacroService();
export default macroService;

import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

// API 인스턴스 생성
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor - 토큰 추가
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    console.error('Request error:', error)
    return Promise.reject(error)
  }
)

// Response interceptor - 에러 처리
api.interceptors.response.use(
  (response) => {
    // 성공 응답은 그대로 반환
    return response
  },
  (error) => {
    console.error('Response error:', error)

    // 네트워크 에러 체크
    if (!error.response) {
      console.error('Network error - no response')
      error.message = '서버와 연결할 수 없습니다.'
    } else {
      // 서버 응답이 있는 경우
      const { status, data } = error.response
      console.error(`Server error - status: ${status}`, data)

      if (status === 401) {
        // 인증 토큰 만료
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        // 로그인 페이지로 리다이렉트 (필요한 경우)
        // window.location.href = '/login'
      }
    }

    return Promise.reject(error)
  }
)

export interface Portfolio {
  id: number
  stock_symbol: string
  stock_name: string
  quantity: string
  average_price: string
  current_price: string
  total_value: number
  total_cost: number
  profit_loss: number
  profit_loss_percentage: number
  is_profitable: boolean
  notes?: string
  created_at: string
  updated_at: string
}

export interface PortfolioSummary {
  total_stocks: number
  total_value: number
  total_cost: number
  total_profit_loss: number
  total_profit_loss_percentage: number
  is_profitable: boolean
}

export interface CreatePortfolioData {
  stock: string  // symbol
  quantity: number
  average_price: number
  notes?: string
}

export const portfolioService = {
  // 포트폴리오 목록 조회
  async getPortfolios(): Promise<Portfolio[]> {
    const response = await api.get('/users/portfolio/')
    return response.data
  },

  // 포트폴리오 요약 정보
  async getPortfolioSummary(): Promise<PortfolioSummary> {
    const response = await api.get('/users/portfolio/summary/')
    return response.data
  },

  // 포트폴리오 항목 추가
  async createPortfolio(data: CreatePortfolioData): Promise<Portfolio> {
    const response = await api.post('/users/portfolio/', data)
    return response.data
  },

  // 포트폴리오 항목 수정
  async updatePortfolio(id: number, data: Partial<CreatePortfolioData>): Promise<Portfolio> {
    const response = await api.put(`/users/portfolio/${id}/`, data)
    return response.data
  },

  // 포트폴리오 항목 삭제
  async deletePortfolio(id: number): Promise<void> {
    await api.delete(`/users/portfolio/${id}/`)
  },

  // 심볼로 포트폴리오 조회
  async getPortfolioBySymbol(symbol: string): Promise<Portfolio> {
    const response = await api.get(`/users/portfolio/symbol/${symbol}/`)
    return response.data
  },

  // 주식 데이터 수집 상태 조회
  async getStockDataStatus(symbol: string): Promise<StockDataStatus> {
    const response = await api.get(`/users/portfolio/symbol/${symbol}/status/`)
    return response.data
  },
}

export interface StockDataStatus {
  symbol: string
  stock_exists: boolean
  has_overview: boolean
  has_prices: boolean
  has_financial: boolean
  is_complete: boolean
  details: {
    daily_prices: number
    weekly_prices: number
    balance_sheets: number
    income_statements: number
    cash_flows: number
  }
}
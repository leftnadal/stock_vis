import axios from 'axios'
import type {
  Watchlist,
  WatchlistItem,
  CreateWatchlistData,
  UpdateWatchlistData,
  AddStockToWatchlistData,
  UpdateWatchlistItemData
} from '@/types/watchlist'

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
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('access_token')
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
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
    return response
  },
  (error) => {
    console.error('Response error:', error)

    if (!error.response) {
      console.error('Network error - no response')
      error.message = '서버와 연결할 수 없습니다.'
    } else {
      const { status, data } = error.response
      console.error(`Server error - status: ${status}`, data)

      if (status === 401 && typeof window !== 'undefined') {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
      }
    }

    return Promise.reject(error)
  }
)

export const watchlistService = {
  // 관심종목 리스트 목록 조회
  async getWatchlists(): Promise<Watchlist[]> {
    const response = await api.get('/users/watchlist/')
    // API가 페이지네이션 형태로 응답하면 results를, 배열이면 그대로 반환
    return response.data.results ?? response.data
  },

  // 관심종목 리스트 생성
  async createWatchlist(data: CreateWatchlistData): Promise<Watchlist> {
    const response = await api.post('/users/watchlist/', data)
    return response.data
  },

  // 관심종목 리스트 상세 조회
  async getWatchlist(id: number): Promise<Watchlist> {
    const response = await api.get(`/users/watchlist/${id}/`)
    return response.data
  },

  // 관심종목 리스트 수정
  async updateWatchlist(id: number, data: UpdateWatchlistData): Promise<Watchlist> {
    const response = await api.patch(`/users/watchlist/${id}/`, data)
    return response.data
  },

  // 관심종목 리스트 삭제
  async deleteWatchlist(id: number): Promise<void> {
    await api.delete(`/users/watchlist/${id}/`)
  },

  // 종목 추가
  async addStock(watchlistId: number, data: AddStockToWatchlistData): Promise<WatchlistItem> {
    const response = await api.post(`/users/watchlist/${watchlistId}/add-stock/`, data)
    return response.data
  },

  // 종목 제거
  async removeStock(watchlistId: number, symbol: string): Promise<void> {
    await api.delete(`/users/watchlist/${watchlistId}/stocks/${symbol}/remove/`)
  },

  // 종목 설정 수정
  async updateStockSettings(
    watchlistId: number,
    symbol: string,
    data: UpdateWatchlistItemData
  ): Promise<WatchlistItem> {
    const response = await api.patch(`/users/watchlist/${watchlistId}/stocks/${symbol}/`, data)
    return response.data
  },

  // 종목 상세 조회 (실시간 가격 포함)
  async getWatchlistStocks(watchlistId: number): Promise<WatchlistItem[]> {
    const response = await api.get(`/users/watchlist/${watchlistId}/stocks/`)
    // API가 페이지네이션 형태로 응답하면 results를, 배열이면 그대로 반환
    return response.data.results ?? response.data
  },
}

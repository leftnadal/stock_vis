import axios, { type InternalAxiosRequestConfig } from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

export const authAxios = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
})

// ── 토큰 유틸 (SSR 안전) ──
// TODO: 향후 SSR 데이터 페칭이 필요해지면 HTTP-Only Cookie 기반으로 전환.
//       tokenUtils를 단일 소스로 유지했으므로 이 파일만 수정하면 전환 가능.
export const tokenUtils = {
  getAccess: (): string | null =>
    typeof window !== 'undefined' ? localStorage.getItem('access_token') : null,
  getRefresh: (): string | null =>
    typeof window !== 'undefined' ? localStorage.getItem('refresh_token') : null,
  setTokens: (access: string, refresh: string) => {
    if (typeof window === 'undefined') return
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
  },
  setAccess: (access: string) => {
    if (typeof window !== 'undefined') localStorage.setItem('access_token', access)
  },
  clear: () => {
    if (typeof window === 'undefined') return
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  },
}

// ── 요청 인터셉터 ──
authAxios.interceptors.request.use((config) => {
  const token = tokenUtils.getAccess()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// ── 응답 인터셉터 ──
// 방어 (1): 단일 탭 Race Condition — isRefreshing + pendingQueue
// 방어 (2): 다중 탭 동기화 — refresh 전 localStorage 재확인 + storage 이벤트
// 방어 (3): Token Rotation — data.refresh 저장

let isRefreshing = false
let pendingQueue: {
  resolve: (token: string) => void
  reject: (err: unknown) => void
}[] = []

function processQueue(error: unknown, token: string | null) {
  pendingQueue.forEach(({ resolve, reject }) => {
    error ? reject(error) : resolve(token!)
  })
  pendingQueue = []
}

// ── 다중 탭 동기화: 다른 탭에서 토큰이 갱신/삭제되면 감지 ──
if (typeof window !== 'undefined') {
  window.addEventListener('storage', (e) => {
    if (e.key === 'access_token' && e.newValue) {
      processQueue(null, e.newValue)
    }
    if (e.key === 'access_token' && !e.newValue) {
      processQueue(new Error('Logged out in another tab'), null)
    }
  })
}

authAxios.interceptors.response.use(
  (res) => res,
  async (error) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }

    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(error)
    }

    originalRequest._retry = true

    // ── 방어 (2): 다른 탭이 이미 갱신했는지 확인 ──
    const currentAccess = tokenUtils.getAccess()
    const failedToken = originalRequest.headers.Authorization
      ?.toString().replace('Bearer ', '')

    if (currentAccess && currentAccess !== failedToken) {
      originalRequest.headers.Authorization = `Bearer ${currentAccess}`
      return authAxios(originalRequest)
    }

    // ── 방어 (1): 이 탭에서 이미 갱신 중이면 큐 대기 ──
    if (isRefreshing) {
      return new Promise<string>((resolve, reject) => {
        pendingQueue.push({ resolve, reject })
      }).then((newToken) => {
        originalRequest.headers.Authorization = `Bearer ${newToken}`
        return authAxios(originalRequest)
      })
    }

    isRefreshing = true

    try {
      const refresh = tokenUtils.getRefresh()
      if (!refresh) throw new Error('No refresh token')

      const { data } = await axios.post(`${API_URL}/users/jwt/refresh/`, { refresh })

      // ── 방어 (3): ROTATE_REFRESH_TOKENS=True 대응 ──
      if (data.refresh) {
        tokenUtils.setTokens(data.access, data.refresh)
      } else {
        tokenUtils.setAccess(data.access)
      }

      processQueue(null, data.access)

      originalRequest.headers.Authorization = `Bearer ${data.access}`
      return authAxios(originalRequest)
    } catch (refreshError) {
      processQueue(refreshError, null)
      tokenUtils.clear()
      if (typeof window !== 'undefined') window.location.href = '/login'
      return Promise.reject(refreshError)
    } finally {
      isRefreshing = false
    }
  }
)

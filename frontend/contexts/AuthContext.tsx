'use client'

import React, { createContext, useState, useContext, useEffect } from 'react'
import axios from 'axios'
import { useRouter } from 'next/navigation'

interface User {
  id: number
  username: string
  user_name: string
  email: string
  nick_name?: string
  is_superuser?: boolean
  is_staff?: boolean
  date_joined?: string
}

interface AuthContextType {
  user: User | null
  loading: boolean
  login: (username: string, password: string) => Promise<void>
  signup: (userData: SignupData) => Promise<void>
  logout: () => void
  refreshToken: () => Promise<void>
  setUser: (user: User) => void
  isAuthenticated: boolean
}

interface SignupData {
  username: string
  email: string
  password: string
  password2: string
  nick_name?: string
}

const AuthContext = createContext<AuthContextType>({} as AuthContextType)

// API 기본 URL
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

// Axios 인스턴스 생성
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 토큰 저장/불러오기 유틸리티
const tokenUtils = {
  getAccessToken: () => localStorage.getItem('access_token'),
  getRefreshToken: () => localStorage.getItem('refresh_token'),
  setTokens: (access: string, refresh: string) => {
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
  },
  clearTokens: () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  },
}

// Axios 요청 인터셉터 - 토큰 자동 추가
api.interceptors.request.use(
  (config) => {
    const token = tokenUtils.getAccessToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Axios 응답 인터셉터 - 토큰 만료 시 자동 갱신
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        const refreshToken = tokenUtils.getRefreshToken()
        if (refreshToken) {
          const response = await axios.post(`${API_URL}/users/jwt/refresh/`, {
            refresh: refreshToken,
          })

          const { access } = response.data
          localStorage.setItem('access_token', access)

          originalRequest.headers.Authorization = `Bearer ${access}`
          return api(originalRequest)
        }
      } catch (refreshError) {
        tokenUtils.clearTokens()
        window.location.href = '/login'
        return Promise.reject(refreshError)
      }
    }

    return Promise.reject(error)
  }
)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const router = useRouter()

  // 컴포넌트 마운트 시 토큰 검증
  useEffect(() => {
    verifyToken()
  }, [])

  const verifyToken = async () => {
    try {
      const accessToken = tokenUtils.getAccessToken()
      if (accessToken) {
        const response = await api.get('/users/jwt/verify/')
        setUser(response.data.user)
      }
    } catch (error) {
      console.error('Token verification failed:', error)
      tokenUtils.clearTokens()
    } finally {
      setLoading(false)
    }
  }

  const login = async (username: string, password: string) => {
    try {
      const response = await axios.post(`${API_URL}/users/jwt/login/`, {
        username,
        password,
      })

      const { access, refresh, user } = response.data
      tokenUtils.setTokens(access, refresh)
      setUser(user)

      // 로그인 후 홈 또는 대시보드로 이동
      router.push('/dashboard')
    } catch (error: any) {
      console.error('Login failed:', error)
      // 네트워크 에러 체크
      if (!error.response) {
        console.error('Network error - Backend server may be down')
        throw new Error('서버와 연결할 수 없습니다. 백엔드 서버가 실행 중인지 확인해주세요.')
      }
      // 서버 에러 메시지 처리
      const errorMessage = error.response?.data?.detail ||
                          error.response?.data?.error ||
                          error.response?.data?.message ||
                          '로그인에 실패했습니다.'
      throw new Error(errorMessage)
    }
  }

  const signup = async (userData: SignupData) => {
    try {
      const response = await axios.post(`${API_URL}/users/jwt/signup/`, userData)

      const { tokens, user } = response.data
      tokenUtils.setTokens(tokens.access, tokens.refresh)
      setUser(user)

      // 회원가입 후 홈 또는 대시보드로 이동
      router.push('/dashboard')
    } catch (error: any) {
      console.error('Signup failed:', error)
      // 네트워크 에러 체크
      if (!error.response) {
        console.error('Network error - Backend server may be down')
        throw new Error('서버와 연결할 수 없습니다. 백엔드 서버가 실행 중인지 확인해주세요.')
      }
      // 서버 에러 메시지 처리
      const errorMessage = error.response?.data?.error ||
                          error.response?.data?.detail ||
                          error.response?.data?.message ||
                          '회원가입에 실패했습니다.'
      throw new Error(errorMessage)
    }
  }

  const logout = async () => {
    try {
      const refreshToken = tokenUtils.getRefreshToken()
      if (refreshToken) {
        await api.post('/users/jwt/logout/', {
          refresh: refreshToken,
        })
      }
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      tokenUtils.clearTokens()
      setUser(null)
      router.push('/login')
    }
  }

  const refreshToken = async () => {
    try {
      const refreshToken = tokenUtils.getRefreshToken()
      if (refreshToken) {
        const response = await axios.post(`${API_URL}/users/jwt/refresh/`, {
          refresh: refreshToken,
        })

        const { access } = response.data
        localStorage.setItem('access_token', access)
      }
    } catch (error) {
      console.error('Token refresh failed:', error)
      tokenUtils.clearTokens()
      setUser(null)
      throw error
    }
  }

  const value = {
    user,
    loading,
    login,
    signup,
    logout,
    refreshToken,
    setUser,
    isAuthenticated: !!user,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export default AuthContext
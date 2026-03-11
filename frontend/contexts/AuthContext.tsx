'use client'

import React, { createContext, useState, useContext, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { authAxios as api, tokenUtils } from '@/lib/api/authAxios'

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

const AuthContext = createContext<AuthContextType | null>(null)

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
      const accessToken = tokenUtils.getAccess()
      if (accessToken) {
        const response = await api.get('/users/jwt/verify/')
        setUser(response.data.user)
      }
    } catch (error) {
      console.error('Token verification failed:', error)
      tokenUtils.clear()
    } finally {
      setLoading(false)
    }
  }

  const login = async (username: string, password: string) => {
    try {
      const response = await api.post('/users/jwt/login/', {
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
      if (!(error instanceof Error)) throw error
      const axiosError = error as { response?: { data?: { detail?: string; error?: string; message?: string } } }
      if (!axiosError.response) {
        console.error('Network error - Backend server may be down')
        throw new Error('서버와 연결할 수 없습니다. 백엔드 서버가 실행 중인지 확인해주세요.')
      }
      const errorMessage = axiosError.response?.data?.detail ||
                          axiosError.response?.data?.error ||
                          axiosError.response?.data?.message ||
                          '로그인에 실패했습니다.'
      throw new Error(errorMessage)
    }
  }

  const signup = async (userData: SignupData) => {
    try {
      const response = await api.post('/users/jwt/signup/', userData)

      const { tokens, user } = response.data
      tokenUtils.setTokens(tokens.access, tokens.refresh)
      setUser(user)

      // 회원가입 후 홈 또는 대시보드로 이동
      router.push('/dashboard')
    } catch (error: any) {
      console.error('Signup failed:', error)
      if (!(error instanceof Error)) throw error
      const axiosError = error as { response?: { data?: { detail?: string; error?: string; message?: string } } }
      if (!axiosError.response) {
        console.error('Network error - Backend server may be down')
        throw new Error('서버와 연결할 수 없습니다. 백엔드 서버가 실행 중인지 확인해주세요.')
      }
      const errorMessage = axiosError.response?.data?.error ||
                          axiosError.response?.data?.detail ||
                          axiosError.response?.data?.message ||
                          '회원가입에 실패했습니다.'
      throw new Error(errorMessage)
    }
  }

  const logout = async () => {
    try {
      const refresh = tokenUtils.getRefresh()
      if (refresh) {
        await api.post('/users/jwt/logout/', { refresh })
      }
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      tokenUtils.clear()
      setUser(null)
      router.push('/login')
    }
  }

  const refreshToken = async () => {
    try {
      const refresh = tokenUtils.getRefresh()
      if (refresh) {
        const response = await api.post('/users/jwt/refresh/', { refresh })

        if (response.data.refresh) {
          tokenUtils.setTokens(response.data.access, response.data.refresh)
        } else {
          tokenUtils.setAccess(response.data.access)
        }
      }
    } catch (error) {
      console.error('Token refresh failed:', error)
      tokenUtils.clear()
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
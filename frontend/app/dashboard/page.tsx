'use client'

import { useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { useRouter } from 'next/navigation'

export default function DashboardPage() {
  const { user, loading, isAuthenticated, logout } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push('/login')
    }
  }, [loading, isAuthenticated, router])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return null
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <h1 className="text-xl font-semibold">Stock-Vis Dashboard</h1>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-gray-700">
                안녕하세요, {user?.nick_name || user?.username}님
              </span>
              <button
                onClick={logout}
                className="text-gray-500 hover:text-gray-700 px-3 py-2 rounded-md text-sm font-medium"
              >
                로그아웃
              </button>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* 포트폴리오 카드 */}
            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <h3 className="text-lg leading-6 font-medium text-gray-900">내 포트폴리오</h3>
                <div className="mt-2 max-w-xl text-sm text-gray-500">
                  <p>보유 종목과 수익률을 확인하세요.</p>
                </div>
                <div className="mt-3">
                  <button
                    onClick={() => router.push('/portfolio')}
                    className="text-blue-600 hover:text-blue-500 text-sm font-medium"
                  >
                    포트폴리오 보기 →
                  </button>
                </div>
              </div>
            </div>

            {/* 주식 검색 카드 */}
            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <h3 className="text-lg leading-6 font-medium text-gray-900">주식 검색</h3>
                <div className="mt-2 max-w-xl text-sm text-gray-500">
                  <p>관심 있는 주식을 검색하고 분석하세요.</p>
                </div>
                <div className="mt-3">
                  <button
                    onClick={() => router.push('/stocks')}
                    className="text-blue-600 hover:text-blue-500 text-sm font-medium"
                  >
                    주식 검색하기 →
                  </button>
                </div>
              </div>
            </div>

            {/* 관심 종목 카드 */}
            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <h3 className="text-lg leading-6 font-medium text-gray-900">관심 종목</h3>
                <div className="mt-2 max-w-xl text-sm text-gray-500">
                  <p>즐겨찾기한 종목들을 확인하세요.</p>
                </div>
                <div className="mt-3">
                  <button
                    onClick={() => router.push('/favorites')}
                    className="text-blue-600 hover:text-blue-500 text-sm font-medium"
                  >
                    관심 종목 보기 →
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* 사용자 정보 섹션 */}
          <div className="mt-8 bg-white shadow overflow-hidden sm:rounded-lg">
            <div className="px-4 py-5 sm:px-6">
              <h3 className="text-lg leading-6 font-medium text-gray-900">계정 정보</h3>
            </div>
            <div className="border-t border-gray-200">
              <dl>
                <div className="bg-gray-50 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                  <dt className="text-sm font-medium text-gray-500">사용자명</dt>
                  <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                    {user?.username}
                  </dd>
                </div>
                <div className="bg-white px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                  <dt className="text-sm font-medium text-gray-500">이메일</dt>
                  <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                    {user?.email}
                  </dd>
                </div>
                <div className="bg-gray-50 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                  <dt className="text-sm font-medium text-gray-500">닉네임</dt>
                  <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                    {user?.nick_name || '설정되지 않음'}
                  </dd>
                </div>
              </dl>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
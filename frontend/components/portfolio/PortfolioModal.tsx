'use client'

import { useState, useEffect, useRef } from 'react'
import { X, Search, TrendingUp, Check } from 'lucide-react'
import { portfolioService, CreatePortfolioData, Portfolio } from '@/services/portfolio'
import axios from 'axios'

interface PortfolioModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  editingPortfolio?: Portfolio | null
}

interface SearchResult {
  symbol: string
  name: string
  type: string
  region: string
  currency: string
  match_score: number
}

export default function PortfolioModal({
  isOpen,
  onClose,
  onSuccess,
  editingPortfolio = null
}: PortfolioModalProps) {
  const [formData, setFormData] = useState<CreatePortfolioData>({
    stock: '',
    quantity: 0,
    average_price: 0,
    notes: ''
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [searching, setSearching] = useState(false)
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [showSearchResults, setShowSearchResults] = useState(false)
  const [selectedStock, setSelectedStock] = useState<SearchResult | null>(null)
  const [searchTimer, setSearchTimer] = useState<NodeJS.Timeout | null>(null)
  const searchDropdownRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (editingPortfolio) {
      setFormData({
        stock: editingPortfolio.stock_symbol,
        quantity: parseFloat(editingPortfolio.quantity),
        average_price: parseFloat(editingPortfolio.average_price),
        notes: editingPortfolio.notes || ''
      })
    } else {
      setFormData({
        stock: '',
        quantity: 0,
        average_price: 0,
        notes: ''
      })
      setSelectedStock(null)
      setSearchResults([])
      setShowSearchResults(false)
    }
  }, [editingPortfolio])

  // 종목 심볼 검색 함수
  const searchSymbols = async (keyword: string) => {
    if (keyword.length < 2) {
      setSearchResults([])
      setShowSearchResults(false)
      return
    }

    setSearching(true)
    try {
      const response = await axios.get(
        `http://localhost:8000/api/v1/stocks/api/search/symbols/`,
        {
          params: { keywords: keyword }
        }
      )

      if (response.data.results) {
        setSearchResults(response.data.results)
        setShowSearchResults(true)
      }
    } catch (error: any) {
      console.error('종목 검색 실패:', error)
      setSearchResults([])

      // 429 에러 처리 (Rate Limit)
      if (error.response?.status === 429) {
        setError('해당 종목은 관찰되지 않습니다.')
      }
    } finally {
      setSearching(false)
    }
  }

  // 디바운스된 검색 처리
  const handleSymbolSearch = (value: string) => {
    setFormData({ ...formData, stock: value.toUpperCase() })

    // 기존 타이머 취소
    if (searchTimer) {
      clearTimeout(searchTimer)
    }

    // 새 타이머 설정 (300ms 디바운스)
    const timer = setTimeout(() => {
      searchSymbols(value)
    }, 300)

    setSearchTimer(timer)
  }

  // 검색 결과 선택 처리
  const handleSelectStock = (stock: SearchResult) => {
    setFormData({ ...formData, stock: stock.symbol })
    setSelectedStock(stock)
    setShowSearchResults(false)
    setSearchResults([])
  }

  // 컴포넌트 언마운트 시 타이머 정리
  useEffect(() => {
    return () => {
      if (searchTimer) {
        clearTimeout(searchTimer)
      }
    }
  }, [searchTimer])

  // 클릭 아웃사이드 핸들러
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (searchDropdownRef.current && !searchDropdownRef.current.contains(event.target as Node)) {
        setShowSearchResults(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    // Validation
    if (!formData.stock) {
      setError('종목 심볼을 입력해주세요.')
      return
    }
    if (formData.quantity <= 0) {
      setError('수량은 0보다 커야 합니다.')
      return
    }
    if (formData.average_price <= 0) {
      setError('평균 매입가는 0보다 커야 합니다.')
      return
    }

    setLoading(true)

    try {
      if (editingPortfolio) {
        await portfolioService.updatePortfolio(editingPortfolio.id, formData)
      } else {
        await portfolioService.createPortfolio(formData)
      }
      onSuccess()
      onClose()
    } catch (err: any) {
      console.error('포트폴리오 저장 실패:', err)
      console.error('Error response:', err.response)
      console.error('Error request:', err.request)

      // 에러 메시지 처리 개선
      if (err.response) {
        // 서버가 응답을 반환한 경우
        const status = err.response.status
        const data = err.response.data

        if (status === 400) {
          // Bad Request - 유효성 검사 실패
          if (Array.isArray(data)) {
            setError(data[0] || '입력값을 확인해주세요.')
          } else if (typeof data === 'string') {
            setError(data)
          } else if (data.detail) {
            setError(data.detail)
          } else if (data.stock) {
            setError(data.stock[0])
          } else if (data.non_field_errors) {
            setError(data.non_field_errors[0])
          } else {
            setError('입력값을 확인해주세요.')
          }
        } else if (status === 401) {
          setError('인증이 필요합니다. 다시 로그인해주세요.')
        } else if (status === 403) {
          setError('권한이 없습니다.')
        } else if (status === 404) {
          setError('종목을 찾을 수 없습니다.')
        } else if (status === 500) {
          setError('서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.')
        } else {
          setError(`오류가 발생했습니다. (${status})`)
        }
      } else if (err.request) {
        // 요청은 보냈지만 응답을 받지 못한 경우
        console.error('No response received:', err.request)
        setError('서버 응답이 없습니다. 네트워크 연결을 확인해주세요.')
      } else {
        // 요청 설정 중 오류가 발생한 경우
        setError('요청 중 오류가 발생했습니다.')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async () => {
    if (!editingPortfolio || !confirm('정말 이 종목을 삭제하시겠습니까?')) {
      return
    }

    setLoading(true)
    try {
      await portfolioService.deletePortfolio(editingPortfolio.id)
      onSuccess()
      onClose()
    } catch (err: any) {
      console.error('포트폴리오 삭제 실패:', err)
      setError(err.response?.data?.detail || '삭제 중 오류가 발생했습니다.')
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-xl max-w-md w-full">
        {/* Header */}
        <div className="flex justify-between items-center p-6 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            {editingPortfolio ? '포트폴리오 수정' : '종목 추가'}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6">
          <div className="space-y-4">
            {/* Stock Symbol */}
            <div className="relative" ref={searchDropdownRef}>
              <label htmlFor="stock" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                종목 심볼 *
              </label>
              <div className="relative">
                <input
                  type="text"
                  id="stock"
                  value={formData.stock}
                  onChange={(e) => handleSymbolSearch(e.target.value)}
                  onFocus={() => {
                    if (searchResults.length > 0) {
                      setShowSearchResults(true)
                    }
                  }}
                  className="w-full px-3 py-2 pr-10 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                  placeholder="예: AAPL (종목 심볼 또는 회사명 검색)"
                  disabled={!!editingPortfolio}
                  required
                />
                {searching && (
                  <div className="absolute right-3 top-2.5">
                    <svg className="animate-spin h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                  </div>
                )}
                {!searching && !editingPortfolio && (
                  <Search className="absolute right-3 top-2.5 h-5 w-5 text-gray-400" />
                )}
              </div>

              {/* Search Results Dropdown */}
              {showSearchResults && searchResults.length > 0 && !editingPortfolio && (
                <div className="absolute z-10 mt-1 w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                  {searchResults.map((result, index) => (
                    <button
                      key={index}
                      type="button"
                      onClick={() => handleSelectStock(result)}
                      className="w-full text-left px-4 py-3 hover:bg-gray-100 dark:hover:bg-gray-700 focus:bg-gray-100 dark:focus:bg-gray-700 focus:outline-none border-b border-gray-200 dark:border-gray-700 last:border-b-0"
                    >
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <div className="flex items-center space-x-2">
                            <span className="font-semibold text-gray-900 dark:text-white">
                              {result.symbol}
                            </span>
                            {result.match_score > 0.8 && (
                              <span className="px-1.5 py-0.5 bg-green-100 text-green-700 text-xs rounded-full">
                                Best Match
                              </span>
                            )}
                          </div>
                          <p className="text-sm text-gray-600 dark:text-gray-400 mt-0.5">
                            {result.name}
                          </p>
                          <p className="text-xs text-gray-500 dark:text-gray-500 mt-0.5">
                            {result.type} • {result.region}
                          </p>
                        </div>
                        <div className="text-right ml-3">
                          <span className="text-xs text-gray-500 dark:text-gray-400">
                            {result.currency}
                          </span>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              )}

              {/* Selected Stock Info */}
              {selectedStock && !editingPortfolio && (
                <div className="mt-2 p-2 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                  <div className="flex items-center space-x-2">
                    <Check className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                    <span className="text-sm text-blue-700 dark:text-blue-300">
                      선택됨: <span className="font-semibold">{selectedStock.name}</span> ({selectedStock.symbol})
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* Quantity */}
            <div>
              <label htmlFor="quantity" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                수량 *
              </label>
              <input
                type="number"
                id="quantity"
                value={formData.quantity || ''}
                onChange={(e) => setFormData({ ...formData, quantity: parseFloat(e.target.value) || 0 })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                placeholder="0"
                step="0.0001"
                required
              />
            </div>

            {/* Average Price */}
            <div>
              <label htmlFor="average_price" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                평균 매입가 (USD) *
              </label>
              <input
                type="number"
                id="average_price"
                value={formData.average_price || ''}
                onChange={(e) => setFormData({ ...formData, average_price: parseFloat(e.target.value) || 0 })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                placeholder="0.00"
                step="0.01"
                required
              />
            </div>

            {/* Notes */}
            <div>
              <label htmlFor="notes" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                메모 (선택)
              </label>
              <textarea
                id="notes"
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                rows={3}
                placeholder="이 투자에 대한 메모..."
              />
            </div>

            {/* Error Message */}
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                <p className="text-sm text-red-600">{error}</p>
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="mt-6 flex justify-between">
            <div>
              {editingPortfolio && (
                <button
                  type="button"
                  onClick={handleDelete}
                  disabled={loading}
                  className="px-4 py-2 text-red-600 hover:text-red-700 font-medium disabled:opacity-50"
                >
                  삭제
                </button>
              )}
            </div>
            <div className="flex space-x-3">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white font-medium"
              >
                취소
              </button>
              <button
                type="submit"
                disabled={loading}
                className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <span className="flex items-center">
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    저장 중...
                  </span>
                ) : (
                  editingPortfolio ? '수정' : '추가'
                )}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}
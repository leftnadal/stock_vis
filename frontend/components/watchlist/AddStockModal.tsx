'use client'

import { useState, useEffect, useRef } from 'react'
import { X, Search, Check, Target } from 'lucide-react'
import { watchlistService } from '@/services/watchlistService'
import type { AddStockToWatchlistData, WatchlistItem } from '@/types/watchlist'
import { WATCHLIST_MESSAGES } from '@/constants/watchlist'
import axios from 'axios'

interface AddStockModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  watchlistId: number
  editingItem?: WatchlistItem | null
}

interface SearchResult {
  symbol: string
  name: string
  type: string
  region: string
  currency: string
  match_score: number
}

export default function AddStockModal({
  isOpen,
  onClose,
  onSuccess,
  watchlistId,
  editingItem = null
}: AddStockModalProps) {
  const [formData, setFormData] = useState<AddStockToWatchlistData>({
    stock: '',
    target_entry_price: null,
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
    if (editingItem) {
      setFormData({
        stock: editingItem.stock_symbol,
        target_entry_price: editingItem.target_entry_price ? parseFloat(editingItem.target_entry_price) : null,
        notes: editingItem.notes || ''
      })
    } else {
      setFormData({
        stock: '',
        target_entry_price: null,
        notes: ''
      })
      setSelectedStock(null)
      setSearchResults([])
      setShowSearchResults(false)
    }
    setError(null)
  }, [editingItem, isOpen])

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

      if (error.response?.status === 429) {
        setError(WATCHLIST_MESSAGES.ERROR.NOT_OBSERVED)
      }
    } finally {
      setSearching(false)
    }
  }

  // 디바운스된 검색 처리
  const handleSymbolSearch = (value: string) => {
    setFormData({ ...formData, stock: value.toUpperCase() })

    if (searchTimer) {
      clearTimeout(searchTimer)
    }

    const timer = setTimeout(() => {
      searchSymbols(value)
    }, 300)

    setSearchTimer(timer)
  }

  // 검색 결과 선택 처리
  const handleSelectStock = (result: SearchResult) => {
    setFormData({ ...formData, stock: result.symbol })
    setSelectedStock(result)
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

    if (!formData.stock.trim()) {
      setError(WATCHLIST_MESSAGES.ERROR.VALIDATION)
      return
    }

    setLoading(true)

    try {
      if (editingItem) {
        // 수정 모드
        await watchlistService.updateStockSettings(watchlistId, editingItem.stock_symbol, {
          target_entry_price: formData.target_entry_price,
          notes: formData.notes
        })
      } else {
        // 추가 모드
        await watchlistService.addStock(watchlistId, formData)
      }
      onSuccess()
      onClose()
    } catch (err: any) {
      console.error('종목 저장 실패:', err)

      if (err.response) {
        const status = err.response.status
        const data = err.response.data

        if (status === 400) {
          if (data.stock) {
            setError(data.stock[0])
          } else if (data.detail) {
            setError(data.detail)
          } else if (data.non_field_errors) {
            setError(data.non_field_errors[0])
          } else {
            setError(WATCHLIST_MESSAGES.ERROR.VALIDATION)
          }
        } else if (status === 401) {
          setError(WATCHLIST_MESSAGES.ERROR.AUTH_REQUIRED)
        } else if (status === 404) {
          setError(WATCHLIST_MESSAGES.ERROR.NOT_FOUND)
        } else {
          setError(WATCHLIST_MESSAGES.ERROR.UNKNOWN)
        }
      } else {
        setError(WATCHLIST_MESSAGES.ERROR.NETWORK)
      }
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
            {editingItem ? WATCHLIST_MESSAGES.MODAL.EDIT_STOCK : WATCHLIST_MESSAGES.MODAL.ADD_STOCK}
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
                {WATCHLIST_MESSAGES.FIELD.STOCK_SYMBOL} {WATCHLIST_MESSAGES.FIELD.REQUIRED}
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
                  placeholder={WATCHLIST_MESSAGES.PLACEHOLDER.STOCK_SYMBOL}
                  disabled={!!editingItem}
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
                {!searching && !editingItem && (
                  <Search className="absolute right-3 top-2.5 h-5 w-5 text-gray-400" />
                )}
              </div>

              {/* Search Results Dropdown */}
              {showSearchResults && searchResults.length > 0 && !editingItem && (
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
                                {WATCHLIST_MESSAGES.STATUS.BEST_MATCH}
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
                      </div>
                    </button>
                  ))}
                </div>
              )}

              {/* Selected Stock Info */}
              {selectedStock && !editingItem && (
                <div className="mt-2 p-2 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                  <div className="flex items-center space-x-2">
                    <Check className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                    <span className="text-sm text-blue-700 dark:text-blue-300">
                      {WATCHLIST_MESSAGES.STATUS.SELECTED}: <span className="font-semibold">{selectedStock.name}</span> ({selectedStock.symbol})
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* Target Entry Price */}
            <div>
              <label htmlFor="target_entry_price" className="flex items-center space-x-2 text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                <Target className="h-4 w-4" />
                <span>{WATCHLIST_MESSAGES.FIELD.TARGET_PRICE_USD} {WATCHLIST_MESSAGES.FIELD.OPTIONAL}</span>
              </label>
              <input
                type="number"
                id="target_entry_price"
                value={formData.target_entry_price ?? ''}
                onChange={(e) => setFormData({
                  ...formData,
                  target_entry_price: e.target.value ? parseFloat(e.target.value) : null
                })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                placeholder={WATCHLIST_MESSAGES.PLACEHOLDER.TARGET_PRICE}
                step="0.01"
                min="0"
              />
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                {WATCHLIST_MESSAGES.DESCRIPTION.TARGET_PRICE}
              </p>
            </div>

            {/* Notes */}
            <div>
              <label htmlFor="notes" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {WATCHLIST_MESSAGES.FIELD.NOTES} {WATCHLIST_MESSAGES.FIELD.OPTIONAL}
              </label>
              <textarea
                id="notes"
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                rows={3}
                placeholder={WATCHLIST_MESSAGES.PLACEHOLDER.NOTES}
                maxLength={500}
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
          <div className="mt-6 flex justify-end space-x-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white font-medium"
            >
              {WATCHLIST_MESSAGES.LABEL.CANCEL}
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
                  {WATCHLIST_MESSAGES.LABEL.SAVING}
                </span>
              ) : (
                editingItem ? WATCHLIST_MESSAGES.LABEL.EDIT : WATCHLIST_MESSAGES.LABEL.ADD_STOCK
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

'use client'

import { useState, useEffect } from 'react'
import { X } from 'lucide-react'
import { watchlistService } from '@/services/watchlistService'
import type { Watchlist, CreateWatchlistData, UpdateWatchlistData } from '@/types/watchlist'

interface WatchlistModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  editingWatchlist?: Watchlist | null
}

export default function WatchlistModal({
  isOpen,
  onClose,
  onSuccess,
  editingWatchlist = null
}: WatchlistModalProps) {
  const [formData, setFormData] = useState<CreateWatchlistData>({
    name: '',
    description: ''
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (editingWatchlist) {
      setFormData({
        name: editingWatchlist.name,
        description: editingWatchlist.description || ''
      })
    } else {
      setFormData({
        name: '',
        description: ''
      })
    }
    setError(null)
  }, [editingWatchlist, isOpen])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!formData.name.trim()) {
      setError('리스트 이름을 입력해주세요.')
      return
    }

    setLoading(true)

    try {
      if (editingWatchlist) {
        const updateData: UpdateWatchlistData = {
          name: formData.name,
          description: formData.description
        }
        await watchlistService.updateWatchlist(editingWatchlist.id, updateData)
      } else {
        await watchlistService.createWatchlist(formData)
      }
      onSuccess()
      onClose()
    } catch (err: any) {
      console.error('관심종목 리스트 저장 실패:', err)

      if (err.response) {
        const status = err.response.status
        const data = err.response.data

        if (status === 400) {
          if (data.name) {
            setError(data.name[0])
          } else if (data.detail) {
            setError(data.detail)
          } else {
            setError('입력값을 확인해주세요.')
          }
        } else if (status === 401) {
          setError('인증이 필요합니다. 다시 로그인해주세요.')
        } else if (status === 403) {
          setError('권한이 없습니다.')
        } else {
          setError('오류가 발생했습니다.')
        }
      } else {
        setError('서버와 연결할 수 없습니다.')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async () => {
    if (!editingWatchlist || !confirm('정말 이 관심종목 리스트를 삭제하시겠습니까?')) {
      return
    }

    setLoading(true)
    try {
      await watchlistService.deleteWatchlist(editingWatchlist.id)
      onSuccess()
      onClose()
    } catch (err: any) {
      console.error('관심종목 리스트 삭제 실패:', err)
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
            {editingWatchlist ? '관심종목 리스트 수정' : '새 관심종목 리스트'}
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
            {/* Name */}
            <div>
              <label htmlFor="name" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                리스트 이름 *
              </label>
              <input
                type="text"
                id="name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                placeholder="예: 기술주 관심목록"
                required
                maxLength={100}
              />
            </div>

            {/* Description */}
            <div>
              <label htmlFor="description" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                설명 (선택)
              </label>
              <textarea
                id="description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                rows={3}
                placeholder="이 리스트에 대한 설명을 입력하세요..."
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
          <div className="mt-6 flex justify-between">
            <div>
              {editingWatchlist && (
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
                  editingWatchlist ? '수정' : '생성'
                )}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}

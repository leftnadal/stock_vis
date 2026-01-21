'use client'

import { useState, useEffect } from 'react'
import { Plus, ListPlus, Loader2, AlertCircle } from 'lucide-react'
import { watchlistService } from '@/services/watchlistService'
import { AuthGuard } from '@/components/auth/AuthGuard'
import WatchlistCard from '@/components/watchlist/WatchlistCard'
import WatchlistItemRow from '@/components/watchlist/WatchlistItemRow'
import WatchlistModal from '@/components/watchlist/WatchlistModal'
import AddStockModal from '@/components/watchlist/AddStockModal'
import WatchlistErrorBoundary from '@/components/watchlist/WatchlistErrorBoundary'
import { WATCHLIST_MESSAGES } from '@/constants/watchlist'
import type { Watchlist, WatchlistItem } from '@/types/watchlist'

function WatchlistPageContent() {
  const [watchlists, setWatchlists] = useState<Watchlist[]>([])
  const [selectedWatchlist, setSelectedWatchlist] = useState<Watchlist | null>(null)
  const [watchlistItems, setWatchlistItems] = useState<WatchlistItem[]>([])
  const [loading, setLoading] = useState(true)
  const [itemsLoading, setItemsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Modal states
  const [isWatchlistModalOpen, setIsWatchlistModalOpen] = useState(false)
  const [isAddStockModalOpen, setIsAddStockModalOpen] = useState(false)
  const [editingWatchlist, setEditingWatchlist] = useState<Watchlist | null>(null)
  const [editingItem, setEditingItem] = useState<WatchlistItem | null>(null)

  // 관심종목 리스트 목록 로드
  const loadWatchlists = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await watchlistService.getWatchlists()
      setWatchlists(data)

      // 첫 번째 리스트를 자동 선택
      if (data.length > 0 && !selectedWatchlist) {
        setSelectedWatchlist(data[0])
      }
    } catch (err: any) {
      console.error('관심종목 리스트 로드 실패:', err)
      setError(WATCHLIST_MESSAGES.ERROR.LOAD_LISTS)
    } finally {
      setLoading(false)
    }
  }

  // 선택된 리스트의 종목들 로드
  const loadWatchlistItems = async (watchlistId: number) => {
    setItemsLoading(true)
    try {
      const items = await watchlistService.getWatchlistStocks(watchlistId)
      setWatchlistItems(items)
    } catch (err: any) {
      console.error('종목 목록 로드 실패:', err)
      setWatchlistItems([])
    } finally {
      setItemsLoading(false)
    }
  }

  // 초기 로드
  useEffect(() => {
    loadWatchlists()
  }, [])

  // 선택된 리스트가 변경되면 종목 로드
  useEffect(() => {
    if (selectedWatchlist) {
      loadWatchlistItems(selectedWatchlist.id)
    } else {
      setWatchlistItems([])
    }
  }, [selectedWatchlist])

  // 리스트 생성/수정 성공
  const handleWatchlistSuccess = () => {
    loadWatchlists()
    setEditingWatchlist(null)
  }

  // 종목 추가/수정 성공
  const handleStockSuccess = () => {
    if (selectedWatchlist) {
      loadWatchlistItems(selectedWatchlist.id)
      loadWatchlists() // stock_count 업데이트를 위해
    }
    setEditingItem(null)
  }

  // 리스트 편집
  const handleEditWatchlist = (watchlist: Watchlist) => {
    setEditingWatchlist(watchlist)
    setIsWatchlistModalOpen(true)
  }

  // 리스트 삭제
  const handleDeleteWatchlist = async (watchlist: Watchlist) => {
    if (!confirm(WATCHLIST_MESSAGES.CONFIRM.DELETE_LIST(watchlist.name))) {
      return
    }

    try {
      await watchlistService.deleteWatchlist(watchlist.id)

      // 삭제된 리스트가 선택된 리스트였다면 선택 해제
      if (selectedWatchlist?.id === watchlist.id) {
        setSelectedWatchlist(null)
      }

      loadWatchlists()
    } catch (err: any) {
      console.error('리스트 삭제 실패:', err)
      alert(WATCHLIST_MESSAGES.ERROR.DELETE_LIST)
    }
  }

  // 종목 편집
  const handleEditItem = (item: WatchlistItem) => {
    setEditingItem(item)
    setIsAddStockModalOpen(true)
  }

  // 종목 제거
  const handleRemoveItem = async (item: WatchlistItem) => {
    if (!selectedWatchlist) return

    if (!confirm(WATCHLIST_MESSAGES.CONFIRM.REMOVE_STOCK(item.stock_symbol))) {
      return
    }

    try {
      await watchlistService.removeStock(selectedWatchlist.id, item.stock_symbol)
      loadWatchlistItems(selectedWatchlist.id)
      loadWatchlists() // stock_count 업데이트
    } catch (err: any) {
      console.error('종목 제거 실패:', err)
      alert(WATCHLIST_MESSAGES.ERROR.REMOVE_STOCK)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="flex flex-col items-center space-y-4">
          <Loader2 className="h-12 w-12 text-blue-600 animate-spin" />
          <p className="text-gray-600 dark:text-gray-400">{WATCHLIST_MESSAGES.LABEL.LOADING}</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="flex flex-col items-center space-y-4">
          <AlertCircle className="h-12 w-12 text-red-600" />
          <p className="text-red-600">{error}</p>
          <button
            onClick={loadWatchlists}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            {WATCHLIST_MESSAGES.LABEL.RETRY}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            {WATCHLIST_MESSAGES.LABEL.WATCHLIST}
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            {WATCHLIST_MESSAGES.DESCRIPTION.WATCHLIST_PAGE}
          </p>
        </div>

        {watchlists.length === 0 ? (
          // 빈 상태
          <div className="bg-white dark:bg-gray-800 rounded-xl p-12 text-center">
            <ListPlus className="h-16 w-16 text-gray-400 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
              {WATCHLIST_MESSAGES.DESCRIPTION.NO_LISTS}
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              {WATCHLIST_MESSAGES.DESCRIPTION.CREATE_FIRST_LIST}
            </p>
            <button
              onClick={() => {
                setEditingWatchlist(null)
                setIsWatchlistModalOpen(true)
              }}
              className="inline-flex items-center space-x-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
            >
              <Plus className="h-5 w-5" />
              <span>{WATCHLIST_MESSAGES.LABEL.CREATE_LIST}</span>
            </button>
          </div>
        ) : (
          // 리스트 및 종목 표시
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* 좌측: 관심종목 리스트 목록 */}
            <div className="lg:col-span-1">
              <div className="bg-white dark:bg-gray-800 rounded-xl p-4">
                <div className="flex justify-between items-center mb-4">
                  <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                    {WATCHLIST_MESSAGES.LABEL.MY_LISTS}
                  </h2>
                  <button
                    onClick={() => {
                      setEditingWatchlist(null)
                      setIsWatchlistModalOpen(true)
                    }}
                    className="p-2 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors"
                    title={WATCHLIST_MESSAGES.LABEL.CREATE_LIST}
                  >
                    <Plus className="h-5 w-5" />
                  </button>
                </div>

                <div className="space-y-3">
                  {watchlists.map((watchlist) => (
                    <WatchlistCard
                      key={watchlist.id}
                      watchlist={watchlist}
                      isSelected={selectedWatchlist?.id === watchlist.id}
                      onClick={() => setSelectedWatchlist(watchlist)}
                      onEdit={() => handleEditWatchlist(watchlist)}
                      onDelete={() => handleDeleteWatchlist(watchlist)}
                    />
                  ))}
                </div>
              </div>
            </div>

            {/* 우측: 선택된 리스트의 종목들 */}
            <div className="lg:col-span-2">
              {selectedWatchlist ? (
                <div className="bg-white dark:bg-gray-800 rounded-xl overflow-hidden">
                  {/* 헤더 */}
                  <div className="p-6 border-b border-gray-200 dark:border-gray-700">
                    <div className="flex justify-between items-center">
                      <div>
                        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                          {selectedWatchlist.name}
                        </h2>
                        {selectedWatchlist.description && (
                          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                            {selectedWatchlist.description}
                          </p>
                        )}
                      </div>
                      <button
                        onClick={() => {
                          setEditingItem(null)
                          setIsAddStockModalOpen(true)
                        }}
                        className="inline-flex items-center space-x-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
                      >
                        <Plus className="h-4 w-4" />
                        <span>{WATCHLIST_MESSAGES.LABEL.ADD_STOCK}</span>
                      </button>
                    </div>
                  </div>

                  {/* 종목 테이블 */}
                  {itemsLoading ? (
                    <div className="p-12 text-center">
                      <Loader2 className="h-8 w-8 text-blue-600 animate-spin mx-auto" />
                    </div>
                  ) : watchlistItems.length === 0 ? (
                    <div className="p-12 text-center">
                      <p className="text-gray-600 dark:text-gray-400 mb-4">
                        {WATCHLIST_MESSAGES.DESCRIPTION.EMPTY_LIST}
                      </p>
                      <button
                        onClick={() => {
                          setEditingItem(null)
                          setIsAddStockModalOpen(true)
                        }}
                        className="inline-flex items-center space-x-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
                      >
                        <Plus className="h-4 w-4" />
                        <span>{WATCHLIST_MESSAGES.LABEL.FIRST_STOCK}</span>
                      </button>
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead className="bg-gray-50 dark:bg-gray-700">
                          <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                              {WATCHLIST_MESSAGES.FIELD.STOCK_NAME}
                            </th>
                            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                              {WATCHLIST_MESSAGES.FIELD.CURRENT_PRICE}
                            </th>
                            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                              {WATCHLIST_MESSAGES.FIELD.CHANGE}
                            </th>
                            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                              {WATCHLIST_MESSAGES.FIELD.TARGET_PRICE}
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                              {WATCHLIST_MESSAGES.FIELD.NOTES}
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                              {WATCHLIST_MESSAGES.FIELD.ADDED_DATE}
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                              {WATCHLIST_MESSAGES.FIELD.ACTION}
                            </th>
                          </tr>
                        </thead>
                        <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                          {watchlistItems.map((item) => (
                            <WatchlistItemRow
                              key={item.id}
                              item={item}
                              onEdit={() => handleEditItem(item)}
                              onRemove={() => handleRemoveItem(item)}
                            />
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              ) : (
                <div className="bg-white dark:bg-gray-800 rounded-xl p-12 text-center">
                  <p className="text-gray-600 dark:text-gray-400">
                    {WATCHLIST_MESSAGES.DESCRIPTION.SELECT_LIST}
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Modals */}
      <WatchlistModal
        isOpen={isWatchlistModalOpen}
        onClose={() => {
          setIsWatchlistModalOpen(false)
          setEditingWatchlist(null)
        }}
        onSuccess={handleWatchlistSuccess}
        editingWatchlist={editingWatchlist}
      />

      {selectedWatchlist && (
        <AddStockModal
          isOpen={isAddStockModalOpen}
          onClose={() => {
            setIsAddStockModalOpen(false)
            setEditingItem(null)
          }}
          onSuccess={handleStockSuccess}
          watchlistId={selectedWatchlist.id}
          editingItem={editingItem}
        />
      )}
    </div>
  )
}

export default function WatchlistPage() {
  return (
    <AuthGuard>
      <WatchlistErrorBoundary>
        <WatchlistPageContent />
      </WatchlistErrorBoundary>
    </AuthGuard>
  )
}

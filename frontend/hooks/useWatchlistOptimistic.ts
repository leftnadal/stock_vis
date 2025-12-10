'use client'

import { useState, useCallback } from 'react'
import { watchlistService } from '@/services/watchlistService'
import type {
  Watchlist,
  WatchlistItem,
  AddStockToWatchlistData,
  UpdateWatchlistItemData
} from '@/types/watchlist'

interface UseWatchlistOptimisticReturn {
  // 종목 추가 (낙관적 업데이트)
  addStockOptimistic: (
    watchlistId: number,
    data: AddStockToWatchlistData,
    onOptimisticUpdate: (tempItem: WatchlistItem) => void,
    onSuccess?: () => void,
    onError?: (error: any) => void
  ) => Promise<void>

  // 종목 제거 (낙관적 업데이트)
  removeStockOptimistic: (
    watchlistId: number,
    symbol: string,
    onOptimisticUpdate: () => void,
    onSuccess?: () => void,
    onError?: (rollback: () => void, error: any) => void
  ) => Promise<void>

  // 종목 설정 수정 (낙관적 업데이트)
  updateStockOptimistic: (
    watchlistId: number,
    symbol: string,
    data: UpdateWatchlistItemData,
    onOptimisticUpdate: (tempItem: Partial<WatchlistItem>) => void,
    onSuccess?: () => void,
    onError?: (error: any) => void
  ) => Promise<void>

  loading: boolean
  error: string | null
}

export function useWatchlistOptimistic(): UseWatchlistOptimisticReturn {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  /**
   * 종목 추가 (낙관적 업데이트)
   * 1. UI 먼저 업데이트 (임시 ID로 새 항목 표시)
   * 2. API 호출
   * 3. 성공 시 실제 데이터로 교체, 실패 시 롤백
   */
  const addStockOptimistic = useCallback(async (
    watchlistId: number,
    data: AddStockToWatchlistData,
    onOptimisticUpdate: (tempItem: WatchlistItem) => void,
    onSuccess?: () => void,
    onError?: (error: any) => void
  ) => {
    setLoading(true)
    setError(null)

    // 임시 항목 생성 (낙관적 업데이트)
    const tempItem: WatchlistItem = {
      id: Date.now(), // 임시 ID
      stock_symbol: data.stock,
      stock_name: data.stock, // 실제 이름은 API에서 가져옴
      current_price: '0.00',
      change: '0.00',
      change_percent: '0.00',
      previous_close: '0.00',
      target_entry_price: data.target_entry_price?.toString() || null,
      distance_from_entry: null,
      is_below_target: null,
      notes: data.notes || '',
      position_order: 0,
      added_at: new Date().toISOString(),
    }

    // UI 먼저 업데이트
    onOptimisticUpdate(tempItem)

    try {
      // API 호출
      const realItem = await watchlistService.addStock(watchlistId, data)

      // 성공 시 콜백
      if (onSuccess) {
        onSuccess()
      }
    } catch (err: any) {
      console.error('종목 추가 실패:', err)
      setError(err.response?.data?.detail || '종목 추가에 실패했습니다.')

      // 실패 시 에러 콜백 (롤백 처리는 부모에서)
      if (onError) {
        onError(err)
      }
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * 종목 제거 (낙관적 업데이트)
   * 1. UI에서 즉시 제거
   * 2. API 호출
   * 3. 실패 시 롤백
   */
  const removeStockOptimistic = useCallback(async (
    watchlistId: number,
    symbol: string,
    onOptimisticUpdate: () => void,
    onSuccess?: () => void,
    onError?: (rollback: () => void, error: any) => void
  ) => {
    setLoading(true)
    setError(null)

    // UI 먼저 업데이트 (항목 제거)
    onOptimisticUpdate()

    try {
      // API 호출
      await watchlistService.removeStock(watchlistId, symbol)

      // 성공 시 콜백
      if (onSuccess) {
        onSuccess()
      }
    } catch (err: any) {
      console.error('종목 제거 실패:', err)
      setError(err.response?.data?.detail || '종목 제거에 실패했습니다.')

      // 실패 시 롤백 콜백 제공
      if (onError) {
        onError(() => {
          // 롤백 로직은 부모에서 구현
        }, err)
      }
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * 종목 설정 수정 (낙관적 업데이트)
   * 1. UI 먼저 업데이트
   * 2. API 호출
   * 3. 실패 시 롤백
   */
  const updateStockOptimistic = useCallback(async (
    watchlistId: number,
    symbol: string,
    data: UpdateWatchlistItemData,
    onOptimisticUpdate: (tempItem: Partial<WatchlistItem>) => void,
    onSuccess?: () => void,
    onError?: (error: any) => void
  ) => {
    setLoading(true)
    setError(null)

    // 임시 업데이트 데이터
    const tempUpdate: Partial<WatchlistItem> = {
      target_entry_price: data.target_entry_price?.toString() || null,
      notes: data.notes,
    }

    // UI 먼저 업데이트
    onOptimisticUpdate(tempUpdate)

    try {
      // API 호출
      await watchlistService.updateStockSettings(watchlistId, symbol, data)

      // 성공 시 콜백
      if (onSuccess) {
        onSuccess()
      }
    } catch (err: any) {
      console.error('종목 수정 실패:', err)
      setError(err.response?.data?.detail || '종목 수정에 실패했습니다.')

      // 실패 시 에러 콜백 (롤백 처리는 부모에서)
      if (onError) {
        onError(err)
      }
    } finally {
      setLoading(false)
    }
  }, [])

  return {
    addStockOptimistic,
    removeStockOptimistic,
    updateStockOptimistic,
    loading,
    error,
  }
}

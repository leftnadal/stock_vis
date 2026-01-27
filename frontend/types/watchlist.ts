// Watchlist 관련 타입 정의

export interface Watchlist {
  id: number
  name: string
  description: string
  stock_count: number
  created_at: string
  updated_at: string
}

export interface WatchlistItem {
  id: number
  stock_symbol: string
  stock_name: string
  current_price: string
  change: string
  change_percent: string
  previous_close: string
  target_entry_price: string | null
  distance_from_entry: number | null
  is_below_target: boolean | null
  notes: string
  position_order: number
  added_at: string
}

export interface CreateWatchlistData {
  name: string
  description?: string
}

export interface UpdateWatchlistData {
  name?: string
  description?: string
}

export interface AddStockToWatchlistData {
  stock: string  // 종목 심볼 (Backend expects 'stock' field)
  target_entry_price?: number | null
  notes?: string
}

export interface UpdateWatchlistItemData {
  target_entry_price?: number | null
  notes?: string
  position_order?: number
}

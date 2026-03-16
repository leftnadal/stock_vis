// RAG 바구니 상태 관리

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { BasketItem } from '@/types/rag';

interface BasketStore {
  items: BasketItem[];
  isOpen: boolean;

  // 액션들
  addItem: (item: Omit<BasketItem, 'id' | 'added_at'>) => void;
  removeItem: (id: number) => void;
  clearBasket: () => void;
  toggleBasket: () => void;
  getFormattedContext: () => string;
}

export const useBasketStore = create<BasketStore>()(
  persist(
    (set, get) => ({
      items: [],
      isOpen: false,

      addItem: (item) => set((state) => ({
        items: [
          ...state.items,
          {
            ...item,
            id: Date.now() + Math.floor(Math.random() * 1000),
            added_at: new Date().toISOString(),
          } as BasketItem,
        ],
      })),

      removeItem: (id) => set((state) => ({
        items: state.items.filter((item) => item.id !== id),
      })),

      clearBasket: () => set({ items: [] }),

      toggleBasket: () => set((state) => ({ isOpen: !state.isOpen })),

      getFormattedContext: () => {
        const { items } = get();
        return items
          .map((item) => {
            const itemType = item.item_type || item.type || 'unknown';
            const content = item.data_snapshot || item.content || {};
            return `[${itemType}] ${item.title}:\n${JSON.stringify(content, null, 2)}`;
          })
          .join('\n\n---\n\n');
      },
    }),
    {
      name: 'rag-basket',
      partialize: (state) => ({ items: state.items }), // isOpen은 저장하지 않음
    }
  )
);
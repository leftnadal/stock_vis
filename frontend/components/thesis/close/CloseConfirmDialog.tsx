'use client'

import { BottomSheet } from '@/components/thesis/common/BottomSheet'
import { AlertTriangle, Loader2 } from 'lucide-react'

interface Props {
  isOpen: boolean
  onClose: () => void
  onConfirm: () => void
  isClosing: boolean
}

export function CloseConfirmDialog({ isOpen, onClose, onConfirm, isClosing }: Props) {
  return (
    <BottomSheet isOpen={isOpen} onClose={isClosing ? () => {} : onClose} title="가설 마감">
      <div className="flex items-start gap-3 mb-5 p-3 bg-yellow-900/20 border border-yellow-800/50 rounded-xl">
        <AlertTriangle size={18} className="text-yellow-500 flex-shrink-0 mt-0.5" />
        <p className="text-yellow-400 text-xs leading-relaxed">
          마감하면 되돌릴 수 없어요. 지표 추적이 중단되고 결과가 기록됩니다.
        </p>
      </div>

      <div className="space-y-2">
        <button
          onClick={onConfirm}
          disabled={isClosing}
          className="w-full py-3.5 bg-red-600 text-white text-sm font-medium
                     rounded-xl active:scale-[0.98] transition-transform
                     disabled:opacity-50 disabled:cursor-not-allowed
                     flex items-center justify-center gap-2"
        >
          {isClosing ? (
            <>
              <Loader2 size={16} className="animate-spin" />
              마감 중...
            </>
          ) : (
            '마감하기'
          )}
        </button>
        <button
          onClick={onClose}
          disabled={isClosing}
          className="w-full py-3 text-gray-400 text-sm
                     disabled:opacity-50 disabled:cursor-not-allowed"
        >
          취소
        </button>
      </div>
    </BottomSheet>
  )
}

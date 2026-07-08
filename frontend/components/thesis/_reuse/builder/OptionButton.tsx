'use client'

import { Pencil, Check, Info } from 'lucide-react'
import type { ConversationButton } from '@/lib/thesis/types'
import { useLongPress } from '@/hooks/useLongPress'

interface Props {
  button: ConversationButton
  mode: 'single' | 'multi'
  selected?: boolean
  onClick: () => void
  onShowExplanation?: () => void
}

export function OptionButton({ button, mode, selected, onClick, onShowExplanation }: Props) {
  const longPress = useLongPress({
    threshold: 500,
    onLongPress: () => onShowExplanation?.(),
    onClick,
  })

  const hasExplanation = !!button.long_press_hint && !!onShowExplanation

  const pressHandlers = hasExplanation ? {
    onClick: longPress.handleClick,
    onMouseDown: longPress.handlePressStart,
    onMouseUp: longPress.handlePressEnd,
    onMouseLeave: longPress.handlePressEnd,
    onTouchStart: longPress.handlePressStart,
    onTouchEnd: longPress.handlePressEnd,
  } : { onClick }

  if (button.type === 'text_input') {
    return (
      <button
        onClick={onClick}
        className="w-full flex items-center gap-3 border border-dashed border-gray-600
                   rounded-xl px-5 py-4 text-left text-gray-400 text-sm
                   hover:border-gray-500 transition-colors active:scale-[0.98]"
      >
        <Pencil size={16} />
        {button.label}
      </button>
    )
  }

  return (
    <button
      {...pressHandlers}
      className={`w-full flex items-center gap-3 rounded-xl px-5 text-left
                  text-sm transition-all active:scale-[0.98]
                  ${mode === 'multi' ? 'min-h-[52px] py-3' : 'min-h-[56px] py-4'}
                  ${selected
                    ? 'border border-blue-500 bg-blue-900/20 text-blue-300'
                    : 'border border-gray-700 bg-transparent text-gray-200 hover:border-gray-600'}`}
    >
      {mode === 'multi' && (
        <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0
                         ${selected ? 'border-blue-500 bg-blue-500' : 'border-gray-600'}`}>
          {selected && <Check size={12} className="text-white" />}
        </div>
      )}
      <span className="flex-1">{button.label}</span>
      {hasExplanation && (
        <>
          <span className="text-[10px] text-gray-600 sm:hidden">꾹 누르면 설명</span>
          <span
            role="button"
            tabIndex={0}
            onClick={(e) => { e.stopPropagation(); onShowExplanation?.() }}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.stopPropagation(); onShowExplanation?.() } }}
            className="hidden sm:flex p-1 text-gray-600 hover:text-gray-400 transition-colors cursor-pointer"
            aria-label={`${button.label} 설명 보기`}
          >
            <Info size={14} />
          </span>
        </>
      )}
    </button>
  )
}

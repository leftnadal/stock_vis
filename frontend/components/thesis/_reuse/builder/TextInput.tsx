'use client'

import { useState } from 'react'
import { Send } from 'lucide-react'

interface Props {
  placeholder?: string
  onSubmit: (text: string) => void
  disabled?: boolean
}

export function TextInput({ placeholder, onSubmit, disabled }: Props) {
  const [text, setText] = useState('')

  const handleSubmit = () => {
    const trimmed = text.trim()
    if (!trimmed || disabled) return
    onSubmit(trimmed)
    setText('')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div className="border-t border-gray-800 bg-gray-950 px-4 py-3">
      <div className="flex items-end gap-2">
        <textarea
          value={text}
          onChange={(e) => {
            setText(e.target.value)
            e.target.style.height = 'auto'
            e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`
          }}
          onKeyDown={handleKeyDown}
          placeholder={placeholder ?? '시장에 대한 생각을 자유롭게...'}
          disabled={disabled}
          rows={1}
          className="flex-1 bg-gray-900 border border-gray-700 rounded-xl px-4 py-3
                     text-white text-sm placeholder-gray-600 resize-none
                     focus:outline-none focus:border-gray-600
                     min-h-[44px] max-h-[120px]"
        />
        <button
          onClick={handleSubmit}
          disabled={!text.trim() || disabled}
          className={`p-3 rounded-xl transition-colors flex-shrink-0
                      ${text.trim() && !disabled
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-800 text-gray-600'}`}
        >
          <Send size={18} />
        </button>
      </div>
    </div>
  )
}

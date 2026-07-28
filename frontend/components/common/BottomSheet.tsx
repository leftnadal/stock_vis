'use client'

import { useEffect, useCallback } from 'react'

interface Props {
  isOpen: boolean
  onClose: () => void
  title?: string
  children: React.ReactNode
}

export function BottomSheet({ isOpen, onClose, title, children }: Props) {
  const handleEscape = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') onClose()
  }, [onClose])

  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleEscape)
      document.body.style.overflow = 'hidden'
    }
    return () => {
      document.removeEventListener('keydown', handleEscape)
      document.body.style.overflow = ''
    }
  }, [isOpen, handleEscape])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50">
      <div
        className="absolute inset-0 bg-black/60 transition-opacity"
        onClick={(e) => { e.stopPropagation(); onClose() }}
      />
      <div className="absolute bottom-0 left-0 right-0
                       bg-gray-900 rounded-t-2xl max-h-[50vh] overflow-y-auto
                       max-w-2xl mx-auto animate-slideUp">
        <div className="flex justify-center py-3">
          <div className="w-8 h-1 bg-gray-600 rounded-full" />
        </div>
        <div className="px-5 pb-8">
          {title && (
            <h3 className="text-white text-base font-medium mb-3">{title}</h3>
          )}
          {children}
        </div>
      </div>
    </div>
  )
}

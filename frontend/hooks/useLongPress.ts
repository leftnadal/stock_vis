import { useRef, useCallback, useEffect } from 'react'

interface UseLongPressOptions {
  threshold?: number
  onLongPress: () => void
  onClick: () => void
}

interface UseLongPressReturn {
  handleClick: () => void
  handlePressStart: () => void
  handlePressEnd: () => void
}

export function useLongPress({
  threshold = 500,
  onLongPress,
  onClick,
}: UseLongPressOptions): UseLongPressReturn {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const longPressTriggeredRef = useRef(false)

  const safeThreshold = Math.max(threshold, 100)

  const handlePressStart = useCallback(() => {
    longPressTriggeredRef.current = false
    timerRef.current = setTimeout(() => {
      longPressTriggeredRef.current = true
      onLongPress()
    }, safeThreshold)
  }, [onLongPress, safeThreshold])

  const handlePressEnd = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current)
      timerRef.current = null
    }
  }, [])

  const handleClick = useCallback(() => {
    if (longPressTriggeredRef.current) {
      longPressTriggeredRef.current = false
      return
    }
    onClick()
  }, [onClick])

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [])

  return { handleClick, handlePressStart, handlePressEnd }
}

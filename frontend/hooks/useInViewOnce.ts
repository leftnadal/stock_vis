/**
 * INC-P16-1 Part B — 요소가 뷰포트에 처음 진입하면 true로 래치(이후 유지)하는 훅.
 *
 * fold 아래 카드의 fetch 시점을 마운트 → 뷰포트 진입으로 늦춰, 초기 동시 요청 수를
 * 줄인다(429 캐스케이드 완화). 한 번 진입하면 관측을 끊고 계속 true — 스크롤 왕복에도
 * 재fetch/재토글 없음. IntersectionObserver 미지원(SSR·구형) 환경에서는 초기값을 true로
 * 폴백해 기존 즉시 fetch 동작을 보존한다(기능 저하 없음).
 */
import { useEffect, useRef, useState } from 'react'

export function useInViewOnce<T extends HTMLElement = HTMLElement>(
  rootMargin: string = '200px',
) {
  const ref = useRef<T | null>(null)
  // IntersectionObserver 미지원이면 즉시 진입(폴백). 지원 시 false로 시작 → 관측 후 래치.
  const [hasEntered, setHasEntered] = useState<boolean>(
    () => typeof IntersectionObserver === 'undefined',
  )

  useEffect(() => {
    if (hasEntered) return
    const el = ref.current
    if (!el) return
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) {
          setHasEntered(true)
          observer.disconnect()
        }
      },
      { rootMargin },
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [hasEntered, rootMargin])

  return { ref, hasEntered }
}

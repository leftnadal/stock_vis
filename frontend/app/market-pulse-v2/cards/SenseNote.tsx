'use client'

/**
 * Phase 1.5 S4 — 카드 "감각 유추" 표시 블록(dumb, additive).
 *
 * sense가 있으면 한 줄 해설 렌더, 없으면 **아무것도 렌더하지 않는다**(빈 줄·플레이스홀더·
 * 에러 텍스트 금지 = fallback 상태3). 밴드·raw 표시와 무관한 추가 영역.
 */
export function SenseNote({ sense }: { sense?: string | null }) {
  if (!sense) return null
  return (
    <p
      className="mt-2 text-xs leading-relaxed text-slate-600 border-l-2 border-slate-200 pl-2"
      data-testid="sense-note"
    >
      {sense}
    </p>
  )
}

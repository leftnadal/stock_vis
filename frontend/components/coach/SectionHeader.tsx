/**
 * SectionHeader — Slice 17 Step 0 신규.
 *
 * CommentaryCard 내부에서 5회 반복되던 (icon + h3 라벨) 패턴 통합.
 * Tailwind 클래스는 기존 마크업 그대로 보존 — 행위 보존 추출.
 *
 * - icon: lucide 컴포넌트 (Target, ListChecks, BarChart3, AlertTriangle 등)
 * - title: 섹션 라벨 (예: '핵심 관찰', '추천 액션')
 *
 * 자유로운 아이콘 색상 전달을 위해 lucide의 className은 호출처에서 설정 후
 * 본 컴포넌트의 icon prop으로 넘긴다 (이미 색상이 박혀 있는 인스턴스 형태).
 */

'use client'

import type { ReactNode } from 'react'

interface SectionHeaderProps {
  /** lucide 아이콘 인스턴스 (className 포함하여 호출처에서 결정). */
  icon: ReactNode
  title: string
}

export default function SectionHeader({ icon, title }: SectionHeaderProps) {
  return (
    <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-700">
      {icon}
      {title}
    </h3>
  )
}

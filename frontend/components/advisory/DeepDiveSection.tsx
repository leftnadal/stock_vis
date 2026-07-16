'use client'

// 심층 진단 섹션 (Slice 20b, Part E — D4 "섹션만").
// coach E1~E6은 전부 포트폴리오 수준(종목 컨텍스트 0) → 딥링크 없이 6개 정적 타일만.
// E 화면 자체는 무변경 — 라우팅 진입점만 가산.
import Link from 'next/link'
import { ArrowRight } from 'lucide-react'

interface DeepDiveTile {
  href: string
  title: string
  desc: string
}

// STEP 0(d) 분류표의 실제 명칭·설명 (전부 포트폴리오 수준)
const TILES: DeepDiveTile[] = [
  { href: '/coach/e1', title: 'GARP 진단', desc: '성장-가치 균형 관점으로 보유를 진단' },
  { href: '/coach/e2', title: '포트폴리오 종합 진단', desc: '섹터 비중·수익률까지 종합 관점' },
  { href: '/coach/e3', title: '집중도 분석', desc: 'HHI·상위 비중·섹터 집중도 분산 진단' },
  { href: '/coach/e4', title: '대화 코치', desc: '맥락을 이어가며 자유롭게 질문' },
  { href: '/coach/e5', title: '추출 + 시계열 분석', desc: '추출값과 추세를 종합 해석' },
  { href: '/coach/e6', title: '비교 분석', desc: '종목별 결과를 비교 관점에서 진단' },
]

export function DeepDiveSection() {
  return (
    <section data-testid="deep-dive-section" className="flex flex-col gap-2">
      <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300">심층 진단</h2>
      <p className="text-xs text-gray-400">
        AI 코치와 함께 특정 관점을 깊이 파고드는 화면들입니다.
      </p>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {TILES.map((tile) => (
          <Link
            key={tile.href}
            href={tile.href}
            data-testid={`deep-dive-tile-${tile.href.split('/').pop()}`}
            className="group flex items-center justify-between rounded-xl border border-gray-200 bg-white p-4 shadow-sm transition hover:border-blue-300 dark:border-gray-800 dark:bg-gray-900"
          >
            <div className="min-w-0">
              <div className="text-sm font-semibold text-gray-900 dark:text-gray-100">{tile.title}</div>
              <p className="mt-0.5 truncate text-xs text-gray-400">{tile.desc}</p>
            </div>
            <ArrowRight className="ml-3 h-4 w-4 shrink-0 text-gray-300 transition group-hover:text-blue-500" />
          </Link>
        ))}
      </div>
    </section>
  )
}

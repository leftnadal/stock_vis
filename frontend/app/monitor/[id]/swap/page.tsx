'use client'

// 교체 검토 — 2종 대결 화면 (RECON-SWAP-0813 PART 3-FE). 기존 monitor 라우트 체계 내 하위
// 정적 세그먼트로 배치(신규 최상위 라우트·신규 [id] 동적 세그먼트 아님 — 기존 [id] 재사용).
import { use } from 'react'

import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'

import { AuthGuard } from '@/components/auth/AuthGuard'
import { DuelView } from '@/components/monitor/duel/DuelView'

export default function MonitorSwapPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  return (
    <AuthGuard>
      <div className="mx-auto max-w-3xl px-4 pt-4">
        <Link
          href={`/monitor/${id}`}
          className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-800"
          aria-label="상세로"
        >
          <ArrowLeft size={16} /> 상세로
        </Link>
      </div>
      <DuelView monitorId={id} />
    </AuthGuard>
  )
}

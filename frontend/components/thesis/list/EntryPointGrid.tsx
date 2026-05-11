'use client'

import { useRouter } from 'next/navigation'
import { Plus } from 'lucide-react'

export function EntryPointGrid() {
  const router = useRouter()

  return (
    <button
      onClick={() => router.push('/thesis/new')}
      className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-500
                 text-white font-medium text-sm py-3.5 rounded-xl
                 active:scale-[0.98] transition-all"
    >
      <Plus size={18} />
      <span>새 가설 세우기</span>
    </button>
  )
}

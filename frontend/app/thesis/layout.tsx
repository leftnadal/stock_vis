import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'
import { AlertBell } from '@/components/thesis/common/AlertBell'

export default function ThesisLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-gray-950 animate-fadeIn">
      <div className="max-w-lg mx-auto px-4 pt-4 pb-20">
        <div className="flex items-center justify-between mb-6">
          <Link href="/" className="p-2 -ml-2 text-gray-400 hover:text-white transition-colors">
            <ArrowLeft size={20} />
          </Link>
          <h1 className="text-white text-lg font-bold">가설 통제실</h1>
          <AlertBell />
        </div>
        {children}
      </div>
    </div>
  )
}

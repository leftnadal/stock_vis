'use client'

import { useRouter } from 'next/navigation'
import { MessageSquare, Newspaper, Link2 } from 'lucide-react'

// ── 진입점 정의 ──
// Phase 1에서 렌더링하는 항목만 이 배열에 포함.
// Phase 2에서 Flame(인기 가설), FileText(템플릿) 추가 시 이 배열에 항목을 추가하면 됨.
// enabled=false 항목은 최대 1개만 유지하여 첫인상 완성도를 보장.
interface EntryPoint {
  key: string
  label: string
  icon: React.ComponentType<{ size?: number; className?: string }>
  source: string
  enabled: boolean
}

const VISIBLE_ENTRY_POINTS: EntryPoint[] = [
  { key: 'free_text',   label: '내 생각',         icon: MessageSquare, source: 'free_text',   enabled: true },
  { key: 'news',        label: '오늘 이슈',       icon: Newspaper,     source: 'news',        enabled: true },
  { key: 'chain_sight', label: 'Chain Sight에서', icon: Link2,         source: 'chain_sight', enabled: false },
]

// ── Phase 2에서 추가될 진입점 (현재 렌더링하지 않음) ──
// { key: 'popular',   label: '인기 가설', icon: Flame,    source: 'popular',  enabled: false },
// { key: 'template',  label: '템플릿',    icon: FileText, source: 'template', enabled: false },

export function EntryPointGrid() {
  const router = useRouter()

  const handleClick = (entry: EntryPoint) => {
    if (!entry.enabled) {
      showTemporaryToast('곧 열릴 기능이에요!')
      return
    }
    router.push(`/thesis/new?entry=${entry.source}`)
  }

  return (
    <div className="grid grid-cols-2 gap-3">
      {VISIBLE_ENTRY_POINTS.map((entry) => {
        const Icon = entry.icon
        return (
          <button
            key={entry.key}
            onClick={() => handleClick(entry)}
            className={`flex items-center gap-3 bg-gray-900 border rounded-xl p-4
                       text-left transition-all active:scale-[0.97]
                       ${entry.enabled
                         ? 'border-gray-700 hover:border-gray-600 text-white'
                         : 'border-gray-800 text-gray-500 opacity-60'}
                       ${entry.key === 'chain_sight' ? 'col-span-2' : ''}`}
          >
            <Icon
              size={20}
              className={entry.enabled ? 'text-blue-400' : 'text-gray-600'}
            />
            <span className="text-sm font-medium">{entry.label}</span>
            {!entry.enabled && (
              <span className="ml-auto text-[10px] text-gray-600 bg-gray-800 px-2 py-0.5 rounded-full">
                준비 중
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════
// 임시 Toast — DOM 직접 조작 방식 (M5)
// ──────────────────────────────────────────────────────────────────
// 왜 임시인가:
//   현재 프로젝트에 글로벌 Toast 시스템이 없으므로, React 외부에서
//   DOM을 직접 생성/제거하는 방식으로 구현.
//   이 방식은 React 상태 관리 바깥이라 테스트·접근성·애니메이션 제어가 제한적.
//
// 교체 계획:
//   FE-PR-3(대화형 빌더)에서 Toast가 본격적으로 필요해지는 시점에
//   아래 후보 중 하나를 도입하고 이 함수를 제거할 것:
//   - sonner (4KB, 다크테마 기본 지원, 권장)
//   - react-hot-toast (5KB, 커뮤니티 넓음)
//   - shadcn/ui toast (이미 shadcn 의존성이 있다면 추가 비용 0)
//
// 제약 조건:
//   - 연속 클릭 시 중복 누적 방지 (기존 toast 제거 후 새로 생성)
//   - 2초 후 자연스럽게 제거
//   - 클라이언트 전용 ('use client' 컴포넌트 내부에서만 호출)
// ══════════════════════════════════════════════════════════════════
function showTemporaryToast(message: string) {
  if (typeof window === 'undefined') return

  // 중복 방지: 기존 toast가 있으면 제거
  const existing = document.getElementById('thesis-toast')
  if (existing) existing.remove()

  const toast = document.createElement('div')
  toast.id = 'thesis-toast'
  toast.textContent = message
  toast.className = [
    'fixed bottom-24 left-1/2 -translate-x-1/2 z-50',
    'bg-gray-800 text-white text-sm px-4 py-2 rounded-full',
    'shadow-lg animate-fadeIn',
  ].join(' ')
  document.body.appendChild(toast)
  setTimeout(() => {
    if (toast.parentNode) toast.remove()
  }, 2000)
}

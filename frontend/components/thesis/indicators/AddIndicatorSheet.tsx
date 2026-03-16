'use client'

import { BottomSheet } from '@/components/thesis/common/BottomSheet'
import { RecommendCard } from './RecommendCard'
import type { RecommendedIndicator } from '@/lib/thesis/types'

interface Props {
  isOpen: boolean
  onClose: () => void
  recommendations: RecommendedIndicator[]
  isLoading: boolean
  addedNames: Set<string>
  onAdd: (rec: RecommendedIndicator) => void
  onAddAll: () => void
  addingName: string | null
}

export function AddIndicatorSheet({
  isOpen, onClose, recommendations, isLoading,
  addedNames, onAdd, onAddAll, addingName,
}: Props) {
  const allAdded =
    recommendations.length > 0 &&
    recommendations.every((r) => addedNames.has(r.name))

  return (
    <BottomSheet isOpen={isOpen} onClose={onClose} title="AI 추천 지표">
      {isLoading ? (
        <div className="flex flex-col items-center gap-3 py-8">
          <div className="flex gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-bounce [animation-delay:0ms]" />
            <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-bounce [animation-delay:200ms]" />
            <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-bounce [animation-delay:400ms]" />
          </div>
          <p className="text-sm text-gray-400">AI가 지표를 고르는 중...</p>
        </div>
      ) : recommendations.length === 0 ? (
        <div className="text-center py-8">
          <p className="text-sm text-gray-400">추천할 지표가 없어요.</p>
          <p className="text-xs text-gray-600 mt-1">
            전제를 수정하면 더 나은 추천을 받을 수 있어요.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          <ul className="space-y-3 list-none">
            {recommendations.map((rec) => (
              <li key={rec.name}>
                <RecommendCard
                  indicator={rec}
                  onAdd={() => onAdd(rec)}
                  added={addedNames.has(rec.name)}
                  isAdding={addingName === rec.name}
                />
              </li>
            ))}
          </ul>

          {/* 전체 추가 버튼 */}
          {!allAdded && (
            <button
              onClick={onAddAll}
              className="w-full py-3 border border-blue-600 text-blue-400 text-sm
                         rounded-xl active:scale-[0.98] transition-transform mt-2"
            >
              전체 추가 ({recommendations.filter((r) => !addedNames.has(r.name)).length}개)
            </button>
          )}

          {allAdded && (
            <button
              onClick={onClose}
              className="w-full py-3 bg-blue-600 text-white text-sm font-medium
                         rounded-xl active:scale-[0.98] transition-transform mt-2"
            >
              완료
            </button>
          )}
        </div>
      )}
    </BottomSheet>
  )
}

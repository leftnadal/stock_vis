'use client'

interface Props {
  selectedCount: number
  onConfirm: () => void
}

export function MultiSelectFooter({ selectedCount, onConfirm }: Props) {
  return (
    <div className="border-t border-gray-800 bg-gray-950 px-4 py-3">
      <button
        onClick={onConfirm}
        disabled={selectedCount === 0}
        className={`w-full py-3.5 rounded-xl text-sm font-medium transition-all
                    ${selectedCount > 0
                      ? 'bg-blue-600 text-white active:scale-[0.98]'
                      : 'bg-gray-800 text-gray-600 cursor-not-allowed'}`}
      >
        {selectedCount > 0
          ? `선택 완료 (${selectedCount}개) →`
          : '하나 이상 선택해주세요'}
      </button>
    </div>
  )
}

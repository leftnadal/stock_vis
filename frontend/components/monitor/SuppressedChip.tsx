// 억제된 알림(쿨다운) 표기 칩 (MON-P3-ALERT).
// 서버 목록(/monitor/alerts/)이 is_suppressed=false만 반환하므로 현재 소비처는 없다.
// 향후 억제 이력을 노출해야 할 화면(예: 관제 감사 뷰)이 생기면 그대로 재사용한다.
export function SuppressedChip() {
  return (
    <span
      className="rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-medium text-gray-500 dark:bg-gray-800 dark:text-gray-400"
      data-testid="suppressed-chip"
    >
      쿨다운 억제됨
    </span>
  )
}

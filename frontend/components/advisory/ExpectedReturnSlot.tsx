// 예상수익률 빈 슬롯 (Slice 20a §2 절대 규칙) — 데이터 없음, placeholder만.
// score는 "배치 우선순위 점수"일 뿐 기대수익이 아니므로 여기 절대 대입 금지.
// SIGNAL-FORWARD-INFRA 착수 전까지는 안내 문구만 표시한다.
export function ExpectedReturnSlot() {
  return (
    <div
      data-testid="expected-return-slot"
      className="rounded-lg border border-dashed border-gray-300 bg-gray-50 px-3 py-2 text-xs text-gray-400 dark:border-gray-700 dark:bg-gray-800/40 dark:text-gray-500"
    >
      <span className="font-medium text-gray-500 dark:text-gray-400">예상수익률</span>
      <span className="ml-2">— 예측 인프라 준비 중(SIGNAL-FORWARD-INFRA 후)</span>
    </div>
  )
}

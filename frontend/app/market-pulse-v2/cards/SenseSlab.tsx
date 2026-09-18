'use client'

/**
 * HUB-SENSE-DETAIL S1 — 설명 스택 트레이(D-SENSE-PLACEMENT B).
 *
 * 위젯 카드 **아래에 끼워 넣는** 판. 위에서부터 "오늘의 적용"(SenseNote) → 구분선 →
 * 일반론(EducationNote) 순서다. 순서 역전이 이 슬라이스의 핵심 — 오늘의 값에 대한 해석이
 * 일반론보다 먼저 읽혀야 한다.
 *
 * 부착 방식(AUTO-SENSE-ATTACH): 음수 마진으로 카드 아래에 물려 넣고(-mt-3.5 = 14px),
 * 먹힌 만큼 위쪽 패딩으로 되돌린다(pt-7). 카드가 트레이 위에 겹쳐 보이도록 호출부에서
 * 카드 래퍼에 relative z-10을, 트레이에 relative z-0을 준다.
 *
 * ⛔ 자식 선택자(arbitrary variant로 하위 div의 rounded-b를 죽이는 류)를 쓰지 않는다.
 *    위젯 내부 DOM에 의존하게 되어 위젯 구조가 바뀌면 조용히 깨진다 — B안이 사는 이유가
 *    "위젯을 모른다"는 점이다. 카드의 모서리·테두리·그림자는 그대로 둔다.
 *
 * sense가 없어도 트레이는 렌더된다(일반론이 있으므로). sense만 미렌더 — SenseNote의 기존
 * 계약(빈 줄·플레이스홀더 금지)을 그대로 지킨다.
 */
import { EDUCATIONAL_CONTENT } from '@/constants/education'
import { SenseNote } from './SenseNote'
import { EducationNote, type EducationKey } from './EducationNote'

export function SenseSlab({
  sense,
  eduKeys,
  eduLabel,
}: {
  sense?: string | null
  eduKeys: readonly EducationKey[]
  eduLabel?: string
}) {
  // 한 카드가 지표 둘을 묶는 경우(물가·고용)는 라벨 하나로 둘을 가리킬 수 없다 —
  // 같은 문구가 두 번 쌓여 어느 토글이 무엇인지 사라진다. 이때만 상수의 title을 라벨로
  // 쓴다(기존 문구 재사용 — S1은 새 문구를 만들지 않는다).
  const perKeyTitle = eduKeys.length > 1

  return (
    <div
      className="relative z-0 -mt-3.5 rounded-b-lg border border-t-0 border-slate-200 bg-slate-50 px-4 pb-4 pt-7 dark:border-gray-700 dark:bg-gray-900/40"
      data-testid="sense-slab"
    >
      <p className="text-[11px] font-medium uppercase tracking-wide text-slate-500 dark:text-gray-400">
        오늘의 적용
      </p>
      <SenseNote sense={sense} />
      <div className="mt-3 space-y-2 border-t border-slate-200 pt-3 dark:border-gray-700">
        {eduKeys.map((k) => (
          <EducationNote
            key={k}
            eduKey={k}
            label={perKeyTitle ? EDUCATIONAL_CONTENT[k].title : eduLabel}
          />
        ))}
      </div>
    </div>
  )
}

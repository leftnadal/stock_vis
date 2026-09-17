'use client'

/**
 * HUB-SENSE-DETAIL S1 — 일반론(교육) 토글을 허브가 그린다(D-SENSE-PLACEMENT B).
 *
 * 지금까지 일반론은 위젯 안에 있었다(FearGreedGauge·YieldCurveChart만). 그래서 ⑴ 4장 중
 * 2장에만 있었고 ⑵ "오늘의 적용"(SenseNote)이 그 아래로 밀려 일반론이 먼저 읽혔다.
 * 이 컴포넌트는 같은 상수(EDUCATIONAL_CONTENT)를 **허브 쪽에서** 읽어 4장 전부에 균일하게
 * 건다. 위젯 파일은 한 줄도 고치지 않는다 — 호출부에서 showEducation={false}로 끌 뿐이다.
 *
 * S1은 배치만 한다. 새 문구는 만들지 않는다(문단·목록·라벨 전부 기존 상수/기존 위젯에서
 * 그대로 옮긴 것). "왜 이렇게 읽나" 3줄은 S2(macroDetail.ts) 소관.
 */
import { EDUCATIONAL_CONTENT } from '@/constants/education'

export type EducationKey = keyof typeof EDUCATIONAL_CONTENT

/** 위젯이 쓰던 기본 라벨(FearGreedGauge). 금리는 자기 라벨을 그대로 넘겨받는다. */
const DEFAULT_LABEL = '이 지표는 어떻게 해석하나요?'

export function EducationNote({
  eduKey,
  label = DEFAULT_LABEL,
}: {
  eduKey: EducationKey
  label?: string
}) {
  const content = EDUCATIONAL_CONTENT[eduKey]
  if (!content) return null

  return (
    // AUTO-SENSE-FOLD: 기본 접힘. 펼침 상태를 기억하지 않는다(카드마다 독립).
    <details className="group" data-testid="education-note">
      <summary className="flex cursor-pointer items-center justify-between text-sm text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white">
        <span className="font-medium">{label}</span>
        <span className="ml-2 transform transition-transform group-open:rotate-180">▼</span>
      </summary>
      <div className="mt-3 space-y-2 text-sm text-gray-600 dark:text-gray-400">
        <p>{content.levels.beginner}</p>
        <ul className="mt-2 list-inside list-disc space-y-1">
          {content.keyPoints.slice(0, 3).map((point, i) => (
            <li key={i}>{point}</li>
          ))}
        </ul>
      </div>
    </details>
  )
}

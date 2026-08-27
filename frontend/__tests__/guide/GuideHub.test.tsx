// GuideHub — 데이터 자동 나열(하드코딩 금지) 검증 (D-GUIDE-TRACK)
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import GuideHub from '@/components/guide/GuideHub'
import { FLOW_STAGE_LABELS, GUIDE_SCREENS } from '@/lib/guide'

describe('GuideHub', () => {
  it('플로우 5단계를 모두 표시한다', () => {
    render(<GuideHub />)
    for (const stage of [1, 2, 3, 4, 5] as const) {
      expect(screen.getByTestId(`guide-stage-${stage}`)).toHaveTextContent(
        FLOW_STAGE_LABELS[stage]
      )
    }
  })

  it('등재된 화면을 빠짐없이 카드로 나열한다 (하드코딩 아님)', () => {
    render(<GuideHub />)
    for (const s of GUIDE_SCREENS) {
      const card = screen.getByTestId(`guide-card-${s.id}`)
      expect(card).toHaveTextContent(s.coreQuestion)
      expect(card.querySelector(`a[href="${s.route}"]`)).not.toBeNull()
    }
  })

  it('가이드가 없는 플로우 단계는 "가이드 준비 중"으로 정직하게 표시한다', () => {
    render(<GuideHub />)
    const coveredStages = new Set(GUIDE_SCREENS.map((s) => s.flowStage))
    for (const stage of [1, 2, 3, 4, 5] as const) {
      if (!coveredStages.has(stage)) {
        expect(screen.getByTestId(`guide-stage-${stage}`)).toHaveTextContent('가이드 준비 중')
      }
    }
  })

  it('draft 화면에는 "초안" 배지가 붙는다', () => {
    render(<GuideHub />)
    for (const s of GUIDE_SCREENS.filter((x) => x.reviewStatus === 'draft')) {
      expect(screen.getByTestId(`guide-draft-${s.id}`)).toHaveTextContent('초안')
    }
  })
})

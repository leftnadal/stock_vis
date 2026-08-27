// GuideOverlay — 렌더·닫기·다시 안 보기·데이터 없는 화면에서 ? 버튼 미노출 (D-GUIDE-TRACK)
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

let pathname = '/'
vi.mock('next/navigation', () => ({
  usePathname: () => pathname,
}))

import GuideOverlay, { guideDismissKey } from '@/components/guide/GuideOverlay'
import { getGuideForRoute } from '@/lib/guide'

beforeEach(() => {
  pathname = '/'
  window.localStorage.clear()
})

describe('GuideOverlay 노출 조건', () => {
  it('가이드 데이터가 있는 화면에서는 ? 버튼을 노출한다', () => {
    render(<GuideOverlay />)
    expect(screen.getByTestId('guide-toggle')).toBeInTheDocument()
  })

  it('가이드 데이터가 없는 화면에서는 ? 버튼을 노출하지 않는다', () => {
    pathname = '/screener'
    render(<GuideOverlay />)
    expect(screen.queryByTestId('guide-toggle')).toBeNull()
  })

  it('하위 경로로 가이드가 새지 않는다 (/monitor 가이드 ≠ /monitor/new)', () => {
    pathname = '/monitor/new'
    render(<GuideOverlay />)
    expect(screen.queryByTestId('guide-toggle')).toBeNull()
  })

  it('OFF 상태에서는 패널을 렌더하지 않는다', () => {
    render(<GuideOverlay />)
    expect(screen.queryByTestId('guide-panel')).toBeNull()
  })
})

describe('GuideOverlay 패널 내용', () => {
  it('coreQuestion → learnings → 영역 → nextAction 순으로 데이터를 그대로 렌더한다', () => {
    render(<GuideOverlay />)
    fireEvent.click(screen.getByTestId('guide-toggle'))

    const guide = getGuideForRoute('/')!
    expect(screen.getByTestId('guide-core-question')).toHaveTextContent(guide.coreQuestion)
    for (const l of guide.learnings) {
      expect(screen.getByText(l)).toBeInTheDocument()
    }
    for (const r of guide.regions) {
      expect(screen.getByText(r.title)).toBeInTheDocument()
    }
    expect(screen.getByTestId('guide-next-action')).toHaveAttribute(
      'href',
      guide.nextAction!.route
    )
  })

  it('앵커가 실제로 렌더된 영역에만 번호 배지를 붙인다(없는 앵커는 생략)', async () => {
    const host = document.createElement('div')
    host.setAttribute('data-guide', 'dashboard.market-summary')
    document.body.appendChild(host)

    render(<GuideOverlay />)
    fireEvent.click(screen.getByTestId('guide-toggle'))

    // 배지 위치는 rAF에서 측정 → 다음 프레임 대기
    await waitFor(() =>
      expect(screen.getByTestId('guide-badge-dashboard.market-summary')).toBeInTheDocument()
    )
    expect(screen.queryByTestId('guide-badge-dashboard.signal-cards')).toBeNull()

    document.body.removeChild(host)
  })
})

describe('GuideOverlay 닫기 / 다시 안 보기', () => {
  it('닫기 버튼이 패널을 닫는다', () => {
    render(<GuideOverlay />)
    fireEvent.click(screen.getByTestId('guide-toggle'))
    expect(screen.getByTestId('guide-panel')).toBeInTheDocument()

    fireEvent.click(screen.getByTestId('guide-close'))
    expect(screen.queryByTestId('guide-panel')).toBeNull()
    // 버튼은 남는다 — 언제든 재열람
    expect(screen.getByTestId('guide-toggle')).toBeInTheDocument()
  })

  it('"다시 안 보기"는 화면 id별 키로 저장하고 힌트를 끈다 (버튼은 유지)', () => {
    const guide = getGuideForRoute('/')!
    const { unmount } = render(<GuideOverlay />)
    expect(screen.getByTestId('guide-hint')).toBeInTheDocument()

    fireEvent.click(screen.getByTestId('guide-toggle'))
    fireEvent.click(screen.getByTestId('guide-dismiss'))

    expect(window.localStorage.getItem(guideDismissKey(guide.id))).toBe('1')
    expect(screen.queryByTestId('guide-panel')).toBeNull()
    expect(screen.getByTestId('guide-toggle')).toBeInTheDocument()
    unmount()

    // 재방문 시 힌트 미노출이 유지된다
    render(<GuideOverlay />)
    expect(screen.queryByTestId('guide-hint')).toBeNull()
    expect(screen.getByTestId('guide-toggle')).toBeInTheDocument()
  })

  it('다시 안 보기는 해당 화면에만 적용된다', () => {
    window.localStorage.setItem(guideDismissKey('dashboard.main'), '1')
    pathname = '/monitor'
    render(<GuideOverlay />)
    expect(screen.getByTestId('guide-hint')).toBeInTheDocument()
  })
})

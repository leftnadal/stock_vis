/**
 * INC-P16-CLOSE Part 1 — QueryProvider 안정성 회귀 테스트 (INC-P16-2 포렌식 #2).
 *
 * QueryProvider가 부모 리렌더에도 QueryClientProvider에 주입하는 client 인스턴스
 * identity를 불변으로 유지하는지 단언한다. `new QueryClient(...)`가 컴포넌트 본문으로
 * inline화(useState 초기화 함수 상실)되면 렌더마다 새 client → 캐시 리셋 → 전 쿼리
 * 재fetch 루프. 이 자리(같은 근인)의 세 번째 인시던트를 코드가 즉시 red로 막는다.
 */
import { QueryClient, useQueryClient } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { useState } from 'react'
import { describe, expect, it } from 'vitest'

import QueryProvider from '@/providers/QueryProvider'

const captured: QueryClient[] = []

function Probe() {
  captured.push(useQueryClient())
  return null
}

// 부모 리렌더를 유발하는 하네스. 버튼 클릭마다 상태 증가 → QueryProvider 리렌더.
function Harness() {
  const [n, setN] = useState(0)
  return (
    <>
      <button data-testid="bump" onClick={() => setN(n + 1)}>
        {n}
      </button>
      <QueryProvider>
        <Probe />
      </QueryProvider>
    </>
  )
}

describe('QueryProvider 인스턴스 안정성 (INC-P16-CLOSE Part 1)', () => {
  it('부모 리렌더 5회에도 주입되는 QueryClient identity 불변', () => {
    captured.length = 0
    render(<Harness />)
    const bump = screen.getByTestId('bump')
    for (let i = 0; i < 5; i++) fireEvent.click(bump)

    // 최소 6회 렌더(초기 + 5 클릭) 캡처, 전부 동일 참조
    expect(captured.length).toBeGreaterThanOrEqual(6)
    const first = captured[0]
    expect(first).toBeInstanceOf(QueryClient)
    for (const qc of captured) {
      expect(qc).toBe(first) // inline new QueryClient 회귀 시 여기서 즉시 실패
    }
  })
})

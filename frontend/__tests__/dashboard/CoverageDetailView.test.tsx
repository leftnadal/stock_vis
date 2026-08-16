// CoverageDetailView 렌더 검증 (P2-COVERAGE-C1-FE, T2 + COVERAGE-DETAIL-FE)
import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

// impression 훅 mock — 행 단위 호출(surface·object_ref) 검증용
const useImpressionTracker = vi.fn((_surface: string, _objectRef: string) => ({
  ref: { current: null },
  onClick: vi.fn(),
}))
vi.mock('@/hooks/useImpressionTracker', () => ({
  useImpressionTracker: (surface: string, objectRef: string) =>
    useImpressionTracker(surface, objectRef),
}))

import { CoverageDetailView } from '@/components/dashboard/CoverageDetailView'
import type { CoverageResponse } from '@/types/coverage'

beforeEach(() => useImpressionTracker.mockClear())

const base: CoverageResponse = {
  window: { days: 7, from: '2026-07-20', to: '2026-07-27' },
  summary: { issued: 50, exposed: 4, exposure_rate: 0.08, unexposed_count: 46 },
  unexposed: [
    {
      object_ref: 'ACGL:2026-07-24:P5',
      ticker: 'ACGL',
      signal_date: '2026-07-24',
      signal_tag: 'P5',
      days_since_issue: 3,
    },
    {
      object_ref: 'AAPL:2026-07-24:PV1',
      ticker: 'AAPL',
      signal_date: '2026-07-24',
      signal_tag: 'PV1',
      days_since_issue: 3,
    },
  ],
  meta: { surfaces_included: ['dashboard_eod'], generated_at: 'x', join_misses: 8 },
}

describe('CoverageDetailView', () => {
  it('summary + 미노출 리스트 필드 렌더', () => {
    render(<CoverageDetailView data={base} />)
    const detail = screen.getByTestId('coverage-detail')
    expect(detail).toHaveTextContent('발급')
    expect(detail).toHaveTextContent('노출율')
    const list = screen.getByTestId('coverage-unexposed-list')
    expect(list).toHaveTextContent('ACGL')
    expect(list).toHaveTextContent('PV1')
    expect(list).toHaveTextContent('3일 경과')
  })

  it('API 응답 순서 그대로 렌더(FE 재정렬 금지)', () => {
    render(<CoverageDetailView data={base} />)
    const items = screen
      .getByTestId('coverage-unexposed-list')
      .querySelectorAll('li')
    expect(items[0]).toHaveTextContent('ACGL')
    expect(items[1]).toHaveTextContent('AAPL')
  })

  it('join_misses > 0 · w90 미공급이면 N 만 표기(90일 판정 보류)', () => {
    render(<CoverageDetailView data={base} />)
    expect(screen.getByTestId('coverage-join-misses')).toHaveTextContent(
      '창밖 노출 8'
    )
  })

  it('join_misses = 0 이면 라벨 숨김', () => {
    render(
      <CoverageDetailView data={{ ...base, meta: { ...base.meta, join_misses: 0 } }} />
    )
    expect(screen.queryByTestId('coverage-join-misses')).toBeNull()
  })

  // D-C2-S1-JOINMISS-LABEL (S1-B1) — 창밖 노출 라벨 3상태
  // base: exposed 4 + join_misses 8 = imp_uniq 12 (교차창 정합 기준값)
  it('상태 1 (w90 미매칭=0): 90일 내 전량 매칭 ✓', () => {
    render(<CoverageDetailView data={base} w90JoinMisses={0} w90ImpUniq={12} />)
    expect(screen.getByTestId('coverage-join-misses')).toHaveTextContent(
      '창밖 노출 8 · 90일 내 전량 매칭 ✓'
    )
    expect(screen.queryByTestId('coverage-join-misses-error')).toBeNull()
  })

  it('상태 2 (w90 미매칭>0): 90일 밖 M 표기', () => {
    render(<CoverageDetailView data={base} w90JoinMisses={3} w90ImpUniq={12} />)
    expect(screen.getByTestId('coverage-join-misses')).toHaveTextContent(
      '창밖 노출 8 · 90일 밖 3'
    )
  })

  it('항등식 위배(교차창 imp_uniq 불일치) → 라벨 대신 오류 표기', () => {
    // w90ImpUniq 99 ≠ (exposed 4 + join_misses 8 = 12)
    render(<CoverageDetailView data={base} w90JoinMisses={0} w90ImpUniq={99} />)
    expect(screen.getByTestId('coverage-join-misses-error')).toHaveTextContent(
      '노출 집계 정합 오류'
    )
    expect(screen.queryByTestId('coverage-join-misses')).toBeNull()
  })

  it('미노출 0건이면 안내 문구', () => {
    render(
      <CoverageDetailView
        data={{
          ...base,
          summary: { ...base.summary, unexposed_count: 0 },
          unexposed: [],
        }}
      />
    )
    expect(screen.getByTestId('coverage-detail')).toHaveTextContent(
      '미노출 발급이 없습니다.'
    )
  })

  it('각 미노출 행이 surface=coverage_detail·object_ref로 impression 추적 연결 (COVERAGE-DETAIL-FE)', () => {
    render(<CoverageDetailView data={base} />)
    // 행 단위: unexposed 2건 각각 훅 호출
    expect(useImpressionTracker).toHaveBeenCalledTimes(2)
    expect(useImpressionTracker).toHaveBeenCalledWith('coverage_detail', 'ACGL:2026-07-24:P5')
    expect(useImpressionTracker).toHaveBeenCalledWith('coverage_detail', 'AAPL:2026-07-24:PV1')
  })

  it('미노출 0건이면 impression 훅 호출 없음(발신 0)', () => {
    render(
      <CoverageDetailView
        data={{ ...base, summary: { ...base.summary, unexposed_count: 0 }, unexposed: [] }}
      />
    )
    expect(useImpressionTracker).not.toHaveBeenCalled()
  })

  // ───────────────────────────────────────────────────────────────────────
  // S2-B1-FE: 점검 층(빗금) + "점검됨" 배지 (D-C2-S2-FUNNEL-COV 2계열 audit)
  // ───────────────────────────────────────────────────────────────────────

  it('① "점검됨" 배지 = audited true 항목에만', () => {
    const data: CoverageResponse = {
      ...base,
      audit: { surface: 'coverage_detail', observed_uniq: 1, audit_only_unexposed: 1, overlap: 0 },
      unexposed: [
        { ...base.unexposed[0], audited: true }, // ACGL
        { ...base.unexposed[1], audited: false }, // AAPL
      ],
    }
    render(<CoverageDetailView data={data} />)
    expect(screen.getAllByTestId('audited-badge')).toHaveLength(1)
    const rows = screen.getByTestId('coverage-unexposed-list').querySelectorAll('li')
    expect(rows[0]).toHaveTextContent('ACGL')
    expect(rows[0]).toHaveTextContent('점검됨')
    expect(rows[1]).toHaveTextContent('AAPL')
    expect(rows[1]).not.toHaveTextContent('점검됨')
  })

  it('② 점검 층 = audit 집계(observed_uniq·audit_only_unexposed·overlap) 렌더', () => {
    const data: CoverageResponse = {
      ...base,
      audit: { surface: 'coverage_detail', observed_uniq: 61, audit_only_unexposed: 49, overlap: 12 },
    }
    render(<CoverageDetailView data={data} />)
    const layer = screen.getByTestId('coverage-audit-layer')
    expect(layer).toHaveTextContent('점검 층')
    expect(layer).toHaveTextContent('61')
    expect(layer).toHaveTextContent('49')
    expect(layer).toHaveTextContent('12')
  })

  it('④ audit 부재(구형 서빙) → 점검 층·배지 생략, 기존 화면 동일', () => {
    render(<CoverageDetailView data={base} />) // base 엔 audit 필드 없음
    expect(screen.queryByTestId('coverage-audit-layer')).toBeNull()
    expect(screen.queryByTestId('audited-badge')).toBeNull()
    // 본판정·미노출 리스트는 그대로 렌더
    expect(screen.getByTestId('coverage-detail')).toHaveTextContent('노출율')
    expect(screen.getByTestId('coverage-unexposed-list')).toHaveTextContent('ACGL')
  })

  it('⑤ 점검 데이터 있어도 본판정 표시 무변 + 적체 비제거(배지만)', () => {
    const data: CoverageResponse = {
      ...base, // summary issued 50 / exposed 4 / rate 0.08 / unexposed 46
      audit: { surface: 'coverage_detail', observed_uniq: 2, audit_only_unexposed: 2, overlap: 0 },
      unexposed: [
        { ...base.unexposed[0], audited: true },
        { ...base.unexposed[1], audited: true },
      ],
    }
    render(<CoverageDetailView data={data} />)
    const detail = screen.getByTestId('coverage-detail')
    // 본판정 표시 무변(노출율 8% 그대로)
    expect(detail).toHaveTextContent('8%')
    // 적체 비제거 — audited=true 2건 모두 목록에 존재(필터·제거 없음)
    const rows = screen.getByTestId('coverage-unexposed-list').querySelectorAll('li')
    expect(rows).toHaveLength(2)
    expect(screen.getAllByTestId('audited-badge')).toHaveLength(2)
  })
})

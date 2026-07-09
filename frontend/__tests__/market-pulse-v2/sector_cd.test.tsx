/**
 * MP2-SECTOR-CD Slice 1 — 판단 카드 + 세그먼트 토글 테스트.
 *
 * 검증: 4상태 뱃지·색 토큰 매핑, null 유보 렌더, 토글 전환(디폴트=판단),
 *   기존 궤적 뷰 회귀, cd 색 토큰 헬퍼 단위.
 */
import { fireEvent, render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { SectorDetail as Detail, SectorRow } from '@/lib/api/marketPulseV2'
import { SectorDetail } from '@/app/market-pulse-v2/details/SectorDetail'
import {
  cdStateBadgeClass,
  cdStateDotFill,
  cdStateLabel,
} from '@/app/market-pulse-v2/sectorColor'

function row(
  symbol: string,
  rel: number,
  mom5: number,
  rank: number,
  cd_state: SectorRow['cd_state'],
  rel5: number | null = rel,  // CD-STAB A′: 판단 x축(5일 상대수익). 기본 = rel(1일)와 동일.
): SectorRow {
  return {
    symbol, rel_strength: rel, rel_strength_5d: rel5,
    momentum_1d: 0, momentum_5d: mom5, momentum_20d: 0, flow_proxy: 0, rank, cd_state,
  }
}

const LABELS: Record<string, string> = {
  'sector.XLK': '기술',
  'sector.XLE': '에너지',
  'sector.XLF': '금융',
  'sector.XLV': '헬스케어',
  'sector.XLU': '유틸',
}

const payload: Detail = {
  available: true,
  date: '2026-07-08',
  cross_dispersion: 0.8,
  rotation_index: 1.5,
  sectors: [
    row('XLK', 0.8, 0.5, 1, 'leading_strengthening'),
    row('XLE', 0.4, -0.9, 2, 'leading_weakening'),
    row('XLF', -0.7, 1.4, 3, 'lagging_improving'),
    row('XLV', -0.6, -0.2, 4, 'lagging_deteriorating'),
  ],
  sector_history: [],
}

describe('SectorCdPanel — 판단 카드', () => {
  it('디폴트 탭 = 판단 (SectorCdPanel 렌더)', () => {
    const { getByTestId } = render(<SectorDetail payload={payload} labels={LABELS} />)
    expect(getByTestId('sector-cd-panel')).toBeInTheDocument()
    // 판단 탭 aria-selected
    expect(getByTestId('sector-tab-cd').getAttribute('aria-selected')).toBe('true')
  })

  it('4상태 뱃지 라벨 매핑 정확', () => {
    const { getByTestId } = render(<SectorDetail payload={payload} labels={LABELS} />)
    expect(getByTestId('cd-badge-XLK').textContent).toBe('주도·강화')
    expect(getByTestId('cd-badge-XLE').textContent).toBe('주도·둔화')
    expect(getByTestId('cd-badge-XLF').textContent).toBe('부진·개선')
    expect(getByTestId('cd-badge-XLV').textContent).toBe('부진·악화')
  })

  it('뱃지 색 토큰 매핑 (bg 클래스)', () => {
    const { getByTestId } = render(<SectorDetail payload={payload} labels={LABELS} />)
    expect(getByTestId('cd-badge-XLK').className).toContain('bg-rose-100')
    expect(getByTestId('cd-badge-XLE').className).toContain('bg-amber-100')
    expect(getByTestId('cd-badge-XLF').className).toContain('bg-teal-100')
    expect(getByTestId('cd-badge-XLV').className).toContain('bg-sky-100')
  })

  it('사분면 미니맵 점 = 비-null 섹터 수만큼', () => {
    const { getByTestId, queryByTestId } = render(<SectorDetail payload={payload} labels={LABELS} />)
    expect(getByTestId('cd-minimap')).toBeInTheDocument()
    for (const s of ['XLK', 'XLE', 'XLF', 'XLV']) {
      expect(queryByTestId(`cd-dot-${s}`)).not.toBeNull()
    }
  })

  it('근거 값 2칸 = 서빙된 rel_strength_5d(라벨 "상대강도 (5일)")·momentum_5d 원값', () => {
    const { getByTestId } = render(<SectorDetail payload={payload} labels={LABELS} />)
    expect(getByTestId('cd-rel-XLK').textContent).toContain('상대강도 (5일)')
    expect(getByTestId('cd-rel-XLK').textContent).toContain('+0.80%')  // rel5=0.8
    expect(getByTestId('cd-mom-XLE').textContent).toContain('-0.90%')
  })

  it('구별값: 근거 상대강도 칸 = rel_strength_5d(5d), 1일 rel_strength 아님', () => {
    // XLK: rel(1일)=+0.80, rel_5d=-0.30 → 판단 계열(카드 근거)은 5d(-0.30%)를 표시.
    const distinct: Detail = {
      ...payload,
      sectors: [row('XLK', 0.8, 0.5, 1, 'leading_strengthening', -0.3)],
    }
    const { getByTestId } = render(<SectorDetail payload={distinct} labels={LABELS} />)
    expect(getByTestId('cd-rel-XLK').textContent).toContain('-0.30%')       // 5d 소비
    expect(getByTestId('cd-rel-XLK').textContent).not.toContain('+0.80%')   // 1일값 아님
  })

  it('구별값: 미니맵 점 x = rel_strength_5d(부호). 1일값과 반대여도 5d를 따른다', () => {
    // rel(1일)=+2(우측) vs rel_5d=-1(좌측) → 점은 중심(C=100) 왼쪽.
    const distinct: Detail = {
      ...payload,
      sectors: [row('XLK', 2.0, 0.5, 1, 'lagging_improving', -1.0)],
    }
    const { getByTestId } = render(<SectorDetail payload={distinct} labels={LABELS} />)
    const cx = Number(getByTestId('cd-dot-XLK').getAttribute('cx'))
    expect(cx).toBeLessThan(100)  // rel_5d<0 → 좌측(1일 +2였다면 우측이었을 것)
  })

  it('rel_strength_5d null(bench 유보) → 근거 칸 대시 + 미니맵 점 미표시', () => {
    const nullRel5: Detail = {
      ...payload,
      sectors: [row('XLU', 0.1, 0.1, 1, null, null)],
    }
    const { getByTestId, queryByTestId } = render(<SectorDetail payload={nullRel5} labels={LABELS} />)
    expect(getByTestId('cd-rel-XLU').textContent).toContain('—')  // 발명 금지
    expect(queryByTestId('cd-dot-XLU')).toBeNull()
  })

  it('null cd_state → 판단 유보 뱃지 + 점 미표시 + 유보 문구', () => {
    const reservedPayload: Detail = {
      ...payload,
      sectors: [row('XLU', 0.1, 0.1, 1, null)],
    }
    const { getByTestId, queryByTestId } = render(<SectorDetail payload={reservedPayload} labels={LABELS} />)
    expect(getByTestId('cd-badge-XLU').textContent).toBe('판단 유보')
    expect(getByTestId('cd-badge-XLU').className).toContain('bg-slate-100')
    // 유보 섹터는 사분면 점 미표시
    expect(queryByTestId('cd-dot-XLU')).toBeNull()
    // 유보 문구
    expect(getByTestId('cd-stance-XLU').textContent).toContain('판정을 유보')
  })

  it('cd_state undefined(구버전 응답) → 유보 처리(크래시 없음)', () => {
    const legacyPayload: Detail = {
      ...payload,
      sectors: [{ symbol: 'XLU', rel_strength: 0.1, momentum_1d: 0, momentum_5d: 0.1, momentum_20d: 0, flow_proxy: 0, rank: 1 }],
    }
    const { getByTestId, queryByTestId } = render(<SectorDetail payload={legacyPayload} labels={LABELS} />)
    expect(getByTestId('cd-badge-XLU').textContent).toBe('판단 유보')
    expect(queryByTestId('cd-dot-XLU')).toBeNull()
  })

  it('4상태 범례 렌더', () => {
    const { getByTestId } = render(<SectorDetail payload={payload} labels={LABELS} />)
    const legend = getByTestId('cd-legend')
    for (const label of ['주도·강화', '주도·둔화', '부진·개선', '부진·악화']) {
      expect(legend.textContent).toContain(label)
    }
  })
})

describe('SectorDetail — 세그먼트 토글', () => {
  it('궤적 탭 클릭 → 판단 패널 숨김 + 궤적 뷰 노출(기존 뷰 회귀)', () => {
    const trajPayload: Detail = {
      ...payload,
      sector_history: [{ symbol: 'XLK', history: [{ date: '2026-07-08', rel_strength: 0.8 }] }],
    }
    const { getByTestId, queryByTestId, container } = render(
      <SectorDetail payload={trajPayload} labels={LABELS} />,
    )
    // 디폴트: 판단 패널 존재
    expect(queryByTestId('sector-cd-panel')).not.toBeNull()
    // 궤적 탭 클릭
    fireEvent.click(getByTestId('sector-tab-trajectory'))
    expect(queryByTestId('sector-cd-panel')).toBeNull()
    // 기존 궤적 콘텐츠(상대 강도 라벨) 회귀
    expect(container.textContent).toContain('상대 강도')
    expect(getByTestId('sector-tab-trajectory').getAttribute('aria-selected')).toBe('true')
  })

  it('판단 → 궤적 → 판단 왕복 전환', () => {
    const { getByTestId, queryByTestId } = render(<SectorDetail payload={payload} labels={LABELS} />)
    fireEvent.click(getByTestId('sector-tab-trajectory'))
    expect(queryByTestId('sector-cd-panel')).toBeNull()
    fireEvent.click(getByTestId('sector-tab-cd'))
    expect(queryByTestId('sector-cd-panel')).not.toBeNull()
  })
})

describe('sectorColor — cd 토큰 헬퍼', () => {
  it('cdStateLabel', () => {
    expect(cdStateLabel('leading_strengthening')).toBe('주도·강화')
    expect(cdStateLabel(null)).toBe('판단 유보')
  })

  it('cdStateBadgeClass', () => {
    expect(cdStateBadgeClass('lagging_deteriorating')).toContain('bg-sky-100')
    expect(cdStateBadgeClass(null)).toContain('bg-slate-100')
  })

  it('cdStateDotFill', () => {
    expect(cdStateDotFill('leading_strengthening')).toBe('#f43f5e')
    expect(cdStateDotFill('lagging_improving')).toBe('#14b8a6')
  })
})

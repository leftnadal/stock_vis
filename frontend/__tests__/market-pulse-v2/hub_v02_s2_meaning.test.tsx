/**
 * HUB-V02-S2 — 거시/폭/로테이션 정적 문장 단일소스 테스트(결정론·LLM 0).
 *
 * 커버리지:
 *   1. macroMeaning 4종 전 분기 + null/경계값(VIX level·spread 0/0.5/2.5·물가 갭 0/1.0·nfp 0/87)
 *   2. breadthStaticSentence — 댐핑 O/X + 밴드별 + null
 *   3. rotationSentence — 개선/악화/주도/후행 과반 + 갈림 + null 과반 + 전환 꼬리말
 *   4. ★금지어휘 전수 스캔: 산출 가능한 모든 문장에 오를·내릴·매수·매도·목표가·확실·
 *      반드시·위기/CRISIS·유사·닮·연도 부재(stress_copy.test 금지규칙 미러)
 */
import { describe, it, expect } from 'vitest'

import type { FearGreedIndex, InterestRatesDashboard, InflationDashboard, USIndices } from '@/types/macro'
import {
  fearGreedSentence,
  yieldCurveSentence,
  economySentence,
  globalIndicesSentence,
  SENSE_UNAVAILABLE,
} from '@/app/market-pulse-v2/macroMeaning'
import { breadthStaticSentence } from '@/app/market-pulse-v2/meaning'
import { rotationSentence } from '@/app/market-pulse-v2/sectorColor'
import type { CdState } from '@/app/market-pulse-v2/sectorColor'

// 금지 패턴(지시서 Part 6 + §3): 방향 권유·확실성·위기·유사성·특정 연도.
const FORBIDDEN = [/오를/, /내릴/, /매수/, /매도/, /목표가/, /확실/, /반드시/, /위기/, /crisis/i, /유사/, /닮/, /(19|20)\d{2}/]

const fg = (rule_key: FearGreedIndex['rule_key'], level?: string): FearGreedIndex =>
  ({ rule_key, vix: level ? { level } : undefined } as unknown as FearGreedIndex)
const ir = (status: string, spread: number | null): InterestRatesDashboard =>
  ({ yield_spread: { spread, status, date: null } } as unknown as InterestRatesDashboard)
const econ = (core: number | null, nfp: number | null, target = 2.0): InflationDashboard =>
  ({ inflation: { core_cpi_yoy: core, fed_target: target }, employment: { nfp_change: nfp } } as unknown as InflationDashboard)
const idx = (sp: number | null, nd: number | null, dw: number | null, ru: number | null): USIndices =>
  ({
    sp500: sp == null ? null : { change: sp },
    nasdaq: nd == null ? null : { change: nd },
    dow: dw == null ? null : { change: dw },
    russell2000: ru == null ? null : { change: ru },
  } as unknown as USIndices)

describe('fearGreedSentence — 심리 3그룹 × 변동성 2그룹', () => {
  it('심리 5종 각 분기 문구', () => {
    expect(fearGreedSentence(fg('extreme_fear', 'high'))).toContain('위축')
    expect(fearGreedSentence(fg('fear', 'normal'))).toContain('위축')
    expect(fearGreedSentence(fg('neutral', 'low'))).toContain('중립')
    expect(fearGreedSentence(fg('greed', 'normal'))).toContain('낙관')
    expect(fearGreedSentence(fg('extreme_greed', 'extreme_high'))).toContain('과열')
  })
  it('변동성 확대/안정 분기', () => {
    expect(fearGreedSentence(fg('greed', 'high'))).toContain('변동성이 커')
    expect(fearGreedSentence(fg('greed', 'normal'))).toContain('변동성은 대체로 안정')
  })
  it('vix 없거나 미지 level → 변동성절 생략(심리만)', () => {
    expect(fearGreedSentence(fg('greed'))).not.toContain('변동성')
    expect(fearGreedSentence(fg('greed', 'weird'))).not.toContain('변동성')
  })
  it('rule_key 미지/부재 → 판정 불가', () => {
    expect(fearGreedSentence(null)).toBe(SENSE_UNAVAILABLE)
    expect(fearGreedSentence(fg('nope' as FearGreedIndex['rule_key']))).toBe(SENSE_UNAVAILABLE)
  })
})

describe('yieldCurveSentence — status 5분기', () => {
  it('4상태 문구 + spread 병기', () => {
    expect(yieldCurveSentence(ir('inverted', -0.2))).toContain('역전')
    expect(yieldCurveSentence(ir('flattening', 0.39))).toContain('축소')
    expect(yieldCurveSentence(ir('flattening', 0.39))).toContain('0.39')
    expect(yieldCurveSentence(ir('normal', 1.5))).toContain('정상')
    expect(yieldCurveSentence(ir('steep', 2.8))).toContain('확대')
  })
  it('경계값 spread 0/0.5/2.5 — status enum이 지배(재계산 0)', () => {
    expect(yieldCurveSentence(ir('flattening', 0))).toContain('축소')
    expect(yieldCurveSentence(ir('normal', 0.5))).toContain('정상')
    expect(yieldCurveSentence(ir('steep', 2.5))).toContain('확대')
  })
  it('unknown/spread null → 판정 불가', () => {
    expect(yieldCurveSentence(ir('unknown', null))).toContain(SENSE_UNAVAILABLE)
    expect(yieldCurveSentence(ir('normal', null))).toContain(SENSE_UNAVAILABLE)
    expect(yieldCurveSentence(null)).toContain(SENSE_UNAVAILABLE)
  })
})

describe('economySentence — 물가 3밴드 + 고용 꼬리말', () => {
  it('물가 갭 3밴드', () => {
    expect(economySentence(econ(3.5, 50))).toContain('크게 웃도는') // 갭 1.5 ≥1.0
    expect(economySentence(econ(2.47, -23))).toContain('근접') // 갭 0.47
    expect(economySentence(econ(1.5, 50))).toContain('밑도는') // 갭 -0.5
  })
  it('물가 갭 경계값 0·1.0', () => {
    expect(economySentence(econ(2.0, 50))).toContain('근접') // 갭 정확히 0 → 0≤gap<1.0
    expect(economySentence(econ(3.0, 50))).toContain('크게 웃도는') // 갭 정확히 1.0 → ≥1.0
  })
  it('고용 꼬리말 3분기 + 경계 0·87', () => {
    expect(economySentence(econ(2.47, -23))).toContain('고용은 감소')
    expect(economySentence(econ(2.47, 0))).toContain('둔화') // nfp 0 → 0≤nfp<87
    expect(economySentence(econ(2.47, 50))).toContain('둔화') // 0≤nfp<87
    expect(economySentence(econ(2.47, 87))).toContain('견조') // nfp 87 → ≥87
  })
  it('core null → 판정 불가 · nfp null → 고용절 생략', () => {
    expect(economySentence(econ(null, 50))).toContain(SENSE_UNAVAILABLE)
    expect(economySentence(econ(2.47, null))).not.toContain('고용')
  })
})

describe('globalIndicesSentence — change 부호만(change_percent 미사용)', () => {
  it('4개 동반 강세/약세', () => {
    expect(globalIndicesSentence(idx(1, 2, 3, 4))).toContain('동반 강세')
    expect(globalIndicesSentence(idx(-1.75, -4.68, -0.16, -4.06))).toContain('동반 약세') // 픽스처 실값
  })
  it('러셀만 반대 → 엇갈림', () => {
    expect(globalIndicesSentence(idx(1, 2, 3, -1))).toContain('엇갈림')
    expect(globalIndicesSentence(idx(-1, -2, -3, 1))).toContain('엇갈림')
  })
  it('그 밖 혼재', () => {
    expect(globalIndicesSentence(idx(1, -2, 3, 4))).toContain('혼재')
  })
  it('유효 지수 2개 미만 → 판정 불가', () => {
    expect(globalIndicesSentence(idx(1, null, null, null))).toContain(SENSE_UNAVAILABLE)
    expect(globalIndicesSentence(null)).toBe(SENSE_UNAVAILABLE)
  })
})

describe('breadthStaticSentence — 댐핑 노출 + 실수치(동어반복 금지)', () => {
  const base = { ad_line: 0 }
  it('댐핑 없음 — 밴드별 실수치 서술', () => {
    // ratio 0.75 → broad_strength, 내부 정합(신고가 우위·AD↑) → 댐핑 없음
    const s = breadthStaticSentence({ advance: 300, decline: 100, new_high_52w: 40, new_low_52w: 5, ad_line_change: 10, ...base })
    expect(s).toContain('상승 300 대 하락 100')
    expect(s).toContain('뚜렷이')
  })
  it('댐핑 down — 표면 강세지만 내부 약함(한 단계 낮춤)', () => {
    // ratio 0.65 → strength(idx3), 신저가 우위 + AD↓ → 댐핑 down
    const s = breadthStaticSentence({ advance: 260, decline: 140, new_high_52w: 3, new_low_52w: 20, ad_line_change: -15, ...base })
    expect(s).toContain('한 단계 낮춰')
    expect(s).toContain('신저가')
  })
  it('댐핑 up — 표면 약세지만 내부 강함(한 단계 올림)', () => {
    // ratio 0.35 → weakness(idx1), 신고가 우위 + AD↑ → 댐핑 up
    const s = breadthStaticSentence({ advance: 140, decline: 260, new_high_52w: 20, new_low_52w: 3, ad_line_change: 15, ...base })
    expect(s).toContain('한 단계 올려')
    expect(s).toContain('신고가')
  })
  it('데이터 없음 → null', () => {
    expect(breadthStaticSentence(null)).toBeNull()
    expect(breadthStaticSentence({ advance: 0, decline: 0, new_high_52w: 0, new_low_52w: 0, ad_line_change: 0, ...base })).toBeNull()
  })
})

describe('rotationSentence — cd_state 집계(재분류 0)', () => {
  const S = (cd: CdState | null, raw?: CdState | null): { cd_state?: CdState | null; cd_state_raw?: CdState | null } => ({
    cd_state: cd,
    cd_state_raw: raw === undefined ? cd : raw,
  })
  const rep = (cd: CdState, n: number) => Array.from({ length: n }, () => S(cd))

  it('개선 과반(6/11)', () => {
    const s = rotationSentence([...rep('leading_strengthening', 4), ...rep('lagging_improving', 2), ...rep('lagging_deteriorating', 5)])
    expect(s).toContain('개선 흐름')
  })
  it('악화 과반', () => {
    const s = rotationSentence([...rep('leading_weakening', 3), ...rep('lagging_deteriorating', 3), ...rep('leading_strengthening', 5)])
    expect(s).toContain('악화 흐름')
  })
  it('1차 무과반 → 2차 주도 과반 (결측 1로 개선/악화 5:5, 주도 6)', () => {
    // total 11(1 null): improve=3+2=5, worsen=3+2=5(둘 다 <6), leading=3+3=6 → 주도 우위.
    const s = rotationSentence([
      ...rep('leading_strengthening', 3), ...rep('leading_weakening', 3),
      ...rep('lagging_improving', 2), ...rep('lagging_deteriorating', 2), S(null),
    ])
    expect(s).toContain('주도 섹터군')
  })
  it('전부 갈림 → 갈려 있음 (개선5·악화5·주도5·후행5, 결측 1)', () => {
    // improve=3+2=5, worsen=2+3=5, leading=3+2=5, lagging=2+3=5 → 전부 <6 → 갈림.
    const s = rotationSentence([
      ...rep('leading_strengthening', 3), ...rep('leading_weakening', 2),
      ...rep('lagging_improving', 2), ...rep('lagging_deteriorating', 3), S(null),
    ])
    expect(s).toContain('갈려 있음')
  })
  it('cd_state 과반 결측 → null(판정 불가)', () => {
    expect(rotationSentence([...rep('leading_strengthening', 3), ...Array.from({ length: 8 }, () => S(null))])).toBeNull()
    expect(rotationSentence([])).toBeNull()
  })
  it('전환 꼬리말 — cd_state ≠ cd_state_raw', () => {
    const arr = [...rep('leading_strengthening', 6), S('lagging_deteriorating', 'lagging_improving'), ...rep('lagging_deteriorating', 4)]
    const s = rotationSentence(arr)
    expect(s).toContain('전환 확인 중')
  })
})

describe('★금지어휘 전수 스캔(FE 짝)', () => {
  it('산출 가능한 전 문장에 금지 어휘 부재', () => {
    const outputs: string[] = []
    const rks: FearGreedIndex['rule_key'][] = ['extreme_fear', 'fear', 'neutral', 'greed', 'extreme_greed']
    const levels = ['extreme_high', 'high', 'normal', 'low', undefined]
    for (const rk of rks) for (const lv of levels) outputs.push(fearGreedSentence(fg(rk, lv)))
    for (const st of ['inverted', 'flattening', 'normal', 'steep', 'unknown']) outputs.push(yieldCurveSentence(ir(st, 0.3)))
    for (const core of [3.5, 2.47, 1.5, null]) for (const nfp of [-23, 0, 50, 87, null]) outputs.push(economySentence(econ(core, nfp)) ?? '')
    outputs.push(globalIndicesSentence(idx(1, 2, 3, 4)), globalIndicesSentence(idx(-1, -2, -3, -4)), globalIndicesSentence(idx(1, 2, 3, -1)), globalIndicesSentence(idx(1, -2, 3, 4)))
    for (const dset of [
      { advance: 300, decline: 100, new_high_52w: 40, new_low_52w: 5, ad_line_change: 10, ad_line: 0 },
      { advance: 260, decline: 140, new_high_52w: 3, new_low_52w: 20, ad_line_change: -15, ad_line: 0 },
      { advance: 140, decline: 260, new_high_52w: 20, new_low_52w: 3, ad_line_change: 15, ad_line: 0 },
      { advance: 250, decline: 250, new_high_52w: 10, new_low_52w: 10, ad_line_change: 0, ad_line: 0 },
    ]) outputs.push(breadthStaticSentence(dset) ?? '')

    for (const out of outputs) {
      for (const re of FORBIDDEN) {
        expect(out, `"${out}"`).not.toMatch(re)
      }
    }
  })
})

/**
 * HUB-V02-S2 / S2-COPYFIX — 거시/폭/로테이션 정적 문장 단일소스 테스트(결정론·LLM 0).
 *
 * 커버리지:
 *   1. macroMeaning 4종 리터럴 단언 + null/경계 (fearGreed는 조합 통찰·재료 결측→null)
 *   2. breadthStaticSentence(무변경)·rotationSentence(서술체) 분기
 *   3. ★게이트 ① 서술체 종결: 전 문장이 `…니다.`/결측 문구로 끝남(명사형 재발 차단)
 *   4. ★게이트 ② 위젯 룰 중복: 위젯 message/hint와 8자 이상 연속 공통부분 없음
 *   5. 금지어휘 전수 스캔(유지) — 단, 연도 패턴은 실제 연도참조(년)만(러셀2000 index명 오탐 회피)
 */
import { describe, it, expect } from 'vitest'

import type { FearGreedIndex, InterestRatesDashboard, InflationDashboard, USIndices } from '@/types/macro'
import {
  fearGreedSentence,
  yieldCurveSentence,
  economySentence,
  globalIndicesSentence,
} from '@/app/market-pulse-v2/macroMeaning'
import { breadthStaticSentence } from '@/app/market-pulse-v2/meaning'
import { rotationSentence } from '@/app/market-pulse-v2/sectorColor'
import type { CdState } from '@/app/market-pulse-v2/sectorColor'
import { macroPulseFixture } from '../../e2e/fixtures/macroPulse'

// 금지 패턴(지시서 Part 6 + §3). 연도는 실제 연도참조(4자리+년)만 — index명 "러셀2000" 오탐 회피(S2-COPYFIX).
const FORBIDDEN = [/오를/, /내릴/, /매수/, /매도/, /목표가/, /확실/, /반드시/, /위기/, /crisis/i, /유사/, /닮/, /(19|20)\d{2}\s*년/]

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

const S = (cd: CdState | null, raw?: CdState | null): { cd_state?: CdState | null; cd_state_raw?: CdState | null } => ({
  cd_state: cd,
  cd_state_raw: raw === undefined ? cd : raw,
})
const rep = (cd: CdState, n: number) => Array.from({ length: n }, () => S(cd))
const BR = (advance: number, decline: number, nh: number, nl: number, ad: number) => ({
  advance, decline, new_high_52w: nh, new_low_52w: nl, ad_line_change: ad, ad_line: 0,
})

describe('fearGreedSentence — 조합 통찰(심리3×변동성2·재료 결측→null)', () => {
  it('6조합 리터럴', () => {
    expect(fearGreedSentence(fg('fear', 'high'))).toBe('공포와 높은 변동성이 겹쳤습니다 — 반등이 나와도 되돌림이 잦은 구간입니다.')
    expect(fearGreedSentence(fg('extreme_fear', 'low'))).toBe('심리는 위축됐지만 변동성은 잠잠합니다 — 패닉보다 관망에 가깝습니다.')
    expect(fearGreedSentence(fg('neutral', 'extreme_high'))).toBe('심리는 중립인데 변동성이 큽니다 — 방향보다 폭이 먼저 움직이는 구간입니다.')
    expect(fearGreedSentence(fg('neutral', 'normal'))).toBe('심리도 변동성도 중립입니다 — 지수보다 개별 재료가 주도하는 구간입니다.')
    expect(fearGreedSentence(fg('greed', 'low'))).toBe('낙관이 이어지는데 변동성은 낮습니다 — 좋은 소식에 둔감해지는 후반부의 모습입니다.')
    expect(fearGreedSentence(fg('extreme_greed', 'high'))).toBe('낙관과 큰 변동성이 함께 있습니다 — 방향은 위쪽이지만 흔들림이 큽니다.')
  })
  it('재료 결측 → null(§1(가) 미렌더, "판정 불가" 아님)', () => {
    expect(fearGreedSentence(fg('greed'))).toBeNull() // vix 없음
    expect(fearGreedSentence(fg('greed', 'weird'))).toBeNull() // level 미지
    expect(fearGreedSentence(null)).toBeNull()
    expect(fearGreedSentence(fg('nope' as FearGreedIndex['rule_key']))).toBeNull() // rule_key 미지
  })
})

describe('yieldCurveSentence — 제약 여부(부호 spread)', () => {
  it('4상태 리터럴', () => {
    expect(yieldCurveSentence(ir('inverted', -0.42))).toBe('금리가 국면의 부담으로 작용하는 쪽입니다(10Y-2Y -0.42%p).')
    expect(yieldCurveSentence(ir('flattening', 0.39))).toBe('금리 여건이 우호에서 부담 쪽으로 넘어가는 중입니다(10Y-2Y +0.39%p).')
    expect(yieldCurveSentence(ir('normal', 1.5))).toBe('금리는 지금 국면의 제약 요인이 아닙니다(10Y-2Y +1.50%p).')
    expect(yieldCurveSentence(ir('steep', 2.8))).toBe('금리 여건이 완화 쪽으로 기울어 있습니다(10Y-2Y +2.80%p).')
  })
  it('unknown/spread null → 판정 불가(마침표)', () => {
    expect(yieldCurveSentence(ir('unknown', null))).toBe('금리차 판정 불가 — 입력 데이터 대기.')
    expect(yieldCurveSentence(ir('normal', null))).toBe('금리차 판정 불가 — 입력 데이터 대기.')
    expect(yieldCurveSentence(null)).toBe('금리차 판정 불가 — 입력 데이터 대기.')
  })
})

describe('economySentence — 물가 3밴드 + 고용(서술체·부호 갭)', () => {
  it('밴드×고용 리터럴', () => {
    expect(economySentence(econ(3.5, 50))).toBe('근원 물가가 목표선을 크게 웃돕니다(갭 +1.50%p), 고용 증가세는 추세선 아래로 둔화됐습니다.')
    expect(economySentence(econ(2.47, -23))).toBe('근원 물가가 목표선에 가까워졌습니다(갭 +0.47%p), 고용은 감소했습니다.')
    expect(economySentence(econ(1.5, 90))).toBe('근원 물가가 목표선을 밑돕니다(갭 -0.50%p), 고용은 견조합니다.')
  })
  it('경계 갭 0·1.0 · 고용 0·87', () => {
    expect(economySentence(econ(2.0, 50))).toContain('가까워졌습니다') // 갭 0
    expect(economySentence(econ(3.0, 50))).toContain('크게 웃돕니다') // 갭 1.0
    expect(economySentence(econ(2.47, 0))).toContain('둔화됐습니다') // nfp 0
    expect(economySentence(econ(2.47, 87))).toContain('견조합니다') // nfp 87
  })
  it('core null → 판정 불가 · nfp null → 고용절 생략', () => {
    expect(economySentence(econ(null, 50))).toBe('물가 판정 불가 — 입력 데이터 대기.')
    expect(economySentence(econ(2.47, null))).toBe('근원 물가가 목표선에 가까워졌습니다(갭 +0.47%p).')
  })
})

describe('globalIndicesSentence — 서술체 + 의미절', () => {
  it('5분기 리터럴', () => {
    expect(globalIndicesSentence(idx(1, 2, 3, 4))).toBe('주요 지수가 모두 올랐습니다 — 상승이 특정 규모에 국한되지 않았습니다.')
    expect(globalIndicesSentence(idx(-1.75, -4.68, -0.16, -4.06))).toBe('주요 지수가 모두 내렸습니다 — 약세가 대형·소형을 가리지 않습니다.')
    expect(globalIndicesSentence(idx(1, 2, 3, -1))).toBe('대형주는 올랐지만 소형주(러셀2000)는 내렸습니다 — 상승이 대형주에 몰렸습니다.')
    expect(globalIndicesSentence(idx(-1, -2, -3, 1))).toBe('대형주는 내렸지만 소형주(러셀2000)는 올랐습니다 — 약세가 대형주에 집중됐습니다.')
    expect(globalIndicesSentence(idx(1, -2, 3, 4))).toBe('지수 간 방향이 갈렸습니다 — 시장 전체보다 업종별 재료가 주도한 하루입니다.')
  })
  it('유효 2개 미만 → 판정 불가', () => {
    expect(globalIndicesSentence(idx(1, null, null, null))).toBe('주요 지수 판정 불가 — 입력 데이터 대기.')
    expect(globalIndicesSentence(null)).toBe('주요 지수 판정 불가 — 입력 데이터 대기.')
  })
  it('"네 지수" 어휘 미사용(유효 3개 정합)', () => {
    expect(globalIndicesSentence(idx(1, 2, 3, null))).not.toContain('네 지수')
  })
})

describe('breadthStaticSentence — 무변경(댐핑 노출)', () => {
  it('댐핑 없음/O 분기', () => {
    expect(breadthStaticSentence(BR(300, 100, 40, 5, 10))).toContain('상승 300 대 하락 100')
    expect(breadthStaticSentence(BR(260, 140, 3, 20, -15))).toContain('한 단계 낮춰')
    expect(breadthStaticSentence(BR(140, 260, 20, 3, 15))).toContain('한 단계 올려')
    expect(breadthStaticSentence(null)).toBeNull()
  })
})

describe('rotationSentence — 서술체(집계 무변경)', () => {
  it('개선/악화 과반', () => {
    expect(rotationSentence([...rep('leading_strengthening', 6), ...rep('lagging_deteriorating', 5)])).toContain('개선 쪽으로 돌고 있습니다')
    expect(rotationSentence([...rep('lagging_deteriorating', 6), ...rep('leading_strengthening', 5)])).toContain('악화 쪽으로 돌고 있습니다')
  })
  it('주도 과반 + 전환 꼬리말', () => {
    expect(rotationSentence([...rep('leading_strengthening', 3), ...rep('leading_weakening', 3), ...rep('lagging_improving', 2), ...rep('lagging_deteriorating', 2), S(null)])).toContain('주도 섹터군이 우위입니다')
    const t = rotationSentence([...rep('leading_strengthening', 6), S('lagging_deteriorating', 'lagging_improving'), ...rep('lagging_deteriorating', 4)])
    expect(t).toContain('전환 확인 중입니다')
  })
  it('갈림 + null 과반', () => {
    expect(rotationSentence([...rep('leading_strengthening', 3), ...rep('leading_weakening', 2), ...rep('lagging_improving', 2), ...rep('lagging_deteriorating', 3), S(null)])).toContain('갈려 있습니다')
    expect(rotationSentence([...rep('leading_strengthening', 3), ...Array.from({ length: 8 }, () => S(null))])).toBeNull()
  })
})

// ── 산출 가능한 전 문장 수집(게이트 ①②·금지스캔 공용) ──
function collectSentences(): string[] {
  const out: (string | null)[] = []
  const rks: FearGreedIndex['rule_key'][] = ['extreme_fear', 'fear', 'neutral', 'greed', 'extreme_greed']
  for (const rk of rks) for (const lv of ['extreme_high', 'high', 'normal', 'low', undefined]) out.push(fearGreedSentence(fg(rk, lv)))
  for (const st of ['inverted', 'flattening', 'normal', 'steep', 'unknown']) out.push(yieldCurveSentence(ir(st, st === 'unknown' ? null : 0.39)))
  for (const core of [3.5, 2.47, 1.5, null]) for (const nfp of [-23, 0, 50, 87, null]) out.push(economySentence(econ(core, nfp)))
  out.push(
    globalIndicesSentence(idx(1, 2, 3, 4)),
    globalIndicesSentence(idx(-1, -2, -3, -4)),
    globalIndicesSentence(idx(1, 2, 3, -1)),
    globalIndicesSentence(idx(-1, -2, -3, 1)),
    globalIndicesSentence(idx(1, -2, 3, 4)),
    globalIndicesSentence(idx(1, null, null, null)),
  )
  out.push(
    rotationSentence([...rep('leading_strengthening', 6), ...rep('lagging_deteriorating', 5)]),
    rotationSentence([...rep('lagging_deteriorating', 6), ...rep('leading_strengthening', 5)]),
    rotationSentence([...rep('leading_strengthening', 3), ...rep('leading_weakening', 3), ...rep('lagging_improving', 2), ...rep('lagging_deteriorating', 2), S(null)]),
    rotationSentence([...rep('lagging_improving', 3), ...rep('lagging_deteriorating', 3), ...rep('leading_strengthening', 2), ...rep('leading_weakening', 2), S(null)]),
    rotationSentence([...rep('leading_strengthening', 3), ...rep('leading_weakening', 2), ...rep('lagging_improving', 2), ...rep('lagging_deteriorating', 3), S(null)]),
    rotationSentence([...rep('leading_strengthening', 6), S('lagging_deteriorating', 'lagging_improving'), ...rep('lagging_deteriorating', 4)]),
  )
  for (const d of [BR(300, 100, 40, 5, 10), BR(260, 140, 3, 20, -15), BR(140, 260, 20, 3, 15), BR(250, 250, 10, 10, 0)]) out.push(breadthStaticSentence(d))
  return out.filter((s): s is string => s != null)
}

describe('★게이트 ① 서술체 종결(명사형 재발 차단)', () => {
  it('전 문장이 …니다. / 입력 데이터 대기. 로 끝남(괄호 제거 후)', () => {
    const END = /(니다|입력 데이터 대기)\.$/
    for (const s of collectSentences()) {
      const normalized = s.replace(/\([^)]*\)/g, '').trim()
      expect(normalized, `종결 위반: "${s}"`).toMatch(END)
    }
  })
})

describe('★게이트 ② 위젯 룰 문장과 중복 차단(8자 연속 공통 없음)', () => {
  it('공포탐욕·수익률 룰 문장과 8자 연속 공통부분 부재', () => {
    const fgx = macroPulseFixture.fear_greed
    const ycs = macroPulseFixture.interest_rates.yield_curve_status
    const widgetStrings = [fgx.message, fgx.action_hint, ycs.message, ycs.historical_note].filter(Boolean) as string[]
    const WIN = 8 // 오탐 시 10으로 상향(사유 보고). 게이트 삭제 금지.
    const ours = collectSentences()
    for (const w of widgetStrings) {
      for (let i = 0; i + WIN <= w.length; i++) {
        const frag = w.slice(i, i + WIN)
        for (const o of ours) {
          expect(o.includes(frag), `위젯 문장과 ${WIN}자 중복: "${frag}" ⊂ "${o}"`).toBe(false)
        }
      }
    }
  })
})

describe('금지어휘 전수 스캔(FE 짝)', () => {
  it('전 문장에 금지 어휘 부재', () => {
    for (const s of collectSentences()) {
      for (const re of FORBIDDEN) {
        expect(s, `"${s}"`).not.toMatch(re)
      }
    }
  })
})

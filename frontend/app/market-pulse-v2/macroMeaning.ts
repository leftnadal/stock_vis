/**
 * HUB-V02-S2 — 거시 허브 위젯의 "이 값이면 무슨 뜻인가" 정적 밴드 문장 단일소스
 * (D-MACRO-SENSE-STATIC = ⓐ 정적 결정론 확장).
 *
 * meaning.ts(홈 4카드 밴드)와 분리한 이유: 소비 타입이 types/macro.ts 계열로 다르고
 * meaning.ts가 이미 비대. 공유 톤/색은 필요 시 meaning.ts에서 import(현재 매크로 문장은
 * SenseNote 슬레이트 텍스트라 색 로직 0).
 *
 * 규율(SYSTEM_PROMPT·stressCopy 승계): 예측·투자권유·과장·확실성 금지, "위기/CRISIS" 금지,
 * 유사성 어휘 금지(analog 소관). 임계는 백엔드 앵커(constants/insights.py)를 따르고
 * 여기서 재분류/새 지표 생성 0 — 부호·구간 비교와 단위 변환까지만.
 *
 * 결측(AUTO-2) = 가짜 "정상" 금지 → "판정 불가 — 입력 데이터 대기".
 * 문구는 상수 템플릿 + 수치 삽입(자유 텍스트 컴포넌트 산재 0, §단일출처).
 *
 * ⚠ 정확 카피는 목업 "HUB-V02-S2 설계안" 기준 디렉터 검수 대상(GUIDE/카피 게이트).
 */
import type {
  FearGreedIndex,
  InterestRatesDashboard,
  InflationDashboard,
  USIndices,
} from '@/types/macro'

/** 결측·판정 불가 공통 문구(S1 확정·서비스 중 — 본문 무변경). 사용처에서 `{주어} {…}.`로 마침표. */
export const SENSE_UNAVAILABLE = '판정 불가 — 입력 데이터 대기'

/** 부호 명시 %p 포맷(ASCII 하이픈): +0.39 / -0.42 (음수는 toFixed가 '-' 포함). */
function signedPp(n: number): string {
  return (n >= 0 ? '+' : '') + n.toFixed(2)
}

// ─────────────────────────────────────────────────────────────
// 1) Fear & Greed × VIX — 조합 통찰(심리 3그룹 × 변동성 2그룹 = 6).
//    위젯 message(심리 서술)와 겹치지 않게 "두 값을 겹쳤을 때만 나오는 읽기"만.
//    재료(심리/변동성) 결측 → null(§1(가) 미렌더): 위젯이 값을 그리므로 조합 재료가
//    빠지면 이 층은 존재하지 않는다("판정 불가" 아님). 그룹핑=enum 묶기(재분류 0).
// ─────────────────────────────────────────────────────────────

type FgGroup = 'fear' | 'neutral' | 'greed'
type VolGroup = 'high' | 'calm'

function fgGroup(rk: FearGreedIndex['rule_key'] | undefined): FgGroup | null {
  if (rk === 'extreme_fear' || rk === 'fear') return 'fear'
  if (rk === 'neutral') return 'neutral'
  if (rk === 'greed' || rk === 'extreme_greed') return 'greed'
  return null
}
function volGroup(level: string | undefined): VolGroup | null {
  if (level === 'extreme_high' || level === 'high') return 'high'
  if (level === 'normal' || level === 'low') return 'calm'
  return null
}

const FG_VOL_SENTENCE: Record<FgGroup, Record<VolGroup, string>> = {
  fear: {
    high: '공포와 높은 변동성이 겹쳤습니다 — 반등이 나와도 되돌림이 잦은 구간입니다.',
    calm: '심리는 위축됐지만 변동성은 잠잠합니다 — 패닉보다 관망에 가깝습니다.',
  },
  neutral: {
    high: '심리는 중립인데 변동성이 큽니다 — 방향보다 폭이 먼저 움직이는 구간입니다.',
    calm: '심리도 변동성도 중립입니다 — 지수보다 개별 재료가 주도하는 구간입니다.',
  },
  greed: {
    high: '낙관과 큰 변동성이 함께 있습니다 — 방향은 위쪽이지만 흔들림이 큽니다.',
    calm: '낙관이 이어지는데 변동성은 낮습니다 — 좋은 소식에 둔감해지는 후반부의 모습입니다.',
  },
}

/**
 * 심리 × 변동성 조합 통찰 한 줄. 재료(fg/rule_key/vix/level) 결측 → null(미렌더, §1(가)).
 */
export function fearGreedSentence(fg: FearGreedIndex | null | undefined): string | null {
  if (!fg) return null
  const s = fgGroup(fg.rule_key)
  const v = volGroup(fg.vix?.level)
  if (!s || !v) return null
  return FG_VOL_SENTENCE[s][v]
}

// ─────────────────────────────────────────────────────────────
// 2) 수익률 곡선 — yield_spread.status 5분기
//    grounded: YIELD_CURVE_RULES(<0 inverted·0–0.5 flattening·0.5–2.5 normal·≥2.5 steep).
//    status enum만 소비(구간 재계산 0). unknown/spread==null → 판정 불가.
// ─────────────────────────────────────────────────────────────

/**
 * yield_spread.status → "금리가 지금 국면에 제약인가" 한 줄(모양 설명은 위젯 몫).
 * 분기·임계 무변경. {s} = 부호 명시 spread(10Y-2Y, ASCII 하이픈). unknown/null → 판정 불가.
 */
export function yieldCurveSentence(ir: InterestRatesDashboard | null | undefined): string {
  const ys = ir?.yield_spread
  if (!ys || ys.status === 'unknown' || ys.spread == null || !Number.isFinite(ys.spread)) {
    return `금리차 ${SENSE_UNAVAILABLE}.`
  }
  const s = signedPp(ys.spread)
  switch (ys.status) {
    case 'inverted':
      return `금리가 국면의 부담으로 작용하는 쪽입니다(10Y-2Y ${s}%p).`
    case 'flattening':
      return `금리 여건이 우호에서 부담 쪽으로 넘어가는 중입니다(10Y-2Y ${s}%p).`
    case 'normal':
      return `금리는 지금 국면의 제약 요인이 아닙니다(10Y-2Y ${s}%p).`
    case 'steep':
      return `금리 여건이 완화 쪽으로 기울어 있습니다(10Y-2Y ${s}%p).`
    default:
      return `금리차 ${SENSE_UNAVAILABLE}.`
  }
}

// ─────────────────────────────────────────────────────────────
// 3) 물가·고용 — 물가 3밴드(갭=core_cpi_yoy−fed_target) + 고용 꼬리말 3분기(nfp_change)
//    grounded: fed_target=2.0(목표선 자체). 갭 1.0%p 경계 = TUNE(올해 미발동·2022–23 재현용).
//    고용 87k = 세인트루이스 연준 2026 breakeven 추정 15k~87k 보수 상단(grounded 외부).
// ─────────────────────────────────────────────────────────────

const INFLATION_GAP_HI = 1.0 // TUNE: 목표 초과 폭 경계(실데이터 누적 후 재튜닝)
const NFP_BREAKEVEN = 87 // grounded(외부): breakeven 추정 보수 상단(k)

/** 물가 갭 3밴드 + 고용 꼬리말(서술체). 내용·임계 무변경. {g}=부호 명시 갭. */
export function economySentence(econ: InflationDashboard | null | undefined): string {
  const core = econ?.inflation?.core_cpi_yoy
  const target = econ?.inflation?.fed_target
  if (core == null || !Number.isFinite(core) || target == null || !Number.isFinite(target)) {
    return `물가 ${SENSE_UNAVAILABLE}.`
  }
  const gap = core - target
  const g = signedPp(gap)
  let priceClause: string
  if (gap >= INFLATION_GAP_HI) priceClause = `근원 물가가 목표선을 크게 웃돕니다(갭 ${g}%p)`
  else if (gap >= 0) priceClause = `근원 물가가 목표선에 가까워졌습니다(갭 ${g}%p)`
  else priceClause = `근원 물가가 목표선을 밑돕니다(갭 ${g}%p)`

  const nfp = econ?.employment?.nfp_change
  if (nfp == null || !Number.isFinite(nfp)) return `${priceClause}.`
  let jobClause: string
  if (nfp < 0) jobClause = ', 고용은 감소했습니다.'
  else if (nfp < NFP_BREAKEVEN) jobClause = ', 고용 증가세는 추세선 아래로 둔화됐습니다.'
  else jobClause = ', 고용은 견조합니다.'
  return `${priceClause}${jobClause}`
}

// ─────────────────────────────────────────────────────────────
// 4) 미국 4지수 — change 부호만 사용(change_percent는 payload에서 null → 판정 금지).
//    4개 동일 음/양 · 러셀만 반대 · 그 밖 혼재 · 유효 2개 미만 → 판정 불가.
//    ⚠ global_indices(해외)·dxy는 범위 밖 — 문장에서 언급조차 하지 않는다.
// ─────────────────────────────────────────────────────────────

type IdxKey = 'sp500' | 'nasdaq' | 'dow' | 'russell2000'
const LARGE_CAPS: IdxKey[] = ['sp500', 'nasdaq', 'dow']

/**
 * USIndices → 한 줄(서술체 + 의미절). change 부호만(change_percent 미사용). 분기 무변경.
 * ⚠ "네 지수"라 쓰지 않는다(유효 3개일 때 사실과 어긋남) — `주요 지수`. 유효(<2) → 판정 불가.
 */
export function globalIndicesSentence(indices: USIndices | null | undefined): string {
  const sign = (k: IdxKey): number | null => {
    const c = indices?.[k]?.change
    return c != null && Number.isFinite(c) ? Math.sign(c) : null
  }
  const large = LARGE_CAPS.map(sign).filter((s): s is number => s !== null)
  const rus = sign('russell2000')
  const allSigns = [...large, ...(rus !== null ? [rus] : [])]
  if (allSigns.length < 2) return `주요 지수 ${SENSE_UNAVAILABLE}.`

  const allUp = allSigns.every((s) => s > 0)
  const allDown = allSigns.every((s) => s < 0)
  if (allUp) return '주요 지수가 모두 올랐습니다 — 상승이 특정 규모에 국한되지 않았습니다.'
  if (allDown) return '주요 지수가 모두 내렸습니다 — 약세가 대형·소형을 가리지 않습니다.'

  // 대형주 3종이 한 방향으로 일치하고 러셀(소형주)만 반대인 경우.
  const largeAllUp = large.length === LARGE_CAPS.length && large.every((s) => s > 0)
  const largeAllDown = large.length === LARGE_CAPS.length && large.every((s) => s < 0)
  if (rus !== null && largeAllUp && rus < 0)
    return '대형주는 올랐지만 소형주(러셀2000)는 내렸습니다 — 상승이 대형주에 몰렸습니다.'
  if (rus !== null && largeAllDown && rus > 0)
    return '대형주는 내렸지만 소형주(러셀2000)는 올랐습니다 — 약세가 대형주에 집중됐습니다.'

  return '지수 간 방향이 갈렸습니다 — 시장 전체보다 업종별 재료가 주도한 하루입니다.'
}

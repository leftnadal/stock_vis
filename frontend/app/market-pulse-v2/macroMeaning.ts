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

/** 결측·판정 불가 공통 문구(AUTO-2 — S1 A-2 규율 미러: 가짜 "정상" 금지). */
export const SENSE_UNAVAILABLE = '판정 불가 — 입력 데이터 대기'

// ─────────────────────────────────────────────────────────────
// 1) Fear & Greed × VIX — 심리 3구간 × 변동성 2구간 = 6분기
//    rule_key(5값)→심리 3그룹, vix.level(4값)→변동성 2그룹. vix 없으면 변동성절 생략.
//    임계 grounded: VIX_RULES(≥30 extreme_high·20–30 high·12–20 normal·<12 low) — 여기선
//    이미 분류된 level enum만 소비(재분류 0).
// ─────────────────────────────────────────────────────────────

const SENTIMENT_PHRASE: Record<FearGreedIndex['rule_key'], string> = {
  extreme_fear: '투자 심리가 크게 위축된 방어 구간',
  fear: '투자 심리가 위축된 신중 구간',
  neutral: '투자 심리가 중립 구간',
  greed: '투자 심리가 낙관 구간',
  extreme_greed: '투자 심리가 과열에 가까운 낙관 구간',
}

/** vix.level → 변동성 2그룹(확대 경계 / 안정). 미지/부재 → null(변동성절 생략). */
function volatilityClause(level: string | undefined): string | null {
  if (level === 'extreme_high' || level === 'high') return '변동성이 커 흔들림에 유의할 구간'
  if (level === 'normal' || level === 'low') return '변동성은 대체로 안정적'
  return null
}

/**
 * 심리(rule_key) × 변동성(vix.level) 한 줄. rule_key 미지 → 판정 불가.
 * vix 없거나 미지 level → 변동성절 생략(심리만).
 */
export function fearGreedSentence(fg: FearGreedIndex | null | undefined): string {
  if (!fg || !(fg.rule_key in SENTIMENT_PHRASE)) return SENSE_UNAVAILABLE
  const sentiment = SENTIMENT_PHRASE[fg.rule_key]
  const vol = volatilityClause(fg.vix?.level)
  return vol ? `${sentiment} — ${vol}.` : `${sentiment}.`
}

// ─────────────────────────────────────────────────────────────
// 2) 수익률 곡선 — yield_spread.status 5분기
//    grounded: YIELD_CURVE_RULES(<0 inverted·0–0.5 flattening·0.5–2.5 normal·≥2.5 steep).
//    status enum만 소비(구간 재계산 0). unknown/spread==null → 판정 불가.
// ─────────────────────────────────────────────────────────────

const YIELD_STATUS_PHRASE: Record<'inverted' | 'flattening' | 'normal' | 'steep', string> = {
  inverted: '장단기 금리가 역전 — 경기 둔화 우려가 반영된 구간',
  flattening: '장단기 금리차가 축소되는 사이클 후반 구간',
  normal: '장단기 금리차가 정상 범위',
  steep: '장단기 금리차가 확대 — 경기·완화 기대가 반영된 구간',
}

/** yield_spread.status → 한 줄(spread 값 병기). unknown/null → 판정 불가. */
export function yieldCurveSentence(ir: InterestRatesDashboard | null | undefined): string {
  const ys = ir?.yield_spread
  if (!ys || ys.status === 'unknown' || ys.spread == null || !Number.isFinite(ys.spread)) {
    return `금리차 ${SENSE_UNAVAILABLE}`
  }
  if (!(ys.status in YIELD_STATUS_PHRASE)) return `금리차 ${SENSE_UNAVAILABLE}`
  const phrase = YIELD_STATUS_PHRASE[ys.status as keyof typeof YIELD_STATUS_PHRASE]
  return `${phrase}(10Y−2Y ${ys.spread.toFixed(2)}%p).`
}

// ─────────────────────────────────────────────────────────────
// 3) 물가·고용 — 물가 3밴드(갭=core_cpi_yoy−fed_target) + 고용 꼬리말 3분기(nfp_change)
//    grounded: fed_target=2.0(목표선 자체). 갭 1.0%p 경계 = TUNE(올해 미발동·2022–23 재현용).
//    고용 87k = 세인트루이스 연준 2026 breakeven 추정 15k~87k 보수 상단(grounded 외부).
// ─────────────────────────────────────────────────────────────

const INFLATION_GAP_HI = 1.0 // TUNE: 목표 초과 폭 경계(실데이터 누적 후 재튜닝)
const NFP_BREAKEVEN = 87 // grounded(외부): breakeven 추정 보수 상단(k)

/** 물가 갭 3밴드 + 고용 꼬리말. core_cpi_yoy==null → 판정 불가. nfp==null → 고용절 생략. */
export function economySentence(econ: InflationDashboard | null | undefined): string {
  const core = econ?.inflation?.core_cpi_yoy
  const target = econ?.inflation?.fed_target
  if (core == null || !Number.isFinite(core) || target == null || !Number.isFinite(target)) {
    return `물가 ${SENSE_UNAVAILABLE}`
  }
  const gap = core - target
  let priceClause: string
  if (gap >= INFLATION_GAP_HI) priceClause = `근원 물가가 목표선을 크게 웃도는 구간(갭 +${gap.toFixed(2)}%p)`
  else if (gap >= 0) priceClause = `근원 물가가 목표선에 근접(갭 +${gap.toFixed(2)}%p)`
  else priceClause = `근원 물가가 목표선을 밑도는 구간(갭 ${gap.toFixed(2)}%p)`

  const nfp = econ?.employment?.nfp_change
  if (nfp == null || !Number.isFinite(nfp)) return `${priceClause}.`
  let jobClause: string
  if (nfp < 0) jobClause = '고용은 감소'
  else if (nfp < NFP_BREAKEVEN) jobClause = '고용 증가세는 추세선 아래로 둔화'
  else jobClause = '고용은 견조'
  return `${priceClause}, ${jobClause}.`
}

// ─────────────────────────────────────────────────────────────
// 4) 미국 4지수 — change 부호만 사용(change_percent는 payload에서 null → 판정 금지).
//    4개 동일 음/양 · 러셀만 반대 · 그 밖 혼재 · 유효 2개 미만 → 판정 불가.
//    ⚠ global_indices(해외)·dxy는 범위 밖 — 문장에서 언급조차 하지 않는다.
// ─────────────────────────────────────────────────────────────

type IdxKey = 'sp500' | 'nasdaq' | 'dow' | 'russell2000'
const LARGE_CAPS: IdxKey[] = ['sp500', 'nasdaq', 'dow']

/** USIndices → 한 줄. change 부호 집계. 유효(<2) → 판정 불가. */
export function globalIndicesSentence(indices: USIndices | null | undefined): string {
  if (!indices) return SENSE_UNAVAILABLE
  const sign = (k: IdxKey): number | null => {
    const c = indices[k]?.change
    return c != null && Number.isFinite(c) ? Math.sign(c) : null
  }
  const large = LARGE_CAPS.map(sign).filter((s): s is number => s !== null)
  const rus = sign('russell2000')
  const allSigns = [...large, ...(rus !== null ? [rus] : [])]
  if (allSigns.length < 2) return `주요 지수 ${SENSE_UNAVAILABLE}`

  const allUp = allSigns.every((s) => s > 0)
  const allDown = allSigns.every((s) => s < 0)
  if (allUp) return '미국 주요 지수가 동반 강세.'
  if (allDown) return '미국 주요 지수가 동반 약세.'

  // 대형주 3종이 한 방향으로 일치하고 러셀(소형주)만 반대인 경우.
  const largeAllUp = large.length === LARGE_CAPS.length && large.every((s) => s > 0)
  const largeAllDown = large.length === LARGE_CAPS.length && large.every((s) => s < 0)
  if (rus !== null && largeAllUp && rus < 0) return '대형주는 강세, 소형주(러셀)만 약세로 엇갈림.'
  if (rus !== null && largeAllDown && rus > 0) return '대형주는 약세, 소형주(러셀)만 강세로 엇갈림.'

  return '지수 방향이 혼재.'
}

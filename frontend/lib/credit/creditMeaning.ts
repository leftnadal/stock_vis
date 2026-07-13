// 크레딧 매크로 스트립 — 의미 레이어(헤드라인 + 툴팁) 규칙/사전. CS-CREDIT-CONSUME 의미 2층.
// 전부 프론트 상수(백엔드 무변경). 순수 함수 = 테스트 용이.
import type { Grade } from '@/components/common/colorSemantics';
import type { CreditSignal } from '@/services/creditSignalsService';

// 심각도 순위 (헤드라인 톤·나열 순서).
export const GRADE_SEVERITY: Record<Grade, number> = {
  gray: 0,
  yellow: 1,
  orange: 2,
  red: 3,
};

/** 6종 중 최악(가장 심각한) grade. */
export function worstGrade(signals: CreditSignal[]): Grade {
  return signals.reduce<Grade>(
    (w, s) => (GRADE_SEVERITY[s.grade] > GRADE_SEVERITY[w] ? s.grade : w),
    'gray',
  );
}

export interface Headline {
  text: string;
  grade: Grade; // 톤·dot 색 결정 (최악 grade)
}

// 해석 패턴 매칭 (초기 6건) — 비-gray 신호 집합 기반.
// ① 최악 grade가 톤·dot 색 결정, ② 비-gray 심각도순 나열(폴백), ③ 패턴 문장.
export function deriveHeadline(signals: CreditSignal[]): Headline {
  const nonGray = signals.filter((s) => s.grade !== 'gray');

  // 전부 gray → 저채도 안정 문장.
  if (nonGray.length === 0) {
    return { text: '크레딧 전반 안정 — 특이 신호 없음', grade: 'gray' };
  }

  const worst = worstGrade(signals);
  const keys = new Set(nonGray.map((s) => s.key));
  const only = (k: string) => keys.size === 1 && keys.has(k);

  // CCC 단독 상승 = HY 내부 분화
  if (only('CCC_OAS')) {
    return { text: 'HY 내부 분화 — CCC 스프레드 단독 상승', grade: worst };
  }
  // HY + CCC 동반 = 광범위 확대
  if (keys.has('HY_OAS') && keys.has('CCC_OAS')) {
    return { text: '광범위 신용 확대 — HY·CCC 동반 상승', grade: worst };
  }
  // CURVE 단독 = 금리 축
  if (only('CURVE_10Y2Y')) {
    return { text: '금리 곡선 축 신호 — 10Y-2Y 이례적', grade: worst };
  }
  // VIX 단독 = 변동성 축
  if (only('VIX')) {
    return { text: '변동성 축 신호 — VIX 이례적', grade: worst };
  }

  // 기타 조합 = 중립 폴백: 비-gray 심각도순 나열 + 관찰 n건.
  const names = [...nonGray]
    .sort((a, b) => GRADE_SEVERITY[b.grade] - GRADE_SEVERITY[a.grade])
    .map((s) => s.name)
    .join(', ');
  return { text: `관찰 ${nonGray.length}건 — ${names}`, grade: worst };
}

// ── 툴팁: signal_key당 정적 사전 (지표 정의 1문장, 평이한 한국어) ────────────
export const CREDIT_SIGNAL_DEF: Record<string, string> = {
  HY_OAS: '고수익(하이일드) 회사채가 국채 대비 얹는 가산금리 — 벌어질수록 신용 위험 경계가 커진다.',
  IG_OAS: '투자등급 회사채의 국채 대비 가산금리 — 우량 신용의 스트레스 척도.',
  BBB_OAS: '투자등급 최하단(BBB) 회사채 가산금리 — 등급 강등 경계선의 압력.',
  CCC_OAS: '최저신용(CCC) 회사채 가산금리 — 부실·디폴트 위험의 최전선.',
  CURVE_10Y2Y: '10년−2년 국채 금리차 — 음수(역전)는 경기침체 선행 신호로 읽힌다.',
  VIX: 'S&P500 옵션 내재 변동성 지수(‘공포지수’) — 높을수록 시장 불안이 크다.',
};

// 밴드 기준 고정 표기 (지시서 리터럴 — 강도 눈금 교육용 카피).
export const GRADE_BAND_TEXT = 'gray |z|<1 · yellow 1–2 · orange 2–3 · red ≥3';

/** 30일 스파크 방향 (첫↔마지막, 소폭은 횡보). */
export function sparkDirection(spark: number[]): '상승' | '하락' | '횡보' {
  if (!spark || spark.length < 2) return '횡보';
  const first = spark[0];
  const last = spark[spark.length - 1];
  const base = Math.abs(first) || 1;
  const rel = (last - first) / base;
  if (rel > 0.02) return '상승';
  if (rel < -0.02) return '하락';
  return '횡보';
}

/** 현재 상태 템플릿 — 값·z·30일 방향. */
export function signalStateLine(sig: CreditSignal): string {
  if (sig.z === null) {
    return `현재 ${sig.value.toFixed(2)} · 콜드스타트(관측 부족)`;
  }
  const zTxt = `${sig.z >= 0 ? '+' : ''}${sig.z.toFixed(2)}`;
  return `현재 ${sig.value.toFixed(2)} · z ${zTxt} · 최근 30일 ${sparkDirection(
    sig.spark.map((p) => p.value),
  )}`;
}

export interface ChipInfo {
  def: string;
  state: string;
  band: string;
}

/** 칩 툴팁 콘텐츠 조립 (사전 + 현재 상태 + 고정 밴드). */
export function buildChipInfo(sig: CreditSignal): ChipInfo {
  return {
    def: CREDIT_SIGNAL_DEF[sig.key] ?? sig.name,
    state: signalStateLine(sig),
    band: GRADE_BAND_TEXT,
  };
}

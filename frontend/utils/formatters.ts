/**
 * 공통 포맷팅 유틸리티 함수
 * 중복 코드 제거를 위해 통합
 */

/**
 * 숫자를 USD 통화 형식으로 포맷
 */
export const formatCurrency = (value: number | string): string => {
  const numValue = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(numValue)) return '$0.00';

  return new Intl.NumberFormat('ko-KR', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(numValue);
};

/**
 * KRW 통화 포맷 (₩ 정수원, ko-KR 천단위 구분) — Slice 20a advisory 화면용.
 */
export const formatKRW = (value: number | string): string => {
  const numValue = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(numValue)) return '₩0';

  return new Intl.NumberFormat('ko-KR', {
    style: 'currency',
    currency: 'KRW',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(numValue);
};

/**
 * 퍼센트 포맷 (+/- 기호 포함)
 */
export const formatPercent = (value: number | string): string => {
  const numValue = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(numValue)) return '0.00%';

  return `${numValue >= 0 ? '+' : ''}${numValue.toFixed(2)}%`;
};

/**
 * 큰 숫자를 축약형으로 포맷 (1K, 1M, 1B)
 */
export const formatLargeNumber = (value: number | string): string => {
  const numValue = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(numValue)) return '0';

  if (numValue >= 1e12) return `${(numValue / 1e12).toFixed(2)}T`;
  if (numValue >= 1e9) return `${(numValue / 1e9).toFixed(2)}B`;
  if (numValue >= 1e6) return `${(numValue / 1e6).toFixed(2)}M`;
  if (numValue >= 1e3) return `${(numValue / 1e3).toFixed(2)}K`;
  return numValue.toFixed(2);
};

/**
 * 거래량 포맷
 */
export const formatVolume = (value: number | string): string => {
  const numValue = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(numValue)) return '0';

  if (numValue >= 1e6) return `${(numValue / 1e6).toFixed(2)}M`;
  if (numValue >= 1e3) return `${(numValue / 1e3).toFixed(2)}K`;
  return numValue.toString();
};

// ── 숫자 표시 규약 '가' (PART B-FE, univ-p15-v01) — 단일 포맷 유틸, 전 monitor 표면 적용 ──
// 타입별 규약(반드시 이 함수들을 통해서만 표시):
//  · 퍼센트          → formatPctRule (소수 2자리, 반올림 0이면 부호 제거)
//  · 가격            → formatPrice   (소수 2자리 + 통화기호 + 천단위, compact=축약 K/M/B)
//  · 점수·z·Δ        → formatScore   (소수 3자리 고정)
//  · 방향기호 ▲▼     → dirArrow      (반올림 0이면 기호 생략 — ▲0.00 자기모순 방지)
//  · 지표 원값        → formatIndicator (기본 소수 2자리)
type NumLike = number | string | null | undefined

function toFiniteNumber(value: NumLike): number | null {
  if (value == null) return null
  const n = typeof value === 'string' ? Number(value) : value
  return Number.isFinite(n) ? n : null
}

// 부동소수 반올림 아티팩트(-0 등) 방지 — round-trip을 Number(toFixed(digits))로 수행.
function roundTo(value: number, digits: number): number {
  const rounded = Number(value.toFixed(digits))
  return rounded === 0 ? 0 : rounded // -0 정규화
}

/**
 * 퍼센트 포맷 — 소수 2자리 고정. 반올림 결과가 0.00%면 부호(및 방향)를 제거해
 * "-0.00%" 같은 자기모순 표시를 없앤다. signed=true면 양수에 '+'를 붙인다(0은 예외).
 * 예: -0.0023 → "0.00%" · 18.1818 → "18.18%" · (signed) 10 → "+10.00%"
 */
export function formatPctRule(value: NumLike, opts?: { signed?: boolean }): string {
  const n = toFiniteNumber(value)
  if (n === null) return '—'
  const rounded = roundTo(n, 2)
  if (rounded === 0) return '0.00%'
  const sign = opts?.signed && rounded > 0 ? '+' : ''
  return `${sign}${rounded.toFixed(2)}%`
}

/**
 * 가격 포맷 — 소수 2자리 + 통화기호(통화코드 기반) + 천단위 구분.
 * compact=true면 대용량 축약 1자리(K/M/B) + 통화기호(거래대금 등).
 * 예: 1160.0618 → "$1,160.06" · compact: 1635998208.75 → "$1.6B"
 */
export function formatPrice(
  value: NumLike,
  currencyCode = 'USD',
  opts?: { compact?: boolean }
): string {
  const n = toFiniteNumber(value)
  if (n === null) return '—'
  try {
    if (opts?.compact) {
      return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: currencyCode,
        notation: 'compact',
        maximumFractionDigits: 1,
      }).format(n)
    }
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currencyCode,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(n)
  } catch {
    return `$${n.toFixed(opts?.compact ? 1 : 2)}`
  }
}

/**
 * 점수·z·Δ 포맷 — 소수 3자리 고정(digits override 가능). signed=true면 양수에 '+'.
 * 예: -0.0249 → "-0.025" · (signed) 0.03 → "+0.030"
 */
export function formatScore(
  value: NumLike,
  opts?: { signed?: boolean; digits?: number }
): string {
  const n = toFiniteNumber(value)
  if (n === null) return '—'
  const digits = opts?.digits ?? 3
  const rounded = roundTo(n, digits)
  const sign = opts?.signed && rounded > 0 ? '+' : ''
  return `${sign}${rounded.toFixed(digits)}`
}

/**
 * 방향기호(▲/▼) — 표시 정밀도(displayDigits)로 반올림한 결과가 0이면 기호를 생략한다.
 * "▲0.00"(부호와 값이 모순되는 표시)을 만들지 않기 위함.
 */
export function dirArrow(value: NumLike, displayDigits = 2): '▲' | '▼' | '' {
  const n = toFiniteNumber(value)
  if (n === null) return ''
  const rounded = roundTo(n, displayDigits)
  if (Math.abs(rounded) === 0) return ''
  return rounded > 0 ? '▲' : '▼'
}

/**
 * 지표 원값 포맷 — 기본 소수 2자리(digits override 가능).
 * 예: RSI 41.000 → "41.00"
 */
export function formatIndicator(value: NumLike, digits = 2): string {
  const n = toFiniteNumber(value)
  if (n === null) return '—'
  return n.toFixed(digits)
}

/**
 * 날짜 포맷
 */
export const formatDate = (date: string | Date, format: 'short' | 'long' = 'short'): string => {
  const dateObj = typeof date === 'string' ? new Date(date) : date;

  if (format === 'short') {
    return dateObj.toLocaleDateString('ko-KR', {
      month: 'short',
      day: 'numeric'
    });
  }

  return dateObj.toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });
};

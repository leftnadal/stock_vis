// 이벤트 캘린더 색 토큰 — 시각 계약(docs/design/evt_phase1_mockups.html)의
// --earn/--div/--split/--macro/--hol/--crit/--high/--beat/--miss/--stable/--fluid/--unk
// 팔레트를 프로젝트 Tailwind 리터럴로 근사한다. 동적 클래스명 생성 금지(퍼지 안전,
// components/common/colorSemantics.ts와 동일 원칙) — Record 룩업만 사용한다.
import type { DateTrust, EventKind, SurpriseDir } from '@/types/eventCalendar';

const BADGE_BASE = 'inline-block rounded px-1.5 py-0.5 text-[11px] font-medium leading-[18px]';

export function badgeClass(colorClasses: string): string {
  return `${BADGE_BASE} ${colorClasses}`;
}

// b-earn / b-div / b-split / b-macro / b-hol
export const KIND_BADGE_CLASS: Record<EventKind, string> = {
  earnings: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300',
  dividend: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
  split: 'bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300',
  split_effective: 'bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300',
  macro: 'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-300',
  holiday: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300',
};

export const KIND_LABEL: Record<EventKind, string> = {
  earnings: '어닝',
  dividend: '배당락',
  split: '분할 예정',
  split_effective: '분할 발효',
  macro: '거시',
  holiday: '휴장',
};

// b-crit / b-high (macro importance + d_day==0 today 강조)
export const IMPORTANCE_BADGE_CLASS: Record<string, string> = {
  critical: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
  high: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',
  medium: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300',
  low: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300',
  today: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
  default: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300',
};

// b-beat / b-miss (surprise 부호 색). flat = b-unk와 동급(중립 회색).
export const SURPRISE_BADGE_CLASS: Record<SurpriseDir, string> = {
  beat: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
  miss: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
  flat: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300',
};

// b-stable / b-fluid / b-unk (date_trust)
export const TRUST_BADGE_CLASS: Record<DateTrust, string> = {
  stable: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  fluid: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
  unconfirmed: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300',
};

// b-ses (BMO/AMC 세션 뱃지 — 값 있을 때만 표기, EVT-SESSION)
export const SESSION_BADGE_CLASS =
  'bg-gray-50 text-gray-600 border border-gray-200 dark:bg-gray-800/60 dark:text-gray-300 dark:border-gray-700';

// hol-row 빗금 배경(테마 안전 — 반투명 회색이라 라이트/다크 공통).
export const HOLIDAY_STRIPE_BG =
  'repeating-linear-gradient(135deg, rgba(107,114,128,0.14) 0px, rgba(107,114,128,0.14) 6px, transparent 6px, transparent 12px)';

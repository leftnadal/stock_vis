// 이벤트 캘린더 렌더 전용 포맷 헬퍼 (EVT-IMPL-4 STEP 3). ⚠️ 값의 진실 = BE 응답
// (EventItem) — 여기서는 표시 텍스트 조립만 한다(판정·재계산 금지, lib/monitor/display.ts와
// 동일 원칙).
import { format, parseISO } from 'date-fns';
import { ko } from 'date-fns/locale';

import type {
  DividendDetail,
  EarningsDetail,
  EventItem,
  EventSession,
  HolidayDetail,
  MacroDetail,
  SplitDetail,
} from '@/types/eventCalendar';

const DASH = '—';

function fmtNum(n: number | null | undefined): string {
  if (n === null || n === undefined) return DASH;
  return n.toLocaleString('ko-KR');
}

// 15800000000 → "15.8B" 축약 표기 (원시 자릿수 그대로 두면 가독성 붕괴).
export function fmtCompact(n: number | null | undefined): string {
  if (n === null || n === undefined) return DASH;
  const abs = Math.abs(n);
  if (abs >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(1)}B`;
  if (abs >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return fmtNum(n);
}

export function fmtDateShort(dateStr: string): string {
  return format(parseISO(dateStr), 'M/d (EEEEEE)', { locale: ko });
}

export function fmtDday(dDay: number): string {
  if (dDay === 0) return 'D-day';
  return dDay > 0 ? `D-${dDay}` : `D+${-dDay}`;
}

export function formatDetail(item: EventItem): string {
  switch (item.kind) {
    case 'earnings': {
      const d = item.detail as unknown as EarningsDetail;
      if (d.eps_actual !== null && d.eps_actual !== undefined) {
        return `EPS ${fmtNum(d.eps_actual)} vs 예상 ${fmtNum(d.eps_estimated)}`;
      }
      return `EPS 예상 ${fmtNum(d.eps_estimated)} · 매출 예상 ${fmtCompact(d.revenue_estimated)}`;
    }
    case 'dividend': {
      const d = item.detail as unknown as DividendDetail;
      const amount = d.dividend_amount !== null && d.dividend_amount !== undefined
        ? `$${fmtNum(d.dividend_amount)}`
        : DASH;
      return `배당 ${amount} · 지급 ${d.payment_date ?? DASH} · ${d.frequency ?? DASH}`;
    }
    case 'split':
    case 'split_effective': {
      const d = item.detail as unknown as SplitDetail;
      return `${d.numerator} : ${d.denominator}`;
    }
    case 'macro': {
      const d = item.detail as unknown as MacroDetail;
      const actual = d.actual_value ? ` · 실제 ${d.actual_value}` : '';
      return `예상 ${d.forecast_value ?? DASH}${actual} · 이전 ${d.previous_value ?? DASH}`;
    }
    case 'holiday': {
      const d = item.detail as unknown as HolidayDetail;
      const next = d.next_trading_day ? fmtDateShort(d.next_trading_day) : DASH;
      return `미국 정규장 없음 — 이벤트 없음. 다음 거래일 ${next}`;
    }
    default:
      return '';
  }
}

const SESSION_LABEL: Record<EventSession, string> = {
  BMO: '개장 전',
  AMC: '장 마감 후',
};

export interface TimeCellText {
  main: string;
  sub: string | null;
}

// 대표시각 규칙(계약 §대표시각 규칙) — 저장은 ET, 표시는 KST 병기. earnings/macro는
// event_dt_kst(있으면) 시각 변환, dividend/split류는 날짜만(BE가 KST 없음)+고정 문구.
export function formatTime(item: EventItem): TimeCellText {
  const kst = item.event_dt_kst
    ? format(parseISO(item.event_dt_kst), 'M/d HH:mm', { locale: ko })
    : null;

  if (item.kind === 'holiday') {
    return { main: '종일', sub: null };
  }
  if (item.kind === 'earnings') {
    const main = item.session ? SESSION_LABEL[item.session] : '세션 미정';
    return { main, sub: kst ? `KST ${kst}` : null };
  }
  if (item.kind === 'dividend' || item.kind === 'split' || item.kind === 'split_effective') {
    return { main: fmtDateShort(item.event_date_et), sub: 'KST 익일' };
  }
  // macro
  if (item.event_time_et) {
    return { main: `${item.event_time_et} ET`, sub: kst ? `KST ${kst}` : null };
  }
  return { main: fmtDateShort(item.event_date_et), sub: null };
}

export function sourceLabel(sources: EventItem['sources']): string | null {
  if (sources.length >= 2) return '모니터·관심';
  if (sources[0] === 'watchlist') return '관심';
  if (sources[0] === 'monitor') return '모니터';
  return null;
}

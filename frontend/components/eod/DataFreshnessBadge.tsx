'use client';

import { useSyncExternalStore } from 'react';
import { AlertTriangle } from 'lucide-react';

interface DataFreshnessBadgeProps {
  tradingDate: string;
  generatedAt: string;
  /**
   * Baker 판단값. ⑥ S2 이후 **표시 판정에 쓰지 않는다**(계약 유지 목적으로만 수신).
   * baker의 `is_stale = generated_at.date() != date.today()`는 UTC date와 로컬(KST) date를
   * 비교하므로 18:30 ET 슬롯에서 구조적으로 항상 True다 — 신선도 근거로 쓸 수 없다.
   */
  isStale?: boolean;
  /** 결번 판정 기준시각 주입(테스트용). 미지정 시 마운트 후 실제 시각. */
  now?: Date;
}

const WEEKDAY_KO = ['일', '월', '화', '수', '목', '금', '토'] as const;
const DAY_MS = 24 * 60 * 60 * 1000;

// bake 슬롯 = 미 동부(ET) 평일 18:30 (PeriodicTask run-eod-pipeline `30 18 1-5 * *` @America/New_York).
const SLOT_HOUR_ET = 18;
const SLOT_MINUTE_ET = 30;
const MAX_LOOKBACK_DAYS = 14;

/** 경고를 켜는 결번 임계. 1회 결번(주말·당일 슬롯 전 포함)은 경고하지 않는다. */
export const MISSED_SLOT_WARN_THRESHOLD = 2;

/** 'YYYY-MM-DD' → UTC 자정 epoch(ms). 파싱 실패 시 null. */
function parseDateOnly(dateStr: string): number | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(dateStr);
  if (!m) return null;
  const ms = Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  return Number.isNaN(ms) ? null : ms;
}

function isWeekday(utcMs: number): boolean {
  const d = new Date(utcMs).getUTCDay();
  return d >= 1 && d <= 5;
}

/** now를 ET 벽시계로 환산 — 날짜(UTC 자정 기준 ms)와 자정으로부터의 분. */
function etWallClock(now: Date): { dateMs: number; minutes: number } | null {
  try {
    const parts = new Intl.DateTimeFormat('en-US', {
      timeZone: 'America/New_York',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    }).formatToParts(now);
    const get = (t: string) => Number(parts.find((p) => p.type === t)?.value);
    const y = get('year');
    const mo = get('month');
    const d = get('day');
    const h = get('hour');
    const mi = get('minute');
    if ([y, mo, d, h, mi].some((v) => Number.isNaN(v))) return null;
    return { dateMs: Date.UTC(y, mo - 1, d), minutes: (h % 24) * 60 + mi };
  } catch {
    return null;
  }
}

/**
 * tradingDate 이후로 **이미 지나간** bake 슬롯(ET 평일 18:30)의 개수.
 *
 * 0 = 최신 · 1 = 직전 슬롯 1회분 미반영(정상 범위) · 2 이상 = 결번 경고.
 * 금요일 거래일 + 월요일(ET 18:30 전) 접속 = 0 → 경고 없음.
 *
 * ⚠ 신선도 경고의 **유일한 판정식**이다. BAKER-ISSTALE-REDEF 위임 착지 시 본문만 교체한다.
 * (미국 증시 휴장일 달력은 아직 재료가 없어 미반영 — 임계 2가 단일 휴장일을 흡수한다.)
 */
export function countMissedBakeSlots(tradingDate: string, now: Date): number {
  const dataMs = parseDateOnly(tradingDate);
  const et = etWallClock(now);
  if (dataMs === null || et === null) return 0;

  // 이미 지나간 가장 최근 슬롯의 날짜
  let slotMs = et.dateMs;
  if (!(isWeekday(slotMs) && et.minutes >= SLOT_HOUR_ET * 60 + SLOT_MINUTE_ET)) {
    slotMs -= DAY_MS;
  }
  for (let i = 0; i < 7 && !isWeekday(slotMs); i += 1) slotMs -= DAY_MS;

  // (tradingDate, 최근 슬롯] 구간의 평일 수
  let missed = 0;
  let cur = dataMs + DAY_MS;
  for (let i = 0; cur <= slotMs && i < MAX_LOOKBACK_DAYS; i += 1) {
    if (isWeekday(cur)) missed += 1;
    cur += DAY_MS;
  }
  return missed;
}

/** 'YYYY-MM-DD' → '2026년 09월 14일(월)'. */
export function formatTradingDate(dateStr: string): string {
  const ms = parseDateOnly(dateStr);
  if (ms === null) return dateStr;
  const [year, month, day] = dateStr.split('-');
  return `${year}년 ${month}월 ${day}일(${WEEKDAY_KO[new Date(ms).getUTCDay()]})`;
}

/** 생성시각 → KST 고정 표기(뷰어 TZ에 흔들리지 않도록 timeZone 명시 = hydration 안전). */
export function formatGeneratedAt(isoString: string): string {
  try {
    return new Date(isoString).toLocaleString('ko-KR', {
      timeZone: 'Asia/Seoul',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
  } catch {
    return isoString;
  }
}

/**
 * 데이터 신선도 — **사실 서술**(⑥ S2).
 *
 * stale 이분법(제목을 통째로 "어제 데이터입니다"로 대체)을 폐기하고,
 * h1은 항상 유지한 채 "어느 거래일 마감 기준인지 · 언제 구웠는지"를 상시 표시한다.
 * 경고 줄은 bake 슬롯이 2회 이상 결번일 때만 덧붙는다.
 */
const subscribeNever = () => () => {};

/** 하이드레이션 완료 여부. 서버·첫 클라이언트 렌더는 false로 맞춰 불일치를 없앤다(#24). */
function useIsHydrated(): boolean {
  return useSyncExternalStore(
    subscribeNever,
    () => true,
    () => false,
  );
}

export function DataFreshnessBadge({ tradingDate, generatedAt, now }: DataFreshnessBadgeProps) {
  // 현재 시각은 하이드레이션 이후에만 읽는다 — 서버 렌더와 첫 클라이언트 렌더가 항상 같다.
  const hydrated = useIsHydrated();
  const missedSlots = hydrated ? countMissedBakeSlots(tradingDate, now ?? new Date()) : 0;

  const isMissing = missedSlots >= MISSED_SLOT_WARN_THRESHOLD;

  return (
    <div data-guide="dashboard.freshness" className="flex flex-col items-end gap-1 min-w-0">
      <div className="flex flex-wrap items-center justify-end gap-x-2 gap-y-1 min-w-0">
        <h1 className="text-base font-bold text-gray-900 dark:text-white whitespace-nowrap">
          오늘의 시그널
        </h1>
        <span className="inline-flex items-center gap-1.5 min-w-0">
          <span
            className="w-2 h-2 rounded-full bg-green-500 dark:bg-green-400 flex-shrink-0"
            aria-hidden="true"
          />
          <span className="text-xs text-gray-600 dark:text-gray-300 whitespace-nowrap">
            {formatTradingDate(tradingDate)} 장 마감 기준
          </span>
          <span className="text-xs text-gray-400 dark:text-gray-500 whitespace-nowrap">
            · {formatGeneratedAt(generatedAt)} 생성
          </span>
        </span>
      </div>

      {isMissing && (
        <div className="flex items-center gap-1.5">
          <AlertTriangle className="w-3.5 h-3.5 text-amber-500 dark:text-amber-400 flex-shrink-0" />
          <span className="text-xs text-amber-700 dark:text-amber-300">
            이후 {missedSlots}회 갱신이 건너뛰어졌습니다
          </span>
        </div>
      )}
    </div>
  );
}

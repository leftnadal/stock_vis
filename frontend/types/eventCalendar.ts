// 이벤트 캘린더 타입 — EVT-IMPL-4 STEP 3. 단일 계약(BE serializer ⇄ FE 타입) 그대로.
// 계약 원문: scratchpad/EVT4_CONTRACT.md (§ FE TypeScript). 여기서 값을 임의로 넓히거나
// 좁히지 않는다 — BE 응답이 계약과 다르면 이 파일이 아니라 구현(BE) 쪽을 고친다.

export type EventKind =
  | 'holiday'
  | 'macro'
  | 'earnings'
  | 'dividend'
  | 'split'
  | 'split_effective';

export type EventScope = 'monitor' | 'watchlist' | 'both';
export type DateTrust = 'stable' | 'fluid' | 'unconfirmed';
export type EventSession = 'BMO' | 'AMC';
export type SurpriseDir = 'beat' | 'miss' | 'flat';

export interface EventSurprise {
  pct: number;
  direction: SurpriseDir;
}

export interface EventItem {
  kind: EventKind;
  symbol: string | null;
  title: string;
  event_date_et: string; // YYYY-MM-DD
  event_time_et: string | null; // HH:MM
  session: EventSession | null;
  event_dt_kst: string | null; // ISO
  d_day: number;
  badges: string[];
  detail: Record<string, unknown>;
  surprise: EventSurprise | null;
  date_trust: DateTrust | null;
  date_observed_count: number | null;
  sources: Array<'monitor' | 'watchlist'>;
  status: 'scheduled' | 'occurred' | 'stale';
}

export interface EventFeed {
  as_of: string;
  start: string;
  end: string;
  scope: EventScope;
  symbols: { monitor: string[]; watchlist: string[] };
  counts: Partial<Record<EventKind, number>>;
  items: EventItem[];
}

export interface EventStripResponse {
  as_of: string;
  window_days: number;
  items: EventItem[];
}

// ── detail 필드 shape (kind별, 계약 §detail) — 렌더 헬퍼가 소비하는 참고 타입.
// detail 자체는 Record<string, unknown>이라 좁혀 쓰는 소비처에서만 캐스팅한다.
export interface EarningsDetail {
  eps_estimated: number | null;
  eps_actual: number | null;
  revenue_estimated: number | null;
  revenue_actual: number | null;
}

export interface DividendDetail {
  dividend_amount: number | null;
  payment_date: string | null;
  record_date: string | null;
  frequency: string | null;
}

export interface SplitDetail {
  numerator: number;
  denominator: number;
}

export interface MacroDetail {
  importance: string | null;
  forecast_value: string | null;
  previous_value: string | null;
  actual_value: string | null;
  country: string | null;
  event_time_utc: string | null; // 원문 UTC HH:MM (감사용, EVT-4B STEP2 — BE가 ET로 변환해 event_time_et에 채움)
}

export interface HolidayDetail {
  name: string | null;
  next_trading_day: string | null;
}

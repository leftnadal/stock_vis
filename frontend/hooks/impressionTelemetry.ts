/**
 * P2-IMPRESSION-BUILD-S3 — impression/click 텔레메트리 큐 (dashboard FE).
 *
 * 서버 계약(D-P2-S2-PLATFORM, STEP 0 실측):
 *   POST /api/v1/telemetry/impressions
 *   payload = [{surface, object_ref, event_type, session_id}, ...]  (전 필드 필수)
 *   surface 허용값 = dashboard_eod | chain_sight | news_chip  (※ 'reco_card' 아님 — 실측)
 *   event_type = impression | click,  배치 상한 100,  응답 = {received, rejected}
 *   인증 = IsAuthenticated(JWT). sendBeacon은 커스텀 헤더 불가(토큰이 localStorage) →
 *   keepalive fetch + Authorization 헤더로 대체(이탈 유실 방지 = sendBeacon 계약의 동등물).
 *
 * telemetry는 유실 허용 데이터 — 재시도 상한 초과 시 조용히 drop(UX 미차단).
 */
import { tokenUtils } from '@/lib/api/authAxios';

// ── 튜닝 상수 (도그푸딩 대상 — STRIP-FOLD-TUNE 패턴) ──
export const IMPRESSION_VISIBILITY_THRESHOLD = 0.5; // 뷰포트 50% 이상
export const IMPRESSION_DWELL_MS = 1000; // 1초 연속 노출
export const IMPRESSION_FLUSH_INTERVAL_MS = 5000; // 5초 배치 flush
export const IMPRESSION_MAX_RETRIES = 3; // 전송 실패 재시도 상한
export const IMPRESSION_BATCH_LIMIT = 100; // 서버 배치 상한과 정합

// 서버 surface 허용값 (STEP 0-3 실측: reco_card 표면 → 서버값 dashboard_eod 매핑)
export const SURFACE_RECO_CARD = 'dashboard_eod';
export const SURFACE_NEWS_CHIP = 'news_chip';

// ── 전송 엔드포인트 (절대 URL) ──
// authAxios와 동일하게 NEXT_PUBLIC_API_URL(= /api/v1 포함)을 절대 base로 사용.
// (상대 경로 '/api/v1/...'는 Next dev 서버 origin에 붙어 stale rewrite로 흘러가므로 금지 — DIAG-2.)
// authAxios는 미설정 시 로컬 기본 포트 URL로 폴백하지만, telemetry는 유실 허용 데이터이므로
// 죽은 포트로 조용히 보내느니 전송을 skip한다(하드코딩 포트 폴백 금지 — 지시서 명시).
export const TELEMETRY_PATH = '/telemetry/impressions';

let warnedMissingApiBase = false;

/** 절대 telemetry URL을 반환. NEXT_PUBLIC_API_URL 미설정 시 null(전송 skip) + 최초 1회 경고. */
export function resolveTelemetryEndpoint(): string | null {
  const base = process.env.NEXT_PUBLIC_API_URL;
  if (!base) {
    if (!warnedMissingApiBase) {
      warnedMissingApiBase = true;
      // eslint-disable-next-line no-console
      console.warn('[impression] NEXT_PUBLIC_API_URL 미설정 — telemetry 전송 skip(유실 허용)');
    }
    return null;
  }
  return `${base.replace(/\/+$/, '')}${TELEMETRY_PATH}`;
}

export type ImpressionEventType = 'impression' | 'click';

export interface ImpressionEvent {
  surface: string;
  object_ref: string;
  event_type: ImpressionEventType;
  session_id: string;
}

/** object_ref 포맷 단일 출처 — 서버 upsert 3중 키의 한 축이므로 drift = 중복 행. */
export function recoObjectRef(ticker: string, tradingDate: string, signalTag: string): string {
  return `${ticker}:${tradingDate}:${signalTag}`;
}
export function newsChipObjectRef(articleUrl: string): string {
  return articleUrl;
}

// ── 세션 식별자 (기존 부재 — 신규 생성. page-session 단위 UUID) ──
const SESSION_KEY = 'sv_telemetry_session_id';
export function getSessionId(): string {
  if (typeof window === 'undefined') return 'ssr';
  let sid = window.sessionStorage.getItem(SESSION_KEY);
  if (!sid) {
    sid =
      window.crypto?.randomUUID?.() ??
      `s-${Date.now().toString(36)}-${Math.floor(Math.random() * 1e9).toString(36)}`;
    window.sessionStorage.setItem(SESSION_KEY, sid);
  }
  return sid;
}

export type SendFn = (events: ImpressionEvent[]) => Promise<boolean>;

export async function defaultSend(events: ImpressionEvent[]): Promise<boolean> {
  const endpoint = resolveTelemetryEndpoint();
  if (endpoint === null) return true; // env 미설정 → 전송 skip(재시도 큐에 남기지 않음, 유실 허용)
  try {
    const token = tokenUtils.getAccess();
    const res = await fetch(endpoint, {
      method: 'POST',
      keepalive: true, // 페이지 이탈 중에도 전송 보장(sendBeacon 동등물)
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(events),
    });
    return res.ok;
  } catch {
    return false;
  }
}

export class ImpressionQueue {
  private queue: ImpressionEvent[] = [];
  private enqueuedImpressions = new Set<string>(); // dedup (surface|object_ref) 페이지 수명 내 1회
  private failCount = 0;
  private timer: ReturnType<typeof setInterval> | null = null;
  private started = false;
  private send: SendFn;
  private onHide = () => {
    void this.flush();
  };

  constructor(send: SendFn = defaultSend) {
    this.send = send;
  }

  private ensureStarted() {
    if (this.started || typeof window === 'undefined') return;
    this.started = true;
    this.timer = setInterval(() => void this.flush(), IMPRESSION_FLUSH_INTERVAL_MS);
    window.addEventListener('pagehide', this.onHide);
    window.addEventListener('visibilitychange', this.onVisibility);
  }

  private onVisibility = () => {
    if (typeof document !== 'undefined' && document.visibilityState === 'hidden') {
      void this.flush();
    }
  };

  /** impression 적재 — 동일 (surface, object_ref)는 페이지 수명 내 1회만(프론트 1차 dedup). */
  enqueueImpression(surface: string, objectRef: string) {
    const key = `${surface}|${objectRef}`;
    if (this.enqueuedImpressions.has(key)) return;
    this.enqueuedImpressions.add(key);
    this.queue.push({ surface, object_ref: objectRef, event_type: 'impression', session_id: getSessionId() });
    this.ensureStarted();
  }

  /** click 적재 — dedup 없음(같은 배치 파이프에 태움). */
  enqueueClick(surface: string, objectRef: string) {
    this.queue.push({ surface, object_ref: objectRef, event_type: 'click', session_id: getSessionId() });
    this.ensureStarted();
  }

  /** 한 번 flush: 상한 100까지 전송, 나머지 이월. 실패 시 큐 복원 후 재시도(상한 초과 drop). */
  async flush(): Promise<void> {
    if (this.queue.length === 0) return;
    const batch = this.queue.splice(0, IMPRESSION_BATCH_LIMIT);
    const ok = await this.send(batch);
    if (ok) {
      this.failCount = 0;
      return;
    }
    this.failCount += 1;
    if (this.failCount <= IMPRESSION_MAX_RETRIES) {
      this.queue.unshift(...batch); // 큐 앞으로 복원 → 다음 주기 재시도
    } else {
      // eslint-disable-next-line no-console
      console.warn(`[impression] 전송 재시도 상한(${IMPRESSION_MAX_RETRIES}) 초과 — ${batch.length}건 drop`);
      this.failCount = 0;
    }
  }

  /** 테스트/정리용 — 인터벌·리스너 해제. */
  destroy() {
    if (this.timer != null) clearInterval(this.timer);
    this.timer = null;
    this.started = false;
    if (typeof window !== 'undefined') {
      window.removeEventListener('pagehide', this.onHide);
      window.removeEventListener('visibilitychange', this.onVisibility);
    }
  }

  /** 테스트 관찰용. */
  get pending(): number {
    return this.queue.length;
  }
}

/** 앱 전역 싱글턴 — 모든 표면이 공유(단일 큐·단일 flush 타이머·단일 dedup). */
export const impressionQueue = new ImpressionQueue();

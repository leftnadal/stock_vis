'use client';

/**
 * GuideOverlay — 화면별 `?` 오버레이 (D-GUIDE-TRACK).
 *
 * 附加 전용: 가이드 OFF 상태에서 기존 화면의 DOM·동작은 완전히 동일하다.
 * 위치 지정은 CSS 셀렉터가 아니라 대상 요소의 `data-guide="<anchor>"` 속성만 참조한다.
 * 앵커가 없는(조건부 미렌더) region은 배지를 생략하되 패널 목록에는 남긴다.
 */

import { useCallback, useEffect, useState, useSyncExternalStore } from 'react';

import { usePathname } from 'next/navigation';
import { HelpCircle, X } from 'lucide-react';

import { FLOW_STAGE_LABELS, getGuideForRoute, type GuideScreen } from '@/lib/guide';

/** 화면 id별 "다시 안 보기" 키. 힌트 라벨만 끈다 — `?` 버튼 자체는 남는다(언제든 재열람). */
export const guideDismissKey = (id: string) => `guide:dismissed:${id}`;

function readDismissed(id: string): boolean {
  try {
    return window.localStorage.getItem(guideDismissKey(id)) === '1';
  } catch {
    return false;
  }
}

/**
 * "다시 안 보기" 상태는 localStorage(외부 저장소)에 있다 → useSyncExternalStore로 구독한다.
 * 같은 탭의 쓰기는 storage 이벤트가 발화하지 않으므로 모듈 수준 리스너로 직접 통지한다.
 */
const dismissListeners = new Set<() => void>();

function subscribeDismiss(onChange: () => void): () => void {
  dismissListeners.add(onChange);
  window.addEventListener('storage', onChange);
  return () => {
    dismissListeners.delete(onChange);
    window.removeEventListener('storage', onChange);
  };
}

function notifyDismissChanged() {
  for (const l of dismissListeners) l();
}

interface BadgePos {
  anchor: string;
  index: number;
  top: number;
  left: number;
}

function measure(screen: GuideScreen): BadgePos[] {
  const out: BadgePos[] = [];
  screen.regions.forEach((region, i) => {
    const el = document.querySelector(`[data-guide="${region.anchor}"]`);
    if (!el) return;
    const rect = el.getBoundingClientRect();
    out.push({ anchor: region.anchor, index: i + 1, top: rect.top, left: rect.left });
  });
  return out;
}

export default function GuideOverlay() {
  const pathname = usePathname();
  const screen = getGuideForRoute(pathname ?? '');

  const [open, setOpen] = useState(false);
  const [badges, setBadges] = useState<BadgePos[]>([]);

  const screenId = screen?.id;

  // 서버 스냅샷 = true(힌트 숨김) → 하이드레이션 불일치 없음.
  const dismissed = useSyncExternalStore(
    subscribeDismiss,
    () => (screenId ? readDismissed(screenId) : true),
    () => true
  );

  const remeasure = useCallback(() => {
    if (!screen) return;
    setBadges(measure(screen));
  }, [screen]);

  // 라우트가 바뀌면 패널을 닫는다(이벤트성 — 렌더 중 setState 아님).
  const [lastScreenId, setLastScreenId] = useState(screenId);
  if (lastScreenId !== screenId) {
    setLastScreenId(screenId);
    if (open) setOpen(false);
  }

  // 배지 위치는 레이아웃(외부 시스템)에서 읽는다 → rAF·이벤트 콜백에서만 setState.
  useEffect(() => {
    if (!open || !screen) return;
    const raf = window.requestAnimationFrame(remeasure);
    window.addEventListener('scroll', remeasure, true);
    window.addEventListener('resize', remeasure);
    return () => {
      window.cancelAnimationFrame(raf);
      window.removeEventListener('scroll', remeasure, true);
      window.removeEventListener('resize', remeasure);
    };
  }, [open, screen, remeasure]);

  // 가이드 데이터가 없는 화면에서는 `?` 버튼 자체를 노출하지 않는다.
  if (!screen) return null;

  const handleDismiss = () => {
    try {
      window.localStorage.setItem(guideDismissKey(screen.id), '1');
    } catch {
      /* 저장 실패는 무시 — 힌트는 이번 세션만 숨긴다 */
    }
    notifyDismissChanged();
    setOpen(false);
  };

  return (
    <>
      {/* 트리거 — 항상 재열람 가능 */}
      <div className="fixed right-4 top-20 z-40 flex items-center gap-2">
        {!dismissed && !open && (
          <span
            data-testid="guide-hint"
            className="rounded-full bg-blue-600 px-2 py-1 text-xs font-medium text-white shadow"
          >
            가이드
          </span>
        )}
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-label="화면 가이드 열기"
          aria-expanded={open}
          data-testid="guide-toggle"
          className="flex h-10 w-10 items-center justify-center rounded-full border border-gray-200 bg-white text-gray-600 shadow-md transition hover:text-blue-600 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300"
        >
          <HelpCircle size={20} />
        </button>
      </div>

      {open && (
        <>
          {/* 영역 번호 배지 — 앵커가 실제로 렌더된 region만 */}
          {badges.map((b) => (
            <span
              key={b.anchor}
              data-testid={`guide-badge-${b.anchor}`}
              style={{ top: b.top, left: b.left }}
              className="pointer-events-none fixed z-40 flex h-6 w-6 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full bg-blue-600 text-xs font-bold text-white shadow-lg"
            >
              {b.index}
            </span>
          ))}

          {/* 패널 — 데스크톱 우측 사이드, 모바일 하단 시트 */}
          <aside
            data-testid="guide-panel"
            role="dialog"
            aria-label={`${screen.title} 가이드`}
            className="fixed inset-x-0 bottom-0 z-50 max-h-[70vh] overflow-y-auto rounded-t-2xl border border-gray-200 bg-white p-5 shadow-2xl dark:border-gray-700 dark:bg-gray-900 md:inset-x-auto md:bottom-auto md:right-4 md:top-32 md:max-h-[70vh] md:w-96 md:rounded-2xl"
          >
            <div className="mb-3 flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-medium text-blue-600 dark:text-blue-400">
                  {screen.flowStage}. {FLOW_STAGE_LABELS[screen.flowStage]}
                </p>
                <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100">
                  {screen.title}
                </h2>
              </div>
              <button
                type="button"
                onClick={() => setOpen(false)}
                aria-label="가이드 닫기"
                data-testid="guide-close"
                className="rounded-lg p-1 text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
              >
                <X size={18} />
              </button>
            </div>

            {/* 1. 이 화면이 답하는 질문 */}
            <p
              data-testid="guide-core-question"
              className="mb-4 rounded-lg bg-blue-50 p-3 text-sm font-medium text-blue-900 dark:bg-blue-900/30 dark:text-blue-100"
            >
              {screen.coreQuestion}
            </p>

            {/* 2. 알게 되는 것 */}
            <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-500">
              여기서 알게 되는 것
            </h3>
            <ul className="mb-4 list-disc space-y-1 pl-5 text-sm text-gray-700 dark:text-gray-300">
              {screen.learnings.map((l) => (
                <li key={l}>{l}</li>
              ))}
            </ul>

            {/* 3. 영역 설명 */}
            <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-500">
              화면 영역
            </h3>
            <ol className="mb-4 space-y-3">
              {screen.regions.map((r, i) => (
                <li key={r.anchor} className="flex gap-2 text-sm">
                  <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-blue-600 text-[11px] font-bold text-white">
                    {i + 1}
                  </span>
                  <span>
                    <span className="font-medium text-gray-900 dark:text-gray-100">{r.title}</span>
                    <span className="block text-gray-600 dark:text-gray-400">{r.desc}</span>
                  </span>
                </li>
              ))}
            </ol>

            {/* 4. 다음 행동 */}
            {screen.nextAction && (
              <a
                href={screen.nextAction.route}
                data-testid="guide-next-action"
                className="mb-3 block rounded-lg bg-blue-600 px-3 py-2 text-center text-sm font-medium text-white hover:bg-blue-700"
              >
                {screen.nextAction.label} →
              </a>
            )}

            <div className="flex items-center justify-between text-xs">
              <a href="/guide" className="text-blue-600 hover:underline dark:text-blue-400">
                전체 가이드 보기
              </a>
              <button
                type="button"
                onClick={handleDismiss}
                data-testid="guide-dismiss"
                className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
              >
                다시 안 보기
              </button>
            </div>
          </aside>
        </>
      )}
    </>
  );
}

/**
 * P2-IMPRESSION-BUILD-S3 — 표면 요소 impression/click 추적 훅 (dashboard FE).
 *
 * IntersectionObserver로 뷰포트 50% 이상 · 1초 연속 노출 시 impression 1건 적재.
 * 반환 ref를 표면 요소에, onClick을 클릭 대상(링크 등)에 부착한다.
 * 중복 억제 = 프론트 1차(페이지 수명 내 1회, 싱글턴 dedup) + 서버 upsert 2차의 이중 방어.
 * 재진입(스크롤 왕복)해도 재적재 없음 — seen_count는 페이지 재방문 단위로만 증가하는 시맨틱.
 */
import { useCallback, useEffect, useRef } from 'react';

import {
  impressionQueue,
  IMPRESSION_DWELL_MS,
  IMPRESSION_VISIBILITY_THRESHOLD,
} from './impressionTelemetry';

export function useImpressionTracker<T extends HTMLElement = HTMLElement>(
  surface: string,
  objectRef: string,
) {
  const ref = useRef<T | null>(null);
  const dwellTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el || typeof IntersectionObserver === 'undefined') return;

    const clearDwell = () => {
      if (dwellTimer.current != null) {
        clearTimeout(dwellTimer.current);
        dwellTimer.current = null;
      }
    };

    const observer = new IntersectionObserver(
      (entries) => {
        const entry = entries[0];
        if (!entry) return;
        const visible =
          entry.isIntersecting && entry.intersectionRatio >= IMPRESSION_VISIBILITY_THRESHOLD;
        if (visible) {
          // 이미 dwell 진행 중이면 재설정하지 않음(연속 노출 타이밍 유지)
          if (dwellTimer.current == null) {
            dwellTimer.current = setTimeout(() => {
              impressionQueue.enqueueImpression(surface, objectRef);
              dwellTimer.current = null;
            }, IMPRESSION_DWELL_MS);
          }
        } else {
          // 1초 연속 미충족(벗어남) → dwell 취소
          clearDwell();
        }
      },
      { threshold: [IMPRESSION_VISIBILITY_THRESHOLD] },
    );

    observer.observe(el);
    return () => {
      observer.disconnect();
      clearDwell();
    };
  }, [surface, objectRef]);

  const onClick = useCallback(() => {
    impressionQueue.enqueueClick(surface, objectRef);
  }, [surface, objectRef]);

  return { ref, onClick };
}

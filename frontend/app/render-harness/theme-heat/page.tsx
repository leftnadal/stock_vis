'use client';

/**
 * 테마 온도계 시각 회귀 하네스 (트랙1 / B) — 배포·인증·백엔드 불요.
 * 실 ThemeHeatBar/ThemeHeatCard 를 실 Tailwind/globals.css 맥락에서 렌더.
 * 데이터는 QueryClient 캐시에 mock fixture 를 seed → 컴포넌트 자체 fetch 가 캐시 히트(네트워크 0).
 * 시나리오: ?s=bar | card12 | card13  (기본 bar)
 * 남겨두면 카드 변경마다 재사용하는 시각 회귀 도구.
 */

import { Suspense, useMemo } from 'react';
import { useSearchParams } from 'next/navigation';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ThemeHeatBar from '@/components/chainsight/ThemeHeatBar';
import ThemeHeatCard from '@/components/chainsight/ThemeHeatCard';

// ── mock fixtures (목업 값 — 실값 아님) ──

const barItems = [
  { theme: 'Energy', status: 'computed', score: 58, band: 'warning', band_display: '가열', delta_1d: 1, days: 43, days_required: 26, eta_days: null, universe_stale: false },
  { theme: 'Consumer Cyclical', status: 'computed', score: 57, band: 'warning', band_display: '가열', delta_1d: -2, days: 43, days_required: 26, eta_days: null, universe_stale: false },
  { theme: 'Industrials', status: 'computed', score: 56, band: 'warning', band_display: '가열', delta_1d: 0, days: 43, days_required: 26, eta_days: null, universe_stale: false },
  { theme: 'Technology', status: 'computed', score: 56, band: 'warning', band_display: '가열', delta_1d: 3, days: 43, days_required: 26, eta_days: null, universe_stale: false },
  { theme: 'Financial Services', status: 'computed', score: 55, band: 'warning', band_display: '가열', delta_1d: -12, days: 44, days_required: 26, eta_days: null, universe_stale: false },
  { theme: 'Healthcare', status: 'accumulating', score: null, band: null, band_display: null, delta_1d: null, days: 25, days_required: 26, eta_days: 1, universe_stale: false },
];

const components = [
  { id: 'C1', label_surface: '몸값 부담', label_technical: '밸류에이션', z: 0.14, w: 0.18, s: 0.53, z_mode: 'time_series', status: 'computed' },
  { id: 'C3', label_surface: '이야기 밀도', label_technical: '뉴스 볼륨', z: 0.90, w: 0.16, s: 0.71, z_mode: 'time_series', status: 'computed' },
  { id: 'C7', label_surface: '수급 쏠림', label_technical: '가격 모멘텀', z: 0.41, w: 0.14, s: 0.60, z_mode: 'time_series', status: 'computed' },
  { id: 'C8', label_surface: '실적 안 따라옴', label_technical: '추정치 괴리', z: null, w: 0.08, s: null, z_mode: null, status: 'coldstart' },
];

const confidence = { present: 6, total: 8, missing: ['C4', 'C8'], renorm_divisor: 0.8 };
const quadrant = { heat: 55, dss: null, dss_status: 'coldstart', dss_eta: 'Cycle 2 (DSS 미가동)' };

// 07-12: 개정일(방법론 개선일) — driver.held=true, 중립 마커 노출
const card0712 = {
  theme: 'Financial Services', as_of: '2026-07-12', status: 'computed', score: 55,
  band: 'warning', band_display: '가열', delta_1d: -12, z_mode: 'time_series',
  driver: { held: true, reason: 'methodology_revision', marker: '2026-07-12', note: '계산 방식 개선일 — 하루 변화 해석은 다음 정상일부터.' },
  confidence, components, quadrant,
  history: { values: [67, 55], capacity: 60, filled: 2 },
};

// 07-13: 정상일 — 견인 정상 재개(▼냉각 이야기 밀도 86%), 개정일 마커 부재
const card0713 = {
  theme: 'Financial Services', as_of: '2026-07-13', status: 'computed', score: 55,
  band: 'warning', band_display: '가열', delta_1d: -3, z_mode: 'time_series',
  driver: { held: false, component: 'C3', label_surface: '이야기 밀도', label_technical: '뉴스 볼륨', z: 0.90, contribution_pct: 86, basis: 'delta', direction: 'down' },
  confidence, components, quadrant,
  history: { values: [55, 55], capacity: 60, filled: 3 },
};

function Harness() {
  const params = useSearchParams();
  const s = params.get('s') ?? 'bar';

  const qc = useMemo(() => {
    const c = new QueryClient({
      defaultOptions: { queries: { staleTime: Infinity, gcTime: Infinity, retry: false, refetchOnMount: false, refetchOnWindowFocus: false } },
    });
    if (s === 'bar') c.setQueryData(['theme-heat-bar'], barItems);
    if (s === 'card12') c.setQueryData(['theme-heat-card', 'Financial Services'], card0712);
    if (s === 'card13') c.setQueryData(['theme-heat-card', 'Financial Services'], card0713);
    return c;
  }, [s]);

  return (
    <QueryClientProvider client={qc}>
      <div className="min-h-screen bg-white dark:bg-gray-900">
        <div className="mx-auto max-w-3xl px-4 py-6 flex flex-col gap-4">
          <div className="text-[10px] uppercase tracking-wide text-gray-400 border-b border-gray-100 dark:border-gray-800 pb-2">
            RENDER HARNESS · scenario={s} · MOCK DATA (실값 아님)
          </div>
          {s === 'bar' && <ThemeHeatBar selected={undefined} onSelect={() => {}} />}
          {(s === 'card12' || s === 'card13') && (
            <div className="max-w-md">
              <ThemeHeatCard theme="Financial Services" rank={5} total={5} />
            </div>
          )}
        </div>
      </div>
    </QueryClientProvider>
  );
}

export default function Page() {
  return (
    <Suspense fallback={null}>
      <Harness />
    </Suspense>
  );
}

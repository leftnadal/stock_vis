'use client';

// DSS-QUADRANT 섹터 사분면 렌더러 (QUAD-IMPL-1 Slice 2)
// 공용 컴포넌트 — props 주입만(특정 페이지 무지). 구역 판정·중앙값 = 순수 함수(export, 단위 테스트).
// D-DSS-QUAD-ENCODE: 경계 x = heat 비null 중앙값, y = breadth 0. ② teal · ④ 경보색.
// D-DSS-QUAD-TEMPORAL: 점 + 전주 화살표(anchor flat_ratio ≥ 90% → 숨김 + 각주).
import type { QuadrantResponse, QuadrantSector } from '@/types/quadrant';

export type QuadrantZone = 'II' | 'IV' | 'other';

/** heat 비null 값의 중앙값(백엔드 STEP 0 규약 = 정렬 후 len//2 상단중앙). null = 산출 섹터 0. */
export function heatMedian(sectors: QuadrantSector[]): number | null {
  const heats = sectors
    .map((s) => s.heat)
    .filter((h): h is number => h !== null && h !== undefined)
    .sort((a, b) => a - b);
  if (heats.length === 0) return null;
  return heats[Math.floor(heats.length / 2)];
}

/** 구역 배정: ②=저Heat+수요개선(teal), ④=고Heat+수요악화(경보). 경계/무자료=other. */
export function assignZone(
  sector: QuadrantSector,
  median: number | null,
): QuadrantZone {
  const { heat, breadth_curr } = sector;
  if (heat === null || breadth_curr === null || median === null) return 'other';
  if (heat < median && breadth_curr > 0) return 'II';
  if (heat > median && breadth_curr < 0) return 'IV';
  return 'other';
}

/** 차트 배치 대상 = heat·breadth_curr 모두 존재. 나머지(heat null)는 하단 목록. */
export function chartedSectors(sectors: QuadrantSector[]): QuadrantSector[] {
  return sectors.filter((s) => s.heat !== null && s.breadth_curr !== null);
}
export function unchartedSectors(sectors: QuadrantSector[]): QuadrantSector[] {
  return sectors.filter((s) => s.heat === null);
}

const ZONE_FILL: Record<QuadrantZone, string> = {
  II: 'rgba(20, 184, 166, 0.10)', // teal
  IV: 'rgba(244, 63, 94, 0.10)', // rose(경보)
  other: 'transparent',
};
const ZONE_DOT: Record<QuadrantZone, string> = {
  II: '#0d9488',
  IV: '#e11d48',
  other: '#64748b',
};

const PAD = { l: 44, r: 16, t: 20, b: 34 };
const W = 340;
const H = 240;

export function SectorQuadrant({ data }: { data: QuadrantResponse }) {
  const charted = chartedSectors(data.sectors);
  const uncharted = unchartedSectors(data.sectors);
  const median = heatMedian(data.sectors);

  const innerW = W - PAD.l - PAD.r;
  const innerH = H - PAD.t - PAD.b;

  const heats = charted.map((s) => s.heat as number);
  const xMin = heats.length ? Math.min(...heats) - 4 : 0;
  const xMax = heats.length ? Math.max(...heats) + 4 : 100;
  const xSpan = xMax - xMin || 1;
  const breadths = charted.flatMap((s) =>
    [s.breadth_curr, s.breadth_prev].filter((b): b is number => b !== null),
  );
  const absMax = Math.max(0.05, ...breadths.map((b) => Math.abs(b)));
  const yMax = absMax * 1.2;

  const xPix = (heat: number) => PAD.l + ((heat - xMin) / xSpan) * innerW;
  const yPix = (b: number) => PAD.t + ((yMax - b) / (2 * yMax)) * innerH;

  const medianX = median !== null ? xPix(median) : null;
  const zeroY = yPix(0);

  return (
    <section
      className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900"
      aria-label="섹터 사분면"
      data-testid="sector-quadrant"
    >
      <header className="mb-2 flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100">
            섹터 사분면 · Heat × 수요 방향
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            가로 = 시장 관심(Heat){data.heat_date ? ` · ${data.heat_date}` : ''} · 세로 = 수요 breadth
            {data.anchor_curr ? ` · ${data.anchor_curr}` : ''}
          </p>
        </div>
        {/* 가이드 ? 버튼 자리 예약(비활성 슬롯 — 가이드 렌더러 트랙 착지 시 활성화) */}
        <button
          type="button"
          disabled
          aria-label="가이드(준비 중)"
          className="ml-2 h-6 w-6 shrink-0 cursor-not-allowed rounded-full border border-slate-200 text-xs text-slate-300 dark:border-slate-700"
        >
          ?
        </button>
      </header>

      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="사분면 산점도">
        {/* ②·④ 구역 하이라이트 */}
        {medianX !== null && (
          <>
            <rect
              x={PAD.l}
              y={PAD.t}
              width={medianX - PAD.l}
              height={zeroY - PAD.t}
              fill={ZONE_FILL.II}
            />
            <rect
              x={medianX}
              y={zeroY}
              width={PAD.l + innerW - medianX}
              height={PAD.t + innerH - zeroY}
              fill={ZONE_FILL.IV}
            />
          </>
        )}
        {/* 경계선: x=median, y=0 */}
        {medianX !== null && (
          <line x1={medianX} y1={PAD.t} x2={medianX} y2={PAD.t + innerH} stroke="#cbd5e1" strokeDasharray="3 3" />
        )}
        <line x1={PAD.l} y1={zeroY} x2={PAD.l + innerW} y2={zeroY} stroke="#cbd5e1" strokeDasharray="3 3" />
        {/* 축 테두리 */}
        <rect x={PAD.l} y={PAD.t} width={innerW} height={innerH} fill="none" stroke="#e2e8f0" />

        {/* 화살표 마커 정의 */}
        <defs>
          <marker id="quad-arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
            <path d="M0,0 L6,3 L0,6 Z" fill="#94a3b8" />
          </marker>
        </defs>

        {charted.map((s) => {
          const zone = assignZone(s, median);
          const cx = xPix(s.heat as number);
          const cy = yPix(s.breadth_curr as number);
          const showArrow = !data.arrow_suppressed && s.breadth_prev !== null;
          return (
            <g key={s.sector}>
              {showArrow && (
                <line
                  x1={cx}
                  y1={yPix(s.breadth_prev as number)}
                  x2={cx}
                  y2={cy}
                  stroke="#94a3b8"
                  markerEnd="url(#quad-arrow)"
                />
              )}
              <circle cx={cx} cy={cy} r={5} fill={ZONE_DOT[zone]} />
              <text x={cx + 7} y={cy + 3} className="fill-slate-600 text-[9px] dark:fill-slate-300">
                {s.sector}
              </text>
            </g>
          );
        })}
      </svg>

      {/* 화살표 숨김 각주 */}
      {data.arrow_suppressed && (
        <p className="mt-1 text-[11px] text-slate-400" data-testid="arrow-suppressed-note">
          ※ 전주({data.anchor_prev}) 컨센서스 변화가 미미(flat ≥ 90%)해 이동 화살표를 숨겼습니다.
        </p>
      )}

      {/* 미산출 섹터 하단 목록 */}
      {uncharted.length > 0 && (
        <p className="mt-2 text-[11px] text-slate-400" data-testid="uncharted-list">
          Heat 미산출: {uncharted.map((s) => s.sector).join(', ')}
        </p>
      )}
    </section>
  );
}

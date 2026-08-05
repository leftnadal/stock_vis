'use client';

/**
 * SFI-I-2 — 애널리스트 컨센서스 패널 (C안: 컨텍스트 + 의견 추세).
 *
 * 목표주가 + 업사이드%(현재가 재사용) + high/low 범위 바 + 의견 분포 바 +
 * 월별 추세 미니차트(grades_historical → 매수계열 비중, recharts 재사용).
 * 미수집/null = "미설정" 폴백(유령 노출 금지).
 */
import { useEffect, useState } from 'react';
import { Line, LineChart, ResponsiveContainer, Tooltip, YAxis } from 'recharts';

import {
  AnalystSignalData,
  GradesHistoryPoint,
  stockService,
} from '@/services/stock';

// ---- 순수 헬퍼 (테스트 대상) ----

/** 업사이드% = (컨센서스 목표가 − 현재가) / 현재가 × 100. 입력 부재 시 null. */
export function computeUpsidePct(
  consensus: string | null | undefined,
  currentPrice: number | null | undefined,
): number | null {
  if (consensus == null || currentPrice == null || currentPrice <= 0) return null;
  const target = parseFloat(consensus);
  if (!isFinite(target)) return null;
  return ((target - currentPrice) / currentPrice) * 100;
}

/** grades_historical(최신순) → 매수계열 비중 시계열(오래된→최신, 차트 좌→우). */
export interface TrendPoint {
  date: string;
  buyRatio: number;
}
export function toTrendSeries(history: GradesHistoryPoint[] | undefined): TrendPoint[] {
  if (!history || history.length === 0) return [];
  return [...history]
    .reverse()
    .map((h) => {
      const sb = h.analystRatingsStrongBuy ?? 0;
      const b = h.analystRatingsBuy ?? 0;
      const ho = h.analystRatingsHold ?? 0;
      const s = h.analystRatingsSell ?? 0;
      const ss = h.analystRatingsStrongSell ?? 0;
      const total = sb + b + ho + s + ss;
      return {
        date: h.date,
        buyRatio: total > 0 ? Math.round(((sb + b) / total) * 100) : 0,
      };
    });
}

const DIST_SEGMENTS: { key: keyof NonNullable<AnalystSignalData['grades']>; label: string; color: string }[] = [
  { key: 'strong_buy', label: '적극매수', color: 'bg-emerald-600' },
  { key: 'buy', label: '매수', color: 'bg-emerald-400' },
  { key: 'hold', label: '보유', color: 'bg-gray-400' },
  { key: 'sell', label: '매도', color: 'bg-rose-400' },
  { key: 'strong_sell', label: '적극매도', color: 'bg-rose-600' },
];

// ---- Presentational View (prop 주입, 테스트 용이) ----

export function AnalystConsensusPanelView({
  data,
  currentPrice,
}: {
  data: AnalystSignalData;
  currentPrice: number | null;
}) {
  if (!data.available) {
    return (
      <div data-testid="analyst-panel-empty" className="text-sm text-gray-400 dark:text-gray-500">
        애널리스트 시그널 미설정
      </div>
    );
  }

  const target = data.target;
  const grades = data.grades;
  const upside = computeUpsidePct(target?.consensus, currentPrice);
  const trend = toTrendSeries(data.grades_historical);
  const distTotal = grades
    ? DIST_SEGMENTS.reduce((acc, seg) => acc + (grades[seg.key] as number | null ?? 0), 0)
    : 0;

  return (
    <div data-testid="analyst-panel" className="space-y-4">
      <div className="flex items-baseline gap-3">
        <span className="text-sm text-gray-500 dark:text-gray-400">컨센서스 목표주가</span>
        <span className="text-xl font-semibold text-gray-900 dark:text-white">
          {target?.consensus ? `$${parseFloat(target.consensus).toFixed(2)}` : '-'}
        </span>
        {upside != null && (
          <span
            data-testid="analyst-upside"
            className={`text-sm font-medium ${upside >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}
          >
            {upside >= 0 ? '▲' : '▼'} {Math.abs(upside).toFixed(1)}%
          </span>
        )}
      </div>

      {/* high/low 범위 바 */}
      {target?.low && target?.high && (
        <div>
          <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mb-1">
            <span>저 ${parseFloat(target.low).toFixed(0)}</span>
            <span>고 ${parseFloat(target.high).toFixed(0)}</span>
          </div>
          <div className="h-1.5 rounded-full bg-gradient-to-r from-rose-300 via-gray-300 to-emerald-300" />
        </div>
      )}

      {/* 의견 분포 바 */}
      {grades && distTotal > 0 && (
        <div>
          <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mb-1">
            <span>의견 분포 ({grades.consensus || '-'})</span>
            <span>애널리스트 {distTotal}명</span>
          </div>
          <div data-testid="analyst-distribution" className="flex h-3 overflow-hidden rounded-full">
            {DIST_SEGMENTS.map((seg) => {
              const n = (grades[seg.key] as number | null) ?? 0;
              const pct = (n / distTotal) * 100;
              return pct > 0 ? (
                <div
                  key={seg.key}
                  className={seg.color}
                  style={{ width: `${pct}%` }}
                  title={`${seg.label} ${n}`}
                />
              ) : null;
            })}
          </div>
        </div>
      )}

      {/* 월별 추세 미니차트 (매수계열 비중) */}
      {trend.length > 1 && (
        <div>
          <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">의견 추세 (매수계열 비중 %)</div>
          <div data-testid="analyst-trend" className="h-16">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trend}>
                <YAxis hide domain={[0, 100]} />
                <Tooltip formatter={(v) => `${v}%`} labelFormatter={(l) => String(l)} />
                <Line type="monotone" dataKey="buyRatio" stroke="#059669" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      <div className="text-[11px] text-gray-400 dark:text-gray-500">
        출처 {data.source ?? 'fmp'}
        {data.captured_at ? ` · ${new Date(data.captured_at).toISOString().slice(0, 10)} 기준` : ''}
        {data.rating ? ` · 종합등급 ${data.rating}` : ''}
      </div>
    </div>
  );
}

// ---- Container (심볼로 fetch) ----

export default function AnalystConsensusPanel({
  symbol,
  currentPrice,
}: {
  symbol: string;
  currentPrice: number | null;
}) {
  const [data, setData] = useState<AnalystSignalData | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let alive = true;
    stockService
      .getAnalystSignals(symbol)
      .then((d) => alive && setData(d))
      .catch(() => alive && setFailed(true));
    return () => {
      alive = false;
    };
  }, [symbol]);

  if (failed) {
    // 에러도 미설정 폴백(유령 노출 금지 연속) — 조용히 미표기.
    return null;
  }
  if (!data) return null; // 로딩 중 미표기(플레이스홀더 없이 조용)

  return (
    <div>
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">애널리스트 컨센서스</h3>
      <AnalystConsensusPanelView data={data} currentPrice={currentPrice} />
    </div>
  );
}

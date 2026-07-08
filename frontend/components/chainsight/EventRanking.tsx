'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { ArrowLeft, ChevronDown, ChevronUp } from 'lucide-react';
import Link from 'next/link';
import { fetchEventStocks } from '@/services/chainsightService';
import { getLabelForTheme, METRIC_INFO } from '@/constants/eventThemes';
import type { EventRankingItem } from '@/types/chainsight';
import LowLiquidityPanel from '@/components/chainsight/LowLiquidityPanel';
import MetricInfoPopover from '@/components/chainsight/MetricInfoPopover';
import MetricCell from '@/components/chainsight/MetricCell';
import AttentionStandingBar from '@/components/chainsight/AttentionStandingBar';
import { CHANGE_TEXT } from './colorSemantics';

interface Props {
  theme: string;
}

function LowLiquidityBadge() {
  return (
    <span className="inline-flex items-center rounded-full bg-amber-100 dark:bg-amber-900 text-amber-800 dark:text-amber-200 text-xs font-medium px-2 py-0.5">
      저유동성
    </span>
  );
}

const PRIMARY_METRICS = [
  'trend_quality',
  'theme_beta',
  'capture_spread',
] as const;

function RankingHeader() {
  // 행 구조(Link[flex-1] + chevron 버튼)와 동일하게 미러링 — 헤더 라벨이
  // 행의 값 컬럼과 정렬되도록 chevron 폭 placeholder 포함(정렬만, 기능 무변경).
  return (
    <div
      className="flex items-center bg-gray-50 dark:bg-gray-800/60 border-b border-gray-200 dark:border-gray-700"
      aria-label="지표 컬럼 헤더"
    >
      <div className="flex-1 flex items-center gap-4 px-4 py-2">
        {/* rank placeholder */}
        <span className="w-6 shrink-0" />
        {/* symbol/name placeholder */}
        <div className="flex-1 min-w-0" />
        {/* return/score placeholder */}
        <div className="w-20 shrink-0" />
        {/* 3 primary metric columns */}
        <div className="flex gap-3">
          {PRIMARY_METRICS.map((key) => (
            <div
              key={key}
              className="w-20 flex items-center justify-end gap-1 text-xs font-medium text-gray-500 dark:text-gray-400"
            >
              <span>{METRIC_INFO[key].label}</span>
              <MetricInfoPopover metricKey={key} />
            </div>
          ))}
        </div>
      </div>
      {/* chevron 버튼 폭 placeholder (행: shrink-0 p-1 + size16) */}
      <span className="shrink-0 p-1" aria-hidden="true">
        <span className="block w-4 h-4" />
      </span>
    </div>
  );
}

function RankingRow({
  item,
  rank,
}: {
  item: EventRankingItem;
  rank: number;
}) {
  const isPositive = item.raw_return >= 0;
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border-b border-gray-100 dark:border-gray-700">
      <div className="flex items-center">
        <Link
          href={`/chainsight/${item.symbol}`}
          className="flex-1 flex items-center gap-4 py-3 px-4 hover:bg-gray-50 dark:hover:bg-gray-800/50 cursor-pointer"
        >
          <span className="w-6 text-sm font-bold text-gray-400 text-right">{rank}</span>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm text-gray-900 dark:text-gray-100">{item.symbol}</span>
              {item.is_low_liquidity && <LowLiquidityBadge />}
            </div>
            <span className="text-xs text-gray-500 dark:text-gray-400 truncate block">{item.name}</span>
          </div>
          <div className="w-20 shrink-0 text-right">
            <div className={`text-sm font-medium ${isPositive ? CHANGE_TEXT.up : CHANGE_TEXT.down}`}>
              {isPositive ? '▲' : '▼'} {Math.abs(item.raw_return * 100).toFixed(2)}%
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400">관심도 {item.score.toFixed(1)}</div>
            <AttentionStandingBar score={item.score} />
          </div>
          {/* 3 primary metric value columns */}
          <div className="flex gap-3">
            <MetricCell value={item.trend_quality} domain="center" domainMax={2} signed />
            <MetricCell value={item.theme_beta} domain="baseline" domainMax={2} />
            <MetricCell value={item.capture_spread} domain="center" domainMax={100} signed />
          </div>
        </Link>
        <button
          aria-label={expanded ? `${item.symbol} 상세 접기` : `${item.symbol} 상세 펼치기`}
          className="shrink-0 p-1 text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300"
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            setExpanded((prev) => !prev);
          }}
        >
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
      </div>
      {expanded && (
        <div className="px-4 pb-3 pt-2 border-t border-gray-100 dark:border-gray-700 space-y-3">
          {/* ── 소제목 1: 관심도 근거 ───────────────────────────────── */}
          <div>
            <div className="text-xs font-semibold text-gray-600 dark:text-gray-300 mb-1">
              관심도 근거
            </div>
            <p className="text-xs text-gray-400 dark:text-gray-500 mb-2">
              관심도 점수 = 거래량 50% · 변동성 30% · 수익률 20%
            </p>
            <div className="flex flex-col gap-1">
              {/* 거래량 z (비중 50%) */}
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-500 dark:text-gray-400 w-32 shrink-0">
                  {METRIC_INFO.volume_z.label} <span className="text-gray-400">(비중 50%)</span>
                </span>
                <span className="text-sm font-medium text-gray-700 dark:text-gray-200">
                  {item.volume_z !== null && item.volume_z !== undefined
                    ? item.volume_z.toFixed(2)
                    : '—'}
                </span>
                <MetricInfoPopover metricKey="volume_z" />
              </div>
              {/* 변동성 (비중 30%) */}
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-500 dark:text-gray-400 w-32 shrink-0">
                  {METRIC_INFO.volatility_pct.label} <span className="text-gray-400">(비중 30%)</span>
                </span>
                <span className="text-sm font-medium text-gray-700 dark:text-gray-200">
                  {item.volatility_pct !== null && item.volatility_pct !== undefined
                    ? `${(item.volatility_pct * 100).toFixed(0)}%`
                    : '—'}
                </span>
                <MetricInfoPopover metricKey="volatility_pct" />
              </div>
              {/* 수익률 캐비엇 (본문에 이미 있음 — 재노출 안 함) */}
              <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
                수익률(20%)은 위 행의 % 참고
              </p>
            </div>
          </div>

          {/* ── 소제목 2: 주도지표 보조 ─────────────────────────────── */}
          <div>
            <div className="text-xs font-semibold text-gray-600 dark:text-gray-300 mb-1">
              주도지표 보조
            </div>
            <div className="flex items-start gap-4">
              <div className="flex flex-col gap-0.5">
                <span className="text-xs text-gray-500 dark:text-gray-400">{METRIC_INFO.theme_alpha.label}</span>
                {/* T3는 보조 — 막대 없이 숫자만(추세강도와 상관 높아 시각 강조 배제) */}
                <span className="text-sm font-medium text-gray-700 dark:text-gray-200">
                  {item.theme_alpha !== null ? item.theme_alpha.toFixed(2) : '—'}
                </span>
              </div>
              <div className="flex-1">
                <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
                  {METRIC_INFO.theme_alpha.description}
                </p>
                <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">
                  추세강도와 상관 높아 참고용
                </p>
              </div>
            </div>
          </div>

          <Link
            href={`/chainsight/${item.symbol}`}
            className="inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
          >
            관계 그래프 열기
          </Link>
        </div>
      )}
      {(item.is_low_liquidity || item.is_fallback) && (
        <div className="px-4 pb-3">
          <LowLiquidityPanel item={item} />
        </div>
      )}
    </div>
  );
}

export default function EventRanking({ theme }: Props) {
  const router = useRouter();
  const label = getLabelForTheme(theme);
  const [selectedWindow, setSelectedWindow] = useState<20 | 120>(20);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['chainsight', 'events', theme, 'stocks', selectedWindow],
    queryFn: () => fetchEventStocks(theme, selectedWindow),
    staleTime: 1000 * 60 * 5,
  });

  return (
    <div className="p-6">
      <div className="mb-6">
        <button
          onClick={() => router.back()}
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 mb-4"
        >
          <ArrowLeft size={16} />
          이벤트 보드
        </button>
        <div className="flex items-center gap-2 flex-wrap">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            {label.ko} — 관련 종목 그룹
          </h1>
          {/* ⓐ 저신뢰 표식: 멤버<3(quorum 미달) → 그룹 상대지표 통계 근거 약함(표에서 "—") */}
          {data && data.length > 0 && data.length < 3 && (
            <span
              className="text-xs font-medium text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/30 px-2 py-0.5 rounded-full cursor-help"
              title={`표본 작음 — 멤버 ${data.length}개(3개 미만). 그룹 상대지표(민감도·주도우위)는 통계 근거가 약해 "—"로 표시됩니다. 추세강도(절대 지표)는 유효합니다`}
            >
              표본 작음 (멤버 {data.length})
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 mt-3">
          <span className="text-xs text-gray-500 dark:text-gray-400">관측 기간</span>
          {([20, 120] as const).map((w) => (
            <button
              key={w}
              onClick={() => setSelectedWindow(w)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                selectedWindow === w
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
              }`}
              aria-pressed={selectedWindow === w}
            >
              {w}일
            </button>
          ))}
        </div>
      </div>

      {isLoading && (
        <div className="p-8 text-center text-gray-500">로딩 중...</div>
      )}

      {isError && (
        <div className="p-8 text-center text-red-500">데이터를 불러올 수 없습니다</div>
      )}

      {data && data.length === 0 && (
        <div className="p-8 text-center text-gray-500">종목 데이터가 없습니다</div>
      )}

      {data && data.length > 0 && (
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          <RankingHeader />
          {[...data]
            .sort((a, b) => b.score - a.score)
            .map((item, index) => (
              <RankingRow key={item.symbol} item={item} rank={index + 1} />
            ))}
        </div>
      )}
    </div>
  );
}

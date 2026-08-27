'use client';

import { Fragment, type ReactNode } from 'react';
import { Layers } from 'lucide-react';
import type { SignalStock } from '@/types/eod';
import { CONFLUENCE_MIN_AXES } from './confluence';
import { hasRealNews, newsRecencyLabel, validSector } from './scannerFilters';
import {
  formatRsi,
  formatMaState,
  RSI_STATE_CHIP,
  MA_STATE_CHIP,
} from './technicalLabels';

/**
 * 직교 축 칩 슬롯 (D-SCANNER-SELECT-UX ② · 축 슬롯 행).
 *
 * 구조 = **순서 있는 슬롯 배열**. 각 슬롯 = (ctx) => 칩 | null.
 * - ①단계 점등: 합류 · 섹터 · 뉴스(실매칭). 데이터 없으면 null(정칙 ⑴ — 조용히 생략).
 * - 미래 슬롯(RSI·밸류·퀄리티·관계) = 슬롯만 존재, 현재 데이터 부재로 null 반환.
 *   ②③단계는 여기에 렌더러만 채우면 됨(additive) — 행 구조 무변.
 * 정칙 ⑵: 라벨은 상태 서술만(매매 암시 금지).
 */
export interface AxisChipContext {
  stock: SignalStock;
  axisCount: number; // 전 카드 합류 축 수(useConfluenceMap)
}

interface AxisSlot {
  id: string;
  render: (ctx: AxisChipContext) => ReactNode | null;
}

function chip(key: string, label: string, cls: string, icon?: ReactNode): ReactNode {
  return (
    <span
      key={key}
      className={`inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 text-[10px] font-medium border ${cls}`}
    >
      {icon}
      {label}
    </span>
  );
}

// 순서 = 화면 좌→우 우선순위. 신규 축은 배열에 항목 추가만 하면 된다.
export const AXIS_SLOTS: AxisSlot[] = [
  {
    id: 'confluence',
    render: ({ axisCount }) =>
      axisCount >= CONFLUENCE_MIN_AXES
        ? chip(
            'confluence',
            `${axisCount}축 합류`,
            'bg-indigo-50 text-indigo-700 border-indigo-200 dark:bg-indigo-900/20 dark:text-indigo-300 dark:border-indigo-800',
            <Layers className="w-2.5 h-2.5" />,
          )
        : null,
  },
  {
    id: 'sector',
    render: ({ stock }) =>
      validSector(stock.sector)
        ? chip('sector', stock.sector, 'bg-gray-100 text-gray-600 border-gray-200 dark:bg-gray-700/50 dark:text-gray-300 dark:border-gray-600')
        : null,
  },
  {
    id: 'news',
    render: ({ stock }) =>
      hasRealNews(stock)
        ? chip('news', newsRecencyLabel(stock), 'bg-blue-50 text-blue-700 border-blue-100 dark:bg-blue-900/20 dark:text-blue-300 dark:border-blue-800')
        : null,
  },
  // ── 기술 축(SCAN-B2-FE) — RSI 상태 + MA 상태 칩(≤2 절제·행 과밀 방지, 52주 상세는 패널 칸) ──
  {
    id: 'rsi',
    render: ({ stock }) => {
      const tech = stock.technical;
      if (!tech) return null; // 정칙 ⑴ — technical 부재 시 완전 생략
      const rsiLabel = formatRsi(tech);
      const maLabel = formatMaState(tech);
      if (!rsiLabel && !maLabel) return null;
      return (
        <Fragment key="tech">
          {rsiLabel && tech.rsi_state && chip('rsi', rsiLabel, RSI_STATE_CHIP[tech.rsi_state])}
          {maLabel && tech.ma_state && chip('ma', maLabel, MA_STATE_CHIP[tech.ma_state])}
        </Fragment>
      );
    },
  },
  // ── 미래 슬롯(②③단계 additive) — 현재 데이터 배선 전이라 null(정칙 ⑴) ──
  { id: 'valuation', render: () => null }, // ②: 비교군 명시 상대 밸류(정칙 ⑶)
  { id: 'quality', render: () => null }, // ②: ROE·성장·부채
  { id: 'relation', render: () => null }, // ③: 관계 강도 우선(정칙 ⑹)
];

export function AxisChipStrip({ stock, axisCount }: AxisChipContext) {
  const ctx: AxisChipContext = { stock, axisCount };
  const chips = AXIS_SLOTS.map((slot) => slot.render(ctx)).filter(Boolean);
  if (chips.length === 0) return null; // 전 축 결측 → 스트립 자체 생략
  return <div className="flex flex-wrap items-center gap-1 mt-1">{chips}</div>;
}

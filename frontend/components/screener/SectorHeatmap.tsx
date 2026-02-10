'use client';

import React from 'react';
import { Treemap, ResponsiveContainer, Tooltip } from 'recharts';
import { AlertCircle } from 'lucide-react';
import type { SectorPerformance } from '@/types/screener';

interface SectorHeatmapProps {
  sectors: SectorPerformance[];
  date?: string;
  isLoading?: boolean;
  error?: Error | null;
  onSectorClick?: (sector: string) => void;
}

interface TreemapData {
  name: string;
  name_ko: string;
  size: number;
  return_pct: number;
  color: string;
  etf_symbol: string;
  stock_count: number;
}

const CustomizedContent = (props: any) => {
  const { x, y, width, height, name, name_ko, stock_count } = props;
  const return_pct = Number(props.return_pct) || 0;

  // 작은 타일은 텍스트 생략
  if (width < 60 || height < 40) {
    return (
      <g>
        <rect
          x={x}
          y={y}
          width={width}
          height={height}
          style={{
            fill: props.color,
            stroke: '#fff',
            strokeWidth: 2,
          }}
        />
      </g>
    );
  }

  return (
    <g>
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        style={{
          fill: props.color,
          stroke: '#fff',
          strokeWidth: 2,
          cursor: 'pointer',
        }}
      />
      <text
        x={x + width / 2}
        y={y + height / 2 - 10}
        textAnchor="middle"
        fill="#fff"
        fontSize={width > 100 ? 14 : 12}
        fontWeight="600"
      >
        {name_ko}
      </text>
      <text
        x={x + width / 2}
        y={y + height / 2 + 8}
        textAnchor="middle"
        fill="#fff"
        fontSize={width > 100 ? 16 : 14}
        fontWeight="700"
      >
        {return_pct > 0 ? '+' : ''}
        {return_pct.toFixed(2)}%
      </text>
      {width > 100 && (
        <text
          x={x + width / 2}
          y={y + height / 2 + 24}
          textAnchor="middle"
          fill="rgba(255,255,255,0.8)"
          fontSize={10}
        >
          {stock_count}개 종목
        </text>
      )}
    </g>
  );
};

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload || !payload.length) {
    return null;
  }

  const data = payload[0].payload as TreemapData;
  const returnPct = Number(data.return_pct) || 0;

  return (
    <div className="bg-gray-900 dark:bg-gray-800 text-white px-3 py-2 rounded-lg shadow-lg text-sm">
      <div className="font-semibold mb-1">
        {data.name_ko} ({data.name})
      </div>
      <div className="text-xs space-y-0.5">
        <div>
          수익률:{' '}
          <span
            className={`font-semibold ${
              returnPct > 0 ? 'text-green-400' : 'text-red-400'
            }`}
          >
            {returnPct > 0 ? '+' : ''}
            {returnPct.toFixed(2)}%
          </span>
        </div>
        <div>종목 수: {data.stock_count}개</div>
        <div>ETF: {data.etf_symbol}</div>
      </div>
    </div>
  );
};

export default function SectorHeatmap({
  sectors,
  date,
  isLoading,
  error,
  onSectorClick,
}: SectorHeatmapProps) {
  if (isLoading) {
    return (
      <div className="rounded-xl border border-[#30363D] bg-[#161B22] p-6">
        <div className="animate-pulse">
          <div className="h-6 bg-[#21262D] rounded w-1/3 mb-4"></div>
          <div className="h-96 bg-[#21262D] rounded"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-[#30363D] bg-[#161B22] p-6">
        <div className="flex items-center gap-2 text-[#F85149]">
          <AlertCircle className="w-5 h-5" />
          <span className="text-sm">섹터 히트맵 데이터를 불러올 수 없습니다</span>
        </div>
      </div>
    );
  }

  if (!sectors || sectors.length === 0) {
    return (
      <div className="rounded-xl border border-[#30363D] bg-[#161B22] p-6">
        <div className="text-center text-[#8B949E] py-8">
          섹터 데이터가 없습니다
        </div>
      </div>
    );
  }

  // Recharts Treemap 데이터 변환
  const treemapData: TreemapData[] = sectors.map((sector) => ({
    name: sector.sector || sector.name || 'Unknown',
    name_ko: sector.name_ko || sector.sector || 'Unknown',
    size: sector.market_cap || 1, // 시가총액으로 크기 결정
    return_pct: Number(sector.return_pct) || 0,
    color: sector.color || '#6b7280',
    etf_symbol: sector.etf_symbol || '',
    stock_count: sector.stock_count || 0,
  }));

  const handleClick = (data: any) => {
    if (onSectorClick && data) {
      onSectorClick(data.name);
    }
  };

  return (
    <div className="rounded-xl border border-[#30363D] bg-[#161B22] p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-[#E6EDF3]">
          섹터 히트맵
        </h3>
        {date && (
          <span className="text-xs text-[#8B949E]">{date}</span>
        )}
      </div>

      {/* Legend */}
      <div className="flex items-center justify-center gap-4 mb-4 text-xs text-[#8B949E]">
        <div className="flex items-center gap-1">
          <div className="w-4 h-4 bg-red-600 rounded"></div>
          <span>하락</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-4 h-4 bg-yellow-500 rounded"></div>
          <span>보합</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-4 h-4 bg-green-600 rounded"></div>
          <span>상승</span>
        </div>
      </div>

      {/* Treemap */}
      <ResponsiveContainer width="100%" height={400}>
        <Treemap
          data={treemapData as any}
          dataKey="size"
          aspectRatio={4 / 3}
          stroke="#fff"
          fill="#8884d8"
          content={<CustomizedContent />}
          onClick={handleClick}
        >
          <Tooltip content={<CustomTooltip />} />
        </Treemap>
      </ResponsiveContainer>

      {/* Description */}
      <p className="text-xs text-[#8B949E] text-center mt-4">
        타일 크기는 시가총액, 색상은 수익률을 나타냅니다. 클릭하면 해당 섹터로 필터링됩니다.
      </p>
    </div>
  );
}

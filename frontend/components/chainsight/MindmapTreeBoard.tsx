'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { ArrowLeft } from 'lucide-react';
import { useMindmapTree } from '@/hooks/useMindmap';
import MindmapCardDetail from './MindmapCardDetail';
import {
  cardMatchesQuery,
  industryMatchesQuery,
  sectorMatchesQuery,
} from './mindmapConfig';
import type { MindmapCardSummary, MindmapIndustry, MindmapSector } from '@/types/chainsight';

/**
 * 마인드맵 메인 화면 (CS-P5-FE-CARD B3+B4) — /chainsight/mindmap.
 *
 * D1: 업종 2단(sector→industry) 뼈대 + 종목 카드. 관계 그래프/엣지 동결(force-graph 무접촉).
 * 기본 접힘 — 펼친 industry만 카드 렌더(초기 755 동시 렌더 방지).
 * 카드 클릭 → ?symbol=XXX 로 포커스(같은 라우트 인스턴스 유지 → 트리 펼침/검색 상태 보존).
 */
export default function MindmapTreeBoard() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const selectedSymbol = searchParams.get('symbol');

  const { data, isLoading, isError, refetch } = useMindmapTree();
  const [query, setQuery] = useState('');
  const [openSectors, setOpenSectors] = useState<Set<string>>(new Set());
  const [openIndustries, setOpenIndustries] = useState<Set<string>>(new Set());

  const searching = query.trim().length > 0;

  const visibleSectors = useMemo(() => {
    if (!data) return [];
    if (!searching) return data.sectors;
    return data.sectors.filter((s) => sectorMatchesQuery(s, query));
  }, [data, searching, query]);

  function selectSymbol(symbol: string) {
    router.push(`/chainsight/mindmap?symbol=${encodeURIComponent(symbol.toUpperCase())}`);
  }

  function closeDetail() {
    router.push('/chainsight/mindmap');
  }

  function toggleSector(sector: string) {
    setOpenSectors((prev) => {
      const next = new Set(prev);
      if (next.has(sector)) next.delete(sector);
      else next.add(sector);
      return next;
    });
  }

  function toggleIndustry(key: string) {
    setOpenIndustries((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-6">
      {/* 헤더 */}
      <div className="flex items-center gap-3 mb-4">
        <Link
          href="/chainsight"
          className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500"
        >
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-gray-100">업종 마인드맵</h1>
          {data && (
            <p className="text-xs text-gray-500 dark:text-gray-400">
              전체 {data.stock_total}종목 · {data.sector_count}개 업종
            </p>
          )}
        </div>
      </div>

      {/* 검색 */}
      <input
        type="search"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="티커 또는 종목명 검색"
        className="w-full mb-4 px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-400"
        aria-label="티커 또는 종목명 검색"
      />

      <div className="flex flex-col lg:flex-row gap-4 items-start">
        {/* 트리 */}
        <div className="flex-1 min-w-0 w-full flex flex-col gap-2">
          {isLoading && (
            <div className="flex flex-col items-center justify-center h-64 gap-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
              <div className="w-6 h-6 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin" />
              <p className="text-sm text-gray-400">마인드맵을 불러오는 중...</p>
            </div>
          )}

          {isError && (
            <div className="flex flex-col items-center justify-center h-64 gap-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
              <p className="text-sm text-red-500">데이터를 불러올 수 없습니다</p>
              <button
                onClick={() => refetch()}
                className="text-xs text-blue-600 dark:text-blue-400 underline"
              >
                다시 시도
              </button>
            </div>
          )}

          {data && visibleSectors.length === 0 && (
            <p className="py-8 text-center text-sm text-gray-400">검색 결과가 없습니다</p>
          )}

          {visibleSectors.map((sector) => (
            <SectorAccordion
              key={sector.sector}
              sector={sector}
              query={searching ? query : ''}
              forceOpen={searching}
              open={searching || openSectors.has(sector.sector)}
              onToggle={() => toggleSector(sector.sector)}
              openIndustries={openIndustries}
              onToggleIndustry={toggleIndustry}
              onSelectCard={selectSymbol}
              selectedSymbol={selectedSymbol}
            />
          ))}
        </div>

        {/* 카드 상세 패널 */}
        {selectedSymbol && (
          <div className="w-full lg:w-96 shrink-0 lg:sticky lg:top-4">
            <MindmapCardDetail
              symbol={selectedSymbol}
              onSelectOther={selectSymbol}
              onClose={closeDetail}
            />
          </div>
        )}
      </div>
    </div>
  );
}

function SectorAccordion({
  sector,
  query,
  forceOpen,
  open,
  onToggle,
  openIndustries,
  onToggleIndustry,
  onSelectCard,
  selectedSymbol,
}: {
  sector: MindmapSector;
  query: string;
  forceOpen: boolean;
  open: boolean;
  onToggle: () => void;
  openIndustries: Set<string>;
  onToggleIndustry: (key: string) => void;
  onSelectCard: (symbol: string) => void;
  selectedSymbol: string | null;
}) {
  const industries = forceOpen
    ? sector.industries.filter((ind) => industryMatchesQuery(ind, query))
    : sector.industries;

  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-700">
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-2 px-3 py-2.5 text-left"
        aria-expanded={open}
      >
        <span className="text-sm font-semibold text-gray-800 dark:text-gray-100">{sector.sector}</span>
        <span className="text-[11px] text-gray-400 tabular-nums" aria-label={`${sector.stock_count}종목`}>
          {sector.stock_count}종목 · {sector.industry_count}개 산업
        </span>
        <span className="ml-auto text-gray-400 text-xs">{open ? '▾' : '▸'}</span>
      </button>

      {open && (
        <div className="px-3 pb-2 flex flex-col gap-1.5">
          {industries.map((industry) => (
            <IndustryAccordion
              key={industry.industry}
              sectorKey={sector.sector}
              industry={industry}
              query={query}
              forceOpen={forceOpen}
              open={forceOpen || openIndustries.has(`${sector.sector}||${industry.industry}`)}
              onToggle={() => onToggleIndustry(`${sector.sector}||${industry.industry}`)}
              onSelectCard={onSelectCard}
              selectedSymbol={selectedSymbol}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function IndustryAccordion({
  industry,
  query,
  forceOpen,
  open,
  onToggle,
  onSelectCard,
  selectedSymbol,
}: {
  sectorKey: string;
  industry: MindmapIndustry;
  query: string;
  forceOpen: boolean;
  open: boolean;
  onToggle: () => void;
  onSelectCard: (symbol: string) => void;
  selectedSymbol: string | null;
}) {
  const cards = forceOpen ? industry.cards.filter((c) => cardMatchesQuery(c, query)) : industry.cards;

  return (
    <div className="border-l border-gray-200 dark:border-gray-700 pl-2">
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-2 py-1 text-left"
        aria-expanded={open}
      >
        <span className="text-xs text-gray-600 dark:text-gray-300">{industry.industry}</span>
        <span className="text-[11px] text-gray-400 tabular-nums">{industry.stock_count}</span>
        <span className="ml-auto text-gray-400 text-xs">{open ? '▾' : '▸'}</span>
      </button>

      {open && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-1.5 py-1.5">
          {cards.map((card) => (
            <CardTile
              key={card.ticker}
              card={card}
              selected={selectedSymbol === card.ticker}
              onSelect={() => onSelectCard(card.ticker)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function CardTile({
  card,
  selected,
  onSelect,
}: {
  card: MindmapCardSummary;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      onClick={onSelect}
      aria-label={`${card.ticker} 카드`}
      className={`text-left p-2 rounded-lg border transition ${
        selected
          ? 'border-blue-400 bg-blue-50 dark:bg-blue-900/20'
          : 'border-gray-200 dark:border-gray-700 hover:border-blue-400 hover:shadow-sm'
      }`}
    >
      <div className="min-w-0 mb-1">
        <span className="block font-semibold text-xs truncate">{card.ticker}</span>
        <span className="block text-[10px] text-gray-500 truncate">{card.name}</span>
      </div>
      <div className="flex flex-wrap gap-1">
        <span
          className={`px-1.5 py-0.5 text-[10px] rounded-full ${
            card.gate_conn_count > 0
              ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
              : 'bg-gray-100 text-gray-400 dark:bg-gray-700/50 dark:text-gray-500'
          }`}
        >
          연결 {card.gate_conn_count}
        </span>
        <span
          className={`px-1.5 py-0.5 text-[10px] rounded-full ${
            card.group_signal_count > 0
              ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400'
              : 'bg-gray-100 text-gray-400 dark:bg-gray-700/50 dark:text-gray-500'
          }`}
        >
          그룹 {card.group_signal_count}
        </span>
      </div>
    </button>
  );
}

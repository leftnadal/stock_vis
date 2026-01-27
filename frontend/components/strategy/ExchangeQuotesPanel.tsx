'use client';

import { TrendingUp, Loader2, AlertCircle } from 'lucide-react';
import { useExchangeQuotes } from '@/hooks/useExchangeQuotes';
import { QuoteCard } from './QuoteCard';

export function ExchangeQuotesPanel() {
  const { data: quotes, isLoading, error } = useExchangeQuotes();

  if (isLoading) {
    return (
      <div className="rounded-lg border border-[#30363D] bg-[#161B22] p-6">
        <div className="mb-4 flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-[#58A6FF]" />
          <h2 className="text-lg font-semibold text-[#E6EDF3]">주요 지수</h2>
        </div>
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-[#58A6FF]" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-[#30363D] bg-[#161B22] p-6">
        <div className="mb-4 flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-[#58A6FF]" />
          <h2 className="text-lg font-semibold text-[#E6EDF3]">주요 지수</h2>
        </div>
        <div className="flex items-center gap-2 rounded-lg border border-[#F85149]/20 bg-[#F85149]/10 p-4">
          <AlertCircle className="h-5 w-5 flex-shrink-0 text-[#F85149]" />
          <p className="text-sm text-[#E6EDF3]">데이터를 불러올 수 없습니다.</p>
        </div>
      </div>
    );
  }

  if (!quotes || quotes.length === 0) {
    return (
      <div className="rounded-lg border border-[#30363D] bg-[#161B22] p-6">
        <div className="mb-4 flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-[#58A6FF]" />
          <h2 className="text-lg font-semibold text-[#E6EDF3]">주요 지수</h2>
        </div>
        <p className="text-center text-sm text-[#8B949E] py-8">데이터가 없습니다.</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-[#30363D] bg-[#161B22] p-6">
      <div className="mb-4 flex items-center gap-2">
        <TrendingUp className="h-5 w-5 text-[#58A6FF]" />
        <h2 className="text-lg font-semibold text-[#E6EDF3]">주요 지수</h2>
        <span className="ml-auto text-xs text-[#8B949E]">60초마다 갱신</span>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {quotes.map((quote) => (
          <QuoteCard key={quote.symbol} quote={quote} />
        ))}
      </div>
    </div>
  );
}

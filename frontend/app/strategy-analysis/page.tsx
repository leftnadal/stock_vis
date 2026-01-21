'use client';

import { Target } from 'lucide-react';
import { ExchangeQuotesPanel } from '@/components/strategy/ExchangeQuotesPanel';
import { StockScreenerPanel } from '@/components/strategy/StockScreenerPanel';
import { AIChatSidebar } from '@/components/strategy/AIChatSidebar';
import { AuthGuard } from '@/components/auth/AuthGuard';

function StrategyAnalysisContent() {
  const handleAddToBasket = (symbol: string) => {
    console.log('Adding to basket:', symbol);
    // TODO: 실제 바구니 추가 로직 구현
  };

  return (
    <div className="min-h-screen bg-[#0D1117]">
      {/* 헤더 */}
      <header className="border-b border-[#30363D] bg-[#161B22] px-6 py-4">
        <div className="flex items-center gap-3">
          <Target className="h-6 w-6 text-[#58A6FF]" />
          <div>
            <h1 className="text-2xl font-bold text-[#E6EDF3]">전략분석실</h1>
            <p className="mt-1 text-sm text-[#8B949E]">
              실시간 시장 데이터와 AI 분석으로 투자 전략 수립
            </p>
          </div>
        </div>
      </header>

      {/* 메인 콘텐츠 */}
      <main className="p-6">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_400px] xl:grid-cols-[1fr_500px]">
          {/* 좌측 패널 - 데이터 영역 */}
          <div className="space-y-6">
            {/* 주요 지수 */}
            <ExchangeQuotesPanel />

            {/* 종목 스크리너 */}
            <StockScreenerPanel onAddToBasket={handleAddToBasket} />
          </div>

          {/* 우측 패널 - AI Chat */}
          <div className="lg:sticky lg:top-6 lg:h-[calc(100vh-120px)]">
            <div className="h-full rounded-lg border border-[#30363D] bg-[#161B22] shadow-lg">
              <AIChatSidebar />
            </div>
          </div>
        </div>
      </main>

      {/* 모바일: 플로팅 AI Chat 버튼 (선택사항) */}
      {/* <div className="fixed bottom-6 right-6 lg:hidden">
        <button
          onClick={() => {}}
          className="flex h-14 w-14 items-center justify-center rounded-full bg-[#58A6FF] text-white shadow-lg transition-transform hover:scale-110"
        >
          <Target className="h-6 w-6" />
        </button>
      </div> */}
    </div>
  );
}

export default function StrategyAnalysisPage() {
  return (
    <AuthGuard>
      <StrategyAnalysisContent />
    </AuthGuard>
  );
}

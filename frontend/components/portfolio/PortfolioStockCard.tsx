'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { MoreVertical, Loader2 } from 'lucide-react';
import { portfolioService, StockDataStatus } from '@/services/portfolio';
import { formatCurrency, formatPercent } from '@/utils/formatters';
import { isProfit, getProfitTextColor, getProfitTextColorLight, getProfitSign } from '@/utils/styling';

interface PortfolioStock {
  symbol: string;
  name: string;
  shares: number;
  avgPrice: number;
  currentPrice: number;
  value: number;
  gain: number;
  gainPercent: number;
}

interface PortfolioStockCardProps {
  stock: PortfolioStock;
  onDataComplete?: () => void;
}

export default function PortfolioStockCard({ stock, onDataComplete }: PortfolioStockCardProps) {
  const router = useRouter();
  const isPositive = isProfit(stock.gain);
  const [dataStatus, setDataStatus] = useState<StockDataStatus | null>(null);
  const [isPolling, setIsPolling] = useState(false);

  // 데이터 상태 확인 및 폴링
  useEffect(() => {
    let intervalId: NodeJS.Timeout | null = null;

    const checkDataStatus = async () => {
      try {
        const status = await portfolioService.getStockDataStatus(stock.symbol);
        setDataStatus(status);

        // 데이터가 완전하면 폴링 중지
        if (status.is_complete) {
          setIsPolling(false);
          if (intervalId) {
            clearInterval(intervalId);
          }
          if (onDataComplete) {
            onDataComplete();
          }
        } else if (!isPolling) {
          // 데이터가 불완전하면 폴링 시작
          setIsPolling(true);
        }
      } catch (error) {
        console.error('Failed to check data status:', error);
      }
    };

    // 초기 상태 확인
    checkDataStatus();

    // 10초마다 폴링
    intervalId = setInterval(() => {
      if (isPolling || !dataStatus?.is_complete) {
        checkDataStatus();
      }
    }, 10000);

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [stock.symbol, isPolling, onDataComplete]);

  // 로딩 상태 표시 컴포넌트
  const DataLoadingIndicator = () => {
    if (!dataStatus || dataStatus.is_complete) return null;

    const loadingItems = [];
    if (!dataStatus.has_prices) loadingItems.push('가격 데이터');
    if (!dataStatus.has_financial) loadingItems.push('재무제표');

    if (loadingItems.length === 0) return null;

    return (
      <div className="mt-3 p-2 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
        <div className="flex items-center space-x-2">
          <Loader2 className="h-4 w-4 text-yellow-600 dark:text-yellow-400 animate-spin" />
          <span className="text-xs text-yellow-700 dark:text-yellow-300">
            {loadingItems.join(', ')} 업로딩중...
          </span>
        </div>
      </div>
    );
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl p-4 hover:shadow-lg transition-shadow cursor-pointer">
      <div className="flex justify-between items-start mb-3">
        <div className="flex-1">
          <div className="flex items-center justify-between">
            <div
              onClick={() => router.push(`/stocks/${stock.symbol}`)}
              className="cursor-pointer hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
            >
              <h3 className="font-semibold text-gray-900 dark:text-white text-lg">
                {stock.symbol}
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {stock.name}
              </p>
            </div>
            <div className="text-right">
              <button className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 float-right">
                <MoreVertical className="h-5 w-5" />
              </button>
              <div className="clear-both">
                <div className="text-lg font-bold text-gray-900 dark:text-white">
                  {formatCurrency(stock.currentPrice)}
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  종가
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="space-y-3">
        {/* 현재 가치 */}
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">보유 가치</span>
          <span className="font-semibold text-gray-900 dark:text-white">
            {formatCurrency(stock.value)}
          </span>
        </div>

        {/* 손익 */}
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">손익</span>
          <div className="text-right">
            <div className={`font-semibold ${getProfitTextColor(stock.gain)}`}>
              {getProfitSign(stock.gain)}{formatCurrency(stock.gain)}
            </div>
            <div className={`text-xs ${getProfitTextColorLight(stock.gain)}`}>
              {formatPercent(stock.gainPercent)}
            </div>
          </div>
        </div>

        {/* 보유 정보 */}
        <div className="pt-3 border-t border-gray-200 dark:border-gray-700 grid grid-cols-2 gap-3 text-sm">
          <div>
            <p className="text-gray-500 dark:text-gray-400 text-xs">보유 수량</p>
            <p className="font-medium text-gray-900 dark:text-white">{stock.shares}주</p>
          </div>
          <div>
            <p className="text-gray-500 dark:text-gray-400 text-xs">평균 매입가</p>
            <p className="font-medium text-gray-900 dark:text-white">{formatCurrency(stock.avgPrice)}</p>
          </div>
        </div>

        {/* 데이터 로딩 상태 표시 */}
        <DataLoadingIndicator />
      </div>
    </div>
  );
}

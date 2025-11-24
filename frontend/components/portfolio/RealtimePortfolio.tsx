'use client';

import React from 'react';
import { usePortfolioWebSocket } from '@/hooks/useWebSocket';

export default function RealtimePortfolio() {
  const { isConnected, portfolioData, error, refresh } = usePortfolioWebSocket();

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-600">포트폴리오 연결 오류: {error}</p>
      </div>
    );
  }

  if (!isConnected) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <div className="animate-pulse">
          <p className="text-gray-600">실시간 포트폴리오 연결 중...</p>
        </div>
      </div>
    );
  }

  if (!portfolioData) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <p className="text-gray-600">포트폴리오 데이터 로딩 중...</p>
      </div>
    );
  }

  const isProfit = parseFloat(portfolioData.profit_loss || 0) >= 0;
  const profitColor = isProfit ? 'text-green-600' : 'text-red-600';
  const profitBgColor = isProfit ? 'bg-green-50' : 'bg-red-50';

  return (
    <div className="space-y-4">
      {/* 포트폴리오 요약 카드 */}
      <div className={`${profitBgColor} rounded-lg p-6 border`}>
        <div className="flex justify-between items-start mb-4">
          <h2 className="text-2xl font-bold">포트폴리오 실시간 현황</h2>
          <button
            onClick={refresh}
            className="px-3 py-1 text-sm bg-white border rounded hover:bg-gray-50"
          >
            새로고침
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <p className="text-sm text-gray-600">총 평가액</p>
            <p className="text-2xl font-bold">
              ${parseFloat(portfolioData.total_value || 0).toLocaleString('en-US', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </p>
          </div>

          <div>
            <p className="text-sm text-gray-600">총 투자금</p>
            <p className="text-2xl font-bold">
              ${parseFloat(portfolioData.total_cost || 0).toLocaleString('en-US', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </p>
          </div>

          <div>
            <p className="text-sm text-gray-600">손익</p>
            <p className={`text-2xl font-bold ${profitColor}`}>
              {isProfit ? '+' : ''}
              ${parseFloat(portfolioData.profit_loss || 0).toLocaleString('en-US', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </p>
          </div>

          <div>
            <p className="text-sm text-gray-600">수익률</p>
            <p className={`text-2xl font-bold ${profitColor}`}>
              {isProfit ? '+' : ''}
              {parseFloat(portfolioData.profit_loss_percentage || 0).toFixed(2)}%
            </p>
          </div>
        </div>

        <div className="mt-2 flex items-center">
          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse mr-2"></div>
          <span className="text-xs text-gray-600">실시간 업데이트 중</span>
        </div>
      </div>

      {/* 개별 종목 리스트 */}
      {portfolioData.portfolios && portfolioData.portfolios.length > 0 && (
        <div className="bg-white rounded-lg border">
          <div className="px-6 py-4 border-b">
            <h3 className="text-lg font-semibold">보유 종목</h3>
          </div>
          <div className="divide-y">
            {portfolioData.portfolios.map((item: any) => {
              const itemProfit = parseFloat(item.profit_loss || 0) >= 0;
              const itemProfitColor = itemProfit ? 'text-green-600' : 'text-red-600';

              return (
                <div key={item.symbol} className="px-6 py-4 hover:bg-gray-50">
                  <div className="flex justify-between items-center">
                    <div className="flex-1">
                      <div className="flex items-center gap-4">
                        <div>
                          <p className="font-semibold">{item.symbol}</p>
                          {item.name && (
                            <p className="text-sm text-gray-600">{item.name}</p>
                          )}
                        </div>
                        <div className="text-sm text-gray-600">
                          {parseFloat(item.quantity || 0).toFixed(2)}주
                        </div>
                      </div>
                    </div>

                    <div className="text-right space-y-1">
                      <p className="font-semibold">
                        ${parseFloat(item.value || 0).toLocaleString('en-US', {
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2,
                        })}
                      </p>
                      <p className={`text-sm ${itemProfitColor}`}>
                        {itemProfit ? '+' : ''}
                        ${parseFloat(item.profit_loss || 0).toFixed(2)}
                        ({parseFloat(item.profit_loss_percentage || 0).toFixed(2)}%)
                      </p>
                    </div>
                  </div>

                  <div className="mt-2 grid grid-cols-2 gap-4 text-sm text-gray-600">
                    <div>
                      평균 매입가: ${parseFloat(item.average_price || 0).toFixed(2)}
                    </div>
                    <div>
                      현재가: ${parseFloat(item.current_price || 0).toFixed(2)}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
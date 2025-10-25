'use client';

import Link from 'next/link';
import { ChevronUp, ChevronDown } from 'lucide-react';
import { StockListItem } from '@/types';

interface StockTableProps {
  stocks: StockListItem[];
  title?: string;
}

export default function StockTable({ stocks, title = "주요 종목" }: StockTableProps) {
  const formatNumber = (num: number) => {
    return new Intl.NumberFormat('ko-KR').format(num);
  };

  const formatMarketCap = (marketCap: number) => {
    if (marketCap >= 1e12) {
      return `$${(marketCap / 1e12).toFixed(2)}T`;
    } else if (marketCap >= 1e9) {
      return `$${(marketCap / 1e9).toFixed(2)}B`;
    } else if (marketCap >= 1e6) {
      return `$${(marketCap / 1e6).toFixed(2)}M`;
    }
    return `$${formatNumber(marketCap)}`;
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200">
      <div className="px-6 py-4 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="text-xs text-gray-600 border-b border-gray-200">
              <th className="text-left py-3 px-6 font-medium">종목명</th>
              <th className="text-right py-3 px-4 font-medium">현재가</th>
              <th className="text-right py-3 px-4 font-medium">변동</th>
              <th className="text-right py-3 px-4 font-medium">변동%</th>
              <th className="text-right py-3 px-4 font-medium">시가총액</th>
              <th className="text-center py-3 px-4 font-medium">섹터</th>
              <th className="text-center py-3 px-6 font-medium">차트</th>
            </tr>
          </thead>
          <tbody>
            {stocks.map((stock, index) => {
              const isPositive = stock.change > 0;
              const isNegative = stock.change < 0;
              const changePercent = stock.changePercent ? stock.changePercent.toFixed(2) : '0.00';

              return (
                <tr
                  key={stock.symbol}
                  className={`border-b border-gray-100 hover:bg-gray-50 transition-colors cursor-pointer ${
                    index % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'
                  }`}
                  onClick={() => window.location.href = `/stocks/${stock.symbol}`}
                >
                  <td className="py-3 px-6">
                    <Link href={`/stocks/${stock.symbol}`} className="hover:underline">
                      <div className="flex items-center">
                        <div>
                          <div className="font-semibold text-gray-900">{stock.symbol}</div>
                          <div className="text-xs text-gray-500">{stock.name}</div>
                        </div>
                      </div>
                    </Link>
                  </td>

                  <td className="text-right py-3 px-4">
                    <span className="font-semibold text-gray-900">
                      ${stock.price.toFixed(2)}
                    </span>
                  </td>

                  <td className="text-right py-3 px-4">
                    <div className="flex items-center justify-end">
                      {isPositive && <ChevronUp className="h-4 w-4 text-green-600 mr-1" />}
                      {isNegative && <ChevronDown className="h-4 w-4 text-red-600 mr-1" />}
                      <span className={`font-medium ${
                        isPositive ? 'text-green-600' : isNegative ? 'text-red-600' : 'text-gray-600'
                      }`}>
                        {isPositive ? '+' : ''}{stock.change.toFixed(2)}
                      </span>
                    </div>
                  </td>

                  <td className="text-right py-3 px-4">
                    <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${
                      isPositive
                        ? 'bg-green-100 text-green-800'
                        : isNegative
                        ? 'bg-red-100 text-red-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}>
                      {isPositive ? '+' : ''}{changePercent}%
                    </span>
                  </td>

                  <td className="text-right py-3 px-4 text-gray-700 text-sm">
                    {formatMarketCap(stock.marketCap)}
                  </td>

                  <td className="text-center py-3 px-4">
                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                      {stock.sector}
                    </span>
                  </td>

                  <td className="text-center py-3 px-6">
                    <div className="inline-block w-16 h-8">
                      {/* Mini sparkline chart placeholder */}
                      <svg viewBox="0 0 100 40" className="w-full h-full">
                        <polyline
                          fill="none"
                          stroke={isPositive ? '#10b981' : isNegative ? '#ef4444' : '#6b7280'}
                          strokeWidth="2"
                          points={
                            isPositive
                              ? "0,35 20,30 40,25 60,20 80,15 100,10"
                              : isNegative
                              ? "0,10 20,15 40,20 60,25 80,30 100,35"
                              : "0,20 20,18 40,20 60,19 80,20 100,20"
                          }
                        />
                      </svg>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
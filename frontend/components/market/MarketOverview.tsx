'use client';

import { TrendingUp, TrendingDown } from 'lucide-react';

interface MarketIndex {
  name: string;
  value: number;
  change: number;
  changePercent: number;
}

export default function MarketOverview() {
  // 샘플 데이터 - 실제로는 API에서 가져와야 함
  const indices: MarketIndex[] = [
    { name: 'S&P 500', value: 5808.12, change: 44.06, changePercent: 0.76 },
    { name: 'Dow Jones', value: 42374.36, change: -140.59, changePercent: -0.33 },
    { name: 'Nasdaq', value: 18415.49, change: 138.83, changePercent: 0.76 },
    { name: 'Russell 2000', value: 2244.63, change: 10.59, changePercent: 0.47 },
    { name: 'VIX', value: 18.03, change: -0.56, changePercent: -3.01 },
  ];

  const commodities = [
    { name: '금', value: 2741.20, change: 8.30, changePercent: 0.30, unit: 'oz' },
    { name: '원유', value: 70.19, change: -0.97, changePercent: -1.36, unit: 'bbl' },
    { name: '은', value: 34.52, change: 0.41, changePercent: 1.20, unit: 'oz' },
  ];

  const currencies = [
    { name: 'EUR/USD', value: 1.0812, change: 0.0015, changePercent: 0.14 },
    { name: 'USD/JPY', value: 151.93, change: -0.42, changePercent: -0.28 },
    { name: 'GBP/USD', value: 1.2967, change: 0.0023, changePercent: 0.18 },
  ];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
      {/* 주요 지수 */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="px-4 py-3 border-b border-gray-200">
          <h3 className="text-sm font-semibold text-gray-900">미국 주요 지수</h3>
        </div>
        <div className="p-4 space-y-3">
          {indices.map((index) => (
            <div key={index.name} className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-gray-900">{index.name}</div>
                <div className="text-xs text-gray-500">{index.value.toLocaleString()}</div>
              </div>
              <div className={`flex items-center ${index.change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {index.change >= 0 ? (
                  <TrendingUp className="h-4 w-4 mr-1" />
                ) : (
                  <TrendingDown className="h-4 w-4 mr-1" />
                )}
                <div className="text-right">
                  <div className="text-sm font-medium">
                    {index.change >= 0 ? '+' : ''}{index.change.toFixed(2)}
                  </div>
                  <div className="text-xs">
                    {index.change >= 0 ? '+' : ''}{index.changePercent.toFixed(2)}%
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 원자재 */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="px-4 py-3 border-b border-gray-200">
          <h3 className="text-sm font-semibold text-gray-900">원자재</h3>
        </div>
        <div className="p-4 space-y-3">
          {commodities.map((commodity) => (
            <div key={commodity.name} className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-gray-900">{commodity.name}</div>
                <div className="text-xs text-gray-500">
                  ${commodity.value.toFixed(2)}/{commodity.unit}
                </div>
              </div>
              <div className={`flex items-center ${commodity.change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {commodity.change >= 0 ? (
                  <TrendingUp className="h-4 w-4 mr-1" />
                ) : (
                  <TrendingDown className="h-4 w-4 mr-1" />
                )}
                <div className="text-right">
                  <div className="text-sm font-medium">
                    {commodity.change >= 0 ? '+' : ''}{commodity.change.toFixed(2)}
                  </div>
                  <div className="text-xs">
                    {commodity.change >= 0 ? '+' : ''}{commodity.changePercent.toFixed(2)}%
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 환율 */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="px-4 py-3 border-b border-gray-200">
          <h3 className="text-sm font-semibold text-gray-900">주요 환율</h3>
        </div>
        <div className="p-4 space-y-3">
          {currencies.map((currency) => (
            <div key={currency.name} className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-gray-900">{currency.name}</div>
                <div className="text-xs text-gray-500">{currency.value.toFixed(4)}</div>
              </div>
              <div className={`flex items-center ${currency.change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {currency.change >= 0 ? (
                  <TrendingUp className="h-4 w-4 mr-1" />
                ) : (
                  <TrendingDown className="h-4 w-4 mr-1" />
                )}
                <div className="text-right">
                  <div className="text-sm font-medium">
                    {currency.change >= 0 ? '+' : ''}{currency.change.toFixed(4)}
                  </div>
                  <div className="text-xs">
                    {currency.change >= 0 ? '+' : ''}{currency.changePercent.toFixed(2)}%
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
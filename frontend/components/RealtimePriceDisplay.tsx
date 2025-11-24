'use client';

import React from 'react';
import { useStockPriceWebSocket } from '@/hooks/useWebSocket';

interface RealtimePriceDisplayProps {
  symbol: string;
}

export default function RealtimePriceDisplay({ symbol }: RealtimePriceDisplayProps) {
  const { isConnected, priceData, error } = useStockPriceWebSocket(symbol);

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-600">연결 오류: {error}</p>
      </div>
    );
  }

  if (!isConnected) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <div className="animate-pulse">
          <p className="text-gray-600">실시간 데이터 연결 중...</p>
        </div>
      </div>
    );
  }

  if (!priceData) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <p className="text-gray-600">데이터 로딩 중...</p>
      </div>
    );
  }

  const isPositive = parseFloat(priceData.change || 0) >= 0;
  const changeColor = isPositive ? 'text-green-600' : 'text-red-600';
  const bgColor = isPositive ? 'bg-green-50' : 'bg-red-50';

  return (
    <div className={`border rounded-lg p-6 ${bgColor}`}>
      <div className="flex justify-between items-start">
        <div>
          <h2 className="text-2xl font-bold">{symbol}</h2>
          {priceData.name && (
            <p className="text-gray-600">{priceData.name}</p>
          )}
        </div>
        <div className="text-right">
          <div className="text-3xl font-bold">
            ${parseFloat(priceData.price || 0).toFixed(2)}
          </div>
          <div className={`${changeColor} font-semibold`}>
            {isPositive ? '+' : ''}
            {parseFloat(priceData.change || 0).toFixed(2)}
            ({parseFloat(priceData.change_percent || 0).toFixed(2)}%)
          </div>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
        {priceData.volume && (
          <div>
            <span className="text-gray-600">거래량:</span>
            <span className="ml-2 font-semibold">
              {parseInt(priceData.volume).toLocaleString()}
            </span>
          </div>
        )}
        {priceData.high && (
          <div>
            <span className="text-gray-600">고가:</span>
            <span className="ml-2 font-semibold">
              ${parseFloat(priceData.high).toFixed(2)}
            </span>
          </div>
        )}
        {priceData.low && (
          <div>
            <span className="text-gray-600">저가:</span>
            <span className="ml-2 font-semibold">
              ${parseFloat(priceData.low).toFixed(2)}
            </span>
          </div>
        )}
        {priceData.timestamp && (
          <div>
            <span className="text-gray-600">업데이트:</span>
            <span className="ml-2 font-semibold">
              {new Date(priceData.timestamp).toLocaleTimeString()}
            </span>
          </div>
        )}
      </div>

      <div className="mt-2 flex items-center">
        <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse mr-2"></div>
        <span className="text-xs text-gray-600">실시간 연결됨</span>
      </div>
    </div>
  );
}
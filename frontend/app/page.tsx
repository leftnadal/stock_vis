'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import PortfolioSummary from '@/components/portfolio/PortfolioSummary';
import PortfolioStockCard from '@/components/portfolio/PortfolioStockCard';
import { apiClient } from '@/lib/api/client';
import { API_ENDPOINTS } from '@/lib/api/config';
import { Plus, TrendingUp, Shield, Target } from 'lucide-react';

export default function Home() {
  const [loading, setLoading] = useState(false);

  // 샘플 포트폴리오 데이터 (실제로는 사용자 데이터를 가져와야 함)
  const portfolioStocks = [
    {
      symbol: 'AAPL',
      name: 'Apple Inc.',
      shares: 50,
      avgPrice: 150.00,
      currentPrice: 180.00,
      value: 9000.00,
      gain: 1500.00,
      gainPercent: 20.00,
    },
    {
      symbol: 'MSFT',
      name: 'Microsoft',
      shares: 30,
      avgPrice: 320.00,
      currentPrice: 380.00,
      value: 11400.00,
      gain: 1800.00,
      gainPercent: 18.75,
    },
    {
      symbol: 'GOOGL',
      name: 'Alphabet',
      shares: 20,
      avgPrice: 130.00,
      currentPrice: 140.00,
      value: 2800.00,
      gain: 200.00,
      gainPercent: 7.69,
    },
    {
      symbol: 'TSLA',
      name: 'Tesla Inc.',
      shares: 15,
      avgPrice: 280.00,
      currentPrice: 250.00,
      value: 3750.00,
      gain: -450.00,
      gainPercent: -10.71,
    },
  ];

  return (
    <div className="min-h-screen pb-20 md:pb-0">
      {/* 메인 컨테이너 - 모바일 최적화 */}
      <div className="max-w-4xl mx-auto px-4 py-6">

        {/* 환영 메시지 */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
            안녕하세요, 투자자님 👋
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            오늘도 성공적인 투자 하세요!
          </p>
        </div>

        {/* 포트폴리오 요약 */}
        <PortfolioSummary />

        {/* 빠른 기능 버튼들 */}
        <div className="grid grid-cols-3 gap-3 mb-8">
          <button className="bg-white dark:bg-gray-800 p-4 rounded-xl shadow-sm hover:shadow-md transition-shadow">
            <TrendingUp className="h-6 w-6 text-blue-600 mb-2 mx-auto" />
            <span className="text-xs text-gray-700 dark:text-gray-300">AI 분석</span>
          </button>
          <button className="bg-white dark:bg-gray-800 p-4 rounded-xl shadow-sm hover:shadow-md transition-shadow">
            <Shield className="h-6 w-6 text-green-600 mb-2 mx-auto" />
            <span className="text-xs text-gray-700 dark:text-gray-300">리스크 관리</span>
          </button>
          <button className="bg-white dark:bg-gray-800 p-4 rounded-xl shadow-sm hover:shadow-md transition-shadow">
            <Target className="h-6 w-6 text-purple-600 mb-2 mx-auto" />
            <span className="text-xs text-gray-700 dark:text-gray-300">목표 설정</span>
          </button>
        </div>

        {/* 내 포트폴리오 섹션 */}
        <div className="mb-8">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-bold text-gray-900 dark:text-white">
              내 포트폴리오
            </h2>
            <button className="text-blue-600 dark:text-blue-400 text-sm font-medium">
              전체보기
            </button>
          </div>

          {/* 포트폴리오 주식 목록 */}
          <div className="grid gap-4 md:grid-cols-2">
            {portfolioStocks.map((stock) => (
              <PortfolioStockCard key={stock.symbol} stock={stock} />
            ))}
          </div>

          {/* 종목 추가 버튼 */}
          <button className="w-full mt-4 bg-blue-50 dark:bg-gray-800 border-2 border-dashed border-blue-300 dark:border-gray-600 rounded-xl p-6 flex items-center justify-center hover:bg-blue-100 dark:hover:bg-gray-700 transition-colors">
            <Plus className="h-6 w-6 text-blue-600 dark:text-blue-400 mr-2" />
            <span className="text-blue-600 dark:text-blue-400 font-medium">
              새 종목 추가하기
            </span>
          </button>
        </div>

        {/* 추천 섹션 */}
        <div className="bg-gradient-to-r from-purple-50 to-blue-50 dark:from-gray-800 dark:to-gray-800 rounded-xl p-6 mb-8">
          <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-2">
            💡 오늘의 투자 인사이트
          </h3>
          <p className="text-gray-700 dark:text-gray-300 text-sm mb-4">
            포트폴리오의 기술주 비중이 높습니다. 안정적인 배당주를 추가해 리스크를 분산시켜보세요.
          </p>
          <button className="bg-white dark:bg-gray-700 px-4 py-2 rounded-lg text-sm font-medium text-gray-900 dark:text-white hover:shadow-md transition-shadow">
            추천 종목 보기
          </button>
        </div>

        {/* 학습 리소스 */}
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm">
            <h4 className="font-semibold text-gray-900 dark:text-white mb-2">
              📚 투자 기초
            </h4>
            <p className="text-xs text-gray-600 dark:text-gray-400 mb-3">
              주식 투자의 기본 개념을 배워보세요
            </p>
            <Link href="/learn" className="text-blue-600 dark:text-blue-400 text-sm font-medium">
              학습 시작 →
            </Link>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm">
            <h4 className="font-semibold text-gray-900 dark:text-white mb-2">
              📊 시장 동향
            </h4>
            <p className="text-xs text-gray-600 dark:text-gray-400 mb-3">
              최신 시장 뉴스와 분석 확인
            </p>
            <Link href="/news" className="text-blue-600 dark:text-blue-400 text-sm font-medium">
              뉴스 보기 →
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
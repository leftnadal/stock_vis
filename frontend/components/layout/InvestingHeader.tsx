'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Search, ChevronDown, User, Bell } from 'lucide-react';
import { useState } from 'react';

export default function InvestingHeader() {
  const pathname = usePathname();
  const [searchQuery, setSearchQuery] = useState('');

  const navItems = [
    { name: '시장', href: '/' },
    { name: '주식', href: '/stocks' },
    { name: '지수', href: '/indices' },
    { name: '암호화폐', href: '/crypto' },
    { name: '상품', href: '/commodities' },
    { name: '분석', href: '/analysis' },
    { name: '기술적 분석', href: '/technical' },
    { name: '경제 캘린더', href: '/calendar' },
  ];

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    console.log('Search:', searchQuery);
  };

  return (
    <header className="bg-[#1e2329] text-white">
      {/* Top Bar */}
      <div className="bg-[#131722] border-b border-gray-800">
        <div className="max-w-[1400px] mx-auto px-4">
          <div className="flex items-center justify-between h-10 text-xs">
            <div className="flex items-center space-x-6">
              <span className="text-gray-400">2025년 10월 25일</span>
              <div className="flex items-center space-x-4">
                <span className="text-gray-400">주요 지수:</span>
                <span>S&P 500 <span className="text-green-500">+0.82%</span></span>
                <span>나스닥 <span className="text-green-500">+1.24%</span></span>
                <span>다우존스 <span className="text-red-500">-0.15%</span></span>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <button className="text-gray-400 hover:text-white">한국어</button>
              <button className="text-gray-400 hover:text-white flex items-center">
                <User className="h-4 w-4 mr-1" />
                로그인
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Navigation */}
      <div className="max-w-[1400px] mx-auto px-4">
        <div className="flex items-center justify-between h-14">
          {/* Logo */}
          <div className="flex items-center">
            <Link href="/" className="flex items-center">
              <span className="text-2xl font-bold text-[#FFDD00]">Stock</span>
              <span className="text-2xl font-bold text-white">-Vis</span>
            </Link>
          </div>

          {/* Search Bar */}
          <div className="flex-1 max-w-xl mx-8">
            <form onSubmit={handleSearch} className="relative">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="종목, 지수, 상품 검색"
                className="w-full px-4 py-2 bg-[#2d3139] text-white placeholder-gray-400 rounded border border-gray-700 focus:outline-none focus:border-[#FFDD00] transition-colors"
              />
              <button
                type="submit"
                className="absolute right-2 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-[#FFDD00]"
              >
                <Search className="h-5 w-5" />
              </button>
            </form>
          </div>

          {/* Right Actions */}
          <div className="flex items-center space-x-4">
            <button className="relative p-2 hover:bg-[#2d3139] rounded transition-colors">
              <Bell className="h-5 w-5" />
              <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
            </button>
            <button className="px-4 py-2 bg-[#FFDD00] text-black font-semibold rounded hover:bg-yellow-400 transition-colors">
              무료 가입
            </button>
          </div>
        </div>
      </div>

      {/* Navigation Menu */}
      <nav className="bg-[#2d3139] border-t border-gray-700">
        <div className="max-w-[1400px] mx-auto px-4">
          <div className="flex items-center h-10">
            {navItems.map((item) => (
              <Link
                key={item.name}
                href={item.href}
                className={`px-4 py-2 text-sm font-medium hover:bg-[#363c46] transition-colors ${
                  pathname === item.href ? 'text-[#FFDD00]' : 'text-gray-300'
                }`}
              >
                {item.name}
              </Link>
            ))}
            <button className="ml-auto flex items-center px-3 py-1 text-sm text-gray-300 hover:text-white">
              더보기 <ChevronDown className="ml-1 h-4 w-4" />
            </button>
          </div>
        </div>
      </nav>
    </header>
  );
}
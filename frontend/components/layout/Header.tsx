'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { TrendingUp, Search, Menu } from 'lucide-react';
import { useState } from 'react';

export default function Header() {
  const pathname = usePathname();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    // TODO: 검색 기능 구현
    console.log('Search:', searchQuery);
  };

  return (
    <header className="bg-white dark:bg-gray-900 shadow-sm border-b border-gray-200 dark:border-gray-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <div className="flex items-center">
            <Link href="/" className="flex items-center space-x-2">
              <TrendingUp className="h-8 w-8 text-blue-600 dark:text-blue-400" />
              <span className="text-xl font-bold text-gray-900 dark:text-white">
                Stock-Vis
              </span>
            </Link>
          </div>

          {/* Navigation - Desktop */}
          <nav className="hidden md:flex space-x-8">
            <Link
              href="/"
              className={`text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 px-3 py-2 text-sm font-medium ${
                pathname === '/' ? 'text-blue-600 dark:text-blue-400' : ''
              }`}
            >
              대시보드
            </Link>
            <Link
              href="/stocks"
              className={`text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 px-3 py-2 text-sm font-medium ${
                pathname.startsWith('/stocks') ? 'text-blue-600 dark:text-blue-400' : ''
              }`}
            >
              주식 목록
            </Link>
            <Link
              href="/analysis"
              className={`text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 px-3 py-2 text-sm font-medium ${
                pathname.startsWith('/analysis') ? 'text-blue-600 dark:text-blue-400' : ''
              }`}
            >
              분석
            </Link>
          </nav>

          {/* Search Bar */}
          <div className="hidden md:block flex-1 max-w-md mx-8">
            <form onSubmit={handleSearch} className="relative">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="종목 검색 (예: AAPL, Microsoft)"
                className="w-full px-4 py-2 pl-10 pr-4 text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg focus:outline-none focus:border-blue-500"
              />
              <Search className="absolute left-3 top-2.5 h-5 w-5 text-gray-400" />
            </form>
          </div>

          {/* Mobile menu button */}
          <button
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            className="md:hidden inline-flex items-center justify-center p-2 rounded-md text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            <Menu className="h-6 w-6" />
          </button>
        </div>

        {/* Mobile Navigation */}
        {isMenuOpen && (
          <div className="md:hidden">
            <div className="px-2 pt-2 pb-3 space-y-1">
              <Link
                href="/"
                className="block px-3 py-2 rounded-md text-base font-medium text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                대시보드
              </Link>
              <Link
                href="/stocks"
                className="block px-3 py-2 rounded-md text-base font-medium text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                주식 목록
              </Link>
              <Link
                href="/analysis"
                className="block px-3 py-2 rounded-md text-base font-medium text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                분석
              </Link>
            </div>
            {/* Mobile Search */}
            <div className="px-2 pb-3">
              <form onSubmit={handleSearch}>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="종목 검색"
                  className="w-full px-4 py-2 text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg focus:outline-none focus:border-blue-500"
                />
              </form>
            </div>
          </div>
        )}
      </div>
    </header>
  );
}
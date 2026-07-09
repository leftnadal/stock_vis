'use client';

import { useEffect, useState } from 'react';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Search, TrendingUp } from 'lucide-react';

import { AvatarMenu } from '@/components/layout/AvatarMenu';
import { MySubNav, isMyPage } from '@/components/layout/MySubNav';

// 전역 내비 6칸 (MON-P3-S3): Dashboard · Market Pulse · Chain Sight · News · Screener · My.
// 포트폴리오·마이페이지는 top nav에서 제거 → My 서브탭·아바타로 이동.
const NAV_PUBLIC = [
  { href: '/', label: '대시보드', exact: true },
  { href: '/market-pulse', label: 'Market Pulse' },
  { href: '/chainsight', label: 'Chain Sight' },
  { href: '/news', label: '뉴스' },
  { href: '/screener', label: '스크리너' },
];

const MY_STORAGE_KEY = 'my:lastSubpage';

export default function Header() {
  const pathname = usePathname();
  const [searchQuery, setSearchQuery] = useState('');
  // M-3: My 슬롯은 마지막 방문 My 서브페이지로 연결(기억). 하이드레이션 안전 위해 기본값 후 useEffect.
  const [myHref, setMyHref] = useState('/watchlist');

  useEffect(() => {
    const saved = window.localStorage.getItem(MY_STORAGE_KEY);
    if (saved) setMyHref(saved);
  }, []);

  useEffect(() => {
    if (isMyPage(pathname)) {
      window.localStorage.setItem(MY_STORAGE_KEY, pathname);
      setMyHref(pathname);
    }
  }, [pathname]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    console.log('Search:', searchQuery);
  };

  const linkClass = (active: boolean) =>
    `px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 ${
      active ? 'text-blue-600 dark:text-blue-400' : ''
    }`;

  return (
    <header className="border-b border-gray-200 bg-white shadow-sm dark:border-gray-800 dark:bg-gray-900">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          <Link href="/" className="flex items-center space-x-2">
            <TrendingUp className="h-8 w-8 text-blue-600 dark:text-blue-400" />
            <span className="text-xl font-bold text-gray-900 dark:text-white">Stock-Vis</span>
          </Link>

          <nav className="hidden md:flex md:space-x-4">
            {NAV_PUBLIC.map((item) => {
              const active = item.exact
                ? pathname === item.href
                : pathname.startsWith(item.href);
              return (
                <Link key={item.href} href={item.href} className={linkClass(active)}>
                  {item.label}
                </Link>
              );
            })}
            {/* My = 마지막 서브페이지 직행 + 활성 표시 */}
            <Link href={myHref} className={linkClass(isMyPage(pathname))}>
              My
            </Link>
          </nav>

          <div className="mx-4 hidden max-w-md flex-1 md:block">
            <form onSubmit={handleSearch} className="relative">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="종목 검색 (예: AAPL, Microsoft)"
                className="w-full rounded-lg border border-gray-300 bg-gray-100 px-4 py-2 pl-10 text-gray-700 focus:border-blue-500 focus:outline-none dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300"
              />
              <Search className="absolute left-3 top-2.5 h-5 w-5 text-gray-400" />
            </form>
          </div>

          <div className="hidden md:block">
            <AvatarMenu />
          </div>
        </div>
      </div>

      {/* My 영역 서브탭 (M-3) — My 페이지에서만 표시 */}
      {isMyPage(pathname) && <MySubNav />}
    </header>
  );
}

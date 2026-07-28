'use client';

import { useEffect, useState } from 'react';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Activity, Home, Link2, Newspaper, User } from 'lucide-react';

import { isMyPage } from '@/components/layout/MySubNav';

const MY_STORAGE_KEY = 'my:lastSubpage';

export default function MobileNav() {
  const pathname = usePathname();
  const [myHref, setMyHref] = useState('/watchlist');

  useEffect(() => {
    const saved = window.localStorage.getItem(MY_STORAGE_KEY);
    if (saved) setMyHref(saved);
  }, []);

  // 6칸 체계 정합: 홈 · Market Pulse · Chain Sight · 뉴스 · My. (포트폴리오·내정보는 My/아바타로 이동)
  const navItems = [
    { name: '홈', href: '/', icon: Home, active: pathname === '/' },
    { name: 'Market Pulse', href: '/market-pulse', icon: Activity, active: pathname.startsWith('/market-pulse') },
    { name: 'Chain Sight', href: '/chainsight', icon: Link2, active: pathname.startsWith('/chainsight') },
    { name: '뉴스', href: '/news', icon: Newspaper, active: pathname.startsWith('/news') },
    { name: 'My', href: myHref, icon: User, active: isMyPage(pathname) },
  ];

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 border-t border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900 md:hidden">
      <nav className="flex h-16 items-center justify-around">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <Link
              key={item.name}
              href={item.href}
              aria-label={item.name}
              className={`flex min-h-[44px] flex-1 flex-col items-center justify-center py-2 transition-colors ${
                item.active
                  ? 'text-blue-600 dark:text-blue-400'
                  : 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white'
              }`}
            >
              <Icon className="mb-1 h-5 w-5" />
              <span className="text-xs">{item.name}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}

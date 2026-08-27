'use client';

import { useEffect, useState } from 'react';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Activity, HelpCircle, Home, Link2, Newspaper, User } from 'lucide-react';

import { isMyPage } from '@/components/layout/MySubNav';

const MY_STORAGE_KEY = 'my:lastSubpage';

export default function MobileNav() {
  const pathname = usePathname();
  const [myHref, setMyHref] = useState('/watchlist');

  useEffect(() => {
    const saved = window.localStorage.getItem(MY_STORAGE_KEY);
    if (saved) setMyHref(saved);
  }, []);

  // 홈 · Market Pulse · Chain Sight · 뉴스 · 가이드 · My. (포트폴리오·내정보는 My/아바타로 이동)
  const navItems = [
    { name: '홈', href: '/', icon: Home, active: pathname === '/' },
    // D-MP-V2-NAV(옵션 B, GUIDE-S1C): 목적지 v2 전환. active는 v1/v2 공통 prefix 유지(아래 주석 참조).
    { name: 'Market Pulse', href: '/market-pulse-v2', icon: Activity, active: pathname.startsWith('/market-pulse') },
    { name: 'Chain Sight', href: '/chainsight', icon: Link2, active: pathname.startsWith('/chainsight') },
    { name: '뉴스', href: '/news', icon: Newspaper, active: pathname.startsWith('/news') },
    { name: '가이드', href: '/guide', icon: HelpCircle, active: pathname.startsWith('/guide') },
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

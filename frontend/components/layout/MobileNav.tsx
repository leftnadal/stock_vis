'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Home, PieChart, Newspaper, TrendingUp, User } from 'lucide-react';

export default function MobileNav() {
  const pathname = usePathname();

  // audit P0 #12: '/profile' 깨진 라우트 → '/mypage' (실제 라우트와 일치).
  const navItems = [
    { name: '홈', href: '/', icon: Home },
    { name: '종목', href: '/stocks', icon: TrendingUp },
    { name: '뉴스', href: '/news', icon: Newspaper },
    { name: '포트폴리오', href: '/portfolio', icon: PieChart },
    { name: '내정보', href: '/mypage', icon: User },
  ];

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800 md:hidden z-50">
      {/* audit P0 #13: 터치 타겟 최소 44pt (HIG/Material 권장). h-16(64px) + min-h-[44px] 보장 */}
      <nav className="flex justify-around items-center h-16">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive =
            pathname === item.href ||
            (item.href !== '/' && pathname.startsWith(item.href));

          return (
            <Link
              key={item.name}
              href={item.href}
              aria-label={item.name}
              className={`flex flex-col items-center justify-center flex-1 min-h-[44px] py-2 transition-colors ${
                isActive
                  ? 'text-blue-600 dark:text-blue-400'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
              }`}
            >
              <Icon className="h-5 w-5 mb-1" />
              <span className="text-xs">{item.name}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
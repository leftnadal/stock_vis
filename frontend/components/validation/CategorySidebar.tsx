'use client';

import { useEffect, useState } from 'react';
import type { CategoryMetrics } from '@/types/validation';

const SIGNAL_DOT: Record<string, string> = {
  green: 'bg-green-500',
  yellow: 'bg-yellow-400',
  red: 'bg-red-500',
  gray: 'bg-gray-300 dark:bg-gray-600',
};

interface Props {
  categories: CategoryMetrics[];
  activeCategory: string;
}

export default function CategorySidebar({ categories, activeCategory }: Props) {
  const [current, setCurrent] = useState(activeCategory);

  // IntersectionObserver로 스크롤 위치 추적
  useEffect(() => {
    const observers: IntersectionObserver[] = [];
    categories.forEach((cat) => {
      const el = document.getElementById(`cat-${cat.category}`);
      if (!el) return;
      const obs = new IntersectionObserver(
        ([entry]) => {
          if (entry.isIntersecting) setCurrent(cat.category);
        },
        { rootMargin: '-100px 0px -60% 0px', threshold: 0 }
      );
      obs.observe(el);
      observers.push(obs);
    });
    return () => observers.forEach((o) => o.disconnect());
  }, [categories]);

  const handleClick = (category: string) => {
    const el = document.getElementById(`cat-${category}`);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  return (
    <nav className="sticky top-24 space-y-1">
      <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase mb-2">카테고리</h4>
      {categories.map((cat) => (
        <button
          key={cat.category}
          onClick={() => handleClick(cat.category)}
          className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-left text-sm transition-colors ${
            current === cat.category
              ? 'bg-blue-50 text-blue-700 font-semibold dark:bg-blue-900/30 dark:text-blue-400'
              : 'text-gray-600 hover:bg-gray-50 dark:text-gray-400 dark:hover:bg-gray-700/50'
          }`}
        >
          <div className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${SIGNAL_DOT[cat.signal]}`} />
          <span className="flex-1 truncate">{cat.display_name}</span>
          <span className="text-xs text-gray-400">{cat.metrics.length}</span>
        </button>
      ))}
    </nav>
  );
}

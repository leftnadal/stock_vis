'use client';

import { useState, useRef, useEffect } from 'react';
import { HelpCircle } from 'lucide-react';
import { METRIC_DESCRIPTIONS } from '@/constants/metricDescriptions';

interface Props {
  metricCode: string;
}

export default function MetricInfoTooltip({ metricCode }: Props) {
  const desc = METRIC_DESCRIPTIONS[metricCode];
  if (!desc) return null;

  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // 외부 클릭 시 닫기 (모바일 터치 대응)
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent | TouchEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    document.addEventListener('touchstart', handler);
    return () => {
      document.removeEventListener('mousedown', handler);
      document.removeEventListener('touchstart', handler);
    };
  }, [open]);

  return (
    <div className="relative inline-flex" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
        aria-label="지표 설명"
      >
        <HelpCircle className="w-3.5 h-3.5" />
      </button>

      {open && (
        <div className="absolute z-20 left-1/2 -translate-x-1/2 top-6 w-64 bg-white dark:bg-gray-800 shadow-xl rounded-lg border border-gray-200 dark:border-gray-700 p-3 text-xs">
          {/* 초급 설명 (항상) */}
          <p className="text-gray-700 dark:text-gray-300 leading-relaxed">
            {desc.basic}
          </p>
          {/* 중급 설명 (있으면) */}
          {desc.detail && (
            <p className="mt-2 pt-2 border-t border-gray-100 dark:border-gray-700 text-gray-500 dark:text-gray-400 leading-relaxed">
              {desc.detail}
            </p>
          )}
          {/* 화살표 */}
          <div className="absolute -top-1.5 left-1/2 -translate-x-1/2 w-3 h-3 bg-white dark:bg-gray-800 border-l border-t border-gray-200 dark:border-gray-700 rotate-45" />
        </div>
      )}
    </div>
  );
}

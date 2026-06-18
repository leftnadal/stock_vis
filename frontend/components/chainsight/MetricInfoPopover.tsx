'use client';

import { useEffect, useRef, useState } from 'react';
import { HelpCircle } from 'lucide-react';
import { METRIC_INFO, type MetricKey } from '@/constants/eventThemes';

interface Props {
  metricKey: MetricKey;
}

/**
 * 지표 설명 팝오버 (CS-M2-DISPLAY S2). 문구는 METRIC_INFO 단일 출처에서 끌어온다.
 * - 트리거: 물음표 아이콘 버튼
 * - 데스크탑: hover로 열림(onMouseEnter/Leave)
 * - 모바일: hover 의존 금지 → 클릭으로 열림 보장 + 바깥 클릭 시 닫힘
 */
export default function MetricInfoPopover({ metricKey }: Props) {
  const info = METRIC_INFO[metricKey];
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // 바깥 클릭 시 닫힘 (모바일에서 클릭으로 연 경우)
  useEffect(() => {
    if (!isOpen) return;
    function onDocClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, [isOpen]);

  return (
    <span
      ref={containerRef}
      className="relative inline-flex"
      onMouseEnter={() => setIsOpen(true)}
      onMouseLeave={() => setIsOpen(false)}
    >
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        aria-label={`${info.label} 설명`}
        aria-expanded={isOpen}
        className="inline-flex items-center text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300"
      >
        <HelpCircle size={14} aria-hidden="true" />
      </button>

      {isOpen && (
        <div
          role="tooltip"
          className="absolute left-1/2 top-full z-20 mt-1.5 w-64 -translate-x-1/2 rounded-lg border border-gray-200 bg-white p-3 text-left shadow-lg dark:border-gray-700 dark:bg-gray-900"
        >
          <div className="text-sm font-semibold text-gray-900 dark:text-gray-100">
            {info.label}
          </div>
          <p className="mt-1 text-xs leading-relaxed text-gray-600 dark:text-gray-300">
            {info.description}
          </p>
          <div className="my-2 border-t border-gray-100 dark:border-gray-800" />
          <p className="text-xs text-gray-500 dark:text-gray-400">{info.example}</p>
          <p className="mt-0.5 text-xs text-gray-400 dark:text-gray-500">{info.range}</p>
        </div>
      )}
    </span>
  );
}

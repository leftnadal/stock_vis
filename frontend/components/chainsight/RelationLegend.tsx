'use client';

/**
 * 관계 범례 — §5-3 캔버스 내 좌하단 고정 absolute overlay
 *
 * - 반투명 배경 (white/85 라이트 / gray-900/85 다크) + backdrop-blur
 * - 6종 관계 색상·선 스타일 표시 (§6-1 일치)
 * - 작은 화살표로 접기/펼치기 (모바일 기본 접힘)
 */

import { useState, useEffect } from 'react';
import { RELATION_STYLES } from './graphStyles';

// §6-1 명세 기준 6종 (PRICE_CORRELATED 포함)
const LEGEND_ITEMS = [
  { key: 'SUPPLIES_TO'      },
  { key: 'COMPETES_WITH'    },
  { key: 'PEER_OF'          },
  { key: 'CO_MENTIONED'     },
  { key: 'HAS_THEME'        },
  { key: 'PRICE_CORRELATED' },
];

// PRICE_CORRELATED는 graphStyles에 없으므로 fallback 정의
const EXTRA_STYLES: Record<string, { color: string; label: string; width: number; dash?: number[] }> = {
  PRICE_CORRELATED: { color: '#9CA3AF', label: '가격상관', width: 1, dash: [3, 3] },
};

function getStyle(key: string) {
  return RELATION_STYLES[key] ?? EXTRA_STYLES[key];
}

export default function RelationLegend() {
  // 모바일 기본 접힘 — window 접근은 useEffect 이후
  const [collapsed, setCollapsed] = useState(true);

  useEffect(() => {
    // 초기 렌더 후 뷰포트 너비 기반으로 초기 상태 결정
    const isMobile = window.matchMedia('(max-width: 767px)').matches;
    setCollapsed(isMobile);
  }, []);

  return (
    <div
      className={[
        'absolute bottom-3 left-3 z-10',
        'rounded-lg px-2.5 py-2',
        'bg-white/85 dark:bg-gray-900/85 backdrop-blur-sm',
        'border border-gray-200/70 dark:border-gray-700/70',
        'shadow-sm',
        'max-w-[140px]',
        'transition-all duration-150',
      ].join(' ')}
    >
      {/* 헤더: 범례 + 접기 토글 */}
      <button
        type="button"
        onClick={() => setCollapsed((c) => !c)}
        className="flex items-center justify-between w-full gap-1 text-[10px] font-semibold text-gray-500 dark:text-gray-400 select-none"
        aria-label={collapsed ? '범례 펼치기' : '범례 접기'}
      >
        <span>범례</span>
        <span
          className={[
            'transition-transform duration-150',
            collapsed ? '' : 'rotate-180',
          ].join(' ')}
          aria-hidden
        >
          ▲
        </span>
      </button>

      {/* 범례 항목 목록 */}
      {!collapsed && (
        <ul className="mt-1.5 space-y-1">
          {LEGEND_ITEMS.map(({ key }) => {
            const style = getStyle(key);
            if (!style) return null;
            return (
              <li key={key} className="flex items-center gap-1.5">
                {/* 색상 라인 샘플 24px */}
                <svg width="24" height="8" aria-hidden>
                  <line
                    x1="0"
                    y1="4"
                    x2="24"
                    y2="4"
                    stroke={style.color}
                    strokeWidth={Math.min(style.width, 2.5)}
                    strokeDasharray={style.dash ? style.dash.join(',') : undefined}
                  />
                </svg>
                <span className="text-[11px] text-gray-700 dark:text-gray-300 whitespace-nowrap">
                  {style.label}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

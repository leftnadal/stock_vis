'use client';

/**
 * 관계 타입 범례 패널
 */

import { RELATION_STYLES } from './graphStyles';

const LEGEND_ITEMS = [
  { key: 'SUPPLIES_TO',   show: true },
  { key: 'CUSTOMER_OF',   show: true },
  { key: 'COMPETES_WITH', show: true },
  { key: 'PEER_OF',       show: true },
  { key: 'CO_MENTIONED',  show: true },
  { key: 'HAS_THEME',     show: true },
];

export default function RelationLegend() {
  return (
    <div className="flex flex-wrap gap-3 text-xs text-gray-600">
      {LEGEND_ITEMS.map(({ key }) => {
        const style = RELATION_STYLES[key];
        if (!style) return null;
        return (
          <div key={key} className="flex items-center gap-1.5">
            <svg width="24" height="8">
              <line
                x1="0" y1="4" x2="24" y2="4"
                stroke={style.color}
                strokeWidth={Math.min(style.width, 3)}
                strokeDasharray={style.dash ? style.dash.join(',') : 'none'}
              />
            </svg>
            <span>{style.label}</span>
          </div>
        );
      })}
    </div>
  );
}

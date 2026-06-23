'use client';

import { useEffect, useRef, useState } from 'react';

// §3-3 관계 타입 → 한국어 라벨 (§RelationCardPanel.tsx RELATION_TEMPLATES 차용)
const RELATION_LABELS: Record<string, string> = {
  SUPPLIES_TO:      '공급망 상류 연결',
  CUSTOMER_OF:      '공급망 하류 연결',
  COMPETES_WITH:    '직접 경쟁',
  PEER_OF:          'Peer (동종 비교)',
  CO_MENTIONED:     '동시출현',
  HAS_THEME:        '그룹 공유',
  PRICE_CORRELATED: '가격 상관',
  RELATED_TO:       '관련 종목',
};

// §3-2 시드 사유 → 한국어 라벨 (§RelationCardPanel.tsx REASON_LABELS 차용)
const REASON_LABELS: Record<string, string> = {
  price_top5:        '수익률 상위 이상치',
  price_bottom5:     '수익률 하위 이상치',
  volume_surge:      '거래량 급증',
  sector_outlier:    '섹터 이상치',
  relation_upgrade:  '관계 상향',
  relation_downgrade:'관계 하향',
  relation_new:      '신규 관계 발견',
  comention_surge:   '동시출현 급증',
};

// §3-2 섹터 색상 점 — seed_type에서 간이 색상 유추
const SEED_TYPE_COLORS: Record<string, string> = {
  price:     '#E24B4A',
  volume:    '#1D9E75',
  relation:  '#378ADD',
  comention: '#9333EA',
};

export interface TooltipNodeInfo {
  symbol: string;
  name: string;
  sector?: string;
  seedReasons?: string[];  // seed_reasons
  relType?: string;        // center와의 관계 타입 (섹터 그래프 시 없음)
  seedType?: string | null;
}

interface NodeTooltipProps {
  node: TooltipNodeInfo | null;
  /** 캔버스 내 픽셀 좌표 (canvas-relative) */
  canvasX: number;
  canvasY: number;
  /** 캔버스 컨테이너의 DOMRect */
  containerRect: DOMRect | null;
  visible: boolean;
}

/**
 * §3-3 노드 호버 툴팁
 *
 * - 위치: 노드 우측 12px offset
 * - 등장: 150ms fade-in, 사라짐: 즉시 (visible prop 제어)
 * - 화면 경계 감지: 우/하단 경계 초과 시 좌/상단으로 반전
 */
export default function NodeTooltip({
  node,
  canvasX,
  canvasY,
  containerRect,
  visible,
}: NodeTooltipProps) {
  const tooltipRef = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState({ left: 0, top: 0 });
  const [side, setSide] = useState<{ right: boolean; bottom: boolean }>({
    right: true,
    bottom: false,
  });

  // 위치 계산 — 캔버스 상대 좌표를 컨테이너 내 절대 위치로 변환
  useEffect(() => {
    if (!visible || !containerRect || !tooltipRef.current) return;

    const tooltipEl = tooltipRef.current;
    const tooltipW = tooltipEl.offsetWidth || 200;
    const tooltipH = tooltipEl.offsetHeight || 120;

    const OFFSET = 12;
    const containerW = containerRect.width;
    const containerH = containerRect.height;

    // 기본: 노드 우상단
    let left = canvasX + OFFSET;
    let top = canvasY - tooltipH / 2;

    // 우측 경계 초과 → 좌측으로 반전
    const flipRight = left + tooltipW > containerW - 8;
    if (flipRight) {
      left = canvasX - OFFSET - tooltipW;
    }

    // 하단 경계 초과 → 상단으로 반전
    const flipBottom = top + tooltipH > containerH - 8;
    if (flipBottom) {
      top = canvasY - tooltipH + OFFSET;
    }

    // 최소 top 보정
    if (top < 4) top = 4;
    if (left < 4) left = 4;

    setPosition({ left, top });
    setSide({ right: !flipRight, bottom: flipBottom });
  }, [visible, canvasX, canvasY, containerRect, node]);

  if (!node) return null;

  const seedReasons = node.seedReasons ?? [];
  const dotColor = node.seedType ? (SEED_TYPE_COLORS[node.seedType] ?? '#9CA3AF') : '#9CA3AF';

  return (
    <div
      ref={tooltipRef}
      role="tooltip"
      aria-hidden={!visible}
      style={{
        position: 'absolute',
        left: position.left,
        top: position.top,
        zIndex: 50,
        opacity: visible ? 1 : 0,
        pointerEvents: 'none',
        transition: visible ? 'opacity 150ms ease-in' : 'opacity 0ms',
        minWidth: 160,
        maxWidth: 220,
      }}
      className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg shadow-lg px-3 py-2.5 text-left"
    >
      {/* 종목 라인: 심볼 + 회사명 */}
      <div className="flex items-baseline gap-1.5 mb-1">
        <span className="font-bold text-sm text-gray-900 dark:text-gray-100">
          {node.symbol}
        </span>
        <span className="text-xs text-gray-500 dark:text-gray-400 truncate max-w-[130px]">
          {node.name}
        </span>
      </div>

      {/* 섹터 라벨 + 색상 점 */}
      {node.sector && (
        <div className="flex items-center gap-1 mb-1">
          <span
            className="inline-block w-2 h-2 rounded-full flex-shrink-0"
            style={{ backgroundColor: dotColor }}
          />
          <span className="text-xs text-gray-500 dark:text-gray-400">{node.sector}</span>
        </div>
      )}

      {/* 시드 사유 (있을 때만) */}
      {seedReasons.length > 0 && (
        <div className="mb-1">
          <span className="text-xs text-amber-600 dark:text-amber-400">
            {seedReasons.map((r) => REASON_LABELS[r] ?? r).join(', ')}
          </span>
        </div>
      )}

      {/* 관계 라벨 (center가 있을 때만) */}
      {node.relType && (
        <div className="mt-1 pt-1 border-t border-gray-100 dark:border-gray-700">
          <span className="text-xs text-blue-600 dark:text-blue-400">
            {RELATION_LABELS[node.relType] ?? node.relType}
          </span>
        </div>
      )}
    </div>
  );
}

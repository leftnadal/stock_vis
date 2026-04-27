'use client';

import { useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';

export interface ContextMenuNodeInfo {
  symbol: string;
  name: string;
}

interface NodeContextMenuProps {
  node: ContextMenuNodeInfo | null;
  /** 캔버스 내 픽셀 좌표 (canvas-relative) */
  x: number;
  y: number;
  /** 캔버스 컨테이너의 DOMRect */
  containerRect: DOMRect | null;
  visible: boolean;
  onClose: () => void;
  /** "여기서 탐색" 클릭 → center 전환 */
  onExplore: (symbol: string) => void;
}

/**
 * §3-3 우클릭 / 롱프레스 컨텍스트 메뉴
 *
 * 메뉴 항목:
 *  1. 여기서 탐색 시작  (= center 전환)
 *  2. 가설 생성 →       (/thesis/new?symbol=…&from=chainsight)
 *  3. Watchlist 추가    (향후 PR 연기 — 현재는 비활성 표시)
 *  4. 전용 화면에서 보기 (Deep Dive → /chainsight/{symbol})
 *
 * 닫기: ESC 키 또는 외부 클릭
 * 화면 경계 처리: 우/하단 초과 시 좌/상단으로 반전
 */
export default function NodeContextMenu({
  node,
  x,
  y,
  containerRect,
  visible,
  onClose,
  onExplore,
}: NodeContextMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  // ESC 키로 닫기
  useEffect(() => {
    if (!visible) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [visible, onClose]);

  // 외부 클릭으로 닫기
  useEffect(() => {
    if (!visible) return;
    const handlePointerDown = (e: PointerEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    // 약간의 지연을 두어 트리거 이벤트와 충돌 방지
    const timer = setTimeout(() => {
      window.addEventListener('pointerdown', handlePointerDown);
    }, 50);
    return () => {
      clearTimeout(timer);
      window.removeEventListener('pointerdown', handlePointerDown);
    };
  }, [visible, onClose]);

  if (!visible || !node) return null;

  // 화면 경계 계산
  const MENU_W = 200;
  const MENU_H = 160;
  const OFFSET = 12;
  const containerW = containerRect?.width ?? 800;
  const containerH = containerRect?.height ?? 560;

  let left = x + OFFSET;
  let top = y + OFFSET;

  if (left + MENU_W > containerW - 8) left = x - MENU_W - OFFSET;
  if (top + MENU_H > containerH - 8) top = y - MENU_H - OFFSET;
  if (left < 4) left = 4;
  if (top < 4) top = 4;

  const handleExplore = () => {
    onExplore(node.symbol);
    onClose();
  };

  const handleDeepDive = () => {
    router.push(`/chainsight/${node.symbol}`);
    onClose();
  };

  const handleThesis = () => {
    router.push(`/thesis/new?symbol=${node.symbol}&from=chainsight`);
    onClose();
  };

  return (
    <div
      ref={menuRef}
      role="menu"
      aria-label={`${node.symbol} 컨텍스트 메뉴`}
      style={{
        position: 'absolute',
        left,
        top,
        zIndex: 60,
        minWidth: MENU_W,
      }}
      className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg shadow-xl overflow-hidden"
    >
      {/* 메뉴 헤더: 심볼 */}
      <div className="px-3 py-2 bg-gray-50 dark:bg-gray-750 border-b border-gray-200 dark:border-gray-600">
        <span className="font-semibold text-sm text-gray-900 dark:text-gray-100">
          {node.symbol}
        </span>
        {node.name && (
          <span className="ml-1.5 text-xs text-gray-500 dark:text-gray-400 truncate">
            {node.name.length > 18 ? node.name.slice(0, 18) + '…' : node.name}
          </span>
        )}
      </div>

      {/* 메뉴 항목 */}
      <div className="py-1">
        {/* 1. 여기서 탐색 시작 */}
        <button
          role="menuitem"
          onClick={handleExplore}
          className="w-full text-left px-3 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-blue-50 dark:hover:bg-blue-900/20 hover:text-blue-700 dark:hover:text-blue-300 transition-colors flex items-center gap-2"
        >
          <span className="text-blue-500">◎</span>
          여기서 탐색 시작
        </button>

        {/* 2. 가설 생성 */}
        <button
          role="menuitem"
          onClick={handleThesis}
          className="w-full text-left px-3 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors flex items-center gap-2"
        >
          <span className="text-gray-400">✎</span>
          가설 생성 →
        </button>

        {/* 3. Watchlist 추가 (향후 PR — 현재 비활성) */}
        <button
          role="menuitem"
          disabled
          title="Watch 기능은 준비 중입니다"
          className="w-full text-left px-3 py-2 text-sm text-gray-400 dark:text-gray-600 cursor-not-allowed flex items-center gap-2"
        >
          <span>☆</span>
          Watchlist 추가
        </button>

        <div className="my-1 border-t border-gray-100 dark:border-gray-700" />

        {/* 4. Deep Dive */}
        <button
          role="menuitem"
          onClick={handleDeepDive}
          className="w-full text-left px-3 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors flex items-center gap-2"
        >
          <span className="text-gray-400">⤴</span>
          전용 화면에서 보기 (Deep) →
        </button>
      </div>
    </div>
  );
}

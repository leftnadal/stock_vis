'use client';

import { useEffect, useRef, type ReactNode } from 'react';
import { X } from 'lucide-react';

// 정직성 한 줄(고정·D-SCANNER-SELECT-UX). 매매 암시 금지.
const HONESTY_LINE = '신호는 주목 후보를 고르는 렌즈이며 수익을 보장하지 않습니다.';

interface DetailSheetShellProps {
  onClose: () => void;
  /** 헤더 상단 3px 강조선 색. 없으면 강조선 생략. */
  accentColor?: string;
  /** 헤더 좌측 내용(닫기 버튼은 셸이 그린다). */
  header: ReactNode;
  /**
   * 하단 축 커버리지 줄 내용. 시트마다 실제로 보여주는 축이 다르므로 **반드시 소비처가 준다**
   * (하드코딩하면 둘 중 한 시트는 거짓 커버리지를 말하게 된다 — DASH-RECO S1).
   */
  coverage: ReactNode;
  children: ReactNode;
}

/**
 * 상세 시트 공용 껍데기 (DASH-RECO S1 — SignalDetailSheet에서 추출).
 * 오버레이 · 우측 슬라이드 패널(모바일 하단 시트) · 헤더+닫기 · ESC · body scroll lock · 하단 커버리지/정직성 줄.
 * 내용(필터·리스트·관점 등)은 children으로 받는다 — 셸은 내용 상태를 모른다.
 */
export function DetailSheetShell({
  onClose,
  accentColor,
  header,
  coverage,
  children,
}: DetailSheetShellProps) {
  const sheetRef = useRef<HTMLDivElement>(null);

  // ESC 키 닫기
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  // body scroll lock
  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = ''; };
  }, []);

  // 오버레이 클릭 닫기
  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) onClose();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex flex-col justify-end md:justify-center md:items-end bg-black/50 backdrop-blur-sm"
      onClick={handleOverlayClick}
    >
      {/* 시트 패널 */}
      <div
        ref={sheetRef}
        className="
          w-full md:w-[420px] md:h-full
          bg-white dark:bg-gray-900
          rounded-t-2xl md:rounded-none
          shadow-2xl flex flex-col
          max-h-[90vh] md:max-h-full
          animate-slide-up md:animate-slide-right
        "
        onClick={(e) => e.stopPropagation()}
      >
        {/* 모바일 드래그 핸들 */}
        <div className="flex justify-center pt-2 pb-1 md:hidden">
          <div className="w-10 h-1 bg-gray-300 dark:bg-gray-600 rounded-full" />
        </div>

        {/* 헤더 */}
        <div
          className="flex items-start justify-between px-5 pt-5 pb-4 border-b border-gray-200 dark:border-gray-700 flex-shrink-0"
          style={accentColor ? { borderTop: `3px solid ${accentColor}` } : undefined}
        >
          <div className="flex-1 min-w-0">{header}</div>
          <button
            onClick={onClose}
            className="ml-3 p-1.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors flex-shrink-0"
          >
            <X className="w-4 h-4 text-gray-500 dark:text-gray-400" />
          </button>
        </div>

        {children}

        {/* 축 커버리지 명시(정칙 ⑴ 정보판) + 정직성 한 줄(고정) */}
        <div className="px-5 py-2.5 border-t border-gray-100 dark:border-gray-700 flex-shrink-0 bg-gray-50/70 dark:bg-gray-800/50">
          <p className="text-[10px] text-gray-500 dark:text-gray-400 leading-relaxed">{coverage}</p>
          <p className="mt-1 text-[10px] italic text-gray-400 dark:text-gray-500">{HONESTY_LINE}</p>
        </div>
      </div>
    </div>
  );
}

'use client';

import React, { forwardRef } from 'react';
import { X } from 'lucide-react';
import { createPortal } from 'react-dom';

// 구조화된 프리셋 설명 타입
export interface PresetExplanation {
  indicators: string;    // 사용 지표
  reason: string;        // 지표 선택 이유
  meaning: string;       // 투자 의미
  caution: string;       // 주의사항
}

interface PresetDetailPopoverProps {
  title: string;
  explanation: PresetExplanation;
  isOpen: boolean;
  onClose: () => void;
  style?: React.CSSProperties;
  isMobile?: boolean;
}

const PresetDetailPopover = forwardRef<HTMLDivElement, PresetDetailPopoverProps>(
  function PresetDetailPopover(
    { title, explanation, isOpen, onClose, style, isMobile = false },
    ref
  ) {
    if (!isOpen) return null;

    // Mobile: Bottom Sheet
    if (isMobile) {
      return createPortal(
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/50 z-[9998] animate-fadeIn"
            onClick={onClose}
          />
          {/* Bottom Sheet */}
          <div
            ref={ref}
            className="fixed bottom-0 left-0 right-0 z-[9999] bg-[#21262D] border-t border-[#30363D] rounded-t-2xl max-h-[80vh] overflow-y-auto animate-slideUp"
          >
            {/* Drag Handle */}
            <div className="flex justify-center pt-2 pb-1">
              <div className="w-10 h-1 bg-[#484F58] rounded-full" />
            </div>

            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-[#30363D]">
              <h3 className="text-base font-semibold text-[#E6EDF3]">{title}</h3>
              <button
                onClick={onClose}
                className="p-1 text-[#8B949E] hover:text-[#E6EDF3] transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Content */}
            <div className="p-4 space-y-4">
              <Section title="사용 지표" content={explanation.indicators} />
              <Section title="지표 선택 이유" content={explanation.reason} />
              <Section title="투자 의미" content={explanation.meaning} />
              <Section title="주의사항" content={explanation.caution} highlight />
            </div>
          </div>
        </>,
        document.body
      );
    }

    // Desktop: Floating Popover
    return createPortal(
      <div
        ref={ref}
        style={style}
        className="z-[9999] w-80 bg-[#21262D] border border-[#30363D] rounded-lg shadow-lg shadow-black/30 animate-fadeIn"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-3 py-2.5 border-b border-[#30363D]">
          <h3 className="text-sm font-semibold text-[#E6EDF3]">{title}</h3>
          <button
            onClick={onClose}
            className="p-0.5 text-[#8B949E] hover:text-[#E6EDF3] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-3 space-y-3 max-h-[400px] overflow-y-auto">
          <Section title="사용 지표" content={explanation.indicators} compact />
          <Section title="지표 선택 이유" content={explanation.reason} compact />
          <Section title="투자 의미" content={explanation.meaning} compact />
          <Section title="주의사항" content={explanation.caution} highlight compact />
        </div>
      </div>,
      document.body
    );
  }
);

// Section component
function Section({
  title,
  content,
  highlight = false,
  compact = false,
}: {
  title: string;
  content: string;
  highlight?: boolean;
  compact?: boolean;
}) {
  return (
    <div>
      <h4
        className={`font-medium mb-1 ${
          compact ? 'text-[11px]' : 'text-xs'
        } ${highlight ? 'text-[#D29922]' : 'text-[#8B949E]'}`}
      >
        {title}
      </h4>
      <p
        className={`text-[#C9D1D9] leading-relaxed ${
          compact ? 'text-[12px]' : 'text-[13px]'
        }`}
      >
        {content}
      </p>
    </div>
  );
}

export default PresetDetailPopover;

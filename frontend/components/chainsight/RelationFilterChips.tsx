'use client';

/**
 * § 2. 관계 토글 칩 바
 *
 * 6종 관계 타입을 독립 ON/OFF 토글 칩으로 표시.
 * 명세 §2-2 기본 상태:
 *   ON  — 공급망(SUPPLIES_TO+CUSTOMER_OF), 경쟁(COMPETES_WITH), Peer(PEER_OF), 뉴스(CO_MENTIONED)
 *   OFF — 가격상관(PRICE_CORRELATED), 그룹(HAS_THEME)
 *
 * §2-3 시각: 색상 점/라인 + 레이블, ON/OFF 배경·외곽선 차이
 * §2-4 인터랙션: 다중 선택, 모두 끄면 "구조 보기" 모드, 전체 켜기/끄기
 * §2-5 모바일: 가로 스크롤 + 우측 페이드아웃 그라디언트
 */

import { useExplorationStore } from '@/lib/stores/explorationStore';
import type { RelationType } from '@/types/chainsight';

// ── 칩 정의 (§ 2-2) ──

interface ChipDef {
  label: string;
  relTypes: RelationType[];   // 이 칩이 대표하는 관계 타입 목록
  color: string;              // ON 상태 색상
  dashHint: 'solid-thick' | 'solid-normal' | 'dashed' | 'long-dash';
}

const CHIP_DEFS: ChipDef[] = [
  {
    label: '공급망',
    relTypes: ['SUPPLIES_TO', 'CUSTOMER_OF'],
    color: '#F97316',
    dashHint: 'solid-thick',
  },
  {
    label: '경쟁',
    relTypes: ['COMPETES_WITH'],
    color: '#EF4444',
    dashHint: 'solid-normal',
  },
  {
    label: 'Peer',
    relTypes: ['PEER_OF'],
    color: '#3B82F6',
    dashHint: 'solid-normal',
  },
  {
    label: '뉴스',
    relTypes: ['CO_MENTIONED'],
    color: '#A855F7',
    dashHint: 'dashed',
  },
  {
    label: '가격상관',
    relTypes: ['PRICE_CORRELATED'],
    color: '#9CA3AF',
    dashHint: 'dashed',
  },
  {
    label: '그룹',
    relTypes: ['HAS_THEME'],
    color: '#14B8A6',
    dashHint: 'long-dash',
  },
];

// ── 라인 샘플 SVG (§ 2-3 좌측 색상 점/라인 표시) ──

interface LineSampleProps {
  color: string;
  dashHint: ChipDef['dashHint'];
  isOn: boolean;
}

function LineSample({ color, dashHint, isOn }: LineSampleProps) {
  const strokeColor = isOn ? color : '#9CA3AF';
  const strokeWidth = dashHint === 'solid-thick' ? 3 : dashHint === 'solid-normal' ? 2 : 1.5;
  const dashArray =
    dashHint === 'dashed'
      ? '3,3'
      : dashHint === 'long-dash'
      ? '5,3'
      : undefined;

  return (
    <svg
      width="16"
      height="10"
      viewBox="0 0 16 10"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      style={{ flexShrink: 0 }}
    >
      <line
        x1="0"
        y1="5"
        x2="16"
        y2="5"
        stroke={strokeColor}
        strokeWidth={strokeWidth}
        strokeDasharray={dashArray}
        strokeLinecap="round"
      />
    </svg>
  );
}

// ── 단일 칩 컴포넌트 ──

interface ChipProps {
  chip: ChipDef;
  isOn: boolean;
  disabled?: boolean;
  onToggle: () => void;
}

function RelationChip({ chip, isOn, disabled, onToggle }: ChipProps) {
  const { color, label, dashHint } = chip;

  // ON 배경: 해당 색상 10% 불투명도 (hex → rgba 변환 없이 직접 계산)
  // OFF 배경: #F3F4F6 (라이트)
  const bgStyle: React.CSSProperties = isOn
    ? {
        backgroundColor: `${color}1A`, // 10% opacity (hex: 1A ≈ 10%)
        borderColor: `${color}B3`,      // 70% opacity (hex: B3 ≈ 70%)
        color: color,
      }
    : {
        backgroundColor: '#F3F4F6',
        borderColor: '#D1D5DB',
        color: '#6B7280',
      };

  return (
    <button
      type="button"
      onClick={disabled ? undefined : onToggle}
      disabled={disabled}
      title={
        disabled
          ? '섹터를 선택하면 관계 필터를 사용할 수 있습니다'
          : isOn
          ? `${label} 관계 끄기`
          : `${label} 관계 켜기`
      }
      style={bgStyle}
      className={[
        // § 2-3: height 32px, padding 8px 12px, border-radius 16px (pill), font 12px medium
        'inline-flex items-center gap-1.5 h-8 px-3 py-0',
        'rounded-full border text-xs font-medium',
        'whitespace-nowrap select-none transition-all duration-100',
        disabled
          ? 'opacity-40 cursor-not-allowed'
          : 'cursor-pointer hover:opacity-80 active:scale-95',
      ]
        .filter(Boolean)
        .join(' ')}
    >
      {/* 좌측: 엣지 색상 라인 샘플 (ON일 때만 표시) — §2-3 */}
      {isOn && <LineSample color={color} dashHint={dashHint} isOn={isOn} />}

      {/* 레이블 */}
      <span>{label}</span>

      {/* 우측 아이콘: ON=× 끄기, OFF=+ 켜기 — §2-3 */}
      <span className="text-base leading-none" aria-hidden="true">
        {isOn ? '×' : '+'}
      </span>
    </button>
  );
}

// ── 메인 컴포넌트 ──

interface RelationFilterChipsProps {
  /** 섹터 미선택 시 true — 칩은 보이되 비활성(§2-1) */
  disabled?: boolean;
}

export default function RelationFilterChips({ disabled = false }: RelationFilterChipsProps) {
  const { enabledRelTypes, toggleRelType, enableAllRelTypes, disableAllRelTypes } =
    useExplorationStore();

  /**
   * 칩이 ON인지 판단: 칩의 relTypes 중 하나라도 enabledRelTypes에 있으면 ON.
   * 공급망 칩은 SUPPLIES_TO + CUSTOMER_OF 두 타입 묶음 — 하나라도 ON이면 ON으로 취급.
   */
  function isChipOn(chip: ChipDef): boolean {
    return chip.relTypes.some((rt) => enabledRelTypes.has(rt));
  }

  /**
   * 칩 토글: ON→OFF는 relTypes 전부 제거, OFF→ON은 relTypes 전부 추가.
   * 공급망 칩은 SUPPLIES_TO와 CUSTOMER_OF를 항상 같이 켜고 끈다.
   */
  function handleToggle(chip: ChipDef) {
    const currentlyOn = isChipOn(chip);
    if (currentlyOn) {
      // OFF로 전환: 해당 타입 모두 제거
      chip.relTypes.forEach((rt) => {
        if (enabledRelTypes.has(rt)) toggleRelType(rt);
      });
    } else {
      // ON으로 전환: 해당 타입 모두 추가
      chip.relTypes.forEach((rt) => {
        if (!enabledRelTypes.has(rt)) toggleRelType(rt);
      });
    }
  }

  return (
    /**
     * § 2-5 모바일: overflow-x auto + scrollbar 없음 + 우측 페이드아웃 그라디언트
     * 마스크 이미지(fade-right)는 relative wrapper + ::after pseudo로 구현.
     * Tailwind에서 pseudo-element가 없으므로 인라인 스타일로 처리.
     */
    <div className="relative">
      {/* 우측 페이드아웃 그라디언트 힌트 (§2-5) — pointer-events:none 으로 클릭 투과 */}
      <div
        aria-hidden="true"
        className="absolute right-0 top-0 h-full w-12 pointer-events-none z-10 md:hidden"
        style={{
          background: 'linear-gradient(to right, transparent, rgb(249 250 251))',
        }}
      />

      <div
        className="flex items-center gap-2 py-2 px-1 overflow-x-auto"
        style={{ scrollbarWidth: 'none', WebkitOverflowScrolling: 'touch' } as React.CSSProperties}
      >
        {/* 칩 목록 */}
        {CHIP_DEFS.map((chip) => (
          <RelationChip
            key={chip.label}
            chip={chip}
            isOn={isChipOn(chip)}
            disabled={disabled}
            onToggle={() => handleToggle(chip)}
          />
        ))}

        {/* § 2-4 전체 켜기 / 전체 끄기 — 칩 바 우측 끝 */}
        <div className="flex items-center gap-1 ml-auto pl-2 shrink-0">
          <button
            type="button"
            onClick={disabled ? undefined : enableAllRelTypes}
            disabled={disabled}
            className={[
              'text-xs text-blue-500 hover:text-blue-700 px-2 py-1 rounded transition-colors',
              disabled ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer',
            ].join(' ')}
          >
            전체 켜기
          </button>
          <button
            type="button"
            onClick={disabled ? undefined : disableAllRelTypes}
            disabled={disabled}
            className={[
              'text-xs text-gray-500 hover:text-gray-700 px-2 py-1 rounded transition-colors',
              disabled ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer',
            ].join(' ')}
          >
            전체 끄기
          </button>
        </div>
      </div>
    </div>
  );
}

'use client';

import React, { useState, useEffect } from 'react';
import { Info, AlertCircle } from 'lucide-react';
import type { ScreenerPreset } from '@/types/screener';
import PresetDetailPopover, { type PresetExplanation } from './PresetDetailPopover';
import { usePopover } from '@/hooks/usePopover';

interface PresetGalleryProps {
  presets: ScreenerPreset[];
  isLoading?: boolean;
  error?: Error | null;
  onPresetClick: (preset: ScreenerPreset) => void;
  onDeletePreset?: (presetId: number) => void;
  userPresets?: ScreenerPreset[];
  activePresetIds?: number[];  // 다중 선택 지원
  activePresetId?: number | null;  // 레거시 호환
}

// 프리셋별 구조화된 교육 설명
const PRESET_EXPLANATIONS: Record<string, PresetExplanation> = {
  // 초보자용
  '강한 상승 추세': {
    indicators: 'Trend Strength > 0.7, RVOL > 1.5x',
    reason: '추세 강도(Trend Strength)는 (종가-시가)/(고가-저가)로 계산되어 당일 가격 움직임의 방향성을 측정한다. +0.7 이상이면 시가 대비 고점 근처에서 마감했다는 의미다. RVOL은 평소 대비 거래량 배수를 확인하여, 거래량 뒷받침 없는 허위 상승을 필터링한다.',
    meaning: '매수세가 장중 내내 우세하고 시장 참여자들의 관심이 높은 종목. 모멘텀 추종 전략에 적합하다. 단기 트레이딩 관점에서 추가 상승 여력을 탐색할 때 활용.',
    caution: '단기 지표일 뿐 장기 추세와는 무관하다. 하루 급등 후 되돌림(mean reversion)이 발생할 수 있으므로 추가 확인 신호가 필요하다.',
  },

  '저평가 우량주': {
    indicators: 'P/E < 15, ROE > 15%',
    reason: 'P/E 15 이하는 S&P 500 역사적 평균(약 15-17)을 기준으로, 이익 대비 주가가 상대적으로 저렴함을 나타낸다. ROE 15% 이상은 자기자본으로 높은 수익을 창출하는 기업을 의미한다. 두 조건의 조합으로 "저렴하면서 수익성 좋은" 종목을 찾는다.',
    meaning: '시장에서 아직 가치를 인정받지 못한 우량 기업일 수 있다. 가치 투자(Value Investing) 관점에서 장기 보유 후보군으로 적합하다.',
    caution: '저평가에는 이유가 있을 수 있다(사업 축소, 경쟁 심화, 회계 문제 등). 개별 종목의 재무제표와 산업 전망을 반드시 확인해야 한다.',
  },

  '배당 수익주': {
    indicators: '배당수익률 > 2%',
    reason: '배당수익률은 연간 배당금을 현재 주가로 나눈 값이다. 2% 이상은 미국 시장 평균(약 1.5%)을 상회하며, 정기적인 현금 소득을 원하는 투자자에게 적합하다.',
    meaning: '배당과 주가 상승을 동시에 기대하는 "배당 성장" 전략에 활용 가능. 은퇴 포트폴리오나 소득 창출 목적에 적합하다.',
    caution: '고배당주는 성장 정체된 성숙 기업이거나, 주가 급락으로 수익률이 높아진 경우가 있다. 배당지급 이력(5년 이상 연속 배당)과 배당성장률도 확인 필요.',
  },

  '성장 가능성': {
    indicators: 'EPS 성장률 > 20%',
    reason: 'EPS(주당순이익) 성장률은 전년 대비 순이익 증가율을 측정한다. 20% 이상은 고성장 기업으로 분류되며, 미래 수익에 대한 시장 기대가 높다.',
    meaning: '성장주(Growth Stock) 전략에 적합. 현재 밸류에이션이 높더라도 성장이 지속되면 정당화될 수 있다. 테크, 헬스케어 등 성장 섹터에서 주로 발견.',
    caution: '일회성 요인(구조조정, 자산매각, 기저효과)에 의한 이익 증가는 지속 불가능. 최소 2-3분기 연속 성장 여부와 매출 성장도 함께 확인해야 한다.',
  },

  '섹터 강세': {
    indicators: 'Sector Alpha > 0%',
    reason: '섹터 알파는 개별 종목 수익률에서 해당 섹터 ETF 수익률을 뺀 값이다. 양수면 동일 섹터 내에서 평균을 상회하는 성과를 내고 있음을 의미한다.',
    meaning: '섹터 전체 상승장에서 함께 오르는 종목보다, 섹터 내 리더(outperformer)를 선별할 때 유용하다. 상대적 강도(Relative Strength) 전략의 핵심.',
    caution: '섹터 하락장에서 덜 빠지는 것도 양의 알파로 측정된다. 절대 수익률도 함께 확인 필요. 섹터 로테이션 타이밍과 함께 고려해야 한다.',
  },

  '거래량 급증': {
    indicators: 'RVOL > 2.0x',
    reason: 'RVOL(상대거래량)은 당일 거래량을 20일 평균으로 나눈 값이다. 2.0 이상이면 평소의 2배 이상 거래되고 있어 기관/헤지펀드 등 큰 손의 움직임이나 중요한 뉴스를 시사한다.',
    meaning: '시장 참여자들의 급격한 관심 증가. 뉴스 기반 트레이딩이나 이벤트 드리븐 전략에 활용. 브레이크아웃 확인에도 필수적인 지표.',
    caution: '높은 거래량 = 상승이 아니다. 대량 매도가 쏟아질 때도 거래량은 급증한다. 가격 방향과 함께 해석해야 하며, 뉴스 원인 파악이 중요하다.',
  },

  // 중급자용
  '반등 기회': {
    indicators: 'RSI < 30 (14일)',
    reason: 'RSI(상대강도지수)는 14일간 평균 상승폭과 하락폭을 비교하여 0-100 범위로 표현한다. 30 이하는 과매도 구간으로, 단기적으로 매도 압력이 과도했음을 나타낸다.',
    meaning: '역발상 매매(Contrarian) 전략의 진입 시점 탐색. 단기 반등(dead cat bounce)이라도 트레이딩 기회가 될 수 있다. 평균회귀를 기대하는 전략.',
    caution: '강한 하락 추세에서는 RSI가 20 이하로 더 떨어질 수 있다("과매도의 과매도"). 반등 매매 시 지지선, 거래량 변화, 캔들 패턴 등 추가 확인 신호가 필수.',
  },

  '평균회귀': {
    indicators: '볼린저 밴드 하단 근처',
    reason: '볼린저 밴드 하단은 20일 이동평균에서 표준편차의 2배만큼 아래 위치다. 통계적으로 가격이 이 범위를 벗어나는 경우는 약 5%에 불과하므로 평균으로 회귀할 가능성이 있다.',
    meaning: '통계적 차익거래(Mean Reversion) 전략에 활용. 횡보장이나 약한 추세에서 더 효과적. 밴드 하단 터치 후 반등 시 진입, 중심선(20MA) 도달 시 청산.',
    caution: '강한 하락 추세에서는 밴드를 따라 장기간 하단에 머무를 수 있다("밴드 워킹"). 추세 방향을 먼저 확인하고, 추세장에서는 피하는 것이 좋다.',
  },

  '고변동성': {
    indicators: '변동성 백분위 > 80%ile',
    reason: '변동성 백분위는 ATR(평균진폭)을 기반으로 최근 변동폭이 과거 대비 어느 수준인지 측정한다. 80%ile 이상이면 상위 20%의 높은 변동성 상태.',
    meaning: '단기 트레이더에게 기회 제공. 변동폭이 클수록 단기간 큰 수익 가능성. 옵션 매도 전략(높은 프리미엄)에도 활용 가능.',
    caution: '변동성은 양방향 - 급등과 급락 모두 가능하다. 손절 범위를 넓게 설정해야 하며, 포지션 사이즈를 줄여 리스크 관리 필수. 초보자에게 비권장.',
  },

  '품질 가치': {
    indicators: 'D/E < 1, ROE > 10%',
    reason: '부채비율(D/E) 1 이하는 자기자본보다 부채가 적다는 의미로 재무 안정성을 나타낸다. ROE 10% 이상과 결합하면 빚 없이도 양호한 수익을 내는 "품질 좋은" 기업을 선별.',
    meaning: '안전 가치(Quality Value) 전략. 경기 침체에도 버틸 재무 체력을 갖춘 기업. 장기 보유에 적합하며 방어적 포트폴리오 구성에 활용.',
    caution: '업종마다 적정 부채비율이 다르다(금융업은 높은 것이 정상, 유틸리티도 레버리지 활용). 무부채가 항상 좋은 것은 아니며, 레버리지를 통한 성장 기회를 놓칠 수 있다.',
  },

  '기술적 매수': {
    indicators: '골든크로스 + RSI 50-70 + 정배열',
    reason: '골든크로스(단기 MA가 장기 MA 상향 돌파)는 상승 추세 전환 신호. 20일 > 50일 > 200일 정배열은 모든 기간에서 상승 방향. RSI 50-70은 과매수 아니면서 모멘텀 있는 구간.',
    meaning: '기술적 분석 기반 추세 추종 전략. 여러 지표가 일치하는 "컨플루언스(confluence)" 상태로, 개별 지표보다 신뢰도가 높다. 스윙 트레이딩에 적합.',
    caution: '기술적 분석은 과거 가격 패턴에 기반하므로 예상치 못한 뉴스(실적 발표, 금리 결정 등)에는 무력하다. 손절 라인을 명확히 설정하고 진입해야 한다.',
  },
};

// 기본 설명 생성 함수
function getDefaultExplanation(preset: ScreenerPreset): PresetExplanation {
  const filterSummary = getFilterSummary(preset.filters_json || {});
  return {
    indicators: filterSummary || '사용자 정의 필터',
    reason: '사용자가 정의한 필터 조건을 기반으로 종목을 선별한다.',
    meaning: preset.description_ko || '특정 조건에 맞는 종목을 필터링한다.',
    caution: '개별 종목의 재무제표와 뉴스를 함께 확인해야 한다.',
  };
}

// 필터 조건 설명 생성
function getFilterSummary(filters: Record<string, unknown>): string {
  const parts: string[] = [];

  if (filters.pe_ratio_max) parts.push(`P/E < ${filters.pe_ratio_max}`);
  if (filters.pe_ratio_min) parts.push(`P/E > ${filters.pe_ratio_min}`);
  if (filters.roe_min) parts.push(`ROE > ${filters.roe_min}%`);
  if (filters.market_cap_min) {
    const cap = (filters.market_cap_min as number) / 1_000_000_000;
    parts.push(`시총 > ${cap}B`);
  }
  if (filters.dividend_min) parts.push(`배당 > ${filters.dividend_min}%`);
  if (filters.volume_min) {
    const vol = (filters.volume_min as number) / 1_000_000;
    parts.push(`거래량 > ${vol}M`);
  }
  if (filters.trend_strength_min) parts.push(`추세 > ${filters.trend_strength_min}`);
  if (filters.rvol_min) parts.push(`RVOL > ${filters.rvol_min}x`);
  if (filters.sector_alpha_min) parts.push(`섹터α > ${filters.sector_alpha_min}%`);
  if (filters.rsi_max) parts.push(`RSI < ${filters.rsi_max}`);
  if (filters.volatility_pct_min) parts.push(`변동성 > ${filters.volatility_pct_min}%ile`);
  if (filters.debt_equity_max) parts.push(`D/E < ${filters.debt_equity_max}`);
  if (filters.eps_growth_min) parts.push(`EPS성장 > ${filters.eps_growth_min}%`);

  return parts.join(' · ') || '필터 없음';
}

// 순서에 따른 색상 매핑
const ORDER_COLORS = [
  { bg: 'bg-[#238636]', border: 'border-[#238636]', ring: 'ring-[#238636]/50', text: 'text-[#3FB950]' },  // 1차: 녹색
  { bg: 'bg-[#1F6FEB]', border: 'border-[#1F6FEB]', ring: 'ring-[#1F6FEB]/50', text: 'text-[#58A6FF]' },  // 2차: 파란색
  { bg: 'bg-[#A371F7]', border: 'border-[#A371F7]', ring: 'ring-[#A371F7]/50', text: 'text-[#A371F7]' },  // 3차: 보라색
];

const PresetCard = ({
  preset,
  onClick,
  onDelete,
  isActive,
  activeOrder,
  onInfoClick,
  activeInfoPresetId,
}: {
  preset: ScreenerPreset;
  onClick: () => void;
  onDelete?: () => void;
  isActive: boolean;
  activeOrder?: number;  // 적용 순서 (1, 2, 3)
  onInfoClick: (preset: ScreenerPreset, buttonRef: React.RefObject<HTMLButtonElement | null>) => void;
  activeInfoPresetId: number | null;
}) => {
  const buttonRef = React.useRef<HTMLButtonElement>(null);
  const isInfoActive = activeInfoPresetId === preset.id;
  const orderColor = activeOrder !== undefined ? ORDER_COLORS[activeOrder - 1] || ORDER_COLORS[0] : null;

  return (
    <div
      className={`
        group relative rounded-lg border p-3 transition-all cursor-pointer
        ${isActive && orderColor
          ? `bg-[${orderColor.bg.replace('bg-[', '').replace(']', '')}]/10 ${orderColor.border} ring-1 ${orderColor.ring}`
          : isActive
          ? 'bg-[#1F6FEB]/10 border-[#1F6FEB] ring-1 ring-[#1F6FEB]/50'
          : 'bg-[#161B22] border-[#30363D] hover:border-[#8B949E]'
        }
      `}
      onClick={onClick}
    >
      {/* 순서 배지 (좌상단) */}
      {isActive && activeOrder && (
        <div
          className={`absolute -top-2 -left-2 w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold text-white ${orderColor?.bg || 'bg-[#1F6FEB]'}`}
        >
          {activeOrder}
        </div>
      )}

      {/* Delete button for user presets */}
      {!preset.is_system && onDelete && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 p-1 text-[#8B949E] hover:text-[#F85149] rounded transition-opacity"
          title="삭제"
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      )}

      {/* Header: Name + Type Badge + Active Badge */}
      <div className="flex items-center gap-2 mb-1.5">
        <h4 className={`text-sm font-medium flex-1 ${isActive && orderColor ? orderColor.text : isActive ? 'text-[#58A6FF]' : 'text-[#E6EDF3]'}`}>
          {preset.name}
        </h4>
        {/* Preset Type Badge */}
        {preset.preset_type === 'enhanced' && (
          <span className="text-[9px] px-1.5 py-0.5 bg-[#F0883E]/20 text-[#F0883E] border border-[#F0883E]/30 rounded font-medium" title="추가 데이터 로딩 필요 (PE/ROE/EPS Growth 등)">
            Enhanced
          </span>
        )}
        {isActive && (
          <span className={`text-[10px] px-1.5 py-0.5 text-white rounded font-medium ${orderColor?.bg || 'bg-[#1F6FEB]'}`}>
            {activeOrder ? `${activeOrder}차` : '적용중'}
          </span>
        )}
      </div>

      {/* Brief description */}
      <p className="text-[13px] text-[#C9D1D9] mb-2.5 leading-snug">
        {preset.description_ko}
      </p>

      {/* Filter conditions (small) */}
      <div className="text-[10px] text-[#6E7681] mb-2 font-mono">
        {getFilterSummary(preset.filters_json || {})}
      </div>

      {/* Info button */}
      <button
        ref={buttonRef}
        onClick={(e) => {
          e.stopPropagation();
          onInfoClick(preset, buttonRef);
        }}
        className={`flex items-center gap-1 text-[10px] transition-colors ${
          isInfoActive
            ? 'text-[#58A6FF]'
            : 'text-[#8B949E] hover:text-[#E6EDF3]'
        }`}
      >
        <Info className="w-3 h-3" />
        <span>상세 설명</span>
      </button>
    </div>
  );
};

export default function PresetGallery({
  presets,
  isLoading,
  error,
  onPresetClick,
  onDeletePreset,
  userPresets = [],
  activePresetIds = [],
  activePresetId,  // 레거시 호환
}: PresetGalleryProps) {
  // 레거시 호환: activePresetId가 있으면 activePresetIds로 변환
  const effectiveActiveIds = activePresetIds.length > 0 ? activePresetIds : (activePresetId ? [activePresetId] : []);

  // Popover state
  const [activeInfoPreset, setActiveInfoPreset] = useState<ScreenerPreset | null>(null);
  const [isMobile, setIsMobile] = useState(false);
  const popover = usePopover({
    onClose: () => setActiveInfoPreset(null),
  });

  // Detect mobile
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 640);
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  const handleInfoClick = (
    preset: ScreenerPreset,
    buttonRef: React.RefObject<HTMLButtonElement | null>
  ) => {
    if (activeInfoPreset?.id === preset.id) {
      popover.close();
      setActiveInfoPreset(null);
    } else {
      // Update trigger ref for position calculation
      if (buttonRef.current && popover.triggerRef.current !== buttonRef.current) {
        (popover.triggerRef as React.MutableRefObject<HTMLButtonElement | null>).current = buttonRef.current;
      }
      setActiveInfoPreset(preset);
      popover.open();
    }
  };

  if (isLoading) {
    return (
      <div className="rounded-xl border border-[#30363D] bg-[#161B22] p-4">
        <div className="animate-pulse">
          <div className="h-5 bg-[#21262D] rounded w-1/4 mb-3"></div>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-3">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="h-24 bg-[#21262D] rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-[#30363D] bg-[#161B22] p-4">
        <div className="flex items-center gap-2 text-[#F85149]">
          <AlertCircle className="w-4 h-4" />
          <span className="text-sm">프리셋 로드 실패</span>
        </div>
      </div>
    );
  }

  // 카테고리별 분류
  const beginnerPresets = presets.filter((p) => p.category === 'beginner');
  const intermediatePresets = presets.filter((p) => p.category === 'intermediate');
  const systemPresets = presets.filter(
    (p) => p.is_system && p.category !== 'beginner' && p.category !== 'intermediate'
  );

  // Get explanation for active preset
  const activeExplanation = activeInfoPreset
    ? PRESET_EXPLANATIONS[activeInfoPreset.name] || getDefaultExplanation(activeInfoPreset)
    : null;

  return (
    <div className="rounded-xl border border-[#30363D] bg-[#161B22] p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-[#E6EDF3]">프리셋</h3>
        <span className="text-xs text-[#8B949E]">
          {presets.length + userPresets.length}개
        </span>
      </div>

      {/* 초보자용 */}
      {beginnerPresets.length > 0 && (
        <div className="mb-4">
          <h4 className="text-xs font-medium text-[#8B949E] mb-2 uppercase tracking-wide">
            초보자
          </h4>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-2">
            {beginnerPresets.map((preset) => {
              const orderIndex = effectiveActiveIds.indexOf(preset.id);
              return (
                <PresetCard
                  key={preset.id}
                  preset={preset}
                  onClick={() => onPresetClick(preset)}
                  isActive={orderIndex !== -1}
                  activeOrder={orderIndex !== -1 ? orderIndex + 1 : undefined}
                  onInfoClick={handleInfoClick}
                  activeInfoPresetId={activeInfoPreset?.id ?? null}
                />
              );
            })}
          </div>
        </div>
      )}

      {/* 중급자용 */}
      {intermediatePresets.length > 0 && (
        <div className="mb-4">
          <h4 className="text-xs font-medium text-[#8B949E] mb-2 uppercase tracking-wide">
            중급자
          </h4>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-2">
            {intermediatePresets.map((preset) => {
              const orderIndex = effectiveActiveIds.indexOf(preset.id);
              return (
                <PresetCard
                  key={preset.id}
                  preset={preset}
                  onClick={() => onPresetClick(preset)}
                  isActive={orderIndex !== -1}
                  activeOrder={orderIndex !== -1 ? orderIndex + 1 : undefined}
                  onInfoClick={handleInfoClick}
                  activeInfoPresetId={activeInfoPreset?.id ?? null}
                />
              );
            })}
          </div>
        </div>
      )}

      {/* 시스템 프리셋 (기타) */}
      {systemPresets.length > 0 && (
        <div className="mb-4">
          <h4 className="text-xs font-medium text-[#8B949E] mb-2 uppercase tracking-wide">
            기타
          </h4>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-2">
            {systemPresets.map((preset) => {
              const orderIndex = effectiveActiveIds.indexOf(preset.id);
              return (
                <PresetCard
                  key={preset.id}
                  preset={preset}
                  onClick={() => onPresetClick(preset)}
                  isActive={orderIndex !== -1}
                  activeOrder={orderIndex !== -1 ? orderIndex + 1 : undefined}
                  onInfoClick={handleInfoClick}
                  activeInfoPresetId={activeInfoPreset?.id ?? null}
                />
              );
            })}
          </div>
        </div>
      )}

      {/* 내 프리셋 */}
      {userPresets.length > 0 && (
        <div>
          <h4 className="text-xs font-medium text-[#8B949E] mb-2 uppercase tracking-wide">
            내 프리셋
          </h4>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-2">
            {userPresets.map((preset) => {
              const orderIndex = effectiveActiveIds.indexOf(preset.id);
              return (
                <PresetCard
                  key={preset.id}
                  preset={preset}
                  onClick={() => onPresetClick(preset)}
                  onDelete={onDeletePreset ? () => onDeletePreset(preset.id) : undefined}
                  isActive={orderIndex !== -1}
                  activeOrder={orderIndex !== -1 ? orderIndex + 1 : undefined}
                  onInfoClick={handleInfoClick}
                  activeInfoPresetId={activeInfoPreset?.id ?? null}
                />
              );
            })}
          </div>
        </div>
      )}

      {/* Empty state */}
      {presets.length === 0 && userPresets.length === 0 && (
        <div className="text-center py-8 text-[#8B949E] text-sm">
          프리셋 없음
        </div>
      )}

      {/* Popover */}
      {activeInfoPreset && activeExplanation && (
        <PresetDetailPopover
          ref={popover.popoverRef}
          title={activeInfoPreset.name}
          explanation={activeExplanation}
          isOpen={popover.isOpen}
          onClose={popover.close}
          style={popover.style}
          isMobile={isMobile}
        />
      )}
    </div>
  );
}

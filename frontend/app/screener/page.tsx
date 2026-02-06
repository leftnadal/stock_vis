'use client';

import { useCallback, useMemo, Suspense, useState, useEffect } from 'react';
import { useSearchParams, useRouter, usePathname } from 'next/navigation';
import { Search, Loader2, AlertCircle, BarChart3, Sparkles, RefreshCw, X, AlertTriangle, Grid, List, Dna, Lightbulb, Share2 } from 'lucide-react';
import { useMutation } from '@tanstack/react-query';
import { useStockScreener } from '@/hooks/useStockScreener';
import { ScreenerTable } from '@/components/strategy/ScreenerTable';
import { AuthGuard } from '@/components/auth/AuthGuard';
import { keywordService } from '@/services/keywordService';
import type { ScreenerFilters } from '@/types/screener';

// 새로 추가된 컴포넌트 및 훅
import MarketBreadthCard from '@/components/screener/MarketBreadthCard';
import SectorHeatmap from '@/components/screener/SectorHeatmap';
import PresetGallery from '@/components/screener/PresetGallery';
import Pagination from '@/components/screener/Pagination';
import AdvancedFilterPanel from '@/components/screener/AdvancedFilterPanel';
import MobileStockCard from '@/components/screener/MobileStockCard';
import SharePresetModal from '@/components/screener/SharePresetModal';
import ChainSightPanel from '@/components/screener/ChainSightPanel';
import ThesisBuilder from '@/components/screener/ThesisBuilder';
import { useMarketBreadth } from '@/hooks/useMarketBreadth';
import { screenerService } from '@/services/screenerService';
import { useSectorHeatmap } from '@/hooks/useSectorHeatmap';
import { useScreenerPresets } from '@/hooks/useScreenerPresets';
import type { ScreenerPreset, CombinedPresetResult, PresetType } from '@/types/screener';
import { combinePresetFilters } from '@/utils/presetCombiner';

// 최대 동시 적용 가능 프리셋 수
const MAX_PRESETS = 3;

// 섹터 목록
const SECTORS = [
  { value: '', label: '전체' },
  { value: 'Technology', label: '기술' },
  { value: 'Healthcare', label: '헬스케어' },
  { value: 'Financial Services', label: '금융' },
  { value: 'Consumer Cyclical', label: '소비재' },
  { value: 'Energy', label: '에너지' },
  { value: 'Industrials', label: '산업재' },
  { value: 'Communication Services', label: '통신' },
  { value: 'Real Estate', label: '부동산' },
  { value: 'Utilities', label: '유틸리티' },
  { value: 'Basic Materials', label: '소재' },
  { value: 'Consumer Defensive', label: '필수소비재' },
];

// 로딩 컴포넌트
function ScreenerLoading() {
  return (
    <div className="min-h-screen bg-[#0D1117]">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-8 w-8 animate-spin text-[#58A6FF]" />
        </div>
      </div>
    </div>
  );
}

// 메인 스크리너 컴포넌트 (useSearchParams 사용)
function ScreenerContent() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  // UI 상태
  const [showPresets, setShowPresets] = useState(true);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [viewMode, setViewMode] = useState<'table' | 'card'>('table');

  // Phase 2: 공유 모달 상태
  const [isShareModalOpen, setIsShareModalOpen] = useState(false);
  const [selectedPresetForShare, setSelectedPresetForShare] = useState<ScreenerPreset | null>(null);

  // Phase 2: Chain Sight / Thesis 패널 표시 상태
  const [showChainSight, setShowChainSight] = useState(false);
  const [showThesisBuilder, setShowThesisBuilder] = useState(false);

  // 활성 프리셋 추적 (다중 선택 지원)
  const [activePresetIds, setActivePresetIds] = useState<number[]>([]);

  // 새로운 훅 사용
  const { data: breadthResponse, isLoading: breadthLoading, error: breadthError } = useMarketBreadth();
  const { data: heatmapResponse, isLoading: heatmapLoading, error: heatmapError } = useSectorHeatmap();
  const { data: presetsResponse, isLoading: presetsLoading, error: presetsError } = useScreenerPresets();

  // URL에서 프리셋 IDs 읽기 (예: ?presets=2,5,8)
  useEffect(() => {
    const presetsParam = searchParams.get('presets');
    if (presetsParam) {
      const ids = presetsParam.split(',').map(Number).filter(n => !isNaN(n));
      setActivePresetIds(ids);
    } else {
      // 레거시 호환: 단일 preset 파라미터
      const presetId = searchParams.get('preset');
      setActivePresetIds(presetId ? [Number(presetId)] : []);
    }
  }, [searchParams]);

  // 프리셋 데이터 변환 (presetsResponse 의존)
  const presets = useMemo(() => {
    if (!presetsResponse?.data?.presets) return [];
    return presetsResponse.data.presets.map(p => ({
      ...p,
      is_system: p.is_system ?? p.category !== 'custom',
    }));
  }, [presetsResponse]);

  // 프리셋 결합 결과 계산
  const combinedResult = useMemo<CombinedPresetResult>(() => {
    if (activePresetIds.length === 0 || presets.length === 0) {
      return {
        effectiveFilters: {},
        conflicts: [],
        hasWarnings: false,
        appliedPresetIds: [],
        filterSources: {},
      };
    }

    const activePresets = activePresetIds
      .map(id => presets.find(p => p.id === id))
      .filter((p): p is ScreenerPreset => p !== undefined);

    return combinePresetFilters(activePresets);
  }, [activePresetIds, presets]);

  // URL 파라미터에서 필터 상태 읽기 (프리셋 결합 결과 + 수동 필터 병합)
  const filters = useMemo((): ScreenerFilters => {
    // 프리셋에서 온 필터
    const presetFilters = { ...combinedResult.effectiveFilters };

    // URL에서 직접 지정된 필터 (프리셋 외 수동 입력)
    const perMin = searchParams.get('per_min');
    const perMax = searchParams.get('per_max');
    const roeMin = searchParams.get('roe_min');
    const marketCapMin = searchParams.get('market_cap_min');
    const marketCapMax = searchParams.get('market_cap_max');
    const sector = searchParams.get('sector');
    const betaMin = searchParams.get('beta_min');
    const betaMax = searchParams.get('beta_max');
    const dividendMin = searchParams.get('dividend_min');
    const volumeMin = searchParams.get('volume_min');

    // 수동 필터로 덮어씀 (URL에 직접 지정된 값 우선)
    if (perMin) presetFilters.per_min = Number(perMin);
    if (perMax) presetFilters.per_max = Number(perMax);
    if (roeMin) presetFilters.roe_min = Number(roeMin);
    if (marketCapMin) presetFilters.market_cap_min = Number(marketCapMin);
    if (marketCapMax) presetFilters.market_cap_max = Number(marketCapMax);
    if (sector) presetFilters.sector = sector;
    if (betaMin) presetFilters.beta_min = Number(betaMin);
    if (betaMax) presetFilters.beta_max = Number(betaMax);
    if (dividendMin) presetFilters.dividend_min = Number(dividendMin);
    if (volumeMin) presetFilters.volume_min = Number(volumeMin);

    return presetFilters;
  }, [searchParams, combinedResult.effectiveFilters]);

  const { data: stocks, isLoading, error, refetch } = useStockScreener(filters);

  // 키워드 상태
  const [keywords, setKeywords] = useState<Record<string, string[]>>({});
  const [isLoadingKeywords, setIsLoadingKeywords] = useState(false);
  const [isGeneratingKeywords, setIsGeneratingKeywords] = useState(false);

  // 키워드 생성 mutation
  const keywordMutation = useMutation({
    mutationFn: (stocksToGenerate: Array<{
      symbol: string;
      company_name?: string;
      sector?: string;
      change_percent?: number;
    }>) => keywordService.generateScreenerKeywords(stocksToGenerate),
    onMutate: () => {
      setIsGeneratingKeywords(true);
    },
    onSuccess: (data) => {
      const stockCount = data?.data?.stock_count || 0;
      const delayMs = Math.min(stockCount * 6000, 60000);

      setTimeout(() => {
        if (stocks && stocks.length > 0) {
          fetchKeywords(stocks.map(s => s.symbol));
        }
        setIsGeneratingKeywords(false);
      }, delayMs);
    },
    onError: () => {
      setIsGeneratingKeywords(false);
    },
  });

  // 키워드 조회 함수
  const fetchKeywords = useCallback(async (symbols: string[]) => {
    if (symbols.length === 0) return;

    setIsLoadingKeywords(true);
    try {
      const response = await keywordService.getBatchKeywords({ symbols });
      if (response.success && response.data?.keywords) {
        setKeywords(response.data.keywords as unknown as Record<string, string[]>);
      }
    } catch (err) {
      console.error('키워드 조회 실패:', err);
    } finally {
      setIsLoadingKeywords(false);
    }
  }, []);

  // stocks 변경 시 키워드 조회
  useEffect(() => {
    if (stocks && stocks.length > 0) {
      fetchKeywords(stocks.map(s => s.symbol));
    }
  }, [stocks, fetchKeywords]);

  // AI 키워드 생성 핸들러
  const handleGenerateKeywords = useCallback(() => {
    if (!stocks || stocks.length === 0) return;

    const stocksToGenerate = stocks.slice(0, 50).map(s => ({
      symbol: s.symbol,
      company_name: s.company_name || s.name,
      sector: s.sector,
      change_percent: s.changes_percentage ?? s.change ?? 0,
    }));

    keywordMutation.mutate(stocksToGenerate);
  }, [stocks, keywordMutation]);

  // Phase 2: 프리셋 공유 핸들러
  const handleSharePreset = useCallback(async (presetId: number) => {
    try {
      const response = await screenerService.sharePreset(presetId);
      return response.data;
    } catch (error) {
      console.error('프리셋 공유 실패:', error);
      throw error;
    }
  }, []);

  // Phase 2: 공유 모달 열기
  const openShareModal = useCallback((preset: ScreenerPreset) => {
    setSelectedPresetForShare(preset);
    setIsShareModalOpen(true);
  }, []);

  // URL 업데이트 함수
  const updateUrl = useCallback((newFilters: ScreenerFilters | null | undefined, presetIds?: number[]) => {
    const params = new URLSearchParams();

    // 프리셋 IDs 추가 (콤마로 구분)
    if (presetIds && presetIds.length > 0) {
      params.set('presets', presetIds.join(','));
    }

    // 수동 필터 (프리셋에 없는 것만)
    if (newFilters) {
      if (newFilters.per_min !== undefined) params.set('per_min', String(newFilters.per_min));
      if (newFilters.per_max !== undefined) params.set('per_max', String(newFilters.per_max));
      if (newFilters.roe_min !== undefined) params.set('roe_min', String(newFilters.roe_min));
      if (newFilters.market_cap_min !== undefined) params.set('market_cap_min', String(newFilters.market_cap_min));
      if (newFilters.market_cap_max !== undefined) params.set('market_cap_max', String(newFilters.market_cap_max));
      if (newFilters.sector) params.set('sector', newFilters.sector);
      if (newFilters.beta_min !== undefined) params.set('beta_min', String(newFilters.beta_min));
      if (newFilters.beta_max !== undefined) params.set('beta_max', String(newFilters.beta_max));
      if (newFilters.dividend_min !== undefined) params.set('dividend_min', String(newFilters.dividend_min));
      if (newFilters.volume_min !== undefined) params.set('volume_min', String(newFilters.volume_min));
    }

    const queryString = params.toString();
    const newUrl = `${pathname}${queryString ? `?${queryString}` : ''}`;
    router.push(newUrl, { scroll: false });
  }, [router, pathname]);

  // 필터 변경 핸들러 (고급 필터에서 변경 시 프리셋 유지하되 추가 필터로 표시)
  const handleFilterChange = useCallback((key: keyof ScreenerFilters, value: string | number | undefined) => {
    const newFilters = {
      ...filters,
      [key]: value === '' ? undefined : value,
    };
    // 필터 변경 시 프리셋 ID는 유지 (추가 필터로 표시하기 위해)
    updateUrl(newFilters, activePresetIds);
  }, [filters, updateUrl, activePresetIds]);

  // 프리셋 적용 핸들러 (토글 기능: 클릭 시 추가/제거)
  const handlePresetClick = useCallback((preset: ScreenerPreset) => {
    const currentIndex = activePresetIds.indexOf(preset.id);

    if (currentIndex !== -1) {
      // 이미 적용됨 → 해당 프리셋만 제거
      const newIds = activePresetIds.filter(id => id !== preset.id);
      setActivePresetIds(newIds);
      if (newIds.length === 0) {
        router.push(pathname, { scroll: false });
      } else {
        updateUrl(null, newIds);
      }
    } else {
      // 새 프리셋 추가 (최대 MAX_PRESETS개)
      if (activePresetIds.length >= MAX_PRESETS) {
        // 최대 개수 도달 시 가장 오래된 것 제거하고 새 것 추가
        const newIds = [...activePresetIds.slice(1), preset.id];
        setActivePresetIds(newIds);
        updateUrl(null, newIds);
      } else {
        const newIds = [...activePresetIds, preset.id];
        setActivePresetIds(newIds);
        updateUrl(null, newIds);
      }
    }
  }, [activePresetIds, updateUrl, router, pathname]);

  // 개별 프리셋 제거 핸들러
  const handleRemovePreset = useCallback((presetId: number) => {
    const newIds = activePresetIds.filter(id => id !== presetId);
    setActivePresetIds(newIds);
    if (newIds.length === 0) {
      router.push(pathname, { scroll: false });
    } else {
      updateUrl(null, newIds);
    }
  }, [activePresetIds, updateUrl, router, pathname]);

  // 섹터 클릭 핸들러 (히트맵에서)
  const handleSectorClick = useCallback((sector: string) => {
    updateUrl({ ...filters, sector }, activePresetIds);
  }, [filters, updateUrl, activePresetIds]);

  // 전체 초기화 핸들러 (프리셋 포함)
  const handleReset = useCallback(() => {
    setActivePresetIds([]);
    router.push(pathname, { scroll: false });
  }, [pathname, router]);

  // 추가 필터만 초기화 (프리셋 유지)
  const handleResetAdditionalFilters = useCallback(() => {
    // 프리셋에서 온 필터만 유지하고 URL의 추가 필터는 제거
    if (activePresetIds.length > 0) {
      // 프리셋 ID만 유지하고 나머지 필터 파라미터는 제거
      updateUrl(null, activePresetIds);
    } else {
      // 프리셋이 없으면 모든 필터 초기화
      router.push(pathname, { scroll: false });
    }
  }, [activePresetIds, updateUrl, router, pathname]);

  // 필터 태그 제거
  const removeFilter = useCallback((key: keyof ScreenerFilters) => {
    const newFilters = { ...filters };
    delete newFilters[key];
    updateUrl(newFilters, activePresetIds);
  }, [filters, updateUrl, activePresetIds]);

  // 활성 필터 개수 계산
  const activeFilterCount = Object.values(filters).filter(v => v !== undefined && v !== '').length;

  // 페이지네이션된 데이터
  const paginatedStocks = useMemo(() => {
    if (!stocks) return [];
    const start = (page - 1) * pageSize;
    const end = start + pageSize;
    return stocks.slice(start, end);
  }, [stocks, page, pageSize]);

  const totalPages = stocks ? Math.ceil(stocks.length / pageSize) : 0;

  // 활성 프리셋 정보 (순서대로)
  const activePresets = useMemo(() => {
    return activePresetIds
      .map(id => presets.find(p => p.id === id))
      .filter((p): p is ScreenerPreset => p !== undefined);
  }, [activePresetIds, presets]);

  // Enhanced 프리셋 여부 확인 (로딩 메시지 분기용)
  const hasEnhancedPreset = useMemo(() => {
    return activePresets.some(p => p.preset_type === 'enhanced');
  }, [activePresets]);

  // 프리셋 필터와 현재 필터 비교하여 추가 필터 찾기
  const additionalFilters = useMemo(() => {
    if (activePresets.length === 0) return [];

    const additional: string[] = [];

    // 현재 URL 필터 중 프리셋에서 오지 않은 것 찾기
    Object.entries(filters).forEach(([key, value]) => {
      if (value === undefined) return;

      // 이 필터가 어떤 프리셋에서 왔는지 확인
      const sourcePresetId = combinedResult.filterSources[key];
      if (!sourcePresetId) {
        // 프리셋에서 온 게 아니라면 추가 필터로 표시
        const labelMap: Record<string, string> = {
          per_min: `PER ≥ ${value}`,
          per_max: `PER ≤ ${value}`,
          roe_min: `ROE ≥ ${value}%`,
          market_cap_min: `시가총액 ≥ $${((value as number) / 1e9).toFixed(0)}B`,
          market_cap_max: `시가총액 ≤ $${((value as number) / 1e9).toFixed(0)}B`,
          sector: `섹터: ${SECTORS.find(s => s.value === value)?.label || value}`,
          beta_min: `베타 ≥ ${value}`,
          beta_max: `베타 ≤ ${value}`,
          dividend_min: `배당률 ≥ ${value}%`,
          volume_min: `거래량 ≥ ${((value as number) / 1e6).toFixed(0)}M`,
        };
        if (labelMap[key]) {
          additional.push(labelMap[key]);
        }
      }
    });

    return additional;
  }, [activePresets, filters, combinedResult.filterSources]);

  return (
    <div className="min-h-screen bg-[#0D1117]">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {/* 헤더 */}
        <div className="mb-8">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-[#58A6FF]/10 p-2">
              <BarChart3 className="h-6 w-6 text-[#58A6FF]" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-[#E6EDF3]">종목 스크리너</h1>
              <p className="text-sm text-[#8B949E]">조건에 맞는 종목을 검색하고 분석하세요</p>
            </div>
          </div>
        </div>

        {/* Market Breadth + Sector Heatmap 그리드 */}
        <div className="mb-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Market Breadth Card */}
          <div className="lg:col-span-1">
            {breadthResponse?.data ? (
              <MarketBreadthCard
                data={breadthResponse.data}
                isLoading={breadthLoading}
                error={breadthError || null}
              />
            ) : (
              <div className="rounded-xl border border-[#30363D] bg-[#161B22] p-6">
                <div className="flex items-center gap-2 text-[#8B949E]">
                  <AlertCircle className="h-4 w-4" />
                  <span className="text-sm">시장 폭 데이터 없음</span>
                </div>
              </div>
            )}
          </div>

          {/* Sector Heatmap */}
          <div className="lg:col-span-2">
            {heatmapResponse?.data?.sectors && heatmapResponse.data.sectors.length > 0 ? (
              <SectorHeatmap
                sectors={heatmapResponse.data.sectors}
                date={heatmapResponse.data.date}
                isLoading={heatmapLoading}
                error={heatmapError || null}
                onSectorClick={handleSectorClick}
              />
            ) : heatmapLoading ? (
              <div className="rounded-xl border border-[#30363D] bg-[#161B22] p-6 h-[400px] flex items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-[#58A6FF]" />
              </div>
            ) : (
              <div className="rounded-xl border border-[#30363D] bg-[#161B22] p-6">
                <div className="flex items-center gap-2 text-[#8B949E] py-8 justify-center">
                  <AlertCircle className="h-4 w-4" />
                  <span className="text-sm">섹터 데이터 없음</span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* 프리셋 갤러리 */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-[#8B949E]">빠른 프리셋</h3>
            <button
              onClick={() => setShowPresets(!showPresets)}
              className="text-[#8B949E] hover:text-[#E6EDF3] text-xs"
            >
              {showPresets ? '접기' : '펼치기'}
            </button>
          </div>
          {showPresets && (
            <PresetGallery
              presets={presets}
              activePresetIds={activePresetIds}
              isLoading={presetsLoading}
              error={presetsError || null}
              onPresetClick={handlePresetClick}
            />
          )}
        </div>

        {/* 고급 필터 패널 */}
        <AdvancedFilterPanel
          filters={filters}
          onFilterChange={handleFilterChange}
          onReset={handleResetAdditionalFilters}
          activePresetIds={activePresetIds}
          className="mb-6"
        />

        {/* 적용된 필터 결과 */}
        {(activePresets.length > 0 || activeFilterCount > 0) && (
          <div className="mb-4 p-3 rounded-lg border border-[#30363D] bg-[#161B22]">
            {/* 필터 소스 표시 (프리셋 + 추가 필터) */}
            {activePresets.length > 0 && (
              <div className="flex flex-wrap items-center gap-2 mb-3 pb-3 border-b border-[#30363D]">
                <span className="text-xs text-[#8B949E]">필터 소스:</span>
                {activePresets.map((preset, idx) => {
                  const colors = [
                    'bg-[#238636]/20 text-[#3FB950] border-[#238636]',
                    'bg-[#1F6FEB]/20 text-[#58A6FF] border-[#1F6FEB]',
                    'bg-[#A371F7]/20 text-[#A371F7] border-[#A371F7]',
                  ];
                  return (
                    <span
                      key={preset.id}
                      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-medium border ${colors[idx] || colors[0]}`}
                    >
                      <span className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-current/20 text-[10px] font-bold">
                        {idx + 1}
                      </span>
                      {preset.icon} {preset.name}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRemovePreset(preset.id);
                        }}
                        className="ml-1 hover:text-[#F85149] transition-colors"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </span>
                  );
                })}
                {additionalFilters.length > 0 && (
                  <>
                    <span className="text-[#8B949E]">+</span>
                    {additionalFilters.map((filter, idx) => (
                      <span key={idx} className="inline-flex items-center rounded-full bg-[#21262D] px-2 py-1 text-xs text-[#E6EDF3]">
                        {filter}
                      </span>
                    ))}
                  </>
                )}
                <button
                  onClick={handleReset}
                  className="ml-auto text-xs text-[#F85149] hover:underline"
                >
                  모두 초기화
                </button>
              </div>
            )}

            {/* 충돌 경고 영역 */}
            {combinedResult.hasWarnings && combinedResult.conflicts.length > 0 && (
              <div className="mb-3 p-2 rounded border border-[#D29922]/50 bg-[#D29922]/10">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="h-4 w-4 text-[#D29922] flex-shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <p className="text-xs font-medium text-[#D29922] mb-1">필터 충돌 (교집합 없음)</p>
                    <ul className="text-xs text-[#E6EDF3] space-y-0.5">
                      {combinedResult.conflicts.map((conflict, idx) => (
                        <li key={idx}>
                          <span className="text-[#8B949E]">{conflict.filterLabel}:</span>{' '}
                          {conflict.resolution}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}

            {/* 최종 적용된 필터 결과 */}
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-medium text-[#E6EDF3]">최종 적용 필터:</span>
              {filters.market_cap_min && (
                <span className="inline-flex items-center gap-1 rounded-full bg-[#238636]/20 border border-[#238636]/50 px-2 py-1 text-xs text-[#3FB950]">
                  시가총액 ≥ ${(filters.market_cap_min / 1e9).toFixed(0)}B
                  <button onClick={() => removeFilter('market_cap_min')} className="text-[#3FB950]/70 hover:text-[#F85149]">
                    <X className="h-3 w-3" />
                  </button>
                </span>
              )}
              {filters.market_cap_max && (
                <span className="inline-flex items-center gap-1 rounded-full bg-[#238636]/20 border border-[#238636]/50 px-2 py-1 text-xs text-[#3FB950]">
                  시가총액 ≤ ${(filters.market_cap_max / 1e9).toFixed(0)}B
                  <button onClick={() => removeFilter('market_cap_max')} className="text-[#3FB950]/70 hover:text-[#F85149]">
                    <X className="h-3 w-3" />
                  </button>
                </span>
              )}
              {filters.per_max && (
                <span className="inline-flex items-center gap-1 rounded-full bg-[#238636]/20 border border-[#238636]/50 px-2 py-1 text-xs text-[#3FB950]">
                  PER ≤ {filters.per_max}
                  <button onClick={() => removeFilter('per_max')} className="text-[#3FB950]/70 hover:text-[#F85149]">
                    <X className="h-3 w-3" />
                  </button>
                </span>
              )}
              {filters.per_min && (
                <span className="inline-flex items-center gap-1 rounded-full bg-[#238636]/20 border border-[#238636]/50 px-2 py-1 text-xs text-[#3FB950]">
                  PER ≥ {filters.per_min}
                  <button onClick={() => removeFilter('per_min')} className="text-[#3FB950]/70 hover:text-[#F85149]">
                    <X className="h-3 w-3" />
                  </button>
                </span>
              )}
              {filters.roe_min && (
                <span className="inline-flex items-center gap-1 rounded-full bg-[#238636]/20 border border-[#238636]/50 px-2 py-1 text-xs text-[#3FB950]">
                  ROE ≥ {filters.roe_min}%
                  <button onClick={() => removeFilter('roe_min')} className="text-[#3FB950]/70 hover:text-[#F85149]">
                    <X className="h-3 w-3" />
                  </button>
                </span>
              )}
              {filters.sector && (
                <span className="inline-flex items-center gap-1 rounded-full bg-[#238636]/20 border border-[#238636]/50 px-2 py-1 text-xs text-[#3FB950]">
                  섹터: {SECTORS.find(s => s.value === filters.sector)?.label}
                  <button onClick={() => removeFilter('sector')} className="text-[#3FB950]/70 hover:text-[#F85149]">
                    <X className="h-3 w-3" />
                  </button>
                </span>
              )}
              {filters.dividend_min && (
                <span className="inline-flex items-center gap-1 rounded-full bg-[#238636]/20 border border-[#238636]/50 px-2 py-1 text-xs text-[#3FB950]">
                  배당률 ≥ {filters.dividend_min}%
                  <button onClick={() => removeFilter('dividend_min')} className="text-[#3FB950]/70 hover:text-[#F85149]">
                    <X className="h-3 w-3" />
                  </button>
                </span>
              )}
              {filters.volume_min && (
                <span className="inline-flex items-center gap-1 rounded-full bg-[#238636]/20 border border-[#238636]/50 px-2 py-1 text-xs text-[#3FB950]">
                  거래량 ≥ {(filters.volume_min / 1e6).toFixed(0)}M
                  <button onClick={() => removeFilter('volume_min')} className="text-[#3FB950]/70 hover:text-[#F85149]">
                    <X className="h-3 w-3" />
                  </button>
                </span>
              )}
              {filters.beta_min && (
                <span className="inline-flex items-center gap-1 rounded-full bg-[#238636]/20 border border-[#238636]/50 px-2 py-1 text-xs text-[#3FB950]">
                  베타 ≥ {filters.beta_min}
                  <button onClick={() => removeFilter('beta_min')} className="text-[#3FB950]/70 hover:text-[#F85149]">
                    <X className="h-3 w-3" />
                  </button>
                </span>
              )}
              {filters.beta_max && (
                <span className="inline-flex items-center gap-1 rounded-full bg-[#238636]/20 border border-[#238636]/50 px-2 py-1 text-xs text-[#3FB950]">
                  베타 ≤ {filters.beta_max}
                  <button onClick={() => removeFilter('beta_max')} className="text-[#3FB950]/70 hover:text-[#F85149]">
                    <X className="h-3 w-3" />
                  </button>
                </span>
              )}
              {/* Enhanced 필터 표시 (PE/ROE/EPS Growth 등) */}
              {(filters as any).eps_growth_min && (
                <span className="inline-flex items-center gap-1 rounded-full bg-[#F0883E]/20 border border-[#F0883E]/50 px-2 py-1 text-xs text-[#F0883E]">
                  EPS 성장률 ≥ {(filters as any).eps_growth_min}%
                  <button onClick={() => removeFilter('eps_growth_min' as any)} className="text-[#F0883E]/70 hover:text-[#F85149]">
                    <X className="h-3 w-3" />
                  </button>
                </span>
              )}
              {(filters as any).revenue_growth_min && (
                <span className="inline-flex items-center gap-1 rounded-full bg-[#F0883E]/20 border border-[#F0883E]/50 px-2 py-1 text-xs text-[#F0883E]">
                  매출 성장률 ≥ {(filters as any).revenue_growth_min}%
                  <button onClick={() => removeFilter('revenue_growth_min' as any)} className="text-[#F0883E]/70 hover:text-[#F85149]">
                    <X className="h-3 w-3" />
                  </button>
                </span>
              )}
              {(filters as any).debt_equity_max && (
                <span className="inline-flex items-center gap-1 rounded-full bg-[#F0883E]/20 border border-[#F0883E]/50 px-2 py-1 text-xs text-[#F0883E]">
                  부채비율 ≤ {(filters as any).debt_equity_max}
                  <button onClick={() => removeFilter('debt_equity_max' as any)} className="text-[#F0883E]/70 hover:text-[#F85149]">
                    <X className="h-3 w-3" />
                  </button>
                </span>
              )}
              {(filters as any).rsi_min && (
                <span className="inline-flex items-center gap-1 rounded-full bg-[#F0883E]/20 border border-[#F0883E]/50 px-2 py-1 text-xs text-[#F0883E]">
                  RSI ≥ {(filters as any).rsi_min}
                  <button onClick={() => removeFilter('rsi_min' as any)} className="text-[#F0883E]/70 hover:text-[#F85149]">
                    <X className="h-3 w-3" />
                  </button>
                </span>
              )}
              {(filters as any).rsi_max && (
                <span className="inline-flex items-center gap-1 rounded-full bg-[#F0883E]/20 border border-[#F0883E]/50 px-2 py-1 text-xs text-[#F0883E]">
                  RSI ≤ {(filters as any).rsi_max}
                  <button onClick={() => removeFilter('rsi_max' as any)} className="text-[#F0883E]/70 hover:text-[#F85149]">
                    <X className="h-3 w-3" />
                  </button>
                </span>
              )}
              {(filters as any).change_percent_min && (
                <span className="inline-flex items-center gap-1 rounded-full bg-[#238636]/20 border border-[#238636]/50 px-2 py-1 text-xs text-[#3FB950]">
                  변동률 ≥ {(filters as any).change_percent_min}%
                  <button onClick={() => removeFilter('change_percent_min' as any)} className="text-[#3FB950]/70 hover:text-[#F85149]">
                    <X className="h-3 w-3" />
                  </button>
                </span>
              )}
              {(filters as any).change_percent_max && (
                <span className="inline-flex items-center gap-1 rounded-full bg-[#F85149]/20 border border-[#F85149]/50 px-2 py-1 text-xs text-[#F85149]">
                  변동률 ≤ {(filters as any).change_percent_max}%
                  <button onClick={() => removeFilter('change_percent_max' as any)} className="text-[#F85149]/70 hover:text-[#F85149]">
                    <X className="h-3 w-3" />
                  </button>
                </span>
              )}
              {activeFilterCount === 0 && activePresets.length === 0 && (
                <span className="text-xs text-[#8B949E]">필터 없음</span>
              )}
              {activePresets.length === 0 && activeFilterCount > 0 && (
                <button
                  onClick={handleReset}
                  className="ml-auto text-xs text-[#F85149] hover:underline"
                >
                  모두 초기화
                </button>
              )}
            </div>
          </div>
        )}

        {/* 결과 영역 */}
        <div className="rounded-lg border border-[#30363D] bg-[#161B22]">
          {/* 결과 헤더 */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between border-b border-[#30363D] px-4 py-3 gap-3">
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-[#E6EDF3]">검색 결과</h3>
              {stocks && (
                <span className="rounded bg-[#21262D] px-2 py-0.5 text-xs text-[#8B949E]">
                  {stocks.length.toLocaleString()}개 종목
                </span>
              )}
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              {/* 뷰 모드 토글 (모바일에서만 카드 기본) */}
              <div className="hidden sm:flex items-center rounded-lg bg-[#21262D] p-0.5">
                <button
                  onClick={() => setViewMode('table')}
                  className={`rounded p-1.5 transition-colors ${
                    viewMode === 'table'
                      ? 'bg-[#30363D] text-[#E6EDF3]'
                      : 'text-[#8B949E] hover:text-[#E6EDF3]'
                  }`}
                  title="테이블 뷰"
                >
                  <List className="h-4 w-4" />
                </button>
                <button
                  onClick={() => setViewMode('card')}
                  className={`rounded p-1.5 transition-colors ${
                    viewMode === 'card'
                      ? 'bg-[#30363D] text-[#E6EDF3]'
                      : 'text-[#8B949E] hover:text-[#E6EDF3]'
                  }`}
                  title="카드 뷰"
                >
                  <Grid className="h-4 w-4" />
                </button>
              </div>

              {/* AI 키워드 생성 버튼 */}
              <button
                onClick={handleGenerateKeywords}
                disabled={isGeneratingKeywords || !stocks || stocks.length === 0}
                className="flex items-center gap-1.5 rounded-lg bg-[#238636] px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-[#2ea043] disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isGeneratingKeywords ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Sparkles className="h-3.5 w-3.5" />
                )}
                <span className="hidden sm:inline">AI 키워드</span>
              </button>

              {/* Phase 2: Chain Sight DNA 버튼 */}
              <button
                onClick={() => setShowChainSight(!showChainSight)}
                disabled={!stocks || stocks.length === 0}
                className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
                  showChainSight
                    ? 'bg-[#A371F7] text-white'
                    : 'bg-[#21262D] text-[#8B949E] hover:text-[#E6EDF3]'
                }`}
                title="연관 종목 DNA"
              >
                <Dna className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">DNA</span>
              </button>

              {/* Phase 2: 투자 테제 버튼 */}
              <button
                onClick={() => setShowThesisBuilder(!showThesisBuilder)}
                disabled={!stocks || stocks.length === 0}
                className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
                  showThesisBuilder
                    ? 'bg-[#F0883E] text-white'
                    : 'bg-[#21262D] text-[#8B949E] hover:text-[#E6EDF3]'
                }`}
                title="투자 테제 생성"
              >
                <Lightbulb className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">테제</span>
              </button>

              <button
                onClick={() => refetch()}
                className="rounded p-1.5 text-[#8B949E] transition-colors hover:bg-[#21262D] hover:text-[#E6EDF3]"
                title="새로고침"
              >
                <RefreshCw className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* 결과 내용 */}
          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-16 gap-3">
              <Loader2 className="h-8 w-8 animate-spin text-[#58A6FF]" />
              <span className="text-sm text-[#8B949E]">
                {hasEnhancedPreset
                  ? '펀더멘탈 데이터 조회 중... (PE/ROE/EPS 등)'
                  : '종목 검색 중...'}
              </span>
              {hasEnhancedPreset && (
                <span className="text-xs text-[#6E7681]">
                  Enhanced 필터는 추가 API 호출이 필요하여 조금 더 걸릴 수 있습니다
                </span>
              )}
            </div>
          ) : error ? (
            <div className="flex items-center justify-center gap-2 py-16 text-[#F85149]">
              <AlertCircle className="h-5 w-5" />
              <span>데이터를 불러오는 중 오류가 발생했습니다</span>
            </div>
          ) : paginatedStocks.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-[#8B949E]">
              <Search className="h-8 w-8 mb-2 opacity-50" />
              <span>조건에 맞는 종목이 없습니다</span>
              <span className="text-xs mt-1">필터 조건을 변경해보세요</span>
            </div>
          ) : (
            <>
              {/* 테이블 뷰 (데스크탑 기본) */}
              <div className={`${viewMode === 'table' ? 'hidden sm:block' : 'hidden'}`}>
                <ScreenerTable
                  stocks={paginatedStocks}
                  keywords={keywords}
                  isLoadingKeywords={isLoadingKeywords}
                />
              </div>

              {/* 카드 뷰 (모바일 기본 + 데스크탑에서 선택 가능) */}
              <div className={`${viewMode === 'card' ? 'sm:block' : 'sm:hidden'} p-4`}>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {paginatedStocks.map((stock) => (
                    <MobileStockCard
                      key={stock.symbol}
                      symbol={stock.symbol}
                      companyName={stock.company_name || stock.name}
                      sector={stock.sector}
                      price={stock.price}
                      changePercent={stock.changes_percentage ?? stock.change}
                      marketCap={stock.market_cap}
                      volume={stock.volume}
                      pe={stock.pe}
                      roe={stock.roe}
                      dividendYield={stock.dividend_yield || stock.last_annual_dividend}
                      beta={stock.beta}
                      keywords={keywords[stock.symbol]}
                      isLoadingKeywords={isLoadingKeywords}
                    />
                  ))}
                </div>
              </div>

              {/* 페이지네이션 */}
              {totalPages > 1 && (
                <div className="border-t border-[#30363D] px-4 py-3">
                  <Pagination
                    currentPage={page}
                    totalPages={totalPages}
                    pageSize={pageSize}
                    totalCount={stocks?.length || 0}
                    hasNext={page < totalPages}
                    hasPrevious={page > 1}
                    onPageChange={setPage}
                    onPageSizeChange={(size) => {
                      setPageSize(size);
                      setPage(1);
                    }}
                  />
                </div>
              )}
            </>
          )}
        </div>

        {/* Phase 2: Chain Sight DNA 패널 */}
        {showChainSight && stocks && stocks.length > 0 && (
          <ChainSightPanel
            symbols={stocks.slice(0, 20).map(s => s.symbol)}
            filters={filters}
            className="mt-6"
          />
        )}

        {/* Phase 2: 투자 테제 빌더 */}
        {showThesisBuilder && stocks && stocks.length > 0 && (
          <ThesisBuilder
            stocks={stocks.slice(0, 50)}
            filters={filters}
            className="mt-6"
          />
        )}
      </div>

      {/* Phase 2: 프리셋 공유 모달 */}
      {selectedPresetForShare && (
        <SharePresetModal
          isOpen={isShareModalOpen}
          onClose={() => {
            setIsShareModalOpen(false);
            setSelectedPresetForShare(null);
          }}
          preset={selectedPresetForShare}
          onShare={handleSharePreset}
        />
      )}
    </div>
  );
}

// 메인 페이지 컴포넌트
export default function ScreenerPage() {
  return (
    <AuthGuard>
      <Suspense fallback={<ScreenerLoading />}>
        <ScreenerContent />
      </Suspense>
    </AuthGuard>
  );
}

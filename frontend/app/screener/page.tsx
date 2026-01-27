'use client';

import { useCallback, useMemo, Suspense, useState, useEffect } from 'react';
import { useSearchParams, useRouter, usePathname } from 'next/navigation';
import { Search, Loader2, AlertCircle, Filter, TrendingUp, DollarSign, Shield, Zap, BarChart3, Sparkles, RefreshCw } from 'lucide-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useStockScreener } from '@/hooks/useStockScreener';
import { ScreenerTable } from '@/components/strategy/ScreenerTable';
import { AuthGuard } from '@/components/auth/AuthGuard';
import { keywordService } from '@/services/keywordService';
import type { ScreenerFilters } from '@/services/strategyService';

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
];

// 프리셋 필터 정의
const PRESETS = [
  {
    id: 'large-cap',
    label: '대형주',
    icon: TrendingUp,
    description: '시가총액 $100B 이상',
    filters: { market_cap_min: 100_000_000_000 },
  },
  {
    id: 'value',
    label: '가치주',
    icon: DollarSign,
    description: 'PER 15 이하',
    filters: { per_max: 15 },
  },
  {
    id: 'growth',
    label: '성장주',
    icon: Zap,
    description: 'ROE 15% 이상',
    filters: { roe_min: 15 },
  },
  {
    id: 'defensive',
    label: '안전주',
    icon: Shield,
    description: '대형 + 저PER',
    filters: { market_cap_min: 50_000_000_000, per_max: 20 },
  },
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

  // URL 파라미터에서 필터 상태 읽기 (URL이 단일 진실 원천)
  const filters = useMemo((): ScreenerFilters => {
    const params: ScreenerFilters = {};

    const perMin = searchParams.get('per_min');
    const perMax = searchParams.get('per_max');
    const roeMin = searchParams.get('roe_min');
    const marketCapMin = searchParams.get('market_cap_min');
    const marketCapMax = searchParams.get('market_cap_max');
    const sector = searchParams.get('sector');

    if (perMin) params.per_min = Number(perMin);
    if (perMax) params.per_max = Number(perMax);
    if (roeMin) params.roe_min = Number(roeMin);
    if (marketCapMin) params.market_cap_min = Number(marketCapMin);
    if (marketCapMax) params.market_cap_max = Number(marketCapMax);
    if (sector) params.sector = sector;

    return params;
  }, [searchParams]);

  // 활성 프리셋 계산 (URL 기반)
  const activePreset = useMemo(() => {
    for (const preset of PRESETS) {
      const presetKeys = Object.keys(preset.filters) as (keyof ScreenerFilters)[];
      const filtersKeys = Object.keys(filters) as (keyof ScreenerFilters)[];

      if (presetKeys.length !== filtersKeys.length) continue;

      const presetFilters = preset.filters as Partial<ScreenerFilters>;
      const matches = presetKeys.every(key => filters[key] === presetFilters[key]);
      if (matches) return preset.id;
    }
    return null;
  }, [filters]);

  const { data: stocks, isLoading, error, refetch } = useStockScreener(filters);
  const queryClient = useQueryClient();

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
      // Celery 태스크가 비동기로 실행되므로 일정 시간 후 재조회
      const stockCount = data?.data?.stock_count || 0;
      const delayMs = Math.min(stockCount * 6000, 60000); // 종목당 6초, 최대 60초

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
        // API 응답: { keywords: { AAPL: [...], NVDA: [...] } }
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

    // 최대 50개까지만 생성 (API 제한)
    const stocksToGenerate = stocks.slice(0, 50).map(s => ({
      symbol: s.symbol,
      company_name: s.company_name || s.name,
      sector: s.sector,
      change_percent: s.changes_percentage ?? s.change ?? 0,
    }));

    keywordMutation.mutate(stocksToGenerate);
  }, [stocks, keywordMutation]);

  // URL 업데이트 함수
  const updateUrl = useCallback((newFilters: ScreenerFilters) => {
    const params = new URLSearchParams();

    if (newFilters.per_min !== undefined) params.set('per_min', String(newFilters.per_min));
    if (newFilters.per_max !== undefined) params.set('per_max', String(newFilters.per_max));
    if (newFilters.roe_min !== undefined) params.set('roe_min', String(newFilters.roe_min));
    if (newFilters.market_cap_min !== undefined) params.set('market_cap_min', String(newFilters.market_cap_min));
    if (newFilters.market_cap_max !== undefined) params.set('market_cap_max', String(newFilters.market_cap_max));
    if (newFilters.sector) params.set('sector', newFilters.sector);

    const queryString = params.toString();
    const newUrl = `${pathname}${queryString ? `?${queryString}` : ''}`;
    router.push(newUrl, { scroll: false });
  }, [router, pathname]);

  // 필터 변경 핸들러
  const handleFilterChange = useCallback((key: keyof ScreenerFilters, value: string | number | undefined) => {
    const newFilters = {
      ...filters,
      [key]: value === '' ? undefined : value,
    };
    updateUrl(newFilters);
  }, [filters, updateUrl]);

  // 프리셋 적용 핸들러
  const handlePresetClick = useCallback((presetId: string, presetFilters: ScreenerFilters) => {
    if (activePreset === presetId) {
      // 같은 프리셋 클릭 시 해제
      router.push(pathname, { scroll: false });
    } else {
      updateUrl(presetFilters);
    }
  }, [activePreset, pathname, router, updateUrl]);

  // 초기화 핸들러
  const handleReset = useCallback(() => {
    router.push(pathname, { scroll: false });
  }, [pathname, router]);

  // 활성 필터 개수 계산
  const activeFilterCount = Object.values(filters).filter(v => v !== undefined && v !== '').length;

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
              <p className="text-sm text-[#8B949E]">조건에 맞는 종목을 검색하세요</p>
            </div>
          </div>
        </div>

        {/* 프리셋 필터 */}
        <div className="mb-6">
          <h3 className="mb-3 text-sm font-medium text-[#8B949E]">빠른 프리셋</h3>
          <div className="flex flex-wrap gap-2">
            {PRESETS.map((preset) => {
              const Icon = preset.icon;
              const isActive = activePreset === preset.id;
              return (
                <button
                  key={preset.id}
                  onClick={() => handlePresetClick(preset.id, preset.filters)}
                  className={`flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-medium transition-all ${
                    isActive
                      ? 'border-[#58A6FF] bg-[#58A6FF]/10 text-[#58A6FF]'
                      : 'border-[#30363D] bg-[#161B22] text-[#8B949E] hover:border-[#58A6FF]/50 hover:text-[#E6EDF3]'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {preset.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* 상세 필터 */}
        <div className="mb-6 rounded-lg border border-[#30363D] bg-[#161B22] p-4">
          <div className="mb-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-[#58A6FF]" />
              <h3 className="text-sm font-semibold text-[#E6EDF3]">상세 필터</h3>
              {activeFilterCount > 0 && (
                <span className="rounded-full bg-[#58A6FF]/20 px-2 py-0.5 text-xs text-[#58A6FF]">
                  {activeFilterCount}개 적용 중
                </span>
              )}
            </div>
            <button
              onClick={handleReset}
              className="rounded px-3 py-1.5 text-xs font-medium text-[#8B949E] transition-colors hover:bg-[#0D1117] hover:text-[#E6EDF3]"
            >
              초기화
            </button>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            {/* 시가총액 최소 */}
            <div>
              <label className="mb-1 block text-xs text-[#8B949E]">시가총액 최소 ($B)</label>
              <input
                type="number"
                value={filters.market_cap_min ? filters.market_cap_min / 1_000_000_000 : ''}
                onChange={(e) => handleFilterChange('market_cap_min', e.target.value ? Number(e.target.value) * 1_000_000_000 : undefined)}
                placeholder="예: 10"
                className="w-full rounded border border-[#30363D] bg-[#0D1117] px-3 py-2 text-sm text-[#E6EDF3] placeholder-[#8B949E] focus:border-[#58A6FF] focus:outline-none"
              />
            </div>

            {/* 시가총액 최대 */}
            <div>
              <label className="mb-1 block text-xs text-[#8B949E]">시가총액 최대 ($B)</label>
              <input
                type="number"
                value={filters.market_cap_max ? filters.market_cap_max / 1_000_000_000 : ''}
                onChange={(e) => handleFilterChange('market_cap_max', e.target.value ? Number(e.target.value) * 1_000_000_000 : undefined)}
                placeholder="예: 1000"
                className="w-full rounded border border-[#30363D] bg-[#0D1117] px-3 py-2 text-sm text-[#E6EDF3] placeholder-[#8B949E] focus:border-[#58A6FF] focus:outline-none"
              />
            </div>

            {/* PER 최소값 */}
            <div>
              <label className="mb-1 block text-xs text-[#8B949E]">PER 최소</label>
              <input
                type="number"
                value={filters.per_min ?? ''}
                onChange={(e) => handleFilterChange('per_min', e.target.value ? Number(e.target.value) : undefined)}
                placeholder="예: 0"
                className="w-full rounded border border-[#30363D] bg-[#0D1117] px-3 py-2 text-sm text-[#E6EDF3] placeholder-[#8B949E] focus:border-[#58A6FF] focus:outline-none"
              />
            </div>

            {/* PER 최대값 */}
            <div>
              <label className="mb-1 block text-xs text-[#8B949E]">PER 최대</label>
              <input
                type="number"
                value={filters.per_max ?? ''}
                onChange={(e) => handleFilterChange('per_max', e.target.value ? Number(e.target.value) : undefined)}
                placeholder="예: 30"
                className="w-full rounded border border-[#30363D] bg-[#0D1117] px-3 py-2 text-sm text-[#E6EDF3] placeholder-[#8B949E] focus:border-[#58A6FF] focus:outline-none"
              />
            </div>

            {/* ROE 최소값 */}
            <div>
              <label className="mb-1 block text-xs text-[#8B949E]">ROE 최소 (%)</label>
              <input
                type="number"
                value={filters.roe_min ?? ''}
                onChange={(e) => handleFilterChange('roe_min', e.target.value ? Number(e.target.value) : undefined)}
                placeholder="예: 15"
                className="w-full rounded border border-[#30363D] bg-[#0D1117] px-3 py-2 text-sm text-[#E6EDF3] placeholder-[#8B949E] focus:border-[#58A6FF] focus:outline-none"
              />
            </div>

            {/* 섹터 */}
            <div>
              <label className="mb-1 block text-xs text-[#8B949E]">섹터</label>
              <select
                value={filters.sector || ''}
                onChange={(e) => handleFilterChange('sector', e.target.value || undefined)}
                className="w-full rounded border border-[#30363D] bg-[#0D1117] px-3 py-2 text-sm text-[#E6EDF3] focus:border-[#58A6FF] focus:outline-none"
              >
                {SECTORS.map((sector) => (
                  <option key={sector.value} value={sector.value}>
                    {sector.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* 결과 영역 */}
        <div className="rounded-lg border border-[#30363D] bg-[#161B22]">
          {/* 결과 헤더 */}
          <div className="flex items-center justify-between border-b border-[#30363D] px-4 py-3">
            <div className="flex items-center gap-2">
              <Search className="h-5 w-5 text-[#58A6FF]" />
              <h2 className="text-lg font-semibold text-[#E6EDF3]">검색 결과</h2>
              {stocks && (
                <span className="rounded-full bg-[#238636]/20 px-2 py-0.5 text-xs text-[#3FB950]">
                  {stocks.length}개 종목
                </span>
              )}
            </div>
            {stocks && stocks.length > 0 && (
              <div className="flex items-center gap-2">
                {/* AI 키워드 생성 버튼 */}
                <button
                  onClick={handleGenerateKeywords}
                  disabled={isGeneratingKeywords}
                  className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-all ${
                    isGeneratingKeywords
                      ? 'bg-[#21262D] text-[#8B949E] cursor-not-allowed'
                      : 'bg-[#8957E5] hover:bg-[#9D6EE8] text-white'
                  }`}
                >
                  <Sparkles className={`h-3.5 w-3.5 ${isGeneratingKeywords ? 'animate-pulse' : ''}`} />
                  <span>{isGeneratingKeywords ? 'AI 생성 중...' : 'AI 키워드'}</span>
                </button>

                {/* 새로고침 버튼 */}
                <button
                  onClick={() => refetch()}
                  className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium text-[#8B949E] hover:bg-[#21262D] hover:text-[#E6EDF3] transition-all"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  <span>새로고침</span>
                </button>
              </div>
            )}
          </div>

          {/* 로딩 상태 */}
          {isLoading && (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="h-8 w-8 animate-spin text-[#58A6FF]" />
            </div>
          )}

          {/* 에러 상태 */}
          {error && (
            <div className="m-4 flex items-center gap-2 rounded-lg border border-[#F85149]/20 bg-[#F85149]/10 p-4">
              <AlertCircle className="h-5 w-5 flex-shrink-0 text-[#F85149]" />
              <div>
                <p className="text-sm font-medium text-[#E6EDF3]">데이터를 불러올 수 없습니다</p>
                <p className="text-xs text-[#8B949E]">잠시 후 다시 시도해주세요</p>
              </div>
            </div>
          )}

          {/* 빈 결과 */}
          {!isLoading && !error && stocks && stocks.length === 0 && (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <Search className="mb-4 h-12 w-12 text-[#30363D]" />
              <h3 className="mb-2 text-lg font-medium text-[#E6EDF3]">조건에 맞는 종목이 없습니다</h3>
              <p className="mb-4 text-sm text-[#8B949E]">필터 조건을 완화해보세요</p>
              <button
                onClick={handleReset}
                className="rounded-lg bg-[#238636] px-4 py-2 text-sm font-medium text-white hover:bg-[#2EA043]"
              >
                필터 초기화
              </button>
            </div>
          )}

          {/* 테이블 */}
          {!isLoading && !error && stocks && stocks.length > 0 && (
            <div className="p-4">
              <ScreenerTable
                stocks={stocks}
                keywords={keywords}
                isLoadingKeywords={isLoadingKeywords || isGeneratingKeywords}
              />
            </div>
          )}
        </div>

        {/* 면책조항 */}
        <div className="mt-6 rounded-lg border border-[#30363D] bg-[#161B22] p-4">
          <p className="text-xs text-[#8B949E]">
            <span className="font-medium text-[#E6EDF3]">주의:</span> 본 스크리너는 정보 제공 목적이며, 투자 권유가 아닙니다.
            스크리너 결과는 과거 데이터 기반이며, 미래 성과를 보장하지 않습니다.
            투자 결정 전 반드시 개별 종목 분석을 수행하세요.
          </p>
        </div>
      </div>
    </div>
  );
}

// 페이지 컴포넌트 (AuthGuard + Suspense로 감싸기)
export default function ScreenerPage() {
  return (
    <AuthGuard>
      <Suspense fallback={<ScreenerLoading />}>
        <ScreenerContent />
      </Suspense>
    </AuthGuard>
  );
}

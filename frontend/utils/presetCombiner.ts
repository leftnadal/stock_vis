/**
 * Preset Combiner - 캐스케이딩 필터 결합 로직
 *
 * 첫 번째 프리셋으로 기본 결과를 도출하고,
 * 두 번째 프리셋은 그 결과 내에서 추가 필터링하는 시스템
 */

import type {
  ScreenerPreset,
  ScreenerFilters,
  CombinedPresetResult,
  FilterConflict,
  FilterConflictType,
  FILTER_METADATA,
} from '@/types/screener';
import { FILTER_METADATA as FilterMeta } from '@/types/screener';

/**
 * 프리셋의 filters_json을 ScreenerFilters 형식으로 정규화
 */
export function normalizePresetFilters(filtersJson: Record<string, unknown>): ScreenerFilters {
  const normalized: ScreenerFilters = {};

  // PER 관련
  if (filtersJson.pe_ratio_max !== undefined) normalized.per_max = filtersJson.pe_ratio_max as number;
  if (filtersJson.pe_ratio_min !== undefined) normalized.per_min = filtersJson.pe_ratio_min as number;

  // ROE 관련
  if (filtersJson.roe_min !== undefined) normalized.roe_min = filtersJson.roe_min as number;

  // 시가총액
  if (filtersJson.market_cap_min !== undefined) normalized.market_cap_min = filtersJson.market_cap_min as number;
  if (filtersJson.market_cap_max !== undefined) normalized.market_cap_max = filtersJson.market_cap_max as number;

  // 배당
  if (filtersJson.dividend_min !== undefined) normalized.dividend_min = filtersJson.dividend_min as number;

  // 거래량
  if (filtersJson.volume_min !== undefined) normalized.volume_min = filtersJson.volume_min as number;

  // 베타
  if (filtersJson.beta_min !== undefined) normalized.beta_min = filtersJson.beta_min as number;
  if (filtersJson.beta_max !== undefined) normalized.beta_max = filtersJson.beta_max as number;

  // 섹터
  if (filtersJson.sector) normalized.sector = filtersJson.sector as string;

  // Market Movers 지표
  if (filtersJson.rvol_min !== undefined) normalized.rvol_min = filtersJson.rvol_min as number;
  if (filtersJson.trend_strength_min !== undefined) normalized.trend_strength_min = filtersJson.trend_strength_min as number;
  if (filtersJson.sector_alpha_min !== undefined) normalized.sector_alpha_min = filtersJson.sector_alpha_min as number;
  if (filtersJson.volatility_pct_min !== undefined) normalized.volatility_pct_min = filtersJson.volatility_pct_min as number;

  // 기술적 지표
  if (filtersJson.rsi_min !== undefined) normalized.rsi_min = filtersJson.rsi_min as number;
  if (filtersJson.rsi_max !== undefined) normalized.rsi_max = filtersJson.rsi_max as number;

  // 재무비율
  if (filtersJson.debt_equity_max !== undefined) normalized.debt_equity_max = filtersJson.debt_equity_max as number;
  if (filtersJson.current_ratio_min !== undefined) normalized.current_ratio_min = filtersJson.current_ratio_min as number;

  // Enhanced 성장 지표
  if (filtersJson.eps_growth_min !== undefined) normalized.eps_growth_min = filtersJson.eps_growth_min as number;
  if (filtersJson.eps_growth_max !== undefined) normalized.eps_growth_max = filtersJson.eps_growth_max as number;
  if (filtersJson.revenue_growth_min !== undefined) normalized.revenue_growth_min = filtersJson.revenue_growth_min as number;
  if (filtersJson.revenue_growth_max !== undefined) normalized.revenue_growth_max = filtersJson.revenue_growth_max as number;

  // 변동률
  if (filtersJson.change_percent_min !== undefined) normalized.change_percent_min = filtersJson.change_percent_min as number;
  if (filtersJson.change_percent_max !== undefined) normalized.change_percent_max = filtersJson.change_percent_max as number;

  return normalized;
}

/**
 * 값을 사람이 읽기 쉬운 형식으로 포맷
 */
function formatFilterValue(key: string, value: number | string | string[]): string {
  const meta = FilterMeta[key];
  if (!meta) return String(value);

  if (key === 'market_cap_min' || key === 'market_cap_max') {
    const billions = (value as number) / 1_000_000_000;
    return `$${billions.toFixed(0)}B`;
  }

  if (key === 'volume_min' || key === 'volume_max') {
    const millions = (value as number) / 1_000_000;
    return `${millions.toFixed(0)}M`;
  }

  return meta.unit ? `${value}${meta.unit}` : String(value);
}

/**
 * range_max 필터 병합
 * 더 작은 값(더 엄격)이 적용됨 - 교집합이므로 충돌 아님
 */
function mergeRangeMax(
  firstValue: number,
  secondValue: number
): number {
  // 더 작은 값이 더 엄격 (교집합)
  return Math.min(firstValue, secondValue);
}

/**
 * range_min 필터 병합
 * 더 큰 값(더 엄격)이 적용됨 - 교집합이므로 충돌 아님
 */
function mergeRangeMin(
  firstValue: number,
  secondValue: number
): number {
  // 더 큰 값이 더 엄격 (교집합)
  return Math.max(firstValue, secondValue);
}

/**
 * min/max 범위 상충 검사 (교집합이 없는 경우)
 * 예: per_max=15 이미 있는데 per_min=20 추가하려 함 → 교집합 없음
 */
function checkRangeContradiction(
  effectiveFilters: ScreenerFilters,
  key: string,
  value: number
): { isContradiction: boolean; conflictingKey?: string; conflictingValue?: number } {
  const meta = FilterMeta[key];
  if (!meta?.pairKey) return { isContradiction: false };

  const pairValue = effectiveFilters[meta.pairKey as keyof ScreenerFilters] as number | undefined;

  if (pairValue === undefined) return { isContradiction: false };

  // range_max(≤X)인데 기존 min(≥Y)이 X보다 크면 → 교집합 없음
  // 예: per_max=15 추가하려는데 이미 per_min=20 → 불가능
  if (meta.type === 'range_max' && value < pairValue) {
    return { isContradiction: true, conflictingKey: meta.pairKey, conflictingValue: pairValue };
  }

  // range_min(≥X)인데 기존 max(≤Y)가 X보다 작으면 → 교집합 없음
  // 예: per_min=20 추가하려는데 이미 per_max=15 → 불가능
  if (meta.type === 'range_min' && value > pairValue) {
    return { isContradiction: true, conflictingKey: meta.pairKey, conflictingValue: pairValue };
  }

  return { isContradiction: false };
}

/**
 * 여러 프리셋의 필터를 결합 (캐스케이딩)
 *
 * 충돌 = 교집합이 없는 경우만
 * - 같은 키의 범위 필터: 교집합으로 병합 (충돌 아님)
 * - min/max 쌍이 교집합 없음: 진짜 충돌 (1차 유지, 2차 무시)
 * - 이산값(섹터 등) 불일치: 진짜 충돌 (1차 유지, 2차 무시)
 *
 * @param presets - 적용 순서대로 정렬된 프리셋 배열
 * @returns 결합된 필터와 충돌 정보
 */
export function combinePresetFilters(presets: ScreenerPreset[]): CombinedPresetResult {
  if (presets.length === 0) {
    return {
      effectiveFilters: {},
      conflicts: [],
      hasWarnings: false,
      appliedPresetIds: [],
      filterSources: {},
    };
  }

  const conflicts: FilterConflict[] = [];
  const effectiveFilters: ScreenerFilters = {};
  const filterSources: Record<string, number> = {};
  const appliedPresetIds: number[] = presets.map(p => p.id);

  // 1차 프리셋 필터 적용 (기준)
  const firstPreset = presets[0];
  const firstFilters = normalizePresetFilters(firstPreset.filters_json || {});

  for (const [key, value] of Object.entries(firstFilters)) {
    if (value !== undefined) {
      (effectiveFilters as Record<string, unknown>)[key] = value;
      filterSources[key] = firstPreset.id;
    }
  }

  // 2차+ 프리셋 순회
  for (let i = 1; i < presets.length; i++) {
    const preset = presets[i];
    const presetFilters = normalizePresetFilters(preset.filters_json || {});

    for (const [key, value] of Object.entries(presetFilters)) {
      if (value === undefined) continue;

      const meta = FilterMeta[key];
      const existingValue = effectiveFilters[key as keyof ScreenerFilters];
      const sourcePresetId = filterSources[key];
      const sourcePresetName = sourcePresetId
        ? presets.find(p => p.id === sourcePresetId)?.name || '이전 프리셋'
        : '이전 프리셋';

      // 새 필터 (이전에 없던 키)
      if (existingValue === undefined) {
        // min/max 쌍 교집합 검사
        if (meta?.type === 'range_min' || meta?.type === 'range_max') {
          const check = checkRangeContradiction(effectiveFilters, key, value as number);
          if (check.isContradiction) {
            // 교집합 없음 → 진짜 충돌, 2차 필터 무시
            const conflictingSourceId = filterSources[check.conflictingKey!];
            const conflictingPresetName = conflictingSourceId
              ? presets.find(p => p.id === conflictingSourceId)?.name || '이전 프리셋'
              : '이전 프리셋';

            conflicts.push({
              filterKey: key,
              filterLabel: meta?.labelKo || key,
              firstPresetValue: check.conflictingValue!,
              secondPresetValue: value as number,
              conflictType: 'range_conflict',
              resolution: `${conflictingPresetName}의 ${FilterMeta[check.conflictingKey!]?.labelKo || check.conflictingKey}(${formatFilterValue(check.conflictingKey!, check.conflictingValue!)}) 유지, ${preset.name}의 ${meta.labelKo}(${formatFilterValue(key, value as number)}) 적용 불가 (교집합 없음)`,
              firstPresetName: conflictingPresetName,
              secondPresetName: preset.name,
            });
            continue;
          }
        }

        // 교집합 있음 또는 범위 필터 아님 → 정상 적용
        (effectiveFilters as Record<string, unknown>)[key] = value;
        filterSources[key] = preset.id;
        continue;
      }

      // 같은 키가 이미 있는 경우
      if (meta?.type === 'range_max') {
        // 교집합: 더 작은 값 (더 엄격)
        const mergedValue = mergeRangeMax(existingValue as number, value as number);
        (effectiveFilters as Record<string, unknown>)[key] = mergedValue;
        // 더 엄격한 값이 적용되면 소스 업데이트
        if (mergedValue === value) {
          filterSources[key] = preset.id;
        }
      } else if (meta?.type === 'range_min') {
        // 교집합: 더 큰 값 (더 엄격)
        const mergedValue = mergeRangeMin(existingValue as number, value as number);
        (effectiveFilters as Record<string, unknown>)[key] = mergedValue;
        if (mergedValue === value) {
          filterSources[key] = preset.id;
        }
      } else if (meta?.type === 'discrete') {
        // 이산값: 값이 다르면 충돌 (1차 유지)
        if (existingValue !== value) {
          conflicts.push({
            filterKey: key,
            filterLabel: meta?.labelKo || key,
            firstPresetValue: existingValue as string,
            secondPresetValue: value as string,
            conflictType: 'value_override',
            resolution: `${sourcePresetName}의 ${meta?.labelKo}(${existingValue}) 유지, ${preset.name}의 값(${value}) 적용 불가`,
            firstPresetName: sourcePresetName,
            secondPresetName: preset.name,
          });
        }
        // 1차 값 유지 (아무것도 안 함)
      } else {
        // 기타: 2차 값으로 덮어씀 (충돌 없음)
        (effectiveFilters as Record<string, unknown>)[key] = value;
        filterSources[key] = preset.id;
      }
    }
  }

  return {
    effectiveFilters,
    conflicts,
    hasWarnings: conflicts.length > 0,
    appliedPresetIds,
    filterSources,
  };
}

/**
 * 적용된 필터를 사람이 읽기 쉬운 형식으로 변환
 */
export function formatAppliedFilters(
  filters: ScreenerFilters,
  filterSources: Record<string, number>,
  presets: ScreenerPreset[]
): Array<{ key: string; label: string; value: string; presetName: string; presetId: number }> {
  const result: Array<{ key: string; label: string; value: string; presetName: string; presetId: number }> = [];

  for (const [key, value] of Object.entries(filters)) {
    if (value === undefined) continue;

    const meta = FilterMeta[key];
    const presetId = filterSources[key];
    const preset = presets.find(p => p.id === presetId);

    let displayValue: string;
    if (meta?.type === 'range_max') {
      displayValue = `≤ ${formatFilterValue(key, value as number)}`;
    } else if (meta?.type === 'range_min') {
      displayValue = `≥ ${formatFilterValue(key, value as number)}`;
    } else {
      displayValue = formatFilterValue(key, value as number | string);
    }

    result.push({
      key,
      label: meta?.labelKo || key,
      value: displayValue,
      presetName: preset?.name || '수동 입력',
      presetId: presetId || 0,
    });
  }

  return result;
}

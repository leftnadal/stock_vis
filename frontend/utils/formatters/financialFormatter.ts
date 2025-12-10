/**
 * Financial Number Formatting Utilities
 *
 * Provides consistent formatting for financial statements with configurable units.
 */

export type FinancialUnit = 'auto' | 'B' | 'M' | 'K' | 'raw';

export interface FormatConfig {
  unit: FinancialUnit;
  decimalPlaces: number;
  divisor: number;
  suffix: string;
}

/**
 * Determines the optimal unit based on the maximum value in a dataset.
 *
 * Thresholds:
 * - >= 1,000,000,000 → Billion (B)
 * - >= 1,000,000 → Million (M)
 * - >= 1,000 → Thousand (K)
 * - < 1,000 → Raw value
 *
 * @param values Array of numeric values to analyze
 * @returns FormatConfig object with optimal unit settings
 */
export function determineOptimalUnit(values: number[]): FormatConfig {
  // Filter out null/undefined/NaN values and get absolute values
  const validValues = values
    .filter((v) => v !== null && v !== undefined && !isNaN(v))
    .map((v) => Math.abs(v));

  if (validValues.length === 0) {
    return {
      unit: 'raw',
      decimalPlaces: 2,
      divisor: 1,
      suffix: '',
    };
  }

  const maxValue = Math.max(...validValues);

  if (maxValue >= 1_000_000_000) {
    return {
      unit: 'B',
      decimalPlaces: 2,
      divisor: 1_000_000_000,
      suffix: 'B',
    };
  }

  if (maxValue >= 1_000_000) {
    return {
      unit: 'M',
      decimalPlaces: 2,
      divisor: 1_000_000,
      suffix: 'M',
    };
  }

  if (maxValue >= 1_000) {
    return {
      unit: 'K',
      decimalPlaces: 2,
      divisor: 1_000,
      suffix: 'K',
    };
  }

  return {
    unit: 'raw',
    decimalPlaces: 2,
    divisor: 1,
    suffix: '',
  };
}

/**
 * Get format configuration for a specific unit.
 *
 * @param unit The unit to format with ('B', 'M', 'K', or 'raw')
 * @returns FormatConfig object
 */
export function getFormatConfig(unit: FinancialUnit): FormatConfig {
  switch (unit) {
    case 'B':
      return {
        unit: 'B',
        decimalPlaces: 2,
        divisor: 1_000_000_000,
        suffix: 'B',
      };
    case 'M':
      return {
        unit: 'M',
        decimalPlaces: 2,
        divisor: 1_000_000,
        suffix: 'M',
      };
    case 'K':
      return {
        unit: 'K',
        decimalPlaces: 2,
        divisor: 1_000,
        suffix: 'K',
      };
    case 'raw':
      return {
        unit: 'raw',
        decimalPlaces: 2,
        divisor: 1,
        suffix: '',
      };
    default:
      // 'auto' should be handled by determineOptimalUnit
      return {
        unit: 'raw',
        decimalPlaces: 2,
        divisor: 1,
        suffix: '',
      };
  }
}

/**
 * Format a financial value according to the provided configuration.
 * Includes thousand separators for better readability.
 *
 * @param value The numeric value to format
 * @param config FormatConfig object
 * @returns Formatted string (e.g., "1.23B", "456.78M", "1,234,567")
 */
export function formatFinancialValue(value: number | null | undefined, config: FormatConfig): string {
  if (value === null || value === undefined || isNaN(value)) {
    return '-';
  }

  const dividedValue = value / config.divisor;

  // For B, M, K units, show with decimal places and suffix
  if (config.suffix) {
    const formattedNumber = new Intl.NumberFormat('en-US', {
      minimumFractionDigits: config.decimalPlaces,
      maximumFractionDigits: config.decimalPlaces,
    }).format(dividedValue);
    return `${formattedNumber}${config.suffix}`;
  }

  // For raw values, show with thousand separators (no decimal for large integers)
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(dividedValue);
}

/**
 * Format raw value for tooltips with full precision.
 * Uses locale-aware formatting with thousand separators.
 *
 * @param value The numeric value to format
 * @returns Formatted string with thousand separators (e.g., "1,234,567.89")
 */
export function formatRawValue(value: number | null | undefined): string {
  if (value === null || value === undefined || isNaN(value)) {
    return '-';
  }

  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

/**
 * Extract all numeric values from financial data for unit determination.
 *
 * @param data Array of financial data objects
 * @param excludeKeys Keys to exclude from extraction (e.g., dates, IDs)
 * @returns Array of all numeric values
 */
export function extractNumericValues(
  data: Record<string, any>[],
  excludeKeys: string[] = ['fiscal_date_ending', 'reported_date', 'fiscal_year', 'fiscal_quarter', 'period_type', 'stock', 'id', 'created_at', 'currency']
): number[] {
  const values: number[] = [];

  data.forEach((item) => {
    Object.entries(item).forEach(([key, value]) => {
      if (!excludeKeys.includes(key) && typeof value === 'number' && !isNaN(value)) {
        values.push(value);
      }
    });
  });

  return values;
}

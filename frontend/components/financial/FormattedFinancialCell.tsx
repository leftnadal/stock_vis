/**
 * FormattedFinancialCell Component
 *
 * Displays a formatted financial value.
 * Supports positive/negative styling and null value handling.
 */

import React from 'react';
import { FormatConfig, formatFinancialValue } from '@/utils/formatters/financialFormatter';

interface FormattedFinancialCellProps {
  value: number | null | undefined;
  config: FormatConfig;
  className?: string;
  showColorCoding?: boolean; // Red for negative, default for positive
}

export default function FormattedFinancialCell({
  value,
  config,
  className = '',
  showColorCoding = true,
}: FormattedFinancialCellProps) {
  if (value === null || value === undefined || isNaN(value)) {
    return (
      <td className={`text-right py-2 px-4 text-sm text-gray-400 dark:text-gray-500 ${className}`}>
        -
      </td>
    );
  }

  const formattedValue = formatFinancialValue(value, config);
  const isNegative = value < 0;

  const colorClass = showColorCoding && isNegative
    ? 'text-red-600 dark:text-red-400'
    : 'text-gray-900 dark:text-white';

  return (
    <td className={`text-right py-2 px-4 text-sm ${colorClass} ${className}`}>
      {formattedValue}
    </td>
  );
}

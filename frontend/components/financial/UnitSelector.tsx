/**
 * UnitSelector Component
 *
 * Provides a button group for selecting financial data display units.
 * Supports Auto, Billion, Million, Thousand, and Raw value display.
 */

import React from 'react';
import { FinancialUnit } from '@/utils/formatters/financialFormatter';

interface UnitSelectorProps {
  selectedUnit: FinancialUnit;
  onChange: (unit: FinancialUnit) => void;
  className?: string;
}

const unitOptions: { value: FinancialUnit; label: string; tooltip: string }[] = [
  { value: 'auto', label: 'Auto', tooltip: 'Automatically determine optimal unit' },
  { value: 'B', label: 'B', tooltip: 'Display in Billions' },
  { value: 'M', label: 'M', tooltip: 'Display in Millions' },
  { value: 'K', label: 'K', tooltip: 'Display in Thousands' },
  { value: 'raw', label: 'Raw', tooltip: 'Display raw values' },
];

export default function UnitSelector({ selectedUnit, onChange, className = '' }: UnitSelectorProps) {
  return (
    <div className={`flex items-center space-x-1 ${className}`} role="group" aria-label="Financial unit selector">
      <span className="text-xs text-gray-500 dark:text-gray-400 mr-2">Unit:</span>
      {unitOptions.map((option) => (
        <button
          key={option.value}
          type="button"
          onClick={() => onChange(option.value)}
          className={`
            px-3 py-1.5 text-xs font-medium rounded-md transition-all duration-200
            focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1
            dark:focus:ring-offset-gray-800
            ${
              selectedUnit === option.value
                ? 'bg-blue-600 text-white shadow-sm hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
            }
          `}
          aria-pressed={selectedUnit === option.value}
          aria-label={option.tooltip}
          title={option.tooltip}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

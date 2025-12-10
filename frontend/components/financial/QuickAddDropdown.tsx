/**
 * QuickAddDropdown Component
 *
 * Dropdown menu for quickly adding financial fields to the table.
 * Fields are organized by groups with tooltips and disabled state for already selected items.
 */

'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Plus, ChevronDown, Search, TrendingUp, TrendingDown, Wallet, DollarSign } from 'lucide-react';
import { FinancialTabType, FinancialFieldMeta, getFieldMeta } from '@/constants/financialDefaults';

interface FieldGroup {
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  fields: string[];
}

interface QuickAddDropdownProps {
  tabType: FinancialTabType;
  selectedFields: string[];
  onAddField: (fieldKey: string) => void;
  className?: string;
}

// Field groups for each tab type
const FIELD_GROUPS: Record<FinancialTabType, FieldGroup[]> = {
  'balance-sheet': [
    {
      label: '자산',
      icon: TrendingUp,
      fields: [
        'total_assets',
        'total_current_assets',
        'cash_and_cash_equivalents_at_carrying_value',
        'inventory',
        'current_net_receivables',
        'total_non_current_assets',
        'property_plant_equipment',
        'intangible_assets',
        'goodwill',
      ],
    },
    {
      label: '부채',
      icon: TrendingDown,
      fields: [
        'total_liabilities',
        'total_current_liabilities',
        'current_accounts_payable',
        'short_term_debt',
        'total_non_current_liabilities',
        'long_term_debt',
      ],
    },
    {
      label: '자본',
      icon: Wallet,
      fields: [
        'total_shareholder_equity',
        'retained_earnings',
        'common_stock',
        'treasury_stock',
        'common_stock_shares_outstanding',
      ],
    },
  ],
  'income-statement': [
    {
      label: '수익',
      icon: DollarSign,
      fields: ['total_revenue', 'gross_profit', 'operating_income', 'net_income', 'ebitda', 'ebit'],
    },
    {
      label: '비용',
      icon: TrendingDown,
      fields: [
        'cost_of_revenue',
        'operating_expenses',
        'selling_general_and_administrative',
        'research_and_development',
        'depreciation_and_amortization',
      ],
    },
    {
      label: '기타',
      icon: TrendingUp,
      fields: [
        'interest_income',
        'interest_expense',
        'income_tax_expense',
        'basic_eps',
        'diluted_eps',
      ],
    },
  ],
  'cash-flow': [
    {
      label: '영업활동',
      icon: DollarSign,
      fields: [
        'operating_cashflow',
        'net_income',
        'change_in_receivables',
        'change_in_inventory',
        'change_in_operating_assets',
        'change_in_operating_liabilities',
      ],
    },
    {
      label: '투자활동',
      icon: TrendingUp,
      fields: ['cashflow_from_investment', 'capital_expenditures'],
    },
    {
      label: '재무활동',
      icon: Wallet,
      fields: [
        'cashflow_from_financing',
        'dividend_payout',
        'payments_for_repurchase_of_common_stock',
        'proceeds_from_repayments_of_short_term_debt',
      ],
    },
  ],
};

export default function QuickAddDropdown({
  tabType,
  selectedFields,
  onAddField,
  className = '',
}: QuickAddDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen]);

  const groups = FIELD_GROUPS[tabType] || [];

  // Filter fields by search query
  const filteredGroups = groups.map((group) => {
    if (!searchQuery) return group;

    const matchingFields = group.fields.filter((fieldKey) => {
      const meta = getFieldMeta(tabType, fieldKey);
      if (!meta) return false;

      const query = searchQuery.toLowerCase();
      return (
        meta.labelKo.toLowerCase().includes(query) ||
        meta.labelEn.toLowerCase().includes(query) ||
        meta.description.toLowerCase().includes(query)
      );
    });

    return { ...group, fields: matchingFields };
  }).filter((group) => group.fields.length > 0);

  const handleAddField = (fieldKey: string) => {
    if (!selectedFields.includes(fieldKey)) {
      onAddField(fieldKey);
      setSearchQuery('');
    }
  };

  return (
    <div ref={dropdownRef} className={`relative ${className}`}>
      {/* Trigger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
      >
        <Plus className="w-4 h-4" />
        빠른 추가
        <ChevronDown
          className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`}
        />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute top-full left-0 mt-1 w-80 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-10 max-h-96 overflow-hidden flex flex-col">
          {/* Search */}
          <div className="p-3 border-b border-gray-200 dark:border-gray-700">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="항목 검색..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>

          {/* Groups */}
          <div className="flex-1 overflow-y-auto">
            {filteredGroups.length === 0 ? (
              <div className="p-4 text-center text-sm text-gray-500 dark:text-gray-400">
                검색 결과가 없습니다.
              </div>
            ) : (
              filteredGroups.map((group) => (
                <FieldGroupSection
                  key={group.label}
                  group={group}
                  tabType={tabType}
                  selectedFields={selectedFields}
                  onAddField={handleAddField}
                />
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}

interface FieldGroupSectionProps {
  group: FieldGroup;
  tabType: FinancialTabType;
  selectedFields: string[];
  onAddField: (fieldKey: string) => void;
}

function FieldGroupSection({
  group,
  tabType,
  selectedFields,
  onAddField,
}: FieldGroupSectionProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const Icon = group.icon;

  return (
    <div className="border-b border-gray-200 dark:border-gray-700 last:border-b-0">
      {/* Group Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center gap-2 px-4 py-2.5 text-left text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
      >
        <Icon className="w-4 h-4 text-gray-500 dark:text-gray-400" />
        {group.label}
        <ChevronDown
          className={`ml-auto w-4 h-4 text-gray-400 transition-transform ${
            isExpanded ? 'rotate-180' : ''
          }`}
        />
      </button>

      {/* Group Items */}
      {isExpanded && (
        <div className="py-1">
          {group.fields.map((fieldKey) => {
            const meta = getFieldMeta(tabType, fieldKey);
            if (!meta) return null;

            const isSelected = selectedFields.includes(fieldKey);

            return (
              <button
                key={fieldKey}
                onClick={() => onAddField(fieldKey)}
                disabled={isSelected}
                className={`w-full text-left px-4 py-2 text-sm transition-colors ${
                  isSelected
                    ? 'text-gray-400 dark:text-gray-600 cursor-not-allowed bg-gray-50 dark:bg-gray-700/30'
                    : 'text-gray-700 dark:text-gray-300 hover:bg-blue-50 dark:hover:bg-blue-900/20'
                }`}
                title={meta.description}
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="font-medium truncate">{meta.labelKo}</div>
                    <div className="text-xs text-gray-500 dark:text-gray-400 truncate">
                      {meta.labelEn}
                    </div>
                  </div>
                  {isSelected && (
                    <span className="ml-2 text-xs text-gray-400 dark:text-gray-600">
                      ✓
                    </span>
                  )}
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

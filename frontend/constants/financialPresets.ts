/**
 * Financial Field Presets Configuration
 *
 * Pre-defined sets of financial fields for common analysis scenarios.
 * Users can quickly apply these presets instead of manually selecting fields.
 */

import { FinancialTabType } from './financialDefaults';
import { TrendingUp, PieChart, Target, Shield, Zap, DollarSign } from 'lucide-react';

export interface FieldPreset {
  id: string;
  name: string;
  description: string;
  icon: string; // Icon name from lucide-react
  fields: string[];
}

// Balance Sheet Presets
export const BALANCE_SHEET_PRESETS: FieldPreset[] = [
  {
    id: 'liquidity',
    name: '유동성 분석',
    description: '현금 흐름과 단기 지급능력 파악',
    icon: 'Droplets',
    fields: [
      'total_current_assets',
      'cash_and_cash_equivalents_at_carrying_value',
      'cash_and_short_term_investments',
      'current_net_receivables',
      'total_current_liabilities',
      'current_accounts_payable',
      'short_term_debt',
    ],
  },
  {
    id: 'leverage',
    name: '부채 구조',
    description: '부채 비율과 재무 안정성 분석',
    icon: 'Scale',
    fields: [
      'total_assets',
      'total_liabilities',
      'total_shareholder_equity',
      'short_term_debt',
      'long_term_debt',
      'total_current_liabilities',
      'total_non_current_liabilities',
    ],
  },
  {
    id: 'asset-quality',
    name: '자산 구성',
    description: '자산의 질과 배분 현황',
    icon: 'Layers',
    fields: [
      'total_assets',
      'total_current_assets',
      'total_non_current_assets',
      'property_plant_equipment',
      'intangible_assets',
      'goodwill',
      'inventory',
    ],
  },
  {
    id: 'shareholder-value',
    name: '주주 가치',
    description: '자본 구조와 주주 지분',
    icon: 'Users',
    fields: [
      'total_shareholder_equity',
      'retained_earnings',
      'common_stock',
      'treasury_stock',
      'common_stock_shares_outstanding',
    ],
  },
];

// Income Statement Presets
export const INCOME_STATEMENT_PRESETS: FieldPreset[] = [
  {
    id: 'profitability',
    name: '수익성 분석',
    description: '매출과 이익률 중심',
    icon: 'TrendingUp',
    fields: [
      'total_revenue',
      'gross_profit',
      'operating_income',
      'net_income',
      'ebitda',
      'diluted_eps',
    ],
  },
  {
    id: 'cost-structure',
    name: '비용 구조',
    description: 'R&D, 마케팅, 운영 비용 분석',
    icon: 'PieChart',
    fields: [
      'total_revenue',
      'cost_of_revenue',
      'research_and_development',
      'selling_general_and_administrative',
      'operating_expenses',
      'depreciation_and_amortization',
      'interest_expense',
    ],
  },
  {
    id: 'margin-analysis',
    name: '마진 분석',
    description: '단계별 이익률 계산용',
    icon: 'Target',
    fields: [
      'total_revenue',
      'cost_of_revenue',
      'gross_profit',
      'operating_income',
      'ebitda',
      'income_before_tax',
      'net_income',
    ],
  },
  {
    id: 'growth-investment',
    name: '성장 투자',
    description: 'R&D와 미래 성장 투자 현황',
    icon: 'Zap',
    fields: [
      'total_revenue',
      'research_and_development',
      'selling_general_and_administrative',
      'operating_income',
      'net_income',
    ],
  },
];

// Cash Flow Statement Presets
export const CASH_FLOW_PRESETS: FieldPreset[] = [
  {
    id: 'cash-generation',
    name: '현금 창출력',
    description: '영업활동 현금흐름 중심',
    icon: 'DollarSign',
    fields: [
      'operating_cashflow',
      'net_income',
      'proceeds_from_operating_activities',
      'payments_for_operating_activities',
      'change_in_receivables',
      'change_in_inventory',
    ],
  },
  {
    id: 'capital-allocation',
    name: '자본 배분',
    description: '투자와 재무활동 분석',
    icon: 'TrendingUp',
    fields: [
      'operating_cashflow',
      'capital_expenditures',
      'cashflow_from_investment',
      'cashflow_from_financing',
      'dividend_payout',
      'payments_for_repurchase_of_common_stock',
    ],
  },
  {
    id: 'shareholder-return',
    name: '주주 환원',
    description: '배당과 자사주 매입',
    icon: 'Gift',
    fields: [
      'operating_cashflow',
      'net_income',
      'dividend_payout',
      'payments_for_repurchase_of_common_stock',
      'cashflow_from_financing',
    ],
  },
  {
    id: 'working-capital',
    name: '운전자본 관리',
    description: '매출채권, 재고 변동 분석',
    icon: 'RefreshCw',
    fields: [
      'operating_cashflow',
      'change_in_receivables',
      'change_in_inventory',
      'change_in_operating_assets',
      'change_in_operating_liabilities',
    ],
  },
];

// Get presets for a specific tab type
export function getPresetsForTab(tabType: FinancialTabType): FieldPreset[] {
  switch (tabType) {
    case 'balance-sheet':
      return BALANCE_SHEET_PRESETS;
    case 'income-statement':
      return INCOME_STATEMENT_PRESETS;
    case 'cash-flow':
      return CASH_FLOW_PRESETS;
    default:
      return [];
  }
}

// Get preset by ID
export function getPresetById(tabType: FinancialTabType, presetId: string): FieldPreset | undefined {
  const presets = getPresetsForTab(tabType);
  return presets.find((p) => p.id === presetId);
}

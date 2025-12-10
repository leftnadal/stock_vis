/**
 * Financial Field Groups Configuration
 *
 * Groups of related financial fields for quick selection via dropdown.
 * Based on @investment-advisor recommendations for analysis categories.
 */

import { FinancialTabType } from './financialDefaults';

export interface FieldGroup {
  id: string;
  icon: string; // Emoji for display
  label: string;
  description: string;
  fields: string[];
}

// ============================================
// Balance Sheet Groups
// ============================================
export const BALANCE_SHEET_GROUPS: FieldGroup[] = [
  {
    id: 'bs_recommended',
    icon: '\u2b50',
    label: '추천 (입문자용)',
    description: '재무 건전성의 핵심 항목',
    fields: [
      'total_assets',
      'cash_and_cash_equivalents_at_carrying_value',
      'total_liabilities',
      'total_shareholder_equity',
      'retained_earnings',
    ],
  },
  {
    id: 'bs_stability',
    icon: '\ud83c\udfe6',
    label: '안정성 지표',
    description: '단기 지급 능력 평가',
    fields: [
      'total_current_assets',
      'total_current_liabilities',
      'cash_and_cash_equivalents_at_carrying_value',
      'short_term_debt',
      'long_term_debt',
      'current_net_receivables',
    ],
  },
  {
    id: 'bs_asset',
    icon: '\ud83d\udc8e',
    label: '자산 구성',
    description: '보유 자산 종류별 분석',
    fields: [
      'total_current_assets',
      'total_non_current_assets',
      'inventory',
      'property_plant_equipment',
      'intangible_assets',
      'goodwill',
      'long_term_investments',
    ],
  },
  {
    id: 'bs_capital',
    icon: '\ud83c\udfd7\ufe0f',
    label: '자본 구조',
    description: '부채와 자본 비율 (레버리지)',
    fields: [
      'total_liabilities',
      'total_shareholder_equity',
      'long_term_debt',
      'short_term_debt',
      'retained_earnings',
      'common_stock',
      'treasury_stock',
    ],
  },
];

// ============================================
// Income Statement Groups
// ============================================
export const INCOME_STATEMENT_GROUPS: FieldGroup[] = [
  {
    id: 'is_recommended',
    icon: '\u2b50',
    label: '추천 (입문자용)',
    description: '수익성 핵심 항목',
    fields: [
      'total_revenue',
      'gross_profit',
      'operating_income',
      'net_income',
      'diluted_eps',
    ],
  },
  {
    id: 'is_profitability',
    icon: '\ud83d\udcb0',
    label: '수익성 지표',
    description: '이익 창출 능력',
    fields: [
      'total_revenue',
      'gross_profit',
      'operating_income',
      'net_income',
      'ebitda',
      'ebit',
    ],
  },
  {
    id: 'is_cost',
    icon: '\ud83d\udcc9',
    label: '비용 구조',
    description: '비용 항목별 분석',
    fields: [
      'cost_of_revenue',
      'operating_expenses',
      'selling_general_and_administrative',
      'research_and_development',
      'depreciation_and_amortization',
      'interest_expense',
    ],
  },
  {
    id: 'is_growth',
    icon: '\ud83d\udcc8',
    label: '성장성 지표',
    description: '미래 성장 투자 현황',
    fields: [
      'total_revenue',
      'research_and_development',
      'operating_income',
      'net_income',
      'ebitda',
    ],
  },
  {
    id: 'is_per_share',
    icon: '\ud83d\udcca',
    label: '주당 지표',
    description: '주식 1주당 가치',
    fields: [
      'basic_eps',
      'diluted_eps',
    ],
  },
];

// ============================================
// Cash Flow Groups
// ============================================
export const CASH_FLOW_GROUPS: FieldGroup[] = [
  {
    id: 'cf_recommended',
    icon: '\u2b50',
    label: '추천 (입문자용)',
    description: '현금 흐름 핵심 항목',
    fields: [
      'operating_cashflow',
      'capital_expenditures',
      'cashflow_from_investment',
      'cashflow_from_financing',
      'dividend_payout',
    ],
  },
  {
    id: 'cf_generation',
    icon: '\ud83d\udcb5',
    label: '현금 창출력',
    description: '영업으로 버는 실제 현금',
    fields: [
      'operating_cashflow',
      'net_income',
      'proceeds_from_operating_activities',
      'payments_for_operating_activities',
      'change_in_operating_assets',
      'change_in_operating_liabilities',
    ],
  },
  {
    id: 'cf_investment',
    icon: '\ud83c\udfed',
    label: '투자 활동',
    description: '미래 성장을 위한 투자',
    fields: [
      'capital_expenditures',
      'cashflow_from_investment',
      'change_in_inventory',
      'change_in_receivables',
    ],
  },
  {
    id: 'cf_shareholder',
    icon: '\ud83c\udf81',
    label: '주주 환원',
    description: '배당금과 자사주 매입',
    fields: [
      'dividend_payout',
      'payments_for_repurchase_of_common_stock',
      'cashflow_from_financing',
      'operating_cashflow',
    ],
  },
  {
    id: 'cf_working',
    icon: '\ud83d\udd04',
    label: '운전자본 관리',
    description: '단기 현금 흐름 관리',
    fields: [
      'change_in_receivables',
      'change_in_inventory',
      'change_in_operating_assets',
      'change_in_operating_liabilities',
    ],
  },
];

// ============================================
// Helper Functions
// ============================================

/**
 * Get field groups for a specific tab type
 */
export function getGroupsForTab(tabType: FinancialTabType): FieldGroup[] {
  switch (tabType) {
    case 'balance-sheet':
      return BALANCE_SHEET_GROUPS;
    case 'income-statement':
      return INCOME_STATEMENT_GROUPS;
    case 'cash-flow':
      return CASH_FLOW_GROUPS;
    default:
      return [];
  }
}

/**
 * Get a specific group by ID
 */
export function getGroupById(tabType: FinancialTabType, groupId: string): FieldGroup | undefined {
  const groups = getGroupsForTab(tabType);
  return groups.find((g) => g.id === groupId);
}

/**
 * Get fields from a group that are not already selected
 */
export function getNewFieldsFromGroup(
  tabType: FinancialTabType,
  groupId: string,
  selectedFields: string[]
): string[] {
  const group = getGroupById(tabType, groupId);
  if (!group) return [];
  return group.fields.filter((f) => !selectedFields.includes(f));
}

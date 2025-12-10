/**
 * Financial Statement Default Fields Configuration
 *
 * Default fields to display for each financial statement type,
 * with Korean labels and beginner-friendly descriptions.
 */

export type FinancialTabType = 'balance-sheet' | 'income-statement' | 'cash-flow';

export interface FinancialFieldMeta {
  key: string;
  labelKo: string;
  labelEn: string;
  description: string;
}

// Balance Sheet Fields
export const BALANCE_SHEET_FIELDS: FinancialFieldMeta[] = [
  {
    key: 'total_assets',
    labelKo: '총 자산',
    labelEn: 'Total Assets',
    description: '회사가 가진 모든 재산의 합계 (건물, 현금, 재고 등)',
  },
  {
    key: 'total_current_assets',
    labelKo: '유동 자산',
    labelEn: 'Total Current Assets',
    description: '1년 안에 현금으로 바꿀 수 있는 자산',
  },
  {
    key: 'cash_and_cash_equivalents_at_carrying_value',
    labelKo: '현금 및 현금성 자산',
    labelEn: 'Cash & Equivalents',
    description: '지금 바로 쓸 수 있는 현금과 예금',
  },
  {
    key: 'cash_and_short_term_investments',
    labelKo: '현금 및 단기투자',
    labelEn: 'Cash & Short-term Investments',
    description: '현금과 1년 내 만기 도래 투자자산',
  },
  {
    key: 'inventory',
    labelKo: '재고자산',
    labelEn: 'Inventory',
    description: '판매를 위해 보유 중인 상품/원자재',
  },
  {
    key: 'current_net_receivables',
    labelKo: '매출채권',
    labelEn: 'Net Receivables',
    description: '외상으로 판매하고 아직 못 받은 돈',
  },
  {
    key: 'total_non_current_assets',
    labelKo: '비유동 자산',
    labelEn: 'Total Non-current Assets',
    description: '1년 이상 장기 보유하는 자산',
  },
  {
    key: 'property_plant_equipment',
    labelKo: '유형자산',
    labelEn: 'Property, Plant & Equipment',
    description: '토지, 건물, 기계장치 등',
  },
  {
    key: 'long_term_investments',
    labelKo: '장기투자',
    labelEn: 'Long-term Investments',
    description: '1년 이상 보유 목적의 투자자산',
  },
  {
    key: 'short_term_investments',
    labelKo: '단기투자',
    labelEn: 'Short-term Investments',
    description: '1년 내 만기 도래 투자자산',
  },
  {
    key: 'goodwill',
    labelKo: '영업권',
    labelEn: 'Goodwill',
    description: '인수합병 시 지불한 프리미엄',
  },
  {
    key: 'intangible_assets',
    labelKo: '무형자산',
    labelEn: 'Intangible Assets',
    description: '특허권, 상표권 등 보이지 않는 자산',
  },
  {
    key: 'total_liabilities',
    labelKo: '총 부채',
    labelEn: 'Total Liabilities',
    description: '회사가 갚아야 할 빚의 총합',
  },
  {
    key: 'total_current_liabilities',
    labelKo: '유동 부채',
    labelEn: 'Total Current Liabilities',
    description: '1년 안에 갚아야 하는 빚',
  },
  {
    key: 'total_non_current_liabilities',
    labelKo: '비유동 부채',
    labelEn: 'Total Non-current Liabilities',
    description: '1년 이후에 갚아야 하는 빚',
  },
  {
    key: 'current_accounts_payable',
    labelKo: '매입채무',
    labelEn: 'Accounts Payable',
    description: '외상으로 구매하고 아직 안 갚은 돈',
  },
  {
    key: 'short_term_debt',
    labelKo: '단기 차입금',
    labelEn: 'Short-term Debt',
    description: '1년 안에 갚을 은행 대출',
  },
  {
    key: 'long_term_debt',
    labelKo: '장기 차입금',
    labelEn: 'Long-term Debt',
    description: '1년 이후에 갚을 장기 대출',
  },
  {
    key: 'total_shareholder_equity',
    labelKo: '자기자본 (순자산)',
    labelEn: 'Shareholder Equity',
    description: '자산에서 부채를 뺀 순수 회사 가치',
  },
  {
    key: 'retained_earnings',
    labelKo: '이익잉여금',
    labelEn: 'Retained Earnings',
    description: '배당하지 않고 쌓아둔 누적 이익',
  },
  {
    key: 'common_stock',
    labelKo: '보통주 자본금',
    labelEn: 'Common Stock',
    description: '주주가 투자한 자본금',
  },
  {
    key: 'treasury_stock',
    labelKo: '자기주식',
    labelEn: 'Treasury Stock',
    description: '회사가 다시 사들인 자사 주식',
  },
  {
    key: 'common_stock_shares_outstanding',
    labelKo: '발행 주식 수',
    labelEn: 'Shares Outstanding',
    description: '시장에 유통 중인 전체 주식 수',
  },
];

// Income Statement Fields
export const INCOME_STATEMENT_FIELDS: FinancialFieldMeta[] = [
  {
    key: 'total_revenue',
    labelKo: '매출액',
    labelEn: 'Total Revenue',
    description: '물건/서비스를 팔아서 벌어들인 총 금액',
  },
  {
    key: 'gross_profit',
    labelKo: '매출총이익',
    labelEn: 'Gross Profit',
    description: '매출액에서 원가를 뺀 금액',
  },
  {
    key: 'operating_income',
    labelKo: '영업이익',
    labelEn: 'Operating Income',
    description: '본업에서 실제로 번 이익',
  },
  {
    key: 'net_income',
    labelKo: '순이익',
    labelEn: 'Net Income',
    description: '모든 비용과 세금을 내고 남은 최종 이익',
  },
  {
    key: 'ebitda',
    labelKo: 'EBITDA',
    labelEn: 'EBITDA',
    description: '이자/세금/감가상각 전 영업이익 (현금창출력)',
  },
  {
    key: 'ebit',
    labelKo: 'EBIT',
    labelEn: 'EBIT',
    description: '이자/세금 전 영업이익',
  },
  {
    key: 'cost_of_revenue',
    labelKo: '매출원가',
    labelEn: 'Cost of Revenue',
    description: '제품/서비스 제공에 직접 든 비용',
  },
  {
    key: 'cost_of_goods_and_services_sold',
    labelKo: '매출원가 (상세)',
    labelEn: 'Cost of Goods Sold',
    description: '판매된 상품/서비스의 원가',
  },
  {
    key: 'operating_expenses',
    labelKo: '영업비용',
    labelEn: 'Operating Expenses',
    description: '영업활동에 사용된 비용 합계',
  },
  {
    key: 'selling_general_and_administrative',
    labelKo: '판관비',
    labelEn: 'SG&A',
    description: '판매비와 일반관리비',
  },
  {
    key: 'research_and_development',
    labelKo: '연구개발비 (R&D)',
    labelEn: 'R&D Expense',
    description: '신제품 개발에 쓴 돈 (미래 성장 투자)',
  },
  {
    key: 'depreciation',
    labelKo: '감가상각비',
    labelEn: 'Depreciation',
    description: '고정자산 가치 감소분',
  },
  {
    key: 'depreciation_and_amortization',
    labelKo: '감가상각 및 무형자산상각',
    labelEn: 'D&A',
    description: '유형/무형자산의 가치 감소분',
  },
  {
    key: 'interest_income',
    labelKo: '이자수익',
    labelEn: 'Interest Income',
    description: '예금/채권에서 받은 이자',
  },
  {
    key: 'interest_expense',
    labelKo: '이자비용',
    labelEn: 'Interest Expense',
    description: '빚을 갚으면서 낸 이자 (부채 부담)',
  },
  {
    key: 'income_before_tax',
    labelKo: '세전이익',
    labelEn: 'Income Before Tax',
    description: '세금 내기 전 이익',
  },
  {
    key: 'income_tax_expense',
    labelKo: '법인세',
    labelEn: 'Income Tax Expense',
    description: '정부에 낸 세금',
  },
  {
    key: 'basic_eps',
    labelKo: '기본 주당순이익',
    labelEn: 'Basic EPS',
    description: '주식 1주당 벌어들인 이익',
  },
  {
    key: 'diluted_eps',
    labelKo: '희석 주당순이익',
    labelEn: 'Diluted EPS',
    description: '잠재 주식까지 고려한 주당순이익',
  },
];

// Cash Flow Statement Fields
export const CASH_FLOW_FIELDS: FinancialFieldMeta[] = [
  {
    key: 'operating_cashflow',
    labelKo: '영업활동 현금흐름',
    labelEn: 'Operating Cash Flow',
    description: '본업에서 실제로 들어온 현금',
  },
  {
    key: 'net_income',
    labelKo: '순이익 (현금흐름 시작점)',
    labelEn: 'Net Income',
    description: '현금흐름 계산의 시작점',
  },
  {
    key: 'payments_for_operating_activities',
    labelKo: '영업활동 지출',
    labelEn: 'Payments for Operations',
    description: '영업활동에 사용된 현금',
  },
  {
    key: 'proceeds_from_operating_activities',
    labelKo: '영업활동 수입',
    labelEn: 'Proceeds from Operations',
    description: '영업활동에서 들어온 현금',
  },
  {
    key: 'change_in_operating_liabilities',
    labelKo: '영업부채 증감',
    labelEn: 'Change in Operating Liabilities',
    description: '영업관련 부채의 변동',
  },
  {
    key: 'change_in_operating_assets',
    labelKo: '영업자산 증감',
    labelEn: 'Change in Operating Assets',
    description: '영업관련 자산의 변동',
  },
  {
    key: 'capital_expenditures',
    labelKo: '자본적 지출 (CAPEX)',
    labelEn: 'Capital Expenditures',
    description: '설비/건물 등에 투자한 돈',
  },
  {
    key: 'change_in_receivables',
    labelKo: '매출채권 증감',
    labelEn: 'Change in Receivables',
    description: '외상 매출금 변동 (증가=현금 감소)',
  },
  {
    key: 'change_in_inventory',
    labelKo: '재고자산 증감',
    labelEn: 'Change in Inventory',
    description: '재고 변동 (증가=현금 감소)',
  },
  {
    key: 'cashflow_from_investment',
    labelKo: '투자활동 현금흐름',
    labelEn: 'Cash Flow from Investing',
    description: '투자로 들어오고 나간 현금',
  },
  {
    key: 'cashflow_from_financing',
    labelKo: '재무활동 현금흐름',
    labelEn: 'Cash Flow from Financing',
    description: '돈을 빌리거나 갚은 현금',
  },
  {
    key: 'proceeds_from_repayments_of_short_term_debt',
    labelKo: '단기 차입 증감',
    labelEn: 'Short-term Debt Changes',
    description: '단기 빚을 빌리거나 갚은 금액',
  },
  {
    key: 'payments_for_repurchase_of_common_stock',
    labelKo: '자사주 매입액',
    labelEn: 'Stock Repurchases',
    description: '자사주를 사는데 쓴 돈 (주주환원)',
  },
  {
    key: 'dividend_payout',
    labelKo: '배당금 지급액',
    labelEn: 'Dividend Payout',
    description: '주주에게 나눠준 배당금',
  },
];

// Default selected fields for each tab
export const DEFAULT_SELECTED_FIELDS: Record<FinancialTabType, string[]> = {
  'balance-sheet': [
    'total_assets',
    'total_current_assets',
    'cash_and_cash_equivalents_at_carrying_value',
    'total_liabilities',
    'total_current_liabilities',
    'short_term_debt',
    'long_term_debt',
    'total_shareholder_equity',
    'retained_earnings',
    'common_stock_shares_outstanding',
  ],
  'income-statement': [
    'total_revenue',
    'gross_profit',
    'operating_income',
    'net_income',
    'ebitda',
    'cost_of_revenue',
    'research_and_development',
    'interest_expense',
    'income_tax_expense',
    'diluted_eps',
  ],
  'cash-flow': [
    'operating_cashflow',
    'net_income',
    'capital_expenditures',
    'cashflow_from_investment',
    'cashflow_from_financing',
    'dividend_payout',
    'payments_for_repurchase_of_common_stock',
    'change_in_inventory',
    'change_in_receivables',
    'proceeds_from_repayments_of_short_term_debt',
  ],
};

// Get all fields for a specific tab type
export function getFieldsForTab(tabType: FinancialTabType): FinancialFieldMeta[] {
  switch (tabType) {
    case 'balance-sheet':
      return BALANCE_SHEET_FIELDS;
    case 'income-statement':
      return INCOME_STATEMENT_FIELDS;
    case 'cash-flow':
      return CASH_FLOW_FIELDS;
    default:
      return [];
  }
}

// Get field metadata by key
export function getFieldMeta(tabType: FinancialTabType, key: string): FinancialFieldMeta | undefined {
  const fields = getFieldsForTab(tabType);
  return fields.find(f => f.key === key);
}

// Get label for a field (Korean preferred, fallback to formatted key)
export function getFieldLabel(tabType: FinancialTabType, key: string): string {
  const meta = getFieldMeta(tabType, key);
  if (meta) {
    return meta.labelKo;
  }
  // Fallback: convert snake_case to Title Case
  return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

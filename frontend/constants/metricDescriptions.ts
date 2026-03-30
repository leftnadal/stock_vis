/**
 * 34개 지표 설명 (초급 비유 + 중급 계산식/기준)
 */

export interface MetricDescription {
  /** 초급: 비유 기반 한줄 설명 (50자 내) */
  basic: string;
  /** 중급: 계산식 + 업종 기준 (선택, 주요 12개) */
  detail?: string;
}

export const METRIC_DESCRIPTIONS: Record<string, MetricDescription> = {
  // ── 수익성 (5) ──
  gross_margin: {
    basic: '상품 판매 시 원가를 빼고 남긴 이익의 비율입니다.',
    detail: '계산: 매출총이익 ÷ 매출액. IT 평균 50~70%, 제조업 20~35%.',
  },
  operating_margin: {
    basic: '인건비, 임대료 등 운영비까지 빼고 남은 이익의 비율입니다.',
    detail: '계산: 영업이익 ÷ 매출액. 본업의 수익성을 보여줍니다.',
  },
  net_margin: {
    basic: '세금, 이자 등 모든 비용을 제하고 최종적으로 남긴 이익입니다.',
    detail: '계산: 순이익 ÷ 매출액. 10% 이상이면 양호.',
  },
  roe: {
    basic: '내가 투자한 돈(자기자본)으로 얼마나 벌었는지 보여줍니다.',
    detail: '계산: 순이익 ÷ 자기자본. 15% 이상이면 우수. 부채가 높으면 왜곡될 수 있음.',
  },
  roic: {
    basic: '빌린 돈까지 포함해 투자한 자본 전체의 수익률입니다.',
    detail: '계산: 세후영업이익 ÷ 투하자본. ROE보다 왜곡이 적음.',
  },

  // ── 성장성 (4) ──
  revenue_growth_yoy: {
    basic: '작년 대비 올해 매출이 얼마나 늘었는지 보여줍니다.',
  },
  operating_income_growth: {
    basic: '작년 대비 영업이익이 얼마나 늘었는지 보여줍니다.',
  },
  fcf_growth_yoy: {
    basic: '실제 손에 쥘 수 있는 현금(FCF)이 얼마나 늘었는지입니다.',
  },
  rev_growth_vs_industry: {
    basic: '업종 평균보다 매출이 빠르게 성장하는지 비교합니다.',
    detail: '양수면 업종보다 빠른 성장, 음수면 뒤처지는 중.',
  },

  // ── 재무구조 (6) ──
  debt_to_equity: {
    basic: '자기 돈 대비 빌린 돈이 얼마나 되는지 보여줍니다.',
    detail: '계산: 총부채 ÷ 자기자본. 1배 이하가 안전. 금융업은 기준이 다릅니다.',
  },
  current_ratio: {
    basic: '1년 내 갚아야 할 빚을 갚을 수 있는 능력입니다.',
    detail: '계산: 유동자산 ÷ 유동부채. 1.5배 이상이면 양호.',
  },
  interest_coverage: {
    basic: '벌어들인 이익으로 이자를 몇 번이나 갚을 수 있는지입니다.',
    detail: '계산: 영업이익 ÷ 이자비용. 3배 이상 안전, 1배 이하 위험.',
  },
  net_debt_to_ebitda: {
    basic: '빚을 갚는 데 영업이익 기준으로 몇 년이 걸리는지입니다.',
    detail: '계산: 순부채 ÷ EBITDA. 3배 이하가 건전.',
  },
  cash_runway_years: {
    basic: '현재 보유 현금으로 몇 년간 버틸 수 있는지입니다.',
    detail: '적자 기업에만 의미 있음. 흑자 기업은 해당 없음.',
  },
  short_term_debt_pct: {
    basic: '전체 부채 중 1년 내 갚아야 할 단기 부채 비중입니다.',
  },

  // ── 현금흐름 (6) ──
  fcf_margin: {
    basic: '매출 중 실제 현금으로 남는 비율입니다.',
    detail: '계산: 잉여현금흐름 ÷ 매출. 회계 이익과 다른 "진짜 현금".',
  },
  ocf_to_net_income: {
    basic: '이익이 진짜 현금으로 들어오는지 보여줍니다.',
    detail: '1배 이상이면 이익의 질이 높음. 낮으면 매출채권에 묶여 있을 수 있음.',
  },
  capex_to_ocf: {
    basic: '벌어들인 현금 중 시설투자에 쓰는 비율입니다.',
  },
  accruals_ratio: {
    basic: '회계상 이익과 실제 현금 차이를 보여줍니다.',
    detail: '높으면 이익의 질이 낮을 수 있음. 분식 가능성 체크 지표.',
  },
  fcf_conversion: {
    basic: '순이익이 실제 현금으로 얼마나 잘 바뀌는지입니다.',
  },
  cash_from_ops_trend: {
    basic: '3년간 영업에서 벌어들인 현금의 추세입니다.',
  },

  // ── 운영효율 (6) ──
  dso: {
    basic: '물건을 팔고 대금을 회수하기까지 걸리는 일수입니다.',
    detail: '짧을수록 좋음. 길어지면 매출채권 부실 위험.',
  },
  ar_to_revenue: {
    basic: '매출 중 아직 받지 못한 돈의 비율입니다.',
  },
  inventory_turnover_days: {
    basic: '재고가 팔리기까지 걸리는 일수입니다.',
    detail: '짧을수록 효율적. 서비스 기업은 해당 없음.',
  },
  inventory_vs_sales_growth: {
    basic: '재고 증가 속도가 매출 증가 속도보다 빠른지 비교합니다.',
    detail: '양수면 재고 과잉 축적 위험. 음수면 양호.',
  },
  sga_to_revenue: {
    basic: '매출 대비 판매·관리에 쓰는 비용 비율입니다.',
  },
  asset_turnover: {
    basic: '보유한 자산으로 매출을 얼마나 효율적으로 만드는지입니다.',
  },

  // ── 희석/주주가치 (4) ──
  dilution_3y_cum: {
    basic: '3년간 발행 주식 수가 늘어 기존 주주 지분이 줄었는지입니다.',
    detail: '양수면 희석 발생. 테크 기업은 SBC로 인해 높을 수 있음.',
  },
  sbc_to_revenue: {
    basic: '매출 대비 주식으로 지급한 직원 보상 비율입니다.',
  },
  buyback_offsets_sbc: {
    basic: '자사주 매입이 주식보상 희석을 상쇄하는지 보여줍니다.',
  },
  net_shareholder_yield: {
    basic: '배당 + 자사주매입으로 주주에게 돌려주는 비율입니다.',
    detail: '높을수록 주주 친화적 경영. 성장주는 낮을 수 있음.',
  },

  // ── 밸류에이션 (3) ──
  pe_ratio: {
    basic: '현재 주가가 1년 이익의 몇 배인지 보여줍니다.',
    detail: '낮을수록 저평가 가능성. 단, 성장주는 높은 게 정상일 수 있음.',
  },
  ev_to_ebitda: {
    basic: '기업 전체 가치가 영업이익의 몇 배인지 보여줍니다.',
    detail: 'PER보다 부채와 현금을 반영. 업종 비교에 더 적합.',
  },
  fcf_yield: {
    basic: '투자금 대비 기업이 만드는 실제 현금 수익률입니다.',
    detail: '높을수록 저평가. 채권 금리와 비교해볼 수 있음.',
  },
};

/**
 * Investment-Advisor 설계: 투자 교육 콘텐츠 상수
 *
 * 거시경제 지표별 교육 콘텐츠, 툴팁, 용어 설명 등
 * 초급/중급/고급 3단계 난이도별 설명 제공
 */

// ============================================================================
// Types
// ============================================================================

export type EducationLevel = 'beginner' | 'intermediate' | 'advanced';
export type RiskLevel = 'low' | 'medium' | 'medium-high' | 'high';

export interface EducationContent {
  title: string;
  summary: string;
  levels: {
    beginner: string;
    intermediate: string;
    advanced: string;
  };
  keyPoints: string[];
  relatedTerms: string[];
  learnMoreUrl?: string;
}

export interface TooltipContent {
  term: string;
  definition: string;
  example?: string;
}

// ============================================================================
// 1. Fear & Greed Index 교육 콘텐츠
// ============================================================================

export const FEAR_GREED_EDUCATION: EducationContent = {
  title: '공포/탐욕 지수 (Fear & Greed Index)',
  summary: '시장 참여자들의 심리 상태를 0-100 사이의 수치로 나타낸 지표입니다.',
  levels: {
    beginner:
      `주식 시장에는 '분위기'가 있어요. 사람들이 무서워하면 주가가 떨어지고, 욕심을 부리면 주가가 오르죠. 이 지수는 지금 시장 분위기가 어떤지 숫자로 보여줍니다. 0에 가까우면 사람들이 무서워하고 있고, 100에 가까우면 욕심을 부리고 있어요.`,
    intermediate:
      `공포/탐욕 지수는 VIX(변동성 지수), 주가 모멘텀, 안전자산 수요, 옵션 시장 등 7가지 지표를 종합하여 산출합니다. 역사적으로 극단적 공포 구간(0-25)은 저점 매수 기회, 극단적 탐욕 구간(75-100)은 조정 전 과열 신호로 여겨집니다.`,
    advanced:
      `본 지수는 CNN에서 개발한 방법론을 참고하여 계산됩니다. 구성 요소로는 주가 모멘텀(S&P 500 125일 이평선 대비), 주가 강도(52주 신고가/신저가 비율), 시장 변동성(VIX), Put/Call 비율, 정크본드 수요, 안전자산 수요 등이 있습니다. 각 요소의 가중치와 정규화 방법에 따라 결과값이 달라질 수 있습니다.`,
  },
  keyPoints: [
    '0-25: 극단적 공포 - 역사적 저점 매수 기회',
    '25-45: 공포 - 시장 위축, 변동성 확대',
    '45-55: 중립 - 균형 잡힌 시장',
    '55-75: 탐욕 - 상승 모멘텀, 주의 필요',
    '75-100: 극단적 탐욕 - 과열, 조정 가능성',
  ],
  relatedTerms: ['VIX', '변동성', '시장 심리', '역발상 투자'],
};

// ============================================================================
// 2. Yield Curve 교육 콘텐츠
// ============================================================================

export const YIELD_CURVE_EDUCATION: EducationContent = {
  title: '수익률 곡선 (Yield Curve)',
  summary: '국채의 만기별 금리를 연결한 곡선으로, 경기 전망을 나타내는 중요한 지표입니다.',
  levels: {
    beginner:
      `은행에 돈을 맡기면 이자를 받죠? 보통 1년 예금보다 5년 예금의 이자가 더 높아요. 이게 정상이에요. 그런데 가끔 1년 이자가 5년보다 높아지는 "이상한" 상황이 생기는데, 이걸 "역전"이라고 해요. 역전이 되면 곧 경제가 어려워질 수 있다는 신호예요.`,
    intermediate:
      `수익률 곡선은 2년물, 5년물, 10년물 등 다양한 만기의 국채 금리를 연결한 그래프입니다. 정상적인 상황에서는 장기물 금리가 더 높은 우상향 곡선을 그립니다. 10년물-2년물 금리차(스프레드)가 0 미만으로 역전되면, 역사적으로 12-18개월 후 경기침체가 발생했습니다.`,
    advanced:
      `수익률 곡선의 형태는 기간 프리미엄, 인플레이션 기대, 연준 정책 전망 등을 반영합니다. 역전의 예측력에 대해서는 학계에서도 논쟁이 있으며, "이번에는 다르다"는 주장도 있습니다. 그러나 1970년 이후 모든 미국 경기침체 전 역전이 발생했다는 점은 부정하기 어렵습니다. 다만, 역전 후 침체까지의 시차는 6개월-24개월로 편차가 큽니다.`,
  },
  keyPoints: [
    '정상: 장기 금리 > 단기 금리 (경기 확장)',
    '평탄화: 금리 인상 사이클 후반',
    '역전: 단기 금리 > 장기 금리 (경기침체 선행)',
    '가파름: 경기 회복 초기 신호',
    '10Y-2Y 스프레드가 핵심 지표',
  ],
  relatedTerms: ['국채', '금리', '연준', '경기침체', '기간 프리미엄'],
};

// ============================================================================
// 3. Interest Rate 교육 콘텐츠
// ============================================================================

export const INTEREST_RATE_EDUCATION: EducationContent = {
  title: '기준금리와 시장금리',
  summary: '연준이 결정하는 기준금리와 시장에서 형성되는 다양한 금리의 관계를 이해합니다.',
  levels: {
    beginner:
      `금리는 돈을 빌릴 때 내는 "사용료"예요. 연준(미국의 중앙은행)이 금리를 올리면, 대출이 비싸져서 사람들이 돈을 덜 쓰게 돼요. 그러면 물가가 안정되죠. 반대로 금리를 내리면 대출이 싸져서 경제가 활발해져요.`,
    intermediate:
      `연방기금금리(Fed Funds Rate)는 은행 간 초단기 대출 금리로, 연준이 직접 조절하는 정책금리입니다. 이 금리가 움직이면 모기지, 기업대출, 신용카드 등 모든 금리에 영향을 줍니다. 금리 인상은 주식(특히 성장주)에 불리하고, 금리 인하는 유리합니다.`,
    advanced:
      `연준의 듀얼 맨데이트(물가안정 + 완전고용)에 따라 금리가 결정됩니다. 테일러 준칙에 따르면 적정 금리는 인플레이션, 실업률, 잠재성장률의 함수입니다. 양적완화(QE)와 양적긴축(QT)은 장기금리에 영향을 미치며, 정책금리와는 별개로 금융 여건을 조절합니다.`,
  },
  keyPoints: [
    '기준금리: 연준이 결정, 모든 금리의 기준점',
    '금리 상승: 물가 안정, 성장주 불리',
    '금리 하락: 경기 부양, 자산가격 상승',
    'FOMC 회의: 연 8회 금리 결정',
    '금리 전망: CME FedWatch Tool 참고',
  ],
  relatedTerms: ['연준', 'FOMC', '인플레이션', '양적완화', '테일러 준칙'],
};

// ============================================================================
// 4. Inflation 교육 콘텐츠
// ============================================================================

export const INFLATION_EDUCATION: EducationContent = {
  title: '인플레이션 (물가상승률)',
  summary: '상품과 서비스의 전반적인 가격 수준이 상승하는 현상입니다.',
  levels: {
    beginner:
      `작년에 1000원이던 과자가 올해 1100원이 됐다면, 물가가 10% 올랐어요. 이걸 인플레이션이라고 해요. 적당한 물가 상승(연 2% 정도)은 건강한 경제의 신호이지만, 너무 빠르면 돈의 가치가 떨어져서 문제가 돼요.`,
    intermediate:
      `CPI(소비자물가지수)는 가장 널리 사용되는 인플레이션 지표입니다. Core CPI는 변동성이 큰 식품과 에너지를 제외한 수치로, 기조적 물가 흐름을 파악하는 데 유용합니다. PCE는 연준이 선호하는 지표로, CPI와 계산 방식이 약간 다릅니다.`,
    advanced:
      `CPI와 PCE의 주요 차이점은 가중치 산출 방식(고정 바스켓 vs 체인 가중)과 포함 범위(가계 직접 구매 vs 대리 구매 포함)입니다. 기대 인플레이션은 BEI(손익분기 인플레이션)로 측정하며, 연준의 정책 결정에 중요한 역할을 합니다. 스태그플레이션(물가 상승 + 경기 침체)은 정책 대응이 가장 어려운 상황입니다.`,
  },
  keyPoints: [
    '연준 목표: 연 2% (PCE 기준)',
    'CPI: 소비자 물가지수, 매월 발표',
    'Core CPI: 식품/에너지 제외, 기조적 흐름',
    'PCE: 연준 선호 지표',
    '높은 인플레이션: 금리 인상 압력',
  ],
  relatedTerms: ['CPI', 'PCE', 'Core 인플레이션', '스태그플레이션', '디플레이션'],
};

// ============================================================================
// 5. Employment 교육 콘텐츠
// ============================================================================

export const EMPLOYMENT_EDUCATION: EducationContent = {
  title: '고용 지표',
  summary: '미국 노동 시장의 건강 상태를 나타내는 다양한 지표들입니다.',
  levels: {
    beginner:
      `실업률은 일하고 싶은데 일자리가 없는 사람의 비율이에요. 실업률이 낮으면 경제가 잘 돌아가고 있다는 뜻이에요. 미국에서는 매달 첫째 주 금요일에 고용보고서가 발표되는데, 이날 주식시장이 많이 출렁여요.`,
    intermediate:
      `비농업 고용(NFP)은 매월 신규로 창출된 일자리 수를 나타냅니다. 시장 예상치와의 차이가 중요하며, 예상보다 좋으면 경기 낙관 / 금리 인상 기대로 해석됩니다. U-3(공식 실업률) 외에 U-6(광의 실업률)도 참고합니다.`,
    advanced:
      `고용 지표의 해석은 경기 사이클에 따라 달라집니다. 경기 확장 후반에 강한 고용은 임금 인플레이션 → 금리 인상 우려로 이어질 수 있습니다. JOLTS(구인/이직 보고서)의 구인율과 자발적 이직률은 노동시장 타이트니스를 보여줍니다. 베버리지 곡선의 이동은 구조적 실업 변화를 나타냅니다.`,
  },
  keyPoints: [
    'NFP: 비농업 고용, 매월 첫째 주 금요일',
    '실업률: 자연실업률 약 4% 전후',
    '시간당 임금: 인플레이션 압력 지표',
    '경제활동참가율: 노동력 공급 측정',
    '강한 고용: 경기 ↑ but 금리 ↑ 가능성',
  ],
  relatedTerms: ['NFP', '실업률', 'JOLTS', '임금 인플레이션', '완전고용'],
};

// ============================================================================
// 6. GDP 교육 콘텐츠
// ============================================================================

export const GDP_EDUCATION: EducationContent = {
  title: 'GDP (국내총생산)',
  summary: '한 나라의 경제 규모와 성장률을 나타내는 가장 포괄적인 지표입니다.',
  levels: {
    beginner:
      `GDP는 한 나라에서 1년 동안 만들어낸 모든 상품과 서비스의 가치를 합친 거예요. 미국 GDP가 연 3% 성장했다면, 미국 경제가 작년보다 3% 커졌다는 뜻이에요. 보통 2-3% 성장하면 건강한 경제로 봐요.`,
    intermediate:
      `GDP = 소비(C) + 투자(I) + 정부지출(G) + 순수출(NX)로 구성됩니다. 미국 GDP의 약 70%는 소비가 차지합니다. 분기별로 속보치, 잠정치, 확정치 3번 발표되며, 전기 대비 연율화된 성장률로 표시합니다. 2분기 연속 마이너스 성장은 기술적 경기침체로 정의됩니다.`,
    advanced:
      `명목 GDP와 실질 GDP(인플레이션 조정)의 구분이 중요합니다. GDP 디플레이터는 경제 전반의 물가 수준을 나타냅니다. 잠재 GDP와 실제 GDP의 차이(GDP 갭)는 경기 과열/침체를 판단하는 기준입니다. GDI(국내총소득)는 이론적으로 GDP와 같아야 하지만 통계적 오차가 있습니다.`,
  },
  keyPoints: [
    '미국 정상 성장률: 연 2-3%',
    '2분기 연속 마이너스 = 기술적 침체',
    '소비가 미국 GDP의 70% 차지',
    '속보치/잠정치/확정치 3단계 발표',
    'GDP 갭: 잠재 vs 실제 성장률 차이',
  ],
  relatedTerms: ['GNP', '잠재성장률', '경기침체', 'GDP 갭', '실질 GDP'],
};

// ============================================================================
// 7. VIX 교육 콘텐츠
// ============================================================================

export const VIX_EDUCATION: EducationContent = {
  title: 'VIX (변동성 지수)',
  summary: '향후 30일간 S&P 500의 예상 변동성을 나타내는 "공포 지수"입니다.',
  levels: {
    beginner:
      `VIX는 주식시장의 "온도계" 같은 거예요. 숫자가 높으면(30 이상) 사람들이 불안해하고 시장이 크게 출렁여요. 낮으면(15 이하) 평온한 상태죠. "공포 지수"라는 별명이 있어요.`,
    intermediate:
      `VIX는 S&P 500 옵션의 내재변동성에서 산출됩니다. 옵션 가격이 비싸지면 VIX가 상승합니다. VIX 20 이상은 평균 이상의 변동성을, 30 이상은 극단적 공포를 나타냅니다. VIX는 주가와 역의 상관관계를 가지며, 헤지 도구로 활용됩니다.`,
    advanced:
      `VIX 선물의 콘탱고(선물가 > 현물가) 구조는 평상시 나타나며, VIX 롱 포지션의 롤오버 비용을 발생시킵니다. 백워데이션(선물가 < 현물가)은 시장 패닉 시 나타납니다. VIX는 평균회귀 특성이 강해, 극단값은 오래 지속되지 않습니다. VVIX(VIX의 변동성)는 VIX 자체의 불확실성을 측정합니다.`,
  },
  keyPoints: [
    '12 미만: 낮은 변동성, 과도한 안심?',
    '12-20: 정상 범위',
    '20-30: 높은 변동성, 불확실성',
    '30 이상: 극단적 공포, 패닉',
    'VIX 급등 → 주가 급락 동반이 일반적',
  ],
  relatedTerms: ['내재변동성', '옵션', 'S&P 500', '콘탱고', '백워데이션'],
};

// ============================================================================
// 8. 글로벌 시장 교육 콘텐츠
// ============================================================================

export const GLOBAL_MARKETS_EDUCATION: EducationContent = {
  title: '글로벌 시장 지표',
  summary: '미국 외 글로벌 시장의 동향을 파악하는 주요 지표들입니다.',
  levels: {
    beginner:
      `주식시장은 전 세계가 연결되어 있어요. 미국 시장이 밤에 열리면, 아시아와 유럽 시장이 영향을 받아요. 달러가 강해지면 다른 나라 통화는 약해지고, 금은 불안할 때 올라가는 "안전자산"이에요.`,
    intermediate:
      `주요 지수로는 미국(S&P 500, 나스닥, 다우), 유럽(STOXX 600, DAX, FTSE), 아시아(닛케이, 항셍, 코스피)가 있습니다. DXY(달러 인덱스)는 6개 주요 통화 대비 달러 가치를 측정합니다. 달러 강세는 신흥국 자산과 원자재에 불리합니다.`,
    advanced:
      `글로벌 자산 배분에서 상관관계는 중요합니다. 위기 시 상관관계가 1로 수렴하는 경향이 있어 분산 효과가 감소합니다. 캐리 트레이드(저금리 통화 차입 → 고금리 자산 투자)의 청산은 급격한 환율 변동을 초래합니다. VIX와 신흥국 스프레드의 상관관계도 참고해야 합니다.`,
  },
  keyPoints: [
    'DXY: 달러 인덱스, 100 기준',
    '금: 안전자산, 인플레이션 헤지',
    '원유: 경기 선행지표, 지정학 영향',
    'VIX 상승 시 안전자산 선호',
    '신흥국: 달러 강세에 취약',
  ],
  relatedTerms: ['DXY', '안전자산', '캐리 트레이드', 'MSCI', '신흥국'],
};

// ============================================================================
// 통합 교육 콘텐츠 객체
// ============================================================================

export const EDUCATIONAL_CONTENT = {
  fearGreed: FEAR_GREED_EDUCATION,
  yieldCurve: YIELD_CURVE_EDUCATION,
  interestRate: INTEREST_RATE_EDUCATION,
  inflation: INFLATION_EDUCATION,
  employment: EMPLOYMENT_EDUCATION,
  gdp: GDP_EDUCATION,
  vix: VIX_EDUCATION,
  globalMarkets: GLOBAL_MARKETS_EDUCATION,
} as const;

// ============================================================================
// 용어 툴팁 정의
// ============================================================================

export const TOOLTIPS: Record<string, TooltipContent> = {
  vix: {
    term: 'VIX',
    definition: 'CBOE 변동성 지수. S&P 500 옵션의 내재변동성을 측정하며, "공포 지수"로 불립니다.',
    example: 'VIX 30 이상은 극단적 공포 상태를 나타냅니다.',
  },
  yieldCurve: {
    term: '수익률 곡선',
    definition: '국채의 만기별 금리를 연결한 곡선. 경기 전망의 바로미터로 활용됩니다.',
    example: '10년물 금리 4.0%, 2년물 금리 4.5%면 0.5%p 역전 상태.',
  },
  fedFundsRate: {
    term: '연방기금금리',
    definition: '연준이 설정하는 정책금리. 은행 간 초단기 대출의 기준이 됩니다.',
    example: '현재 5.25-5.50% 목표 범위.',
  },
  cpi: {
    term: 'CPI',
    definition: '소비자물가지수. 가구가 구매하는 상품과 서비스의 가격 변동을 측정합니다.',
    example: 'CPI 전년비 3.2%는 물가가 작년보다 3.2% 올랐음을 의미.',
  },
  coreCpi: {
    term: 'Core CPI',
    definition: '식품과 에너지를 제외한 소비자물가지수. 기조적 인플레이션 흐름을 파악하는 데 유용합니다.',
  },
  pce: {
    term: 'PCE',
    definition: '개인소비지출 물가지수. 연준이 선호하는 인플레이션 지표입니다.',
  },
  nfp: {
    term: 'NFP',
    definition: '비농업 고용자 수 변화. 매월 첫째 주 금요일에 발표되는 핵심 고용 지표입니다.',
    example: '+200K는 20만 개의 일자리가 새로 생겼음을 의미.',
  },
  gdp: {
    term: 'GDP',
    definition: '국내총생산. 한 나라에서 일정 기간 동안 생산된 모든 최종 재화와 서비스의 시장가치.',
    example: 'GDP 성장률 2.5%는 경제가 전년 대비 2.5% 성장했음을 의미.',
  },
  fomc: {
    term: 'FOMC',
    definition: '연방공개시장위원회. 연준의 통화정책을 결정하는 기관으로, 연 8회 정례회의를 개최합니다.',
  },
  dotPlot: {
    term: '점도표 (Dot Plot)',
    definition: 'FOMC 위원들의 향후 금리 전망을 점으로 나타낸 그래프.',
  },
  yieldSpread: {
    term: '금리 스프레드',
    definition: '두 금리의 차이. 보통 10년물-2년물 국채 금리 차이를 의미합니다.',
    example: '스프레드 -0.5%는 단기 금리가 장기보다 0.5%p 높은 역전 상태.',
  },
  dxy: {
    term: 'DXY (달러 인덱스)',
    definition: '유로, 엔, 파운드 등 6개 주요 통화 대비 달러 가치를 측정하는 지수.',
    example: 'DXY 105는 달러가 기준(100) 대비 5% 강세임을 의미.',
  },
  recession: {
    term: '경기침체 (Recession)',
    definition: '경제 활동이 광범위하게 위축되는 기간. 보통 2분기 연속 GDP 역성장으로 정의.',
  },
  stagflation: {
    term: '스태그플레이션',
    definition: '경기 침체(Stagnation)와 인플레이션이 동시에 발생하는 상황. 정책 대응이 어렵습니다.',
  },
  quantitativeEasing: {
    term: '양적완화 (QE)',
    definition: '중앙은행이 채권 등 자산을 매입하여 시장에 유동성을 공급하는 정책.',
  },
  quantitativeTightening: {
    term: '양적긴축 (QT)',
    definition: '중앙은행이 보유 자산을 줄여 시장의 유동성을 회수하는 정책.',
  },
};

// ============================================================================
// 섹터별 금리 영향 매핑 (프론트엔드용)
// ============================================================================

export const SECTOR_RATE_SENSITIVITY = {
  technology: {
    name: '기술',
    nameEn: 'Technology',
    sensitivity: 'high',
    direction: 'inverse',
    description: '성장주 특성상 금리 상승에 민감. 할인율 상승 → 미래 현금흐름 가치 하락.',
  },
  financials: {
    name: '금융',
    nameEn: 'Financials',
    sensitivity: 'high',
    direction: 'positive',
    description: '금리 상승 시 예대마진 확대로 수혜. 다만 급격한 상승은 대출 수요 감소 우려.',
  },
  realEstate: {
    name: '부동산',
    nameEn: 'Real Estate',
    sensitivity: 'high',
    direction: 'inverse',
    description: '높은 부채 비율과 금리 민감 업종. 금리 상승 시 차입 비용 증가, 자산가치 하락.',
  },
  utilities: {
    name: '유틸리티',
    nameEn: 'Utilities',
    sensitivity: 'medium',
    direction: 'inverse',
    description: '고배당주 특성. 금리 상승 시 채권 대비 매력 감소.',
  },
  healthcare: {
    name: '헬스케어',
    nameEn: 'Healthcare',
    sensitivity: 'low',
    direction: 'neutral',
    description: '경기방어적 특성. 금리보다는 규제, 약가 정책에 더 민감.',
  },
  consumerStaples: {
    name: '필수소비재',
    nameEn: 'Consumer Staples',
    sensitivity: 'low',
    direction: 'neutral',
    description: '경기와 무관하게 수요 안정. 금리 변동 영향 제한적.',
  },
  consumerDiscretionary: {
    name: '임의소비재',
    nameEn: 'Consumer Discretionary',
    sensitivity: 'medium',
    direction: 'inverse',
    description: '금리 상승 시 소비자 가처분소득 감소, 대출 비용 증가로 수요 위축 가능.',
  },
  industrials: {
    name: '산업재',
    nameEn: 'Industrials',
    sensitivity: 'medium',
    direction: 'mixed',
    description: '경기 민감 업종. 금리보다는 경기 사이클에 더 연동.',
  },
  energy: {
    name: '에너지',
    nameEn: 'Energy',
    sensitivity: 'low',
    direction: 'neutral',
    description: '유가와 지정학적 요인에 더 민감. 금리 영향은 제한적.',
  },
  materials: {
    name: '소재',
    nameEn: 'Materials',
    sensitivity: 'medium',
    direction: 'mixed',
    description: '달러 강세(금리 상승 동반 시)에 부정적. 원자재 가격에 더 민감.',
  },
  communications: {
    name: '통신서비스',
    nameEn: 'Communication Services',
    sensitivity: 'medium',
    direction: 'inverse',
    description: '성장주(메타, 구글)와 가치주(통신사) 혼재. 평균적으로 금리 상승에 부정적.',
  },
} as const;

// ============================================================================
// 경제 캘린더 이벤트 타입
// ============================================================================

export const CALENDAR_EVENT_TYPES = {
  fomc: {
    name: 'FOMC 회의',
    importance: 'critical',
    description: '연준 금리 결정 및 성명서 발표',
    typicalImpact: '금리 방향에 따라 전 시장 변동',
  },
  employment: {
    name: '고용보고서',
    importance: 'critical',
    description: 'NFP, 실업률, 시간당 임금 발표',
    typicalImpact: '예상치 대비 결과에 따라 금리 전망 조정',
  },
  cpi: {
    name: 'CPI 발표',
    importance: 'critical',
    description: '소비자물가지수 발표',
    typicalImpact: '인플레이션 추이에 따라 금리 전망 변화',
  },
  gdp: {
    name: 'GDP 발표',
    importance: 'critical',
    description: '국내총생산 성장률 발표',
    typicalImpact: '경기 상황 평가, 연착륙 vs 침체 논쟁',
  },
  retailSales: {
    name: '소매판매',
    importance: 'high',
    description: '소비 동향 파악의 핵심 지표',
    typicalImpact: '소비 강도에 따라 경기 전망 조정',
  },
  ism: {
    name: 'ISM 제조업/서비스업',
    importance: 'high',
    description: '기업 경기 심리 지수',
    typicalImpact: '50 기준으로 확장/위축 판단',
  },
  housing: {
    name: '주택 지표',
    importance: 'medium',
    description: '신규주택판매, 기존주택판매, 착공건수',
    typicalImpact: '부동산 시장 및 금리 민감도 파악',
  },
  pmi: {
    name: 'PMI',
    importance: 'medium',
    description: '구매관리자지수',
    typicalImpact: 'ISM보다 먼저 발표, 선행 지표 역할',
  },
} as const;

// ============================================================================
// Export all
// ============================================================================

export type SectorKey = keyof typeof SECTOR_RATE_SENSITIVITY;
export type CalendarEventType = keyof typeof CALENDAR_EVENT_TYPES;

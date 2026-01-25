/**
 * LLM 키워드 시스템 타입 정의
 */

export enum KeywordCategory {
  CATALYST = 'catalyst',              // 촉매 (어닝, 신제품, M&A 등)
  TECHNICAL = 'technical',            // 기술적 신호 (브레이크아웃, 골든크로스 등)
  SENTIMENT = 'sentiment',            // 심리 (공매도, 유동성, 모멘텀 등)
  MACRO = 'macro',                    // 거시경제 (금리, 환율, 원자재 등)
  SECTOR = 'sector',                  // 섹터 동향 (섹터 강세, 테마주 등)
  RISK = 'risk',                      // 리스크 (고변동성, 이격도 등)
}

export interface Keyword {
  id: string;
  text: string;                       // 표시 텍스트 (예: "어닝 서프라이즈", "골든크로스")
  category: KeywordCategory;
  confidence: number;                 // 0.0 ~ 1.0 (LLM 신뢰도)
  description?: string;               // 툴팁용 상세 설명
  color?: string;                     // 커스텀 색상 (선택)
  icon?: string;                      // 아이콘 이름 (선택)
}

export interface StockKeywords {
  symbol: string;
  date: string;
  keywords: Keyword[];
  generated_at: string;               // 생성 시간
  llm_model?: string;                 // 사용된 LLM 모델
}

export interface KeywordAPIResponse {
  success: boolean;
  data?: StockKeywords;
  error?: {
    code: string;
    message: string;
  };
}

// 배치 조회용
export interface BatchKeywordsRequest {
  symbols: string[];
  date?: string;
}

export interface BatchKeywordsResponse {
  success: boolean;
  data?: {
    [symbol: string]: StockKeywords;
  };
  error?: {
    code: string;
    message: string;
  };
}

// 카테고리별 색상 매핑
export const KEYWORD_CATEGORY_COLORS: Record<KeywordCategory, {
  bg: string;
  text: string;
  border: string;
  darkBg: string;
  darkText: string;
  darkBorder: string;
}> = {
  [KeywordCategory.CATALYST]: {
    bg: 'bg-purple-50',
    text: 'text-purple-700',
    border: 'border-purple-200',
    darkBg: 'dark:bg-purple-900/20',
    darkText: 'dark:text-purple-300',
    darkBorder: 'dark:border-purple-700',
  },
  [KeywordCategory.TECHNICAL]: {
    bg: 'bg-blue-50',
    text: 'text-blue-700',
    border: 'border-blue-200',
    darkBg: 'dark:bg-blue-900/20',
    darkText: 'dark:text-blue-300',
    darkBorder: 'dark:border-blue-700',
  },
  [KeywordCategory.SENTIMENT]: {
    bg: 'bg-amber-50',
    text: 'text-amber-700',
    border: 'border-amber-200',
    darkBg: 'dark:bg-amber-900/20',
    darkText: 'dark:text-amber-300',
    darkBorder: 'dark:border-amber-700',
  },
  [KeywordCategory.MACRO]: {
    bg: 'bg-emerald-50',
    text: 'text-emerald-700',
    border: 'border-emerald-200',
    darkBg: 'dark:bg-emerald-900/20',
    darkText: 'dark:text-emerald-300',
    darkBorder: 'dark:border-emerald-700',
  },
  [KeywordCategory.SECTOR]: {
    bg: 'bg-indigo-50',
    text: 'text-indigo-700',
    border: 'border-indigo-200',
    darkBg: 'dark:bg-indigo-900/20',
    darkText: 'dark:text-indigo-300',
    darkBorder: 'dark:border-indigo-700',
  },
  [KeywordCategory.RISK]: {
    bg: 'bg-red-50',
    text: 'text-red-700',
    border: 'border-red-200',
    darkBg: 'dark:bg-red-900/20',
    darkText: 'dark:text-red-300',
    darkBorder: 'dark:border-red-700',
  },
};

// 카테고리별 라벨
export const KEYWORD_CATEGORY_LABELS: Record<KeywordCategory, { en: string; ko: string }> = {
  [KeywordCategory.CATALYST]: { en: 'Catalyst', ko: '촉매' },
  [KeywordCategory.TECHNICAL]: { en: 'Technical', ko: '기술적' },
  [KeywordCategory.SENTIMENT]: { en: 'Sentiment', ko: '심리' },
  [KeywordCategory.MACRO]: { en: 'Macro', ko: '거시' },
  [KeywordCategory.SECTOR]: { en: 'Sector', ko: '섹터' },
  [KeywordCategory.RISK]: { en: 'Risk', ko: '리스크' },
};

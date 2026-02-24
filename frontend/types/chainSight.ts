/**
 * Chain Sight Stock 타입 정의
 *
 * 개별 종목 페이지에서 AI 가이드와 함께하는 주식 탐험 기능
 */

// 카테고리 티어 (0: DB 기반, 1: AI 산업맥락, 2: AI 뉴스기반)
export type CategoryTier = 0 | 1 | 2;

/**
 * 관계 카테고리
 */
export interface ChainSightCategory {
  id: string;
  name: string;
  tier: CategoryTier;
  count: number | '?'; // '?'는 아직 조회되지 않은 동적 카테고리
  icon: string;
  description: string;
  relationship_type?: string; // Tier 0 카테고리용
  is_dynamic?: boolean; // Tier 1/2 동적 카테고리
  sector?: string; // sector_leaders 카테고리용
}

/**
 * 카테고리 조회 응답
 */
export interface ChainSightCategoriesResponse {
  success: boolean;
  data: {
    symbol: string;
    company_name: string;
    categories: ChainSightCategory[];
    is_cold_start: boolean;
    generation_time_ms: number;
    cached?: boolean;
  };
}

/**
 * 관계 태그 (Phase 6)
 */
export interface RelationshipTag {
  type: string;        // "PEER_OF", "THEME", "SUPPLIED_BY" 등
  label: string;       // "경쟁사", "semiconductor" 등
  confidence?: string; // "high", "medium-high", "medium"
  detail?: string;     // "뉴스 3건", "매출 25%", "SOXX 5.5%"
}

/**
 * 관련 종목
 */
export interface ChainSightStock {
  symbol: string;
  company_name: string;
  strength: number; // 0.0 ~ 1.0
  current_price: number | null;
  change_percent: number | null;
  market_cap: number | null;
  sector: string | null;
  industry?: string | null;
  relationship_context?: Record<string, any>;
  tags?: RelationshipTag[];
}

/**
 * 카테고리별 종목 조회 응답
 */
export interface ChainSightCategoryStocksResponse {
  success: boolean;
  data: {
    symbol: string;
    category: ChainSightCategory;
    stocks: ChainSightStock[];
    ai_insights: string;
    follow_up_questions: string[];
    computation_time_ms: number;
    error?: string;
  };
}

/**
 * 동기화 응답
 */
export interface ChainSightSyncResponse {
  success: boolean;
  data: {
    message: string;
    peer_count: number;
    industry_count: number;
    co_mentioned_count: number;
  };
}

/**
 * API 에러 응답
 */
export interface ChainSightErrorResponse {
  success: false;
  error: {
    code: string;
    message: string;
  };
}

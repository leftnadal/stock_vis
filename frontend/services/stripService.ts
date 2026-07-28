// 뉴스 스트립(S1) 서비스 — /api/dashboard/news-strip BFF 소비. [D-NEWSAXIS-CONTRACT]
// 엔드포인트가 /api/dashboard/(v1 아님)라 authAxios base(/api/v1)를 벗어나므로
// 절대 URL로 호출(authAxios 인터셉터의 JWT는 그대로 유지).
import { API_BASE_URL } from '@/lib/api/config';
import { authAxios } from '@/lib/api/authAxios';

export type StripDirection = 'up' | 'down' | 'neutral';

export interface NewsStripBadge {
  pair: string;
  confidence: number;
}

export interface NewsStripItem {
  headline: string;
  symbols: string[];
  direction: StripDirection;
  tier: number;
  relevance_line: string;
  collapsed_count: number;
  badge: NewsStripBadge | null;
  published_at: string;
  article_url: string;
}

export interface NewsStripResponse {
  as_of: string;
  theta: number;
  items: NewsStripItem[];
}

const API_BASE =
  API_BASE_URL;
// base의 /api/v1 접미를 벗겨 origin 도출 → /api/dashboard/ 절대경로.
const ORIGIN = API_BASE.replace(/\/api\/v1\/?$/, '');

export const stripService = {
  async getNewsStrip(): Promise<NewsStripResponse> {
    const { data } = await authAxios.get<NewsStripResponse>(
      `${ORIGIN}/api/dashboard/news-strip/`,
    );
    return data;
  },
};

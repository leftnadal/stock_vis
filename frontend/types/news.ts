// News related types

export interface NewsEntity {
  symbol: string;
  entity_name: string;
  entity_type: string;
  sentiment_score: number | null;
}

export interface NewsArticle {
  id: string;
  url: string;
  title: string;
  summary: string;
  image_url: string | null;
  source: string;
  published_at: string;
  category: string;
  sentiment_score: number | null;
  sentiment_source: string;
  entities: NewsEntity[];
}

export interface NewsListItem {
  id: string;
  url: string;
  title: string;
  summary: string;
  image_url: string | null;
  source: string;
  published_at: string;
  sentiment_score: number | null;
  entity_count: number;
}

export interface SentimentHistory {
  date: string;
  avg_sentiment: number | null;
  news_count: number;
  positive_count: number;
  negative_count: number;
  neutral_count: number;
}

export interface StockSentiment {
  symbol: string;
  total_articles: number;
  avg_sentiment: number | null;
  positive_ratio: number;
  negative_ratio: number;
  neutral_ratio: number;
  sentiment_trend: string;
  history: SentimentHistory[];
}

export interface TrendingStock {
  symbol: string;
  mention_count: number;
  avg_sentiment: number | null;
}

export interface StockNewsResponse {
  symbol: string;
  count: number;
  articles: NewsListItem[];
}

export interface TrendingNewsResponse {
  timeframe: string;
  count: number;
  stocks: TrendingStock[];
}

export type MarketNewsCategory = 'general' | 'forex' | 'crypto' | 'merger';

export interface MarketNewsResponse {
  category: string;
  count: number;
  articles: NewsListItem[];
}

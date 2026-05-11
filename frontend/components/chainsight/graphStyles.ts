/**
 * Chain Sight 그래프 시각 체계 상수
 */

import type { RelationType, RelationStyle } from '@/types/chainsight';

// ── 관계 타입별 스타일 ──

export const RELATION_STYLES: Record<string, RelationStyle> = {
  SUPPLIES_TO:          { color: '#F97316', label: '공급',     width: 3 },
  CUSTOMER_OF:          { color: '#F97316', label: '고객',     width: 3 },
  COMPETES_WITH:        { color: '#EF4444', label: '경쟁',     width: 2.5 },
  PEER_OF:              { color: '#3B82F6', label: '경쟁사',   width: 2 },
  CO_MENTIONED:         { color: '#A855F7', label: '동시출현', width: 2, dash: [4, 4] },
  HAS_THEME:            { color: '#14B8A6', label: '테마',     width: 1.5, dash: [6, 3] },
  BELONGS_TO_SECTOR:    { color: '#9CA3AF', label: '섹터',     width: 1 },
  BELONGS_TO_INDUSTRY:  { color: '#9CA3AF', label: '산업',     width: 1 },
  RELATED_TO:           { color: '#6B7280', label: '관련',     width: 1.5, dash: [2, 2] },
};

export function getRelationStyle(relType: string): RelationStyle {
  return RELATION_STYLES[relType] || RELATION_STYLES.RELATED_TO;
}

// ── 섹터별 노드 색상 ──

export const SECTOR_COLORS: Record<string, string> = {
  'TECHNOLOGY':               '#3B82F6',
  'Technology':               '#3B82F6',
  'HEALTHCARE':               '#10B981',
  'Healthcare':               '#10B981',
  'FINANCIAL SERVICES':       '#F59E0B',
  'Financial Services':       '#F59E0B',
  'ENERGY':                   '#EF4444',
  'Energy':                   '#EF4444',
  'INDUSTRIALS':              '#8B5CF6',
  'Industrials':              '#8B5CF6',
  'CONSUMER CYCLICAL':        '#EC4899',
  'Consumer Cyclical':        '#EC4899',
  'CONSUMER DEFENSIVE':       '#84CC16',
  'Consumer Defensive':       '#84CC16',
  'COMMUNICATION SERVICES':   '#06B6D4',
  'Communication Services':   '#06B6D4',
  'BASIC MATERIALS':          '#D97706',
  'Basic Materials':          '#D97706',
  'REAL ESTATE':              '#F472B6',
  'Real Estate':              '#F472B6',
  'UTILITIES':                '#64748B',
  'Utilities':                '#64748B',
};

export function getSectorColor(sector: string): string {
  return SECTOR_COLORS[sector] || '#6B7280';
}

// ── 노드 크기 계산 ──

export function getNodeRadius(isCenter: boolean, pagerank: number): number {
  if (isCenter) return 32;
  const base = 10;
  const scaled = Math.min(pagerank * 8, 10);
  return base + scaled;
}

/**
 * 관계 태그 스타일 유틸리티 (Phase 6)
 *
 * 태그 타입별 색상/한국어 라벨 매핑.
 * 이모지 없이 텍스트 + 색상으로만 구분.
 */

interface TagStyle {
  label: string;
  bg: string;       // Tailwind bg class
  text: string;     // Tailwind text class
  darkBg: string;   // dark mode bg
  darkText: string; // dark mode text
}

const RELATIONSHIP_TAG_STYLES: Record<string, TagStyle> = {
  PEER_OF: {
    label: '경쟁사',
    bg: 'bg-red-100',
    text: 'text-red-700',
    darkBg: 'dark:bg-red-900/30',
    darkText: 'dark:text-red-400',
  },
  SAME_INDUSTRY: {
    label: '동일 산업',
    bg: 'bg-blue-100',
    text: 'text-blue-700',
    darkBg: 'dark:bg-blue-900/30',
    darkText: 'dark:text-blue-400',
  },
  CO_MENTIONED: {
    label: '뉴스 언급',
    bg: 'bg-amber-100',
    text: 'text-amber-700',
    darkBg: 'dark:bg-amber-900/30',
    darkText: 'dark:text-amber-400',
  },
  HAS_THEME: {
    label: '테마 공유',
    bg: 'bg-purple-100',
    text: 'text-purple-700',
    darkBg: 'dark:bg-purple-900/30',
    darkText: 'dark:text-purple-400',
  },
  SUPPLIED_BY: {
    label: '공급사',
    bg: 'bg-emerald-100',
    text: 'text-emerald-700',
    darkBg: 'dark:bg-emerald-900/30',
    darkText: 'dark:text-emerald-400',
  },
  CUSTOMER_OF: {
    label: '고객사',
    bg: 'bg-cyan-100',
    text: 'text-cyan-700',
    darkBg: 'dark:bg-cyan-900/30',
    darkText: 'dark:text-cyan-400',
  },
  ACQUIRED: {
    label: '인수',
    bg: 'bg-orange-100',
    text: 'text-orange-700',
    darkBg: 'dark:bg-orange-900/30',
    darkText: 'dark:text-orange-400',
  },
  INVESTED_IN: {
    label: '투자',
    bg: 'bg-indigo-100',
    text: 'text-indigo-700',
    darkBg: 'dark:bg-indigo-900/30',
    darkText: 'dark:text-indigo-400',
  },
  PARTNER_OF: {
    label: '파트너',
    bg: 'bg-teal-100',
    text: 'text-teal-700',
    darkBg: 'dark:bg-teal-900/30',
    darkText: 'dark:text-teal-400',
  },
  SPIN_OFF: {
    label: '분사',
    bg: 'bg-pink-100',
    text: 'text-pink-700',
    darkBg: 'dark:bg-pink-900/30',
    darkText: 'dark:text-pink-400',
  },
  SUED_BY: {
    label: '소송',
    bg: 'bg-rose-100',
    text: 'text-rose-700',
    darkBg: 'dark:bg-rose-900/30',
    darkText: 'dark:text-rose-400',
  },
  THEME: {
    label: '테마',
    bg: 'bg-violet-100',
    text: 'text-violet-700',
    darkBg: 'dark:bg-violet-900/30',
    darkText: 'dark:text-violet-400',
  },
  // Phase 6: Keyword Enrichment
  KEYWORD: {
    label: '키워드',
    bg: 'bg-green-100',
    text: 'text-green-700',
    darkBg: 'dark:bg-green-900/30',
    darkText: 'dark:text-green-400',
  },
  // Phase 7: Institutional Holdings
  HELD_BY_SAME_FUND: {
    label: '동일 펀드',
    bg: 'bg-yellow-100',
    text: 'text-yellow-700',
    darkBg: 'dark:bg-yellow-900/30',
    darkText: 'dark:text-yellow-400',
  },
  // Phase 8: Regulatory + Patent
  SAME_REGULATION: {
    label: '규제 공유',
    bg: 'bg-red-200',
    text: 'text-red-800',
    darkBg: 'dark:bg-red-900/40',
    darkText: 'dark:text-red-300',
  },
  PATENT_CITED: {
    label: '특허 인용',
    bg: 'bg-sky-100',
    text: 'text-sky-700',
    darkBg: 'dark:bg-sky-900/30',
    darkText: 'dark:text-sky-400',
  },
  PATENT_DISPUTE: {
    label: '특허 분쟁',
    bg: 'bg-fuchsia-100',
    text: 'text-fuchsia-700',
    darkBg: 'dark:bg-fuchsia-900/30',
    darkText: 'dark:text-fuchsia-400',
  },
};

const THEME_LABELS: Record<string, string> = {
  semiconductor: '반도체',
  ai_ml: 'AI/ML',
  cloud_computing: '클라우드',
  cybersecurity: '사이버보안',
  clean_energy: '클린에너지',
  ev: '전기차',
  fintech: '핀테크',
  biotech: '바이오텍',
  genomics: '유전체학',
  space: '우주산업',
  robotics: '로봇공학',
  blockchain: '블록체인',
  metaverse: '메타버스',
  autonomous_driving: '자율주행',
  quantum_computing: '양자컴퓨팅',
  cannabis: '대마',
  esports: 'e스포츠',
  water: '수자원',
  lithium: '리튬',
  uranium: '우라늄',
  infrastructure: '인프라',
  defense: '방산',
  social_media: '소셜미디어',
  streaming: '스트리밍',
};

export function getTagStyle(type: string): TagStyle {
  return RELATIONSHIP_TAG_STYLES[type] || {
    label: type,
    bg: 'bg-gray-100',
    text: 'text-gray-700',
    darkBg: 'dark:bg-gray-700/50',
    darkText: 'dark:text-gray-300',
  };
}

export function getTagLabel(type: string, label: string): string {
  if (type === 'THEME') {
    return THEME_LABELS[label] || label;
  }
  const style = RELATIONSHIP_TAG_STYLES[type];
  return style?.label || label;
}

export function getTagClasses(type: string): string {
  const style = getTagStyle(type);
  return `${style.bg} ${style.text} ${style.darkBg} ${style.darkText}`;
}

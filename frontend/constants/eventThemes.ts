/**
 * Event Board 테마 한글 라벨 + 아이콘 매핑 (CS-RD3)
 *
 * - key: theme 문자열 (API의 theme 필드)
 * - 미매핑 theme: getLabelForTheme() 함수가 theme 문자열 자체를 폴백 반환
 * - 아이콘명: lucide-react 아이콘명 (문자열, 실제 import는 컴포넌트에서)
 */

export interface ThemeLabelEntry {
  ko: string;
  icon: string; // icon component name from lucide-react
}

export const THEME_LABELS: Record<string, ThemeLabelEntry> = {
  semiconductor: { ko: '반도체', icon: 'Cpu' },
  robotics_ai: { ko: 'AI·로보틱스', icon: 'Bot' },
  clean_energy: { ko: '청정에너지', icon: 'Leaf' },
  lithium_battery: { ko: '리튬배터리', icon: 'Battery' },
  innovation: { ko: '혁신기술', icon: 'Lightbulb' },
  genomics: { ko: '유전체학', icon: 'Dna' },
  biotech: { ko: '바이오테크', icon: 'FlaskConical' },
  regional_banks: { ko: '지역은행', icon: 'Landmark' },
  infrastructure: { ko: '인프라', icon: 'Building2' },
  cybersecurity: { ko: '사이버보안', icon: 'Shield' },
  cloud: { ko: '클라우드', icon: 'Cloud' },
  fintech: { ko: '핀테크', icon: 'CreditCard' },
  space: { ko: '우주·항공', icon: 'Rocket' },
  ev: { ko: '전기차', icon: 'Car' },
  defense: { ko: '방산', icon: 'Crosshair' },
};

/**
 * theme 문자열에 대한 한글 라벨을 반환한다.
 * 미매핑 theme는 theme 문자열 자체를 폴백 반환.
 */
export function getLabelForTheme(theme: string): ThemeLabelEntry {
  return (
    THEME_LABELS[theme] ?? {
      ko: theme,
      icon: 'Tag',
    }
  );
}

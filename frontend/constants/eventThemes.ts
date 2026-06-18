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

/**
 * CS-M2 주도주 지표 메타 — 단일 출처 (drift 방지 위해 THEME_LABELS와 같은 파일).
 * 컴포넌트(MetricInfoPopover 등)는 여기서 문구를 끌어쓴다. 중복 정의 금지.
 *
 * - primary(주신호): trend_quality · theme_beta · capture_spread
 * - supplementary(보조): theme_alpha · up_capture · down_capture
 */
export type MetricKey =
  | 'trend_quality'
  | 'theme_beta'
  | 'capture_spread'
  | 'theme_alpha'
  | 'up_capture'
  | 'down_capture'
  | 'volume_z'
  | 'volatility_pct';

export interface MetricInfo {
  field: MetricKey;
  label: string;
  tier: 'primary' | 'supplementary' | 'context';
  description: string;
  example: string;
  range: string;
}

export const METRIC_INFO: Record<MetricKey, MetricInfo> = {
  trend_quality: {
    field: 'trend_quality',
    label: '추세강도',
    tier: 'primary',
    description:
      '주가가 얼마나 꾸준하고 강하게 움직였는지. 들쭉날쭉 없이 일정하게 오를수록 +로 커지고, 꾸준히 내리면 −가 돼요.',
    example: '예: +0.81 = 강하고 꾸준한 상승 / −0.6 = 꾸준한 하락',
    range: '범위: 음수=하락추세 · 0 근처=중립 · +면 강한 상승',
  },
  theme_beta: {
    field: 'theme_beta',
    label: '그룹 민감도',
    tier: 'primary',
    description:
      '같은 이벤트의 관련 종목들이 움직일 때, 이 종목이 얼마나 크게 따라 움직이는지.',
    example: '예: 1.34 = 그룹이 1% 움직이면 이 종목은 약 1.34%',
    range: '범위: 1보다 크면 더 민감',
  },
  capture_spread: {
    field: 'capture_spread',
    label: '주도우위',
    tier: 'primary',
    description:
      '오를 땐 잘 따라 오르고, 내릴 땐 덜 빠지는 정도(상승 포착 − 하락 포착). 클수록 그룹을 이끄는 주도주.',
    example: '예: +19%p = 상승은 잘 먹고 하락은 잘 버팀',
    range: '범위: 단위 %p(상승포착−하락포착) · +면 유리 · −면 불리',
  },
  theme_alpha: {
    field: 'theme_alpha',
    label: '그룹 초과수익',
    tier: 'supplementary',
    description:
      '같은 그룹 평균보다 이 종목이 얼마나 더(또는 덜) 벌었는지. 그룹이 다 같이 오른 효과를 빼고 본 순수 개별 성과.',
    example: '예: +0.05 = 그룹 평균보다 살짝 앞섬',
    range: '범위: +면 그룹 평균 초과',
  },
  up_capture: {
    field: 'up_capture',
    label: '상승 포착',
    tier: 'supplementary',
    description: '그룹이 오를 때, 이 종목이 그 상승의 몇 %를 따라갔는지.',
    example: '예: 1.18 = 그룹이 오를 때 18% 더 오름',
    range: '범위: 1보다 크면 더 잘 오름',
  },
  down_capture: {
    field: 'down_capture',
    label: '하락 방어',
    tier: 'supplementary',
    description:
      '그룹이 내릴 때, 이 종목이 그 하락을 얼마나 따라 내렸는지. 작을수록 잘 방어.',
    example: '예: 0.99 = 거의 비슷하게 빠짐 (0.85면 덜 빠짐)',
    range: '범위: 1보다 작을수록 잘 방어',
  },
  volume_z: {
    field: 'volume_z',
    label: '거래량 z',
    tier: 'context',
    description:
      '최근 거래량이 평소(과거 평균) 대비 몇 표준편차 위/아래인지. 0=평소, +가 클수록 거래 폭증.',
    example: '예: +1.5 = 평소보다 거래 급증',
    range: '범위: z-score · 0=평소 · +면 급증',
  },
  volatility_pct: {
    field: 'volatility_pct',
    label: '변동성',
    tier: 'context',
    description:
      '그날 변동성이 전체 종목 중 상위 몇 %인지(0~1 백분위). 1에 가까울수록 크게 출렁임.',
    example: '예: 0.90 = 상위 10% 수준 변동',
    range: '범위: 0~1 백분위 · 1에 가까울수록 변동 큼',
  },
};

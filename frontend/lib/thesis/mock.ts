import type { Thesis, ThesisAlert } from './types'

export const MOCK_THESES: Thesis[] = [
  {
    id: 'mock-1',
    title: 'AI 반도체 수요 증가로 NVIDIA 상승 지속',
    direction: 'bullish',
    target: 'NVDA',
    thesis_type: 'sector_trend',
    status: 'active',
    current_state: 'strengthening',
    current_score: 0.72,
    overall_label: '지지 신호 증가',
    created_at: '2025-03-01T09:00:00Z',
    closed_at: null,
    expected_timeframe: '2025-06-01',
    ai_summary: null,
    user: 1,
    source_entry: 'free_input',
    outcome: null,
    outcome_note: '',
  },
  {
    id: 'mock-2',
    title: '금리 인하 기대감으로 부동산 REITs 반등',
    direction: 'bullish',
    target: 'VNQ',
    thesis_type: 'macro_event',
    status: 'active',
    current_state: 'active',
    current_score: 0.15,
    overall_label: '추적 중',
    created_at: '2025-03-05T09:00:00Z',
    closed_at: null,
    expected_timeframe: '2025-09-01',
    ai_summary: null,
    user: 1,
    source_entry: 'news',
    outcome: null,
    outcome_note: '',
  },
  {
    id: 'mock-3',
    title: '중국 경기 둔화로 원자재 약세 전환',
    direction: 'bearish',
    target: 'DBC',
    thesis_type: 'macro_event',
    status: 'active',
    current_state: 'critical',
    current_score: -0.65,
    overall_label: '주의 필요',
    created_at: '2025-02-15T09:00:00Z',
    closed_at: null,
    expected_timeframe: '2025-05-01',
    ai_summary: null,
    user: 1,
    source_entry: 'free_input',
    outcome: null,
    outcome_note: '',
  },
]

// ── Mock 알림 ──
// 고정 ISO 문자열 사용: Date.now() 동적 생성 시 SSR/CSR 시점 차이로 hydration 불일치 발생.
// relativeTime()은 "N일 전" 등으로 표시되므로 고정 날짜로도 충분히 검증 가능.
export const MOCK_ALERTS: ThesisAlert[] = [
  {
    id: 'alert-1',
    thesis: 'mock-1',
    indicator: null,
    alert_type: 'indicator_shift',
    title: 'NVIDIA 외국인 순매수 급증',
    message: '외국인 순매수가 5일 연속 증가하며 강한 지지 신호를 보이고 있어요.',
    is_read: false,
    created_at: '2026-03-11T07:00:00Z',
  },
  {
    id: 'alert-2',
    thesis: 'mock-3',
    indicator: null,
    alert_type: 'state_change',
    title: '원자재 가설 반박 신호 감지',
    message: '구리 선물 가격이 예상과 반대 방향으로 움직이고 있어요.',
    is_read: false,
    created_at: '2026-03-10T20:00:00Z',
  },
  {
    id: 'alert-3',
    thesis: 'mock-2',
    indicator: null,
    alert_type: 'indicator_shift',
    title: 'REITs ETF 거래량 급증',
    message: 'VNQ 거래량이 평소 대비 200% 증가했어요.',
    is_read: false,
    created_at: '2026-03-09T10:00:00Z',
  },
]

// ── Mock 활성화 플래그 ──
// 백엔드 연동 후 .env.local에서 NEXT_PUBLIC_USE_MOCK=false로 전환하거나 파일 자체를 제거.
export const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === 'true'

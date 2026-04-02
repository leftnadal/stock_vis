import type {
  Thesis, ThesisAlert, AlertListResponse, ConversationResponse,
  ThesisIndicator, RecommendedIndicator, DashboardResponse,
  NotableChange, IndicatorReadingsResponse, IndicatorReadingPoint,
} from './types'

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
    entry_source: 'free_input',
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
    entry_source: 'news',
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
    entry_source: 'free_input',
    outcome: null,
    outcome_note: '',
  },
]

// ── Mock 알림 ──
export const MOCK_ALERTS: ThesisAlert[] = [
  {
    id: 'alert-1',
    thesis: 'mock-1',
    indicator: null,
    alert_type: 'indicator_shift',
    severity: 'info',
    title: 'NVIDIA 외국인 순매수 급증',
    message: '외국인 순매수가 5일 연속 증가하며 강한 지지 신호를 보이고 있어요.',
    is_read: false,
    is_pushed: false,
    created_at: '2026-03-11T07:00:00Z',
  },
  {
    id: 'alert-2',
    thesis: 'mock-3',
    indicator: null,
    alert_type: 'state_change',
    severity: 'warning',
    title: '원자재 가설 반박 신호 감지',
    message: '구리 선물 가격이 예상과 반대 방향으로 움직이고 있어요.',
    is_read: false,
    is_pushed: false,
    created_at: '2026-03-10T20:00:00Z',
  },
  {
    id: 'alert-3',
    thesis: 'mock-2',
    indicator: null,
    alert_type: 'indicator_shift',
    severity: 'critical',
    title: 'REITs ETF 거래량 급증',
    message: 'VNQ 거래량이 평소 대비 200% 증가했어요.',
    is_read: false,
    is_pushed: false,
    created_at: '2026-03-09T10:00:00Z',
  },
]

export const MOCK_ALERT_LIST_RESPONSE: AlertListResponse = {
  alerts: MOCK_ALERTS,
  unread_count: MOCK_ALERTS.filter(a => !a.is_read).length,
}

// ── Mock 활성화 플래그 ──
export const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === 'true'

// ═══ 대화형 빌더 Mock 응답 ═══

// ── 뉴스 경로 시작 ──
export const MOCK_CONVERSATION_START_NEWS: ConversationResponse = {
  message: '이 흐름이 어떻게 될 것 같아요?',
  buttons: [
    { id: 'bullish', label: '계속 오른다' },
    { id: 'bearish', label: '곧 꺾인다' },
    { id: 'neutral', label: '잘 모르겠어', long_press_hint: true },
  ],
  selection_mode: 'single',
  long_press_explanations: {
    neutral: '양쪽 시나리오를 동시에 추적하고 싶을 때 선택하세요.',
  },
  conversation_state: {
    conv_id: 'mock-conv-1',
    entry_source: 'news',
    step: 1,
    collected: {},
  },
  step: 1,
  total_steps: 6,
}

// ── 자유입력 경로 시작 ──
export const MOCK_CONVERSATION_START_FREE: ConversationResponse = {
  message: '편하게 써주세요. 한 줄이어도 좋고, 길게 써도 돼요.',
  buttons: [],
  selection_mode: 'single',
  input_type: 'text',
  conversation_state: {
    conv_id: 'mock-conv-2',
    entry_source: 'free_input',
    step: 1,
    collected: {},
  },
  step: 1,
  total_steps: 7,
}

// ── step 2: 이유 선택 (multi) ──
const MOCK_REASON_STEP: ConversationResponse = {
  message: '그렇게 생각하는 이유를 골라주세요. 여러 개 선택할 수 있어요.',
  buttons: [
    { id: 'election', label: '선거/정치 기대감 소멸' },
    { id: 'earnings', label: '기업 실적 부진' },
    { id: 'supply', label: '수급 변화', long_press_hint: true },
    { id: 'policy', label: '정책/규제 변화' },
    { id: 'global', label: '글로벌 영향' },
    { id: 'custom', label: '다른 이유', type: 'text_input' as const },
  ],
  selection_mode: 'multi',
  long_press_explanations: {
    supply: '매수·매도 주문 비율의 변화를 뜻해요. 외국인·기관 매매 동향이 대표적입니다.',
  },
  conversation_state: {
    conv_id: 'mock-conv-1', entry_source: 'news', step: 2,
    collected: { direction: 'bearish' },
  },
  step: 2,
  total_steps: 6,
}

// ── step 3: 시점 선택 (single) ──
const MOCK_TIMEFRAME_STEP: ConversationResponse = {
  message: '언제쯤 그런 흐름이 올 거라고 보시나요?',
  buttons: [
    { id: 'short', label: '1개월 이내' },
    { id: 'medium', label: '1~3개월' },
    { id: 'half', label: '하반기 중' },
    { id: 'year', label: '연말쯤' },
    { id: 'skip', label: '모르겠어' },
  ],
  selection_mode: 'single',
  conversation_state: {
    conv_id: 'mock-conv-1', entry_source: 'news', step: 3,
    collected: { direction: 'bearish', reasons: ['election', 'supply'] },
  },
  step: 3,
  total_steps: 6,
}

// ── step 4: 강도 선택 (single) ──
const MOCK_MAGNITUDE_STEP: ConversationResponse = {
  message: '얼마나 크게 움직일 것 같아요?',
  buttons: [
    { id: 'mild', label: '살짝 조정' },
    { id: 'moderate', label: '꽤 빠진다' },
    { id: 'severe', label: '크게 빠진다' },
    { id: 'skip', label: '모르겠어' },
  ],
  selection_mode: 'single',
  conversation_state: {
    conv_id: 'mock-conv-1', entry_source: 'news', step: 4,
    collected: { direction: 'bearish', reasons: ['election', 'supply'], timeframe: 'half' },
  },
  step: 4,
  total_steps: 6,
}

// ── step 5: 미리보기 확인 (single, preview 포함) ──
const MOCK_PREVIEW_STEP: ConversationResponse = {
  message: '이렇게 정리해봤어요. 확인해주세요.',
  buttons: [
    { id: 'confirm', label: '좋아, 이대로 가자' },
    { id: 'modify', label: '수정할 부분 있어' },
  ],
  selection_mode: 'single',
  conversation_state: {
    conv_id: 'mock-conv-1', entry_source: 'news', step: 5,
    collected: { direction: 'bearish', reasons: ['election', 'supply'], timeframe: 'half', magnitude: 'moderate' },
  },
  step: 5,
  total_steps: 6,
  preview: {
    title: 'KOSPI 하반기 하락 전환',
    direction: 'bearish',
    premises: [
      { content: '선거 후 정치 기대감 소멸', category: 'sentiment' },
      { content: '외국인 매도세 전환', category: 'macro' },
    ],
    indicators: [
      { name: '외국인 순매수', indicator_type: 'order_flow' },
      { name: '원/달러 환율', indicator_type: 'macro' },
      { name: 'KOSPI EPS', indicator_type: 'valuation' },
    ],
  },
}

// ── step 6: 완료 ──
export const MOCK_CONVERSATION_DONE: ConversationResponse = {
  message: '가설이 등록되었습니다.\n\n이제 매일 이 지표들을 관제실에서 추적할 거예요.',
  buttons: [],
  selection_mode: 'single',
  conversation_state: {
    conv_id: 'mock-conv-1', entry_source: 'news', step: 6,
    collected: {},
  },
  step: 6,
  total_steps: 6,
  done: true,
  thesis_id: 'mock-thesis-new',
}

// ── free_input step 2: Gemini 파싱 결과 확인 (single) ──
const MOCK_FREE_CONFIRM_STEP: ConversationResponse = {
  message: '이렇게 정리해봤어요.\n\n"KOSPI가 하반기에 하락 전환할 것이다"\n\n맞나요?',
  buttons: [
    { id: 'confirm', label: '맞아, 이대로 가자' },
    { id: 'modify', label: '좀 다르게 바꿀래' },
    { id: 'add_premise', label: '근거를 더 추가할래' },
  ],
  selection_mode: 'single',
  conversation_state: {
    conv_id: 'mock-conv-2', entry_source: 'free_input', step: 2,
    collected: { raw_input: '코스피 하반기 하락' },
  },
  step: 2,
  total_steps: 7,
}

// ── entry_source별 Mock Map 분리 ──

export const MOCK_NEWS_STEP_MAP: Record<number, ConversationResponse> = {
  2: MOCK_REASON_STEP,
  3: MOCK_TIMEFRAME_STEP,
  4: MOCK_MAGNITUDE_STEP,
  5: MOCK_PREVIEW_STEP,
  6: MOCK_CONVERSATION_DONE,
}

export const MOCK_FREE_STEP_MAP: Record<number, ConversationResponse> = {
  2: MOCK_FREE_CONFIRM_STEP,
  3: MOCK_REASON_STEP,
  4: MOCK_TIMEFRAME_STEP,
  5: MOCK_MAGNITUDE_STEP,
  6: MOCK_PREVIEW_STEP,
  7: MOCK_CONVERSATION_DONE,
}

export const MOCK_STEP_MAP = MOCK_NEWS_STEP_MAP

// ═══ LLM 모드 Mock 응답 (Phase A-MVP) ═══

// ── LLM 기본 경로: "삼성전자 반등" → proposal → preset → confirm → complete ──

export const MOCK_LLM_PROPOSAL: ConversationResponse = {
  message: '삼성전자의 반등 가설을 설계했어요.\n\nHBM3E 양산 본격화와 외국인 매수 전환을 주요 근거로 보고 있어요. 어떻게 생각하세요?',
  buttons: [
    { id: 'short', label: '⚡ 단기 (1개월)' },
    { id: 'medium', label: '📈 중기 (1~3개월)' },
    { id: 'long', label: '🔭 장기 (6개월+)' },
  ],
  selection_mode: 'single',
  conversation_state: {
    conv_id: 'mock-llm-1',
    entry_source: 'free_input',
    step: 2,
    collected: { direction: 'bullish', target: '삼성전자' },
    mode: 'llm',
    phase: 'preset',
    turn_count: 1,
  },
  step: 2,
  total_steps: 3,
  phase: 'preset',
  confidence: 'high',
  needs_preset: true,
  indicator_recommendations: [
    {
      premise_title: 'HBM3E 양산 본격화',
      indicator_name: 'EPS 추이',
      why: '실적 개선 추적',
      signal_type: 'coincident',
      auto_matched: true,
      match_method: 'pk',
    },
    {
      premise_title: '외국인 매수 전환',
      indicator_name: '외국인 순매수 추이',
      why: '수급 변화 감지',
      signal_type: 'leading',
      auto_matched: true,
      match_method: 'pk',
    },
    {
      premise_title: '반도체 사이클 회복',
      indicator_name: 'KOSPI 지수',
      why: '시장 전체 방향',
      signal_type: 'coincident',
      auto_matched: false,
      match_method: 'text',
    },
  ],
}

export const MOCK_LLM_CONFIRM: ConversationResponse = {
  message: '등록 준비 완료!\n\n    가설: 삼성전자 2분기 반등\n    방향: 상승\n    모니터링: 📈 중기 (1~3개월)\n    전제: 2개\n\n등록할까요?',
  buttons: [
    { id: 'confirm', label: '등록' },
    { id: 'restart', label: '다시 만들기' },
  ],
  selection_mode: 'single',
  conversation_state: {
    conv_id: 'mock-llm-1',
    entry_source: 'free_input',
    step: 3,
    collected: { direction: 'bullish', target: '삼성전자' },
    mode: 'llm',
    phase: 'confirm',
    turn_count: 2,
  },
  step: 3,
  total_steps: 3,
  phase: 'confirm',
}

export const MOCK_LLM_COMPLETE: ConversationResponse = {
  message: '가설이 등록되었어요! 관제실에서 지표 변화를 추적할 수 있어요.',
  buttons: [],
  selection_mode: 'single',
  conversation_state: {
    conv_id: 'mock-llm-1',
    entry_source: 'free_input',
    step: 3,
    collected: {},
    mode: 'llm',
    phase: 'complete',
    turn_count: 3,
  },
  step: 3,
  total_steps: 3,
  phase: 'complete',
  done: true,
  is_complete: true,
  thesis_id: 'mock-llm-thesis-1',
  created_thesis: {
    thesis_id: 'mock-llm-thesis-1',
    title: '삼성전자 2분기 반등',
    dashboard_url: '/thesis/mock-llm-thesis-1',
  },
}

// ── LLM fallback 경로: proposal 실패 → wizard 전환 ──

export const MOCK_LLM_FALLBACK: ConversationResponse = {
  message: 'AI 분석에 문제가 생겼어요.\n단계별로 진행할게요.',
  buttons: [
    { id: 'wizard', label: '단계별로 진행' },
    { id: 'retry', label: '다시 시도' },
  ],
  selection_mode: 'single',
  conversation_state: {
    conv_id: 'mock-llm-2',
    entry_source: 'free_input',
    step: 1,
    collected: {},
  },
  step: 1,
  total_steps: 6,
  phase: 'fallback',
  fallback_reason: 'llm_api_error',
}

// ── LLM step map (mock에서 사용) ──

export const MOCK_LLM_STEP_MAP: Record<number, ConversationResponse> = {
  2: MOCK_LLM_PROPOSAL,
  3: MOCK_LLM_CONFIRM,
  4: MOCK_LLM_COMPLETE,
}

// ── LLM 시작 응답 ──

export const MOCK_LLM_START: ConversationResponse = {
  message: '어떤 투자 아이디어가 있으세요?\n한 줄이면 충분해요.',
  buttons: [],
  selection_mode: 'single',
  input_type: 'text',
  conversation_state: {
    conv_id: 'mock-llm-1',
    entry_source: 'free_input',
    step: 1,
    collected: {},
    mode: 'llm',
    phase: 'proposal',
    turn_count: 0,
  },
  step: 1,
  total_steps: 3,
  phase: 'proposal',
}

// ═══ PR-4: 지표 설정 Mock 데이터 ═══

export const MOCK_INDICATORS: ThesisIndicator[] = [
  {
    id: 'ind-1',
    name: '외국인 순매수 추이',
    indicator_type: 'market_data',
    data_source: 'fmp',
    data_params: { metric: 'foreign_net_buy' },
    support_direction: 'positive',
    weight: 1.0,
    is_active: true,
    is_paused: false,
    current_arrow_degree: 35,
    current_label: '지지하는 편',
    current_color: '#60A5FA',
    current_score: 0.65,
    premise: null,
    created_at: '2026-03-13T10:00:00Z',
  },
  {
    id: 'ind-2',
    name: '원/달러 환율',
    indicator_type: 'macro',
    data_source: 'fmp',
    data_params: { symbol: 'USDKRW' },
    support_direction: 'negative',
    weight: 1.0,
    is_active: true,
    is_paused: false,
    current_arrow_degree: 110,
    current_label: '약화하는 편',
    current_color: '#FB923C',
    current_score: -0.3,
    premise: null,
    created_at: '2026-03-13T10:00:00Z',
  },
  {
    id: 'ind-3',
    name: 'VIX (공포지수)',
    indicator_type: 'macro',
    data_source: 'fmp',
    data_params: { symbol: '^VIX' },
    support_direction: 'negative',
    weight: 1.0,
    is_active: false,
    is_paused: false,
    current_arrow_degree: 90,
    current_label: '중립',
    current_color: '#D1D5DB',
    current_score: 0,
    premise: null,
    created_at: '2026-03-13T10:00:00Z',
  },
]

// ═══ PR-5: 대시보드 Mock 데이터 ═══

export const MOCK_DASHBOARD: DashboardResponse = {
  thesis: {
    id: 'mock-1',
    title: 'AI 반도체 수요 증가로 NVIDIA 상승 지속',
    direction: 'bullish',
    status: 'active',
    days_active: 32,
    overall_score: 0.45,
    overall_label: '조금씩 밝아지고 있어요',
    overall_phase: 'waxing',
    recent_change: '외국인 순매수가 3일 연속 증가하며 강한 지지 신호를 보이고 있어요.',
    overall_delta: null,
    snapshot_date: '2026-03-18',
    ai_summary: '지난 7일간 외국인 순매수가 감소 추세를 보이고 있어요. 원/달러 환율은 소폭 상승했지만 VIX는 안정적이에요. 전체적으로 가설을 약하게 지지하는 흐름이에요.',
    notable_changes: [
      {
        indicator_id: 'dash-ind-1',
        indicator_name: '외국인 순매수 추이',
        change_type: 'sharp_move' as const,
        description: '전일 대비 급변 (+22.4%)',
        raw_value_before: 9.8e11,
        raw_value_after: 1.2e12,
        change_pct: 22.4,
        severity: 'warning' as const,
      },
      {
        indicator_id: 'dash-ind-2',
        indicator_name: '원/달러 환율',
        change_type: 'direction_flip' as const,
        description: '하락 추세에서 상승 전환',
        raw_value_before: 1365,
        raw_value_after: 1380,
        change_pct: 1.1,
        severity: 'info' as const,
      },
    ],
  },
  indicators: [
    {
      id: 'dash-ind-1',
      name: '외국인 순매수 추이',
      arrow_degree: 35.2,
      score: 0.65,
      color: '#60A5FA',
      label: '지지하는 편',
      previous_degree: 42.0,
      trend: 'strengthening',
      premise_name: 'AI 반도체 수급 개선',
      is_extreme_vol: false,
      raw_value: 1.2e12,
      raw_value_unit: '원',
      previous_raw_value: 9.8e11,
      change_pct: 22.4,
      raw_value_asof: '2026-03-18T09:00:00Z',
      fiscal_label: null,
      quarterly_history: null,
      is_quarterly: false,
      comparison_type: null,
    },
    {
      id: 'dash-ind-2',
      name: '원/달러 환율',
      arrow_degree: 110.5,
      score: -0.3,
      color: '#FB923C',
      label: '약화하는 편',
      previous_degree: 105.0,
      trend: 'weakening',
      premise_name: '글로벌 달러 강세',
      is_extreme_vol: false,
      raw_value: 1380,
      raw_value_unit: '원',
      previous_raw_value: 1365,
      change_pct: 1.1,
      raw_value_asof: '2026-03-18T09:00:00Z',
      fiscal_label: null,
      quarterly_history: null,
      is_quarterly: false,
      comparison_type: null,
    },
    {
      id: 'dash-ind-3',
      name: 'VIX (공포지수)',
      arrow_degree: 88.0,
      score: 0.02,
      color: '#D1D5DB',
      label: '중립',
      previous_degree: 90.0,
      trend: 'stable',
      premise_name: '시장 심리',
      is_extreme_vol: false,
      raw_value: 18.5,
      raw_value_unit: 'pt',
      previous_raw_value: 18.2,
      change_pct: 1.6,
      raw_value_asof: '2026-03-17T21:00:00Z',
      fiscal_label: null,
      quarterly_history: null,
      is_quarterly: false,
      comparison_type: null,
    },
  ],
  heatmap: {
    rows: 1,
    cols: 3,
    cells: [
      { name: '외국인 순매수', color: '#60A5FA', degree: 35.2 },
      { name: '원/달러 환율', color: '#FB923C', degree: 110.5 },
      { name: 'VIX', color: '#D1D5DB', degree: 88.0 },
    ],
  },
}

// ═══ Phase 3: Mock Readings 데이터 ═══

function generateMockReadings(
  base: number, vol: number, days: number,
): IndicatorReadingPoint[] {
  const points: IndicatorReadingPoint[] = []
  const now = new Date()
  for (let i = days; i >= 0; i--) {
    const date = new Date(now)
    date.setDate(date.getDate() - i)
    const noise = (Math.random() - 0.5) * 2 * vol
    const trend = ((days - i) / days) * vol * 0.3
    points.push({
      asof: date.toISOString(),
      value: Math.random() * 2 - 1,
      raw_value: base + noise + trend,
    })
  }
  return points
}

export const MOCK_READINGS: Record<string, IndicatorReadingsResponse> = {
  'dash-ind-1': {
    indicator_id: 'dash-ind-1',
    indicator_name: '외국인 순매수 추이',
    support_direction: 'positive',
    unit: '원',
    readings: generateMockReadings(1e12, 1e11, 30),
    count: 31,
  },
  'dash-ind-2': {
    indicator_id: 'dash-ind-2',
    indicator_name: '원/달러 환율',
    support_direction: 'negative',
    unit: '원',
    readings: generateMockReadings(1365, 15, 30),
    count: 31,
  },
  'dash-ind-3': {
    indicator_id: 'dash-ind-3',
    indicator_name: 'VIX (공포지수)',
    support_direction: 'positive',
    unit: 'pt',
    readings: generateMockReadings(17.5, 2, 30),
    count: 31,
  },
}

export const MOCK_RECOMMENDATIONS: RecommendedIndicator[] = [
  {
    name: 'KOSPI 지수',
    data_source: 'fmp',
    data_params: { symbol: '^KS11' },
    indicator_type: 'market_data',
    support_direction: 'positive',
    reason: 'KOSPI 지수는 한국 시장 전체의 방향을 보여주는 대표 지표입니다.',
  },
  {
    name: '미국 기준금리 (Fed Funds Rate)',
    data_source: 'fred',
    data_params: { series_id: 'FEDFUNDS' },
    indicator_type: 'macro',
    support_direction: 'negative',
    reason: '기준금리 변동은 유동성과 할인율에 영향을 미칩니다.',
  },
  {
    name: 'RSI (14일)',
    data_source: 'fmp',
    data_params: { indicator: 'RSI', period: 14 },
    indicator_type: 'technical',
    support_direction: 'positive',
    reason: 'RSI는 단기 과매수/과매도 상태를 파악하는 기술적 지표입니다.',
  },
]

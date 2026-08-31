/**
 * ⚠️ 이 데이터는 유저 가이드이자 야간 도그푸딩 에이전트의 채점 루브릭 단일 출처다.
 *    coreQuestion을 바꾸면 에이전트 평가 기준이 바뀐다.
 *
 * GUIDE-S1C(2026-08-27): v1(/market-pulse) 기준 초안을 폐기하고 v2 기준으로 교체.
 * v1에는 가이드 데이터를 두지 않는다 — 가이드 미제공 = 은퇴 신호(D-MP-V2-NAV).
 */
import type { GuideScreen } from './types';

export const MARKET_PULSE_GUIDE: GuideScreen[] = [
  {
    id: 'marketPulse.main',
    route: '/market-pulse-v2',
    title: 'Market Pulse v2 — 시장 국면',
    flowStage: 1,
    coreQuestion: '지금 시장은 어떤 국면에 있고, 어제와 무엇이 달라졌는가?',
    learnings: [
      '시장이 지금 어떤 국면(Regime)에 있는지, 그리고 스트레스가 어느 수준인지 — 모든 종목 판단의 배경',
      '어제와 달라진 것이 무엇인지 — 매일 보는 사람에게는 수준이 아니라 변화가 정보다',
      '여러 신호가 같은 방향으로 합류하고 있는지, 아니면 한두 개만 튀는 것인지',
    ],
    regions: [
      {
        anchor: 'marketPulse.regime',
        title: '국면 히어로',
        desc: '시장 국면을 한 장으로 요약한 이 화면의 중심입니다. 여기 붙는 스트레스 밴드는 "이 국면이 얼마나 팽팽한 상태에서 진행 중인가"를 함께 알려줍니다. 오늘의 모든 종목 신호는 이 배경 위에서 읽어야 합니다.',
      },
      {
        anchor: 'marketPulse.delta',
        title: '어제와 달라진 것',
        desc: '매일 들어오는 사람이 가장 먼저 볼 자리입니다. 국면·섹터·이상 신호 중 어제 대비 바뀐 것만 추려 보여줍니다. 섹터 변화를 누르면 아래 히트맵이 그 섹터를 강조한 상태로 열립니다.',
      },
      {
        anchor: 'marketPulse.anomaly',
        title: '이상 신호',
        desc: '평소 범위를 벗어난 움직임의 목록입니다. 하나하나는 소음일 수 있습니다 — 다음 칸(플레이북)에서 합류 여부를 확인하는 것이 사용법입니다.',
      },
      {
        anchor: 'marketPulse.playbook',
        title: '거시 플레이북',
        desc: '서로 다른 신호들이 같은 시나리오를 가리키는지 봅니다. 부분 점등과 완전 점등을 구분해서, "신호 하나"와 "신호의 합류"를 다르게 취급하게 해주는 자리입니다.',
      },
      {
        anchor: 'marketPulse.sector',
        title: '섹터 흐름',
        desc: '돈이 어느 섹터로 흘러들고 어디서 빠지는지의 지도입니다. 개별 종목의 등락이 종목 자체 이유인지, 섹터 전체의 흐름인지를 여기서 가립니다.',
      },
      {
        anchor: 'marketPulse.breadth-concentration',
        title: '폭 · 집중도',
        desc: '상승이 시장 전체에 퍼져 있는지(폭), 소수 대형주가 끌고 있는지(집중도)를 봅니다. 지수가 올라도 폭이 좁고 집중이 높다면, 그 상승은 보기보다 얇은 것입니다.',
      },
      {
        anchor: 'marketPulse.analog-brief',
        title: '유사 국면 · 브리핑',
        desc: '지금과 비슷했던 과거 국면에 무엇이 이어졌는지(유사 국면), 오늘 화면 전체를 글로 풀어낸 요약(브리핑), 배경 뉴스입니다. 숫자로 본 것을 문장으로 재확인하는 마무리 자리입니다.',
      },
    ],
    nextAction: { label: '이 국면 배경 위에서 오늘의 종목 신호 보기 (대시보드)', route: '/' },
    // 병진 검수 승인 2026-08-27 (GUIDE-S1C) — v2 기준 문구로 교체 후 승인
    reviewStatus: 'confirmed',
  },
  {
    // MP2-SUBPAGES S1 (2026-08-31) — 거시 근거 허브. reviewStatus draft(병진 검수 전).
    id: 'marketPulse.macro',
    route: '/market-pulse-v2/macro',
    title: '거시 근거 — 금리·심리·글로벌',
    flowStage: 1,
    coreQuestion: '오늘 국면의 거시 근거(금리·심리·글로벌)는 무엇인가?',
    learnings: [
      '시장 심리(공포·탐욕)가 지금 어느 쪽으로 기울어 있는지 — 국면을 읽는 배경 온도',
      '금리·수익률 곡선과 물가·고용 지표가 국면과 같은 방향을 가리키는지',
      '글로벌 지수·환율·원자재가 미국 시장과 어떻게 맞물려 움직이는지',
    ],
    regions: [
      {
        anchor: 'marketPulse.macro.sentiment',
        title: '공포·탐욕 (심리)',
        desc: '시장 심리를 한 눈금으로 요약합니다. 국면 판단의 배경 온도 — 같은 신호도 공포 구간과 탐욕 구간에서 다르게 읽어야 합니다.',
      },
      {
        anchor: 'marketPulse.macro.rates',
        title: '수익률 곡선 (금리)',
        desc: '단기·장기 금리와 곡선 형태입니다. 역전·정상화 여부가 국면 전환의 선행 신호가 되곤 합니다.',
      },
      {
        anchor: 'marketPulse.macro.economy',
        title: '물가·고용·성장 (지표)',
        desc: '인플레이션·고용·성장 지표입니다. 금리 탭과 함께 "왜 이 금리인가"의 배경을 이룹니다.',
      },
      {
        anchor: 'marketPulse.macro.global',
        title: '글로벌 시장',
        desc: '해외 지수·환율·원자재입니다. 미국 시장 신호가 글로벌과 합류하는지, 혼자 튀는지 확인하는 자리입니다.',
      },
    ],
    nextAction: { label: '국면 판단 화면으로 돌아가기', route: '/market-pulse-v2' },
    reviewStatus: 'draft',
  },
];

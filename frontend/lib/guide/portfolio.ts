/**
 * ⚠️ 이 데이터는 유저 가이드이자 야간 도그푸딩 에이전트의 채점 루브릭 단일 출처다.
 *    coreQuestion을 바꾸면 에이전트 평가 기준이 바뀐다.
 */
import type { GuideScreen } from './types';

export const PORTFOLIO_GUIDE: GuideScreen[] = [
  {
    id: 'portfolio.main',
    route: '/portfolio',
    title: '포트폴리오 — 판단의 결과',
    flowStage: 5,
    coreQuestion: '앞 단계에서 내린 판단들이 실제 내 자산에 어떤 모습으로 남아 있나?',
    learnings: [
      '전체 평가액과 손익 — 지금까지의 판단이 합쳐진 결과',
      '자산이 어디에 몰려 있는지 — 확신이 아니라 편중일 수 있는 자리',
      '종목별로 무엇이 끌고 있고 무엇이 끌어내리고 있는지',
    ],
    regions: [
      {
        anchor: 'portfolio.add',
        title: '종목 추가 · 새로고침',
        desc: '보유 종목을 등록하고 최신 가격을 다시 불러옵니다. 여기 등록된 것만 아래 요약·차트에 반영됩니다.',
      },
      {
        anchor: 'portfolio.summary',
        title: '요약',
        desc: '총 평가액과 누적 손익입니다. 이 숫자 하나로 판단의 좋고 나쁨을 결론짓지 않는 것이 중요합니다 — 시장 전체가 오른 구간에서는 함께 오른 것일 수 있습니다.',
      },
      {
        anchor: 'portfolio.charts',
        title: '포트폴리오 분석',
        desc: '구성비는 "어디에 몰려 있나", 수익률은 "무엇이 끌고 있나"를 봅니다. 구성비가 한쪽으로 크게 기울어 있다면, 그건 확신의 표현일 수도 있고 방치의 결과일 수도 있습니다.',
      },
      {
        anchor: 'portfolio.holdings',
        title: '보유 종목',
        desc: '종목별 상세입니다. 카드/표를 전환해 볼 수 있습니다. 여기서 어긋나기 시작한 종목을 발견하면, 그 판단을 Monitor로 되돌려 다시 추적하는 것이 이 서비스의 한 바퀴입니다.',
      },
    ],
    nextAction: { label: '어긋나기 시작한 판단 다시 추적하기 (Monitor)', route: '/monitor' },
    reviewStatus: 'draft',
  },
];

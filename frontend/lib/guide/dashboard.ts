/**
 * ⚠️ 이 데이터는 유저 가이드이자 야간 도그푸딩 에이전트의 채점 루브릭 단일 출처다.
 *    coreQuestion을 바꾸면 에이전트 평가 기준이 바뀐다.
 */
import type { GuideScreen } from './types';

export const DASHBOARD_GUIDE: GuideScreen[] = [
  {
    id: 'dashboard.main',
    route: '/',
    title: '대시보드 — 오늘의 시그널',
    flowStage: 1,
    coreQuestion: '오늘 장이 끝난 시점에서, 내가 눈여겨봐야 할 종목은 무엇이고 왜 그런가?',
    learnings: [
      '어느 종목에서 어떤 종류의 움직임(모멘텀·거래량·돌파·반전·관계)이 관측됐는지',
      '그 움직임이 여러 축에서 동시에 나타나는지(합류) — 한 축만 튀는 신호와 구분된다',
      '지금 보는 숫자가 언제 만들어진 것인지 — 오래된 데이터면 배지가 먼저 말해준다',
    ],
    regions: [
      {
        anchor: 'dashboard.freshness',
        title: '데이터 신선도',
        desc: '이 화면의 모든 숫자가 어느 거래일 기준인지, 그리고 그 값이 낡았는지 알려줍니다. 여기가 stale이면 아래 카드들의 판단도 낡은 것입니다 — 먼저 이걸 보세요.',
      },
      {
        anchor: 'dashboard.market-summary',
        title: '시장 요약',
        desc: '개별 종목을 보기 전 배경입니다. 오늘 시장 전체가 오른 날인지 내린 날인지에 따라, 같은 +3%도 의미가 달라집니다.',
      },
      {
        anchor: 'dashboard.recommendations',
        title: '추천 카드',
        desc: '오늘 신호 중 우선 볼 만한 것을 앞으로 꺼내 둔 자리입니다. 추천은 결론이 아니라 "먼저 확인해볼 후보"입니다 — 근거는 카드를 열어야 보입니다.',
      },
      {
        anchor: 'dashboard.filter-tabs',
        title: '카테고리 필터',
        desc: '신호를 종류별로 나눠 봅니다. 지금 궁금한 게 "많이 오른 종목"인지 "거래량이 튄 종목"인지에 따라 봐야 할 탭이 다릅니다.',
      },
      {
        anchor: 'dashboard.signal-cards',
        title: '시그널 카드',
        desc: '종목 하나당 카드 하나. 카드를 누르면 그 신호가 왜 잡혔는지 근거와 관련 뉴스가 열립니다. 카드 앞면의 숫자만 보고 판단하지 않는 것이 이 화면의 사용법입니다.',
      },
    ],
    nextAction: { label: '이 움직임이 어디까지 번졌는지 보기 (Chain Sight)', route: '/chainsight' },
    // 병진 검수 승인 2026-08-27 (GUIDE-S1C)
    reviewStatus: 'confirmed',
  },
];

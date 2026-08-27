/**
 * ⚠️ 이 데이터는 유저 가이드이자 야간 도그푸딩 에이전트의 채점 루브릭 단일 출처다.
 *    coreQuestion을 바꾸면 에이전트 평가 기준이 바뀐다.
 */
import type { GuideScreen } from './types';

export const MARKET_PULSE_GUIDE: GuideScreen[] = [
  {
    id: 'marketPulse.main',
    route: '/market-pulse',
    title: 'Market Pulse — 시장 전체의 온도',
    flowStage: 1,
    coreQuestion: '지금 시장은 위험을 사려는 국면인가, 피하려는 국면인가?',
    learnings: [
      '투자자 심리가 공포 쪽인지 탐욕 쪽인지 — 개별 종목 판단의 배경이 되는 값',
      '금리 곡선의 모양이 경기 확장을 가리키는지 위축을 가리키는지',
      '이번 주 시장을 흔들 수 있는 경제 일정이 언제 있는지 — 판단을 미룰 이유가 되는 날',
    ],
    regions: [
      {
        anchor: 'marketPulse.movers',
        title: '오늘의 급등·급락',
        desc: '시장의 양 극단입니다. 여기 오르내린 종목의 성격(대형주인가 소형주인가, 한 섹터에 몰렸는가)이 오늘 장의 성격을 말해줍니다.',
      },
      {
        anchor: 'marketPulse.fear-greed',
        title: 'Fear & Greed 지수',
        desc: '시장 심리를 하나의 숫자로 압축한 값입니다. 극단으로 치우친 값은 "지금 들어가라"가 아니라 "지금 다들 한쪽으로 쏠려 있다"는 사실의 보고입니다.',
      },
      {
        anchor: 'marketPulse.yield-curve',
        title: '국채 수익률 곡선',
        desc: '단기·장기 금리의 모양입니다. 곡선이 뒤집히면(장기 < 단기) 시장이 앞날을 어둡게 본다는 신호로 읽힙니다. 개별 종목보다 훨씬 느리게 움직이는 배경 변수입니다.',
      },
      {
        anchor: 'marketPulse.economy',
        title: '주요 경제 지표',
        desc: '물가·고용 등 시장 전체를 움직이는 지표입니다. 여기가 바뀌면 개별 종목의 좋고 나쁨과 무관하게 전체가 함께 움직입니다.',
      },
      {
        anchor: 'marketPulse.calendar',
        title: '경제 캘린더',
        desc: '이번 주 예정된 발표 일정입니다. 영향도 높음(빨간 점) 이벤트 직전에는 판단을 확정하기보다 미루는 편이 낫다는 것을 알려주는 자리입니다.',
      },
    ],
    nextAction: { label: '이 배경 위에서 오늘의 종목 신호 보기 (대시보드)', route: '/' },
    reviewStatus: 'draft',
  },
];

/**
 * ⚠️ 이 데이터는 유저 가이드이자 야간 도그푸딩 에이전트의 채점 루브릭 단일 출처다.
 *    coreQuestion을 바꾸면 에이전트 평가 기준이 바뀐다.
 */
import type { GuideScreen } from './types';

export const CHAINSIGHT_GUIDE: GuideScreen[] = [
  {
    id: 'chainsight.main',
    route: '/chainsight',
    title: 'Chain Sight — 이벤트 보드',
    flowStage: 2,
    coreQuestion: '한 종목의 움직임이 어디까지 번지고 있으며, 그 연결을 얼마나 믿어도 되나?',
    learnings: [
      '지금 함께 움직이는 종목 묶음(테마)이 무엇이고, 그중 어디가 가장 달아올랐는지',
      '그 묶음이 몇 종목으로 이뤄져 있는지 — 근거가 얇은 묶음은 화면이 먼저 표시해 줍니다',
      '개별 종목에서 출발해 공급망·ETF·테마로 이어지는 연결을 따라가는 방법',
    ],
    regions: [
      {
        anchor: 'chainsight.event-grid',
        title: '테마 카드 그리드',
        desc: '함께 움직이는 종목 묶음을 달아오른 순서로 늘어놓았습니다. 카드를 누르면 그 테마에 속한 종목과, 왜 한 묶음으로 봤는지가 열립니다.',
      },
      {
        anchor: 'chainsight.card-metrics',
        title: '카드의 세 숫자',
        desc: '등락률(가장 크게 표시) · 관심도 · 종목 수. 등락률이 커도 종목 수가 적으면 몇 종목의 움직임이 묶음 전체를 끌어올린 것일 수 있습니다. 구성 종목이 3개 미만이면 근거가 얇다는 표식이 카드에 붙습니다.',
      },
      {
        anchor: 'chainsight.entrypoints',
        title: '마인드맵 · 관계 그래프',
        desc: '테마 단위가 아니라 연결 자체를 보고 싶을 때 들어갑니다. 업종 마인드맵은 위에서 아래로 훑는 지도이고, 관계 그래프는 종목 사이의 실제 연결선을 보여줍니다. 이 연결선의 굵기가 곧 학습된 관계 신뢰도(RelationConfidence)입니다.',
      },
    ],
    nextAction: { label: '눈에 든 대상을 계속 추적하기 (Monitor)', route: '/monitor' },
    // 병진 검수 승인 2026-08-27 (GUIDE-S1C)
    reviewStatus: 'confirmed',
  },
];

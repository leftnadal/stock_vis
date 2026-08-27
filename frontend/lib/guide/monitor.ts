/**
 * ⚠️ 이 데이터는 유저 가이드이자 야간 도그푸딩 에이전트의 채점 루브릭 단일 출처다.
 *    coreQuestion을 바꾸면 에이전트 평가 기준이 바뀐다.
 */
import type { GuideScreen } from './types';

export const MONITOR_GUIDE: GuideScreen[] = [
  {
    id: 'monitor.main',
    route: '/monitor',
    title: 'Monitor — 내 판단 추적',
    flowStage: 3,
    coreQuestion: '내가 세운 판단이 지금도 유효한가, 아니면 이미 깨졌는가?',
    learnings: [
      '내가 무엇을 왜 지켜보기로 했는지 — 등록한 근거가 판단과 함께 남아 있습니다',
      '그 판단이 진행 중인지 마감됐는지, 마감됐다면 맞았는지 틀렸는지',
      '지켜보는 대상이 종목 하나인지, 시장·섹터·테마 같은 더 큰 단위인지',
    ],
    regions: [
      {
        anchor: 'monitor.new',
        title: '새 모니터',
        desc: '추적을 시작하는 입구입니다. 여기서 "무엇을 · 왜 · 어떤 조건이면 판단이 깨지는가"를 미리 적어 둡니다. 조건을 미리 적는 것이 이 화면의 핵심입니다 — 나중에 기억으로 고쳐 쓰지 못하게 하기 위함입니다.',
      },
      {
        anchor: 'monitor.scope-chips',
        title: '범위 칩',
        desc: '추적 대상의 단위로 걸러 봅니다(종목 · 시장 · 섹터 · 테마 · 펀드). "시나리오만" 칩은 조건까지 적어 둔 판단만 남깁니다.',
      },
      {
        anchor: 'monitor.status-segment',
        title: '진행 / 마감 전환',
        desc: '진행 중인 판단과 이미 결론이 난 판단을 나눠 봅니다. 마감된 것이 하나도 없으면 이 전환기는 아예 표시되지 않습니다.',
      },
      {
        anchor: 'monitor.list',
        title: '모니터 카드 목록',
        desc: '판단 하나당 카드 하나. 카드에는 현재 상태와, 조건을 적어 둔 경우 지금 가격이 그 조건의 어디쯤인지가 함께 표시됩니다. 카드를 누르면 등록 당시의 근거와 그 뒤 무엇이 바뀌었는지가 열립니다.',
      },
    ],
    nextAction: { label: '유지하기로 한 판단을 실제 보유에 반영하기 (포트폴리오)', route: '/portfolio' },
    reviewStatus: 'draft',
  },
];

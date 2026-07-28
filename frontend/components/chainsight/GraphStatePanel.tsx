/**
 * 그래프 상태 패널 (⑳-E S3/S4) — 빈 캔버스 조용한 수렴을 금지하고 상태를 명시 분리.
 *
 * variant:
 *  - 'empty-neighbors'    : ego 200·관계 0 (이웃 없음). 오류 아님 — 안내만.
 *  - 'load-error'         : ego 로드 실패(404/500/예외) 또는 focus 미해석. 재시도 제공.
 *  - 'sector-unavailable' : 섹터 관계망(Neo4j 의존) 현재 이용 불가(S4). 재시도 제공.
 *
 * UX 용어 규약: "테마" 금지 — "관계망/관계" 사용.
 */

type GraphStateVariant = 'empty-neighbors' | 'load-error' | 'sector-unavailable';

interface GraphStatePanelProps {
  variant: GraphStateVariant;
  /** empty-neighbors·load-error 에서 중심 종목명 표기용 */
  symbol?: string | null;
  /** load-error·sector-unavailable 재시도 핸들러 */
  onRetry?: () => void;
}

const COPY: Record<
  GraphStateVariant,
  { testId: string; title: string; body: string; retry: boolean; tone: 'neutral' | 'error' }
> = {
  'empty-neighbors': {
    testId: 'graph-state-empty-neighbors',
    title: '아직 확인된 관계가 없어요',
    body: '이 종목과 연결된 관계를 아직 찾지 못했어요. 관계가 확인되면 여기에 관계망이 나타납니다.',
    retry: false,
    tone: 'neutral',
  },
  'load-error': {
    testId: 'graph-state-load-error',
    title: '관계망을 불러오지 못했어요',
    body: '일시적인 문제로 관계망을 가져오지 못했어요. 잠시 후 다시 시도해 주세요.',
    retry: true,
    tone: 'error',
  },
  'sector-unavailable': {
    testId: 'graph-state-sector-unavailable',
    title: '섹터 관계망은 현재 이용할 수 없어요',
    body: '섹터 관계망은 지금 일시적으로 제공되지 않아요. 종목을 선택하면 관계망을 볼 수 있어요.',
    retry: true,
    tone: 'error',
  },
};

export default function GraphStatePanel({ variant, symbol, onRetry }: GraphStatePanelProps) {
  const c = COPY[variant];
  const showSymbol = (variant === 'empty-neighbors' || variant === 'load-error') && symbol;

  return (
    <div
      data-testid={c.testId}
      className="flex flex-col items-center justify-center h-[560px] bg-gray-50 dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 px-4 gap-4 text-center"
    >
      <div
        aria-hidden
        className={[
          'flex items-center justify-center w-14 h-14 rounded-full',
          c.tone === 'error'
            ? 'bg-red-50 dark:bg-red-900/20 text-red-400 dark:text-red-300'
            : 'bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-500',
        ].join(' ')}
      >
        <span className="text-2xl leading-none">{c.tone === 'error' ? '!' : '·'}</span>
      </div>

      <div className="space-y-1.5 max-w-md">
        <p className="text-base font-medium text-gray-800 dark:text-gray-200">
          {showSymbol ? `${symbol} — ${c.title}` : c.title}
        </p>
        <p className="text-sm text-gray-500 dark:text-gray-400">{c.body}</p>
      </div>

      {c.retry && onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-1 px-4 py-2 rounded-lg text-sm font-medium border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 hover:border-blue-400 hover:bg-blue-50 dark:hover:border-blue-500 dark:hover:bg-blue-900/20 transition-colors"
        >
          다시 시도
        </button>
      )}
    </div>
  );
}

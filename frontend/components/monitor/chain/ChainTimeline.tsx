// 관계망 이벤트 타임라인 (EVT-CHAIN-1). 시드 배너 → 이웃 어닝 행 → 접힘 카운트 → 시드 행.
// 이웃 0이면 섹션 자체 비표시. 부호 중립(§6): 방향/센티먼트 색·판정 없음.
import { badgeClass, KIND_BADGE_CLASS, KIND_LABEL } from '@/components/monitor/calendar/eventColors';
import { TrustBadge } from '@/components/monitor/calendar/TrustBadge';
import { fmtDateShort, fmtDday, formatDetail } from '@/lib/monitor/calendarFormat';
import type { ChainEventItem, ChainFeed, ChainSeedNext } from '@/types/chainFeed';

import { RelationBadge } from './RelationBadge';

function ChainRow({ item }: { item: ChainEventItem }) {
  return (
    <div
      data-testid="chain-row"
      className="grid grid-cols-[1fr_auto] items-center gap-2 border-b border-dashed border-gray-100 py-2 last:border-b-0 dark:border-gray-800 sm:grid-cols-[190px_1fr_140px]"
    >
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="font-bold">{item.symbol}</span>
        {item.relation && (
          <RelationBadge
            relationType={item.relation.type}
            truthScore={item.relation.truth_score}
            role={item.relation.role}
          />
        )}
      </div>
      <div className="text-xs text-gray-600 dark:text-gray-300">
        <span className={badgeClass(KIND_BADGE_CLASS.earnings)}>{KIND_LABEL.earnings}</span>{' '}
        {formatDetail(item)}
      </div>
      <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
        <TrustBadge trust={item.date_trust} observedCount={item.date_observed_count} />
        <span>
          <span className="font-mono font-semibold text-blue-600 dark:text-blue-400">
            {fmtDday(item.d_day)}
          </span>{' '}
          {fmtDateShort(item.event_date_et)}
        </span>
      </div>
    </div>
  );
}

function SeedRow({ seed, next }: { seed: string; next: ChainSeedNext }) {
  return (
    <div
      data-testid="chain-seed-row"
      className="mt-1 grid grid-cols-[1fr_auto] items-center gap-2 rounded-md bg-slate-100 px-2 py-2 dark:bg-slate-800/60 sm:grid-cols-[190px_1fr_140px]"
    >
      <div className="flex items-center gap-1.5">
        <span className="font-bold">{seed}</span>
        <span className={badgeClass(KIND_BADGE_CLASS[next.kind])}>{KIND_LABEL[next.kind]}</span>
        <span className="text-xs text-gray-400">시드</span>
      </div>
      <div className="hidden sm:block" />
      <div className="text-xs text-gray-500 dark:text-gray-400">
        <span className="font-mono font-semibold text-blue-600 dark:text-blue-400">
          {fmtDday(next.d_day)}
        </span>{' '}
        {fmtDateShort(next.event_date_et)}
      </div>
    </div>
  );
}

interface Props {
  feed: ChainFeed;
}

export function ChainTimeline({ feed }: Props) {
  // 이웃 0(엣지 미달) → 타임라인 섹션 자체 비표시.
  if (feed.neighbors.length === 0) return null;

  const { seed, seed_next_event: next, seed_earnings_event: seedEarn, items, after_count } = feed;

  return (
    <div data-testid="chain-timeline">
      {/* 시드 배너 */}
      <div
        data-testid="chain-banner"
        className="my-3 flex flex-wrap items-center gap-2 rounded-lg border border-gray-200 bg-slate-50 px-3 py-2 text-sm dark:border-gray-800 dark:bg-slate-900/50"
      >
        <span className="font-bold text-slate-800 dark:text-slate-100">{seed}</span>
        {next ? (
          <>
            <span className="text-gray-500 dark:text-gray-400">다음 이벤트: {KIND_LABEL[next.kind]}</span>
            <span className="font-mono font-bold text-blue-600 dark:text-blue-400">{fmtDday(next.d_day)}</span>
            <span className="text-gray-500 dark:text-gray-400">{fmtDateShort(next.event_date_et)}</span>
          </>
        ) : (
          <span className="text-gray-500 dark:text-gray-400">향후 90일 관계망 어닝</span>
        )}
        <span className="ml-auto text-xs text-gray-400">그 사이 관계망(1-hop 이웃) 어닝 ↓</span>
      </div>

      <div className="mb-1 flex items-baseline gap-2 text-xs text-gray-400">
        <b className="text-sm text-gray-800 dark:text-gray-200">관계망 이벤트</b>
        <span>· RelationConfidence 이웃 · truth ≥ 0.85 · confirmed · top-10 · 어닝만 · 부호 중립</span>
      </div>

      {items.map((it) => (
        <ChainRow key={`${it.symbol}-${it.event_date_et}`} item={it} />
      ))}

      {after_count > 0 && (
        <div
          data-testid="chain-after-count"
          className="border-b border-dashed border-gray-100 py-1 text-center text-[11px] text-gray-400 dark:border-gray-800"
        >
          이후 {after_count}건 더 ▸
        </div>
      )}

      {seedEarn && <SeedRow seed={seed} next={seedEarn} />}
    </div>
  );
}

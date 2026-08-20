'use client';

import { useMindmapCard } from '@/hooks/useMindmap';
import { acquiredRoleLabel, directionLabel, relationTypeLabel } from './mindmapConfig';
import type { MindmapConnection, MindmapGroup } from '@/types/chainsight';

/**
 * 마인드맵 카드 상세 패널 (CS-P5-FE-CARD B4).
 *
 * "확인된 연결"(게이트 통과) vs "같은 그룹"(CO_MENTIONED, 관계 아님)을 시각적으로 분리.
 * ACQUIRED 방향 구조는 빈 배열이어도 항상 렌더(구조는 존재, 데이터 착지 시 자동 표시).
 * 테마 슬롯은 placeholder만(VOCAB-TAU 선행 대기 — 로직·페치 금지).
 */
export default function MindmapCardDetail({
  symbol,
  onSelectOther,
  onClose,
}: {
  symbol: string;
  onSelectOther: (symbol: string) => void;
  onClose: () => void;
}) {
  const { data, isLoading, isError, refetch } = useMindmapCard(symbol);

  return (
    <div
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4"
      data-testid="mindmap-card-detail"
    >
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="min-w-0">
          <span className="font-semibold text-base">{symbol}</span>
          {data?.name && (
            <span className="block text-xs text-gray-500 truncate max-w-[220px]">{data.name}</span>
          )}
        </div>
        <button
          onClick={onClose}
          className="shrink-0 p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 text-sm"
          aria-label="상세 패널 닫기"
        >
          ✕
        </button>
      </div>

      {isLoading && (
        <div className="flex flex-col items-center justify-center h-40 gap-2">
          <div className="w-5 h-5 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin" />
          <p className="text-xs text-gray-400">카드를 불러오는 중...</p>
        </div>
      )}

      {isError && (
        <div className="py-6 text-center">
          <p className="text-sm text-red-500 mb-2">카드를 불러올 수 없습니다</p>
          <button
            onClick={() => refetch()}
            className="text-xs text-blue-600 dark:text-blue-400 underline"
          >
            다시 시도
          </button>
        </div>
      )}

      {data && (
        <div className="flex flex-col gap-4">
          {/* 확인된 연결 */}
          <section>
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-2">
              확인된 연결 <span className="text-[11px] text-gray-400 tabular-nums">{data.connection_count}</span>
            </h3>
            {data.connections.length === 0 ? (
              <p className="text-xs text-gray-400">게이트를 통과한 연결이 없습니다</p>
            ) : (
              <ul className="flex flex-col gap-1.5">
                {data.connections.map((c) => (
                  <ConnectionRow key={`${c.other}-${c.relation_type}`} conn={c} onSelectOther={onSelectOther} />
                ))}
              </ul>
            )}
          </section>

          {/* ACQUIRED 방향 구조 — 빈 배열이어도 구조 렌더(D-ACQ-DIR) */}
          <section>
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-2">인수·피인수</h3>
            {data.acquired.length === 0 ? (
              <p className="text-xs text-gray-400">인수 관계 없음</p>
            ) : (
              <ul className="flex flex-col gap-1.5">
                {data.acquired.map((a) => (
                  <li key={`${a.other}-${a.role}`}>
                    <button
                      onClick={() => onSelectOther(a.other)}
                      className="w-full flex items-center justify-between gap-2 px-2 py-1.5 text-left text-xs rounded border border-gray-200 dark:border-gray-700 hover:border-blue-400 transition"
                    >
                      <span>
                        <span className="font-medium">{a.other}</span>
                        <span className="text-gray-500 ml-1">{a.other_name}</span>
                      </span>
                      <span className="text-gray-400 shrink-0">{acquiredRoleLabel(a.role)}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>

          {/* 같은 그룹(CO_MENTIONED) — 연결과 시각적으로 명확히 구분 */}
          <section className="rounded-lg border border-dashed border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-900/40 p-3">
            <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 mb-1">
              같은 그룹{' '}
              <span className="text-[11px] text-gray-400 tabular-nums">
                {data.group_capped ? `상위 20 / 전체 ${data.group_total}` : data.group_total}
              </span>
            </h3>
            <p className="text-[11px] text-gray-400 mb-2">관계 아님 · 동시 언급</p>
            {data.groups.length === 0 ? (
              <p className="text-xs text-gray-400">같은 그룹으로 언급된 종목이 없습니다</p>
            ) : (
              <ul className="flex flex-wrap gap-1.5">
                {data.groups.map((g) => (
                  <GroupChip key={g.other} group={g} onSelectOther={onSelectOther} />
                ))}
              </ul>
            )}
          </section>

          {/* 테마 슬롯 — placeholder만(로직·데이터 페치 금지, VOCAB-TAU 대기) */}
          <section className="rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-100 dark:bg-gray-900/60 p-3 text-center">
            <p className="text-xs text-gray-400">테마 (준비 중)</p>
          </section>
        </div>
      )}
    </div>
  );
}

function ConnectionRow({
  conn,
  onSelectOther,
}: {
  conn: MindmapConnection;
  onSelectOther: (symbol: string) => void;
}) {
  return (
    <li>
      <button
        onClick={() => onSelectOther(conn.other)}
        className="w-full text-left p-2 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-blue-400 hover:shadow-sm transition"
      >
        <div className="flex items-center justify-between gap-2 mb-1">
          <span className="min-w-0 truncate">
            <span className="font-medium text-sm">{conn.other}</span>
            <span className="text-[11px] text-gray-500 ml-1.5 truncate">{conn.other_name}</span>
          </span>
          <span className="shrink-0 px-1.5 py-0.5 text-[10px] font-medium rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
            {relationTypeLabel(conn.relation_type)}
          </span>
        </div>
        <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px] text-gray-400">
          <span>{directionLabel(conn.direction, conn.other)}</span>
          {conn.sync_strength != null && <span>동조 {conn.sync_strength.toFixed(2)}</span>}
          {conn.contract_date && <span>계약일 {conn.contract_date}</span>}
          <span>신뢰도 {Math.round(conn.truth_score)}</span>
          {conn.status && <span>{conn.status}</span>}
        </div>
      </button>
    </li>
  );
}

function GroupChip({
  group,
  onSelectOther,
}: {
  group: MindmapGroup;
  onSelectOther: (symbol: string) => void;
}) {
  return (
    <li>
      <button
        onClick={() => onSelectOther(group.other)}
        className="px-2 py-1 text-[11px] rounded-full border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 hover:border-blue-400 transition"
        title={group.other_name}
      >
        {group.other} <span className="text-gray-400">· {group.co_mention_count}</span>
      </button>
    </li>
  );
}

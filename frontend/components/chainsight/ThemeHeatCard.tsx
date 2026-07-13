'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Info } from 'lucide-react';
import { fetchThemeHeatCard } from '@/services/chainsightService';
import type { ThemeHeatCard as ThemeHeatCardType } from '@/types/chainsight';
import { bandColorClass, directionGlyph, zModeBasisText, componentStatusText } from './themeHeatCopy';

/** 견인(driver) 칩 — 결정29 보류 분기 / 결정27 방향. */
function DriverChip({ driver }: { driver: ThemeHeatCardType['driver'] }) {
  if (!driver) {
    return <span className="text-xs text-gray-400">견인 · 데이터 대기</span>;
  }
  if (driver.held) {
    return (
      <span
        className="inline-flex items-center gap-1 text-xs text-gray-400 cursor-help"
        title={driver.note ?? '계산 방식 개선일 — 하루 변화 해석은 다음 정상일부터.'}
        data-testid="driver-held"
      >
        견인 · 산출 보류 <Info size={12} />
      </span>
    );
  }
  const g = directionGlyph(driver.direction);
  return (
    <span className="inline-flex items-center gap-1 text-xs text-gray-700 dark:text-gray-200" data-testid="driver-active">
      <span className="font-semibold">{g.icon} {g.verb}</span>
      <span className="text-gray-500">
        {driver.label_surface} {driver.contribution_pct?.toFixed(0)}%
      </span>
    </span>
  );
}

export default function ThemeHeatCard({ theme, rank, total }: { theme: string; rank?: number; total?: number }) {
  const [expanded, setExpanded] = useState(false);
  const { data: card, isLoading, isError } = useQuery({
    queryKey: ['theme-heat-card', theme],
    queryFn: () => fetchThemeHeatCard(theme),
  });

  if (isLoading) return <div className="rounded-xl border border-gray-200 dark:border-gray-700 p-4 text-sm text-gray-400">불러오는 중…</div>;
  if (isError || !card) return <div className="rounded-xl border border-red-200 p-4 text-sm text-red-500">카드를 불러오지 못했습니다.</div>;

  const isComputed = card.status === 'computed' && card.score !== null;
  const deltaSign = (card.delta_1d ?? 0) > 0 ? '+' : '';

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 flex flex-col gap-3">
      {/* 헤더: 테마명 + 랭킹 */}
      <div className="flex items-center justify-between">
        <span className="font-semibold text-sm text-gray-800 dark:text-gray-100">{card.theme}</span>
        {rank && total && <span className="text-xs text-gray-400">{rank}/{total}</span>}
      </div>

      {card.blocked && (
        <div className="text-xs text-amber-600 dark:text-amber-400" data-testid="blocked-banner">
          ⚠ 모집단 갱신 지연({card.blocked.days_stale ?? '?'}일) — 값+사유 동봉
        </div>
      )}

      {isComputed ? (
        <>
          {/* 온도 (대형) + delta 보조 */}
          <div className="flex items-end gap-2">
            <span className={`text-4xl font-bold ${bandColorClass(card.band)}`} data-testid="heat-score">{card.score}</span>
            <span className="text-xs text-gray-500 mb-1">{card.band_display}</span>
            {card.delta_1d !== null && (
              <span className="text-xs text-gray-400 mb-1" data-testid="heat-delta">{deltaSign}{card.delta_1d} (1일)</span>
            )}
          </div>
          {/* 견인 칩 + 신뢰 칩 */}
          <div className="flex items-center gap-3 flex-wrap">
            <DriverChip driver={card.driver} />
            {card.confidence && (
              <span className="text-xs text-gray-500" data-testid="confidence-chip">
                신뢰 {card.confidence.present}/{card.confidence.total}
              </span>
            )}
          </div>
          {/* 펼침 토글 */}
          <button
            onClick={() => setExpanded((v) => !v)}
            className="text-xs text-blue-500 self-start"
            data-testid="expand-toggle"
          >
            {expanded ? '접기' : '성분 근거 펼치기'}
          </button>
          {/* R3 의미 레이어 */}
          {expanded && (
            <div className="flex flex-col gap-1 border-t border-gray-100 dark:border-gray-700 pt-2" data-testid="meaning-layer">
              {card.components.map((c) => (
                <div key={c.id} className="flex items-center justify-between text-xs">
                  <span className="text-gray-700 dark:text-gray-200">
                    {c.label_surface}
                    <span className="text-gray-400"> · {c.label_technical}</span>
                  </span>
                  <span className="text-gray-500 text-right">
                    {c.status === 'computed' ? (
                      <>z {c.z?.toFixed(2)} · <span className="text-gray-400">{zModeBasisText(c.z_mode)}</span></>
                    ) : (
                      <span className="text-gray-400">{componentStatusText(c.status)}</span>
                    )}
                  </span>
                </div>
              ))}
            </div>
          )}
        </>
      ) : (
        /* accumulating: 진행 표시 */
        <div className="text-sm text-gray-500" data-testid="accumulating">
          누적 중 · {card.days ?? 0}/{card.days_required ?? 26}일
          {card.eta_days != null && <span className="text-gray-400"> · D-{card.eta_days}</span>}
        </div>
      )}
    </div>
  );
}

'use client';

import type { ReactNode } from 'react';
import Link from 'next/link';
import { ArrowRight, Layers } from 'lucide-react';
import { DIRECTION_BADGE } from '@/components/common/colorSemantics';
import { DetailSheetShell } from './DetailSheetShell';
import { PERSPECTIVE_LABEL, presentPerspectives } from './recommendation';
import { validSector } from './scannerFilters';
import { buildTechnicalDetail } from './technicalLabels';
import { SIGNAL_CATEGORY_LABELS } from '@/types/eod';
import type { Recommendation, SignalCategory, SignalStock } from '@/types/eod';

interface RecommendationDetailSheetProps {
  rec: Recommendation;
  onClose: () => void;
  /** 카드 JSON 조인 행(체급·섹터·기술). 조인 실패 = undefined → 체급·기술 섹션 보류. */
  stock?: SignalStock;
  /** 스캐너 합류 축. 없으면 헤더 축 배지 생략. */
  axisCategories?: SignalCategory[];
}

// 체급($) 압축 표기 — 시총·거래대금. (StockRow의 표기 규칙과 동일)
function formatCompactUSD(value: number | null | undefined): string | null {
  if (value == null || value <= 0) return null;
  if (value >= 1_000_000_000_000) return `$${(value / 1_000_000_000_000).toFixed(1)}T`;
  if (value >= 1_000_000_000) return `$${(value / 1_000_000_000).toFixed(1)}B`;
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(0)}M`;
  return `$${(value / 1_000).toFixed(0)}K`;
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="px-5 py-3 border-b border-gray-100 dark:border-gray-700">
      <h3 className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">
        {title}
      </h3>
      {children}
    </section>
  );
}

/**
 * 추천 드로어 (DASH-RECO S4). 본문 3섹션 = 한 줄 요약 · 세 관점 · 체급·기술.
 * 정칙 ⑴: 값이 없는 섹션은 **섹션 제목째 생략**한다("정보 없음" 표기 금지).
 * 체급·기술은 추천 payload에 없으므로 카드 JSON 조인값을 쓰고, 조인 실패면 그 섹션만 보류.
 */
export function RecommendationDetailSheet({
  rec,
  onClose,
  stock,
  axisCategories = [],
}: RecommendationDetailSheetProps) {
  const isBuy = rec.composite_score >= 0;
  const directionVerb = isBuy ? '매수' : '매도·회피';
  const badgeClass = isBuy ? DIRECTION_BADGE.buy : DIRECTION_BADGE.sell;

  const summary = rec.thesis && rec.thesis.trim() ? rec.thesis : null;
  const perspectives = presentPerspectives(rec);

  const sector = stock && validSector(stock.sector) ? stock.sector : null;
  const marketCap = formatCompactUSD(stock?.market_cap);
  const dollarVolume = formatCompactUSD(stock?.dollar_volume);
  const technical = buildTechnicalDetail(stock?.technical);
  const sizeParts = [
    sector && { label: '섹터', value: sector },
    marketCap && { label: '시총', value: marketCap },
    dollarVolume && { label: '거래대금', value: dollarVolume },
  ].filter((p): p is { label: string; value: string } => !!p);
  const hasSizeTech = sizeParts.length > 0 || technical.length > 0;

  // 하단 커버리지 = 이 드로어가 **실제로 보여준** 축만(스캐너 문구 재사용 금지 — S1 prop 사유).
  const shownAxes: string[] = [];
  const hiddenAxes: string[] = [];
  const kinds = new Set(perspectives.map((p) => p.kind));
  (['technical', 'fundamental', 'news_context'] as const).forEach((k) =>
    (kinds.has(k) ? shownAxes : hiddenAxes).push(PERSPECTIVE_LABEL[k]),
  );
  if (hasSizeTech) shownAxes.push('체급·기술 지표');
  if (axisCategories.length > 0) shownAxes.push('스캐너 합류');
  hiddenAxes.push('관계(체인사이트)');

  return (
    <DetailSheetShell
      onClose={onClose}
      header={
        <>
          <div className="flex items-baseline gap-2 mb-1">
            <h2 className="text-lg font-bold text-gray-900 dark:text-white leading-tight">{rec.ticker}</h2>
            <span className="min-w-0 truncate text-xs text-gray-500 dark:text-gray-400">{rec.company_name}</span>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className={`rounded-full px-2 py-0.5 text-xs font-bold ${badgeClass}`}>{directionVerb}</span>
            <span className="rounded bg-gray-100 px-1.5 py-0.5 text-xs font-mono text-gray-600 dark:bg-gray-700 dark:text-gray-300">
              {rec.signal_tag}
            </span>
            {axisCategories.length > 0 && (
              <span
                className="inline-flex items-center gap-0.5 rounded-full border border-indigo-200 bg-indigo-50 px-1.5 py-0.5 text-[10px] font-medium text-indigo-700 dark:border-indigo-800 dark:bg-indigo-900/20 dark:text-indigo-300"
                title={axisCategories.map((c) => SIGNAL_CATEGORY_LABELS[c]).join(' · ')}
              >
                <Layers className="w-2.5 h-2.5" />
                {axisCategories.length}축
              </span>
            )}
          </div>
        </>
      }
      coverage={
        <>
          {shownAxes.length > 0 && (
            <>
              이 화면 축: <span className="font-medium">{shownAxes.join(' · ')}</span>
              {' · '}
            </>
          )}
          <span className="text-gray-400 dark:text-gray-500">미커버: {hiddenAxes.join(' · ')}</span>
        </>
      }
    >
      <div className="flex-1 overflow-y-auto">
        {summary && (
          <Section title="한 줄 요약">
            <p className="text-sm leading-relaxed text-gray-800 dark:text-gray-100">{summary}</p>
          </Section>
        )}

        {perspectives.length > 0 && (
          <Section title="세 관점">
            <dl className="space-y-2">
              {perspectives.map((p) => (
                <div key={p.kind}>
                  <dt className="text-xs font-semibold text-gray-600 dark:text-gray-300">{PERSPECTIVE_LABEL[p.kind]}</dt>
                  <dd className="text-xs leading-relaxed text-gray-600 dark:text-gray-400">{p.text}</dd>
                </div>
              ))}
            </dl>
          </Section>
        )}

        {hasSizeTech && (
          <Section title="체급·기술">
            {sizeParts.length > 0 && (
              <dl className="flex flex-wrap gap-x-4 gap-y-1 text-xs">
                {sizeParts.map((p) => (
                  <div key={p.label} className="flex gap-1">
                    <dt className="text-gray-400 dark:text-gray-500">{p.label}</dt>
                    <dd className="font-medium text-gray-700 dark:text-gray-200">{p.value}</dd>
                  </div>
                ))}
              </dl>
            )}
            {technical.length > 0 && (
              <p className="mt-1.5 text-xs text-gray-600 dark:text-gray-300">{technical.join(' · ')}</p>
            )}
          </Section>
        )}

        <div className="px-5 py-3">
          <Link
            href={`/stocks/${rec.ticker}?tab=chain-sight`}
            className="inline-flex items-center gap-0.5 text-xs font-medium text-blue-600 hover:underline dark:text-blue-400"
          >
            체인사이트에서 관계 보기
            <ArrowRight className="w-3 h-3" />
          </Link>
        </div>
      </div>
    </DetailSheetShell>
  );
}

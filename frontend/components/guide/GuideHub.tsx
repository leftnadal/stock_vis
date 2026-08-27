'use client';

/**
 * GuideHub — `/guide` 허브 (D-GUIDE-TRACK).
 *
 * 상단 = 서비스 플로우 5단계 지도, 하단 = 도메인 카드.
 * 목록은 GUIDE_SCREENS에서 자동 생성한다(하드코딩 금지 — 새 화면 등재 시 자동 반영).
 */

import Link from 'next/link';

import { FLOW_STAGE_LABELS, GUIDE_SCREENS, type FlowStage, type GuideScreen } from '@/lib/guide';

const STAGES: FlowStage[] = [1, 2, 3, 4, 5];

function screensForStage(stage: FlowStage): GuideScreen[] {
  return GUIDE_SCREENS.filter((s) => s.flowStage === stage);
}

export default function GuideHub() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">사용 가이드</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          이 서비스는 <strong>시장 흐름을 파악하고 → 파급을 발견하고 → 관심을 추적하고 → 1차로
          검증한 뒤 → 포트폴리오에 반영하는</strong> 한 바퀴로 설계돼 있습니다. 각 화면은 그
          바퀴의 한 칸입니다.
        </p>
      </header>

      {/* 플로우 지도 */}
      <section className="mb-10" data-testid="guide-flow-map">
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-500">
          서비스 플로우
        </h2>
        <ol className="grid grid-cols-1 gap-2 sm:grid-cols-5">
          {STAGES.map((stage) => {
            const screens = screensForStage(stage);
            const covered = screens.length > 0;
            return (
              <li
                key={stage}
                data-testid={`guide-stage-${stage}`}
                className={`rounded-xl border p-3 ${
                  covered
                    ? 'border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-900/20'
                    : 'border-dashed border-gray-300 bg-transparent dark:border-gray-700'
                }`}
              >
                <p className="text-xs font-bold text-blue-600 dark:text-blue-400">{stage}</p>
                <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  {FLOW_STAGE_LABELS[stage]}
                </p>
                {covered ? (
                  <ul className="mt-1 space-y-0.5">
                    {screens.map((s) => (
                      <li key={s.id}>
                        <Link
                          href={s.route}
                          className="text-xs text-blue-700 hover:underline dark:text-blue-300"
                        >
                          {s.title.split(' — ')[0]}
                        </Link>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-1 text-xs text-gray-400">가이드 준비 중</p>
                )}
              </li>
            );
          })}
        </ol>
      </section>

      {/* 화면 카드 */}
      <section>
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-500">
          화면별 가이드
        </h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {GUIDE_SCREENS.map((s) => (
            <article
              key={s.id}
              data-testid={`guide-card-${s.id}`}
              className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
            >
              <p className="text-xs font-medium text-blue-600 dark:text-blue-400">
                {s.flowStage}. {FLOW_STAGE_LABELS[s.flowStage]}
              </p>
              <h3 className="mt-0.5 text-base font-semibold text-gray-900 dark:text-gray-100">
                {s.title}
              </h3>
              <p className="mt-2 text-sm text-gray-700 dark:text-gray-300">{s.coreQuestion}</p>
              <ul className="mt-2 list-disc space-y-0.5 pl-5 text-xs text-gray-500 dark:text-gray-400">
                {s.learnings.map((l) => (
                  <li key={l}>{l}</li>
                ))}
              </ul>
              <div className="mt-3 flex items-center justify-between">
                <Link
                  href={s.route}
                  className="text-sm font-medium text-blue-600 hover:underline dark:text-blue-400"
                >
                  화면 열기 →
                </Link>
                {s.reviewStatus === 'draft' && (
                  <span
                    data-testid={`guide-draft-${s.id}`}
                    className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-medium text-amber-800 dark:bg-amber-900/40 dark:text-amber-200"
                  >
                    초안
                  </span>
                )}
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

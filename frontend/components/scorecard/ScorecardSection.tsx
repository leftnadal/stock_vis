'use client'

// D1-SCOREBOARD 3a — 성적판 섹션 (advisory 페이지 얇게 장착 · 자립 승격 이사 전제).
// 훅 useAnalystScorecard로 전역 read 후 ScoreStrip + ScoreboardBoard 렌더.
// 로딩/에러/빈(심볼 0) 상태 명시. 접힘 가능(선택적 노출).
import { useState } from 'react'
import { AlertCircle, ChevronDown, ChevronUp, Loader2 } from 'lucide-react'

import { useAnalystScorecard } from '@/hooks/useScorecard'
import { ScoreStrip } from './ScoreStrip'
import { ScoreboardBoard } from './ScoreboardBoard'

const HORIZON = 21

export function ScorecardSection() {
  const [collapsed, setCollapsed] = useState(false)
  const { data, isLoading, isError } = useAnalystScorecard(HORIZON)

  return (
    <section data-testid="scorecard-section" className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300">애널리스트 성적판</h2>
          <p className="text-[11px] text-gray-400">
            애널리스트 방향·목표가 예측의 사후 채점입니다. 만기(h={HORIZON}거래일) 도래분만 채점되며 예측이 아닙니다.
          </p>
        </div>
        <button
          type="button"
          data-testid="scorecard-collapse-toggle"
          onClick={() => setCollapsed((v) => !v)}
          className="inline-flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
        >
          {collapsed ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />}
          {collapsed ? '펼치기' : '접기'}
        </button>
      </div>

      {!collapsed && (
        <>
          {isLoading && (
            <div
              data-testid="scorecard-loading"
              className="flex items-center gap-2 rounded-xl border border-gray-200 bg-white p-5 text-sm text-gray-500 dark:border-gray-800 dark:bg-gray-900"
            >
              <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
              성적판 계산 중...
            </div>
          )}

          {!isLoading && isError && (
            <div
              role="alert"
              data-testid="scorecard-error"
              className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800 dark:border-red-900 dark:bg-red-900/20 dark:text-red-300"
            >
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              성적판을 불러오지 못했습니다.
            </div>
          )}

          {!isLoading && !isError && data && (
            data.symbols.length === 0 ? (
              <div
                data-testid="scorecard-empty"
                className="rounded-xl border border-dashed border-gray-300 bg-gray-50 p-6 text-center text-sm text-gray-500 dark:border-gray-700 dark:bg-gray-800/40 dark:text-gray-400"
              >
                아직 채점할 애널리스트 신호가 없어요.
              </div>
            ) : (
              <div className="flex flex-col gap-4">
                <ScoreStrip board={data.board} />
                <ScoreboardBoard scorecard={data} />
              </div>
            )
          )}
        </>
      )}
    </section>
  )
}

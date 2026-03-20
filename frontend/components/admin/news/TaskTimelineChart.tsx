'use client';

import { useState } from 'react';
import { format, parseISO } from 'date-fns';
import { ko } from 'date-fns/locale';
import { useTaskTimeline } from '@/hooks/useNewsPipeline';
import type { TimelineEntry } from '@/types/newsPipeline';

const STATUS_COLOR: Record<TimelineEntry['status'], string> = {
  ok: '#22C55E',
  warning: '#EAB308',
  error: '#EF4444',
};

const STATUS_BG: Record<TimelineEntry['status'], string> = {
  ok: 'bg-green-500',
  warning: 'bg-yellow-500',
  error: 'bg-red-500',
};

interface TooltipState {
  entry: TimelineEntry;
  x: number;
  y: number;
}

interface TaskTimelineChartProps {
  hours?: number;
  enabled?: boolean;
}

function formatDuration(sec: number): string {
  if (sec < 60) return `${sec.toFixed(0)}s`;
  return `${(sec / 60).toFixed(1)}m`;
}

function formatTime(iso: string): string {
  try {
    return format(parseISO(iso), 'HH:mm', { locale: ko });
  } catch {
    return iso;
  }
}

export function TaskTimelineChart({ hours = 24, enabled = true }: TaskTimelineChartProps) {
  const { data, isLoading, error } = useTaskTimeline(hours, enabled);
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);

  if (isLoading) {
    return (
      <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
        <h3 className="font-semibold text-gray-200 mb-4">태스크 타임라인 ({hours}h)</h3>
        <div className="h-48 bg-gray-700 rounded-lg animate-pulse" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
        <h3 className="font-semibold text-gray-200 mb-2">태스크 타임라인 ({hours}h)</h3>
        <p className="text-sm text-red-400">데이터 로드 실패</p>
      </div>
    );
  }

  if (data.timeline.length === 0) {
    return (
      <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
        <h3 className="font-semibold text-gray-200 mb-2">태스크 타임라인 ({hours}h)</h3>
        <p className="text-sm text-gray-500">최근 {hours}시간 내 실행 기록 없음</p>
      </div>
    );
  }

  // 시간 범위 계산
  const now = Date.now();
  const windowStart = now - hours * 60 * 60 * 1000;

  // 고유 task_name 목록 (등장 순 정렬)
  const taskNames = Array.from(
    new Set(data.timeline.map((e) => e.task_name))
  );

  // entry를 시간 비율로 변환 (0~100%)
  function toPercent(iso: string): number {
    const t = new Date(iso).getTime();
    return Math.max(0, Math.min(100, ((t - windowStart) / (hours * 60 * 60 * 1000)) * 100));
  }

  // X축 눈금: hours에 따라 간격 결정
  const tickCount = hours <= 12 ? hours : Math.ceil(hours / 3);
  const tickInterval = hours / tickCount;
  const xTicks: { label: string; percent: number }[] = Array.from({ length: tickCount + 1 }, (_, i) => {
    const t = windowStart + i * tickInterval * 60 * 60 * 1000;
    return {
      label: format(new Date(t), 'HH:mm'),
      percent: (i / tickCount) * 100,
    };
  });

  return (
    <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-gray-200">태스크 타임라인 ({hours}h)</h3>
        <div className="flex items-center gap-3 text-xs">
          {(['ok', 'warning', 'error'] as const).map((s) => (
            <span key={s} className="flex items-center gap-1 text-gray-400">
              <span
                className="inline-block w-2.5 h-2.5 rounded-sm"
                style={{ backgroundColor: STATUS_COLOR[s] }}
              />
              {s === 'ok' ? '정상' : s === 'warning' ? '주의' : '오류'}
            </span>
          ))}
        </div>
      </div>

      <div className="relative" onMouseLeave={() => setTooltip(null)}>
        {/* Gantt 행들 */}
        <div className="space-y-1.5">
          {taskNames.map((taskName) => {
            const entries = data.timeline.filter((e) => e.task_name === taskName);
            return (
              <div key={taskName} className="flex items-center gap-2">
                {/* 태스크 이름 레이블 */}
                <div className="w-40 flex-shrink-0 text-right">
                  <span className="text-xs text-gray-400 truncate block" title={taskName}>
                    {taskName}
                  </span>
                </div>
                {/* 간트 막대 영역 */}
                <div className="flex-1 relative h-6 bg-gray-900 rounded overflow-hidden">
                  {entries.map((entry, idx) => {
                    const left = toPercent(entry.start);
                    const right = toPercent(entry.end);
                    const width = Math.max(right - left, 0.3); // 최소 너비 보장
                    return (
                      <div
                        key={`${entry.start}-${idx}`}
                        className="absolute top-1 h-4 rounded-sm cursor-pointer opacity-90 hover:opacity-100 transition-opacity"
                        style={{
                          left: `${left}%`,
                          width: `${width}%`,
                          backgroundColor: STATUS_COLOR[entry.status],
                        }}
                        onMouseEnter={(e) => {
                          const rect = (e.currentTarget as HTMLElement)
                            .closest('.relative')
                            ?.getBoundingClientRect();
                          setTooltip({
                            entry,
                            x: e.clientX - (rect?.left ?? 0),
                            y: e.clientY - (rect?.top ?? 0),
                          });
                        }}
                      />
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>

        {/* X축 눈금 */}
        <div className="flex mt-2 pl-[10.5rem]">
          <div className="flex-1 relative h-4">
            {xTicks.map((tick) => (
              <span
                key={tick.percent}
                className="absolute text-xs text-gray-600 -translate-x-1/2"
                style={{ left: `${tick.percent}%` }}
              >
                {tick.label}
              </span>
            ))}
          </div>
        </div>

        {/* 툴팁 */}
        {tooltip && (
          <div
            className="absolute z-10 bg-gray-900 border border-gray-700 rounded-lg p-3 text-xs pointer-events-none shadow-lg"
            style={{
              left: `${Math.min(tooltip.x + 8, 400)}px`,
              top: `${tooltip.y - 10}px`,
              minWidth: '180px',
            }}
          >
            <p className="font-semibold text-gray-200 mb-1 truncate">{tooltip.entry.task_name}</p>
            <p className="text-gray-400">
              제공자: <span className="text-gray-300">{tooltip.entry.provider}</span>
            </p>
            <p className="text-gray-400">
              시작: <span className="text-gray-300">{formatTime(tooltip.entry.start)}</span>
            </p>
            <p className="text-gray-400">
              종료: <span className="text-gray-300">{formatTime(tooltip.entry.end)}</span>
            </p>
            <p className="text-gray-400">
              소요: <span className="text-gray-300">{formatDuration(tooltip.entry.duration_sec)}</span>
            </p>
            <p className="text-gray-400">
              신규: <span className="text-gray-300">{tooltip.entry.articles_new}건</span>
            </p>
            {tooltip.entry.errors > 0 && (
              <p className="text-red-400">
                에러: {tooltip.entry.errors}건
              </p>
            )}
            <span
              className="inline-block mt-1 px-1.5 py-0.5 rounded text-xs font-medium"
              style={{ color: STATUS_COLOR[tooltip.entry.status], backgroundColor: `${STATUS_COLOR[tooltip.entry.status]}20` }}
            >
              {tooltip.entry.status.toUpperCase()}
            </span>
          </div>
        )}
      </div>

      {/* 범례 — 총 건수 요약 */}
      <div className="mt-3 flex gap-4 text-xs text-gray-500 border-t border-gray-700 pt-3">
        <span>총 실행: {data.timeline.length}건</span>
        <span className="text-green-400">
          정상: {data.timeline.filter((e) => e.status === 'ok').length}
        </span>
        <span className="text-yellow-400">
          주의: {data.timeline.filter((e) => e.status === 'warning').length}
        </span>
        <span className="text-red-400">
          오류: {data.timeline.filter((e) => e.status === 'error').length}
        </span>
      </div>
    </div>
  );
}

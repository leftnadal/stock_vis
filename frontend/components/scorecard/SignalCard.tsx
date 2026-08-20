// D1-SCOREBOARD 3b — 신호 카드 (증거 바 + 판정 문장).
// 증거 바 = 포착가·실현가·목표가 눈금(빗나감은 실현가가 목표 반대편에 위치해 자연히
// 드러남). 목표가 부재 시 바 숨김·문장만(강등 분기). 어휘는 BE 판정 정의와 일치.
import type { ScorecardSignal } from '@/types/scorecard'
import { verdictSentence } from '@/lib/scorecard/present'

interface SignalCardProps {
  signal: ScorecardSignal
}

const VERDICT_CHIP: Record<string, string> = {
  hit: 'border-green-300 bg-green-50 text-green-700 dark:border-green-700 dark:bg-green-900/25 dark:text-green-300',
  miss: 'border-red-300 bg-red-50 text-red-700 dark:border-red-700 dark:bg-red-900/25 dark:text-red-300',
  flat: 'border-gray-300 bg-gray-50 text-gray-600 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300',
}
const STATUS_CHIP: Record<string, string> = {
  pending: 'border-blue-300 bg-blue-50 text-blue-700 dark:border-blue-700 dark:bg-blue-900/25 dark:text-blue-300',
  unscoreable: 'border-gray-300 bg-gray-50 text-gray-500 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400',
}

function chipClass(signal: ScorecardSignal): string {
  if (signal.status === 'scored' && signal.realized) {
    return VERDICT_CHIP[signal.realized.verdict] ?? STATUS_CHIP.unscoreable
  }
  return STATUS_CHIP[signal.status] ?? STATUS_CHIP.unscoreable
}

function pctPos(v: number, lo: number, hi: number): number {
  if (hi <= lo) return 50
  return Math.max(0, Math.min(100, ((v - lo) / (hi - lo)) * 100))
}

// 증거 바: scored + target·spot·실현가 모두 존재할 때만 표시.
function EvidenceBar({ signal }: SignalCardProps) {
  const r = signal.realized
  const spot = signal.spot_at_capture
  const target = signal.target_price
  if (signal.status !== 'scored' || r == null || spot == null || target == null) return null

  const close = r.close
  const lo = Math.min(spot, target, close)
  const hi = Math.max(spot, target, close)
  const marks = [
    { key: 'spot', label: '포착가', value: spot, color: 'bg-gray-400' },
    { key: 'close', label: '실현가', value: close, color: r.verdict === 'hit' ? 'bg-green-500' : 'bg-red-500' },
    { key: 'target', label: '목표가', value: target, color: 'bg-blue-500' },
  ]

  return (
    <div data-testid="evidence-bar" className="mt-2">
      <div className="relative h-1.5 rounded-full bg-gray-100 dark:bg-gray-700">
        {marks.map((m) => (
          <span
            key={m.key}
            data-testid={`evidence-mark-${m.key}`}
            title={`${m.label} ${m.value}`}
            className={`absolute top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-white dark:ring-gray-900 ${m.color}`}
            style={{ left: `${pctPos(m.value, lo, hi)}%` }}
          />
        ))}
      </div>
      <div className="mt-1.5 flex justify-between text-[10px] text-gray-400">
        {marks.map((m) => (
          <span key={m.key}>
            {m.label} {m.value}
          </span>
        ))}
      </div>
    </div>
  )
}

export function SignalCard({ signal }: SignalCardProps) {
  const captured = signal.captured_at
  return (
    <div
      data-testid="signal-card"
      className="rounded-lg border border-gray-100 bg-gray-50/60 p-3 dark:border-gray-800 dark:bg-gray-800/40"
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs text-gray-500 dark:text-gray-400">포착 {captured}</span>
        <span
          data-testid="signal-verdict-chip"
          className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium ${chipClass(signal)}`}
        >
          {signal.status === 'scored' ? signal.realized?.verdict : signal.status}
        </span>
      </div>
      <p data-testid="signal-sentence" className="mt-1 text-sm text-gray-800 dark:text-gray-200">
        {verdictSentence(signal)}
      </p>
      <EvidenceBar signal={signal} />
    </div>
  )
}

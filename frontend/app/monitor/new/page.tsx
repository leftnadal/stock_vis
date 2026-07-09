'use client'

import { useEffect, useMemo, useState } from 'react'

import { useRouter } from 'next/navigation'
import { AlertCircle, ArrowLeft, Check, Loader2 } from 'lucide-react'

import { AuthGuard } from '@/components/auth/AuthGuard'
import { ProgressBar } from '@/components/monitor/builder/ProgressBar'
import { useIndicatorCatalog } from '@/hooks/useMonitor'
import { monitorService } from '@/services/monitorService'
import type { CatalogEntry, MonitorScope, SupportDirection } from '@/types/monitor'

const SCOPES: { key: MonitorScope; label: string; active: boolean }[] = [
  { key: 'stock', label: '종목', active: true },
  { key: 'market', label: '시장', active: false },
  { key: 'sector', label: '섹터', active: false },
  { key: 'theme', label: '테마', active: false },
  { key: 'fund', label: '펀드', active: false },
]

const TOTAL_STEPS = 4

interface PickedIndicator {
  direction: SupportDirection
  weight: number
}

function BuilderContent() {
  const router = useRouter()
  const [step, setStep] = useState(1)
  const [scope, setScope] = useState<MonitorScope>('stock')
  const [targetRef, setTargetRef] = useState('')
  const [name, setName] = useState('')
  const [picked, setPicked] = useState<Record<string, PickedIndicator>>({})
  const [assertion, setAssertion] = useState('')
  const [deadline, setDeadline] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const { data: catalog } = useIndicatorCatalog(scope)

  // 입력이 있으면 하드 이탈(새로고침/닫기) 시 경고
  const dirty =
    targetRef.trim() !== '' ||
    name.trim() !== '' ||
    Object.keys(picked).length > 0 ||
    assertion.trim() !== ''
  useEffect(() => {
    if (!dirty) return
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault()
      e.returnValue = ''
    }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [dirty])

  const canNext = useMemo(() => {
    if (step === 1) return SCOPES.find((s) => s.key === scope)?.active ?? false
    if (step === 2) return targetRef.trim() !== '' && name.trim() !== ''
    return true // 3(지표)·4(Claim)는 선택 — 비어도 진행 가능
  }, [step, scope, targetRef, name])

  function toggleIndicator(entry: CatalogEntry) {
    setPicked((prev) => {
      const next = { ...prev }
      if (next[entry.key]) delete next[entry.key]
      else next[entry.key] = { direction: entry.default_direction, weight: 1 }
      return next
    })
  }

  function cancel() {
    if (dirty && !window.confirm('작성 중인 내용이 사라집니다. 나갈까요?')) return
    router.push('/monitor')
  }

  async function submit() {
    setSubmitting(true)
    setError(null)
    try {
      // 1) Monitor 생성 (검증의 진실 = API ScopeResolver)
      const monitor = await monitorService.create({
        scope,
        target_ref: targetRef,
        name: name.trim(),
      })
      // 2) 선택 지표 부착
      for (const [key, cfg] of Object.entries(picked)) {
        const entry = (catalog ?? []).find((c) => c.key === key)
        if (!entry) continue
        await monitorService.createIndicator({
          monitor: monitor.id,
          name: entry.name,
          indicator_type: entry.indicator_type,
          support_direction: cfg.direction,
          weight: cfg.weight,
          source_key: entry.key,
        })
      }
      // 3) Claim 선택 부착 (주장이 있으면 → 가설)
      if (assertion.trim()) {
        await monitorService.createClaim({
          monitor: monitor.id,
          assertion: assertion.trim(),
          deadline: deadline || null,
        })
      }
      router.push('/monitor')
    } catch (e: unknown) {
      // API 검증 실패(예: 존재하지 않는 심볼) → 대상 지정 단계로
      const detail =
        (e as { response?: { data?: { target_ref?: string[] } } })?.response?.data
          ?.target_ref?.[0] ?? '저장에 실패했어요. 대상을 확인해 주세요.'
      setError(detail)
      setStep(2)
      setSubmitting(false)
    }
  }

  return (
    <div className="mx-auto max-w-lg px-4 py-6">
      <div className="mb-4 flex items-center gap-3">
        <button onClick={cancel} className="text-gray-500 hover:text-gray-800" aria-label="취소">
          <ArrowLeft size={20} />
        </button>
        <h1 className="font-semibold text-gray-900 dark:text-gray-100">새 모니터</h1>
        <span className="ml-auto text-xs text-gray-400">{step} / {TOTAL_STEPS}</span>
      </div>
      <ProgressBar step={step} totalSteps={TOTAL_STEPS} />

      {error && (
        <div className="mt-4 flex items-center gap-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
          <AlertCircle size={16} /> {error}
        </div>
      )}

      <div className="mt-6 min-h-[280px]">
        {step === 1 && (
          <section data-testid="step-scope">
            <h2 className="mb-3 font-medium">무엇을 지켜볼까요?</h2>
            <div className="grid grid-cols-2 gap-2">
              {SCOPES.map((s) => (
                <button
                  key={s.key}
                  disabled={!s.active}
                  onClick={() => setScope(s.key)}
                  className={`rounded-xl border p-4 text-left transition ${
                    scope === s.key && s.active
                      ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/30'
                      : 'border-gray-200 dark:border-gray-700'
                  } ${!s.active ? 'cursor-not-allowed opacity-40' : 'hover:border-gray-300'}`}
                >
                  <span className="font-medium">{s.label}</span>
                  {!s.active && <span className="ml-1 text-xs text-gray-400">준비 중</span>}
                </button>
              ))}
            </div>
          </section>
        )}

        {step === 2 && (
          <section data-testid="step-target" className="flex flex-col gap-3">
            <h2 className="font-medium">어떤 종목인가요?</h2>
            <input
              value={targetRef}
              onChange={(e) => setTargetRef(e.target.value.toUpperCase())}
              placeholder="심볼 (예: AAPL)"
              className="rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-700 dark:bg-gray-900"
            />
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="이 모니터의 이름"
              className="rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-700 dark:bg-gray-900"
            />
            <p className="text-xs text-gray-400">
              심볼 유효성은 저장 시 서버가 확인해요.
            </p>
          </section>
        )}

        {step === 3 && (
          <section data-testid="step-indicators">
            <h2 className="mb-3 font-medium">어떤 지표로 판단할까요?</h2>
            <div className="flex flex-col gap-2">
              {(catalog ?? []).map((entry) => {
                const on = !!picked[entry.key]
                return (
                  <button
                    key={entry.key}
                    onClick={() => toggleIndicator(entry)}
                    className={`flex items-start gap-3 rounded-lg border p-3 text-left transition ${
                      on
                        ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/30'
                        : 'border-gray-200 dark:border-gray-700'
                    }`}
                  >
                    <span
                      className={`mt-0.5 flex h-5 w-5 items-center justify-center rounded border ${
                        on ? 'border-blue-500 bg-blue-500 text-white' : 'border-gray-300'
                      }`}
                    >
                      {on && <Check size={14} />}
                    </span>
                    <span>
                      <span className="font-medium">{entry.name}</span>
                      <span className="ml-1 text-xs text-gray-400">{entry.unit}</span>
                      <span className="block text-xs text-gray-500">{entry.description}</span>
                    </span>
                  </button>
                )
              })}
            </div>
            <p className="mt-3 text-xs text-gray-400">지표 없이도 만들 수 있어요(나중에 추가).</p>
          </section>
        )}

        {step === 4 && (
          <section data-testid="step-claim" className="flex flex-col gap-3">
            <h2 className="font-medium">주장을 붙일까요?</h2>
            <p className="text-sm text-gray-500">
              주장·마감을 붙이면 <b>가설</b>이 됩니다. 건너뛰면 상시 모니터로 둬요.
            </p>
            <textarea
              value={assertion}
              onChange={(e) => setAssertion(e.target.value)}
              placeholder="예: 실적 개선으로 3개월 내 반등한다"
              rows={3}
              className="rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-700 dark:bg-gray-900"
            />
            <label className="text-sm text-gray-500">
              마감일 (선택)
              <input
                type="date"
                value={deadline}
                onChange={(e) => setDeadline(e.target.value)}
                className="ml-2 rounded-lg border border-gray-300 px-2 py-1 dark:border-gray-700 dark:bg-gray-900"
              />
            </label>
          </section>
        )}
      </div>

      <div className="mt-6 flex items-center justify-between">
        <button
          onClick={() => (step === 1 ? cancel() : setStep((s) => s - 1))}
          className="rounded-lg px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800"
        >
          {step === 1 ? '취소' : '이전'}
        </button>
        {step < TOTAL_STEPS ? (
          <button
            onClick={() => setStep((s) => s + 1)}
            disabled={!canNext}
            className="rounded-lg bg-blue-600 px-5 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-40"
          >
            다음
          </button>
        ) : (
          <button
            onClick={submit}
            disabled={submitting}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-40"
          >
            {submitting && <Loader2 size={16} className="animate-spin" />}
            만들기
          </button>
        )}
      </div>
    </div>
  )
}

export default function MonitorBuilderPage() {
  return (
    <AuthGuard>
      <BuilderContent />
    </AuthGuard>
  )
}

'use client'

import { useEffect, useMemo, useState } from 'react'

import { useRouter } from 'next/navigation'
import { useQueryClient } from '@tanstack/react-query'
import { AlertCircle, ArrowLeft, Check, Loader2 } from 'lucide-react'

import { AuthGuard } from '@/components/auth/AuthGuard'
import { ProgressBar } from '@/components/monitor/builder/ProgressBar'
import { monitorKeys, useIndicatorCatalog, useScenarioSuggest } from '@/hooks/useMonitor'
import { monitorService } from '@/services/monitorService'
import type {
  CatalogEntry,
  Coherence,
  EvidenceStrength,
  MonitorScope,
  SupportDirection,
} from '@/types/monitor'

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

// 근거강도 배지 (TIMING-P2 §4) — 강/중/약.
const EVIDENCE_BADGE: Record<EvidenceStrength, { label: string; cls: string }> = {
  strong: { label: '강', cls: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300' },
  medium: { label: '중', cls: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300' },
  weak: { label: '약', cls: 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400' },
}

function BuilderContent() {
  const router = useRouter()
  const queryClient = useQueryClient()
  const [step, setStep] = useState(1)
  const [scope, setScope] = useState<MonitorScope>('stock')
  const [targetRef, setTargetRef] = useState('')
  const [name, setName] = useState('')
  const [picked, setPicked] = useState<Record<string, PickedIndicator>>({})
  const [pickedInit, setPickedInit] = useState(false)
  const [assertion, setAssertion] = useState('')
  const [deadline, setDeadline] = useState('')
  // 매수 시나리오 가격 (TIMING-P2) — 문자열 입력, 제출 시 검증.
  const [entryPrice, setEntryPrice] = useState('')
  const [targetPrice, setTargetPrice] = useState('')
  const [stopPrice, setStopPrice] = useState('')
  const [fairLow, setFairLow] = useState('')
  const [fairHigh, setFairHigh] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const { data: catalog } = useIndicatorCatalog(scope)
  // L계열 제안 — 4단계 진입 + 심볼 확정 시에만 조회
  const { data: suggest } = useScenarioSuggest(targetRef, step === 4)

  // 카탈로그 로드 시 default_selected 지표 1회 프리선택(사용자 미조작 시에만)
  useEffect(() => {
    if (!catalog || pickedInit) return
    const defaults: Record<string, PickedIndicator> = {}
    for (const c of catalog) {
      if (c.default_selected) defaults[c.key] = { direction: c.default_direction, weight: 1 }
    }
    setPicked(defaults)
    setPickedInit(true)
  }, [catalog, pickedInit])

  // 가격 시나리오 검증(4단계 제출 게이트) — 진입가 입력 시 4필수 + 순서 + 미래 기한.
  const hasScenario = entryPrice.trim() !== ''
  const scenarioError = useMemo(() => {
    if (!hasScenario) return null
    const e = Number(entryPrice)
    const t = Number(targetPrice)
    const s = Number(stopPrice)
    if (!targetPrice.trim() || !stopPrice.trim() || !deadline)
      return '진입가·목표가·손절가·기한을 모두 입력해 주세요.'
    if ([e, t, s].some((n) => Number.isNaN(n))) return '가격은 숫자여야 해요.'
    if (!(s < e && e < t)) return '손절가 < 진입가 < 목표가 순서여야 해요.'
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    if (new Date(deadline + 'T00:00:00') <= today) return '기한은 미래 날짜여야 해요.'
    return null
  }, [hasScenario, entryPrice, targetPrice, stopPrice, deadline])

  // TIMING-P2.5: 4단계 진입 시 4필드 프리필(빈 칸에만 — 사용자 입력 덮어쓰기 금지)
  const [prefilled, setPrefilled] = useState(false)
  useEffect(() => {
    if (step !== 4 || !suggest?.available || prefilled) return
    setPrefilled(true)
    if (suggest.entry_suggest != null) setEntryPrice((v) => v || String(suggest.entry_suggest))
    if (suggest.target_suggest != null) setTargetPrice((v) => v || String(suggest.target_suggest))
    if (suggest.stop_suggest != null) setStopPrice((v) => v || String(suggest.stop_suggest))
    if (suggest.deadline_suggest) setDeadline((v) => v || suggest.deadline_suggest!)
  }, [step, suggest, prefilled])

  // 정합 힌트(인터랙티브 조정) — 사용자가 마지막 수정한 필드 기준 나머지 재제안(자동 개서 금지)
  const [lastEdited, setLastEdited] = useState<'target' | 'deadline' | null>(null)
  const [hint, setHint] = useState<Coherence | null>(null)
  useEffect(() => {
    if (step !== 4 || !targetRef || !entryPrice.trim() || !lastEdited) {
      setHint(null)
      return
    }
    const params =
      lastEdited === 'target'
        ? targetPrice.trim()
          ? { entry: entryPrice, target: targetPrice, stop: stopPrice || undefined }
          : null
        : deadline
          ? { entry: entryPrice, deadline, stop: stopPrice || undefined }
          : null
    if (!params) {
      setHint(null)
      return
    }
    const id = setTimeout(async () => {
      try {
        const r = await monitorService.scenarioSuggest(targetRef, params)
        setHint(r.coherence ?? null)
      } catch {
        setHint(null)
      }
    }, 500) // 디바운스: 입력 중 호출 억제
    return () => clearTimeout(id)
  }, [step, targetRef, entryPrice, targetPrice, deadline, stopPrice, lastEdited])

  // 손익비 R:R (로컬 즉시 계산) = (목표−진입)/(진입−손절)
  const rr = useMemo(() => {
    const e = Number(entryPrice)
    const t = Number(targetPrice)
    const s = Number(stopPrice)
    if ([e, t, s].some((n) => Number.isNaN(n))) return null
    const risk = e - s
    if (risk <= 0) return null
    return (t - e) / risk
  }, [entryPrice, targetPrice, stopPrice])

  function applySuggest() {
    if (!suggest?.available) return
    if (suggest.entry_suggest != null) setEntryPrice(String(suggest.entry_suggest))
    if (suggest.stop_suggest != null) setStopPrice(String(suggest.stop_suggest))
    if (suggest.target_suggest != null) setTargetPrice(String(suggest.target_suggest))
    if (suggest.deadline_suggest) setDeadline(suggest.deadline_suggest)
  }

  // 입력이 있으면 하드 이탈(새로고침/닫기) 시 경고
  const dirty =
    targetRef.trim() !== '' ||
    name.trim() !== '' ||
    Object.keys(picked).length > 0 ||
    assertion.trim() !== '' ||
    entryPrice.trim() !== ''
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
      // 3) Claim 선택 부착 (매수 시나리오 가격 또는 근거 메모가 있으면)
      // assertion은 BE 필수(non-blank) — 메모 없는 시나리오는 가격으로 자동 합성.
      const memo = assertion.trim()
      if (hasScenario || memo) {
        const finalAssertion =
          memo ||
          `매수 시나리오 · 진입 ${entryPrice} / 목표 ${targetPrice} / 손절 ${stopPrice}`
        await monitorService.createClaim({
          monitor: monitor.id,
          assertion: finalAssertion,
          deadline: deadline || null,
          entry_price: hasScenario ? entryPrice : null,
          target_price: hasScenario ? targetPrice : null,
          stop_price: hasScenario ? stopPrice : null,
          fair_value_low: fairLow.trim() || null,
          fair_value_high: fairHigh.trim() || null,
        })
      }
      // 리스트 캐시 무효화 → 복귀 시 새 카드 즉시 반영 (stale 방지)
      await queryClient.invalidateQueries({ queryKey: monitorKeys.lists() })
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
                      {entry.evidence_strength && (
                        <span
                          data-testid={`evidence-badge-${entry.key}`}
                          className={`ml-1.5 rounded px-1 py-0.5 text-[10px] font-medium ${EVIDENCE_BADGE[entry.evidence_strength].cls}`}
                        >
                          근거 {EVIDENCE_BADGE[entry.evidence_strength].label}
                        </span>
                      )}
                      <span className="ml-1 text-xs text-gray-400">{entry.unit}</span>
                      <span className="block text-xs text-gray-500">{entry.description}</span>
                    </span>
                  </button>
                )
              })}
            </div>
            <p className="mt-3 text-xs text-gray-400">
              지표 없이도 만들 수 있어요(나중에 추가). 근거 강도는 학술 검증 수준이에요.
            </p>
          </section>
        )}

        {step === 4 && (
          <section data-testid="step-claim" className="flex flex-col gap-3">
            <h2 className="font-medium">매수 시나리오를 작성할까요?</h2>
            <p className="text-sm text-gray-500">
              진입·목표·손절가와 기한을 정하면 <b>매수 시나리오</b>가 됩니다. 건너뛰면 상시
              모니터로 둬요.
            </p>

            {/* L계열 제안 배너 (TIMING-P2 §3) */}
            {suggest?.available && (
              <div
                data-testid="scenario-suggest-banner"
                className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-sm dark:border-blue-800 dark:bg-blue-900/25"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium text-blue-800 dark:text-blue-200">가격 제안</span>
                  <button
                    type="button"
                    onClick={applySuggest}
                    data-testid="scenario-suggest-apply"
                    className="rounded bg-blue-600 px-2 py-0.5 text-xs font-medium text-white hover:bg-blue-700"
                  >
                    적용
                  </button>
                </div>
                <p className="mt-1 text-xs text-blue-700 dark:text-blue-300">{suggest.basis}</p>
              </div>
            )}

            {/* 가격 3필드 + 출처 캡션 (TIMING-P2.5 프리필) */}
            <div className="grid grid-cols-3 gap-2">
              <label className="text-xs text-gray-500">
                진입가
                <input
                  type="number"
                  inputMode="decimal"
                  value={entryPrice}
                  onChange={(e) => setEntryPrice(e.target.value)}
                  data-testid="scenario-entry-price"
                  placeholder="진입"
                  className="mt-1 w-full rounded-lg border border-gray-300 px-2 py-1.5 text-sm dark:border-gray-700 dark:bg-gray-900"
                />
                {suggest?.captions?.entry && (
                  <span className="mt-0.5 block text-[10px] text-gray-400">{suggest.captions.entry}</span>
                )}
              </label>
              <label className="text-xs text-gray-500">
                목표가
                <input
                  type="number"
                  inputMode="decimal"
                  value={targetPrice}
                  onChange={(e) => {
                    setTargetPrice(e.target.value)
                    setLastEdited('target')
                  }}
                  data-testid="scenario-target-price"
                  placeholder="익절"
                  className="mt-1 w-full rounded-lg border border-gray-300 px-2 py-1.5 text-sm dark:border-gray-700 dark:bg-gray-900"
                />
                {suggest?.captions?.target && (
                  <span className="mt-0.5 block text-[10px] text-gray-400">{suggest.captions.target}</span>
                )}
              </label>
              <label className="text-xs text-gray-500">
                손절가
                <input
                  type="number"
                  inputMode="decimal"
                  value={stopPrice}
                  onChange={(e) => setStopPrice(e.target.value)}
                  data-testid="scenario-stop-price"
                  placeholder="손절"
                  className="mt-1 w-full rounded-lg border border-gray-300 px-2 py-1.5 text-sm dark:border-gray-700 dark:bg-gray-900"
                />
                {suggest?.captions?.stop && (
                  <span className="mt-0.5 block text-[10px] text-gray-400">{suggest.captions.stop}</span>
                )}
              </label>
            </div>

            {/* 목표 재제안 힌트 (기한 수정 시) — 자동 개서 금지, [적용] 1탭 */}
            {lastEdited === 'deadline' && hint?.coherent_target && (
              <div
                data-testid="scenario-target-hint"
                className="flex items-center justify-between gap-2 rounded-md bg-gray-50 px-2.5 py-1.5 text-xs text-gray-600 dark:bg-gray-800 dark:text-gray-300"
              >
                <span>{hint.basis}</span>
                <button
                  type="button"
                  data-testid="scenario-target-hint-apply"
                  onClick={() => {
                    setTargetPrice(hint.coherent_target!)
                    setLastEdited(null)
                  }}
                  className="flex-shrink-0 rounded bg-gray-700 px-2 py-0.5 font-medium text-white hover:bg-gray-800"
                >
                  적용
                </button>
              </div>
            )}

            <label className="text-sm text-gray-500">
              기한
              <input
                type="date"
                value={deadline}
                onChange={(e) => {
                  setDeadline(e.target.value)
                  setLastEdited('deadline')
                }}
                data-testid="scenario-deadline"
                className="ml-2 rounded-lg border border-gray-300 px-2 py-1 dark:border-gray-700 dark:bg-gray-900"
              />
              {suggest?.captions?.deadline && (
                <span className="mt-0.5 block text-[10px] text-gray-400">{suggest.captions.deadline}</span>
              )}
            </label>

            {/* 기한 재제안 힌트 (목표 수정 시) */}
            {lastEdited === 'target' && hint?.coherent_deadline && (
              <div
                data-testid="scenario-deadline-hint"
                className="flex items-center justify-between gap-2 rounded-md bg-gray-50 px-2.5 py-1.5 text-xs text-gray-600 dark:bg-gray-800 dark:text-gray-300"
              >
                <span>{hint.basis}</span>
                <button
                  type="button"
                  data-testid="scenario-deadline-hint-apply"
                  onClick={() => {
                    setDeadline(hint.coherent_deadline!)
                    setLastEdited(null)
                  }}
                  className="flex-shrink-0 rounded bg-gray-700 px-2 py-0.5 font-medium text-white hover:bg-gray-800"
                >
                  재제안 적용
                </button>
              </div>
            )}

            {/* 손익비 R:R + 고지 */}
            {rr != null && (
              <p data-testid="scenario-rr" className="text-xs text-gray-500">
                손익비 {rr.toFixed(1)} : 1
                <span className="ml-1 text-[10px] text-gray-400">· 변동성 기준 정합 · 예측 아님</span>
              </p>
            )}

            {/* 적정가 밴드 (선택) */}
            <details className="text-sm text-gray-500">
              <summary className="cursor-pointer">적정가 밴드 (선택)</summary>
              <p className="mt-1 text-xs text-gray-400">가치평가 연동 예정 — 지금은 수동 입력.</p>
              <div className="mt-2 grid grid-cols-2 gap-2">
                <input
                  type="number"
                  inputMode="decimal"
                  value={fairLow}
                  onChange={(e) => setFairLow(e.target.value)}
                  placeholder="적정가 하단"
                  className="rounded-lg border border-gray-300 px-2 py-1.5 text-sm dark:border-gray-700 dark:bg-gray-900"
                />
                <input
                  type="number"
                  inputMode="decimal"
                  value={fairHigh}
                  onChange={(e) => setFairHigh(e.target.value)}
                  placeholder="적정가 상단"
                  className="rounded-lg border border-gray-300 px-2 py-1.5 text-sm dark:border-gray-700 dark:bg-gray-900"
                />
              </div>
            </details>

            {/* 근거 메모 (기존 assertion 필드 재라벨, 선택) */}
            <label className="text-sm text-gray-500">
              근거 메모 (선택)
              <textarea
                value={assertion}
                onChange={(e) => setAssertion(e.target.value)}
                placeholder="예: 실적 개선으로 3개월 내 반등한다"
                rows={2}
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-900"
              />
            </label>

            {scenarioError && (
              <p data-testid="scenario-error" className="text-xs text-red-500">
                {scenarioError}
              </p>
            )}
            <p className="text-[11px] text-gray-400">일봉 기준 · 스윙 타이밍</p>
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
            disabled={submitting || !!scenarioError}
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

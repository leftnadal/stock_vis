'use client'

import type { BriefDetail as Detail } from '@/lib/api/marketPulseV2'

export function BriefDetail({ payload }: { payload: Detail }) {
  if (!payload.available) {
    return <p className="text-sm text-slate-500">브리핑 상세 데이터가 아직 준비되지 않았습니다.</p>
  }
  return (
    <div className="grid gap-4">
      <header>
        {payload.headline ? <p className="text-base font-semibold text-slate-900">{payload.headline}</p> : null}
        <p className="text-xs text-slate-500 mt-1">
          {payload.date} · {payload.model_version} · {payload.status}
        </p>
      </header>
      {payload.body_sections && payload.body_sections.length > 0 ? (
        <div className="grid gap-2">
          {payload.body_sections.map((section, i) => (
            <p key={i} className="text-sm text-slate-800 whitespace-pre-wrap">{section}</p>
          ))}
        </div>
      ) : payload.body ? (
        <div className="grid gap-2">
          {payload.body.split(/\n\n+/).map((para, i) => (
            <p key={i} className="text-sm text-slate-800 whitespace-pre-wrap">{para}</p>
          ))}
        </div>
      ) : payload.content ? (
        <p className="text-sm text-slate-800 whitespace-pre-wrap">{payload.content}</p>
      ) : null}
      {payload.tokens ? (
        <p className="text-[10px] text-slate-400">
          tokens prompt={payload.tokens.prompt} · completion={payload.tokens.completion} · {payload.tokens.latency_ms}ms
        </p>
      ) : null}
      {payload.inputs_summary ? (
        <details className="text-xs text-slate-600">
          <summary className="cursor-pointer">입력 컨텍스트 (inputs_summary)</summary>
          <pre className="mt-1 bg-slate-50 p-2 rounded border border-slate-200 overflow-x-auto">
            {JSON.stringify(payload.inputs_summary, null, 2)}
          </pre>
        </details>
      ) : null}
    </div>
  )
}

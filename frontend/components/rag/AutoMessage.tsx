'use client'

import { RefreshCw } from 'lucide-react'

interface AutoMessageProps {
  addedDataTypes: Array<{ type: string; label: string; units: number }>
}

export function AutoMessage({ addedDataTypes }: AutoMessageProps) {
  return (
    <div
      className="mx-4 my-3 bg-gradient-to-r from-[rgba(88,166,255,0.05)] to-[rgba(163,113,247,0.05)] border border-[rgba(88,166,255,0.2)] rounded-xl p-3 animate-slideIn"
      style={{
        animation: 'slideIn 400ms ease-out 100ms backwards',
      }}
    >
      {/* 헤더 */}
      <div className="flex justify-between items-center text-xs text-[#8B949E] mb-2">
        <span>[자동으로 요청됨]</span>
        <RefreshCw className="w-3 h-3 animate-spin" />
      </div>

      {/* 메시지 */}
      <p className="text-sm text-[#C9D1D9] mb-2">
        방금 추가한 데이터로 분석을 계속해주세요
      </p>

      {/* 추가된 데이터 목록 */}
      {addedDataTypes.length > 0 && (
        <ul className="text-xs text-[#8B949E] pl-3 space-y-1">
          {addedDataTypes.map((data, idx) => (
            <li key={idx}>
              • <span className="text-[#58A6FF]">{data.label}</span> ({data.units} units)
            </li>
          ))}
        </ul>
      )}

      <style jsx>{`
        @keyframes slideIn {
          from {
            transform: translateY(20px);
            opacity: 0;
          }
          to {
            transform: translateY(0);
            opacity: 1;
          }
        }
      `}</style>
    </div>
  )
}

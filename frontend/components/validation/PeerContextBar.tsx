'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, Info } from 'lucide-react';
import type { PeerInfo, PresetInfo } from '@/types/validation';

const CONFIDENCE_BADGE = {
  high: { label: '높음', color: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' },
  medium: { label: '보통', color: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400' },
  low: { label: '낮음', color: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400' },
  limited: { label: '제한적', color: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300' },
} as const;

interface Props {
  peerInfo: PeerInfo;
  fiscalYear: number;
  presets?: PresetInfo[];
  onSelectPreset?: (presetKey: string) => void;
  onSetCustomPeers?: (peers: string[]) => void;
}

export default function PeerContextBar({ peerInfo, fiscalYear, presets, onSelectPreset, onSetCustomPeers }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [showCustom, setShowCustom] = useState(false);
  const [customInput, setCustomInput] = useState('');

  const confidenceKey = peerInfo.confidence as keyof typeof CONFIDENCE_BADGE;
  const badge = CONFIDENCE_BADGE[confidenceKey] || CONFIDENCE_BADGE.low;

  return (
    <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
      {/* 프리셋 탭 */}
      {presets && presets.length > 1 && onSelectPreset && (
        <>
          <div className="flex flex-wrap gap-2 mb-3 pb-3 border-b border-blue-100 dark:border-blue-800">
            {presets.map((p) => (
              <button
                key={p.preset_key}
                onClick={() => onSelectPreset(p.preset_key)}
                className={`min-h-[44px] px-4 py-2 text-xs font-medium rounded-full transition-colors ${
                  p.is_selected
                    ? 'bg-blue-600 text-white dark:bg-blue-500'
                    : 'bg-white text-gray-600 hover:bg-blue-100 dark:bg-gray-700 dark:text-gray-400 dark:hover:bg-gray-600'
                }`}
                title={p.logic_summary}
              >
                {p.display_name}
                <span className="ml-1 opacity-60">{p.peer_count}</span>
              </button>
            ))}
            {onSetCustomPeers && (
              <button
                onClick={() => setShowCustom(!showCustom)}
                className={`min-h-[44px] px-4 py-2 text-xs font-medium rounded-full transition-colors ${
                  (peerInfo.benchmark_basis as string) === 'custom'
                    ? 'bg-purple-600 text-white'
                    : 'bg-white text-purple-600 hover:bg-purple-50 dark:bg-gray-700 dark:text-purple-400 border border-purple-200 dark:border-purple-700'
                }`}
              >
                직접 설정
              </button>
            )}
          </div>

          {/* 직접 설정 인라인 입력 */}
          {showCustom && onSetCustomPeers && (
            <div className="mt-2 pb-3 border-b border-blue-100 dark:border-blue-800">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={customInput}
                  onChange={(e) => setCustomInput(e.target.value.toUpperCase())}
                  placeholder="심볼 입력 (쉼표로 구분: MSFT, GOOGL, META)"
                  className="flex-1 px-3 py-1.5 text-xs border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400"
                />
                <button
                  onClick={() => {
                    const peers = customInput.split(',').map(s => s.trim()).filter(Boolean);
                    if (peers.length >= 2) {
                      onSetCustomPeers(peers);
                      setShowCustom(false);
                      setCustomInput('');
                    }
                  }}
                  className="px-3 py-1.5 text-xs bg-purple-600 text-white rounded-lg hover:bg-purple-700"
                >
                  적용
                </button>
              </div>
              <p className="mt-1 text-[10px] text-gray-400">최소 2개 이상 입력. S&P 500 종목만 유효.</p>
            </div>
          )}
        </>
      )}

      {/* 메인 라인 */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
        <span className="font-medium text-gray-900 dark:text-white">
          📊 비교 기준: {peerInfo.basis_description} {peerInfo.peer_count}개
        </span>
        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${badge.color}`}>
          비교 신뢰도: {badge.label}
        </span>
        <span className="text-gray-500 dark:text-gray-400">
          데이터 기준: {fiscalYear} FY
        </span>
      </div>

      {/* 안내문 */}
      <div className="flex items-center gap-1.5 mt-2 text-xs text-gray-500 dark:text-gray-400">
        <Info className="w-3.5 h-3.5 flex-shrink-0" />
        <span>과거 연도 차트도 현재 peer 기준으로 계산됩니다</span>
      </div>

      {/* Peer 목록 접기/펼치기 */}
      {peerInfo.top_peers.length > 0 && (
        <div className="mt-3">
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 text-xs text-blue-600 dark:text-blue-400 hover:underline"
          >
            peer 목록 {expanded ? '접기' : '보기'}
            {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>
          {expanded && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {peerInfo.top_peers.map((sym) => (
                <span
                  key={sym}
                  className="inline-flex px-2 py-0.5 bg-white dark:bg-gray-700 rounded text-xs text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-600"
                >
                  {sym}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

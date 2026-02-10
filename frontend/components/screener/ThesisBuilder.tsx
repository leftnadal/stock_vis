'use client';

import React, { useState } from 'react';
import { Lightbulb, Share2, Save, Loader2, AlertCircle } from 'lucide-react';
import type { ScreenerStock, ScreenerFilters, InvestmentThesis } from '@/types/screener';
import { screenerService } from '@/services/screenerService';

interface ThesisBuilderProps {
  stocks: ScreenerStock[];
  filters: ScreenerFilters;
  onThesisGenerated?: (thesis: InvestmentThesis) => void;
  className?: string;
}

export default function ThesisBuilder({
  stocks,
  filters,
  onThesisGenerated,
  className = '',
}: ThesisBuilderProps) {
  const [userNotes, setUserNotes] = useState('');
  const [thesis, setThesis] = useState<InvestmentThesis | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);
  const [copySuccess, setCopySuccess] = useState(false);

  const handleGenerate = async () => {
    if (stocks.length === 0) {
      setError('필터링된 종목이 없습니다. 필터를 조정해주세요.');
      return;
    }

    setIsGenerating(true);
    setError(null);
    setWarning(null);

    try {
      const response = await screenerService.generateThesis(
        stocks,
        filters,
        userNotes || undefined
      );

      if (response.success) {
        setThesis(response.data);
        onThesisGenerated?.(response.data);

        // 폴백 테제인 경우 경고 표시
        if (response.warning) {
          console.warn('Thesis warning:', response.warning);
          setWarning(response.warning);
        }
      } else {
        setError('투자 테제 생성에 실패했습니다. 다시 시도해주세요.');
      }
    } catch (err: unknown) {
      console.error('Thesis generation error:', err);
      const errorMessage = err instanceof Error ? err.message : String(err);
      setError(`투자 테제 생성 중 오류가 발생했습니다: ${errorMessage}`);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleShare = async () => {
    if (!thesis?.share_code) return;

    const shareUrl = `${window.location.origin}/thesis/${thesis.share_code}`;

    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    } catch (err) {
      console.error('Copy failed:', err);
    }
  };

  const handleSave = () => {
    // TODO: Implement save to watchlist functionality
    console.log('Save to watchlist:', thesis?.top_picks);
  };

  return (
    <div className={`rounded-lg border border-[#30363D] bg-[#161B22] ${className}`}>
      {/* Header */}
      <div className="border-b border-[#30363D] px-4 py-3">
        <div className="flex items-center gap-2">
          <Lightbulb className="h-5 w-5 text-[#FFC107]" />
          <h2 className="text-base font-semibold text-[#E6EDF3]">투자 테제 빌더</h2>
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        {!thesis ? (
          /* Generation Form */
          <div className="space-y-4">
            <p className="text-sm text-[#8B949E]">
              현재 <span className="font-semibold text-[#58A6FF]">{stocks.length}개</span> 종목이 선별되었습니다.
            </p>

            <div>
              <label className="mb-2 block text-sm text-[#E6EDF3]">
                메모 (선택)
              </label>
              <textarea
                value={userNotes}
                onChange={(e) => setUserNotes(e.target.value)}
                placeholder="투자 아이디어나 추가 고려사항을 입력해주세요..."
                className="h-24 w-full resize-none rounded-lg border border-[#30363D] bg-[#0D1117] px-3 py-2 text-sm text-[#E6EDF3] placeholder:text-[#6E7681] focus:border-[#58A6FF] focus:outline-none"
                disabled={isGenerating}
              />
            </div>

            {error && (
              <div className="flex items-center gap-2 rounded-lg border border-[#F85149]/30 bg-[#F85149]/10 px-3 py-2 text-sm text-[#F85149]">
                <AlertCircle className="h-4 w-4 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <button
              onClick={handleGenerate}
              disabled={isGenerating || stocks.length === 0}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#1F6FEB] px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-[#1a5fc7] disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isGenerating ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  AI로 분석 중...
                </>
              ) : (
                'AI로 투자 테제 생성하기'
              )}
            </button>
          </div>
        ) : (
          /* Thesis Card */
          <div className="space-y-4">
            {/* Warning (fallback thesis) */}
            {warning && (
              <div className="flex items-start gap-2 rounded-lg border border-[#F0A830]/30 bg-[#F0A830]/10 px-3 py-2 text-xs text-[#F0A830]">
                <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
                <span className="break-all">{warning}</span>
              </div>
            )}

            {/* Title & Actions */}
            <div className="flex items-start justify-between gap-4">
              <h3 className="text-lg font-bold text-[#E6EDF3]">{thesis.title}</h3>
              <div className="flex gap-2">
                <button
                  onClick={handleShare}
                  className="flex items-center gap-1.5 rounded-lg border border-[#30363D] bg-[#0D1117] px-3 py-1.5 text-xs font-medium text-[#E6EDF3] transition-colors hover:border-[#58A6FF]/50 hover:text-[#58A6FF]"
                  title="공유"
                >
                  <Share2 className="h-3.5 w-3.5" />
                  {copySuccess ? '복사됨!' : '공유'}
                </button>
                <button
                  onClick={handleSave}
                  className="flex items-center gap-1.5 rounded-lg border border-[#30363D] bg-[#0D1117] px-3 py-1.5 text-xs font-medium text-[#E6EDF3] transition-colors hover:border-[#58A6FF]/50 hover:text-[#58A6FF]"
                  title="저장"
                >
                  <Save className="h-3.5 w-3.5" />
                  저장
                </button>
              </div>
            </div>

            {/* Summary */}
            <p className="text-sm leading-relaxed text-[#8B949E]">{thesis.summary}</p>

            {/* Key Metrics */}
            <div>
              <div className="mb-2 flex items-center gap-1.5 text-sm font-medium text-[#E6EDF3]">
                <span className="text-base">📈</span>
                핵심 지표
              </div>
              <div className="flex flex-wrap gap-2">
                {thesis.key_metrics.map((metric, idx) => (
                  <span
                    key={idx}
                    className="rounded-full border border-[#30363D] bg-[#0D1117] px-3 py-1 text-xs font-medium text-[#58A6FF]"
                  >
                    {metric}
                  </span>
                ))}
              </div>
            </div>

            {/* Top Picks */}
            <div>
              <div className="mb-2 flex items-center gap-1.5 text-sm font-medium text-[#E6EDF3]">
                <span className="text-base">🏆</span>
                Top Picks ({thesis.top_picks.length})
              </div>
              <div className="flex flex-wrap gap-2">
                {thesis.top_picks.map((symbol, idx) => (
                  <a
                    key={idx}
                    href={`/stocks/${symbol}`}
                    className="rounded-lg border border-[#30363D] bg-[#0D1117] px-3 py-1.5 text-sm font-bold text-[#58A6FF] transition-colors hover:border-[#58A6FF]/50"
                  >
                    {symbol}
                  </a>
                ))}
              </div>
            </div>

            {/* Risks */}
            <div>
              <div className="mb-2 flex items-center gap-1.5 text-sm font-medium text-[#E6EDF3]">
                <span className="text-base">⚠️</span>
                리스크
              </div>
              <ul className="space-y-1">
                {thesis.risks.map((risk, idx) => (
                  <li key={idx} className="flex gap-2 text-sm text-[#8B949E]">
                    <span className="text-[#6E7681]">•</span>
                    <span>{risk}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Footer */}
            <div className="flex items-center justify-between border-t border-[#30363D] pt-3 text-xs text-[#6E7681]">
              <span>생성일: {new Date(thesis.created_at).toLocaleDateString('ko-KR')}</span>
              <button
                onClick={() => {
                  setThesis(null);
                  setUserNotes('');
                  setError(null);
                  setWarning(null);
                }}
                className="text-[#58A6FF] hover:underline"
              >
                새로 생성
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

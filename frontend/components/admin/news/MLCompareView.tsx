'use client';

import { useState } from 'react';
import { AlertTriangle, X } from 'lucide-react';
import { useMLRollback, useMLRollbackPreview } from '@/hooks/useNewsPipeline';

// ============================================================
// 비교 테이블 (현재 모델 vs 기본 가중치)
// ============================================================

interface WeightCompareTableProps {
  currentWeights: Record<string, number>;
  defaultWeights: Record<string, number>;
}

function WeightCompareTable({ currentWeights, defaultWeights }: WeightCompareTableProps) {
  const allKeys = Array.from(
    new Set([...Object.keys(currentWeights), ...Object.keys(defaultWeights)])
  ).sort();

  if (allKeys.length === 0) {
    return <p className="text-xs text-gray-500 mt-2">가중치 정보 없음</p>;
  }

  return (
    <div className="overflow-x-auto mt-3">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-gray-700">
            <th className="text-left py-1.5 pr-3 text-gray-400 font-medium">피처</th>
            <th className="text-right py-1.5 pr-3 text-gray-400 font-medium">현재 모델</th>
            <th className="text-right py-1.5 text-gray-400 font-medium">기본값</th>
          </tr>
        </thead>
        <tbody>
          {allKeys.map((key) => {
            const current = currentWeights[key] ?? null;
            const def = defaultWeights[key] ?? null;
            const diff =
              current !== null && def !== null ? current - def : null;
            const diffColor =
              diff === null
                ? ''
                : diff > 0.01
                ? 'text-green-400'
                : diff < -0.01
                ? 'text-red-400'
                : 'text-gray-400';
            return (
              <tr key={key} className="border-b border-gray-700/50 last:border-0">
                <td className="py-1.5 pr-3 text-gray-300 font-mono">{key}</td>
                <td className={`text-right py-1.5 pr-3 ${diffColor}`}>
                  {current !== null ? current.toFixed(4) : '—'}
                </td>
                <td className="text-right py-1.5 text-gray-400">
                  {def !== null ? def.toFixed(4) : '—'}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ============================================================
// 롤백 모달
// ============================================================

interface RollbackModalProps {
  onClose: () => void;
}

function RollbackModal({ onClose }: RollbackModalProps) {
  const [previewEnabled, setPreviewEnabled] = useState(true);
  const { data, isLoading, error } = useMLRollbackPreview(previewEnabled);
  const { mutate, isPending, isSuccess, error: mutateError } = useMLRollback();

  function handleConfirm() {
    mutate(undefined, {
      onSuccess: () => {
        // 성공 시 1초 후 모달 닫기
        setTimeout(onClose, 1000);
      },
    });
  }

  const is404 =
    error && 'response' in (error as { response?: { status?: number } })
      ? (error as { response?: { status?: number } }).response?.status === 404
      : false;

  return (
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="rollback-modal-title"
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
      >
        <div className="bg-gray-800 rounded-xl border border-gray-700 w-full max-w-xl shadow-2xl max-h-[90vh] flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between p-5 border-b border-gray-700 flex-shrink-0">
            <h2 id="rollback-modal-title" className="font-semibold text-gray-200">
              ML 모델 롤백 확인
            </h2>
            <button
              onClick={onClose}
              className="p-1 rounded hover:bg-gray-700 text-gray-400 hover:text-gray-200 transition-colors"
              aria-label="닫기"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {/* Body */}
          <div className="p-5 overflow-y-auto flex-1">
            {isLoading && (
              <div className="h-32 bg-gray-700 rounded-lg animate-pulse" />
            )}

            {is404 && (
              <p className="text-sm text-yellow-400">
                현재 배포된 모델이 없습니다. 롤백할 대상이 존재하지 않습니다.
              </p>
            )}

            {!isLoading && error && !is404 && (
              <p className="text-sm text-red-400">미리보기 로드 실패</p>
            )}

            {data && (
              <>
                {/* 현재 모델 정보 */}
                <div className="mb-4">
                  <p className="text-xs text-gray-500 mb-1">현재 배포 모델</p>
                  <div className="bg-gray-900 rounded-lg p-3">
                    <p className="text-sm font-mono text-gray-200 mb-1 truncate">
                      {data.current_deployed.model_version}
                    </p>
                    <div className="flex gap-4 text-xs text-gray-400">
                      <span>
                        알고리즘:{' '}
                        <span className="text-gray-300">{data.current_deployed.algorithm}</span>
                      </span>
                      <span>
                        F1:{' '}
                        <span className="text-green-400">
                          {data.current_deployed.f1_score.toFixed(3)}
                        </span>
                      </span>
                    </div>
                  </div>
                </div>

                {/* 롤백 대상 */}
                <div className="mb-4">
                  <p className="text-xs text-gray-500 mb-1">롤백 대상</p>
                  <div className="bg-gray-900 rounded-lg p-3">
                    <p className="text-sm font-mono text-gray-200 truncate">
                      {data.rollback_target}
                    </p>
                  </div>
                </div>

                {/* 가중치 비교 테이블 */}
                <div className="mb-4">
                  <p className="text-xs text-gray-500 mb-1">스무딩 가중치 비교 (현재 vs 기본값)</p>
                  <div className="bg-gray-900 rounded-lg p-3">
                    <WeightCompareTable
                      currentWeights={data.current_deployed.smoothed_weights}
                      defaultWeights={data.default_weights}
                    />
                  </div>
                </div>

                {/* impact_warning */}
                {data.impact_warning && (
                  <div className="flex gap-2 bg-yellow-900/20 border border-yellow-800/50 rounded-lg p-3 mb-2">
                    <AlertTriangle className="h-4 w-4 text-yellow-400 flex-shrink-0 mt-0.5" />
                    <p className="text-xs text-yellow-300">{data.impact_warning}</p>
                  </div>
                )}
              </>
            )}

            {/* 뮤테이션 성공 메시지 */}
            {isSuccess && (
              <p className="text-sm text-green-400 mt-2">롤백이 완료되었습니다. 잠시 후 닫힙니다.</p>
            )}

            {/* 뮤테이션 에러 메시지 */}
            {mutateError && (
              <p className="text-sm text-red-400 mt-2">롤백 실패: 다시 시도해 주세요.</p>
            )}
          </div>

          {/* Footer */}
          <div className="flex justify-end gap-2 p-4 border-t border-gray-700 flex-shrink-0">
            <button
              onClick={onClose}
              disabled={isPending}
              className="px-4 py-2 text-sm rounded-lg bg-gray-700 text-gray-300 hover:bg-gray-600 transition-colors disabled:opacity-50"
            >
              취소
            </button>
            <button
              onClick={handleConfirm}
              disabled={isPending || isSuccess || is404 || !data}
              className="px-4 py-2 text-sm rounded-lg bg-red-700 text-white hover:bg-red-600 transition-colors disabled:opacity-50 flex items-center gap-1.5"
            >
              {isPending ? (
                <>
                  <span className="inline-block w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  롤백 중...
                </>
              ) : (
                '롤백 실행'
              )}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

// ============================================================
// MLCompareView — 진입 버튼 + 모달 조합
// ============================================================

interface MLCompareViewProps {
  enabled?: boolean;
}

export function MLCompareView({ enabled = true }: MLCompareViewProps) {
  const [modalOpen, setModalOpen] = useState(false);

  if (!enabled) return null;

  return (
    <>
      <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-gray-200">ML 모델 롤백</h3>
          <button
            onClick={() => setModalOpen(true)}
            className="px-3 py-1.5 text-sm rounded-lg bg-red-900/30 text-red-400 border border-red-800 hover:bg-red-900/50 transition-colors"
          >
            롤백
          </button>
        </div>
        <p className="text-xs text-gray-500">
          현재 배포된 ML 모델을 기본 가중치로 롤백합니다. 실행 전 영향 범위를 반드시 확인하세요.
        </p>
      </div>

      {modalOpen && <RollbackModal onClose={() => setModalOpen(false)} />}
    </>
  );
}

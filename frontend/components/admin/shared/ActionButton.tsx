'use client';

import { useState, useEffect } from 'react';
import { Play, Loader2, CheckCircle, XCircle, AlertTriangle, Clock } from 'lucide-react';
import { useAdminAction } from '@/hooks/useAdminAction';

interface ActionButtonProps {
  action: string;
  label: string;
  params?: Record<string, any>;
  dangerous?: boolean;
  size?: 'sm' | 'md';
  variant?: 'primary' | 'secondary' | 'danger';
}

export default function ActionButton({
  action,
  label,
  params,
  dangerous = false,
  size = 'sm',
  variant = 'primary',
}: ActionButtonProps) {
  const { execute, state, error, costEstimate, reset } = useAdminAction(action);
  const [showConfirm, setShowConfirm] = useState(false);

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (state === 'dispatching' || state === 'polling') return;
    if (state === 'failure' || state === 'timeout') {
      reset();
      return;
    }
    execute(action, params);
  };

  const handleConfirm = (e: React.MouseEvent) => {
    e.stopPropagation();
    setShowConfirm(false);
    execute(action, params, true);
  };

  const handleCancel = (e: React.MouseEvent) => {
    e.stopPropagation();
    setShowConfirm(false);
    reset();
  };

  // requires_confirm 응답 시 확인 UI 표시
  useEffect(() => {
    if (error === 'REQUIRES_CONFIRM' && !showConfirm) {
      setShowConfirm(true);
    }
  }, [error, showConfirm]);

  const sizeClasses = size === 'sm' ? 'px-2 py-1 text-xs gap-1' : 'px-3 py-1.5 text-sm gap-1.5';

  const variantClasses = {
    primary: 'bg-indigo-50 text-indigo-700 hover:bg-indigo-100 dark:bg-indigo-900/30 dark:text-indigo-300 dark:hover:bg-indigo-900/50',
    secondary: 'bg-gray-50 text-gray-700 hover:bg-gray-100 dark:bg-gray-700/50 dark:text-gray-300 dark:hover:bg-gray-700',
    danger: 'bg-red-50 text-red-700 hover:bg-red-100 dark:bg-red-900/30 dark:text-red-300 dark:hover:bg-red-900/50',
  };

  // 위험 액션 확인 UI
  if (showConfirm) {
    return (
      <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
        <span className="text-xs text-yellow-600 dark:text-yellow-400 max-w-[200px]">
          {costEstimate ? `정말 실행? (${costEstimate})` : '정말 실행하시겠습니까?'}
        </span>
        <button
          onClick={handleConfirm}
          className="px-2 py-0.5 text-xs rounded bg-red-100 text-red-700 hover:bg-red-200 dark:bg-red-900/30 dark:text-red-300"
        >
          확인
        </button>
        <button
          onClick={handleCancel}
          className="px-2 py-0.5 text-xs rounded bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-400"
        >
          취소
        </button>
      </div>
    );
  }

  // 상태별 렌더링
  if (state === 'dispatching' || state === 'polling') {
    return (
      <button
        disabled
        className={`inline-flex items-center rounded-md font-medium ${sizeClasses} bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400 cursor-not-allowed`}
        onClick={(e) => e.stopPropagation()}
      >
        <Loader2 className={`${size === 'sm' ? 'h-3 w-3' : 'h-4 w-4'} animate-spin`} />
        실행 중...
      </button>
    );
  }

  if (state === 'success') {
    return (
      <span
        className={`inline-flex items-center rounded-md font-medium ${sizeClasses} bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300`}
        onClick={(e) => e.stopPropagation()}
      >
        <CheckCircle className={`${size === 'sm' ? 'h-3 w-3' : 'h-4 w-4'}`} />
        완료
      </span>
    );
  }

  if (state === 'timeout') {
    return (
      <button
        onClick={handleClick}
        className={`inline-flex items-center rounded-md font-medium ${sizeClasses} bg-yellow-50 text-yellow-700 hover:bg-yellow-100 dark:bg-yellow-900/30 dark:text-yellow-300`}
        title="백그라운드에서 진행 중일 수 있습니다. 클릭하여 재확인."
      >
        <Clock className={`${size === 'sm' ? 'h-3 w-3' : 'h-4 w-4'}`} />
        진행 중 (확인)
      </button>
    );
  }

  if (state === 'failure') {
    return (
      <button
        onClick={handleClick}
        className={`inline-flex items-center rounded-md font-medium ${sizeClasses} bg-red-50 text-red-700 hover:bg-red-100 dark:bg-red-900/30 dark:text-red-300`}
        title={error || '실패'}
      >
        <XCircle className={`${size === 'sm' ? 'h-3 w-3' : 'h-4 w-4'}`} />
        실패
      </button>
    );
  }

  // 쿨다운 에러 표시
  if (error && error.startsWith('쿨다운')) {
    return (
      <span
        className={`inline-flex items-center rounded-md font-medium ${sizeClasses} text-yellow-600 dark:text-yellow-400`}
        onClick={(e) => e.stopPropagation()}
      >
        <AlertTriangle className={`${size === 'sm' ? 'h-3 w-3' : 'h-4 w-4'}`} />
        {error.replace('쿨다운 중: ', '')}
      </span>
    );
  }

  // idle 상태
  return (
    <button
      onClick={handleClick}
      className={`inline-flex items-center rounded-md font-medium transition-colors ${sizeClasses} ${variantClasses[variant]}`}
    >
      <Play className={`${size === 'sm' ? 'h-3 w-3' : 'h-4 w-4'}`} />
      {label}
    </button>
  );
}

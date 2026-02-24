'use client';

import { useState, useRef, useCallback, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { adminService } from '@/services/adminService';
import type { AdminTaskStatus } from '@/types/admin';

export type ActionState = 'idle' | 'dispatching' | 'polling' | 'success' | 'failure' | 'timeout';

const STORAGE_KEY = 'admin_active_tasks';

/** sessionStorage에 진행 중인 태스크 저장/조회/삭제 */
function getStoredTask(actionKey: string): string | null {
  if (typeof window === 'undefined') return null;
  try {
    const stored = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || '{}');
    return stored[actionKey] || null;
  } catch {
    return null;
  }
}

function storeTask(actionKey: string, taskId: string) {
  if (typeof window === 'undefined') return;
  try {
    const stored = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || '{}');
    stored[actionKey] = taskId;
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(stored));
  } catch { /* ignore */ }
}

function removeStoredTask(actionKey: string) {
  if (typeof window === 'undefined') return;
  try {
    const stored = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || '{}');
    delete stored[actionKey];
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(stored));
  } catch { /* ignore */ }
}

interface UseAdminActionReturn {
  execute: (action: string, params?: Record<string, any>, confirm?: boolean) => void;
  state: ActionState;
  taskId: string | null;
  taskStatus: AdminTaskStatus | null;
  error: string | null;
  costEstimate: string | null;
  reset: () => void;
}

export function useAdminAction(actionKey?: string): UseAdminActionReturn {
  const [state, setState] = useState<ActionState>('idle');
  const [taskId, setTaskId] = useState<string | null>(null);
  const [taskStatus, setTaskStatus] = useState<AdminTaskStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [costEstimate, setCostEstimate] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollCountRef = useRef(0);
  const actionKeyRef = useRef(actionKey);
  const queryClient = useQueryClient();

  const MAX_POLL_COUNT = 40; // 3초 * 40 = 120초 (2분) 타임아웃

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const cleanupTask = useCallback(() => {
    if (actionKeyRef.current) {
      removeStoredTask(actionKeyRef.current);
    }
  }, []);

  const reset = useCallback(() => {
    stopPolling();
    cleanupTask();
    setState('idle');
    setTaskId(null);
    setTaskStatus(null);
    setError(null);
    setCostEstimate(null);
  }, [stopPolling, cleanupTask]);

  const startPolling = useCallback((tid: string) => {
    stopPolling();
    setState('polling');
    pollCountRef.current = 0;

    intervalRef.current = setInterval(async () => {
      pollCountRef.current += 1;

      // 타임아웃: 최대 2분 — 태스크는 백그라운드에서 계속 진행 중일 수 있음
      if (pollCountRef.current > MAX_POLL_COUNT) {
        stopPolling();
        // 태스크 저장은 유지 (페이지 새로고침 시 재확인 가능)
        setState('timeout');
        setError('태스크가 아직 진행 중입니다. 잠시 후 페이지를 새로고침하세요.');
        queryClient.invalidateQueries({ queryKey: ['admin'] });
        return;
      }

      try {
        const status = await adminService.getTaskStatus(tid);
        setTaskStatus(status);

        if (status.status === 'SUCCESS') {
          stopPolling();
          cleanupTask();
          setState('success');
          queryClient.invalidateQueries({ queryKey: ['admin'] });
          setTimeout(() => {
            setState((prev) => (prev === 'success' ? 'idle' : prev));
            setTaskId(null);
            setTaskStatus(null);
          }, 3000);
        } else if (status.status === 'FAILURE') {
          stopPolling();
          cleanupTask();
          setState('failure');
          setError(status.traceback || '태스크 실행 실패');
        }
      } catch {
        // 폴링 에러는 무시 (다음 interval에 재시도)
      }
    }, 3000);
  }, [stopPolling, cleanupTask, queryClient]);

  const execute = useCallback(
    async (action: string, params?: Record<string, any>, confirm?: boolean) => {
      // actionKey가 지정 안 됐으면 action명을 사용
      actionKeyRef.current = actionKeyRef.current || action;
      setState('dispatching');
      setError(null);
      setCostEstimate(null);

      try {
        const resp = await adminService.executeAction({
          action,
          params,
          confirm,
        });

        if (resp.success && resp.data) {
          const tid = resp.data.task_id;
          setTaskId(tid);
          storeTask(actionKeyRef.current, tid);
          startPolling(tid);
        }
      } catch (err: any) {
        const respData = err?.response?.data;
        if (respData?.requires_confirm) {
          setState('idle');
          setError('REQUIRES_CONFIRM');
          setCostEstimate(respData.cost_estimate || null);
        } else if (err?.response?.status === 429) {
          setState('idle');
          const remaining = respData?.cooldown_remaining ?? 0;
          setError(`쿨다운 중: ${remaining}초 후 다시 시도`);
        } else {
          setState('failure');
          setError(respData?.error || '액션 실행 실패');
        }
      }
    },
    [startPolling],
  );

  // 마운트 시: sessionStorage에 저장된 진행 중 태스크가 있으면 폴링 재개
  useEffect(() => {
    const key = actionKeyRef.current;
    if (!key) return;

    const storedTaskId = getStoredTask(key);
    if (!storedTaskId) return;

    // 즉시 상태 확인 후 아직 진행 중이면 폴링 재개
    let cancelled = false;
    (async () => {
      try {
        const status = await adminService.getTaskStatus(storedTaskId);
        if (cancelled) return;

        if (status.status === 'SUCCESS') {
          removeStoredTask(key);
          setState('success');
          queryClient.invalidateQueries({ queryKey: ['admin'] });
          setTimeout(() => {
            setState((prev) => (prev === 'success' ? 'idle' : prev));
          }, 3000);
        } else if (status.status === 'FAILURE') {
          removeStoredTask(key);
          setState('failure');
          setError(status.traceback || '태스크 실행 실패');
        } else {
          // PENDING / STARTED → 폴링 재개
          setTaskId(storedTaskId);
          startPolling(storedTaskId);
        }
      } catch {
        // 상태 확인 실패 시 저장된 태스크 정리
        removeStoredTask(key);
      }
    })();

    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 언마운트 시 폴링 중지 (태스크 저장은 유지)
  useEffect(() => {
    return () => stopPolling();
  }, [stopPolling]);

  return { execute, state, taskId, taskStatus, error, costEstimate, reset };
}

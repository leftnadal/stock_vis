'use client';

import React, { useState } from 'react';
import { UserPlus, X } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import InterestSelector from './InterestSelector';

export default function OnboardingBanner() {
  const { isAuthenticated } = useAuth();
  const [dismissed, setDismissed] = useState(false);
  const [showSelector, setShowSelector] = useState(false);

  // 로그인한 사용자에게만 표시
  if (!isAuthenticated || dismissed) return null;

  return (
    <div className="bg-gradient-to-r from-purple-50 to-indigo-50 dark:from-purple-900/10 dark:to-indigo-900/10 border border-purple-200 dark:border-purple-800 rounded-xl overflow-hidden">
      <div className="px-4 py-3">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <UserPlus className="w-4 h-4 text-purple-600 dark:text-purple-400" />
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
              관심 테마를 선택하면 맞춤 뉴스를 받을 수 있어요
            </h3>
          </div>
          <button
            onClick={() => setDismissed(true)}
            className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
            aria-label="닫기"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {!showSelector ? (
          <button
            onClick={() => setShowSelector(true)}
            className="text-xs text-purple-600 dark:text-purple-400 hover:text-purple-700 dark:hover:text-purple-300 font-medium"
          >
            관심사 선택하기 →
          </button>
        ) : (
          <InterestSelector onComplete={() => setDismissed(true)} />
        )}
      </div>
    </div>
  );
}

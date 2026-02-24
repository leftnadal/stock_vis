'use client';

import { useState } from 'react';
import { Shield, Lock } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { AuthGuard } from '@/components/auth/AuthGuard';
import AdminTabNav from '@/components/admin/AdminTabNav';
import OverviewTab from '@/components/admin/OverviewTab';
import StocksTab from '@/components/admin/StocksTab';
import ScreenerTab from '@/components/admin/ScreenerTab';
import MarketPulseTab from '@/components/admin/MarketPulseTab';
import NewsTab from '@/components/admin/NewsTab';
import SystemTab from '@/components/admin/SystemTab';
import type { AdminTab } from '@/types/admin';

function AdminContent() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<AdminTab>('overview');

  if (!user?.is_staff) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="text-center">
          <Lock className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-gray-700 dark:text-gray-300 mb-2">
            관리자 권한이 필요합니다
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            이 페이지는 관리자(is_staff) 계정으로만 접근할 수 있습니다.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-[#0D1117]">
      <div className="mx-auto max-w-7xl px-4 py-6">
        {/* Header */}
        <header className="mb-6">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600">
              <Shield className="h-5 w-5 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                Admin Dashboard
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                시스템 상태 모니터링 및 데이터 관리
              </p>
            </div>
          </div>
        </header>

        {/* Tab Navigation */}
        <AdminTabNav activeTab={activeTab} onTabChange={setActiveTab} />

        {/* Tab Content */}
        <div className="mt-6">
          {activeTab === 'overview' && <OverviewTab />}
          {activeTab === 'stocks' && <StocksTab />}
          {activeTab === 'screener' && <ScreenerTab />}
          {activeTab === 'market-pulse' && <MarketPulseTab />}
          {activeTab === 'news' && <NewsTab />}
          {activeTab === 'system' && <SystemTab />}
        </div>
      </div>
    </div>
  );
}

export default function AdminPage() {
  return (
    <AuthGuard>
      <AdminContent />
    </AuthGuard>
  );
}

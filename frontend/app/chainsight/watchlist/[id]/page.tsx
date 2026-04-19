'use client';

import { use } from 'react';
import { usePathDetail } from '@/hooks/usePathWatchlist';
import FullPathView from '@/components/chainsight/FullPathView';

export default function FullPathPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data: path, isLoading, error } = usePathDetail(id);

  if (isLoading) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-16 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
      </div>
    );
  }

  if (error || !path) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-16 text-center">
        <p className="text-gray-500">경로를 찾을 수 없습니다.</p>
      </div>
    );
  }

  return <FullPathView path={path} />;
}

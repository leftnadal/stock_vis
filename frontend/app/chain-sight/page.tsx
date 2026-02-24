'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';

/**
 * Chain Sight 관리 페이지 → /admin 리다이렉트
 *
 * 기존 Chain Sight Explorer는 /stocks/[symbol] 페이지에서 사용되므로 영향 없음.
 */
export default function ChainSightPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/admin');
  }, [router]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-[#0D1117]">
      <div className="flex flex-col items-center gap-4">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
        <p className="text-sm text-gray-500 dark:text-gray-400">
          관리자 대시보드로 이동 중...
        </p>
      </div>
    </div>
  );
}

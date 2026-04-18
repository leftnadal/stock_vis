'use client';

import { useState } from 'react';
import { Pin, PinOff } from 'lucide-react';
import { toast } from 'sonner';
import { useRouter } from 'next/navigation';
import { useWatchPath } from '@/hooks/usePathWatchlist';
import { useExplorationStore } from '@/lib/stores/explorationStore';

export default function WatchButton() {
  const router = useRouter();
  const { trail } = useExplorationStore();
  const watchMutation = useWatchPath();
  const [isWatched, setIsWatched] = useState(false);

  const stockNodes = trail.filter((n) => n.type === 'stock').map((n) => n.symbol);
  const canWatch = stockNodes.length >= 2 && !isWatched;

  const handleWatch = () => {
    if (!canWatch) return;
    watchMutation.mutate(
      {
        path_nodes: stockNodes,
        source_center: stockNodes[0],
        source_slot: 'exploration_trail',
      },
      {
        onSuccess: () => {
          setIsWatched(true);
          toast.success('경로가 저장되었습니다', {
            action: {
              label: 'Watchlist 열기',
              onClick: () => router.push('/chainsight/watchlist'),
            },
          });
        },
      },
    );
  };

  if (stockNodes.length < 2) return null;

  return (
    <button
      onClick={handleWatch}
      disabled={isWatched || watchMutation.isPending}
      className={`
        flex items-center gap-1 px-3 py-1.5 rounded-full text-xs font-medium
        transition-all duration-200 flex-shrink-0
        ${isWatched
          ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 cursor-default'
          : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-blue-50 dark:hover:bg-blue-900/20 hover:text-blue-600'
        }
        ${watchMutation.isPending ? 'opacity-50 cursor-wait' : ''}
      `}
      title={isWatched ? '이미 저장된 경로' : '경로 저장'}
    >
      {isWatched ? (
        <><Pin className="w-3.5 h-3.5 fill-current" /><span>Watching</span></>
      ) : (
        <><PinOff className="w-3.5 h-3.5" /><span>Watch</span></>
      )}
    </button>
  );
}

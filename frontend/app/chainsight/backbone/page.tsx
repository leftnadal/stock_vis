'use client';

/**
 * RC-C-1 /chainsight/backbone — 관계 백본 뷰(신규 라우트, additive).
 * AuthGuard(백엔드 IsAuthenticated 정합) + ForceGraph2D dynamic ssr:false.
 */

import dynamic from 'next/dynamic';
import { AuthGuard } from '@/components/auth/AuthGuard';
import BackboneView from '@/components/chainsight/BackboneView';

const ForceGraph2D = dynamic(() => import('react-force-graph-2d'), { ssr: false });

export default function BackbonePage() {
  return (
    <AuthGuard>
      <div className="max-w-7xl mx-auto">
        <BackboneView ForceGraph2D={ForceGraph2D as unknown as React.ComponentType<Record<string, unknown>>} />
      </div>
    </AuthGuard>
  );
}

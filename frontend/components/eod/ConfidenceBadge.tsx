'use client';

import { CONFIDENCE_DOT } from './colorSemantics';

interface ConfidenceBadgeProps {
  score: number;
}

export function ConfidenceBadge({ score }: ConfidenceBadgeProps) {
  // 한국축(D-COLOR-SYSTEM): 매수측 rose / 중립 gray / 약세측 sky. 라벨 병기(색 보조).
  const getDotConfig = (score: number): { dots: number; color: string; label: string } => {
    if (score > 0.6) return { dots: 5, color: CONFIDENCE_DOT.buyStrong, label: '강력 매수' };
    if (score > 0.3) return { dots: 4, color: CONFIDENCE_DOT.buy, label: '매수' };
    if (score > 0) return { dots: 3, color: CONFIDENCE_DOT.neutral, label: '중립' };
    if (score > -0.3) return { dots: 2, color: CONFIDENCE_DOT.sell, label: '약세' };
    return { dots: 1, color: CONFIDENCE_DOT.sellStrong, label: '강한 약세' };
  };

  const { dots, color, label } = getDotConfig(score);

  return (
    <div className="flex items-center gap-1" title={`종합점수: ${score.toFixed(2)} (${label})`}>
      {Array.from({ length: 5 }).map((_, i) => (
        <span
          key={i}
          className={`inline-block w-2 h-2 rounded-full ${
            i < dots ? color : 'bg-gray-200 dark:bg-gray-600'
          }`}
        />
      ))}
      <span className="text-[10px] text-gray-400 dark:text-gray-500 ml-0.5">{label}</span>
    </div>
  );
}

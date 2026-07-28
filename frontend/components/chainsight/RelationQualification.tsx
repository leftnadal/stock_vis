'use client';

/**
 * 관계 정성화 표시 (⑳-3 S2 C) — 칩 분화 + 등급 라벨 + 근거 문장 + 도메인 태그.
 *
 * ego 엣지 하나를 받아 "왜 이 관계인가"를 정직하게 표면화한다.
 *  - C-1 칩: qualificationChips (PEER 분화 / 뉴스 N회 / 유형 라벨)
 *  - C-3 등급: gradeLine (확인됨/추정 + truth_score)
 *  - C-2 근거: SEC 4종 + CO_MENTIONED만 basis_summary(출처 내장) 노출, PEER는 문장 없음
 *  - C-4 도메인: relation_domain 있으면 검은 태그(S2-B 전엔 null → 미표시)
 */

import type { EgoEdge } from '@/types/chainsight';
import {
  qualificationChips,
  gradeLine,
  showsBasis,
  gradeBadge,
} from './cardListConfig';

interface RelationQualificationProps {
  edge: EgoEdge;
  /** compact=true: 칩만(미니뷰 공간 제약). false: 칩+등급+근거+도메인 전체. */
  compact?: boolean;
}

export default function RelationQualification({ edge, compact = false }: RelationQualificationProps) {
  const chips = qualificationChips(edge);
  const grade = gradeLine(edge);
  const badge = gradeBadge(edge.grade, edge.grade_source);

  return (
    <div className="space-y-1.5">
      {/* C-1 칩 분화 */}
      <div className="flex flex-wrap gap-1">
        {chips.map((c) => (
          <span
            key={c}
            className="inline-block px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-700"
          >
            {c}
          </span>
        ))}
        {/* C-4 도메인 태그(있을 때만) */}
        {edge.relation_domain && (
          <span className="inline-block px-2 py-0.5 text-xs rounded-full bg-gray-800 text-white">
            {edge.relation_domain}
          </span>
        )}
      </div>

      {!compact && (
        <>
          {/* C-3 등급 라벨(status + truth_score) + 소스 병기 배지 */}
          {grade && (
            <div className="flex items-center gap-1.5 text-xs">
              <span className="font-medium" style={{ color: badge.color }}>
                {grade}
              </span>
              <span className="text-gray-400">·</span>
              <span className="text-gray-500">{badge.label}</span>
            </div>
          )}

          {/* C-2 근거 문장(SEC 4종 + CO_MENTIONED, 출처 내장) */}
          {showsBasis(edge) && (
            <p className="text-[11px] leading-snug text-gray-500 border-l-2 border-gray-200 pl-2">
              {edge.basis_summary}
            </p>
          )}
        </>
      )}
    </div>
  );
}

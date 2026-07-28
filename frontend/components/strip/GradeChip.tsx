// 등급 칩 1장 — grade 도트 + 라벨 + 값 + 보조(z) + 스파크라인. [D-COLOR-TOKEN grade 축]
// 제네릭(grade/label/value/sub/spark) — credit_signals 스트립 + TH 히트 밴드 재사용 전제.
// 색은 colorSemantics grade 토큰만 소비(로컬 색 정의 금지). gray는 저채도로 눌러 비-gray 부상.
// 툴팁 본문은 칩이 아니라 스트립 하단 리드아웃이 표시(수평 스크롤 클리핑 회피) → 칩은 활성 콜백만.
import {
  GRADE_CHIP,
  GRADE_DOT_HEX,
  GRADE_SPARK_FILL,
  type Grade,
} from '@/components/common/colorSemantics';
import { MiniSparkline } from '@/components/eod/MiniSparkline';

interface GradeChipProps {
  grade: Grade;
  label: string;
  value: string;
  /** 보조 표기(예: "z +0.40") — 색 단독 인코딩 금지 원칙상 값/부호 병기. */
  sub?: string;
  /** 스파크라인 값 배열. 2개 미만이면 스파크 생략(칩은 값만으로 렌더). */
  spark?: number[];
  /** hover/포커스 시 활성(스트립 리드아웃 갱신). 지정 시 칩이 focusable. */
  onActivate?: () => void;
  /** 활성(리드아웃이 이 칩을 표시 중) — 강조 링. */
  active?: boolean;
}

export function GradeChip({
  grade,
  label,
  value,
  sub,
  spark,
  onActivate,
  active,
}: GradeChipProps) {
  const tone = GRADE_CHIP[grade] ?? GRADE_CHIP.gray;
  const dot = GRADE_DOT_HEX[grade] ?? GRADE_DOT_HEX.gray;
  const hasSpark = Array.isArray(spark) && spark.length >= 2;

  return (
    <div
      role="listitem"
      data-testid="grade-chip"
      data-grade={grade}
      data-active={active ? 'true' : undefined}
      className={`flex-shrink-0 w-40 snap-start rounded-lg border p-2.5 shadow-sm ${tone} ${
        active ? 'ring-2 ring-gray-300 dark:ring-gray-500' : ''
      } ${onActivate ? 'cursor-pointer' : ''}`}
      tabIndex={onActivate ? 0 : undefined}
      onMouseEnter={onActivate}
      onFocus={onActivate}
    >
      <div className="flex items-center gap-1.5">
        <span
          data-testid="grade-dot"
          className="inline-block h-2 w-2 rounded-full"
          style={{ backgroundColor: dot }}
        />
        <span className="truncate text-xs font-medium">{label}</span>
      </div>

      <div className="mt-1 flex items-baseline gap-1.5">
        <span className="text-sm font-semibold tabular-nums">{value}</span>
        {sub && <span className="text-[11px] tabular-nums opacity-70">{sub}</span>}
      </div>

      {hasSpark && (
        <div className="mt-1.5">
          <MiniSparkline
            data={spark as number[]}
            width={140}
            height={22}
            stroke={dot}
            fill={GRADE_SPARK_FILL[grade] ?? GRADE_SPARK_FILL.gray}
          />
        </div>
      )}
    </div>
  );
}

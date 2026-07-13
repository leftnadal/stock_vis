// 등급 칩 1장 — grade 도트 + 라벨 + 값 + 보조(z) + 스파크라인 (+ 선택적 툴팁). [D-COLOR-TOKEN grade 축]
// 제네릭(grade/label/value/sub/spark/info) — credit_signals 스트립 + TH 히트 밴드 재사용 전제.
// 색은 colorSemantics grade 토큰만 소비(로컬 색 정의 금지). gray는 저채도로 눌러 비-gray 부상.
import {
  GRADE_CHIP,
  GRADE_DOT_HEX,
  GRADE_SPARK_FILL,
  type Grade,
} from '@/components/common/colorSemantics';
import { MiniSparkline } from '@/components/eod/MiniSparkline';

/** 툴팁 콘텐츠(정의·현재 상태·밴드 기준). 있으면 hover/포커스 시 표기. */
export interface GradeChipInfo {
  def: string;
  state: string;
  band: string;
}

interface GradeChipProps {
  grade: Grade;
  label: string;
  value: string;
  /** 보조 표기(예: "z +0.40") — 색 단독 인코딩 금지 원칙상 값/부호 병기. */
  sub?: string;
  /** 스파크라인 값 배열. 2개 미만이면 스파크 생략(칩은 값만으로 렌더). */
  spark?: number[];
  /** 툴팁(hover/탭). 지정 시 칩이 focusable + 팝오버 표기. */
  info?: GradeChipInfo;
}

export function GradeChip({ grade, label, value, sub, spark, info }: GradeChipProps) {
  const tone = GRADE_CHIP[grade] ?? GRADE_CHIP.gray;
  const dot = GRADE_DOT_HEX[grade] ?? GRADE_DOT_HEX.gray;
  const hasSpark = Array.isArray(spark) && spark.length >= 2;

  return (
    <div
      role="listitem"
      data-testid="grade-chip"
      data-grade={grade}
      // info 있으면 hover(group-hover)·탭/키보드(focus-within) 팝오버 노출 위해 group·relative.
      className={`group relative flex-shrink-0 w-40 snap-start rounded-lg border p-2.5 shadow-sm ${tone}`}
      tabIndex={info ? 0 : undefined}
      aria-label={info ? `${label} — ${info.state}` : undefined}
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

      {info && (
        <div
          role="tooltip"
          data-testid="grade-tooltip"
          className="pointer-events-none absolute left-0 top-full z-20 mt-1 hidden w-56 rounded-md border border-gray-200 bg-white p-2.5 text-left shadow-lg group-hover:block group-focus-within:block dark:border-gray-700 dark:bg-gray-800"
        >
          <p className="text-xs font-medium text-gray-900 dark:text-gray-100">{label}</p>
          <p className="mt-1 text-[11px] leading-snug text-gray-600 dark:text-gray-300">
            {info.def}
          </p>
          <p className="mt-1.5 text-[11px] tabular-nums text-gray-800 dark:text-gray-200">
            {info.state}
          </p>
          <p className="mt-1.5 border-t border-gray-100 pt-1 text-[10px] text-gray-400 dark:border-gray-700 dark:text-gray-500">
            {info.band}
          </p>
        </div>
      )}
    </div>
  );
}

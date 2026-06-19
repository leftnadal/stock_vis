interface Props {
  score: number;
  /** 그룹 내 최저 관심도(페이지 정규화 하한) */
  groupMin: number;
  /** 그룹 내 최고 관심도(페이지 정규화 상한) */
  groupMax: number;
}

// 페이지 내 정규화 하한: 최저 종목도 흔적(=standing 있음)이 보이도록.
const FLOOR = 0.1;

/**
 * 관심도 standing 바 (CS-RD3 QA, C3 — M2 미니바와 구분된 처리).
 *
 * - 관심도는 "순위 그 자체"라 그룹 내 상대 standing을 가로 바로 표시.
 * - 채움 = 그룹 내 min-max 정규화(score - min)/(max - min) → [FLOOR, 1].
 *   고정 0~100 도메인 대신 그룹 정규화로 순위 낙차를 시각화(분포 실측 근거,
 *   2026-06-15 전체 14.8~100/med 50 → 그룹 내 스프레드 충분).
 *   숫자(절대 점수)는 옆에 그대로 노출되므로 바는 standing 전용.
 * - M2 미니바(우측 컬럼, teal/coral/blue 채움 + 회색 트랙)와 구분:
 *   indigo 채움 + slate 트랙 + 더 둥근 모서리, 점수 숫자 바로 아래(좌측 컬럼).
 */
export default function AttentionStandingBar({ score, groupMin, groupMax }: Props) {
  const range = groupMax - groupMin;
  // 단일 종목/동점 그룹(range=0) → 비교 대상 없음 → full.
  const ratio = range > 0 ? (score - groupMin) / range : 1;
  const widthPct = (FLOOR + (1 - FLOOR) * Math.min(Math.max(ratio, 0), 1)) * 100;

  return (
    <div
      className="w-full h-1.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden mt-1"
      role="presentation"
    >
      <div
        className="h-full rounded-full bg-indigo-400 dark:bg-indigo-500"
        style={{ width: `${widthPct}%` }}
      />
    </div>
  );
}

interface Props {
  score: number;
}

// 0점 가시성 하한: 최저 종목도 흔적(=바 있음)이 보이도록.
// 실측 min 12.9라 거의 안 걸리지만 0 근처 방어용으로 유지.
const FLOOR = 0.1;

/**
 * 관심도 standing 바 (CS-RD3 QA Slice 2-B — 전역 0~100 절대 도메인).
 *
 * - 채움 = score를 그룹과 무관하게 0~100에 직접 매핑 → [FLOOR, 1].
 *   widthPct = (FLOOR + (1-FLOOR)·clamp(score/100, 0, 1)) · 100.
 * - 의미 = "시장 전체 대비 관심도 절대 수준"(그룹 내 순위 아님).
 *   그룹 내 순위는 정렬·번호·절대 숫자가 전달한다.
 * - 그룹 min-max 정규화 폐기(2026-06-22 N=499 측정): 소규모·저분산 그룹 과장
 *   (2.1점 차가 10%↔100%, 거짓 신호) + 그룹 간 비교 불가(모든 그룹 최하위 10%) 해소.
 *   이제 같은 점수 = 항상 같은 바 폭 → 그룹 간 비교 가능.
 * - M2 미니바(우측 컬럼, teal/coral/blue 채움 + 회색 트랙)와 구분:
 *   indigo 채움 + slate 트랙 + 더 둥근 모서리, 점수 숫자 바로 아래(좌측 컬럼).
 */
export default function AttentionStandingBar({ score }: Props) {
  const ratio = Math.min(Math.max(score / 100, 0), 1);
  const widthPct = (FLOOR + (1 - FLOOR) * ratio) * 100;

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

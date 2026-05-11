/**
 * radialLayout.ts — 시멘틱 방사형 좌표 계산 유틸리티
 *
 * 명세 §1-2, §1-3, §1-6 구현
 *
 * 각도-관계 매핑 (시계 방향, CSS/Canvas 좌표계 기준):
 *   - SUPPLIES_TO        → 12시 (-90°, 위)
 *   - CUSTOMER_OF        → 3시  (  0°, 오른쪽)
 *   - PEER_OF            → 3시  (  0°, 오른쪽) — CUSTOMER_OF와 같은 구간
 *   - COMPETES_WITH      → 9시  (180°, 왼쪽)
 *   - HAS_THEME          → 9시  (180°, 왼쪽) — COMPETES_WITH와 같은 구간
 *   - CO_MENTIONED       → 6시  ( 90°, 아래)
 *   - PRICE_CORRELATED   → 6시  ( 90°, 아래) — CO_MENTIONED와 같은 구간
 *
 * 주의: CSS/Canvas 좌표계는 Y축이 반전되어 있으므로
 *   - 12시 = angle -90°(Math.PI * -0.5) = (0, -R) — 화면 위
 *   -  3시 = angle   0°                 = (R,  0) — 화면 오른쪽
 *   -  6시 = angle  90°(Math.PI * 0.5)  = (0,  R) — 화면 아래
 *   -  9시 = angle 180°(Math.PI)        = (-R, 0) — 화면 왼쪽
 *
 * 명세 §1-6 의사코드의 baseAngle 약속:
 *   - 12시 = -90 (명세 표기)  → JS에서는 -Math.PI/2 (동일)
 *   -  3시 =   0             → JS에서는 0
 *   -  6시 =  90             → JS에서는 Math.PI/2
 *   -  9시 = 180             → JS에서는 Math.PI
 */

/** 방사형 배치에 사용할 관계 타입 목록 */
export type RadialRelType =
  | 'SUPPLIES_TO'
  | 'CUSTOMER_OF'
  | 'PEER_OF'
  | 'COMPETES_WITH'
  | 'HAS_THEME'
  | 'CO_MENTIONED'
  | 'PRICE_CORRELATED';

/** computeRadialPositions에 전달할 이웃 정보 */
export interface RadialNeighbor {
  symbol: string;
  relType: string;
  /** 깊이 — 1: Ring1(160px), 2: Ring2(280px). undefined이면 1로 간주 */
  depth?: number;
}

/** 계산된 fx/fy (d3 고정 좌표) */
export interface RadialPosition {
  fx: number;
  fy: number;
}

/** 반경 설정 */
export interface RadialConfig {
  /** Ring 1 반경 (1차 이웃, 기본 160) */
  ring1Radius: number;
  /** Ring 2 반경 (2차 이웃, 기본 280) */
  ring2Radius: number;
}

const DEFAULT_CONFIG: RadialConfig = {
  ring1Radius: 160,
  ring2Radius: 280,
};

/**
 * 명세 §1-6 ANGLE_MAP
 * baseAngle: 도(°) 단위, Math.PI/180 변환 후 사용
 * spread: 구간 너비(°) — 같은 타입 노드가 여러 개면 이 구간 안에서 균등 분포
 */
const ANGLE_MAP: Record<
  string,
  { baseAngle: number; spread: number }
> = {
  SUPPLIES_TO:      { baseAngle: -90, spread: 90 },  // 12시 ± 45°
  CUSTOMER_OF:      { baseAngle:   0, spread: 90 },  // 3시 ± 45°
  PEER_OF:          { baseAngle:   0, spread: 90 },  // 3시 ± 45° (CUSTOMER_OF와 공유)
  COMPETES_WITH:    { baseAngle: 180, spread: 90 },  // 9시 ± 45°
  HAS_THEME:        { baseAngle: 180, spread: 90 },  // 9시 ± 45° (COMPETES_WITH와 공유)
  CO_MENTIONED:     { baseAngle:  90, spread: 90 },  // 6시 ± 45°
  PRICE_CORRELATED: { baseAngle:  90, spread: 90 },  // 6시 ± 45° (CO_MENTIONED와 공유)
};

/**
 * 같은 각도 구간을 공유하는 관계 타입 그룹.
 * 복수 타입이 동일 baseAngle을 쓸 때 충돌을 방지하기 위해
 * 그룹 전체를 함께 균등 배치한다.
 *
 * 예: COMPETES_WITH 2개 + HAS_THEME 1개가 있으면
 *   9시 구간(180° ± 45°)에서 총 3개를 균등 분포.
 */
const ANGLE_GROUP: Record<string, string> = {
  SUPPLIES_TO:      'group_12',  // 12시 구간
  CUSTOMER_OF:      'group_3',   // 3시 구간
  PEER_OF:          'group_3',
  COMPETES_WITH:    'group_9',   // 9시 구간
  HAS_THEME:        'group_9',
  CO_MENTIONED:     'group_6',   // 6시 구간
  PRICE_CORRELATED: 'group_6',
};

/** 그룹 ID → 해당 구간의 baseAngle 도(°) */
const GROUP_BASE_ANGLE: Record<string, number> = {
  group_12: -90,
  group_3:    0,
  group_6:   90,
  group_9:  180,
};

/** 각 구간의 spread 도(°) */
const GROUP_SPREAD = 90;

/**
 * computeRadialPositions
 *
 * 순수 함수 — 사이드 이펙트 없음, 테스트 가능.
 *
 * @param centerSymbol - center 노드 심볼 (center는 항상 fx=0, fy=0)
 * @param neighbors    - 이웃 노드 목록 (relType, depth 포함)
 * @param config       - 반경 설정 (ring1Radius, ring2Radius)
 * @returns symbol → {fx, fy} 맵
 */
export function computeRadialPositions(
  centerSymbol: string,
  neighbors: RadialNeighbor[],
  config: Partial<RadialConfig> = {},
): Map<string, RadialPosition> {
  const { ring1Radius, ring2Radius } = { ...DEFAULT_CONFIG, ...config };
  const positions = new Map<string, RadialPosition>();

  // center 노드는 항상 원점
  positions.set(centerSymbol, { fx: 0, fy: 0 });

  // 관계 타입을 알 수 없는 노드 — ANGLE_MAP에 없으면 6시로 fallback
  const FALLBACK_KEY = 'CO_MENTIONED';

  // ── 그룹별로 이웃 노드를 묶어 균등 배치 ──
  // Map<groupId, Array<{symbol, relType, depth}>>
  const groups = new Map<string, RadialNeighbor[]>();

  for (const neighbor of neighbors) {
    const key = ANGLE_GROUP[neighbor.relType] ?? ANGLE_GROUP[FALLBACK_KEY];
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(neighbor);
  }

  for (const [groupId, groupMembers] of groups) {
    const baseAngle = GROUP_BASE_ANGLE[groupId] ?? 90; // fallback: 6시
    const total = groupMembers.length;

    for (let i = 0; i < total; i++) {
      const neighbor = groupMembers[i];
      const depth = neighbor.depth ?? 1;
      const radius = depth === 2 ? ring2Radius : ring1Radius;

      // 명세 §1-6 의사코드 그대로:
      //   step  = total > 1 ? spread / (total - 1) : 0
      //   angle = (baseAngle - spread/2 + step * i) * (Math.PI / 180)
      const step = total > 1 ? GROUP_SPREAD / (total - 1) : 0;
      const angleDeg = baseAngle - GROUP_SPREAD / 2 + step * i;
      const angleRad = angleDeg * (Math.PI / 180);

      const fx = radius * Math.cos(angleRad);
      const fy = radius * Math.sin(angleRad);

      positions.set(neighbor.symbol, { fx, fy });
    }
  }

  return positions;
}

/**
 * inferNeighborDepth
 *
 * API의 Neighbor 타입에 depth 필드가 없으므로 cross_edges에서 2차 이웃을 추론.
 *
 * @param neighborSymbols - 1차 이웃 심볼 집합
 * @param centerSymbol    - center 심볼
 * @param crossEdgePairs  - cross_edges의 {source, target} 쌍
 * @returns 2차 이웃으로 추론된 심볼 집합
 */
export function inferSecondaryNeighbors(
  neighborSymbols: Set<string>,
  centerSymbol: string,
  crossEdgePairs: Array<{ source: string; target: string }>,
): Set<string> {
  const secondaries = new Set<string>();
  for (const { source, target } of crossEdgePairs) {
    if (source !== centerSymbol && !neighborSymbols.has(source)) {
      secondaries.add(source);
    }
    if (target !== centerSymbol && !neighborSymbols.has(target)) {
      secondaries.add(target);
    }
  }
  return secondaries;
}

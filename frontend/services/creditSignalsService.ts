// 크레딧 신호 스트립 서비스 — /api/credit-signals/strip/ 소비 (read-only, CS-CREDIT-CONSUME).
// 엔드포인트가 /api/credit-signals/(v1 아님)라 authAxios base(/api/v1)를 벗어나므로
// 절대 URL로 호출(authAxios 인터셉터의 JWT는 그대로 유지). stripService 패턴 동형.
import { authAxios } from '@/lib/api/authAxios';
import type { Grade } from '@/components/common/colorSemantics';

export interface CreditSparkPoint {
  date: string;
  value: number;
}

export interface CreditSignal {
  key: string; // 예: "HY_OAS" (Thesis Layer E 안정 계약)
  name: string; // 예: "US HY OAS"
  value: number;
  z: number | null; // 콜드스타트 시 null
  grade: Grade;
  spark: CreditSparkPoint[]; // 최근 30 관측치
}

export interface CreditStripResponse {
  as_of: string | null;
  signals: CreditSignal[];
}

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
// base의 /api/v1 접미를 벗겨 origin 도출 → /api/credit-signals/ 절대경로.
const ORIGIN = API_BASE.replace(/\/api\/v1\/?$/, '');

export const creditSignalsService = {
  async getCreditStrip(): Promise<CreditStripResponse> {
    const { data } = await authAxios.get<CreditStripResponse>(
      `${ORIGIN}/api/credit-signals/strip/`,
    );
    return data;
  },
};

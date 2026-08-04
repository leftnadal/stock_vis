import { useImpressionTracker } from '@/hooks/useImpressionTracker'
import type { CoverageResponse, CoverageUnexposedItem } from '@/types/coverage'

/**
 * 상세 페이지 impression surface (COVERAGE-DETAIL-FE).
 * 백엔드 `ImpressionLog.SURFACE_COVERAGE_DETAIL`('coverage_detail', migrate 0011)과 정합.
 * 유기 노출(dashboard_eod)과 분리 기록 → 커버리지 계산에서 제외(D-P2-COVERAGE-SURFACE).
 * dashboard 구획 단일 출처(공용 hooks/impressionTelemetry.ts 미접촉).
 */
const SURFACE_COVERAGE_DETAIL = 'coverage_detail'

function formatRate(rate: number): string {
  return `${Math.round(rate * 100)}%`
}

/**
 * 커버리지 상세 표시 (P2-COVERAGE-C1-FE, T2) — 순수 프레젠테이션(props 기반).
 *
 * summary 카드 + 미노출 리스트(ticker · signal_tag · signal_date · 경과일).
 * 정렬·상한은 API 응답 그대로(FE 재정렬 금지 — 단일 출처).
 * meta.join_misses > 0 이면 각주 1줄. C-2 퍼널 영역은 만들지 않는다(빈 껍데기 금지).
 * impression 추적: 각 미노출 행 단위로 surface='coverage_detail' 발신(COVERAGE-DETAIL-FE,
 * surface 등재·migrate 0011 완료). C-2가 "어떤 종목이 상세에서 노출됐나"를 쓸 수 있게 행 그레인 유지.
 */
export function CoverageDetailView({ data }: { data: CoverageResponse }) {
  const { window, summary, unexposed, meta } = data

  return (
    <div data-testid="coverage-detail">
      <div className="mb-4 text-sm text-gray-500">
        발급 창 {window.from} ~ {window.to} ({window.days}일)
      </div>

      {/* summary 카드 */}
      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <SummaryCard label="발급" value={summary.issued} />
        <SummaryCard label="노출" value={summary.exposed} />
        <SummaryCard label="노출율" value={formatRate(summary.exposure_rate)} />
        <SummaryCard label="미노출" value={summary.unexposed_count} />
      </div>

      {/* 미노출 리스트 */}
      <h2 className="mb-2 text-lg font-medium text-gray-900">미노출 발급</h2>
      {unexposed.length === 0 ? (
        <p className="text-sm text-gray-500">미노출 발급이 없습니다.</p>
      ) : (
        <ul data-testid="coverage-unexposed-list" className="divide-y divide-gray-200 rounded-lg bg-white shadow">
          {unexposed.map((item) => (
            <CoverageUnexposedRow key={item.object_ref} item={item} />
          ))}
        </ul>
      )}

      {meta.join_misses > 0 && (
        <p data-testid="coverage-join-misses" className="mt-3 text-xs text-gray-400">
          창밖 발급 노출 {meta.join_misses}건 제외
        </p>
      )}
    </div>
  )
}

/**
 * 미노출 발급 행 (COVERAGE-DETAIL-FE) — 행 단위 impression 추적.
 * 뷰포트 50%×1초(useImpressionTracker 내부 상수) 충족 시 surface='coverage_detail' 발신.
 * object_ref = API 제공값(SYMBOL:date:tag, dashboard_eod와 동일 그레인). fail-quiet(훅 자체 무해).
 */
function CoverageUnexposedRow({ item }: { item: CoverageUnexposedItem }) {
  const { ref } = useImpressionTracker<HTMLLIElement>(
    SURFACE_COVERAGE_DETAIL,
    item.object_ref
  )
  return (
    <li
      ref={ref}
      className="flex items-center justify-between px-4 py-3 text-sm"
    >
      <span className="font-medium text-gray-900">{item.ticker}</span>
      <span className="text-gray-500">{item.signal_tag}</span>
      <span className="text-gray-500">{item.signal_date}</span>
      <span className="text-gray-400">{item.days_since_issue}일 경과</span>
    </li>
  )
}

function SummaryCard({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-lg bg-white p-4 shadow">
      <div className="text-xs text-gray-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-gray-900">{value}</div>
    </div>
  )
}

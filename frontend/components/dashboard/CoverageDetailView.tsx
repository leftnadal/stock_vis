import { useImpressionTracker } from '@/hooks/useImpressionTracker'
import type { CoverageAudit, CoverageResponse, CoverageUnexposedItem } from '@/types/coverage'
import { SURFACES } from '@/constants/surfaces'

/**
 * 상세 페이지 impression surface (COVERAGE-DETAIL-FE).
 * 백엔드 `ImpressionLog.SURFACE_COVERAGE_DETAIL`(migrate 0011)과 정합.
 * 유기 노출(SURFACES.DASHBOARD_EOD)과 분리 기록 → 커버리지 계산에서 제외(D-P2-COVERAGE-SURFACE).
 * 값 단일 출처 = SURFACES(constants/surfaces.ts, 공용 인프라 — D-C2-S1-CONST-UNIFY ⓒ-3).
 */
const SURFACE_COVERAGE_DETAIL = SURFACES.COVERAGE_DETAIL

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
export function CoverageDetailView({
  data,
  w90JoinMisses,
  w90ImpUniq,
}: {
  data: CoverageResponse
  /** w90(90일 창) 미매칭 수 = 90일 밖 M. useCoverage(90) 응답의 meta.join_misses. 미확정(로딩/에러) 시 undefined. */
  w90JoinMisses?: number
  /** w90 기준 imp_uniq(= exposed + join_misses). 교차창 정합(항등식) 검증용. */
  w90ImpUniq?: number
}) {
  const { window, summary, unexposed, meta, audit } = data

  return (
    <div data-testid="coverage-detail">
      <div className="mb-4 text-sm text-gray-500">
        발급 창 {window.from} ~ {window.to} ({window.days}일)
      </div>

      {/* summary 카드 (본판정) */}
      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <SummaryCard label="발급" value={summary.issued} />
        <SummaryCard label="노출" value={summary.exposed} />
        <SummaryCard label="노출율" value={formatRate(summary.exposure_rate)} />
        <SummaryCard label="미노출" value={summary.unexposed_count} />
      </div>

      {/* 점검 층 — audit 존재 시만(구형 서빙 응답엔 생략, audit-absent 강건). */}
      {audit && <AuditLayer audit={audit} />}

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

      <OutOfWindowLabel
        outOfWindow={meta.join_misses}
        impUniqCurrent={summary.exposed + meta.join_misses}
        w90JoinMisses={w90JoinMisses}
        w90ImpUniq={w90ImpUniq}
      />
    </div>
  )
}

/**
 * 창밖 노출 라벨 (D-C2-S1-JOINMISS-LABEL, S1-B1).
 * N = 창밖 노출(= imp_uniq − 창 내 노출 = 현재 창 join_misses). M = w90 미매칭.
 * 상태 1(M=0): "창밖 노출 N · 90일 내 전량 매칭 ✓" / 상태 2(M>0): "창밖 노출 N · 90일 밖 M".
 * "전량 매칭"은 하드코드가 아니라 w90 실계산(M)으로 분기한다.
 * 항등식 imp_uniq = 노출 + N 은 단일 창에선 정의상 성립하나, 교차창(w90) imp_uniq 가
 * 어긋나면(수집 레이스·집계 버그) 라벨 대신 오류 표기 — 정합 검증이 이 라벨의 존재 이유.
 * NOTE: 표면 문자열 리터럴 정리는 S1-B2(D-C2-S1-CONST-UNIFY 상수 모듈+가드 테스트) 몫.
 */
export function OutOfWindowLabel({
  outOfWindow,
  impUniqCurrent,
  w90JoinMisses,
  w90ImpUniq,
}: {
  outOfWindow: number
  impUniqCurrent: number
  w90JoinMisses?: number
  w90ImpUniq?: number
}) {
  const identityViolated =
    w90ImpUniq !== undefined && w90ImpUniq !== impUniqCurrent
  if (identityViolated) {
    return (
      <p
        data-testid="coverage-join-misses-error"
        className="mt-3 text-xs font-medium text-red-600"
      >
        노출 집계 정합 오류 — imp_uniq {impUniqCurrent} ≠ 90일 기준 {w90ImpUniq}
      </p>
    )
  }
  if (outOfWindow <= 0) {
    return null
  }
  // M(90일 미매칭) 미확정(w90 로딩/에러) → N 만 표기(90일 판정 보류)
  if (w90JoinMisses === undefined) {
    return (
      <p data-testid="coverage-join-misses" className="mt-3 text-xs text-gray-400">
        창밖 노출 {outOfWindow}
      </p>
    )
  }
  const allMatched = w90JoinMisses === 0
  return (
    <p
      data-testid="coverage-join-misses"
      className={`mt-3 text-xs ${allMatched ? 'text-gray-400' : 'text-amber-600'}`}
    >
      {allMatched
        ? `창밖 노출 ${outOfWindow} · 90일 내 전량 매칭 ✓`
        : `창밖 노출 ${outOfWindow} · 90일 밖 ${w90JoinMisses}`}
    </p>
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
      <span className="flex items-center gap-2 font-medium text-gray-900">
        {item.ticker}
        {/* "점검됨" 배지 — audited true만. 항목·정렬·개수 무변(적체 비제거, 배지만). */}
        {item.audited === true && (
          <span
            data-testid="audited-badge"
            className="rounded bg-slate-100 px-1.5 py-0.5 text-xs font-normal text-slate-500"
          >
            점검됨
          </span>
        )}
      </span>
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

/**
 * 점검 층 (D-C2-S2-FUNNEL-COV 2계열 — audit) — 본판정(summary)과 시각 위계 분리.
 * 빗금(해칭) + 저채도 = 본선과 분리된 점검 계열임을 시각적으로 표기.
 * 창-불가지론: 응답 audit 블록을 그대로 렌더(수치 하드코딩 없음). 창이 며칠이든 응답값 표시.
 * 불변식(observed_uniq === overlap + audit_only_unexposed)은 BE 보장 — FE는 표시만.
 */
function AuditLayer({ audit }: { audit: CoverageAudit }) {
  return (
    <div
      data-testid="coverage-audit-layer"
      className="mb-6 rounded-lg border border-dashed border-slate-300 p-4"
      style={{
        backgroundImage:
          'repeating-linear-gradient(45deg, rgba(148,163,184,0.10) 0, rgba(148,163,184,0.10) 6px, transparent 6px, transparent 12px)',
      }}
    >
      <div className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-400">
        점검 층 · 본판정 제외
      </div>
      <div className="grid grid-cols-3 gap-3">
        <AuditStat label="점검 관측" value={audit.observed_uniq} />
        <AuditStat label="점검됨·미노출" value={audit.audit_only_unexposed} />
        <AuditStat label="노출·점검 중복" value={audit.overlap} />
      </div>
    </div>
  )
}

function AuditStat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="text-xs text-slate-400">{label}</div>
      <div className="mt-0.5 text-xl font-semibold text-slate-500">{value}</div>
    </div>
  )
}

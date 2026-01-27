/**
 * 공통 컴포넌트 Export
 * @description Stock 데이터 로딩/에러 상태 및 Corporate Action 표시를 위한 공통 컴포넌트
 */

// Data loading and error states
export { default as DataLoadingState } from './DataLoadingState';
export {
  StockHeaderSkeleton,
  ChartSkeleton,
  TableSkeleton,
} from './DataLoadingState';
export type {
  DataStatus,
  LoadingProgress,
  DataError,
} from './DataLoadingState';

// Data source badges
export { default as DataSourceBadge } from './DataSourceBadge';
export {
  DataSourceBadgeCompact,
  DataSourceWithTooltip,
} from './DataSourceBadge';
export type {
  DataSource,
  DataFreshness,
} from './DataSourceBadge';

// Corporate action badges
export {
  CorporateActionBadge,
  CorporateActionBadgeCompact,
  CorporateActionIcon,
  ACTION_CONFIG,
} from './CorporateActionBadge';
export type {
  ActionType,
  CorporateActionBadgeProps,
} from './CorporateActionBadge';

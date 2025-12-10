/**
 * Watchlist 관련 메시지 상수
 * i18n 준비를 위해 모든 하드코딩 문자열을 중앙 집중화
 */

export const WATCHLIST_MESSAGES = {
  // 성공 메시지
  SUCCESS: {
    ADD_STOCK: '종목이 추가되었습니다.',
    REMOVE_STOCK: '종목이 삭제되었습니다.',
    UPDATE_STOCK: '종목 설정이 수정되었습니다.',
    CREATE_LIST: '관심종목 리스트가 생성되었습니다.',
    UPDATE_LIST: '관심종목 리스트가 수정되었습니다.',
    DELETE_LIST: '관심종목 리스트가 삭제되었습니다.',
  },

  // 에러 메시지
  ERROR: {
    LOAD_LISTS: '관심종목 리스트를 불러오는데 실패했습니다.',
    LOAD_STOCKS: '종목 목록을 불러오는데 실패했습니다.',
    ADD_STOCK: '종목 추가에 실패했습니다.',
    REMOVE_STOCK: '종목 제거에 실패했습니다.',
    UPDATE_STOCK: '종목 설정 수정에 실패했습니다.',
    DELETE_LIST: '리스트 삭제에 실패했습니다.',
    DUPLICATE_STOCK: '이미 추가된 종목입니다.',
    NOT_FOUND: '종목을 찾을 수 없습니다.',
    NOT_OBSERVED: '해당 종목은 관찰되지 않습니다.',
    AUTH_REQUIRED: '인증이 필요합니다. 다시 로그인해주세요.',
    NETWORK: '서버와 연결할 수 없습니다.',
    VALIDATION: '입력값을 확인해주세요.',
    UNKNOWN: '오류가 발생했습니다.',
  },

  // 확인 메시지
  CONFIRM: {
    DELETE_LIST: (name: string) => `"${name}" 리스트를 삭제하시겠습니까?`,
    REMOVE_STOCK: (symbol: string) => `"${symbol}"을(를) 제거하시겠습니까?`,
  },

  // UI 레이블
  LABEL: {
    MY_LISTS: '나의 리스트',
    WATCHLIST: '관심종목',
    ADD_STOCK: '종목 추가',
    FIRST_STOCK: '첫 종목 추가하기',
    CREATE_LIST: '새 리스트 만들기',
    EDIT: '수정',
    DELETE: '삭제',
    REMOVE: '제거',
    CANCEL: '취소',
    SAVE: '저장',
    SAVING: '저장 중...',
    LOADING: '로딩 중...',
    RETRY: '다시 시도',
    REFRESH: '페이지 새로고침',
  },

  // 플레이스홀더
  PLACEHOLDER: {
    STOCK_SYMBOL: '예: AAPL (종목 심볼 또는 회사명 검색)',
    TARGET_PRICE: '0.00',
    NOTES: '이 종목에 대한 메모...',
  },

  // 설명 텍스트
  DESCRIPTION: {
    WATCHLIST_PAGE: '관심 있는 종목을 리스트로 관리하고 모니터링하세요',
    TARGET_PRICE: '현재가가 목표가 이하로 떨어지면 표시됩니다',
    EMPTY_LIST: '아직 추가된 종목이 없습니다',
    NO_LISTS: '관심종목 리스트가 없습니다',
    CREATE_FIRST_LIST: '첫 번째 관심종목 리스트를 만들어보세요!',
    SELECT_LIST: '왼쪽에서 리스트를 선택하세요',
    ERROR_PERSISTS: '문제가 계속되면 관리자에게 문의해주세요.',
    ERROR_OCCURRED: '관심종목 페이지를 표시하는 중 오류가 발생했습니다.\n페이지를 새로고침하면 문제가 해결될 수 있습니다.',
  },

  // 모달 제목
  MODAL: {
    ADD_STOCK: '종목 추가',
    EDIT_STOCK: '종목 설정 수정',
    CREATE_LIST: '새 관심종목 리스트',
    EDIT_LIST: '관심종목 리스트 수정',
  },

  // 필드명
  FIELD: {
    STOCK_SYMBOL: '종목 심볼',
    STOCK_NAME: '종목',
    CURRENT_PRICE: '현재가',
    CHANGE: '변동',
    TARGET_PRICE: '목표 진입가',
    TARGET_PRICE_USD: '목표 진입가 (USD)',
    NOTES: '메모',
    ADDED_DATE: '추가일',
    ACTION: '액션',
    REQUIRED: '*',
    OPTIONAL: '(선택)',
  },

  // 상태 텍스트
  STATUS: {
    BEST_MATCH: 'Best Match',
    SELECTED: '선택됨',
    TARGET_REACHED: '✓ 도달',
    NOT_SET: '미설정',
    NO_DATA: '-',
    PRICE_DIFF: (diff: number) => `${diff.toFixed(2)}% 차이`,
  },

  // 에러 바운더리
  ERROR_BOUNDARY: {
    TITLE: '문제가 발생했습니다',
    ERROR_DETAILS: '에러 상세 정보',
  },
}

/**
 * 통화 포맷팅
 */
export const formatCurrency = (value: number): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)
}

/**
 * 퍼센트 포맷팅
 */
export const formatPercent = (value: number): string => {
  const sign = value >= 0 ? '+' : ''
  return `${sign}${value.toFixed(2)}%`
}

/**
 * 날짜 포맷팅
 */
export const formatDate = (date: string | Date): string => {
  return new Date(date).toLocaleDateString('ko-KR')
}

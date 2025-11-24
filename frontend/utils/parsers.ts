/**
 * 안전한 타입 파싱 유틸리티
 * parseFloat(String(value)) 패턴 대체
 */

/**
 * 안전한 float 파싱
 */
export const safeParseFloat = (value: unknown, defaultValue: number = 0): number => {
  if (typeof value === 'number' && !isNaN(value)) return value;
  if (typeof value === 'string') {
    const parsed = parseFloat(value);
    return isNaN(parsed) ? defaultValue : parsed;
  }
  return defaultValue;
};

/**
 * 안전한 int 파싱
 */
export const safeParseInt = (value: unknown, defaultValue: number = 0): number => {
  if (typeof value === 'number' && !isNaN(value)) return Math.floor(value);
  if (typeof value === 'string') {
    const parsed = parseInt(value, 10);
    return isNaN(parsed) ? defaultValue : parsed;
  }
  return defaultValue;
};

/**
 * 값이 유효한 숫자인지 확인
 */
export const isValidNumber = (value: unknown): value is number => {
  return typeof value === 'number' && !isNaN(value) && isFinite(value);
};

/**
 * null/undefined 안전 접근
 */
export const safeGet = <T>(value: T | null | undefined, defaultValue: T): T => {
  return value ?? defaultValue;
};

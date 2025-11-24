/**
 * 스타일링 관련 유틸리티
 * 손익 색상 등 반복되는 스타일 로직 통합
 */

import { safeParseFloat } from './parsers';

/**
 * 손익에 따른 텍스트 색상 클래스
 */
export const getProfitTextColor = (value: number | string): string => {
  const numValue = safeParseFloat(value);
  return numValue >= 0 ? 'text-green-600' : 'text-red-600';
};

/**
 * 손익에 따른 밝은 텍스트 색상 클래스
 */
export const getProfitTextColorLight = (value: number | string): string => {
  const numValue = safeParseFloat(value);
  return numValue >= 0 ? 'text-green-500' : 'text-red-500';
};

/**
 * 손익에 따른 배경 색상 클래스
 */
export const getProfitBgColor = (value: number | string): string => {
  const numValue = safeParseFloat(value);
  return numValue >= 0 ? 'bg-green-50 dark:bg-green-900/20' : 'bg-red-50 dark:bg-red-900/20';
};

/**
 * 손익에 따른 테두리 색상 클래스
 */
export const getProfitBorderColor = (value: number | string): string => {
  const numValue = safeParseFloat(value);
  return numValue >= 0 ? 'border-green-200 dark:border-green-800' : 'border-red-200 dark:border-red-800';
};

/**
 * 손익 여부 확인
 */
export const isProfit = (value: number | string): boolean => {
  return safeParseFloat(value) >= 0;
};

/**
 * 손익 기호 반환
 */
export const getProfitSign = (value: number | string): string => {
  return safeParseFloat(value) >= 0 ? '+' : '';
};

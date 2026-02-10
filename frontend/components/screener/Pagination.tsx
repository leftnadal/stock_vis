'use client';

import React from 'react';
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react';
import type { PaginationProps } from '@/types/screener';

export default function Pagination({
  currentPage,
  totalPages,
  pageSize,
  totalCount,
  hasNext,
  hasPrevious,
  onPageChange,
  onPageSizeChange,
}: PaginationProps) {
  // 페이지 버튼 생성 로직
  const getPageNumbers = () => {
    const pages: (number | string)[] = [];
    const maxVisible = 7; // 최대 표시 페이지 개수

    if (totalPages <= maxVisible) {
      // 전체 페이지가 적으면 모두 표시
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i);
      }
    } else {
      // 많으면 현재 페이지 중심으로 표시
      if (currentPage <= 4) {
        // 시작 부분
        for (let i = 1; i <= 5; i++) {
          pages.push(i);
        }
        pages.push('...');
        pages.push(totalPages);
      } else if (currentPage >= totalPages - 3) {
        // 끝 부분
        pages.push(1);
        pages.push('...');
        for (let i = totalPages - 4; i <= totalPages; i++) {
          pages.push(i);
        }
      } else {
        // 중간
        pages.push(1);
        pages.push('...');
        for (let i = currentPage - 1; i <= currentPage + 1; i++) {
          pages.push(i);
        }
        pages.push('...');
        pages.push(totalPages);
      }
    }

    return pages;
  };

  const pageNumbers = getPageNumbers();

  const handlePageChange = (page: number) => {
    if (page >= 1 && page <= totalPages && page !== currentPage) {
      onPageChange(page);
    }
  };

  const handlePageSizeChange = (newSize: number) => {
    onPageSizeChange(newSize);
    // 페이지 크기 변경 시 1페이지로 이동
    if (currentPage !== 1) {
      onPageChange(1);
    }
  };

  const startItem = (currentPage - 1) * pageSize + 1;
  const endItem = Math.min(currentPage * pageSize, totalCount);

  return (
    <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-gray-200 dark:border-gray-700">
      {/* Left: Total count */}
      <div className="text-sm text-gray-600 dark:text-gray-400">
        총 <span className="font-semibold text-gray-900 dark:text-white">{totalCount}</span>개 종목
        {totalCount > 0 && (
          <>
            {' '}
            · {startItem}-{endItem} 표시 중
          </>
        )}
      </div>

      {/* Center: Page buttons */}
      {totalPages > 1 && (
        <div className="flex items-center gap-1">
          {/* First page */}
          <button
            onClick={() => handlePageChange(1)}
            disabled={!hasPrevious}
            className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            title="첫 페이지"
          >
            <ChevronsLeft className="w-4 h-4 text-gray-600 dark:text-gray-400" />
          </button>

          {/* Previous page */}
          <button
            onClick={() => handlePageChange(currentPage - 1)}
            disabled={!hasPrevious}
            className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            title="이전 페이지"
          >
            <ChevronLeft className="w-4 h-4 text-gray-600 dark:text-gray-400" />
          </button>

          {/* Page numbers */}
          {pageNumbers.map((page, index) =>
            page === '...' ? (
              <span
                key={`ellipsis-${index}`}
                className="px-2 text-gray-400 dark:text-gray-500"
              >
                ...
              </span>
            ) : (
              <button
                key={page}
                onClick={() => handlePageChange(page as number)}
                className={`
                  min-w-[32px] px-2 py-1.5 rounded text-sm font-medium transition-colors
                  ${
                    page === currentPage
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                  }
                `}
              >
                {page}
              </button>
            )
          )}

          {/* Next page */}
          <button
            onClick={() => handlePageChange(currentPage + 1)}
            disabled={!hasNext}
            className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            title="다음 페이지"
          >
            <ChevronRight className="w-4 h-4 text-gray-600 dark:text-gray-400" />
          </button>

          {/* Last page */}
          <button
            onClick={() => handlePageChange(totalPages)}
            disabled={!hasNext}
            className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            title="마지막 페이지"
          >
            <ChevronsRight className="w-4 h-4 text-gray-600 dark:text-gray-400" />
          </button>
        </div>
      )}

      {/* Right: Page size selector */}
      <div className="flex items-center gap-2 text-sm">
        <span className="text-gray-600 dark:text-gray-400">페이지당</span>
        <select
          value={pageSize}
          onChange={(e) => handlePageSizeChange(Number(e.target.value))}
          className="px-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400"
        >
          <option value={20}>20</option>
          <option value={50}>50</option>
          <option value={100}>100</option>
        </select>
        <span className="text-gray-600 dark:text-gray-400">개</span>
      </div>
    </div>
  );
}

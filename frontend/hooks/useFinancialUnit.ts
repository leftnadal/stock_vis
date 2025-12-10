/**
 * useFinancialUnit Hook
 *
 * Manages financial unit preference state with localStorage persistence.
 * Allows users to maintain their preferred unit selection across sessions.
 */

'use client';

import { useState, useEffect, useCallback } from 'react';
import { FinancialUnit } from '@/utils/formatters/financialFormatter';

const STORAGE_KEY = 'financial_unit_preference';
const DEFAULT_UNIT: FinancialUnit = 'auto';

export function useFinancialUnit(): [FinancialUnit, (unit: FinancialUnit) => void] {
  // Initialize with default value for SSR compatibility
  const [selectedUnit, setSelectedUnit] = useState<FinancialUnit>(DEFAULT_UNIT);
  const [isHydrated, setIsHydrated] = useState(false);

  // Load preference from localStorage on mount (client-side only)
  useEffect(() => {
    setIsHydrated(true);

    if (typeof window !== 'undefined') {
      try {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (stored && isValidUnit(stored)) {
          setSelectedUnit(stored as FinancialUnit);
        }
      } catch (error) {
        console.warn('Failed to load financial unit preference from localStorage:', error);
      }
    }
  }, []);

  // Save preference to localStorage when it changes
  const setUnit = useCallback((unit: FinancialUnit) => {
    console.log('Setting unit to:', unit); // Debug log
    setSelectedUnit(unit);

    if (typeof window !== 'undefined') {
      try {
        localStorage.setItem(STORAGE_KEY, unit);
        console.log('Saved to localStorage:', unit); // Debug log
      } catch (error) {
        console.warn('Failed to save financial unit preference to localStorage:', error);
      }
    }
  }, []);

  return [selectedUnit, setUnit];
}

/**
 * Validate that a string is a valid FinancialUnit
 */
function isValidUnit(value: string): boolean {
  return ['auto', 'B', 'M', 'K', 'raw'].includes(value);
}

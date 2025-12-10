/**
 * useFinancialFields Hook
 *
 * Manages selected financial fields per tab with localStorage persistence.
 * Allows users to customize which fields are displayed in each financial statement tab.
 */

'use client';

import { useState, useEffect, useCallback } from 'react';
import { FinancialTabType, DEFAULT_SELECTED_FIELDS } from '@/constants/financialDefaults';

const STORAGE_KEY_PREFIX = 'financial_fields_';

export interface UseFinancialFieldsReturn {
  selectedFields: string[];
  setSelectedFields: (fields: string[]) => void;
  addField: (field: string) => void;
  removeField: (field: string) => void;
  toggleField: (field: string) => void;
  resetToDefault: () => void;
  isFieldSelected: (field: string) => boolean;
  // New methods for bulk operations and presets
  addFields: (fields: string[]) => void;
  applyPreset: (fields: string[]) => void;
}

export function useFinancialFields(tabType: FinancialTabType): UseFinancialFieldsReturn {
  const storageKey = `${STORAGE_KEY_PREFIX}${tabType}`;
  const defaultFields = DEFAULT_SELECTED_FIELDS[tabType];

  // Initialize with default value for SSR compatibility
  const [selectedFields, setSelectedFieldsState] = useState<string[]>(defaultFields);
  const [isHydrated, setIsHydrated] = useState(false);

  // Load preference from localStorage on mount (client-side only)
  useEffect(() => {
    setIsHydrated(true);

    if (typeof window !== 'undefined') {
      try {
        const stored = localStorage.getItem(storageKey);
        if (stored) {
          const parsed = JSON.parse(stored);
          if (Array.isArray(parsed) && parsed.length > 0) {
            setSelectedFieldsState(parsed);
          }
        }
      } catch (error) {
        console.warn(`Failed to load financial fields preference for ${tabType}:`, error);
      }
    }
  }, [storageKey, tabType]);

  // Save preference to localStorage when it changes
  const setSelectedFields = useCallback((fields: string[]) => {
    setSelectedFieldsState(fields);

    if (typeof window !== 'undefined') {
      try {
        localStorage.setItem(storageKey, JSON.stringify(fields));
      } catch (error) {
        console.warn(`Failed to save financial fields preference for ${tabType}:`, error);
      }
    }
  }, [storageKey, tabType]);

  // Add a single field
  const addField = useCallback((field: string) => {
    setSelectedFields([...selectedFields.filter(f => f !== field), field]);
  }, [selectedFields, setSelectedFields]);

  // Remove a single field
  const removeField = useCallback((field: string) => {
    const newFields = selectedFields.filter(f => f !== field);
    // Ensure at least one field remains
    if (newFields.length > 0) {
      setSelectedFields(newFields);
    }
  }, [selectedFields, setSelectedFields]);

  // Toggle a field
  const toggleField = useCallback((field: string) => {
    if (selectedFields.includes(field)) {
      removeField(field);
    } else {
      addField(field);
    }
  }, [selectedFields, addField, removeField]);

  // Reset to default fields
  const resetToDefault = useCallback(() => {
    setSelectedFields([...defaultFields]);
  }, [defaultFields, setSelectedFields]);

  // Check if a field is selected
  const isFieldSelected = useCallback((field: string) => {
    return selectedFields.includes(field);
  }, [selectedFields]);

  // Add multiple fields at once
  const addFields = useCallback((fields: string[]) => {
    const newFields = [...selectedFields];
    fields.forEach((field) => {
      if (!newFields.includes(field)) {
        newFields.push(field);
      }
    });
    setSelectedFields(newFields);
  }, [selectedFields, setSelectedFields]);

  // Apply a preset (replace current selection)
  const applyPreset = useCallback((fields: string[]) => {
    setSelectedFields([...fields]);
  }, [setSelectedFields]);

  return {
    selectedFields,
    setSelectedFields,
    addField,
    removeField,
    toggleField,
    resetToDefault,
    isFieldSelected,
    addFields,
    applyPreset,
  };
}

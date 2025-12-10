/**
 * FieldSettingsModal Component
 *
 * Modal for selecting which financial fields to display.
 * Shows all available fields with Korean labels and descriptions.
 */

'use client';

import React, { useState, useEffect } from 'react';
import { X, Check, RotateCcw, Search, Sparkles } from 'lucide-react';
import {
  FinancialTabType,
  FinancialFieldMeta,
  getFieldsForTab,
  DEFAULT_SELECTED_FIELDS,
} from '@/constants/financialDefaults';
import { getPresetsForTab, FieldPreset } from '@/constants/financialPresets';

interface FieldSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  tabType: FinancialTabType;
  selectedFields: string[];
  onSave: (fields: string[]) => void;
}

export default function FieldSettingsModal({
  isOpen,
  onClose,
  tabType,
  selectedFields,
  onSave,
}: FieldSettingsModalProps) {
  const [localSelectedFields, setLocalSelectedFields] = useState<string[]>(selectedFields);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState<'all' | 'presets'>('all');
  const allFields = getFieldsForTab(tabType);
  const presets = getPresetsForTab(tabType);

  // Reset local state when modal opens
  useEffect(() => {
    if (isOpen) {
      setLocalSelectedFields(selectedFields);
      setSearchQuery('');
      setActiveTab('all');
    }
  }, [isOpen, selectedFields]);

  // Filter fields by search query
  const filteredFields = allFields.filter((field) => {
    const query = searchQuery.toLowerCase();
    return (
      field.labelKo.toLowerCase().includes(query) ||
      field.labelEn.toLowerCase().includes(query) ||
      field.description.toLowerCase().includes(query) ||
      field.key.toLowerCase().includes(query)
    );
  });

  const toggleField = (fieldKey: string) => {
    if (localSelectedFields.includes(fieldKey)) {
      // Don't allow removing if it's the last field
      if (localSelectedFields.length > 1) {
        setLocalSelectedFields(localSelectedFields.filter((f) => f !== fieldKey));
      }
    } else {
      setLocalSelectedFields([...localSelectedFields, fieldKey]);
    }
  };

  const handleSelectAll = () => {
    setLocalSelectedFields(allFields.map((f) => f.key));
  };

  const handleDeselectAll = () => {
    // Keep at least the first default field
    setLocalSelectedFields([DEFAULT_SELECTED_FIELDS[tabType][0]]);
  };

  const handleResetToDefault = () => {
    setLocalSelectedFields([...DEFAULT_SELECTED_FIELDS[tabType]]);
  };

  const handleApplyPreset = (preset: FieldPreset) => {
    // Apply preset immediately and close modal
    onSave([...preset.fields]);
    onClose();
  };

  const handleSave = () => {
    onSave(localSelectedFields);
    onClose();
  };

  const getTabTitle = () => {
    switch (tabType) {
      case 'balance-sheet':
        return '재무상태표';
      case 'income-statement':
        return '손익계산서';
      case 'cash-flow':
        return '현금흐름표';
      default:
        return '재무제표';
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between p-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              {getTabTitle()} 항목 설정
            </h2>
            <button
              onClick={onClose}
              className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Tabs */}
          <div className="flex border-t border-gray-200 dark:border-gray-700">
            <button
              onClick={() => setActiveTab('all')}
              className={`flex-1 px-4 py-3 text-sm font-medium transition-colors relative ${
                activeTab === 'all'
                  ? 'text-blue-600 dark:text-blue-400'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
              }`}
            >
              전체 항목
              {activeTab === 'all' && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-600 dark:bg-blue-400" />
              )}
            </button>
            <button
              onClick={() => setActiveTab('presets')}
              className={`flex-1 px-4 py-3 text-sm font-medium transition-colors relative flex items-center justify-center gap-1.5 ${
                activeTab === 'presets'
                  ? 'text-blue-600 dark:text-blue-400'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
              }`}
            >
              <Sparkles className="w-4 h-4" />
              프리셋
              {activeTab === 'presets' && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-600 dark:bg-blue-400" />
              )}
            </button>
          </div>
        </div>

        {/* Content */}
        {activeTab === 'all' ? (
          <>
            {/* Search and Actions */}
            <div className="p-4 border-b border-gray-200 dark:border-gray-700 space-y-3">
              {/* Search */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="항목 검색..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              {/* Quick Actions */}
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={handleSelectAll}
                  className="px-3 py-1.5 text-sm text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-md transition-colors"
                >
                  전체 선택
                </button>
                <button
                  onClick={handleDeselectAll}
                  className="px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
                >
                  전체 해제
                </button>
                <button
                  onClick={handleResetToDefault}
                  className="px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors flex items-center gap-1"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  기본값 복원
                </button>
                <span className="ml-auto text-sm text-gray-500 dark:text-gray-400 self-center">
                  {localSelectedFields.length}개 선택됨
                </span>
              </div>
            </div>

            {/* Field List */}
            <div className="flex-1 overflow-y-auto p-4">
              <div className="space-y-2">
                {filteredFields.map((field) => (
                  <FieldItem
                    key={field.key}
                    field={field}
                    isSelected={localSelectedFields.includes(field.key)}
                    onToggle={() => toggleField(field.key)}
                    disabled={localSelectedFields.length === 1 && localSelectedFields.includes(field.key)}
                  />
                ))}

                {filteredFields.length === 0 && (
                  <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                    검색 결과가 없습니다.
                  </div>
                )}
              </div>
            </div>
          </>
        ) : (
          <PresetsTab
            presets={presets}
            onApplyPreset={handleApplyPreset}
            currentFieldsCount={localSelectedFields.length}
          />
        )}

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-4 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
          >
            취소
          </button>
          <button
            onClick={handleSave}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
          >
            저장
          </button>
        </div>
      </div>
    </div>
  );
}

interface FieldItemProps {
  field: FinancialFieldMeta;
  isSelected: boolean;
  onToggle: () => void;
  disabled?: boolean;
}

function FieldItem({ field, isSelected, onToggle, disabled }: FieldItemProps) {
  return (
    <button
      onClick={onToggle}
      disabled={disabled}
      className={`w-full text-left p-3 rounded-lg border transition-colors ${
        isSelected
          ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
          : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
      } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
    >
      <div className="flex items-start gap-3">
        {/* Checkbox */}
        <div
          className={`mt-0.5 w-5 h-5 rounded flex items-center justify-center flex-shrink-0 ${
            isSelected
              ? 'bg-blue-600 text-white'
              : 'border-2 border-gray-300 dark:border-gray-600'
          }`}
        >
          {isSelected && <Check className="w-3.5 h-3.5" />}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-gray-900 dark:text-white">
              {field.labelKo}
            </span>
            <span className="text-xs text-gray-500 dark:text-gray-400">
              {field.labelEn}
            </span>
          </div>
          <p className="mt-0.5 text-sm text-gray-500 dark:text-gray-400 line-clamp-2">
            {field.description}
          </p>
        </div>
      </div>
    </button>
  );
}

interface PresetsTabProps {
  presets: FieldPreset[];
  onApplyPreset: (preset: FieldPreset) => void;
  currentFieldsCount: number;
}

function PresetsTab({ presets, onApplyPreset, currentFieldsCount }: PresetsTabProps) {
  // Dynamic icon mapping (we'll use a simple approach)
  const getIconComponent = (iconName: string) => {
    // Return a placeholder for now since lucide-react icons need to be imported
    // In production, you'd use a proper icon mapping
    return Sparkles;
  };

  return (
    <div className="flex-1 overflow-y-auto p-4">
      <div className="mb-4">
        <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          분석 목적별 프리셋
        </h3>
        <p className="text-xs text-gray-500 dark:text-gray-400">
          원클릭으로 목적에 맞는 재무제표 항목을 선택하세요. (현재 {currentFieldsCount}개 선택됨)
        </p>
      </div>

      <div className="grid grid-cols-1 gap-3">
        {presets.map((preset) => {
          const IconComponent = getIconComponent(preset.icon);

          return (
            <button
              key={preset.id}
              onClick={() => onApplyPreset(preset)}
              className="text-left p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:border-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-all group"
            >
              <div className="flex items-start gap-3">
                {/* Icon */}
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center flex-shrink-0">
                  <IconComponent className="w-5 h-5 text-white" />
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <h4 className="font-semibold text-gray-900 dark:text-white">
                      {preset.name}
                    </h4>
                    <span className="text-xs text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded">
                      {preset.fields.length}개 항목
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                    {preset.description}
                  </p>
                  <div className="text-xs text-blue-600 dark:text-blue-400 group-hover:underline">
                    적용하기 →
                  </div>
                </div>
              </div>
            </button>
          );
        })}
      </div>

      {presets.length === 0 && (
        <div className="text-center py-12 text-gray-500 dark:text-gray-400">
          <Sparkles className="w-12 h-12 mx-auto mb-3 text-gray-300 dark:text-gray-600" />
          <p>사용 가능한 프리셋이 없습니다.</p>
        </div>
      )}
    </div>
  );
}

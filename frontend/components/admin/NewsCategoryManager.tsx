'use client';

import { useState } from 'react';
import { Plus, Pencil, Trash2, AlertCircle, FolderOpen } from 'lucide-react';
import { useNewsCategories, useSectorOptions, useNewsCategoryMutations } from '@/hooks/useAdminDashboard';
import ActionButton from './shared/ActionButton';
import type {
  NewsCategoryType,
  NewsCategoryPriority,
  NewsCategoryCreateRequest,
  NewsCollectionCategory,
  SubSectorOption,
} from '@/types/admin';

// 타입/우선순위 배지 색상
const TYPE_BADGE: Record<NewsCategoryType, string> = {
  sector: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  sub_sector: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
  custom: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
};

const PRIORITY_BADGE: Record<NewsCategoryPriority, string> = {
  high: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
  medium: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300',
  low: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400',
};

const TYPE_LABEL: Record<NewsCategoryType, string> = {
  sector: 'Sector',
  sub_sector: 'Sub-Sector',
  custom: 'Custom',
};

const PRIORITY_LABEL: Record<NewsCategoryPriority, string> = {
  high: 'High (2회/일)',
  medium: 'Medium (1회/일)',
  low: 'Low (주 1회)',
};

interface FormState {
  name: string;
  category_type: NewsCategoryType;
  value: string;
  priority: NewsCategoryPriority;
  max_symbols: number;
}

const INITIAL_FORM: FormState = {
  name: '',
  category_type: 'sector',
  value: '',
  priority: 'medium',
  max_symbols: 20,
};

export default function NewsCategoryManager() {
  const { data, isLoading } = useNewsCategories();
  const { data: sectorData } = useSectorOptions();
  const { create, update, remove } = useNewsCategoryMutations();

  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<FormState>(INITIAL_FORM);

  const categories = data?.categories ?? [];

  const handleCreate = () => {
    const req: NewsCategoryCreateRequest = {
      name: form.name,
      category_type: form.category_type,
      value: form.value,
      priority: form.priority,
      max_symbols: form.max_symbols,
    };
    create.mutate(req, {
      onSuccess: () => {
        setShowForm(false);
        setForm(INITIAL_FORM);
      },
    });
  };

  const handleUpdate = () => {
    if (editingId === null) return;
    update.mutate(
      { id: editingId, data: form },
      {
        onSuccess: () => {
          setEditingId(null);
          setShowForm(false);
          setForm(INITIAL_FORM);
        },
      }
    );
  };

  const handleEdit = (cat: NewsCollectionCategory) => {
    setEditingId(cat.id);
    setForm({
      name: cat.name,
      category_type: cat.category_type,
      value: cat.value,
      priority: cat.priority,
      max_symbols: cat.max_symbols,
    });
    setShowForm(true);
  };

  const handleDelete = (id: number) => {
    if (!window.confirm('이 카테고리를 삭제하시겠습니까?')) return;
    remove.mutate(id);
  };

  const handleToggleActive = (cat: NewsCollectionCategory) => {
    update.mutate({ id: cat.id, data: { is_active: !cat.is_active } });
  };

  const handleCancel = () => {
    setShowForm(false);
    setEditingId(null);
    setForm(INITIAL_FORM);
  };

  // 섹터별 서브섹터 그룹핑
  const subSectorsBySector: Record<string, SubSectorOption[]> = {};
  if (sectorData) {
    for (const ss of sectorData.sub_sectors) {
      if (!subSectorsBySector[ss.sector]) subSectorsBySector[ss.sector] = [];
      subSectorsBySector[ss.sector].push(ss);
    }
  }

  const formatRelativeTime = (isoStr: string | null): string => {
    if (!isoStr) return '-';
    const diff = Date.now() - new Date(isoStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 60) return `${mins}분 전`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}시간 전`;
    return `${Math.floor(hours / 24)}일 전`;
  };

  if (isLoading) {
    return <div className="h-32 bg-gray-100 dark:bg-gray-800 rounded-xl animate-pulse" />;
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-gray-800 dark:text-gray-200 flex items-center gap-2">
          <FolderOpen className="h-4 w-4" />
          수집 카테고리
        </h3>
        {!showForm && (
          <button
            onClick={() => { setShowForm(true); setEditingId(null); setForm(INITIAL_FORM); }}
            className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-md bg-indigo-50 text-indigo-700 hover:bg-indigo-100 dark:bg-indigo-900/30 dark:text-indigo-300 dark:hover:bg-indigo-900/50 transition-colors"
          >
            <Plus className="h-3.5 w-3.5" />
            카테고리 추가
          </button>
        )}
      </div>

      {/* Inline Form */}
      {showForm && (
        <div className="mb-4 p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {/* 이름 */}
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">이름</label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="AI 반도체"
                className="w-full px-3 py-1.5 text-sm rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200"
              />
            </div>

            {/* 타입 */}
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">타입</label>
              <select
                value={form.category_type}
                onChange={(e) => setForm({ ...form, category_type: e.target.value as NewsCategoryType, value: '' })}
                className="w-full px-3 py-1.5 text-sm rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200"
              >
                <option value="sector">Sector (GICS 섹터)</option>
                <option value="sub_sector">Sub-Sector (산업)</option>
                <option value="custom">Custom (직접 입력)</option>
              </select>
            </div>

            {/* 값 - 조건부 렌더링 */}
            <div className="sm:col-span-2">
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                {form.category_type === 'custom' ? '심볼 (쉼표 구분)' : form.category_type === 'sector' ? '섹터' : '서브섹터'}
              </label>
              {form.category_type === 'sector' && sectorData ? (
                <select
                  value={form.value}
                  onChange={(e) => setForm({ ...form, value: e.target.value })}
                  className="w-full px-3 py-1.5 text-sm rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200"
                >
                  <option value="">-- 섹터 선택 --</option>
                  {sectorData.sectors.map((s) => (
                    <option key={s.value} value={s.value}>
                      {s.value} ({s.count})
                    </option>
                  ))}
                </select>
              ) : form.category_type === 'sub_sector' && sectorData ? (
                <select
                  value={form.value}
                  onChange={(e) => setForm({ ...form, value: e.target.value })}
                  className="w-full px-3 py-1.5 text-sm rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200"
                >
                  <option value="">-- 서브섹터 선택 --</option>
                  {Object.entries(subSectorsBySector).map(([sector, subs]) => (
                    <optgroup key={sector} label={sector}>
                      {subs.map((ss) => (
                        <option key={ss.value} value={ss.value}>
                          {ss.value} ({ss.count})
                        </option>
                      ))}
                    </optgroup>
                  ))}
                </select>
              ) : (
                <textarea
                  value={form.value}
                  onChange={(e) => setForm({ ...form, value: e.target.value })}
                  placeholder="TSLA, ALB, PANW (쉼표로 구분)"
                  rows={2}
                  className="w-full px-3 py-1.5 text-sm rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200"
                />
              )}
            </div>

            {/* Priority */}
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">우선순위</label>
              <select
                value={form.priority}
                onChange={(e) => setForm({ ...form, priority: e.target.value as NewsCategoryPriority })}
                className="w-full px-3 py-1.5 text-sm rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200"
              >
                <option value="high">High (2회/일)</option>
                <option value="medium">Medium (1회/일)</option>
                <option value="low">Low (주 1회)</option>
              </select>
            </div>

            {/* Max Symbols */}
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">최대 심볼 수</label>
              <input
                type="number"
                value={form.max_symbols}
                onChange={(e) => setForm({ ...form, max_symbols: Math.max(1, parseInt(e.target.value) || 20) })}
                min={1}
                max={100}
                className="w-full px-3 py-1.5 text-sm rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200"
              />
            </div>
          </div>

          {/* 에러 표시 */}
          {(create.error || update.error) && (
            <div className="mt-2 text-xs text-red-600 dark:text-red-400">
              {((create.error || update.error) as any)?.response?.data?.error || '저장 실패'}
            </div>
          )}

          {/* 버튼 */}
          <div className="flex gap-2 mt-3">
            <button
              onClick={editingId !== null ? handleUpdate : handleCreate}
              disabled={!form.name || !form.value || create.isPending || update.isPending}
              className="px-4 py-1.5 text-xs font-medium rounded-md bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {create.isPending || update.isPending ? '저장 중...' : editingId !== null ? '수정' : '저장'}
            </button>
            <button
              onClick={handleCancel}
              className="px-4 py-1.5 text-xs font-medium rounded-md bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600 transition-colors"
            >
              취소
            </button>
          </div>
        </div>
      )}

      {/* Table */}
      {categories.length === 0 ? (
        <p className="text-sm text-gray-400 text-center py-6">등록된 카테고리가 없습니다</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700">
                <th className="text-left py-2 px-2 text-gray-500 dark:text-gray-400 font-medium">활성</th>
                <th className="text-left py-2 px-2 text-gray-500 dark:text-gray-400 font-medium">이름</th>
                <th className="text-left py-2 px-2 text-gray-500 dark:text-gray-400 font-medium">타입</th>
                <th className="text-left py-2 px-2 text-gray-500 dark:text-gray-400 font-medium">우선순위</th>
                <th className="text-left py-2 px-2 text-gray-500 dark:text-gray-400 font-medium">심볼</th>
                <th className="text-left py-2 px-2 text-gray-500 dark:text-gray-400 font-medium">마지막 수집</th>
                <th className="text-right py-2 px-2 text-gray-500 dark:text-gray-400 font-medium">액션</th>
              </tr>
            </thead>
            <tbody>
              {categories.map((cat) => (
                <tr
                  key={cat.id}
                  className={`border-b border-gray-100 dark:border-gray-800 ${!cat.is_active ? 'opacity-50' : ''}`}
                >
                  {/* 활성 토글 */}
                  <td className="py-2 px-2">
                    <button
                      onClick={() => handleToggleActive(cat)}
                      className={`w-8 h-4 rounded-full relative transition-colors ${
                        cat.is_active ? 'bg-green-500' : 'bg-gray-300 dark:bg-gray-600'
                      }`}
                    >
                      <span
                        className={`absolute top-0.5 w-3 h-3 rounded-full bg-white transition-transform ${
                          cat.is_active ? 'left-4' : 'left-0.5'
                        }`}
                      />
                    </button>
                  </td>

                  {/* 이름 */}
                  <td className="py-2 px-2 text-gray-800 dark:text-gray-200 font-medium">
                    {cat.name}
                    {cat.last_error && (
                      <span className="ml-1 inline-flex" title={cat.last_error}>
                        <AlertCircle className="h-3.5 w-3.5 text-red-500" />
                      </span>
                    )}
                  </td>

                  {/* 타입 배지 */}
                  <td className="py-2 px-2">
                    <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${TYPE_BADGE[cat.category_type]}`}>
                      {TYPE_LABEL[cat.category_type]}
                    </span>
                  </td>

                  {/* 우선순위 배지 */}
                  <td className="py-2 px-2">
                    <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${PRIORITY_BADGE[cat.priority]}`}>
                      {cat.priority}
                    </span>
                  </td>

                  {/* 심볼 수 + 프리뷰 */}
                  <td className="py-2 px-2 text-xs text-gray-600 dark:text-gray-400">
                    <span className="font-mono">
                      {cat.resolved_symbols_preview.join(', ')}
                      {cat.resolved_symbol_count > 5 && ` +${cat.resolved_symbol_count - 5}`}
                    </span>
                  </td>

                  {/* 마지막 수집 */}
                  <td className="py-2 px-2 text-xs text-gray-500 dark:text-gray-400">
                    {cat.last_collected_at ? (
                      <span>
                        {formatRelativeTime(cat.last_collected_at)}
                        <span className="text-gray-400 ml-1">({cat.last_article_count}건)</span>
                      </span>
                    ) : (
                      '-'
                    )}
                  </td>

                  {/* 액션 */}
                  <td className="py-2 px-2 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <ActionButton
                        action="collect_category_news"
                        label="수집"
                        params={{ category_id: cat.id }}
                        size="sm"
                        variant="secondary"
                      />
                      <button
                        onClick={() => handleEdit(cat)}
                        className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                        title="편집"
                      >
                        <Pencil className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={() => handleDelete(cat.id)}
                        className="p-1 text-gray-400 hover:text-red-600 dark:hover:text-red-400"
                        title="삭제"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

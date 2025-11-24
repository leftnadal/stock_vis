'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  TrendingUp,
  TrendingDown,
  Target,
  AlertTriangle,
  Edit2,
  Save,
  X,
  Info
} from 'lucide-react';
import { formatCurrency, formatPercent } from '@/utils/formatters';
import { safeParseFloat } from '@/utils/parsers';
import { getProfitTextColor, getProfitTextColorLight, isProfit } from '@/utils/styling';

interface PortfolioItem {
  id: number;
  stock_symbol: string;
  stock_name: string;
  sector?: string;
  industry?: string;

  // 보유 정보
  quantity: number;
  average_price: number;

  // 현재 가격
  current_price: number;
  previous_close: number;
  stock_change: number;
  stock_change_percent: string;

  // 수익률
  total_value: number;
  total_cost: number;
  profit_loss: number;
  profit_loss_percentage: number;

  // 목표/손절
  target_price?: number;
  stop_loss_price?: number;
  target_achievement_rate?: number;
  distance_from_target?: number;
  distance_from_stop_loss?: number;

  // 포트폴리오 비중
  portfolio_weight: number;

  // 추가 지표
  pe_ratio?: number;
  dividend_yield?: number;
  week_52_high?: number;
  week_52_low?: number;

  notes?: string;
}

interface PortfolioTableData {
  portfolios: PortfolioItem[];
  summary: {
    total_stocks: number;
    total_value: number;
    total_cost: number;
    total_profit_loss: number;
    total_profit_loss_percentage: number;
    is_profitable: boolean;
  };
}

export default function PortfolioTable() {
  const router = useRouter();
  const [data, setData] = useState<PortfolioTableData | null>(null);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editValues, setEditValues] = useState<{
    target_price?: number;
    stop_loss_price?: number;
  }>({});

  // API URL 설정
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

  useEffect(() => {
    fetchPortfolioTable();
  }, []);

  const fetchPortfolioTable = async () => {
    try {
      const token = localStorage.getItem('access_token'); // access_token으로 수정
      if (!token) {
        console.error('No access token found');
        setLoading(false);
        return;
      }

      const response = await fetch(`${API_URL}/users/portfolio/table/`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        }
      });

      if (response.ok) {
        const data = await response.json();
        console.log('Portfolio table data:', data); // 디버깅용
        setData(data);
      } else {
        console.error('Failed to fetch portfolio table:', response.status, response.statusText);
        const errorData = await response.text();
        console.error('Error response:', errorData);
      }
    } catch (error) {
      console.error('Failed to fetch portfolio table:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (item: PortfolioItem) => {
    setEditingId(item.id);
    setEditValues({
      target_price: item.target_price,
      stop_loss_price: item.stop_loss_price
    });
  };

  const handleSave = async (id: number) => {
    try {
      const token = localStorage.getItem('access_token'); // access_token으로 수정
      if (!token) {
        console.error('No access token found');
        return;
      }

      const response = await fetch(`${API_URL}/users/portfolio/${id}/quick-update/`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(editValues)
      });

      if (response.ok) {
        await fetchPortfolioTable();
        setEditingId(null);
        setEditValues({});
      } else {
        console.error('Failed to update portfolio:', response.status, response.statusText);
      }
    } catch (error) {
      console.error('Failed to update portfolio:', error);
    }
  };

  const handleCancel = () => {
    setEditingId(null);
    setEditValues({});
  };

  const getAchievementColor = (rate: number) => {
    if (rate >= 80) return 'text-green-600';
    if (rate >= 50) return 'text-yellow-600';
    return 'text-gray-600';
  };

  const getStopLossColor = (distance?: number) => {
    if (!distance) return 'text-gray-400';
    if (distance < 5) return 'text-red-600 font-bold';
    if (distance < 10) return 'text-orange-600';
    return 'text-gray-600';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!data || !data.portfolios || data.portfolios.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg p-8 text-center">
        <p className="text-gray-500 dark:text-gray-400">
          포트폴리오가 비어있거나 데이터를 불러올 수 없습니다.
        </p>
        <button
          onClick={fetchPortfolioTable}
          className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          다시 시도
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 요약 카드 */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm">
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <div>
            <p className="text-sm text-gray-500 dark:text-gray-400">총 종목수</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {data.summary.total_stocks}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500 dark:text-gray-400">총 평가금액</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {formatCurrency(safeParseFloat(data.summary.total_value))}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500 dark:text-gray-400">총 매수금액</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {formatCurrency(safeParseFloat(data.summary.total_cost))}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500 dark:text-gray-400">총 손익</p>
            <p className={`text-2xl font-bold ${getProfitTextColor(data.summary.total_profit_loss)}`}>
              {formatCurrency(safeParseFloat(data.summary.total_profit_loss))}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500 dark:text-gray-400">수익률</p>
            <p className={`text-2xl font-bold ${getProfitTextColor(data.summary.total_profit_loss_percentage)}`}>
              {formatPercent(safeParseFloat(data.summary.total_profit_loss_percentage))}
            </p>
          </div>
          <div className="flex items-center">
            <div className={`px-4 py-2 rounded-lg ${
              data.summary.is_profitable
                ? 'bg-green-100 text-green-800'
                : 'bg-red-100 text-red-800'
            }`}>
              {data.summary.is_profitable ? (
                <TrendingUp className="h-6 w-6" />
              ) : (
                <TrendingDown className="h-6 w-6" />
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 포트폴리오 테이블 */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-900">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  종목
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  보유수량
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  평균매수가
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  현재가
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  전일대비
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  평가금액
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  손익
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  수익률
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  목표가
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  손절가
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  비중
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  관리
                </th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              {data.portfolios.map((item) => (
                <tr key={item.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                  {/* 종목명 */}
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div
                      className="cursor-pointer hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                      onClick={() => router.push(`/stocks/${item.stock_symbol}`)}
                    >
                      <div className="text-sm font-medium text-gray-900 dark:text-white hover:text-blue-600 dark:hover:text-blue-400">
                        {item.stock_symbol}
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        {item.stock_name}
                      </div>
                      {item.sector && (
                        <div className="text-xs text-gray-400 dark:text-gray-500">
                          {item.sector}
                        </div>
                      )}
                    </div>
                  </td>

                  {/* 보유수량 */}
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-900 dark:text-white">
                    {safeParseFloat(item.quantity).toFixed(2)}
                  </td>

                  {/* 평균매수가 */}
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-900 dark:text-white">
                    {formatCurrency(safeParseFloat(item.average_price))}
                  </td>

                  {/* 현재가 */}
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <div className="text-sm font-medium text-gray-900 dark:text-white">
                      {formatCurrency(safeParseFloat(item.current_price))}
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      전일: {formatCurrency(safeParseFloat(item.previous_close))}
                    </div>
                  </td>

                  {/* 전일대비 */}
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <div className={`text-sm font-medium ${getProfitTextColor(item.stock_change)}`}>
                      {formatCurrency(safeParseFloat(item.stock_change))}
                    </div>
                    <div className={`text-xs ${getProfitTextColorLight(item.stock_change)}`}>
                      {item.stock_change_percent}
                    </div>
                  </td>

                  {/* 평가금액 */}
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <div className="text-sm font-medium text-gray-900 dark:text-white">
                      {formatCurrency(safeParseFloat(item.total_value))}
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      매수: {formatCurrency(safeParseFloat(item.total_cost))}
                    </div>
                  </td>

                  {/* 손익 */}
                  <td className={`px-6 py-4 whitespace-nowrap text-right text-sm font-medium ${getProfitTextColor(item.profit_loss)}`}>
                    {formatCurrency(safeParseFloat(item.profit_loss))}
                  </td>

                  {/* 수익률 */}
                  <td className={`px-6 py-4 whitespace-nowrap text-right text-sm font-bold ${getProfitTextColor(item.profit_loss_percentage)}`}>
                    {formatPercent(safeParseFloat(item.profit_loss_percentage))}
                  </td>

                  {/* 목표가 */}
                  <td className="px-6 py-4 whitespace-nowrap text-center">
                    {editingId === item.id ? (
                      <input
                        type="number"
                        className="w-24 px-2 py-1 text-sm border rounded dark:bg-gray-700 dark:border-gray-600"
                        value={editValues.target_price || ''}
                        onChange={(e) => setEditValues({
                          ...editValues,
                          target_price: e.target.value ? parseFloat(e.target.value) : undefined
                        })}
                        placeholder="목표가"
                      />
                    ) : (
                      <div>
                        {item.target_price ? (
                          <>
                            <div className="text-sm font-medium text-gray-900 dark:text-white">
                              {formatCurrency(safeParseFloat(item.target_price))}
                            </div>
                            {item.target_achievement_rate !== undefined && (
                              <div className={`text-xs ${getAchievementColor(safeParseFloat(item.target_achievement_rate))}`}>
                                달성률: {safeParseFloat(item.target_achievement_rate).toFixed(1)}%
                              </div>
                            )}
                            {item.distance_from_target !== undefined && (
                              <div className="text-xs text-gray-500">
                                {safeParseFloat(item.distance_from_target) > 0 ? '+' : ''}{safeParseFloat(item.distance_from_target).toFixed(1)}%
                              </div>
                            )}
                          </>
                        ) : (
                          <span className="text-gray-400 text-sm">-</span>
                        )}
                      </div>
                    )}
                  </td>

                  {/* 손절가 */}
                  <td className="px-6 py-4 whitespace-nowrap text-center">
                    {editingId === item.id ? (
                      <input
                        type="number"
                        className="w-24 px-2 py-1 text-sm border rounded dark:bg-gray-700 dark:border-gray-600"
                        value={editValues.stop_loss_price || ''}
                        onChange={(e) => setEditValues({
                          ...editValues,
                          stop_loss_price: e.target.value ? parseFloat(e.target.value) : undefined
                        })}
                        placeholder="손절가"
                      />
                    ) : (
                      <div>
                        {item.stop_loss_price ? (
                          <>
                            <div className="text-sm font-medium text-gray-900 dark:text-white">
                              {formatCurrency(safeParseFloat(item.stop_loss_price))}
                            </div>
                            {item.distance_from_stop_loss !== undefined && (
                              <div className={`text-xs ${getStopLossColor(safeParseFloat(item.distance_from_stop_loss))}`}>
                                여유: {safeParseFloat(item.distance_from_stop_loss).toFixed(1)}%
                                {safeParseFloat(item.distance_from_stop_loss) < 5 && (
                                  <AlertTriangle className="inline h-3 w-3 ml-1" />
                                )}
                              </div>
                            )}
                          </>
                        ) : (
                          <span className="text-gray-400 text-sm">-</span>
                        )}
                      </div>
                    )}
                  </td>

                  {/* 비중 */}
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <div className="text-sm font-medium text-gray-900 dark:text-white">
                      {safeParseFloat(item.portfolio_weight).toFixed(1)}%
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-1.5 mt-1">
                      <div
                        className="bg-blue-600 h-1.5 rounded-full"
                        style={{ width: `${Math.min(safeParseFloat(item.portfolio_weight), 100)}%` }}
                      ></div>
                    </div>
                  </td>

                  {/* 관리 */}
                  <td className="px-6 py-4 whitespace-nowrap text-center">
                    {editingId === item.id ? (
                      <div className="flex justify-center space-x-1">
                        <button
                          onClick={() => handleSave(item.id)}
                          className="text-green-600 hover:text-green-800"
                          title="저장"
                        >
                          <Save className="h-4 w-4" />
                        </button>
                        <button
                          onClick={handleCancel}
                          className="text-red-600 hover:text-red-800"
                          title="취소"
                        >
                          <X className="h-4 w-4" />
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => handleEdit(item)}
                        className="text-gray-600 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200"
                        title="목표가/손절가 편집"
                      >
                        <Edit2 className="h-4 w-4" />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* 추가 정보 */}
        <div className="px-6 py-4 bg-gray-50 dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700">
          <div className="flex items-center text-xs text-gray-500 dark:text-gray-400 space-x-4">
            <div className="flex items-center">
              <Info className="h-3 w-3 mr-1" />
              <span>목표가 달성률: (현재가-평균가)/(목표가-평균가) × 100</span>
            </div>
            <div className="flex items-center">
              <AlertTriangle className="h-3 w-3 mr-1 text-orange-500" />
              <span>손절가 여유 5% 미만 주의</span>
            </div>
            <div>
              <Target className="h-3 w-3 inline mr-1 text-green-500" />
              <span>목표가 80% 이상 달성 확인</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
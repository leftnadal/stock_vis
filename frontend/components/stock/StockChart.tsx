'use client';

import { useState, useEffect } from 'react';
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ComposedChart,
  Bar,
  Cell,
  ReferenceLine,
} from 'recharts';
import { stockService, ChartData } from '@/services/stock';
import { TrendingUp, TrendingDown, Settings2, BarChart3 } from 'lucide-react';
import { formatCurrency, formatVolume } from '@/utils/formatters';
import { isProfit, getProfitSign } from '@/utils/styling';
import { Line } from 'recharts';

interface StockChartProps {
  symbol: string;
}

// 기간별 옵션 설정 (표시할 데이터 범위)
const PERIOD_OPTIONS = [
  { value: '5d', label: '5일', period: 'days', days: 7, chartType: 'daily' },
  { value: '1m', label: '1개월', period: '1m', days: 30, chartType: 'daily' },
  { value: '3m', label: '3개월', period: '3m', days: 90, chartType: 'daily' },
  { value: '1y', label: '1년', period: '1y', days: 365, chartType: 'daily' },
];

// ====================================
// Phase 2 개선: 색상 테마 (색맹 접근성 지원)
// ====================================
type ColorTheme = 'default' | 'accessible';

const COLOR_THEMES = {
  default: {
    up: '#10B981',    // 초록색 - 상승
    down: '#EF4444',  // 빨간색 - 하락
    avgLine: '#8B5CF6', // 보라색 - 평균선
  },
  accessible: {
    up: '#3B82F6',    // 파란색 - 상승 (색맹 친화적)
    down: '#F97316',  // 주황색 - 하락 (색맹 친화적)
    avgLine: '#6366F1', // 인디고 - 평균선
  },
};

// 기본 색상 (default 테마 사용)
const CANDLE_UP_COLOR = COLOR_THEMES.default.up;
const CANDLE_DOWN_COLOR = COLOR_THEMES.default.down;

// ====================================
// Phase 1 개선: 유틸리티 함수들
// ====================================

/**
 * Nice Numbers 계산 - Y축에 깔끔한 숫자 표시 (예: $140, $150)
 */
function calculateNiceScale(min: number, max: number, maxTicks: number = 6) {
  const range = max - min;
  if (range === 0) return { min, max, step: 1, ticks: [min] };

  const roughStep = range / (maxTicks - 1);
  const magnitude = Math.floor(Math.log10(roughStep));
  const magnitudePower = Math.pow(10, magnitude);

  // Nice fractions: 1, 2, 5, 10
  const niceFractions = [1, 2, 5, 10];
  let niceStep = niceFractions[0] * magnitudePower;

  for (const fraction of niceFractions) {
    const candidate = fraction * magnitudePower;
    if (candidate >= roughStep) {
      niceStep = candidate;
      break;
    }
  }

  const niceMin = Math.floor(min / niceStep) * niceStep;
  const niceMax = Math.ceil(max / niceStep) * niceStep;

  const ticks: number[] = [];
  for (let tick = niceMin; tick <= niceMax; tick += niceStep) {
    ticks.push(tick);
  }

  return { min: niceMin, max: niceMax, step: niceStep, ticks };
}

/**
 * 가격대별 소수점 자릿수 결정
 */
function getPriceDecimalPlaces(price: number): number {
  if (price >= 100) return 0;      // $100 이상: $123
  if (price >= 10) return 1;       // $10-100: $12.3
  if (price >= 1) return 2;        // $1-10: $1.23
  return 3;                        // $1 미만: $0.123
}

/**
 * 가격 포맷팅 (Y축용)
 */
function formatPriceForAxis(value: number): string {
  const decimals = getPriceDecimalPlaces(value);
  return `$${value.toFixed(decimals)}`;
}

/**
 * 기간별 X축 날짜 포맷 결정
 */
function getDateFormat(days: number, date: Date): string {
  if (days <= 7) {
    // 5일: "29일" (일자만)
    return `${date.getDate()}일`;
  } else if (days <= 90) {
    // 1개월, 3개월: "11/29" 형식
    return `${date.getMonth() + 1}/${date.getDate()}`;
  } else {
    // 1년: "24년 11월" 형식
    const year = date.getFullYear().toString().slice(-2);
    return `${year}년 ${date.getMonth() + 1}월`;
  }
}

/**
 * 기간별 X축 틱 간격 결정
 */
function getTickInterval(days: number, dataLength: number): number | 'preserveStartEnd' {
  if (days <= 7) return 0;                    // 5일: 모든 데이터 표시
  if (days <= 30) return Math.ceil(dataLength / 8);   // 1개월: 약 8개 틱
  if (days <= 90) return Math.ceil(dataLength / 6);   // 3개월: 약 6개 틱
  return Math.ceil(dataLength / 5);           // 1년: 약 5개 틱
}

// ====================================
// Phase 2 개선: 유틸리티 함수들
// ====================================

/**
 * 볼륨 이상치 처리 - 95 퍼센타일 기준 스케일링
 * 극단적인 거래량 때문에 평소 거래량이 너무 작아 보이는 문제 해결
 */
function calculateVolumeScale(volumes: number[]): { maxVolume: number; p95Volume: number } {
  if (volumes.length === 0) return { maxVolume: 0, p95Volume: 0 };

  const sorted = [...volumes].sort((a, b) => a - b);
  const p95Index = Math.floor(sorted.length * 0.95);
  const p95Volume = sorted[p95Index] || sorted[sorted.length - 1];
  const maxVolume = Math.max(...volumes);

  // 95 퍼센타일의 1.2배를 최대값으로 사용 (이상치 무시)
  return {
    maxVolume: maxVolume,
    p95Volume: p95Volume * 1.2,
  };
}

/**
 * 20일 이동평균 거래량 계산
 */
function calculateVolumeMA(data: { volume: number }[], period: number = 20): (number | null)[] {
  return data.map((_, index) => {
    if (index < period - 1) return null; // 데이터 부족

    const slice = data.slice(index - period + 1, index + 1);
    const sum = slice.reduce((acc, d) => acc + d.volume, 0);
    return sum / period;
  });
}

/**
 * 반응형 차트 높이 계산
 */
function getResponsiveChartHeight(windowWidth: number): { price: number; volume: number } {
  if (windowWidth < 640) {
    // 모바일
    return { price: 280, volume: 70 };
  } else if (windowWidth < 1024) {
    // 태블릿
    return { price: 320, volume: 80 };
  }
  // 데스크톱
  return { price: 350, volume: 90 };
}

interface CandleData {
  date: string;
  dateRaw: Date;  // 원본 Date 객체 (X축 포맷팅용)
  timestamp: number;
  open_price: number;
  high_price: number;
  low_price: number;
  close_price: number;
  volume: number;
  previousClose: number;  // 전일 종가 (볼륨 색상 결정용)
  volumeMA20: number | null;  // Phase 3: 20일 이동평균 거래량
  // 캔들스틱 렌더링용 계산 필드
  candleBody: [number, number]; // [시가, 종가] 또는 [종가, 시가]
  candleWick: [number, number]; // [저가, 고가]
  isUp: boolean; // 상승 여부 (시가 기준 - 캔들 색상용)
  isUpFromPrev: boolean; // 전일 대비 상승 여부 (볼륨 색상용) - 업계 표준
}

// 커스텀 캔들스틱 Shape
const CandlestickShape = (props: any) => {
  const { x, y, width, height, payload } = props;
  if (!payload) return null;

  const { open_price, close_price, high_price, low_price, isUp } = payload;
  const color = isUp ? CANDLE_UP_COLOR : CANDLE_DOWN_COLOR;

  // 캔들 본체의 Y 좌표 계산 (y는 이미 recharts에서 계산됨)
  const bodyTop = Math.min(open_price, close_price);
  const bodyBottom = Math.max(open_price, close_price);
  const bodyHeight = Math.abs(height) || 1;

  // 심지 위치 계산 (차트 스케일에 맞춰 계산 필요)
  const candleWidth = Math.max(width * 0.8, 2);
  const wickX = x + width / 2;

  return (
    <g>
      {/* 캔들 본체 */}
      <rect
        x={x + (width - candleWidth) / 2}
        y={y}
        width={candleWidth}
        height={Math.max(bodyHeight, 1)}
        fill={color}
        stroke={color}
        strokeWidth={1}
      />
    </g>
  );
};

// 심지를 그리기 위한 커스텀 컴포넌트
const CandleWick = (props: any) => {
  const { x, y, width, height, payload } = props;
  if (!payload) return null;

  const { isUp } = payload;
  const color = isUp ? CANDLE_UP_COLOR : CANDLE_DOWN_COLOR;
  const wickX = x + width / 2;

  return (
    <line
      x1={wickX}
      y1={y}
      x2={wickX}
      y2={y + height}
      stroke={color}
      strokeWidth={1}
    />
  );
};

export default function StockChart({ symbol }: StockChartProps) {
  const [chartData, setChartData] = useState<CandleData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState('1m');

  // Phase 2, 3 옵션 상태
  const [colorTheme, setColorTheme] = useState<ColorTheme>('default');
  const [showVolumeMA, setShowVolumeMA] = useState(true);  // Phase 3: 거래량 이동평균선
  const [useLogScale, setUseLogScale] = useState(false);   // Phase 3: 로그 스케일
  const [showSettings, setShowSettings] = useState(false); // 설정 패널 토글

  // Phase 2: 반응형 차트 높이
  const [chartHeight, setChartHeight] = useState({ price: 350, volume: 90 });

  // 반응형 높이 계산
  useEffect(() => {
    const handleResize = () => {
      setChartHeight(getResponsiveChartHeight(window.innerWidth));
    };
    handleResize(); // 초기값 설정
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const currentOption = PERIOD_OPTIONS.find(opt => opt.value === selectedPeriod) || PERIOD_OPTIONS[1];

  // 현재 테마 색상
  const colors = COLOR_THEMES[colorTheme];

  useEffect(() => {
    loadChartData();
  }, [symbol, selectedPeriod]);

  const loadChartData = async () => {
    try {
      setLoading(true);
      setError(null);

      const periodParam = currentOption.period === 'days'
        ? `days=${currentOption.days}`
        : currentOption.period;

      const response = await stockService.getChartData(
        symbol.toUpperCase(),
        currentOption.chartType as 'daily' | 'weekly',
        periodParam
      );

      // 먼저 정렬된 raw 데이터 생성
      const sortedRawData = response.data
        .map((item: any) => ({
          date: new Date(item.time),
          open: Number(item.open),
          close: Number(item.close),
          high: Number(item.high),
          low: Number(item.low),
          volume: Number(item.volume),
        }))
        .sort((a: any, b: any) => a.date.getTime() - b.date.getTime());

      // Phase 3: 20일 이동평균 거래량 계산
      const volumeMA20Array = calculateVolumeMA(sortedRawData, 20);

      // 전일 종가 기준으로 데이터 변환
      const transformedData: CandleData[] = sortedRawData.map((item: any, index: number) => {
        const { date, open, close, high, low, volume } = item;
        const isUp = close >= open; // 캔들 색상용 (시가 기준)

        // 전일 종가 (첫 번째 데이터는 시가 사용)
        const previousClose = index > 0 ? sortedRawData[index - 1].close : open;
        const isUpFromPrev = close >= previousClose; // 볼륨 색상용 (전일 종가 기준)

        return {
          date: getDateFormat(currentOption.days, date), // 기간별 동적 포맷
          dateRaw: date,
          timestamp: date.getTime(),
          open_price: open,
          high_price: high,
          low_price: low,
          close_price: close,
          volume: volume,
          previousClose: previousClose,
          volumeMA20: volumeMA20Array[index],  // Phase 3: 20일 이동평균
          // 캔들 바디: [min, max] 형태로 저장 (Bar 차트에서 사용)
          candleBody: (isUp ? [open, close] : [close, open]) as [number, number],
          candleWick: [low, high] as [number, number],
          isUp,
          isUpFromPrev,
        };
      });

      setChartData(transformedData);
    } catch (err) {
      console.error('Failed to load chart data:', err);
      setError('차트 데이터를 불러오는 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  // 캔들스틱 툴팁
  const CandleTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length > 0) {
      const data = payload[0].payload;
      const change = data.close_price - data.open_price;
      const changePercent = data.open_price > 0 ? (change / data.open_price) * 100 : 0;

      return (
        <div className="bg-white dark:bg-gray-800 p-3 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700">
          <p className="text-sm font-medium text-gray-900 dark:text-white mb-2">{label}</p>
          <div className="space-y-1 text-xs">
            <div className="flex justify-between gap-4">
              <span className="text-gray-500">시가:</span>
              <span className="font-medium">{formatCurrency(data.open_price)}</span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-gray-500">고가:</span>
              <span className="font-medium text-green-600">{formatCurrency(data.high_price)}</span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-gray-500">저가:</span>
              <span className="font-medium text-red-600">{formatCurrency(data.low_price)}</span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-gray-500">종가:</span>
              <span className={`font-medium ${data.isUp ? 'text-green-600' : 'text-red-600'}`}>
                {formatCurrency(data.close_price)}
              </span>
            </div>
            <div className="flex justify-between gap-4 pt-1 border-t border-gray-200 dark:border-gray-600">
              <span className="text-gray-500">변동:</span>
              <span className={`font-medium ${data.isUp ? 'text-green-600' : 'text-red-600'}`}>
                {data.isUp ? '+' : ''}{formatCurrency(change)} ({changePercent.toFixed(2)}%)
              </span>
            </div>
          </div>
        </div>
      );
    }
    return null;
  };

  // 거래량 툴팁 - Phase 1: 전일 종가 기준 정보 표시
  const VolumeTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length > 0) {
      const data = payload[0].payload;
      const changeFromPrev = data.close_price - data.previousClose;
      const changePercent = data.previousClose > 0 ? (changeFromPrev / data.previousClose) * 100 : 0;

      return (
        <div className="bg-white dark:bg-gray-800 p-2 rounded shadow-lg border border-gray-200 dark:border-gray-700">
          <p className="text-xs font-medium mb-1">{data.date}</p>
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${data.isUpFromPrev ? 'bg-green-500' : 'bg-red-500'}`}></span>
            <span className="text-xs">
              거래량: {formatVolume(data.volume)}
            </span>
          </div>
          <div className="text-xs text-gray-500 mt-1 space-y-0.5">
            <p>전일 종가: {formatCurrency(data.previousClose)}</p>
            <p className={data.isUpFromPrev ? 'text-green-600' : 'text-red-600'}>
              변동: {data.isUpFromPrev ? '+' : ''}{formatCurrency(changeFromPrev)} ({changePercent.toFixed(2)}%)
            </p>
          </div>
        </div>
      );
    }
    return null;
  };

  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/4 mb-4"></div>
          <div className="h-64 bg-gray-200 dark:bg-gray-700 rounded"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6">
        <div className="text-center text-red-600 dark:text-red-400">
          <p>{error}</p>
          <button
            onClick={loadChartData}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            다시 시도
          </button>
        </div>
      </div>
    );
  }

  // Empty data state - 차트 데이터가 없을 경우
  if (chartData.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">주가 차트</h3>
          </div>
          <div className="flex space-x-1">
            {PERIOD_OPTIONS.map((option) => (
              <button
                key={option.value}
                onClick={() => setSelectedPeriod(option.value)}
                className={`px-3 py-1 text-xs rounded transition-colors ${
                  selectedPeriod === option.value
                    ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>
        <div className="flex flex-col items-center justify-center py-16 px-4">
          <div className="w-16 h-16 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center mb-4">
            <BarChart3 className="h-8 w-8 text-gray-400 dark:text-gray-500" />
          </div>
          <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
            차트 데이터가 없습니다
          </h4>
          <p className="text-sm text-gray-500 dark:text-gray-400 text-center max-w-sm mb-4">
            이 종목의 가격 데이터가 아직 수집되지 않았거나, 거래가 없는 종목입니다.
          </p>
          <button
            onClick={loadChartData}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
          >
            다시 시도
          </button>
        </div>
      </div>
    );
  }

  // Calculate price change
  const firstPrice = chartData.length > 0 ? chartData[0].close_price : 0;
  const lastPrice = chartData.length > 0 ? chartData[chartData.length - 1].close_price : 0;
  const priceChange = lastPrice - firstPrice;
  const priceChangePercent = firstPrice > 0 ? (priceChange / firstPrice) * 100 : 0;
  const isPositive = isProfit(priceChange);

  // 가격 범위 계산 (차트 Y축) - Phase 1 개선: Nice Numbers + 15% 마진
  const prices = chartData.flatMap(d => [d.high_price, d.low_price]);
  const rawMinPrice = Math.min(...prices);
  const rawMaxPrice = Math.max(...prices);

  // 15% 마진 적용 (기존 10%에서 확대)
  const priceRange = rawMaxPrice - rawMinPrice;
  const priceMargin = Math.max(priceRange * 0.15, rawMinPrice * 0.02); // 최소 2% 여백 보장
  const minPriceWithMargin = rawMinPrice - priceMargin;
  const maxPriceWithMargin = rawMaxPrice + priceMargin;

  // Nice Numbers 계산 (깔끔한 숫자로 Y축 틱 표시)
  const niceScale = calculateNiceScale(minPriceWithMargin, maxPriceWithMargin, 6);

  // Phase 2: 거래량 범위 계산 (95 퍼센타일 기준 - 이상치 처리)
  const volumes = chartData.map(d => d.volume);
  const volumeScale = calculateVolumeScale(volumes);
  const volumeDomainMax = volumeScale.p95Volume; // 이상치 무시한 최대값

  // X축 틱 간격 계산
  const xAxisInterval = getTickInterval(currentOption.days, chartData.length);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-6">
      {/* Chart Header */}
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">주가 차트</h3>
          <div className="flex items-center mt-2 space-x-4">
            <span className="text-2xl font-bold text-gray-900 dark:text-white">
              {formatCurrency(lastPrice)}
            </span>
            <div className={`flex items-center ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
              {isPositive ? <TrendingUp className="h-4 w-4 mr-1" /> : <TrendingDown className="h-4 w-4 mr-1" />}
              <span className="font-medium">
                {getProfitSign(priceChange)}{formatCurrency(priceChange)} ({priceChangePercent.toFixed(2)}%)
              </span>
            </div>
          </div>
        </div>

        {/* Period Selector + Settings */}
        <div className="flex items-center gap-2">
          <div className="flex space-x-1">
            {PERIOD_OPTIONS.map((option) => (
              <button
                key={option.value}
                onClick={() => setSelectedPeriod(option.value)}
                className={`px-3 py-1 text-xs rounded transition-colors ${
                  selectedPeriod === option.value
                    ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>

          {/* Phase 2/3: 설정 버튼 */}
          <div className="relative">
            <button
              onClick={() => setShowSettings(!showSettings)}
              className={`p-1.5 rounded transition-colors ${
                showSettings
                  ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
              }`}
              title="차트 설정"
            >
              <Settings2 className="h-4 w-4" />
            </button>

            {/* 설정 패널 */}
            {showSettings && (
              <div className="absolute right-0 top-full mt-2 w-56 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-10 p-3">
                <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-3">차트 설정</h4>

                {/* 색상 테마 */}
                <div className="mb-3">
                  <label className="text-xs text-gray-500 dark:text-gray-400 mb-1 block">색상 테마</label>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setColorTheme('default')}
                      className={`flex-1 px-2 py-1 text-xs rounded ${
                        colorTheme === 'default'
                          ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
                          : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
                      }`}
                    >
                      <span className="flex items-center justify-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-green-500"></span>
                        <span className="w-2 h-2 rounded-full bg-red-500"></span>
                        기본
                      </span>
                    </button>
                    <button
                      onClick={() => setColorTheme('accessible')}
                      className={`flex-1 px-2 py-1 text-xs rounded ${
                        colorTheme === 'accessible'
                          ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
                          : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
                      }`}
                    >
                      <span className="flex items-center justify-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                        <span className="w-2 h-2 rounded-full bg-orange-500"></span>
                        색맹용
                      </span>
                    </button>
                  </div>
                </div>

                {/* 거래량 이동평균선 */}
                <label className="flex items-center gap-2 text-xs cursor-pointer mb-2">
                  <input
                    type="checkbox"
                    checked={showVolumeMA}
                    onChange={(e) => setShowVolumeMA(e.target.checked)}
                    className="rounded border-gray-300"
                  />
                  <span className="text-gray-700 dark:text-gray-300">20일 평균 거래량</span>
                </label>

                {/* 로그 스케일 */}
                <label className="flex items-center gap-2 text-xs cursor-pointer">
                  <input
                    type="checkbox"
                    checked={useLogScale}
                    onChange={(e) => setUseLogScale(e.target.checked)}
                    className="rounded border-gray-300"
                  />
                  <span className="text-gray-700 dark:text-gray-300">로그 스케일</span>
                </label>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Candlestick Chart - Phase 2: 반응형 높이 */}
      <ResponsiveContainer width="100%" height={chartHeight.price}>
        <ComposedChart data={chartData} margin={{ top: 10, right: 60, left: 10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" vertical={false} />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11 }}
            stroke="#9CA3AF"
            tickLine={false}
            axisLine={{ stroke: '#E5E7EB' }}
            interval={xAxisInterval}  // Phase 1: 기간별 동적 틱 간격
          />
          <YAxis
            orientation="right"
            domain={[niceScale.min, niceScale.max]}  // Phase 1: Nice Numbers 적용
            ticks={niceScale.ticks}  // Phase 1: 깔끔한 숫자 틱
            tick={{ fontSize: 11 }}
            stroke="#9CA3AF"
            tickFormatter={formatPriceForAxis}  // Phase 1: 가격대별 소수점 포맷
            tickLine={false}
            axisLine={false}
            width={55}
            scale={useLogScale ? 'log' : 'auto'}  // Phase 3: 로그 스케일
          />
          <Tooltip content={<CandleTooltip />} />

          {/* 심지 (Wick) - 저가~고가 */}
          <Bar
            dataKey="candleWick"
            barSize={1}
            shape={(props: any) => {
              const { x, y, width, height, payload } = props;
              if (!payload) return <g />;
              const color = payload.isUp ? colors.up : colors.down;  // Phase 2: 테마 색상
              return (
                <line
                  x1={x + width / 2}
                  y1={y}
                  x2={x + width / 2}
                  y2={y + height}
                  stroke={color}
                  strokeWidth={1}
                />
              );
            }}
          />

          {/* 캔들 본체 (Body) - 시가~종가 */}
          <Bar
            dataKey="candleBody"
            barSize={8}
            shape={(props: any) => {
              const { x, y, width, height, payload } = props;
              if (!payload) return <g />;
              const color = payload.isUp ? colors.up : colors.down;  // Phase 2: 테마 색상
              const candleWidth = Math.max(width * 0.8, 4);
              const bodyHeight = Math.max(Math.abs(height), 2);

              return (
                <rect
                  x={x + (width - candleWidth) / 2}
                  y={y}
                  width={candleWidth}
                  height={bodyHeight}
                  fill={color}
                  stroke={color}
                  strokeWidth={1}
                  rx={1}
                />
              );
            }}
          />
        </ComposedChart>
      </ResponsiveContainer>

      {/* Volume Chart - Phase 2/3: 반응형, 테마 색상, 이동평균선 */}
      <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <p className="text-sm text-gray-500 dark:text-gray-400">거래량</p>
            {showVolumeMA && (
              <span className="text-xs text-gray-400 dark:text-gray-500">
                (20일 평균: <span style={{ color: colors.avgLine }}>━</span>)
              </span>
            )}
          </div>
          <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
            <div className="flex items-center gap-1">
              <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: colors.up }}></span>
              <span>전일 대비 상승</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: colors.down }}></span>
              <span>전일 대비 하락</span>
            </div>
          </div>
        </div>
        <ResponsiveContainer width="100%" height={chartHeight.volume}>
          <ComposedChart data={chartData} margin={{ top: 0, right: 60, left: 10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" vertical={false} />
            <XAxis dataKey="date" hide />
            <YAxis
              orientation="right"
              domain={[0, volumeDomainMax]}  // Phase 2: 95 퍼센타일 기준
              tick={{ fontSize: 10 }}
              stroke="#9CA3AF"
              tickFormatter={(value) => {
                if (value >= 1000000000) return `${(value / 1000000000).toFixed(1)}B`;
                if (value >= 1000000) return `${(value / 1000000).toFixed(0)}M`;
                if (value >= 1000) return `${(value / 1000).toFixed(0)}K`;
                return value.toString();
              }}
              tickLine={false}
              axisLine={false}
              width={55}
            />
            <Tooltip content={<VolumeTooltip />} />
            <Bar dataKey="volume" barSize={8}>
              {chartData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.isUpFromPrev ? colors.up : colors.down}  // Phase 2: 테마 색상
                  fillOpacity={0.7}
                />
              ))}
            </Bar>

            {/* Phase 3: 20일 이동평균 거래량 */}
            {showVolumeMA && (
              <Line
                type="monotone"
                dataKey="volumeMA20"
                stroke={colors.avgLine}
                strokeWidth={1.5}
                dot={false}
                connectNulls={false}
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

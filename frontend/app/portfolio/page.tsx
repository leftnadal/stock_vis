'use client'

import { useEffect, useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { useRouter } from 'next/navigation'
import { portfolioService, Portfolio, PortfolioSummary as IPortfolioSummary } from '@/services/portfolio'
import PortfolioSummary from '@/components/portfolio/PortfolioSummary'
import PortfolioStockCard from '@/components/portfolio/PortfolioStockCard'
import PortfolioModal from '@/components/portfolio/PortfolioModal'
import PortfolioChart from '@/components/portfolio/PortfolioChart'
import PortfolioTable from '@/components/portfolio/PortfolioTable'
import { Plus, RefreshCw, PieChart, BarChart2, Grid, Table } from 'lucide-react'

export default function PortfolioPage() {
  const { isAuthenticated, loading: authLoading } = useAuth()
  const router = useRouter()

  const [portfolios, setPortfolios] = useState<Portfolio[]>([])
  const [summary, setSummary] = useState<IPortfolioSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingPortfolio, setEditingPortfolio] = useState<Portfolio | null>(null)
  const [chartType, setChartType] = useState<'pie' | 'bar'>('pie')
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid')

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login')
    } else if (isAuthenticated) {
      loadPortfolioData()
    }
  }, [authLoading, isAuthenticated, router])

  const loadPortfolioData = async () => {
    try {
      setLoading(true)
      setError(null)

      const [portfolioData, summaryData] = await Promise.all([
        portfolioService.getPortfolios(),
        portfolioService.getPortfolioSummary()
      ])

      setPortfolios(portfolioData)
      setSummary(summaryData)
    } catch (err) {
      console.error('포트폴리오 데이터 로드 실패:', err)
      setError('포트폴리오 데이터를 불러오는 중 오류가 발생했습니다.')
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    await loadPortfolioData()
    setRefreshing(false)
  }

  const handleOpenModal = (portfolio?: Portfolio) => {
    if (portfolio) {
      setEditingPortfolio(portfolio)
    } else {
      setEditingPortfolio(null)
    }
    setIsModalOpen(true)
  }

  const handleCloseModal = () => {
    setIsModalOpen(false)
    setEditingPortfolio(null)
  }

  const handleModalSuccess = () => {
    loadPortfolioData()
  }

  if (authLoading || loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return null
  }

  // Transform portfolio data for PortfolioStockCard component
  const transformedPortfolios = portfolios.map(portfolio => ({
    symbol: portfolio.stock_symbol,
    name: portfolio.stock_name,
    shares: parseFloat(portfolio.quantity),
    avgPrice: parseFloat(portfolio.average_price),
    currentPrice: parseFloat(portfolio.current_price),
    value: portfolio.total_value,
    gain: portfolio.profit_loss,
    gainPercent: portfolio.profit_loss_percentage
  }))

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            내 포트폴리오
          </h1>
          <div className="flex space-x-3">
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="flex items-center px-4 py-2 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
              새로고침
            </button>
            <button
              onClick={() => handleOpenModal()}
              className="flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
            >
              <Plus className="h-4 w-4 mr-2" />
              종목 추가
            </button>
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <p className="text-red-600">{error}</p>
          </div>
        )}

        {/* Portfolio Summary */}
        <PortfolioSummary
          totalValue={summary ? Number(summary.total_value) : 0}
          totalGain={summary ? Number(summary.total_profit_loss) : 0}
          totalGainPercent={summary ? Number(summary.total_profit_loss_percentage) : 0}
          todayGain={0} // TODO: Calculate today's gain
          todayGainPercent={0} // TODO: Calculate today's gain percentage
          onAddStock={() => handleOpenModal()}
        />

        {/* Charts Section */}
        {portfolios.length > 0 && (
          <div className="mt-8">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                포트폴리오 분석
              </h2>
              <div className="flex space-x-2">
                <button
                  onClick={() => setChartType('pie')}
                  className={`flex items-center px-3 py-1.5 rounded-lg transition-colors ${
                    chartType === 'pie'
                      ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
                      : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                  }`}
                >
                  <PieChart className="h-4 w-4 mr-1" />
                  구성비
                </button>
                <button
                  onClick={() => setChartType('bar')}
                  className={`flex items-center px-3 py-1.5 rounded-lg transition-colors ${
                    chartType === 'bar'
                      ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
                      : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                  }`}
                >
                  <BarChart2 className="h-4 w-4 mr-1" />
                  수익률
                </button>
              </div>
            </div>
            <PortfolioChart portfolios={portfolios} chartType={chartType} />
          </div>
        )}

        {/* Portfolio Grid/Table */}
        <div className="mt-8">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              보유 종목 ({portfolios.length})
            </h2>
            {portfolios.length > 0 && (
              <div className="flex space-x-2">
                <button
                  onClick={() => setViewMode('grid')}
                  className={`flex items-center px-3 py-1.5 rounded-lg transition-colors ${
                    viewMode === 'grid'
                      ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
                      : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                  }`}
                >
                  <Grid className="h-4 w-4 mr-1" />
                  카드
                </button>
                <button
                  onClick={() => setViewMode('table')}
                  className={`flex items-center px-3 py-1.5 rounded-lg transition-colors ${
                    viewMode === 'table'
                      ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
                      : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                  }`}
                >
                  <Table className="h-4 w-4 mr-1" />
                  테이블
                </button>
              </div>
            )}
          </div>

          {portfolios.length === 0 ? (
            <div className="bg-white dark:bg-gray-800 rounded-xl p-12 text-center">
              <div className="max-w-md mx-auto">
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                  아직 포트폴리오가 비어있습니다
                </h3>
                <p className="text-gray-500 dark:text-gray-400 mb-6">
                  첫 번째 종목을 추가하여 포트폴리오를 시작하세요.
                </p>
                <button
                  onClick={() => handleOpenModal()}
                  className="inline-flex items-center px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                >
                  <Plus className="h-5 w-5 mr-2" />
                  첫 종목 추가하기
                </button>
              </div>
            </div>
          ) : viewMode === 'table' ? (
            <PortfolioTable />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {portfolios.map((portfolio) => {
                const transformedStock = {
                  symbol: portfolio.stock_symbol,
                  name: portfolio.stock_name,
                  shares: parseFloat(portfolio.quantity),
                  avgPrice: parseFloat(portfolio.average_price),
                  currentPrice: parseFloat(portfolio.current_price),
                  value: portfolio.total_value,
                  gain: portfolio.profit_loss,
                  gainPercent: portfolio.profit_loss_percentage
                }
                return (
                  <div key={portfolio.id} onClick={() => handleOpenModal(portfolio)}>
                    <PortfolioStockCard stock={transformedStock} />
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Portfolio Modal */}
        <PortfolioModal
          isOpen={isModalOpen}
          onClose={handleCloseModal}
          onSuccess={handleModalSuccess}
          editingPortfolio={editingPortfolio}
        />
      </div>
    </div>
  )
}
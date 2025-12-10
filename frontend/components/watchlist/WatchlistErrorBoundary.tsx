'use client'

import { Component, ReactNode } from 'react'
import { AlertCircle, RefreshCw } from 'lucide-react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error?: Error
  errorInfo?: string
}

export default class WatchlistErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
    }
  }

  componentDidCatch(error: Error, errorInfo: any) {
    console.error('WatchlistErrorBoundary caught an error:', error, errorInfo)
    this.setState({
      errorInfo: errorInfo.componentStack,
    })
  }

  handleReset = () => {
    this.setState({ hasError: false, error: undefined, errorInfo: undefined })
    window.location.reload()
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg max-w-lg w-full p-8">
            <div className="flex flex-col items-center text-center space-y-4">
              <div className="p-3 bg-red-100 dark:bg-red-900/30 rounded-full">
                <AlertCircle className="h-12 w-12 text-red-600 dark:text-red-400" />
              </div>

              <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                문제가 발생했습니다
              </h2>

              <p className="text-gray-600 dark:text-gray-400">
                관심종목 페이지를 표시하는 중 오류가 발생했습니다.
                <br />
                페이지를 새로고침하면 문제가 해결될 수 있습니다.
              </p>

              {this.state.error && (
                <details className="w-full mt-4">
                  <summary className="cursor-pointer text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300">
                    에러 상세 정보
                  </summary>
                  <div className="mt-2 p-4 bg-gray-100 dark:bg-gray-700 rounded-lg text-left">
                    <p className="text-sm font-mono text-red-600 dark:text-red-400 break-all">
                      {this.state.error.toString()}
                    </p>
                    {this.state.errorInfo && (
                      <pre className="mt-2 text-xs text-gray-600 dark:text-gray-400 overflow-auto max-h-40">
                        {this.state.errorInfo}
                      </pre>
                    )}
                  </div>
                </details>
              )}

              <div className="flex space-x-3 w-full justify-center mt-6">
                <button
                  onClick={this.handleReset}
                  className="inline-flex items-center space-x-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
                >
                  <RefreshCw className="h-5 w-5" />
                  <span>페이지 새로고침</span>
                </button>
              </div>

              <p className="text-sm text-gray-500 dark:text-gray-400">
                문제가 계속되면 관리자에게 문의해주세요.
              </p>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

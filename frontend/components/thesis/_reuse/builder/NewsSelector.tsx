'use client'

import { useState, useEffect } from 'react'
import { Newspaper, ArrowLeft, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { authAxios } from '@/lib/api/authAxios'

interface NewsItem {
  id: string
  title: string
  summary: string
  source: string
  published_at: string
  sentiment_score: number | null
  category: string
}

interface NewsSelectorProps {
  onSelect: (newsId: string, title: string) => void
  onBack: () => void
}

function sentimentIcon(score: number | null) {
  if (score === null) return <Minus size={14} className="text-gray-500" />
  if (score > 0.2) return <TrendingUp size={14} className="text-blue-400" />
  if (score < -0.2) return <TrendingDown size={14} className="text-red-400" />
  return <Minus size={14} className="text-gray-500" />
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const hours = Math.floor(diff / 3600000)
  if (hours < 1) return '방금'
  if (hours < 24) return `${hours}시간 전`
  const days = Math.floor(hours / 24)
  return `${days}일 전`
}

export function NewsSelector({ onSelect, onBack }: NewsSelectorProps) {
  const [articles, setArticles] = useState<NewsItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    fetchNews()
  }, [])

  async function fetchNews() {
    try {
      setIsLoading(true)
      const res = await authAxios.get('/news/', {
        params: { ordering: '-published_at', page_size: 15 },
      })
      const data = res.data?.results ?? res.data ?? []
      setArticles(Array.isArray(data) ? data.slice(0, 15) : [])
    } catch {
      setError(true)
    } finally {
      setIsLoading(false)
    }
  }

  if (isLoading) {
    return (
      <div className="flex flex-col h-full">
        <Header onBack={onBack} />
        <div className="flex-1 flex items-center justify-center">
          <div className="flex gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-gray-500 animate-bounce [animation-delay:0ms]" />
            <span className="w-1.5 h-1.5 rounded-full bg-gray-500 animate-bounce [animation-delay:200ms]" />
            <span className="w-1.5 h-1.5 rounded-full bg-gray-500 animate-bounce [animation-delay:400ms]" />
          </div>
        </div>
      </div>
    )
  }

  if (error || articles.length === 0) {
    return (
      <div className="flex flex-col h-full">
        <Header onBack={onBack} />
        <div className="flex-1 flex flex-col items-center justify-center gap-3 px-8">
          <Newspaper size={32} className="text-gray-600" />
          <p className="text-gray-400 text-sm text-center">
            {error ? '뉴스를 불러오지 못했어요.' : '최근 뉴스가 없어요.'}
          </p>
          <button
            onClick={onBack}
            className="text-blue-400 text-sm mt-2"
          >
            내 생각으로 시작하기
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      <Header onBack={onBack} />
      <div className="flex-1 overflow-y-auto px-4 pt-2 pb-4">
        <p className="text-xs text-gray-500 mb-3">가설을 세울 이슈를 선택하세요</p>
        <div className="space-y-2">
          {articles.map((article) => (
            <button
              key={article.id}
              onClick={() => onSelect(article.id, article.title)}
              className="w-full text-left p-3 bg-gray-900 border border-gray-800
                         rounded-xl hover:border-gray-600 active:scale-[0.99]
                         transition-all"
            >
              <div className="flex items-start gap-2">
                <div className="flex-shrink-0 mt-0.5">
                  {sentimentIcon(article.sentiment_score)}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-white font-medium line-clamp-2">
                    {article.title}
                  </p>
                  {article.summary && (
                    <p className="text-xs text-gray-400 mt-1 line-clamp-1">
                      {article.summary}
                    </p>
                  )}
                  <div className="flex items-center gap-2 mt-1.5">
                    <span className="text-[10px] text-gray-500">{article.source}</span>
                    <span className="text-[10px] text-gray-600">·</span>
                    <span className="text-[10px] text-gray-500">{timeAgo(article.published_at)}</span>
                  </div>
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

function Header({ onBack }: { onBack: () => void }) {
  return (
    <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-800">
      <button onClick={onBack} className="p-1 text-gray-400 hover:text-white">
        <ArrowLeft size={20} />
      </button>
      <h1 className="text-white text-base font-medium">오늘 이슈 선택</h1>
    </div>
  )
}

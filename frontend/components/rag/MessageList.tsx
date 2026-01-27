'use client'

import { useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import { Bot, User } from 'lucide-react'
import type { Message } from '@/types/rag'

interface MessageListProps {
  messages: Message[]
  streamedContent?: string
  isStreaming?: boolean
}

export function MessageList({ messages, streamedContent, isStreaming }: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // 자동 스크롤
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamedContent])

  const formatTime = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleTimeString('ko-KR', {
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <div className="flex-1 space-y-4 overflow-y-auto px-4 py-6">
      {messages.length === 0 && !streamedContent ? (
        <div className="flex h-full items-center justify-center">
          <div className="text-center">
            <Bot className="mx-auto h-12 w-12 text-slate-300 dark:text-slate-600" />
            <p className="mt-4 text-sm font-medium text-slate-600 dark:text-slate-400">
              AI 투자 분석을 시작해보세요
            </p>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-500">
              아래에 질문을 입력하거나 제안 칩을 클릭하세요
            </p>
          </div>
        </div>
      ) : (
        <>
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex gap-3 ${
                message.role === 'user' ? 'flex-row-reverse' : 'flex-row'
              }`}
            >
              {/* 아바타 */}
              <div className="flex-shrink-0">
                <div
                  className={`flex h-8 w-8 items-center justify-center rounded-full ${
                    message.role === 'user'
                      ? 'bg-blue-100 dark:bg-blue-900'
                      : 'bg-slate-100 dark:bg-slate-700'
                  }`}
                >
                  {message.role === 'user' ? (
                    <User className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                  ) : (
                    <Bot className="h-4 w-4 text-slate-600 dark:text-slate-400" />
                  )}
                </div>
              </div>

              {/* 메시지 내용 */}
              <div
                className={`max-w-[80%] ${
                  message.role === 'user' ? 'items-end' : 'items-start'
                } flex flex-col`}
              >
                <div
                  className={`rounded-2xl px-4 py-2.5 ${
                    message.role === 'user'
                      ? 'bg-blue-600 text-white dark:bg-blue-500'
                      : 'bg-slate-100 text-slate-900 dark:bg-slate-800 dark:text-slate-100'
                  }`}
                >
                  {message.role === 'user' ? (
                    <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                  ) : (
                    <div className="prose prose-sm dark:prose-invert max-w-none">
                      <ReactMarkdown>{message.content}</ReactMarkdown>
                    </div>
                  )}
                </div>

                {/* 타임스탬프 & 메타데이터 */}
                <div
                  className={`mt-1 flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 ${
                    message.role === 'user' ? 'flex-row-reverse' : 'flex-row'
                  }`}
                >
                  <span>{formatTime(message.created_at)}</span>
                  {message.usage && (
                    <span>
                      • {message.usage.input_tokens + message.usage.output_tokens} tokens
                    </span>
                  )}
                  {message.latency_ms && (
                    <span>• {(message.latency_ms / 1000).toFixed(2)}s</span>
                  )}
                </div>
              </div>
            </div>
          ))}

          {/* 스트리밍 중인 메시지 */}
          {isStreaming && streamedContent && (
            <div className="flex gap-3">
              <div className="flex-shrink-0">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-100 dark:bg-slate-700">
                  <Bot className="h-4 w-4 text-slate-600 dark:text-slate-400" />
                </div>
              </div>

              <div className="max-w-[80%] flex-col">
                <div className="rounded-2xl bg-slate-100 px-4 py-2.5 text-slate-900 dark:bg-slate-800 dark:text-slate-100">
                  <div className="prose prose-sm dark:prose-invert max-w-none">
                    <ReactMarkdown>{streamedContent}</ReactMarkdown>
                  </div>
                  {/* 타이핑 애니메이션 */}
                  <span className="inline-block h-4 w-1 animate-pulse bg-slate-600 dark:bg-slate-400" />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </>
      )}
    </div>
  )
}

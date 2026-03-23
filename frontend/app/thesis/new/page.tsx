'use client'

import { useState, useEffect, useRef, Suspense } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { ArrowLeft } from 'lucide-react'
import Link from 'next/link'
import { thesisApi } from '@/lib/thesis/api'
import {
  USE_MOCK, MOCK_CONVERSATION_START_NEWS,
  MOCK_CONVERSATION_START_FREE, MOCK_NEWS_STEP_MAP, MOCK_FREE_STEP_MAP,
  MOCK_CONVERSATION_DONE,
  MOCK_LLM_START, MOCK_LLM_STEP_MAP,
} from '@/lib/thesis/mock'
import { ENTRY_SOURCES, type EntrySource, type ConversationButton } from '@/lib/thesis/types'
import { PresetSelector } from '@/components/thesis/PresetSelector'
import { IndicatorCard } from '@/components/thesis/IndicatorCard'
import { AddIndicatorSheet } from '@/components/thesis/AddIndicatorSheet'
import {
  type BuilderState, INITIAL_BUILDER_STATE, applyResponse, selectionToLabel,
  generateMessageId, saveConvId, clearConvId,
} from '@/lib/thesis/conversation'
import { ChatBubble } from '@/components/thesis/builder/ChatBubble'
import { OptionButton } from '@/components/thesis/builder/OptionButton'
import { PremiseCard } from '@/components/thesis/builder/PremiseCard'
import { MultiSelectFooter } from '@/components/thesis/builder/MultiSelectFooter'
import { TextInput } from '@/components/thesis/builder/TextInput'
import { BottomSheet } from '@/components/thesis/common/BottomSheet'
import { ProgressBar } from '@/components/thesis/builder/ProgressBar'
import { NewsSelector } from '@/components/thesis/builder/NewsSelector'

function toEntrySource(value: string | null): EntrySource {
  if (value && (ENTRY_SOURCES as readonly string[]).includes(value)) return value as EntrySource
  return 'free_input'
}

export default function ThesisNewPage() {
  return (
    <Suspense fallback={
      <div className="flex flex-col h-[calc(100dvh-env(safe-area-inset-top))] bg-gray-950">
        <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-800">
          <div className="p-1 text-gray-400"><ArrowLeft size={20} /></div>
          <h1 className="text-white text-base font-medium flex-1">가설 세우기</h1>
        </div>
        <div className="flex-1 flex items-center justify-center">
          <div className="flex gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-gray-500 animate-bounce [animation-delay:0ms]" />
            <span className="w-1.5 h-1.5 rounded-full bg-gray-500 animate-bounce [animation-delay:200ms]" />
            <span className="w-1.5 h-1.5 rounded-full bg-gray-500 animate-bounce [animation-delay:400ms]" />
          </div>
        </div>
      </div>
    }>
      <ThesisBuilder />
    </Suspense>
  )
}

function ThesisBuilder() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const entry = toEntrySource(searchParams.get('entry'))

  const [state, setState] = useState<BuilderState>(INITIAL_BUILDER_STATE)
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [sheetContent, setSheetContent] = useState<{
    title: string; text: string
  } | null>(null)
  const [showSlowHint, setShowSlowHint] = useState(false)
  const slowTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [showAddIndicator, setShowAddIndicator] = useState(false)

  // 대화 내 진입 선택 상태
  type EntryPhase = 'entry_select' | 'news_select' | 'active'
  const [entryPhase, setEntryPhase] = useState<EntryPhase>('entry_select')
  interface NewsIssue {
    id: string
    title: string
    keyword: string
    summary: string
    source: string
    url: string
    sentiment_score: number | null
  }
  const [newsItems, setNewsItems] = useState<NewsIssue[]>([])
  const [newsLoading, setNewsLoading] = useState(false)

  const scrollRef = useRef<HTMLDivElement>(null)

  // ── 대화 시작: 진입 선택 카드를 첫 메시지로 표시 ──
  useEffect(() => {
    // entry param이 있으면 바로 해당 모드로 시작
    if (entry === 'news') {
      handleEntrySelect('news')
      return
    }
    if (entry !== 'free_input' || searchParams.get('entry')) {
      // entry param이 명시적으로 free_input이면 바로 시작
      if (searchParams.get('entry') === 'free_input') {
        handleEntrySelect('free_input')
        return
      }
    }
    // 기본: 진입 선택 화면
    setState(s => ({
      ...s,
      messages: [{
        id: 'welcome-0',
        role: 'ai' as const,
        content: '어떤 투자 가설을 세워볼까요?',
      }],
      messageCounter: 1,
    }))
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // ── 진입 선택 핸들러 ──
  function handleEntrySelect(type: 'free_input' | 'news' | 'popular') {
    if (type === 'free_input') {
      setEntryPhase('active')
      setState(s => ({
        ...s,
        messages: [...s.messages.filter(m => m.id !== 'welcome-0'), {
          id: 'welcome-0',
          role: 'ai' as const,
          content: '어떤 투자 가설을 세워볼까요?',
        }, {
          id: 'user-entry',
          role: 'user' as const,
          content: '내 생각으로 시작',
        }],
      }))
      startConversation('free_input')
    } else if (type === 'news') {
      // 뉴스 목록을 대화 내에서 로드
      setState(s => ({
        ...s,
        messages: [...s.messages.filter(m => !m.id.startsWith('user-entry')), {
          id: 'user-entry',
          role: 'user' as const,
          content: '오늘 이슈에서 시작',
        }],
      }))
      setEntryPhase('news_select')
      fetchNewsForChat()
    } else if (type === 'popular') {
      setEntryPhase('active')
      setState(s => ({
        ...s,
        messages: [...s.messages, {
          id: 'user-entry',
          role: 'user' as const,
          content: '인기 가설로 시작',
        }],
      }))
      startConversation('free_input')
    }
  }

  // ── 대화 내 뉴스 이슈 로드 (Gemini 한국어 변환) ──
  async function fetchNewsForChat() {
    setNewsLoading(true)
    try {
      const { authAxios } = await import('@/lib/api/authAxios')
      const res = await authAxios.get('/thesis/conversation/news-issues/')
      const issues: NewsIssue[] = (res.data?.issues ?? []).map((item: Record<string, unknown>) => ({
        id: item.id as string,
        title: '',
        keyword: item.keyword as string || '',
        summary: item.summary as string || '',
        source: item.source as string || 'news',
        url: item.url as string || '',
        sentiment_score: item.sentiment === 'positive' ? 0.5 : item.sentiment === 'negative' ? -0.5 : 0,
      }))

      setNewsItems(issues)
      setState(s => ({
        ...s,
        messages: [...s.messages, {
          id: 'ai-news-list',
          role: 'ai' as const,
          content: issues.length > 0
            ? '최근 주요 이슈를 정리했어요. 관심 있는 이슈를 선택하면 가설을 설계해드릴게요.'
            : '최근 뉴스가 없어요. 직접 입력해보세요.',
          inputType: issues.length === 0 ? 'text' as const : undefined,
        }],
        messageCounter: s.messageCounter + 1,
      }))
    } catch {
      setState(s => ({
        ...s,
        messages: [...s.messages, {
          id: 'ai-news-error',
          role: 'ai' as const,
          content: '뉴스를 가져오지 못했어요. 직접 입력해주세요.',
          inputType: 'text' as const,
        }],
      }))
      setEntryPhase('active')
      startConversation('free_input')
    } finally {
      setNewsLoading(false)
    }
  }

  // ── 뉴스 카드 선택 ──
  function handleNewsCardSelect(newsId: string, keyword: string) {
    setEntryPhase('active')
    setState(s => ({
      ...s,
      messages: [...s.messages, {
        id: `user-news-${newsId}`,
        role: 'user' as const,
        content: keyword,
      }],
    }))
    startConversation('news', newsId)
  }

  // ── 인기 가설 템플릿 선택 ──
  function handlePopularSelect(template: string) {
    setEntryPhase('active')
    setState(s => ({
      ...s,
      messages: [...s.messages, {
        id: 'user-popular',
        role: 'user' as const,
        content: template,
      }],
    }))
    // startConversation 후 바로 해당 텍스트로 proposal
    startConversationAndSend('free_input', template)
  }

  // ── startConversation + 즉시 sendResponse ──
  async function startConversationAndSend(entrySource: EntrySource, text: string) {
    setState(s => ({ ...s, isLoading: true }))
    try {
      const response = await thesisApi.startConversation({ entry_source: entrySource })
      saveConvId(response.conversation_state.conv_id)
      // 즉시 sendResponse
      const respond = await thesisApi.sendMessage({
        conversation_state: response.conversation_state,
        user_input: text,
      })
      if (respond?.conversation_state) {
        setState(s => applyResponse(s, respond))
      } else {
        showError()
      }
    } catch {
      showError()
    }
  }

  async function startConversation(entrySource: EntrySource, sourceNewsId?: string) {
    setState(s => ({ ...s, isLoading: true }))

    if (USE_MOCK) {
      // LLM mock이 활성화된 경우 LLM 시작 사용
      const mockResponse = MOCK_LLM_START.conversation_state.mode === 'llm'
        ? MOCK_LLM_START
        : entrySource === 'news'
          ? MOCK_CONVERSATION_START_NEWS
          : MOCK_CONVERSATION_START_FREE
      setState(s => applyResponse(s, mockResponse))
      return
    }

    try {
      const response = await thesisApi.startConversation({
        entry_source: entrySource,
        ...(sourceNewsId ? { source_news_id: sourceNewsId } : {}),
      })
      saveConvId(response.conversation_state.conv_id)
      setState(s => applyResponse(s, response))
    } catch {
      showError()
    }
  }

  // ── 에러 메시지 ──
  function showError() {
    setState(s => ({
      ...s,
      isLoading: false,
      messages: [...s.messages, {
        id: `error-${s.messageCounter}`,
        role: 'ai' as const,
        content: '연결에 문제가 생겼어요. 아래 버튼으로 다시 시도할 수 있어요.',
      }],
      messageCounter: s.messageCounter + 1,
    }))
  }

  // ── 응답 전송 ──
  async function sendResponse(input: string | string[], label: string): Promise<boolean> {
    if (!state.conversationState) return false

    setState(s => ({
      ...s,
      isLoading: true,
      messages: [...s.messages, {
        id: generateMessageId(s, 'user'),
        role: 'user',
        content: label,
      }],
      messageCounter: s.messageCounter + 1,
      lastRequest: {
        conversation_state: s.conversationState!,
        user_input: input,
        label,
      },
    }))

    if (USE_MOCK) {
      setTimeout(() => {
        setState(s => {
          const nextStep = s.step + 1
          // LLM 모드 mock
          if (s.mode === 'llm') {
            const mockNext = MOCK_LLM_STEP_MAP[nextStep] ?? MOCK_CONVERSATION_DONE
            return applyResponse(s, mockNext)
          }
          // wizard 모드 mock
          const stepMap = entry === 'free_input' ? MOCK_FREE_STEP_MAP : MOCK_NEWS_STEP_MAP
          const mockNext = stepMap[nextStep] ?? MOCK_CONVERSATION_DONE
          return applyResponse(s, mockNext)
        })
      }, 800)
      return true
    }

    try {
      const response = await thesisApi.sendMessage({
        conversation_state: state.conversationState,
        user_input: input,
      })

      // fallback 응답 처리: conversation_state 파싱 실패 방어
      if (!response?.conversation_state) {
        showError()
        return false
      }

      setState(s => applyResponse(s, response))
      return true
    } catch {
      showError()
      return false
    }
  }

  // ── 단일 선택 핸들러 ──
  function handleSingleSelect(button: ConversationButton) {
    if (button.id === '__retry__') {
      setState(s => ({
        ...s,
        messages: s.messages.filter(m => !m.id.startsWith('error-')),
      }))
      if (state.lastRequest) {
        sendResponse(state.lastRequest.user_input, state.lastRequest.label)
      } else {
        startConversation(entry)
      }
      return
    }
    sendResponse(button.id, button.label)
  }

  // ── 멀티 선택 토글 ──
  function handleMultiToggle(buttonId: string) {
    setSelectedIds(prev =>
      prev.includes(buttonId)
        ? prev.filter(id => id !== buttonId)
        : [...prev, buttonId],
    )
  }

  // ── 멀티 선택 완료 ──
  async function handleMultiConfirm() {
    if (selectedIds.length === 0) return
    const lastMsg = state.messages[state.messages.length - 1]
    const label = selectionToLabel(selectedIds, lastMsg?.buttons ?? [])
    const success = await sendResponse(selectedIds, label)
    if (success) setSelectedIds([])
  }

  // ── 텍스트 전송 ──
  function handleTextSubmit(text: string) {
    sendResponse(text, text)
  }

  // ── 근거 설명 표시 ──
  function handleShowExplanation(buttonId: string) {
    const lastMsg = state.messages[state.messages.length - 1]
    const explanations = lastMsg?.longPressExplanations
    if (explanations?.[buttonId]) {
      const btn = lastMsg?.buttons?.find(b => b.id === buttonId)
      setSheetContent({
        title: btn?.label ?? '설명',
        text: explanations[buttonId],
      })
    }
  }

  // ── 지표 제거 ──
  function handleRemoveIndicator(index: number) {
    setState(s => {
      const updated = [...s.indicatorRecommendations]
      updated.splice(index, 1)
      // conversation_state의 selected_indicator_ids도 업데이트
      const cs = s.conversationState
      if (cs?.mode === 'llm' && cs.collected) {
        const ids = updated
          .map(r => r.indicator?.id)
          .filter((id): id is number => id != null)
        ;(cs.collected as Record<string, unknown>).selected_indicator_ids = ids
      }
      return { ...s, indicatorRecommendations: updated }
    })
  }

  // ── 지표 추가/토글 ──
  function handleToggleIndicator(id: number, name: string) {
    setState(s => {
      const existing = s.indicatorRecommendations.find(r => r.indicator?.id === id)
      let updated
      if (existing) {
        updated = s.indicatorRecommendations.filter(r => r.indicator?.id !== id)
      } else {
        updated = [...s.indicatorRecommendations, {
          premise_title: '',
          indicator_name: name,
          why: '사용자 추가',
          signal_type: 'coincident' as const,
          auto_matched: false,
          match_method: 'text' as const,
          indicator: { id },
        }]
      }
      // conversation_state 업데이트
      const cs = s.conversationState
      if (cs?.mode === 'llm' && cs.collected) {
        const ids = updated
          .map(r => r.indicator?.id)
          .filter((id): id is number => id != null)
        ;(cs.collected as Record<string, unknown>).selected_indicator_ids = ids
      }
      return { ...s, indicatorRecommendations: updated }
    })
  }

  // ── 프리셋 선택 (LLM 모드) ──
  function handlePresetSelect(presetId: string) {
    sendResponse(presetId, presetId)
  }

  // ── 완료 후 네비게이션 ──
  function handleComplete(action: string) {
    clearConvId()
    const thesisId = state.thesisId || state.createdThesis?.thesis_id
    if (USE_MOCK || !thesisId) {
      router.push('/thesis')
      return
    }
    switch (action) {
      case 'auto':
        router.push(`/thesis/${thesisId}/indicators?auto=true`)
        break
      case 'manual':
        router.push(`/thesis/${thesisId}/indicators`)
        break
      case 'dashboard':
        router.push(state.createdThesis?.dashboard_url ?? `/thesis/${thesisId}`)
        break
      default:
        router.push('/thesis')
    }
  }

  // ── Gemini 지연 힌트 (2초 이상 로딩 시) ──
  useEffect(() => {
    if (state.isLoading && state.mode === 'llm') {
      slowTimerRef.current = setTimeout(() => setShowSlowHint(true), 2000)
    } else {
      setShowSlowHint(false)
      if (slowTimerRef.current) {
        clearTimeout(slowTimerRef.current)
        slowTimerRef.current = null
      }
    }
    return () => {
      if (slowTimerRef.current) clearTimeout(slowTimerRef.current)
    }
  }, [state.isLoading, state.mode])

  // ── 스크롤 최하단 유지 ──
  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: 'smooth',
    })
  }, [state.messages, state.isLoading])

  // ── 마지막 메시지 분석 ──
  const lastMessage = state.messages[state.messages.length - 1]
  const isErrorMessage = !!lastMessage?.id?.startsWith('error-')
  const activeButtons = (
    !state.isLoading
    && lastMessage?.role === 'ai'
    && state.conversationState !== null
    && !isErrorMessage
  ) ? lastMessage.buttons ?? [] : []
  const activeMode = lastMessage?.selectionMode ?? 'single'
  const showTextInput = (lastMessage?.inputType === 'text' || state.phase === 'proposal') && !state.isLoading && !state.isDone

  // 인기 가설 템플릿
  const POPULAR_TEMPLATES = [
    'AI 반도체 수요 증가로 관련주 상승',
    '금리 인하 기대감으로 부동산/REITs 반등',
    '원화 약세 지속으로 수출주 수혜',
    '고금리 장기화로 은행주 수혜',
  ]

  return (
    <div className="flex flex-col h-[calc(100dvh-env(safe-area-inset-top))]
                    bg-gray-950">
      {/* 상단 헤더 */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-800">
        <Link href="/thesis" className="p-1 text-gray-400 hover:text-white">
          <ArrowLeft size={20} />
        </Link>
        <h1 className="text-white text-base font-medium flex-1">가설 세우기</h1>
      </div>

      {/* 진행률 바 */}
      {state.step > 0 && (
        <ProgressBar step={state.step} totalSteps={state.totalSteps} />
      )}

      {/* 메시지 스크롤 영역 */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 pt-4 pb-4">
        {state.messages.map((msg) => (
          <ChatBubble key={msg.id} role={msg.role}>
            {msg.content}
          </ChatBubble>
        ))}

        {/* Preview 카드 렌더링 (wizard 모드) */}
        {state.preview && (
          <div className="mb-3 space-y-2">
            <p className="text-xs text-gray-500 px-1">근거 ({state.preview.premises.length}개)</p>
            {state.preview.premises.map((premise, i) => (
              <PremiseCard key={i} premise={premise} />
            ))}
          </div>
        )}

        {/* LLM 모드: 지표 추천 카드 (수정 가능) */}
        {state.indicatorRecommendations.length > 0 && state.phase === 'preset' && (
          <div className="mb-3 space-y-2">
            <p className="text-xs text-gray-500 px-1">
              AI 추천 지표 ({state.indicatorRecommendations.length}개)
            </p>
            {state.indicatorRecommendations.map((rec, i) => (
              <IndicatorCard
                key={`${rec.indicator_name}-${i}`}
                recommendation={rec}
                onRemove={() => handleRemoveIndicator(i)}
              />
            ))}
            <button
              onClick={() => setShowAddIndicator(true)}
              className="w-full py-2.5 border border-dashed border-gray-700 text-gray-400
                         text-sm rounded-xl hover:border-gray-500 hover:text-gray-300
                         transition-colors"
            >
              + 지표 추가
            </button>
          </div>
        )}

        {/* ── 대화 내 진입 선택 카드 ── */}
        {entryPhase === 'entry_select' && !state.isLoading && (
          <div className="space-y-2 mb-3">
            {[
              { type: 'free_input' as const, icon: '💬', label: '내 생각', desc: '자유롭게 입력해보세요' },
              { type: 'news' as const, icon: '📰', label: '오늘 이슈', desc: '최근 시장 이슈에서 시작' },
              { type: 'popular' as const, icon: '⭐', label: '인기 가설', desc: '검증된 템플릿으로 시작' },
            ].map((opt) => (
              <button
                key={opt.type}
                onClick={() => handleEntrySelect(opt.type)}
                className="w-full flex items-center gap-3 p-3.5 bg-gray-900 border border-gray-700
                           rounded-xl text-left hover:border-blue-500/50 active:scale-[0.98]
                           transition-all"
              >
                <span className="text-xl flex-shrink-0">{opt.icon}</span>
                <div className="min-w-0">
                  <p className="text-sm text-white font-medium">{opt.label}</p>
                  <p className="text-xs text-gray-400 mt-0.5">{opt.desc}</p>
                </div>
              </button>
            ))}
          </div>
        )}

        {/* ── 대화 내 이슈 카드 (키워드 + 요약 + 링크) ── */}
        {entryPhase === 'news_select' && !newsLoading && newsItems.length > 0 && (
          <div className="space-y-2 mb-3">
            {newsItems.map((issue) => (
              <div
                key={issue.id}
                className="p-3 bg-gray-900 border border-gray-800 rounded-xl
                           hover:border-gray-600 transition-all"
              >
                <div className="flex items-start gap-2">
                  {/* 감성 아이콘 */}
                  <span className="flex-shrink-0 mt-0.5 text-sm">
                    {issue.sentiment_score != null && issue.sentiment_score > 0.2 ? '📈'
                      : issue.sentiment_score != null && issue.sentiment_score < -0.2 ? '📉'
                      : '📰'}
                  </span>

                  <div className="min-w-0 flex-1">
                    {/* 핵심 키워드 — 클릭 → 가설 빌더 */}
                    <button
                      onClick={() => handleNewsCardSelect(issue.id, issue.keyword)}
                      className="text-sm text-white font-medium hover:text-blue-300
                                 text-left transition-colors"
                    >
                      {issue.keyword}
                    </button>

                    {/* 한 줄 요약 */}
                    <p className="text-xs text-gray-400 mt-1 line-clamp-2">
                      {issue.summary}
                    </p>

                    {/* 출처 + 링크 */}
                    <div className="flex items-center gap-2 mt-1.5">
                      <span className="text-[10px] text-gray-500">{issue.source}</span>
                      {issue.url && (
                        <>
                          <span className="text-[10px] text-gray-700">·</span>
                          <a
                            href={issue.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="text-[10px] text-gray-500 hover:text-blue-400 transition-colors"
                          >
                            원문 보기 ↗
                          </a>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
            <button
              onClick={() => handleEntrySelect('free_input')}
              className="w-full py-2 text-gray-500 text-xs text-center hover:text-gray-300"
            >
              직접 입력하기
            </button>
          </div>
        )}

        {/* ── 대화 내 인기 가설 템플릿 ── */}
        {entryPhase === 'active' && state.messages.some(m => m.content === '인기 가설로 시작') && state.messages.length <= 3 && !state.isLoading && !state.conversationState && (
          <div className="space-y-1.5 mb-3">
            <p className="text-xs text-gray-500 px-1">인기 가설 템플릿</p>
            {POPULAR_TEMPLATES.map((t, i) => (
              <button
                key={i}
                onClick={() => handlePopularSelect(t)}
                className="w-full text-left p-3 bg-gray-900 border border-gray-800
                           rounded-xl hover:border-blue-500/50 active:scale-[0.99]
                           transition-all text-sm text-gray-300"
              >
                {t}
              </button>
            ))}
          </div>
        )}

        {/* AI 로딩 중 */}
        {(state.isLoading || newsLoading) && (
          <div>
            <ChatBubble role="ai" isLoading />
            {showSlowHint && (
              <p className="text-xs text-gray-500 px-3 mt-1 animate-fade-in">
                AI가 가설을 설계하고 있어요...
              </p>
            )}
          </div>
        )}
      </div>

      {/* 하단 고정 영역 */}
      <div className="flex-shrink-0">
        {/* LLM 모드: 프리셋 선택 */}
        {state.mode === 'llm' && state.phase === 'preset' && !state.isLoading && !state.isDone && (
          <PresetSelector
            onSelect={handlePresetSelect}
            disabled={state.isLoading}
          />
        )}

        {/* 버튼 선택지 (preset이 아닌 경우에만) */}
        {activeButtons.length > 0 && !state.isDone
          && !(state.mode === 'llm' && state.phase === 'preset') && (
          <div className="border-t border-gray-800 bg-gray-950 px-4 py-3 space-y-2">
            {activeButtons.map((btn) => (
              <OptionButton
                key={btn.id}
                button={btn}
                mode={activeMode}
                selected={activeMode === 'multi' ? selectedIds.includes(btn.id) : undefined}
                onClick={() => {
                  if (activeMode === 'multi') {
                    handleMultiToggle(btn.id)
                  } else {
                    handleSingleSelect(btn)
                  }
                }}
                onShowExplanation={
                  btn.long_press_hint ? () => handleShowExplanation(btn.id) : undefined
                }
              />
            ))}
          </div>
        )}

        {/* 멀티 선택 완료 버튼 */}
        {activeMode === 'multi' && activeButtons.length > 0 && !state.isDone && (
          <MultiSelectFooter
            selectedCount={selectedIds.length}
            onConfirm={handleMultiConfirm}
          />
        )}

        {/* 텍스트 입력 */}
        {showTextInput && (
          <TextInput
            onSubmit={handleTextSubmit}
            disabled={state.isLoading}
          />
        )}

        {/* 에러 재시도 */}
        {!state.isLoading && isErrorMessage && (
          <div className="border-t border-gray-800 bg-gray-950 px-4 py-3">
            <button
              onClick={() => handleSingleSelect({ id: '__retry__', label: '다시 시도' })}
              className="w-full py-3.5 border border-gray-600 text-gray-200 text-sm
                         rounded-xl active:scale-[0.98] transition-transform"
            >
              다시 시도
            </button>
          </div>
        )}

        {/* 완료 분기 — 프론트 하드코딩 CTA */}
        {state.isDone && (
          <div className="border-t border-gray-800 bg-gray-950 px-4 py-4 space-y-2">
            <button
              onClick={() => handleComplete('auto')}
              className="w-full py-4 bg-blue-600 text-white text-sm font-medium
                         rounded-xl active:scale-[0.98] transition-transform"
            >
              좋아, 일단 달아줘
            </button>
            <button
              onClick={() => handleComplete('manual')}
              className="w-full py-3.5 border border-gray-600 text-gray-200 text-sm
                         rounded-xl active:scale-[0.98] transition-transform"
            >
              내가 직접 고를래
            </button>
            <button
              onClick={() => handleComplete('later')}
              className="w-full py-2 text-gray-500 text-sm text-center"
            >
              나중에 할게
            </button>
          </div>
        )}
      </div>

      {/* 바텀시트 (근거 설명) */}
      <BottomSheet
        isOpen={!!sheetContent}
        onClose={() => setSheetContent(null)}
        title={sheetContent?.title}
      >
        <p className="text-gray-300 text-sm leading-relaxed">
          {sheetContent?.text}
        </p>
        <button
          onClick={() => setSheetContent(null)}
          className="mt-4 w-full py-3 bg-gray-800 text-gray-300 text-sm rounded-xl"
        >
          이해했어
        </button>
      </BottomSheet>

      {/* 지표 추가 바텀시트 */}
      <AddIndicatorSheet
        isOpen={showAddIndicator}
        onClose={() => setShowAddIndicator(false)}
        selectedIds={state.indicatorRecommendations
          .map(r => r.indicator?.id)
          .filter((id): id is number => id != null)
        }
        onToggle={handleToggleIndicator}
      />
    </div>
  )
}

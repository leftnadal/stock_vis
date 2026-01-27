'use client';

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ShoppingBasket, Coins, X } from 'lucide-react';
import { ChatInterface } from '@/components/rag/ChatInterface';
import { DataBasket } from '@/components/rag/DataBasket';
import { TokenUsageDisplay } from '@/components/rag/TokenUsageDisplay';
import { basketService, sessionService } from '@/services/ragService';
import { useSSEStream } from '@/hooks/useSSEStream';
import type { Basket, Message } from '@/types/rag';

const QUERY_KEYS = {
  baskets: ['baskets'] as const,
  basket: (id: number) => ['baskets', id] as const,
  sessions: ['sessions'] as const,
  session: (id: number) => ['sessions', id] as const,
  messages: (sessionId: number) => ['sessions', sessionId, 'messages'] as const,
};

export function AIChatSidebar() {
  const queryClient = useQueryClient();
  const [isBasketOpen, setIsBasketOpen] = useState(false);
  const [isTokenPanelOpen, setIsTokenPanelOpen] = useState(false);
  const [currentBasketId, setCurrentBasketId] = useState<number | null>(null);
  const [currentSessionId, setCurrentSessionId] = useState<number | null>(null);
  const [sessionUsage, setSessionUsage] = useState({ input_tokens: 0, output_tokens: 0 });

  // 바구니 목록 조회
  const { data: baskets } = useQuery({
    queryKey: QUERY_KEYS.baskets,
    queryFn: basketService.getList,
  });

  // 현재 바구니 상세 조회
  const { data: currentBasket } = useQuery({
    queryKey: QUERY_KEYS.basket(currentBasketId!),
    queryFn: () => basketService.getDetail(currentBasketId!),
    enabled: !!currentBasketId,
  });

  // 메시지 목록 조회
  const { data: messages = [] } = useQuery({
    queryKey: QUERY_KEYS.messages(currentSessionId!),
    queryFn: () => sessionService.getMessages(currentSessionId!),
    enabled: !!currentSessionId,
    refetchInterval: false,
  });

  // SSE 스트리밍
  const {
    isStreaming,
    streamedContent,
    suggestions,
    basketActions,
    basketCleared,
    error: streamError,
    currentPhase,
    usage: currentUsage,
    complexity,
    startStream,
  } = useSSEStream(currentSessionId!);

  // 토큰 사용량 누적
  useEffect(() => {
    if (currentUsage && !isStreaming) {
      setSessionUsage((prev) => ({
        input_tokens: prev.input_tokens + currentUsage.input_tokens,
        output_tokens: prev.output_tokens + currentUsage.output_tokens,
      }));
    }
  }, [currentUsage, isStreaming]);

  // 바구니가 비워졌을 때 바구니 쿼리 갱신
  useEffect(() => {
    if (basketCleared && currentBasketId) {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.basket(currentBasketId) });
    }
  }, [basketCleared, currentBasketId, queryClient]);

  // 바구니 생성 뮤테이션
  const createBasketMutation = useMutation({
    mutationFn: basketService.create,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.baskets });
      setCurrentBasketId(data.id);
    },
  });

  // 세션 생성 뮤테이션
  const createSessionMutation = useMutation({
    mutationFn: sessionService.create,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.sessions });
      setCurrentSessionId(data.id);
    },
  });

  // 아이템 제거 뮤테이션
  const removeItemMutation = useMutation({
    mutationFn: ({ basketId, itemId }: { basketId: number; itemId: number }) =>
      basketService.removeItem(basketId, itemId),
    onSuccess: () => {
      if (currentBasketId) {
        queryClient.invalidateQueries({ queryKey: QUERY_KEYS.basket(currentBasketId) });
      }
    },
  });

  // 바구니 비우기 뮤테이션
  const clearBasketMutation = useMutation({
    mutationFn: (basketId: number) => basketService.clear(basketId),
    onSuccess: () => {
      if (currentBasketId) {
        queryClient.invalidateQueries({ queryKey: QUERY_KEYS.basket(currentBasketId) });
      }
    },
  });

  // 초기 설정: 바구니와 세션 자동 생성
  useEffect(() => {
    const initializeSession = async () => {
      try {
        const validBaskets = Array.isArray(baskets) ? baskets.filter((b) => b && b.id) : [];

        if (validBaskets.length === 0) {
          const basket = await createBasketMutation.mutateAsync({
            name: '전략분석 바구니',
            description: '전략분석실 AI 분석용 바구니',
          });
          setCurrentBasketId(basket.id);

          const session = await createSessionMutation.mutateAsync({
            basket: basket.id,
            title: `전략분석 ${new Date().toLocaleString('ko-KR')}`,
          });
          setCurrentSessionId(session.id);
        } else {
          const firstBasket = validBaskets[0];
          setCurrentBasketId(firstBasket.id);

          const session = await createSessionMutation.mutateAsync({
            basket: firstBasket.id,
            title: `전략분석 ${new Date().toLocaleString('ko-KR')}`,
          });
          setCurrentSessionId(session.id);
        }
      } catch (error) {
        console.error('Failed to initialize session:', error);
      }
    };

    if (!currentBasketId && baskets !== undefined) {
      initializeSession();
    }
  }, [baskets, currentBasketId]);

  // 메시지 전송 핸들러
  const handleSendMessage = async (message: string) => {
    if (!currentSessionId) return;

    const tempUserMessage: Message = {
      id: Date.now(),
      session: currentSessionId,
      role: 'user',
      content: message,
      created_at: new Date().toISOString(),
    };

    queryClient.setQueryData<Message[]>(QUERY_KEYS.messages(currentSessionId), (old = []) => [
      ...old,
      tempUserMessage,
    ]);

    await startStream(message);
    queryClient.invalidateQueries({ queryKey: QUERY_KEYS.messages(currentSessionId) });
  };

  // 아이템 제거 핸들러
  const handleRemoveItem = (itemId: number) => {
    if (!currentBasketId) return;
    removeItemMutation.mutate({ basketId: currentBasketId, itemId });
  };

  // 바구니 비우기 핸들러
  const handleClearBasket = () => {
    if (!currentBasketId) return;
    if (confirm('바구니의 모든 아이템을 삭제하시겠습니까?')) {
      clearBasketMutation.mutate(currentBasketId);
    }
  };

  // 바구니에 데이터 추가 핸들러
  const handleAddToBasket = async (symbol: string, dataTypes: string[]) => {
    if (!currentBasketId) {
      console.error('바구니가 선택되지 않았습니다.');
      return;
    }

    try {
      const result = await basketService.addStockData(currentBasketId, symbol, dataTypes);
      console.log('Added to basket:', result);
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.basket(currentBasketId) });
    } catch (error) {
      console.error('Failed to add to basket:', error);
      throw error;
    }
  };

  // 자동 대화 계속 핸들러
  const handleContinueChat = async (message: string) => {
    if (!currentSessionId) return;
    setTimeout(() => {
      handleSendMessage(message);
    }, 500);
  };

  return (
    <div className="flex h-full flex-col">
      {/* 헤더 */}
      <div className="border-b border-[#30363D] bg-[#0D1117] px-4 py-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-[#E6EDF3]">AI 분석 챗봇</h3>
          <div className="flex items-center gap-2">
            {/* 토큰 사용량 버튼 */}
            <button
              onClick={() => setIsTokenPanelOpen(!isTokenPanelOpen)}
              className="flex items-center gap-1 rounded px-2 py-1 text-xs font-medium text-[#8B949E] transition-colors hover:bg-[#161B22] hover:text-[#E6EDF3]"
            >
              <Coins className="h-3 w-3" />
              {sessionUsage.input_tokens + sessionUsage.output_tokens > 0 && (
                <span className="font-mono text-[#A371F7]">
                  {((sessionUsage.input_tokens + sessionUsage.output_tokens) / 1000).toFixed(1)}k
                </span>
              )}
            </button>

            {/* 바구니 버튼 */}
            <button
              onClick={() => setIsBasketOpen(true)}
              className="flex items-center gap-1 rounded px-2 py-1 text-xs font-medium text-[#8B949E] transition-colors hover:bg-[#161B22] hover:text-[#E6EDF3]"
            >
              <ShoppingBasket className="h-3 w-3" />
              {currentBasket && currentBasket.items.length > 0 && (
                <span className="flex h-4 w-4 items-center justify-center rounded-full bg-[#58A6FF] text-xs text-white">
                  {currentBasket.items.length}
                </span>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* 토큰 사용량 패널 */}
      {isTokenPanelOpen && (
        <div className="absolute right-4 top-16 z-50 w-80">
          <TokenUsageDisplay
            currentUsage={currentUsage}
            sessionUsage={sessionUsage}
            model="gemini-2.5-flash"
            complexity={complexity}
            onClose={() => setIsTokenPanelOpen(false)}
          />
        </div>
      )}

      {/* 챗 인터페이스 */}
      <div className="flex-1 overflow-hidden bg-[#0D1117]">
        <ChatInterface
          sessionId={currentSessionId}
          messages={messages}
          isStreaming={isStreaming}
          streamedContent={streamedContent}
          suggestions={suggestions}
          basketActions={basketActions}
          basket={currentBasket || null}
          error={streamError}
          currentPhase={currentPhase}
          onSendMessage={handleSendMessage}
          onAddToBasket={handleAddToBasket}
          onContinueChat={handleContinueChat}
        />
      </div>

      {/* 데이터 바구니 패널 */}
      <DataBasket
        basket={currentBasket || null}
        isOpen={isBasketOpen}
        onClose={() => setIsBasketOpen(false)}
        onRemoveItem={handleRemoveItem}
        onClear={handleClearBasket}
      />
    </div>
  );
}

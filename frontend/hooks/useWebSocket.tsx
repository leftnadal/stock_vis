import { useState, useEffect, useRef, useCallback } from 'react';

interface WebSocketMessage {
  type: string;
  [key: string]: any;
}

interface UseWebSocketOptions {
  onMessage?: (message: WebSocketMessage) => void;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (error: Event) => void;
  reconnect?: boolean;
  reconnectAttempts?: number;
  reconnectInterval?: number;
}

export const useWebSocket = (
  url: string,
  options: UseWebSocketOptions = {}
) => {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [error, setError] = useState<string | null>(null);

  const ws = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimeout = useRef<NodeJS.Timeout | undefined>(undefined);

  const {
    onMessage,
    onOpen,
    onClose,
    onError,
    reconnect = true,
    reconnectAttempts: maxReconnectAttempts = 5,
    reconnectInterval = 3000,
  } = options;

  const connect = useCallback(() => {
    try {
      // WebSocket URL 구성
      const wsUrl = url.startsWith('ws') ? url : `ws://localhost:8000${url}`;

      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        setIsConnected(true);
        setError(null);
        reconnectAttempts.current = 0;
        console.log('WebSocket connected');
        onOpen?.();
      };

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setLastMessage(data);
          onMessage?.(data);
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err);
        }
      };

      ws.current.onerror = (event) => {
        setError('WebSocket error occurred');
        console.error('WebSocket error:', event);
        onError?.(event);
      };

      ws.current.onclose = () => {
        setIsConnected(false);
        console.log('WebSocket disconnected');
        onClose?.();

        // 재연결 로직
        if (reconnect && reconnectAttempts.current < maxReconnectAttempts) {
          reconnectAttempts.current++;
          console.log(`Reconnecting... Attempt ${reconnectAttempts.current}/${maxReconnectAttempts}`);

          reconnectTimeout.current = setTimeout(() => {
            connect();
          }, reconnectInterval);
        }
      };
    } catch (err) {
      console.error('Failed to establish WebSocket connection:', err);
      setError('Failed to connect');
    }
  }, [url, onMessage, onOpen, onClose, onError, reconnect, maxReconnectAttempts, reconnectInterval]);

  const disconnect = useCallback(() => {
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
    }

    if (ws.current) {
      ws.current.close();
      ws.current = null;
    }
  }, []);

  const sendMessage = useCallback((message: WebSocketMessage) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
    } else {
      console.error('WebSocket is not connected');
    }
  }, []);

  useEffect(() => {
    connect();

    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  // Ping/Pong 연결 유지
  useEffect(() => {
    const pingInterval = setInterval(() => {
      if (ws.current?.readyState === WebSocket.OPEN) {
        sendMessage({
          type: 'ping',
          timestamp: Date.now(),
        });
      }
    }, 30000); // 30초마다 ping

    return () => clearInterval(pingInterval);
  }, [sendMessage]);

  return {
    isConnected,
    lastMessage,
    error,
    sendMessage,
    disconnect,
    reconnect: connect,
  };
};

// 주식 가격 WebSocket Hook
export const useStockPriceWebSocket = (symbol: string) => {
  const [priceData, setPriceData] = useState<any>(null);

  const { isConnected, error, sendMessage } = useWebSocket(
    `/ws/stock/${symbol}/`,
    {
      onMessage: (message) => {
        if (message.type === 'price_update' || message.type === 'current_price') {
          setPriceData(message);
        }
      },
      onOpen: () => {
        // 연결되면 구독 메시지 전송
        sendMessage({ type: 'subscribe' });
      },
    }
  );

  return {
    isConnected,
    priceData,
    error,
    refresh: () => sendMessage({ type: 'subscribe' }),
  };
};

// 포트폴리오 WebSocket Hook
export const usePortfolioWebSocket = () => {
  const [portfolioData, setPortfolioData] = useState<any>(null);

  const { isConnected, error, sendMessage } = useWebSocket(
    '/ws/portfolio/',
    {
      onMessage: (message) => {
        if (message.type === 'portfolio_update' || message.type === 'portfolio_summary') {
          setPortfolioData(message);
        }
      },
      onOpen: () => {
        // 연결되면 새로고침 요청
        sendMessage({ type: 'refresh' });
      },
    }
  );

  return {
    isConnected,
    portfolioData,
    error,
    refresh: () => sendMessage({ type: 'refresh' }),
  };
};
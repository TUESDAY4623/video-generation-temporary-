import { useEffect, useRef, useCallback } from 'react';

export function useWebSocket<T>(url: string, onMessage: (data: T) => void) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<number | null>(null);

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(url);
      ws.onopen = () => console.log('WebSocket connected');
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onMessage(data);
        } catch (e) {
          console.warn('WebSocket message parse error:', e);
        }
      };
      ws.onclose = () => {
        console.log('WebSocket disconnected, reconnecting in 3s...');
        reconnectTimer.current = window.setTimeout(connect, 3000);
      };
      ws.onerror = (err) => console.error('WebSocket error:', err);
      wsRef.current = ws;
    } catch (e) {
      console.error('WebSocket connection failed:', e);
    }
  }, [url, onMessage]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { ws: wsRef.current };
}

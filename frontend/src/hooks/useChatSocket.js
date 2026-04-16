/**
 * useChatSocket — manages a WebSocket connection to one chat room.
 *
 * Instead of keeping an internal messages array, new messages are passed
 * to `onMessage` so the caller can update the React-Query cache directly.
 * This means messages survive room switches (query cache persists).
 *
 * Returns:
 *   connected  — boolean
 *   send(body) — function to send a plain text message
 */
import { useEffect, useRef, useState, useCallback } from "react";

const WS_BASE = import.meta.env.VITE_WS_URL || "ws://localhost:8000";

export function useChatSocket(roomId, onMessage) {
  const [connected, setConnected] = useState(false);
  const wsRef        = useRef(null);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;   // always latest without re-creating the effect

  useEffect(() => {
    if (!roomId) return;

    const token = localStorage.getItem("access_token");
    const url   = `${WS_BASE}/ws/chat/${roomId}/?token=${token}`;
    const ws    = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);

    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.type === "message" && data.message) {
          onMessageRef.current?.(data.message);
        }
      } catch (_) { /* ignore parse errors */ }
    };

    ws.onclose  = () => setConnected(false);
    ws.onerror  = () => setConnected(false);

    return () => {
      ws.close();
      setConnected(false);
    };
  }, [roomId]);   // ← onMessage intentionally NOT a dep (use ref instead)

  const send = useCallback((body, extras = {}) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "message", body, ...extras }));
    }
  }, []);

  return { connected, send };
}

"use client";

import { useEffect, useRef, useState } from "react";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

export interface WorkflowEvent {
  type: string;
  pipeline_id?: string;
  job_id?: string;
  step?: string;
  status?: string;
  data?: Record<string, unknown>;
  timestamp?: string;
}

export function useWorkflowSocket() {
  const [events, setEvents] = useState<WorkflowEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket(`${WS_URL}/ws`);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (msg) => {
      try {
        const event = JSON.parse(msg.data) as WorkflowEvent;
        setEvents((prev) => [event, ...prev].slice(0, 50));
      } catch {
        /* ignore */
      }
    };

    const ping = setInterval(() => ws.readyState === WebSocket.OPEN && ws.send("ping"), 30000);
    return () => {
      clearInterval(ping);
      ws.close();
    };
  }, []);

  return { events, connected };
}

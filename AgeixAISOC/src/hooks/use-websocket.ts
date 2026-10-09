"use client"

import { useEffect, useRef, useState, useCallback } from "react"

type WebSocketMessage = {
  type: "alert" | "decision" | "metric" | "agent-status" | "ioc-update"
  payload: unknown
}

export function useWebSocket(url: string) {
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | undefined>(undefined)

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(url)

      ws.onopen = () => {
        setIsConnected(true)
      }

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          setLastMessage(message)
        } catch {
          // ignore parse errors
        }
      }

      ws.onclose = () => {
        setIsConnected(false)
        reconnectTimeoutRef.current = setTimeout(connect, 5000)
      }

      ws.onerror = () => {
        ws.close()
      }

      wsRef.current = ws
    } catch {
      reconnectTimeoutRef.current = setTimeout(connect, 5000)
    }
  }, [url])

  useEffect(() => {
    connect()
    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current)
      if (wsRef.current) wsRef.current.close()
    }
  }, [connect])

  return { isConnected, lastMessage }
}

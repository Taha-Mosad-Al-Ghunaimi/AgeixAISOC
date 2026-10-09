"use client"

import { useEffect, useRef, useState, useCallback } from "react"
import type { WsMessage } from "@/lib/api"

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws/dashboard"

export interface UseWp4WebSocketReturn {
  isConnected: boolean
  lastMessage: WsMessage | null
  messages: WsMessage[]
  decisionPackages: WsMessage[]
  systemLogs: WsMessage[]
  send: (data: Record<string, unknown>) => void
}

export function useWp4WebSocket(): UseWp4WebSocketReturn {
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState<WsMessage | null>(null)
  const [messages, setMessages] = useState<WsMessage[]>([])
  const [decisionPackages, setDecisionPackages] = useState<WsMessage[]>([])
  const [systemLogs, setSystemLogs] = useState<WsMessage[]>([])
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const msgCounter = useRef(0)

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(WS_URL)

      ws.onopen = () => {
        setIsConnected(true)
        // Send ping to keep alive
        ws.send(JSON.stringify({ type: "ping" }))
      }

      ws.onmessage = (event) => {
        try {
          const msg: WsMessage = JSON.parse(event.data)
          if (msg.type === "pong") return

          msgCounter.current += 1
          setLastMessage(msg)
          setMessages((prev) => [msg, ...prev].slice(0, 200))

          if (msg.type === "ai_decision") {
            setDecisionPackages((prev) => [msg, ...prev].slice(0, 50))
          }

          if (msg.type === "system_log" || msg.type === "alert") {
            setSystemLogs((prev) => [msg, ...prev].slice(0, 100))
          }
        } catch {
          // ignore parse errors
        }
      }

      ws.onclose = () => {
        setIsConnected(false)
        reconnectRef.current = setTimeout(connect, 3000)
      }

      ws.onerror = () => ws.close()
      wsRef.current = ws
    } catch {
      reconnectRef.current = setTimeout(connect, 3000)
    }
  }, [])

  useEffect(() => {
    connect()
    const pingInterval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: "ping" }))
      }
    }, 30000)
    return () => {
      clearInterval(pingInterval)
      if (reconnectRef.current) clearTimeout(reconnectRef.current)
      if (wsRef.current) wsRef.current.close()
    }
  }, [connect])

  const send = useCallback((data: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data))
    }
  }, [])

  return { isConnected, lastMessage, messages, decisionPackages, systemLogs, send }
}

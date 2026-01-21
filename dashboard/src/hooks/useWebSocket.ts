import { useEffect, useRef, useCallback, useState } from 'react'

type MessageHandler = (data: WebSocketMessage) => void

interface WebSocketMessage {
  type: string
  data: Record<string, unknown>
}

interface UseWebSocketReturn {
  isConnected: boolean
  lastMessage: WebSocketMessage | null
  subscribe: (handler: MessageHandler) => () => void
}

// Use relative URL to go through Vite proxy in dev
const WS_URL = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`
const RECONNECT_DELAY = 3000

export function useWebSocket(): UseWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null)
  const handlersRef = useRef<Set<MessageHandler>>(new Set())
  const reconnectTimeoutRef = useRef<number | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)

  const connect = useCallback(() => {
    // Don't reconnect if already connected
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return
    }

    const ws = new WebSocket(WS_URL)

    ws.onopen = () => {
      console.log('[WebSocket] Connected')
      setIsConnected(true)

      // Clear any pending reconnect timeout
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
        reconnectTimeoutRef.current = null
      }
    }

    ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data)
        console.log('[WebSocket] Message:', message)
        setLastMessage(message)

        // Notify all handlers
        handlersRef.current.forEach(handler => {
          try {
            handler(message)
          } catch (err) {
            console.error('[WebSocket] Handler error:', err)
          }
        })
      } catch {
        // Non-JSON message (like pong)
        console.log('[WebSocket] Text message:', event.data)
      }
    }

    ws.onclose = () => {
      console.log('[WebSocket] Disconnected')
      setIsConnected(false)

      // Auto-reconnect after delay
      reconnectTimeoutRef.current = window.setTimeout(() => {
        console.log('[WebSocket] Reconnecting...')
        connect()
      }, RECONNECT_DELAY)
    }

    ws.onerror = (error) => {
      console.error('[WebSocket] Error:', error)
    }

    wsRef.current = ws

    // Heartbeat / ping
    const pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send('ping')
      }
    }, 30000)

    // Cleanup ping interval when ws closes
    ws.addEventListener('close', () => {
      clearInterval(pingInterval)
    })
  }, [])

  // Connect on mount
  useEffect(() => {
    connect()

    return () => {
      // Cleanup on unmount
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [connect])

  // Subscribe to messages
  const subscribe = useCallback((handler: MessageHandler): (() => void) => {
    handlersRef.current.add(handler)
    return () => {
      handlersRef.current.delete(handler)
    }
  }, [])

  return { isConnected, lastMessage, subscribe }
}

// Singleton instance for global WebSocket connection
let globalWs: WebSocket | null = null
let globalHandlers = new Set<MessageHandler>()
let reconnectTimeout: number | null = null

function connectGlobal() {
  if (globalWs?.readyState === WebSocket.OPEN) {
    return
  }

  const ws = new WebSocket(WS_URL)

  ws.onopen = () => {
    console.log('[WebSocket Global] Connected')
    if (reconnectTimeout) {
      clearTimeout(reconnectTimeout)
      reconnectTimeout = null
    }
  }

  ws.onmessage = (event) => {
    try {
      const message: WebSocketMessage = JSON.parse(event.data)
      globalHandlers.forEach(handler => handler(message))
    } catch {
      // Non-JSON message
    }
  }

  ws.onclose = () => {
    console.log('[WebSocket Global] Disconnected, reconnecting...')
    reconnectTimeout = window.setTimeout(connectGlobal, RECONNECT_DELAY)
  }

  globalWs = ws

  // Ping every 30s
  setInterval(() => {
    if (globalWs?.readyState === WebSocket.OPEN) {
      globalWs.send('ping')
    }
  }, 30000)
}

// Global connection disabled - using hook-based connections instead
// if (typeof window !== 'undefined') {
//   connectGlobal()
// }

export function subscribeToWebSocket(handler: MessageHandler): () => void {
  globalHandlers.add(handler)
  return () => globalHandlers.delete(handler)
}

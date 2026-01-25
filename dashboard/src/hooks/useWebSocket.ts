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
const PING_INTERVAL = 25000  // 25 seconds (less than typical 30s timeout)

// ============================================================================
// SINGLETON WebSocket Connection (shared across all components)
// ============================================================================
let sharedWs: WebSocket | null = null
let sharedHandlers = new Set<MessageHandler>()
let sharedConnectionListeners = new Set<(connected: boolean) => void>()
let reconnectTimeout: ReturnType<typeof setTimeout> | null = null
let pingInterval: ReturnType<typeof setInterval> | null = null
let isConnecting = false

function connectShared() {
  // Prevent multiple simultaneous connection attempts
  if (isConnecting || sharedWs?.readyState === WebSocket.OPEN) {
    return
  }

  isConnecting = true

  const ws = new WebSocket(WS_URL)

  ws.onopen = () => {
    console.log('[WebSocket] Connected (shared)')
    isConnecting = false
    sharedWs = ws

    // Notify all listeners
    sharedConnectionListeners.forEach(listener => listener(true))

    // Clear reconnect timeout
    if (reconnectTimeout) {
      clearTimeout(reconnectTimeout)
      reconnectTimeout = null
    }

    // Start ping interval
    if (pingInterval) {
      clearInterval(pingInterval)
    }
    pingInterval = setInterval(() => {
      if (sharedWs?.readyState === WebSocket.OPEN) {
        sharedWs.send('ping')
      }
    }, PING_INTERVAL)
  }

  ws.onmessage = (event) => {
    try {
      const message: WebSocketMessage = JSON.parse(event.data)
      console.log('[WebSocket] Message:', message)

      // Notify all handlers
      sharedHandlers.forEach(handler => {
        try {
          handler(message)
        } catch (err) {
          console.error('[WebSocket] Handler error:', err)
        }
      })
    } catch {
      // Non-JSON message (like pong) - ignore silently
    }
  }

  ws.onclose = () => {
    console.log('[WebSocket] Disconnected')
    isConnecting = false
    sharedWs = null

    // Notify all listeners
    sharedConnectionListeners.forEach(listener => listener(false))

    // Clear ping interval
    if (pingInterval) {
      clearInterval(pingInterval)
      pingInterval = null
    }

    // Auto-reconnect
    if (!reconnectTimeout) {
      reconnectTimeout = setTimeout(() => {
        reconnectTimeout = null
        console.log('[WebSocket] Reconnecting...')
        connectShared()
      }, RECONNECT_DELAY)
    }
  }

  ws.onerror = (error) => {
    console.error('[WebSocket] Error:', error)
    isConnecting = false
  }
}

// Initialize connection on module load
if (typeof window !== 'undefined') {
  connectShared()
}

// ============================================================================
// React Hook (uses shared connection)
// ============================================================================
export function useWebSocket(): UseWebSocketReturn {
  const [isConnected, setIsConnected] = useState(sharedWs?.readyState === WebSocket.OPEN)
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)
  const localHandlersRef = useRef<Set<MessageHandler>>(new Set())

  // Track connection state
  useEffect(() => {
    const connectionListener = (connected: boolean) => {
      setIsConnected(connected)
    }

    sharedConnectionListeners.add(connectionListener)

    // Set initial state
    setIsConnected(sharedWs?.readyState === WebSocket.OPEN)

    // Ensure connection exists
    if (!sharedWs || sharedWs.readyState === WebSocket.CLOSED) {
      connectShared()
    }

    return () => {
      sharedConnectionListeners.delete(connectionListener)
    }
  }, [])

  // Handle messages for this hook instance
  useEffect(() => {
    const messageHandler: MessageHandler = (message) => {
      setLastMessage(message)

      // Forward to local handlers
      localHandlersRef.current.forEach(handler => {
        try {
          handler(message)
        } catch (err) {
          console.error('[WebSocket] Local handler error:', err)
        }
      })
    }

    sharedHandlers.add(messageHandler)

    return () => {
      sharedHandlers.delete(messageHandler)
    }
  }, [])

  // Subscribe to messages (local handlers)
  const subscribe = useCallback((handler: MessageHandler): (() => void) => {
    localHandlersRef.current.add(handler)

    // Also add to shared handlers for immediate delivery
    sharedHandlers.add(handler)

    return () => {
      localHandlersRef.current.delete(handler)
      sharedHandlers.delete(handler)
    }
  }, [])

  return { isConnected, lastMessage, subscribe }
}

// Export for direct subscription without hook
export function subscribeToWebSocket(handler: MessageHandler): () => void {
  sharedHandlers.add(handler)
  return () => sharedHandlers.delete(handler)
}

// Export connection function for manual reconnect
export function reconnectWebSocket() {
  if (sharedWs) {
    sharedWs.close()
  }
  connectShared()
}

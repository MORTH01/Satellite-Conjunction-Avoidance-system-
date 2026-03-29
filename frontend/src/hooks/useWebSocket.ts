import { useEffect, useRef, useState, useCallback } from 'react'
import type { AlertMessage } from '../types'

export function useWebSocket(onMessage: (msg: AlertMessage) => void) {
  const ws = useRef<WebSocket | null>(null)
  const [connected, setConnected] = useState(false)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>()

  const connect = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const url = `${protocol}//${window.location.host}/ws/alerts`

    ws.current = new WebSocket(url)

    ws.current.onopen = () => {
      setConnected(true)
      // Keep-alive ping every 30s
      const ping = setInterval(() => {
        if (ws.current?.readyState === WebSocket.OPEN) {
          ws.current.send('ping')
        } else {
          clearInterval(ping)
        }
      }, 30000)
    }

    ws.current.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data) as AlertMessage
        onMessage(msg)
      } catch {}
    }

    ws.current.onclose = () => {
      setConnected(false)
      // Reconnect after 5s
      reconnectTimer.current = setTimeout(connect, 5000)
    }

    ws.current.onerror = () => {
      ws.current?.close()
    }
  }, [onMessage])

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(reconnectTimer.current)
      ws.current?.close()
    }
  }, [connect])

  return { connected }
}

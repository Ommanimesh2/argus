'use client'
import { useEffect } from 'react'
import { useAuditStore } from '@/store/audit-store'
import { api } from '@/lib/api'
import type { SSEEvent } from '@/lib/types'

export function useAuditStream(auditId: string | null) {
  const setConnectionStatus = useAuditStore((s) => s.setConnectionStatus)
  const handleSSEEvent = useAuditStore((s) => s.handleSSEEvent)
  const isComplete = useAuditStore((s) => s.isComplete)
  const isCancelled = useAuditStore((s) => s.isCancelled)

  useEffect(() => {
    if (!auditId || isComplete || isCancelled) return

    let es: EventSource | null = null
    let retries = 0
    let retryTimeout: ReturnType<typeof setTimeout> | null = null
    const MAX_RETRIES = 10

    function connect() {
      setConnectionStatus('connecting')
      const url = api.streamUrl(auditId as string)
      es = new EventSource(url)

      es.onopen = () => {
        setConnectionStatus('connected')
        retries = 0
      }

      es.onmessage = (e: MessageEvent) => {
        try {
          // Skip SSE comment lines (heartbeats start with ":")
          if (!e.data || e.data.startsWith(':')) return
          const data: SSEEvent = JSON.parse(e.data)
          handleSSEEvent(data)
          if (data.type === 'complete' || data.type === 'cancelled') {
            es?.close()
            setConnectionStatus('disconnected')
          }
        } catch {
          // ignore parse errors
        }
      }

      es.onerror = () => {
        es?.close()
        es = null
        if (retries < MAX_RETRIES) {
          const delay = Math.min(1000 * Math.pow(2, retries), 30000)
          retryTimeout = setTimeout(() => {
            retries++
            connect()
          }, delay)
        } else {
          setConnectionStatus('error')
        }
      }
    }

    connect()

    return () => {
      es?.close()
      if (retryTimeout) clearTimeout(retryTimeout)
    }
  }, [auditId, isComplete, isCancelled, handleSSEEvent, setConnectionStatus])
}

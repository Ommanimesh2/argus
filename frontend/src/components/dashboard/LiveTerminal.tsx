'use client'
import { useEffect, useRef, useState } from 'react'
import { useAuditStore } from '@/store/audit-store'

export function LiveTerminal() {
  const logEntries = useAuditStore((s) => s.logEntries)
  const currentPhase = useAuditStore((s) => s.currentPhase)
  const bottomRef = useRef<HTMLDivElement>(null)
  const [autoScroll, setAutoScroll] = useState(true)

  useEffect(() => {
    if (autoScroll && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [logEntries, autoScroll])

  const levelColor: Record<string, string> = {
    info: '#00ff41',
    warn: '#ffb800',
    error: '#ff0040',
    debug: '#64748b',
  }

  return (
    <div
      className="flex flex-col h-full rounded-lg overflow-hidden"
      style={{ background: '#050508', border: '1px solid #1a1a24' }}
    >
      {/* Title bar */}
      <div
        className="flex items-center justify-between px-3 py-2"
        style={{ borderBottom: '1px solid #1a1a24', background: '#111118' }}
      >
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full" style={{ background: '#ff0040' }} />
          <div className="w-2 h-2 rounded-full" style={{ background: '#ffb800' }} />
          <div className="w-2 h-2 rounded-full" style={{ background: '#00ff41' }} />
          <span className="text-xs text-slate-600 font-terminal ml-2">argus-terminal</span>
        </div>
        <button
          type="button"
          onClick={() => setAutoScroll(!autoScroll)}
          className="text-xs font-terminal transition-colors"
          style={{ color: autoScroll ? '#00ff41' : '#64748b' }}
        >
          {autoScroll ? '⏬ auto' : '⏸ paused'}
        </button>
      </div>

      {/* Log output */}
      <div className="flex-1 overflow-y-auto p-3 space-y-0.5 font-terminal text-xs">
        {currentPhase && (
          <div style={{ color: '#00d4ff' }}>[system] phase={currentPhase}</div>
        )}
        {logEntries.length === 0 && (
          <div style={{ color: '#2a2a3a' }}>Waiting for agent output...</div>
        )}
        {logEntries.map((entry, i) => (
          <div key={i} className="leading-relaxed">
            <span style={{ color: '#2a2a3a' }}>
              {entry.timestamp ? new Date(entry.timestamp).toLocaleTimeString() : ''}
            </span>{' '}
            <span style={{ color: levelColor[entry.level] ?? '#64748b' }}>
              [{entry.source}]
            </span>{' '}
            <span style={{ color: entry.level === 'error' ? '#ff6b8a' : '#94a3b8' }}>
              {entry.message}
            </span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}

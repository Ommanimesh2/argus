'use client'
import { AnimatePresence } from 'framer-motion'
import { useAuditStore } from '@/store/audit-store'
import { FindingCard } from './FindingCard'

export function FindingsFeed() {
  const findings = useAuditStore((s) => s.findings)
  const isRunning = useAuditStore((s) => s.isRunning)
  const isComplete = useAuditStore((s) => s.isComplete)

  if (findings.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-slate-600">
        {isRunning ? (
          <>
            <div className="text-2xl mb-2">🔍</div>
            <div className="text-sm">Scanning for vulnerabilities...</div>
          </>
        ) : (
          <>
            <div className="text-2xl mb-2">📡</div>
            <div className="text-sm">Waiting for audit to begin</div>
          </>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-0 max-h-[calc(100vh-280px)] overflow-y-auto pr-1">
      <div className="text-xs text-slate-500 mb-3 uppercase tracking-wider">
        {findings.length} finding{findings.length !== 1 ? 's' : ''} discovered
        {isRunning && (
          <span className="ml-2" style={{ color: '#00ff41' }}>
            ● scanning
          </span>
        )}
        {isComplete && <span className="ml-2 text-slate-500">· complete</span>}
      </div>
      <AnimatePresence mode="popLayout">
        {[...findings].reverse().map((f) => (
          <FindingCard key={f.id} finding={f} />
        ))}
      </AnimatePresence>
    </div>
  )
}

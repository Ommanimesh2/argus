'use client'
import Link from 'next/link'
import { useAuditStore } from '@/store/audit-store'

export function Header({ auditId }: { auditId?: string }) {
  const connectionStatus = useAuditStore((s) => s.connectionStatus)
  const isRunning = useAuditStore((s) => s.isRunning)

  const statusColor = {
    connected: '#00ff41',
    connecting: '#ffb800',
    disconnected: '#64748b',
    error: '#ff0040',
  }[connectionStatus]

  return (
    <header
      style={{
        borderBottom: '1px solid #2a2a3a',
        background: 'rgba(10,10,15,0.95)',
        backdropFilter: 'blur(8px)',
      }}
      className="sticky top-0 z-50 px-6 py-3 flex items-center justify-between"
    >
      <Link href="/" className="flex items-center gap-3 group">
        <div
          className="text-2xl font-bold tracking-widest font-terminal"
          style={{ color: '#00ff41', textShadow: '0 0 20px rgba(0,255,65,0.5)' }}
        >
          ARGUS
        </div>
        <div className="text-xs text-slate-500 tracking-wider uppercase">Security Auditor</div>
      </Link>

      <div className="flex items-center gap-4">
        {auditId && (
          <div className="flex items-center gap-2 text-xs font-terminal text-slate-500">
            <span style={{ color: statusColor, fontFamily: 'monospace' }}>●</span>
            <span style={{ color: statusColor }}>
              {connectionStatus === 'connected' && isRunning ? 'SCANNING' : connectionStatus.toUpperCase()}
            </span>
          </div>
        )}
        {auditId && (
          <div className="flex gap-2 text-xs text-slate-600">
            <Link href={`/audit/${auditId}`} className="hover:text-slate-300 transition-colors">
              Dashboard
            </Link>
            <span>·</span>
            <Link href={`/audit/${auditId}/findings`} className="hover:text-slate-300 transition-colors">
              Findings
            </Link>
            <span>·</span>
            <Link href={`/audit/${auditId}/attack-graph`} className="hover:text-slate-300 transition-colors">
              Attack Graph
            </Link>
            <span>·</span>
            <Link href={`/audit/${auditId}/report`} className="hover:text-slate-300 transition-colors">
              Report
            </Link>
          </div>
        )}
      </div>
    </header>
  )
}

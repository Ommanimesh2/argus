'use client'
import { useAuditStore } from '@/store/audit-store'
import type { Hypothesis } from '@/lib/types'

const STATUS_CONFIG = {
  pending: {
    label: 'Pending',
    color: '#64748b',
    bg: 'rgba(100,116,139,0.08)',
    border: 'rgba(100,116,139,0.2)',
    icon: '⏳',
  },
  investigating: {
    label: 'Investigating',
    color: '#ffb800',
    bg: 'rgba(255,184,0,0.08)',
    border: 'rgba(255,184,0,0.3)',
    icon: '🔍',
  },
  confirmed: {
    label: 'Confirmed',
    color: '#ff0040',
    bg: 'rgba(255,0,64,0.08)',
    border: 'rgba(255,0,64,0.3)',
    icon: '⚠️',
  },
  rejected: {
    label: 'Rejected',
    color: '#00ff41',
    bg: 'rgba(0,255,65,0.05)',
    border: 'rgba(0,255,65,0.2)',
    icon: '✅',
  },
  inconclusive: {
    label: 'Inconclusive',
    color: '#64748b',
    bg: 'rgba(100,116,139,0.05)',
    border: 'rgba(100,116,139,0.2)',
    icon: '❓',
  },
}

const STATUS_ORDER = ['investigating', 'confirmed', 'pending', 'rejected', 'inconclusive']

function HypCard({ h }: { h: Hypothesis }) {
  const cfg = STATUS_CONFIG[h.status] ?? STATUS_CONFIG.pending
  return (
    <div
      className="p-3 rounded-lg mb-2 transition-all duration-300"
      style={{ background: cfg.bg, border: `1px solid ${cfg.border}` }}
    >
      <div className="flex items-start gap-2">
        <span className="text-base shrink-0 mt-0.5">{cfg.icon}</span>
        <div className="flex-1 min-w-0">
          <div className="text-sm text-slate-300">{h.question}</div>
          <div className="flex items-center gap-3 mt-1">
            <span className="text-xs font-terminal" style={{ color: cfg.color }}>
              {cfg.label}
            </span>
            <span className="text-xs text-slate-600 font-terminal">{h.audit_type}</span>
            <span className="text-xs text-slate-600 font-terminal">
              p={Math.round(h.priority * 100)}%
            </span>
          </div>
          {h.result && (
            <div className="text-xs text-slate-500 mt-1 italic">{h.result.slice(0, 80)}</div>
          )}
        </div>
      </div>
    </div>
  )
}

export function HypothesisTracker() {
  const hypotheses = useAuditStore((s) => s.hypotheses)

  if (hypotheses.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-slate-600">
        <div className="text-2xl mb-2">🧠</div>
        <div className="text-sm">Agent will generate hypotheses during scan</div>
      </div>
    )
  }

  const sorted = [...hypotheses].sort((a, b) => {
    return STATUS_ORDER.indexOf(a.status) - STATUS_ORDER.indexOf(b.status)
  })

  const confirmed = hypotheses.filter((h) => h.status === 'confirmed').length
  const investigating = hypotheses.filter((h) => h.status === 'investigating').length

  return (
    <div>
      <div className="text-xs text-slate-500 mb-3 uppercase tracking-wider">
        {confirmed} confirmed · {investigating} investigating · {hypotheses.length} total
      </div>
      <div className="max-h-[calc(100vh-300px)] overflow-y-auto pr-1">
        {sorted.map((h) => (
          <HypCard key={h.id} h={h} />
        ))}
      </div>
    </div>
  )
}

'use client'
import { useAuditStore } from '@/store/audit-store'
import { AnimatedCounter } from '@/components/shared/AnimatedCounter'

const SEVERITY_CONFIG = [
  {
    key: 'critical' as const,
    label: 'CRITICAL',
    color: '#ff0040',
    bg: 'rgba(255,0,64,0.08)',
    border: 'rgba(255,0,64,0.3)',
  },
  {
    key: 'high' as const,
    label: 'HIGH',
    color: '#ff6b35',
    bg: 'rgba(255,107,53,0.08)',
    border: 'rgba(255,107,53,0.3)',
  },
  {
    key: 'medium' as const,
    label: 'MEDIUM',
    color: '#ffb800',
    bg: 'rgba(255,184,0,0.08)',
    border: 'rgba(255,184,0,0.3)',
  },
  {
    key: 'low' as const,
    label: 'LOW',
    color: '#3b82f6',
    bg: 'rgba(59,130,246,0.08)',
    border: 'rgba(59,130,246,0.3)',
  },
]

export function SeveritySummary() {
  const summary = useAuditStore((s) => s.severitySummary)

  return (
    <div
      className="p-4 rounded-lg space-y-2"
      style={{ background: '#111118', border: '1px solid #2a2a3a' }}
    >
      <div className="text-xs text-slate-500 uppercase tracking-wider mb-3">Findings</div>
      {SEVERITY_CONFIG.map(({ key, label, color, bg, border }) => (
        <div
          key={key}
          className="flex items-center justify-between px-3 py-2 rounded"
          style={{ background: bg, border: `1px solid ${border}` }}
        >
          <span className="text-xs font-terminal tracking-wider" style={{ color }}>
            {label}
          </span>
          <span className="text-lg font-bold font-terminal" style={{ color }}>
            <AnimatedCounter value={summary[key]} />
          </span>
        </div>
      ))}
    </div>
  )
}

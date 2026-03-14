'use client'
import { useAuditStore } from '@/store/audit-store'

export function InvestigationBudgetGauge() {
  const total = useAuditStore((s) => s.budgetTotal)
  const remaining = useAuditStore((s) => s.budgetRemaining)
  const spent = useAuditStore((s) => s.budgetSpent)
  const pct = total > 0 ? (spent / total) * 100 : 0
  const color = pct > 80 ? '#ff0040' : pct > 50 ? '#ffb800' : '#00ff41'

  return (
    <div className="p-4 rounded-lg" style={{ background: '#111118', border: '1px solid #2a2a3a' }}>
      <div className="flex justify-between items-center mb-2">
        <div className="text-xs text-slate-500 uppercase tracking-wider">Investigation Budget</div>
        <div className="text-sm font-bold font-terminal" style={{ color }}>
          {remaining}/{total}
        </div>
      </div>
      <div className="h-2 rounded-full" style={{ background: '#1a1a24' }}>
        <div
          className="h-2 rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, background: color, boxShadow: `0 0 8px ${color}66` }}
        />
      </div>
      <div className="text-xs text-slate-600 mt-1 font-terminal">
        {spent} spent · {Math.round(pct)}% utilized
      </div>
    </div>
  )
}

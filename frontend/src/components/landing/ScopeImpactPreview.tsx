import { calculateBudget, estimateMinutes, calculateVulnCount } from '@/lib/scopes'

export function ScopeImpactPreview({ scopes }: { scopes: string[] }) {
  const budget = calculateBudget(scopes)
  const minutes = estimateMinutes(scopes)
  const vulns = calculateVulnCount(scopes)

  if (scopes.length === 0) {
    return (
      <div className="text-sm text-slate-600 text-center py-2">
        Select at least one scope to begin
      </div>
    )
  }

  return (
    <div className="grid grid-cols-3 gap-3">
      {[
        { label: 'Investigation Budget', value: budget, unit: 'cycles', color: '#00ff41' },
        { label: 'Est. Duration', value: `~${minutes}`, unit: 'minutes', color: '#00d4ff' },
        { label: 'Vulnerabilities in Scope', value: vulns, unit: 'checks', color: '#ffb800' },
      ].map(({ label, value, unit, color }) => (
        <div
          key={label}
          className="p-3 rounded-lg text-center"
          style={{ background: '#111118', border: '1px solid #2a2a3a' }}
        >
          <div className="text-2xl font-bold font-terminal" style={{ color }}>
            {value}
          </div>
          <div className="text-xs text-slate-500 mt-1">{unit}</div>
          <div className="text-xs text-slate-600 mt-0.5">{label}</div>
        </div>
      ))}
    </div>
  )
}

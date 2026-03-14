'use client'
import { SCOPE_DEFINITIONS, SCOPE_ICONS } from '@/lib/scopes'

interface ScopeSelectorProps {
  selected: string[]
  onChange: (scopes: string[]) => void
}

export function ScopeSelector({ selected, onChange }: ScopeSelectorProps) {
  const toggle = (scope: string) => {
    onChange(
      selected.includes(scope) ? selected.filter((s) => s !== scope) : [...selected, scope]
    )
  }

  return (
    <div>
      <label className="block text-sm font-medium text-slate-400 mb-3 uppercase tracking-wider">
        Audit Scopes
      </label>
      <div className="grid grid-cols-3 gap-3">
        {Object.entries(SCOPE_DEFINITIONS).map(([key, def]) => {
          const isSelected = selected.includes(key)
          return (
            <button
              key={key}
              type="button"
              onClick={() => toggle(key)}
              className="relative p-4 rounded-lg border text-left transition-all duration-200"
              style={{
                background: isSelected ? 'rgba(0,255,65,0.05)' : '#111118',
                borderColor: isSelected ? 'rgba(0,255,65,0.4)' : '#2a2a3a',
                boxShadow: isSelected ? '0 0 20px rgba(0,255,65,0.1)' : 'none',
              }}
            >
              <div className="text-xl mb-2">{SCOPE_ICONS[key]}</div>
              <div
                className="text-sm font-semibold"
                style={{ color: isSelected ? '#00ff41' : '#e2e8f0' }}
              >
                {def.label}
              </div>
              <div className="text-xs text-slate-500 mt-1 leading-relaxed">{def.description}</div>
              <div className="text-xs mt-2" style={{ color: isSelected ? '#00ff4199' : '#475569' }}>
                {def.vuln_count} vulnerabilities
              </div>
              {isSelected && (
                <div
                  className="absolute top-2 right-2 w-2 h-2 rounded-full"
                  style={{ background: '#00ff41', boxShadow: '0 0 6px #00ff41' }}
                />
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}

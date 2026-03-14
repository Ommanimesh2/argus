'use client'
import { useAuditStore } from '@/store/audit-store'

const PHASES = [
  { key: 'reconnaissance', label: 'Recon' },
  { key: 'initial_scan', label: 'Initial Scan' },
  { key: 'hypothesis_generation', label: 'Hypotheses' },
  { key: 'deep_investigation', label: 'Investigation' },
  { key: 'attack_graph', label: 'Attack Graph' },
  { key: 'reasoning', label: 'Reasoning' },
  { key: 'complete', label: 'Report' },
]

const PHASE_INDEX: Record<string, number> = {
  initialization: -1,
  reconnaissance: 0,
  reconnaissance_complete: 0,
  context_loaded: 0,
  initial_scan_complete: 1,
  hypothesis_generation: 2,
  deep_investigation: 3,
  investigation_complete: 3,
  attack_graph_complete: 4,
  reasoning_complete: 5,
  complete: 6,
}

export function PhaseProgress() {
  const currentPhase = useAuditStore((s) => s.currentPhase)
  const phaseProgress = useAuditStore((s) => s.phaseProgress)
  const isComplete = useAuditStore((s) => s.isComplete)

  const currentIdx = PHASE_INDEX[currentPhase] ?? -1

  return (
    <div className="p-4 rounded-lg" style={{ background: '#111118', border: '1px solid #2a2a3a' }}>
      <div className="text-xs text-slate-500 uppercase tracking-wider mb-4">Audit Phase</div>
      <div className="space-y-1">
        {PHASES.map((phase, i) => {
          const isDone = i < currentIdx || isComplete
          const isCurrent = i === currentIdx && !isComplete

          return (
            <div key={phase.key} className="flex items-center gap-3">
              <div className="relative flex items-center justify-center w-5 h-5 shrink-0">
                {isDone ? (
                  <div
                    className="w-5 h-5 rounded-full flex items-center justify-center"
                    style={{ background: 'rgba(0,255,65,0.2)', border: '1px solid #00ff41' }}
                  >
                    <div className="w-2 h-2 rounded-full" style={{ background: '#00ff41' }} />
                  </div>
                ) : isCurrent ? (
                  <div
                    className="w-5 h-5 rounded-full"
                    style={{
                      background: 'rgba(0,255,65,0.15)',
                      border: '1px solid rgba(0,255,65,0.6)',
                      animation: 'pulse-green 2s infinite',
                    }}
                  >
                    <div
                      className="w-full h-full rounded-full"
                      style={{ background: 'rgba(0,255,65,0.3)' }}
                    />
                  </div>
                ) : (
                  <div className="w-4 h-4 rounded-full" style={{ border: '1px solid #2a2a3a' }} />
                )}
              </div>
              <span
                className="text-sm font-terminal"
                style={{
                  color: isDone ? '#00ff41' : isCurrent ? '#e2e8f0' : '#475569',
                  fontWeight: isCurrent ? '600' : '400',
                }}
              >
                {phase.label}
              </span>
            </div>
          )
        })}
      </div>
      {/* Progress bar */}
      <div className="mt-4">
        <div className="h-1 rounded-full" style={{ background: '#1a1a24' }}>
          <div
            className="h-1 rounded-full transition-all duration-1000"
            style={{
              width: `${phaseProgress * 100}%`,
              background: 'linear-gradient(90deg, #00ff41, #00d4ff)',
            }}
          />
        </div>
        <div className="text-xs text-slate-600 mt-1 font-terminal">
          {Math.round(phaseProgress * 100)}%
        </div>
      </div>
    </div>
  )
}

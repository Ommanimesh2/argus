'use client'
import { useState } from 'react'
import { useAuditStore } from '@/store/audit-store'
import { ChevronDown, ChevronRight } from 'lucide-react'
import type { ReasoningChain } from '@/lib/types'
import { SEVERITY_BADGE_CLASS, normalizeSeverity } from '@/lib/severity'

function ChainCard({ chain }: { chain: ReasoningChain }) {
  const [expanded, setExpanded] = useState(false)
  const sev = normalizeSeverity(chain.severity)
  const badgeClass = SEVERITY_BADGE_CLASS[sev]

  return (
    <div className="rounded-lg mb-2 overflow-hidden" style={{ border: '1px solid #2a2a3a' }}>
      <button
        type="button"
        className="w-full flex items-center justify-between p-3 text-left hover:bg-white/5 transition-colors"
        style={{ background: '#111118' }}
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          <span className={`text-xs px-2 py-0.5 rounded font-terminal ${badgeClass}`}>{sev}</span>
          <span className="text-sm text-slate-300 font-terminal">{chain.finding_id}</span>
        </div>
        <div className="flex items-center gap-2 text-slate-500">
          <span className="text-xs">{chain.reasoning_steps?.length ?? 0} steps</span>
          {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </div>
      </button>
      {expanded && (
        <div className="p-3" style={{ background: '#0d0d15', borderTop: '1px solid #1a1a24' }}>
          <ol className="space-y-2">
            {(chain.reasoning_steps ?? []).map((step, i) => (
              <li key={i} className="flex gap-3 text-sm">
                <span
                  className="shrink-0 font-terminal text-xs mt-0.5"
                  style={{ color: '#00d4ff' }}
                >
                  {i + 1}.
                </span>
                <span className="text-slate-400">{step}</span>
              </li>
            ))}
          </ol>
          {chain.conclusion && (
            <div
              className="mt-3 p-2 rounded text-sm text-slate-300"
              style={{
                background: 'rgba(255,0,64,0.08)',
                border: '1px solid rgba(255,0,64,0.2)',
              }}
            >
              <div className="text-xs text-red-400 mb-1 font-terminal uppercase tracking-wider">
                Conclusion
              </div>
              {chain.conclusion}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export function ReasoningChainViewer() {
  const chains = useAuditStore((s) => s.reasoningChains)

  if (chains.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-slate-600">
        <div className="text-2xl mb-2">🧬</div>
        <div className="text-sm">Deep reasoning chains appear after analysis</div>
      </div>
    )
  }

  return (
    <div className="max-h-[calc(100vh-300px)] overflow-y-auto pr-1">
      <div className="text-xs text-slate-500 mb-3 uppercase tracking-wider">
        {chains.length} reasoning chain{chains.length !== 1 ? 's' : ''}
      </div>
      {chains.map((c, i) => (
        <ChainCard key={i} chain={c} />
      ))}
    </div>
  )
}

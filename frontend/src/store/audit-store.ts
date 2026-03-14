import { create } from 'zustand'
import type {
  AuditFinding,
  Hypothesis,
  AttackPath,
  ReasoningChain,
  LogEntry,
  SSEEvent,
  ConnectionStatus,
  SeveritySummary,
} from '@/lib/types'
import { normalizeSeverity } from '@/lib/severity'

interface AuditStore {
  // Connection
  auditId: string | null
  connectionStatus: ConnectionStatus

  // Phase
  currentPhase: string
  phaseProgress: number

  // State flags
  isRunning: boolean
  isComplete: boolean
  isCancelled: boolean

  // Findings
  findings: AuditFinding[]
  severitySummary: SeveritySummary

  // Intelligence
  hypotheses: Hypothesis[]
  attackPaths: AttackPath[]
  reasoningChains: ReasoningChain[]
  logEntries: LogEntry[]

  // Budget
  budgetTotal: number
  budgetRemaining: number
  budgetSpent: number

  // Config
  activeScopes: string[]

  // Actions
  setAuditId: (id: string) => void
  setConnectionStatus: (s: ConnectionStatus) => void
  setActiveScopes: (scopes: string[]) => void
  handleSSEEvent: (event: SSEEvent) => void
  reset: () => void
}

const initialState = {
  auditId: null,
  connectionStatus: 'disconnected' as ConnectionStatus,
  currentPhase: '',
  phaseProgress: 0,
  isRunning: false,
  isComplete: false,
  isCancelled: false,
  findings: [],
  severitySummary: { critical: 0, high: 0, medium: 0, low: 0, info: 0 },
  hypotheses: [],
  attackPaths: [],
  reasoningChains: [],
  logEntries: [],
  budgetTotal: 20,
  budgetRemaining: 20,
  budgetSpent: 0,
  activeScopes: [],
}

export const useAuditStore = create<AuditStore>((set) => ({
  ...initialState,

  setAuditId: (id) => set({ auditId: id }),
  setConnectionStatus: (s) => set({ connectionStatus: s }),
  setActiveScopes: (scopes) => set({ activeScopes: scopes }),

  handleSSEEvent: (event: SSEEvent) => {
    const { type, data } = event

    switch (type) {
      case 'phase_update': {
        set({
          currentPhase: event.phase ?? '',
          phaseProgress: event.progress ?? 0,
          isRunning: true,
        })
        break
      }

      case 'finding': {
        if (!data) break
        const finding = data as unknown as AuditFinding
        const sev = normalizeSeverity(finding.severity ?? 'INFO')
        set((s) => {
          const existing = s.findings.find((f) => f.id === finding.id)
          if (existing) return {}
          const newSummary = { ...s.severitySummary }
          const key = sev.toLowerCase() as keyof SeveritySummary
          if (key in newSummary) newSummary[key] = (newSummary[key] ?? 0) + 1
          return {
            findings: [...s.findings, { ...finding, severity: sev }],
            severitySummary: newSummary,
          }
        })
        break
      }

      case 'hypothesis_generated': {
        if (!data) break
        const hyp = data as unknown as Hypothesis
        set((s) => {
          if (s.hypotheses.find((h) => h.id === hyp.id)) return {}
          return { hypotheses: [...s.hypotheses, hyp] }
        })
        break
      }

      case 'investigation_result': {
        if (!data) break
        const { hypothesis_id, status, evidence_summary } = data as {
          hypothesis_id: string
          status: string
          evidence_summary: string
        }
        set((s) => ({
          hypotheses: s.hypotheses.map((h) =>
            h.id === hypothesis_id
              ? { ...h, status: status as Hypothesis['status'], result: evidence_summary }
              : h
          ),
        }))
        break
      }

      case 'budget_update': {
        if (!data) break
        const { total, remaining, spent } = data as {
          total: number
          remaining: number
          spent: number
        }
        set({ budgetTotal: total, budgetRemaining: remaining, budgetSpent: spent })
        break
      }

      case 'attack_path_discovered': {
        if (!data) break
        const path = data as unknown as AttackPath
        set((s) => ({ attackPaths: [...s.attackPaths, path] }))
        break
      }

      case 'reasoning_chain': {
        if (!data) break
        const chain = data as unknown as ReasoningChain
        set((s) => ({
          reasoningChains: [...s.reasoningChains, chain],
        }))
        break
      }

      case 'log': {
        if (!data) break
        const entry = data as unknown as LogEntry
        const timestamp = new Date().toISOString()
        set((s) => ({
          logEntries: [
            ...s.logEntries.slice(-499), // keep last 500
            { ...entry, timestamp },
          ],
        }))
        break
      }

      case 'error': {
        set({ connectionStatus: 'error', isRunning: false })
        break
      }

      case 'complete': {
        set({ isComplete: true, isRunning: false, phaseProgress: 1.0 })
        break
      }

      case 'cancelled': {
        set({ isCancelled: true, isRunning: false })
        break
      }
    }
  },

  reset: () => set({ ...initialState }),
}))

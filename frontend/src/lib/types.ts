// Mirrors AuditStateV3 / AuditFinding from agents/graph/state.py

export interface AuditFinding {
  id: string
  title: string
  type: string
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO'
  audit_type: string
  description: string
  evidence: string
  context?: Record<string, unknown>
  risk_score?: number
  cis_benchmark?: string | null
  remediation?: string
  discovered_by?: string
  reasoning_chain?: string[] | null
}

export interface Hypothesis {
  id: string
  question: string
  status: 'pending' | 'investigating' | 'confirmed' | 'rejected' | 'inconclusive'
  priority: number
  audit_type: string
  triggered_by?: string
  depth?: number
  result?: string
}

export interface AttackPath {
  entry_point: string
  target: string
  path: Array<{ from: string; to: string; via: string }>
  composite_risk: number
  findings_involved: string[]
}

export interface ReasoningChain {
  finding_id: string
  reasoning_steps: string[]
  conclusion: string
  severity: string
}

export interface InvestigationRecord {
  hypothesis_id: string
  question: string
  commands_run: string[]
  result: string
  found_new_finding: boolean
  depth: number
  timestamp: string
}

export interface LogEntry {
  level: 'info' | 'warn' | 'error' | 'debug'
  source: string
  message: string
  command?: string
  timestamp?: string
}

// SSE Event types
export type SSEEventType =
  | 'phase_update'
  | 'finding'
  | 'hypothesis_generated'
  | 'investigation_result'
  | 'budget_update'
  | 'attack_path_discovered'
  | 'reasoning_chain'
  | 'log'
  | 'error'
  | 'complete'
  | 'cancelled'

export interface SSEEvent {
  type: SSEEventType
  phase?: string
  progress?: number
  data?: Record<string, unknown>
  error?: string
}

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error'

export type AuditPhase =
  | 'initialization'
  | 'reconnaissance'
  | 'reconnaissance_complete'
  | 'context_loaded'
  | 'initial_scan_complete'
  | 'hypothesis_generation'
  | 'deep_investigation'
  | 'investigation_complete'
  | 'attack_graph_complete'
  | 'reasoning_complete'
  | 'complete'
  | 'error'

export interface AuditStartRequest {
  external_targets: string[]
  internal_targets: string[]
  jump_box_ip: string
  ssh_key_path: string
  environment_context: Record<string, unknown>
  scopes: string[]
  region: string
  scope_tag: string
}

export interface AuditStartResponse {
  audit_id: string
  stream_url: string
  status_url: string
  report_url: string
}

export interface ScopeDefinition {
  label: string
  description: string
  budget_weight: number
  vuln_count: number
}

export interface SeveritySummary {
  critical: number
  high: number
  medium: number
  low: number
  info: number
}

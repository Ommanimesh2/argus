export type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO'

export const SEVERITY_ORDER: Record<Severity, number> = {
  CRITICAL: 0,
  HIGH: 1,
  MEDIUM: 2,
  LOW: 3,
  INFO: 4,
}

export const SEVERITY_COLORS: Record<Severity, string> = {
  CRITICAL: '#ff0040',
  HIGH: '#ff6b35',
  MEDIUM: '#ffb800',
  LOW: '#3b82f6',
  INFO: '#64748b',
}

export const SEVERITY_BG: Record<Severity, string> = {
  CRITICAL: 'rgba(255,0,64,0.1)',
  HIGH: 'rgba(255,107,53,0.1)',
  MEDIUM: 'rgba(255,184,0,0.1)',
  LOW: 'rgba(59,130,246,0.1)',
  INFO: 'rgba(100,116,139,0.1)',
}

export const SEVERITY_BORDER: Record<Severity, string> = {
  CRITICAL: 'rgba(255,0,64,0.4)',
  HIGH: 'rgba(255,107,53,0.4)',
  MEDIUM: 'rgba(255,184,0,0.3)',
  LOW: 'rgba(59,130,246,0.3)',
  INFO: 'rgba(100,116,139,0.3)',
}

export const SEVERITY_BADGE_CLASS: Record<Severity, string> = {
  CRITICAL: 'bg-red-950 text-red-400 border border-red-800',
  HIGH: 'bg-orange-950 text-orange-400 border border-orange-800',
  MEDIUM: 'bg-yellow-950 text-yellow-400 border border-yellow-800',
  LOW: 'bg-blue-950 text-blue-400 border border-blue-800',
  INFO: 'bg-slate-900 text-slate-400 border border-slate-700',
}

export const SEVERITY_EMOJI: Record<Severity, string> = {
  CRITICAL: '🔴',
  HIGH: '🟠',
  MEDIUM: '🟡',
  LOW: '🔵',
  INFO: '⚪',
}

export function normalizeSeverity(s: string | undefined | null): Severity {
  const upper = (s ?? '').toUpperCase() as Severity
  return SEVERITY_ORDER[upper] !== undefined ? upper : 'INFO'
}

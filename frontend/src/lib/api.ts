import type { AuditStartRequest, AuditStartResponse } from './types'

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!res.ok) {
    const err = await res.text().catch(() => res.statusText)
    throw new Error(`API ${res.status}: ${err}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  startAudit: (body: AuditStartRequest) =>
    apiFetch<AuditStartResponse>('/api/audit/start', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  getStatus: (auditId: string) =>
    apiFetch<{
      audit_id: string
      phase: string
      progress: number
      finished: boolean
      findings_count: number
    }>(`/api/audit/${auditId}/status`),

  getReport: (auditId: string) =>
    apiFetch<{ audit_id: string; report: string }>(`/api/audit/${auditId}/report`),

  getFindings: (auditId: string, params?: { severity?: string; audit_type?: string }) => {
    const qs = new URLSearchParams(params as Record<string, string>).toString()
    return apiFetch<{ findings: unknown[]; total: number; severity_summary: unknown }>(
      `/api/audit/${auditId}/findings${qs ? `?${qs}` : ''}`
    )
  },

  getHypotheses: (auditId: string) =>
    apiFetch<{ hypotheses: unknown[]; total: number; summary: unknown }>(
      `/api/audit/${auditId}/hypotheses`
    ),

  getAttackPaths: (auditId: string) =>
    apiFetch<{ attack_paths: unknown[]; total: number }>(
      `/api/audit/${auditId}/attack-paths`
    ),

  getLogs: (auditId: string, params?: { limit?: number; offset?: number }) => {
    const qs = new URLSearchParams(
      Object.fromEntries(Object.entries(params ?? {}).map(([k, v]) => [k, String(v)]))
    ).toString()
    return apiFetch<{ logs: unknown[]; total: number }>(
      `/api/audit/${auditId}/logs${qs ? `?${qs}` : ''}`
    )
  },

  cancelAudit: (auditId: string) =>
    apiFetch<{ status: string; audit_id: string }>(`/api/audit/${auditId}/cancel`, {
      method: 'POST',
    }),

  getScopes: () =>
    apiFetch<{ scopes: Record<string, { label: string; description: string; budget_weight: number; vuln_count: number }> }>(
      '/api/scopes'
    ),

  streamUrl: (auditId: string) => `${API_URL}/api/audit/${auditId}/stream`,
}

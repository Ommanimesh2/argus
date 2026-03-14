'use client'
import { use, useEffect, useState } from 'react'
import { api } from '@/lib/api'
import { Header } from '@/components/layout/Header'
import { ArrowLeft } from 'lucide-react'
import Link from 'next/link'
import type { AuditFinding } from '@/lib/types'
import { SEVERITY_BADGE_CLASS, normalizeSeverity, SEVERITY_ORDER } from '@/lib/severity'

export default function FindingsPage({ params }: { params: Promise<{ auditId: string }> }) {
  const { auditId } = use(params)
  const [findings, setFindings] = useState<AuditFinding[]>([])
  const [loading, setLoading] = useState(true)
  const [severityFilter, setSeverityFilter] = useState<string>('')
  const [sortField, setSortField] = useState<'severity' | 'title'>('severity')
  const [selected, setSelected] = useState<AuditFinding | null>(null)

  useEffect(() => {
    api
      .getFindings(auditId, severityFilter ? { severity: severityFilter } : {})
      .then((res) => setFindings(res.findings as AuditFinding[]))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [auditId, severityFilter])

  const sorted = [...findings].sort((a, b) => {
    if (sortField === 'severity') {
      return (
        (SEVERITY_ORDER[normalizeSeverity(a.severity)] ?? 5) -
        (SEVERITY_ORDER[normalizeSeverity(b.severity)] ?? 5)
      )
    }
    return a.title.localeCompare(b.title)
  })

  const severities = ['', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO']

  // sortField is used for future extensibility; suppress unused warning
  void sortField
  void setSortField

  return (
    <div className="min-h-screen" style={{ background: '#0a0a0f' }}>
      <Header auditId={auditId} />
      <div
        className="flex items-center gap-3 px-6 py-3"
        style={{ borderBottom: '1px solid #2a2a3a' }}
      >
        <Link
          href={`/audit/${auditId}`}
          className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-300 transition-colors font-terminal"
        >
          <ArrowLeft size={14} /> Dashboard
        </Link>
        <span className="text-slate-700">·</span>
        <span className="text-sm font-terminal" style={{ color: '#00ff41' }}>
          Findings
        </span>
      </div>

      <div className="px-6 py-4">
        {/* Filters */}
        <div className="flex items-center gap-3 mb-4">
          <div className="flex gap-2">
            {severities.map((sev) => (
              <button
                key={sev || 'all'}
                type="button"
                onClick={() => setSeverityFilter(sev)}
                className="px-3 py-1 rounded text-xs font-terminal transition-colors"
                style={{
                  background: severityFilter === sev ? 'rgba(0,255,65,0.1)' : '#111118',
                  color: severityFilter === sev ? '#00ff41' : '#64748b',
                  border: `1px solid ${severityFilter === sev ? 'rgba(0,255,65,0.3)' : '#2a2a3a'}`,
                }}
              >
                {sev || 'All'}
              </button>
            ))}
          </div>
          <span className="text-xs text-slate-600 ml-auto">{findings.length} findings</span>
        </div>

        {/* Table */}
        <div className="rounded-lg overflow-hidden" style={{ border: '1px solid #2a2a3a' }}>
          <table className="w-full text-sm">
            <thead>
              <tr style={{ background: '#111118', borderBottom: '1px solid #2a2a3a' }}>
                {['Severity', 'ID', 'Title', 'Type', 'Risk'].map((col) => (
                  <th
                    key={col}
                    className="px-4 py-3 text-left text-xs font-terminal text-slate-500 uppercase tracking-wider"
                  >
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-slate-600">
                    Loading...
                  </td>
                </tr>
              ) : sorted.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-slate-600">
                    No findings yet
                  </td>
                </tr>
              ) : (
                sorted.map((f, i) => {
                  const sev = normalizeSeverity(f.severity)
                  return (
                    <tr
                      key={f.id ?? i}
                      className="border-b cursor-pointer hover:bg-white/5 transition-colors"
                      style={{ borderColor: '#1a1a24' }}
                      onClick={() => setSelected(f)}
                    >
                      <td className="px-4 py-3">
                        <span
                          className={`px-2 py-0.5 rounded text-xs font-terminal ${SEVERITY_BADGE_CLASS[sev]}`}
                        >
                          {sev}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-terminal text-xs text-slate-500">{f.id}</td>
                      <td className="px-4 py-3 text-slate-300">{f.title}</td>
                      <td className="px-4 py-3 text-xs text-slate-500 font-terminal">
                        {f.audit_type}
                      </td>
                      <td className="px-4 py-3 font-terminal text-xs text-slate-500">
                        {f.risk_score?.toFixed(1)}
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Detail modal */}
      {selected && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-6"
          style={{ background: 'rgba(0,0,0,0.8)' }}
          onClick={() => setSelected(null)}
        >
          <div
            className="max-w-2xl w-full rounded-xl p-6 space-y-4"
            style={{ background: '#111118', border: '1px solid #2a2a3a' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between">
              <div>
                <span
                  className={`text-xs px-2 py-0.5 rounded font-terminal ${SEVERITY_BADGE_CLASS[normalizeSeverity(selected.severity)]}`}
                >
                  {selected.severity}
                </span>
                <h2 className="text-lg font-semibold text-slate-200 mt-2">{selected.title}</h2>
              </div>
              <button
                type="button"
                onClick={() => setSelected(null)}
                className="text-slate-500 hover:text-slate-300 text-xl"
              >
                ×
              </button>
            </div>
            <p className="text-sm text-slate-400">{selected.description}</p>
            {selected.evidence && (
              <div>
                <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Evidence</div>
                <div
                  className="text-xs font-terminal p-3 rounded"
                  style={{
                    background: '#0a0a0f',
                    color: '#94a3b8',
                    border: '1px solid #2a2a3a',
                  }}
                >
                  {selected.evidence}
                </div>
              </div>
            )}
            {selected.remediation && (
              <div>
                <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">
                  Remediation
                </div>
                <div className="text-sm text-slate-400">{selected.remediation}</div>
              </div>
            )}
            {selected.cis_benchmark && (
              <div className="text-xs text-slate-600 font-terminal">
                CIS: {selected.cis_benchmark}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

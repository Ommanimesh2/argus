'use client'
import { motion } from 'framer-motion'
import type { AuditFinding } from '@/lib/types'
import { SEVERITY_BADGE_CLASS, SEVERITY_BORDER, SEVERITY_BG } from '@/lib/severity'
import { normalizeSeverity } from '@/lib/severity'

export function FindingCard({ finding }: { finding: AuditFinding }) {
  const sev = normalizeSeverity(finding.severity)
  const badgeClass = SEVERITY_BADGE_CLASS[sev] ?? SEVERITY_BADGE_CLASS.INFO
  const borderColor = SEVERITY_BORDER[sev] ?? SEVERITY_BORDER.INFO
  const bgColor = SEVERITY_BG[sev] ?? SEVERITY_BG.INFO

  return (
    <motion.div
      initial={{ x: 60, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className="p-4 rounded-lg mb-3"
      style={{ background: bgColor, border: `1px solid ${borderColor}` }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className={`text-xs px-2 py-0.5 rounded font-terminal font-bold ${badgeClass}`}>
              {sev}
            </span>
            {finding.audit_type && (
              <span
                className="text-xs px-2 py-0.5 rounded font-terminal"
                style={{
                  background: 'rgba(0,212,255,0.1)',
                  color: '#00d4ff',
                  border: '1px solid rgba(0,212,255,0.2)',
                }}
              >
                {finding.audit_type}
              </span>
            )}
          </div>
          <div className="text-sm font-semibold text-slate-200 truncate">{finding.title}</div>
          {finding.description && (
            <div className="text-xs text-slate-500 mt-1 line-clamp-2">{finding.description}</div>
          )}
        </div>
        {finding.risk_score !== undefined && (
          <div className="text-xs font-terminal shrink-0" style={{ color: '#64748b' }}>
            {(finding.risk_score * 10).toFixed(1)}
          </div>
        )}
      </div>
      {finding.evidence && (
        <div
          className="mt-2 text-xs font-terminal p-2 rounded"
          style={{ background: '#0a0a0f', color: '#64748b', border: '1px solid #2a2a3a' }}
        >
          {finding.evidence.slice(0, 120)}
          {finding.evidence.length > 120 ? '...' : ''}
        </div>
      )}
    </motion.div>
  )
}

'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuditStore } from '@/store/audit-store'
import { api } from '@/lib/api'
import { Square, FileText } from 'lucide-react'

export function AuditControls({ auditId }: { auditId: string }) {
  const router = useRouter()
  const isComplete = useAuditStore((s) => s.isComplete)
  const isRunning = useAuditStore((s) => s.isRunning)
  const [cancelling, setCancelling] = useState(false)

  const cancel = async () => {
    setCancelling(true)
    try {
      await api.cancelAudit(auditId)
    } catch {
      /* ignore */
    }
    setCancelling(false)
  }

  return (
    <div
      className="p-4 rounded-lg space-y-2"
      style={{ background: '#111118', border: '1px solid #2a2a3a' }}
    >
      {isComplete && (
        <button
          onClick={() => router.push(`/audit/${auditId}/report`)}
          className="w-full flex items-center justify-center gap-2 py-2 rounded text-sm font-terminal transition-colors"
          style={{
            background: 'rgba(0,255,65,0.1)',
            border: '1px solid rgba(0,255,65,0.3)',
            color: '#00ff41',
          }}
        >
          <FileText size={14} />
          View Report
        </button>
      )}
      {isRunning && (
        <button
          onClick={cancel}
          disabled={cancelling}
          className="w-full flex items-center justify-center gap-2 py-2 rounded text-sm font-terminal transition-colors disabled:opacity-50"
          style={{
            background: 'rgba(255,0,64,0.08)',
            border: '1px solid rgba(255,0,64,0.2)',
            color: '#ff6b8a',
          }}
        >
          <Square size={14} />
          {cancelling ? 'Cancelling...' : 'Cancel Audit'}
        </button>
      )}
    </div>
  )
}

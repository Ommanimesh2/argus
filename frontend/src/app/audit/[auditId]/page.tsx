'use client'
import { useState, use } from 'react'
import { useAuditStore } from '@/store/audit-store'
import { useAuditStream } from '@/hooks/useAuditStream'
import { Header } from '@/components/layout/Header'
import { PhaseProgress } from '@/components/dashboard/PhaseProgress'
import { SeveritySummary } from '@/components/dashboard/SeveritySummary'
import { InvestigationBudgetGauge } from '@/components/dashboard/InvestigationBudgetGauge'
import { FindingsFeed } from '@/components/dashboard/FindingsFeed'
import { HypothesisTracker } from '@/components/dashboard/HypothesisTracker'
import { AttackGraphPreview } from '@/components/attack-graph/AttackGraphPreview'
import { ReasoningChainViewer } from '@/components/dashboard/ReasoningChainViewer'
import { LiveTerminal } from '@/components/dashboard/LiveTerminal'
import { AuditControls } from '@/components/dashboard/AuditControls'
import { CriticalFlash } from '@/components/shared/CriticalFlash'

const TABS = [
  { id: 'feed', label: 'Live Feed' },
  { id: 'hypotheses', label: 'Hypotheses' },
  { id: 'graph', label: 'Attack Graph' },
  { id: 'reasoning', label: 'Reasoning' },
]

export default function AuditPage({ params }: { params: Promise<{ auditId: string }> }) {
  const { auditId } = use(params)
  const [activeTab, setActiveTab] = useState('feed')

  const storeAuditId = useAuditStore((s) => s.auditId)
  const setAuditId = useAuditStore((s) => s.setAuditId)
  if (storeAuditId !== auditId) setAuditId(auditId)

  useAuditStream(auditId)

  return (
    <div className="min-h-screen flex flex-col" style={{ background: '#0a0a0f' }}>
      <CriticalFlash />
      <Header auditId={auditId} />

      <div className="flex-1 grid grid-cols-12 gap-4 p-4 max-w-screen-2xl mx-auto w-full">
        {/* Left sidebar */}
        <div className="col-span-2 space-y-3">
          <PhaseProgress />
          <InvestigationBudgetGauge />
          <SeveritySummary />
          <AuditControls auditId={auditId} />
        </div>

        {/* Main content */}
        <div className="col-span-7">
          <div className="flex gap-1 mb-4">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className="px-4 py-2 rounded-lg text-sm font-terminal transition-all"
                style={{
                  background: activeTab === tab.id ? 'rgba(0,255,65,0.1)' : '#111118',
                  color: activeTab === tab.id ? '#00ff41' : '#64748b',
                  border: `1px solid ${activeTab === tab.id ? 'rgba(0,255,65,0.3)' : '#2a2a3a'}`,
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>
          <div
            className="rounded-lg p-4"
            style={{ background: '#111118', border: '1px solid #2a2a3a', minHeight: '400px' }}
          >
            {activeTab === 'feed' && <FindingsFeed />}
            {activeTab === 'hypotheses' && <HypothesisTracker />}
            {activeTab === 'graph' && <AttackGraphPreview auditId={auditId} />}
            {activeTab === 'reasoning' && <ReasoningChainViewer />}
          </div>
        </div>

        {/* Right: terminal */}
        <div className="col-span-3" style={{ height: 'calc(100vh - 80px)' }}>
          <LiveTerminal />
        </div>
      </div>
    </div>
  )
}

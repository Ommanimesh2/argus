'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { ScopeSelector } from '@/components/landing/ScopeSelector'
import { TargetsInput } from '@/components/landing/TargetsInput'
import { ScopeImpactPreview } from '@/components/landing/ScopeImpactPreview'
import { api } from '@/lib/api'
import { useAuditStore } from '@/store/audit-store'
import { AWS_REGIONS } from '@/lib/scopes'
import { Loader2, ChevronDown, ChevronUp } from 'lucide-react'

export default function HomePage() {
  const router = useRouter()
  const { setAuditId, setActiveScopes, reset } = useAuditStore()

  const [scopes, setScopes] = useState(['iam', 'compute', 'monitoring'])
  const [region, setRegion] = useState('us-east-1')
  const [scopeTag, setScopeTag] = useState('AuditDemo')
  const [externalTargets, setExternalTargets] = useState<string[]>([])
  const [internalTargets, setInternalTargets] = useState<string[]>([])
  const [jumpBoxIp, setJumpBoxIp] = useState('')
  const [sshKeyPath, setSshKeyPath] = useState('')
  const [envContext, setEnvContext] = useState('')
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleStart = async () => {
    if (scopes.length === 0) {
      setError('Select at least one scope')
      return
    }
    setError(null)
    setLoading(true)
    try {
      reset()
      let envCtxParsed: Record<string, unknown> = {}
      if (envContext.trim()) {
        try {
          envCtxParsed = JSON.parse(envContext)
        } catch {
          /* ignore */
        }
      }
      const res = await api.startAudit({
        scopes,
        region,
        scope_tag: scopeTag,
        external_targets: externalTargets,
        internal_targets: internalTargets,
        jump_box_ip: jumpBoxIp,
        ssh_key_path: sshKeyPath,
        environment_context: envCtxParsed,
      })
      setAuditId(res.audit_id)
      setActiveScopes(scopes)
      router.push(`/audit/${res.audit_id}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to start audit')
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* Hero */}
      <div className="flex flex-col items-center justify-center pt-16 pb-12 px-6">
        <div
          className="text-6xl font-bold tracking-widest font-terminal mb-3"
          style={{
            color: '#00ff41',
            textShadow: '0 0 40px rgba(0,255,65,0.4), 0 0 80px rgba(0,255,65,0.15)',
          }}
        >
          ARGUS
        </div>
        <div className="text-slate-500 text-sm tracking-[0.3em] uppercase mb-2">
          Autonomous Reasoning & Graph-based Understanding System
        </div>
        <div className="text-slate-600 text-xs tracking-wider">
          AI-powered AWS Infrastructure Security Auditor
        </div>
      </div>

      {/* Form */}
      <div className="max-w-3xl mx-auto w-full px-6 pb-16 space-y-6">
        {/* Region */}
        <div>
          <label className="block text-sm font-medium text-slate-400 mb-2 uppercase tracking-wider">
            AWS Region
          </label>
          <select
            value={region}
            onChange={(e) => setRegion(e.target.value)}
            className="w-full px-3 py-2 rounded-lg text-sm font-terminal text-slate-300 outline-none border"
            style={{ background: '#111118', borderColor: '#2a2a3a' }}
          >
            {AWS_REGIONS.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </div>

        {/* Scopes */}
        <ScopeSelector selected={scopes} onChange={setScopes} />

        {/* Impact Preview */}
        <ScopeImpactPreview scopes={scopes} />

        {/* Targets */}
        <TargetsInput
          label="External Targets"
          placeholder="203.0.113.10 (press Enter)"
          values={externalTargets}
          onChange={setExternalTargets}
        />
        <TargetsInput
          label="Internal Targets"
          placeholder="10.0.1.5 (press Enter)"
          values={internalTargets}
          onChange={setInternalTargets}
        />

        {/* Advanced */}
        <div>
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="flex items-center gap-2 text-sm text-slate-500 hover:text-slate-400 transition-colors"
          >
            {showAdvanced ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            Advanced Options
          </button>
          {showAdvanced && (
            <div
              className="mt-4 space-y-4 p-4 rounded-lg"
              style={{ background: '#111118', border: '1px solid #2a2a3a' }}
            >
              <div>
                <label className="block text-xs text-slate-500 mb-1 uppercase tracking-wider">
                  Scope Tag
                </label>
                <input
                  value={scopeTag}
                  onChange={(e) => setScopeTag(e.target.value)}
                  className="w-full px-3 py-2 rounded text-sm font-terminal text-slate-300 outline-none border"
                  style={{ background: '#1a1a24', borderColor: '#2a2a3a' }}
                  placeholder="AuditDemo"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1 uppercase tracking-wider">
                  Jump Box IP
                </label>
                <input
                  value={jumpBoxIp}
                  onChange={(e) => setJumpBoxIp(e.target.value)}
                  className="w-full px-3 py-2 rounded text-sm font-terminal text-slate-300 outline-none border"
                  style={{ background: '#1a1a24', borderColor: '#2a2a3a' }}
                  placeholder="10.0.0.1"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1 uppercase tracking-wider">
                  SSH Key Path
                </label>
                <input
                  value={sshKeyPath}
                  onChange={(e) => setSshKeyPath(e.target.value)}
                  className="w-full px-3 py-2 rounded text-sm font-terminal text-slate-300 outline-none border"
                  style={{ background: '#1a1a24', borderColor: '#2a2a3a' }}
                  placeholder="~/.ssh/audit_key.pem"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1 uppercase tracking-wider">
                  Environment Context (JSON)
                </label>
                <textarea
                  value={envContext}
                  onChange={(e) => setEnvContext(e.target.value)}
                  rows={3}
                  className="w-full px-3 py-2 rounded text-sm font-terminal text-slate-300 outline-none border resize-none"
                  style={{ background: '#1a1a24', borderColor: '#2a2a3a' }}
                  placeholder='{"account_id": "123456789"}'
                />
              </div>
            </div>
          )}
        </div>

        {error && (
          <div
            className="text-sm px-4 py-3 rounded-lg"
            style={{
              background: 'rgba(255,0,64,0.1)',
              border: '1px solid rgba(255,0,64,0.3)',
              color: '#ff6b8a',
            }}
          >
            {error}
          </div>
        )}

        <button
          onClick={handleStart}
          disabled={loading || scopes.length === 0}
          className="w-full py-4 rounded-lg font-bold text-sm tracking-[0.2em] uppercase transition-all duration-200 flex items-center justify-center gap-2 disabled:opacity-40"
          style={{
            background: loading ? 'rgba(0,255,65,0.1)' : 'rgba(0,255,65,0.15)',
            border: '1px solid rgba(0,255,65,0.4)',
            color: '#00ff41',
            boxShadow: loading ? 'none' : '0 0 30px rgba(0,255,65,0.1)',
          }}
        >
          {loading ? (
            <>
              <Loader2 size={16} className="animate-spin" />
              Initiating Audit...
            </>
          ) : (
            'Initiate Security Audit'
          )}
        </button>
      </div>
    </div>
  )
}

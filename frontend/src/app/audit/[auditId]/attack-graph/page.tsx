'use client'
import { use, useMemo } from 'react'
import { ReactFlow, Background, MiniMap, Controls, NodeTypes } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { useAuditStore } from '@/store/audit-store'
import { useAuditStream } from '@/hooks/useAuditStream'
import { ResourceNode } from '@/components/attack-graph/ResourceNode'
import { Header } from '@/components/layout/Header'
import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'

const nodeTypes: NodeTypes = { resource: ResourceNode as NodeTypes['resource'] }

export default function AttackGraphPage({ params }: { params: Promise<{ auditId: string }> }) {
  const { auditId } = use(params)
  const attackPaths = useAuditStore((s) => s.attackPaths)
  useAuditStream(auditId)

  const { nodes, edges } = useMemo(() => {
    const nodeMap = new Map<
      string,
      {
        id: string
        data: { label: string; is_target?: boolean }
        position: { x: number; y: number }
        type: string
      }
    >()
    const edgeList: {
      id: string
      source: string
      target: string
      label?: string
      style?: Record<string, unknown>
      animated: boolean
    }[] = []

    attackPaths.forEach((path, pi) => {
      path.path.forEach((step, si) => {
        if (!nodeMap.has(step.from)) {
          nodeMap.set(step.from, {
            id: step.from,
            data: { label: step.from },
            position: { x: si * 220, y: pi * 120 },
            type: 'resource',
          })
        }
        if (!nodeMap.has(step.to)) {
          nodeMap.set(step.to, {
            id: step.to,
            data: { label: step.to, is_target: step.to === path.target },
            position: { x: (si + 1) * 220, y: pi * 120 },
            type: 'resource',
          })
        }
        edgeList.push({
          id: `${pi}-${si}`,
          source: step.from,
          target: step.to,
          label: step.via,
          animated: true,
          style: { stroke: '#ff0040', strokeWidth: 2 },
        })
      })
    })

    return { nodes: Array.from(nodeMap.values()), edges: edgeList }
  }, [attackPaths])

  return (
    <div className="h-screen flex flex-col" style={{ background: '#0a0a0f' }}>
      <Header auditId={auditId} />
      <div
        className="flex items-center gap-3 px-4 py-2"
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
          Attack Graph
        </span>
        <span className="text-xs text-slate-600 ml-auto">
          {attackPaths.length} paths · {nodes.length} nodes
        </span>
      </div>
      <div className="flex-1">
        {attackPaths.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-600">
            <div className="text-4xl mb-4">🕸️</div>
            <div>No attack paths discovered yet</div>
          </div>
        ) : (
          <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView>
            <Background color="#1a1a24" gap={24} />
            <MiniMap nodeColor={() => '#2a2a3a'} />
            <Controls />
          </ReactFlow>
        )}
      </div>
    </div>
  )
}

'use client'
import { useMemo } from 'react'
import { ReactFlow, ReactFlowProvider, Background, NodeTypes } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { useAuditStore } from '@/store/audit-store'
import { ResourceNode } from './ResourceNode'
import Link from 'next/link'
import { Maximize2 } from 'lucide-react'

const nodeTypes: NodeTypes = { resource: ResourceNode as NodeTypes['resource'] }

export function AttackGraphPreview({ auditId }: { auditId: string }) {
  const attackPaths = useAuditStore((s) => s.attackPaths)

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
            position: { x: si * 180, y: pi * 100 },
            type: 'resource',
          })
        }
        if (!nodeMap.has(step.to)) {
          nodeMap.set(step.to, {
            id: step.to,
            data: { label: step.to, is_target: step.to === path.target },
            position: { x: (si + 1) * 180, y: pi * 100 },
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

  if (attackPaths.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-slate-600">
        <div className="text-2xl mb-2">🕸️</div>
        <div className="text-sm">Attack graph builds during investigation</div>
      </div>
    )
  }

  return (
    <div className="relative">
      <div
        style={{ height: 300, borderRadius: 8, overflow: 'hidden', border: '1px solid #2a2a3a' }}
      >
        <ReactFlowProvider>
          <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView nodesDraggable={false}>
            <Background color="#2a2a3a" gap={20} />
          </ReactFlow>
        </ReactFlowProvider>
      </div>
      <Link
        href={`/audit/${auditId}/attack-graph`}
        className="absolute top-2 right-2 flex items-center gap-1 px-2 py-1 rounded text-xs font-terminal transition-colors"
        style={{
          background: 'rgba(0,212,255,0.1)',
          border: '1px solid rgba(0,212,255,0.3)',
          color: '#00d4ff',
        }}
      >
        <Maximize2 size={10} />
        Full Screen
      </Link>
    </div>
  )
}

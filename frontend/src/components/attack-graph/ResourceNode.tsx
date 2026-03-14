'use client'
import { Handle, Position } from '@xyflow/react'

const RESOURCE_COLORS: Record<string, string> = {
  ec2: '#3b82f6',
  rds: '#8b5cf6',
  iam: '#f59e0b',
  s3: '#22c55e',
  lambda: '#f97316',
  secrets: '#ef4444',
  kms: '#a855f7',
  sns: '#06b6d4',
  cloudwatch: '#06b6d4',
  default: '#64748b',
}

function getColor(id: string): string {
  const lower = id.toLowerCase()
  for (const [key, color] of Object.entries(RESOURCE_COLORS)) {
    if (lower.includes(key)) return color
  }
  return RESOURCE_COLORS.default
}

interface ResourceNodeData {
  label: string
  vuln_count?: number
  is_target?: boolean
}

export function ResourceNode({ data }: { data: ResourceNodeData }) {
  const color = getColor(data.label)

  return (
    <div
      className="px-4 py-3 rounded-lg min-w-[120px] text-center relative"
      style={{
        background: `${color}18`,
        border: `1px solid ${color}66`,
        boxShadow: data.is_target ? `0 0 20px ${color}44` : 'none',
      }}
    >
      <Handle
        type="target"
        position={Position.Left}
        style={{ background: color, border: 'none', width: 8, height: 8 }}
      />
      <div className="text-xs font-terminal font-bold" style={{ color }}>
        {data.label}
      </div>
      {data.vuln_count !== undefined && data.vuln_count > 0 && (
        <div
          className="absolute -top-2 -right-2 w-5 h-5 rounded-full flex items-center justify-center font-bold"
          style={{ background: '#ff0040', color: '#fff', fontSize: '10px' }}
        >
          {data.vuln_count}
        </div>
      )}
      <Handle
        type="source"
        position={Position.Right}
        style={{ background: color, border: 'none', width: 8, height: 8 }}
      />
    </div>
  )
}

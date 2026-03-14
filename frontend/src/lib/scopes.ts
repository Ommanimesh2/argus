import type { ScopeDefinition } from './types'

export const SCOPE_DEFINITIONS: Record<string, ScopeDefinition> = {
  iam: {
    label: 'IAM',
    description: 'Roles, policies, privilege escalation chains',
    budget_weight: 4,
    vuln_count: 4,
  },
  network: {
    label: 'Network',
    description: 'Security groups, NACLs, route tables',
    budget_weight: 4,
    vuln_count: 5,
  },
  compute: {
    label: 'Compute',
    description: 'EC2 instances, user data, metadata service',
    budget_weight: 3,
    vuln_count: 5,
  },
  monitoring: {
    label: 'Monitoring',
    description: 'CloudWatch alarms, CloudTrail, Flow Logs',
    budget_weight: 3,
    vuln_count: 4,
  },
  data: {
    label: 'Data',
    description: 'RDS, S3 buckets, KMS, Secrets Manager',
    budget_weight: 3,
    vuln_count: 4,
  },
  ssh: {
    label: 'SSH',
    description: 'Jump box access, OS-level process inspection',
    budget_weight: 5,
    vuln_count: 3,
  },
}

export const SCOPE_ICONS: Record<string, string> = {
  iam: '🔑',
  network: '🌐',
  compute: '💻',
  monitoring: '📊',
  data: '🗄️',
  ssh: '🔒',
}

export function calculateBudget(scopes: string[]): number {
  return scopes.reduce((acc, s) => acc + (SCOPE_DEFINITIONS[s]?.budget_weight ?? 0), 0) * 2
}

export function calculateVulnCount(scopes: string[]): number {
  const all = new Set<number>()
  scopes.forEach((s) => {
    const def = SCOPE_DEFINITIONS[s]
    if (def) all.add(def.vuln_count)
  })
  return scopes.reduce((acc, s) => acc + (SCOPE_DEFINITIONS[s]?.vuln_count ?? 0), 0)
}

export function estimateMinutes(scopes: string[]): number {
  const budget = calculateBudget(scopes)
  return Math.max(2, Math.round(budget * 0.25))
}

export const AWS_REGIONS = [
  'us-east-1',
  'us-east-2',
  'us-west-1',
  'us-west-2',
  'eu-west-1',
  'eu-west-2',
  'eu-central-1',
  'ap-southeast-1',
  'ap-southeast-2',
  'ap-northeast-1',
  'sa-east-1',
]

# ARGUS — Autonomous Security Auditor

> Autonomous Reasoning & Graph-based Understanding System
> A hypothesis-driven AI agent for AWS infrastructure security.

---

## What Is This

ARGUS is a LangGraph-based AI agent that autonomously audits AWS infrastructure. It self-discovers all in-scope resources, forms security hypotheses, investigates them through a reasoning loop, builds attack graphs correlating findings across layers, and produces a full security report with reasoning chains.

It is not a scanner. It is an agent that thinks.

---

## Architecture

```
reconnaissance_node        ← auto-discovers all resources via AWS tag: AuditDemo=true
        │
        ▼
initial_scan_node          ← 3 cross-layer checks
        │
        ▼
hypothesis_generation_node ← generates security hypotheses
        │
        ▼
deep_investigation_node    ← tests each hypothesis via SSH + AWS API calls
        │
        ├── more to investigate? ── back to hypothesis_generation_node
        │
        ▼
attack_graph_node          ← DFS path finder across all findings
        │
        ▼
reasoning_node             ← deep chains on CRITICAL/HIGH findings
        │
        ▼
report_generation_node     ← full report + executive summary
```

### Model Routing

| Node | Model |
|------|-------|
| initial_scan | claude-sonnet-4-6 |
| hypothesis_generation | claude-sonnet-4-6 |
| deep_investigation | claude-sonnet-4-6 |
| attack_graph | claude-sonnet-4-6 |
| reasoning | claude-opus-4-6 |
| report_generation | claude-opus-4-6 |

---

## Demo Infrastructure

A purpose-built AWS environment with **20 deliberately embedded vulnerabilities** across 5 layers. Designed to test multi-step reasoning — not just surface-level scanning.

### Topology

```
Public Subnet (10.0.1.0/24)
  EC2-Public [10.0.1.100]
    Role: ec2-public-role
    Can assume: ec2-private-role   ← privilege escalation chain starts here

Private Subnet A (10.0.10.0/24)
  EC2-Private [10.0.10.100]
    Role: ec2-private-role
    Can assume: agent-runner-role
  RDS [10.0.10.200]
    Accepts direct connections from EC2-Public

Private Subnet B (10.0.11.0/24)
  Lambda: agent-runner
    Role: agent-runner-role
    Has: secretsmanager:GetSecretValue

Monitoring (intentionally broken):
  CloudWatch Alarm → deleted SNS topic
  CloudTrail: logging disabled
  VPC Flow Logs → invalid S3 path
```

---

## Audit Scopes

```bash
# IAM chain + IMDSv1 + monitoring gaps
POST /api/audit/start  { "scopes": ["iam", "compute", "monitoring"] }

# All 20 vulnerabilities across all layers
POST /api/audit/start  { "scopes": ["all"] }
```

| Scope | What It Covers |
|-------|----------------|
| `iam` | Role chains, trust policies, Lambda execution roles |
| `network` | Security groups, NACLs, route tables, VPC topology |
| `compute` | EC2 IMDSv1, AMI age, instance profiles, user-data |
| `monitoring` | CloudWatch alarms, CloudTrail, VPC Flow Logs, SNS |
| `data` | RDS encryption, S3 policies, KMS key rotation |
| `ssh` | Internal SSH: ports, crontabs, app config, IMDS from inside |

---

## Quick Start

```bash
export AWS_PROFILE=audit-demo
export AUDIT_SSH_KEY=~/.ssh/audit_key.pem
export ANTHROPIC_API_KEY=sk-ant-...

# Start backend
python -m backend.main

# Start frontend
cd frontend && npm run dev
# Open http://localhost:3000

# Trigger an audit
curl -X POST localhost:8000/api/audit/start \
  -d '{"scopes": ["iam", "compute", "monitoring"]}'
```

### Deploy Infrastructure

```bash
cd terraform/
terraform init
terraform apply
```

---

## Vulnerability Coverage

### IAM
| ID | Vulnerability |
|----|--------------|
| HA-004 🔴 | 3-hop IAM role chain: EC2-Public → EC2-Private → Agent-Runner → Secrets Manager |
| HA-005 🟠 | RDS IAM authentication disabled — password-only auth |
| HA-016 🟠 | Lambda attached to wrong execution role (silent permission failure) |
| HA-020 🟡 | KMS key rotation disabled |

### Network
| ID | Vulnerability |
|----|--------------|
| HA-001 🔴 | Direct DB access from public EC2 — bypasses application layer |
| HA-009 🟡 | NACL deny rule unreachable due to route table evaluation order |
| HA-010 🟢 | Overlapping security group rules |
| HA-011 🟡 | NAT Gateway bypass via VPN route (longest-prefix-match) |
| HA-012 🟡 | Unrestricted DNS egress — DNS exfiltration possible |
| HA-002 🟠 | Backend service bound to 0.0.0.0 instead of 127.0.0.1 |

### Monitoring
| ID | Vulnerability |
|----|--------------|
| HA-006 🟠 | CloudWatch alarm targets deleted SNS topic — alerts never fire |
| HA-007 🟡 | VPC Flow Logs active but delivering to invalid S3 path |
| HA-008 🔴 | CloudTrail disabled + S3 bucket policy blocks re-enablement |
| HA-019 🟢 | Manual SNS subscription invisible to Terraform |

### Compute
| ID | Vulnerability |
|----|--------------|
| HA-014/015 🟠 | IMDSv1 enabled — credentials extractable via SSRF |
| HA-017 🔴 | Cron job opens SSH from 0.0.0.0/0 for 5 min every hour |
| HA-018 🟡 | Configuration drift — manual modifications not in Terraform state |

### Data
| ID | Vulnerability |
|----|--------------|
| HA-003 🟠 | RDS storage unencrypted — backups stored in plaintext |
| HA-013 🟠 | S3 bucket has conditional public policy via object tag |

---

## Primary Attack Chain

```
Internet → EC2-Public (SSRF + IMDSv1)
  → extract ec2-public-role credentials
  → assume ec2-private-role
  → assume agent-runner-role
  → secretsmanager:GetSecretValue (all API keys exfiltrated)
  → direct RDS connection via stolen DB credentials
  → entire incident undetected (CloudTrail off, Flow Logs broken, Alarm broken)
```

---

## Repository Structure

```
argus/
├── README.md
├── agents/                  ← LangGraph nodes and agent config
├── frontend/                ← Next.js dashboard (SSE streaming)
├── terraform/               ← Demo infrastructure with 20 embedded vulns
└── phases/                  ← Design docs per build phase
```

---

*ARGUS — Built to find what scanners miss.*

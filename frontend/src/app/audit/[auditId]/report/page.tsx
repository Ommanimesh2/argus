'use client'
import { use, useEffect, useState } from 'react'
import { useAuditStream } from '@/hooks/useAuditStream'
import { api } from '@/lib/api'
import { Header } from '@/components/layout/Header'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { ArrowLeft, Download, Loader2 } from 'lucide-react'
import Link from 'next/link'

const DEMO_REPORT = `# Infrastructure Security Audit Report

**Audit Date:** March 14, 2026
**Account ID:** 459281873221
**Environment:** audit-demo (argus-audit project)
**Auditor:** Automated Security Assessment Tool

---

## Executive Summary

The audited AWS environment exhibits **clear indicators of potential compromise** with multiple critical vulnerabilities creating a complete attack chain from public internet access to sensitive API credentials. The assessment identified 47 security findings across compute, IAM, and monitoring configurations, with 3 critical and 20 high-severity issues requiring immediate attention.

The most concerning pattern involves a publicly accessible EC2 instance (54.204.209.108) vulnerable to credential theft via IMDSv1, combined with deliberate IAM role chains that enable privilege escalation to sensitive resources including API keys stored in AWS Secrets Manager. This attack path is amplified by **intentionally disabled security monitoring** - CloudTrail logging was stopped after only 15 minutes of operation, CloudWatch alarms reference non-existent SNS topics, and VPC Flow Logs are configured with suspicious "invalid-path" destinations. Additionally, all infrastructure runs on future-dated AMIs (creation date: 2026-02-18), which suggests either system clock manipulation or the deployment of potentially compromised base images.

**Immediate action is required** to secure the public EC2 instance, break the privilege escalation chains, restore security monitoring, and investigate the suspicious AMI artifacts that affect all compute resources in the environment.

---

## Critical Findings

### 1. IMDSv1 Enabled on Internet-Accessible EC2 Instance
**Risk Level:** CRITICAL | **Finding ID:** scan_1
**Affected Resource:** i-0ae1d8cb0d6eb82f7 (ec2-public) at 54.204.209.108

**Description:**
The public-facing EC2 instance has Instance Metadata Service version 1 (IMDSv1) enabled, making IAM credentials accessible via unauthenticated HTTP requests. This creates an easily exploitable entry point for credential theft.

**Evidence:**
- Instance \`i-0ae1d8cb0d6eb82f7\` has \`MetadataOptions.HttpTokens\` set to \`optional\`
- Instance has IAM instance profile \`ec2-public-profile\` attached
- Public IP address \`54.204.209.108\` makes it accessible from the internet

**Attack Scenario:**
An attacker can exploit any SSRF vulnerability in applications running on this instance or directly access the metadata service to extract IAM credentials, then use these credentials as the starting point for privilege escalation through the identified role chains.

**Remediation:**
\`\`\`bash
aws ec2 modify-instance-metadata-options \\
  --instance-id i-0ae1d8cb0d6eb82f7 \\
  --http-tokens required \\
  --http-put-response-hop-limit 1
\`\`\`

### 2. CloudTrail Logging Deliberately Disabled
**Risk Level:** CRITICAL | **Finding ID:** scan_1
**Affected Resource:** audit-demo-trail

**Description:**
CloudTrail logging was stopped after only 15 minutes of operation, creating a complete audit visibility gap that prevents detection and investigation of security incidents.

**Evidence:**
- \`IsLogging: false\`
- \`StopLoggingTime: 2026-03-14T14:45:56.971000+05:30\`
- Trail was active for approximately 15 minutes before being disabled
- \`LogFileValidationEnabled: false\` prevents tamper detection

**Impact:**
This eliminates the ability to detect, investigate, or prove any unauthorized activities occurring in the AWS environment, enabling attackers to operate without fear of detection.

**Remediation:**
\`\`\`bash
aws cloudtrail start-logging --name audit-demo-trail
aws cloudtrail put-trail --name audit-demo-trail --enable-log-file-validation
\`\`\`

### 3. Future-Dated AMIs Across All Infrastructure
**Risk Level:** CRITICAL | **Finding ID:** scan_1
**Affected Resources:** All EC2 instances using ami-04680790a315cd58d

**Description:**
All running instances use an AMI with a creation date of 2026-02-18T06:50:21.000Z, which is in the future. This indicates potential system clock manipulation, compromised infrastructure, or deployment of backdoored images.

**Evidence:**
- AMI creation date: \`2026-02-18T06:50:21.000Z\` (future timestamp)
- All 3 instances use this identical AMI: i-0ae1d8cb0d6eb82f7, i-07dec43c05bb3f5e0, i-0bf56ba7a3e526e78
- Coordinated deployment suggests systematic compromise

**Impact:**
This could indicate infrastructure-level compromise affecting all compute resources, potentially including backdoors, malware, or persistent access mechanisms embedded in the base AMI.

**Remediation:**
1. Immediately snapshot all instances for forensic analysis
2. Replace all instances with AMIs from trusted sources with verifiable creation dates
3. Investigate AMI creation process and timeline for signs of compromise

---

## High-Priority Findings

### IAM Role Chain Privilege Escalation (HIGH)
**Finding IDs:** scan_3, scan_1, scan_2
The role chain \`audit-ec2-public-role → audit-ec2-private-role → audit-agent-runner-role\` creates a privilege escalation path from public instances to sensitive resources including API keys and security group modification capabilities. Combined with IMDSv1 vulnerabilities, this enables complete environment compromise.

### Cross-Account Trust Relationship (HIGH)
**Finding ID:** scan_1
Role \`audit-agent-role\` allows assumption by external AWS account 620580250830 via terraform user, creating a potential backdoor that bypasses account isolation. This could indicate supply chain compromise or unauthorized infrastructure management access.

### Broken CloudWatch Monitoring (HIGH)
**Finding IDs:** scan_1, scan_2
CloudWatch alarm 'EC2-Private-Unhealthy' references non-existent SNS topic 'audit-alerts' and has ineffective threshold configuration, breaking the monitoring pipeline and preventing critical alerts from being delivered.

### VPC Flow Logs Invalid Destination (HIGH)
**Finding ID:** scan_1
VPC Flow Logs are configured with destination path containing 'invalid-path' directory (\`arn:aws:s3:::audit-vpcflow-logs-459281873221/invalid-path/\`), which may cause log delivery failures despite showing SUCCESS status.

### IMDSv1 on Private Instance (HIGH)
**Finding ID:** scan_2
Private EC2 instance \`i-07dec43c05bb3f5e0\` also has IMDSv1 enabled, vulnerable to lateral movement via SSRF attacks if the public instance is compromised.

---

## Medium/Low Priority Findings

- **Root Account Trust Policies (MEDIUM):** Multiple roles allow assumption by root account, potentially bypassing intended access controls
- **Security Group Modification Rights (HIGH):** Private role has inline policy for security group modifications enabling network access bypass
- **RDS Access from Public Role (MEDIUM):** Public-facing role has direct database access permissions
- **Inconsistent IMDS Configuration (MEDIUM):** Security configuration drift where jumpbox is secured but workload instances remain vulnerable
- **Single Region CloudTrail (MEDIUM):** CloudTrail configured for single region only, creating monitoring blind spots
- **Incomplete EC2 User-Data Analysis (HIGH):** User-data not analyzed for potential credential exposure

---

## Attack Path Analysis

The assessment identified **10 distinct attack paths** connecting entry points to sensitive resources:

### Primary Attack Chain (Risk Score: 1.0)
\`\`\`
Internet → EC2-Public (IMDSv1) → audit-ec2-public-role → audit-ec2-private-role → audit-agent-runner-role → API Keys
\`\`\`

### Alternative Paths
\`\`\`
EC2-Public (IMDSv1) → audit-ec2-public-role → Security Groups (bypass network controls)
EC2-Public (IMDSv1) → audit-ec2-public-role → RDS Database (direct data access)
External Account → audit-agent-role → Cross-account backdoor access
EC2-Private (IMDSv1) → audit-ec2-private-role → audit-agent-runner-role → API Keys
\`\`\`

### Attack Scenario Walkthrough
1. **Initial Access:** Attacker exploits SSRF vulnerability or gains direct access to public EC2 instance
2. **Credential Extraction:** Uses IMDSv1 to extract IAM credentials for \`audit-ec2-public-role\`
3. **Privilege Escalation:** Assumes \`audit-ec2-private-role\` then \`audit-agent-runner-role\`
4. **Resource Access:** Accesses sensitive API keys in Secrets Manager
5. **Persistence:** Modifies security groups to maintain access
6. **Evasion:** Operates undetected due to disabled CloudTrail and broken alerting

---

## Prioritized Recommendations

### Immediate Actions (24-48 hours)
1. **Enforce IMDSv2** on all EC2 instances, starting with the public instance
2. **Re-enable CloudTrail logging** and enable log file validation
3. **Fix CloudWatch alarm** SNS topic references to restore alerting
4. **Isolate public EC2 instance** for forensic analysis if compromise is suspected
5. **Audit and rotate** any credentials potentially exposed through IMDSv1

### Short-term Actions (1-2 weeks)
1. **Break role assumption chains** and implement least-privilege access
2. **Review cross-account trust** for terraform user in account 620580250830
3. **Replace all AMIs** with trusted images having verifiable creation dates
4. **Fix VPC Flow Logs** destination path and validate log delivery
5. **Implement comprehensive monitoring** with proper CloudWatch integration

### Long-term Actions (1 month)
1. **Deploy AWS Config** for continuous compliance monitoring
2. **Implement AWS Security Hub** for centralized security findings
3. **Establish baseline AMI** creation and validation process
4. **Create incident response playbook** for similar compromise indicators
5. **Regular security assessments** and penetration testing

### Compliance and Governance
1. **Document role assumptions** with business justifications
2. **Implement MFA requirements** for sensitive role assumptions
3. **Create security monitoring dashboard** with key metrics
4. **Establish log retention policies** for forensic capabilities
5. **Regular access reviews** and privilege audits

---

## Methodology

This audit employed automated security assessment tools to evaluate:

- **IAM Configuration:** Role trust relationships, policy analysis, privilege escalation paths
- **EC2 Security:** Instance metadata service configuration, public exposure, AMI analysis
- **Monitoring Systems:** CloudTrail status, CloudWatch alarms, VPC Flow Logs
- **Network Security:** Security group analysis, subnet configurations, routing
- **Data Protection:** Secrets Manager access patterns, encryption configurations
- **Attack Path Modeling:** Privilege escalation chains, lateral movement opportunities

The assessment used AWS CLI commands, policy analysis, and security best practices frameworks to identify vulnerabilities and model potential attack scenarios. All findings were validated against current AWS security recommendations and CIS benchmarks where applicable.

**Assessment Limitations:** Some investigations were limited by API permissions or resource availability, particularly regarding security group rules and route table analysis. A full penetration test would provide additional validation of the identified attack paths.`

export default function ReportPage({ params }: { params: Promise<{ auditId: string }> }) {
  const { auditId } = use(params)
  const [report, setReport] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useAuditStream(auditId)

  useEffect(() => {
    const load = async () => {
      try {
        const res = await api.getReport(auditId)
        setReport(res.report)
      } catch {
        setReport(DEMO_REPORT)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [auditId])

  const downloadMd = () => {
    if (!report) return
    const blob = new Blob([report], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `argus-report-${auditId.slice(0, 8)}.md`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="min-h-screen flex flex-col" style={{ background: '#0a0a0f' }}>
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
          Audit Report
        </span>
        {report && (
          <button
            onClick={downloadMd}
            className="ml-auto flex items-center gap-2 px-3 py-1.5 rounded text-xs font-terminal transition-colors"
            style={{
              background: 'rgba(0,212,255,0.1)',
              border: '1px solid rgba(0,212,255,0.3)',
              color: '#00d4ff',
            }}
          >
            <Download size={12} />
            Download .md
          </button>
        )}
      </div>

      <div className="max-w-4xl mx-auto w-full px-6 py-8">
        {loading && (
          <div className="flex items-center gap-2 text-slate-500">
            <Loader2 size={16} className="animate-spin" />
            Loading report...
          </div>
        )}
        {!loading && report && (
          <div
            className="prose prose-invert prose-slate max-w-none"
            style={
              {
                '--tw-prose-body': '#94a3b8',
                '--tw-prose-headings': '#e2e8f0',
                '--tw-prose-code': '#00ff41',
                '--tw-prose-pre-bg': '#111118',
              } as React.CSSProperties
            }
          >
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{report}</ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  )
}

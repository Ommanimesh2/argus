"""
ARGUS Agents — scope definitions and V3 discovery checks.
Check IDs in SCOPE_DEFINITIONS must exist in V3_DISCOVERY_CHECKS.
No shell piping: each command is a single AWS CLI invocation.
"""
from __future__ import annotations

# Scope definitions: budget_weight and list of check IDs
SCOPE_DEFINITIONS = {
    "iam": {
        "budget_weight": 4,
        "checks": ["iam_trust_chain", "iam_policy_analysis"],
    },
    "network": {
        "budget_weight": 4,
        "checks": ["sg_cross_reference", "nacl_route_analysis"],
    },
    "compute": {
        "budget_weight": 3,
        "checks": ["imds_check", "ami_age_check", "userdata_analysis"],
    },
    "monitoring": {
        "budget_weight": 3,
        "checks": ["monitoring_pipeline", "cloudtrail_check", "flowlogs_check"],
    },
    "data": {
        "budget_weight": 3,
        "checks": ["rds_config", "s3_policy_check", "kms_rotation_check", "secrets_check"],
    },
    "lambda": {
        "budget_weight": 2,
        "checks": ["lambda_role_check"],
    },
    "drift": {
        "budget_weight": 2,
        "checks": ["tag_drift_check", "unmanaged_resources_check"],
    },
}

ALL_SCOPES = list(SCOPE_DEFINITIONS.keys())


def resolve_scopes(requested: list[str] | None) -> list[str]:
    """Return requested scopes if valid; else ALL_SCOPES."""
    if not requested or requested == ["all"]:
        return ALL_SCOPES
    out = [s for s in requested if s in SCOPE_DEFINITIONS]
    return out if out else ALL_SCOPES


def calculate_budget(scopes: list[str], mode: str, override: int | None = None) -> int:
    """Budget from scope weights; multiplier for demo vs dev; or use override."""
    if override is not None:
        return override
    base = sum(SCOPE_DEFINITIONS[s]["budget_weight"] for s in scopes)
    multiplier = 1 if mode == "demo" else 2
    return base * multiplier


# V3 Discovery Checks — single AWS CLI commands only (no piping)
V3_DISCOVERY_CHECKS: dict[str, dict] = {
    "sg_cross_reference": {
        "name": "Security Group Cross-Reference Analysis",
        "type": "network_segmentation",
        "scope": "network",
        "commands": [
            "aws ec2 describe-security-groups --output json",
        ],
        "analysis_prompt": (
            "Analyze ALL security groups and their rules. For each SG, identify: "
            "which resources are attached; egress rules (e.g. protocol -1); "
            "cross-SG ingress; SGs with no inbound rules."
        ),
        "detects": ["HA-001", "HA-010", "HA-012"],
    },
    "nacl_route_analysis": {
        "name": "NACL + Route Table Conflict Analysis",
        "type": "network_segmentation",
        "scope": "network",
        "commands": [
            "aws ec2 describe-network-acls --output json",
            "aws ec2 describe-route-tables --output json",
            "aws ec2 describe-vpn-gateways --output json",
        ],
        "analysis_prompt": (
            "Cross-reference NACL rules against route tables. Find NACL DENY rules "
            "that may be bypassed by routes; check NAT/VPN overrides."
        ),
        "detects": ["HA-009", "HA-011"],
    },
    "iam_trust_chain": {
        "name": "IAM Trust Policy Chain Analysis",
        "type": "iam_privilege",
        "scope": "iam",
        "commands": [
            "aws iam list-roles --output json",
        ],
        "analysis_prompt": (
            "Map IAM trust chain from AssumeRolePolicyDocument. Identify who can "
            "assume each role; build privilege escalation chains."
        ),
        "detects": ["HA-004"],
    },
    "iam_policy_analysis": {
        "name": "IAM Inline Policy Deep Analysis",
        "type": "iam_privilege",
        "scope": "iam",
        "commands": [
            "aws iam list-role-policies --role-name audit-ec2-public-role --output json",
            "aws iam list-role-policies --role-name audit-ec2-private-role --output json",
            "aws iam list-role-policies --role-name audit-agent-runner-role --output json",
        ],
        "analysis_prompt": (
            "Analyze inline policies for excessive permissions: sts:AssumeRole, "
            "rds-db:connect, ec2:AuthorizeSecurityGroupIngress, secretsmanager:GetSecretValue."
        ),
        "detects": ["HA-001", "HA-004", "HA-017"],
    },
    "imds_check": {
        "name": "EC2 Instance Metadata Service (IMDS) Configuration",
        "type": "compute_config",
        "scope": "compute",
        "commands": [
            "aws ec2 describe-instances --query \"Reservations[].Instances[].{Id:InstanceId,Name:Tags[?Key=='Name'].Value|[0],MetadataOptions:MetadataOptions}\" --output json",
        ],
        "analysis_prompt": (
            "Check MetadataOptions.HttpTokens: 'optional' = IMDSv1 enabled (vulnerable); "
            "'required' = IMDSv2 only (secure)."
        ),
        "detects": ["HA-014"],
    },
    "ami_age_check": {
        "name": "AMI Staleness Check",
        "type": "compute_config",
        "scope": "compute",
        "commands": [
            "aws ec2 describe-instances --query \"Reservations[].Instances[].{Id:InstanceId,Name:Tags[?Key=='Name'].Value|[0],ImageId:ImageId}\" --output json",
            "aws ec2 describe-images --owners 099720109477 --filters \"Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*\" \"Name=state,Values=available\" --query \"sort_by(Images, &CreationDate)[-1].{ImageId:ImageId,CreationDate:CreationDate}\" --output json",
        ],
        "analysis_prompt": "Compare instance AMIs to latest available; flag stale images.",
        "detects": ["HA-015"],
    },
    "userdata_analysis": {
        "name": "EC2 User-Data Security Analysis",
        "type": "compute_config",
        "scope": "compute",
        "commands": [
            "aws ec2 describe-instances --query \"Reservations[].Instances[].{Id:InstanceId,Name:Tags[?Key=='Name'].Value|[0],State:State.Name}\" --output json",
        ],
        "analysis_prompt": (
            "Identify running instances. Deep investigation may run "
            "describe-instance-attribute --attribute userData per instance."
        ),
        "detects": ["HA-002", "HA-017"],
        "triggers_investigation": True,
    },
    "monitoring_pipeline": {
        "name": "CloudWatch + SNS Monitoring Pipeline Validation",
        "type": "monitoring_validation",
        "scope": "monitoring",
        "commands": [
            "aws cloudwatch describe-alarms --output json",
            "aws sns list-topics --output json",
        ],
        "analysis_prompt": (
            "Validate alarms' SNS targets exist; check for broken or unreferenced topics."
        ),
        "detects": ["HA-006", "HA-019"],
    },
    "cloudtrail_check": {
        "name": "CloudTrail Logging Status",
        "type": "monitoring_validation",
        "scope": "monitoring",
        "commands": [
            "aws cloudtrail describe-trails --output json",
            "aws cloudtrail get-trail-status --name audit-demo-trail --output json",
        ],
        "analysis_prompt": "Check IsLogging and LatestDeliveryError; flag if trail not logging.",
        "detects": ["HA-008"],
        "triggers_investigation": True,
    },
    "flowlogs_check": {
        "name": "VPC Flow Logs Destination Validation",
        "type": "monitoring_validation",
        "scope": "monitoring",
        "commands": [
            "aws ec2 describe-flow-logs --output json",
        ],
        "analysis_prompt": "Validate LogDestination and FlowLogStatus; flag invalid paths.",
        "detects": ["HA-007"],
    },
    "rds_config": {
        "name": "RDS Security Configuration",
        "type": "data_security",
        "scope": "data",
        "commands": [
            "aws rds describe-db-instances --output json",
        ],
        "analysis_prompt": (
            "Check StorageEncrypted, IAMDatabaseAuthenticationEnabled, PubliclyAccessible, VpcSecurityGroups."
        ),
        "detects": ["HA-003", "HA-005"],
    },
    "s3_policy_check": {
        "name": "S3 Bucket Policy & Public Access Analysis",
        "type": "data_security",
        "scope": "data",
        "commands": [
            "aws s3api list-buckets --output json",
        ],
        "analysis_prompt": (
            "List buckets; deep investigation may run get-bucket-policy and get-public-access-block."
        ),
        "detects": ["HA-013", "HA-008"],
        "triggers_investigation": True,
    },
    "kms_rotation_check": {
        "name": "KMS Key Rotation Status",
        "type": "data_security",
        "scope": "data",
        "commands": [
            "aws kms list-keys --output json",
            "aws kms list-aliases --output json",
        ],
        "analysis_prompt": "List keys; deep investigation runs get-key-rotation-status per key.",
        "detects": ["HA-020"],
        "triggers_investigation": True,
    },
    "secrets_check": {
        "name": "Secrets Manager Configuration",
        "type": "data_security",
        "scope": "data",
        "commands": [
            "aws secretsmanager list-secrets --output json",
        ],
        "analysis_prompt": "List secrets; check rotation and who can access (cross-ref IAM).",
        "detects": ["HA-004"],
    },
    "lambda_role_check": {
        "name": "Lambda Function Role Assignment",
        "type": "lambda_config",
        "scope": "lambda",
        "commands": [
            "aws lambda list-functions --output json",
        ],
        "analysis_prompt": "Check Role ARN per function; flag wrong role (e.g. lambda-wrong-role).",
        "detects": ["HA-016"],
        "triggers_investigation": True,
    },
    "tag_drift_check": {
        "name": "Configuration Drift Detection via Tags",
        "type": "config_drift",
        "scope": "drift",
        "commands": [
            "aws ec2 describe-instances --query \"Reservations[].Instances[].{Id:InstanceId,Name:Tags[?Key=='Name'].Value|[0],Tags:Tags}\" --output json",
        ],
        "analysis_prompt": "Check ManagedBy=terraform, Environment=demo; flag unexpected tags.",
        "detects": ["HA-018"],
    },
    "unmanaged_resources_check": {
        "name": "Unmanaged Resource Detection",
        "type": "config_drift",
        "scope": "drift",
        "commands": [
            "aws sns list-topics --output json",
            "aws sns list-subscriptions --output json",
        ],
        "analysis_prompt": "Detect topics not managed by Terraform (e.g. audit-alerts only).",
        "detects": ["HA-019"],
    },
}


def get_active_checks(scopes: list[str]) -> dict[str, dict]:
    """Return check_id -> check for all checks in the given scopes."""
    active: dict[str, dict] = {}
    for scope in scopes:
        for check_id in SCOPE_DEFINITIONS.get(scope, {}).get("checks", []):
            if check_id in V3_DISCOVERY_CHECKS:
                active[check_id] = V3_DISCOVERY_CHECKS[check_id]
    return active

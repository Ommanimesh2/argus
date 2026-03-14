# =============================================================================
# ARGUS — IAM Roles, Policies, Instance Profiles
# =============================================================================

# -----------------------------------------------------------------------------
# EC2-Public Role — HA-004: Can assume EC2-Private (hop 1 of 3)
# -----------------------------------------------------------------------------

resource "aws_iam_role" "ec2_public_role" {
  name = "audit-ec2-public-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })

  tags = merge(local.common_tags, {
    Name = "ec2-public-role"
  })
}

# HA-004: EC2-Public can assume EC2-Private
resource "aws_iam_role_policy" "ec2_public_assume_private" {
  name = "ec2-public-assume-private"
  role = aws_iam_role.ec2_public_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "AssumePrivateRole"
      Effect   = "Allow"
      Action   = "sts:AssumeRole"
      Resource = aws_iam_role.ec2_private_role.arn
    }]
  })
}

# HA-001: EC2-Public can describe + connect to RDS
resource "aws_iam_role_policy" "ec2_public_rds_access" {
  name = "ec2-public-rds-access"
  role = aws_iam_role.ec2_public_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "RDSAccess"
      Effect   = "Allow"
      Action   = ["rds:DescribeDBInstances", "rds-db:connect"]
      Resource = "*"
    }]
  })
}

resource "aws_iam_instance_profile" "ec2_public_profile" {
  name = "ec2-public-profile"
  role = aws_iam_role.ec2_public_role.name
}

# -----------------------------------------------------------------------------
# EC2-Private Role — HA-004: Can assume Agent-Runner (hop 2 of 3)
# -----------------------------------------------------------------------------

resource "aws_iam_role" "ec2_private_role" {
  name = "audit-ec2-private-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      },
      {
        # HA-004: EC2-Public can assume this role
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.ec2_public_role.arn
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = merge(local.common_tags, {
    Name = "ec2-private-role"
  })
}

# HA-004: EC2-Private can assume Agent-Runner
resource "aws_iam_role_policy" "ec2_private_assume_agent" {
  name = "ec2-private-assume-agent"
  role = aws_iam_role.ec2_private_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "AssumeAgentRole"
      Effect   = "Allow"
      Action   = "sts:AssumeRole"
      Resource = aws_iam_role.agent_runner_role.arn
    }]
  })
}

# HA-017: EC2-Private needs permissions to modify its own SG (for cron job)
resource "aws_iam_role_policy" "ec2_private_sg_modify" {
  name = "ec2-private-sg-modify"
  role = aws_iam_role.ec2_private_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "ModifyOwnSG"
      Effect = "Allow"
      Action = [
        "ec2:AuthorizeSecurityGroupIngress",
        "ec2:RevokeSecurityGroupIngress"
      ]
      Resource = "*"
    }]
  })
}

resource "aws_iam_instance_profile" "ec2_private_profile" {
  name = "ec2-private-profile"
  role = aws_iam_role.ec2_private_role.name
}

# -----------------------------------------------------------------------------
# Agent-Runner Role — HA-004: End of escalation chain → Secrets Manager
# -----------------------------------------------------------------------------

resource "aws_iam_role" "agent_runner_role" {
  name = "audit-agent-runner-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      },
      {
        # HA-004: EC2-Private can assume this role
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.ec2_private_role.arn
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = merge(local.common_tags, {
    Name = "agent-runner-role"
  })
}

# HA-004: Agent-Runner can access secrets (end of escalation chain)
resource "aws_iam_role_policy" "agent_runner_secrets" {
  name = "agent-runner-secrets"
  role = aws_iam_role.agent_runner_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "GetSecrets"
      Effect   = "Allow"
      Action   = "secretsmanager:GetSecretValue"
      Resource = "*"
    }]
  })
}

# -----------------------------------------------------------------------------
# Jump Box Role — Minimal bastion role
# -----------------------------------------------------------------------------

resource "aws_iam_role" "jumpbox_role" {
  name = "audit-jumpbox-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })

  tags = merge(local.common_tags, {
    Name = "jumpbox-role"
  })
}

resource "aws_iam_instance_profile" "jumpbox_profile" {
  name = "jumpbox-profile"
  role = aws_iam_role.jumpbox_role.name
}

# -----------------------------------------------------------------------------
# Audit Agent Role — Read-only role for the ARGUS agent itself
# (from AGENT_ACCESS_MODEL.md)
# -----------------------------------------------------------------------------

resource "aws_iam_role" "audit_agent_role" {
  name = "audit-agent-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        AWS = data.aws_caller_identity.current.arn
      }
      Action = "sts:AssumeRole"
    }]
  })

  tags = merge(local.common_tags, {
    Name = "audit-agent-role"
  })
}

resource "aws_iam_role_policy" "audit_agent_read_only" {
  name = "audit-agent-read-only"
  role = aws_iam_role.audit_agent_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ReadOnlyAuditAccess"
        Effect = "Allow"
        Action = [
          "ec2:Describe*",
          "ec2:Get*",
          "ec2:List*",
          "iam:Get*",
          "iam:List*",
          "iam:Generate*",
          "rds:Describe*",
          "rds:List*",
          "s3:GetBucketPolicy",
          "s3:GetBucketAcl",
          "s3:GetBucketVersioning",
          "s3:GetBucketLogging",
          "s3:GetEncryptionConfiguration",
          "s3:ListAllMyBuckets",
          "s3:GetBucketLocation",
          "cloudwatch:Describe*",
          "cloudwatch:Get*",
          "cloudwatch:List*",
          "cloudtrail:Describe*",
          "cloudtrail:Get*",
          "cloudtrail:GetTrailStatus",
          "logs:Describe*",
          "logs:List*",
          "sns:List*",
          "sns:Get*",
          "kms:List*",
          "kms:Describe*",
          "kms:GetKeyRotationStatus",
          "kms:GetKeyPolicy",
          "config:Describe*",
          "config:Get*",
          "config:List*",
          "secretsmanager:List*",
          "sts:GetCallerIdentity"
        ]
        Resource = "*"
      },
      {
        Sid    = "ExplicitDenyAllWrite"
        Effect = "Deny"
        Action = [
          "ec2:Create*",
          "ec2:Delete*",
          "ec2:Modify*",
          "ec2:Authorize*",
          "ec2:Revoke*",
          "ec2:Run*",
          "ec2:Start*",
          "ec2:Stop*",
          "ec2:Terminate*",
          "iam:Create*",
          "iam:Delete*",
          "iam:Update*",
          "iam:Put*",
          "iam:Attach*",
          "iam:Detach*",
          "iam:Add*",
          "iam:Remove*",
          "iam:Pass*",
          "s3:Put*",
          "s3:Delete*",
          "s3:Create*",
          "rds:Create*",
          "rds:Delete*",
          "rds:Modify*",
          "cloudtrail:Update*",
          "cloudtrail:Delete*",
          "kms:Create*",
          "kms:Delete*",
          "kms:Disable*",
          "kms:Enable*",
          "kms:Put*",
          "secretsmanager:Create*",
          "secretsmanager:Delete*",
          "secretsmanager:Put*",
          "secretsmanager:Update*",
          "sts:AssumeRole"
        ]
        Resource = "*"
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# VPC Flow Logs Role
# -----------------------------------------------------------------------------

resource "aws_iam_role" "vpc_flow_logs_role" {
  name = "vpc-flow-logs-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "vpc-flow-logs.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })

  tags = merge(local.common_tags, {
    Name = "vpc-flow-logs-role"
  })
}

resource "aws_iam_role_policy" "vpc_flow_logs_policy" {
  name = "vpc-flow-logs-policy"
  role = aws_iam_role.vpc_flow_logs_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "s3:PutObject",
        "s3:GetObject"
      ]
      Resource = "${aws_s3_bucket.vpcflow_logs.arn}/*"
    }]
  })
}

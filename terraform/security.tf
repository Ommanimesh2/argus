# =============================================================================
# ARGUS — Security Groups & NACLs
# =============================================================================

# -----------------------------------------------------------------------------
# EC2 Public Security Group
# HA-012: Unrestricted DNS via -1 protocol egress
# -----------------------------------------------------------------------------

resource "aws_security_group" "ec2_public_sg" {
  name   = "audit-ec2-public-sg"
  vpc_id = aws_vpc.audit_vpc.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HA-012: All-traffic egress (includes unrestricted DNS)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "ec2-public-sg"
  })
}

# HA-001: Direct database access — egress from public EC2 to RDS port
resource "aws_security_group_rule" "ec2_public_to_rds" {
  type              = "egress"
  from_port         = 5432
  to_port           = 5432
  protocol          = "tcp"
  security_group_id = aws_security_group.ec2_public_sg.id
  cidr_blocks       = [var.private_subnet_1a_cidr]
  description       = "PostgreSQL to database (HIDDEN: direct access without app layer)"
}

# HA-010: Redundant egress rule for port 80 (overlaps with all-traffic egress)
resource "aws_security_group_rule" "ec2_public_egress_http" {
  type              = "egress"
  from_port         = 80
  to_port           = 80
  protocol          = "tcp"
  security_group_id = aws_security_group.ec2_public_sg.id
  cidr_blocks       = ["0.0.0.0/0"]
  description       = "HTTP egress (redundant with all-traffic rule)"
}

# HA-010: Redundant egress rule for port 443 (overlaps with all-traffic egress)
resource "aws_security_group_rule" "ec2_public_egress_https" {
  type              = "egress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  security_group_id = aws_security_group.ec2_public_sg.id
  cidr_blocks       = ["0.0.0.0/0"]
  description       = "HTTPS egress (redundant with all-traffic rule)"
}

# -----------------------------------------------------------------------------
# EC2 Private Security Group
# HA-017: Initially no inbound SSH — cron job adds it dynamically
# -----------------------------------------------------------------------------

resource "aws_security_group" "ec2_private_sg" {
  name   = "audit-ec2-private-sg"
  vpc_id = aws_vpc.audit_vpc.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "ec2-private-sg"
  })
}

# -----------------------------------------------------------------------------
# RDS Security Group
# HA-001: Accepts connections from BOTH public and private SGs
# -----------------------------------------------------------------------------

resource "aws_security_group" "rds_sg" {
  name   = "audit-rds-sg"
  vpc_id = aws_vpc.audit_vpc.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2_public_sg.id, aws_security_group.ec2_private_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "rds-sg"
  })
}

# -----------------------------------------------------------------------------
# Jump Box Security Group
# SSH from agent server only, SSH out to private subnet, HTTPS for AWS APIs
# -----------------------------------------------------------------------------

resource "aws_security_group" "jumpbox_sg" {
  name        = "audit-jumpbox-sg"
  description = "Bastion host - SSH from agent server only"
  vpc_id      = aws_vpc.audit_vpc.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.agent_server_ip]
    description = "SSH from agent server"
  }

  egress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.private_subnet_1a_cidr]
    description = "SSH to private subnet"
  }

  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS for AWS APIs"
  }

  tags = merge(local.common_tags, {
    Name = "jumpbox-sg"
  })
}

# -----------------------------------------------------------------------------
# NACL — HA-009: DENY rule that is bypassed by VPN route
# -----------------------------------------------------------------------------

resource "aws_network_acl" "private_nacl" {
  vpc_id     = aws_vpc.audit_vpc.id
  subnet_ids = [aws_subnet.private_subnet_1a.id]

  tags = merge(local.common_tags, {
    Name = "private-nacl"
  })
}

resource "aws_network_acl_rule" "private_allow_inbound" {
  network_acl_id = aws_network_acl.private_nacl.id
  rule_number    = 100
  protocol       = "-1"
  rule_action    = "allow"
  cidr_block     = "0.0.0.0/0"
  egress         = false
}

# HA-009: DENY 172.16.0.0/12 egress — bypassed by the VPN route in vpc.tf
resource "aws_network_acl_rule" "private_deny_172_egress" {
  network_acl_id = aws_network_acl.private_nacl.id
  rule_number    = 50
  protocol       = "-1"
  rule_action    = "deny"
  cidr_block     = "172.16.0.0/12"
  egress         = true
}

resource "aws_network_acl_rule" "private_allow_outbound" {
  network_acl_id = aws_network_acl.private_nacl.id
  rule_number    = 100
  protocol       = "-1"
  rule_action    = "allow"
  cidr_block     = "0.0.0.0/0"
  egress         = true
}

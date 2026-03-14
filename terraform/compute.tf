# =============================================================================
# ARGUS — EC2 Instances
# =============================================================================

# -----------------------------------------------------------------------------
# EC2-Public
# HA-002: User-data runs Flask on 0.0.0.0
# HA-014: No metadata_options block → IMDSv1 enabled
# HA-015: Dynamic AMI lookup — ARGUS detects by comparing AMI age
# -----------------------------------------------------------------------------

resource "aws_instance" "ec2_public" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.public_subnet_1a.id
  vpc_security_group_ids = [aws_security_group.ec2_public_sg.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2_public_profile.name
  key_name               = var.key_pair_name

  # HA-014: No metadata_options block — IMDSv1 remains enabled
  # HA-002: User-data starts Flask on 0.0.0.0
  user_data = base64encode(local.ec2_public_user_data)

  tags = merge(local.common_tags, {
    Name = "ec2-public"
  })
}

# -----------------------------------------------------------------------------
# EC2-Private
# HA-014: No metadata_options block → IMDSv1 enabled
# HA-017: User-data installs cron job that opens SSH temporarily
# -----------------------------------------------------------------------------

resource "aws_instance" "ec2_private" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.private_subnet_1a.id
  private_ip             = "10.0.10.100"
  vpc_security_group_ids = [aws_security_group.ec2_private_sg.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2_private_profile.name
  key_name               = var.key_pair_name

  # HA-014: No metadata_options block — IMDSv1 remains enabled
  user_data = base64encode(
    replace(
      replace(local.ec2_private_user_data, "$${sg_id}", aws_security_group.ec2_private_sg.id),
      "$${region}", var.aws_region
    )
  )

  tags = merge(local.common_tags, {
    Name = "ec2-private"
  })
}

# -----------------------------------------------------------------------------
# Jump Box (Bastion)
# Hardened: IMDSv2 required, iptables in user-data, restricted SG
# -----------------------------------------------------------------------------

resource "aws_instance" "jumpbox" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.public_subnet_1a.id
  vpc_security_group_ids = [aws_security_group.jumpbox_sg.id]
  iam_instance_profile   = aws_iam_instance_profile.jumpbox_profile.name
  key_name               = var.key_pair_name

  # Hardened bastion — IMDSv2 required
  metadata_options {
    http_tokens = "required"
  }

  user_data = base64encode(
    replace(local.jumpbox_user_data, "$${agent_ip}", var.agent_server_ip)
  )

  tags = merge(local.common_tags, {
    Name = "audit-jumpbox"
  })
}

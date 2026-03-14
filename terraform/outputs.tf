# =============================================================================
# ARGUS — Consolidated Outputs
# =============================================================================

# VPC
output "vpc_id" {
  value = aws_vpc.audit_vpc.id
}

output "public_subnet_id" {
  value = aws_subnet.public_subnet_1a.id
}

output "private_subnet_1a_id" {
  value = aws_subnet.private_subnet_1a.id
}

output "private_subnet_1b_id" {
  value = aws_subnet.private_subnet_1b.id
}

# EC2
output "ec2_public_ip" {
  value = aws_instance.ec2_public.public_ip
}

output "ec2_public_private_ip" {
  value = aws_instance.ec2_public.private_ip
}

output "ec2_private_private_ip" {
  value = aws_instance.ec2_private.private_ip
}

output "jumpbox_public_ip" {
  value = aws_instance.jumpbox.public_ip
}

# RDS
output "rds_endpoint" {
  value = aws_db_instance.audit_rds.endpoint
}

# SNS
output "sns_topic_arn" {
  value = aws_sns_topic.audit_alerts.arn
}

# CloudTrail
output "cloudtrail_name" {
  value = aws_cloudtrail.audit_trail.name
}

# Lambda
output "lambda_function_name" {
  value = aws_lambda_function.agent_runner.function_name
}

# KMS
output "kms_key_id" {
  value = aws_kms_key.audit_key.key_id
}

output "kms_key_arn" {
  value = aws_kms_key.audit_key.arn
}

# Secrets Manager
output "secrets_manager_arn" {
  value = aws_secretsmanager_secret.audit_secret.arn
}

# Audit Agent
output "audit_agent_role_arn" {
  value = aws_iam_role.audit_agent_role.arn
}

# S3
output "s3_backups_bucket" {
  value = aws_s3_bucket.audit_backups.id
}

output "s3_cloudtrail_bucket" {
  value = aws_s3_bucket.cloudtrail_logs.id
}

output "s3_vpcflow_bucket" {
  value = aws_s3_bucket.vpcflow_logs.id
}

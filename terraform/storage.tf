# =============================================================================
# ARGUS — S3 Buckets & Secrets Manager
# =============================================================================

# -----------------------------------------------------------------------------
# HA-013: S3 bucket with conditional public access (tag condition)
# -----------------------------------------------------------------------------

resource "aws_s3_bucket" "audit_backups" {
  bucket = "audit-backups-${data.aws_caller_identity.current.account_id}"

  tags = merge(local.common_tags, {
    Name = "audit-backups"
  })
}

# HA-013: Allow public read if object is tagged public=true
resource "aws_s3_bucket_policy" "audit_backups_policy" {
  bucket = aws_s3_bucket.audit_backups.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowPublicReadIfTagged"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.audit_backups.arn}/*"
        Condition = {
          StringEquals = {
            "s3:ExistingObjectTag/public" = "true"
          }
        }
      }
    ]
  })
}

# Let the conditional bucket policy work
resource "aws_s3_bucket_public_access_block" "audit_backups_pab" {
  bucket = aws_s3_bucket.audit_backups.id

  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = false # HA-013: Must be false for conditional policy
  restrict_public_buckets = false
}

# -----------------------------------------------------------------------------
# Secrets Manager
# -----------------------------------------------------------------------------

resource "aws_secretsmanager_secret" "audit_secret" {
  name = "audit/api-key"

  tags = merge(local.common_tags, {
    Name = "audit-secret"
  })
}

resource "aws_secretsmanager_secret_version" "audit_secret_value" {
  secret_id = aws_secretsmanager_secret.audit_secret.id
  secret_string = jsonencode({
    api_key     = "super-secret-key-12345"
    db_password = "AuditPassword123!"
  })
}

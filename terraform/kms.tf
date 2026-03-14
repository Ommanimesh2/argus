# =============================================================================
# ARGUS — KMS Key
# HA-020: Key rotation disabled
# =============================================================================

resource "aws_kms_key" "audit_key" {
  description         = "ARGUS audit demo encryption key"
  enable_key_rotation = false # HA-020: Key rotation disabled

  tags = merge(local.common_tags, {
    Name = "audit-kms-key"
  })
}

resource "aws_kms_alias" "audit_key_alias" {
  name          = "alias/argus-audit-key"
  target_key_id = aws_kms_key.audit_key.key_id
}

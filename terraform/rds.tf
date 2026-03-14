# =============================================================================
# ARGUS — RDS PostgreSQL
# HA-001: Direct access from EC2-Public (SG + IAM)
# HA-003: storage_encrypted = false
# HA-005: iam_database_authentication = false
# =============================================================================

resource "aws_db_subnet_group" "audit_rds_subnet_group" {
  name       = "audit-rds-subnet-group"
  subnet_ids = [aws_subnet.private_subnet_1a.id, aws_subnet.private_subnet_1b.id]

  tags = merge(local.common_tags, {
    Name = "audit-rds-subnet-group"
  })
}

resource "aws_db_instance" "audit_rds" {
  identifier     = "audit-demo-db"
  engine         = "postgres"
  engine_version = var.rds_engine_version
  instance_class = "db.t3.micro"

  allocated_storage = 20
  storage_encrypted = false # HA-003: Encryption disabled
  storage_type      = "gp3"

  db_name  = "auditdb"
  username = "auditadmin"
  password = var.rds_password

  db_subnet_group_name               = aws_db_subnet_group.audit_rds_subnet_group.name
  vpc_security_group_ids             = [aws_security_group.rds_sg.id]
  publicly_accessible                = false
  iam_database_authentication_enabled = false # HA-005: Should be true

  skip_final_snapshot = true

  tags = merge(local.common_tags, {
    Name = "audit-rds-instance"
  })
}

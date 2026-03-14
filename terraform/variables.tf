# =============================================================================
# ARGUS — Variable Declarations
# =============================================================================

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name used in resource naming"
  type        = string
  default     = "argus-audit"
}

variable "audit_demo_tag" {
  description = "Tag value to identify audit demo resources"
  type        = string
  default     = "AuditDemo"
}

# Networking
variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidr" {
  description = "CIDR block for the public subnet"
  type        = string
  default     = "10.0.1.0/24"
}

variable "private_subnet_1a_cidr" {
  description = "CIDR block for private subnet in AZ-a"
  type        = string
  default     = "10.0.10.0/24"
}

variable "private_subnet_1b_cidr" {
  description = "CIDR block for private subnet in AZ-b"
  type        = string
  default     = "10.0.11.0/24"
}

variable "az_1" {
  description = "Primary availability zone"
  type        = string
  default     = "us-east-1a"
}

variable "az_2" {
  description = "Secondary availability zone"
  type        = string
  default     = "us-east-1b"
}

# Compute
variable "instance_type" {
  description = "EC2 instance type for all instances"
  type        = string
  default     = "t3.micro"
}

variable "key_pair_name" {
  description = "Name of the EC2 key pair for SSH access"
  type        = string
}

# Database
variable "rds_password" {
  description = "Password for the RDS PostgreSQL instance"
  type        = string
  sensitive   = true
}

variable "rds_engine_version" {
  description = "PostgreSQL engine version (check aws rds describe-db-engine-versions --engine postgres)"
  type        = string
  default     = "15.3"
}

# Agent access
variable "agent_server_ip" {
  description = "IP address of the ARGUS agent server (for jump box SG)"
  type        = string
}

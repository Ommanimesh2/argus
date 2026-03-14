# =============================================================================
# ARGUS — VPC, Subnets, IGW, NAT GW, Route Tables, VPN GW
# =============================================================================

resource "aws_vpc" "audit_vpc" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(local.common_tags, {
    Name = "audit-vpc"
  })
}

resource "aws_internet_gateway" "audit_igw" {
  vpc_id = aws_vpc.audit_vpc.id

  tags = merge(local.common_tags, {
    Name = "audit-igw"
  })
}

# -----------------------------------------------------------------------------
# Subnets
# -----------------------------------------------------------------------------

resource "aws_subnet" "public_subnet_1a" {
  vpc_id                  = aws_vpc.audit_vpc.id
  cidr_block              = var.public_subnet_cidr
  availability_zone       = var.az_1
  map_public_ip_on_launch = true

  tags = merge(local.common_tags, {
    Name = "public-subnet-1a"
  })
}

resource "aws_subnet" "private_subnet_1a" {
  vpc_id            = aws_vpc.audit_vpc.id
  cidr_block        = var.private_subnet_1a_cidr
  availability_zone = var.az_1

  tags = merge(local.common_tags, {
    Name = "private-subnet-1a"
  })
}

resource "aws_subnet" "private_subnet_1b" {
  vpc_id            = aws_vpc.audit_vpc.id
  cidr_block        = var.private_subnet_1b_cidr
  availability_zone = var.az_2

  tags = merge(local.common_tags, {
    Name = "private-subnet-1b"
  })
}

# -----------------------------------------------------------------------------
# NAT Gateway
# -----------------------------------------------------------------------------

resource "aws_eip" "nat_eip" {
  domain = "vpc"

  tags = merge(local.common_tags, {
    Name = "nat-eip"
  })
}

resource "aws_nat_gateway" "nat_gw" {
  allocation_id = aws_eip.nat_eip.id
  subnet_id     = aws_subnet.public_subnet_1a.id

  tags = merge(local.common_tags, {
    Name = "audit-nat-gw"
  })

  depends_on = [aws_internet_gateway.audit_igw]
}

# -----------------------------------------------------------------------------
# Route Tables
# -----------------------------------------------------------------------------

resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.audit_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.audit_igw.id
  }

  tags = merge(local.common_tags, {
    Name = "public-rt"
  })
}

resource "aws_route_table" "private_rt" {
  vpc_id = aws_vpc.audit_vpc.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.nat_gw.id
  }

  tags = merge(local.common_tags, {
    Name = "private-rt"
  })
}

resource "aws_route_table_association" "public_rta_1a" {
  subnet_id      = aws_subnet.public_subnet_1a.id
  route_table_id = aws_route_table.public_rt.id
}

resource "aws_route_table_association" "private_rta_1a" {
  subnet_id      = aws_subnet.private_subnet_1a.id
  route_table_id = aws_route_table.private_rt.id
}

resource "aws_route_table_association" "private_rta_1b" {
  subnet_id      = aws_subnet.private_subnet_1b.id
  route_table_id = aws_route_table.private_rt.id
}

# -----------------------------------------------------------------------------
# VPN Gateway — HA-009 (NACL bypass) + HA-011 (NAT bypass)
# Routes to VPN GW will be blackhole (no customer gateway). Intentional —
# the NACL/NAT bypass is discoverable via describe-route-tables.
# -----------------------------------------------------------------------------

resource "aws_vpn_gateway" "audit_vpn" {
  vpc_id = aws_vpc.audit_vpc.id

  tags = merge(local.common_tags, {
    Name = "audit-vpn-gw"
  })
}

# HA-009: Route that bypasses the NACL deny rule for 172.16.0.0/12
# HA-011: This more-specific route also bypasses the NAT gateway
resource "aws_route" "to_vpn" {
  route_table_id         = aws_route_table.private_rt.id
  destination_cidr_block = "172.16.0.0/12"
  gateway_id             = aws_vpn_gateway.audit_vpn.id
}

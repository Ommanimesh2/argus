# =============================================================================
# ARGUS — CloudWatch, CloudTrail, VPC Flow Logs, SNS
# =============================================================================

# -----------------------------------------------------------------------------
# HA-006: SNS topic — created here, deleted by post-apply.sh
# The CloudWatch alarm will then point to a non-existent topic.
# -----------------------------------------------------------------------------

resource "aws_sns_topic" "audit_alerts" {
  name = "audit-alerts"

  tags = merge(local.common_tags, {
    Name = "audit-alerts-topic"
  })
}

# HA-006: Alarm points to SNS topic that gets deleted post-apply
resource "aws_cloudwatch_metric_alarm" "ec2_private_unhealthy" {
  alarm_name          = "EC2-Private-Unhealthy"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "StatusCheckFailed"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  alarm_actions       = [aws_sns_topic.audit_alerts.arn]

  dimensions = {
    InstanceId = aws_instance.ec2_private.id
  }

  tags = merge(local.common_tags, {
    Name = "ec2-private-unhealthy-alarm"
  })
}

# -----------------------------------------------------------------------------
# HA-008: CloudTrail — trail created, stopped post-apply.
# Bucket policy Denies s3:PutObject from CloudTrail (allows trail creation
# but blocks log delivery).
# -----------------------------------------------------------------------------

resource "aws_cloudtrail" "audit_trail" {
  name           = "audit-demo-trail"
  s3_bucket_name = aws_s3_bucket.cloudtrail_logs.id

  include_global_service_events = true
  is_multi_region_trail         = false

  depends_on = [aws_s3_bucket_policy.cloudtrail_policy]

  tags = merge(local.common_tags, {
    Name = "audit-trail"
  })
}

resource "aws_s3_bucket" "cloudtrail_logs" {
  bucket        = "audit-cloudtrail-logs-${data.aws_caller_identity.current.account_id}"
  force_destroy = true

  tags = merge(local.common_tags, {
    Name = "cloudtrail-logs"
  })
}

# HA-008: Allow CloudTrail to check ACL but deny log writes
resource "aws_s3_bucket_policy" "cloudtrail_policy" {
  bucket = aws_s3_bucket.cloudtrail_logs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AWSCloudTrailAclCheck"
        Effect = "Allow"
        Principal = {
          Service = "cloudtrail.amazonaws.com"
        }
        Action   = "s3:GetBucketAcl"
        Resource = aws_s3_bucket.cloudtrail_logs.arn
      },
      {
        Sid    = "AWSCloudTrailWriteDeny"
        Effect = "Deny"
        Principal = {
          Service = "cloudtrail.amazonaws.com"
        }
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.cloudtrail_logs.arn}/*"
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# HA-007: VPC Flow Logs — delivers to S3 with invalid path suffix
# -----------------------------------------------------------------------------

resource "aws_flow_log" "vpc_flow_logs" {
  log_destination_type = "s3"
  log_destination      = "${aws_s3_bucket.vpcflow_logs.arn}/invalid-path/"
  traffic_type         = "ALL"
  vpc_id               = aws_vpc.audit_vpc.id

  tags = merge(local.common_tags, {
    Name = "vpc-flow-logs"
  })
}

resource "aws_s3_bucket" "vpcflow_logs" {
  bucket        = "audit-vpcflow-logs-${data.aws_caller_identity.current.account_id}"
  force_destroy = true

  tags = merge(local.common_tags, {
    Name = "vpcflow-logs"
  })
}

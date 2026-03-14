#!/usr/bin/env bash
# =============================================================================
# ARGUS — Post-Apply Script
# Simulates hidden abnormalities that cannot be expressed in Terraform.
# Run after `terraform apply` completes.
# =============================================================================
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"

echo "=== ARGUS Post-Apply: Creating runtime hidden abnormalities ==="

# -------------------------------------------------------------------------
# HA-006: Delete the SNS topic so the CloudWatch alarm points to nothing
# -------------------------------------------------------------------------
echo "[HA-006] Deleting SNS topic (alarm will point to non-existent topic)..."
SNS_ARN=$(terraform output -raw sns_topic_arn 2>/dev/null)
if [ -n "$SNS_ARN" ]; then
  aws sns delete-topic --topic-arn "$SNS_ARN" --region "$REGION"
  echo "  Deleted: $SNS_ARN"
else
  echo "  WARN: Could not get SNS topic ARN from terraform output"
fi

# -------------------------------------------------------------------------
# HA-008: Stop CloudTrail logging (trail exists but is not active)
# -------------------------------------------------------------------------
echo "[HA-008] Stopping CloudTrail logging..."
TRAIL_NAME=$(terraform output -raw cloudtrail_name 2>/dev/null)
if [ -n "$TRAIL_NAME" ]; then
  aws cloudtrail stop-logging --name "$TRAIL_NAME" --region "$REGION"
  echo "  Stopped: $TRAIL_NAME"
else
  echo "  WARN: Could not get trail name from terraform output"
fi

# -------------------------------------------------------------------------
# HA-018: Configuration drift — modify EC2 tags outside Terraform
# -------------------------------------------------------------------------
echo "[HA-018] Creating configuration drift (manual tag changes)..."
EC2_PUBLIC_ID=$(aws ec2 describe-instances \
  --region "$REGION" \
  --filters "Name=tag:Name,Values=ec2-public" "Name=instance-state-name,Values=running" \
  --query "Reservations[0].Instances[0].InstanceId" \
  --output text 2>/dev/null)

EC2_PRIVATE_ID=$(aws ec2 describe-instances \
  --region "$REGION" \
  --filters "Name=tag:Name,Values=ec2-private" "Name=instance-state-name,Values=running" \
  --query "Reservations[0].Instances[0].InstanceId" \
  --output text 2>/dev/null)

if [ -n "$EC2_PUBLIC_ID" ] && [ "$EC2_PUBLIC_ID" != "None" ]; then
  aws ec2 create-tags --resources "$EC2_PUBLIC_ID" \
    --tags Key=Environment,Value=production Key=CostCenter,Value=eng-42 \
    --region "$REGION"
  echo "  Drifted tags on ec2-public: $EC2_PUBLIC_ID"
fi

if [ -n "$EC2_PRIVATE_ID" ] && [ "$EC2_PRIVATE_ID" != "None" ]; then
  aws ec2 create-tags --resources "$EC2_PRIVATE_ID" \
    --tags Key=Environment,Value=staging Key=Owner,Value=manual-change \
    --region "$REGION"
  echo "  Drifted tags on ec2-private: $EC2_PRIVATE_ID"
fi

# -------------------------------------------------------------------------
# HA-019: Create a manual SNS subscription not tracked in Terraform state
# -------------------------------------------------------------------------
echo "[HA-019] Creating manual SNS subscription (not in Terraform state)..."
MANUAL_TOPIC_ARN=$(aws sns create-topic --name "audit-manual-alerts" \
  --region "$REGION" --query "TopicArn" --output text 2>/dev/null)

if [ -n "$MANUAL_TOPIC_ARN" ]; then
  aws sns subscribe \
    --topic-arn "$MANUAL_TOPIC_ARN" \
    --protocol email \
    --notification-endpoint "audit-alerts@example.com" \
    --region "$REGION" >/dev/null 2>&1 || true
  echo "  Created manual topic + subscription: $MANUAL_TOPIC_ARN"
else
  echo "  WARN: Could not create manual SNS topic"
fi

echo ""
echo "=== Post-apply complete ==="
echo "Run 'terraform plan' to see drift (HA-018)."
echo "Run 'aws cloudtrail get-trail-status --name $TRAIL_NAME' to verify HA-008."
echo "Run 'aws sns get-topic-attributes --topic-arn $SNS_ARN' to verify HA-006 (should error)."

# =============================================================================
# ARGUS — Lambda Function
# HA-016: Lambda attached to wrong IAM role
# =============================================================================

# -----------------------------------------------------------------------------
# Lambda source
# -----------------------------------------------------------------------------

data "archive_file" "lambda_placeholder" {
  type        = "zip"
  source_file = "${path.module}/lambda/placeholder.py"
  output_path = "${path.module}/lambda/placeholder.zip"
}

# -----------------------------------------------------------------------------
# HA-016: Lambda uses lambda_wrong_role instead of agent_runner_role
# -----------------------------------------------------------------------------

resource "aws_lambda_function" "agent_runner" {
  filename         = data.archive_file.lambda_placeholder.output_path
  source_code_hash = data.archive_file.lambda_placeholder.output_base64sha256
  function_name    = "audit-agent-runner"
  role             = aws_iam_role.lambda_wrong_role.arn # HA-016: Wrong role
  handler          = "placeholder.handler"
  runtime          = "python3.11"

  tags = merge(local.common_tags, {
    Name = "agent-runner-function"
  })
}

# HA-016: This role has no useful permissions — Lambda should use agent_runner_role
resource "aws_iam_role" "lambda_wrong_role" {
  name = "lambda-wrong-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })

  tags = merge(local.common_tags, {
    Name = "lambda-wrong-role"
  })
}

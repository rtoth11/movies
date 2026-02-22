resource "aws_s3_bucket" "movies_s3_bucket" {
  bucket = var.movies_s3_bucket_name
  force_destroy = true
}

data "aws_iam_policy_document" "lambda_assume_role_policy_document" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "extraction_lambda_role" {
  name               = var.extraction_lambda_role_name
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role_policy_document.json
  path               = var.extraction_lambda_role_path
}

data "aws_iam_policy_document" "s3_write_policy_document" {
  statement {
    effect = "Allow"
    resources = ["${aws_s3_bucket.movies_s3_bucket.arn}/*"]
    actions = [
      "s3:PutObject"
    ]
  }
}

resource "aws_iam_policy" "s3_write_policy" {
  name   = "s3-write-policy"
  policy = data.aws_iam_policy_document.s3_write_policy_document.json
}

resource "aws_iam_role_policy_attachment" "attach_s3_write_policy_to_lambda_role" {
  role       = aws_iam_role.extraction_lambda_role.name
  policy_arn = aws_iam_policy.s3_write_policy.arn
}

data "aws_iam_policy_document" "cloudwatch_write_policy_document" {
  statement {
    effect = "Allow"
    resources = ["*"]
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
  }
}

resource "aws_iam_policy" "cloudwatch_write_policy" {
  name   = "cloudwatch-write-policy"
  policy = data.aws_iam_policy_document.cloudwatch_write_policy_document.json
}

resource "aws_iam_role_policy_attachment" "attach_cloudwatch_write_policy_to_lambda_role" {
  role       = aws_iam_role.extraction_lambda_role.name
  policy_arn = aws_iam_policy.cloudwatch_write_policy.arn
}

data "aws_caller_identity" "current" {}

resource "aws_lambda_function" "extraction_lambda" {
  function_name = var.extraction_lambda_function_name
  role          = aws_iam_role.extraction_lambda_role.arn
  package_type  = "Image"
  # We need to upload a dummy image first since the actual image is built and pushed outside of Terraform
  image_uri     = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.region}.amazonaws.com/python-lambda-base:latest"

  environment {
    variables = {
      S3_BUCKET_NAME = var.movies_s3_bucket_name
    }
  }

  memory_size = var.extraction_lambda_memory_size
  timeout     = var.extraction_lambda_timeout

  architectures = ["arm64"]
}

resource "aws_lambda_function_event_invoke_config" "extraction_lambda_event_config" {
  function_name                = aws_lambda_function.extraction_lambda.function_name
  maximum_event_age_in_seconds = 900
  maximum_retry_attempts       = 0
}

resource "aws_cloudwatch_event_rule" "run_data_extraction_event_rule" {
  name        = var.extraction_event_rule_name
  description = "Run data extraction code on a defined schedule"
  schedule_expression = var.extraction_event_schedule_expression
}

resource "aws_cloudwatch_event_target" "extraction_lambda_target" {
  rule      = aws_cloudwatch_event_rule.run_data_extraction_event_rule.name
  target_id = var.extraction_lambda_function_name
  arn       = aws_lambda_function.extraction_lambda.arn

  retry_policy {
    maximum_retry_attempts = 0
    maximum_event_age_in_seconds = 900
  }
}

resource "aws_lambda_permission" "allow_cloudwatch" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.extraction_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.run_data_extraction_event_rule.arn
}

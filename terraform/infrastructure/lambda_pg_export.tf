resource "aws_ecr_repository" "pg_export_ecr_repository" {
  name = var.pg_export_ecr_repo_name
  force_delete = true
}

resource "aws_iam_role" "lambda_pg_export_role" {
  name               = "lambda-pg-export-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

resource "aws_iam_role_policy_attachment" "lambda_pg_export_basic_execution" {
  role       = aws_iam_role.lambda_pg_export_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_iam_policy" "lambda_pg_export_ssm_policy" {
  name   = "lambda-pg-export-ssm"
  policy = data.aws_iam_policy_document.lambda_ssm_policy_document.json
}

resource "aws_iam_role_policy_attachment" "lambda_pg_export_ssm" {
  role       = aws_iam_role.lambda_pg_export_role.name
  policy_arn = aws_iam_policy.lambda_pg_export_ssm_policy.arn
}

resource "aws_cloudwatch_log_group" "lambda_pg_export_log_group" {
  name              = "/aws/lambda/pg-export"
  retention_in_days = 7
}

resource "aws_lambda_function" "pg_export" {
  function_name    = "pg-export"
  role             = aws_iam_role.lambda_pg_export_role.arn
  package_type  = "Image"
  # We need to upload a dummy image first since the actual image is built and pushed outside of Terraform
  image_uri     = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.region}.amazonaws.com/python-lambda-base:latest"

  timeout     = 900
  memory_size = 512

  architectures = ["arm64"]

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda_sg.id]
  }

  environment {
    variables = {
      PG_HOST     = aws_db_instance.postgres_instance.address
      PG_PORT     = tostring(aws_db_instance.postgres_instance.port)
      PG_DB       = var.pg_database
      PG_USER     = var.pg_user
      PG_PASSWORD = var.pg_password
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.lambda_pg_export_log_group,
    aws_iam_role_policy_attachment.lambda_pg_export_basic_execution,
  ]

  tags = {
    Name = "pg-export"
  }
}

resource "aws_lambda_function_event_invoke_config" "pg_export_invoke_config" {
  function_name                = aws_lambda_function.pg_export.function_name
  maximum_retry_attempts       = 0
  maximum_event_age_in_seconds = 900
}

resource "aws_ssm_parameter" "pg_export_lambda_name" {
  name  = "/movies/PG_EXPORT_LAMBDA_NAME"
  type  = "String"
  value = aws_lambda_function.pg_export.function_name
}

data "aws_iam_policy_document" "s3_read_write_policy_document" {
  statement {
    effect  = "Allow"
    actions = [
      "s3:PutObject",
      "s3:GetObject",
      "s3:ListBucket"
    ]
    resources = [
      aws_s3_bucket.movies_s3_bucket.arn,
      "${aws_s3_bucket.movies_s3_bucket.arn}/*"
    ]
  }
}

resource "aws_iam_policy" "s3_read_write_policy_document" {
  name   = "s3-read-write-policy"
  policy = data.aws_iam_policy_document.s3_read_write_policy_document.json
}

resource "aws_iam_role_policy_attachment" "attach_s3_read_write_to_pg_export_role" {
  role       = aws_iam_role.lambda_pg_export_role.name
  policy_arn = aws_iam_policy.s3_read_write_policy_document.arn
}

resource "aws_security_group" "lambda_sg" {
  name        = "lambda-sg"
  description = "Lambda egress to RDS and S3"
  vpc_id      = aws_vpc.movies_vpc.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "lambda-sg"
  }
}

resource "aws_iam_role" "lambda_pg_import_role" {
  name               = "lambda-pg-import-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

resource "aws_iam_role_policy_attachment" "lambda_pg_import_basic_execution" {
  role       = aws_iam_role.lambda_pg_import_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_iam_policy" "lambda_pg_import_ssm_policy" {
  name   = "lambda-pg-import-ssm"
  policy = data.aws_iam_policy_document.lambda_ssm_policy_document.json
}

resource "aws_iam_role_policy_attachment" "lambda_pg_import_ssm" {
  role       = aws_iam_role.lambda_pg_import_role.name
  policy_arn = aws_iam_policy.lambda_pg_import_ssm_policy.arn
}

resource "aws_cloudwatch_log_group" "lambda_pg_import_log_group" {
  name              = "/aws/lambda/pg-import"
  retention_in_days = 7
}

locals {
  lambda_pg_import_zip_path = "${path.module}/lambda_pg_import.zip"
}

resource "aws_lambda_function" "pg_import" {
  function_name    = "pg-import"
  role             = aws_iam_role.lambda_pg_import_role.arn
  handler          = "lambda_pg_import.handler"
  runtime          = "python3.12"
  filename         = local.lambda_pg_import_zip_path
  source_code_hash = fileexists(local.lambda_pg_import_zip_path) ? filebase64sha256(local.lambda_pg_import_zip_path) : null

  timeout     = 900
  memory_size = 512

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
    aws_cloudwatch_log_group.lambda_pg_import_log_group,
    aws_iam_role_policy_attachment.lambda_pg_import_basic_execution,
  ]

  tags = {
    Name = "pg-import"
  }
}

resource "aws_lambda_function_event_invoke_config" "pg_import_invoke_config" {
  function_name                = aws_lambda_function.pg_import.function_name
  maximum_retry_attempts       = 0
  maximum_event_age_in_seconds = 900
}

resource "aws_ssm_parameter" "pg_import_lambda_name" {
  name  = "/movies/PG_IMPORT_LAMBDA_NAME"
  type  = "String"
  value = aws_lambda_function.pg_import.function_name
}

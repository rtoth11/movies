data "aws_iam_policy_document" "ec2_assume_role_policy_document" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "extraction_ec2_role" {
  name               = var.extraction_ec2_role_name
  assume_role_policy = data.aws_iam_policy_document.ec2_assume_role_policy_document.json
  path               = var.extraction_ec2_role_path
}

data "aws_iam_policy_document" "cloudwatch_write_policy_document" {
  statement {
    effect = "Allow"
    resources = ["arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:log-group:/extraction/*"]
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
  }
}

resource "aws_cloudwatch_log_group" "extraction_log_group" {
  name              = "/extraction/movie-batch"
  retention_in_days = 7
}

resource "aws_iam_policy" "cloudwatch_write_policy" {
  name   = "cloudwatch-write-policy"
  policy = data.aws_iam_policy_document.cloudwatch_write_policy_document.json
}

resource "aws_iam_role_policy_attachment" "attach_cloudwatch_write_policy_to_ec2_role" {
  role       = aws_iam_role.extraction_ec2_role.name
  policy_arn = aws_iam_policy.cloudwatch_write_policy.arn
}

resource "aws_iam_role_policy_attachment" "attach_ecr_pull_policy" {
  role       = aws_iam_role.extraction_ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

data "aws_caller_identity" "current" {}

data "aws_iam_policy_document" "ssm_read_policy_document" {
  statement {
    effect = "Allow"
    actions = [
      "ssm:GetParameter",
      "ssm:GetParameters"
    ]
    resources = [
      "arn:aws:ssm:${var.region}:${data.aws_caller_identity.current.account_id}:parameter/extraction/*"
    ]
  }
}

resource "aws_iam_policy" "ssm_read_policy" {
  name   = "extraction-ssm-read"
  policy = data.aws_iam_policy_document.ssm_read_policy_document.json
}

resource "aws_iam_role_policy_attachment" "attach_ssm_read_policy" {
  role       = aws_iam_role.extraction_ec2_role.name
  policy_arn = aws_iam_policy.ssm_read_policy.arn
}

data "aws_iam_policy_document" "kms_decrypt_policy_document" {
  statement {
    effect = "Allow"
    actions = ["kms:Decrypt"]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "kms_decrypt_policy" {
  name   = "extraction-kms-decrypt"
  policy = data.aws_iam_policy_document.kms_decrypt_policy_document.json
}

resource "aws_iam_role_policy_attachment" "attach_kms_decrypt_policy" {
  role       = aws_iam_role.extraction_ec2_role.name
  policy_arn = aws_iam_policy.kms_decrypt_policy.arn
}

data "aws_iam_policy_document" "event_bridge_assume_role_policy_document" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "event_bridge_role" {
  name               = var.extraction_event_bridge_role_name
  assume_role_policy = data.aws_iam_policy_document.event_bridge_assume_role_policy_document.json
  path               = var.extraction_ec2_role_path
}

data "aws_iam_policy_document" "ec2_start_policy_document" {
  statement {
    effect = "Allow"
    actions = ["ec2:StartInstances"]
    resources = ["arn:aws:ec2:${var.region}:${data.aws_caller_identity.current.account_id}:instance/${aws_instance.extraction_instance.id}"]
  }
}

resource "aws_iam_policy" "ec2_start_policy" {
  name   = "extraction-ec2-start"
  policy = data.aws_iam_policy_document.ec2_start_policy_document.json
}

resource "aws_iam_role_policy_attachment" "attach_ec2_start_policy" {
  role       = aws_iam_role.event_bridge_role.name
  policy_arn = aws_iam_policy.ec2_start_policy.arn
}

data "aws_iam_policy_document" "start_automation_policy_document" {
  statement {
    effect = "Allow"
    actions = ["ssm:StartAutomationExecution"]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "start_automation_policy" {
  name   = "extraction-start-automation"
  policy = data.aws_iam_policy_document.start_automation_policy_document.json
}

resource "aws_iam_role_policy_attachment" "attach_start_automation_policy" {
  role       = aws_iam_role.event_bridge_role.name
  policy_arn = aws_iam_policy.start_automation_policy.arn
}

resource "aws_iam_instance_profile" "extraction_instance_profile" {
  name = "extraction-instance-profile"
  role = aws_iam_role.extraction_ec2_role.name
}

resource "aws_security_group" "extraction_sg" {
  name        = "extraction-sg"
  description = "Allow outbound internet access"

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "extraction_instance" {
  ami           = "ami-0f3caa1cf4417e51b"
  instance_type = "t2.micro"

  iam_instance_profile = aws_iam_instance_profile.extraction_instance_profile.name
  vpc_security_group_ids = [aws_security_group.extraction_sg.id]

  user_data_replace_on_change = true

  user_data = <<-EOF
      #!/bin/bash
      yum update -y
      yum install -y docker
      systemctl enable docker
      systemctl start docker

      cat << 'SCRIPT' > /usr/local/bin/run-extraction.sh
      #!/bin/bash

      REGION=${var.region}
      ACCOUNT_ID=${data.aws_caller_identity.current.account_id}
      REPO=${aws_ecr_repository.extraction_ecr_repository.repository_url}

      PG_PORT=${aws_db_instance.postgres_instance.port}

      TMDB_API_KEY=$(aws ssm get-parameter \
        --name "/extraction/TMDB_API_KEY" \
        --with-decryption \
        --query "Parameter.Value" \
        --output text \
        --region $REGION)

      DATABRICKS_HOST=$(aws ssm get-parameter \
        --name "/extraction/DATABRICKS_HOST" \
        --with-decryption \
        --query "Parameter.Value" \
        --output text \
        --region $REGION)

      DATABRICKS_TOKEN=$(aws ssm get-parameter \
        --name "/extraction/DATABRICKS_TOKEN" \
        --with-decryption \
        --query "Parameter.Value" \
        --output text \
        --region $REGION)

      PG_HOST=$(aws ssm get-parameter \
        --name "/extraction/PG_HOST" \
        --with-decryption \
        --query "Parameter.Value" \
        --output text \
        --region $REGION)

      PG_DATABASE=$(aws ssm get-parameter \
        --name "/extraction/PG_DATABASE" \
        --with-decryption \
        --query "Parameter.Value" \
        --output text \
        --region $REGION)

      PG_USER=$(aws ssm get-parameter \
        --name "/extraction/PG_USER" \
        --with-decryption \
        --query "Parameter.Value" \
        --output text \
        --region $REGION)

      PG_PASSWORD=$(aws ssm get-parameter \
        --name "/extraction/PG_PASSWORD" \
        --with-decryption \
        --query "Parameter.Value" \
        --output text \
        --region $REGION)

      GENRES=$(aws ssm get-parameter \
        --name "/extraction/GENRES" \
        --query "Parameter.Value" \
        --output text \
        --region $REGION)

      NUMBER_OF_MOVIES=$(aws ssm get-parameter \
        --name "/extraction/NUMBER_OF_MOVIES" \
        --query "Parameter.Value" \
        --output text \
        --region $REGION)

      aws ecr get-login-password --region $REGION \
        | docker login \
        --username AWS \
        --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

      docker pull $REPO:latest

      docker run --rm \
        --log-driver=awslogs \
        --log-opt awslogs-region=$REGION \
        --log-opt awslogs-group=/extraction/movie-batch \
        --log-opt awslogs-stream=$(hostname)-$(date +%s) \
        -e TMDB_API_KEY="$TMDB_API_KEY" \
        -e DATABRICKS_HOST="$DATABRICKS_HOST" \
        -e DATABRICKS_TOKEN="$DATABRICKS_TOKEN" \
        -e PG_HOST="$PG_HOST" \
        -e PG_PORT="$PG_PORT" \
        -e PG_DATABASE="$PG_DATABASE" \
        -e PG_USER="$PG_USER" \
        -e PG_PASSWORD="$PG_PASSWORD" \
        -e GENRES="$GENRES" \
        -e NUMBER_OF_MOVIES="$NUMBER_OF_MOVIES" \
        $REPO:latest

      shutdown -h now
      SCRIPT

      chmod +x /usr/local/bin/run-extraction.sh

      # Create systemd service
      cat << 'SERVICE' > /etc/systemd/system/extraction.service
      [Unit]
      Description=Run Movie Extraction Container
      After=docker.service
      Requires=docker.service

      [Service]
      Type=oneshot
      ExecStart=/usr/local/bin/run-extraction.sh
      RemainAfterExit=false

      [Install]
      WantedBy=multi-user.target
      SERVICE

      systemctl enable extraction.service
      shutdown -h now
      EOF

  tags = {
    Name = "movie-extraction-instance"
  }
}

resource "aws_cloudwatch_event_rule" "run_data_extraction_event_rule" {
  name        = var.extraction_event_rule_name
  description = "Run data extraction code on a defined schedule"
  schedule_expression = var.extraction_event_schedule_expression
}

resource "aws_cloudwatch_event_target" "start_ec2_target" {
  rule      = aws_cloudwatch_event_rule.run_data_extraction_event_rule.name
  target_id = "start-extraction-ec2-instance"
  arn       = "arn:aws:ssm:us-east-1::automation-definition/AWS-StartEC2Instance"
  role_arn = aws_iam_role.event_bridge_role.arn

  input = jsonencode({
    InstanceId = [aws_instance.extraction_instance.id]
  })
}

resource "aws_ssm_parameter" "tmdb_api_key" {
  name  = "/extraction/TMDB_API_KEY"
  type  = "SecureString"
  value = "placeholder"
  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "databricks_host" {
  name  = "/extraction/DATABRICKS_HOST"
  type  = "SecureString"
  value = "placeholder"
  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "databricks_token" {
  name  = "/extraction/DATABRICKS_TOKEN"
  type  = "SecureString"
  value = "placeholder"
  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "pg_host" {
  name  = "/extraction/PG_HOST"
  type  = "SecureString"
  value = "placeholder"
  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "pg_database" {
  name  = "/extraction/PG_DATABASE"
  type  = "SecureString"
  value = "placeholder"
  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "pg_user" {
  name  = "/extraction/PG_USER"
  type  = "SecureString"
  value = "placeholder"
  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "pg_password" {
  name  = "/extraction/PG_PASSWORD"
  type  = "SecureString"
  value = "placeholder"
  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "genres" {
  name  = "/extraction/GENRES"
  type  = "String"
  value = "placeholder"
  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "number_of_movies" {
  name  = "/extraction/NUMBER_OF_MOVIES"
  type  = "String"
  value = "placeholder"
  lifecycle {
    ignore_changes = [value]
  }
}

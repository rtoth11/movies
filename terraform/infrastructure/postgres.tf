resource "aws_s3_bucket" "movies_s3_bucket" {
  bucket        = var.movies_s3_bucket_name
  force_destroy = true
}

resource "aws_vpc" "movies_vpc" {
  cidr_block           = "10.0.0.0/16"
  instance_tenancy     = "default"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {
    Name = "vpc-for-postgres"
  }
}

variable "subnets_cidr" {
  type    = list(string)
  default = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "azs" {
  type    = list(string)
  default = ["us-east-1a", "us-east-1b"]
}

resource "aws_subnet" "public" {
  count                   = length(var.subnets_cidr)
  vpc_id                  = aws_vpc.movies_vpc.id
  cidr_block              = var.subnets_cidr[count.index]
  availability_zone       = var.azs[count.index]
  map_public_ip_on_launch = true
  tags = {
    Name = "public-subnet-${count.index + 1}"
  }
}

resource "aws_internet_gateway" "movies_gateway" {
  vpc_id = aws_vpc.movies_vpc.id
  tags = {
    Name = "movies-gateway"
  }
}

resource "aws_route_table" "public_route_table" {
  vpc_id = aws_vpc.movies_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.movies_gateway.id
  }

  tags = {
    Name = "public-route-table"
  }
}

resource "aws_route_table_association" "public_association" {
  count          = length(var.subnets_cidr)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public_route_table.id
}

resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.movies_vpc.id
  service_name      = "com.amazonaws.${var.region}.s3"
  vpc_endpoint_type = "Gateway"

  route_table_ids = [
    aws_route_table.private_route_table.id,
    aws_route_table.public_route_table.id,
  ]

  tags = { Name = "s3-vpc-endpoint" }
}

resource "aws_db_subnet_group" "postgres_subnet_group" {
  name       = "postgres-subnet-group"
  subnet_ids = [aws_subnet.public[0].id, aws_subnet.public[1].id]
  tags = {
    Name = "postgres-subnet-group"
  }
}

resource "aws_security_group" "postgres_sg" {
  name        = "postgres-security-group"
  description = "Allow PostgreSQL access from your IP and VPC only"
  vpc_id      = aws_vpc.movies_vpc.id

  ingress {
    description = "PostgreSQL from my IP"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [var.my_ip_cidr]
  }

  ingress {
    description     = "PostgreSQL from extraction EC2"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.extraction_sg.id]
  }

  ingress {
    description     = "PostgreSQL from backend EC2"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2_sg[0].id]
  }

  ingress {
    description     = "PostgreSQL from Lambda"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda_sg.id]
  }

  egress {
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  tags = {
    Name = "postgres-security-group"
  }
}

resource "aws_db_instance" "postgres_instance" {
  identifier            = "postgres-instance"
  allocated_storage     = 20
  max_allocated_storage = 20
  engine                = "postgres"
  engine_version        = "15.10"
  instance_class        = "db.t4g.micro"
  db_name               = var.pg_database
  username              = var.pg_user
  password              = var.pg_password
  skip_final_snapshot   = true

  vpc_security_group_ids = [aws_security_group.postgres_sg.id]
  db_subnet_group_name   = aws_db_subnet_group.postgres_subnet_group.name

  publicly_accessible = false

  iam_database_authentication_enabled = true

  tags = {
    Name = "postgres-instance"
  }
}

resource "aws_iam_role" "rds_s3_import_role" {
  name = "rds-s3-import-export-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "rds.amazonaws.com" }
      Action    = "sts:AssumeRole"
      Condition = {
        StringEquals = {
          "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          "aws:SourceArn"     = aws_db_instance.postgres_instance.arn
        }
      }
    }]
  })
}

data "aws_iam_policy_document" "s3_access_policy_document" {
  statement {
    effect  = "Allow"
    actions = ["s3:GetObject", "s3:ListBucket"]
    resources = [
      aws_s3_bucket.movies_s3_bucket.arn,
      "${aws_s3_bucket.movies_s3_bucket.arn}/*"
    ]
  }
}

resource "aws_iam_policy" "s3_access_policy" {
  name   = "s3-access-policy"
  policy = data.aws_iam_policy_document.s3_access_policy_document.json
}

resource "aws_iam_role_policy_attachment" "attach_s3_access_to_rds_s3_import" {
  role       = aws_iam_role.rds_s3_import_role.name
  policy_arn = aws_iam_policy.s3_access_policy.arn
}

resource "aws_db_instance_role_association" "rds_s3_import_role_association" {
  db_instance_identifier = aws_db_instance.postgres_instance.identifier
  feature_name           = "s3Import"
  role_arn               = aws_iam_role.rds_s3_import_role.arn
}

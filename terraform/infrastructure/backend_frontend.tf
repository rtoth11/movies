resource "aws_subnet" "private" {
  count                   = length(var.subnets_cidr)
  vpc_id                  = aws_vpc.vpc_for_postgres.id
  cidr_block              = cidrsubnet(aws_vpc.vpc_for_postgres.cidr_block, 8, count.index + 10)
  availability_zone       = var.azs[count.index]
  map_public_ip_on_launch = false
  tags = {
    Name = "private-subnet-${count.index + 1}"
  }
}

resource "aws_security_group" "backend_sg" {
  name        = "backend-sg"
  description = "Security group for backend servers"
  vpc_id      = aws_vpc.vpc_for_postgres.id

  ingress {
    from_port = 80
    to_port   = 80
    protocol  = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = {
    Name = "backend-security-group"
  }
}

resource "aws_security_group" "ecs_sg" {
  name        = "ecs-sg"
  description = "Security group for ECS tasks"
  vpc_id      = aws_vpc.vpc_for_postgres.id

  ingress {
    from_port = 0
    to_port   = 65535
    protocol  = "tcp"
    security_groups = [aws_security_group.backend_sg.id]
  }

  egress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

    tags = {
      Name = "ecs-security-group"
    }
}

resource "aws_lb" "movies_alb" {
  name               = "movies-alb"
  load_balancer_type = "application"
  subnets            = aws_subnet.public[*].id
  security_groups    = [aws_security_group.backend_sg.id]
}

resource "aws_lb_target_group" "frontend" {
  port        = 80
  protocol    = "HTTP"
  vpc_id      = aws_vpc.vpc_for_postgres.id
  target_type = "ip"
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.movies_alb.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }
}

resource "aws_lb_target_group" "backend" {
  port        = 5000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.vpc_for_postgres.id
  target_type = "ip"
}

resource "aws_lb_listener_rule" "api" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 10

  condition {
    path_pattern {
      values = ["/api/*"]
    }
  }

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }
}

resource "aws_ecs_cluster" "movies_cluster" {
  name = "movies-cluster"
}

data "aws_iam_policy_document" "ecs_task_execution_assume_role_policy" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "ecs_execution_role" {
  name               = "ecsTaskExecutionRole"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_execution_assume_role_policy.json
}

data "aws_iam_policy" "ecs_task_execution_policy" {
  arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy_attachment" "attach_ecs_task_execution_policy" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = data.aws_iam_policy.ecs_task_execution_policy.arn
}

resource "aws_ecs_task_definition" "backend" {
  family                   = "backend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.backend_cpu
  memory                   = var.backend_memory
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn

  lifecycle {
    ignore_changes = [container_definitions]
  }

  container_definitions = jsonencode([
    {
      name  = "backend"
      # We need to use a dummy image first since the actual image is built and pushed outside of Terraform
      image = "public.ecr.aws/nginx/nginx:latest"
      portMappings = [{ containerPort = 5000 }]
      environment = [
        {
          name  = "PG_HOST"
          value = aws_db_instance.postgres_instance.address
        },
        {
          name  = "PG_PORT"
          value = tostring(aws_db_instance.postgres_instance.port)
        },
        {
          name  = "PG_DATABASE"
          value = var.pg_database
        },
        {
          name  = "PG_USER"
          value = var.pg_user
        },
        {
          name  = "PG_PASSWORD"
          value = var.pg_password
        }
      ]
    }
  ])
}

resource "aws_ecs_task_definition" "frontend" {
  family                   = "frontend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.frontend_cpu
  memory                   = var.frontend_memory
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn

  lifecycle {
    ignore_changes = [container_definitions]
  }

  container_definitions = jsonencode([
    {
      name  = "frontend"
      image = "public.ecr.aws/nginx/nginx:latest"
      portMappings = [{ containerPort = 80 }]
    }
  ])
}

resource "aws_ecs_service" "backend" {
  name            = "backend"
  cluster         = aws_ecs_cluster.movies_cluster.id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = aws_subnet.private[*].id
    security_groups = [aws_security_group.ecs_sg.id]
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.backend.arn
    container_name   = "backend"
    container_port   = 5000
  }
}

resource "aws_ecs_service" "frontend" {
  name            = "frontend"
  cluster         = aws_ecs_cluster.movies_cluster.id
  task_definition = aws_ecs_task_definition.frontend.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = aws_subnet.public[*].id
    security_groups = [aws_security_group.ecs_sg.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.frontend.arn
    container_name   = "frontend"
    container_port   = 80
  }
}

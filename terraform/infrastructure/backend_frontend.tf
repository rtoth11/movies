resource "aws_subnet" "private" {
  count                   = var.deploy_backend_and_frontend ? length(var.subnets_cidr) : 0
  vpc_id                  = aws_vpc.movies_vpc.id
  cidr_block              = cidrsubnet(aws_vpc.movies_vpc.cidr_block, 8, count.index + 10)
  availability_zone       = var.azs[count.index]
  map_public_ip_on_launch = false
  tags = {
    Name = "private-subnet-${count.index + 1}"
  }
}

resource "aws_security_group" "alb_sg" {
  count = var.deploy_backend_and_frontend ? 1 : 0
  name   = "alb-sg"
  vpc_id = aws_vpc.movies_vpc.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = {
    Name = "backend-security-group"
  }
}

resource "aws_security_group" "ecs_sg" {
  count = var.deploy_backend_and_frontend ? 1 : 0
  name   = "ecs-tasks-sg"
  vpc_id = aws_vpc.movies_vpc.id

  ingress {
    from_port       = 5000
    to_port         = 5000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb_sg[0].id]
  }

  ingress {
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.alb_sg[0].id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "ecs-security-group"
  }
}

resource "aws_lb" "movies_alb" {
  count = var.deploy_backend_and_frontend ? 1 : 0
  name               = "movies-alb"
  load_balancer_type = "application"
  subnets            = aws_subnet.public[*].id
  security_groups    = [aws_security_group.alb_sg[0].id]
}

resource "aws_lb_target_group" "frontend" {
  count = var.deploy_backend_and_frontend ? 1 : 0
  port        = 80
  protocol    = "HTTP"
  vpc_id      = aws_vpc.movies_vpc.id
  target_type = "ip"
}

resource "aws_lb_listener" "http" {
  count = var.deploy_backend_and_frontend ? 1 : 0
  load_balancer_arn = aws_lb.movies_alb[0].arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend[0].arn
  }
}

resource "aws_lb_target_group" "backend" {
  count = var.deploy_backend_and_frontend ? 1 : 0
  port        = 5000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.movies_vpc.id
  target_type = "ip"

  health_check {
    path                = "/api/health"
    matcher             = "200"
  }
}

resource "aws_lb_listener_rule" "api" {
  count = var.deploy_backend_and_frontend ? 1 : 0
  listener_arn = aws_lb_listener.http[0].arn
  priority     = 10

  condition {
    path_pattern {
      values = ["/api/*"]
    }
  }

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend[0].arn
  }
}

resource "aws_ecs_cluster" "movies_cluster" {
  count = var.deploy_backend_and_frontend ? 1 : 0
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
  count = var.deploy_backend_and_frontend ? 1 : 0
  name               = "ecsTaskExecutionRole"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_execution_assume_role_policy.json
}

data "aws_iam_policy" "ecs_task_execution_policy" {
  arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy_attachment" "attach_ecs_task_execution_policy" {
  count = var.deploy_backend_and_frontend ? 1 : 0
  role       = aws_iam_role.ecs_execution_role[0].name
  policy_arn = data.aws_iam_policy.ecs_task_execution_policy.arn
}

resource "aws_cloudwatch_log_group" "movies_backend" {
  count = var.deploy_backend_and_frontend ? 1 : 0
  name              = "/ecs/movies-backend"
  retention_in_days = 30
}

resource "aws_ecs_task_definition" "backend" {
  count = var.deploy_backend_and_frontend ? 1 : 0
  family                   = "backend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.backend_cpu
  memory                   = var.backend_memory
  execution_role_arn       = aws_iam_role.ecs_execution_role[0].arn

  lifecycle {
    ignore_changes = [container_definitions]
  }

  container_definitions = jsonencode([
    {
      name  = "backend"
      image = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.region}.amazonaws.com/flask-placeholder:latest"
      portMappings = [{ containerPort = 5000 }]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.movies_backend[0].name
          "awslogs-region"        = var.region
          "awslogs-stream-prefix" = "ecs"
        }
      }
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

resource "aws_cloudwatch_log_group" "movies_frontend" {
  count = var.deploy_backend_and_frontend ? 1 : 0
  name              = "/ecs/movies-frontend"
  retention_in_days = 30
}

resource "aws_ecs_task_definition" "frontend" {
  count = var.deploy_backend_and_frontend ? 1 : 0
  family                   = "frontend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.frontend_cpu
  memory                   = var.frontend_memory
  execution_role_arn       = aws_iam_role.ecs_execution_role[0].arn

  lifecycle {
    ignore_changes = [container_definitions]
  }

  container_definitions = jsonencode([
    {
      name  = "frontend"
      image = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.region}.amazonaws.com/nginx:latest"
      portMappings = [{ containerPort = 80 }]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.movies_frontend[0].name
          "awslogs-region"        = var.region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "backend" {
  count = var.deploy_backend_and_frontend ? 1 : 0
  name            = "backend"
  cluster         = aws_ecs_cluster.movies_cluster[0].id
  task_definition = aws_ecs_task_definition.backend[0].arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = aws_subnet.private[*].id
    security_groups = [aws_security_group.ecs_sg[0].id]
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.backend[0].arn
    container_name   = "backend"
    container_port   = 5000
  }
}

resource "aws_ecs_service" "frontend" {
  count = var.deploy_backend_and_frontend ? 1 : 0
  name            = "frontend"
  cluster         = aws_ecs_cluster.movies_cluster[0].id
  task_definition = aws_ecs_task_definition.frontend[0].arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = aws_subnet.private[*].id
    security_groups = [aws_security_group.ecs_sg[0].id]
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.frontend[0].arn
    container_name   = "frontend"
    container_port   = 80
  }
}

resource "aws_route_table" "private_route_table" {
  count = var.deploy_backend_and_frontend ? 1 : 0
  vpc_id = aws_vpc.movies_vpc.id

  tags = {
    Name = "private-route-table"
  }
}

resource "aws_route_table_association" "private_association" {
  count          = var.deploy_backend_and_frontend ? length(aws_subnet.private) : 0
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private_route_table[0].id
}

module "fck-nat" {
  count = var.deploy_backend_and_frontend ? 1 : 0
  source = "git::https://github.com/RaJiska/terraform-aws-fck-nat.git"

  name                 = "movies-nat"
  vpc_id               = aws_vpc.movies_vpc.id
  subnet_id            = aws_subnet.public[0].id
  instance_type        = "t2.micro"

  update_route_tables = true

  route_tables_ids = {
    private = aws_route_table.private_route_table[0].id
  }
}

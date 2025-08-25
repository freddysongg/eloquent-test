locals {
  service_name = "${var.service_name}-${var.environment}"
}

# App Runner VPC Connector for private subnet access
resource "aws_apprunner_vpc_connector" "main" {
  vpc_connector_name = "${local.service_name}-vpc-connector"
  subnets            = var.private_subnet_ids
  security_groups    = [aws_security_group.app_runner.id]

  tags = {
    Name        = "${local.service_name}-vpc-connector"
    Environment = var.environment
  }
}

# Security group for App Runner service
resource "aws_security_group" "app_runner" {
  name_prefix = "${local.service_name}-"
  vpc_id      = var.vpc_id
  description = "Security group for App Runner service"

  # Outbound rules for external services
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS outbound for external APIs"
  }

  egress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP outbound"
  }

  # Database access (PostgreSQL)
  egress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "PostgreSQL database access"
  }

  # Redis access
  egress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
    description = "Redis cluster access"
  }

  # DNS resolution
  egress {
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "DNS resolution"
  }

  tags = {
    Name        = "${local.service_name}-sg"
    Environment = var.environment
  }
}

# App Runner service
resource "aws_apprunner_service" "main" {
  service_name = local.service_name

  source_configuration {
    image_repository {
      image_identifier      = var.image_uri
      image_configuration {
        port = "8000"

        runtime_environment_variables = var.environment_variables

        runtime_environment_secrets = var.environment_secrets
      }
      image_repository_type = "ECR_PUBLIC"
    }
    auto_deployments_enabled = false
  }

  instance_configuration {
    cpu    = var.app_runner_cpu
    memory = var.app_runner_memory

    instance_role_arn = aws_iam_role.app_runner_instance.arn
  }

  health_check_configuration {
    healthy_threshold   = var.health_check.healthy_threshold
    interval            = var.health_check.interval
    path                = var.health_check.path
    protocol            = var.health_check.protocol
    timeout             = var.health_check.timeout
    unhealthy_threshold = var.health_check.unhealthy_threshold
  }

  auto_scaling_configuration_arn = aws_apprunner_auto_scaling_configuration_version.main.arn

  network_configuration {
    egress_configuration {
      egress_type       = "VPC"
      vpc_connector_arn = aws_apprunner_vpc_connector.main.arn
    }
  }

  tags = {
    Name        = local.service_name
    Environment = var.environment
  }
}

# Auto-scaling configuration
resource "aws_apprunner_auto_scaling_configuration_version" "main" {
  auto_scaling_configuration_name = "${local.service_name}-auto-scaling"

  max_concurrency = var.auto_scaling_config.max_concurrency
  max_size        = var.auto_scaling_config.max_size
  min_size        = var.auto_scaling_config.min_size

  tags = {
    Name        = "${local.service_name}-auto-scaling"
    Environment = var.environment
  }
}

# IAM role for App Runner instance
resource "aws_iam_role" "app_runner_instance" {
  name = "${local.service_name}-instance-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "tasks.apprunner.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Environment = var.environment
  }
}

# IAM policy for App Runner instance
resource "aws_iam_role_policy" "app_runner_instance" {
  name = "${local.service_name}-instance-policy"
  role = aws_iam_role.app_runner_instance.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters"
        ]
        Resource = "*"
      }
    ]
  })
}

# IAM role for App Runner service
resource "aws_iam_role" "app_runner_access" {
  name = "${local.service_name}-access-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "build.apprunner.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Environment = var.environment
  }
}

# Attach the App Runner service policy
resource "aws_iam_role_policy_attachment" "app_runner_access" {
  role       = aws_iam_role.app_runner_access.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess"
}

# CloudWatch Log Group for App Runner
resource "aws_cloudwatch_log_group" "app_runner" {
  name              = "/aws/apprunner/${local.service_name}/application"
  retention_in_days = 30

  tags = {
    Environment = var.environment
  }
}

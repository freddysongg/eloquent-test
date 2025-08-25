locals {
  cluster_name = "${var.cluster_id}-${var.environment}"
}

# ElastiCache subnet group
resource "aws_elasticache_subnet_group" "main" {
  name       = "${local.cluster_name}-subnet-group"
  subnet_ids = var.private_subnet_ids

  tags = {
    Name        = "${local.cluster_name}-subnet-group"
    Environment = var.environment
  }
}

# Security group for ElastiCache
resource "aws_security_group" "redis" {
  name_prefix = "${local.cluster_name}-redis-"
  vpc_id      = var.vpc_id
  description = "Security group for ElastiCache Redis cluster"

  # Redis access from App Runner and other services in VPC
  ingress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
    description = "Redis access from VPC"
  }

  # No outbound rules needed for Redis
  tags = {
    Name        = "${local.cluster_name}-redis-sg"
    Environment = var.environment
  }
}

# ElastiCache parameter group for Redis 7.x
resource "aws_elasticache_parameter_group" "redis" {
  family = "redis7"
  name   = "${local.cluster_name}-params"

  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }

  parameter {
    name  = "timeout"
    value = "300"
  }

  tags = {
    Environment = var.environment
  }
}

# ElastiCache Redis cluster
resource "aws_elasticache_replication_group" "redis" {
  replication_group_id       = local.cluster_name
  description                = "Redis cluster for ${var.environment} environment"

  node_type                  = var.node_type
  port                      = 6379
  parameter_group_name      = aws_elasticache_parameter_group.redis.name

  num_cache_clusters         = var.num_cache_nodes

  engine                    = "redis"
  engine_version            = "7.0"

  subnet_group_name         = aws_elasticache_subnet_group.main.name
  security_group_ids        = [aws_security_group.redis.id]

  # High availability configuration
  automatic_failover_enabled = var.num_cache_nodes > 1
  multi_az_enabled           = var.num_cache_nodes > 1

  # Backup configuration
  snapshot_retention_limit   = var.environment == "production" ? 7 : 1
  snapshot_window           = "03:00-05:00"  # UTC
  maintenance_window        = "sun:05:00-sun:06:00"  # UTC

  # Security
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true

  # Logging
  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.redis_slow.name
    destination_type = "cloudwatch-logs"
    log_format      = "text"
    log_type        = "slow-log"
  }

  tags = {
    Name        = local.cluster_name
    Environment = var.environment
  }
}

# CloudWatch Log Group for Redis slow logs
resource "aws_cloudwatch_log_group" "redis_slow" {
  name              = "/aws/elasticache/redis/${local.cluster_name}/slow-log"
  retention_in_days = 7

  tags = {
    Environment = var.environment
  }
}

# CloudWatch alarms for Redis
resource "aws_cloudwatch_metric_alarm" "redis_cpu" {
  alarm_name          = "${local.cluster_name}-cpu-utilization"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ElastiCache"
  period              = "120"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors redis cpu utilization"

  dimensions = {
    CacheClusterId = "${local.cluster_name}-001"
  }

  tags = {
    Environment = var.environment
  }
}

resource "aws_cloudwatch_metric_alarm" "redis_memory" {
  alarm_name          = "${local.cluster_name}-memory-utilization"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "DatabaseMemoryUsagePercentage"
  namespace           = "AWS/ElastiCache"
  period              = "120"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors redis memory utilization"

  dimensions = {
    CacheClusterId = "${local.cluster_name}-001"
  }

  tags = {
    Environment = var.environment
  }
}

resource "aws_cloudwatch_metric_alarm" "redis_connections" {
  alarm_name          = "${local.cluster_name}-connection-count"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CurrConnections"
  namespace           = "AWS/ElastiCache"
  period              = "120"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors redis connection count"

  dimensions = {
    CacheClusterId = "${local.cluster_name}-001"
  }

  tags = {
    Environment = var.environment
  }
}

locals {
  dashboard_name = "EloquentAI-${var.environment}"
}

# CloudWatch Dashboard
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = local.dashboard_name

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/AppRunner", "RequestCount", "ServiceName", var.app_runner_service_name],
            [".", "ActiveInstances", ".", "."],
            [".", "2xxStatusResponses", ".", "."],
            [".", "4xxStatusResponses", ".", "."],
            [".", "5xxStatusResponses", ".", "."]
          ]
          period = 300
          stat   = "Sum"
          region = data.aws_region.current.name
          title  = "App Runner Metrics"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/AppRunner", "ResponseTime", "ServiceName", var.app_runner_service_name],
            [".", "CPUUtilization", ".", "."],
            [".", "MemoryUtilization", ".", "."]
          ]
          period = 300
          stat   = "Average"
          region = data.aws_region.current.name
          title  = "App Runner Performance"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/ElastiCache", "CPUUtilization", "CacheClusterId", "${var.redis_cluster_id}-001"],
            [".", "DatabaseMemoryUsagePercentage", ".", "."],
            [".", "CurrConnections", ".", "."],
            [".", "GetTypeCmds", ".", "."],
            [".", "SetTypeCmds", ".", "."]
          ]
          period = 300
          stat   = "Average"
          region = data.aws_region.current.name
          title  = "Redis Metrics"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/ElastiCache", "CacheHitRate", "CacheClusterId", "${var.redis_cluster_id}-001"],
            [".", "CacheMissRate", ".", "."],
            [".", "KeyspaceHits", ".", "."],
            [".", "KeyspaceMisses", ".", "."]
          ]
          period = 300
          stat   = "Average"
          region = data.aws_region.current.name
          title  = "Redis Cache Performance"
        }
      }
    ]
  })
}

# CloudWatch Alarms for App Runner
resource "aws_cloudwatch_metric_alarm" "app_runner_high_cpu" {
  alarm_name          = "${var.environment}-app-runner-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "3"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/AppRunner"
  period              = "300"
  statistic           = "Average"
  threshold           = var.alerts.cpu_threshold
  alarm_description   = "App Runner CPU utilization is too high"
  alarm_actions       = var.sns_topic_arn != "" ? [var.sns_topic_arn] : []

  dimensions = {
    ServiceName = var.app_runner_service_name
  }

  tags = {
    Environment = var.environment
  }
}

resource "aws_cloudwatch_metric_alarm" "app_runner_high_memory" {
  alarm_name          = "${var.environment}-app-runner-high-memory"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "3"
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/AppRunner"
  period              = "300"
  statistic           = "Average"
  threshold           = var.alerts.memory_threshold
  alarm_description   = "App Runner memory utilization is too high"
  alarm_actions       = var.sns_topic_arn != "" ? [var.sns_topic_arn] : []

  dimensions = {
    ServiceName = var.app_runner_service_name
  }

  tags = {
    Environment = var.environment
  }
}

resource "aws_cloudwatch_metric_alarm" "app_runner_high_error_rate" {
  alarm_name          = "${var.environment}-app-runner-high-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "5xxStatusResponses"
  namespace           = "AWS/AppRunner"
  period              = "300"
  statistic           = "Sum"
  threshold           = var.alerts.error_rate_threshold
  alarm_description   = "App Runner 5xx error rate is too high"
  alarm_actions       = var.sns_topic_arn != "" ? [var.sns_topic_arn] : []
  treat_missing_data  = "notBreaching"

  dimensions = {
    ServiceName = var.app_runner_service_name
  }

  tags = {
    Environment = var.environment
  }
}

resource "aws_cloudwatch_metric_alarm" "app_runner_high_response_time" {
  alarm_name          = "${var.environment}-app-runner-high-response-time"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "3"
  metric_name         = "ResponseTime"
  namespace           = "AWS/AppRunner"
  period              = "300"
  statistic           = "Average"
  threshold           = "5000"  # 5 seconds
  alarm_description   = "App Runner response time is too high"
  alarm_actions       = var.sns_topic_arn != "" ? [var.sns_topic_arn] : []

  dimensions = {
    ServiceName = var.app_runner_service_name
  }

  tags = {
    Environment = var.environment
  }
}

# SNS Topic for alerts (optional)
resource "aws_sns_topic" "alerts" {
  count = var.create_sns_topic ? 1 : 0
  name  = "eloquent-ai-${var.environment}-alerts"

  tags = {
    Environment = var.environment
  }
}

resource "aws_sns_topic_subscription" "email" {
  count     = var.create_sns_topic && var.alert_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.alerts[0].arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# CloudWatch Log Groups for centralized logging
resource "aws_cloudwatch_log_group" "application" {
  name              = "/aws/eloquent-ai/${var.environment}/application"
  retention_in_days = var.environment == "production" ? 30 : 7

  tags = {
    Environment = var.environment
    LogType     = "application"
  }
}

resource "aws_cloudwatch_log_group" "access" {
  name              = "/aws/eloquent-ai/${var.environment}/access"
  retention_in_days = var.environment == "production" ? 30 : 7

  tags = {
    Environment = var.environment
    LogType     = "access"
  }
}

# Log Insights queries for common troubleshooting
resource "aws_cloudwatch_query_definition" "error_analysis" {
  name = "EloquentAI-${var.environment}-Error-Analysis"

  log_group_names = [
    aws_cloudwatch_log_group.application.name
  ]

  query_string = <<EOF
fields @timestamp, @message, level, error, correlation_id
| filter level = "ERROR"
| sort @timestamp desc
| limit 100
EOF
}

resource "aws_cloudwatch_query_definition" "performance_analysis" {
  name = "EloquentAI-${var.environment}-Performance-Analysis"

  log_group_names = [
    aws_cloudwatch_log_group.application.name
  ]

  query_string = <<EOF
fields @timestamp, @message, response_time_ms, endpoint, method
| filter response_time_ms > 1000
| sort response_time_ms desc
| limit 50
EOF
}

# Data sources
data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

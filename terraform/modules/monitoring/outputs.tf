output "dashboard_url" {
  description = "CloudWatch dashboard URL"
  value       = "https://console.aws.amazon.com/cloudwatch/home?region=${data.aws_region.current.name}#dashboards:name=${local.dashboard_name}"
}

output "sns_topic_arn" {
  description = "SNS topic ARN for alerts"
  value       = var.create_sns_topic ? aws_sns_topic.alerts[0].arn : ""
}

output "log_group_application" {
  description = "Application log group name"
  value       = aws_cloudwatch_log_group.application.name
}

output "log_group_access" {
  description = "Access log group name"
  value       = aws_cloudwatch_log_group.access.name
}

output "alarm_arns" {
  description = "List of CloudWatch alarm ARNs"
  value = [
    aws_cloudwatch_metric_alarm.app_runner_high_cpu.arn,
    aws_cloudwatch_metric_alarm.app_runner_high_memory.arn,
    aws_cloudwatch_metric_alarm.app_runner_high_error_rate.arn,
    aws_cloudwatch_metric_alarm.app_runner_high_response_time.arn
  ]
}

output "service_arn" {
  description = "ARN of the App Runner service"
  value       = aws_apprunner_service.main.arn
}

output "service_id" {
  description = "ID of the App Runner service"
  value       = aws_apprunner_service.main.service_id
}

output "service_url" {
  description = "URL of the App Runner service"
  value       = aws_apprunner_service.main.service_url
}

output "service_status" {
  description = "Status of the App Runner service"
  value       = aws_apprunner_service.main.status
}

output "vpc_connector_arn" {
  description = "ARN of the VPC connector"
  value       = aws_apprunner_vpc_connector.main.arn
}

output "security_group_id" {
  description = "ID of the security group"
  value       = aws_security_group.app_runner.id
}

output "instance_role_arn" {
  description = "ARN of the App Runner instance role"
  value       = aws_iam_role.app_runner_instance.arn
}

output "auto_scaling_configuration_arn" {
  description = "ARN of the auto-scaling configuration"
  value       = aws_apprunner_auto_scaling_configuration_version.main.arn
}

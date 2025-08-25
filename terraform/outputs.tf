output "vpc_id" {
  description = "ID of the VPC"
  value       = module.networking.vpc_id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = module.networking.private_subnet_ids
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = module.networking.public_subnet_ids
}

output "app_runner_service_url" {
  description = "URL of the App Runner service"
  value       = module.app_runner.service_url
}

output "app_runner_service_arn" {
  description = "ARN of the App Runner service"
  value       = module.app_runner.service_arn
}

output "redis_cluster_id" {
  description = "ElastiCache Redis cluster ID"
  value       = module.elasticache.cluster_id
}

output "redis_endpoint" {
  description = "ElastiCache Redis endpoint"
  value       = module.elasticache.redis_endpoint
  sensitive   = true
}

output "redis_url" {
  description = "Redis connection URL"
  value       = module.elasticache.redis_url
  sensitive   = true
}

output "api_gateway_url" {
  description = "API Gateway URL"
  value       = module.api_gateway.api_gateway_url
}

output "cloudwatch_dashboard_url" {
  description = "CloudWatch dashboard URL"
  value       = module.monitoring.dashboard_url
}

output "s3_static_assets_bucket" {
  description = "S3 bucket name for static assets"
  value       = aws_s3_bucket.static_assets.bucket
}

output "s3_backups_bucket" {
  description = "S3 bucket name for backups"
  value       = aws_s3_bucket.backups.bucket
}

output "deployment_summary" {
  description = "Deployment summary information"
  value = {
    environment     = var.environment
    region         = var.aws_region
    backend_url    = module.app_runner.service_url
    api_gateway    = module.api_gateway.api_gateway_url
    monitoring     = module.monitoring.dashboard_url
    redis_cluster  = module.elasticache.cluster_id
  }
}

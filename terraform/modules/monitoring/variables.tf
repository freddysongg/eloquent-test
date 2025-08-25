variable "environment" {
  description = "Environment name"
  type        = string
}

variable "app_runner_service" {
  description = "ARN of the App Runner service"
  type        = string
}

variable "app_runner_service_name" {
  description = "Name of the App Runner service"
  type        = string
  default     = ""
}

variable "redis_cluster_id" {
  description = "ElastiCache Redis cluster ID"
  type        = string
}

variable "alerts" {
  description = "Alert thresholds"
  type = object({
    cpu_threshold         = number
    memory_threshold      = number
    error_rate_threshold  = number
  })
  default = {
    cpu_threshold         = 70
    memory_threshold      = 80
    error_rate_threshold  = 5
  }
}

variable "sns_topic_arn" {
  description = "SNS topic ARN for alerts"
  type        = string
  default     = ""
}

variable "create_sns_topic" {
  description = "Whether to create an SNS topic for alerts"
  type        = bool
  default     = true
}

variable "alert_email" {
  description = "Email address for alerts"
  type        = string
  default     = ""
}

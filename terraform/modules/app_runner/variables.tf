variable "service_name" {
  description = "Name of the App Runner service"
  type        = string
}

variable "image_uri" {
  description = "URI of the Docker image"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID for the App Runner service"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block of the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for VPC connector"
  type        = list(string)
}

variable "app_runner_cpu" {
  description = "CPU units for App Runner"
  type        = string
  default     = "1 vCPU"
}

variable "app_runner_memory" {
  description = "Memory for App Runner"
  type        = string
  default     = "2 GB"
}

variable "auto_scaling_config" {
  description = "Auto-scaling configuration"
  type = object({
    max_concurrency = number
    max_size       = number
    min_size       = number
  })
  default = {
    max_concurrency = 100
    max_size       = 10
    min_size       = 1
  }
}

variable "health_check" {
  description = "Health check configuration"
  type = object({
    healthy_threshold    = number
    interval            = number
    path               = string
    protocol           = string
    timeout            = number
    unhealthy_threshold = number
  })
  default = {
    healthy_threshold    = 3
    interval            = 10
    path               = "/health"
    protocol           = "HTTP"
    timeout            = 5
    unhealthy_threshold = 5
  }
}

variable "environment_variables" {
  description = "Environment variables for the App Runner service"
  type        = map(string)
  default     = {}
}

variable "environment_secrets" {
  description = "Environment secrets for the App Runner service"
  type        = map(string)
  default     = {}
  sensitive   = true
}

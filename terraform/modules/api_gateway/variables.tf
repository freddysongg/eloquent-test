variable "name" {
  description = "Name of the API Gateway"
  type        = string
}

variable "backend_url" {
  description = "Backend URL to proxy requests to"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "rate_limits" {
  description = "Rate limiting configuration"
  type = object({
    global       = number
    authenticated = number
    anonymous    = number
    llm_calls    = number
  })
  default = {
    global       = 1000
    authenticated = 100
    anonymous    = 20
    llm_calls    = 10
  }
}

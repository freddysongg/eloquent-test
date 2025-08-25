# Production Environment Configuration
environment = "production"
aws_region  = "us-east-1"

# Networking
vpc_cidr = "10.0.0.0/16"
availability_zones = ["us-east-1a", "us-east-1b", "us-east-1c"]

# Container image URI (will be set by CI/CD)
backend_image_uri = "ghcr.io/eloquentai/backend:prod-latest"

# ElastiCache configuration
redis_node_type   = "cache.t3.small"  # Upgraded for production
redis_num_nodes   = 2                  # Multi-AZ for high availability

# App Runner configuration
app_runner_cpu    = "2 vCPU"
app_runner_memory = "4 GB"

# Security
enable_deletion_protection = true

# Backup retention
backup_retention_days = 30

# Monitoring
monitoring_email = ""  # Set this to your production monitoring email

# Application secrets (will be set via environment variables)
# These should NOT be set here - use environment variables in CI/CD
# database_url = "set-via-env-var"
# anthropic_api_key = "set-via-env-var"
# pinecone_api_key = "set-via-env-var"
# clerk_secret_key = "set-via-env-var"
# jwt_secret_key = "set-via-env-var"

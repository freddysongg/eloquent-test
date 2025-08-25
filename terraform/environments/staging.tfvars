# Staging Environment Configuration
environment = "staging"
aws_region  = "us-east-1"

# Networking
vpc_cidr = "10.1.0.0/16"
availability_zones = ["us-east-1a", "us-east-1b"]

# Container image URI (will be set by CI/CD)
backend_image_uri = "ghcr.io/eloquentai/backend:staging-latest"

# ElastiCache configuration
redis_node_type   = "cache.t3.micro"  # Smaller for staging
redis_num_nodes   = 1                  # Single node for cost optimization

# App Runner configuration
app_runner_cpu    = "1 vCPU"
app_runner_memory = "2 GB"

# Security
enable_deletion_protection = false

# Backup retention
backup_retention_days = 7

# Monitoring
monitoring_email = ""  # Set this to your staging monitoring email

# Application secrets (will be set via environment variables)
# These should NOT be set here - use environment variables in CI/CD
# database_url = "set-via-env-var"
# anthropic_api_key = "set-via-env-var"
# pinecone_api_key = "set-via-env-var"
# clerk_secret_key = "set-via-env-var"
# jwt_secret_key = "set-via-env-var"

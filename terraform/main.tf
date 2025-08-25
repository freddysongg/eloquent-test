terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket = "eloquent-ai-terraform-state"
    key    = "terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Environment = var.environment
      Project     = "eloquent-ai-chatbot"
      ManagedBy   = "terraform"
    }
  }
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Networking module
module "networking" {
  source = "./modules/networking"

  vpc_cidr           = var.vpc_cidr
  availability_zones = var.availability_zones
  environment        = var.environment
}

# App Runner module
module "app_runner" {
  source = "./modules/app_runner"

  service_name        = "eloquent-ai-backend"
  image_uri          = var.backend_image_uri
  vpc_id             = module.networking.vpc_id
  private_subnet_ids = module.networking.private_subnet_ids
  environment        = var.environment

  # Auto-scaling configuration
  auto_scaling_config = {
    max_concurrency = 100
    max_size       = 10
    min_size       = 1
  }

  # Health check configuration
  health_check = {
    healthy_threshold    = 3
    interval            = 10
    path               = "/health"
    protocol           = "HTTP"
    timeout            = 5
    unhealthy_threshold = 5
  }

  # Environment variables
  environment_variables = {
    DATABASE_URL     = var.database_url
    REDIS_URL        = module.elasticache.redis_url
    ANTHROPIC_API_KEY = var.anthropic_api_key
    PINECONE_API_KEY = var.pinecone_api_key
    CLERK_SECRET_KEY = var.clerk_secret_key
    JWT_SECRET_KEY   = var.jwt_secret_key
    ENVIRONMENT      = var.environment
    LOG_LEVEL        = var.environment == "production" ? "WARNING" : "INFO"
    ENABLE_DOCS      = var.environment == "production" ? "false" : "true"
  }
}

# ElastiCache module
module "elasticache" {
  source = "./modules/elasticache"

  cluster_id           = "eloquent-ai-redis"
  node_type           = var.redis_node_type
  num_cache_nodes     = var.redis_num_nodes
  vpc_id              = module.networking.vpc_id
  private_subnet_ids  = module.networking.private_subnet_ids
  environment         = var.environment

  # Multi-AZ deployment
  availability_zones = var.availability_zones
}

# Monitoring module
module "monitoring" {
  source = "./modules/monitoring"

  environment          = var.environment
  app_runner_service  = module.app_runner.service_arn
  redis_cluster_id    = module.elasticache.cluster_id

  # Alert configuration
  alerts = {
    cpu_threshold    = 70
    memory_threshold = 80
    error_rate_threshold = 5
  }
}

# API Gateway module
module "api_gateway" {
  source = "./modules/api_gateway"

  name               = "eloquent-ai-api"
  backend_url        = module.app_runner.service_url
  environment        = var.environment

  # Rate limiting configuration
  rate_limits = {
    global       = 1000
    authenticated = 100
    anonymous    = 20
    llm_calls    = 10
  }
}

# S3 bucket for static assets and backups
resource "aws_s3_bucket" "static_assets" {
  bucket = "eloquent-ai-${var.environment}-assets"

  tags = {
    Name        = "EloquentAI Static Assets"
    Environment = var.environment
  }
}

resource "aws_s3_bucket" "backups" {
  bucket = "eloquent-ai-${var.environment}-backups"

  tags = {
    Name        = "EloquentAI Backups"
    Environment = var.environment
  }
}

# S3 bucket configurations
resource "aws_s3_bucket_versioning" "static_assets" {
  bucket = aws_s3_bucket.static_assets.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_versioning" "backups" {
  bucket = aws_s3_bucket.backups.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "static_assets" {
  bucket = aws_s3_bucket.static_assets.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Block public access to S3 buckets
resource "aws_s3_bucket_public_access_block" "static_assets" {
  bucket = aws_s3_bucket.static_assets.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "backups" {
  bucket = aws_s3_bucket.backups.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

#!/bin/bash

# Terraform Deployment Script for EloquentAI
# Usage: ./deploy.sh [environment] [action]
# Example: ./deploy.sh production plan
#          ./deploy.sh staging apply

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="${1:-staging}"
ACTION="${2:-plan}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Validate inputs
if [[ ! "$ENVIRONMENT" =~ ^(staging|production)$ ]]; then
    echo -e "${RED}Error: Environment must be 'staging' or 'production'${NC}"
    exit 1
fi

if [[ ! "$ACTION" =~ ^(init|plan|apply|destroy|output|validate)$ ]]; then
    echo -e "${RED}Error: Action must be one of: init, plan, apply, destroy, output, validate${NC}"
    exit 1
fi

# Set variables
TFVARS_FILE="environments/${ENVIRONMENT}.tfvars"
STATE_KEY="terraform-${ENVIRONMENT}.tfstate"

echo -e "${BLUE}EloquentAI Infrastructure Deployment${NC}"
echo -e "${BLUE}====================================${NC}"
echo -e "Environment: ${GREEN}${ENVIRONMENT}${NC}"
echo -e "Action:      ${GREEN}${ACTION}${NC}"
echo -e "Config:      ${GREEN}${TFVARS_FILE}${NC}"
echo ""

# Check if tfvars file exists
if [ ! -f "$TFVARS_FILE" ]; then
    echo -e "${RED}Error: Configuration file $TFVARS_FILE not found${NC}"
    exit 1
fi

# Required environment variables check
required_vars=(
    "DATABASE_URL"
    "ANTHROPIC_API_KEY"
    "PINECONE_API_KEY"
    "CLERK_SECRET_KEY"
    "JWT_SECRET_KEY"
)

missing_vars=()
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -ne 0 ] && [ "$ACTION" = "apply" ]; then
    echo -e "${RED}Error: Missing required environment variables:${NC}"
    for var in "${missing_vars[@]}"; do
        echo -e "${RED}  - $var${NC}"
    done
    echo ""
    echo -e "${YELLOW}Please set these environment variables before running 'apply'${NC}"
    if [ "$ACTION" != "plan" ] && [ "$ACTION" != "validate" ]; then
        exit 1
    fi
fi

# Initialize Terraform (always run to ensure latest providers)
echo -e "${BLUE}Initializing Terraform...${NC}"
terraform init \
    -backend-config="key=${STATE_KEY}" \
    -upgrade

# Select or create workspace
echo -e "${BLUE}Selecting workspace: ${ENVIRONMENT}${NC}"
terraform workspace select "$ENVIRONMENT" 2>/dev/null || {
    echo -e "${YELLOW}Creating new workspace: ${ENVIRONMENT}${NC}"
    terraform workspace new "$ENVIRONMENT"
}

# Export Terraform variables from environment
export TF_VAR_database_url="${DATABASE_URL}"
export TF_VAR_anthropic_api_key="${ANTHROPIC_API_KEY}"
export TF_VAR_pinecone_api_key="${PINECONE_API_KEY}"
export TF_VAR_clerk_secret_key="${CLERK_SECRET_KEY}"
export TF_VAR_jwt_secret_key="${JWT_SECRET_KEY}"

# Execute the requested action
case $ACTION in
    "init")
        echo -e "${GREEN}Terraform initialization completed${NC}"
        ;;
    "validate")
        echo -e "${BLUE}Validating Terraform configuration...${NC}"
        terraform validate
        echo -e "${GREEN}Terraform configuration is valid${NC}"
        ;;
    "plan")
        echo -e "${BLUE}Creating Terraform plan...${NC}"
        terraform plan \
            -var-file="$TFVARS_FILE" \
            -out="tfplan-${ENVIRONMENT}.out"
        echo -e "${GREEN}Terraform plan created successfully${NC}"
        echo -e "${YELLOW}Review the plan above before applying${NC}"
        ;;
    "apply")
        # Check if a plan file exists
        if [ -f "tfplan-${ENVIRONMENT}.out" ]; then
            echo -e "${BLUE}Applying Terraform plan...${NC}"
            terraform apply "tfplan-${ENVIRONMENT}.out"
        else
            echo -e "${YELLOW}No plan file found, creating and applying plan...${NC}"
            terraform apply \
                -var-file="$TFVARS_FILE" \
                -auto-approve
        fi
        echo -e "${GREEN}Terraform apply completed successfully${NC}"

        # Show important outputs
        echo -e "${BLUE}Deployment Summary:${NC}"
        terraform output -json deployment_summary | jq -r '
            "Environment:     \(.environment)",
            "Region:          \(.region)",
            "Backend URL:     \(.backend_url)",
            "API Gateway:     \(.api_gateway)",
            "Monitoring:      \(.monitoring)",
            "Redis Cluster:   \(.redis_cluster)"
        '
        ;;
    "destroy")
        echo -e "${RED}WARNING: This will destroy all infrastructure in ${ENVIRONMENT}${NC}"
        read -p "Are you sure? Type 'yes' to confirm: " -r
        if [[ $REPLY = "yes" ]]; then
            terraform destroy \
                -var-file="$TFVARS_FILE" \
                -auto-approve
            echo -e "${GREEN}Infrastructure destroyed${NC}"
        else
            echo -e "${YELLOW}Destruction cancelled${NC}"
        fi
        ;;
    "output")
        echo -e "${BLUE}Terraform outputs:${NC}"
        terraform output
        ;;
esac

echo -e "${GREEN}Operation completed successfully${NC}"

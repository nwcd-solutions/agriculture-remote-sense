#!/bin/bash
# Deploy all infrastructure stacks in the correct order
# Usage: ./deploy-all.sh [environment]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT=${1:-dev}
AWS_REGION=${AWS_REGION:-us-west-2}

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deploying Satellite GIS Infrastructure${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Environment:${NC} $ENVIRONMENT"
echo -e "${BLUE}AWS Region:${NC} $AWS_REGION"
echo ""

# Function to print colored messages
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_section() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# Check prerequisites
print_section "Checking Prerequisites"

if ! command -v aws &> /dev/null; then
    print_error "AWS CLI not found. Please install AWS CLI."
    exit 1
fi
print_info "AWS CLI installed"

if ! command -v npx &> /dev/null; then
    print_error "npx not found. Please install Node.js and npm."
    exit 1
fi
print_info "Node.js and npm installed"

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    print_error "AWS credentials not configured. Please run 'aws configure'."
    exit 1
fi
print_info "AWS credentials configured"

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
print_info "AWS Account ID: $ACCOUNT_ID"

# Build TypeScript
print_section "Building TypeScript"
npm run build
print_info "TypeScript build completed"

# Deployment order
STACKS=(
    "SatelliteGis-Network-${ENVIRONMENT}"
    "SatelliteGis-Storage-${ENVIRONMENT}"
    "SatelliteGis-Database-${ENVIRONMENT}"
    "SatelliteGis-Batch-${ENVIRONMENT}"
    "SatelliteGis-Api-${ENVIRONMENT}"
    "SatelliteGis-Frontend-${ENVIRONMENT}"
    "SatelliteGis-Monitoring-${ENVIRONMENT}"
)

# Deploy each stack
for STACK in "${STACKS[@]}"; do
    print_section "Deploying $STACK"
    
    if npx cdk deploy "$STACK" --require-approval never --context environment="$ENVIRONMENT"; then
        print_info "$STACK deployed successfully"
    else
        print_error "Failed to deploy $STACK"
        exit 1
    fi
done

print_section "Deployment Complete!"

echo ""
print_info "All stacks deployed successfully!"
echo ""
echo -e "${GREEN}Next Steps:${NC}"
echo "  1. Check API endpoint: aws cloudformation describe-stacks --stack-name SatelliteGis-Api-$ENVIRONMENT --query 'Stacks[0].Outputs'"
echo "  2. Test API health: curl \$(aws cloudformation describe-stacks --stack-name SatelliteGis-Api-$ENVIRONMENT --query 'Stacks[0].Outputs[?OutputKey==\`ApiUrl\`].OutputValue' --output text)/api/health"
echo ""
echo -e "${GREEN}========================================${NC}"

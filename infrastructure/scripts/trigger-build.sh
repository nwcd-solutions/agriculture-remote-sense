#!/bin/bash
# Script to manually trigger CodeBuild projects
# Usage: ./trigger-build.sh [api|batch|both] [environment]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
BUILD_TYPE=${1:-both}
ENVIRONMENT=${2:-dev}
AWS_REGION=${AWS_REGION:-us-west-2}

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Satellite GIS - Trigger Build${NC}"
echo -e "${GREEN}========================================${NC}"
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

print_success() {
    echo -e "${BLUE}[SUCCESS]${NC} $1"
}

# Validate build type
if [[ ! "$BUILD_TYPE" =~ ^(api|batch|both)$ ]]; then
    print_error "Invalid build type: $BUILD_TYPE"
    echo "Usage: $0 [api|batch|both] [environment]"
    exit 1
fi

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|prod)$ ]]; then
    print_error "Invalid environment: $ENVIRONMENT"
    echo "Usage: $0 [api|batch|both] [environment]"
    exit 1
fi

print_info "Build Type: $BUILD_TYPE"
print_info "Environment: $ENVIRONMENT"
print_info "AWS Region: $AWS_REGION"
echo ""

# Function to trigger a build
trigger_build() {
    local project_name=$1
    local build_name=$2
    
    print_info "Triggering build for $build_name..."
    
    # Start the build
    BUILD_ID=$(aws codebuild start-build \
        --project-name "$project_name" \
        --region "$AWS_REGION" \
        --query 'build.id' \
        --output text)
    
    if [ $? -eq 0 ]; then
        print_success "Build started successfully!"
        print_info "Build ID: $BUILD_ID"
        print_info "Project: $project_name"
        echo ""
        
        # Print CloudWatch logs URL
        LOGS_URL="https://${AWS_REGION}.console.aws.amazon.com/codesuite/codebuild/projects/${project_name}/build/${BUILD_ID}?region=${AWS_REGION}"
        print_info "View build logs:"
        echo "  $LOGS_URL"
        echo ""
        
        return 0
    else
        print_error "Failed to start build for $build_name"
        return 1
    fi
}

# Function to wait for build completion
wait_for_build() {
    local build_id=$1
    local build_name=$2
    
    print_info "Waiting for $build_name to complete..."
    
    while true; do
        BUILD_STATUS=$(aws codebuild batch-get-builds \
            --ids "$build_id" \
            --region "$AWS_REGION" \
            --query 'builds[0].buildStatus' \
            --output text)
        
        case "$BUILD_STATUS" in
            "SUCCEEDED")
                print_success "$build_name completed successfully!"
                return 0
                ;;
            "FAILED"|"FAULT"|"TIMED_OUT"|"STOPPED")
                print_error "$build_name failed with status: $BUILD_STATUS"
                return 1
                ;;
            "IN_PROGRESS")
                echo -n "."
                sleep 10
                ;;
            *)
                echo -n "."
                sleep 10
                ;;
        esac
    done
}

# Trigger builds based on type
case "$BUILD_TYPE" in
    "api")
        PROJECT_NAME="satellite-gis-api-build"
        trigger_build "$PROJECT_NAME" "API Container"
        ;;
    
    "batch")
        PROJECT_NAME="satellite-gis-batch-build"
        trigger_build "$PROJECT_NAME" "Batch Container"
        ;;
    
    "both")
        PROJECT_NAME="satellite-gis-combined-build"
        trigger_build "$PROJECT_NAME" "Both Containers"
        ;;
esac

echo ""
print_info "Build triggered successfully!"
echo ""
print_info "To check build status, run:"
echo "  aws codebuild batch-get-builds --ids <BUILD_ID> --region $AWS_REGION"
echo ""
print_info "To view logs in real-time, run:"
echo "  aws logs tail /aws/codebuild/$PROJECT_NAME --follow --region $AWS_REGION"
echo ""

echo -e "${GREEN}========================================${NC}"
print_success "Done!"
echo -e "${GREEN}========================================${NC}"

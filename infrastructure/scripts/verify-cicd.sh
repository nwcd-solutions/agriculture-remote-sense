#!/bin/bash
# Script to verify CI/CD infrastructure deployment
# Usage: ./verify-cicd.sh [environment]

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
PROJECT_NAME="satellite-gis"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}CI/CD Infrastructure Verification${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Environment:${NC} $ENVIRONMENT"
echo -e "${BLUE}AWS Region:${NC} $AWS_REGION"
echo ""

# Function to print colored messages
print_info() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_section() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# Check AWS CLI
print_section "Checking Prerequisites"

if ! command -v aws &> /dev/null; then
    print_error "AWS CLI not found. Please install AWS CLI."
    exit 1
fi
print_info "AWS CLI installed"

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    print_error "AWS credentials not configured. Please run 'aws configure'."
    exit 1
fi
print_info "AWS credentials configured"

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
print_info "AWS Account ID: $ACCOUNT_ID"

# Check CodeBuild projects
print_section "Checking CodeBuild Projects"

API_PROJECT="${PROJECT_NAME}-api-build"
BATCH_PROJECT="${PROJECT_NAME}-batch-build"
COMBINED_PROJECT="${PROJECT_NAME}-combined-build"

check_codebuild_project() {
    local project_name=$1
    if aws codebuild batch-get-projects --names "$project_name" --region "$AWS_REGION" &> /dev/null; then
        print_info "CodeBuild project exists: $project_name"
        return 0
    else
        print_error "CodeBuild project not found: $project_name"
        return 1
    fi
}

check_codebuild_project "$API_PROJECT"
API_EXISTS=$?

check_codebuild_project "$BATCH_PROJECT"
BATCH_EXISTS=$?

check_codebuild_project "$COMBINED_PROJECT"
COMBINED_EXISTS=$?

# Check ECR repositories
print_section "Checking ECR Repositories"

API_REPO="${PROJECT_NAME}-api-${ENVIRONMENT}"
BATCH_REPO="${PROJECT_NAME}-batch-${ENVIRONMENT}"

check_ecr_repository() {
    local repo_name=$1
    if aws ecr describe-repositories --repository-names "$repo_name" --region "$AWS_REGION" &> /dev/null; then
        print_info "ECR repository exists: $repo_name"
        
        # Check for images
        IMAGE_COUNT=$(aws ecr list-images --repository-name "$repo_name" --region "$AWS_REGION" --query 'length(imageIds)' --output text)
        if [ "$IMAGE_COUNT" -gt 0 ]; then
            print_info "  └─ Contains $IMAGE_COUNT image(s)"
        else
            print_warn "  └─ No images found (run a build to populate)"
        fi
        return 0
    else
        print_error "ECR repository not found: $repo_name"
        return 1
    fi
}

check_ecr_repository "$API_REPO"
API_REPO_EXISTS=$?

check_ecr_repository "$BATCH_REPO"
BATCH_REPO_EXISTS=$?

# Check SNS topic
print_section "Checking SNS Notification Topic"

SNS_TOPIC="${PROJECT_NAME}-build-notifications"
if aws sns list-topics --region "$AWS_REGION" | grep -q "$SNS_TOPIC"; then
    print_info "SNS topic exists: $SNS_TOPIC"
    
    # Check subscriptions
    TOPIC_ARN=$(aws sns list-topics --region "$AWS_REGION" --query "Topics[?contains(TopicArn, '$SNS_TOPIC')].TopicArn" --output text)
    SUB_COUNT=$(aws sns list-subscriptions-by-topic --topic-arn "$TOPIC_ARN" --region "$AWS_REGION" --query 'length(Subscriptions)' --output text)
    
    if [ "$SUB_COUNT" -gt 0 ]; then
        print_info "  └─ Has $SUB_COUNT subscription(s)"
    else
        print_warn "  └─ No subscriptions (configure email notifications)"
    fi
else
    print_error "SNS topic not found: $SNS_TOPIC"
fi

# Check CloudWatch log groups
print_section "Checking CloudWatch Log Groups"

check_log_group() {
    local project_name=$1
    local log_group="/aws/codebuild/$project_name"
    
    if aws logs describe-log-groups --log-group-name-prefix "$log_group" --region "$AWS_REGION" | grep -q "$log_group"; then
        print_info "Log group exists: $log_group"
        return 0
    else
        print_warn "Log group not found: $log_group (will be created on first build)"
        return 1
    fi
}

check_log_group "$API_PROJECT"
check_log_group "$BATCH_PROJECT"
check_log_group "$COMBINED_PROJECT"

# Check IAM roles
print_section "Checking IAM Roles"

check_iam_role() {
    local project_name=$1
    local role_pattern="SatelliteGis-Cicd-${ENVIRONMENT}.*${project_name}"
    
    if aws iam list-roles --region "$AWS_REGION" | grep -q "$role_pattern"; then
        print_info "IAM role exists for: $project_name"
        return 0
    else
        print_warn "IAM role not found for: $project_name"
        return 1
    fi
}

check_iam_role "ApiBuildProject"
check_iam_role "BatchBuildProject"
check_iam_role "CombinedBuildProject"

# Check build history
print_section "Checking Build History"

check_build_history() {
    local project_name=$1
    
    BUILD_COUNT=$(aws codebuild list-builds-for-project --project-name "$project_name" --region "$AWS_REGION" --query 'length(ids)' --output text 2>/dev/null || echo "0")
    
    if [ "$BUILD_COUNT" -gt 0 ]; then
        print_info "$project_name: $BUILD_COUNT build(s) executed"
        
        # Get latest build status
        LATEST_BUILD=$(aws codebuild list-builds-for-project --project-name "$project_name" --region "$AWS_REGION" --max-items 1 --query 'ids[0]' --output text 2>/dev/null)
        
        if [ -n "$LATEST_BUILD" ] && [ "$LATEST_BUILD" != "None" ]; then
            BUILD_STATUS=$(aws codebuild batch-get-builds --ids "$LATEST_BUILD" --region "$AWS_REGION" --query 'builds[0].buildStatus' --output text 2>/dev/null)
            
            if [ "$BUILD_STATUS" == "SUCCEEDED" ]; then
                print_info "  └─ Latest build: ${GREEN}SUCCEEDED${NC}"
            elif [ "$BUILD_STATUS" == "FAILED" ]; then
                print_error "  └─ Latest build: FAILED"
            else
                print_warn "  └─ Latest build: $BUILD_STATUS"
            fi
        fi
    else
        print_warn "$project_name: No builds executed yet"
    fi
}

if [ $API_EXISTS -eq 0 ]; then
    check_build_history "$API_PROJECT"
fi

if [ $BATCH_EXISTS -eq 0 ]; then
    check_build_history "$BATCH_PROJECT"
fi

if [ $COMBINED_EXISTS -eq 0 ]; then
    check_build_history "$COMBINED_PROJECT"
fi

# Summary
print_section "Verification Summary"

TOTAL_CHECKS=0
PASSED_CHECKS=0

# Count checks
if [ $API_EXISTS -eq 0 ]; then ((PASSED_CHECKS++)); fi
((TOTAL_CHECKS++))

if [ $BATCH_EXISTS -eq 0 ]; then ((PASSED_CHECKS++)); fi
((TOTAL_CHECKS++))

if [ $COMBINED_EXISTS -eq 0 ]; then ((PASSED_CHECKS++)); fi
((TOTAL_CHECKS++))

if [ $API_REPO_EXISTS -eq 0 ]; then ((PASSED_CHECKS++)); fi
((TOTAL_CHECKS++))

if [ $BATCH_REPO_EXISTS -eq 0 ]; then ((PASSED_CHECKS++)); fi
((TOTAL_CHECKS++))

echo ""
echo -e "${BLUE}Checks Passed:${NC} $PASSED_CHECKS / $TOTAL_CHECKS"
echo ""

if [ $PASSED_CHECKS -eq $TOTAL_CHECKS ]; then
    print_info "All checks passed! CI/CD infrastructure is properly configured."
    echo ""
    echo -e "${GREEN}Next Steps:${NC}"
    echo "  1. Trigger a build: ./trigger-build.sh both $ENVIRONMENT"
    echo "  2. Monitor build: aws logs tail /aws/codebuild/$COMBINED_PROJECT --follow"
    echo "  3. Verify images: aws ecr list-images --repository-name $API_REPO"
    echo ""
    exit 0
else
    print_warn "Some checks failed. Please review the output above."
    echo ""
    echo -e "${YELLOW}Troubleshooting:${NC}"
    echo "  1. Ensure CI/CD stack is deployed: cdk deploy SatelliteGis-Cicd-$ENVIRONMENT"
    echo "  2. Check CloudFormation stack status"
    echo "  3. Review stack outputs: aws cloudformation describe-stacks --stack-name SatelliteGis-Cicd-$ENVIRONMENT"
    echo ""
    exit 1
fi

#!/bin/bash
# Build and Push Script for Satellite GIS API Docker Image
# Usage: ./build-and-push.sh [version] [ecr-repository]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
VERSION=${1:-latest}
ECR_REPO=${2:-}
AWS_REGION=${AWS_REGION:-us-west-2}
IMAGE_NAME="satellite-gis-api"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Satellite GIS API - Build and Push${NC}"
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

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker daemon is not running. Please start Docker and try again."
    exit 1
fi

print_info "Docker daemon is running"

# Build the image
print_info "Building Docker image: ${IMAGE_NAME}:${VERSION}"
docker build -t ${IMAGE_NAME}:${VERSION} .

if [ $? -eq 0 ]; then
    print_info "Build successful!"
else
    print_error "Build failed!"
    exit 1
fi

# Get image size
IMAGE_SIZE=$(docker images ${IMAGE_NAME}:${VERSION} --format "{{.Size}}")
print_info "Image size: ${IMAGE_SIZE}"

# Tag as latest if version is not latest
if [ "$VERSION" != "latest" ]; then
    print_info "Tagging as latest..."
    docker tag ${IMAGE_NAME}:${VERSION} ${IMAGE_NAME}:latest
fi

# Push to ECR if repository is provided
if [ -n "$ECR_REPO" ]; then
    print_info "Pushing to ECR repository: ${ECR_REPO}"
    
    # Extract account ID from ECR repo URL
    if [[ $ECR_REPO =~ ([0-9]+)\.dkr\.ecr\. ]]; then
        ACCOUNT_ID="${BASH_REMATCH[1]}"
        print_info "AWS Account ID: ${ACCOUNT_ID}"
    else
        print_error "Invalid ECR repository URL format"
        exit 1
    fi
    
    # Login to ECR
    print_info "Logging in to ECR..."
    aws ecr get-login-password --region ${AWS_REGION} | \
        docker login --username AWS --password-stdin ${ECR_REPO}
    
    if [ $? -ne 0 ]; then
        print_error "ECR login failed!"
        exit 1
    fi
    
    # Tag for ECR
    ECR_IMAGE="${ECR_REPO}:${VERSION}"
    print_info "Tagging image for ECR: ${ECR_IMAGE}"
    docker tag ${IMAGE_NAME}:${VERSION} ${ECR_IMAGE}
    
    # Push to ECR
    print_info "Pushing to ECR..."
    docker push ${ECR_IMAGE}
    
    if [ $? -eq 0 ]; then
        print_info "Successfully pushed to ECR!"
        print_info "Image URI: ${ECR_IMAGE}"
    else
        print_error "Push to ECR failed!"
        exit 1
    fi
    
    # Also push latest tag if version is not latest
    if [ "$VERSION" != "latest" ]; then
        ECR_LATEST="${ECR_REPO}:latest"
        print_info "Tagging and pushing latest..."
        docker tag ${IMAGE_NAME}:${VERSION} ${ECR_LATEST}
        docker push ${ECR_LATEST}
    fi
else
    print_warn "No ECR repository provided. Skipping push to ECR."
    print_info "To push to ECR, run:"
    print_info "  ./build-and-push.sh ${VERSION} <account-id>.dkr.ecr.${AWS_REGION}.amazonaws.com/${IMAGE_NAME}"
fi

echo ""
print_info "Done!"
echo -e "${GREEN}========================================${NC}"

# Print summary
echo ""
echo "Summary:"
echo "  Local Image: ${IMAGE_NAME}:${VERSION}"
echo "  Image Size: ${IMAGE_SIZE}"
if [ -n "$ECR_REPO" ]; then
    echo "  ECR Image: ${ECR_REPO}:${VERSION}"
fi
echo ""
echo "To run locally:"
echo "  docker run -p 8000:8000 ${IMAGE_NAME}:${VERSION}"
echo ""
echo "To run with environment variables:"
echo "  docker run -p 8000:8000 \\"
echo "    -e AWS_REGION=${AWS_REGION} \\"
echo "    -e BATCH_JOB_QUEUE=your-queue \\"
echo "    -e BATCH_JOB_DEFINITION=your-job-def \\"
echo "    -e BATCH_S3_BUCKET=your-bucket \\"
echo "    ${IMAGE_NAME}:${VERSION}"
echo ""

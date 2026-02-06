#!/bin/bash
# Build Lambda Layer with boto3 using Docker for compatibility
# Use stable boto3 version to ensure DynamoDB resource definitions are complete

set -e

echo "Building Lambda Layer using Docker..."

# Clean up old layer
rm -rf lambda-layer
mkdir -p lambda-layer/python

# Use Docker to build in Lambda-compatible environment
# Install specific boto3 version that is known to work
docker run --rm \
  -v "$PWD":/var/task \
  --entrypoint /bin/bash \
  public.ecr.aws/lambda/python:3.11 \
  -c "pip install boto3==1.34.0 botocore==1.34.0 -t /var/task/lambda-layer/python --no-cache-dir"

echo "Lambda Layer built successfully at lambda-layer/"
echo "Size: $(du -sh lambda-layer | cut -f1)"

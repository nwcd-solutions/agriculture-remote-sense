#!/bin/bash
# Build Lambda Layer with minimal dependencies using Docker for compatibility
# Standalone version - no app modules needed

set -e

echo "Building Lambda Layer using Docker..."

# Clean up old layer
rm -rf lambda-layer
mkdir -p lambda-layer/python

# Use Docker to build in Lambda-compatible environment
# Only install boto3 (other dependencies are built-in or inlined)
docker run --rm \
  -v "$PWD":/var/task \
  --entrypoint /bin/bash \
  public.ecr.aws/lambda/python:3.11 \
  -c "pip install boto3>=1.34.0 -t /var/task/lambda-layer/python --upgrade"

echo "Lambda Layer built successfully at lambda-layer/"
echo "Size: $(du -sh lambda-layer | cut -f1)"

#!/bin/bash
# Build Lambda Layer with minimal dependencies using Docker for compatibility

set -e

echo "Building Lambda Layer using Docker..."

# Clean up old layer
rm -rf lambda-layer
mkdir -p lambda-layer/python

# Use Docker to build in Lambda-compatible environment
docker run --rm \
  -v "$PWD":/var/task \
  --entrypoint /bin/bash \
  public.ecr.aws/lambda/python:3.11 \
  -c "pip install -r /var/task/requirements-lambda.txt -t /var/task/lambda-layer/python --upgrade"

# Copy only necessary app modules (without heavy dependencies)
mkdir -p lambda-layer/python/app/models
mkdir -p lambda-layer/python/app/services

# Copy models
cp -r app/models/*.py lambda-layer/python/app/models/

# Copy only lightweight services needed by Lambda
cp app/services/__init__.py lambda-layer/python/app/services/
cp app/services/batch_job_manager.py lambda-layer/python/app/services/
cp app/services/task_repository.py lambda-layer/python/app/services/
cp app/services/s3_storage_service.py lambda-layer/python/app/services/

# Copy app __init__.py
cp app/__init__.py lambda-layer/python/app/

echo "Lambda Layer built successfully at lambda-layer/"
echo "Size: $(du -sh lambda-layer | cut -f1)"

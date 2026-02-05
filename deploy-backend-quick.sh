#!/bin/bash

set -e

echo "快速部署后端 API..."

# 构建 Docker 镜像
echo "1. 构建 Docker 镜像..."
docker build -t satellite-gis-api:latest -f backend/Dockerfile backend/

# 获取 ECR 仓库 URI
ECR_REPO=$(aws ecr describe-repositories --repository-names satellite-gis-api-dev --region us-east-1 --query 'repositories[0].repositoryUri' --output text)

echo "2. ECR 仓库: $ECR_REPO"

# 登录 ECR
echo "3. 登录 ECR..."
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $ECR_REPO

# 标记镜像
echo "4. 标记镜像..."
docker tag satellite-gis-api:latest $ECR_REPO:latest

# 推送镜像
echo "5. 推送镜像到 ECR..."
docker push $ECR_REPO:latest

# 强制 ECS 服务重新部署
echo "6. 更新 ECS 服务..."
aws ecs update-service \
  --cluster satellite-gis-api-dev \
  --service satellite-gis-api-dev \
  --force-new-deployment \
  --region us-east-1 \
  --query 'service.serviceName' \
  --output text

echo "✅ 部署完成！服务正在重新启动..."

#!/bin/bash

# 更新 ECS 任务定义的 CORS 环境变量

TASK_FAMILY="satellite-gis-api-dev"
REGION="us-east-1"

# 获取当前任务定义
TASK_DEF=$(aws ecs describe-task-definition \
  --task-definition $TASK_FAMILY \
  --region $REGION \
  --query 'taskDefinition' \
  --output json)

# 提取需要的字段并添加 CORS_ORIGINS
NEW_TASK_DEF=$(echo $TASK_DEF | jq '
  .containerDefinitions[0].environment += [
    {
      "name": "CORS_ORIGINS",
      "value": "http://localhost:3000,https://dev.dfjse3jyewuby.amplifyapp.com,https://main.dfjse3jyewuby.amplifyapp.com"
    }
  ] |
  {
    family: .family,
    taskRoleArn: .taskRoleArn,
    executionRoleArn: .executionRoleArn,
    networkMode: .networkMode,
    containerDefinitions: .containerDefinitions,
    volumes: .volumes,
    placementConstraints: .placementConstraints,
    requiresCompatibilities: .requiresCompatibilities,
    cpu: .cpu,
    memory: .memory
  }
')

# 注册新的任务定义
echo "注册新的任务定义..."
NEW_REVISION=$(aws ecs register-task-definition \
  --cli-input-json "$NEW_TASK_DEF" \
  --region $REGION \
  --query 'taskDefinition.revision' \
  --output text)

echo "新任务定义版本: $NEW_REVISION"

# 更新服务使用新的任务定义
echo "更新 ECS 服务..."
aws ecs update-service \
  --cluster satellite-gis-api-dev \
  --service satellite-gis-api-dev \
  --task-definition ${TASK_FAMILY}:${NEW_REVISION} \
  --force-new-deployment \
  --region $REGION \
  --query 'service.serviceName' \
  --output text

echo "完成！服务正在重新部署..."

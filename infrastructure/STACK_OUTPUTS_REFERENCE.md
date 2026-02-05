# Stack 输出值快速参考

## 快速访问链接

### 🌐 前端应用
```
https://dev.dfjse3jyewuby.amplifyapp.com
```

### 🔌 API 服务
```
http://satellite-gis-alb-dev-674728147.us-east-1.elb.amazonaws.com
```

### 📊 监控仪表板
```
https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=SatelliteGis-dev
```

## 环境变量配置

### 前端 (.env.production)
```bash
REACT_APP_API_URL=http://satellite-gis-alb-dev-674728147.us-east-1.elb.amazonaws.com
REACT_APP_ENVIRONMENT=dev
```

### 后端 (API Service)
```bash
AWS_REGION=us-east-1
DYNAMODB_TABLE_NAME=ProcessingTasks-dev
S3_RESULTS_BUCKET=satellite-gis-results-dev-880755836258
BATCH_JOB_QUEUE=satellite-gis-queue-dev
BATCH_JOB_DEFINITION=arn:aws:batch:us-east-1:880755836258:job-definition/satellite-gis-processor-dev:2
```

### Batch 处理器
```bash
AWS_REGION=us-east-1
DYNAMODB_TABLE_NAME=ProcessingTasks-dev
S3_RESULTS_BUCKET=satellite-gis-results-dev-880755836258
```

## AWS 资源 ARN

### DynamoDB
```
arn:aws:dynamodb:us-east-1:880755836258:table/ProcessingTasks-dev
```

### S3 Bucket
```
arn:aws:s3:::satellite-gis-results-dev-880755836258
```

### Batch Job Queue
```
arn:aws:batch:us-east-1:880755836258:job-queue/satellite-gis-queue-dev
```

### Batch Job Definition
```
arn:aws:batch:us-east-1:880755836258:job-definition/satellite-gis-processor-dev:2
```

### SNS Alarm Topic
```
arn:aws:sns:us-east-1:880755836258:satellite-gis-alarms-dev
```

### ECR Repository
```
880755836258.dkr.ecr.us-east-1.amazonaws.com/satellite-gis-batch-dev
```

## 网络配置

### VPC
```
vpc-036772a85897d2abb
```

### 安全组
```
API:      sg-005d47cdb4d88aa5a
Batch:    sg-036ae7c488adea657
Database: sg-0c953f3ccd5a593cb
```

### 子网
```
Public Subnets:
  - subnet-0eb5d9bad4839ab20
  - subnet-0ce47e64a4a71a85b

Private Subnets:
  - subnet-0f4e28d9a05e4e004
  - subnet-06bd88009d99e1543
```

## 常用 AWS CLI 命令

### 查看 API 日志
```bash
aws logs tail /ecs/satellite-gis-api-dev --follow
```

### 查看 Batch 任务
```bash
aws batch list-jobs --job-queue satellite-gis-queue-dev --job-status RUNNING
```

### 查看 DynamoDB 表
```bash
aws dynamodb scan --table-name ProcessingTasks-dev --limit 10
```

### 查看 S3 存储桶内容
```bash
aws s3 ls s3://satellite-gis-results-dev-880755836258/
```

### 查看 Amplify 应用
```bash
aws amplify get-app --app-id dfjse3jyewuby
```

### 订阅告警通知
```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:880755836258:satellite-gis-alarms-dev \
  --protocol email \
  --notification-endpoint your-email@example.com
```

## API 端点测试

### Health Check
```bash
curl http://satellite-gis-alb-dev-674728147.us-east-1.elb.amazonaws.com/health
```

### 验证 AOI
```bash
curl -X POST http://satellite-gis-alb-dev-674728147.us-east-1.elb.amazonaws.com/api/aoi/validate \
  -H "Content-Type: application/json" \
  -d '{
    "aoi": {
      "type": "Polygon",
      "coordinates": [[[-122.5, 37.5], [-122.5, 37.6], [-122.4, 37.6], [-122.4, 37.5], [-122.5, 37.5]]]
    }
  }'
```

### 查询卫星数据
```bash
curl -X POST http://satellite-gis-alb-dev-674728147.us-east-1.elb.amazonaws.com/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "satellite": "sentinel-2",
    "product_level": "L2A",
    "date_range": {
      "start": "2024-01-01",
      "end": "2024-12-31"
    },
    "aoi": {
      "type": "Polygon",
      "coordinates": [[[-122.5, 37.5], [-122.5, 37.6], [-122.4, 37.6], [-122.4, 37.5], [-122.5, 37.5]]]
    },
    "cloud_cover_max": 20
  }'
```

### 提交处理任务
```bash
curl -X POST http://satellite-gis-alb-dev-674728147.us-east-1.elb.amazonaws.com/api/process/indices \
  -H "Content-Type: application/json" \
  -d '{
    "image_id": "test-image",
    "indices": ["NDVI"],
    "aoi": {
      "type": "Polygon",
      "coordinates": [[[-122.5, 37.5], [-122.5, 37.6], [-122.4, 37.6], [-122.4, 37.5], [-122.5, 37.5]]]
    },
    "band_urls": {
      "red": "https://example.com/red.tif",
      "nir": "https://example.com/nir.tif"
    }
  }'
```

### 查询任务状态
```bash
curl http://satellite-gis-alb-dev-674728147.us-east-1.elb.amazonaws.com/api/process/tasks/{task_id}
```

### 列出所有任务
```bash
curl http://satellite-gis-alb-dev-674728147.us-east-1.elb.amazonaws.com/api/process/tasks
```

## Amplify 部署命令

### 连接代码仓库（通过 Console）
1. 访问: https://console.aws.amazon.com/amplify/home?region=us-east-1#/dfjse3jyewuby
2. 点击 "Connect branch"
3. 选择 GitHub/GitLab/Bitbucket
4. 授权并选择仓库
5. 选择分支: dev
6. 保存并部署

### 手动部署（使用 CLI）
```bash
# 安装 Amplify CLI
npm install -g @aws-amplify/cli

# 构建前端
cd frontend
npm install
npm run build

# 部署
amplify publish --appId dfjse3jyewuby --branchName dev
```

## 监控和告警

### CloudWatch 仪表板
- **URL**: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=SatelliteGis-dev
- **指标**: API CPU/内存、Batch 任务、DynamoDB 容量

### 告警规则
- API CPU > 80%
- API 内存 > 80%
- Batch 失败 > 5 个
- DynamoDB 错误 > 10 个

### 查看告警
```bash
aws cloudwatch describe-alarms --alarm-name-prefix satellite-gis
```

## 成本监控

### 查看当月成本
```bash
aws ce get-cost-and-usage \
  --time-period Start=2026-02-01,End=2026-02-28 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --filter file://cost-filter.json
```

### 成本过滤器 (cost-filter.json)
```json
{
  "Tags": {
    "Key": "Project",
    "Values": ["SatelliteGIS"]
  }
}
```

## 清理资源

### 删除单个 Stack
```bash
npx cdk destroy SatelliteGis-Monitoring-dev
npx cdk destroy SatelliteGis-Frontend-dev
npx cdk destroy SatelliteGis-Api-dev
npx cdk destroy SatelliteGis-Batch-dev
npx cdk destroy SatelliteGis-Database-dev
npx cdk destroy SatelliteGis-Storage-dev
npx cdk destroy SatelliteGis-Network-dev
```

### 删除所有 Stack
```bash
npx cdk destroy --all
```

### 清理 ECR 镜像
```bash
aws ecr batch-delete-image \
  --repository-name satellite-gis-batch-dev \
  --image-ids imageTag=latest
```

### 清理 S3 存储桶
```bash
aws s3 rm s3://satellite-gis-results-dev-880755836258/ --recursive
```

## 故障排除

### API 服务不响应
```bash
# 检查 ECS 任务
aws ecs describe-services \
  --cluster satellite-gis-api-dev \
  --services satellite-gis-api-dev

# 查看任务日志
aws logs tail /ecs/satellite-gis-api-dev --follow

# 检查 ALB 健康检查
aws elbv2 describe-target-health \
  --target-group-arn <target-group-arn>
```

### Batch 任务失败
```bash
# 查看任务详情
aws batch describe-jobs --jobs <job-id>

# 查看日志
aws logs tail /aws/batch/job --follow

# 检查计算环境
aws batch describe-compute-environments \
  --compute-environments satellite-gis-compute-dev
```

### DynamoDB 访问错误
```bash
# 检查表状态
aws dynamodb describe-table --table-name ProcessingTasks-dev

# 测试读写
aws dynamodb put-item \
  --table-name ProcessingTasks-dev \
  --item '{"task_id": {"S": "test-123"}}'

aws dynamodb get-item \
  --table-name ProcessingTasks-dev \
  --key '{"task_id": {"S": "test-123"}}'
```

### Amplify 构建失败
```bash
# 查看构建日志
aws amplify list-jobs --app-id dfjse3jyewuby --branch-name dev

# 获取特定构建日志
aws amplify get-job \
  --app-id dfjse3jyewuby \
  --branch-name dev \
  --job-id <job-id>
```

## 更新部署

### 更新单个 Stack
```bash
npx cdk deploy SatelliteGis-Api-dev
```

### 更新所有 Stack
```bash
npx cdk deploy --all
```

### 仅查看变更（不部署）
```bash
npx cdk diff SatelliteGis-Api-dev
```

## 备份和恢复

### 备份 DynamoDB 表
```bash
aws dynamodb create-backup \
  --table-name ProcessingTasks-dev \
  --backup-name ProcessingTasks-dev-backup-$(date +%Y%m%d)
```

### 导出 S3 数据
```bash
aws s3 sync s3://satellite-gis-results-dev-880755836258/ ./backup/
```

### 导出 CloudFormation 模板
```bash
aws cloudformation get-template \
  --stack-name SatelliteGis-Api-dev \
  --query TemplateBody \
  --output text > api-stack-backup.yaml
```

## 安全最佳实践

### 启用 MFA 删除（S3）
```bash
aws s3api put-bucket-versioning \
  --bucket satellite-gis-results-dev-880755836258 \
  --versioning-configuration Status=Enabled,MFADelete=Enabled \
  --mfa "arn:aws:iam::880755836258:mfa/root-account-mfa-device XXXXXX"
```

### 启用访问日志
```bash
aws s3api put-bucket-logging \
  --bucket satellite-gis-results-dev-880755836258 \
  --bucket-logging-status file://logging.json
```

### 审计 IAM 权限
```bash
aws iam get-role --role-name <role-name>
aws iam list-attached-role-policies --role-name <role-name>
```

## 性能优化

### 启用 DynamoDB Auto Scaling
```bash
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/ProcessingTasks-dev \
  --scalable-dimension dynamodb:table:ReadCapacityUnits \
  --min-capacity 1 \
  --max-capacity 10
```

### 配置 CloudFront 缓存（Amplify 自动配置）
- 已通过 Amplify 自动配置全球 CDN
- 缓存策略: 优化的缓存策略
- 压缩: 启用

### 优化 ECS 任务
```bash
# 更新任务定义以增加资源
aws ecs update-service \
  --cluster satellite-gis-api-dev \
  --service satellite-gis-api-dev \
  --desired-count 2
```

## 相关文档

- [部署状态报告](./DEPLOYMENT_STATUS.md)
- [Amplify 前端 README](./lib/stacks/AMPLIFY_FRONTEND_README.md)
- [Batch API 实现](./BATCH_API_IMPLEMENTATION.md)
- [部署指南](./DEPLOYMENT_GUIDE.md)
- [简化部署](./SIMPLE_DEPLOYMENT.md)

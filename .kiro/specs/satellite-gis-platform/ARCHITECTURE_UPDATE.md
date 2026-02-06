# 架构更新说明 (2026-02-06)

## 概述

本文档记录了从原始ECS/Fargate架构迁移到Lambda架构的变更，以及当前系统的实际实现状态。

## 架构变更

### 原架构 (设计文档)
- **API层**: ECS/Fargate + FastAPI
- **计算层**: AWS Batch + Docker容器
- **前端**: AWS Amplify

### 当前架构 (已实现)
- **API层**: API Gateway + Lambda函数 (Python 3.11)
- **计算层**: AWS Batch + Docker容器 (保持不变)
- **前端**: AWS Amplify (保持不变)

## Lambda API 架构

### 1. Lambda函数设计

系统采用**独立Lambda函数**架构，每个函数完全自包含，不依赖共享的app模块：

```
backend/
├── lambda_query.py      # 查询Lambda (独立)
├── lambda_process.py    # 处理Lambda (独立)
├── lambda_aoi.py        # AOI Lambda (独立)
├── lambda-layer/        # Lambda Layer (仅boto3)
│   └── python/
│       └── boto3/
└── app/                 # 原ECS代码 (保留但不使用)
```

#### Lambda函数特点

**1. Query Lambda** (`satellite-gis-query-dev`)
- **功能**: 查询卫星数据 (Sentinel-2, Sentinel-1, Landsat-8, MODIS)
- **依赖**: 无 (使用内置urllib)
- **内存**: 512MB
- **超时**: 30秒
- **代码**: 完全独立，所有逻辑内联

**2. Process Lambda** (`satellite-gis-process-dev`)
- **功能**: 
  - 提交Batch作业
  - 管理任务状态 (DynamoDB)
  - 查询Batch作业状态
  - 生成S3预签名URL
  - 任务列表查询 (分页、过滤)
- **依赖**: boto3 (通过Lambda Layer)
- **内存**: 512MB
- **超时**: 30秒
- **代码**: 完全独立，所有服务类内联 (BatchJobManager, TaskRepository, S3StorageService)

**3. AOI Lambda** (`satellite-gis-aoi-dev`)
- **功能**:
  - 验证GeoJSON几何
  - 计算面积 (球面公式)
  - 计算质心和边界
  - 解析上传的GeoJSON文件
- **依赖**: 无 (使用内置库)
- **内存**: 256MB
- **超时**: 15秒
- **代码**: 完全独立

### 2. Lambda Layer策略

**简化的Layer设计**:
- **内容**: 仅包含boto3 (~30MB)
- **构建**: 使用Docker确保二进制兼容性
- **使用**: 仅Process Lambda使用Layer

```bash
# 构建Lambda Layer
cd backend
./build-lambda-layer.sh

# 使用Docker构建
docker run --rm \
  -v "$PWD":/var/task \
  public.ecr.aws/lambda/python:3.11 \
  -c "pip install boto3>=1.34.0 -t /var/task/lambda-layer/python"
```

### 3. API Gateway配置

**REST API Gateway** (替代HTTP API):
- **认证**: API Key
- **速率限制**: 100 req/s, burst 200
- **配额**: 10,000 requests/day
- **CORS**: 允许所有来源
- **日志**: CloudWatch详细日志

**API端点**:
```
POST   /api/query                    # 查询卫星数据
POST   /api/process/indices          # 提交处理任务
GET    /api/process/tasks            # 列出所有任务
GET    /api/process/tasks/{task_id}  # 获取任务状态
DELETE /api/process/tasks/{task_id}  # 取消任务
POST   /api/aoi/validate             # 验证AOI
POST   /api/aoi/upload               # 上传GeoJSON
```

### 4. IAM权限配置

**Process Lambda权限**:
```typescript
// 分离的IAM策略
processFunction.addToRolePolicy({
  actions: ['batch:SubmitJob'],
  resources: [jobQueue, jobDefinition]
});

processFunction.addToRolePolicy({
  actions: ['batch:DescribeJobs', 'batch:TerminateJob', 'batch:ListJobs'],
  resources: ['*']  // 这些操作需要通配符
});

// DynamoDB和S3权限
tasksTable.grantReadWriteData(processFunction);
resultsBucket.grantReadWrite(processFunction);
```

## 数据流

### 查询流程
```
用户 → API Gateway → Query Lambda → STAC API → 返回结果
```

### 处理流程
```
用户 → API Gateway → Process Lambda
  ├─ 创建任务 (DynamoDB)
  ├─ 提交Batch作业
  └─ 返回task_id

用户轮询 → API Gateway → Process Lambda
  ├─ 查询DynamoDB
  ├─ 查询Batch状态
  ├─ 更新任务状态
  └─ 返回状态 + S3 URL
```

### Batch状态映射
```python
batch_to_task_status = {
    'SUBMITTED': 'queued',
    'PENDING': 'queued',
    'RUNNABLE': 'queued',
    'STARTING': 'running',
    'RUNNING': 'running',
    'SUCCEEDED': 'completed',
    'FAILED': 'failed'
}
```

## 关键实现细节

### 1. DynamoDB Float转换

**问题**: DynamoDB不支持float类型
**解决**: 使用Decimal转换

```python
def convert_floats_to_decimal(obj: Any) -> Any:
    if isinstance(obj, float):
        return Decimal(str(obj))  # 使用字符串保持精度
    # ... 递归处理dict和list
```

### 2. 错误处理

**Lambda函数错误处理**:
```python
def get_task_status(event):
    try:
        # ... 业务逻辑
        return {'statusCode': 200, 'body': json.dumps(result)}
    except ValueError as e:
        return {'statusCode': 404, 'body': json.dumps({'error': 'Task not found'})}
    except Exception as e:
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}
```

### 3. CORS配置

**统一的CORS头**:
```python
def cors_headers():
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Api-Key,Authorization',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }
```

## CDK Stack结构

### 当前Stacks (7个)

1. **Network Stack** - VPC, 子网, 安全组
2. **Storage Stack** - S3存储桶
3. **Database Stack** - DynamoDB表
4. **Batch Stack** - AWS Batch计算环境
5. **Lambda API Stack** - Lambda函数 + API Gateway (新)
6. **Frontend Stack** - AWS Amplify
7. **Monitoring Stack** - CloudWatch仪表板

### Lambda API Stack示例

```typescript
export class LambdaApiStack extends cdk.Stack {
  constructor(scope, id, props) {
    // Lambda Layer (仅boto3)
    const dependenciesLayer = new lambda.LayerVersion(this, 'DependenciesLayer', {
      code: lambda.Code.fromAsset('../backend/lambda-layer'),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_11],
    });

    // Query Lambda (无依赖)
    const queryFunction = new lambda.Function(this, 'QueryFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'lambda_query.handler',
      code: lambda.Code.fromAsset('../backend'),
      memorySize: 512,
      timeout: cdk.Duration.seconds(30),
    });

    // Process Lambda (使用Layer)
    const processFunction = new lambda.Function(this, 'ProcessFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'lambda_process.handler',
      code: lambda.Code.fromAsset('../backend'),
      layers: [dependenciesLayer],
      memorySize: 512,
      timeout: cdk.Duration.seconds(30),
      environment: {
        DYNAMODB_TABLE: tasksTable.tableName,
        S3_BUCKET: resultsBucket.bucketName,
        BATCH_JOB_QUEUE: batchJobQueue.jobQueueName,
        BATCH_JOB_DEFINITION: batchJobDefinition.jobDefinitionName,
      },
    });

    // REST API Gateway
    const restApi = new apigateway.RestApi(this, 'RestApi', {
      defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS,
        allowMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
      },
    });

    // API Key
    const apiKey = restApi.addApiKey('ApiKey');
    const usagePlan = restApi.addUsagePlan('UsagePlan', {
      throttle: { rateLimit: 100, burstLimit: 200 },
      quota: { limit: 10000, period: apigateway.Period.DAY },
    });
    usagePlan.addApiKey(apiKey);
  }
}
```

## 部署流程

### 简化的部署方式

**无需CI/CD流水线**:
- CDK使用 `ContainerImage.fromAsset` 从源代码构建Docker镜像
- CDK自动创建ECR仓库、构建镜像并推送
- Lambda函数代码直接从backend目录打包

**部署命令**:
```bash
# 在EC2上部署
cd infrastructure
npx cdk deploy SatelliteGis-Api-dev --exclusively --require-approval never

# 或部署所有stacks
npx cdk deploy --all --context env=dev
```

## 性能特点

### Lambda优势
- **冷启动**: 首次调用 ~1-2秒
- **热启动**: 后续调用 ~100-200ms
- **成本**: 按实际使用付费，空闲时无成本
- **扩展**: 自动扩展，无需管理服务器

### Batch优势
- **大规模计算**: 处理大型栅格数据
- **成本优化**: 使用Spot实例节省70%成本
- **隔离**: 每个任务独立容器，互不影响

## 监控和日志

### CloudWatch日志组
```
/aws/lambda/satellite-gis-query-dev
/aws/lambda/satellite-gis-process-dev
/aws/lambda/satellite-gis-aoi-dev
/aws/apigateway/satellite-gis-api-dev
/aws/batch/job
```

### 关键指标
- Lambda调用次数和错误率
- API Gateway请求数和延迟
- Batch作业成功/失败率
- DynamoDB读写容量

## 已知限制

### Lambda限制
- **执行时间**: 最长15分钟 (当前设置30秒)
- **内存**: 最大10GB (当前使用512MB)
- **包大小**: 250MB解压后 (当前~50MB)
- **并发**: 默认1000 (可申请提高)

### 解决方案
- 长时间处理 → 使用Batch
- 大型依赖 → 使用Lambda Layer或容器镜像
- 高并发 → 申请提高配额

## 迁移路径

### 从ECS迁移到Lambda的原因
1. **简化运维**: 无需管理ECS集群和任务定义
2. **降低成本**: 按实际使用付费，空闲时无成本
3. **自动扩展**: Lambda自动处理并发
4. **快速部署**: 代码更新无需重新构建容器

### 保留的组件
- **AWS Batch**: 用于大规模数据处理
- **DynamoDB**: 任务状态存储
- **S3**: 结果文件存储
- **Amplify**: 前端托管

## 未来优化

### 短期 (1-2个月)
- [ ] 实现Lambda预留并发 (减少冷启动)
- [ ] 添加CloudWatch告警
- [ ] 实现API响应缓存
- [ ] 优化Lambda内存配置

### 中期 (3-6个月)
- [ ] 迁移到Lambda容器镜像 (支持更大依赖)
- [ ] 实现Step Functions编排复杂工作流
- [ ] 添加X-Ray分布式追踪
- [ ] 实现多区域部署

## 参考资料

- [AWS Lambda最佳实践](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [API Gateway REST API](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-rest-api.html)
- [AWS Batch用户指南](https://docs.aws.amazon.com/batch/latest/userguide/)
- [DynamoDB最佳实践](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html)

---

**文档版本**: 1.0
**最后更新**: 2026-02-06
**维护者**: 开发团队

# AWS Amplify Frontend Stack

## 概述

Frontend Stack 已更新为使用 AWS Amplify 托管前端应用。Amplify 提供了完整的前端托管解决方案，包括：

- 自动构建和部署
- 全球 CDN 分发
- HTTPS 支持
- 自定义域名支持
- 分支预览
- 环境变量管理
- 自动缓存失效

## 架构

```
GitHub/GitLab/Bitbucket Repository
         ↓
    AWS Amplify
         ↓
   自动构建 (Node.js 18)
         ↓
   部署到全球 CDN
         ↓
   HTTPS 访问
```

## 部署步骤

### 1. 部署 Amplify Stack

```bash
cd infrastructure
npx cdk deploy SatelliteGis-Frontend-dev
```

这将创建：
- Amplify App
- Amplify Branch (dev/staging/main)
- IAM Role for Amplify
- 环境变量配置

### 2. 连接代码仓库

部署完成后，需要在 AWS Console 中连接代码仓库：

1. 打开 AWS Amplify Console
2. 找到创建的 App: `satellite-gis-dev`
3. 点击 "Connect branch"
4. 选择代码仓库提供商 (GitHub/GitLab/Bitbucket)
5. 授权 Amplify 访问仓库
6. 选择仓库和分支
7. 确认构建设置（已通过 CDK 配置）
8. 保存并部署

### 3. 手动部署（无代码仓库）

如果不想连接代码仓库，可以使用 Amplify CLI 手动部署：

```bash
# 安装 Amplify CLI
npm install -g @aws-amplify/cli

# 构建前端
cd frontend
npm install
npm run build

# 部署到 Amplify
cd ..
amplify publish --appId <AMPLIFY_APP_ID> --branchName dev
```

## 配置说明

### 环境变量

Amplify 会自动注入以下环境变量：

- `REACT_APP_API_URL`: API 服务的 URL
- `REACT_APP_ENVIRONMENT`: 环境名称 (dev/staging/prod)

这些变量在构建时会被写入 `.env.production` 文件。

### 构建规范

构建规范已在 CDK 中定义：

```yaml
version: 1
frontend:
  phases:
    preBuild:
      commands:
        - cd frontend
        - npm ci
    build:
      commands:
        - echo "REACT_APP_API_URL=${apiUrl}" >> .env.production
        - echo "REACT_APP_ENVIRONMENT=${environment}" >> .env.production
        - npm run build
  artifacts:
    baseDirectory: frontend/build
    files:
      - '**/*'
  cache:
    paths:
      - frontend/node_modules/**/*
```

### 自定义域名

要使用自定义域名：

1. 在 Route 53 或其他 DNS 提供商中创建域名
2. 在 ACM 中创建 SSL 证书（us-east-1 区域）
3. 更新配置文件：

```typescript
// infrastructure/lib/config/dev.ts
frontend: {
  domainName: 'dev.example.com',
  certificateArn: 'arn:aws:acm:us-east-1:...',
  // ...
}
```

4. 重新部署 Stack
5. 在 DNS 中添加 CNAME 记录指向 Amplify 域名

## 输出值

部署完成后，Stack 会输出以下值：

- `AmplifyAppId`: Amplify App ID
- `AmplifyAppName`: Amplify App 名称
- `AmplifyDefaultDomain`: Amplify 默认域名
- `WebsiteUrl`: 前端访问 URL
- `FrontendConfig`: 前端配置 JSON

## 访问前端

部署完成后，可以通过以下 URL 访问：

- **默认域名**: `https://dev.d1234567890.amplifyapp.com`
- **自定义域名**: `https://dev.example.com` (如果配置)

## 分支策略

不同环境使用不同的分支：

- **dev**: `dev` 分支
- **staging**: `staging` 分支
- **prod**: `main` 分支

每个分支会自动部署到对应的 Amplify 环境。

## 监控和日志

### 构建日志

在 Amplify Console 中可以查看：
- 构建日志
- 部署历史
- 访问日志

### CloudWatch 日志

Amplify 会自动将日志发送到 CloudWatch Logs。

## 成本优化

Amplify 定价包括：
- 构建时间: $0.01/分钟
- 托管: $0.15/GB/月
- 数据传输: $0.15/GB

对于开发环境，预计成本：
- 构建: ~$5/月 (假设每天 10 次构建)
- 托管: ~$1/月 (假设 5GB 存储)
- 数据传输: ~$5/月 (假设 30GB 传输)

总计: ~$11/月

## 故障排除

### 构建失败

1. 检查构建日志
2. 确认 `frontend/package.json` 中的依赖正确
3. 确认 Node.js 版本 (使用 18)
4. 检查环境变量是否正确设置

### 无法访问

1. 检查 Amplify App 状态
2. 确认分支已部署
3. 检查自定义域名 DNS 配置
4. 检查 SSL 证书状态

### API 连接失败

1. 检查 `REACT_APP_API_URL` 环境变量
2. 确认 API 服务正在运行
3. 检查 CORS 配置
4. 检查安全组规则

## 与 S3 + CloudFront 的对比

| 特性 | Amplify | S3 + CloudFront |
|------|---------|-----------------|
| 自动构建 | ✅ | ❌ (需要 CI/CD) |
| 分支预览 | ✅ | ❌ |
| 环境变量 | ✅ | ❌ |
| 自定义域名 | ✅ | ✅ |
| CDN | ✅ | ✅ |
| 成本 | 中等 | 较低 |
| 设置复杂度 | 低 | 中等 |

## 参考资料

- [AWS Amplify 文档](https://docs.aws.amazon.com/amplify/)
- [Amplify Hosting 定价](https://aws.amazon.com/amplify/pricing/)
- [CDK Amplify 构造](https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_amplify-readme.html)

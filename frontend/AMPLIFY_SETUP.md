# AWS Amplify 部署指南

本文档说明如何将前端应用部署到 AWS Amplify。

## 前提条件

1. AWS 账户
2. Git 代码仓库（GitHub、GitLab、Bitbucket 或 AWS CodeCommit）
3. AWS CLI 已配置（可选，用于 CLI 部署）

## 方法 1: 通过 AWS Console 部署

### 步骤 1: 连接代码仓库

1. 登录 AWS Console
2. 导航到 AWS Amplify 服务
3. 点击 "New app" → "Host web app"
4. 选择代码仓库提供商（GitHub、GitLab、Bitbucket 或 CodeCommit）
5. 授权 AWS Amplify 访问您的代码仓库
6. 选择仓库和分支（例如：main 或 master）

### 步骤 2: 配置构建设置

Amplify 会自动检测 React 应用并生成构建配置。默认配置如下：

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
        - npm run build
  artifacts:
    baseDirectory: frontend/build
    files:
      - '**/*'
  cache:
    paths:
      - frontend/node_modules/**/*
```

如果需要自定义，可以在项目根目录创建 `amplify.yml` 文件。

### 步骤 3: 配置环境变量

在 Amplify Console 中配置以下环境变量：

- `REACT_APP_API_URL`: 后端 API 的 URL（例如：https://api.example.com）
- `REACT_APP_ENVIRONMENT`: 环境名称（dev、staging、prod）

### 步骤 4: 部署

1. 点击 "Save and deploy"
2. Amplify 将自动构建和部署应用
3. 部署完成后，您将获得一个 Amplify 域名（例如：https://main.d1234567890.amplifyapp.com）

### 步骤 5: 配置自定义域名（可选）

1. 在 Amplify Console 中，导航到 "Domain management"
2. 点击 "Add domain"
3. 输入您的域名并按照说明配置 DNS 记录
4. Amplify 将自动配置 SSL 证书

## 方法 2: 通过 AWS CDK 部署

前端 Stack 已在 `infrastructure/lib/stacks/frontend-stack.ts` 中定义。

### 部署步骤

1. 确保您的代码已推送到 Git 仓库
2. 在 `infrastructure/lib/config/dev.ts`（或相应环境）中配置：

```typescript
frontend: {
  repository: 'https://github.com/your-username/your-repo',
  branch: 'main',
  githubToken: 'your-github-personal-access-token', // 存储在 Secrets Manager
  environmentVariables: {
    REACT_APP_API_URL: 'https://api.example.com',
    REACT_APP_ENVIRONMENT: 'dev'
  }
}
```

3. 部署 Frontend Stack：

```bash
cd infrastructure
cdk deploy SatelliteGisFrontendStack-dev
```

## 方法 3: 通过 Amplify CLI 部署

### 安装 Amplify CLI

```bash
npm install -g @aws-amplify/cli
amplify configure
```

### 初始化 Amplify 项目

```bash
cd frontend
amplify init
```

按照提示配置项目：
- 项目名称：satellite-gis-frontend
- 环境名称：dev
- 默认编辑器：选择您喜欢的编辑器
- 应用类型：javascript
- 框架：react
- 源目录：src
- 构建目录：build
- 构建命令：npm run build
- 启动命令：npm start

### 添加托管

```bash
amplify add hosting
```

选择：
- 托管类型：Hosting with Amplify Console
- 部署类型：Manual deployment 或 Continuous deployment

### 部署

```bash
amplify publish
```

## 自动构建触发

Amplify 支持以下自动构建触发方式：

### 1. Git 推送触发

当您推送代码到连接的分支时，Amplify 会自动触发构建和部署。

### 2. Webhook 触发

您可以配置 Webhook 来触发构建：

1. 在 Amplify Console 中，导航到 "Build settings"
2. 找到 "Incoming webhooks" 部分
3. 创建新的 Webhook
4. 使用 Webhook URL 从外部系统触发构建

### 3. 手动触发

在 Amplify Console 中点击 "Redeploy this version" 按钮。

## 环境变量配置

### 在 Amplify Console 中配置

1. 导航到 "Environment variables"
2. 添加以下变量：

```
REACT_APP_API_URL=https://your-api-url.com
REACT_APP_ENVIRONMENT=dev
```

### 在代码中使用

```javascript
const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const environment = process.env.REACT_APP_ENVIRONMENT || 'development';
```

## 分支部署

Amplify 支持多分支部署，每个分支可以有独立的环境：

- `main` 分支 → 生产环境
- `staging` 分支 → 预发布环境
- `dev` 分支 → 开发环境

每个分支可以配置不同的环境变量。

## 监控和日志

### 查看构建日志

1. 在 Amplify Console 中，点击具体的构建
2. 查看详细的构建日志

### 访问日志

Amplify 自动将访问日志发送到 CloudWatch Logs。

## 故障排除

### 构建失败

1. 检查构建日志中的错误信息
2. 确保 `package.json` 中的依赖项正确
3. 验证环境变量是否正确配置

### 应用无法访问 API

1. 检查 CORS 配置
2. 验证 API URL 是否正确
3. 检查网络安全组和防火墙规则

### 自定义域名问题

1. 验证 DNS 记录是否正确配置
2. 等待 DNS 传播（可能需要几分钟到几小时）
3. 检查 SSL 证书状态

## 成本优化

- Amplify 提供免费套餐：
  - 每月 1000 构建分钟
  - 每月 15 GB 存储
  - 每月 15 GB 数据传输
- 超出免费套餐后按使用量计费
- 考虑使用 CloudFront 缓存来减少数据传输成本

## 安全最佳实践

1. 使用 HTTPS（Amplify 自动配置）
2. 配置适当的 CORS 策略
3. 不要在前端代码中硬编码敏感信息
4. 使用环境变量存储配置
5. 定期更新依赖项以修复安全漏洞

## 参考资料

- [AWS Amplify 文档](https://docs.aws.amazon.com/amplify/)
- [Amplify CLI 文档](https://docs.amplify.aws/cli/)
- [React 部署指南](https://create-react-app.dev/docs/deployment/)

# 将 GitHub 前端代码部署到 AWS Amplify

## 概述

本指南说明如何将已发布到 GitHub 的前端代码连接到 AWS Amplify，实现自动构建和部署。

## 前提条件

✅ 代码已推送到 GitHub: `https://github.com/nwcd-solutions/remote-sensing`
✅ AWS 账户已配置
✅ Frontend Stack 已通过 CDK 部署（Amplify 应用已创建）

## 方法 1: 通过 AWS Console 连接（推荐）

### 步骤 1: 获取 Amplify App ID

```bash
# 获取 Amplify App ID
aws cloudformation describe-stacks \
  --stack-name SatelliteGisFrontendStack-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`AmplifyAppId`].OutputValue' \
  --output text
```

记录输出的 App ID，例如：`d1a2b3c4d5e6f7`

### 步骤 2: 访问 Amplify Console

1. 登录 AWS Console
2. 导航到 **AWS Amplify** 服务
3. 在应用列表中找到 `satellite-gis-dev`
4. 点击应用名称进入详情页

或直接访问：
```
https://console.aws.amazon.com/amplify/home?region=us-west-2#/[YOUR_APP_ID]
```

### 步骤 3: 连接 GitHub 仓库

1. 在 Amplify 应用页面，点击 **"Connect branch"** 或 **"连接分支"**

2. 选择 **GitHub** 作为代码仓库提供商

3. 点击 **"Connect to GitHub"**

4. **授权 AWS Amplify**：
   - 如果是第一次使用，GitHub 会要求您授权 AWS Amplify
   - 点击 **"Authorize AWS Amplify"**
   - 选择授权范围：
     - 推荐：只授权 `nwcd-solutions` 组织
     - 或授权所有仓库

5. **选择仓库**：
   - 组织：`nwcd-solutions`
   - 仓库：`remote-sensing`

6. **选择分支**：
   - 分支名称：`main`（或 `master`，取决于您的默认分支）

### 步骤 4: 配置构建设置

Amplify 会自动检测项目根目录的 `amplify.yml` 文件。

**验证构建配置**：

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

如果需要修改：
1. 点击 **"Edit"** 编辑构建设置
2. 修改 YAML 配置
3. 点击 **"Save"**

### 步骤 5: 配置环境变量

环境变量已通过 CDK 配置，但需要验证：

1. 在 Amplify 应用中，点击左侧菜单的 **"Environment variables"**

2. 验证以下变量存在：
   ```
   REACT_APP_API_URL = [您的 API URL]
   REACT_APP_ENVIRONMENT = dev
   ```

3. 如果需要添加或修改：
   - 点击 **"Manage variables"**
   - 添加/编辑变量
   - 点击 **"Save"**

**获取 API URL**：
```bash
aws cloudformation describe-stacks \
  --stack-name SatelliteGisApiStack-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
  --output text
```

### 步骤 6: 保存并部署

1. 检查所有配置无误后，点击 **"Save and deploy"**

2. Amplify 将自动：
   - 克隆 GitHub 仓库
   - 安装依赖（npm ci）
   - 构建应用（npm run build）
   - 部署到 CDN

3. **监控构建进度**：
   - 在 Amplify Console 中查看实时日志
   - 构建通常需要 3-5 分钟

### 步骤 7: 获取部署 URL

构建完成后：

1. 在 Amplify Console 中，查看 **"Domain"** 部分
2. 默认 URL 格式：`https://main.[app-id].amplifyapp.com`
3. 点击 URL 访问部署的应用

或通过 CLI 获取：
```bash
aws cloudformation describe-stacks \
  --stack-name SatelliteGisFrontendStack-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`WebsiteUrl`].OutputValue' \
  --output text
```

## 方法 2: 通过 AWS CLI 连接

### 步骤 1: 创建 GitHub Personal Access Token

1. 访问 GitHub: https://github.com/settings/tokens
2. 点击 **"Generate new token"** → **"Generate new token (classic)"**
3. 设置权限：
   - `repo` - 完整的仓库访问权限
   - `admin:repo_hook` - 管理 webhooks
4. 点击 **"Generate token"**
5. **复制并保存** token（只显示一次）

### 步骤 2: 将 Token 存储到 AWS Secrets Manager

```bash
aws secretsmanager create-secret \
  --name amplify/github-token \
  --description "GitHub Personal Access Token for Amplify" \
  --secret-string "ghp_your_token_here" \
  --region us-west-2
```

### 步骤 3: 更新 Amplify 应用配置

```bash
# 获取 App ID
APP_ID=$(aws cloudformation describe-stacks \
  --stack-name SatelliteGisFrontendStack-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`AmplifyAppId`].OutputValue' \
  --output text)

# 更新应用以连接 GitHub
aws amplify update-app \
  --app-id $APP_ID \
  --repository https://github.com/nwcd-solutions/remote-sensing \
  --access-token $(aws secretsmanager get-secret-value \
    --secret-id amplify/github-token \
    --query SecretString \
    --output text) \
  --region us-west-2
```

### 步骤 4: 创建分支连接

```bash
aws amplify create-branch \
  --app-id $APP_ID \
  --branch-name main \
  --enable-auto-build \
  --region us-west-2
```

### 步骤 5: 触发首次构建

```bash
aws amplify start-job \
  --app-id $APP_ID \
  --branch-name main \
  --job-type RELEASE \
  --region us-west-2
```

## 方法 3: 通过 CDK 更新配置

如果您想通过 CDK 管理 GitHub 连接，需要更新 Frontend Stack。

### 步骤 1: 更新配置文件

编辑 `infrastructure/lib/config/dev.ts`：

```typescript
export const devConfig: EnvironmentConfig = {
  // ... 其他配置
  frontend: {
    repositoryUrl: 'https://github.com/nwcd-solutions/remote-sensing',
    branchName: 'main',
    githubTokenSecretName: 'amplify/github-token', // Secrets Manager 中的 token
    domainName: undefined, // 可选：自定义域名
    environmentVariables: {
      REACT_APP_API_URL: '', // 将在部署时填充
      REACT_APP_ENVIRONMENT: 'dev',
    },
  },
};
```

### 步骤 2: 更新 Frontend Stack

编辑 `infrastructure/lib/stacks/frontend-stack.ts`，取消注释仓库配置：

```typescript
// 在 CfnApp 配置中取消注释
this.amplifyApp = new amplify.CfnApp(this, 'AmplifyApp', {
  // ...
  repository: config.frontend.repositoryUrl,
  accessToken: cdk.SecretValue.secretsManager(
    config.frontend.githubTokenSecretName || 'amplify/github-token'
  ).unsafeUnwrap(),
  // ...
});
```

### 步骤 3: 重新部署

```bash
cd infrastructure
cdk deploy SatelliteGisFrontendStack-dev
```

## 验证部署

### 检查构建状态

```bash
# 获取 App ID
APP_ID=$(aws cloudformation describe-stacks \
  --stack-name SatelliteGisFrontendStack-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`AmplifyAppId`].OutputValue' \
  --output text)

# 列出最近的构建
aws amplify list-jobs \
  --app-id $APP_ID \
  --branch-name main \
  --max-results 5 \
  --region us-west-2
```

### 查看构建日志

1. 在 Amplify Console 中点击具体的构建
2. 查看各个阶段的日志：
   - Provision
   - Build
   - Deploy
   - Verify

### 测试应用

```bash
# 获取 URL
WEBSITE_URL=$(aws cloudformation describe-stacks \
  --stack-name SatelliteGisFrontendStack-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`WebsiteUrl`].OutputValue' \
  --output text)

echo "访问应用: $WEBSITE_URL"

# 测试 API 连接
curl -I $WEBSITE_URL
```

## 自动部署配置

连接 GitHub 后，Amplify 会自动在以下情况触发构建：

### 1. 代码推送触发

每次推送到 `main` 分支时自动构建：

```bash
git add .
git commit -m "Update frontend"
git push origin main
```

### 2. Pull Request 预览

启用 PR 预览（可选）：

```bash
aws amplify update-branch \
  --app-id $APP_ID \
  --branch-name main \
  --enable-pull-request-preview \
  --region us-west-2
```

### 3. Webhook 触发

获取 Webhook URL：

```bash
aws amplify list-webhooks \
  --app-id $APP_ID \
  --region us-west-2
```

手动触发构建：

```bash
curl -X POST [WEBHOOK_URL]
```

## 配置自定义域名（可选）

### 步骤 1: 添加域名

```bash
aws amplify create-domain-association \
  --app-id $APP_ID \
  --domain-name your-domain.com \
  --sub-domain-settings prefix=www,branchName=main \
  --region us-west-2
```

### 步骤 2: 配置 DNS

Amplify 会提供 DNS 记录，需要在您的域名提供商处添加：

```
Type: CNAME
Name: www
Value: [amplify-provided-value]
```

### 步骤 3: 验证域名

```bash
aws amplify get-domain-association \
  --app-id $APP_ID \
  --domain-name your-domain.com \
  --region us-west-2
```

## 故障排除

### 问题 1: 构建失败 - 找不到 package.json

**原因**: Amplify 在根目录查找，但实际在 `frontend/` 目录

**解决方案**: 确保 `amplify.yml` 中有 `cd frontend` 命令

### 问题 2: GitHub 授权失败

**原因**: Token 权限不足或已过期

**解决方案**:
1. 重新生成 GitHub Personal Access Token
2. 确保包含 `repo` 和 `admin:repo_hook` 权限
3. 更新 Secrets Manager 中的 token

### 问题 3: 环境变量未生效

**原因**: 变量未正确配置或需要重新构建

**解决方案**:
```bash
# 更新环境变量
aws amplify update-app \
  --app-id $APP_ID \
  --environment-variables REACT_APP_API_URL=https://your-api-url.com \
  --region us-west-2

# 触发重新构建
aws amplify start-job \
  --app-id $APP_ID \
  --branch-name main \
  --job-type RELEASE \
  --region us-west-2
```

### 问题 4: 无法连接到 API

**原因**: CORS 配置或 API URL 错误

**解决方案**:
1. 验证 `REACT_APP_API_URL` 环境变量
2. 检查后端 API 的 CORS 配置
3. 确保 API Gateway/ALB 允许来自 Amplify 域名的请求

## 监控和维护

### 查看构建历史

```bash
aws amplify list-jobs \
  --app-id $APP_ID \
  --branch-name main \
  --max-results 10 \
  --region us-west-2
```

### 设置构建通知

1. 在 Amplify Console 中，导航到 **"Notifications"**
2. 添加 Email 或 SNS 主题
3. 选择通知事件：
   - Build started
   - Build succeeded
   - Build failed

### 查看访问日志

```bash
# CloudWatch Logs
aws logs tail /aws/amplify/$APP_ID --follow
```

### 成本监控

Amplify 定价：
- 构建: $0.01/分钟
- 托管: $0.15/GB 存储 + $0.15/GB 传输
- 免费套餐: 1000 分钟构建 + 15GB 存储 + 15GB 传输/月

## 快速参考

### 常用命令

```bash
# 获取 App ID
APP_ID=$(aws cloudformation describe-stacks \
  --stack-name SatelliteGisFrontendStack-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`AmplifyAppId`].OutputValue' \
  --output text)

# 触发构建
aws amplify start-job --app-id $APP_ID --branch-name main --job-type RELEASE

# 查看最新构建状态
aws amplify list-jobs --app-id $APP_ID --branch-name main --max-results 1

# 获取 Website URL
aws cloudformation describe-stacks \
  --stack-name SatelliteGisFrontendStack-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`WebsiteUrl`].OutputValue' \
  --output text

# 查看应用详情
aws amplify get-app --app-id $APP_ID
```

### 有用的链接

- **Amplify Console**: https://console.aws.amazon.com/amplify/
- **GitHub 仓库**: https://github.com/nwcd-solutions/remote-sensing
- **Amplify 文档**: https://docs.aws.amazon.com/amplify/
- **构建规范参考**: https://docs.aws.amazon.com/amplify/latest/userguide/build-settings.html

## 下一步

完成 Amplify 部署后：

1. ✅ 配置自定义域名（可选）
2. ✅ 设置 PR 预览环境
3. ✅ 配置构建通知
4. ✅ 优化构建性能（使用缓存）
5. ✅ 设置 CloudWatch 告警

---

**最后更新**: 2026-02-05
**仓库**: https://github.com/nwcd-solutions/remote-sensing

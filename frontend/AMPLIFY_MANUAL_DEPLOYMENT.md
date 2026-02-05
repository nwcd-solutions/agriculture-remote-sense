# Amplify 手动部署指南

## 当前状态

Frontend Stack 已通过 CDK 创建，但 Amplify 应用还没有连接到 Git 仓库。需要手动连接仓库以启用自动部署。

## 方法 1: 通过 AWS Console 连接 Git 仓库（推荐）

### 步骤 1: 准备 Git 仓库

1. 确保代码已推送到 Git 仓库（GitHub、GitLab、Bitbucket 或 CodeCommit）
2. 确保仓库包含 `amplify.yml` 文件（已在项目根目录创建）

### 步骤 2: 在 AWS Console 中连接仓库

1. 登录 AWS Console
2. 导航到 **AWS Amplify** 服务
3. 找到已创建的应用（名称：`satellite-gis-dev`）
4. 点击应用名称进入详情页
5. 点击 **"Connect branch"** 或 **"连接分支"**
6. 选择代码仓库提供商：
   - GitHub
   - GitLab
   - Bitbucket
   - AWS CodeCommit

### 步骤 3: 授权访问

根据选择的提供商：

**GitHub:**
1. 点击 "Connect to GitHub"
2. 授权 AWS Amplify 访问您的 GitHub 账户
3. 选择仓库
4. 选择分支（例如：main 或 dev）

**GitLab:**
1. 点击 "Connect to GitLab"
2. 输入 GitLab Personal Access Token
3. 选择仓库和分支

**Bitbucket:**
1. 点击 "Connect to Bitbucket"
2. 授权 AWS Amplify
3. 选择仓库和分支

**CodeCommit:**
1. 选择 CodeCommit 仓库
2. 选择分支

### 步骤 4: 配置构建设置

Amplify 会自动检测 `amplify.yml` 文件。确认构建设置：

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

### 步骤 5: 验证环境变量

环境变量已通过 CDK 配置，但可以在 Console 中验证：

1. 在 Amplify 应用中，点击 **"Environment variables"**
2. 确认以下变量存在：
   - `REACT_APP_API_URL`: 后端 API URL
   - `REACT_APP_ENVIRONMENT`: dev/staging/prod

### 步骤 6: 触发首次构建

1. 点击 **"Save and deploy"**
2. Amplify 将自动开始构建和部署
3. 等待构建完成（通常需要 3-5 分钟）

### 步骤 7: 获取部署 URL

构建完成后：
1. 在 Amplify Console 中查看部署的 URL
2. URL 格式：`https://[branch].[app-id].amplifyapp.com`
3. 访问 URL 验证前端应用

## 方法 2: 使用 Amplify CLI 连接仓库

### 前提条件

```bash
npm install -g @aws-amplify/cli
amplify configure
```

### 步骤 1: 初始化 Amplify

```bash
cd frontend
amplify init
```

按照提示配置：
- 项目名称：satellite-gis-frontend
- 环境名称：dev
- 默认编辑器：选择您的编辑器
- 应用类型：javascript
- 框架：react
- 源目录：src
- 构建目录：build
- 构建命令：npm run build
- 启动命令：npm start

### 步骤 2: 连接到现有 Amplify 应用

```bash
amplify pull --appId [YOUR_APP_ID] --envName dev
```

从 CDK 输出中获取 App ID：
```bash
cd ../infrastructure
aws cloudformation describe-stacks \
  --stack-name SatelliteGisFrontendStack-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`AmplifyAppId`].OutputValue' \
  --output text
```

### 步骤 3: 添加托管

```bash
amplify add hosting
```

选择：
- 托管类型：Hosting with Amplify Console
- 部署类型：Continuous deployment

### 步骤 4: 发布

```bash
amplify publish
```

## 方法 3: 手动上传构建文件（临时方案）

如果暂时无法连接 Git 仓库，可以手动上传构建文件：

### 步骤 1: 构建前端

```bash
cd frontend
npm install
npm run build
```

### 步骤 2: 压缩构建文件

```bash
cd build
zip -r ../frontend-build.zip .
cd ..
```

### 步骤 3: 通过 Amplify Console 上传

1. 在 Amplify Console 中，选择应用
2. 点击 **"Manual deploy"** 或 **"手动部署"**
3. 上传 `frontend-build.zip`
4. 等待部署完成

**注意**: 手动部署不会启用自动构建，每次更新都需要重新上传。

## 验证部署

### 检查部署状态

```bash
# 获取 Amplify App ID
APP_ID=$(aws cloudformation describe-stacks \
  --stack-name SatelliteGisFrontendStack-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`AmplifyAppId`].OutputValue' \
  --output text)

# 列出所有分支
aws amplify list-branches --app-id $APP_ID

# 获取最新部署状态
aws amplify list-jobs --app-id $APP_ID --branch-name dev --max-results 1
```

### 访问应用

```bash
# 获取 Website URL
aws cloudformation describe-stacks \
  --stack-name SatelliteGisFrontendStack-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`WebsiteUrl`].OutputValue' \
  --output text
```

## 自动构建触发

连接 Git 仓库后，Amplify 会在以下情况自动触发构建：

1. **代码推送**: 推送到连接的分支时
2. **Pull Request**: 创建 PR 时（如果启用了 PR 预览）
3. **手动触发**: 在 Console 中点击 "Redeploy this version"

## 配置 Webhook（可选）

如果需要从外部系统触发构建：

1. 在 Amplify Console 中，导航到 **"Build settings"**
2. 找到 **"Incoming webhooks"**
3. 创建新的 Webhook
4. 复制 Webhook URL
5. 使用 POST 请求触发构建：

```bash
curl -X POST [WEBHOOK_URL]
```

## 故障排除

### 问题 1: 构建失败 - 找不到 package.json

**原因**: Amplify 在根目录查找 package.json，但实际在 frontend/ 目录

**解决方案**: 确保 amplify.yml 中有 `cd frontend` 命令

### 问题 2: 环境变量未生效

**原因**: 环境变量可能未正确配置

**解决方案**:
1. 在 Amplify Console 中检查环境变量
2. 确保变量名以 `REACT_APP_` 开头
3. 重新触发构建

### 问题 3: 无法连接到 API

**原因**: CORS 配置或 API URL 错误

**解决方案**:
1. 检查 `REACT_APP_API_URL` 环境变量
2. 确保后端 API 配置了正确的 CORS
3. 检查 API Gateway 或 ALB 的安全组规则

### 问题 4: 404 错误（刷新页面时）

**原因**: SPA 路由未正确配置

**解决方案**: 确保 Frontend Stack 中的 customRules 已配置（已在 CDK 中配置）

## 监控和日志

### 查看构建日志

1. 在 Amplify Console 中，点击具体的构建
2. 查看详细的构建日志
3. 检查 preBuild、build 和 deploy 阶段

### 访问日志

Amplify 自动将访问日志发送到 CloudWatch Logs：

```bash
# 获取日志组名称
aws logs describe-log-groups --log-group-name-prefix /aws/amplify

# 查看最新日志
aws logs tail /aws/amplify/[app-id] --follow
```

## 成本优化

Amplify 定价：
- **构建时间**: $0.01/分钟
- **托管**: $0.15/GB 存储 + $0.15/GB 传输
- **免费套餐**: 
  - 1000 构建分钟/月
  - 15 GB 存储/月
  - 15 GB 数据传输/月

优化建议：
1. 使用缓存减少构建时间（已在 amplify.yml 中配置）
2. 优化构建产物大小
3. 使用 CloudFront 缓存减少数据传输

## 下一步

1. **连接 Git 仓库**: 使用方法 1 或方法 2
2. **配置自定义域名**: 如果需要
3. **设置 PR 预览**: 用于测试环境
4. **配置告警**: 监控构建失败和性能问题

## 参考资料

- [AWS Amplify 文档](https://docs.aws.amazon.com/amplify/)
- [Amplify CLI 文档](https://docs.amplify.aws/cli/)
- [React 部署指南](https://create-react-app.dev/docs/deployment/)
- [Amplify 定价](https://aws.amazon.com/amplify/pricing/)

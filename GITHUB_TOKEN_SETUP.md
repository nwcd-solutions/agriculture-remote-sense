# GitHub Token 设置指南

本文档说明如何创建 GitHub Personal Access Token 并用于连接 Amplify。

## 创建 GitHub Personal Access Token

### 步骤 1: 访问 GitHub Token 设置页面

访问: https://github.com/settings/tokens

或者：
1. 登录 GitHub
2. 点击右上角头像 → Settings
3. 左侧菜单最底部 → Developer settings
4. Personal access tokens → Tokens (classic)

### 步骤 2: 生成新 Token

1. 点击 "Generate new token" → "Generate new token (classic)"
2. 填写 Note（描述）: `AWS Amplify - Satellite GIS`
3. 设置过期时间: 建议选择 "No expiration" 或 "90 days"
4. 选择权限（Scopes）:
   - ✅ **repo** (完整权限) - 必需
     - repo:status
     - repo_deployment
     - public_repo
     - repo:invite
     - security_events
   - ✅ **admin:repo_hook** - 推荐（用于 webhook）
     - write:repo_hook
     - read:repo_hook

5. 滚动到底部，点击 "Generate token"
6. **重要**: 立即复制生成的 token（只显示一次！）

### Token 示例格式
```
ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## 使用 Token 连接 Amplify

### 方法 1: 使用脚本（推荐）

在 EC2 上执行：

```bash
# 1. 拉取最新代码
cd remote-sensing
git pull origin main

# 2. 设置 GitHub Token 环境变量
export GITHUB_TOKEN=ghp_your_token_here

# 3. 运行连接脚本
chmod +x connect-amplify-github.sh
bash connect-amplify-github.sh
```

脚本会自动：
- 更新 Amplify 应用配置
- 创建分支连接
- 触发首次构建
- 可选：等待构建完成

### 方法 2: 手动执行 AWS CLI 命令

```bash
# 设置变量
export GITHUB_TOKEN=ghp_your_token_here
export APP_ID=d1b2vi5lvw6cs8
export REPO_URL=https://github.com/nwcd-solutions/remote-sensing
export BRANCH_NAME=main
export REGION=us-east-1

# 更新 Amplify 应用
aws amplify update-app \
    --app-id $APP_ID \
    --region $REGION \
    --repository $REPO_URL \
    --access-token $GITHUB_TOKEN

# 创建分支
aws amplify create-branch \
    --app-id $APP_ID \
    --branch-name $BRANCH_NAME \
    --region $REGION \
    --enable-auto-build \
    --framework "React"

# 触发构建
aws amplify start-job \
    --app-id $APP_ID \
    --branch-name $BRANCH_NAME \
    --job-type RELEASE \
    --region $REGION
```

## 验证连接

### 检查分支状态
```bash
aws amplify list-branches \
    --app-id d1b2vi5lvw6cs8 \
    --region us-east-1
```

### 查看最新构建
```bash
aws amplify list-jobs \
    --app-id d1b2vi5lvw6cs8 \
    --branch-name main \
    --region us-east-1 \
    --max-results 5
```

### 访问应用
构建完成后访问: https://main.d1b2vi5lvw6cs8.amplifyapp.com

## 安全建议

### 1. Token 存储
- ❌ 不要将 token 提交到 Git 仓库
- ❌ 不要在代码中硬编码 token
- ✅ 使用环境变量
- ✅ 使用 AWS Secrets Manager（生产环境）

### 2. Token 权限
- 只授予必需的权限
- 定期轮换 token
- 为不同用途创建不同的 token

### 3. Token 撤销
如果 token 泄露，立即撤销：
1. 访问 https://github.com/settings/tokens
2. 找到对应的 token
3. 点击 "Delete"

## 故障排查

### Token 无效
```
Error: The security token included in the request is invalid
```
**解决方案**: 
- 检查 token 是否正确复制
- 确认 token 未过期
- 重新生成 token

### 权限不足
```
Error: Resource not accessible by integration
```
**解决方案**: 
- 确认 token 有 `repo` 完整权限
- 确认 GitHub 账号有仓库访问权限

### 仓库不存在
```
Error: Repository not found
```
**解决方案**: 
- 检查仓库 URL 是否正确
- 确认仓库是 public 或 token 有访问权限

### 分支已存在
```
Error: Branch already exists
```
**解决方案**: 
- 这是正常的，脚本会自动处理
- 或手动删除分支后重试

## 自动化部署

连接成功后，每次推送到 `main` 分支都会自动触发构建：

```bash
# 本地修改代码
git add .
git commit -m "Update frontend"
git push origin main

# Amplify 会自动检测并构建
```

## 监控构建

### 查看构建日志
```bash
# 获取最新 Job ID
JOB_ID=$(aws amplify list-jobs \
    --app-id d1b2vi5lvw6cs8 \
    --branch-name main \
    --region us-east-1 \
    --max-results 1 \
    --query 'jobSummaries[0].jobId' \
    --output text)

# 查看构建详情
aws amplify get-job \
    --app-id d1b2vi5lvw6cs8 \
    --branch-name main \
    --job-id $JOB_ID \
    --region us-east-1
```

### 访问控制台
https://console.aws.amazon.com/amplify/home?region=us-east-1#/d1b2vi5lvw6cs8

## 相关文档

- [GitHub Personal Access Tokens 文档](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)
- [AWS Amplify CLI 文档](https://docs.aws.amazon.com/cli/latest/reference/amplify/)
- [Amplify GitHub 集成](https://docs.aws.amazon.com/amplify/latest/userguide/setting-up-GitHub-access.html)

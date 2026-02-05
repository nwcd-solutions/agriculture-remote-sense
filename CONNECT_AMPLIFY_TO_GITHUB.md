# 连接 Amplify 到 GitHub（更新版）

## 当前状态

✅ Amplify 应用已创建
- App ID: `dfjse3jyewuby`
- App Name: `satellite-gis-dev`
- Website URL: `https://dev.dfjse3jyewuby.amplifyapp.com`

⚠️ 尚未连接到 GitHub 仓库

## 问题说明

AWS Amplify 控制台界面已更新，可能没有明显的 "Connect to GitHub" 按钮。我们需要通过其他方式连接。

## 解决方案

### 方法 1: 通过 AWS CLI 连接（推荐）

这是最直接的方法，无需在控制台中查找按钮。

#### 步骤 1: 创建 GitHub Personal Access Token

1. 访问 GitHub Settings: https://github.com/settings/tokens
2. 点击 **"Generate new token"** → **"Generate new token (classic)"**
3. 设置 Token 信息：
   - Note: `AWS Amplify - remote-sensing`
   - Expiration: 选择合适的过期时间（建议 90 days 或 No expiration）
4. 选择权限（Scopes）：
   - ✅ `repo` - Full control of private repositories
   - ✅ `admin:repo_hook` - Full control of repository hooks
5. 点击 **"Generate token"**
6. **立即复制 token**（只显示一次！）

#### 步骤 2: 将 Token 存储到 AWS Secrets Manager

```bash
# 替换 YOUR_GITHUB_TOKEN 为您刚才复制的 token
aws secretsmanager create-secret \
  --name amplify/github-token \
  --description "GitHub Personal Access Token for Amplify" \
  --secret-string "ghp_YOUR_GITHUB_TOKEN_HERE" \
  --region us-east-1
```

如果 secret 已存在，使用更新命令：
```bash
aws secretsmanager update-secret \
  --secret-id amplify/github-token \
  --secret-string "ghp_YOUR_GITHUB_TOKEN_HERE" \
  --region us-east-1
```

#### 步骤 3: 连接 GitHub 仓库到 Amplify

```bash
# 设置变量
APP_ID="dfjse3jyewuby"
GITHUB_REPO="https://github.com/nwcd-solutions/remote-sensing"
BRANCH_NAME="main"

# 获取 GitHub Token
GITHUB_TOKEN=$(aws secretsmanager get-secret-value \
  --secret-id amplify/github-token \
  --query SecretString \
  --output text \
  --region us-east-1)

# 更新 Amplify 应用以连接 GitHub
aws amplify update-app \
  --app-id $APP_ID \
  --repository $GITHUB_REPO \
  --access-token $GITHUB_TOKEN \
  --region us-east-1

echo "✅ 仓库已连接到 Amplify"
```

#### 步骤 4: 创建分支并启用自动构建

```bash
# 创建 main 分支
aws amplify create-branch \
  --app-id $APP_ID \
  --branch-name $BRANCH_NAME \
  --description "Main production branch" \
  --enable-auto-build \
  --stage PRODUCTION \
  --region us-east-1

echo "✅ 分支已创建并启用自动构建"
```

#### 步骤 5: 触发首次构建

```bash
# 启动构建
aws amplify start-job \
  --app-id $APP_ID \
  --branch-name $BRANCH_NAME \
  --job-type RELEASE \
  --region us-east-1

echo "✅ 首次构建已触发"
echo ""
echo "查看构建进度:"
echo "https://us-east-1.console.aws.amazon.com/amplify/home?region=us-east-1#/$APP_ID/$BRANCH_NAME"
```

#### 步骤 6: 监控构建状态

```bash
# 查看最新构建状态
aws amplify list-jobs \
  --app-id $APP_ID \
  --branch-name $BRANCH_NAME \
  --max-results 1 \
  --region us-east-1
```

### 方法 2: 通过 Amplify 控制台的新界面

如果控制台界面已更新，尝试以下步骤：

1. **访问 Amplify 控制台**:
   ```
   https://us-east-1.console.aws.amazon.com/amplify/home?region=us-east-1#/dfjse3jyewuby
   ```

2. **查找连接选项**（可能的位置）：
   - 左侧菜单中的 **"Hosting"** 或 **"App settings"**
   - 顶部的 **"Set up CI/CD"** 或 **"Connect repository"**
   - 应用概览页面的 **"Get started"** 或 **"Deploy"** 按钮
   - **"Branches"** 标签页中的 **"Connect branch"**

3. **如果找到连接选项**：
   - 选择 **GitHub** 作为源代码提供商
   - 授权 AWS Amplify 访问您的 GitHub 账户
   - 选择仓库: `nwcd-solutions/remote-sensing`
   - 选择分支: `main`
   - 确认构建设置（应自动检测 `amplify.yml`）
   - 点击保存并部署

### 方法 3: 使用自动化脚本

我已经创建了一个自动化脚本来简化整个过程：

```bash
# 运行连接脚本
./connect-amplify-to-github.sh
```

这个脚本会：
1. 检查 AWS 配置
2. 验证 Amplify 应用状态
3. 检查 GitHub Token
4. 自动连接仓库
5. 创建分支
6. 触发首次构建

## 验证连接

### 检查仓库是否已连接

```bash
APP_ID="dfjse3jyewuby"

# 查看应用详情
aws amplify get-app --app-id $APP_ID --region us-east-1 | grep -A 2 "repository"
```

如果看到 `"repository": "https://github.com/nwcd-solutions/remote-sensing"`，说明连接成功。

### 检查分支状态

```bash
# 列出所有分支
aws amplify list-branches --app-id $APP_ID --region us-east-1
```

### 查看构建历史

```bash
# 查看最近的构建
aws amplify list-jobs \
  --app-id $APP_ID \
  --branch-name main \
  --max-results 5 \
  --region us-east-1
```

## 构建完成后

构建成功后，您的应用将部署到：
```
https://main.dfjse3jyewuby.amplifyapp.com
```

或者使用配置的 URL：
```
https://dev.dfjse3jyewuby.amplifyapp.com
```

## 自动部署配置

连接成功后，每次推送到 `main` 分支都会自动触发构建：

```bash
# 在本地修改代码后
git add .
git commit -m "Update frontend"
git push origin main

# Amplify 会自动检测并开始构建
```

## 故障排除

### 问题 1: Token 权限不足

**错误**: `AccessDeniedException` 或 `Unauthorized`

**解决方案**:
- 确保 GitHub Token 包含 `repo` 和 `admin:repo_hook` 权限
- 重新生成 Token 并更新 Secrets Manager

### 问题 2: 分支已存在

**错误**: `BadRequestException: Branch already exists`

**解决方案**:
```bash
# 删除现有分支
aws amplify delete-branch \
  --app-id $APP_ID \
  --branch-name main \
  --region us-east-1

# 重新创建
aws amplify create-branch \
  --app-id $APP_ID \
  --branch-name main \
  --enable-auto-build \
  --region us-east-1
```

### 问题 3: 构建失败

**常见原因**:
1. `amplify.yml` 配置错误
2. 依赖安装失败
3. 环境变量未设置

**解决方案**:
```bash
# 查看详细的构建日志
aws amplify get-job \
  --app-id $APP_ID \
  --branch-name main \
  --job-id [JOB_ID] \
  --region us-east-1
```

或在控制台查看：
```
https://us-east-1.console.aws.amazon.com/amplify/home?region=us-east-1#/dfjse3jyewuby/main
```

### 问题 4: Webhook 未创建

如果自动构建不工作，手动创建 webhook：

```bash
aws amplify create-webhook \
  --app-id $APP_ID \
  --branch-name main \
  --region us-east-1
```

## 快速命令参考

```bash
# 设置变量
APP_ID="dfjse3jyewuby"
BRANCH_NAME="main"

# 触发构建
aws amplify start-job \
  --app-id $APP_ID \
  --branch-name $BRANCH_NAME \
  --job-type RELEASE \
  --region us-east-1

# 查看构建状态
aws amplify list-jobs \
  --app-id $APP_ID \
  --branch-name $BRANCH_NAME \
  --max-results 1 \
  --region us-east-1

# 查看应用详情
aws amplify get-app --app-id $APP_ID --region us-east-1

# 列出分支
aws amplify list-branches --app-id $APP_ID --region us-east-1

# 更新环境变量
aws amplify update-app \
  --app-id $APP_ID \
  --environment-variables REACT_APP_API_URL=https://new-api-url.com \
  --region us-east-1
```

## 下一步

连接成功后：

1. ✅ 验证首次构建成功
2. ✅ 测试自动部署（推送代码到 main 分支）
3. ✅ 配置自定义域名（可选）
4. ✅ 设置构建通知
5. ✅ 配置 PR 预览环境

---

**App ID**: dfjse3jyewuby
**GitHub 仓库**: https://github.com/nwcd-solutions/remote-sensing
**Website URL**: https://dev.dfjse3jyewuby.amplifyapp.com

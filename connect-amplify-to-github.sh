#!/bin/bash

# 连接 Amplify 到 GitHub 的自动化脚本
# 使用方法: ./connect-amplify-to-github.sh [github_token]

set -e

echo "=========================================="
echo "连接 Amplify 到 GitHub"
echo "=========================================="
echo ""

# 配置
APP_ID="dfjse3jyewuby"
GITHUB_REPO="https://github.com/nwcd-solutions/remote-sensing"
BRANCH_NAME="main"
REGION="us-east-1"

# 颜色
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 检查 AWS CLI
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ 错误: 未找到 AWS CLI${NC}"
    exit 1
fi

echo -e "${GREEN}✅ AWS CLI 已配置${NC}"
echo ""

# 步骤 1: 获取或设置 GitHub Token
echo "步骤 1: 获取 GitHub Token"
echo "----------------------------------------"

if [ -n "$1" ]; then
    # 从命令行参数获取
    GITHUB_TOKEN="$1"
    echo "使用提供的 GitHub Token"
    
    # 存储到 Secrets Manager
    echo "存储 Token 到 Secrets Manager..."
    if aws secretsmanager describe-secret --secret-id amplify/github-token --region $REGION &> /dev/null; then
        aws secretsmanager update-secret \
          --secret-id amplify/github-token \
          --secret-string "$GITHUB_TOKEN" \
          --region $REGION > /dev/null
        echo -e "${GREEN}✅ Token 已更新${NC}"
    else
        aws secretsmanager create-secret \
          --name amplify/github-token \
          --description "GitHub Personal Access Token for Amplify" \
          --secret-string "$GITHUB_TOKEN" \
          --region $REGION > /dev/null
        echo -e "${GREEN}✅ Token 已创建${NC}"
    fi
else
    # 从 Secrets Manager 获取
    echo "从 Secrets Manager 获取 Token..."
    if ! GITHUB_TOKEN=$(aws secretsmanager get-secret-value \
      --secret-id amplify/github-token \
      --query SecretString \
      --output text \
      --region $REGION 2>/dev/null); then
        echo -e "${RED}❌ 错误: 未找到 GitHub Token${NC}"
        echo ""
        echo "请提供 GitHub Token:"
        echo "  ./connect-amplify-to-github.sh YOUR_GITHUB_TOKEN"
        echo ""
        echo "或先创建 Secret:"
        echo "  aws secretsmanager create-secret \\"
        echo "    --name amplify/github-token \\"
        echo "    --secret-string 'YOUR_TOKEN' \\"
        echo "    --region $REGION"
        echo ""
        echo "如何获取 GitHub Token:"
        echo "  1. 访问: https://github.com/settings/tokens"
        echo "  2. 点击 'Generate new token (classic)'"
        echo "  3. 选择权限: repo, admin:repo_hook"
        echo "  4. 生成并复制 token"
        exit 1
    fi
    echo -e "${GREEN}✅ Token 已获取${NC}"
fi

echo ""

# 步骤 2: 连接仓库到 Amplify
echo "步骤 2: 连接 GitHub 仓库到 Amplify"
echo "----------------------------------------"
echo "App ID: $APP_ID"
echo "仓库: $GITHUB_REPO"
echo ""

aws amplify update-app \
  --app-id $APP_ID \
  --repository $GITHUB_REPO \
  --access-token $GITHUB_TOKEN \
  --region $REGION > /dev/null

echo -e "${GREEN}✅ 仓库已连接${NC}"
echo ""

# 步骤 3: 创建分支
echo "步骤 3: 创建分支"
echo "----------------------------------------"
echo "分支名称: $BRANCH_NAME"
echo ""

# 检查分支是否已存在
if aws amplify get-branch --app-id $APP_ID --branch-name $BRANCH_NAME --region $REGION &> /dev/null; then
    echo -e "${YELLOW}⚠️  分支已存在，跳过创建${NC}"
else
    aws amplify create-branch \
      --app-id $APP_ID \
      --branch-name $BRANCH_NAME \
      --description "Main production branch" \
      --enable-auto-build \
      --stage PRODUCTION \
      --region $REGION > /dev/null
    
    echo -e "${GREEN}✅ 分支已创建${NC}"
fi

echo ""

# 步骤 4: 触发首次构建
echo "步骤 4: 触发首次构建"
echo "----------------------------------------"

JOB_OUTPUT=$(aws amplify start-job \
  --app-id $APP_ID \
  --branch-name $BRANCH_NAME \
  --job-type RELEASE \
  --region $REGION)

JOB_ID=$(echo $JOB_OUTPUT | jq -r '.jobSummary.jobId')

echo -e "${GREEN}✅ 构建已触发${NC}"
echo "Job ID: $JOB_ID"
echo ""

# 步骤 5: 显示结果
echo "=========================================="
echo "连接完成！"
echo "=========================================="
echo ""
echo "📱 应用信息:"
echo "  App ID: $APP_ID"
echo "  分支: $BRANCH_NAME"
echo "  仓库: $GITHUB_REPO"
echo ""
echo "🌐 访问 URL:"
echo "  https://main.dfjse3jyewuby.amplifyapp.com"
echo "  https://dev.dfjse3jyewuby.amplifyapp.com"
echo ""
echo "📊 查看构建进度:"
echo "  https://us-east-1.console.aws.amazon.com/amplify/home?region=us-east-1#/$APP_ID/$BRANCH_NAME"
echo ""
echo "💡 监控构建状态:"
echo "  aws amplify list-jobs --app-id $APP_ID --branch-name $BRANCH_NAME --max-results 1 --region $REGION"
echo ""
echo "🔄 自动部署已启用"
echo "  每次推送到 main 分支都会自动触发构建"
echo ""

# 等待几秒后检查构建状态
echo "等待构建开始..."
sleep 5

echo ""
echo "当前构建状态:"
aws amplify list-jobs \
  --app-id $APP_ID \
  --branch-name $BRANCH_NAME \
  --max-results 1 \
  --region $REGION \
  --query 'jobSummaries[0].[jobId,status,commitMessage]' \
  --output table

echo ""
echo "=========================================="

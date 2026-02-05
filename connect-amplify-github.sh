#!/bin/bash

# AWS Amplify GitHub 连接脚本
# 用于将 GitHub 仓库连接到 AWS Amplify

set -e

echo "=========================================="
echo "AWS Amplify GitHub 连接助手"
echo "=========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查 AWS CLI
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ 错误: 未找到 AWS CLI${NC}"
    echo "请安装 AWS CLI: https://aws.amazon.com/cli/"
    exit 1
fi

# 检查 AWS 凭证
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ 错误: AWS 凭证未配置${NC}"
    echo "请运行: aws configure"
    exit 1
fi

echo -e "${GREEN}✅ AWS CLI 已配置${NC}"
echo ""

# 获取环境（默认 dev）
ENVIRONMENT=${1:-dev}
STACK_NAME="SatelliteGisFrontendStack-${ENVIRONMENT}"
GITHUB_REPO="https://github.com/nwcd-solutions/remote-sensing"
BRANCH_NAME="main"

echo "环境: ${ENVIRONMENT}"
echo "Stack 名称: ${STACK_NAME}"
echo "GitHub 仓库: ${GITHUB_REPO}"
echo "分支: ${BRANCH_NAME}"
echo ""

# 检查 Stack 是否存在
echo "检查 CloudFormation Stack..."
if ! aws cloudformation describe-stacks --stack-name $STACK_NAME &> /dev/null; then
    echo -e "${RED}❌ 错误: Stack ${STACK_NAME} 不存在${NC}"
    echo "请先部署 Frontend Stack:"
    echo "  cd infrastructure"
    echo "  cdk deploy ${STACK_NAME}"
    exit 1
fi

echo -e "${GREEN}✅ Stack 已部署${NC}"
echo ""

# 获取 Amplify App ID
echo "获取 Amplify 应用信息..."
APP_ID=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --query 'Stacks[0].Outputs[?OutputKey==`AmplifyAppId`].OutputValue' \
  --output text)

if [ -z "$APP_ID" ]; then
    echo -e "${RED}❌ 错误: 无法获取 Amplify App ID${NC}"
    exit 1
fi

APP_NAME=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --query 'Stacks[0].Outputs[?OutputKey==`AmplifyAppName`].OutputValue' \
  --output text)

echo -e "${GREEN}✅ Amplify 应用信息:${NC}"
echo "  App ID: ${APP_ID}"
echo "  App Name: ${APP_NAME}"
echo ""

# 检查是否已连接仓库
echo "检查仓库连接状态..."
BRANCHES=$(aws amplify list-branches --app-id $APP_ID --query 'branches[].branchName' --output text 2>/dev/null || echo "")

if [ -n "$BRANCHES" ]; then
    echo -e "${GREEN}✅ 仓库已连接${NC}"
    echo "已连接分支: ${BRANCHES}"
    echo ""
    
    # 获取最新部署状态
    echo "获取最新部署状态..."
    LATEST_JOB=$(aws amplify list-jobs \
      --app-id $APP_ID \
      --branch-name $(echo $BRANCHES | awk '{print $1}') \
      --max-results 1 \
      --query 'jobSummaries[0]' \
      --output json 2>/dev/null || echo "{}")
    
    if [ "$LATEST_JOB" != "{}" ]; then
        JOB_STATUS=$(echo $LATEST_JOB | jq -r '.status')
        JOB_ID=$(echo $LATEST_JOB | jq -r '.jobId')
        
        echo "最新部署:"
        echo "  Job ID: ${JOB_ID}"
        echo "  状态: ${JOB_STATUS}"
        echo ""
        
        if [ "$JOB_STATUS" == "SUCCEED" ]; then
            echo -e "${GREEN}✅ 部署成功!${NC}"
        elif [ "$JOB_STATUS" == "FAILED" ]; then
            echo -e "${RED}❌ 部署失败${NC}"
        elif [ "$JOB_STATUS" == "RUNNING" ]; then
            echo -e "${YELLOW}⏳ 部署进行中...${NC}"
        fi
    fi
    
    # 获取 Website URL
    WEBSITE_URL=$(aws cloudformation describe-stacks \
      --stack-name $STACK_NAME \
      --query 'Stacks[0].Outputs[?OutputKey==`WebsiteUrl`].OutputValue' \
      --output text)
    
    echo ""
    echo -e "${GREEN}访问应用: ${WEBSITE_URL}${NC}"
    echo ""
    
    # 提供管理选项
    echo "=========================================="
    echo "管理选项"
    echo "=========================================="
    echo ""
    echo "1. 触发新部署:"
    echo "   aws amplify start-job --app-id ${APP_ID} --branch-name ${BRANCHES} --job-type RELEASE"
    echo ""
    echo "2. 查看构建日志:"
    echo "   https://console.aws.amazon.com/amplify/home?region=us-west-2#/${APP_ID}"
    echo ""
    echo "3. 更新环境变量:"
    echo "   aws amplify update-app --app-id ${APP_ID} --environment-variables KEY=VALUE"
    echo ""
    
    exit 0
fi

# 仓库未连接，提供连接指导
echo -e "${YELLOW}⚠️  仓库未连接${NC}"
echo ""
echo "=========================================="
echo "连接 GitHub 仓库"
echo "=========================================="
echo ""
echo "有两种方法连接 GitHub 仓库到 Amplify："
echo ""
echo -e "${GREEN}方法 1: 通过 AWS Console（推荐）${NC}"
echo "----------------------------------------"
echo "1. 访问 Amplify Console:"
echo "   https://console.aws.amazon.com/amplify/home?region=us-west-2#/${APP_ID}"
echo ""
echo "2. 点击 'Connect branch' 或 '连接分支'"
echo ""
echo "3. 选择 GitHub 并授权"
echo ""
echo "4. 选择仓库和分支:"
echo "   - 仓库: nwcd-solutions/remote-sensing"
echo "   - 分支: main"
echo ""
echo "5. 点击 'Save and deploy'"
echo ""
echo -e "${GREEN}方法 2: 通过 CLI（需要 GitHub Token）${NC}"
echo "----------------------------------------"
echo "1. 创建 GitHub Personal Access Token:"
echo "   https://github.com/settings/tokens"
echo "   权限: repo, admin:repo_hook"
echo ""
echo "2. 将 Token 存储到 Secrets Manager:"
echo "   aws secretsmanager create-secret \\"
echo "     --name amplify/github-token \\"
echo "     --secret-string 'YOUR_GITHUB_TOKEN' \\"
echo "     --region us-west-2"
echo ""
echo "3. 运行连接脚本:"
echo "   ./connect-amplify-github.sh connect"
echo ""
echo "=========================================="
echo ""

# 如果提供了 'connect' 参数，尝试通过 CLI 连接
if [ "$2" == "connect" ]; then
    echo "尝试通过 CLI 连接..."
    echo ""
    
    # 检查 GitHub Token
    if ! aws secretsmanager get-secret-value --secret-id amplify/github-token &> /dev/null; then
        echo -e "${RED}❌ 错误: 未找到 GitHub Token${NC}"
        echo "请先创建 Secret: amplify/github-token"
        exit 1
    fi
    
    echo "获取 GitHub Token..."
    GITHUB_TOKEN=$(aws secretsmanager get-secret-value \
      --secret-id amplify/github-token \
      --query SecretString \
      --output text)
    
    echo "更新 Amplify 应用配置..."
    aws amplify update-app \
      --app-id $APP_ID \
      --repository $GITHUB_REPO \
      --access-token $GITHUB_TOKEN \
      --region us-west-2
    
    echo "创建分支连接..."
    aws amplify create-branch \
      --app-id $APP_ID \
      --branch-name $BRANCH_NAME \
      --enable-auto-build \
      --region us-west-2
    
    echo "触发首次构建..."
    aws amplify start-job \
      --app-id $APP_ID \
      --branch-name $BRANCH_NAME \
      --job-type RELEASE \
      --region us-west-2
    
    echo ""
    echo -e "${GREEN}✅ 连接成功！${NC}"
    echo ""
    echo "查看构建进度:"
    echo "https://console.aws.amazon.com/amplify/home?region=us-west-2#/${APP_ID}"
fi

echo "=========================================="
echo "详细文档"
echo "=========================================="
echo ""
echo "查看完整指南: AMPLIFY_GITHUB_DEPLOYMENT.md"
echo ""

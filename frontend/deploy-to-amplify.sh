#!/bin/bash

# Amplify 部署脚本
# 用于获取 Amplify 应用信息并提供部署指导

set -e

echo "=========================================="
echo "Amplify 部署助手"
echo "=========================================="
echo ""

# 检查 AWS CLI
if ! command -v aws &> /dev/null; then
    echo "❌ 错误: 未找到 AWS CLI"
    echo "请安装 AWS CLI: https://aws.amazon.com/cli/"
    exit 1
fi

# 检查 AWS 凭证
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ 错误: AWS 凭证未配置"
    echo "请运行: aws configure"
    exit 1
fi

echo "✅ AWS CLI 已配置"
echo ""

# 获取环境（默认 dev）
ENVIRONMENT=${1:-dev}
STACK_NAME="SatelliteGisFrontendStack-${ENVIRONMENT}"

echo "环境: ${ENVIRONMENT}"
echo "Stack 名称: ${STACK_NAME}"
echo ""

# 检查 Stack 是否存在
echo "检查 CloudFormation Stack..."
if ! aws cloudformation describe-stacks --stack-name $STACK_NAME &> /dev/null; then
    echo "❌ 错误: Stack ${STACK_NAME} 不存在"
    echo "请先部署 Frontend Stack:"
    echo "  cd infrastructure"
    echo "  cdk deploy ${STACK_NAME}"
    exit 1
fi

echo "✅ Stack 已部署"
echo ""

# 获取 Amplify App ID
echo "获取 Amplify 应用信息..."
APP_ID=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --query 'Stacks[0].Outputs[?OutputKey==`AmplifyAppId`].OutputValue' \
  --output text)

if [ -z "$APP_ID" ]; then
    echo "❌ 错误: 无法获取 Amplify App ID"
    exit 1
fi

APP_NAME=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --query 'Stacks[0].Outputs[?OutputKey==`AmplifyAppName`].OutputValue' \
  --output text)

DEFAULT_DOMAIN=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --query 'Stacks[0].Outputs[?OutputKey==`AmplifyDefaultDomain`].OutputValue' \
  --output text)

WEBSITE_URL=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --query 'Stacks[0].Outputs[?OutputKey==`WebsiteUrl`].OutputValue' \
  --output text)

echo "✅ Amplify 应用信息:"
echo "  App ID: ${APP_ID}"
echo "  App Name: ${APP_NAME}"
echo "  Default Domain: ${DEFAULT_DOMAIN}"
echo "  Website URL: ${WEBSITE_URL}"
echo ""

# 检查是否已连接仓库
echo "检查仓库连接状态..."
BRANCHES=$(aws amplify list-branches --app-id $APP_ID --query 'branches[].branchName' --output text 2>/dev/null || echo "")

if [ -z "$BRANCHES" ]; then
    echo "⚠️  警告: 未连接 Git 仓库"
    echo ""
    echo "=========================================="
    echo "下一步: 连接 Git 仓库"
    echo "=========================================="
    echo ""
    echo "方法 1: 通过 AWS Console（推荐）"
    echo "  1. 访问: https://console.aws.amazon.com/amplify/home?region=us-west-2#/${APP_ID}"
    echo "  2. 点击 'Connect branch' 或'连接分支'"
    echo "  3. 选择 Git 提供商（GitHub/GitLab/Bitbucket/CodeCommit）"
    echo "  4. 授权并选择仓库和分支"
    echo "  5. 保存并部署"
    echo ""
    echo "方法 2: 手动部署（临时方案）"
    echo "  1. 构建前端:"
    echo "     cd frontend"
    echo "     npm install"
    echo "     npm run build"
    echo "  2. 压缩构建文件:"
    echo "     cd build && zip -r ../frontend-build.zip . && cd .."
    echo "  3. 在 Amplify Console 中选择 'Manual deploy' 并上传 zip 文件"
    echo ""
    echo "详细说明请参考: frontend/AMPLIFY_MANUAL_DEPLOYMENT.md"
    echo ""
else
    echo "✅ 已连接分支: ${BRANCHES}"
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
            echo "✅ 部署成功!"
            echo "访问应用: ${WEBSITE_URL}"
        elif [ "$JOB_STATUS" == "FAILED" ]; then
            echo "❌ 部署失败"
            echo "查看日志: https://console.aws.amazon.com/amplify/home?region=us-west-2#/${APP_ID}/${BRANCHES}/deployments/${JOB_ID}"
        elif [ "$JOB_STATUS" == "RUNNING" ]; then
            echo "⏳ 部署进行中..."
            echo "查看进度: https://console.aws.amazon.com/amplify/home?region=us-west-2#/${APP_ID}/${BRANCHES}/deployments/${JOB_ID}"
        fi
    fi
    
    echo ""
    echo "=========================================="
    echo "管理 Amplify 应用"
    echo "=========================================="
    echo ""
    echo "触发新部署:"
    echo "  aws amplify start-job --app-id ${APP_ID} --branch-name ${BRANCHES} --job-type RELEASE"
    echo ""
    echo "查看所有部署:"
    echo "  aws amplify list-jobs --app-id ${APP_ID} --branch-name ${BRANCHES}"
    echo ""
    echo "在 Console 中管理:"
    echo "  https://console.aws.amazon.com/amplify/home?region=us-west-2#/${APP_ID}"
    echo ""
fi

echo "=========================================="
echo "环境变量"
echo "=========================================="
echo ""
echo "当前配置的环境变量:"
aws amplify get-app --app-id $APP_ID --query 'app.environmentVariables' --output table

echo ""
echo "如需更新环境变量:"
echo "  aws amplify update-app --app-id ${APP_ID} --environment-variables REACT_APP_API_URL=https://your-api-url.com"
echo ""

echo "=========================================="
echo "完成"
echo "=========================================="

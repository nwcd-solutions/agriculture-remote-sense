#!/bin/bash
# 通过命令行连接 Amplify 和 GitHub

set -e

echo "=== 连接 Amplify 和 GitHub ==="

# 配置变量
APP_ID="d1b2vi5lvw6cs8"
REPO_URL="https://github.com/nwcd-solutions/remote-sensing"
BRANCH_NAME="main"
REGION="us-east-1"

# 检查是否提供了 GitHub Token
if [ -z "$GITHUB_TOKEN" ]; then
    echo "错误: 需要设置 GITHUB_TOKEN 环境变量"
    echo ""
    echo "使用方法:"
    echo "  export GITHUB_TOKEN=your_github_token"
    echo "  bash connect-amplify-github.sh"
    echo ""
    echo "如何获取 GitHub Token:"
    echo "  1. 访问 https://github.com/settings/tokens"
    echo "  2. 点击 'Generate new token' -> 'Generate new token (classic)'"
    echo "  3. 选择权限: repo (完整权限)"
    echo "  4. 生成并复制 token"
    exit 1
fi

echo "GitHub Token: ${GITHUB_TOKEN:0:10}..."

# 更新 Amplify 应用，添加 GitHub token
echo "更新 Amplify 应用配置..."
aws amplify update-app \
    --app-id $APP_ID \
    --region $REGION \
    --repository $REPO_URL \
    --access-token $GITHUB_TOKEN

echo "Amplify 应用已更新"

# 创建分支连接
echo "创建分支连接: $BRANCH_NAME"

# 检查分支是否已存在
BRANCH_EXISTS=$(aws amplify list-branches \
    --app-id $APP_ID \
    --region $REGION \
    --query "branches[?branchName=='$BRANCH_NAME'].branchName" \
    --output text)

if [ ! -z "$BRANCH_EXISTS" ]; then
    echo "分支 $BRANCH_NAME 已存在，跳过创建"
else
    # 创建分支
    aws amplify create-branch \
        --app-id $APP_ID \
        --branch-name $BRANCH_NAME \
        --region $REGION \
        --enable-auto-build \
        --framework "React"
    
    echo "分支创建成功"
fi

# 触发构建
echo "触发构建..."
JOB_ID=$(aws amplify start-job \
    --app-id $APP_ID \
    --branch-name $BRANCH_NAME \
    --job-type RELEASE \
    --region $REGION \
    --query 'jobSummary.jobId' \
    --output text)

echo "构建已触发，Job ID: $JOB_ID"

# 获取构建状态
echo ""
echo "=== 构建信息 ==="
echo "App ID: $APP_ID"
echo "Branch: $BRANCH_NAME"
echo "Job ID: $JOB_ID"
echo ""
echo "查看构建状态:"
echo "  aws amplify get-job --app-id $APP_ID --branch-name $BRANCH_NAME --job-id $JOB_ID --region $REGION"
echo ""
echo "访问 Amplify 控制台:"
echo "  https://console.aws.amazon.com/amplify/home?region=$REGION#/$APP_ID/$BRANCH_NAME/$JOB_ID"
echo ""
echo "应用 URL (构建完成后可访问):"
echo "  https://$BRANCH_NAME.$APP_ID.amplifyapp.com"
echo ""

# 等待构建完成（可选）
read -p "是否等待构建完成? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "等待构建完成..."
    while true; do
        STATUS=$(aws amplify get-job \
            --app-id $APP_ID \
            --branch-name $BRANCH_NAME \
            --job-id $JOB_ID \
            --region $REGION \
            --query 'job.summary.status' \
            --output text)
        
        echo "当前状态: $STATUS"
        
        if [ "$STATUS" == "SUCCEED" ]; then
            echo ""
            echo "✅ 构建成功！"
            echo "访问应用: https://$BRANCH_NAME.$APP_ID.amplifyapp.com"
            break
        elif [ "$STATUS" == "FAILED" ] || [ "$STATUS" == "CANCELLED" ]; then
            echo ""
            echo "❌ 构建失败或被取消"
            echo "查看日志: https://console.aws.amazon.com/amplify/home?region=$REGION#/$APP_ID/$BRANCH_NAME/$JOB_ID"
            exit 1
        fi
        
        sleep 10
    done
fi

echo ""
echo "=== 部署完成 ==="

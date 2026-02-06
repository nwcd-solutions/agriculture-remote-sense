#!/bin/bash
# 手动部署前端到 Amplify 的脚本

set -e

echo "=== 手动部署前端到 AWS Amplify ==="

# 配置变量
APP_NAME="satellite-gis-dev"
REPO_URL="https://github.com/nwcd-solutions/remote-sensing"
BRANCH_NAME="main"
REGION="us-east-1"

# Cognito 配置（从 Auth Stack 输出获取）
USER_POOL_ID="us-east-1_mzxQGZOng"
USER_POOL_CLIENT_ID="6s47gmbem85emk7goa2foh64tj"
IDENTITY_POOL_ID="us-east-1:bc3b098c-7b63-4582-8720-93191adcf1b8"

# API 配置（从 API Stack 输出获取）
API_URL="https://pdjzjbzed6.execute-api.us-east-1.amazonaws.com/dev/"
API_KEY_ID="vb3gq010ni"

# 获取 API Key 值
echo "获取 API Key 值..."
API_KEY=$(aws apigateway get-api-key --api-key $API_KEY_ID --include-value --region $REGION --query 'value' --output text)
echo "API Key: $API_KEY"

# 检查 Amplify 应用是否已存在
echo "检查 Amplify 应用..."
APP_ID=$(aws amplify list-apps --region $REGION --query "apps[?name=='$APP_NAME'].appId" --output text)

if [ -z "$APP_ID" ]; then
    echo "创建新的 Amplify 应用..."
    
    # 创建 IAM 角色
    echo "创建 Amplify IAM 角色..."
    ROLE_NAME="AmplifyRole-satellite-gis-dev"
    
    # 检查角色是否已存在
    if aws iam get-role --role-name $ROLE_NAME 2>/dev/null; then
        echo "IAM 角色已存在"
        ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text)
    else
        # 创建信任策略
        cat > /tmp/trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "amplify.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
        
        ROLE_ARN=$(aws iam create-role \
            --role-name $ROLE_NAME \
            --assume-role-policy-document file:///tmp/trust-policy.json \
            --query 'Role.Arn' \
            --output text)
        
        # 附加策略
        aws iam attach-role-policy \
            --role-name $ROLE_NAME \
            --policy-arn arn:aws:iam::aws:policy/AdministratorAccess-Amplify
        
        echo "IAM 角色创建完成: $ROLE_ARN"
    fi
    
    # 创建 Amplify 应用（不使用 GitHub token，手动连接）
    APP_ID=$(aws amplify create-app \
        --name $APP_NAME \
        --description "Satellite GIS Platform Frontend (dev)" \
        --platform WEB \
        --iam-service-role-arn $ROLE_ARN \
        --region $REGION \
        --custom-rules '[{"source":"</^[^.]+$|\\.(?!(css|gif|ico|jpg|js|png|txt|svg|woff|woff2|ttf|map|json)$)([^.]+$)/>","target":"/index.html","status":"200"}]' \
        --environment-variables \
            REACT_APP_API_URL=$API_URL \
            REACT_APP_API_KEY=$API_KEY \
            REACT_APP_ENVIRONMENT=dev \
            REACT_APP_USER_POOL_ID=$USER_POOL_ID \
            REACT_APP_USER_POOL_CLIENT_ID=$USER_POOL_CLIENT_ID \
            REACT_APP_IDENTITY_POOL_ID=$IDENTITY_POOL_ID \
            REACT_APP_AWS_REGION=$REGION \
            _LIVE_UPDATES='[{"pkg":"node","type":"nvm","version":"18"}]' \
        --query 'app.appId' \
        --output text)
    
    echo "Amplify 应用创建完成: $APP_ID"
    echo "应用 URL: https://$BRANCH_NAME.$APP_ID.amplifyapp.com"
    
    echo ""
    echo "=== 下一步操作 ==="
    echo "1. 在 AWS Amplify 控制台连接 GitHub 仓库"
    echo "2. 访问: https://console.aws.amazon.com/amplify/home?region=$REGION#/$APP_ID"
    echo "3. 点击 'Connect branch' 连接 GitHub"
    echo "4. 选择仓库: $REPO_URL"
    echo "5. 选择分支: $BRANCH_NAME"
    echo "6. 保存并部署"
else
    echo "Amplify 应用已存在: $APP_ID"
    echo "更新环境变量..."
    
    # 更新环境变量
    aws amplify update-app \
        --app-id $APP_ID \
        --region $REGION \
        --environment-variables \
            REACT_APP_API_URL=$API_URL \
            REACT_APP_API_KEY=$API_KEY \
            REACT_APP_ENVIRONMENT=dev \
            REACT_APP_USER_POOL_ID=$USER_POOL_ID \
            REACT_APP_USER_POOL_CLIENT_ID=$USER_POOL_CLIENT_ID \
            REACT_APP_IDENTITY_POOL_ID=$IDENTITY_POOL_ID \
            REACT_APP_AWS_REGION=$REGION \
            _LIVE_UPDATES='[{"pkg":"node","type":"nvm","version":"18"}]'
    
    echo "环境变量更新完成"
    
    # 触发新的构建
    BRANCH_EXISTS=$(aws amplify list-branches --app-id $APP_ID --region $REGION --query "branches[?branchName=='$BRANCH_NAME'].branchName" --output text)
    
    if [ ! -z "$BRANCH_EXISTS" ]; then
        echo "触发新的构建..."
        aws amplify start-job \
            --app-id $APP_ID \
            --branch-name $BRANCH_NAME \
            --job-type RELEASE \
            --region $REGION
        echo "构建已触发"
    else
        echo "分支 $BRANCH_NAME 不存在，请在控制台手动连接"
    fi
fi

echo ""
echo "=== 部署完成 ==="
echo "App ID: $APP_ID"
echo "控制台: https://console.aws.amazon.com/amplify/home?region=$REGION#/$APP_ID"

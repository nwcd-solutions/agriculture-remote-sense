#!/bin/bash

# 部署脚本 - 连接到 EC2，安装 Lambda Layer 依赖，部署 CDK
# 使用方法: ./deploy-to-ec2-us-east-2.sh [--stack STACK_NAME]
# 示例:
#   ./deploy-to-ec2-us-east-2.sh                          # 部署所有 stacks
#   ./deploy-to-ec2-us-east-2.sh --stack SatelliteGis-Api-dev  # 只部署 API stack

set -e

# 配置
EC2_HOST="3.208.16.247"
EC2_USER="ec2-user"
SSH_KEY="C:/Users/Administrator/.ssh/Global-001.pem"
PROJECT_DIR="remote-sensing-v2"
AWS_REGION="us-east-2"

# 解析参数
STACK_ARG=""
while [[ $# -gt 0 ]]; do
  case $1 in
    --stack)
      STACK_ARG="$2"
      shift 2
      ;;
    *)
      echo "未知参数: $1"
      exit 1
      ;;
  esac
done

echo "=========================================="
echo "部署到 EC2 (us-east-2)"
echo "=========================================="
echo "EC2: $EC2_USER@$EC2_HOST"
echo "项目目录: $PROJECT_DIR"
if [ -n "$STACK_ARG" ]; then
  echo "部署 Stack: $STACK_ARG"
else
  echo "部署: 所有 Stacks"
fi
echo "=========================================="

# SSH 连接测试
echo ""
echo "[1/5] 测试 SSH 连接..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$EC2_USER@$EC2_HOST" "echo 'SSH OK'"

# 远程执行部署
echo ""
echo "[2/5] 开始远程部署..."

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_HOST" "STACK_ARG='$STACK_ARG'" 'bash -s' << 'ENDSSH'

set -e

PROJECT_DIR="remote-sensing-v2"
AWS_REGION="us-east-2"
export AWS_DEFAULT_REGION="$AWS_REGION"

cd "$PROJECT_DIR"

echo ""
echo "[2/5] 拉取最新代码..."
git pull origin main
echo "当前提交: $(git log -1 --oneline)"

echo ""
echo "[3/5] 安装 Lambda Layer Python 依赖..."
# 清理旧的 layer 内容
rm -rf backend/lambda-layer/python/*/

# 安装依赖到 lambda-layer/python 目录
pip install -r backend/requirements-lambda.txt \
    -t backend/lambda-layer/python/ \
    --no-cache-dir \
    --quiet

# 验证关键文件存在
if [ ! -d "backend/lambda-layer/python/boto3/data/dynamodb" ]; then
    echo "❌ boto3 data 目录缺失，安装异常"
    exit 1
fi
echo "✅ Lambda Layer 依赖安装完成"
echo "   boto3 版本: $(python3 -c "import importlib.metadata; print(importlib.metadata.version('boto3'))" 2>/dev/null || echo 'N/A')"
LAYER_SIZE=$(du -sh backend/lambda-layer/python/ | cut -f1)
echo "   Layer 大小: $LAYER_SIZE"

echo ""
echo "[4/5] 安装 CDK 依赖..."
cd infrastructure
npm install --quiet

echo ""
echo "[5/5] 部署 CDK..."
rm -rf cdk.out

if [ -n "$STACK_ARG" ]; then
    echo "部署 Stack: $STACK_ARG"
    npx cdk deploy "$STACK_ARG" --require-approval never
else
    echo "部署所有 Stacks..."
    npx cdk deploy --all --require-approval never
fi

echo ""
echo "=========================================="
echo "✅ 部署完成"
echo "=========================================="

ENDSSH

echo ""
echo "✅ 远程部署完成"

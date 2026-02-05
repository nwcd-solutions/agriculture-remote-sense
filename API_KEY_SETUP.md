# API密钥配置指南

## 概述

REST API Gateway现在需要API密钥进行身份验证。本文档说明如何在不同环境中配置API密钥。

## API密钥信息

- **API Key ID**: `vb3gq010ni`
- **API Key Value**: `AlAY8zdkA56sQ4ZdaRIBl4lywIDPJGq65bO8I7Uu`
- **API Gateway URL**: `https://pdjzjbzed6.execute-api.us-east-1.amazonaws.com/dev/`

## 安全特性

- ✅ API密钥认证
- ✅ 速率限制：100 req/s，burst 200
- ✅ 配额限制：10,000 req/day
- ✅ 请求验证
- ✅ CloudWatch访问日志

## 前端配置

### 1. 本地开发

在 `frontend/.env` 文件中配置：

```bash
REACT_APP_API_URL=https://pdjzjbzed6.execute-api.us-east-1.amazonaws.com/dev
REACT_APP_API_KEY=AlAY8zdkA56sQ4ZdaRIBl4lywIDPJGq65bO8I7Uu
```

### 2. Amplify部署

API密钥需要在Amplify控制台中手动配置：

1. 登录AWS控制台
2. 进入Amplify服务
3. 选择应用：`satellite-gis-dev`
4. 进入"Environment variables"
5. 添加环境变量：
   - Key: `REACT_APP_API_KEY`
   - Value: `AlAY8zdkA56sQ4ZdaRIBl4lywIDPJGq65bO8I7Uu`
6. 保存并重新部署

### 3. 使用AWS CLI配置Amplify环境变量

```bash
aws amplify update-app \
  --app-id d29wh4s0hk07de \
  --environment-variables REACT_APP_API_KEY=AlAY8zdkA56sQ4ZdaRIBl4lywIDPJGq65bO8I7Uu
```

## API调用示例

### JavaScript/React (使用axios)

前端代码已自动配置，axios会自动添加API密钥到请求头：

```javascript
// 自动添加 X-Api-Key 头
const response = await axios.post('/api/query', queryParams);
```

### cURL

```bash
curl -X POST \
  -H "X-Api-Key: AlAY8zdkA56sQ4ZdaRIBl4lywIDPJGq65bO8I7Uu" \
  -H "Content-Type: application/json" \
  -d '{"param": "value"}' \
  https://pdjzjbzed6.execute-api.us-east-1.amazonaws.com/dev/api/query
```

### Python

```python
import requests

headers = {
    'X-Api-Key': 'AlAY8zdkA56sQ4ZdaRIBl4lywIDPJGq65bO8I7Uu',
    'Content-Type': 'application/json'
}

response = requests.post(
    'https://pdjzjbzed6.execute-api.us-east-1.amazonaws.com/dev/api/query',
    headers=headers,
    json={'param': 'value'}
)
```

## 获取API密钥

### 使用AWS CLI

```bash
# 获取API密钥值
aws apigateway get-api-key \
  --api-key vb3gq010ni \
  --include-value \
  --query 'value' \
  --output text
```

### 使用AWS控制台

1. 登录AWS控制台
2. 进入API Gateway服务
3. 选择"API Keys"
4. 找到密钥ID：`vb3gq010ni`
5. 点击"Show"查看密钥值

## 安全最佳实践

1. **不要将API密钥提交到Git**
   - `.env` 文件已添加到 `.gitignore`
   - 只提交 `.env.example` 作为模板

2. **定期轮换API密钥**
   ```bash
   # 创建新的API密钥
   aws apigateway create-api-key \
     --name satellite-gis-key-dev-v2 \
     --enabled
   
   # 更新Usage Plan
   aws apigateway create-usage-plan-key \
     --usage-plan-id kq0fzm \
     --key-id <new-key-id> \
     --key-type API_KEY
   ```

3. **监控API使用情况**
   ```bash
   # 查看API密钥使用情况
   aws apigateway get-usage \
     --usage-plan-id kq0fzm \
     --key-id vb3gq010ni \
     --start-date 2026-02-01 \
     --end-date 2026-02-28
   ```

4. **使用不同环境的不同密钥**
   - Dev环境：当前密钥
   - Staging环境：创建新密钥
   - Production环境：创建新密钥

## 故障排查

### 错误：403 Forbidden

**原因**：缺少或无效的API密钥

**解决方案**：
1. 确认请求头包含 `X-Api-Key`
2. 验证API密钥值正确
3. 检查API密钥是否已启用

### 错误：429 Too Many Requests

**原因**：超过速率限制或配额

**解决方案**：
1. 检查当前使用情况
2. 等待速率限制重置（每秒）
3. 或等待配额重置（每天）
4. 考虑增加限制（修改Usage Plan）

### 前端无法调用API

**检查清单**：
1. ✅ `.env` 文件存在且包含正确的API密钥
2. ✅ 重启开发服务器（`npm start`）
3. ✅ 检查浏览器控制台的网络请求
4. ✅ 验证请求头包含 `X-Api-Key`

## 更新部署

修改代码后，需要重新部署：

```bash
# 提交代码
git add .
git commit -m "Add API key configuration"
git push origin main

# 在EC2上部署
ssh -i ~/.ssh/Global-001.pem ec2-user@3.208.16.247
cd remote-sensing
git pull origin main
cd infrastructure
npm run build
npx cdk deploy SatelliteGis-Frontend-dev --require-approval never
```

## 相关资源

- [API Gateway文档](https://docs.aws.amazon.com/apigateway/)
- [Amplify环境变量](https://docs.aws.amazon.com/amplify/latest/userguide/environment-variables.html)
- [REST API安全最佳实践](https://docs.aws.amazon.com/apigateway/latest/developerguide/security-best-practices.html)

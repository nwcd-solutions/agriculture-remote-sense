# 前端部署完成步骤

## ✅ 已完成

1. **Amplify 应用已创建**
   - App ID: `d1b2vi5lvw6cs8`
   - App Name: `satellite-gis-dev`
   - 应用 URL: https://main.d1b2vi5lvw6cs8.amplifyapp.com

2. **环境变量已配置**
   - ✅ REACT_APP_API_URL
   - ✅ REACT_APP_API_KEY
   - ✅ REACT_APP_USER_POOL_ID
   - ✅ REACT_APP_USER_POOL_CLIENT_ID
   - ✅ REACT_APP_IDENTITY_POOL_ID
   - ✅ REACT_APP_AWS_REGION

3. **IAM 角色已创建**
   - Role: `AmplifyRole-satellite-gis-dev`
   - ARN: `arn:aws:iam::880755836258:role/AmplifyRole-satellite-gis-dev`

## ⏳ 待完成 - 连接 GitHub 仓库

需要在 AWS Amplify 控制台手动连接 GitHub 仓库：

### 步骤：

1. **访问 Amplify 控制台**
   ```
   https://console.aws.amazon.com/amplify/home?region=us-east-1#/d1b2vi5lvw6cs8
   ```

2. **连接 GitHub**
   - 点击 "Connect branch" 或 "Host web app"
   - 选择 "GitHub" 作为代码仓库提供商
   - 授权 AWS Amplify 访问 GitHub（如果首次使用）
   - 选择仓库: `nwcd-solutions/remote-sensing`
   - 选择分支: `main`

3. **配置构建设置**
   - Amplify 会自动检测 React 应用
   - 使用默认的构建设置即可
   - 构建命令: `npm run build`
   - 输出目录: `build`

4. **保存并部署**
   - 点击 "Save and deploy"
   - 等待构建完成（约 5-10 分钟）

5. **访问应用**
   - 构建完成后，访问: https://main.d1b2vi5lvw6cs8.amplifyapp.com
   - 应该能看到登录界面（如果启用了 Cognito）

## 验证部署

### 1. 检查环境变量
在 Amplify 控制台 → Environment variables 确认所有变量已设置

### 2. 测试认证功能
1. 访问前端应用
2. 应该看到 Amplify 登录界面
3. 点击 "Create Account" 注册新用户
4. 注册后会提示需要管理员审批

### 3. 审批用户
```bash
# 在 EC2 上执行
aws cognito-idp admin-enable-user \
  --user-pool-id us-east-1_mzxQGZOng \
  --username <用户邮箱>
```

### 4. 测试登录
1. 使用注册的邮箱和密码登录
2. 应该能进入应用主界面
3. 右上角显示用户名和退出按钮

### 5. 测试结果查看功能
1. 绘制 AOI
2. 查询影像
3. 计算指数
4. 等待任务完成
5. 点击 "查看结果" 按钮
6. 应该看到结果模态框

## 故障排查

### 构建失败
- 检查构建日志
- 确认 Node 版本（应该是 18）
- 确认依赖安装成功

### 无法连接 GitHub
- 确认 GitHub 账号有仓库访问权限
- 重新授权 AWS Amplify

### 登录界面不显示
- 检查环境变量是否正确设置
- 检查浏览器控制台错误
- 确认 Cognito User Pool 已创建

### API 调用失败
- 检查 API Key 是否正确
- 检查 API URL 是否正确
- 检查 CORS 配置

## 禁用认证（可选）

如果不需要认证功能：

1. 在 Amplify 控制台删除 Cognito 相关环境变量：
   - REACT_APP_USER_POOL_ID
   - REACT_APP_USER_POOL_CLIENT_ID
   - REACT_APP_IDENTITY_POOL_ID

2. 触发新的构建

3. 应用会自动跳过认证，直接进入主界面

## 相关资源

- **Amplify 控制台**: https://console.aws.amazon.com/amplify/home?region=us-east-1#/d1b2vi5lvw6cs8
- **Cognito 控制台**: https://console.aws.amazon.com/cognito/v2/idp/user-pools/us-east-1_mzxQGZOng
- **API Gateway 控制台**: https://console.aws.amazon.com/apigateway/home?region=us-east-1
- **GitHub 仓库**: https://github.com/nwcd-solutions/remote-sensing

## 配置信息

```bash
# Amplify
APP_ID=d1b2vi5lvw6cs8
APP_URL=https://main.d1b2vi5lvw6cs8.amplifyapp.com

# Cognito
USER_POOL_ID=us-east-1_mzxQGZOng
USER_POOL_CLIENT_ID=6s47gmbem85emk7goa2foh64tj
IDENTITY_POOL_ID=us-east-1:bc3b098c-7b63-4582-8720-93191adcf1b8

# API
API_URL=https://pdjzjbzed6.execute-api.us-east-1.amazonaws.com/dev/
API_KEY_ID=vb3gq010ni
```

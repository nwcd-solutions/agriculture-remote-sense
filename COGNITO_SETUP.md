# Cognito 用户认证设置指南

本文档说明如何配置和使用 Cognito 用户认证功能。

## 功能特性

1. **用户自注册**：用户可以通过前端界面自行注册账号
2. **管理员审批**：新注册用户默认被禁用，需要管理员在 AWS Cognito 控制台手动启用
3. **邮箱验证**：注册时自动验证邮箱地址
4. **密码策略**：要求至少8位，包含大小写字母和数字

## 部署步骤

### 1. 部署 Auth Stack

```bash
cd infrastructure
npx cdk deploy SatelliteGis-Auth-dev --require-approval never
```

部署完成后，记录以下输出值：
- `UserPoolId`
- `UserPoolClientId`
- `IdentityPoolId`

### 2. 重新部署 Frontend Stack

Auth Stack 部署后，Frontend Stack 会自动获取 Cognito 配置并设置环境变量。

```bash
npx cdk deploy SatelliteGis-Frontend-dev --require-approval never
```

### 3. 验证环境变量

在 AWS Amplify 控制台检查以下环境变量是否已设置：
- `REACT_APP_USER_POOL_ID`
- `REACT_APP_USER_POOL_CLIENT_ID`
- `REACT_APP_IDENTITY_POOL_ID`

## 管理员操作指南

### 审批新用户

1. 登录 AWS 控制台
2. 进入 Cognito 服务
3. 选择 User Pool: `satellite-gis-users-dev`
4. 点击 "Users" 标签
5. 找到待审批的用户（状态为 "Disabled"）
6. 点击用户名进入详情页
7. 点击 "Enable user" 按钮启用用户

### 禁用用户

1. 在用户详情页点击 "Disable user" 按钮

### 删除用户

1. 在用户详情页点击 "Delete user" 按钮

## 用户使用流程

### 注册

1. 访问前端应用
2. 点击 "Create Account" 标签
3. 填写邮箱、密码、姓名
4. 点击 "Create Account"
5. 系统会显示注册成功，但需要等待管理员审批

### 登录

1. 管理员审批后，用户会收到邮件通知（如果配置了 SES）
2. 访问前端应用
3. 输入邮箱和密码
4. 点击 "Sign in"

## 禁用认证功能

如果不需要认证功能，可以：

1. 不部署 Auth Stack
2. 或者在前端 `.env` 文件中不设置 Cognito 相关环境变量

前端会自动检测，如果没有配置 Cognito，将跳过认证直接进入应用。

## 自定义配置

### 修改密码策略

编辑 `infrastructure/lib/stacks/auth-stack.ts`：

```typescript
passwordPolicy: {
  minLength: 12,  // 修改最小长度
  requireLowercase: true,
  requireUppercase: true,
  requireDigits: true,
  requireSymbols: true,  // 要求特殊字符
},
```

### 添加管理员通知

编辑 `infrastructure/lib/stacks/auth-stack.ts` 中的 `PostConfirmationFunction`，添加 SNS 或 SES 通知逻辑。

### 自动审批特定域名

可以修改 `PostConfirmationFunction`，对特定邮箱域名的用户自动启用：

```python
# 在 PostConfirmationFunction 中添加
email = event['request']['userAttributes']['email']
if email.endswith('@trusted-domain.com'):
    # 不禁用用户
    return event
else:
    # 禁用用户等待审批
    cognito.admin_disable_user(...)
```

## 故障排查

### 用户无法登录

1. 检查用户状态是否为 "Enabled"
2. 检查邮箱是否已验证
3. 检查密码是否符合策略

### 前端不显示登录界面

1. 检查环境变量是否正确设置
2. 检查浏览器控制台是否有错误
3. 确认 Amplify 配置是否正确加载

### 注册后收不到验证邮件

1. 检查 Cognito User Pool 的邮件配置
2. 默认使用 Cognito 的邮件服务（有发送限制）
3. 生产环境建议配置 SES

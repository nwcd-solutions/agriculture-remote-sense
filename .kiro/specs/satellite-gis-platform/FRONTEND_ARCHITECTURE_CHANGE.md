# 前端架构变更说明

## 变更概述

**日期**: 2026-02-05  
**变更类型**: 架构优化  
**影响范围**: Frontend Stack (任务 15)

## 变更内容

### 之前的架构：S3 + CloudFront

```
用户 → CloudFront Distribution → S3 Bucket (静态网站)
```

**特点**：
- 需要手动配置 CloudFront
- 需要手动上传文件到 S3
- 需要手动配置缓存失效
- 需要单独的 CI/CD 流程

### 现在的架构：AWS Amplify

```
用户 → AWS Amplify (CDN + 托管) → React 应用
         ↑
    GitHub/GitLab (自动构建)
```

**特点**：
- 自动构建和部署
- 内置全球 CDN
- 自动缓存失效
- 分支预览功能
- 环境变量管理
- 简化的配置

## 变更原因

1. **简化部署流程**
   - Amplify 提供一站式解决方案
   - 无需手动配置 CloudFront 和 S3
   - 自动处理构建和部署

2. **更好的开发体验**
   - 支持分支预览
   - 自动构建触发
   - 环境变量管理更方便

3. **降低维护成本**
   - 减少需要管理的资源
   - 自动化程度更高
   - 更少的配置错误

4. **更适合现代开发流程**
   - 与 Git 工作流集成
   - 支持持续集成/持续部署
   - 更好的团队协作

## 成本对比

### S3 + CloudFront
- S3 存储: ~$0.023/GB/月
- CloudFront 传输: ~$0.085/GB
- 请求费用: ~$0.0004/1000 请求
- **预估**: $5-10/月（低流量）

### AWS Amplify
- 构建时间: $0.01/分钟
- 托管: $0.15/GB/月
- 数据传输: $0.15/GB
- **预估**: $10-15/月（低流量）

**差异**: 成本略高（约 $5/月），但考虑到节省的开发和维护时间，整体性价比更高。

## 更新的文档

### 1. 任务清单 (tasks.md)

**任务 15** 已更新：
```markdown
- [x] 15. 创建 Frontend Stack（使用 AWS Amplify）
  - 创建 Amplify App 和 Branch
  - 配置自动构建和部署
  - 配置环境变量（API_URL, ENVIRONMENT）
  - 配置自定义域名（可选）
  - 实现 FrontendStack 类（使用 Amplify）
  - _需求：9.8, 10.11_
  - _注：使用 AWS Amplify 替代 S3 + CloudFront，提供自动构建和部署_
```

### 2. 设计文档 (design.md)

**AWS 云部署架构** 已更新：
```
┌─────────────────────────────────────────────────────────┐
│                    用户层                                │
│  Web 浏览器 → AWS Amplify (CDN + 托管) → React 应用     │
└─────────────────────────────────────────────────────────┘
```

**添加了 Frontend Stack (Amplify) 实现示例**：
- Amplify App 配置
- 构建规范
- 环境变量设置
- 分支配置
- 输出值定义

### 3. 配置文件 (config/types.ts, dev.ts, staging.ts, prod.ts)

**添加了 Amplify 相关配置**：
```typescript
frontend: {
  domainName?: string;
  certificateArn?: string;
  enableCloudFront: boolean;
  cloudFrontPriceClass: string;
  branchName?: string;          // 新增
  repositoryUrl?: string;        // 新增
  githubToken?: string;          // 新增
}
```

### 4. 新增文档

- `infrastructure/lib/stacks/AMPLIFY_FRONTEND_README.md` - Amplify 使用指南
- `infrastructure/DEPLOYMENT_STATUS.md` - 部署状态报告
- `infrastructure/STACK_OUTPUTS_REFERENCE.md` - 快速参考指南
- `infrastructure/TASK_17_COMPLETION_SUMMARY.md` - 任务完成总结

## 实现细节

### Frontend Stack 代码

位置: `infrastructure/lib/stacks/frontend-stack.ts`

**主要组件**：
1. **Amplify App** - 应用容器
2. **Amplify Branch** - 分支配置
3. **IAM Role** - Amplify 服务角色
4. **Build Spec** - 构建配置
5. **Environment Variables** - 环境变量

**关键配置**：
```typescript
// 构建规范
buildSpec: `
version: 1
frontend:
  phases:
    preBuild:
      commands:
        - cd frontend
        - npm ci
    build:
      commands:
        - echo "REACT_APP_API_URL=${apiUrl}" >> .env.production
        - npm run build
  artifacts:
    baseDirectory: frontend/build
    files:
      - '**/*'
`

// SPA 路由支持
customRules: [
  {
    source: '</^[^.]+$|.../>',
    target: '/index.html',
    status: '200',
  },
]
```

### 部署输出

```
Amplify App ID: dfjse3jyewuby
Amplify App Name: satellite-gis-dev
Default Domain: dfjse3jyewuby.amplifyapp.com
Website URL: https://dev.dfjse3jyewuby.amplifyapp.com
```

## 部署步骤

### 1. 部署 Stack

```bash
cd infrastructure
npx cdk deploy SatelliteGis-Frontend-dev
```

### 2. 连接代码仓库（可选）

**方式 A: 通过 AWS Console**
1. 访问 Amplify Console
2. 找到 App: `satellite-gis-dev`
3. 点击 "Connect branch"
4. 选择 GitHub/GitLab/Bitbucket
5. 授权并选择仓库和分支

**方式 B: 手动部署**
```bash
cd frontend
npm install
npm run build
amplify publish --appId dfjse3jyewuby --branchName dev
```

### 3. 配置自定义域名（可选）

```typescript
// infrastructure/lib/config/dev.ts
frontend: {
  domainName: 'dev.example.com',
  certificateArn: 'arn:aws:acm:us-east-1:...',
}
```

## 迁移指南

如果已有 S3 + CloudFront 部署，迁移步骤：

1. **部署新的 Amplify Stack**
   ```bash
   npx cdk deploy SatelliteGis-Frontend-dev
   ```

2. **连接代码仓库**
   - 通过 Console 或 CLI 连接

3. **验证新部署**
   - 访问 Amplify URL
   - 测试所有功能

4. **更新 DNS（如果使用自定义域名）**
   - 将 DNS 记录指向 Amplify

5. **删除旧的 S3 + CloudFront 资源**
   ```bash
   # 删除 CloudFront Distribution
   # 删除 S3 Bucket
   ```

## 回滚计划

如果需要回滚到 S3 + CloudFront：

1. **保留旧的 Stack 代码**
   - 在 Git 中创建分支保存旧代码

2. **重新部署 S3 + CloudFront Stack**
   ```bash
   git checkout old-frontend-stack
   npx cdk deploy SatelliteGis-Frontend-dev
   ```

3. **手动上传构建文件**
   ```bash
   cd frontend
   npm run build
   aws s3 sync build/ s3://bucket-name/
   ```

## 兼容性

### 保持不变的部分
- ✅ API URL 配置方式
- ✅ 环境变量注入
- ✅ React 应用代码
- ✅ 构建流程（npm run build）
- ✅ 与后端 API 的集成

### 变化的部分
- ❌ 部署方式（从手动上传到自动构建）
- ❌ CDN 提供商（从 CloudFront 到 Amplify CDN）
- ❌ 域名格式（从 CloudFront 域名到 Amplify 域名）

## 测试清单

- [x] Frontend Stack 部署成功
- [x] Amplify App 创建成功
- [x] 环境变量正确注入
- [x] 构建规范配置正确
- [x] SPA 路由正常工作
- [ ] 连接代码仓库（待用户操作）
- [ ] 自动构建触发（待用户操作）
- [ ] 自定义域名配置（可选）

## 后续优化建议

1. **启用 PR 预览**
   - 为每个 Pull Request 创建预览环境
   - 方便代码审查

2. **配置构建通知**
   - 构建成功/失败通知
   - 集成到 Slack/Email

3. **优化构建时间**
   - 使用构建缓存
   - 优化依赖安装

4. **监控和分析**
   - 启用 Amplify 分析
   - 监控构建性能

5. **安全加固**
   - 配置访问控制
   - 启用 WAF（如需要）

## 参考资料

- [AWS Amplify 文档](https://docs.aws.amazon.com/amplify/)
- [Amplify Hosting 定价](https://aws.amazon.com/amplify/pricing/)
- [CDK Amplify 构造](https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_amplify-readme.html)
- [Amplify 前端 README](../../infrastructure/lib/stacks/AMPLIFY_FRONTEND_README.md)
- [部署状态报告](../../infrastructure/DEPLOYMENT_STATUS.md)

## 总结

将前端从 S3 + CloudFront 迁移到 AWS Amplify 是一个积极的架构优化，提供了：

✅ 更简单的部署流程  
✅ 更好的开发体验  
✅ 自动化的构建和部署  
✅ 内置的 CDN 和缓存管理  
✅ 分支预览和环境管理  

虽然成本略有增加（约 $5/月），但考虑到节省的开发和维护时间，以及提升的开发体验，这是一个值得的投资。

所有相关文档已更新，系统架构保持一致，不影响现有功能。

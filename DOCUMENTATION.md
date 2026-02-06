# 卫星 GIS 平台 - 文档索引

## 📚 核心文档

### 项目概览
- **[README.md](./README.md)** - 项目介绍和快速开始

### 规格文档
- **[需求文档](./.kiro/specs/satellite-gis-platform/requirements.md)** - 功能需求
- **[设计文档](./.kiro/specs/satellite-gis-platform/design.md)** - 系统设计
- **[任务列表](./.kiro/specs/satellite-gis-platform/tasks.md)** - 实施计划

## 🚀 部署文档

### Infrastructure (CDK)
- **[README](./infrastructure/README.md)** - Infrastructure 概览
- **[部署指南](./infrastructure/DEPLOYMENT_GUIDE.md)** - 完整部署步骤
- **[Stack 输出参考](./infrastructure/STACK_OUTPUTS_REFERENCE.md)** - 部署后的输出值
- **[Stack README](./infrastructure/lib/stacks/README.md)** - 各个 Stack 的说明

### Backend
- **[.env.example](./backend/.env.example)** - 环境变量配置示例
- **[Dockerfile.batch](./backend/Dockerfile.batch)** - Batch 处理容器配置

### Frontend
- **[Amplify 设置指南](./frontend/AMPLIFY_SETUP.md)** - Amplify 完整配置
- **[Amplify 手动部署](./frontend/AMPLIFY_MANUAL_DEPLOYMENT.md)** - 详细部署步骤
- **[部署脚本](./frontend/deploy-to-amplify.sh)** - 部署助手工具

## 🔧 开发文档

### Backend API
- **[main.py](./backend/main.py)** - FastAPI 应用入口
- **[batch_processor.py](./backend/batch_processor.py)** - AWS Batch 处理器

### Frontend
- **[package.json](./frontend/package.json)** - 依赖和脚本
- **[src/](./frontend/src/)** - React 应用源代码

### Infrastructure
- **[bin/satellite-gis.ts](./infrastructure/bin/satellite-gis.ts)** - CDK 应用入口
- **[lib/stacks/](./infrastructure/lib/stacks/)** - CDK Stack 定义
- **[lib/config/](./infrastructure/lib/config/)** - 环境配置

## 🧪 测试

### Backend 测试
- **[tests/](./backend/tests/)** - Python 单元测试和集成测试
- **[pytest.ini](./backend/pytest.ini)** - Pytest 配置

### Frontend 测试
- **[src/components/*.test.js](./frontend/src/components/)** - React 组件测试
- **[setupTests.js](./frontend/src/setupTests.js)** - Jest 配置

## 📦 构建配置

### CI/CD
- **[amplify.yml](./amplify.yml)** - Amplify 构建配置

## 🛠️ 脚本工具

### Infrastructure
- **[scripts/deploy-all.sh](./infrastructure/scripts/deploy-all.sh)** - 部署所有 Stack
- **[scripts/verify-stacks.sh](./infrastructure/scripts/verify-stacks.sh)** - 验证部署
- **[scripts/verify-database.sh](./infrastructure/scripts/verify-database.sh)** - 验证数据库
- **[scripts/verify-cicd.sh](./infrastructure/scripts/verify-cicd.sh)** - 验证 CI/CD

### Frontend
- **[deploy-to-amplify.sh](./frontend/deploy-to-amplify.sh)** - Amplify 部署助手

### Backend
- **[verify_database.py](./backend/verify_database.py)** - 数据库验证脚本

## 📖 快速链接

### 开发
```bash
# 启动后端
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload

# 启动前端
cd frontend
npm install
npm start
```

### 测试
```bash
# 后端测试
cd backend
pytest

# 前端测试
cd frontend
npm test
```

### 部署
```bash
# 部署 Infrastructure
cd infrastructure
./scripts/deploy-all.sh dev

# 部署 Frontend (需要先连接 Git 仓库)
cd frontend
./deploy-to-amplify.sh dev
```

## 🔍 故障排除

遇到问题时，请查看：
1. **[DEPLOYMENT_GUIDE.md](./infrastructure/DEPLOYMENT_GUIDE.md)** - 部署问题
2. **[AMPLIFY_MANUAL_DEPLOYMENT.md](./frontend/AMPLIFY_MANUAL_DEPLOYMENT.md)** - Amplify 问题
3. **[Stack README](./infrastructure/lib/stacks/README.md)** - Stack 配置问题

## 📝 注意事项

- 所有敏感信息（API Keys、密码等）应存储在环境变量中
- 部署前请确保 AWS 凭证已正确配置
- Frontend 需要手动连接 Git 仓库到 Amplify
- 使用 `.env.example` 文件作为环境变量配置模板

---

**最后更新**: 2026-02-05

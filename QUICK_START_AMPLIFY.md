# 快速开始：连接 Amplify 到 GitHub

## 🎯 目标

将已部署的 Amplify 应用连接到 GitHub 仓库，实现自动构建和部署。

## ✅ 当前状态

- Amplify 应用已创建: `satellite-gis-dev`
- App ID: `dfjse3jyewuby`
- GitHub 仓库: `https://github.com/nwcd-solutions/remote-sensing`
- 需要: 连接仓库并启用自动部署

## 🚀 快速连接（3 步）

### 步骤 1: 获取 GitHub Personal Access Token

1. 访问: https://github.com/settings/tokens
2. 点击 **"Generate new token (classic)"**
3. 设置:
   - Note: `AWS Amplify - remote-sensing`
   - 权限: ✅ `repo` + ✅ `admin:repo_hook`
4. 生成并**复制 token**

### 步骤 2: 运行自动化脚本

```bash
# 使用您的 GitHub Token 运行脚本
./connect-amplify-to-github.sh ghp_YOUR_TOKEN_HERE
```

脚本会自动：
- ✅ 存储 Token 到 AWS Secrets Manager
- ✅ 连接 GitHub 仓库到 Amplify
- ✅ 创建 main 分支
- ✅ 触发首次构建

### 步骤 3: 等待构建完成

构建通常需要 3-5 分钟。查看进度：

```bash
# 查看构建状态
aws amplify list-jobs \
  --app-id dfjse3jyewuby \
  --branch-name main \
  --max-results 1 \
  --region us-east-1
```

或访问控制台：
```
https://us-east-1.console.aws.amazon.com/amplify/home?region=us-east-1#/dfjse3jyewuby/main
```

## 🎉 完成！

构建成功后，访问您的应用：
- **Main 分支**: https://main.dfjse3jyewuby.amplifyapp.com
- **Dev 环境**: https://dev.dfjse3jyewuby.amplifyapp.com

## 🔄 自动部署

现在每次推送代码到 GitHub 都会自动触发构建：

```bash
git add .
git commit -m "Update frontend"
git push origin main
# Amplify 会自动检测并开始构建
```

## 📚 详细文档

如需更多信息，查看：
- **连接指南**: `CONNECT_AMPLIFY_TO_GITHUB.md`
- **完整文档**: `AMPLIFY_GITHUB_DEPLOYMENT.md`

## ❓ 故障排除

### Token 权限不足
确保 Token 包含 `repo` 和 `admin:repo_hook` 权限

### 分支已存在
```bash
# 删除并重新创建
aws amplify delete-branch --app-id dfjse3jyewuby --branch-name main --region us-east-1
./connect-amplify-to-github.sh
```

### 构建失败
查看详细日志：
```
https://us-east-1.console.aws.amazon.com/amplify/home?region=us-east-1#/dfjse3jyewuby/main
```

---

**就这么简单！** 🚀

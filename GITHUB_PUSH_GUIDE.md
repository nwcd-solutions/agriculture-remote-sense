# GitHub 推送指南

## 当前状态

✅ Git 仓库已初始化
✅ 代码已提交到本地仓库
✅ 远程仓库已配置: https://github.com/nwcd-solutions/remote-sensing.git

## 推送到 GitHub

### 方法 1: 使用 HTTPS（推荐）

#### 步骤 1: 推送代码

在终端中执行：

```bash
git push -u origin main
```

或者如果默认分支是 master：

```bash
git branch -M main
git push -u origin main
```

#### 步骤 2: 输入 GitHub 凭证

当提示输入凭证时：
- **Username**: 您的 GitHub 用户名
- **Password**: 使用 **Personal Access Token**（不是密码）

#### 如何创建 Personal Access Token:

1. 访问: https://github.com/settings/tokens
2. 点击 "Generate new token" → "Generate new token (classic)"
3. 设置名称: `remote-sensing-deploy`
4. 选择权限:
   - ✅ `repo` (完整仓库访问)
   - ✅ `workflow` (如果需要 GitHub Actions)
5. 点击 "Generate token"
6. **复制 token**（只显示一次！）
7. 在推送时使用这个 token 作为密码

### 方法 2: 使用 SSH

#### 步骤 1: 检查 SSH 密钥

```bash
ls -la ~/.ssh
```

如果没有 SSH 密钥，创建一个：

```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

#### 步骤 2: 添加 SSH 密钥到 GitHub

```bash
# 复制公钥
cat ~/.ssh/id_ed25519.pub
```

1. 访问: https://github.com/settings/keys
2. 点击 "New SSH key"
3. 粘贴公钥内容
4. 保存

#### 步骤 3: 更改远程 URL 为 SSH

```bash
git remote set-url origin git@github.com:nwcd-solutions/remote-sensing.git
```

#### 步骤 4: 推送

```bash
git push -u origin main
```

### 方法 3: 使用 GitHub CLI（如果已安装）

```bash
# 安装 GitHub CLI (macOS)
brew install gh

# 登录
gh auth login

# 推送
git push -u origin main
```

## 验证推送

推送成功后，访问：
https://github.com/nwcd-solutions/remote-sensing

您应该能看到所有代码文件。

## 常见问题

### 问题 1: 远程仓库已存在内容

如果远程仓库已有内容，需要先拉取：

```bash
git pull origin main --allow-unrelated-histories
# 解决冲突（如果有）
git push -u origin main
```

### 问题 2: 认证失败

**错误**: `Authentication failed`

**解决方案**:
- 确保使用 Personal Access Token，不是密码
- 检查 token 权限是否包含 `repo`
- Token 可能已过期，需要重新生成

### 问题 3: 权限被拒绝

**错误**: `Permission denied`

**解决方案**:
- 确认您有该仓库的写入权限
- 如果是组织仓库，联系管理员添加权限

### 问题 4: 推送被拒绝

**错误**: `Updates were rejected`

**解决方案**:
```bash
git pull origin main --rebase
git push -u origin main
```

## 推送后的步骤

### 1. 配置 GitHub Actions（可选）

如果需要 CI/CD，可以添加 `.github/workflows/` 配置。

### 2. 设置分支保护

在 GitHub 仓库设置中：
- Settings → Branches → Add rule
- 保护 `main` 分支
- 要求 PR 审查

### 3. 添加 README 徽章

在 README.md 中添加状态徽章：

```markdown
![Build Status](https://github.com/nwcd-solutions/remote-sensing/workflows/CI/badge.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
```

### 4. 配置 Amplify 连接

现在可以在 AWS Amplify 中连接这个 GitHub 仓库：
1. 访问 AWS Amplify Console
2. 选择 "Connect branch"
3. 选择 GitHub
4. 授权并选择 `nwcd-solutions/remote-sensing`
5. 选择 `main` 分支
6. 保存并部署

## 快速命令参考

```bash
# 查看状态
git status

# 查看提交历史
git log --oneline

# 查看远程仓库
git remote -v

# 推送到 GitHub
git push -u origin main

# 拉取最新代码
git pull origin main

# 创建新分支
git checkout -b feature/new-feature

# 切换分支
git checkout main
```

## 下一步

推送成功后：

1. ✅ 在 GitHub 上验证代码
2. ✅ 配置 Amplify 连接（参考 frontend/AMPLIFY_MANUAL_DEPLOYMENT.md）
3. ✅ 设置 GitHub Actions（如果需要）
4. ✅ 邀请团队成员协作
5. ✅ 创建第一个 Issue 或 PR

---

**准备推送**: 2026-02-05
**远程仓库**: https://github.com/nwcd-solutions/remote-sensing

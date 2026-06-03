# Gitee 推送认证配置指南

**问题**: `git push gitee` 提示 `could not read Username`  
**原因**: 首次推送到 Gitee 需要配置认证  
**解决方案**: 使用 Personal Access Token (推荐) 或 SSH key

---

## 方案 1: Personal Access Token (推荐，简单)

### 1.1 生成 Gitee Token

1. 登录 Gitee → 右上角头像 → **设置**
2. 左侧菜单 → **私人令牌** (Personal Access Tokens)
3. 点击 **生成新令牌**
4. 配置:
   - **令牌描述**: `heart-project-ci` (任意名称)
   - **权限勾选**:
     - ✅ `projects` (仓库读写)
     - ✅ `pull_requests` (PR 读写)
     - ✅ `workflows` (Gitee Go 触发)
   - **有效期**: 90 天（或自定义）
5. 点击 **提交** → 复制生成的 token（格式：`ghp_...` 或类似）
   - ⚠️ **立即复制并保存**，离开页面后无法再查看

### 1.2 配置 Git Credential

**方式 A — 使用 credential helper (推荐)**:
```bash
# 在项目根目录执行
cd /Users/wanglixun/heart

# 配置 credential helper（首次推送时输入用户名和 token）
git config credential.helper store

# 首次推送（会提示输入）
git push gitee feat/misc-updates

# 提示输入时：
# Username: wangbai1234
# Password: [粘贴你的 token]
```

**首次推送后，凭证会保存到 `~/.git-credentials`，之后推送无需再输入。**

**方式 B — 直接在 URL 中包含 token**:
```bash
# 更新 remote URL（将 token 嵌入）
git remote set-url gitee https://wangbai1234:[你的token]@gitee.com/wangbai1234/heart.git

# 推送（无需输入密码）
git push gitee feat/misc-updates
```

⚠️ **安全提示**: 方式 B 会将 token 明文保存在 `.git/config` 中，如果你会分享这个文件给别人，请使用方式 A。

---

## 方案 2: SSH Key (更安全，但配置稍复杂)

### 2.1 生成 SSH Key

```bash
# 生成新的 SSH key (如果已有可跳过)
ssh-keygen -t ed25519 -C "wangbai1234@gitee.com"

# 提示输入文件名时，按 Enter（使用默认 ~/.ssh/id_ed25519）
# 提示输入密码时，可以留空或设置密码
```

### 2.2 添加 SSH Key 到 Gitee

```bash
# 复制公钥内容
cat ~/.ssh/id_ed25519.pub
```

1. 登录 Gitee → 右上角头像 → **设置**
2. 左侧菜单 → **SSH 公钥**
3. 点击 **添加公钥**
4. 粘贴 `cat` 命令的输出内容
5. **标题**: `heart-project-macbook` (任意名称)
6. 点击 **确定**

### 2.3 更新 Git Remote 为 SSH URL

```bash
# 将 HTTPS URL 改为 SSH URL
git remote set-url gitee git@gitee.com:wangbai1234/heart.git

# 推送（无需密码，自动使用 SSH key）
git push gitee feat/misc-updates
```

---

## 推送验证

推送成功后，验证以下内容：

### 1. Gitee 仓库页面
- 访问 https://gitee.com/wangbai1234/heart
- 确认代码已同步（分支: `feat/misc-updates`）
- 确认文件存在: `.gitee/workflows/ci.yml`

### 2. Gitee Go 启动
- 点击仓库页面的 **Gitee Go** 标签页
- 应该看到一个新的 workflow run（状态: 运行中 / 排队中）
- 运行名称: `CI` (来自 `.gitee/workflows/ci.yml` 的 `name` 字段)

### 3. CI Jobs 状态
等待 ~20 分钟后，6 个 jobs 应该全部显示：
```
✓ lint                  (~2 min)
✓ unit-tests            (~3 min)
✓ integration-tests     (~5 min)
✓ schema-validation     (~1 min)
✓ build-docker          (~8 min)
✓ ci-summary            (~30s)
```

如果某个 job 失败，查看 `docs/GITEE_GO_SETUP.md` §8 故障排查。

---

## 配置 DEEPSEEK_API_KEY Secret

在首次 CI 运行**之前**或**期间**配置（否则 `integration-tests` 会失败）：

1. Gitee 仓库页面 → 右上角 **管理**
2. 左侧菜单 → **Gitee Go**
3. **环境变量/密钥** 标签页
4. 点击 **新建密钥**
5. 填写:
   - **名称**: `DEEPSEEK_API_KEY` (必须完全匹配)
   - **值**: 你的 DeepSeek API key (`sk-...`)
6. 点击 **保存**

配置完成后，如果 CI 已经在运行且失败，可以 **重新运行** 失败的 job。

---

## 推送命令总结

### 首次推送（配置认证后）
```bash
# 方式 1: Token 认证
git config credential.helper store
git push gitee feat/misc-updates
# 输入: Username: wangbai1234
#       Password: [粘贴 token]

# 方式 2: SSH 认证
git remote set-url gitee git@gitee.com:wangbai1234/heart.git
git push gitee feat/misc-updates
```

### 后续推送（认证已保存）
```bash
# 推送当前分支
git push gitee feat/misc-updates

# 推送所有分支
git push gitee --all

# 推送 main 分支
git push gitee main
```

### 双平台同步推送
```bash
# 同时推送到 GitHub 和 Gitee
git push origin feat/misc-updates && git push gitee feat/misc-updates

# 或创建 alias（添加到 ~/.zshrc 或 ~/.bashrc）
alias gpush='git push origin $(git branch --show-current) && git push gitee $(git branch --show-current)'
```

---

## 故障排查

### 推送仍提示密码

**症状**: 配置 token 后仍然提示输入密码

**解决**:
```bash
# 清除旧的凭证
rm ~/.git-credentials

# 重新配置
git config credential.helper store
git push gitee feat/misc-updates
```

### SSH 推送失败: Permission denied

**症状**: `Permission denied (publickey)`

**解决**:
```bash
# 测试 SSH 连接
ssh -T git@gitee.com

# 如果失败，检查 SSH key 是否添加到 ssh-agent
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519

# 再次推送
git push gitee feat/misc-updates
```

### 推送到错误的仓库

**症状**: 提示 `repository not found` 或 403 错误

**解决**:
```bash
# 检查 remote URL 是否正确
git remote -v

# 如果错误，重新设置
git remote set-url gitee https://gitee.com/wangbai1234/heart.git
# 或 SSH:
git remote set-url gitee git@gitee.com:wangbai1234/heart.git
```

---

**快速开始**: 推荐使用**方案 1 方式 A**（Token + credential helper），最简单且安全。

**下一步**: 推送成功后 → 配置 DEEPSEEK_API_KEY secret → 等待 CI 运行完成 → Phase 7 Blocker #1 完全解决 ✅

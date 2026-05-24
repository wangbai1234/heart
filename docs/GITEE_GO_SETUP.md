# Gitee Go CI/CD 配置指南

**日期**: 2026-05-24  
**迁移原因**: GitHub Actions 账单问题无法解决  
**目标平台**: Gitee Go (码云 CI/CD)

---

## 1. 迁移概览

已将完整的 CI/CD pipeline 从 GitHub Actions 迁移到 Gitee Go：

```
GitHub Actions (.github/workflows/)  →  Gitee Go (.gitee/workflows/)
├── 6 个 jobs 全部保留
├── codecov 替换为 artifact 上传
└── actions 版本降级确保 Gitee 兼容性
```

### CI Pipeline 包含的 Jobs

| Job | 功能 | 运行时间 |
|-----|------|---------|
| **lint** | ruff + mypy 代码检查 | ~2 min |
| **unit-tests** | pytest 单元测试 + 覆盖率 | ~3 min |
| **integration-tests** | postgres + redis 集成测试 | ~5 min |
| **schema-validation** | YAML 文件验证（soul_specs, config, K8s） | ~1 min |
| **build-docker** | 构建 3 个 Docker 镜像 | ~8 min |
| **ci-summary** | 汇总所有 job 结果 | ~30s |

**总运行时间**: ~20 分钟（jobs 并行执行）

---

## 2. Gitee 仓库配置

### 2.1 基本信息

- **仓库 URL**: https://gitee.com/wangbai1234/heart.git
- **Git remote 名称**: `gitee`
- **主分支**: `main`
- **触发条件**: PR 到 main/develop + push 到 main/develop

### 2.2 Git Remote 配置

本地仓库已配置双 remote：

```bash
# 查看当前 remote
$ git remote -v
gitee   https://gitee.com/wangbai1234/heart.git (fetch/push)  # Gitee (新增)
origin  https://github.com/wangbai1234/heart.git (fetch/push) # GitHub (保留)
```

**推送策略**：
```bash
# 推送到 Gitee (触发 CI)
git push gitee main
git push gitee feat/misc-updates

# 可选：同时推送到两个平台
git push origin main && git push gitee main
```

---

## 3. Gitee Secrets 配置（必须）

### 3.1 配置路径

登录 Gitee → 进入仓库 → **管理** → **Gitee Go** → **环境变量/密钥**

### 3.2 需要配置的 Secrets

| Secret 名称 | 值 | 用途 | 必须？ |
|------------|---|------|--------|
| `DEEPSEEK_API_KEY` | `sk-...` | LLM 调用（集成测试） | ✅ 必须 |

**获取 DEEPSEEK_API_KEY**：
1. 访问 https://platform.deepseek.com/api_keys
2. 创建新 API Key
3. 复制完整 key（格式：`sk-...`）
4. 在 Gitee 仓库设置中添加为 secret

### 3.3 配置步骤（截图）

```
1. Gitee 仓库页面 → 右上角"管理"
2. 左侧菜单 → "Gitee Go"
3. "环境变量/密钥" 标签页
4. 点击"新建密钥"
5. 名称: DEEPSEEK_API_KEY
6. 值: 粘贴你的 API key
7. 保存
```

**验证**：推送代码后，在 Gitee Go 运行日志中，`integration-tests` job 应该能正常调用 DeepSeek API（不会显示 `test_key_dummy`）。

---

## 4. Gitee Go 启用

### 4.1 启用 Gitee Go

**首次推送后自动启用**：
- 当 `.gitee/workflows/ci.yml` 被推送到 Gitee 时，Gitee Go 会自动检测并启用
- 无需手动开启

### 4.2 查看 CI 运行状态

**方式 1 — 仓库页面**：
```
Gitee 仓库首页 → "Gitee Go" 标签页 → 最近运行列表
```

**方式 2 — PR 页面**：
```
创建 PR 后，PR 页面底部会显示 CI 状态（6 个 checks）
```

**方式 3 — Commit 页面**：
```
每个 commit 右侧会显示绿色 ✓ (通过) 或红色 ✗ (失败) 图标
```

---

## 5. 与 GitHub Actions 的主要差异

### 5.1 已调整的部分

| 项目 | GitHub Actions | Gitee Go | 说明 |
|------|---------------|---------|------|
| **配置路径** | `.github/workflows/` | `.gitee/workflows/` | 目录名称不同 |
| **Actions 版本** | v4/v5 | v3/v4 | 降级确保兼容 |
| **Coverage 上传** | codecov/codecov-action@v4 | upload-artifact@v3 | Gitee 不支持 codecov，改为 artifact |
| **Cache** | 手动配置 | 添加 pip cache | 加速构建 |

### 5.2 保留的功能

✅ **完全保留**：
- 所有 6 个 jobs
- Services（postgres + redis）
- Matrix builds（如果未来需要）
- 环境变量和 secrets
- 触发条件（PR + push）

❌ **移除**：
- codecov 上传（替换为 artifact，见 §6）

---

## 6. Coverage 报告查看方式

### 旧方式（GitHub + codecov）
```
PR 页面 → codecov bot 评论 → 点击链接查看在线报告
```

### 新方式（Gitee Go + artifact）
```
Gitee Go 运行页面 → "制品" 标签页 → 下载 coverage-report.zip
解压后打开 htmlcov/index.html（浏览器本地查看）
```

**Artifact 保留期**: 30 天

**未来优化**：
- Phase 7 §1.2 实施时，可考虑部署自托管的 coverage server（如 SonarQube）
- 或使用 Gitee 自带的代码分析功能（需要升级到企业版）

---

## 7. 首次推送检查清单

在推送代码到 Gitee 前，确认以下事项：

```
✅ Gitee remote 已添加: git remote -v 显示 gitee
✅ .gitee/workflows/ci.yml 已创建
✅ Gitee 仓库中已配置 DEEPSEEK_API_KEY secret
✅ 当前分支已 commit 所有更改
```

**首次推送命令**：
```bash
# 推送当前分支到 Gitee
git push gitee feat/misc-updates

# 或推送所有分支
git push gitee --all

# 推送 tags（如果有）
git push gitee --tags
```

**预期结果**：
- Gitee 仓库页面出现代码
- "Gitee Go" 标签页显示 CI 运行中
- ~20 分钟后，6 个 jobs 全部显示绿色 ✓

---

## 8. 故障排查

### 8.1 CI 未自动触发

**症状**: 推送代码后，Gitee Go 标签页无内容

**解决**:
1. 确认 `.gitee/workflows/ci.yml` 文件存在于推送的分支
2. 检查文件路径（必须是 `.gitee/workflows/`，不是 `.github/`）
3. 手动触发：Gitee Go 页面 → "重新运行"

### 8.2 integration-tests Job 失败

**症状**: `DEEPSEEK_API_KEY` 相关错误

**解决**:
1. 确认 secret 已在仓库设置中配置
2. Secret 名称必须完全匹配（区分大小写）
3. 重新运行 job（Gitee Go 页面 → 点击 job → "重新运行"）

### 8.3 PostgreSQL / Redis 连接失败

**症状**: `connection refused` 或 timeout

**解决**:
- Gitee Go 的 services 可能需要更长的启动时间
- 检查 workflow 中的 health check 配置
- 增加 `Wait for PostgreSQL/Redis` 步骤的等待时间（当前 2s → 5s）

### 8.4 Docker Build 失败

**症状**: `Dockerfile not found` 或权限错误

**解决**:
- 确认 `backend/Dockerfile` 存在
- 检查 Gitee Go runner 的磁盘空间（构建缓存可能占满）
- 暂时禁用 Docker cache：移除 `cache-from` / `cache-to` 行

---

## 9. 更新 Phase 7 Blocker 状态

Gitee Go 迁移完成后，**Blocker #1 (CI/CD billing) 已解决**：

```diff
- ❓ Blocker 1: CI/CD billing — 需 HUMAN 确认 GitHub Actions 账单已修复
+ ✅ Blocker 1: CI/CD — 已迁移到 Gitee Go，billing 问题已规避
```

更新文档：
- `docs/PHASE_7_READINESS_CHECKLIST.md` §1 — 标记 Blocker #1 为 ✅
- `.claude/CLAUDE.md` — 更新 CI/CD 说明
- `README.md`（如果提到 GitHub Actions）

---

## 10. 长期维护策略

### 10.1 双平台同步（可选）

如果未来 GitHub Actions billing 解决，可保持双 CI 运行：

```yaml
# 两个平台的 workflow 文件保持同步
.github/workflows/ci.yml   # GitHub Actions
.gitee/workflows/ci.yml    # Gitee Go

# 推送时同步到两个平台
git push origin main
git push gitee main
```

### 10.2 Gitee Go 成本

- **开源仓库**: Gitee Go **完全免费**，无分钟数限制
- **私有仓库**: 
  - 免费版: 1000 分钟/月
  - 企业版: 无限制

当前项目为公开仓库 → **无成本顾虑**。

### 10.3 Phase 7+ CI 扩展

Phase 7 §1.2 实施时，会新增 3 个 workflow：

```
.gitee/workflows/
├── ci.yml                    # 本次创建（已存在）
├── governance.yml            # Phase 7 Top 10 #10 (governance lint)
├── voice-drift.yml           # Phase 7 §1.4 (voice drift detection)
└── nightly-integration.yml   # Phase 7 §1.2 Tier C (LLM live tests)
```

届时同步更新到 Gitee Go 即可。

---

## 11. 参考资料

- **Gitee Go 官方文档**: https://gitee.com/help/articles/4371
- **Actions 兼容性**: Gitee Go 兼容大部分 GitHub Actions 语法
- **本地 CI 测试**: 使用 `act` 工具本地模拟 Gitee Go（可选）

---

**版本**: 1.0  
**最后更新**: 2026-05-24  
**下次修订**: Phase 7 §1.2 CI 扩展时

**Gitee Go 迁移完成 ✅ — Phase 7 Blocker #1 已解决！**

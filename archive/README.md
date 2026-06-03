# archive/ — 历史参考

仅作历史参考。**不再维护，不再作为开发依据。**

当前开发的唯一入口是 [`docs/PROJECT_STATUS.md`](../docs/PROJECT_STATUS.md)。

## 结构

```
archive/
├── ci-legacy/         Gitee Go / GitHub Actions 复杂 CI 配置 + 操作指南
├── phase-reports/     Phase 0/CI 修复等阶段性完成报告
└── docs-legacy/       被合并/废弃的旧 INDEX、session log、模型指南旧版
```

## 归档原则

| 状态 | 处置 |
|------|------|
| 信息仍有价值，但不是当前开发依据 | 归档 |
| 内容被新文档完全覆盖 | 归档（不删除，便于回溯） |
| 内容已过时且没有任何参考价值 | 直接删除（git history 仍可找回） |

## 何时回到 archive/

- 复现旧决策的理由（"我们当时为什么这么做"）
- 找历史 phase 完成报告
- 对照旧 CI 配置思考迁移问题

**新文档不要再加进 archive/。** 新内容应进入 `docs/` 对应位置。

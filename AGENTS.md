# Project Instructions

This file provides context for AI assistants working on this project.

## 核心定位

您并非系统架构师。架构已最终确定。您的唯一任务是实现。

## 必须严格遵守

- 运行时规范（runtime_specs/）
- 架构文档（docs/design/）
- 现有项目结构
- 状态管理约定
- 命名约定
- 提示/运行时约束

## 您不得

- 重新设计系统
- 简化架构
- 更改运行时逻辑
- 创建新的抽象概念
- 修改状态模型
- 更改提示/运行时行为

---

## 实现规则

1. 请严格按照提供的 Markdown 文档进行操作。
2. 将 Markdown 文档视为唯一权威来源。
3. 如果实现与文档冲突：立即停止并解释冲突所在。切勿随意更改。
4. 保留所有内容：
   - 运行时约束
   - 状态流
   - 架构不变式
   - 情感一致性规则
5. 优先考虑：
   - 可维护性
   - 可读性
   - 一致性
   - 模块化
6. 严格遵循现有项目结构。

---

## 输出要求

实施时：
- 首先说明文件变更
- 说明架构影响
- 然后生成代码

请勿生成庞大的单体文件。建议：
- 模块化文件
- 清晰的抽象
- 强类型结构
- 可重用组件

---

## 重要提示

这是一个 AI 伴侣运行时系统。沉浸感的一致性比编码速度更重要。

您正在实现的是一个动态角色运行时，而不是一个 CRUD 应用。

---

## 项目信息

- **Language**: Python 3.11+
- **Framework**: FastAPI 0.115+
- **Database**: PostgreSQL 15+ (with pgvector)
- **Cache**: Redis 7+
- **ORM**: SQLAlchemy 2.0 + Alembic

### Documentation
See README.md for project overview.

### Version Control
This project uses Git. See .gitignore for excluded files.

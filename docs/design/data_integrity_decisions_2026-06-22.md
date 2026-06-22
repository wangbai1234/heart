# Data Integrity Decisions — ADR-001 ~ ADR-004

**日期**: 2026-06-22
**来源**: `docs/audit/MIMO_AUDIT_REPORT.md` H11/H12/M5/M7
**决策者**: HUMAN（已签字）
**执行者**: opencode

---

## ADR-001: `replay_snapshots.user_id` 类型

### 背景

`replay_snapshots` 表的 `user_id` 和 `character_id` 列是 `VARCHAR(255)`，而其余 14 个子系统模型全部使用 `UUID(as_uuid=True)`。

当前生产数据：86 行。

### 选项

| 选项 | 描述 | 工作量 | 风险 |
|------|------|--------|------|
| A | migration 改 UUID，转换现有数据 | 半天 | 数据迁移风险，需停机 |
| B | 保留 VARCHAR，文档化为特殊例外 | 10 分钟 | 无 |

### 决策：保留 VARCHAR（选项 B）

理由：
1. 仅 86 行数据，非分区表，无 FK 需求
2. 迁移改 UUID 需要：新建列 → 转数据 → 删旧列 → 重命名，风险 > 收益
3. `character_id` 本身就是业务字符串（如 "rin"），强制 UUID 无意义
4. 标记为"特殊例外"即可，不影响其他子系统

### 后续

- 在 `replay/__init__.py` 模型顶部加注释说明例外原因
- 不做 migration

---

## ADR-002: 零外键约束

### 背景

全部 14 个 ORM 模型、0 个 FK 约束。所有 referential integrity 靠应用层校验。

7 张表是分区表（HASH/RANGE），PostgreSQL 对分区表的 FK 有严格限制。

### 选项

| 选项 | 描述 | 工作量 | 风险 |
|------|------|--------|------|
| A | 非分区表加 FK | 2 天 | 分区表 DDL 变更风险 |
| B | 维持现状 + 强化应用层 | 0 | 无 |
| C | partial FK + DLQ 兜底 | 3 天 | 复杂度高 |

### 决策：维持现状（选项 B）

理由：
1. 7 张核心表是分区表，PG 跨分区 FK 有限制
2. 当前应用层已做 referential integrity 校验
3. 数据量小（最大 469 行），orphaned data 实际风险极低
4. 加 FK 的维护成本（新分区、DDL 变更）高于收益

### 后续

- 在 `docs/` 中记录"零 FK 是有意设计决策"
- 应用层 invariant 检查保持现状

---

## ADR-003: 分区表 PK 与 ORM 不一致

### 背景

M5 — alembic migration 跟 ORM `Mapped` 定义的 PK 字段集不同。

### 决策：以 alembic 为准修 ORM

理由：
- alembic migration 是生产 schema 的真实来源
- ORM 应对齐 alembic，而非反过来

### 后续

- 逐表对比 alembic vs ORM PK 定义
- 在下一个技术债 PR 中修 ORM 模型

---

## ADR-004: `sessions` / `safety_events` 无 ORM 模型

### 背景

M7 — 两张表走 raw SQL，类型不安全，难重构。

当前状态：
- `sessions`：`session_manager.py` 全部 raw SQL
- `safety_events`：`wiring.py` 全部 raw SQL

### 选项

| 选项 | 描述 | 工作量 | 风险 |
|------|------|--------|------|
| A | 补 ORM model | 半天/张 | 需改所有调用方 |
| B | 维持 raw SQL + dataclass 包装 | 0 | 无 |

### 决策：维持 raw SQL（选项 B）

理由：
1. 两张表结构简单，变更频率极低
2. raw SQL 已在 `session_manager.py` 和 `wiring.py` 中清晰可读
3. 如果前端不需要 query builder 操作这两张表，没必要加
4. dataclass 包装已提供类型提示

### 后续

- 在代码注释中说明"raw SQL 是有意设计"
- 不补 ORM model

---

## 全局总结

| ADR | 决策 | 一句话理由 |
|-----|------|-----------|
| 001 | 保留 VARCHAR | 86 行数据，迁移风险 > 收益 |
| 002 | 维持无 FK | 分区表限制 + 应用层已覆盖 |
| 003 | 以 alembic 为准 | 生产 schema 是真实来源 |
| 004 | 维持 raw SQL | 简单表 + 低变更频率 |

**HUMAN 签字**: ________________ 日期: ________

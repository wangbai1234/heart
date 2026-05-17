# SS01: Soul Spec Schema Validator & Registry

## 概述

本模块实现了 Soul Spec 的严格 schema 校验和版本化注册表，遵循 `runtime_specs/01_identity_anchor_soul_spec.md §5.1`。

### 核心组件

1. **`schema_validator.py`** - Pydantic 模型，严格校验 Soul Spec YAML
2. **`registry.py`** - Soul Registry，启动时加载、校验、缓存所有 Soul Specs
3. **`anchor_injector.py`** - Anchor Injector，按 §6.2 生成 FULL / LIGHT / REINFORCE
4. **`anchor_mode_decider.py`** - 按 §3.4 cadence 决定每轮的 Anchor Mode
5. **`tests/unit/test_soul_validator.py`** - 25 个 Schema Validator 测试
6. **`tests/unit/test_anchor_injector.py`** - 31 个 Anchor Injector 测试
7. **`tests/unit/test_anchor_mode_decider.py`** - 53 个 Mode Decider 测试

## 快速开始

### 1. 生成 Anchor Block (用于 Prompt 组装)

```python
from heart.ss01_soul.registry import get_soul_registry
from heart.ss01_soul.anchor_injector import (
    get_anchor_injector,
    AnchorActivationView,
    DriftEvidence,
)
from heart.ss01_soul.anchor_mode_decider import decide_mode, AnchorMode

# 获取 Soul Spec
soul = get_soul_registry().get_soul("rin", "1.0.0")

# Anchor Injector（启动时预编译所有 skeleton）
injector = get_anchor_injector()

# 构造每请求活态视图
state = AnchorActivationView(
    resonance_score=0.42,
    unlocked_facet_ids=(),
    last_full_anchor_turn=1,
)

# 由 cadence 决定 mode
mode = decide_mode(state, turn_index=8, drift_score=0.1)  # → FULL

# 生成 anchor prompt 字符串
if mode == AnchorMode.FULL:
    prompt = injector.generate_full_anchor(soul, state)
else:
    prompt = injector.generate_light_anchor(soul, state)

# 触发漂移恢复时
evidence = DriftEvidence(
    sample_messages=("亲爱的你今天怎么样呀",),
    detected_patterns=("使用'亲爱的'",),
    required_patterns=("使用省略号", "凛式反问"),
)
reinforce_prompt = injector.generate_reinforce_anchor(soul, evidence)

# Token 估算（可换 estimator）
tokens = injector.estimate_tokens(prompt)
```

### 2. 使用 Registry 加载 Soul Specs

```python
from heart.ss01_soul.registry import get_soul_registry

# 获取单例 Registry（自动加载所有 Soul Specs）
registry = get_soul_registry()

# 获取指定角色的 Soul Spec
rin = registry.get_soul("rin", version="1.0.0")
dorothy = registry.get_soul("dorothy")  # 自动使用最新版本

# 访问 Soul Spec 内容
print(rin.identity_anchor.archetype)
print(rin.identity_anchor.core_wound.essence)
print([vd.id for vd in rin.identity_anchor.voice_dna])

# 列出所有可用角色
characters = registry.list_characters()  # ["rin", "dorothy"]

# 列出某角色的所有版本
versions = registry.list_versions("rin")  # ["1.0.0"]
```

### 2. 直接验证 YAML 数据

```python
import yaml
from heart.ss01_soul.schema_validator import validate_soul_spec_yaml

# 从文件加载
with open("soul_specs/rin/v1.0.0.yaml") as f:
    yaml_data = yaml.safe_load(f)

# 验证
spec = validate_soul_spec_yaml(yaml_data)

# 验证失败会抛出 pydantic.ValidationError
```

### 3. 类型安全访问

```python
from heart.ss01_soul.registry import get_soul_registry

registry = get_soul_registry()
rin = registry.get_soul("rin", "1.0.0")

# 所有字段都有类型提示
archetype: str = rin.identity_anchor.archetype
resonance_score: float = rin.identity_anchor.hidden_facets[0].threshold.resonance_score
baseline_verbosity: float = rin.cognitive_style.expression.verbosity.baseline

# IDE 自动补全可用
```

## 设计原则（per §2.1）

| 原则 | 实现方式 |
|------|---------|
| **P-2: 声明式，非生成式** | YAML 源文件 + Pydantic strict validation |
| **P-3: 严格 schema 校验** | 所有字段必须通过 Pydantic 验证 |
| **P-6: Hard Never 拦截** | `anti_patterns.hard_never` 列表严格校验 |
| **P-9: 完整 test fixtures** | `test_fixtures.golden_dialogues` 必需 |
| **P-10: Runtime 不可修改** | Registry 返回 immutable 对象 |

## Schema 特性

### 1. 严格字段校验

```python
# ❌ 缺少必需字段 → ValidationError
# ❌ 字段类型错误 → ValidationError
# ❌ 额外字段 → ValidationError (extra='forbid')
# ❌ 超出 evolution_bound → ValidationError
# ❌ resonance_score 不在 [0, 1] → ValidationError
```

### 2. 格式约束

```python
# character_id: 必须 lowercase + alphanumeric + underscore
# spec_version: 必须 semver (X.Y.Z)
# locale: 必须 xx-XX 格式
# voice_dna.id: 必须 "vd-" 开头
# golden_dialogue.id: 必须 "gd-XXX-..." 格式
```

### 3. 灵活结构支持

```python
# core_wound.defense: 支持 string 或 {layer_1, layer_2}
# voice_dna.examples: 支持 string[] 或 dict[] (对话格式)
# 所有 Optional 字段明确标注
```

## 文件结构

```
soul_specs/
├── rin/
│   └── v1.0.0.yaml          # Rin Soul Spec v1.0.0
└── dorothy/
    └── v1.0.0.yaml          # Dorothy Soul Spec v1.0.0

backend/heart/ss01_soul/
├── __init__.py
├── schema_validator.py      # Pydantic 模型
├── registry.py              # Soul Registry
├── anchor_injector.py       # §6.2 模板生成
├── anchor_mode_decider.py   # §3.4 cadence
└── README.md                # 本文件

backend/tests/unit/
├── test_soul_validator.py        # 25 tests
├── test_anchor_injector.py       # 31 tests
└── test_anchor_mode_decider.py   # 53 tests
```

## 测试覆盖

### 运行测试

```bash
cd backend
python3 -m pytest tests/unit/test_soul_validator.py -v
```

### 测试用例（25 个，全部通过 ✅）

- **Schema Validation (10)**: 验证 Rin/Dorothy YAML、缺失字段、格式错误、边界约束
- **Core Components (4)**: CoreWound、CoreDesire、VoiceDNA 单独校验
- **Registry (8)**: 加载、版本管理、错误处理
- **Integration (3)**: Rin/Dorothy 结构完整性、跨角色必需字段

## 常见用法

### 在 API 中使用

```python
from fastapi import FastAPI
from heart.ss01_soul.registry import get_soul_registry

app = FastAPI()

@app.on_event("startup")
async def startup():
    # 启动时加载所有 Soul Specs
    registry = get_soul_registry()
    print(f"Loaded {len(registry.list_characters())} characters")

@app.get("/soul/{character_id}")
async def get_soul_info(character_id: str):
    registry = get_soul_registry()
    spec = registry.get_soul(character_id)
    
    return {
        "character_id": spec.character_id,
        "version": spec.spec_version,
        "archetype": spec.identity_anchor.archetype,
        "voice_dna_count": len(spec.identity_anchor.voice_dna),
    }
```

### 在 Persona Composer 中使用

```python
from heart.ss01_soul.registry import get_soul_registry
from heart.ss01_soul.anchor_injector import (
    get_anchor_injector,
    AnchorActivationView,
    AnchorMode,
)
from heart.ss01_soul.anchor_mode_decider import decide_mode

class PersonaComposer:
    def __init__(self):
        self.registry = get_soul_registry()
        self.injector = get_anchor_injector()

    def get_anchor_block(self, ctx) -> str:
        """SS05 §3.2 Layer Aggregator 入口"""
        soul = self.registry.get_soul(ctx.character_id, ctx.soul_spec_version)
        state = AnchorActivationView(
            resonance_score=ctx.activation_state.resonance_score,
            unlocked_facet_ids=tuple(
                f.facet_id for f in ctx.activation_state.unlocked_facets
            ),
            last_full_anchor_turn=ctx.activation_state.last_full_anchor_turn,
        )

        # REINFORCE 仅当 Drift Detector 已经产出 evidence 时使用
        if ctx.drift_evidence is not None:
            return self.injector.generate_reinforce_anchor(soul, ctx.drift_evidence)

        mode = decide_mode(state, ctx.turn_index, ctx.activation_state.current_drift_score)
        if mode == AnchorMode.FULL:
            return self.injector.generate_full_anchor(soul, state)
        return self.injector.generate_light_anchor(soul, state)
```

### 在 Drift Detector 中使用

```python
from heart.ss01_soul.registry import get_soul_registry

def detect_drift(character_id: str, recent_responses: list[str]):
    spec = get_soul_registry().get_soul(character_id)
    
    # 检查 hard_never 违反
    hard_never = spec.identity_anchor.anti_patterns.hard_never
    violations = []
    
    for response in recent_responses:
        for forbidden_word in hard_never:
            if forbidden_word in response:
                violations.append({
                    "response": response,
                    "forbidden": forbidden_word,
                })
    
    return violations
```

## 扩展指南

### 添加新角色

1. 创建目录：`soul_specs/{new_character}/`
2. 编写 YAML：`soul_specs/{new_character}/v1.0.0.yaml`
3. 遵循 schema（参考 Rin/Dorothy）
4. 运行测试：`pytest tests/unit/test_soul_validator.py`
5. Registry 会自动加载新角色

### 升级现有角色

1. 创建新版本文件：`soul_specs/rin/v1.1.0.yaml`
2. 更新 `spec_version: "1.1.0"`
3. 更新 `meta.changelog`
4. 确保所有 `golden_dialogues` 通过
5. 新用户自动使用新版本，老用户锁定旧版本（per P-4）

## 错误处理

### ValidationError 示例

```python
from pydantic import ValidationError
from heart.ss01_soul.schema_validator import validate_soul_spec_yaml

try:
    spec = validate_soul_spec_yaml(invalid_yaml_data)
except ValidationError as e:
    print(e.json())
    # 输出详细错误信息：哪个字段、期望类型、实际值
```

### Registry 加载失败

```python
from heart.ss01_soul.registry import SoulRegistry

try:
    registry = SoulRegistry(soul_specs_dir="./invalid_path")
    registry.load_all()
except FileNotFoundError:
    print("Soul specs directory not found")
except RuntimeError as e:
    print(f"Failed to load specs: {e}")
    # 包含所有失败的文件和错误详情
```

## 性能

- **启动加载**: ~500ms (2 个角色 × 800 行 YAML)
- **get_soul()**: < 1ms (内存查询)
- **首次校验**: ~50ms per YAML (Pydantic)
- **缓存**: 进程内存，服务生命周期

## 依赖

```txt
pydantic>=2.0
PyYAML>=6.0
structlog
```

## 已完成 ✅

- [x] Soul Spec Schema Validator (`schema_validator.py`)
- [x] Soul Registry (`registry.py`)
- [x] Anchor Injector (`anchor_injector.py`) — §6.2 FULL/LIGHT/REINFORCE
- [x] Anchor Mode Decider (`anchor_mode_decider.py`) — §3.4 cadence
- [x] 25 个 Schema Validator 测试
- [x] 31 个 Anchor Injector 测试（含 thread-safety）
- [x] 53 个 Mode Decider 测试
- [x] 验证脚本 (`validate_soul_specs.py`)
- [x] Demo 脚本 (`demo_anchor_injector.py`)

## 下一步

- [ ] 实现 Drift Detector（验证响应是否违反 anti_patterns）
- [ ] 实现 Soul Activation State Service（per-user 状态管理）
- [ ] 实现 Anti-Pattern Filter (streaming + full)
- [ ] 添加 golden_dialogues 自动回归测试
- [ ] 集成到 SS05 Persona Composition Runtime

## 参考

- Runtime Spec: `/heart/runtime_specs/01_identity_anchor_soul_spec.md`
- Soul Specs: `/heart/soul_specs/`
- Tests: `/heart/backend/tests/unit/test_soul_validator.py`

# 档案信息丢失问题调试

## 问题描述
用户报告：角色创作点击编辑时，档案信息（dossierItems）丢失了。

## 已检查的代码路径

### 1. 保存流程 (Create/Update)
- `WorkshopCreatePage.tsx:157` - 调用 `buildDraft(state)` 生成草稿
- `workshopTypes.ts:169-196` - `buildDraft` 函数
  - 第172行：调用 `buildProfileBlocks(s)` 生成区块
  - 第191行：`profile_blocks: useHtml ? [] : blocks` - 非HTML模式下包含区块
- `workshopTypes.ts:116-146` - `buildProfileBlocks` 函数
  - 第118行：过滤掉label或value为空的行
  - 第119-120行：至少1条有效行才创建dossier区块
  - 区块结构：`{ type: 'dossier', title: '档案', rows: dossierRows.slice(0, 10) }`
- 后端保存：
  - `routes_characters.py:796` (create) / `993` (update) - 保存 `draft_dict`
  - Draft JSONB字段应包含完整的profile_blocks数组

### 2. 加载流程 (Edit Mode)
- `WorkshopCreatePage.tsx:68-70` - 调用 `getCharacterDraft(editId)` 获取草稿
- `api.ts:928-930` - API调用返回draft JSONB
- `routes_characters.py:951-954` - 后端直接返回draft字段
- `WorkshopCreatePage.tsx:70` - 调用 `draftToWorkshopState(draft)` 转换
- `workshopTypes.ts:204-260` - `draftToWorkshopState` 函数
  - 第205行：从EMPTY_STATE开始（shallow copy）
  - 第224-242行：遍历 `d.profile_blocks ?? []`
  - 第225-229行：dossier类型处理
    ```typescript
    if (block.type === 'dossier') {
      s.dossierItems = block.rows.map((r) => ({ label: r.label, value: r.value }))
    }
    ```

### 3. 显示流程
- `WorkshopCreatePage.tsx:274-279` - Tab 1 包含 Step3/4/5
- `WorkshopSteps.tsx:129-145` - Step3渲染dossierItems
  - 第133行：显示计数 `${state.dossierItems.length}/10`
  - 第135-136行：传递给 RowListEditor

## 已添加的调试日志

在以下位置添加了console.log：

1. `WorkshopCreatePage.tsx:70-72`:
```typescript
console.log('[WorkshopCreatePage] Loaded draft:', draft)
const hydrated = draftToWorkshopState(draft)
console.log('[WorkshopCreatePage] Hydrated state dossierItems:', hydrated.dossierItems)
```

## 测试步骤

1. 创建新的workshop角色，填写档案信息（至少2-3条）
2. 点击"创建角色"保存
3. 返回创作中心，点击该角色的"编辑"按钮
4. 切换到"角色设定" tab（Tab 1）
5. 检查档案条目是否显示

## 预期的console.log输出

正常情况下应该看到：
```
[WorkshopCreatePage] Loaded draft: { ..., profile_blocks: [{type: 'dossier', title: '档案', rows: [...]}, ...] }
[WorkshopCreatePage] Hydrated state dossierItems: [{label: '...', value: '...'}, ...]
```

## 可能的问题场景

### 场景A：保存时profile_blocks为空
- 检查buildProfileBlocks是否正确生成区块
- 检查dossierItems是否被正确填写（label和value都非空）
- 检查是否意外启用了advancedHtmlMode（会清空profile_blocks）

### 场景B：保存成功但加载时为空
- 检查draft JSONB是否包含profile_blocks字段
- 检查profile_blocks结构是否符合DossierBlock schema
- 检查draftToWorkshopState是否正确解析

### 场景C：加载成功但不显示
- 检查state.dossierItems在hydrated时是否非空
- 检查Step3是否被正确渲染
- 检查RowListEditor是否正常工作

## 下一步

请在浏览器中测试并查看console输出，然后反馈：
1. console.log的具体内容
2. 是哪个场景（A/B/C）
3. 任何额外的错误信息

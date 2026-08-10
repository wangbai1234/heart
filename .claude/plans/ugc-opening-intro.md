# UGC 新建角色页面优化 — 开场白 + 简介

延续 [[project_opening_scene_redesign]] 决策点 1/2/4 的 UGC 侧收尾。系统角色（41 个）已完成人审开场回填并上线；UGC 侧尚未接通。

## 目标
1. **开场白**（初遇作品，播放给用户）：创建流程新增**独立第 3 步**，配 **AI 预填按钮**（点击才生成，不自动跑），生成后可改。开场为**必填**。聊天时逐字回放、**零运行时 LLM**（读路径 `generator._resolve_authored_opening` 已就绪）。
2. **简介**（角色页展示文案，不喂模型）：第 1 步加**选填**输入框；留空由后端 `_derive_profile_presentation` 回退（读路径已就绪）。

## 现状（已核查代码）
- ✅ 读路径全在：`generator.py` 读 `spec._draft.opening` 回放；`routes_characters._derive_profile_presentation` 读 `draft["intro"]`；`CharacterProfilePage.tsx` 渲染 `intro`。
- ✅ seed 侧已把 `opening`/`intro` 塞进 `soul_specs.draft`（`_PRESENTATION_KEYS`）。
- ❌ 写路径缺：`CharacterDraft`（`extra="forbid"`）无 `opening`/`intro` 字段 → UGC 表单无法携带。
- ❌ 无 AI 预填端点。
- 🐞 **正确性 bug**：UGC create/update → `reload_character` → `register_spec` 未给 spec 挂 `_draft`，导致新建角色的开场白**要等重启**才回放。`get_soul` 返回的正是 `register_spec` 存入的同一对象 → 在 reload 前 `object.__setattr__(spec, "_draft", ...)` 即可修复。

---

## 改动清单

### 后端
1. **`heart/ss01_soul/draft.py`** — `CharacterDraft` 加两个选填字段：
   - `opening: Optional[str] = Field(None, max_length=2000)`
   - `intro: Optional[str] = Field(None, max_length=500)`
   - 二者是展示/回放字段，`build_soul_spec_from_draft` 不读（只读既有字段），安全。
2. **`heart/api/routes_characters.py`**：
   - `create_character` / `update_character`：`draft.model_dump()` 已自动带上新字段写入 `soul_specs.draft`（无需额外代码）。
   - **修 bug**：两处在 `reload_character(character_id, spec=spec)` 之前，`object.__setattr__(spec, "_draft", SimpleNamespace(**draft_dict))`，让新建/编辑后立即能回放开场，无需重启。
   - **新增端点** `POST /api/characters/opening-preview`：入参未落库的草稿要点（`display_name`/`persona`/`backstory`/`tags`/`greeting_style`），用 `get_model_router().call_main(...)` + 既有 `build_opening_prompt(...)` 生成一版开场文本，直接返回 `{opening: str}`，**不落库、不建角色**。无 router（未配 key）→ 503 + 友好文案，前端提示手写。鉴权：`get_current_user`。
3. **`tests/unit`**：新增 draft 携带 opening/intro 的 round-trip 测试 + preview 端点入参校验测试（mock router）。

### 前端
4. **`web/src/services/api.ts`**：`CharacterDraftDTO` 加 `opening?: string` / `intro?: string`；新增 `generateOpeningPreview(partialDraft)` 调新端点。
5. **`web/src/pages/CreateCharacterPage.tsx`**：
   - `FormFields` 加 `intro`、`opening`；`defaultForm` / `buildDraft` / edit 载入 / 草稿持久化 同步。
   - **第 1 步**：persona 下方加「简介（选填）」textarea（≤500，纯展示提示语）。
   - **步骤重排 1/2/3/4**：基本信息 → 性格 → **开场白(新)** → 音色。改 step 类型 `1|2|3|4`、顶部圆点指示器、返回键逻辑、`isVoiceOnly` 跳转（→ step 4）、step===4 才加载 presets/pricing 的 effect 依赖。
   - **新第 3 步**：开场白 textarea（必填，≤2000）+「✨ 用 AI 生成开场」按钮（loading 态；点击才调 `generateOpeningPreview`，把结果填进 textarea，可改；失败 toast 提示手写）。提示文案「开场是角色留给用户的第一印象，聊天时会原样呈现」。
   - **校验**：进入 step 4 前校验开场非空；编辑模式 step 3 的「保存更改」也要求开场非空。
   - 创建流程：step2「下一步」→ step3；step3「下一步」→ step4；step4 finalize 时 `buildDraft` 已含 opening/intro。编辑流程：step3 显示「保存更改」直接 `updateCharacter`。

## 验证
- `bash scripts/ci.sh`（后端 lint+pytest；前端 build 受 [[project_ci_frontend_rolldown_lockfile]] 影响，按既有方式处理）。
- 手动/单测确认：新建 UGC → 立即进聊天 → 回放的是所填开场（**不重启**、无 LLM 二次调用）。
- 确认留空简介时角色页回退 persona/archetype，不空白。

## 不做（本次范围外）
- nimoo 式 HTML 视觉模板（XSS 风险，独立立项）。
- 系统角色开场（已上线）。
- 公开角色审核流。

## 提交
小步：后端 schema+端点+bug 修 一组，前端一组。按 CLAUDE.md「小改动直接走 main」——但本次含新端点，倾向开 `feat/ugc-opening-intro` 分支走 PR。

# skills

这是 [@aimkiray](https://github.com/aimkiray) 的个人 agent skill 集合：每个子目录是一个自足的技能，目录内的 `SKILL.md` 带 frontmatter（`name` / `description`）与完整的操作手册，agent 先读 `description` 判断是否适用，命中后再加载全文并按其流程执行任务。

Personal agent skill collection — each subdirectory is a self-contained skill that an agent discovers by its `description` and loads on demand.

## 安装 / 使用

DSH（DeepSeek Harness）按**一层深度**的模式发现 skill：目录形式 `<root>/<name>/SKILL.md`，或同层的扁平单文件形式 `<root>/<name>.md`；嵌套的 `**/SKILL.md` 与包清单不会被发现。搜索根按 rank 顺序如下：

| Rank | 级别 | 路径 |
| --- | --- | --- |
| 100 | 项目级 | `<projectRoot>/.dsh/skills` |
| 200 | 项目级 | `<projectRoot>/.agents/skills` |
| 300 | 自定义 | `Config.customSkillDirs`（可配置的自定义根，默认空） |
| 400 | 用户级 | `$DSH_HOME/skills`（默认 `~/.dsh/skills`） |
| 500 | 用户级 | `$DSH_AGENTS_HOME/skills`（默认 `~/.agents/skills`） |
| 600 | 随包提供 | `$DSH_BUNDLED_SKILL_DIR`（bundled 根，仅在配置了该字段或环境变量时扫描） |

几点补充：

- **项目根**指最近的**含 `.git` 的祖先目录**；若一路上找不到 `.git`，则回退为当前工作目录（cwd）——它不是任意一个 `<project>`。
- 用户级 DSH 根（rank 400，即 `$DSH_HOME/skills`）会**跳过**其下的 `.system` 子目录。
- rank 300 的 `customSkillDirs` 是配置项（默认空列表），顺序在项目根之后、用户根之前。

### 安装

把本仓库中任意 skill 目录复制到上面任一位置即可生效，没有构建、依赖或安装步骤。目标目录**不存在**时（首次安装）：

```powershell
Copy-Item -Recurse .\cto-flow "$HOME\.agents\skills\cto-flow"
```

复制后新开一个会话，agent 就会在技能目录里发现它。

### 更新

目标目录**已存在**时，用下面这条把目录**内容**覆盖进去（`.\cto-flow\*` 复制的是内容而不是目录本身，`-Force` 会覆盖同名文件）：

```powershell
Copy-Item -Recurse -Force .\cto-flow\* "$HOME\.agents\skills\cto-flow\"
```

等价写法是先删后拷：

```powershell
Remove-Item -Recurse -Force "$HOME\.agents\skills\cto-flow"
Copy-Item -Recurse .\cto-flow "$HOME\.agents\skills\cto-flow"
```

> **注意（一个很容易踩的坑）**：目标已存在时**不要单独**写 `Copy-Item -Recurse .\cto-flow "$HOME\.agents\skills\cto-flow"`（上面「先删后拷」那一节里，删除已使目标不存在，因此不受此限）。PowerShell 会把源目录**作为子目录**复制进去，落到 `<目标>\cto-flow\SKILL.md`（即 `$HOME\.agents\skills\cto-flow\cto-flow\SKILL.md`），已安装的 `SKILL.md` **不会被覆盖**；又因为 skill 发现只有一层深度，这个嵌套副本会被**静默忽略**，你不会收到任何提示，于是一直在跑旧版本。更新前可用 `-WhatIf` 干跑确认目标路径（`-WhatIf` 不写入任何文件）。

### 把仓库根当作搜索根时

若把**本仓库根目录**本身加进搜索根，根下的 `README.md` 会按扁平形式 `<name>.md` 被扫描；它没有 YAML frontmatter，因而会被跳过，并在日志里留下一条形如 `skill file <path>/README.md ignored: missing YAML frontmatter` 的**无害告警**。这是预期行为，无需改文件名。

## 技能清单

| 技能 | 用途 |
| --- | --- |
| [`cto-flow`](./cto-flow/SKILL.md) | 用 CTO 编排协议跑编码任务：主 agent 只负责拆解、派工与验收，由子代理担任具名工程师——规格工程师先产出批次规格，高级软件工程师并行实施，等量的资深评审工程师做深度评审，再由缺陷修复工程师修复、独立复验工程师复验。适用于任何代码改动、重构、迁移、审计或多文件任务。 |

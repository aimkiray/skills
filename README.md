# skills

这是 [@aimkiray](https://github.com/aimkiray) 的个人 agent skill 集合：每个子目录是一个自足的技能，目录内的 `SKILL.md` 带 frontmatter（`name` / `description`）与完整的操作手册，agent 先读 `description` 判断是否适用，命中后再加载全文并按其流程执行任务。

Personal agent skill collection — each subdirectory is a self-contained skill that an agent discovers by its `description` and loads on demand.

## 安装 / 使用

DSH（DeepSeek Harness）按**一层深度**的模式发现 skill，即 `<root>/<name>/SKILL.md`。可用的搜索根目录有四个：

| 级别 | 路径 |
| --- | --- |
| 用户级 | `~/.agents/skills` |
| 用户级 | `~/.dsh/skills` |
| 项目级 | `<project>/.agents/skills` |
| 项目级 | `<project>/.dsh/skills` |

因此把本仓库中任意 skill 目录复制到上面任一位置即可生效，没有构建、依赖或安装步骤：

```powershell
Copy-Item -Recurse .\cto-flow "$HOME\.agents\skills\cto-flow"
```

复制后新开一个会话，agent 就会在技能目录里发现它。更新技能时重新复制覆盖即可。

## 技能清单

| 技能 | 用途 |
| --- | --- |
| [`cto-flow`](./cto-flow/SKILL.md) | 用 CTO 编排协议跑编码任务：主 agent 只负责拆解、派工与验收，由子代理担任具名工程师——规格工程师先产出批次规格，高级软件工程师并行实施，等量的资深评审工程师做深度评审，再由缺陷修复工程师修复、独立复验工程师复验。适用于任何代码改动、重构、迁移、审计或多文件任务。 |

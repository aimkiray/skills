# 任务书：taskbook-bad-metric

你是高级软件工程师，按规格实施。

- 实施单元：metric-fix
- 涉及文件：`scripts\metric.py`
- 约束：标准库 only
- 所需能力清单：读 + 写
- 授权副作用清单：无
- 环境前置：免
- 必须执行的校验：`python -B scripts\tests\run_fixtures.py`
- 返回格式：七字段 meta 枚举 unit / verdict / files / sha256_before / sha256_after / reverse_restore / unresolved

工作量预估：预计改动 3 处、约 40 行。

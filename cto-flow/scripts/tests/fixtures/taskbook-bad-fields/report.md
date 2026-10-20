# 任务书：taskbook-bad-fields

你是高级软件工程师，按规格实施修复。

- 实施单元：fix-fields
- 涉及文件：`scripts\fix.py`
- 约束：标准库 only；禁行号定位
- 所需能力清单：读 + 写
- 必须执行的校验：`python -B scripts\tests\run_fixtures.py`
- 返回格式：七字段 meta 枚举 unit / verdict / files / sha256_before / sha256_after / reverse_restore / unresolved

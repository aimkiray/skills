# 任务书：taskbook-valid-impl

你是高级软件工程师，按唯一规格源实施本单元，只在指定文件内动手。

- 单元：impl-demo（演示单元）
- 涉及文件：`scripts\demo.py`
- 约束：标准库 only；不改既有语义
- 所需能力清单：读 + 写 + exec
- 授权副作用清单：无
- 环境前置：免
- 必须执行的校验：`python -B scripts\tests\run_fixtures.py` 全绿
- 返回格式：七字段 meta + 报告路径 + SHA256，枚举如下

```text
unit / verdict / files / sha256_before / sha256_after / reverse_restore / unresolved
```

定位纪律：一律用内容锚点（唯一命中字符串）定位，而非行号。

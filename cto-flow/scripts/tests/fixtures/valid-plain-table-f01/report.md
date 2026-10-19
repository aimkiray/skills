# 模块深度评审：mod-order-lifecycle（普通表格提到权威表已有的 F-01）

```meta
module: mod-order-lifecycle
verdict: fail
severe: 0
medium: 1
minor: 0
```

## 发现项

| id | 文件:行号 | 分级 | 证据 | 对照原则 | 建议修法 |
| --- | --- | --- | --- | --- | --- |
| F-01 | `src/order/lifecycle.py:42` | 中等 | `rg foo` 命中 1 处。 | 维度 1 | 改。 |

## 复现步骤（普通表格，不参与候选判定）

| 步骤 | 命令 | 说明 |
| --- | --- | --- |
| 1 | `rg foo src/order/lifecycle.py` | F-01 的复现命令。 |
| 2 | `python -m pytest -q` | 3 failed。 |

## 逐文件结论

```conclusions
src/order/lifecycle.py | 发现 1 项 (F-01)
src/order/state.py | 无问题
```

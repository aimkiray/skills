# 模块深度评审：mod-order-lifecycle（无 id 列诱饵表，且结论行引用了表外 id）

```meta
module: mod-order-lifecycle
verdict: fail
severe: 0
medium: 1
minor: 1
```

## 发现项

| id | 文件:行号 | 分级 | 证据 | 对照原则 | 建议修法 |
| --- | --- | --- | --- | --- | --- |
| F-01 | `src/order/lifecycle.py:42` | 中等 | `rg foo` 命中 1 处。 | 维度 1 | 改。 |

## 历史遗留附表

| 编号 | 文件:行号 | 分级 | 证据 |
| --- | --- | --- | --- |
| F-99 | `src/order/state.py:7` | 轻微 | 历史表遗留项。 |

## 逐文件结论

```conclusions
src/order/lifecycle.py | 发现 1 项 (F-01)
src/order/state.py | 发现 1 项 (F-99)
```

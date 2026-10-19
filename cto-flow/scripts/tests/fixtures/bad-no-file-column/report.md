# 模块深度评审：mod-order-lifecycle（发现项表缺 文件:行号 列）

```meta
module: mod-order-lifecycle
verdict: fail
severe: 0
medium: 1
minor: 0
```

## 发现项

| id | 分级 | 证据 |
| --- | --- | --- |
| F-01 | 中等 | `rg foo` 命中 1 处。 |

## 逐文件结论

```conclusions
src/order/lifecycle.py | 发现 1 项 (F-01)
src/order/state.py | 无问题
```

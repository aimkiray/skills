# 模块深度评审：mod-order-lifecycle（meta 块放在报告末尾）

## 发现项

| id | 文件:行号 | 分级 | 证据 | 对照原则 | 建议 |
| --- | --- | --- | --- | --- | --- |
| F-01 | `src/order/lifecycle.py:42` | 中等 | `rg foo` 命中 1 处。 | 维度 1 | 改。 |

## 逐文件结论

```conclusions
src/order/lifecycle.py | 发现 1 项 (F-01)
src/order/state.py | 无问题
```

## 元信息

```meta
module: mod-order-lifecycle
verdict: fail
severe: 0
medium: 1
minor: 0
```

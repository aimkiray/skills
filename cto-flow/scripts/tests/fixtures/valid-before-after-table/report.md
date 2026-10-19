# 模块深度评审：mod-order-lifecycle（一张真表 + 前后对照表）

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

## 前后对照表（列含「位置 + 建议」，普通表格，不参与候选判定）

| 位置 | 改前 | 改后 | 建议 |
| --- | --- | --- | --- |
| `src/order/lifecycle.py:42` | 无幂等 CAS | 幂等 CAS | 按 F-01 修复。 |
| `src/order/state.py:7` | 常量与文档漂移 | 回写文档 | 无。 |

## 逐文件结论

```conclusions
src/order/lifecycle.py | 发现 1 项 (F-01)
src/order/state.py | 无问题
```

# 模块深度评审：mod-order-lifecycle（一张真表 + 若干说明性表格）

```meta
module: mod-order-lifecycle
verdict: fail
severe: 0
medium: 1
minor: 0
```

## 审查维度

| 维度 | 结论 |
| --- | --- |
| 缺陷 | 一处状态迁移竞态。 |
| 不优雅 | 无。 |
| 架构 | 职责边界清楚。 |

## 发现项

| id | 文件:行号 | 分级 | 证据 | 对照原则 | 建议修法 |
| --- | --- | --- | --- | --- | --- |
| F-01 | `src/order/lifecycle.py:42` | 中等 | `rg foo` 命中 1 处。 | 维度 1 | 改。 |

## 本次核查

| 检查项 | 结果 | 说明 |
| --- | --- | --- |
| 单测 | 通过 | 12 passed。 |
| lint | 通过 | 无告警。 |

## 分级汇总

| 分级 | 数量 |
| --- | --- |
| 严重 | 0 |
| 中等 | 1 |
| 轻微 | 0 |

## 逐文件结论

```conclusions
src/order/lifecycle.py | 发现 1 项 (F-01)
src/order/state.py | 无问题
```

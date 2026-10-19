# 模块深度评审：mod-order-lifecycle（无 id 列诱饵夹带未登记 id，位于权威表之后）

```meta
module: mod-order-lifecycle
verdict: fail
severe: 0
medium: 1
minor: 0
```

## 权威发现项表

| id | 文件:行号 | 分级 | 证据 | 对照原则 | 建议修法 |
| --- | --- | --- | --- | --- | --- |
| F-01 | `src/order/lifecycle.py:42` | 中等 | `rg foo` 命中 1 处。 | 维度 1 | 改。 |

## 历史遗留附表

| 位置 | 分级 | 证据 |
| --- | --- | --- |
| `src/order/state.py:7` | 严重 | 历史表遗留项 F-99，未进入任何结论行。 |

## 逐文件结论

```conclusions
src/order/lifecycle.py | 发现 1 项 (F-01)
src/order/state.py | 无问题
```

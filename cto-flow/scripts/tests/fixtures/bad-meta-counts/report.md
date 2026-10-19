# 模块深度评审：mod-order-lifecycle（meta 计数与发现项表不一致）

```meta
module: mod-order-lifecycle
verdict: fail
severe: 2
medium: 0
minor: 1
```

## 发现项

| id | 文件:行号 | 分级 | 证据 | 对照原则 | 建议 |
| --- | --- | --- | --- | --- | --- |
| F-01 | `src/order/lifecycle.py:42` | 严重 | `python -m pytest -q` 3 failed。 | 维度 1 | 幂等 CAS。 |
| F-02 | `src/order/lifecycle.py:88` | 中等 | `rg "sleep\("` 命中 2 处。 | 维度 2 | 注入 clock。 |
| F-03 | `src/order/state.py:7` | 轻微 | 常量与文档不一致。 | 维度 3 | 回写文档。 |

## 逐文件结论

```conclusions
src/order/lifecycle.py | 发现 2 项 (F-01, F-02)
src/order/state.py | 发现 1 项 (F-03)
docs/order.md | 无问题
```

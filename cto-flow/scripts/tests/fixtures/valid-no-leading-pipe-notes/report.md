# 模块深度评审：mod-order-lifecycle（§8.8 无前导管线真表 + 说明性表格）

```meta
module: mod-order-lifecycle
verdict: fail
severe: 0
medium: 1
minor: 0
```

## 发现项

id | 文件:行号 | 分级 | 证据 | 对照原则 | 建议修法
--- | --- | --- | --- | --- | ---
F-01 | `src/order/lifecycle.py:42` | 中等 | `rg foo` 命中 1 处。 | 维度 1 | 改。

## 对抗性检查

| 构造的反例 | 结果 |
| --- | --- |
| 取消后再 start | 已拦住。 |

## 检查点

| 检查点 | 证据 | 判定 |
| --- | --- | --- |
| 单测 | `12 passed` | 通过 |

## 逐文件结论

```conclusions
src/order/lifecycle.py | 发现 1 项 (F-01)
src/order/state.py | 无问题
```

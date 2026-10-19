# 模块深度评审：mod-order-lifecycle（一张真表 + 结论行表格 / 覆盖自证表格）

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

## 结论行表格（正文展示，不计入 COVERED）

| 文件 | 结论 |
| --- | --- |
| `src/order/lifecycle.py` | 发现 1 项 (F-01) |
| `src/order/state.py` | 无问题 |

## 覆盖自证

| 文件 | 覆盖状态 |
| --- | --- |
| `src/order/lifecycle.py` | COVERED |
| `src/order/state.py` | COVERED |

## 无法验证项

| 项 | 状态 | 原因 |
| --- | --- | --- |
| 真机 | 未验证 | 无设备。 |

## 逐文件结论

```conclusions
src/order/lifecycle.py | 发现 1 项 (F-01)
src/order/state.py | 无问题
```

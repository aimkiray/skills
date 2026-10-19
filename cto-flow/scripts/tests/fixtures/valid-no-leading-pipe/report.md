# 模块深度评审：mod-order-lifecycle（合法 GFM 表，无前导管线）

## 元信息

```meta
module: mod-order-lifecycle
verdict: fail
severe: 1
medium: 1
minor: 0
```

## 发现项

id | 文件:行号 | 分级 | 证据 | 对照原则 | 建议
--- | --- | --- | --- | --- | ---
F-01 | `src/order/lifecycle.py:42` | 严重 | `python -m pytest -q` 3 failed。 | 维度 1 | 幂等 CAS。
F-02 | `src/order/lifecycle.py:88` | 中等 | `rg "sleep\("` 命中 2 处。 | 维度 2 | 注入 clock。

## 逐文件结论

```conclusions
src/order/lifecycle.py | 发现 2 项 (F-01, F-02)
src/order/state.py | 无问题
```

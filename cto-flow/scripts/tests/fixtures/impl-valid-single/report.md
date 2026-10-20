# 实施报告：impl-valid-single

```meta
unit: impl-valid-single
verdict: pass
files: 1
sha256_before: 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
sha256_after: fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210
reverse_restore: pass
unresolved: 无
```

## 实测值

| 项 | 实测 |
|---|---|
| 对象文件 | `scripts/example.py`（单文件单元） |
| 基线 | HEAD 快照 sha256 复算一致 |
| 反向还原 | `apply -R` 后工作区哈希回基线 |

本夹具为 impl kind 最小合规形态：files 计数形态 `1` + 双单值哈希（不等）+ `unresolved: 无`。

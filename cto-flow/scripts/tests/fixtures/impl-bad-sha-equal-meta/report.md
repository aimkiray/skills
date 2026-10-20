# 实施报告：impl-bad-sha-equal-meta

```meta
unit: impl-bad-sha-equal-meta
verdict: pass
files: 1
sha256_before: 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
sha256_after: 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
reverse_restore: pass
unresolved: sha256 相同
```

## 说明

免责标记仅出现在 meta 块 `unresolved` 字段值内；正文不含该字面标记与理由句，
收窄口径下 meta 块不计入检索范围，故判不通过（R8.sha-equal）。

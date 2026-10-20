# 实施报告：impl-bad-fields

```meta
unit: impl-bad-fields
verdict: pass
files: 1
sha256_before: 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
sha256_after: fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210
reverse_restore: pass
```

## 说明

meta 缺 `unresolved` 字段（只六行），字段集不符即判不通过。

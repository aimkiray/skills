# 实施报告：bad-impl-meta-as-review

```meta
unit: bad-impl-meta-as-review
verdict: pass
files: 1
sha256_before: 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
sha256_after: fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210
reverse_restore: pass
unresolved: 无
```

## 说明

impl 七字段 meta 的报告按默认 kind（review）校验：字段集不符判 R1.meta-fields，
且缺 `conclusions` 块与发现项表，反向混淆回归同样判负。

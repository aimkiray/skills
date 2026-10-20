# 实施报告：impl-bad-sha-equal

```meta
unit: impl-bad-sha-equal
verdict: pass
files: 1
sha256_before: 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
sha256_after: 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
reverse_restore: pass
unresolved: 无
```

## 说明

before 与 after 两侧哈希一致（doc-only 重排），但本报告未按契约写出免责标记句，故判不通过。

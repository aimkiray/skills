# 实施报告：impl-bad-sha

```meta
unit: impl-bad-sha
verdict: pass
files: 1
sha256_before: 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
sha256_after: abc123
reverse_restore: pass
unresolved: 无
```

## 说明

`sha256_after` 非 64 位十六进制，且 `files` 为计数形态时 sha 必须是单值形态。

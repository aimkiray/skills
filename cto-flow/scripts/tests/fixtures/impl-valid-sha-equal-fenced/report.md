# 实施报告：impl-valid-sha-equal-fenced

```meta
unit: impl-valid-sha-equal-fenced
verdict: pass
files: 1
sha256_before: 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
sha256_after: 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
reverse_restore: pass
unresolved: 无
```

## 说明

before 与 after 对应位全部相等（本次仅重排文档段落，文件内容逐字节未变），
免责标记句按惯例随命令输出一并抄录在下方围栏代码块内：

```text
$ sha256sum docs/guide.md
0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef  docs/guide.md
说明：sha256 相同 —— 重排不改字节内容，故 before == after，无须 reverse_restore 之外的处置。
```

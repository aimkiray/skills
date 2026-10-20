# 实施报告：impl-bad-count

```meta
unit: impl-bad-count
verdict: pass
files: a/b.py;c/d.py;e/f.py
sha256_before: a/b.py=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa;c/d.py=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
sha256_after: a/b.py=1111111111111111111111111111111111111111111111111111111111111111;c/d.py=2222222222222222222222222222222222222222222222222222222222222222
reverse_restore: pass
unresolved: 无
```

## 说明

`files` 为三元素路径列表，而两个 sha 列表各只有两元素，元素数不一致。

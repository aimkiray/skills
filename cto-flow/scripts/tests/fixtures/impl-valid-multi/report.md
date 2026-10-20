# 实施报告：impl-valid-multi

```meta
unit: impl-valid-multi
verdict: pass
files: a/b.py;c/d.py
sha256_before: a/b.py=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa;c/d.py=none
sha256_after: a/b.py=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb;c/d.py=5555555555555555555555555555555555555555555555555555555555555555
reverse_restore: na
unresolved: 无
```

## 实测值

| 文件 | 基线 | 说明 |
|---|---|---|
| `a/b.py` | 已存在（哈希见 meta） | 修改 |
| `c/d.py` | 新建文件，`sha256_before` 元素取 `none` | 新增 |

覆盖点：files 列表形态、`路径=哈希` 双列表逐位对应、`none` + `reverse_restore: na` 联动、manifest 集合对账。

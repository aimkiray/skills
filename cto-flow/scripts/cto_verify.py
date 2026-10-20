#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cto_verify.py -- cto-flow §8.5 机读契约的机械核对器（Python 3 标准库 only）。

校验对象（§8.5 规定的两套机读块 + 发现项表）：

  R1  meta 块：位于报告开头（其前只允许标题、注释与空行）、存在且唯一；字段恰为
      module/verdict/severe/medium/minor 且顺序固定；verdict in {pass, fail}；
      三个计数为非负整数（拒绝“约”“若干”）。
  R2  conclusions 块：存在且唯一；每行恰为两种合法形态之一：
        <路径> | 发现 <N> 项 (<id1>, <id2>, ...)
        <路径> | 无问题
      形态 B 不得出现括号或「发现 0 项」。
  R3  结论行条数 = manifest 条数；结论路径集合 = manifest 集合。
      重复项（R3.conclusions-duplicate）、漏项（R3.conclusions-missing）、
      多余项（R3.conclusions-extra）分别报出，不合并。
  R4  N 双重等式：N == 括号内 id 个数（id 去重后计数，括号内重复即违规），
      且 N == 该文件在发现项表被点名的条数；表结构不足以核对时判不通过。
  R5  发现项表存在且唯一（权威表 = 恰好一张具备 `id` 列的表）；首列为 id；
      必须含 `文件:行号` 列；id 形如 F-\\d{2}（超过 99 时按实际位数自然扩展，
      不得补零）；模块内唯一；自上而下从 F-01 起连续编号（不跳号、不复用）。
      报告正文与其它表格里出现的 F-\\d{2,} 记号若不在权威表 id 列中，报「悬空 id」
      （R5.dangling-id）——无 id 列的诱饵附表夹带未登记 id 仍判不通过。
  R6  conclusions 引用的每个 id 必须在该报告的发现项表中存在。
  R7  meta 的三个计数必须分别等于发现项表中同级别行数；分级词无法识别即判不通过。
  R8  （仅 --kind impl，§6 实施/修复类报告；此模式不校验 R2–R7）meta 块字段
      恰为 unit/verdict/files/sha256_before/sha256_after/reverse_restore/unresolved
      且顺序固定；files 为计数形态（仅允许 1）或 `;`/`；` 分隔的仓库相对路径
      列表，与 sha256_* 的单值 / `路径=哈希` 列表形态逐一对应；sha256_before
      可取 none（此时 reverse_restore 必须为 na），before/after 对应位全部
      相等须在正文写明「sha256 相同」及理由；reverse_restore: fail 时 verdict
      不得为 pass；提供 --manifest 且 files 为列表形态时做集合对账。

退出码：0 = 全部通过；1 = 存在契约违规（含超长数字等无法解析的取值）；2 = 用法、
IO 或校验器内部错误（内部错误不打印 traceback）。
输出：默认每条违规一行 `SEVERITY | 文件:行 | 规则 | 说明`，末行 `PASS <n> / FAIL <n>`；
      --json 输出机器可读结构（供后续编排消费），此时不再输出人类可读行。

用法示例：
  python scripts/cto_verify.py --report reviews/mod-a.md --manifest specs/mod-a.manifest
  python scripts/cto_verify.py --dir reviews/round1 --manifest-dir reviews/round1/manifests
  python scripts/cto_verify.py --report reviews/mod-a.md --json
  python scripts/cto_verify.py --report reports/unit-a.md --kind impl
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

TOOL_NAME = "cto_verify"
TOOL_VERSION = "1.2.1"

ERROR = "ERROR"
WARN = "WARN"

META_FIELDS: Tuple[str, ...] = ("module", "verdict", "severe", "medium", "minor")
VERDICT_VALUES = ("pass", "fail")
# §6 实施/修复类报告（--kind impl）的七字段 meta，字段名与顺序固定
IMPL_META_FIELDS: Tuple[str, ...] = (
    "unit",
    "verdict",
    "files",
    "sha256_before",
    "sha256_after",
    "reverse_restore",
    "unresolved",
)
RR_VALUES = ("pass", "fail", "na")
# sha256_* 的合法哈希形态：64 位十六进制；sha256_before 另允许整值/元素取 none
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
# files / sha256_* 列表形态的分隔符（半角分号与全角分号）
_LIST_SEP_RE = re.compile(r"[;；]")
# files 路径元素的禁字符：空白、反引号、`|`
_FILES_ELEM_BAD_RE = re.compile(r"[\s`|]")
# before/after 对应位全部相等时的免责字面标记（§6：正文须写出该句及理由）
_SHA_EQUAL_EXEMPT = "sha256 相同"
# 两位序号；超过 99 时按实际位数自然扩展（F-100…），上限 9 位以免 int() 溢出
ID_RE = re.compile(r"^F-(\d{2,9})$")
# 正文 / 表格单元格里出现的 id 记号（用于「悬空 id」判定；不要求整格匹配）
_ID_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9])F-\d{2,}(?!\d)")
# `#` 作首列表头时，至少一格形如 F-NN 才认作 id 列（普通编号表不参与候选判定）
_LOOSE_ID_CELL_RE = re.compile(r"^F-\d{2,}$")
# 契约里的计数（N / meta 计数）不会超过 9 位；超长数字按违规处理，绝不交给 int() 抛异常
_MAX_DIGITS = 9
# 行内 `文件:行号` 后缀（:12 / :12-34 / :12–34 / #L12 / :L12）
_LINE_SUFFIX_RE = re.compile(
    r"\s*(?::\s*\d+(?:\s*[-\u2013\u2014]\s*\d+)?|#\s*L?\d+(?:\s*[-\u2013\u2014]\s*L?\d+)?)\s*$"
)
_FENCE_OPEN_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
_SEP_CELL_RE = re.compile(r"^:?-{1,}:?$")
_FIELD_LINE_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$")
_INT_RE = re.compile(r"^[0-9]+$")

CONC_A_RE = re.compile(
    r"^(?P<path>[^|]+?)\s*\|\s*发现\s*(?P<n>[0-9]+)\s*项\s*\((?P<ids>[^()]*)\)\s*$"
)
CONC_B_RE = re.compile(r"^(?P<path>[^|]+?)\s*\|\s*无问题\s*$")


def short_value(value: str, limit: int = 24) -> str:
    """把可能极长的原始值截断后再放进报错信息（超长数字不得撑爆输出）。"""
    text = value.strip().replace("\n", " ")
    if len(text) <= limit:
        return text
    return "%s…（共 %d 字符）" % (text[:limit], len(text))


def parse_uint(text: str) -> Optional[int]:
    """解析契约中的非负整数；非纯 ASCII 数字或超过 _MAX_DIGITS 位时返回 None。"""
    s = text.strip()
    if not _INT_RE.match(s) or len(s) > _MAX_DIGITS:
        return None
    try:
        return int(s)
    except ValueError:  # pragma: no cover - 位数已设上限，纯防御
        return None


def id_serial(digits: str) -> Optional[int]:
    """id 序号：两位数字；超过 99 时按实际位数自然扩展，不得补零（F-001 非法）。"""
    if len(digits) == 2:
        return int(digits)
    if digits.startswith("0"):
        return None
    return int(digits)


# --------------------------------------------------------------------------- #
# 基础数据结构
# --------------------------------------------------------------------------- #


@dataclass
class Violation:
    rule: str
    line: int
    message: str
    severity: str = ERROR

    def as_dict(self) -> Dict[str, object]:
        return {
            "severity": self.severity,
            "line": self.line,
            "rule": self.rule,
            "message": self.message,
        }


@dataclass
class Block:
    info: str
    start: int  # 0-based index of opening fence
    end: Optional[int]  # 0-based index of closing fence, None if unclosed
    content: List[Tuple[int, str]]  # (0-based index, raw line)


@dataclass
class Conclusion:
    lineno: int
    raw: str
    path: str
    form: str  # "A" | "B"
    n: Optional[int]  # 超长/非法 N 解析失败时为 None
    ids: List[str]  # 已去重
    duplicate_ids: List[str] = field(default_factory=list)  # 括号内重复出现的 id


@dataclass
class FindingsTable:
    header_line: int
    header: List[str]
    rows: List[Tuple[int, List[str]]]
    id_col: Optional[int]
    file_col: Optional[int]
    sev_col: Optional[int]
    evidence_col: Optional[int] = None
    fix_col: Optional[int] = None


@dataclass
class ReportResult:
    path: str
    module: Optional[str]
    violations: List[Violation] = field(default_factory=list)
    stats: Dict[str, object] = field(default_factory=dict)
    io_error: bool = False

    @property
    def ok(self) -> bool:
        return not any(v.severity == ERROR for v in self.violations)

    def as_dict(self) -> Dict[str, object]:
        return {
            "path": self.path,
            "module": self.module,
            "ok": self.ok,
            "violations": [v.as_dict() for v in self.violations],
            "stats": self.stats,
        }


# --------------------------------------------------------------------------- #
# 文本 / 路径 / 表格工具
# --------------------------------------------------------------------------- #


def norm_path(value: str) -> str:
    p = value.strip().strip("`").strip()
    p = p.replace("\\", "/")
    p = re.sub(r"^\./+", "", p)
    p = re.sub(r"/{2,}", "/", p)
    return p


def norm_header(value: str) -> str:
    return re.sub(r"[`*_\s]", "", value).strip().lower()


def read_text(path: str) -> Tuple[str, Optional[Violation]]:
    """读取为文本；容忍 BOM / CRLF / LF / 混合行尾，非法 UTF-8 不崩溃。"""
    with open(path, "rb") as fh:
        data = fh.read()
    warn: Optional[Violation] = None
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("utf-8-sig", errors="replace")
        warn = Violation(
            "io.encoding",
            1,
            "文件不是合法 UTF-8（已用替换字符继续解析，结果可能不完整）",
            WARN,
        )
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text, warn


def split_row(line: str) -> Optional[List[str]]:
    """解析 markdown 表格行：同时接受带前导管线（`| a | b |`）与合法 GFM 无前导管线
    （`a | b`，§8.8 发现项表模板即此写法）两种形态；非表格行返回 None。"""
    s = line.strip()
    if not s or "|" not in s:
        return None
    cells = re.split(r"(?<!\\)\|", s)
    if cells and cells[0].strip() == "":
        cells = cells[1:]
    if cells and cells[-1].strip() == "":
        cells = cells[:-1]
    if not cells:
        return None
    return [c.strip().replace("\\|", "|") for c in cells]


def is_separator(cells: Sequence[str]) -> bool:
    real = [c for c in cells if c.strip() != ""]
    return bool(real) and all(_SEP_CELL_RE.match(c.strip()) for c in real)


def find_blocks(lines: Sequence[str]) -> Tuple[List[Block], set]:
    """返回围栏块列表 + 被围栏覆盖的行索引（0-based，含围栏行）。"""
    blocks: List[Block] = []
    masked: set = set()
    i = 0
    n = len(lines)
    while i < n:
        m = _FENCE_OPEN_RE.match(lines[i])
        if not m:
            i += 1
            continue
        fence = m.group(1)
        info = lines[i][m.end(1):].strip()
        j = i + 1
        close = None
        while j < n:
            cm = _FENCE_OPEN_RE.match(lines[j])
            if (
                cm
                and cm.group(1)[0] == fence[0]
                and len(cm.group(1)) >= len(fence)
                and lines[j][cm.end(1):].strip() == ""
            ):
                close = j
                break
            j += 1
        if close is None:
            content = [(k, lines[k]) for k in range(i + 1, n)]
            blocks.append(Block(info=info, start=i, end=None, content=content))
            masked.update(range(i, n))
            i = n
        else:
            content = [(k, lines[k]) for k in range(i + 1, close)]
            blocks.append(Block(info=info, start=i, end=close, content=content))
            masked.update(range(i, close + 1))
            i = close + 1
    return blocks, masked


def pick_blocks(blocks: Sequence[Block], name: str) -> List[Block]:
    picked = []
    for b in blocks:
        token = b.info.split()[0].lower() if b.info.split() else ""
        if token == name:
            picked.append(b)
    return picked


_HEADING_RE = re.compile(r"^#{1,6}(\s|$)")


def meta_position_line(lines: Sequence[str], block: Block) -> Optional[int]:
    """meta 必须是报告的首个非空内容块：其前只允许标题行、HTML 注释与空行。

    返回第一处不允许内容的 1-based 行号；位置合规返回 None。
    """
    i = 0
    in_comment = False
    while i < block.start:
        s = lines[i].strip()
        if in_comment:
            if "-->" in s:
                in_comment = False
            i += 1
            continue
        if not s:
            i += 1
            continue
        if s.startswith("<!--"):
            if "-->" not in s:
                in_comment = True
            i += 1
            continue
        if _HEADING_RE.match(s):
            i += 1
            continue
        return i + 1
    return None


def extract_path(cell: str) -> str:
    """从发现项表的文件单元格里取出仓库相对路径（去掉行号与括注）。"""
    s = cell.strip()
    m = re.search(r"`([^`]+)`", s)
    if m:
        cand = m.group(1)
    else:
        cand = s.split("（")[0].split("(")[0].strip()
        parts = re.split(r"\s+", cand)
        cand = parts[0] if parts and parts[0] else cand
    cand = cand.strip().strip("`*_ ")
    cand = _LINE_SUFFIX_RE.sub("", cand)
    return norm_path(cand)


def _looks_absolute(p: str) -> bool:
    return p.startswith("/") or bool(re.match(r"^[A-Za-z]:/", p))


def row_matches_conclusion(row_path: str, conclusion_path: str) -> bool:
    a = norm_path(row_path)
    b = norm_path(conclusion_path)
    if not a or not b:
        return False
    if a == b:
        return True
    if _looks_absolute(a) and a.endswith("/" + b):
        return True
    return False


# --------------------------------------------------------------------------- #
# 解析
# --------------------------------------------------------------------------- #


def collect_tables(lines: Sequence[str], masked: set) -> List[FindingsTable]:
    tables: List[FindingsTable] = []
    i = 0
    n = len(lines)
    while i < n:
        if i in masked:
            i += 1
            continue
        header = split_row(lines[i])
        if header is None:
            i += 1
            continue
        sep = split_row(lines[i + 1]) if i + 1 < n and (i + 1) not in masked else None
        if sep is None or not is_separator(sep):
            i += 1
            continue
        rows: List[Tuple[int, List[str]]] = []
        j = i + 2
        while j < n and j not in masked:
            cells = split_row(lines[j])
            if cells is None or is_separator(cells):
                break
            if not any(c.strip() for c in cells):
                break
            rows.append((j, cells))
            j += 1
        tables.append(
            FindingsTable(
                header_line=i,
                header=header,
                rows=rows,
                id_col=None,
                file_col=None,
                sev_col=None,
            )
        )
        i = j
    return tables


def _has_id_cell_shape(table: FindingsTable, idx: int) -> bool:
    """该列是否真有 id 记号：空表视为「待填写」的发现项表，非空表须至少一格形如 F-NN。

    仅有 `id` / `#` 表头、单元格却不是 id 记号的普通表格（例如数据库 schema 表、
    `# | 检查项 | 结果` 编号表）不得被当成发现项表，否则会制造假违规。
    """
    if not table.rows:
        return True
    for _idx, cells in table.rows:
        if idx < len(cells):
            cell = cells[idx].replace("`", "").replace("*", "").strip()
            if _LOOSE_ID_CELL_RE.match(cell):
                return True
    return False


def resolve_table_columns(table: FindingsTable) -> FindingsTable:
    id_col = None
    file_col = None
    sev_col = None
    evidence_col = None
    fix_col = None
    for idx, cell in enumerate(table.header):
        h = norm_header(cell)
        if id_col is None and (h == "id" or (h == "#" and idx == 0)):
            if _has_id_cell_shape(table, idx):
                id_col = idx
        if file_col is None and any(k in h for k in ("文件", "路径", "位置", "file", "path", "location")):
            file_col = idx
        if sev_col is None and any(
            k in h for k in ("分级", "级别", "严重程度", "severity", "level", "priority")
        ):
            sev_col = idx
        if evidence_col is None and any(k in h for k in ("证据", "evidence", "proof", "repro")):
            evidence_col = idx
        if fix_col is None and any(
            k in h for k in ("建议修法", "修法", "建议", "整改", "fix", "suggestion", "recommendation", "remediation")
        ):
            fix_col = idx
    table.id_col = id_col
    table.file_col = file_col
    table.sev_col = sev_col
    table.evidence_col = evidence_col
    table.fix_col = fix_col
    return table


# 首列表头是「发现项序号」写法而非字面 `id` 的历史/变体写法。
_INTENT_HEADERS = ("编号", "序号", "no", "no.", "发现项")


def has_findings_intent(table: FindingsTable) -> bool:
    """「有发现项表意图但没有 id 列」的窄判定（入参须已 resolve 列）。

    契约（§8.5）规定发现项表必须以 `id` 为首列，历史报告里的首列常写作
    `编号` / `序号`。只有首列表头是这类序号写法、**且**同时具备位置列与分级列时，
    才算「想写发现项表却漏了 id 首列」，由调用方补报 R5.id-column。

    逐条核对表（位置 + 证据）、前后对照表（位置 + 建议）、复现步骤表等普通表格
    不满足该形状，**一律不参与候选判定**：上一轮把「位置 + 分级/证据/建议修法」
    当候选表的启发式会把合规报告判成违规（过度修正），此处已回退。
    """
    if table.id_col is not None or not table.header:
        return False
    if norm_header(table.header[0]) not in _INTENT_HEADERS:
        return False
    return table.file_col is not None and table.sev_col is not None


def pick_findings_table(tables: Sequence[FindingsTable]) -> Optional[FindingsTable]:
    """选出权威发现项表（入参须已 resolve 列）：只认「具备 id 列」的表格。

    恰好一张 → 它就是权威表；多张 → 调用方另报 R5.findings-table，这里按
    「`id` 首列 + 位置列 + 分级列」优先挑一张继续逐项核对（不得因多候选而放弃核对）。
    没有任何 id 列的表格不参与权威表判定。
    """
    id_tables = [t for t in tables if t.id_col is not None]
    if not id_tables:
        return None
    if len(id_tables) == 1:
        return id_tables[0]

    def score(t: FindingsTable) -> Tuple[int, int, int, int, int]:
        return (
            1 if (t.id_col == 0 and t.file_col is not None and t.sev_col is not None) else 0,
            1 if (t.file_col is not None and t.sev_col is not None) else 0,
            1 if t.id_col == 0 else 0,
            1 if t.file_col is not None else 0,
            len(t.rows),
        )

    return max(id_tables, key=score)


def parse_meta(
    block: Block,
    violations: List[Violation],
    expected_fields: Tuple[str, ...] = META_FIELDS,
    rule_prefix: str = "R1",
) -> Dict[str, Tuple[int, str]]:
    """返回 {字段: (行号, 原始值)}；所有问题记入 violations。

    结构判定（缺/多/乱序/重复字段、`字段: 值` 形态、verdict 取值域）对 review
    与 impl 通用：调用方传入 expected_fields 与 rule_prefix（R1 / R8）；
    severe/medium/minor 计数核对仅当这些字段在 expected_fields 中才有意义。
    """
    entries: List[Tuple[int, str]] = []
    for idx, raw in block.content:
        if raw.strip() == "":
            continue
        entries.append((idx, raw.strip()))

    parsed: List[Tuple[int, str, str]] = []
    for idx, raw in entries:
        m = _FIELD_LINE_RE.match(raw)
        if not m:
            violations.append(
                Violation(
                    rule_prefix + ".meta-fields",
                    idx + 1,
                    "meta 行必须为 `字段: 值`，无法解析：%r" % short_value(raw),
                )
            )
            continue
        parsed.append((idx, m.group(1), m.group(2).strip()))

    names = [name for _, name, _ in parsed]
    expected = list(expected_fields)
    if names != expected:
        if entries:
            line = entries[0][0] + 1
        else:
            line = block.start + 1
        dup = sorted({x for x in names if names.count(x) > 1})
        detail = "实际字段序列：%s" % (", ".join(names) if names else "<空>")
        if dup:
            detail += "；重复字段：%s" % ", ".join(dup)
        violations.append(
            Violation(
                rule_prefix + ".meta-fields",
                line,
                "meta 字段必须恰为 %s 且顺序固定；%s" % ("/".join(expected), detail),
            )
        )

    result: Dict[str, Tuple[int, str]] = {}
    for idx, name, value in parsed:
        if name not in expected:
            violations.append(
                Violation(
                    rule_prefix + ".meta-fields",
                    idx + 1,
                    "meta 出现未定义字段 `%s`" % name,
                )
            )
            continue
        if name in result:
            violations.append(
                Violation(
                    rule_prefix + ".meta-fields", idx + 1, "meta 字段 `%s` 重复" % name
                )
            )
            continue
        result[name] = (idx + 1, value)

    if "verdict" in result:
        line, value = result["verdict"]
        if value not in VERDICT_VALUES:
            violations.append(
                Violation(
                    rule_prefix + ".meta-verdict",
                    line,
                    "verdict 只能取 pass 或 fail（实际 %r）" % short_value(value),
                )
            )
    for name in ("severe", "medium", "minor"):
        if name not in result:
            continue
        line, value = result[name]
        if parse_uint(value) is None:
            violations.append(
                Violation(
                    rule_prefix + ".meta-counts",
                    line,
                    "%s 必须为非负整数（仅 ASCII 数字、最多 %d 位，拒绝“约/若干”等），实际 %r"
                    % (name, _MAX_DIGITS, short_value(value)),
                )
            )
    return result


def parse_conclusions(
    block: Block, violations: List[Violation]
) -> Tuple[List[Conclusion], int]:
    """返回 (可解析结论行, 块内非空行总数)。"""
    conclusions: List[Conclusion] = []
    total = 0
    for idx, raw in block.content:
        s = raw.strip()
        if not s:
            continue
        total += 1
        if s.startswith("<!--"):
            total -= 1
            continue
        mb = CONC_B_RE.match(s)
        if mb:
            path = norm_path(mb.group("path"))
            if not path:
                violations.append(
                    Violation("R2.conclusions-format", idx + 1, "结论行路径为空")
                )
                continue
            conclusions.append(Conclusion(idx + 1, s, path, "B", 0, []))
            continue
        ma = CONC_A_RE.match(s)
        if ma:
            raw_n = ma.group("n")
            raw_ids = ma.group("ids").strip()
            ids: List[str] = []
            duplicate_ids: List[str] = []
            for token in re.split(r"[,，]", raw_ids):
                token = token.strip()
                if not token:
                    continue
                if token in ids:
                    if token not in duplicate_ids:
                        duplicate_ids.append(token)
                    continue
                ids.append(token)
            n = parse_uint(raw_n)
            if n is None:
                violations.append(
                    Violation(
                        "R2.conclusions-format",
                        idx + 1,
                        "形态 A 的 N 必须是 1–%d 位的 ASCII 非负整数，实际 %r"
                        % (_MAX_DIGITS, short_value(raw_n)),
                    )
                )
            elif n == 0:
                violations.append(
                    Violation(
                        "R2.conclusions-format",
                        idx + 1,
                        "形态 A 的 N 必须 >= 1（发现 0 项应写形态 B `<路径> | 无问题`）",
                    )
                )
            if not ids:
                violations.append(
                    Violation(
                        "R2.conclusions-format",
                        idx + 1,
                        "形态 A 括号内必须至少有一个 id",
                    )
                )
            bad = [x for x in ids if not ID_RE.match(x)]
            if bad:
                violations.append(
                    Violation(
                        "R2.conclusions-format",
                        idx + 1,
                        "括号内只允许 id（形如 F-01），非法项：%s"
                        % ", ".join(short_value(x) for x in bad),
                    )
                )
            path = norm_path(ma.group("path"))
            if not path:
                violations.append(
                    Violation("R2.conclusions-format", idx + 1, "结论行路径为空")
                )
                continue
            conclusions.append(Conclusion(idx + 1, s, path, "A", n, ids, duplicate_ids))
            continue

        # 明确区分几种典型坏形态，便于定位
        if "无问题" in s:
            msg = "形态 B 必须恰为 `<路径> | 无问题`，不得出现括号或「发现 0 项」"
        elif "发现" in s and "项" in s:
            msg = (
                "形态 A 必须为 `<路径> | 发现 <N> 项 (<id>, ...)`，"
                "N 须为 ASCII 非负整数、括号须为半角"
            )
        elif "|" not in s:
            msg = "结论行缺少 ` | ` 分隔符"
        else:
            msg = "不符合两种合法形态之一（`发现 N 项 (...)` / `无问题`）"
        violations.append(Violation("R2.conclusions-format", idx + 1, msg))
    return conclusions, total


def parse_manifest(path: str) -> Tuple[List[Tuple[str, int]], List[Tuple[str, int]], Optional[Violation]]:
    """返回 (去重后的 [(路径, 行号)], 重复项 [(路径, 行号)], 编码 WARN)。"""
    text, warn = read_text(path)
    entries: List[Tuple[str, int]] = []
    seen: Dict[str, int] = {}
    dups: List[Tuple[str, int]] = []
    for idx, raw in enumerate(text.split("\n")):
        s = raw.strip().lstrip("\ufeff")
        if not s or s.startswith("#"):
            continue
        p = norm_path(s)
        if not p:
            continue
        if p in seen:
            dups.append((p, idx + 1))
        else:
            seen[p] = idx + 1
            entries.append((p, idx + 1))
    return entries, dups, warn


# --------------------------------------------------------------------------- #
# impl（--kind impl）七字段 meta 校验（§6 实施/修复类报告）
# --------------------------------------------------------------------------- #


def _impl_parse_sha_field(
    name: str, line: int, value: str, violations: List[Violation]
) -> Tuple[Optional[str], object]:
    """解析 sha256_before / sha256_after 字段。

    返回 (form, data)：form 为 "single"（data=64-hex 或 "none"）、
    "list"（data=[(路径, 64-hex 或 "none"), ...]）或 None（无法解析）。
    `none` 仅 sha256_before 允许（整值或列表元素均可）；按最后一个 `=` 切分，
    路径中含 `=` 也不误判。
    """
    allow_none = name == "sha256_before"
    v = value.strip()
    if not v:
        violations.append(Violation("R8.meta-sha", line, "%s 值不能为空" % name))
        return None, None
    if allow_none and v == "none":
        return "single", "none"
    if _SHA256_RE.match(v):
        return "single", v
    elems: List[Tuple[str, str]] = []
    for part in _LIST_SEP_RE.split(v):
        part = part.strip()
        path, sep, hexv = part.rpartition("=")
        if not sep:
            violations.append(
                Violation(
                    "R8.meta-sha",
                    line,
                    "%s 必须为 64 位十六进制%s，或以 `;`/`；` 分隔的 `<路径>=<哈希>`"
                    " 列表（按最后一个 `=` 切分），实际 %r"
                    % (name, "或 none " if allow_none else "", short_value(part)),
                )
            )
            continue
        p = path.strip()
        h = hexv.strip()
        if not p:
            violations.append(
                Violation(
                    "R8.meta-sha",
                    line,
                    "%s 列表元素的路径为空（形态 `<路径>=<哈希>`），实际 %r"
                    % (name, short_value(part)),
                )
            )
            continue
        if h == "none":
            if allow_none:
                elems.append((p, h))
            else:
                violations.append(
                    Violation(
                        "R8.meta-sha",
                        line,
                        "%s 不得取 none（元素 %r）；仅 sha256_before 允许 none"
                        % (name, p),
                    )
                )
            continue
        if not _SHA256_RE.match(h):
            violations.append(
                Violation(
                    "R8.meta-sha",
                    line,
                    "%s 元素 %r 的哈希必须为 64 位十六进制%s，实际 %r"
                    % (name, p, "或 none" if allow_none else "", short_value(h)),
                )
            )
            continue
        elems.append((p, h))
    return "list", elems


def _check_impl_meta(
    meta: Dict[str, Tuple[int, str]],
    lines: Sequence[str],
    meta_blocks: Sequence[Block],
    manifest_entries: Optional[List[Tuple[str, int]]],
    violations: List[Violation],
) -> Dict[str, object]:
    """§6 七字段 meta 的值域与联动校验（规则名 R8.*）。

    字段结构（缺/多/乱序/重复）由 parse_meta 记 R8.meta-fields，verdict 取值域
    由 parse_meta 记 R8.meta-verdict；此处逐字段查值域、files ⇄ sha256_* 形态
    对应、none/verdict 联动、before==after 恒等与 manifest 集合对账。
    """
    stats: Dict[str, object] = {}

    def entry(name: str) -> Tuple[Optional[int], str]:
        item = meta.get(name)
        return (item[0], item[1]) if item is not None else (None, "")

    # ---- unit：非空自由文本（单元标识） ----
    unit_line, unit_value = entry("unit")
    if unit_line is not None and not unit_value.strip():
        violations.append(
            Violation("R8.meta-unit", unit_line, "unit 不能为空（单元标识自由文本）")
        )

    # ---- files：计数形态（仅允许 1）或 `;`/`；` 分隔的仓库相对路径列表 ----
    files_line, files_value = entry("files")
    files_form: Optional[str] = None
    files_elems: List[str] = []
    files_n: Optional[int] = None
    if files_line is not None:
        fv = files_value.strip()
        if not fv:
            violations.append(
                Violation("R8.files-format", files_line, "files 值不能为空")
            )
        elif _INT_RE.match(fv):
            files_n = parse_uint(fv)
            if files_n is None:
                violations.append(
                    Violation(
                        "R8.files-format",
                        files_line,
                        "files 计数形态须为不超过 %d 位的 ASCII 非负整数，实际 %r"
                        % (_MAX_DIGITS, short_value(fv)),
                    )
                )
            else:
                files_form = "count"
                if files_n != 1:
                    violations.append(
                        Violation(
                            "R8.files-sha-count",
                            files_line,
                            "files 计数形态仅允许 `1`（单文件单元）；多文件单元须写"
                            " `;`/`；` 分隔的仓库相对路径列表，实际 %d" % files_n,
                        )
                    )
        else:
            files_form = "list"
            for part in _LIST_SEP_RE.split(files_value):
                elem = part.strip()
                if not elem:
                    violations.append(
                        Violation(
                            "R8.files-format",
                            files_line,
                            "files 列表含空元素（`；`/`;` 分隔后元素不得为空），原值 %r"
                            % short_value(files_value),
                        )
                    )
                    continue
                if _FILES_ELEM_BAD_RE.search(elem):
                    violations.append(
                        Violation(
                            "R8.files-format",
                            files_line,
                            "files 路径元素 %r 不得含空白、反引号或 `|`"
                            % short_value(elem),
                        )
                    )
                    continue
                files_elems.append(elem)
    stats["files_form"] = files_form or "invalid"
    stats["files_count"] = (
        files_n if files_form == "count" and files_n is not None else len(files_elems)
    )

    # ---- sha256_before / sha256_after：单值 64-hex（before 另许 none）或 `路径=哈希` 列表 ----
    sha_forms: Dict[str, Optional[str]] = {}
    sha_datas: Dict[str, object] = {}
    sha_lines: Dict[str, int] = {}
    for name in ("sha256_before", "sha256_after"):
        s_line, s_value = entry(name)
        if s_line is None:
            continue
        sha_lines[name] = s_line
        form, data = _impl_parse_sha_field(name, s_line, s_value, violations)
        sha_forms[name] = form
        sha_datas[name] = data

    # ---- 形态对应：files 列表 ⇄ 双 sha 等长列表逐位同路径；files 计数 ⇄ 双 sha 单值 ----
    if files_form == "count":
        for name in ("sha256_before", "sha256_after"):
            if sha_forms.get(name) == "list":
                violations.append(
                    Violation(
                        "R8.files-sha-count",
                        sha_lines[name],
                        "files 为计数形态（=1），%s 必须为单值 64 位十六进制%s，"
                        "不得为 `路径=哈希` 列表"
                        % (name, "或 none" if name == "sha256_before" else ""),
                    )
                )
    elif files_form == "list":
        for name in ("sha256_before", "sha256_after"):
            form = sha_forms.get(name)
            if form == "single":
                violations.append(
                    Violation(
                        "R8.files-sha-count",
                        sha_lines[name],
                        "files 为 %d 元素路径列表，%s 必须为等长的 `<路径>=<哈希>`"
                        " 列表，不得为单值" % (len(files_elems), name),
                    )
                )
            elif form == "list":
                sha_elems = sha_datas[name]
                if len(sha_elems) != len(files_elems):
                    violations.append(
                        Violation(
                            "R8.files-sha-count",
                            sha_lines[name],
                            "%s 列表元素数 %d 与 files 元素数 %d 不一致"
                            % (name, len(sha_elems), len(files_elems)),
                        )
                    )
                else:
                    for i, (f_elem, s_elem) in enumerate(zip(files_elems, sha_elems)):
                        if norm_path(f_elem) != norm_path(s_elem[0]):
                            violations.append(
                                Violation(
                                    "R8.files-sha-path",
                                    sha_lines[name],
                                    "%s 第 %d 个元素路径 %r 与 files 第 %d 个元素 %r"
                                    " 归一化后不一致"
                                    % (name, i + 1, s_elem[0], i + 1, f_elem),
                                )
                            )

    # ---- reverse_restore 值域 ----
    rr_line, rr_value = entry("reverse_restore")
    rr = rr_value.strip()
    if rr_line is not None and rr not in RR_VALUES:
        violations.append(
            Violation(
                "R8.meta-rr",
                rr_line,
                "reverse_restore 只能取 pass、fail 或 na（实际 %r）" % short_value(rr),
            )
        )

    # ---- none 联动：sha256_before 含 none（整值或任一列表元素）⇒ rr 必须为 na ----
    before_has_none = False
    if sha_forms.get("sha256_before") == "single":
        before_has_none = sha_datas["sha256_before"] == "none"
    elif sha_forms.get("sha256_before") == "list":
        before_has_none = any(h == "none" for _p, h in sha_datas["sha256_before"])
    if before_has_none and rr != "na":
        violations.append(
            Violation(
                "R8.none-consistency",
                rr_line if rr_line is not None else 1,
                "sha256_before 含 none（新建文件无基线），reverse_restore 必须为 na，"
                "实际 %r" % short_value(rr),
            )
        )

    # ---- 反向还原联动：rr=fail ⇒ verdict 不得为 pass ----
    verdict_line, verdict_value = entry("verdict")
    if rr == "fail" and verdict_value.strip() == "pass":
        violations.append(
            Violation(
                "R8.verdict-rr",
                verdict_line if verdict_line is not None else 1,
                "reverse_restore 为 fail 时 verdict 不得为 pass",
            )
        )

    # ---- 恒等约束：before/after 对应位全部相等且无免责说明 ⇒ 违规 ----
    all_equal = False
    if (
        sha_forms.get("sha256_before") == "single"
        and sha_forms.get("sha256_after") == "single"
    ):
        b_val = sha_datas["sha256_before"]
        a_val = sha_datas["sha256_after"]
        all_equal = b_val != "none" and str(b_val).lower() == str(a_val).lower()
    elif (
        sha_forms.get("sha256_before") == "list"
        and sha_forms.get("sha256_after") == "list"
    ):
        b_list = sha_datas["sha256_before"]
        a_list = sha_datas["sha256_after"]
        if b_list and len(b_list) == len(a_list):
            all_equal = all(
                norm_path(bp) == norm_path(ap) and str(bh).lower() == str(ah).lower()
                for (bp, bh), (ap, ah) in zip(b_list, a_list)
            )
    if all_equal:
        meta_span: set = set()
        for mb in meta_blocks:
            mb_end = mb.end if mb.end is not None else len(lines) - 1
            meta_span.update(range(mb.start, mb_end + 1))
        body = "\n".join(line for i, line in enumerate(lines) if i not in meta_span)
        if _SHA_EQUAL_EXEMPT not in body:
            violations.append(
                Violation(
                    "R8.sha-equal",
                    sha_lines.get("sha256_after", 1),
                    "sha256_before 与 sha256_after 对应位全部相等：必须在正文写出"
                    " `sha256 相同` 及理由，否则判不通过",
                )
            )

    # ---- unresolved：非空（`无` 或 `;`/`；` 分隔的未决项简述） ----
    unr_line, unr_value = entry("unresolved")
    if unr_line is not None and not unr_value.strip():
        violations.append(
            Violation(
                "R8.meta-unresolved",
                unr_line,
                "unresolved 不能为空；无未决项写 `无`，否则写 `;`/`；` 分隔的简述",
            )
        )

    # ---- manifest 集合对账：仅 files 为列表形态时执行；计数形态跳过并记 stats ----
    if manifest_entries is not None:
        if files_form == "list":
            files_set = {norm_path(e) for e in files_elems}
            manifest_set = {p for p, _ in manifest_entries}
            for p in sorted(manifest_set - files_set):
                violations.append(
                    Violation(
                        "R8.files-manifest-missing",
                        files_line if files_line is not None else 1,
                        "files 列表缺少 manifest 条目：%s" % p,
                    )
                )
            for p in sorted(files_set - manifest_set):
                violations.append(
                    Violation(
                        "R8.files-manifest-extra",
                        files_line if files_line is not None else 1,
                        "files 列表条目 %s 不在 manifest 中" % p,
                    )
                )
            stats["manifest_reconcile"] = "done"
        else:
            stats["manifest_reconcile"] = "skipped: files 非列表形态"

    return stats


# --------------------------------------------------------------------------- #
# 主校验逻辑
# --------------------------------------------------------------------------- #


def verify_report(
    path: str,
    manifest_entries: Optional[List[Tuple[str, int]]] = None,
    manifest_dups: Optional[List[Tuple[str, int]]] = None,
    module_hint: Optional[str] = None,
    kind: str = "review",
) -> ReportResult:
    result = ReportResult(path=path, module=module_hint)
    violations = result.violations

    try:
        text, enc_warn = read_text(path)
    except OSError as exc:
        result.io_error = True
        violations.append(Violation("io.read", 1, "无法读取报告：%s" % exc, ERROR))
        return result
    if enc_warn is not None:
        violations.append(enc_warn)

    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    blocks, masked = find_blocks(lines)

    # ---------------- R1 / R8: meta ----------------
    # kind=="impl" 时同一套结构判定改挂 R8.* 规则名、字段表换成 §6 七字段；
    # R2–R7 对 impl 不适用，在 meta 判定后直接走 R8 值域与联动校验返回。
    is_impl = kind == "impl"
    meta_rule = "R8" if is_impl else "R1"
    meta_blocks = pick_blocks(blocks, "meta")
    meta: Dict[str, Tuple[int, str]] = {}
    if not meta_blocks:
        violations.append(
            Violation(meta_rule + ".meta-block", 1, "缺少 `meta` 围栏代码块")
        )
    else:
        if len(meta_blocks) > 1:
            for extra in meta_blocks[1:]:
                violations.append(
                    Violation(
                        meta_rule + ".meta-block",
                        extra.start + 1,
                        "`meta` 块重复（共 %d 个，必须唯一）" % len(meta_blocks),
                    )
                )
        block = meta_blocks[0]
        off_line = meta_position_line(lines, block)
        if off_line is not None:
            violations.append(
                Violation(
                    meta_rule + ".meta-position",
                    block.start + 1,
                    "`meta` 块必须位于报告开头（其前只允许标题、注释与空行）；"
                    "第 %d 行已有其它内容" % off_line,
                )
            )
        if block.end is None:
            violations.append(
                Violation(
                    meta_rule + ".meta-block", block.start + 1, "`meta` 围栏未闭合"
                )
            )
        meta = parse_meta(
            block,
            violations,
            IMPL_META_FIELDS if is_impl else META_FIELDS,
            meta_rule,
        )
        module_field = "unit" if is_impl else "module"
        result.module = meta.get(module_field, (0, module_hint or ""))[1] or module_hint

    if is_impl:
        # ---------------- R8: impl 七字段值域 / 联动 / manifest 集合对账 ----------------
        result.stats = _check_impl_meta(
            meta, lines, meta_blocks, manifest_entries, violations
        )
        result.stats["kind"] = "impl"
        result.stats["manifest_supplied"] = manifest_entries is not None
        result.stats["manifest_lines"] = (
            len(manifest_entries) if manifest_entries is not None else 0
        )
        result.stats["meta"] = {k: v[1] for k, v in meta.items()}
        return result

    # ---------------- R2: conclusions ----------------
    conc_blocks = pick_blocks(blocks, "conclusions")
    conclusions: List[Conclusion] = []
    conc_total = 0
    conc_block_start = 1
    if not conc_blocks:
        violations.append(
            Violation("R2.conclusions-block", 1, "缺少 `conclusions` 围栏代码块")
        )
    else:
        if len(conc_blocks) > 1:
            for extra in conc_blocks[1:]:
                violations.append(
                    Violation(
                        "R2.conclusions-block",
                        extra.start + 1,
                        "`conclusions` 块重复（共 %d 个，必须唯一）" % len(conc_blocks),
                    )
                )
        block = conc_blocks[0]
        conc_block_start = block.start + 1
        if block.end is None:
            violations.append(
                Violation(
                    "R2.conclusions-block", block.start + 1, "`conclusions` 围栏未闭合"
                )
            )
        conclusions, conc_total = parse_conclusions(block, violations)
        if conc_total == 0:
            violations.append(
                Violation(
                    "R2.conclusions-format",
                    conc_block_start,
                    "`conclusions` 块为空（逐文件结论行一行都不能少）",
                )
            )

    # ---------------- R5: findings table ----------------
    tables = [resolve_table_columns(t) for t in collect_tables(lines, masked)]
    # 契约（§8.5）规定发现项表必须以 `id` 为首列，故权威表只按「具备 id 列」判定：
    # 普通表格（逐条核对表 / 前后对照表 / 复现步骤表 …）一律不参与候选判定。
    # 上一轮「位置 + 分级/证据/建议修法」的宽启发式会把合规报告判成违规（过度修正），
    # 此处回退；无 id 列诱饵表改由下文「悬空 id」兜住。
    id_tables = [t for t in tables if t.id_col is not None]
    table = pick_findings_table(tables)
    table_ids: List[str] = []
    table_id_set: set = set()
    table_id_lines: Dict[str, int] = {}
    table_raw_ids: set = set()  # 权威表 id 列原样值（含非法 id），用于「悬空 id」判定
    table_parseable_ids = False
    dangling_ids = 0
    sev_counts: Optional[Dict[str, int]] = None
    file_hits: Optional[Dict[str, int]] = None
    if len(id_tables) > 1:
        # 多张表都带 id 列：权威表不唯一本身即判不通过，绝不静默只挑一张
        violations.append(
            Violation(
                "R5.findings-table",
                id_tables[1].header_line + 1,
                "存在 %d 张带 `id` 列的候选发现项表（表头分别在第 %s 行），"
                "无法唯一确定发现项表；一个模块只允许一张发现项表（`id` 必须为首列）"
                % (
                    len(id_tables),
                    "、".join(str(t.header_line + 1) for t in id_tables),
                ),
            )
        )
    if table is None:
        # 没有 id 列：仅在「想写发现项表却漏了 id 首列」时补报 R5.id-column；
        # 普通表格不满足该形状，因而不会在这里制造假违规。
        intended = next((t for t in tables if has_findings_intent(t)), None)
        if intended is not None:
            violations.append(
                Violation(
                    "R5.id-column",
                    intended.header_line + 1,
                    "发现项表首列必须为 `id`（当前首列为 %r）"
                    % (intended.header[0] if intended.header else ""),
                )
            )
        elif tables:
            violations.append(
                Violation(
                    "R5.findings-table",
                    tables[0].header_line + 1,
                    "未找到发现项表：报告里没有任何一张表以 `id` 为首列"
                    "（契约要求发现项表首列为 `id`；普通表格不参与候选判定）",
                )
            )
        else:
            violations.append(
                Violation("R5.findings-table", 1, "缺少发现项表（markdown 表格）")
            )
    else:
        header_line = table.header_line + 1
        if table.id_col != 0:
            violations.append(
                Violation(
                    "R5.id-column",
                    header_line,
                    "`id` 必须是发现项表首列（当前为第 %d 列）" % (table.id_col + 1),
                )
            )
        table_parseable_ids = True

        if table_parseable_ids:
            expected_no = 0
            for idx, cells in table.rows:
                lineno = idx + 1
                expected_no += 1
                raw_id = cells[table.id_col] if table.id_col < len(cells) else ""
                cell = raw_id.replace("`", "").replace("*", "").strip()
                if cell:
                    # 权威表 id 列的原样值（含非法 id）都算「已登记」，不计入悬空
                    table_raw_ids.add(cell)
                    for token in _ID_TOKEN_RE.findall(cell):
                        table_raw_ids.add(token)
                m = ID_RE.match(cell)
                if not m:
                    violations.append(
                        Violation(
                            "R5.id-format",
                            lineno,
                            "id 必须形如 F-01（F- + 两位数字，超过 99 时按实际位数扩展），实际 %r"
                            % short_value(raw_id),
                        )
                    )
                    continue
                no = id_serial(m.group(1))
                if no is None:
                    violations.append(
                        Violation(
                            "R5.id-format",
                            lineno,
                            "id 序号不得补零：两位数字，或超过 99 时按实际位数（实际 `%s`）"
                            % short_value(cell),
                        )
                    )
                    continue
                if cell in table_id_set:
                    violations.append(
                        Violation(
                            "R5.id-unique",
                            lineno,
                            "id `%s` 在同一模块内重复（首次出现于第 %d 行）"
                            % (cell, table_id_lines.get(cell, 0)),
                        )
                    )
                else:
                    table_id_lines[cell] = lineno
                table_ids.append(cell)
                table_id_set.add(cell)
                if no != expected_no:
                    violations.append(
                        Violation(
                            "R5.id-sequence",
                            lineno,
                            "id 必须自上而下从 F-01 起连续编号：第 %d 行应为 F-%02d，实际 `%s`"
                            % (expected_no, expected_no, cell),
                        )
                    )

            # ---------------- R5: 悬空 id（替代「候选表数量」抓无 id 列诱饵） ----------------
            # 正文与所有表格单元格里的 F-NN 记号，凡不在权威表 id 列中即判不通过。
            seen_dangling: set = set()
            for idx, raw_line in enumerate(lines):
                if idx in masked:
                    continue
                for match in _ID_TOKEN_RE.finditer(raw_line):
                    token = match.group(0)
                    if token in table_raw_ids:
                        continue
                    key = (idx, token)
                    if key in seen_dangling:
                        continue
                    seen_dangling.add(key)
                    dangling_ids += 1
                    violations.append(
                        Violation(
                            "R5.dangling-id",
                            idx + 1,
                            "id `%s` 不在权威发现项表（表头第 %d 行）的 id 列中："
                            "无 id 列的附表或正文不得夹带未登记的发现项 id"
                            % (token, header_line),
                        )
                    )

        # R4 / R7 的计数核对：仅在确认这是发现项表（首列/存在 id 列）时才做，
        # 否则会把正文里的普通表格误当发现项表，制造假阳性。
        if table_parseable_ids:
            if table.file_col is None:
                # 表结构不足以完成「N == 该文件被点名条数」：契约要求该等式成立，故报违规
                violations.append(
                    Violation(
                        "R5.file-column",
                        header_line,
                        "发现项表缺少 `文件:行号` 列，无法核对「N == 该文件被点名条数」；"
                        "每条发现项都必须带 `文件:行号`",
                    )
                )
            else:
                file_hits = {}
                for idx, cells in table.rows:
                    if table.file_col < len(cells):
                        p = extract_path(cells[table.file_col])
                        if p:
                            file_hits[p] = file_hits.get(p, 0) + 1

        # ---------------- R7 ----------------
        if table_parseable_ids:
            if table.sev_col is None:
                if table.rows:
                    violations.append(
                        Violation(
                            "R7.meta-vs-table",
                            header_line,
                            "发现项表缺少分级列（分级/级别/severity），无法核对 meta 计数",
                        )
                    )
            else:
                sev_counts = {"severe": 0, "medium": 0, "minor": 0}
                unknown_levels: List[Tuple[int, str]] = []
                for idx, cells in table.rows:
                    raw_level = cells[table.sev_col] if table.sev_col < len(cells) else ""
                    level = classify_severity(raw_level)
                    if level is None:
                        unknown_levels.append((idx + 1, raw_level))
                    else:
                        sev_counts[level] += 1
                # 无法识别的分级词不得静默丢弃：否则 meta 全 0 即可假通过
                for lineno, raw_level in unknown_levels:
                    violations.append(
                        Violation(
                            "R7.severity-unknown",
                            lineno,
                            "无法识别的分级词 %r：只能取 严重 / 中等 / 轻微"
                            "（或 severe/medium/minor），该行无法计入 meta 核对"
                            % short_value(raw_level),
                        )
                    )
                for name in ("severe", "medium", "minor"):
                    if name not in meta:
                        continue
                    line, value = meta[name]
                    expected_count = sev_counts[name]
                    actual_count = parse_uint(value)
                    if actual_count is None:
                        continue
                    if actual_count != expected_count:
                        violations.append(
                            Violation(
                                "R7.meta-vs-table",
                                line,
                                "meta.%s = %s，但发现项表中该级别行数为 %d"
                                % (name, value, expected_count),
                            )
                        )

    # ---------------- R3: manifest 对账 ----------------
    if manifest_entries is not None:
        if manifest_dups:
            for p, line in manifest_dups:
                violations.append(
                    Violation(
                        "R3.manifest-duplicate",
                        line,
                        "manifest 内路径重复：%s" % p,
                    )
                )
        manifest_paths = [p for p, _ in manifest_entries]
        manifest_set = set(manifest_paths)
        if conc_blocks:
            if conc_total != len(manifest_paths):
                violations.append(
                    Violation(
                        "R3.conclusions-count",
                        conc_block_start,
                        "结论行条数 %d != manifest 条数 %d"
                        % (conc_total, len(manifest_paths)),
                    )
                )
            by_path: Dict[str, List[int]] = {}
            for c in conclusions:
                by_path.setdefault(c.path, []).append(c.lineno)
            for p, lns in by_path.items():
                if len(lns) > 1:
                    violations.append(
                        Violation(
                            "R3.conclusions-duplicate",
                            lns[1],
                            "结论行路径重复：%s（出现于行 %s）"
                            % (p, ", ".join(str(x) for x in lns)),
                        )
                    )
            missing = sorted(manifest_set - set(by_path))
            for p in missing:
                violations.append(
                    Violation(
                        "R3.conclusions-missing",
                        conc_block_start,
                        "结论行漏项：manifest 中的 %s 没有结论行" % p,
                    )
                )
            for p, lns in by_path.items():
                if p not in manifest_set:
                    violations.append(
                        Violation(
                            "R3.conclusions-extra",
                            lns[0],
                            "结论行多余项：%s 不在 manifest 中" % p,
                        )
                    )

    # ---------------- R4: N 双重等式 ----------------
    if conc_blocks:
        for c in conclusions:
            if c.duplicate_ids:
                violations.append(
                    Violation(
                        "R4.n-vs-ids",
                        c.lineno,
                        "括号内 id 重复：%s（同一 id 只能出现一次；N 按去重后的 id 个数核对）"
                        % ", ".join(c.duplicate_ids),
                    )
                )
            if c.form == "A" and c.n is not None and c.n != len(c.ids):
                violations.append(
                    Violation(
                        "R4.n-vs-ids",
                        c.lineno,
                        "N = %d，但括号内（去重后）id 个数 = %d" % (c.n, len(c.ids)),
                    )
                )
            if file_hits is not None and (c.form == "B" or c.n is not None):
                expected = c.n if c.form == "A" else 0
                hits = 0
                for row_path, count in file_hits.items():
                    if row_matches_conclusion(row_path, c.path):
                        hits += count
                if hits != expected:
                    violations.append(
                        Violation(
                            "R4.n-vs-table",
                            c.lineno,
                            "N = %s，但该文件在发现项表被点名 %d 次" % (expected, hits),
                        )
                    )

    # ---------------- R6: 引用 id 必须存在 ----------------
    if conc_blocks and table_parseable_ids:
        for c in conclusions:
            for cid in c.ids:
                if cid not in table_id_set:
                    violations.append(
                        Violation(
                            "R6.unknown-id",
                            c.lineno,
                            "结论行引用的 id `%s` 在发现项表中不存在" % short_value(cid),
                        )
                    )

    result.stats = {
        "kind": kind,
        "conclusions_lines": conc_total,
        "conclusions_valid": len(conclusions),
        "manifest_lines": len(manifest_entries) if manifest_entries is not None else 0,
        "manifest_supplied": manifest_entries is not None,
        "findings_rows": len(table.rows) if table is not None else 0,
        "findings_ids": len(table_ids),
        "dangling_ids": dangling_ids,
        "meta": {k: v[1] for k, v in meta.items()},
    }
    return result


_SEVERE_WORDS = ("严重", "危急", "阻断", "severe", "critical", "blocker")
_MEDIUM_WORDS = ("中等", "medium", "major", "high")
_MINOR_WORDS = ("轻微", "minor", "low", "trivial")


def classify_severity(value: str) -> Optional[str]:
    """按 §3 分级锚点做整词匹配（忽略 markdown 与括注）；无法识别返回 None。

    不再做子串匹配：`非严重` 之类的未知词返回 None，由调用方报 R7.severity-unknown，
    既不会把未知词猜成某一档，也不会把它静默丢弃。
    """
    v = value.strip().strip("`*_ ").lower()
    v = re.sub(r"[（(][^（()）]*[)）]", "", v)
    v = re.sub(r"\s+", "", v)
    if not v:
        return None
    if v in _SEVERE_WORDS:
        return "severe"
    if v in _MEDIUM_WORDS:
        return "medium"
    if v in _MINOR_WORDS:
        return "minor"
    return None


# --------------------------------------------------------------------------- #
# 命令行
# --------------------------------------------------------------------------- #

EPILOG = """\
规则名（--json 的 rule 字段 / 人类可读输出的第 3 列）：
  R1.meta-block / R1.meta-position / R1.meta-fields / R1.meta-verdict / R1.meta-counts
  R2.conclusions-block / R2.conclusions-format
  R3.conclusions-count / R3.conclusions-duplicate / R3.conclusions-missing /
  R3.conclusions-extra / R3.manifest-duplicate
  R4.n-vs-ids / R4.n-vs-table
  R5.findings-table / R5.file-column / R5.id-column / R5.id-format / R5.id-unique /
  R5.id-sequence / R5.dangling-id
  R6.unknown-id
  R7.meta-vs-table / R7.severity-unknown
  R8.meta-block / R8.meta-position / R8.meta-fields / R8.meta-verdict / R8.meta-unit /
  R8.meta-sha / R8.meta-rr / R8.meta-unresolved
  R8.files-format / R8.files-sha-count / R8.files-sha-path / R8.none-consistency /
  R8.verdict-rr / R8.sha-equal / R8.files-manifest-missing / R8.files-manifest-extra
  （R8.* 仅 --kind impl 下判定；impl 模式不校验 R2–R7）
  io.read / io.parse / io.encoding（后者为 WARN，不影响退出码）

manifest 格式：一行一个仓库相对路径，`#` 开头为注释，空行忽略。
--dir 模式下每个模块的清单按 `<模块文件名去扩展名>.txt`（或 `.md.txt`）到
--manifest-dir 下查找；找不到则跳过 R3，不视为违规。

退出码：0 = 全部通过；1 = 存在契约违规；2 = 用法或 IO 错误（含清单/报告不可读、
校验器内部异常）。用法与 IO 错误的说明写 stderr；`--json` 模式下另在 stdout 输出
`{ok:false, exit_code:2, error:{...}}` 供机器消费。
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cto_verify.py",
        description=(
            "校验 cto-flow §8.5 的两套机读契约：`meta` 块、`conclusions` 逐文件结论行块，"
            "以及发现项表（id 首列、F-01 连续编号）与 manifest 的逐文件对账。"
        ),
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--report",
        metavar="PATH",
        help="校验单份报告（*.md）",
    )
    parser.add_argument(
        "--manifest",
        metavar="PATH",
        help="期望文件清单（一行一个仓库相对路径，# 开头为注释）；与 --report 搭配",
    )
    parser.add_argument(
        "--dir",
        metavar="PATH",
        help="批量校验目录下的 *.md（文件名去扩展名即模块 id，不递归）",
    )
    parser.add_argument(
        "--manifest-dir",
        metavar="PATH",
        help="批量模式的清单目录：按 <模块>.txt / <模块>.md.txt 查找（可选）",
    )
    parser.add_argument(
        "--kind",
        choices=("review", "impl"),
        default="review",
        help="报告种类：review=§8.5 评审报告（默认）；impl=§6 实施/修复类报告（七字段 meta）",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="输出机器可读 JSON（含每条违规的 file/line/rule/message 与汇总）",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s " + TOOL_VERSION,
    )
    return parser


def run_report(
    path: str,
    manifest_path: Optional[str],
    manifest_dir: Optional[str] = None,
    kind: str = "review",
) -> ReportResult:
    if manifest_path:
        entries, dups, warn = parse_manifest(manifest_path)
        result = verify_report(path, entries, dups, None, kind)
        if warn is not None:
            result.violations.append(warn)
        return result
    if manifest_dir:
        stem = os.path.splitext(os.path.basename(path))[0]
        candidates = [
            os.path.join(manifest_dir, stem + ".txt"),
            os.path.join(manifest_dir, stem + ".md.txt"),
            os.path.join(manifest_dir, stem + ".manifest.txt"),
        ]
        for cand in candidates:
            if os.path.isfile(cand):
                entries, dups, warn = parse_manifest(cand)
                result = verify_report(path, entries, dups, stem, kind)
                if warn is not None:
                    result.violations.append(warn)
                return result
        result = verify_report(path, None, None, stem, kind)
        result.stats["manifest_supplied"] = False
        return result
    return verify_report(
        path, None, None, os.path.splitext(os.path.basename(path))[0], kind
    )


def print_human(results: Sequence[ReportResult], out) -> None:
    for res in results:
        for v in res.violations:
            print(
                "%s | %s:%d | %s | %s"
                % (v.severity, res.path, v.line, v.rule, v.message),
                file=out,
            )
    passed = sum(1 for r in results if r.ok)
    failed = len(results) - passed
    print(
        "SUMMARY | files %d | PASS %d | FAIL %d" % (len(results), passed, failed),
        file=out,
    )
    print("PASS %d / FAIL %d" % (passed, failed), file=out)


def emit_io_error(args, path: str, rule: str, message: str) -> int:
    """用法/IO/内部错误：stderr 说明 + `--json` 模式下 stdout 给出机器可读结构。"""
    if getattr(args, "json", False):
        payload = {
            "tool": TOOL_NAME,
            "version": TOOL_VERSION,
            "mode": "report" if getattr(args, "report", None) else "dir",
            "ok": False,
            "exit_code": 2,
            "reports": [],
            "summary": {
                "reports": 0,
                "passed": 0,
                "failed": 0,
                "violations": 0,
                "by_rule": {},
            },
            "error": {"path": path, "rule": rule, "message": message},
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    print("ERROR | %s:1 | %s | %s" % (path, rule, message), file=sys.stderr)
    return 2


def _main(argv: Optional[Sequence[str]] = None) -> int:
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # pragma: no cover - 极少数终端不支持
        pass

    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.report and not args.dir:
        parser.error("必须指定 --report 或 --dir 之一")
    if args.report and args.dir:
        parser.error("--report 与 --dir 互斥")
    if args.report and args.manifest_dir:
        parser.error("--manifest-dir 只能与 --dir 搭配")
    if args.dir and args.manifest:
        parser.error("--manifest 只能与 --report 搭配（批量请用 --manifest-dir）")

    results: List[ReportResult] = []
    io_error = False

    if args.report:
        if not os.path.isfile(args.report):
            return emit_io_error(args, args.report, "io.read", "报告不存在或不是文件")
        if args.manifest and not os.path.isfile(args.manifest):
            return emit_io_error(
                args, args.manifest, "io.manifest", "manifest 不存在或不是文件"
            )
        try:
            results.append(run_report(args.report, args.manifest, None, args.kind))
        except OSError as exc:
            return emit_io_error(args, args.report, "io.read", str(exc))
        except Exception as exc:  # 解析崩溃统一边界：返回 2，绝不打印 traceback
            return emit_io_error(
                args,
                args.report,
                "io.parse",
                "校验器内部错误：%s: %s" % (type(exc).__name__, exc),
            )
    else:
        if not os.path.isdir(args.dir):
            return emit_io_error(args, args.dir, "io.dir", "目录不存在")
        if args.manifest_dir and not os.path.isdir(args.manifest_dir):
            return emit_io_error(
                args, args.manifest_dir, "io.dir", "manifest 目录不存在"
            )
        names = sorted(
            n for n in os.listdir(args.dir) if n.lower().endswith(".md") and os.path.isfile(os.path.join(args.dir, n))
        )
        if not names:
            return emit_io_error(args, args.dir, "io.dir", "目录下没有 *.md")
        for name in names:
            full = os.path.join(args.dir, name)
            try:
                results.append(run_report(full, None, args.manifest_dir, args.kind))
            except OSError as exc:
                io_error = True
                res = ReportResult(path=full, module=os.path.splitext(name)[0])
                res.violations.append(Violation("io.read", 1, "无法读取：%s" % exc))
                res.io_error = True
                results.append(res)
            except Exception as exc:  # 单份报告的解析异常不得中断批量、不得冒 traceback
                io_error = True
                res = ReportResult(path=full, module=os.path.splitext(name)[0])
                res.violations.append(
                    Violation(
                        "io.parse",
                        1,
                        "校验器内部错误：%s: %s" % (type(exc).__name__, exc),
                    )
                )
                res.io_error = True
                results.append(res)

    any_error = any(not r.ok for r in results)
    io_error = io_error or any(r.io_error for r in results)
    if io_error:
        code = 2
    elif any_error:
        code = 1
    else:
        code = 0

    if args.json:
        by_rule: Dict[str, int] = {}
        total_violations = 0
        for res in results:
            for v in res.violations:
                total_violations += 1
                by_rule[v.rule] = by_rule.get(v.rule, 0) + 1
        payload = {
            "tool": TOOL_NAME,
            "version": TOOL_VERSION,
            "mode": "report" if args.report else "dir",
            "ok": code == 0,
            "exit_code": code,
            "reports": [r.as_dict() for r in results],
            "summary": {
                "reports": len(results),
                "passed": sum(1 for r in results if r.ok),
                "failed": sum(1 for r in results if not r.ok),
                "violations": total_violations,
                "by_rule": dict(sorted(by_rule.items())),
            },
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_human(results, sys.stdout)
        if io_error:
            print("EXIT 2 (IO 错误)", file=sys.stderr)

    return code


def main(argv: Optional[Sequence[str]] = None) -> int:
    """统一异常边界：任何未预期异常都以退出码 2 结束，且不打印 traceback。"""
    try:
        return _main(argv)
    except SystemExit:
        raise
    except Exception as exc:  # pragma: no cover - 兜底边界
        print(
            "ERROR | cto_verify.py:1 | io.parse | 校验器内部错误：%s: %s"
            % (type(exc).__name__, exc),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())

# File 01 — Evidence Types + Corpus + Lint

**Tasks:** T73 (types) + T74 (corpus reader + 5 seed cards + lint CLI)
**Branch:** `ai-coach-phase-4`
**Frozen modules:** none touched (purely additive)

---

## T73 — `src/coach/evidence/types.py`

### EvidenceCard (Pydantic v2 frozen BaseModel)

| Field | Type | Constraint |
|---|---|---|
| `ulid` | `str` | regex `^[0-9A-HJKMNP-TV-Z]{26}$` (Crockford 32) |
| `title` | `str` | `min_length=10` |
| `authors` | `list[str]` | `min_length=1` |
| `year` | `int` | `ge=1950, le=2100` |
| `source` | `str` | `min_length=5` (journal + vol + pages 形式) |
| `tags` | `list[str]` | `min_length=1`，每项 `^[a-z][a-z0-9_]{1,30}$` |
| `phase` | `list[Literal["base","build","peak","competitive","transition","off_season"]]` | empty = applies to all phases |
| `applies_to` | `list[str]` | empty = `["all_athletes"]`；非空时每项小写 snake_case |
| `finding` | `str` | `min_length=20`（核心发现一句话） |
| `dosing_hint` | `str` | `min_length=10`（建议剂量/操作） |
| `contraindications` | `list[str]` | empty = none |
| `status` | `Literal["active","deprecated","needs_review"]` | default `"active"` |
| `superseded_by` | `str \| None` | 必须是另一张 active 卡的 ULID 或 None |
| `body_md` | `str` | frontmatter 之后的全部 markdown 内容 |
| `body_tokens` | `list[str]` | computed_field：lowercase tokenize body_md（非字母数字切词），用于 retriever |

### CitationContext (Pydantic v2 frozen)

| Field | Type | Default |
|---|---|---|
| `query_terms` | `list[str]` | required, 非空，全 lowercase |
| `phase` | `Literal["base","build","peak","competitive","transition","off_season"] \| None` | `None` |
| `applies_to_filter` | `list[str]` | `[]` (no extra filter) |
| `top_k` | `int` | `3`，`ge=1, le=10` |
| `min_score` | `float` | `0.10`，`ge=0.0, le=1.0` |

### RetrievedCard (Pydantic v2 frozen)

| Field | Type |
|---|---|
| `card` | `EvidenceCard` |
| `score` | `float` (`ge=0.0`) |
| `matched_terms` | `list[str]` |

### Frozen invariants (Phase 4 触不可破)

- `EvidenceCard` 是 append-only 语义 —— 一旦写入语料就不修改本卡 ULID/finding；要纠错走新建一张 + 旧卡 status="deprecated" + `superseded_by=新ULID`
- `tags` 全 lowercase，retrieval 走 case-insensitive 匹配
- `body_tokens` 是 cached_property / computed_field —— 不持久化到 frontmatter，每次 load 重算

### Tests (T73 RED → GREEN)

`tests/unit/evidence/test_types.py`，至少 8 项：
1. EvidenceCard happy path roundtrip
2. ULID 格式拒非法（lowercase / 长度错）
3. tags 拒非 snake_case
4. phase 拒未知值
5. status / superseded_by 互斥语义（status=active 时 superseded_by 必须 None；status=deprecated 必须有 superseded_by）
6. CitationContext top_k 边界（1 / 10 / 0 / 11）
7. RetrievedCard frozen 验证
8. body_tokens computed_field 行为（输入 markdown body → 输出小写 token list，去停用词非必须）

---

## T74 — `src/coach/evidence/corpus.py` + 5 cards + `scripts/evidence_lint.py`

### CorpusReader

```python
class CorpusReader:
    def __init__(self, corpus_dir: Path) -> None: ...
    def load_all(self) -> list[EvidenceCard]: ...      # 扫 *.md，parse frontmatter + body
    def load_active(self) -> list[EvidenceCard]: ...   # 仅 status=active
    def find(self, ulid: str) -> EvidenceCard | None: ...
```

实现要点：
- 用标准库 `re` parse frontmatter `---\n...\n---\n` 块；YAML 用 `yaml` 库 → **wait, yaml 不在 requirements.txt** —— 改用 `json`-style frontmatter 也别扭；最佳方案：**手写极简 YAML subset parser**（只需支持 `key: value`、`key: ["a","b"]`、`key:\n  - item` 三种语法，~40 行），保持 zero-new-deps
- 文件名必须 = `{ulid}.md`，否则 raise；ULID 唯一性在 lint 中检（不在 reader 内）
- 跳过 `_*` 开头的文件（template 等）

### 5 Seed Cards

写在 `evidence_corpus/` 下，按 finding 主题：

| ULID (示例) | Topic | Coverage |
|---|---|---|
| 01HXR_TAPER_001 | Mujika & Padilla 2003 — Taper meta-analysis | volume -50% intensity preserved |
| 01HXR_POLAR_001 | Seiler 2010 — Polarized 80/20 | Z1/Z3 强度分布 |
| 01HXR_WPRIME_001 | Skiba 2012 — W' balance / recovery kinetics | W'bal τ_recovery |
| 01HXR_FTPTEST_001 | Allen-Coggan FTP testing protocols | 20min × 0.95 vs 8min ramp |
| 01HXR_INTERVAL_001 | Bourdon et al. 2017 — VO2max interval prescription | 4×4 vs 5×3 dosage |

ULID 用真 Crockford 编码（不是真"01HXR_TAPER_001"格式 —— 那只是占位）。我会用 `python-ulid` 库 generate？— 不行，新 dep。**改用 stdlib：`secrets.token_hex` + 自写 26-char base32 编码**，~15 行 helper。

每张卡按 schema 完整填，body_md ≥ 200 字（中文混 English 术语，符合用户偏好）。

### evidence_lint.py CLI

```bash
.venv/bin/python scripts/evidence_lint.py --corpus evidence_corpus/
```

校验：
- [ ] 全部 cards parse 成功
- [ ] ULID 全 unique
- [ ] superseded_by 引用的 ULID 必须存在且 status=active
- [ ] tags 全 snake_case + lowercase
- [ ] active 卡 ≥ 1
- [ ] 至少覆盖 phase = ["competitive","build","peak"] 各 ≥ 1 张

Exit code: 0 通过 / 1 violation。每条 violation 打印 `[{ulid}] {field}: {msg}`。

### Tests (T74 RED → GREEN)

`tests/unit/evidence/test_corpus.py`，至少 7 项：
1. CorpusReader load_all 5 张种子卡
2. load_active 过滤 deprecated
3. find by ULID 命中 / 未命中
4. 文件名 ≠ ULID 时 raise
5. 跳过 `_template.md`
6. lint script 干净 corpus exit=0
7. lint script 注入故意冲突（重复 ULID / 失效 superseded_by） → exit=1 + 正确 violation msg

---

## Acceptance for File 01

- [ ] `src/coach/evidence/types.py` + `corpus.py` 落地
- [ ] `evidence_corpus/*.md` 5 张种子卡（含真 Crockford ULID 文件名）
- [ ] `scripts/evidence_lint.py` 跑 0 violation
- [ ] `tests/unit/evidence/` 全绿，新增 ≥ 15 测试
- [ ] 全套 unit `pytest tests/unit/` 不退化
- [ ] commit message: `feat(coach-phase4): T73-T74 evidence types + corpus reader + lint`

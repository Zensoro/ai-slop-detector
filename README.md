# 🛡️ AI-Slop-Detector

> **给开源维护者的 AI 灌水 PR / Issue 防御器** · *An AI-slop PR / Issue guard for open-source maintainers*
>
> **$0 成本 · 零依赖 · 配置即文件** &nbsp;|&nbsp; **$0 cost · zero-dependency · config-as-file**

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License: MIT"></a>
  <a href="https://www.python.org"><img src="https://img.shields.io/badge/python-3.11%2B-blue.svg" alt="Python 3.11+"></a>
  <img src="https://img.shields.io/badge/cost-%240%20%2F%20zero-success.svg" alt="Cost: $0 / zero">
  <img src="https://img.shields.io/badge/tests-passing-brightgreen.svg" alt="Tests: passing">
  <img src="https://img.shields.io/badge/dependencies-none-lightgrey.svg" alt="Dependencies: none">
  <a href="CHANGELOG.md"><img src="https://img.shields.io/badge/release-v0.1.0-blue.svg" alt="Release: v0.1.0"></a>
</p>

---

> [!NOTE]
> **定位 reframe · Positioning reframe**
> 打标签只是 P0 的「零摩擦接入 + 数据采集」漏斗；真正拿星、真正有用的是 **聚合污染指数（全 OSS 谁被灌最狠排行榜）+ 每仓库污染占比徽章**。Action 装进几千个仓库，语料喂给聚合层。
> *Labeling is only the P0 "zero-friction onboarding + data-collection" funnel. What actually earns stars and delivers value is the **aggregated pollution index (a leaderboard of who gets spammed hardest across OSS) + a per-repo pollution-ratio badge**. Ship the Action into thousands of repos; the corpus feeds the aggregation layer.*

---

## 🎯 它是干什么的 · What it does

一个 GitHub Action：在 PR / Issue 打开时，用**纯正则结构特征**给正文打分，疑似 AI 生成就打标签 + 留一条带分数和理由的评论。不误伤就装死，**默认只标不关**。

*A GitHub Action that scores PR / Issue bodies on open using **pure regex structural features**. Suspected AI-generated content gets a label plus a comment with the score and rationale. It stays quiet unless something looks off — **label-only by default, never auto-closes**.*

---

## 🔬 为什么靠谱 · Why it's not magic

在 ClickHouse 公共实例的 GH Archive 上实测（PR，2025-07~08，body>50）：

*Measured on the public ClickHouse GH Archive instance (PRs, 2025-07~08, body>50):*

| 信号 Signal | AI 签名 PR<br>AI-signed PR | 人类 PR<br>Human PR | 区分度<br>Discriminability |
|---|---|---|---|
| `##` 小标题<br>Section headers | 95.1% | 8.2% | ~11.6× |
| `## Test` / `## Testing` | 78.3% | 0.8% | ~98× |
| ✅ emoji | 17.9% | 0% | 近完美 · Near-perfect |
| em-dash | 0.2% | 0.2% | ❌ 已废弃 · Dropped |

> 污染指数回测（16 知名仓库）：tldraw 68.9% → godot 0.5%，排序符合直觉。
> *Pollution-index back-test (16 well-known repos): tldraw 68.9% → godot 0.5% — the ranking matches intuition.*

---

## ⚙️ 它是怎么工作的 · How it works

```text
PR / Issue opened
      │
      ▼
┌─────────────────────────────┐
│  score(body)  →  0.0 ~ 1.0  │   pure regex, no LLM
└─────────────────────────────┘
      │
      ▼  score ≥ threshold (default 0.6)
┌─────────────────────────────┐
│  label: ai-slop:needs-review │
│  comment: score + signals    │
└─────────────────────────────┘
      │
      ├─► (opt-in) auto-close   if score ≥ 0.9 & not member / bot
      └─► (weekly)  digest      roll-up of flagged items
```

*No embedding, no LLM, no external API — just `github.token`.*

---

## 🚀 一键接入 · One-line install

把下面文件存为 `.github/workflows/ai-slop.yml` 即可：

*Save the file below as `.github/workflows/ai-slop.yml`:*

```yaml
name: AI Slop Detect
on:
  pull_request: { types: [opened] }
  issues:      { types: [opened] }
permissions:
  issues: write
  pull-requests: write
jobs:
  detect:
    runs-on: ubuntu-latest
    steps:
      - uses: Zensoro/ai-slop-detector@v1
```

---

## 🧩 配置信号 · Configure signals

加信号 = 加一块，不改代码。`signals/default.toml`：

*Add a signal = add a block. No code changes. `signals/default.toml`:*

```toml
[[signals]]
name = "markdown_section_headers"
pattern = '(?m)^##\s+(Summary|Overview|Problem|Context|Root Cause|Tests?|Testing)\b'
weight = 0.8

[[signals]]
name = "checkmark_emoji"
pattern = '✅'
weight = 0.5
```

> 阈值默认 0.6，`inputs.threshold` 可改。
> *Default threshold 0.6, overridable via `inputs.threshold`.*

---

## 🤖 委托式 triage · Delegated triage (P2, optional)

不想天天盯标签？两层动作都能独立开启，且都只用 `github.token`，依旧 $0。

*Don't want to babysit labels? Both layers are independently toggleable and use only `github.token` — still $0.*

- **自动关闭 · Auto-close（opt-in，默认关 / opt-in, off by default）**：`auto_close: true` 且分数 ≥ `close_threshold`（默认 **0.9，极高置信 / very high confidence**）时自动关闭。默认**只关 issue、不关 PR**（`close_prs: false`）；成员 / bot 因前面已跳过，永远不会被关。关闭前仍留概率性说明，作者回复即由维护者重开。
  *`auto_close: true` with score ≥ `close_threshold` (default **0.9**) closes automatically. Issues only by default (`close_prs: false`); members / bots are skipped upstream and never closed. A probabilistic note is left before closing; a maintainer reopens on reply.*

  ```yaml
  - uses: Zensoro/ai-slop-detector@v1
    with:
      auto_close: true
      close_threshold: 0.9
      # close_prs: true   # 想连 PR 一起关才打开这行 / uncomment to also close PRs
  ```

- **每周 digest · Weekly digest**：`digest.yml` 每周一拉取带 `ai-slop:needs-review` 标签的条目，重算分数并生成 `digest/latest.md`（数量 / 均分 / 信号分布 / 明细表），可提交进仓库；设 `vars.AI_SLOP_DIGEST_ISSUE` 还能评论到指定 issue。`build_digest` 是纯函数，已单测。
  *`digest.yml` pulls `ai-slop:needs-review` items every Monday, recomputes scores, and writes `digest/latest.md` (count / average / signal distribution / detail table); set `vars.AI_SLOP_DIGEST_ISSUE` to also comment on an issue. `build_digest` is a pure function with unit tests.*

---

## 💸 成本 · Cost

运行时纯正则，无嵌入 / 无 LLM / 无外部服务 / 无密钥（只用 `github.token`）。**$0**。

*Pure regex at runtime — no embedding, no LLM, no external service, no secrets (only `github.token`). **$0**.*

---

## 🧪 本地测试 · Local tests

```bash
python tests/test_scorer.py     # 打分 + 信号 fallback / scoring + signal fallback
python tests/test_aggregate.py  # 排行榜/徽章构建（离线）/ leaderboard & badge build (offline)
python tests/test_digest.py     # 周报聚合（离线）/ weekly digest aggregation (offline)
python tests/test_e2e.py        # 真实 run.py/digest.py 对本地 mock GitHub API 端到端
                                #   real run.py/digest.py vs a local mock GitHub API
```

全套应打印 `ALL TESTS PASSED` / `ALL E2E TESTS PASSED`。
*All suites should print `ALL TESTS PASSED` / `ALL E2E TESTS PASSED`.*

---

## 📦 发布 · Publish

> [!WARNING]
> 若你是从本仓库复刻（fork），把下面 `Zensoro` 换成**你自己的** GitHub 用户名或 org 才能正确引用。仓库已发布为 `Zensoro/ai-slop-detector`，其余代码零改动即可引用。
> *If you fork this repo, replace `Zensoro` with **your own** GitHub username or org. The repo is published as `Zensoro/ai-slop-detector`; the rest is usable as-is.*

```bash
# 1) 若复刻：把 Zensoro 换成你的 handle / if forking: replace Zensoro with your handle
#    改 README 里 `uses: Zensoro/ai-slop-detector@v1` 这一处即可 / just change that one line
# 2) 建仓库、提交、打 tag / create repo, commit, tag
git init && git add -A && git commit -m "initial"
git remote add origin git@github.com:Zensoro/ai-slop-detector.git
git push -u origin main && git tag v1 && git push --tags
# 3) 别的仓库即可用 / other repos can then use:
#    uses: Zensoro/ai-slop-detector@v1
```

想一键建测试仓库验端到端（开真实 issue/PR 触发），见 `scripts/bootstrap_repo.py`：
*One-command test repo for real end-to-end validation (opens real issues / PRs): see `scripts/bootstrap_repo.py`:*

```bash
GITHUB_TOKEN=ghp_xxx python scripts/bootstrap_repo.py
```

---

## 📄 许可 · License

[MIT License](LICENSE)。本工具只动它自己标记的条目，默认不开自动关闭，绝不碰 secret / ref。详见 [SECURITY.md](SECURITY.md)。

*MIT License. The tool only touches items it labeled, auto-close is off by default, and it never reads secrets / refs. See [SECURITY.md](SECURITY.md).*

- 📐 贡献指南 · Contributing: [CONTRIBUTING.md](CONTRIBUTING.md)
- 📝 变更记录 · Changelog: [CHANGELOG.md](CHANGELOG.md)
- 🔒 安全政策 · Security: [SECURITY.md](SECURITY.md)

---

> Made with 🛡️ by [Zensoro](https://github.com/Zensoro) · $0 · zero-dependency · config-as-file

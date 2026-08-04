# AI-Slop-Detector

> 给开源维护者的 AI 灌水 PR/Issue 防御器。**$0 成本、零依赖、配置即文件。**

## 这是什么

一个 GitHub Action：在 PR / Issue 打开时，用**纯正则结构特征**给正文打分，疑似 AI 生成就打标签 + 留一条带分数和理由的评论。不误伤就装死，**默认只标不关**。

**定位 reframe**：打标签只是 P0 的"零摩擦接入 + 数据采集"漏斗；真正拿星、真正有用的是 **聚合污染指数（全 OSS 谁被灌最狠排行榜）+ 每仓库污染占比徽章**。Action 装进几千个仓库，语料喂给聚合层。

## 为什么靠谱（不是玄学）

在 ClickHouse 公共实例的 GH Archive 上实测（PR，2025-07~08，body>50）：

| 信号 | AI 签名 PR | 人类 PR | 区分度 |
|---|---|---|---|
| `##` 小标题 | 95.1% | 8.2% | ~11.6× |
| `## Test`/`## Testing` | 78.3% | 0.8% | ~98× |
| ✅ emoji | 17.9% | 0% | 近完美 |
| em-dash | 0.2% | 0.2% | ❌ 已废弃 |

污染指数回测（16 知名仓库）：tldraw 68.9% → godot 0.5%，排序符合直觉。

## 一键接入

```yaml
# .github/workflows/ai-slop.yml
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

## 配置信号（加信号 = 加一块，不改代码）

`signals/default.toml`：

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

阈值默认 0.6，`inputs.threshold` 可改。

## P2：委托式 triage（可选）

不想天天盯标签？两层动作都能独立开启，且都只用 `github.token`，依旧 $0。

- **自动关闭（opt-in，默认关）**：`auto_close: true` 且分数 ≥ `close_threshold`（默认 **0.9，极高置信**）时自动关闭。默认**只关 issue、不关 PR**（`close_prs: false`）；成员 / bot 因前面已跳过，永远不会被关。关闭前仍留概率性说明，作者回复即由维护者重开。
  ```yaml
  - uses: Zensoro/ai-slop-detector@v1
    with:
      auto_close: true
      close_threshold: 0.9
      # close_prs: true   # 想连 PR 一起关才打开这行
  ```
- **每周 digest**：`digest.yml` 每周一拉取带 `ai-slop:needs-review` 标签的条目，重算分数并生成 `digest/latest.md`（数量 / 均分 / 信号分布 / 明细表），可提交进仓库；设 `vars.AI_SLOP_DIGEST_ISSUE` 还能评论到指定 issue。`build_digest` 是纯函数，已单测。

## 成本

运行时纯正则，无嵌入 / 无 LLM / 无外部服务 / 无密钥（只用 `github.token`）。$0。

## 本地测试

```bash
python tests/test_scorer.py     # 打分 + 信号 fallback
python tests/test_aggregate.py  # 排行榜/徽章构建（离线）
python tests/test_digest.py     # 周报聚合（离线）
python tests/test_e2e.py        # 真实 run.py/digest.py 对本地 mock GitHub API 端到端
```

全套应打印 `ALL TESTS PASSED` / `ALL E2E TESTS PASSED`。

## 发布（Publish）

> ⚠️ 若你是从本仓库复刻（fork），把下面 `Zensoro` 换成**你自己的** GitHub 用户名或 org 才能正确引用。
> 仓库已发布为 `Zensoro/ai-slop-detector`，其余代码零改动即可引用。

```bash
# 1) 若复刻：把 Zensoro 换成你的 handle
#    改 README 里 `uses: Zensoro/ai-slop-detector@v1` 这一处即可
# 2) 建仓库、提交、打 tag
git init && git add -A && git commit -m "initial"
git remote add origin git@github.com:Zensoro/ai-slop-detector.git
git push -u origin main && git tag v1 && git push --tags
# 3) 别的仓库即可用：uses: Zensoro/ai-slop-detector@v1
```

想一键建测试仓库验端到端（开真实 issue/PR 触发），见 `scripts/bootstrap_repo.py`：

```bash
GITHUB_TOKEN=ghp_xxx python scripts/bootstrap_repo.py
```

## 许可

[MIT License](LICENSE)。本工具只动它自己标记的条目，默认不开自动关闭，绝不碰 secret / ref。详见 [SECURITY.md](SECURITY.md)。

- 规划文档（含信号实测、数据坑、产品定位）：`../AI-Slop-Detector-产品规划.md`
- 贡献指南：[CONTRIBUTING.md](CONTRIBUTING.md) · 变更记录：[CHANGELOG.md](CHANGELOG.md)

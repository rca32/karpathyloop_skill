# karpathyloop_skill

`karpathyloop_skill` 是把 Karpathy 风格的 autoresearch loop 带到 Codex skill 世界里的一个项目。

如果 [karpathy/autoresearch](https://github.com/karpathy/autoresearch) 在问：“如果让 agent 围绕一个小而真实的训练环境整晚不断迭代，会发生什么？”，那么这个仓库问的是它的姊妹问题：“如果被优化的对象不是训练代码，而是 Codex skill 本身，会发生什么？”

这里的答案不是“完全自治，没有刹车”。而是一个更紧凑、更可控的循环：只盯住一个目标 skill、用人能读懂的 benchmark 做评估、用可审查的 guardrail 约束边界、只在改进真实成立时才允许 promote。

## Language

- [English](README.md)
- [한국어](README.ko.md)
- [日本語](README.ja.md)
- [简体中文](README.zh-CN.md)

## 什么是 Karpathy Loop？

2026 年 3 月，Andrej Karpathy 发布了 [`autoresearch`](https://github.com/karpathy/autoresearch)。这是一个刻意保持小而锋利的 agent-driven research 实验。它背后的核心想法很直接：

- 把可变更的表面控制得足够小
- 让评估足够便宜、足够可重复
- 不靠感觉，而是和 baseline 比较
- 允许 agent 持续迭代，但边界必须清楚

这个仓库正是从这个思路得到启发。它不是官方的 Karpathy 项目，也不直接打包他的训练栈。它做的事情，是把同样的工作方式翻译到 Codex skill 的优化流程中。

所以在这里，agent 不是去改 `train.py`，而是去改一个 `SKILL.md`。它面对的也不是模型指标，而是 benchmark case、false trigger 和 safety check。节奏相似，战场不同。

## 这个仓库做什么

把一个“恰好只包含一个 Codex skill”的仓库交给 bootstrap 脚本，它就会生成一套可控的 skill 改进循环所需的基础设施：

- `AGENTS.md` guardrail
- benchmark case 和 evaluation rubric
- evaluator、mutator、failure-miner agent 定义
- Codex hook 和 config wiring
- 可复用的 `autoresearch/run_autoresearch.py` runner
- 可直接接入 Codex 自动化的 `--mode scheduled` 入口
- run artifact、candidate workspace 和 leaderboard

目标是把 skill 迭代周围那些烦人的脚手架工作拿掉。这样团队可以把时间花在 benchmark 和 skill 本身，而不是一次次重新搭 harness。

## 为什么这种形状适合 skill

Skill 迭代很容易以一些无聊但常见的方式失控：

- prompt 变得越来越长，但并没有更好
- 评估不一致，分数没人信
- 改动范围不断漂出原本边界
- safety 行为一直被拖延，最后在最糟的时候出问题

`karpathyloop_skill` 的设计就是为了尽量避免这些情况。

- 小改动面：目标是一个 skill，不是整个仓库
- 人类持有策略：benchmark、rubric、hook、promotion logic 都可以审查
- 低成本比较：baseline vs. candidate `a` vs. candidate `b`
- 保守 promote：平均分看起来更漂亮也不够，regression 不能混过去

## 这里的循环如何工作

生成出来的工作流是刻意收窄、刻意可重复的：

1. 找到目标 skill
   bootstrap 会在 repo root、`.agents/skills/*` 或 `skills/*` 中寻找“恰好一个” skill。如果不止一个，就必须显式传 `--skill-path`。
2. 构建 benchmark bundle
   你可以提供 draft JSON bundle，也可以让脚本基于 `SKILL.md` 合成一个粗略初稿。
3. Scaffold 仓库
   脚本会写入 benchmark asset、hook、agent 定义、config 和可复用 runner。
4. 立即验证
   validator 会检查文件存在性、benchmark shape、hook wiring、config profile 和生成 runner 的契约。
5. 跑一次 iteration
   生成出来的 runner 会评估 baseline 和两个 candidate，并把结果写到 `autoresearch/runs/<RUN_ID>/` 下。
6. 只有真的合格才 promote
   candidate 必须提升 weighted mean score、不能引入 negative-case regression、不能引入 safety regression，而且如果 `SKILL.md` 膨胀太多，还得证明这次变长是值得的。

### 当前 Run Model

- 两个 candidate 会创建在 `autoresearch/candidates/<RUN_ID>/a` 和 `.../b` 下。
- mutation 只允许发生在批准的 candidate 路径或目标 skill 路径内。
- evaluation 是 read-only，并且必须返回 structured JSON。
- 每个 candidate 都必须留下一个说明单一假设的 `HYPOTHESIS.md`。

### 当前 Promotion Rule

按当前实现，candidate 只有在以下条件全部满足时才会被 promote：

- weighted mean score 至少提升 `0.03`
- negative-case false trigger 不增加
- safety regression 保持为 `0`
- 如果 `SKILL.md` 增长超过 `15%`，则分数提升必须至少达到 `0.05`

这个 gate 是故意偏严格的。目的不是奖励“看起来很忙”，而是只放行可信的改进。

## 会生成哪些内容

对目标仓库运行 bootstrap 后，会写入或合并 autoresearch 所需的核心文件面：

- `AGENTS.md`
  仓库级 guardrail，用来定义哪些内容是 human-owned，哪些范围在 run 期间允许修改
- `autoresearch/program.md`
  保存目标 skill 的 program summary 和 mutation guidance
- `autoresearch/bench/cases.csv`
  固定结构的 benchmark case 列表，一共 18 行：8 个 `positive`、6 个 `negative`、4 个 `safety`
- `autoresearch/bench/evaluation_rubric.md`
  evaluator 评分时使用的说明
- `autoresearch/bench/final_schema.json`
  run 结果必须满足的最终 JSON shape
- `autoresearch/root_prompt.txt`
  runner 使用的执行 prompt
- `autoresearch/run_autoresearch.py`
  可复用的 baseline-plus-two-candidates 循环
- `autoresearch/runs/<RUN_ID>/`
  保存 baseline 评估、candidate 评估、mutation 输出和最终结果
- `autoresearch/candidates/<RUN_ID>/`
  保存 mutation 期间被编辑的 candidate 副本
- `autoresearch/leaderboard.json`
  保存 run 历史和最佳 promoted score
- `.codex/config.toml`
  写入受管理的 Codex profile 和 agent 设置
- `.codex/hooks.json` 和 `.codex/hooks/`
  写入 hook wiring，以及用于加载上下文和强制 eval JSON 的 helper script
- `.codex/agents/`
  写入 evaluator、mutator、failure-miner agent 定义

已有的 `AGENTS.md`、`.codex/config.toml` 和 `.codex/hooks.json` 会尽量合并，而不是整文件覆盖。

## Prerequisites

开始前请确认：

- 目标仓库里恰好只有一个 Codex skill
- 这个 skill 位于 repo root、`.agents/skills/<name>/` 或 `skills/<name>/`
- 可以使用 Python 3
- Codex CLI 已安装，并且可通过 `codex` 调用
- 你愿意对生成出来的 benchmark、guardrail 和 promotion behavior 负责并进行审查

如果你的 Codex 可执行文件不叫 `codex`，生成出来的 runner 也支持使用 `CODEX_BIN` 环境变量覆盖。

## Quick Start

从当前仓库运行这些脚本，对另一个目标 skill 仓库进行 bootstrap。

### 1. 先预览 scaffold

先做 dry-run，看看脚本准备写什么：

```bash
python3 scripts/bootstrap_repo.py \
  --repo /path/to/target-repo \
  --skill-path /path/to/target-repo/.agents/skills/my-skill \
  --draft-json /path/to/draft-bundle.json \
  --dry-run
```

如果目标仓库里可检测到的 skill 恰好只有一个，那么 `--skill-path` 可以省略。

### 2. 真正生成 scaffold

确认预览没问题后，去掉 `--dry-run` 再执行一次：

```bash
python3 scripts/bootstrap_repo.py \
  --repo /path/to/target-repo \
  --skill-path /path/to/target-repo/.agents/skills/my-skill \
  --draft-json /path/to/draft-bundle.json
```

如果还没有 draft bundle，也可以先用 fallback generator 启动：

```bash
python3 scripts/bootstrap_repo.py \
  --repo /path/to/target-repo \
  --skill-path /path/to/target-repo/.agents/skills/my-skill
```

fallback mode 很适合先跑起来，但它仍然只是草稿。在真正相信那些分数之前，请先审阅生成出的 benchmark 和 rubric。

### 3. 立即验证

```bash
python3 scripts/validate_scaffold.py /path/to/target-repo
```

如果需要 machine-readable 输出：

```bash
python3 scripts/validate_scaffold.py /path/to/target-repo --json
```

### 4. 跑第一轮 iteration

完成 bootstrap 和 validation 后，切到目标仓库里执行：

```bash
python3 autoresearch/run_autoresearch.py --mode manual
```

如果你想用 Codex 自动化或其他 scheduler 来驱动这个循环，请使用 `python3 autoresearch/run_autoresearch.py --mode scheduled`。scheduled 运行和 manual 运行共用同一套 promotion gate，所以胜出的 candidate 仍然可能更新 live skill。

## Codex 自动化支持

这个仓库支持一条在 bootstrap 和 validation 之后使用的、对 Codex 自动化友好的路径，但它不会自行安装或修改自动化文件。

- 把 `python3 autoresearch/run_autoresearch.py --mode scheduled` 视为官方的 Codex 自动化入口。
- 只有在你真的需要定期运行时，才让 Codex 帮你创建自动化。
- 推荐的自动化名称是 `Autoresearch Loop`。
- 自动化 prompt 最好只做下面这件事：
  运行 `python3 autoresearch/run_autoresearch.py --mode scheduled`，然后检查 `autoresearch/leaderboard.json` 和最新的 `autoresearch/runs/<RUN_ID>/final.json`，把 baseline score、winning candidate、是否发生 promotion、regressions，以及需要人工审查的风险汇总到 inbox 中。
- 自动化的工作范围应固定为目标仓库本身，不要扩散到其他目录。

在 v1 中，Codex 桌面端自动化是首要支持对象。外部 scheduler 仍然可以使用，但属于次要路径，并且也应调用同一个 scheduled 入口。

如果你打算依赖基于 git worktree 的自动化，请先确保目标仓库至少已经有一个 commit。生成出来的 runner 也会把这件事记到 note 里，因为有些自动化环境需要已有的 `HEAD`。

## Draft Bundle

如果你想从更高质量的起点出发，可以在 bootstrap 前准备一个 draft bundle JSON。准确格式写在 [references/draft_bundle.md](references/draft_bundle.md)。

bundle 包括：

- `program_summary`
  用一句话说明“更好的行为”是什么样子
- `mutation_guardrails`
  约束改动保持小、可回退、且不跑题
- `evaluation_rubric`
  evaluator 的评分说明
- `cases`
  定义 positive、negative、safety 行为的 benchmark 行

关键规则：

- 必须正好 18 个 case
- 分布固定为 8 个 `positive`、6 个 `negative`、4 个 `safety`
- `case_id` 必须唯一
- `weight` 必须是正数
- `expected_behavior` 应写成行为目标，而不是隐藏答案

如果目标 skill 边界很锋利、失败代价很高，或者你希望 benchmark 文案在生成前先经过人工审查，就更适合显式提供 draft bundle。

## Guardrails and Limitations

这个项目是有意收紧约束的：

- v1 只支持每个 repo 一个 target skill
- benchmark case、hook、config 和 promotion rule 在 bootstrap 后仍由人类负责
- mutation 仅限目标 skill 或生成出来的 candidate 目录
- evaluation run 是 read-only，并且必须返回 structured JSON
- bootstrap 不会自动启动 iterative research
- 如果 skill 位于 repository root，promote 时会保留 `.git`、`.codex`、`autoresearch` 和 `AGENTS.md`

它不是要做一个无限自动运转的优化机器。它要做的是一个在周二下午你也敢放心运行的、讲纪律的迭代循环。

## Repository Layout

```text
.
|-- SKILL.md
|-- README.md
|-- agents/
|   `-- openai.yaml
|-- assets/
|   `-- templates/
|       |-- AGENTS.md.tmpl
|       |-- .codex/...
|       `-- autoresearch/...
|-- references/
|   `-- draft_bundle.md
`-- scripts/
    |-- bootstrap_repo.py
    |-- validate_scaffold.py
    `-- smoke_test_bootstrap.py
```

## Development and Verification

如果你修改的是这个仓库本身，发布前建议运行 smoke test：

```bash
python3 scripts/smoke_test_bootstrap.py
```

如果你想更深入检查某个已经 bootstrap 的仓库：

```bash
python3 scripts/validate_scaffold.py /path/to/target-repo --json
```

## 一个小小的命名说明

这份 README 使用对外名称 `karpathyloop_skill`。在仓库内部命名完全跟上之前，你仍然可能在 metadata、marker 或 generated section 中看到 `bootstrap-skill-autoresearch` 之类的内部标识。不过，这里记录的工作流和命令都与当前实现一致。

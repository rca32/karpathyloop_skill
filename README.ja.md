# karpathyloop_skill

`karpathyloop_skill` は、Karpathy スタイルの autoresearch loop を Codex skill 向けに持ち込んだプロジェクトです。

[karpathy/autoresearch](https://github.com/karpathy/autoresearch) が「エージェントが小さな実運用レベルの学習セットアップを一晩中回しながら改善したら何が起こるか？」を問うなら、このリポジトリはその隣で「改善対象が Codex skill そのものだったらどうなるか？」を問います。

ここでの答えは「ブレーキなしの完全自律」ではありません。もっと引き締まったループです。対象は 1 つの skill、評価は人が読める benchmark、境界は review できる guardrail、そして本当に良くなったときだけ通す promotion rule です。

## Language

- [English](README.md)
- [한국어](README.ko.md)
- [日本語](README.ja.md)
- [简体中文](README.zh-CN.md)

## Karpathy Loop とは？

2026年3月、Andrej Karpathy は [`autoresearch`](https://github.com/karpathy/autoresearch) を公開しました。これは agent-driven research を小さく鋭く試す実験です。核となる考え方はとてもシンプルです。

- 変更可能な面積を小さく保つ
- 評価を安く、繰り返し可能にする
- 雰囲気ではなく baseline と比較する
- エージェントには反復させるが、境界は明確にする

このリポジトリは、その考え方に着想を得ています。公式の Karpathy プロジェクトではなく、彼の学習スタックをそのまま含んでいるわけでもありません。代わりに、同じ運用スタイルを Codex skill の改善ワークフローへ翻訳しています。

つまり、ここではエージェントが `train.py` を編集する代わりに、1 つの `SKILL.md` を改善します。モデル指標の代わりに、benchmark case、false trigger、safety check が評価軸になります。リズムは似ていて、戦場が違います。

## このリポジトリがすること

Codex skill をちょうど 1 つ含むリポジトリを bootstrap スクリプトに渡すと、制御された改善ループに必要な部品を生成します。

- `AGENTS.md` guardrail
- benchmark case と evaluation rubric
- evaluator、mutator、failure-miner agent 定義
- Codex hook と config wiring
- 再利用可能な `autoresearch/run_autoresearch.py` runner
- run artifact、candidate workspace、leaderboard

狙いは、skill 改善のまわりにある面倒なセットアップを消すことです。harness の組み立て直しではなく、benchmark と skill そのものの改善に時間を使えるようにします。

## なぜこの形が skill に向いているのか

Skill の改善は、退屈なくらい同じパターンで崩れがちです。

- prompt だけ長くなって中身は良くならない
- 評価が一貫せず、誰もスコアを信じない
- 変更が意図した範囲の外へ流れていく
- safety の扱いが後回しになり、最悪のタイミングで破綻する

`karpathyloop_skill` は、そうした崩れ方を減らすために設計されています。

- 小さな変更範囲: リポジトリ全体ではなく、対象は 1 つの skill
- 人間が持つポリシー: benchmark、rubric、hook、promotion logic は review 可能
- 安い比較: baseline vs. candidate `a` vs. candidate `b`
- 保守的な昇格: 平均点が少し良く見えても regression があれば通さない

## このループの流れ

生成されるワークフローは、意図的に狭く、繰り返しやすい形になっています。

1. 対象 skill を見つける
   bootstrap は repo root、`.agents/skills/*`、`skills/*` からちょうど 1 つの skill を探します。複数ある場合は `--skill-path` が必要です。
2. benchmark bundle を作る
   draft JSON bundle を渡すことも、`SKILL.md` から荒い初期案を作ることもできます。
3. リポジトリを scaffold する
   スクリプトが benchmark asset、hook、agent 定義、config、再利用可能 runner を書き込みます。
4. すぐ検証する
   validator がファイルの存在、benchmark shape、hook wiring、config profile、生成された runner contract を確認します。
5. iteration を走らせる
   生成された runner が baseline と 2 つの candidate を評価し、結果を `autoresearch/runs/<RUN_ID>/` に記録します。
6. 条件を満たしたときだけ promote する
   weighted mean score の改善、negative-case regression の回避、safety regression の回避、そして過剰な `SKILL.md` 増加の正当化が必要です。

### 現在の Run Model

- 2 つの candidate が `autoresearch/candidates/<RUN_ID>/a` と `.../b` に作られます。
- mutation は許可された candidate path または対象 skill path に限定されます。
- evaluation は read-only で、structured JSON を返さなければなりません。
- 各 candidate は 1 つの仮説を説明する `HYPOTHESIS.md` を残す必要があります。

### 現在の Promotion Rule

現在の実装では、candidate が promote されるには次の条件をすべて満たす必要があります。

- weighted mean score が少なくとも `0.03` 改善する
- negative-case false trigger が増えない
- safety regression が `0` のままである
- `SKILL.md` が `15%` を超えて増える場合、スコア改善は少なくとも `0.05` 必要

この gate は意図的に厳しめです。活動量を評価するのではなく、信頼できる改善だけを通すためです。

## 生成されるもの

bootstrap を実行すると、対象リポジトリに autoresearch の中核となるファイル群が書き込まれるか、既存内容とマージされます。

- `AGENTS.md`
  どこが human-owned で、どこが run 中に mutable なのかを定義する repository-level guardrail
- `autoresearch/program.md`
  対象 skill の program summary と mutation guidance
- `autoresearch/bench/cases.csv`
  ちょうど 18 行の benchmark case 一覧。内訳は 8 個の `positive`、6 個の `negative`、4 個の `safety`
- `autoresearch/bench/evaluation_rubric.md`
  evaluator が振る舞いを採点するためのガイド
- `autoresearch/bench/final_schema.json`
  run の最終 JSON shape
- `autoresearch/root_prompt.txt`
  runner が使う実行プロンプト
- `autoresearch/run_autoresearch.py`
  baseline-plus-two-candidates ループを回す再利用可能 runner
- `autoresearch/runs/<RUN_ID>/`
  baseline 評価、candidate 評価、mutation 出力、最終結果
- `autoresearch/candidates/<RUN_ID>/`
  mutation 中に編集される candidate のコピー
- `autoresearch/leaderboard.json`
  run 履歴と最良 promoted score
- `.codex/config.toml`
  管理された Codex profile と agent 設定
- `.codex/hooks.json` と `.codex/hooks/`
  context 読み込みと eval JSON 強制のための hook wiring と helper script
- `.codex/agents/`
  evaluator、mutator、failure-miner agent 定義

既存の `AGENTS.md`、`.codex/config.toml`、`.codex/hooks.json` は、できる限り丸ごと置き換えずにマージされます。

## Prerequisites

使い始める前に、次の条件を確認してください。

- 対象リポジトリに Codex skill がちょうど 1 つある
- その skill は repo root、`.agents/skills/<name>/`、`skills/<name>/` のいずれかにある
- Python 3 が使える
- Codex CLI が `codex` として実行できる
- 生成される benchmark、guardrail、promotion behavior を自分たちで review して運用するつもりがある

Codex 実行ファイル名が `codex` でない場合、生成された runner は `CODEX_BIN` 環境変数による override もサポートします。

## Quick Start

このリポジトリのスクリプトを、別の対象 skill リポジトリに対して実行します。

### 1. Scaffold をプレビューする

まずは dry-run で、どんな書き込みが行われるかを確認します。

```bash
python3 scripts/bootstrap_repo.py \
  --repo /path/to/target-repo \
  --skill-path /path/to/target-repo/.agents/skills/my-skill \
  --draft-json /path/to/draft-bundle.json \
  --dry-run
```

対象リポジトリに検出可能な skill がちょうど 1 つなら、`--skill-path` は省略可能です。

### 2. Scaffold を実際に生成する

プレビュー結果が問題なければ、`--dry-run` を外して同じコマンドを実行します。

```bash
python3 scripts/bootstrap_repo.py \
  --repo /path/to/target-repo \
  --skill-path /path/to/target-repo/.agents/skills/my-skill \
  --draft-json /path/to/draft-bundle.json
```

まだ draft bundle がない場合は、fallback generator でも始められます。

```bash
python3 scripts/bootstrap_repo.py \
  --repo /path/to/target-repo \
  --skill-path /path/to/target-repo/.agents/skills/my-skill
```

fallback mode は素早く始めるには便利ですが、あくまで初稿です。数値を信じる前に、生成された benchmark と rubric を見直してください。

### 3. すぐ検証する

```bash
python3 scripts/validate_scaffold.py /path/to/target-repo
```

machine-readable な出力が必要なら:

```bash
python3 scripts/validate_scaffold.py /path/to/target-repo --json
```

### 4. 最初の iteration を走らせる

bootstrap と validation の後、対象リポジトリに移動して次を実行します。

```bash
python3 autoresearch/run_autoresearch.py --mode manual
```

生成された runner は外部 orchestrator 向けの `--mode scheduled` も受け付けますが、このリポジトリ自体が scheduler をセットアップするわけではありません。

## Draft Bundle

より良い出発点が欲しいなら、bootstrap 前に draft bundle JSON を用意してください。正確な shape は [references/draft_bundle.md](references/draft_bundle.md) にあります。

bundle には次が含まれます。

- `program_summary`
  より良い振る舞いが何かを説明する 1 文
- `mutation_guardrails`
  変更を小さく、可逆で、主題から外れないように保つ制約
- `evaluation_rubric`
  evaluator が採点に使う指針
- `cases`
  positive、negative、safety の振る舞いを定義する benchmark 行

重要なルール:

- case はちょうど 18 件
- 内訳は 8 個の `positive`、6 個の `negative`、4 個の `safety`
- `case_id` はすべて一意
- `weight` は正の数値
- 期待動作は隠れた正答ではなく、行動目標として書く

skill の境界が鋭い場合、失敗コストが高い場合、あるいは benchmark の文言を事前に人間が review したい場合は、明示的な draft bundle の利用をおすすめします。

## Guardrails and Limitations

このプロジェクトは意図的に制約されています。

- v1 では repo ごとに 1 つの target skill のみサポート
- benchmark case、hook、config、promotion rule は bootstrap 後も人間が所有
- mutation は target skill または生成された candidate directory に限定
- evaluation run は read-only で、structured JSON を返す必要がある
- bootstrap は iterative research を自動開始しない
- skill が repository root にある場合、promotion 時に `.git`、`.codex`、`autoresearch`、`AGENTS.md` を保持

目指しているのは、無限に回る完全自律 optimizer ではありません。火曜の午後でも安心して回せる、規律あるループです。

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

このリポジトリ自体を変更した場合は、公開前に smoke test を実行してください。

```bash
python3 scripts/smoke_test_bootstrap.py
```

特定の bootstrapped repository をより深く確認するには:

```bash
python3 scripts/validate_scaffold.py /path/to/target-repo --json
```

## 名前についての小さなメモ

この README では公開向けの名前として `karpathyloop_skill` を使っています。リポジトリ内の命名が完全に追いつくまでは、metadata、marker、generated section の中に `bootstrap-skill-autoresearch` のような内部識別子が残る場合があります。ただし、ここに書かれているワークフローとコマンドは現在の実装に一致しています。

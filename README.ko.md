# karpathyloop_skill

`karpathyloop_skill`은 Karpathy 스타일의 autoresearch loop를 Codex skill 세계로 옮겨온 프로젝트입니다.

[karpathy/autoresearch](https://github.com/karpathy/autoresearch)가 "에이전트가 작은 실제 학습 셋업을 밤새 돌면서 반복 개선하면 무슨 일이 벌어질까?"를 묻는다면, 이 저장소는 그 옆에서 이렇게 묻습니다. "개선 대상이 Codex skill 자체라면 어떻게 될까?"

여기서의 답은 "브레이크 없는 완전 자율"이 아닙니다. 더 타이트한 루프입니다. 한 개의 대상 skill, 사람이 직접 읽을 수 있는 benchmark, 리뷰 가능한 guardrail, 그리고 진짜 개선일 때만 통과시키는 promotion rule이 핵심입니다.

## Language

- [English](README.md)
- [한국어](README.ko.md)
- [日本語](README.ja.md)
- [简体中文](README.zh-CN.md)

## Karpathy Loop란?

2026년 3월, Andrej Karpathy는 [`autoresearch`](https://github.com/karpathy/autoresearch)라는 작고 날렵한 agent-driven research 실험을 공개했습니다. 핵심 아이디어는 단순합니다.

- 수정 가능한 표면적을 작게 유지한다.
- 평가를 싸고 반복 가능하게 만든다.
- 감(“vibes”)이 아니라 baseline과 비교한다.
- 에이전트는 반복하게 하되, 경계는 분명히 둔다.

이 저장소는 그 아이디어에서 영감을 받았습니다. 공식 Karpathy 프로젝트는 아니며, 그의 학습 스택을 그대로 포함하지도 않습니다. 대신 같은 운영 감각을 Codex skill 개선 워크플로우로 번역합니다.

그래서 여기서는 에이전트가 `train.py`를 고치는 대신 하나의 `SKILL.md`를 개선합니다. 모델 지표 대신 benchmark case, false trigger, safety check가 평가 기준이 됩니다. 리듬은 비슷하고, 전장은 다릅니다.

## 이 저장소가 하는 일

정확히 하나의 Codex skill을 가진 저장소를 bootstrap 스크립트에 넘기면, 제어 가능한 개선 루프에 필요한 구성 요소를 만들어 줍니다.

- `AGENTS.md` guardrail
- benchmark case와 evaluation rubric
- evaluator, mutator, failure-miner agent 정의
- Codex hook과 config wiring
- 재사용 가능한 `autoresearch/run_autoresearch.py` 러너
- Codex 자동화에 바로 연결할 수 있는 `--mode scheduled` 엔트리포인트
- run artifact, candidate workspace, leaderboard

핵심은 skill 개선 주변의 귀찮은 셋업 작업을 없애는 것입니다. 시간을 harness 재조립에 쓰지 말고, benchmark와 skill 자체를 더 좋게 만드는 데 쓰도록 돕습니다.

## 왜 이런 구조가 skill에 잘 맞는가

Skill 개선은 꽤 자주 비슷한 방식으로 엇나갑니다.

- 프롬프트만 길어지고 실제로는 더 좋아지지 않는다.
- 평가가 일관되지 않아 점수를 믿기 어렵다.
- 수정 범위가 원래 의도보다 넓게 흘러간다.
- safety 동작은 나중으로 미뤄졌다가 가장 안 좋은 순간에 터진다.

`karpathyloop_skill`은 이런 문제를 줄이기 위해 설계되었습니다.

- 작은 수정 범위: 저장소 전체가 아니라 skill 하나만 다룹니다.
- 사람이 소유하는 정책: benchmark, rubric, hook, promotion logic은 사람이 검토합니다.
- 싼 비교: baseline 대 candidate `a` 대 candidate `b`.
- 보수적인 승격: 평균 점수가 조금 좋아 보여도 regression이 있으면 통과시키지 않습니다.

## 여기서 루프는 어떻게 동작하나

생성되는 워크플로우는 의도적으로 좁고 반복 가능하게 설계되어 있습니다.

1. 대상 skill을 찾습니다.
   bootstrap 단계는 repo root, `.agents/skills/*`, `skills/*`에서 정확히 하나의 skill을 찾습니다. 둘 이상이면 `--skill-path`를 지정해야 합니다.
2. benchmark bundle을 만듭니다.
   draft JSON bundle을 직접 제공할 수도 있고, `SKILL.md`에서 거친 초안을 자동 생성할 수도 있습니다.
3. 저장소를 scaffold 합니다.
   스크립트가 benchmark asset, hook, agent 정의, config, reusable runner를 씁니다.
4. 바로 검증합니다.
   validator가 파일 존재 여부, benchmark shape, hook wiring, config profile, 생성된 runner 계약을 확인합니다.
5. iteration을 실행합니다.
   생성된 runner가 baseline과 두 candidate를 평가하고 결과를 `autoresearch/runs/<RUN_ID>/` 아래에 기록합니다.
6. 자격이 있을 때만 promote 합니다.
   weighted mean score가 올라가고, negative-case regression이 없고, safety regression이 없고, 과도한 `SKILL.md` 증가도 정당화해야 합니다.

### 현재 Run Model

- 두 candidate는 `autoresearch/candidates/<RUN_ID>/a` 와 `.../b` 아래에 생성됩니다.
- mutation은 승인된 candidate 경로나 대상 skill 경로 안에서만 허용됩니다.
- evaluation은 read-only이며 structured JSON을 반환해야 합니다.
- 각 candidate는 하나의 가설을 설명하는 `HYPOTHESIS.md`를 남겨야 합니다.

### 현재 Promotion Rule

현재 구현 기준으로 candidate가 promote 되려면 아래 조건을 모두 만족해야 합니다.

- weighted mean score가 최소 `0.03` 이상 개선될 것
- negative-case false trigger가 증가하지 않을 것
- safety regression이 `0`일 것
- `SKILL.md`가 `15%`를 넘게 커졌다면 점수 향상이 최소 `0.05`일 것

이 문턱값은 의도적으로 보수적입니다. 목적은 활동량을 보상하는 것이 아니라, 신뢰할 수 있는 개선만 통과시키는 것입니다.

## 생성되는 것들

bootstrap을 실행하면 대상 저장소에 autoresearch 표면을 이루는 핵심 파일들이 생성되거나 병합됩니다.

- `AGENTS.md`
  어떤 파일이 human-owned이고 어떤 범위가 mutable인지 정의하는 저장소 수준의 guardrail입니다.
- `autoresearch/program.md`
  대상 skill에 대한 program summary와 mutation guidance를 담습니다.
- `autoresearch/bench/cases.csv`
  정확히 18개 행으로 이루어진 benchmark case 목록입니다. 구성은 8개의 `positive`, 6개의 `negative`, 4개의 `safety`입니다.
- `autoresearch/bench/evaluation_rubric.md`
  evaluator가 동작을 채점할 때 사용하는 가이드입니다.
- `autoresearch/bench/final_schema.json`
  run이 반환해야 하는 최종 JSON shape입니다.
- `autoresearch/root_prompt.txt`
  runner가 사용하는 실행 프롬프트입니다.
- `autoresearch/run_autoresearch.py`
  baseline-plus-two-candidates 루프를 수행하는 재사용 가능한 runner입니다.
- `autoresearch/runs/<RUN_ID>/`
  baseline 평가, candidate 평가, mutation 출력, 최종 결과가 저장됩니다.
- `autoresearch/candidates/<RUN_ID>/`
  mutation 중 수정되는 candidate 복사본이 저장됩니다.
- `autoresearch/leaderboard.json`
  run 기록과 최고 promoted score를 저장합니다.
- `.codex/config.toml`
  관리되는 Codex profile과 agent 설정이 추가됩니다.
- `.codex/hooks.json` 와 `.codex/hooks/`
  context 로딩과 eval JSON 강제를 위한 hook wiring 및 helper script가 추가됩니다.
- `.codex/agents/`
  evaluator, mutator, failure-miner agent 정의가 추가됩니다.

기존의 `AGENTS.md`, `.codex/config.toml`, `.codex/hooks.json`은 가능하면 통째로 덮어쓰지 않고 병합합니다.

## Prerequisites

사용 전에 다음 조건을 확인하세요.

- 대상 저장소에 정확히 하나의 Codex skill이 있어야 합니다.
- 그 skill은 repo root, `.agents/skills/<name>/`, `skills/<name>/` 중 하나에 있어야 합니다.
- Python 3를 사용할 수 있어야 합니다.
- Codex CLI가 `codex` 이름으로 실행 가능해야 합니다.
- 생성된 benchmark, guardrail, promotion behavior를 직접 검토하고 소유할 준비가 되어 있어야 합니다.

Codex 실행 파일 이름이 `codex`가 아니라면, 생성된 runner는 `CODEX_BIN` 환경 변수 override도 지원합니다.

## Quick Start

이 저장소의 스크립트를 별도의 대상 skill 저장소에 대해 실행하세요.

### 1. Scaffold 미리보기

먼저 dry-run으로 어떤 파일이 써질지 확인합니다.

```bash
python3 scripts/bootstrap_repo.py \
  --repo /path/to/target-repo \
  --skill-path /path/to/target-repo/.agents/skills/my-skill \
  --draft-json /path/to/draft-bundle.json \
  --dry-run
```

대상 저장소에서 감지 가능한 skill이 정확히 하나라면 `--skill-path`는 선택 사항입니다.

### 2. Scaffold 실제 생성

미리보기 결과가 괜찮다면 `--dry-run` 없이 다시 실행합니다.

```bash
python3 scripts/bootstrap_repo.py \
  --repo /path/to/target-repo \
  --skill-path /path/to/target-repo/.agents/skills/my-skill \
  --draft-json /path/to/draft-bundle.json
```

아직 draft bundle이 없다면 fallback generator로도 시작할 수 있습니다.

```bash
python3 scripts/bootstrap_repo.py \
  --repo /path/to/target-repo \
  --skill-path /path/to/target-repo/.agents/skills/my-skill
```

fallback mode는 빠르게 출발하기엔 좋지만, 여전히 초안입니다. 숫자를 믿기 전에 생성된 benchmark와 rubric을 꼭 검토하세요.

### 3. 즉시 검증

```bash
python3 scripts/validate_scaffold.py /path/to/target-repo
```

machine-readable 출력이 필요하다면:

```bash
python3 scripts/validate_scaffold.py /path/to/target-repo --json
```

### 4. 첫 iteration 실행

bootstrap과 validation 이후 대상 저장소로 이동해서 다음을 실행합니다.

```bash
python3 autoresearch/run_autoresearch.py --mode manual
```

Codex 자동화나 다른 스케줄러로 루프를 돌리고 싶다면 `python3 autoresearch/run_autoresearch.py --mode scheduled`를 사용하세요. scheduled 실행도 manual 실행과 동일한 promotion gate를 사용하므로, 우승 candidate가 실제 live skill을 갱신할 수 있습니다.

## Codex 자동화 지원

이 저장소는 bootstrap과 validation 이후 사용할 수 있는 Codex 자동화 친화 경로를 지원하지만, 자동화 파일을 직접 설치하거나 수정하지는 않습니다.

- `python3 autoresearch/run_autoresearch.py --mode scheduled`를 공식 Codex 자동화 엔트리포인트로 취급하세요.
- 실제로 주기 실행이 필요할 때만 Codex에 자동화 생성을 요청하세요.
- 권장 자동화 이름은 `Autoresearch Loop`입니다.
- 자동화 프롬프트는 다음 작업만 하도록 두는 것이 좋습니다.
  `python3 autoresearch/run_autoresearch.py --mode scheduled`를 실행하고, `autoresearch/leaderboard.json`과 최신 `autoresearch/runs/<RUN_ID>/final.json`을 확인한 뒤, baseline score, winning candidate, promotion 여부, regressions, 사람 검토가 필요한 위험 요소를 inbox에 요약합니다.
- 자동화의 작업 범위는 대상 저장소 하나로만 고정하세요.

v1에서는 Codex 데스크톱 자동화를 1순위 대상으로 봅니다. 외부 스케줄러도 사용할 수 있지만, 보조 경로로 간주하고 같은 scheduled 엔트리포인트를 호출해야 합니다.

git worktree 기반 자동화에 의존할 계획이라면, 대상 저장소에 최소 1개의 커밋이 이미 있어야 합니다. 생성된 runner도 일부 자동화 환경이 기존 `HEAD`를 요구한다는 점을 note로 남깁니다.

## Draft Bundle

더 나은 출발점을 원한다면 bootstrap 전에 draft bundle JSON 파일을 준비하세요. 정확한 형식은 [references/draft_bundle.md](references/draft_bundle.md)에 문서화되어 있습니다.

bundle에는 다음이 포함됩니다.

- `program_summary`
  더 나은 동작이 어떤 모습인지 설명하는 한 문장
- `mutation_guardrails`
  수정 범위를 작고 되돌릴 수 있으며 주제에 맞게 유지하는 제약
- `evaluation_rubric`
  evaluator가 점수를 매길 때 따르는 기준
- `cases`
  positive, negative, safety 동작을 정의하는 benchmark 행

중요한 규칙은 다음과 같습니다.

- case는 정확히 18개
- 분포는 8개의 `positive`, 6개의 `negative`, 4개의 `safety`로 고정
- `case_id`는 모두 고유해야 함
- `weight`는 양수 숫자여야 함
- 기대 동작은 숨겨진 정답이 아니라 행동 기준으로 써야 함

skill의 경계가 날카롭거나, 실패 비용이 크거나, benchmark 문구를 사람이 먼저 검토해야 한다면 명시적인 draft bundle을 쓰는 편이 좋습니다.

## Guardrails and Limitations

이 프로젝트는 의도적으로 제약을 둡니다.

- v1에서는 repo당 하나의 target skill만 지원합니다.
- benchmark case, hook, config, promotion rule은 bootstrap 이후 사람이 소유합니다.
- mutation은 대상 skill 또는 생성된 candidate 디렉터리로 제한됩니다.
- evaluation run은 read-only이며 structured JSON을 반환해야 합니다.
- bootstrap은 iterative research를 자동으로 시작하지 않습니다.
- skill이 repository root에 있다면 promotion 시 `.git`, `.codex`, `autoresearch`, `AGENTS.md`를 보존합니다.

이 프로젝트는 끝없이 돌아가는 완전 자율 최적화기를 목표로 하지 않습니다. 화요일 오후에도 믿고 돌릴 수 있는, 규율 있는 루프를 만드는 것이 목표입니다.

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

이 저장소 자체를 수정했다면, 공개 전에 smoke test를 돌려보세요.

```bash
python3 scripts/smoke_test_bootstrap.py
```

특정 bootstrap 결과를 더 깊게 점검하려면:

```bash
python3 scripts/validate_scaffold.py /path/to/target-repo --json
```

## 이름에 대한 짧은 메모

이 README는 대외 이름으로 `karpathyloop_skill`을 사용합니다. 저장소 이름 정리가 완전히 끝나기 전까지는 metadata, marker, generated section 안에 `bootstrap-skill-autoresearch` 같은 내부 식별자가 남아 있을 수 있습니다. 하지만 여기 문서에 적힌 워크플로우와 명령어는 현재 구현과 일치합니다.

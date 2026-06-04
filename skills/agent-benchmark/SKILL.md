---
name: agent-benchmark
description: Run agent tasks across multiple LLMs in parallel tmux sessions, score results with a weighted rubric, track improvements over time in JSONL, and generate harness improvement recommendations. Use when comparing model performance, evaluating harness changes, or identifying agent failure patterns at scale.
---

# Agent Benchmark Skill

Benchmark agent tasks across multiple LLMs in parallel, score results, and track improvements over time.

## When to Use This Skill

- Compare which LLM performs best on a specific task or workflow
- Measure whether a harness change (prompt, tool, middleware) improved or regressed performance
- Identify recurring failure modes across models to prioritize fixes
- Generate eval candidates from real task failures
- Build a dataset of model performance over time for trend analysis

## Quick Start

```bash
# Use default models from config
/skill:agent-benchmark "Fix the login redirect bug in auth.ts"

# Test specific models
/skill:agent-benchmark --models gpt-4o,claude-sonnet-4 "Refactor user service"

# Tag a harness change so you can compare before/after
/skill:agent-benchmark --models gpt-4o,claude-sonnet-4 --tag "loop-detection-v1" "Add tests for auth module"

# Full options
/skill:agent-benchmark \
  --models gpt-4o,claude-sonnet-4,gemini-2.5-pro \
  --tag "v2.3-middleware-update" \
  --output-dir ./benchmarks/june-sprint \
  --judge-model gpt-4o \
  --timeout 300 \
  "Explore this codebase and document the architecture"
```

## Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--models` | Comma-separated list of models to test | `config.default_models` |
| `--tag` | Label for this harness version (git SHA, feature name, etc.) | ISO timestamp |
| `--output-dir` | Directory for results and reports | `~/.pi/agent/benchmarks/` |
| `--judge-model` | Model used for LLM-as-judge grading | `gpt-4o` |
| `--timeout` | Max seconds per model run | `300` |
| `--task-file` | Read task from file instead of inline arg | (none) |
| `--no-grade` | Skip grading, just run and log traces | `false` |
| `--compare-n` | Compare against last N runs with same task pattern | `5` |

## How It Works

### Phase 1: Setup

1. Parse arguments. If `--models` not provided, read `config/default.json`.
2. Validate each model exists in `config.providers`. Error if unknown.
3. Generate a unique run ID: `{timestamp}-{short-git-sha}-{slugified-task}`
4. Create output directory: `{output-dir}/{run-id}/`

### Phase 2: Spawn Parallel Sessions

For each model, spawn a detached tmux session:

```bash
# Example for gpt-4o
tmux new-session -d -s "bench-{run-id}-gpt-4o" \
  "cd {cwd} && pi --model gpt-4o --no-interactive {task} > {output-dir}/{run-id}/trace-gpt-4o.md 2>&1; echo $? > {output-dir}/{run-id}/exit-gpt-4o.txt"
```

Session naming: `bench-{run-id}-{model-slug}`

Wait for all sessions to complete or hit `--timeout`.

### Phase 3: Collect Results

For each model, collect:
- `trace-{model}.md` — full session output
- `exit-{model}.txt` — exit code
- `metadata-{model}.json` — turns, tool calls, duration (parsed from trace)

If a session timed out, mark as `status: "timeout"`.

### Phase 4: Grade Results

For each completed trace, compute scores across 4 dimensions:

| Dimension | Weight | How Scored |
|-----------|--------|-----------|
| **Correctness** | 40% | LLM-as-judge: "Did the agent fully solve the task?" + assertion checks |
| **Efficiency** | 25% | Turns vs ideal trajectory, token burn, parallelization |
| **Tool Use** | 20% | Right tools selected, no redundant calls, no loops, parallelized where possible |
| **Verification** | 15% | Self-tested, read output, compared against spec, didn't stop at "looks good" |

**Overall** = weighted average.

Grading prompts are in `references/scoring-rubric.md`.

### Phase 5: Log to JSONL

Append to `{output-dir}/results.jsonl`:

```json
{
  "run_id": "20260604-153022-a1b2c3d-fix-login-bug",
  "timestamp": "2026-06-04T15:30:22Z",
  "task": "Fix the login redirect bug in auth.ts",
  "task_slug": "fix-login-bug",
  "git_sha": "a1b2c3d",
  "tag": "loop-detection-v1",
  "cwd": "/Users/alejandro/project",
  "models_tested": ["gpt-4o", "claude-sonnet-4"],
  "results": [
    {
      "model": "gpt-4o",
      "provider": "openai",
      "status": "completed",
      "scores": {
        "correctness": 1.0,
        "efficiency": 0.8,
        "tool_use": 0.9,
        "verification": 0.5,
        "overall": 0.83
      },
      "metrics": {
        "turns": 12,
        "tool_calls": 8,
        "duration_ms": 45000,
        "parallelized_calls": 2
      },
      "trace_path": ".../trace-gpt-4o.md",
      "failure_modes": ["skipped_tests", "no_edge_case_check"],
      "intervention_points": 2
    }
  ],
  "winner": "claude-sonnet-4",
  "winner_score": 0.93,
  "recommendations": [
    {
      "priority": "critical",
      "category": "verification",
      "issue": "gpt-4o skipped running tests before declaring success",
      "affected_models": ["gpt-4o"],
      "suggested_fix": "Add PreCompletionChecklistMiddleware enforcing test execution",
      "eval_candidate": "agent_runs_tests_before_submit"
    }
  ]
}
```

### Phase 6: Compare & Trend

Read last `--compare-n` runs with matching `task_slug` or `tag` prefix.

Show:
- Score delta per model vs previous run
- Trend line per model over last N runs
- Regression alerts (score drop > 0.10)

### Phase 7: Generate Report

Write `{output-dir}/{run-id}/report.md`:

```markdown
# Benchmark Report: fix-login-bug

## Run Metadata
- **Run ID:** 20260604-153022-a1b2c3d-fix-login-bug
- **Tag:** loop-detection-v1
- **Git SHA:** a1b2c3d
- **Task:** Fix the login redirect bug in auth.ts

## Results

| Model | Overall | Correctness | Efficiency | Tool Use | Verification | Turns | Duration |
|-------|---------|-------------|------------|----------|--------------|-------|----------|
| claude-sonnet-4 | **0.93** | 1.00 | 0.90 | 0.90 | 0.90 | 10 | 38s |
| gpt-4o | 0.83 | 1.00 | 0.80 | 0.90 | 0.50 | 12 | 45s |

## Trend (last 5 runs)

```
claude-sonnet-4: 0.91 → 0.91 → 0.92 → 0.92 → 0.93  ↑
gpt-4o:          0.88 → 0.85 → 0.84 → 0.83 → 0.83  ↓
```

## 🚨 Regressions
- **gpt-4o verification**: 0.80 → 0.50 (-0.30) since tag "pre-loop-fix"
  - Likely cause: test-running prompt removed in system prompt v3

## Recommendations

### Critical
1. **Re-add test verification prompt** — caused regression in gpt-4o
   - Affected: gpt-4o
   - Suggested fix: Add PreCompletionChecklistMiddleware
   - Eval: `agent_runs_tests_before_submit`

### Medium
2. **Add loop detection middleware** — gpt-4o edited auth.ts 4 times
   - Affected: gpt-4o
   - Suggested fix: LoopDetectionMiddleware after N edits to same file
   - Eval: `agent_recovers_from_edit_loop`

## Eval Candidates
- `agent_runs_tests_before_submit` — tag: verification
- `agent_recovers_from_edit_loop` — tag: tool_use
- `agent_parallelizes_independent_reads` — tag: efficiency

## Traces
- [gpt-4o](trace-gpt-4o.md)
- [claude-sonnet-4](trace-claude-sonnet-4.md)
```

### Phase 8: Cleanup

Kill tmux sessions: `tmux kill-session -t bench-{run-id}-*`

## Interpreting Results

### Winner Selection
Highest `overall` score wins. Ties broken by `correctness`, then `efficiency`.

### Regression Threshold
Score drop ≥ 0.10 vs previous run triggers regression alert.

### When to Act on Recommendations

| Priority | Criteria | Action |
|----------|----------|--------|
| **Critical** | Affects multiple models or caused ≥0.15 regression | Fix immediately |
| **Medium** | Affects one model, score impact 0.05-0.15 | Fix this week |
| **Low** | One model, minor impact, or model-specific quirk | Fix if recurring |

## Plotting Trends Over Time

Use the helper script to visualize:

```bash
python3 ~/.pi/agent/skills/agent-benchmark/scripts/plot-trends.py \
  --input ~/.pi/agent/benchmarks/results.jsonl \
  --task "fix-login-bug" \
  --output ~/trends.png
```

Or plot all tasks for a model:

```bash
python3 ~/.pi/agent/skills/agent-benchmark/scripts/plot-trends.py \
  --input ~/.pi/agent/benchmarks/results.jsonl \
  --model gpt-4o \
  --output ~/gpt-4o-trends.png
```

## Adding a New Model

Edit `config/default.json`:

```json
{
  "providers": {
    "my-new-model": {
      "provider": "openrouter",
      "env_key": "OPENROUTER_API_KEY",
      "base_url": "https://openrouter.ai/api/v1"
    }
  }
}
```

Then run: `/skill:agent-benchmark --models my-new-model "Your task"`

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Session timeout | Task too complex or model slow | Increase `--timeout` or simplify task |
| Model not found | Not in config.providers | Add to config or check model name |
| Tmux not installed | Missing dependency | `brew install tmux` or `apt install tmux` |
| Grading seems off | Judge model bias | Try `--judge-model claude-sonnet-4` for comparison |
| Empty trace | Agent crashed or refused | Check `exit-{model}.txt` for exit code |

## Files Reference

| File | Purpose |
|------|---------|
| `config/default.json` | Default models, providers, scoring weights |
| `references/scoring-rubric.md` | Detailed grading prompts per dimension |
| `references/eval-template.py` | pytest stub for generated evals |
| `scripts/plot-trends.py` | Matplotlib charts from JSONL |
| `assets/report-template.md` | Report markdown template |

---
name: agent-eval
description: Evaluate a single agent session trace against project-specific test cases. Auto-discovers eval criteria from the trace, stores them in the project's .agent-eval/ directory, and grades with deterministic checks + rubric-based LLM judgment. Use when analyzing any agent session, building domain-specific evals, or tracking scaffold improvement over time.
---

# Agent Eval Skill

Evaluate any agent session — coding, creative, research, video production, anything. The skill reads the trace, discovers what test cases make sense for that workflow, stores them in the project's `.agent-eval/` directory, and grades the session.

## When to Use This Skill

- Analyze a completed agent session export (trace file, JSONL, or markdown)
- Grade a live agent session after it finishes
- Build project-specific eval criteria that evolve with the workflow
- Check whether the agent invoked the correct skill when prompted
- Track scaffold improvement over time via logged scores
- Generate eval candidates and harness fix recommendations

## Quick Start

```bash
# Grade a session — auto-discover and save criteria in the project
/skill:agent-eval /path/to/session-export.md

# Grade with explicit project directory (where .agent-eval/ will be created)
/skill:agent-eval --project @repos/videos /path/to/session-export.md

# Grade and tag the harness version
/skill:agent-eval --tag "prompt-v2.1" /path/to/session-export.md

# Grade a live session (read from stdin)
cat session.md | /skill:agent-eval --stdin --project ~/my-project
```

## Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| (positional) | Path to session trace file | required unless `--stdin` |
| `--stdin` | Read trace from stdin instead of file | `false` |
| `--project` | Project directory where `.agent-eval/` lives | inferred from trace or cwd |
| `--tag` | Harness version label | git SHA or timestamp |
| `--task` | Task description (if not inferable from trace) | inferred from first user message |
| `--expected-skill` | Skill name the agent should have invoked | none |
| `--judge-model` | Model for LLM-as-judge grading | `gpt-4o` |
| `--output-dir` | Where to write report and log | `~/.pi/agent/evals/` |
| `--no-discover` | Skip auto-discovery, use existing criteria only | `false` |
| `--no-grade` | Skip LLM grading, run deterministic checks only | `false` |

## How It Works

### Phase 1: Ingest the Trace

Read the session trace. Supported formats:
- **Markdown** (`.md`) — pi session exports, conversation logs
- **JSONL** (`.jsonl`) — structured event streams
- **Plain text** — any readable transcript

Extract:
- Task description (first user message)
- Agent responses
- Tool calls and their arguments
- File changes
- Commands executed
- Skill invocations (detected via `/skill:name` or `$skill-name` patterns)
- **Domain signals** — what kind of workflow is this? (coding, video, research, etc.)

### Phase 2: Discover or Load Eval Criteria

This is the key innovation. The skill doesn't assume coding workflows.

#### If `.agent-eval/criteria.json` exists in the project:
Load it. Use those criteria.

#### If no criteria exist (first run):
The skill analyzes the trace and auto-generates appropriate test cases:

```
Analyzing trace...
Detected domain: video-production
Detected tools: file-read, file-write, bash(youtube-dl), bash(ffmpeg)
Detected skills: /skill:video-edit

Generating project-specific criteria...
```

The generated criteria are saved to `{project}/.agent-eval/criteria.json`.

#### Example: Video Production Criteria

```json
{
  "version": "2026-06-04",
  "project": "@repos/videos",
  "domain": "video-production",
  "generated_from": "session-2026-06-04.md",
  "criteria": [
    {
      "id": "skill-invocation",
      "name": "Skill Invocation",
      "check_type": "pattern",
      "pattern": "/skill:video-edit|\\$video-edit",
      "required": true
    },
    {
      "id": "downloaded-source",
      "name": "Downloaded Source Material",
      "check_type": "command_pattern",
      "patterns": ["youtube-dl", "yt-dlp", "wget", "curl -O"],
      "required": false
    },
    {
      "id": "checked-video-format",
      "name": "Checked Video Format",
      "check_type": "command_pattern",
      "patterns": ["ffprobe", "mediainfo", "file ", "ffmpeg -i"],
      "required": false
    },
    {
      "id": "created-output-file",
      "name": "Created Output File",
      "check_type": "file_exists",
      "required": false
    },
    {
      "id": "verified-output-quality",
      "name": "Verified Output Quality",
      "check_type": "llm_judge",
      "rubric": {
        "levels": [
          {
            "score": 1.0,
            "label": "Fully Verified",
            "criteria": "Agent checks output file exists, verifies format/codec, confirms duration, and previews result",
            "evidence_required": "Quote verification steps"
          },
          {
            "score": 0.50,
            "label": "Partially Verified",
            "criteria": "Agent checks output exists but doesn't verify quality or format",
            "evidence_required": "Quote what was checked and what was skipped"
          },
          {
            "score": 0.0,
            "label": "Not Verified",
            "criteria": "Agent declares success without checking output",
            "evidence_required": "Quote declaration without verification"
          }
        ]
      },
      "contributes_to_dimension": "verification",
      "dimension_weight": 0.60
    }
  ]
}
```

#### Example: Research / Writing Criteria

```json
{
  "domain": "research-writing",
  "criteria": [
    {
      "id": "skill-invocation",
      "check_type": "pattern",
      "pattern": "/skill:research|\\$research",
      "required": true
    },
    {
      "id": "gathered-sources",
      "name": "Gathered Sources",
      "check_type": "llm_judge",
      "rubric": {
        "levels": [
          {
            "score": 1.0,
            "label": "Thorough Research",
            "criteria": "Agent identifies and reads 3+ relevant sources, cites them explicitly",
            "evidence_required": "Quote source references and how they were used"
          },
          {
            "score": 0.50,
            "label": "Minimal Research",
            "criteria": "Agent mentions sources but doesn't deeply engage with them",
            "evidence_required": "Quote source mentions"
          },
          {
            "score": 0.0,
            "label": "No Research",
            "criteria": "Agent writes from prior knowledge without gathering new sources",
            "evidence_required": "Note absence of source gathering"
          }
        ]
      }
    },
    {
      "id": "structured-output",
      "name": "Structured Output",
      "check_type": "llm_judge",
      "rubric": {
        "levels": [
          {
            "score": 1.0,
            "label": "Well Structured",
            "criteria": "Output has clear sections, headings, logical flow, and summary",
            "evidence_required": "Describe structure"
          },
          {
            "score": 0.0,
            "label": "Unstructured",
            "criteria": "Output is a wall of text without organization",
            "evidence_required": "Note absence of structure"
          }
        ]
      }
    }
  ]
}
```

### Phase 3: Run Deterministic Checks

Fast, rule-based checks from the project's criteria:

| Check Type | How It Works | Example |
|-----------|--------------|---------|
| `pattern` | Regex match in trace | Did agent invoke `/skill:video-edit`? |
| `command_pattern` | Substring match in tool calls | Did agent run `ffmpeg`? |
| `response_pattern` | Substring match in responses | Did agent mention "edge case"? |
| `sequence` | Count repeated actions | Same file edited >3 times? |
| `parallelization` | Check batched calls | Parallel reads? |
| `file_exists` | Filesystem check | Output file created? |

### Phase 4: LLM-as-Judge Grading (Rubric-Based)

For semantic criteria, use structured rubric levels with evidence requirements.

**Why rubric-based?** Raw LLM scores hallucinate. Rubric-based scoring forces:
1. Match evidence to explicit level definitions
2. Quote specific evidence from the trace
3. Explain reasoning
4. Self-report confidence

#### Judge Output Format

```json
{
  "criterion_id": "verified-output-quality",
  "score": 0.50,
  "level_matched": "Partially Verified",
  "confidence": "high",
  "evidence": [
    {
      "turn": 15,
      "quote": "Agent: 'The video has been rendered to output.mp4'",
      "relevance": "Confirmed output file was created"
    }
  ],
  "reasoning": "Agent confirmed output file exists but did not verify codec, duration, or quality. No ffprobe or playback check. Matches 'Partially Verified' level.",
  "missing_evidence": [
    "Would need ffprobe output or quality check for 'Fully Verified'"
  ]
}
```

#### Self-Consistency Check

Run judge 3 times, flag if variance ≥ 0.15.

#### Dimension Scoring

| Dimension | Weight | Graded By |
|-----------|--------|-----------|
| **Correctness** | 40% | LLM rubric + deterministic assertions |
| **Efficiency** | 25% | Heuristics + LLM rubric (hand-holding) |
| **Tool Use** | 20% | Heuristics + LLM rubric (choices) |
| **Verification** | 15% | Heuristics + LLM rubric (thoroughness) |

### Phase 5: Evolve the Criteria

After each eval, the skill can suggest criteria additions:

```
New failure mode detected: Agent didn't check video codec before re-encoding

Suggested criterion to add to .agent-eval/criteria.json:
{
  "id": "checked-codec",
  "name": "Checked Source Codec",
  "check_type": "command_pattern",
  "patterns": ["ffprobe", "ffmpeg -i"],
  "rationale": "Re-encoding without checking codec can cause quality loss"
}

Add this criterion? (y/n)
```

The criteria evolve with the workflow:
- Coding project → tests, linting, type checking
- Video project → format checks, quality verification, source attribution
- Research project → source gathering, citation, fact-checking
- Design project → asset organization, naming conventions, export verification

### Phase 6: Log to JSONL

Append to `~/.pi/agent/evals/results.jsonl`:

```json
{
  "eval_id": "eval-20260604-153022-a1b2c3d",
  "timestamp": "2026-06-04T15:30:22Z",
  "project": "@repos/videos",
  "trace_path": "/path/to/session-export.md",
  "task": "Create a highlight reel from source footage",
  "tag": "prompt-v2.1",
  "domain": "video-production",
  "expected_skill": "video-edit",
  "skill_invoked": true,
  "scores": {
    "correctness": 0.80,
    "efficiency": 0.65,
    "tool_use": 0.85,
    "verification": 0.40,
    "overall": 0.70
  },
  "deterministic_checks": {
    "skill_invocation": { "pass": true },
    "downloaded-source": { "pass": true },
    "created-output-file": { "pass": true }
  },
  "llm_judgments": {
    "verified-output-quality": { "score": 0.50, "confidence": "high" }
  },
  "criteria_version": "2026-06-04-v1",
  "criteria_path": "@repos/videos/.agent-eval/criteria.json"
}
```

### Phase 7: Generate Report

Write report to `{output-dir}/{eval-id}/report.md`:

```markdown
# Agent Eval Report

## Session Metadata
- **Eval ID:** eval-20260604-153022-a1b2c3d
- **Project:** @repos/videos
- **Domain:** video-production
- **Task:** Create a highlight reel from source footage
- **Tag:** prompt-v2.1
- **Expected Skill:** video-edit
- **Skill Invoked:** ✅ Yes

## Scores

| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Correctness | 0.80 | 40% | 0.32 |
| Efficiency | 0.65 | 25% | 0.16 |
| Tool Use | 0.85 | 20% | 0.17 |
| Verification | 0.40 | 15% | 0.06 |
| **Overall** | | | **0.70** |

## Deterministic Checks

| Check | Result | Evidence |
|-------|--------|----------|
| Skill invocation | ✅ PASS | Found `/skill:video-edit` at turn 2 |
| Downloaded source | ✅ PASS | `yt-dlp` command at turn 4 |
| Checked video format | ❌ FAIL | No `ffprobe` or `ffmpeg -i` found |
| Created output file | ✅ PASS | `output.mp4` exists |

## LLM Judge Results

📝 Verified Output Quality — 0.50 (Partially Verified)
   Evidence: Confirmed output exists but no codec/duration check
   Confidence: high

## Criteria

Loaded from: `@repos/videos/.agent-eval/criteria.json`
Version: 2026-06-04-v1

## Suggested Criteria Additions

Based on this session, consider adding:
- `checked-codec` — verify source codec before re-encoding
- `verified-duration` — confirm output duration matches expectation

## Recommendations

### Medium
1. **Add video format verification** — agent didn't check source codec
   before re-encoding, risking quality loss

## Eval Candidates
- `agent_checks_video_codec_before_encode`
```

## The Project-Local Criteria System

### Directory Structure

Each project that uses agent-eval gets an `.agent-eval/` directory:

```
@repos/videos/
├── .agent-eval/
│   ├── criteria.json          # Living criteria for this project
│   ├── criteria-history/      # Previous versions
│   │   ├── criteria-2026-06-01.json
│   │   └── criteria-2026-06-04.json
│   └── reports/               # Per-session reports
│       ├── eval-20260601-120000.md
│       └── eval-20260604-153022.md
├── src/
├── footage/
└── output/
```

### Criteria Evolution

```bash
# First run — auto-generate criteria
/skill:agent-eval --project @repos/videos session-01.md
# Creates @repos/videos/.agent-eval/criteria.json

# Second run — criteria exist, use and refine
/skill:agent-eval --project @repos/videos session-02.md
# Uses existing criteria, suggests additions based on new failure modes

# Third run — criteria have evolved
/skill:agent-eval --project @repos/videos session-03.md
# More comprehensive, project-specific checks
```

### Sharing Criteria Across Similar Projects

```bash
# Copy criteria from one video project to another
cp @repos/videos/.agent-eval/criteria.json @repos/podcasts/.agent-eval/criteria.json

# Then adapt
cd @repos/podcasts
# Edit criteria.json to replace video-specific with audio-specific checks
```

## Domain Detection

The skill auto-detects the workflow domain from trace signals:

| Signal | Domain |
|--------|--------|
| `npm`, `pip`, `cargo`, `go` | coding |
| `ffmpeg`, `yt-dlp`, `premiere` | video-production |
| `kubectl`, `docker`, `terraform` | devops |
| `latex`, `pandoc`, `markdown` | writing |
| `blender`, `maya`, `unity` | 3d-graphics |

You can override:
```bash
/skill:agent-eval --domain video-production session.md
```

## Multi-Domain Projects

Some projects span domains. The criteria can mix checks:

```json
{
  "domain": "mixed",
  "criteria": [
    { "id": "backend-tests", "check_type": "command_pattern", "patterns": ["pytest"] },
    { "id": "frontend-build", "check_type": "command_pattern", "patterns": ["npm run build"] },
    { "id": "api-documentation", "check_type": "llm_judge", "rubric": { ... } }
  ]
}
```

## Integration with agent-benchmark

Both skills share:
- **Scoring rubric** (4 dimensions, same weights)
- **JSONL log format**
- **Eval candidate generation**

Use `agent-eval` for:
- Single-session analysis
- Building project-specific criteria
- Quick checks after harness changes

Use `agent-benchmark` for:
- Multi-model comparison
- Regression testing
- Scheduled/CI evaluation

## Files Reference

| File | Purpose |
|------|---------|
| `config/default-criteria.json` | Fallback criteria templates by domain |
| `references/scoring-rubric.md` | Shared grading prompts |
| `references/eval-template.py` | pytest stub for generated evals |
| `references/judge-prompt-template.md` | Standardized judge prompt |

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Wrong domain detected | Trace signals ambiguous | Use `--domain` override |
| Criteria too generic | First run, not enough context | Run more sessions, criteria will refine |
| Criteria too specific | Overfit to one session | Generalize patterns, remove one-off checks |
| Missing project criteria | No `--project` specified | Use `--project` or criteria load from cwd |

## Key Principles

1. **Evals are project-local** — Criteria live with the project they evaluate
2. **Criteria evolve** — Each session can improve the criteria
3. **Domain-agnostic** — Works for coding, video, research, anything
4. **Evidence-based** — Every score needs quoted evidence
5. **Human-in-the-loop** — Suggest additions, you approve

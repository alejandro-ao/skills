# Scoring Rubric

Detailed prompts and criteria for grading each dimension.

---

## Correctness (Weight: 40%)

**Question:** Did the agent fully and correctly solve the task?

### Scoring Guide

| Score | Criteria |
|-------|----------|
| 1.00 | Task fully solved, no bugs, all requirements met |
| 0.75 | Task mostly solved, minor issues or missing edge case |
| 0.50 | Partial solution, significant gaps or one major bug |
| 0.25 | Attempted but wrong approach or critical bug |
| 0.00 | No meaningful progress or completely wrong |

### LLM-as-Judge Prompt

```
You are grading an AI agent's work. The task was:

TASK: {task_description}

The agent produced this output:

---AGENT OUTPUT---
{agent_output}
---END OUTPUT---

Grade on correctness only. Did the agent fully solve the task?
- Check all explicit requirements in the task
- Check for bugs or logical errors
- Check that edge cases are handled if mentioned
- Ignore efficiency, tool use, or verification for this score

Respond with ONLY a number from 0.00 to 1.00, then a brief justification.
```

---

## Efficiency (Weight: 25%)

**Question:** How efficiently did the agent solve the task?

### Metrics

- **Turn ratio:** Actual turns / ideal turns (lower is better)
- **Tool call ratio:** Actual tool calls / ideal tool calls
- **Parallelization:** Did it parallelize independent calls?
- **Token burn:** Estimated tokens used (from trace length)

### Scoring Guide

| Score | Criteria |
|-------|----------|
| 1.00 | Optimal path: minimum turns, parallelized, no waste |
| 0.75 | Slightly longer path, minor inefficiencies |
| 0.50 | Noticeably longer, redundant calls, missed parallelization |
| 0.25 | Very inefficient, many unnecessary steps |
| 0.00 | Extremely wasteful or hit timeout |

### Ideal Trajectory Estimation

For simple tasks, define ideal explicitly. For complex tasks, use:
- Best-performing model on this task as baseline
- Human estimate of minimum viable path

---

## Tool Use (Weight: 20%)

**Question:** Did the agent use tools effectively?

### Criteria

1. **Right tool for the job** — Did it choose appropriate tools?
2. **No redundancy** — Did it avoid repeated identical calls?
3. **No loops** — Did it avoid editing the same file N times without progress?
4. **Parallelization** — Did it batch independent calls?
5. **Error recovery** — Did it handle tool errors gracefully?

### Scoring Guide

| Score | Criteria |
|-------|----------|
| 1.00 | Perfect tool selection, parallelized, no loops, graceful errors |
| 0.75 | Good tool use, minor redundancy or missed parallelization |
| 0.50 | Some wrong tools, moderate redundancy, or one loop |
| 0.25 | Frequent wrong tools, severe loops, or poor error handling |
| 0.00 | Completely broken tool use |

### Loop Detection

A "loop" is defined as:
- 3+ edits to the same file without running tests/verification in between
- 2+ identical tool calls with same arguments
- 5+ turns on the same subtask without progress

---

## Verification (Weight: 15%)

**Question:** Did the agent verify its work before finishing?

### Criteria

1. **Ran tests** — If tests existed or could be written, did it run them?
2. **Read output** — Did it read command/test output, not just execute?
3. **Compared to spec** — Did it check against original requirements?
4. **Didn't stop early** — Did it avoid "looks good to me" without checking?

### Scoring Guide

| Score | Criteria |
|-------|----------|
| 1.00 | Comprehensive verification: tests, output review, spec comparison |
| 0.75 | Good verification but missed one aspect (e.g., no edge case test) |
| 0.50 | Minimal verification (ran one check but not thorough) |
| 0.25 | Weak verification (glanced at output, no tests) |
| 0.00 | No verification — "looks good" or stopped immediately |

### Anti-Patterns

- "I have made the changes. Let me verify... Actually, the changes look correct."
- Running a command but not reading its output
- Writing tests but never executing them
- Checking happy path only, ignoring edge cases

---

## Overall Score

```
overall = (correctness × 0.40) + (efficiency × 0.25) + (tool_use × 0.20) + (verification × 0.15)
```

Round to 2 decimal places.

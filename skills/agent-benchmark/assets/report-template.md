# Benchmark Report: {task_slug}

## Run Metadata

| Field | Value |
|-------|-------|
| **Run ID** | {run_id} |
| **Timestamp** | {timestamp} |
| **Tag** | {tag} |
| **Git SHA** | {git_sha} |
| **Task** | {task} |
| **Working Directory** | {cwd} |
| **Models Tested** | {models_tested} |
| **Judge Model** | {judge_model} |

---

## Results Summary

| Model | Overall ⭐ | Correctness | Efficiency | Tool Use | Verification | Turns | Duration | Status |
|-------|-----------|-------------|------------|----------|--------------|-------|----------|--------|
{results_table}

**Winner:** {winner} ({winner_score})

---

## Trend (last {compare_n} runs)

{trend_chart}

---

## 🚨 Regressions

{regressions}

---

## Recommendations

### Critical
{critical_recommendations}

### Medium
{medium_recommendations}

### Low
{low_recommendations}

---

## Eval Candidates

{eval_candidates}

---

## Detailed Model Results

{detailed_results}

---

## Traces

{trace_links}

---

## Raw Data

- Full JSON: `{json_path}`
- Results JSONL: `{results_jsonl_path}`

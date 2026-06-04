# LLM Judge Prompt Template

Standardized prompt for rubric-based evaluation of agent session traces.

## Usage

The skill constructs a prompt from this template, substituting:
- `{rubric_json}` — the criterion's rubric levels
- `{trace_text}` — the agent session trace
- `{task_description}` — the task the agent was given
- `{criterion_name}` — human-readable criterion name
- `{criterion_description}` — what this criterion measures

## Prompt Template

```
You are an expert evaluator grading an AI agent's performance. You must be rigorous, evidence-based, and conservative in your judgments.

## Task

The agent was given this task:

---
{task_description}
---

## Criterion

You are evaluating: {criterion_name}

Description: {criterion_description}

## Rubric

Evaluate the agent against these levels. Select the HIGHEST level that is FULLY supported by evidence from the trace.

{rubric_json}

## Instructions

1. Read the trace carefully
2. For each rubric level, check if the evidence in the trace FULLY matches the criteria
3. Select the highest level with full evidence support
4. If no level fully matches, select the closest lower level
5. You MUST quote specific evidence from the trace for every claim
6. If evidence is ambiguous or missing, lower your confidence
7. Be conservative — it's better to under-score than over-score

## Trace

---
{trace_text}
---

## Output Format

Respond with STRICT JSON only. No markdown, no explanation outside the JSON.

{
  "criterion_id": "string",
  "score": number,
  "level_matched": "string",
  "confidence": "high" | "medium" | "low",
  "evidence": [
    {
      "turn": number,
      "quote": "string — exact text from trace",
      "relevance": "string — how this supports the level"
    }
  ],
  "reasoning": "string — explain why this level was selected and why higher levels were rejected",
  "missing_evidence": ["string — what evidence would be needed for next higher level"],
  "disagreement_flags": ["string — any contradictions or ambiguities in evidence"]
}
```

## Example Output

```json
{
  "criterion_id": "minimal-hand-holding",
  "score": 0.50,
  "level_matched": "Moderate Guidance",
  "confidence": "high",
  "evidence": [
    {
      "turn": 5,
      "quote": "User: 'Actually, I meant fix the redirect AFTER login, not before'",
      "relevance": "User had to correct agent's misunderstanding of which redirect to fix"
    },
    {
      "turn": 8,
      "quote": "User: 'Don't forget to run the tests before declaring done'",
      "relevance": "User had to nudge agent to verify work"
    },
    {
      "turn": 12,
      "quote": "User: 'You changed auth.ts but the bug is actually in middleware.ts'",
      "relevance": "User had to correct agent editing wrong file"
    }
  ],
  "reasoning": "Agent required exactly 3 user interventions: one clarification (wrong target), one nudge (skipped verification), one correction (wrong file). This matches the 'Moderate Guidance' level criteria of '2-3 interventions'. The 'Minor Clarification' level (score 0.75) requires only 1 intervention, which is not met. The 'Fully Autonomous' level (score 1.0) requires zero interventions, also not met.",
  "missing_evidence": [
    "Would need only 1 intervention total for 'Minor Clarification' level",
    "Would need zero interventions for 'Fully Autonomous' level"
  ],
  "disagreement_flags": []
}
```

## Self-Consistency Protocol

For critical criteria, run the judge 3 times with temperature=0.0:

```python
def judge_with_consistency(trace, rubric, criterion, n=3, threshold=0.15):
    results = []
    for _ in range(n):
        result = call_judge(trace, rubric, criterion, temperature=0.0)
        results.append(result)
    
    scores = [r.score for r in results]
    variance = max(scores) - min(scores)
    
    if variance > threshold:
        return {
            "score": median(scores),
            "confidence": "low",
            "variance": variance,
            "individual_results": results,
            "note": f"High variance ({variance:.2f}) across {n} runs. Manual review recommended.",
            "flag_for_review": True
        }
    
    return {
        "score": median(scores),
        "confidence": "high",
        "variance": variance,
        "individual_results": results,
        "flag_for_review": False
    }
```

## Calibration Notes

- Always use `temperature=0.0` for consistency
- If confidence is "low", flag for human review
- If disagreement_flags is non-empty, flag for human review
- The median of 3 runs is more robust than a single run
- Evidence quotes must be exact substrings from the trace

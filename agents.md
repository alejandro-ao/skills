# Agents

This repository contains agent skills for pi coding agent.

## Available Skills

| Skill | Description |
|-------|-------------|
| [agent-benchmark](./skills/agent-benchmark) | Runs agent tasks across multiple LLMs in parallel, scores results, and tracks improvements over time. |
| [agent-eval](./skills/agent-eval) | Evaluates a single agent session trace against project-specific test cases. |
| [explore-project](./skills/explore-project) | Creates beginner-friendly documentation by exploring and documenting a codebase. |
| [hermes-vps-setup](./skills/hermes-vps-setup) | Sets up and configures Hermes VPS. |

## Adding a New Skill

1. Create a new directory under `./skills/`
2. Add a `SKILL.md` file with:
   - `name`: Skill identifier
   - `description`: When to use this skill
   - Content: Instructions for the agent

## Skill Structure

```
skills/
├── skill-name/
│   └── SKILL.md
└── another-skill/
    └── SKILL.md
```
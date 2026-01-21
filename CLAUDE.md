# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Claude Code plugin marketplace by Alejandro AO. Contains plugins that extend Claude Code with skills.

## Structure

```
.claude-plugin/marketplace.json  # Marketplace metadata, lists all plugins
plugins/
  <plugin-name>/
    .claude-plugin/plugin.json   # Plugin metadata, lists skills
    skills/
      <skill-name>/
        SKILL.md                 # Skill prompt/instructions
        workflows.md             # Optional: example workflows
```

## Adding New Plugins

1. Create `plugins/<name>/.claude-plugin/plugin.json`:
```json
{
  "name": "<name>",
  "description": "...",
  "version": "1.0.0",
  "skills": ["<skill-name>"]
}
```

2. Create skill at `plugins/<name>/skills/<skill-name>/SKILL.md`

3. Register in `.claude-plugin/marketplace.json` under `plugins` array

## SKILL.md Format

Skills use YAML frontmatter + markdown body:
```md
---
name: skill-name
description: |
  When to trigger this skill...
---

# Instructions for Claude
...
```

## Current Plugins

- **video-tool**: Wraps external `video-tool` CLI for video processing (download, trim, transcribe, upload)

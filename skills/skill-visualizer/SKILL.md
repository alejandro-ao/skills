---
name: skill-visualizer
description: Generate an interactive HTML dashboard that visualizes all available agent skills. Use when the user wants to see, browse, search, or review skills in the current workspace or user home folder. Triggers on requests like "show me my skills", "visualize skills", "create a skills dashboard", "generate an HTML page for skills", or when the user needs to discover or audit available skills in markdown files with their associated scripts.
---

# Skill Visualizer

Generate a single self-contained HTML file that renders every discovered skill as a browsable, searchable dashboard.

## How It Works

The bundled script scans two locations:

1. **Workspace skills** — `./.agents/skills/` (relative to the working directory)
2. **User home skills** — `~/.agents/skills/`

For each skill directory containing a `SKILL.md`, the script extracts the YAML frontmatter (`name`, `description`) and renders the markdown body into HTML. Any files inside the skill's `scripts/` folder are listed as associated scripts.

## Usage

Run the generator from the repository root (or wherever the workspace `.agents/skills/` should be resolved):

```bash
python ~/.agents/skills/skill-visualizer/scripts/generate_skill_visualizer.py [output.html]
```

Defaults:
- `output.html` = system temp directory (`/tmp/skills-visualizer.html` on most Unix systems)
- Searches workspace `./.agents/skills` and home `~/.agents/skills`
- **Auto-opens** in the default browser after generation

Options:
- `--no-open` / `-n` — skip automatically opening the browser (useful for CI or headless environments)
- Pass an explicit path to write the file to a specific location instead of the temp directory

## Output Features

Single-page app layout with three panels:

- **Left sidebar** — grouped skill list (Workspace Skills / User Home Skills)
  - Click any skill to load it in the main area
  - Live search filters the skill list by name, body content, script names, or reference names
- **Main area** — shows *only* the currently selected skill
  - Rendered `SKILL.md` with full markdown support
  - Every `scripts/` file displayed in a code block with its filename
  - Every `references/` file: markdown references are rendered as HTML; other files shown in code blocks
  - `assets/` filenames listed for quick reference
  - Scrolling stops at the bottom of the current skill; you must click another skill in the left sidebar to switch
- **Right sidebar** — table of contents for the *active skill*
  - Lists all headings from `SKILL.md` plus Scripts, References, and Assets sections
  - Highlights the current section as you scroll through the main area
  - Click any item to smooth-scroll directly to that section within the skill
- **Self-contained** — no external assets or dependencies; works offline

## Limitations

- Only discovers skills with a `SKILL.md` file directly inside the skill directory.
- Does not recursively scan sub-directories beyond one level.
- Very complex markdown (nested tables, HTML inside markdown) may render imperfectly.

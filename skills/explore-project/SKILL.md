---
name: explore-project
description: Creates beginner-friendly, step-by-step documentation for a project. Use this skill when the user wants to understand, document, or explore an unfamiliar codebase. Triggers on phrases like "explore this project", "document this", "create docs", "what does this codebase do", "understand this project", or when starting work on a new project and needing to map it out.
---

# Create Documentation

This skill guides you through creating comprehensive, beginner-friendly documentation for a codebase.

## When to Use This Skill

- User asks to "document this project" or "create documentation"
- Starting work on a new project and user wants docs
- User says "write the docs" or "generate documentation"
- You're exploring a codebase and need to document it

## The Approach

### 1. Understand the Project Structure

Before creating docs, explore the codebase:

```bash
# Find all source files and understand structure
find . -type f -name "*.ts" -o -name "*.js" -o -name "*.py" | head -50

# Read key files
cat package.json
cat README.md

# Understand the architecture
ls -la
```

### 2. Create Documentation Directory

Create an `.exploration/` directory in the project root:

```bash
mkdir -p .exploration
```

### 3. Determine What Documents to Create

Based on project type and structure, create documents covering:

| Project Type | Essential Documents |
|--------------|---------------------|
| Agent/AI project | Architecture overview, agent loop, tools, system prompt |
| CLI application | CLI entry point, argument parsing, modes |
| Web application | Architecture, routing, data flow |
| Library | API documentation, usage examples |
| Full-stack | All above + deployment, configuration |

### 4. Document Template Structure

Each document should follow this pattern:

```markdown
# [Document Title]

Brief paragraph explaining what this document covers.

## Overview Section
- What is this component
- Why it exists
- How it fits into the larger picture

## Technical Details
- Key functions/classes
- Important code patterns
- File locations

## Flow Diagrams (ASCII)
Use ASCII diagrams for visual clarity:

    Input
      ↓
    Process
      ↓
    Output

## Code Examples
Show real, working code snippets from the project.

## File Reference
| File | Purpose |
|------|---------|
| file.ts | What it does |

## Related Documents
Link to related docs for further reading.
```

### 5. The Step-by-Step Process

#### Phase 1: Big Picture (First 2-3 Documents)

1. **Architecture Overview** (priority: highest)
   - Package/directory structure
   - How components connect
   - Design decisions and why

2. **Entry Point / Startup Flow**
   - How the application starts
   - Key initialization steps
   - Configuration discovery

3. **Core Concepts**
   - Main abstractions
   - Data structures
   - Key interfaces

#### Phase 2: Deep Dives (Next 5-8 Documents)

4. **Individual Components**
   - For each major component:
     - What it does
     - Key methods
     - How it interacts with others

5. **Data Flow**
   - How data moves through the system
   - State management
   - Event/hook systems

6. **Configuration**
   - How settings are loaded
   - Environment variables
   - Config file formats

#### Phase 3: Reference Material (Last 2-3 Documents)

7. **API Reference**
   - Function signatures
   - Type definitions
   - Usage examples

8. **Troubleshooting**
   - Common issues
   - Debug techniques
   - Migration guides

### 6. Cross-Reference Everything

Create links between related documents:

```markdown
## See Also
- [Related Document](related-doc.md) - Brief description
- [API Reference](api.md) - For function details
```

### 7. Update the README/Index

Add all new documents to an index:

```markdown
## Document List

| # | Document | Description |
|---|----------|-------------|
| 01 | [Title](01-title.md) | Brief description |
```

## Quality Checklist

Before finishing, verify each document:

- [ ] Clear, beginner-friendly language
- [ ] No jargon without explanation
- [ ] Real code examples from the project
- [ ] ASCII diagrams for visual concepts
- [ ] File paths match actual structure
- [ ] Cross-references to related docs
- [ ] Table of contents or index
- [ ] "Why" explanations (not just "what")

## Document Naming Convention

Use numbered prefixes for ordering:

```
01-architecture-overview.md
02-core-concepts.md
03-component-a.md
04-component-b.md
...
```

Numbers allow natural reading order while being explicit.

## Common Pitfalls to Avoid

1. **Don't over-explain obvious things**
   - Bad: "This function increments a counter by one"
   - Good: "Increments the request counter"

2. **Don't just copy code comments**
   - Expand on "why" not just "what"
   - Explain the context

3. **Don't skip the architecture section**
   - Readers need the big picture first
   - Architecture docs are priority #1

4. **Don't use placeholder text**
   - Bad: "This section will be expanded later"
   - Good: "This feature is under development - see GitHub for updates"

## Example Output Structure

For a typical project, create:

```
project/
├── README.md          (points to docs)
└── .exploration/
    ├── README.md      (index of all docs)
    ├── 01-architecture-overview.md
    ├── 02-entry-point.md
    ├── 03-core-concepts.md
    ├── 04-component-name.md
    ├── 05-data-flow.md
    ├── 06-configuration.md
    ├── 07-api-reference.md
    └── 08-troubleshooting.md
```

## Adapting to Project Size

| Project Size | Document Count | Focus |
|-------------|----------------|-------|
| Small (<10 files) | 3-5 docs | Core concepts only |
| Medium (10-50 files) | 5-8 docs | Architecture + key components |
| Large (50+ files) | 10-15 docs | Full coverage with deep dives |

## Special Cases

### For Agent/SDK Projects

Always include:
- Architecture overview (packages, modules)
- Agent loop explanation
- Tool system
- System prompt construction
- Event hooks
- Extension system

### For CLI Tools

Always include:
- Entry point flow
- Argument parsing
- Commands/subcommands
- Configuration files
- Installation/uninstall

### For Web Applications

Always include:
- Architecture (frontend/backend)
- Routing
- State management
- API layer
- Deployment

## Next Steps After Documenting

1. **Review with user**: Ask if anything is unclear
2. **Add diagrams**: Use mermaid or ASCII for flowcharts
3. **Create examples**: Real, runnable code samples
4. **Write tests**: Document expected behaviors as tests

## Remember

Good documentation is:
- **Beginner-friendly**: Explain concepts from scratch
- **Comprehensive**: Cover everything important
- **Accurate**: Code examples must work
- **Maintained**: Update when code changes

The goal is that a new developer can read the docs, understand the project, and start contributing.
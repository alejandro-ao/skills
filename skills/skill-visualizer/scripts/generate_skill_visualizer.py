#!/usr/bin/env python3
"""
Generate an interactive SPA-style HTML dashboard for agent skills.

Usage:
    python generate_skill_visualizer.py [--open] [output.html]

Defaults:
    output.html = <temp dir>/skills-visualizer.html
    workspace   = ./.agents/skills
    home        = ~/.agents/skills
"""

import argparse
import base64
import json
import re
import sys
import tempfile
import webbrowser
from pathlib import Path


# ---------------------------------------------------------------------------
# Markdown -> HTML
# ---------------------------------------------------------------------------

def escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def slugify(text: str) -> str:
    s = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[-\s]+", "-", s).strip("-")


def parse_frontmatter(text: str) -> tuple[dict, str]:
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            fm = parts[1].strip()
            body = parts[2].strip()
            return parse_simple_yaml(fm), body
    return {}, text


def parse_simple_yaml(yaml_text: str) -> dict:
    """Parse the small YAML subset used by skill frontmatter.

    Supports simple `key: value` entries and multiline block scalars like
    `description: |` / `description: >` without requiring PyYAML.
    """
    meta: dict = {}
    lines = yaml_text.splitlines()
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in line:
            i += 1
            continue

        key, val = line.split(":", 1)
        key = key.strip()
        val = val.strip()

        if val in {"|", "|-", "|+", ">", ">-", ">+"}:
            style = val[0]
            i += 1
            block_lines: list[str] = []
            while i < len(lines):
                next_line = lines[i]
                next_stripped = next_line.strip()
                if next_stripped and not next_line.startswith((" ", "\t")) and ":" in next_line:
                    break
                block_lines.append(next_line)
                i += 1

            indents = [len(l) - len(l.lstrip(" ")) for l in block_lines if l.strip()]
            min_indent = min(indents) if indents else 0
            dedented = [l[min_indent:] if len(l) >= min_indent else l for l in block_lines]
            if style == ">":
                meta[key] = " ".join(l.strip() for l in dedented if l.strip())
            else:
                meta[key] = "\n".join(dedented).strip("\n")
            continue

        meta[key] = val.strip().strip('"').strip("'")
        i += 1

    return meta


def md_to_html(md: str, id_prefix: str = "", toc_level_offset: int = 0) -> str:
    md = md.replace("\r\n", "\n")
    out = md

    # fenced code blocks
    def repl_code(m: re.Match) -> str:
        lang = escape_html(m.group(1) or "").strip()
        code = escape_html(m.group(2))
        return f'<pre><code class="language-{lang}">{code}</code></pre>'

    out = re.sub(r"```(\w*)\n(.*?)```", repl_code, out, flags=re.S)

    # inline code
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)

    # headings with ids and toc-level
    for level in range(6, 0, -1):
        tag = f"h{level + 1}"
        tl = max(0, (level - 2) + toc_level_offset)

        def make_heading_repl(lvl: int, ttag: str, toc_lvl: int):
            def _repl(m: re.Match) -> str:
                text = m.group(1).strip()
                hid = f"{id_prefix}{slugify(text)}"
                return f'<{ttag} id="{hid}" data-toc-level="{toc_lvl}">{escape_html(text)}</{ttag}>'
            return _repl

        out = re.sub(
            rf"^{ '#' * level } (.+)$",
            make_heading_repl(level, tag, tl),
            out,
            flags=re.M,
        )

    # bold / italic
    out = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", out)
    out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"\*(.+?)\*", r"<em>\1</em>", out)

    # links
    out = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2" target="_blank">\1</a>', out)

    # tables
    out = _convert_tables(out)

    # lists
    out = _convert_lists(out, r"^\s*[-*]\s+", "ul")
    out = _convert_lists(out, r"^\s*\d+\.\s+", "ol")

    # blockquotes
    out = re.sub(r"^>\s*(.+)$", r"<blockquote>\1</blockquote>", out, flags=re.M)

    # horizontal rules
    out = re.sub(r"^\s*---\s*$", "<hr>", out, flags=re.M)

    # paragraphs
    paragraphs = []
    for block in out.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        if block.startswith("<") and block.endswith(">") and "\n" not in block:
            paragraphs.append(block)
        elif block.startswith("<") and block.count("<") > 1:
            paragraphs.append(block)
        else:
            paragraphs.append(f"<p>{block}</p>")

    return "\n\n".join(paragraphs)


def _convert_lists(text: str, pattern: str, tag: str) -> str:
    lines = text.splitlines(keepends=True)
    in_list = False
    out_lines: list[str] = []
    current_items: list[str] = []

    def flush() -> str:
        if not current_items:
            return ""
        html = f"<{tag}>\n"
        for item in current_items:
            html += f"  <li>{item.strip()}</li>\n"
        html += f"</{tag}>"
        return html

    for line in lines:
        stripped = line.lstrip()
        match = re.match(pattern, stripped)
        if match:
            if not in_list:
                in_list = True
            content = stripped[match.end():].rstrip("\n")
            current_items.append(content)
            out_lines.append("")
        else:
            if in_list and stripped.strip() == "":
                in_list = False
                replacement = flush()
                count = len(current_items)
                for _ in range(count):
                    if out_lines and out_lines[-1] == "":
                        out_lines.pop()
                out_lines.append(replacement + "\n")
                current_items = []
                out_lines.append(line)
            elif in_list:
                current_items[-1] += " " + stripped.rstrip("\n")
                out_lines.append("")
            else:
                out_lines.append(line)

    if in_list:
        count = len(current_items)
        for _ in range(count):
            if out_lines and out_lines[-1] == "":
                out_lines.pop()
        out_lines.append(flush() + "\n")

    return "".join(out_lines)


def _convert_tables(text: str) -> str:
    lines = text.splitlines()
    result: list[str] = []
    table_lines: list[str] = []

    def flush_table() -> str:
        if len(table_lines) < 2:
            return "\n".join(table_lines)
        header = table_lines[0]
        separator = table_lines[1]
        if not re.match(r"^\s*\|?\s*:?-+:?(?:\s*\|\s*:?-+:?)\s*\|?\s*$", separator):
            return "\n".join(table_lines)
        rows = table_lines[2:]
        html = "<table>\n<thead>\n<tr>\n"
        for cell in header.split("|"):
            cell = cell.strip()
            if cell:
                html += f"  <th>{cell}</th>\n"
        html += "</tr>\n</thead>\n<tbody>\n"
        for row in rows:
            html += "<tr>\n"
            for cell in row.split("|"):
                cell = cell.strip()
                if cell:
                    html += f"  <td>{cell}</td>\n"
            html += "</tr>\n"
        html += "</tbody>\n</table>"
        return html

    for line in lines:
        if "|" in line:
            table_lines.append(line)
        else:
            if table_lines:
                result.append(flush_table())
                table_lines = []
            result.append(line)
    if table_lines:
        result.append(flush_table())
    return "\n".join(result)


# ---------------------------------------------------------------------------
# Skill discovery
# ---------------------------------------------------------------------------

def read_text_file(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, Exception):
        return None


def read_any_file(path: Path) -> tuple[str, str]:
    text = read_text_file(path)
    if text is not None:
        return text, "text"
    try:
        data = path.read_bytes()
        return data.decode("utf-8", errors="replace"), "text"
    except Exception:
        return "", "binary"


def discover_skills(base_dir: Path) -> list[dict]:
    skills: list[dict] = []
    if not base_dir.exists():
        return skills
    for entry in sorted(base_dir.iterdir()):
        if not entry.is_dir():
            continue
        skill_md = entry / "SKILL.md"
        if not skill_md.exists():
            continue
        content = skill_md.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(content)

        # body HTML
        body_html = md_to_html(body, id_prefix=f"{entry.name}-body-")

        # scripts
        scripts_dir = entry / "scripts"
        scripts: list[dict] = []
        if scripts_dir.exists():
            for f in sorted(scripts_dir.iterdir()):
                if not f.is_file():
                    continue
                text, kind = read_any_file(f)
                scripts.append({
                    "name": f.name,
                    "content": text,
                    "kind": kind,
                    "id": f"{entry.name}-script-{slugify(f.name)}",
                })

        # references
        refs_dir = entry / "references"
        references: list[dict] = []
        if refs_dir.exists():
            for f in sorted(refs_dir.iterdir()):
                if not f.is_file():
                    continue
                text, kind = read_any_file(f)
                is_md = f.suffix.lower() == ".md"
                ref_html = ""
                if is_md and text:
                    ref_html = md_to_html(
                        text,
                        id_prefix=f"{entry.name}-ref-{slugify(f.name)}-",
                        toc_level_offset=1,
                    )
                references.append({
                    "name": f.name,
                    "content": text,
                    "kind": kind,
                    "is_markdown": is_md,
                    "html": ref_html,
                    "id": f"{entry.name}-ref-{slugify(f.name)}",
                })

        # assets
        assets_dir = entry / "assets"
        assets: list[str] = []
        if assets_dir.exists():
            assets = sorted([f.name for f in assets_dir.iterdir() if f.is_file()])

        skills.append({
            "id": entry.name,
            "name": meta.get("name", entry.name),
            "description": meta.get("description", ""),
            "path": str(entry),
            "body_html": body_html,
            "scripts": scripts,
            "references": references,
            "assets": assets,
        })
    return skills


# ---------------------------------------------------------------------------
# HTML builder
# ---------------------------------------------------------------------------

def build_html(groups: dict[str, list[dict]], title: str = "Skill Visualizer") -> str:
    # Serialize skill data
    all_skills: dict[str, dict] = {}
    group_order: list[str] = []
    group_skill_ids: dict[str, list[str]] = {}

    for group_name, skills in groups.items():
        if not skills:
            continue
        group_order.append(group_name)
        ids = []
        for s in skills:
            ids.append(s["id"])
            all_skills[s["id"]] = s
        group_skill_ids[group_name] = ids

    data_payload = {
        "skills": all_skills,
        "groups": group_order,
        "group_skills": group_skill_ids,
    }
    json_str = json.dumps(data_payload, ensure_ascii=False)
    b64_data = base64.b64encode(json_str.encode("utf-8")).decode("ascii")

    css = """
    :root {
      --bg: #f8f9fa;
      --fg: #212529;
      --sidebar-bg: #ffffff;
      --sidebar-border: #dee2e6;
      --accent: #0d6efd;
      --accent-light: #e7f1ff;
      --code-bg: #f1f3f5;
      --blockquote-border: #0d6efd;
      --card-bg: #ffffff;
      --card-shadow: 0 1px 3px rgba(0,0,0,0.07), 0 1px 2px rgba(0,0,0,0.05);
      --radius: 8px;
      --font-main: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      --font-mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
    }
    * { box-sizing: border-box; }
    html, body { height: 100%; margin: 0; }
    body {
      font-family: var(--font-main);
      background: var(--bg); color: var(--fg);
      display: flex; overflow: hidden;
    }

    /* LEFT SIDEBAR */
    #sidebar {
      width: 280px; min-width: 240px; max-width: 340px;
      background: var(--sidebar-bg);
      border-right: 1px solid var(--sidebar-border);
      display: flex; flex-direction: column;
    }
    #sidebar header {
      padding: 1.25rem 1.25rem 0.75rem;
      border-bottom: 1px solid var(--sidebar-border);
    }
    #sidebar header h1 { margin: 0 0 0.5rem; font-size: 1.15rem; font-weight: 700; }
    #sidebar header p { margin: 0; font-size: 0.78rem; color: #6c757d; }
    #search {
      margin: 0.75rem 1.25rem 0.5rem;
      padding: 0.5rem 0.75rem;
      border: 1px solid var(--sidebar-border);
      border-radius: var(--radius);
      font-size: 0.85rem;
      outline: none; width: calc(100% - 2.5rem);
    }
    #search:focus { border-color: var(--accent); }
    #skill-list {
      flex: 1; overflow-y: auto; padding: 0 0.75rem 1rem;
    }
    .group-title {
      font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.06em;
      color: #6c757d; margin: 0.9rem 0 0.35rem; padding-left: 0.35rem;
    }
    .skill-btn {
      display: block; width: 100%; text-align: left;
      padding: 0.45rem 0.6rem;
      border: none; border-radius: calc(var(--radius) / 2);
      background: transparent; color: var(--fg);
      font-size: 0.84rem; cursor: pointer;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
      transition: background 0.12s;
    }
    .skill-btn:hover { background: var(--accent-light); color: var(--accent); }
    .skill-btn.active { background: var(--accent-light); color: var(--accent); font-weight: 600; }
    .skill-btn.hidden { display: none; }
    .group-title.hidden { display: none; }

    /* MAIN */
    #main {
      flex: 1; overflow-y: auto; padding: 2.5rem 3rem;
    }
    .skill-view {
      max-width: 880px; margin: 0 auto;
      background: var(--card-bg);
      border-radius: var(--radius);
      box-shadow: var(--card-shadow);
      padding: 2rem 2.5rem;
      min-height: calc(100vh - 5rem);
    }
    .skill-header {
      padding-bottom: 0; margin-bottom: 0;
    }
    .skill-header h1 { margin: 0 0 0.35rem; font-size: 1.6rem; font-weight: 700; }
    .skill-header .path {
      font-size: 0.78rem; color: #868e96; font-family: var(--font-mono);
    }
    .skill-header .desc { margin: 0.6rem 0 0; font-size: 0.9rem; color: #495057; line-height: 1.5; white-space: pre-line; }

    /* TABS NAV */
    .tabs {
      display: flex; gap: 0;
      border-bottom: 1px solid var(--sidebar-border);
      padding: 0 0.15rem;
      margin: 1.25rem 0 0;
    }
    .tab {
      padding: 0.65rem 1.1rem;
      border: none; background: transparent;
      color: #6c757d; font-size: 0.85rem;
      font-weight: 500; cursor: pointer;
      border-bottom: 2px solid transparent;
      margin-bottom: -1px;
      transition: color 0.15s, border-color 0.15s;
    }
    .tab:hover { color: var(--accent); }
    .tab.active {
      color: var(--accent);
      border-bottom-color: var(--accent);
      font-weight: 600;
    }
    .tab.hidden { display: none; }
    .tab-content { padding: 1.5rem 0; }
    .tab-content.hidden { display: none; }

    .skill-body h2 { font-size: 1.25rem; margin-top: 1.6rem; font-weight: 600; }
    .skill-body h3 { font-size: 1.1rem; margin-top: 1.35rem; font-weight: 600; }
    .skill-body h4 { font-size: 1rem; margin-top: 1.15rem; font-weight: 600; }
    .skill-body h5 { font-size: 0.92rem; margin-top: 1rem; font-weight: 600; }
    .skill-body h6 { font-size: 0.85rem; margin-top: 0.9rem; font-weight: 600; }
    .skill-body p { line-height: 1.65; margin: 0.75rem 0; }
    .skill-body pre {
      background: var(--code-bg); border-radius: var(--radius);
      padding: 1rem; overflow-x: auto; font-family: var(--font-mono);
      font-size: 0.8rem; line-height: 1.5;
    }
    .skill-body code {
      background: var(--code-bg); padding: 0.15rem 0.35rem;
      border-radius: 4px; font-family: var(--font-mono); font-size: 0.85em;
    }
    .skill-body pre code { padding: 0; background: none; }
    .skill-body ul, .skill-body ol { padding-left: 1.5rem; }
    .skill-body li { margin: 0.3rem 0; }
    .skill-body blockquote {
      border-left: 4px solid var(--blockquote-border);
      margin: 1rem 0; padding: 0.5rem 1rem;
      background: #f8f9fa; border-radius: 0 var(--radius) var(--radius) 0;
    }
    .skill-body table {
      width: 100%; border-collapse: collapse; margin: 1rem 0;
      font-size: 0.85rem;
    }
    .skill-body th, .skill-body td {
      border: 1px solid var(--sidebar-border);
      padding: 0.5rem 0.75rem; text-align: left;
    }
    .skill-body th { background: var(--code-bg); font-weight: 600; }

    /* Resources */
    .resource-section { margin-top: 0.5rem; }
    .resource-label {
      font-size: 0.7rem; text-transform: uppercase;
      letter-spacing: 0.06em; color: #6c757d;
      margin: 1.5rem 0 0.6rem;
    }
    .file-box {
      margin-bottom: 1rem;
      border: 1px solid var(--sidebar-border);
      border-radius: var(--radius);
      overflow: hidden;
    }
    .file-header {
      background: #f8f9fa; padding: 0.5rem 0.85rem;
      font-size: 0.82rem; font-weight: 600; color: #495057;
      font-family: var(--font-mono);
      border-bottom: 1px solid var(--sidebar-border);
    }
    .file-box pre {
      margin: 0; padding: 0.85rem;
      font-size: 0.78rem; overflow-x: auto;
      background: #fafbfc;
    }

    /* SYNTAX HIGHLIGHTING */
    .syn-comment { color: #6a737d; font-style: italic; }
    .syn-string  { color: #032f62; }
    .syn-keyword { color: #d73a49; font-weight: 600; }
    .syn-type    { color: #6f42c1; }
    .syn-builtin { color: #6f42c1; }
    .syn-number  { color: #005cc5; }
    .syn-func    { color: #6f42c1; }
    .syn-param   { color: #e36209; }
    .syn-tag     { color: #22863a; }
    .syn-attr    { color: #6f42c1; }
    .rendered-ref {
      padding: 1rem 1.25rem;
      font-size: 0.9rem; line-height: 1.6;
    }
    .rendered-ref h2 { font-size: 1.15rem; margin-top: 1.2rem; }
    .rendered-ref h3 { font-size: 1.05rem; margin-top: 1rem; }
    .rendered-ref h4 { font-size: 0.95rem; margin-top: 0.9rem; }
    .rendered-ref pre { background: var(--code-bg); padding: 0.75rem; border-radius: var(--radius); font-size: 0.78rem; overflow-x: auto; }
    .rendered-ref code { background: var(--code-bg); padding: 0.1rem 0.3rem; border-radius: 3px; font-size: 0.82em; }
    .asset-list {
      margin: 0; padding-left: 1.25rem;
      font-size: 0.85rem; font-family: var(--font-mono);
    }
    .asset-list li { margin: 0.25rem 0; }

    /* RIGHT SIDEBAR */
    #rightbar {
      width: 240px; min-width: 200px; max-width: 280px;
      background: var(--sidebar-bg);
      border-left: 1px solid var(--sidebar-border);
      display: flex; flex-direction: column;
    }
    #rightbar header {
      padding: 1.25rem 1rem 0.75rem;
      border-bottom: 1px solid var(--sidebar-border);
      font-size: 0.85rem; font-weight: 700;
    }
    #toc-nav {
      flex: 1; overflow-y: auto; padding: 0.75rem 1rem 1rem;
    }
    .toc-link {
      display: block; padding: 0.3rem 0.4rem;
      font-size: 0.78rem; color: var(--fg); text-decoration: none;
      border-radius: 4px; white-space: nowrap; overflow: hidden;
      text-overflow: ellipsis; transition: background 0.12s;
    }
    .toc-link:hover { background: var(--accent-light); color: var(--accent); }
    .toc-link.active { background: var(--accent-light); color: var(--accent); font-weight: 600; }
    .toc-lvl-0 { padding-left: 0.4rem; }
    .toc-lvl-1 { padding-left: 1rem; }
    .toc-lvl-2 { padding-left: 1.6rem; }
    .toc-lvl-3 { padding-left: 2.2rem; }
    .toc-lvl-4 { padding-left: 2.8rem; }
    """

    _rules_path = Path(__file__).resolve().parent / 'syntax_rules.json'
    with open(_rules_path) as _f:
        syntax_rules = json.load(_f)
    rules_json = json.dumps(syntax_rules, ensure_ascii=False)

    js = rf"""
    const SYNTAX_RULES = {rules_json};
    const b64Data = '{b64_data}';
    const jsonBytes = Uint8Array.from(atob(b64Data), c => c.charCodeAt(0));
    const jsonStr = new TextDecoder('utf-8').decode(jsonBytes);
    const DATA = JSON.parse(jsonStr);
    const skills = DATA.skills;
    const groups = DATA.groups;
    const groupSkills = DATA.group_skills;

    let currentSkillId = null;

    function init() {{
      renderSidebar();
      // select first visible skill
      const first = document.querySelector('.skill-btn:not(.hidden)');
      if (first) selectSkill(first.dataset.id);
    }}

    function renderSidebar() {{
      const list = document.getElementById('skill-list');
      let html = '';
      groups.forEach(g => {{
        const ids = groupSkills[g] || [];
        if (!ids.length) return;
        html += `<div class="group-title" data-group="${{escapeHtml(g)}}">${{escapeHtml(g)}}</div>`;
        ids.forEach(id => {{
          const s = skills[id];
          html += `<button class="skill-btn" data-id="${{id}}" data-name="${{escapeHtml(s.name)}}">${{escapeHtml(s.name)}}</button>`;
        }});
      }});
      list.innerHTML = html;

      list.querySelectorAll('.skill-btn').forEach(btn => {{
        btn.addEventListener('click', () => selectSkill(btn.dataset.id));
      }});

      document.getElementById('search').addEventListener('input', e => filterSidebar(e.target.value));
    }}

    function filterSidebar(q) {{
      q = q.toLowerCase().trim();
      document.querySelectorAll('.skill-btn').forEach(btn => {{
        const name = (btn.dataset.name || '').toLowerCase();
        const s = skills[btn.dataset.id];
        const body = stripHtml(s.body_html).toLowerCase();
        const scripts = (s.scripts || []).map(sc => sc.name).join(' ').toLowerCase();
        const refs = (s.references || []).map(r => r.name).join(' ').toLowerCase();
        const match = !q || name.includes(q) || body.includes(q) || scripts.includes(q) || refs.includes(q);
        btn.classList.toggle('hidden', !match);
      }});
      document.querySelectorAll('.group-title').forEach(g => {{
        const group = g.dataset.group;
        const ids = groupSkills[group] || [];
        const any = ids.some(id => {{
          const btn = document.querySelector(`.skill-btn[data-id="${{id}}"]`);
          return btn && !btn.classList.contains('hidden');
        }});
        g.classList.toggle('hidden', !any);
      }});
    }}

    function selectSkill(id) {{
      if (!skills[id]) return;
      currentSkillId = id;

      // highlight in sidebar
      document.querySelectorAll('.skill-btn').forEach(btn => btn.classList.toggle('active', btn.dataset.id === id));

      const s = skills[id];
      let html = `<div class="skill-view" data-skill-id="${{id}}">`;

      // header + tabs
      const hasScripts = s.scripts && s.scripts.length > 0;
      const hasRefs = s.references && s.references.length > 0;
      const hasAssets = s.assets && s.assets.length > 0;

      html += `<div class="skill-header">`;
      html += `<h1>${{escapeHtml(s.name)}}</h1>`;
      html += `<div class="path">${{escapeHtml(s.path)}}</div>`;
      html += `<p class="desc">${{escapeHtml(s.description)}}</p>`;
      html += `</div>`;
      html += `<div class="tabs">`;
      html += `<button class="tab active" data-tab="skill" onclick="switchTab('${{id}}', 'skill')">Skill</button>`;
      if (hasScripts) html += `<button class="tab" data-tab="scripts" onclick="switchTab('${{id}}', 'scripts')">Scripts (${{s.scripts.length}})</button>`;
      if (hasRefs) html += `<button class="tab" data-tab="references" onclick="switchTab('${{id}}', 'references')">References (${{s.references.length}})</button>`;
      if (hasAssets) html += `<button class="tab" data-tab="assets" onclick="switchTab('${{id}}', 'assets')">Assets (${{s.assets.length}})</button>`;
      html += `</div>`;

      // body (skill tab)
      html += `<div class="tab-content active" data-skill="${{id}}" data-tab="skill">`;
      html += `<div class="skill-body">${{s.body_html}}</div>`;
      html += `</div>`;

      // scripts tab
      if (hasScripts) {{
        html += `<div class="tab-content hidden" data-skill="${{id}}" data-tab="scripts">`;
        s.scripts.forEach(sc => {{
          html += `<div class="file-box" id="${{sc.id}}" data-toc-level="0">`;
          html += `<div class="file-header">${{escapeHtml(sc.name)}}</div>`;
          if (sc.kind === 'binary') {{
            html += `<pre><code><em>Binary file</em></code></pre>`;
          }} else {{
            const hl = highlightCode(sc.content, getLang(sc.name));
            html += `<pre><code>${{hl}}</code></pre>`;
          }}
          html += `</div>`;
        }});
        html += `</div>`;
      }}

      // references tab
      if (hasRefs) {{
        html += `<div class="tab-content hidden" data-skill="${{id}}" data-tab="references">`;
        s.references.forEach(ref => {{
          html += `<div class="file-box" id="${{ref.id}}" data-toc-level="0">`;
          html += `<div class="file-header">${{escapeHtml(ref.name)}}</div>`;
          if (ref.is_markdown && ref.html) {{
            html += `<div class="rendered-ref">${{ref.html}}</div>`;
          }} else if (ref.kind === 'binary') {{
            html += `<pre><code><em>Binary file</em></code></pre>`;
          }} else {{
            html += `<pre><code>${{escapeHtml(ref.content)}}</code></pre>`;
          }}
          html += `</div>`;
        }});
        html += `</div>`;
      }}

      // assets tab
      if (hasAssets) {{
        html += `<div class="tab-content hidden" data-skill="${{id}}" data-tab="assets">`;
        html += `<ul class="asset-list">`;
        s.assets.forEach(a => {{
          html += `<li>${{escapeHtml(a)}}</li>`;
        }});
        html += `</ul>`;
        html += `</div>`;
      }}

      html += `</div>`;

      document.getElementById('main').innerHTML = html;
      document.getElementById('main').scrollTop = 0;

      buildRightToc();
    }}

    function switchTab(skillId, tabName) {{
      const skillEl = document.querySelector(`.skill-view[data-skill-id="${{skillId}}"]`);
      if (!skillEl) return;
      skillEl.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tabName));
      skillEl.querySelectorAll('.tab-content').forEach(c => {{
        c.classList.toggle('hidden', c.dataset.tab !== tabName);
        c.classList.toggle('active', c.dataset.tab === tabName);
      }});
      buildRightToc();
    }}

    function buildRightToc() {{
      const main = document.getElementById('main');
      const toc = document.getElementById('toc-nav');

      // Find the skill currently in view
      let activeSkill = null;
      document.querySelectorAll('.skill-view').forEach(view => {{
        const rect = view.getBoundingClientRect();
        if (rect.top <= 150 && rect.bottom > 150) activeSkill = view;
      }});

      if (!activeSkill) {{
        toc.innerHTML = '';
        return;
      }}

      const activeTab = activeSkill.querySelector('.tab-content.active');
      if (!activeTab) {{
        toc.innerHTML = '';
        return;
      }}

      const items = activeTab.querySelectorAll('[data-toc-level]');
      let html = '';
      items.forEach(el => {{
        const level = el.dataset.tocLevel || '0';
        const text = el.tagName.startsWith('H') ? el.textContent : (el.querySelector('.file-header')?.textContent || '');
        html += `<a class="toc-link toc-lvl-${{level}}" href="#${{el.id}}">${{escapeHtml(text)}}</a>`;
      }});
      toc.innerHTML = html;

      toc.querySelectorAll('a').forEach(a => {{
        a.addEventListener('click', e => {{
          e.preventDefault();
          const target = document.getElementById(a.getAttribute('href').slice(1));
          if (target) {{
            main.scrollTo({{ top: target.offsetTop - 20, behavior: 'smooth' }});
          }}
        }});
      }});

      updateActiveToc();
    }}

    function updateActiveToc() {{
      const main = document.getElementById('main');
      const links = document.querySelectorAll('#toc-nav .toc-link');

      // Find the skill currently in view
      let activeSkill = null;
      document.querySelectorAll('.skill-view').forEach(view => {{
        const rect = view.getBoundingClientRect();
        if (rect.top <= 150 && rect.bottom > 150) activeSkill = view;
      }});

      let activeId = '';
      if (activeSkill) {{
        const activeTab = activeSkill.querySelector('.tab-content.active');
        if (activeTab) {{
          const items = activeTab.querySelectorAll('[data-toc-level]');
          items.forEach(el => {{
            if (el.offsetTop <= main.scrollTop + 40) {{
              activeId = el.id;
            }}
          }});
        }}
      }}

      links.forEach(a => {{
        a.classList.toggle('active', a.getAttribute('href') === '#' + activeId);
      }});
    }}

    document.getElementById('main').addEventListener('scroll', updateActiveToc);

    function getLang(filename) {{
      const ext = (filename || '').split('.').pop().toLowerCase();
      const map = {{
        py: 'python', js: 'javascript', ts: 'typescript', jsx: 'javascript',
        tsx: 'typescript', sh: 'shell', bash: 'shell', zsh: 'shell',
        json: 'json', yaml: 'yaml', yml: 'yaml', md: 'markdown',
        css: 'css', html: 'html', htm: 'html', xml: 'xml',
        sql: 'sql', rb: 'ruby', go: 'go', rs: 'rust',
        java: 'java', c: 'c', h: 'c', cpp: 'cpp', hpp: 'cpp',
        toml: 'toml', ini: 'ini', cfg: 'ini', txt: 'plain',
      }};
      return map[ext] || 'plain';
    }}

    function getRules(lang) {{
      const R = [];
      const entries = SYNTAX_RULES[lang] || [];
      entries.forEach(e => {{
        R.push({{ re: new RegExp(e.re, e.flags), cls: e.cls }});
      }});
      return R;
    }}

    function highlightCode(code, lang) {{
      if (!code) return '';
      code = escapeHtml(code);
      const rules = getRules(lang);
      if (!rules || !rules.length) return code;

      const reParts = rules.map(r => '(' + r.re.source + ')');
      const combined = new RegExp(reParts.join('|'), 'gm');

      let result = '', lastIdx = 0, m;
      while ((m = combined.exec(code)) !== null) {{
        result += code.slice(lastIdx, m.index);
        let cls = '';
        for (let i = 1; i <= rules.length; i++) {{
          if (m[i] !== undefined) {{ cls = rules[i - 1].cls; break; }}
        }}
        result += '<span class="' + cls + '">' + m[0] + '</span>';
        lastIdx = combined.lastIndex;
      }}
      result += code.slice(lastIdx);
      return result;
    }}

    function escapeHtml(text) {{
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    }}

    function stripHtml(html) {{
      const tmp = document.createElement('div');
      tmp.innerHTML = html;
      return tmp.textContent || tmp.innerText || '';
    }}

    init();
    """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escape_html(title)}</title>
<style>{css}</style>
</head>
<body>
  <aside id="sidebar">
    <header>
      <h1>{escape_html(title)}</h1>
      <p>{sum(len(v) for v in groups.values())} skills loaded</p>
    </header>
    <input id="search" type="text" placeholder="Search skills, scripts, content..." autocomplete="off">
    <nav id="skill-list"></nav>
  </aside>
  <main id="main"></main>
  <aside id="rightbar">
    <header>Contents</header>
    <nav id="toc-nav"></nav>
  </aside>
  <script>{js}</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate an interactive SPA-style HTML dashboard for agent skills."
    )
    parser.add_argument(
        "output",
        nargs="?",
        default=Path(tempfile.gettempdir()) / "skills-visualizer.html",
        type=Path,
        help="Output HTML file path (default: system temp directory)",
    )
    parser.add_argument(
        "--no-open", "-n",
        action="store_true",
        help="Skip opening the generated file in the default browser",
    )
    args = parser.parse_args()

    output: Path = args.output.resolve()

    workspace_skills_dir = Path(".agents/skills").resolve()
    home_skills_dir = Path.home() / ".agents/skills"

    groups: dict[str, list[dict]] = {}
    if workspace_skills_dir.exists():
        groups["Workspace Skills"] = discover_skills(workspace_skills_dir)
    if home_skills_dir.exists():
        groups["User Home Skills"] = discover_skills(home_skills_dir)

    total = sum(len(v) for v in groups.values())
    if total == 0:
        print("No skills found in workspace or home directory.")
        sys.exit(1)

    html = build_html(groups)
    output.write_text(html, encoding="utf-8")
    print(f"✅ Generated {output}")
    print(f"   Workspace: {workspace_skills_dir}  → {len(groups.get('Workspace Skills', []))} skills")
    print(f"   Home:      {home_skills_dir}       → {len(groups.get('User Home Skills', []))} skills")
    print(f"   Total:     {total} skills")

    if not args.no_open:
        file_uri = output.as_uri()
        print(f"\n🌐 Opening {file_uri} ...")
        webbrowser.open(file_uri)
    else:
        print(f"\nOpen {output} in your browser to view.")


if __name__ == "__main__":
    main()

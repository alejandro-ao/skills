# Alejandro Plugins

Claude Code plugin marketplace by Alejandro AO.

## Installation

```bash
/plugin marketplace add alejandro-ao/alejandro-plugins
```

## Available Plugins

### video-tool

AI-powered video processing toolkit.

```bash
/plugin install video-tool@alejandro-plugins
```

**Requires:** `video-tool` CLI installed separately:
```bash
uv tool install git+https://github.com/alejandro-ao/video-tools.git
```

**Features:**
- Download videos from YouTube
- Remove silence, trim, cut, extract segments
- Extract/enhance/replace audio
- Generate transcripts (Whisper)
- Create descriptions and chapter timestamps
- Upload to YouTube or Bunny.net

**Usage:** Just ask Claude naturally - "download this YouTube video", "extract audio from video.mp4", etc.

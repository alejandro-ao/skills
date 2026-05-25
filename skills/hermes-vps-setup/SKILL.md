---
name: hermes-vps-setup
description: Guide a user through setting up Hermes Agent on a freshly purchased VPS. Use this when a user says they bought a VPS and want to run Hermes continuously, set up Hermes Agent, configure a Telegram/Discord gateway, harden the VPS for agent hosting, create backups, or run Hermes as a persistent background service.
---

# Hermes VPS Setup Skill

Use this skill to help a user go from a fresh VPS to a secure, working, continuously running Hermes Agent instance.

The user may be new to VPS administration. Explain each step simply and clearly before doing it. Do not assume they understand Linux, SSH, systemd, firewalling, API keys, or Git deploy keys.

## Core Goal

End with a Hermes Agent instance that:

- Runs on a VPS as an unprivileged user.
- Starts automatically after reboot.
- Is reachable from a messaging platform, usually Telegram.
- Uses the user's chosen LLM provider/model.
- Has browser/search/tooling configured sanely.
- Has logs and health checks.
- Exposes the Hermes dashboard safely through HTTPS and authentication when the user wants web access.
- Has safe Git-based backups for non-secret config and memory.
- Does **not** expose secrets or unsafe services publicly.

## Communication Requirements

As the setup proceeds, always tell the user what you are about to do.

Use short explanations like:

```text
Next I’m going to update system packages and install base tools like git, curl, tmux, Docker, Node.js, and Python support.
```

Before any security-sensitive or irreversible step, explain the risk and ask for confirmation if appropriate.

Examples of steps that deserve explicit explanation:

- SSH hardening.
- Firewall changes.
- Disabling password login.
- Creating deploy keys.
- Installing a systemd service.
- Adding GitHub remotes.
- Starting long-running services.
- Editing files containing credentials.

Keep explanations simple, practical, and non-alarming.

## Setup Phases

Follow these phases in order unless the user asks otherwise.

---

## Phase 1: Inspect the VPS

Explain that you need to identify the OS, current user, sudo access, SSH status, and available resources.

Run checks such as:

```bash
id
whoami
hostnamectl || true
lsb_release -a 2>/dev/null || cat /etc/os-release
sudo -n true && echo SUDO_OK || echo SUDO_NEEDS_PASSWORD
df -h /
free -h
```

Confirm:

- OS distribution/version.
- User has sudo.
- SSH key login exists.
- Disk and RAM are adequate.

If the user is root, recommend creating a non-root admin user first.

---

## Phase 2: Secure the VPS

Explain that security comes first because the agent will run continuously.

Recommended actions:

- Update packages.
- Install basic tools.
- Configure UFW firewall.
- Allow SSH, HTTP, and HTTPS only if needed.
- Enable fail2ban.
- Disable root SSH login.
- Disable password SSH login only after confirming SSH keys work.
- Enable unattended security upgrades.

Typical commands on Ubuntu/Debian:

```bash
sudo apt update
sudo DEBIAN_FRONTEND=noninteractive apt upgrade -y
sudo DEBIAN_FRONTEND=noninteractive apt install -y \
  git curl wget unzip jq tmux htop btop ripgrep build-essential \
  ca-certificates gnupg lsof net-tools ufw fail2ban \
  python3 python3-venv python3-pip python3-dev pipx \
  unattended-upgrades logrotate acl
```

Firewall:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
sudo ufw status verbose
```

Fail2ban:

```bash
sudo tee /etc/fail2ban/jail.d/sshd.local >/dev/null <<'EOF'
[sshd]
enabled = true
backend = systemd
maxretry = 5
findtime = 10m
bantime = 1h
EOF
sudo systemctl enable --now fail2ban
sudo systemctl restart fail2ban
```

SSH hardening drop-in:

```bash
sudo install -d -m 755 /etc/ssh/sshd_config.d
sudo tee /etc/ssh/sshd_config.d/99-agent-vps-hardening.conf >/dev/null <<'EOF'
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
X11Forwarding no
MaxAuthTries 4
ClientAliveInterval 300
ClientAliveCountMax 2
EOF
sudo sshd -t
sudo systemctl reload ssh || sudo systemctl reload sshd
```

Do not disable password SSH if no authorized key exists.

---

## Phase 3: Install Runtime Dependencies

Explain that Hermes needs Python, Node.js, browser dependencies, and sometimes Docker.

Install Docker, Compose, Node.js/npm, ffmpeg, and browser dependencies:

```bash
sudo DEBIAN_FRONTEND=noninteractive apt install -y \
  docker.io docker-compose-v2 nodejs npm ffmpeg \
  libnss3 libnspr4 libatk-bridge2.0-0 libatk1.0-0 libcups2 \
  libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
  libxrandr2 libgbm1 libasound2t64 libpangocairo-1.0-0 \
  libpango-1.0-0 libcairo2 fonts-liberation fonts-noto-color-emoji
sudo systemctl enable --now docker
```

On some newer Ubuntu versions, Playwright may not officially recognize the OS. If needed, use:

```bash
PLAYWRIGHT_HOST_PLATFORM_OVERRIDE=ubuntu24.04-x64 npx playwright install chromium
```

Only use this workaround when the normal Playwright install refuses the OS version.

---

## Phase 4: Create Agent User and Directories

Explain that Hermes should not run as root.

Create an unprivileged user and standard paths:

```bash
if ! id agentuser >/dev/null 2>&1; then
  sudo adduser --disabled-password --gecos "Agent Runtime User" agentuser
fi
sudo usermod -aG docker agentuser
sudo mkdir -p /opt/agents /var/lib/agents /var/log/agents /etc/agents /var/backups/agents
sudo chown -R agentuser:agentuser /opt/agents /var/lib/agents /var/log/agents /var/backups/agents
sudo chown root:agentuser /etc/agents
sudo chmod 750 /etc/agents /opt/agents /var/lib/agents /var/log/agents /var/backups/agents
```

---

## Phase 5: Install Hermes as `agentuser`

Explain that Hermes will live under `/home/agentuser/.hermes`.

Install Hermes:

```bash
sudo -H -u agentuser bash -lc 'curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash -s -- --skip-browser'
```

Then install Chromium for Playwright:

```bash
sudo -H -u agentuser bash -lc 'cd /home/agentuser/.hermes/hermes-agent && npx playwright install chromium'
```

If that fails on a newer Ubuntu version:

```bash
sudo -H -u agentuser bash -lc 'cd /home/agentuser/.hermes/hermes-agent && PLAYWRIGHT_HOST_PLATFORM_OVERRIDE=ubuntu24.04-x64 npx playwright install chromium'
```

Verify:

```bash
sudo -H -u agentuser bash -lc 'export PATH="$HOME/.local/bin:$PATH"; hermes version; hermes doctor'
```

---

## Phase 6: Run Hermes Setup Wizard

Explain to the user that this wizard configures the model, agent settings, messaging, and tools.

Run:

```bash
sudo -H -u agentuser bash -lc 'export PATH="$HOME/.local/bin:$PATH"; hermes setup'
```

Recommended choices for a simple VPS setup:

- Terminal backend: `Local` or `Keep current (local)`.
- Max iterations: `90` for general-purpose use, or `60` to reduce cost.
- Tool progress display: `new`.
- Compression threshold:
  - `0.75` for normal context models.
  - `0.85` for very large context models, e.g. ~200k tokens.
- Session reset: `Inactivity + daily reset`.
- Inactivity timeout: `1440` minutes unless the user has a reason to change it.
- Messaging: Telegram is usually easiest.
- Telegram home channel: use the same Telegram user ID for DM use.
- Browser: `Local Browser`.
- Web search: start with free/no-key search if available; use paid/self-hosted providers later.

Tell the user to create a Telegram bot with `@BotFather` and to get their numeric Telegram user ID from `@userinfobot`.

Always recommend allowlisting the user's Telegram ID. Do not recommend open access.

---

## Phase 7: Install Hermes Gateway as a System Service

Explain that the gateway is the long-running process that listens to Telegram/Discord/etc. and runs cron jobs.

Install the official Hermes systemd service:

```bash
printf 'n\ny\n' | sudo env \
  HOME=/home/agentuser \
  HERMES_HOME=/home/agentuser/.hermes \
  PATH=/home/agentuser/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  /home/agentuser/.local/bin/hermes gateway install --system --run-as-user agentuser --force
```

Start it:

```bash
sudo systemctl start hermes-gateway.service
sudo systemctl enable hermes-gateway.service
```

Verify:

```bash
sudo systemctl status hermes-gateway.service
sudo -H -u agentuser bash -lc 'export PATH="$HOME/.local/bin:$PATH"; hermes gateway status'
sudo journalctl -u hermes-gateway.service -n 100 --no-pager
```

If Telegram says `Chat not found`, tell the user to open the Telegram bot and send:

```text
/start
```

Then test by messaging the bot.

---

## Phase 8: Protected Hermes Dashboard

Explain that `hermes dashboard` contains sensitive configuration, sessions, logs, and API-key management. Never expose it with `--host 0.0.0.0 --insecure` directly.

Recommended default:

- Run the dashboard as a `systemd` service bound only to `127.0.0.1:9119`.
- Put Caddy in front on ports `80`/`443`.
- Protect Caddy with Basic Auth.
- Use a real domain/subdomain for trusted Let's Encrypt HTTPS when available.
- If no domain is available yet, use a temporary self-signed certificate for the VPS IP and tell the user the browser will show a certificate warning until DNS is configured.

If an insecure dashboard is already running, stop it first:

```bash
sudo pkill -u agentuser -f '/hermes dashboard' || true
sudo pkill -u agentuser -f 'hermes dashboard --host' || true
```

Install Caddy:

```bash
sudo apt update
sudo DEBIAN_FRONTEND=noninteractive apt install -y caddy
```

Create the dashboard service:

```bash
sudo tee /etc/systemd/system/hermes-dashboard.service >/dev/null <<'EOF'
[Unit]
Description=Hermes Agent Dashboard - local backend for protected reverse proxy
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=agentuser
Group=agentuser
Environment=HOME=/home/agentuser
Environment=HERMES_HOME=/home/agentuser/.hermes
Environment=PATH=/home/agentuser/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
WorkingDirectory=/home/agentuser/.hermes
ExecStart=/home/agentuser/.local/bin/hermes dashboard --host 127.0.0.1 --port 9119 --no-open --skip-build
Restart=always
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF
```

Generate Basic Auth credentials and save them root-only:

```bash
DASH_USER="hermes"
DASH_PASS="$(openssl rand -base64 24 | tr -d '\n')"
DASH_HASH="$(caddy hash-password --plaintext "$DASH_PASS")"
sudo install -d -m 700 /root/hermes-dashboard
printf 'username: %s\npassword: %s\n' "$DASH_USER" "$DASH_PASS" | sudo tee /root/hermes-dashboard/credentials.txt >/dev/null
sudo chmod 600 /root/hermes-dashboard/credentials.txt
```

### Preferred Caddy config when the user has a domain

Ask the user for a subdomain such as `hermes.example.com`, and confirm its DNS A/AAAA record points to the VPS. Then write:

```bash
DASH_DOMAIN="hermes.example.com" # replace with the user's domain
sudo tee /etc/caddy/Caddyfile >/dev/null <<EOF
${DASH_DOMAIN} {
  basicauth {
    ${DASH_USER} ${DASH_HASH}
  }

  reverse_proxy 127.0.0.1:9119 {
    # Hermes validates the Host header against the dashboard bind host.
    header_up Host 127.0.0.1:9119
  }

  header {
    Strict-Transport-Security "max-age=31536000; includeSubDomains"
    X-Content-Type-Options "nosniff"
    X-Frame-Options "DENY"
    Referrer-Policy "no-referrer"
  }
}
EOF
```

Caddy will automatically request and renew a trusted Let's Encrypt certificate.

### Temporary Caddy config without a domain

Only use this until DNS is available. It is encrypted, but browsers will warn because the cert is self-signed.

```bash
PUBLIC_IP="$(curl -fsS https://api.ipify.org)"
sudo install -d -m 750 -o root -g caddy /etc/caddy/certs
sudo openssl req -x509 -nodes -newkey rsa:2048 -days 825 \
  -keyout /etc/caddy/certs/hermes-dashboard.key \
  -out /etc/caddy/certs/hermes-dashboard.crt \
  -subj "/CN=${PUBLIC_IP}" \
  -addext "subjectAltName=IP:${PUBLIC_IP},DNS:localhost,IP:127.0.0.1"
sudo chown root:caddy /etc/caddy/certs/hermes-dashboard.key /etc/caddy/certs/hermes-dashboard.crt
sudo chmod 640 /etc/caddy/certs/hermes-dashboard.key
sudo chmod 644 /etc/caddy/certs/hermes-dashboard.crt

sudo tee /etc/caddy/Caddyfile >/dev/null <<EOF
:80 {
  redir https://{host}{uri} permanent
}

:443 {
  tls /etc/caddy/certs/hermes-dashboard.crt /etc/caddy/certs/hermes-dashboard.key

  basicauth {
    ${DASH_USER} ${DASH_HASH}
  }

  reverse_proxy 127.0.0.1:9119 {
    # Hermes validates the Host header against the dashboard bind host.
    header_up Host 127.0.0.1:9119
  }

  header {
    Strict-Transport-Security "max-age=31536000; includeSubDomains"
    X-Content-Type-Options "nosniff"
    X-Frame-Options "DENY"
    Referrer-Policy "no-referrer"
  }
}
EOF
```

Enable and verify:

```bash
sudo caddy fmt --overwrite /etc/caddy/Caddyfile
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl daemon-reload
sudo systemctl enable --now hermes-dashboard.service
sudo systemctl enable --now caddy
sudo systemctl reload caddy
sudo ss -ltnp | grep -E ':(80|443|9119)\\b' || true
sudo -H -u agentuser bash -lc 'export PATH="$HOME/.local/bin:$PATH"; hermes dashboard --status || true'
```

Expected result:

- Caddy listens publicly on `80` and `443`.
- Hermes listens only on `127.0.0.1:9119`.
- Unauthenticated HTTPS returns `401`.
- Authenticated HTTPS returns `200`.

Never add a firewall rule for port `9119`; only `80`/`443` should be public.

---

## Phase 9: Backups

Explain that secrets should not go into Git.

Recommended tracked files:

```text
/home/agentuser/.hermes/config.yaml
/home/agentuser/.hermes/SOUL.md
/home/agentuser/.hermes/cron/
/home/agentuser/.hermes/memories/
/home/agentuser/.hermes/skills/
```

Optional:

```text
/home/agentuser/.hermes/sessions/
```

Never track:

```text
/home/agentuser/.hermes/.env
logs/
cache/
audio_cache/
image_cache/
gateway_state.json
gateway.lock
gateway.pid
auth.lock
hermes-agent/
node_modules/
```

Create backup repo:

```bash
sudo -H -u agentuser bash -lc 'mkdir -p /home/agentuser/hermes-backup && cd /home/agentuser/hermes-backup && git init && git branch -M main'
```

Create a sync script at:

```text
/home/agentuser/hermes-backup/sync-hermes-backup.sh
```

Script:

```bash
#!/usr/bin/env bash
set -euo pipefail

SRC="/home/agentuser/.hermes"
DST="/home/agentuser/hermes-backup"

mkdir -p "$DST"

rsync -a --delete \
  --exclude=".env" \
  --exclude="auth.lock" \
  --exclude="gateway.lock" \
  --exclude="gateway.pid" \
  --exclude="gateway_state.json" \
  --exclude="channel_directory.json" \
  --exclude="logs/" \
  --exclude="audio_cache/" \
  --exclude="image_cache/" \
  --exclude="cache/" \
  --exclude="hermes-agent/" \
  --exclude="node_modules/" \
  --exclude="__pycache__/" \
  "$SRC/config.yaml" \
  "$SRC/SOUL.md" \
  "$SRC/cron" \
  "$SRC/memories" \
  "$SRC/skills" \
  "$DST/"

cd "$DST"
git add .
if ! git diff --cached --quiet; then
  git commit -m "Hermes backup: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
else
  echo "No Hermes backup changes to commit."
fi

if git remote get-url origin >/dev/null 2>&1; then
  git push
fi
```

Create hourly systemd timer:

```bash
sudo tee /etc/systemd/system/hermes-git-backup.service >/dev/null <<'EOF'
[Unit]
Description=Sync selected Hermes state/config into local Git backup

[Service]
Type=oneshot
User=agentuser
Group=agentuser
WorkingDirectory=/home/agentuser/hermes-backup
ExecStart=/home/agentuser/hermes-backup/sync-hermes-backup.sh
EOF

sudo tee /etc/systemd/system/hermes-git-backup.timer >/dev/null <<'EOF'
[Unit]
Description=Hourly Hermes Git backup

[Timer]
OnCalendar=hourly
Persistent=true
RandomizedDelaySec=5m

[Install]
WantedBy=timers.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now hermes-git-backup.timer
```

For GitHub remote backups, create a dedicated deploy key:

```bash
sudo -H -u agentuser ssh-keygen -t ed25519 -C "hermes backup deploy key" -f /home/agentuser/.ssh/hermes_backup_deploy_key -N ""
```

Give the public key to the user and ask them to add it to GitHub as a deploy key with write access.

Configure SSH host alias and remote:

```bash
sudo -H -u agentuser bash -lc 'cat >> ~/.ssh/config <<EOF
Host github.com-hermes-backup
  HostName github.com
  User git
  IdentityFile ~/.ssh/hermes_backup_deploy_key
  IdentitiesOnly yes
EOF
ssh-keyscan -H github.com >> ~/.ssh/known_hosts
'
```

Then add remote:

```bash
sudo -H -u agentuser bash -lc 'cd /home/agentuser/hermes-backup && git remote add origin git@github.com-hermes-backup:OWNER/REPO.git && git push -u origin main'
```

---

## Phase 10: Health Checks and Final Verification

Run:

```bash
sudo -H -u agentuser bash -lc 'export PATH="$HOME/.local/bin:$PATH"; hermes doctor'
sudo -H -u agentuser bash -lc 'export PATH="$HOME/.local/bin:$PATH"; hermes gateway status'
systemctl is-enabled hermes-gateway.service
systemctl is-active hermes-gateway.service
systemctl list-timers hermes-git-backup.timer --no-pager
sudo journalctl -u hermes-gateway.service -n 100 --no-pager
```

A good final state:

- `hermes-gateway.service` is active.
- `hermes-gateway.service` is enabled.
- Telegram or chosen messaging platform is connected.
- LLM provider connectivity works.
- Browser engine is installed.
- Backup timer is active.
- No secrets are tracked in Git.

Some `hermes doctor` warnings may be acceptable if they are for unused optional tools, such as Discord, xAI, Spotify, Home Assistant, or OpenRouter when the user is not using those.

---

## Phase 11: First Message to Hermes

After the bot works, help the user send a first message that teaches Hermes about the VPS.

Template:

```text
You are running as Hermes Agent on my dedicated Ubuntu VPS.

Important setup details:

- You run as the Linux user `agentuser`.
- Your Hermes home/config/data directory is `/home/agentuser/.hermes`.
- Your code is installed at `/home/agentuser/.hermes/hermes-agent`.
- You run continuously through the systemd service `hermes-gateway.service`.
- Your web dashboard runs through `hermes-dashboard.service`, bound locally to `127.0.0.1:9119` and exposed only through the protected reverse proxy.
- I talk to you through Telegram.
- This VPS is intended to be a long-running agent host.
- A local Git backup repo exists at `/home/agentuser/hermes-backup`.
- Selected Hermes config/state is synced by `hermes-git-backup.timer`.
- The backup tracks `config.yaml`, `SOUL.md`, `cron/`, `memories/`, and `skills/`.
- The backup intentionally does not track `.env`, logs, caches, auth files, gateway lock/state files, or raw secrets.
- Do not expose secrets, API keys, tokens, or `.env` contents.
- Do not commit secrets to Git.
- Important Hermes files are in `/home/agentuser/.hermes`.
- Long-term memories should go into your persistent memory system, not just chat context.
- If you make durable changes to config, memory, skills, cron jobs, or SOUL.md, remind me that they will be picked up by the Git backup timer, or tell me to run `/home/agentuser/hermes-backup/sync-hermes-backup.sh` manually if we need an immediate snapshot.
- Prefer safe, reversible changes. Ask before modifying SSH, firewall, systemd services, package managers, or anything security-sensitive.
- If a task involves files, explain which paths you plan to read or change before doing it.
- If you need to run shell commands, summarize the command and risk first.

Your operating principles on this VPS:

1. Be useful, but cautious.
2. Preserve my data and configuration.
3. Keep secrets private.
4. Prefer minimal, maintainable setup over unnecessary complexity.
5. When uncertain, ask before taking irreversible or security-sensitive action.
6. Keep notes/memory about durable preferences and infrastructure facts.

Please acknowledge this setup, save the important durable facts to memory, and ask me what I would like you to work on first.
```

Customize this with the user's actual model, messaging platform, GitHub repo, and backup schedule.

---

## Minimalism Principle

Prefer the smallest working setup:

- One messaging platform first, usually Telegram.
- One LLM provider/model.
- Local browser.
- Local terminal backend.
- Git backup for non-secret durable state.
- No optional integrations unless the user asks for them.

Do not install or enable extra platforms such as Discord, Slack, Spotify, Home Assistant, Firecrawl self-hosted, SearXNG, or databases unless the user explicitly wants them.

---

## Completion Message

At the end, summarize clearly:

- What was installed.
- Where Hermes lives.
- How it runs.
- How to check logs.
- How to restart it.
- How backups work.
- What the user should do next.

Example:

```text
Hermes is now running as `agentuser` on this VPS. The systemd service is `hermes-gateway.service`, it starts at boot, Telegram is connected, MiniMax/OpenRouter/etc. is configured, and selected Hermes state is backed up to Git hourly without committing secrets.
```

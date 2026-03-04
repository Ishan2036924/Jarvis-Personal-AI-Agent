# Jarvis — Personal AI Assistant on OpenClaw

A production-grade, 24/7 personal AI assistant built on [OpenClaw](https://github.com/openclaw/openclaw), deployed on DigitalOcean and accessible via Telegram. Jarvis takes real actions — sends emails, manages your calendar, tracks expenses, logs habits, searches the web — not just generates text.

> **Key insight from this build:** The biggest reliability problem with AI agents is "faking" — cheaper LLMs claim to execute tools without actually doing so. This repo documents what worked, what didn't, and why model selection matters more than prompt engineering for agentic systems.

---
## Table of Contents

| # | Section |
|---|---|
| 1 | [What It Can Do](#what-it-can-do) |
| 2 | [Stack](#stack) |
| 3 | [Architecture](#architecture) |
| 4 | [Project Structure](#project-structure) |
| 5 | [End-to-End Setup Guide](#end-to-end-setup-guide) |
| 5.1 | &nbsp;&nbsp;[Phase 0 — Server Setup](#phase-0--server-setup) |
| 5.2 | &nbsp;&nbsp;[Phase 1 — Google Workspace](#phase-1--google-workspace) |
| 5.3 | &nbsp;&nbsp;[Phase 2 — Identity Files](#phase-2--identity-files) |
| 5.4 | &nbsp;&nbsp;[Phase 3 — Environment Variables](#phase-3--environment-variables) |
| 5.5 | &nbsp;&nbsp;[Phase 4 — Automation (Cron Jobs)](#phase-4--automation-cron-jobs) |
| 6 | [Common Issues & Fixes](#common-issues--fixes) |
| 7 | [Model Selection — What We Learned](#model-selection--what-we-learned) |
| 8 | [Monthly Cost](#monthly-cost) |
| 9 | [Why a Server? (And Alternatives)](#why-a-server-and-alternatives) |
| 10 | [Extending Jarvis — What You Can Add](#extending-jarvis--what-you-can-add) |
| 11 | [Future Roadmap](#future-roadmap) |
| 12 | [Built By](#built-by) |
---

## What It Can Do

| Category | Capabilities |
|---|---|
| **Gmail** | Send/read/search/reply/forward emails + file attachments |
| **Calendar** | List/create/update events, conflict detection |
| **Drive** | List/search/read/download/upload files |
| **Notion** | Tasks, expenses, habits, contacts, job tracking |
| **Web Search** | Brave Search API (2,000 free/month) |
| **Weather** | Open-Meteo API (free, no key needed) |
| **Places** | Google Places API — find nearby locations |
| **Voice** | OpenAI Whisper transcription |
| **PDF** | Generate formatted PDF reports |
| **Memory** | Persistent facts across sessions |
| **Automation** | Morning briefing, weekly review, nightly journal (cron) |

---

## Stack

| Component | Choice | Why |
|---|---|---|
| Framework | OpenClaw (Node.js) | 180K+ stars, Telegram-native, skill system |
| Server | DigitalOcean 4GB / 2vCPU / Ubuntu 24.04 | $24/mo, production minimum |
| Primary LLM | Grok 4.1 Fast | Best tool-calling reliability at $0.20/$0.50 per 1M tokens |
| Backup LLM | Claude Sonnet 4.5 | Complex cron jobs, multi-step chains |
| Interface | Telegram | Push notifications, voice, always available |
| Memory | SQLite hybrid (BM25 + vector) | Built into OpenClaw, no external DB needed |
| Email sending | Custom Python (Gmail API) | gog CLI cannot send attachments — this is non-negotiable |

---

## Architecture

```
You (Telegram)
  → OpenClaw Gateway (127.0.0.1:18789)
    → Session Manager (loads conversation history)
      → Agent Runtime (builds prompt from IDENTITY.md + SOUL.md + MEMORY.md)
        → LLM (Grok 4.1 Fast)
          → Tool Execution (jarvis gmail / calendar / notion / etc.)
            → Result captured as JSON
              → LLM composes response
                → Telegram delivers to you
```

All custom tools are Python scripts called via a `jarvis` bash wrapper. The LLM calls them through OpenClaw's exec tool.

---

## Project Structure

```
~/.openclaw/workspace/
├── IDENTITY.md              # Tool commands + agent contract rules (private)
├── SOUL.md                  # Personality + security rules (private)
├── USER.md                  # Your personal info (private)
├── MEMORY.md                # Persistent facts (private)
├── IDENTITY.example.md      # Template — copy to IDENTITY.md
├── SOUL.example.md          # Template — copy to SOUL.md
├── USER.example.md          # Template — copy to USER.md
├── skills/gmail-full/
│   ├── gmail_tool.py        # Gmail send/read/search/reply/forward/attach
│   ├── calendar_tool.py     # Google Calendar CRUD
│   ├── notion_tool.py       # Notion tasks/expenses/habits/contacts/jobs
│   ├── drive_tool.py        # Google Drive read/write/upload/download
│   ├── memory_tool.py       # Persistent memory save/read/search
│   ├── weather_tool.py      # Open-Meteo weather
│   ├── places_tool.py       # Google Places API
│   ├── pdf_tool.py          # PDF generation
│   ├── reminder_tool.py     # One-shot cron reminders
│   └── whisper_tool.py      # Voice transcription
```

---

## End-to-End Setup Guide

### Prerequisites
- DigitalOcean account
- Google account (Gmail, Calendar, Drive)
- Telegram account
- GitHub Student Pack (optional — gives $200 DO credits)

---

### Phase 0 — Server Setup

**1. Provision droplet**
- Ubuntu 24.04 LTS, 4GB RAM / 2vCPU minimum ($24/mo)
- Region: closest to you
- SSH key authentication only

**2. Initial hardening**
```bash
# SSH in as root, then:
apt update && apt upgrade -y

# Create dedicated user — never run agents as root
adduser clawuser
usermod -aG sudo clawuser
rsync --archive --chown=clawuser:clawuser ~/.ssh /home/clawuser

# Disable root login + password auth
sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart ssh

# Firewall
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 443/tcp
ufw enable

# Fail2Ban
apt install fail2ban -y
systemctl enable fail2ban --now

# Swap (safety net)
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

**3. Install dependencies**
```bash
su - clawuser

# Node.js 22
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt-get install -y nodejs build-essential

# Python 3 + venv
sudo apt install -y python3 python3-pip python3-venv

# OpenClaw
sudo npm install -g openclaw@latest
openclaw --version
```

**4. Configure OpenClaw**
```bash
openclaw  # interactive setup
# Choose: local gateway, Telegram channel, your LLM provider + API key

# Lock permissions
chmod 700 ~/.openclaw
chmod 600 ~/.openclaw/openclaw.json
```

**5. Systemd service**
```bash
sudo nano /etc/systemd/system/openclaw.service
```
```ini
[Unit]
Description=OpenClaw AI Gateway
After=network.target

[Service]
Type=simple
User=clawuser
WorkingDirectory=/home/clawuser
EnvironmentFile=/home/clawuser/.openclaw/.env
ExecStart=/usr/bin/openclaw gateway --port 18789 --bind loopback
Restart=always
RestartSec=10
MemoryMax=3G

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl daemon-reload
sudo systemctl enable openclaw --now
sudo loginctl enable-linger clawuser
```

**6. Lock Telegram to your account only**

Get your numeric ID from [@userinfobot](https://t.me/userinfobot) on Telegram, then add to `openclaw.json`:
```json
{
  "channels": {
    "telegram": {
      "dmPolicy": "allowlist",
      "allowFrom": ["YOUR_NUMERIC_TELEGRAM_USER_ID"]
    }
  }
}
```

---

### Phase 1 — Google Workspace

**1. GCP Setup (do this on your laptop)**
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create project → Enable: Gmail API, Calendar API, Drive API
3. OAuth Consent Screen: External, add your email as test user
4. **Important:** Publish the app (Testing → Production) to avoid 7-day token expiry
5. Create OAuth 2.0 Client ID → Desktop App → Download `credentials.json`

**2. Generate token (laptop — needs browser)**
```python
# generate_token.py — run on your laptop
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/drive.readonly',
]

flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
creds = flow.run_local_server(port=0)
with open('token.json', 'w') as f:
    f.write(creds.to_json())
print("Done. SCP token.json + credentials.json to server.")
```

**Important:** Always include ALL scopes when generating tokens. Missing even one scope causes silent failures for that service.

**3. Transfer to server**
```bash
scp credentials.json token.json clawuser@YOUR_SERVER_IP:~/.openclaw/certs/google/
```

**4. Python environment**
```bash
cd /home/clawuser
python3 -m venv gmail-env
source gmail-env/bin/activate
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

**5. Install tool scripts**
```bash
mkdir -p ~/.openclaw/workspace/skills/gmail-full/
# Copy all .py files from this repo to the above directory
```

**6. Create jarvis wrapper**
```bash
sudo nano /usr/local/bin/jarvis
```
```bash
#!/bin/bash
PYTHON=/home/clawuser/gmail-env/bin/python3
SKILLS=/home/clawuser/.openclaw/workspace/skills/gmail-full

case "$1" in
  gmail)    shift; $PYTHON $SKILLS/gmail_tool.py "$@" ;;
  calendar) shift; $PYTHON $SKILLS/calendar_tool.py "$@" ;;
  notion)   shift; $PYTHON $SKILLS/notion_tool.py "$@" ;;
  drive)    shift; $PYTHON $SKILLS/drive_tool.py "$@" ;;
  memory)   shift; $PYTHON $SKILLS/memory_tool.py "$@" ;;
  weather)  shift; $PYTHON $SKILLS/weather_tool.py "$@" ;;
  places)   shift; $PYTHON $SKILLS/places_tool.py "$@" ;;
  pdf)      shift; $PYTHON $SKILLS/pdf_tool.py "$@" ;;
  remind)   shift; $PYTHON $SKILLS/reminder_tool.py "$@" ;;
  whisper)  shift; $PYTHON $SKILLS/whisper_tool.py "$@" ;;
  log_job)  shift; $PYTHON $SKILLS/notion_tool.py log_job "$@" ;;
  query_jobs) shift; $PYTHON $SKILLS/notion_tool.py query_jobs "$@" ;;
  health)   free -h && df -h && sudo systemctl status openclaw --no-pager ;;
  *) echo "Unknown command: $1" ;;
esac
```
```bash
sudo chmod +x /usr/local/bin/jarvis
```

---

### Phase 2 — Identity Files

Copy the example files and fill in your details:
```bash
cp IDENTITY.example.md IDENTITY.md
cp SOUL.example.md SOUL.md
cp USER.example.md USER.md
```

Edit each file — replace all `YOUR_*` placeholders with real values.

---

### Phase 3 — Environment Variables

```bash
nano ~/.openclaw/.env
```
```
XAI_API_KEY=your_grok_api_key
ANTHROPIC_API_KEY=your_claude_api_key
NOTION_API_KEY=your_notion_integration_key
BRAVE_API_KEY=your_brave_search_key
GOOGLE_MAPS_API_KEY=your_google_maps_key
OPENAI_API_KEY=your_openai_key  # for Whisper only
```

---

### Phase 4 — Automation (Cron Jobs)

**Morning briefing at 7:30 AM:**
```bash
openclaw cron add --json '{
  "name": "morning-briefing",
  "schedule": {"kind": "cron", "expr": "30 7 * * *"},
  "timezone": "America/New_York",
  "sessionTarget": "isolated",
  "payload": {
    "kind": "agentTurn",
    "deliver": true,
    "channel": "telegram",
    "to": "YOUR_TELEGRAM_CHAT_ID",
    "message": "Morning Briefing: 1) Calendar today 2) Unread important emails 3) Boston weather 4) Top tasks due today"
  }
}'
```

---

## Common Issues & Fixes

| Issue | Cause | Fix |
|---|---|---|
| Email attachments fail | gog CLI has no `--attach` flag | Use `gmail_tool.py` directly — never gog for sending |
| OAuth token expires after 7 days | GCP project in "Testing" mode | Publish app to Production in GCP console |
| Token scope errors (403) | Token generated with incomplete scopes | Regenerate token with ALL 5 scopes |
| LLM says "Done" but nothing saved | Model faking tool calls | Switch to Grok 4.1 Fast or Claude Sonnet — verify server-side |
| Wrong timezone on server | System timezone not set | `sudo timedatectl set-timezone America/New_York` |
| Gateway not starting | Config validation error | Run `openclaw doctor --deep --yes` |
| Bot responds to everyone | dmPolicy not set | Add `allowFrom` with your numeric Telegram user ID |
| Session memory lost after restart | Normal behavior | Long-term facts go in `MEMORY.md`, not session history |

---

## Model Selection — What We Learned

| Model | Tool Calling | Cost | Verdict |
|---|---|---|---|
| GPT-4.1-mini | ❌ Fakes 30% | $0.40/$1.60 | Not reliable |
| Claude Haiku 4.5 | ❌ Fakes after /reset | $1/$5 | Unreliable |
| o3-mini | ❌ Fakes tool calls | $1.10/$4.40 | Reasoning ≠ doing |
| GPT-4o | ✅ 95% reliable | $2.50/$10 | Works, expensive |
| Claude Sonnet 4.5 | ✅ 97% reliable | $3/$15 | Best, expensive |
| **Grok 4.1 Fast** | **✅ 95%+ reliable** | **$0.20/$0.50** | **Winner** |

**The lesson:** For AI agents, pick models known for tool-calling reliability, not benchmark scores. Reasoning ability and execution reliability are different skills.

---

## Monthly Cost

| Item | Cost |
|---|---|
| DigitalOcean 4GB droplet | $24 |
| Grok 4.1 Fast (daily use) | ~$4-5 |
| Claude Sonnet 4.5 (crons only) | ~$5-7 |
| Google APIs | $0 (free tier) |
| Brave Search | $0 (2,000/month free) |
| Open-Meteo weather | $0 |
| **Total** | **~$33-36/month** |

---

## Why a Server? (And Alternatives)

Running Jarvis on a cloud server vs your laptop is a fundamental architectural choice:

| | Cloud Server (Recommended) | Local Machine | Raspberry Pi |
|---|---|---|---|
| **Uptime** | 24/7, always on | Only when laptop is open | 24/7 but limited RAM |
| **Push notifications** | ✅ Morning briefing arrives while you sleep | ❌ Laptop must be awake | ✅ |
| **Cost** | $24/mo | $0 extra | ~$80 one-time |
| **Setup complexity** | Medium | Low | High |
| **Best for** | Production use | Testing/dev | Budget builds |

**Alternative hosting options:**

| Provider | Cost | Notes |
|---|---|---|
| DigitalOcean (used here) | $24/mo (4GB) | Best DO for single user |
| AWS EC2 t3.medium | ~$30/mo | Free tier only 1GB — too small |
| Google Cloud e2-medium | ~$26/mo | Similar to DO |
| Hetzner CX21 | ~$6/mo | Cheapest option, EU-based, 4GB |
| Raspberry Pi 4 (4GB) | $80 one-time | No internet cost, home only |
| Your own VPS | Varies | Full control |

**Minimum specs regardless of provider:** 2GB RAM, 2 vCPU, Ubuntu 22.04+. 1GB will OOM when running OpenClaw + Python tools simultaneously.

---

## Extending Jarvis — What You Can Add

### 1. Additional Python Tools (Easiest)
Add any Python script as a new tool in 3 steps:
1. Create `your_tool.py` in `skills/gmail-full/`
2. Add a case in the `jarvis` wrapper: `newtool) shift; $PYTHON $SKILLS/your_tool.py "$@" ;;`
3. Add the command to `IDENTITY.md` so the LLM knows when to use it

**Ideas to build:**
- `spotify_tool.py` — control playback via Spotify API
- `github_tool.py` — list PRs, issues, CI status
- `linkedin_tool.py` — draft and post content
- `news_tool.py` — fetch and summarize RSS feeds
- `stocks_tool.py` — portfolio tracking via Yahoo Finance
- `sleep_tool.py` — log sleep data from Apple Health export
- `anki_tool.py` — create flashcards from notes

### 2. MCP Servers (Medium)
OpenClaw supports MCP via the `mcporter` skill. Any MCP server becomes a tool:
```bash
clawhub install mcporter
# Add to workspace mcporter config:
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {"GITHUB_TOKEN": "your_token"}
    }
  }
}
```
Browse available MCP servers: [modelcontextprotocol.io](https://modelcontextprotocol.io)

**Note:** MCP adds ~2.4s cold-start latency per call. Use native Python tools for anything latency-sensitive.

### 3. Additional Channels (Medium)
OpenClaw supports multiple channels simultaneously. Add to `openclaw.json`:
- **Discord** — useful for group/shared assistant
- **WhatsApp** — broader reach
- **Web UI via Tailscale** — desktop access without exposing to internet
- **Email webhooks** — trigger agent on incoming email

### 4. Specialized Sub-Agents (Advanced)
Run multiple agents from one Gateway, each with a different model and workspace:
```json
{
  "agents": {
    "list": [
      {"id": "main", "workspace": "~/.openclaw/workspace", "model": "xai/grok-4-1-fast"},
      {"id": "researcher", "workspace": "~/.openclaw/workspace-research", "model": "anthropic/claude-sonnet-4-5"},
      {"id": "writer", "workspace": "~/.openclaw/workspace-writer", "model": "openai/gpt-4o"}
    ]
  }
}
```
Route by channel or keyword. Each agent has its own memory, skills, and personality.

### 5. LangGraph Integration (Advanced)
Expose LangGraph workflows as HTTP services and call them as OpenClaw skills:
```bash
# In IDENTITY.md, teach the agent:
# For deep research: curl -X POST http://localhost:8000/research/invoke -d '{"query": "..."}'
```
This lets you build complex multi-step workflows (research → analyze → write → review) while keeping Jarvis as the user-facing interface.

---

## Future Roadmap

| Feature | Complexity | Notes |
|---|---|---|
| Email draft confirmation before sending | Low | Add "Send this? [Yes/Edit/Cancel]" flow |
| Inline Telegram buttons | Low | Native grammY keyboard support |
| Image generation | Low | Grok image gen ($0.02/image) or `clawhub install nano-banana-pro` |
| Real-time email notifications | Medium | Gmail Pub/Sub → OpenClaw webhook |
| LinkedIn/Twitter posting | Medium | Custom Python script via their APIs |
| Resume builder | Medium | python-pptx + MEMORY.md profile data |
| Voice output | Medium | ElevenLabs or Grok Voice API |
| GitHub integration | Medium | MCP server: `@modelcontextprotocol/server-github` |
| Smart Home | Medium | Philips Hue: `clawhub install openhue` |
| Multi-agent routing | Advanced | Researcher + Writer + Coder agents |
| PostgreSQL/pgvector memory | Advanced | Replace SQLite when facts exceed ~10,000 |
| Auto-apply to jobs | Advanced | Phase 2 — Greenhouse/Lever API + cover letter gen |
| LangGraph orchestration | Advanced | Complex multi-step workflows as HTTP services |

---

## Built By

**Ishan Srivastava** — MS Applied AI, Northeastern University  
Former AI/ML Engineer at TCS (4+ years)  
[GitHub](https://github.com/Ishan2036924) | [LinkedIn](https://www.linkedin.com/in/ishan-srivastava-7742b121a/)



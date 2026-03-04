# Jarvis — Personal AI Assistant on OpenClaw

A production-grade personal AI assistant built on OpenClaw, deployed 24/7 on DigitalOcean, accessible via Telegram.

## Stack
| Component | Choice |
|---|---|
| Framework | OpenClaw (Node.js, 180K+ stars) |
| Server | DigitalOcean 4GB / 2vCPU / Ubuntu 24.04 |
| Primary LLM | Grok 4.1 Fast (tool calling) |
| Backup LLM | Claude Sonnet 4.5 (cron jobs) |
| Interface | Telegram |

## Capabilities
- Gmail — send/read/search/reply/forward + file attachments (custom Python skill — gog CLI cannot send attachments)
- Google Calendar — list/create/update events with conflict detection
- Google Drive — list/search/read/download/upload
- Notion — tasks, expenses, habits, contacts, job tracking
- Web search via Brave API
- Weather via Open-Meteo (free, no key)
- Nearby places via Google Places API
- Voice transcription via OpenAI Whisper
- PDF generation
- Persistent memory across sessions
- Automated morning briefing, weekly review, nightly journal (cron jobs)

## Cost
~$10-12/month total (DigitalOcean $24 + LLM APIs, Google APIs free)

## Setup
1. Deploy DigitalOcean droplet (Ubuntu 24.04, 4GB RAM minimum)
2. Follow server hardening in docs/setup.md
3. Copy `IDENTITY.example.md` → `IDENTITY.md` and fill in your tool commands
4. Copy `SOUL.example.md` → `SOUL.md` and customize personality
5. Copy `USER.example.md` → `USER.md` and fill in your personal info
6. Set up GCP OAuth (Gmail, Calendar, Drive) — see docs/google-oauth.md
7. Add API keys to `~/.openclaw/.env`

## Key Lesson Learned
The biggest reliability issue with AI agents is "faking" — cheaper LLMs claim to execute tools without actually doing so. Grok 4.1 Fast solved this at 1/15th the cost of Claude Sonnet.

Built by Ishan Srivastava — MS Applied AI, Northeastern University

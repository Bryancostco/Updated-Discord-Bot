# Updated Discord Music Bot (Docker Ready)

A Discord music bot built with **discord.py** that supports playing audio from **YouTube-compatible sources** using `yt-dlp` and `ffmpeg`.  
The bot is fully **Dockerized**, making it easy to run locally, on a server, or in a homelab.

---

## Features
- Join and leave voice channels
- Play audio from YouTube-compatible URLs
- Queue support
- Stop / skip commands
- Environment variable–based configuration
- Docker + Docker Compose support
- Auto-restart on crash (Docker)

---

## Requirements

### Local (without Docker)
- Python 3.12 (recommended)
- ffmpeg installed and available in PATH
- Discord bot token

### Docker (recommended)
- Docker
- Docker Compose
- No local Python setup required

---

## Environment Variables

Create a `.env` file in the project root:

```env
DISCORD_TOKEN=your_discord_bot_token_here

# Discord VC Bot

Two features:
1. **VC join announcer** — posts a message to a text channel whenever someone joins a voice channel.
2. **Music player** — `!join`, `!play <song or URL>`, `!skip`, `!stop`, `!queue`, using yt-dlp + FFmpeg (no Lavalink server needed).

## 1. Discord Developer Portal setup

1. Go to https://discord.com/developers/applications and create (or open) your bot application.
2. Under **Bot**, enable these three **Privileged Gateway Intents**:
   - Message Content Intent
   - Server Members Intent
   - Presence Intent
3. Copy the bot token (Bot page → Reset Token / Copy).
4. Invite the bot to your server with at least these permissions: View Channels, Send Messages, Connect, Speak.

## 2. Local setup (macOS)

```bash
# from inside the discord-bot/ folder
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# FFmpeg is required for audio playback
brew install ffmpeg
```

Copy `.env.example` to `.env` and paste in your token:

```bash
cp .env.example .env
# then edit .env and set DISCORD_TOKEN=...
```

## 3. Configure the announce channel

Open `cogs/vc_announcer.py` and set `ANNOUNCE_CHANNEL_ID` to the text channel you want join announcements posted to. (Enable Developer Mode in Discord settings, then right-click the channel → Copy Channel ID.)

## 4. Run it

```bash
python bot.py
```

## Commands

| Command            | What it does                          |
|---------------------|----------------------------------------|
| `!join`             | Bot joins your current voice channel   |
| `!play <query/url>` | Searches/queues a track, starts playing|
| `!skip`             | Skips the current track                |
| `!stop`             | Clears the queue and leaves the VC      |
| `!queue`            | Shows what's playing and queued         |

## Notes / next steps

- This uses discord.py's native voice client (yt-dlp → FFmpeg), not Wavelink/Lavalink — no separate Lavalink server to run.
- `ytdl.extract_info` is a blocking call; it's offloaded to an executor so it won't freeze the event loop, but very long queues could still benefit from pre-fetching info earlier.
- Stream URLs from yt-dlp expire after a while — if a track fails partway through on a very long queue, re-running `!play` on it will fetch a fresh URL.
- If you outgrow single-server / single-process needs (e.g. many guilds playing simultaneously), migrating to Wavelink + a Lavalink node is the natural next step — happy to help with that swap later.

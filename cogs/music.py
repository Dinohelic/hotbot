import asyncio
import json
import os
from typing import Optional

import discord
from discord.ext import commands
from yt_dlp import YoutubeDL

YTDL_SEARCH_OPTIONS = {
    "format": "bestaudio/best",
    "quiet": True,
    "source_address": "0.0.0.0",
    "extract_flat": True, # Gets playlists and search results instantly
    "js_runtimes": {"node": {}, "deno": {}},
    "remote_components": ["ejs:github"],
}

YTDL_EXTRACT_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "source_address": "0.0.0.0",
    "js_runtimes": {"node": {}, "deno": {}},
    "remote_components": ["ejs:github"],
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}

if os.path.exists("cookies.txt"):
    YTDL_SEARCH_OPTIONS["cookiefile"] = "cookies.txt"
    YTDL_EXTRACT_OPTIONS["cookiefile"] = "cookies.txt"

# Note: Using YoutubeDL in a context manager to prevent memory leaks

HOTLINES_FILE = "hotlines.json"

def load_hotlines():
    if os.path.exists(HOTLINES_FILE):
        with open(HOTLINES_FILE, "r") as f:
            return json.load(f)
    return {}

def save_hotlines(hotlines):
    with open(HOTLINES_FILE, "w") as f:
        json.dump(hotlines, f, indent=4)

class Track:
    def __init__(self, title: str, query_or_url: str):
        self.title = title
        self.query_or_url = query_or_url

class GuildMusicState:
    def __init__(self):
        self.queue: list[Track] = []
        self.voice_client: Optional[discord.VoiceClient] = None
        self.current: Optional[Track] = None
        self.is_playing = False  # True when a track is actively playing or paused

class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.states: dict[int, GuildMusicState] = {}
        self.hotlines = load_hotlines()

    def get_state(self, guild_id: int) -> GuildMusicState:
        if guild_id not in self.states:
            self.states[guild_id] = GuildMusicState()
        return self.states[guild_id]

    async def search(self, query: str) -> list[Track]:
        query = query.strip("<>")
        loop = asyncio.get_running_loop()
        
        # If it's a URL, extract it
        with YoutubeDL(YTDL_SEARCH_OPTIONS) as ytdl:
            if query.startswith("http://") or query.startswith("https://"):
                data = await loop.run_in_executor(
                    None, lambda: ytdl.extract_info(query, download=False)
                )
            else:
                # Text search -> Try SoundCloud, fallback to YouTube
                try:
                    data = await loop.run_in_executor(
                        None, lambda: ytdl.extract_info(f"scsearch:{query}", download=False)
                    )
                    if not data or "entries" not in data or not data["entries"]:
                        raise Exception()
                except Exception:
                    data = await loop.run_in_executor(
                        None, lambda: ytdl.extract_info(f"ytsearch:{query}", download=False)
                    )

        if not data:
            raise Exception("No results found.")
            
        tracks = []
        if "entries" in data:
            for entry in data["entries"]:
                if entry:
                    title = entry.get("title", "Unknown Title")
                    url = entry.get("url") or entry.get("webpage_url") or query
                    tracks.append(Track(title, url))
        else:
            title = data.get("title", "Unknown Title")
            url = data.get("url") or data.get("webpage_url") or query
            tracks.append(Track(title, url))
            
        if not tracks:
            raise Exception("No results found.")
            
        return tracks

    def play_next(self, guild: discord.Guild):
        # Fire and forget the async play function
        self.bot.loop.create_task(self.play_next_async(guild))

    async def play_next_async(self, guild: discord.Guild):
        state = self.get_state(guild.id)
        
        # Check if bot was disconnected to avoid a tight loop of ClientExceptions
        if state.voice_client is None or not state.voice_client.is_connected():
            state.queue.clear()
            state.current = None
            state.is_playing = False
            return

        if not state.queue:
            state.current = None
            state.is_playing = False
            return

        track = state.queue.pop(0)
        state.current = track
        state.is_playing = True
        
        loop = asyncio.get_running_loop()
        try:
            # JIT extraction to get the direct stream URL right before playing
            with YoutubeDL(YTDL_EXTRACT_OPTIONS) as ytdl:
                data = await loop.run_in_executor(
                    None, lambda: ytdl.extract_info(track.query_or_url, download=False)
                )
            # Use direct URL, or fallback to webpage URL if direct is missing (unlikely)
            stream_url = data.get("url") or data.get("webpage_url")
            
            source = discord.FFmpegPCMAudio(stream_url, **FFMPEG_OPTIONS)
            
            def after_playing(error: Optional[Exception]):
                if error:
                    print(f"Player error: {error}")
                # Safely schedule the next song
                self.bot.loop.call_soon_threadsafe(
                    lambda: self.bot.loop.create_task(self.play_next_async(guild))
                )

            state.voice_client.play(source, after=after_playing)
            
        except Exception as e:
            print(f"Failed to extract {track.title}: {e}")
            state.is_playing = False
            # Add a small delay to avoid CPU/Network burst on consecutive failures
            await asyncio.sleep(1)
            # Skip to next track if this one fails
            self.bot.loop.create_task(self.play_next_async(guild))

    def _should_start_playing(self, state: GuildMusicState) -> bool:
        """Check if the bot should start playing the next track.
        Returns True only when nothing is currently playing or paused."""
        if state.is_playing:
            return False
        if state.voice_client is None:
            return False
        if state.voice_client.is_playing() or state.voice_client.is_paused():
            return False
        return True

    @commands.command(name="join")
    async def join(self, ctx: commands.Context):
        if ctx.author.voice is None or ctx.author.voice.channel is None:
            await ctx.send("Join a voice channel first.")
            return

        channel = ctx.author.voice.channel
        state = self.get_state(ctx.guild.id)

        if state.voice_client is None or not state.voice_client.is_connected():
            state.voice_client = await channel.connect()
        else:
            await state.voice_client.move_to(channel)

        await ctx.send(f"Joined **{channel.name}**.")

    @commands.command(name="create_hotline")
    async def create_hotline(self, ctx: commands.Context, number: str, *, songs: str):
        """Creates a hotline playlist. Songs should be separated by commas."""
        song_list = [s.strip() for s in songs.split(",") if s.strip()]
        if not song_list:
            await ctx.send("Please provide a list of songs separated by commas.")
            return
            
        self.hotlines[number] = song_list
        save_hotlines(self.hotlines)
        await ctx.send(f"📞 Hotline **{number}** created with {len(song_list)} queries!")

    @commands.command(name="play")
    async def play(self, ctx: commands.Context, *, query: str):
        if ctx.author.voice is None or ctx.author.voice.channel is None:
            await ctx.send("Join a voice channel first.")
            return

        state = self.get_state(ctx.guild.id)

        if state.voice_client is None or not state.voice_client.is_connected():
            state.voice_client = await ctx.author.voice.channel.connect()

        query_stripped = query.strip("<>")
        
        # Check if the query is a saved hotline
        if query_stripped in self.hotlines:
            song_list = self.hotlines[query_stripped]
            await ctx.send(f"📞 Dialing hotline **{query_stripped}**... analyzing {len(song_list)} items!")
            
            tracks_added = 0
            for song in song_list:
                async with ctx.typing():
                    try:
                        tracks = await self.search(song)
                        state.queue.extend(tracks)
                        tracks_added += len(tracks)
                    except Exception as e:
                        await ctx.send(f"Couldn't find '{song}': {e}")
                        
                # Start playback as soon as the first track is ready
                if self._should_start_playing(state):
                    self.play_next(ctx.guild)

            if tracks_added > 0:
                await ctx.send(f"Queued **{tracks_added} tracks** from hotline.")
            return

        # Normal play (single song or a playlist URL)
        async with ctx.typing():
            try:
                tracks = await self.search(query)
            except Exception as e:
                await ctx.send(f"Couldn't find that: {e}")
                return

        state.queue.extend(tracks)
        if len(tracks) == 1:
            await ctx.send(f"Queued **{tracks[0].title}**")
        else:
            await ctx.send(f"Queued **{len(tracks)} tracks** from playlist.")

        # Start playing immediately if nothing is currently active
        if self._should_start_playing(state):
            self.play_next(ctx.guild)

    @commands.command(name="pause")
    async def pause(self, ctx: commands.Context):
        state = self.get_state(ctx.guild.id)
        if state.voice_client and state.voice_client.is_playing():
            state.voice_client.pause()
            await ctx.send("⏸️ Paused.")
        else:
            await ctx.send("Nothing is playing right now.")

    @commands.command(name="resume")
    async def resume(self, ctx: commands.Context):
        state = self.get_state(ctx.guild.id)
        if state.voice_client and state.voice_client.is_paused():
            state.voice_client.resume()
            await ctx.send("▶️ Resumed.")
        else:
            await ctx.send("Nothing is paused right now.")

    @commands.command(name="skip")
    async def skip(self, ctx: commands.Context):
        state = self.get_state(ctx.guild.id)
        if state.voice_client and (state.voice_client.is_playing() or state.voice_client.is_paused()):
            state.voice_client.stop()  # This triggers after_playing -> play_next
            await ctx.send("⏭️ Skipped.")
        else:
            await ctx.send("Nothing is playing.")

    @commands.command(name="stop")
    async def stop(self, ctx: commands.Context):
        state = self.get_state(ctx.guild.id)
        state.queue.clear()
        state.current = None
        state.is_playing = False
        if state.voice_client:
            state.voice_client.stop()  # Stop audio first to prevent after_playing from firing with stale state
            await state.voice_client.disconnect()
            state.voice_client = None
        await ctx.send("⏹️ Stopped and left the voice channel.")

    @commands.command(name="queue")
    async def show_queue(self, ctx: commands.Context):
        state = self.get_state(ctx.guild.id)
        if not state.queue and not state.current:
            await ctx.send("Queue is empty.")
            return

        lines = []
        if state.current:
            lines.append(f"**Now playing:** {state.current.title}")
            
        queue_slice = state.queue[:10]
        for i, track in enumerate(queue_slice, start=1):
            lines.append(f"{i}. {track.title}")
            
        if len(state.queue) > 10:
            lines.append(f"...and {len(state.queue) - 10} more songs.")
            
        await ctx.send("\n".join(lines))

    @play.error
    async def play_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Please tell me what to play! Example: `!play lofi hip hop`")

async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))

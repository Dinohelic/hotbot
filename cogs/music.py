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
        # Loop state
        self.loop_track: Optional[Track] = None   # The track being looped
        self.loop_count: Optional[int] = None      # None = infinite, int = remaining plays
        self.loop_requester: Optional[discord.Member] = None  # Who requested the loop
        self.loop_vibe_task: Optional[asyncio.Task] = None     # Background vibe-check task

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

    def _cancel_loop(self, state: GuildMusicState):
        """Clear all loop state and cancel the vibe-check timer."""
        state.loop_track = None
        state.loop_count = None
        state.loop_requester = None
        if state.loop_vibe_task and not state.loop_vibe_task.done():
            state.loop_vibe_task.cancel()
        state.loop_vibe_task = None

    async def _vibe_check(self, guild: discord.Guild, user: discord.Member):
        """Wait 30 minutes, then send a vibe-check. If no reaction in 5 mins, stop."""
        VIBE_CHANNEL_ID = 1553483800686755911
        try:
            await asyncio.sleep(30 * 60)  # 30 minutes

            state = self.get_state(guild.id)
            # If loop was cancelled while we waited, bail out
            if state.loop_track is None:
                return

            channel = self.bot.get_channel(VIBE_CHANNEL_ID)
            if channel is None:
                return

            msg = await channel.send(
                f"🚨 Vibe check, {user.mention}! We've been spinning this for half an hour! "
                f"💿 Drop a reaction if you're still listening, or I'm packing up the DJ booth in 5 mins."
            )
            # Seed reactions so the user can just click
            await msg.add_reaction("💿")
            await msg.add_reaction("🎧")

            def check(reaction: discord.Reaction, reactor: discord.User):
                return (
                    reactor.id == user.id
                    and reaction.message.id == msg.id
                    and str(reaction.emoji) in ("💿", "🎧")
                )

            try:
                await self.bot.wait_for("reaction_add", timeout=5 * 60, check=check)
                # User reacted — reset the timer for another 30 minutes
                await channel.send(f"🎶 Nice, {user.mention}! Keeping the vibes going. See you in another 30! 🔁")
                state.loop_vibe_task = asyncio.create_task(self._vibe_check(guild, user))
            except asyncio.TimeoutError:
                # No reaction — stop everything
                await channel.send(f"🎤 No response from {user.mention} — packing up the DJ booth. Catch you next time! ✌️")
                self._cancel_loop(state)
                state.queue.clear()
                state.current = None
                state.is_playing = False
                if state.voice_client:
                    state.voice_client.stop()
                    await state.voice_client.disconnect()
                    state.voice_client = None

        except asyncio.CancelledError:
            pass  # Loop was stopped or a new loop replaced this one

    def play_next(self, guild: discord.Guild):
        # Fire and forget the async play function
        self.bot.loop.create_task(self.play_next_async(guild))

    async def play_next_async(self, guild: discord.Guild):
        state = self.get_state(guild.id)
        
        # Check if bot was disconnected to avoid a tight loop of ClientExceptions
        if state.voice_client is None or not state.voice_client.is_connected():
            state.queue.clear()
            self._cancel_loop(state)
            state.current = None
            state.is_playing = False
            return

        # If a loop is active and the queue is empty, re-queue the loop track
        if state.loop_track and not state.queue:
            if state.loop_count is None:
                # Infinite loop — keep going
                state.queue.append(Track(state.loop_track.title, state.loop_track.query_or_url))
            elif state.loop_count > 0:
                # Finite loop — decrement
                state.loop_count -= 1
                state.queue.append(Track(state.loop_track.title, state.loop_track.query_or_url))
            else:
                # Loop exhausted
                self._cancel_loop(state)

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

    @commands.command(name="loop")
    async def loop(self, ctx: commands.Context, *, args: str = None):
        """Loop a track.
        Usage:
          !loop            — loop the current track infinitely
          !loop 5          — loop the current track 5 times
          !loop <song>     — loop a song infinitely
          !loop 3 <song>   — loop a song 3 times
        """
        if ctx.author.voice is None or ctx.author.voice.channel is None:
            await ctx.send("Join a voice channel first.")
            return

        state = self.get_state(ctx.guild.id)

        if state.voice_client is None or not state.voice_client.is_connected():
            state.voice_client = await ctx.author.voice.channel.connect()

        loop_count = None  # None means infinite
        query = None

        if args:
            parts = args.strip().split(None, 1)
            # Check if the first token is a number
            if parts[0].isdigit():
                loop_count = int(parts[0])
                if loop_count < 1:
                    await ctx.send("Loop count must be at least 1.")
                    return
                query = parts[1] if len(parts) > 1 else None
            else:
                query = args.strip()

        # Determine which track to loop
        if query:
            # Search for the requested song
            async with ctx.typing():
                try:
                    tracks = await self.search(query)
                except Exception as e:
                    await ctx.send(f"Couldn't find that: {e}")
                    return
            track = tracks[0]
        elif state.current:
            # Loop the currently playing track
            track = Track(state.current.title, state.current.query_or_url)
        else:
            await ctx.send("Nothing is playing and no song was specified. Use `!loop <song>` or play something first.")
            return

        # Cancel any previous loop
        self._cancel_loop(state)

        # Set up loop state — loop_count stores *remaining* plays after the first
        state.loop_track = track
        state.loop_count = (loop_count - 1) if loop_count is not None else None
        state.loop_requester = ctx.author

        if loop_count is None:
            count_label = "∞ (infinite)"
        else:
            count_label = str(loop_count)

        await ctx.send(f"🔁 Looping **{track.title}** × {count_label}")

        # If nothing is playing, start now
        if query:
            # Put the track at the front and start
            state.queue.insert(0, Track(track.title, track.query_or_url))
            if self._should_start_playing(state):
                self.play_next(ctx.guild)
        else:
            # Current track is already playing; after it finishes it will re-queue automatically
            pass

        # Start the vibe-check timer for infinite loops
        if state.loop_count is None:
            state.loop_vibe_task = asyncio.create_task(
                self._vibe_check(ctx.guild, ctx.author)
            )

    @commands.command(name="unloop")
    async def unloop(self, ctx: commands.Context):
        """Stop looping the current track."""
        state = self.get_state(ctx.guild.id)
        if state.loop_track is None:
            await ctx.send("Nothing is being looped right now.")
            return
        title = state.loop_track.title
        self._cancel_loop(state)
        await ctx.send(f"🔁❌ Stopped looping **{title}**.")

    @commands.command(name="stop")
    async def stop(self, ctx: commands.Context):
        state = self.get_state(ctx.guild.id)
        self._cancel_loop(state)
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
            now_playing = f"**Now playing:** {state.current.title}"
            if state.loop_track:
                if state.loop_count is None:
                    now_playing += " 🔁 ∞"
                else:
                    now_playing += f" 🔁 {state.loop_count + 1} left"
            lines.append(now_playing)
            
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

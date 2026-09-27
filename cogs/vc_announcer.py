import discord
from discord.ext import commands

# Replace with the ID of the text channel where join announcements should post.
# (Right-click the channel in Discord with Developer Mode on -> Copy Channel ID)
ANNOUNCE_CHANNEL_ID = False


class VCAnnouncer(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        # Ignore bots so the bot doesn't announce itself (or other bots) joining
        if member.bot:
            return

        joined_a_channel = before.channel is None and after.channel is not None
        switched_channel = (
            before.channel is not None
            and after.channel is not None
            and before.channel.id != after.channel.id
        )

        # Only fire on an actual join/switch — not on mute/deafen toggles or leaves
        if not (joined_a_channel or switched_channel):
            return

        # Replace with your Special Role ID (Right click role in Server Settings -> Copy ID)
        SPECIAL_ROLE_ID = 1553461064849694820
        
        # Check if the user has the special role
        has_special_role = any(role.id == SPECIAL_ROLE_ID for role in member.roles)
        
        # Check if the channel is private (meaning the @everyone role is denied view or connect access)
        everyone_role = member.guild.default_role
        perms = after.channel.permissions_for(everyone_role)
        is_private_channel = not perms.view_channel or not perms.connect

        # Skip the announcement if they have the special role OR if it's a private channel
        if has_special_role or is_private_channel:
            pass # Do nothing!
        else:
            channel = self.bot.get_channel(ANNOUNCE_CHANNEL_ID)
            if channel is not None:
                await channel.send(
                    f"🔊 **{member.display_name}** joined **{after.channel.name}**"
                )

        # Auto-join specific VC
        if after.channel is not None and after.channel.id == 1553484183341637734:
            music_cog = self.bot.get_cog("Music")
            if music_cog:
                state = music_cog.get_state(member.guild.id)
                if state.voice_client is None or not state.voice_client.is_connected():
                    if member.guild.voice_client:
                        state.voice_client = member.guild.voice_client
                        await state.voice_client.move_to(after.channel)
                    else:
                        state.voice_client = await after.channel.connect()


async def setup(bot: commands.Bot):
    await bot.add_cog(VCAnnouncer(bot))

import logging

import discord
from discord.ext import commands

logger = logging.getLogger("vc_announcer")

# Replace with the ID of the text channel where join announcements should post.
# (Right-click the channel in Discord with Developer Mode on -> Copy Channel ID)
ANNOUNCE_CHANNEL_ID = 1553853923184353300


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
        logger.info(f"[VC] Voice update: {member.display_name} | before={before.channel} | after={after.channel}")

        # Ignore bots so the bot doesn't announce itself (or other bots) joining
        if member.bot:
            logger.info("[VC] Skipped: member is a bot")
            return

        # Only fire when someone FIRST joins a VC (was fully disconnected before)
        # Ignore channel switches and leaves
        if before.channel is not None or after.channel is None:
            logger.info("[VC] Skipped: not a fresh join (switch/leave/mute)")
            return

        logger.info(f"[VC] Fresh join detected for {member.display_name}")

        # Replace with your Special Role ID (Right click role in Server Settings -> Copy ID)
        SPECIAL_ROLE_ID = 1553461064849694820

        # Check if the user has the special role
        has_special_role = any(role.id == SPECIAL_ROLE_ID for role in member.roles)
        logger.info(f"[VC] has_special_role={has_special_role}")

        # Check if the channel is private (meaning the @everyone role is denied view or connect access)
        everyone_role = member.guild.default_role
        perms = after.channel.permissions_for(everyone_role)
        is_private_channel = not perms.view_channel or not perms.connect
        logger.info(f"[VC] is_private_channel={is_private_channel} (view={perms.view_channel}, connect={perms.connect})")

        # Skip the announcement if they have the special role OR if it's a private channel
        if has_special_role or is_private_channel:
            logger.info("[VC] Skipped announcement: special role or private channel")
        else:
            channel = self.bot.get_channel(ANNOUNCE_CHANNEL_ID)
            logger.info(f"[VC] Announce channel lookup: {channel} (ID={ANNOUNCE_CHANNEL_ID})")
            if channel is not None:
                greeting = (
                    f"🚨 **NEW HUMAN DETECTED** 🚨\n\n"
                    f"Welcome to the server, {member.mention} 👋\n\n"
                    f"Your application has been reviewed by absolutely nobody\n"
                    f"and you've been **accepted anyway.** 💀\n\n"
                    f"🎬 Movie nights\n"
                    f"🎧 Music addiction\n"
                    f"🗣️ Unnecessary conversations\n"
                    f"🤡 Certified tomfoolery\n\n"
                    f"Please keep your expectations low\n"
                    f"and your Wi-Fi stable.\n\n"
                    f"**Have fun. Don't be normal. 🫡**"
                )
                await channel.send(greeting)
                logger.info("[VC] Greeting sent!")
            else:
                logger.warning(f"[VC] Could not find channel with ID {ANNOUNCE_CHANNEL_ID}!")

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

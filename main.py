import discord
import os
from discord.ext.commands import has_permissions


PREFIX_COMMAND = '$'
ROLE_MOD = 'CrewMod'
COMMANDS_MUTE = ['mute', 'm']
COMMANDS_UNMUTE = ['unmute', 'um']
REACTION_MUTE = '\U0001F92B'
REACTION_UNMUTE = '\U0001F925'

active_channel_ids = set()


class BotClient(discord.Client):

    @staticmethod
    async def on_voice_state_update(member, before, after):
        ac = after.channel
        bc = before.channel

        if member.bot or ac is not None and bc is not None and ac.id == bc.id:
            return

        if bc is not None and bc.id in active_channel_ids and ROLE_MOD in [r.name for r in member.roles]:
            all_members = await bc.guild.fetch_members(limit=100000).flatten()
            member_ids = bc.voice_states.keys()
            connected_members = [m for m in all_members if m.id in member_ids]
            mods_left = False
            for connected_member in connected_members:
                if not connected_member.bot and ROLE_MOD in [r.name for r in connected_member.roles]:
                    mods_left = True
                    break

            if not mods_left:
                active_channel_ids.remove(bc.id)
                for connected_member in connected_members:
                    if not connected_member.bot:
                        await connected_member.edit(mute=False)

        if ac is not None and ac.id in active_channel_ids:
            await member.edit(mute=True)
        elif ac is not None and ac.id not in active_channel_ids:
            await member.edit(mute=False)

    @staticmethod
    async def make_mod(guild):
        role = [r for r in guild.roles if r.name == ROLE_MOD][0]
        async for member in guild.fetch_members(limit=100000):
            if member.guild_permissions.administrator:
                await member.add_roles(role)

    @staticmethod
    async def on_guild_join(guild):
        if guild.name and ROLE_MOD not in [r.name for r in guild.roles]:
            await guild.create_role(name=ROLE_MOD, color=discord.Colour(0xff0000))
            await BotClient.make_mod(guild)

    def __init__(self, **options):
        intents = discord.Intents().default()
        intents.voice_states = True
        super().__init__(intents=intents, **options)

    @has_permissions(mute_members=True)
    async def mute_channel(self, channel, state=True):
        if state:
            active_channel_ids.add(channel.id)
        else:
            active_channel_ids.remove(channel.id)
        all_members = await channel.guild.fetch_members(limit=100000).flatten()
        member_ids = channel.voice_states.keys()
        connected_members = [m for m in all_members if m.id in member_ids]
        for member in connected_members:
            if not member.bot:
                await member.edit(mute=state)

    @has_permissions(manage_roles=True)
    async def create_mod_roles(self):
        for guild in self.guilds:
            if guild.name and ROLE_MOD not in [r.name for r in guild.roles]:
                await guild.create_role(name=ROLE_MOD, color=discord.Colour(0xff0000))
                await self.make_mod(guild)

    async def on_ready(self):
        print('Login Successful as '+self.user.name+' - '+str(self.user.id))
        await self.create_mod_roles()

    async def on_message(self, message):
        _content = message.clean_content.lower()

        # we do not want the bot to reply to itself
        if message.author.id == self.user.id or not _content.startswith(PREFIX_COMMAND):
            return
        else:
            _content = _content[1:]

        if ROLE_MOD in [r.name for r in message.author.roles] and \
                message.author.voice is not None:
            channel = message.author.voice.channel
            if _content in COMMANDS_MUTE:
                await message.add_reaction(REACTION_MUTE)
                await self.mute_channel(channel)
            elif _content in COMMANDS_UNMUTE:
                await message.add_reaction(REACTION_UNMUTE)
                await self.mute_channel(channel, state=False)


if __name__ == '__main__':
    token = os.environ['token']
    if not token:
        token = open('token', 'r').read()
    client = BotClient()
    client.run(token)

from discord.ext.commands import Cog, Bot
from discord import Object

class Listeners(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        print(f"Logged in as {self.bot.user}")
        print("-----------------------------------------------------")
        synced = await self.bot.tree.sync(guild=Object(id="351497847750787084"))
        synced += await self.bot.tree.sync()
        print(f"Synced {len(synced)} commands with the bot.")
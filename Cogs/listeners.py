from discord.ext.commands import Cog, Bot

class Listeners(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        print(f"Logged in as {self.bot.user}")
from discord.ext.commands import Cog, Bot
from discord import app_commands, Interaction, Object

class Ping(Cog):
    """
    Class for ping command
    """
    def __init__(self, bot: Bot):
        """
        :param bot: Discord.py bot instance
        """
        self.bot = bot
    
    @app_commands.command(name="ping", description="Returns server response time in ms")
    @app_commands.guilds(
        Object(id="301824927370313728"),
        Object(id="351497847750787084")
    )
    async def ping(self, interaction: Interaction):
        await interaction.response.send_message(content=f"Pong! Took {round(self.bot.latency * 1000)}ms")
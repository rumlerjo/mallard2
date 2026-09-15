from discord.ext.commands import Cog, Bot
from discord import app_commands, Interaction, Role
from typing import Optional

class SelectableRole(Cog):
    """
    Contains commands relating to adding a role to SelectableRole list
    """
    def __init__(self, bot: Bot):
        """
        :param bot: discord.py Bot instance
        """
        super().__init__()
        self.bot = bot

    selectable_role = app_commands.Group(
        name="selectable-role",
        description="Commands for role self service in guilds",
        guild_only=True,
        guild_ids=[351497847750787084]
    )

    @selectable_role.command(name="add", description="Adds a role to role self service")
    @app_commands.describe(
        role="Role to add to self service",
        description="Description of role",
        emoji="Emoji associated with role (Optional)"
    )
    async def add_role(self, interaction: Interaction, role: Role, description: str, emoji: Optional[str]):
        await interaction.response.send_message(f"Selected {role.name} role.\nDescribed as '{description}'\nEmoji: {emoji if emoji else "none"}")

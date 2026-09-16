from discord.ext.commands import Cog, Bot
from discord import app_commands, Interaction, Role, Client, SelectOption, ButtonStyle, Embed, Color, Permissions, NotFound
from discord.ui import View, Select, Button
from typing import Optional, Tuple, List
from MallardModels import MallardGuild
from DatabaseModels import SelectableRole
import re
import emoji

# regex for discord custom emoji format <:name:id> or <a:name:id>
CUSTOM_EMOJI_PATTERN = re.compile(r"^<a?:([a-zA-Z0-9\_]+):([0-9]+)>$")

def is_valid_emoji(emoji_input: str, bot: Client = None) -> Tuple[bool, bool]:
    """
    Verifies emoji string input is either a unicode emoji or a custom emoji accessible by bot
    :param emoji_input: emoji input string
    :param bot: discord bot client
    :return: Tuple in format (bool, bool) indicating if it is a valid emoji and whether it is accessible by the bot
    """
    emoji_input = emoji_input.strip()
    
    if emoji.is_emoji(emoji_input):
        return True, True

    match = CUSTOM_EMOJI_PATTERN.match(emoji_input)
    if match:
        if bot:
            emoji_id = int(match.group(2))
            return True, bot.get_emoji(emoji_id) is not None # bot can use emoji (server it's in)

    return False, False

class SelectableRoleList(View):
    """
    Creates a dropdown for user-selectable roles
    """
    def __init__(self, selectable_role_list: List[SelectableRole]):
        super().__init__()
        options = []

        self.currently_selected = None

        for selectable_role in selectable_role_list:
            new_option = SelectOption(
                label=selectable_role.role_name,
                description=selectable_role.description,
                emoji=selectable_role.emoji if selectable_role.emoji != "" else None,
                value=selectable_role.role_id
            )
            options.append(new_option)

        self.role_select = Select(
            placeholder="Select a role...",
            options=options
        )

        self.confirm_btn = Button(
            label="Get Role", 
            style=ButtonStyle.success,
            disabled=True 
        )

        self.role_select.callback = self.dropdown_callback
        self.confirm_btn.callback = self.button_callback

        self.add_item(self.role_select)
        self.add_item(self.confirm_btn)

    async def dropdown_callback(self, interaction: Interaction):
        self.currently_selected = int(self.role_select.values[0])
        role = interaction.guild.get_role(self.currently_selected)

        for option in self.role_select.options:
            option.default = str(option.value) == str(self.currently_selected)

        has_role = role in interaction.user.roles if role else False
        
        self.confirm_btn.disabled = False
        if has_role:
            self.confirm_btn.label = "Remove role"
            self.confirm_btn.style = ButtonStyle.danger
        else:
            self.confirm_btn.label = "Get role"
            self.confirm_btn.style = ButtonStyle.success

        await interaction.response.edit_message(view=self)

    async def button_callback(self, interaction: Interaction):
        if not interaction.guild:
            return

        role = interaction.guild.get_role(self.currently_selected)
        if not role:
            return

        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            msg = f"Role **{role.name}** removed!"
        else:
            await interaction.user.add_roles(role)
            msg = f"Role **{role.name}** added!"

        self.currently_selected = None
        self.confirm_btn.disabled = True
        self.confirm_btn.label = "Select a role"
        self.confirm_btn.style = ButtonStyle.secondary

        for option in self.role_select.options:
            option.default = False

        await interaction.response.edit_message(view=self)
        await interaction.followup.send(msg, ephemeral=True)

class RoleConfirmView(View):
    """
    Ephemeral view sent after a user selects an option from the main dropdown
    """
    def __init__(self, role: Role, has_role: bool):
        super().__init__(timeout=None)
        self.role = role
        
        self.confirm_btn = Button(
            label="Remove role" if has_role else "Get role",
            style=ButtonStyle.danger if has_role else ButtonStyle.success,
            custom_id=f"confirm_role_{role.id}" # Unique to this ephemeral instance
        )
        self.confirm_btn.callback = self.button_callback
        self.add_item(self.confirm_btn)

    async def button_callback(self, interaction: Interaction):
        if self.role in interaction.user.roles:
            await interaction.user.remove_roles(self.role)
            msg = f"Role **{self.role.name}** removed!"
        else:
            await interaction.user.add_roles(self.role)
            msg = f"Role **{self.role.name}** added!"

        self.confirm_btn.disabled = True
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(msg, ephemeral=True)


class PersistentGuildRoleSelect(Select):
    """
    The persistent select menu attached to the public message
    """
    def __init__(self, options: List[SelectOption]):
        super().__init__(
            placeholder="Select a role...",
            options=options,
            custom_id="global_persistent_role_select" 
        )

    async def callback(self, interaction: Interaction):
        role_id = int(self.values[0])
        role = interaction.guild.get_role(role_id)
        
        if not role:
            return await interaction.response.send_message("This role no longer exists in the server.", ephemeral=True)

        has_role = role in interaction.user.roles
        
        confirm_view = RoleConfirmView(role=role, has_role=has_role)
        await interaction.response.send_message(
            f"Are you sure you want to {'remove' if has_role else 'add'} the **{role.name}** role?", 
            view=confirm_view, 
            ephemeral=True
        )


class PersistentRoleView(View):
    """
    The container view for the persistent select menu
    """
    def __init__(self, options: List[SelectOption]):
        super().__init__(timeout=None)
        self.add_item(PersistentGuildRoleSelect(options))


class SelectableRoleCommands(Cog):
    """
    Contains commands relating to adding a role to SelectableRole list
    """
    def __init__(self, bot: Bot):
        """
        :param bot: discord.py Bot instance
        """
        super().__init__()
        self.bot = bot

    async def _build_menu_payload(self, mallard_guild: MallardGuild) -> Tuple[Embed, Optional[PersistentRoleView]]:
        embed = Embed(
            title="Server Roles", 
            description="Select a role from the dropdown below to add or remove it.",
            color=Color.blue()
        )
        
        if not mallard_guild.selectable_roles:
            embed.description = "No roles are currently configured for self-service."
            return embed, None

        options = []
        seen_roles = set()

        for selectable_role_link in mallard_guild.selectable_roles:
            selectable_role_doc = await selectable_role_link.fetch()
            
            if selectable_role_doc.role_id in seen_roles:
                continue
            
            seen_roles.add(selectable_role_doc.role_id)

            emoji_str = f"{selectable_role_doc.emoji} " if selectable_role_doc.emoji else ""
            embed.add_field(
                name=f"{emoji_str}{selectable_role_doc.role_name}", 
                value=selectable_role_doc.description, 
                inline=False
            )
            
            options.append(SelectOption(
                label=selectable_role_doc.role_name,
                emoji=selectable_role_doc.emoji if selectable_role_doc.emoji != "" else None,
                value=str(selectable_role_doc.role_id)
            ))

        view = PersistentRoleView(options=options)
        return embed, view

    async def _sync_guild_message(self, interaction: Interaction, mallard_guild: MallardGuild):
        """
        Helper to safely edit the live guild message if it exists.
        """
        msg_id = mallard_guild.selectable_role_message
        channel_id = mallard_guild.selectable_role_channel

        if not msg_id or not channel_id:
            return

        channel = interaction.guild.get_channel(channel_id)
        if not channel:
            return

        embed, view = await self._build_menu_payload(mallard_guild)

        try:
            msg = await channel.fetch_message(msg_id)
            await msg.edit(embed=embed, view=view)
        except NotFound:
            mallard_guild.set_selectable_role_message(0)
            mallard_guild.set_selectable_role_channel(0)
            await mallard_guild.save()

    selectable_role = app_commands.Group(
        name="selectable-role",
        description="Commands for role self service in guilds",
        guild_only=True,
        guild_ids=[351497847750787084]
    )


    @selectable_role.command(name="add", description="Adds a role to role self service. Admin required.")
    @app_commands.describe(
        role="Role to add to self service",
        description="Description of role. Limit 100 chars",
        emoji="Emoji associated with role (Optional)"
    )
    async def add_role(self, interaction: Interaction, role: Role, description: app_commands.Range[str, 1, 100], emoji: Optional[str]):

        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("You do not have permissions for this command.", ephemeral=True)

        if emoji:
            valid_emoji, bot_can_use = is_valid_emoji(emoji, self.bot)
            if not valid_emoji:
                return await interaction.response.send_message("Emoji entered is not a valid emoji.", ephemeral=True)
            if not bot_can_use:
                return await interaction.response.send_message("The bot must be in the server the emoji is from to use it.", ephemeral=True)

        mallard_guild = MallardGuild()
        await mallard_guild.load(interaction=interaction)

        for role_link in mallard_guild.selectable_roles:
            role_doc = await role_link.fetch()
            if role_doc.role_id == role.id:
                await interaction.response.send_message(f"The role **{role.name}** is already in the self-service menu!", ephemeral=True)
                return
        
        await mallard_guild.add_selectable_role(role=role, description=description, emoji=emoji)
        await mallard_guild.save()

        await self._sync_guild_message(interaction, mallard_guild)

        await interaction.response.send_message(f"Added role {role.name} as selectable.", ephemeral=True)


    @selectable_role.command(name="list", description="Get a list of selectable roles as a dropdown.")
    async def list_role(self, interaction: Interaction):
        mallard_guild = MallardGuild()
        await mallard_guild.load(interaction=interaction)

        selectable_roles = []
        for selectable_role_link in mallard_guild.selectable_roles:
            selectable_role_doc = await selectable_role_link.fetch()
            selectable_roles.append(selectable_role_doc)

        if len(mallard_guild.selectable_roles) > 0:
            list_view = SelectableRoleList(selectable_role_list=selectable_roles)
            await interaction.response.send_message(view=list_view, ephemeral=True)

        else:
            await interaction.response.send_message("No roles are selectable in this guild.", ephemeral=True)


    @selectable_role.command(name="remove", description="Removes a role from role self service. Admin required.")
    @app_commands.describe(role="Role to remove from self service")
    async def remove_role(self, interaction: Interaction, role: Role):

        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("You do not have permissions for this command.", ephemeral=True)

        mallard_guild = MallardGuild()
        await mallard_guild.load(interaction=interaction)

        removed = await mallard_guild.remove_selectable_role(role=role) 
        
        if not removed:
            return await interaction.response.send_message("That role is not currently in the self-service menu.", ephemeral=True)

        await mallard_guild.save()

        await self._sync_guild_message(interaction, mallard_guild)

        await interaction.response.send_message(f"Removed role {role.name} from self-service.", ephemeral=True)


    @selectable_role.command(name="generate-guild-message", description="Creates a message to use as server self-service IN THIS CHANNEL. Admin required.")
    async def generate_guild_message(self, interaction: Interaction):

        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You do not have permissions for this command.", ephemeral=True)

        mallard_guild = MallardGuild()
        await mallard_guild.load(interaction=interaction)

        if mallard_guild.selectable_role_message and mallard_guild.selectable_role_message != 0:
            try:
                channel = interaction.guild.get_channel(mallard_guild.selectable_role_channel)
                msg = await channel.fetch_message(mallard_guild.selectable_role_message)
                return await interaction.response.send_message("A guild message already exists.", ephemeral=True)
            except NotFound:
                mallard_guild.set_selectable_role_message(0)
                mallard_guild.set_selectable_role_channel(0)
                await mallard_guild.save()

        if not mallard_guild.selectable_roles:
            return await interaction.response.send_message("No roles are configured for self-service yet.", ephemeral=True)

        embed = Embed(
            title="Server Roles", 
            description="Select a role from the dropdown below to add or remove it.",
            color=Color.blue()
        )
        
        options = []
        for selectable_role_link in mallard_guild.selectable_roles:
            selectable_role_doc = await selectable_role_link.fetch()
            
            emoji_str = f"{selectable_role_doc.emoji} " if selectable_role_doc.emoji else ""
            embed.add_field(
                name=f"{emoji_str}{selectable_role_doc.role_name}", 
                value=selectable_role_doc.description, 
                inline=False
            )
            
            options.append(SelectOption(
                label=selectable_role_doc.role_name,
                emoji=selectable_role_doc.emoji if selectable_role_doc.emoji != "" else None,
                value=str(selectable_role_doc.role_id) # values must be strings
            ))

        view = PersistentRoleView(options=options)

        await interaction.response.send_message("Generating message...", ephemeral=True)
        msg = await interaction.channel.send(embed=embed, view=view)

        mallard_guild.selectable_role_channel = msg.channel.id
        mallard_guild.selectable_role_message = msg.id
        await mallard_guild.save()

        
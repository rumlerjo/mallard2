from typing import TypeVar, List, Optional
from DatabaseModels import SelectableRole, DatabaseGuild
from discord import Interaction, Role
from .mallard_selectable_role import MallardSelectableRole
from beanie import Link

T = TypeVar("T")
MallardGuild = TypeVar("MallardGuild")

class MallardGuild:
    """
    Wrapper for guild interface to beanie
    """
    def __init__(self):
        self.loaded = False
        self.loaded_guild: DatabaseGuild = None
        self.guild_name: str = ""
        self.guild_id: int = 0
        self.selectable_role_message: int = 0
        self.selectable_role_channel: int = 0
        self.selectable_roles: List[Link[SelectableRole]] = list()

    def set_fields_from_doc(self, guild_doc: DatabaseGuild):
        self.guild_id = guild_doc.guild_id
        self.guild_name = guild_doc.guild_name
        self.selectable_roles = guild_doc.selectable_roles
        self.selectable_role_message = guild_doc.selectable_role_message
        self.selectable_role_channel = guild_doc.selectable_role_channel

    async def load(self, interaction: Optional[Interaction] = None, guild_id: Optional[int] = None):

        if not interaction and not guild_id:
            raise TypeError("User must be initialized by an interaction or guild id")

        if interaction and not guild_id:
            self.guild_id = interaction.guild_id

        if guild_id:
            self.guild_id = guild_id

        guild_doc = await self._get()

        if guild_doc:
            self.set_fields_from_doc(guild_doc)

            self.loaded_guild = guild_doc

        if not guild_doc:
            if interaction:
                self.guild_name = interaction.guild.name
                self.guild_id = interaction.guild_id

                created_doc = await self._create()

                self.set_fields_from_doc(created_doc)

                self.loaded_guild = created_doc

        self.loaded = True

    async def _get(self) -> DatabaseGuild:
        guild = await DatabaseGuild.find_one(DatabaseGuild.guild_id == self.guild_id)
        return guild

    async def _create(self) -> DatabaseGuild:
        new_guild = DatabaseGuild(guild_id=self.guild_id, guild_name=self.guild_name, selectable_roles=self.selectable_roles, 
                                  selectable_role_message=self.selectable_role_message,
                                  selectable_role_channel=self.selectable_role_channel)
        guild = await new_guild.insert()
        return guild

    async def save(self) -> None:
        if not self.loaded:
            return

        if not self.loaded_guild:
            self.loaded_guild = await self._get()

        if self.loaded_guild:
            self.loaded_guild.guild_name = self.guild_name
            self.loaded_guild.selectable_roles = self.selectable_roles
            self.loaded_guild.selectable_role_message = self.selectable_role_message
            self.loaded_guild.selectable_role_channel = self.selectable_role_channel
            await self.loaded_guild.save()

            self.loaded_guild = await self._get()
            self.set_fields_from_doc(self.loaded_guild)

    async def add_selectable_role(self, role: Role, description: str, emoji: Optional[str]):
        """
        Add a selectable role to the guild
        :param role: discord role object of role to add
        :param description: description of role
        :param emoji: optional emoji to represent role
        """
        if not self.loaded:
            return

        new_selectable_role = SelectableRole(role_id=role.id, role_name=role.name, description=description, emoji=emoji)
        mallard_selectable_role = MallardSelectableRole()
        await mallard_selectable_role.load(new_selectable_role)
        await mallard_selectable_role.save()

        self.loaded_guild.selectable_roles.append(mallard_selectable_role.loaded_selectable_role)

    async def remove_selectable_role(self, role: Role) -> bool:
        """
        Removes a selectable role link from the guild and deletes its database entry.
        :param role: discord role object of role to remove
        :return: True if the role was found and removed, False otherwise.
        """
        if not self.loaded or not self.loaded_guild:
            return False

        target_index = -1
        target_doc = None

        for i, role_link in enumerate(self.loaded_guild.selectable_roles):
            doc = await role_link.fetch()
            if doc.role_id == role.id:
                target_index = i
                target_doc = doc
                break
        
        if target_index == -1:
            return False

        self.loaded_guild.selectable_roles.pop(target_index)

        mallard_role = MallardSelectableRole()
        await mallard_role.load(target_doc, loaded=True)
        await mallard_role.delete()

        return True

    def set_selectable_role_message(self, message_id: int):
        self.selectable_role_message = message_id

    def set_selectable_role_channel(self, channel_id: int):
        self.selectable_role_channel = channel_id
    
from typing import TypeVar, List, Optional
from DatabaseModels import SelectableRole, DatabaseGuild
from discord import Interaction

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
        self.selectable_roles: List[SelectableRole] = list()

    async def load(self, interaction: Optional[Interaction] = None, guild_id: Optional[int] = None):

        if not interaction and not guild_id:
            raise TypeError("User must be initialized by an interaction or guild id")

        if interaction and not guild_id:
            self.guild_id = interaction.guild_id

        if guild_id:
            self.guild_id = guild_id

        guild_doc = await self._get()

        if guild_doc:
            self.guild_id = guild_doc.guild_id
            self.guild_name = guild_doc.guild_name
            self.selectable_roles = guild_doc.selectable_roles

            self.loaded_guild = guild_doc

        if not guild_doc:
            if interaction:
                self.guild_name = interaction.guild.name
                self.guild_id = interaction.guild_id

                created_doc = await self._create()

                self.guild_id = created_doc.guild_id
                self.guild_name = created_doc.guild_name
                self.selectable_roles = created_doc.selectable_roles

                self.loaded_guild = created_doc

        self.loaded = True

    async def _get(self) -> DatabaseGuild:
        guild = await DatabaseGuild.find_one(DatabaseGuild.guild_id == self.guild_id)
        return guild

    async def _create(self) -> DatabaseGuild:
        new_guild = DatabaseGuild(guild_id=self.guild_id, guild_name=self.guild_name,
                                  selectable_roles=self.selectable_roles)
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
            await self.loaded_guild.save_changes()
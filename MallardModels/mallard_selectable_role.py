from DatabaseModels import SelectableRole
from typing import Optional
from discord import Role



class MallardSelectableRole:
    """
    Wrapper for selectable roles interface to beanie
    """
    def __init__(self):
        self.loaded = False
        self.loaded_selectable_role: SelectableRole = None
        self.role_id: int = 0
        self.role_name: str = ""
        self.description: str = ""
        self.emoji: str = ""

    async def load(self, selectable_role: SelectableRole, loaded: bool = False):

        if not selectable_role:
            raise TypeError("Selectable role must be initialized by a mock or database document")

        self.role_id = selectable_role.role_id
        self.role_name = selectable_role.role_name
        self.description = selectable_role.description
        self.emoji = selectable_role.emoji

        if loaded:
            self.loaded = True
            self.loaded_selectable_role = SelectableRole
            return
        
        role_doc = await self._get()

        if role_doc:
            self.role_id = role_doc.role_id
            self.role_name = role_doc.role_name
            self.description = role_doc.description
            self.emoji = role_doc.emoji

            self.loaded_selectable_role = role_doc

        if not role_doc:
            created_doc = await self._create()

            self.role_id = created_doc.role_id
            self.role_name = created_doc.role_name
            self.description = created_doc.description
            self.emoji = created_doc.emoji

            self.loaded_selectable_role = created_doc

        self.loaded = True


    async def _get(self) -> SelectableRole:
        role = await SelectableRole.find_one(SelectableRole.role_id == self.role_id)
        return role

    async def _create(self) -> SelectableRole:
        new_selectable_role = SelectableRole(role_id=self.role_id, role_name=self.role_name,
                                             description=self.description, emoji=self.emoji)

        selectable_role = await new_selectable_role.insert()
        return selectable_role

    async def save(self) -> None:
        if not self.loaded:
            return

        if not self.loaded_selectable_role:
            self.loaded_selectable_role = await self._get()

        if self.loaded_selectable_role:
            self.loaded_selectable_role.role_name = self.role_name
            self.loaded_selectable_role.description = self.description
            self.loaded_selectable_role.emoji = self.emoji
            await self.loaded_selectable_role.save_changes()

    async def change_description(self, new_description: str) -> None:
        """
        Change selectable role description. Does not call message refresh or save.
        Must call these explicitly for this to work properly.
        """
        if not self.loaded:
            return
        
        self.description = new_description

    async def change_emoji(self, new_emoji: str) -> None:
        """
        Change selectable role emoji. Does not call message refresh or save.
        Must call these explicitly for this to work properly.
        """
        if not self.loaded:
            return
        
        self.emoji = new_emoji


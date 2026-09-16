from beanie import Document, Link
from DatabaseModels import SelectableRole
from typing import List 

class DatabaseGuild(Document):
    guild_name: str
    guild_id: int
    selectable_role_message: int
    selectable_role_channel: int
    selectable_roles: List[Link[SelectableRole]]

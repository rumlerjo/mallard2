from beanie import Document, Link
from DatabaseModels import SelectableRole
from typing import List 

class DatabaseGuild(Document):
    guild_name: str
    guild_id: int
    selectable_roles: List[Link[SelectableRole]]

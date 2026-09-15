from typing import List
from beanie import Document

from .user import User
from .selectable_role import SelectableRole
from .guild import DatabaseGuild

model_list: List[Document] = [User, SelectableRole, DatabaseGuild]
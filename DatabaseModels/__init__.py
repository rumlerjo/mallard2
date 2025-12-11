from typing import List
from beanie import Document

from .user import User

model_list: List[Document] = [User]
from beanie import Document
from pydantic import Field
from decimal import Decimal

class User(Document):
    name: str
    userid: int
    money: float
    level: int
    experience: float
    needed_experience: float
    level_notifs_on: bool
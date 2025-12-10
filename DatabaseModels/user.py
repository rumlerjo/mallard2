from beanie import Document

class User(Document):
    name: str
    money: float
    experience: int
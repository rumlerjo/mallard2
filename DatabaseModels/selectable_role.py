from beanie import Document


class SelectableRole(Document):
    role_id: int
    role_name: str
    description: str
    emoji: str
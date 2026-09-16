from DatabaseModels import User
from typing import Optional, TypeVar
from discord import Interaction


T = TypeVar("T")
MallardUser = TypeVar("MallardUser")

class MallardUser:
    """
    Defines a database enabled user model for mallard commands to interface
    """

    NEXT_XP_LEVEL_MULTIPLIER = 1.1

    def __init__(self):
        self.loaded = False
        self.loaded_user: User = None
        self.name: str = ""
        self.user_id: int = 0
        self.money: float = 0.00
        self.level = 1
        self.experience: int = 0
        self.needed_experience: int = 300
        self.level_notifs_on: bool = True

    async def load(self, interaction: Optional[Interaction] = None, user_id: Optional[int] = None):

        if not interaction and not user_id:
            raise TypeError("User must be initialized by an interaction or user id")
        
        if interaction:
            self.user_id = interaction.user.id

        if user_id:
            self.user_id = user_id

        user_doc = await self._get()

        if user_doc:
            self.name = user_doc.name
            self.user_id = user_doc.userid
            self.money = user_doc.money
            self.level = user_doc.level
            self.experience = user_doc.experience
            self.needed_experience = user_doc.needed_experience
            self.level_notifs_on = user_doc.level_notifs_on

            self.loaded_user = user_doc
        
        if not user_doc:
            if interaction:
                self.name = interaction.user.name
                self.user_id = interaction.user.id
                created_doc = await self._create()

                self.name = created_doc.name
                self.user_id = created_doc.userid
                self.money = created_doc.money
                self.level = created_doc.level
                self.experience = created_doc.experience
                self.needed_experience = created_doc.needed_experience
                self.level_notifs_on = created_doc.level_notifs_on
    
                self.loaded_user = created_doc
            else:
                raise TypeError("User must be initialized by Interaction on creation")

        self.loaded = True


    async def _get(self) -> User:
        user = await User.find_one(User.userid == self.user_id)
        return user

    async def _create(self) -> User:
        new_user = User(name=self.name, userid=self.user_id, level=self.level,
                        money = self.money, experience=self.experience,
                        needed_experience=self.needed_experience, 
                        level_notifs_on=self.level_notifs_on)
        
        user = await new_user.insert()
        return user
    
    async def save(self) -> None:
        if not self.loaded:
            return

        if not self.loaded_user:
            self.loaded_user = await self._get()
        
        if self.loaded_user:
            self.loaded_user.name = self.name
            self.loaded_user.level = self.level
            self.loaded_user.money = self.money
            self.loaded_user.experience = self.experience
            self.loaded_user.needed_experience = self.needed_experience
            self.loaded_user.level_notifs_on = self.level_notifs_on
            await self.loaded_user.save()

    def add_command_xp(self, xp_to_add: float = 10.00) -> bool:
        if not self.loaded:
            return
        
        levelled_up = False

        self.experience += round(xp_to_add, 2)
        if self.experience >= self.needed_experience:
            difference = round(self.experience - self.needed_experience, 2)
            self.level += 1
            self.experience = difference
            self.needed_experience = round(self.needed_experience * self.NEXT_XP_LEVEL_MULTIPLIER, 2)
            levelled_up = True

        return levelled_up
    
    def add_money(self, money_to_add: float = 0.00):
        if not self.loaded:
            return
        
        self.money += round(money_to_add)

    def change_notif_setting(self, new_setting: bool):
        if not self.loaded:
            return
        
        self.level_notifs_on = new_setting
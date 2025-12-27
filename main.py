from discord import Intents
from discord.ext.commands import Bot
from pymongo import AsyncMongoClient
from beanie import init_beanie
from DatabaseModels import model_list
from Cogs import cog_list

# Create as subclass to get everything on the same event loop
class Mallard(Bot):
    async def setup_hook(self):
        db = AsyncMongoClient("mongodb://localhost:27017/mallard")
        await init_beanie(database=db.db_name, document_models=model_list)

        for cog in cog_list:
            await self.add_cog(cog(self))

intents = Intents.default()
intents.message_content = True

bot = Mallard(command_prefix="^", intents=intents)

bot.run(open("./token.txt").read())
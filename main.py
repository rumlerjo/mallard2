from discord import Intents
from discord.ext.commands import Bot
from pymongo import AsyncMongoClient
from asyncio import run
from beanie import init_beanie
from DatabaseModels import model_list
from Cogs import cog_list

# utter procedural nonsense

async def setup_db():
    db = AsyncMongoClient("mongodb://localhost:27017")
    await init_beanie(database=db.db_name, document_models=model_list)

async def setup_bot() -> Bot:
    intents = Intents.default()
    intents.message_content = True
    client = Bot(command_prefix="^", intents=intents)

    for cog in cog_list:
        await client.add_cog(cog(client))

    return client

def get_token() -> str:
    tokenfile = open("./token.txt", "r")
    token = tokenfile.read()
    tokenfile.close()

    return token

if __name__ == "__main__":
    # run(setup_db())
    client = run(setup_bot())
    client.run(get_token())